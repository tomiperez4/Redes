import socket as socket_module
import threading
import time
from collections import deque

from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol
from lib.constants.protocol_constants import MAX_SEQ, WINDOW_SIZE
from lib.constants.socket_constants import MAX_PACKET_SIZE
from lib.transport.segments.finished_segment import FinishedSegment


class GoBackN(ReliableProtocol):
    def __init__(self, socket, address, log):
        super().__init__(socket, log)

        self.send_buffer = []
        self.receive_queue = deque()
        self.lock = threading.Lock()

        # cositas para el sender
        self.base = 0
        self.next_idx = 0
        self.fin_seq = None
        self.sent_times = {}
        self.address = address

        self.socket.settimeout(self.timeout_interval)
        # cositas para el receiver
        self.expected_seq = 0

        # cositas para los hilos
        self.closed = False
        self.done = False
        self.send_event = threading.Event()
        self.repeat_event = threading.Event()

        # Threads
        self.sender_thread = threading.Thread(
            target=self.__sender_loop, daemon=True)
        self.receiver_thread = threading.Thread(
            target=self.__receiver_loop, daemon=True)

        self.sender_thread.start()
        self.receiver_thread.start()

    # Public API

    def send(self, data):
        with self.lock:
            seq = len(self.send_buffer) % MAX_SEQ
            pkt = DataSegment(seq, data)
            self.send_buffer.append(pkt)
        self.send_event.set()

    def recv(self):
        while not self.receive_queue:
            if self.done:
                return None
            time.sleep(0.01)
        with self.lock:
            return self.receive_queue.popleft()

    def is_done(self):
        return self.done

    def close(self):
        with self.lock:
            seq = len(self.send_buffer) % MAX_SEQ
            pkt = FinishedSegment(seq)
            self.send_buffer.append(pkt)
            self.closed = True

        self.send_event.set()

        # Bloqueamos hasta que el receptor confirme el FIN y setee self.done
        while not self.done:
            time.sleep(0.1)
        self.log.info("Connection closed successfully.")

    # Sender

    def __sender_loop(self):
        while not self.done:
            self.send_event.wait()
            self.send_event.clear()

            # chequeamos is hay que retransmitir por timeout
            if self.repeat_event.is_set():
                self.repeat_event.clear()
                with self.lock:
                    self.next_idx = self.base

            while True:
                with self.lock:
                    # si la ventana está llena no se puede enviar
                    if self.next_idx >= self.base + WINDOW_SIZE:
                        break

                    # si no hay más datos para enviar
                    if self.next_idx >= len(self.send_buffer):
                        if self.closed and self.base == len(self.send_buffer):
                            self.done = True
                        break

                    pkt = self.send_buffer[self.next_idx]
                    seq = self.next_idx % MAX_SEQ

                    if self.next_idx not in self.sent_times:
                        self.sent_times[self.next_idx] = time.time()

                    current_idx = self.next_idx
                    self.next_idx += 1

                self.socket.sendto(pkt.to_bytes(), self.address)
                self.log.debug(f"Sent idx={current_idx} seq={seq}")

    # Receiver

    def __receiver_loop(self):
        while not self.done:
            try:
                raw, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
                seg = Segment.from_bytes(raw)

                if seg.is_data_segment():
                    self.__handle_incoming_data(seg, addr)

                elif seg.is_ack_segment():
                    self.__handle_incoming_ack(seg.ack)

                elif seg.is_finished_segment():
                    self.__handle_incoming_finished(seg.seq, addr)

            except socket_module.timeout:
                self.__handle_timeout()

    def __handle_incoming_data(self, seg, addr):
        with self.lock:
            if seg.seq == self.expected_seq:
                self.log.debug(f"Data received in order: seq={seg.seq}")
                self.receive_queue.append(seg.get_payload())
                self.expected_seq = (self.expected_seq + 1) % MAX_SEQ
            else:
                self.log.warning(
                    f"Out of order! Got {
                        seg.seq}, expected {
                        self.expected_seq}")

            last_ack = (self.expected_seq - 1) % MAX_SEQ
            ack_pkt = AckSegment(last_ack)
            self.socket.sendto(ack_pkt.to_bytes(), addr)

    def __handle_incoming_ack(self, ack_val):
        with self.lock:
            found_idx = -1
            for idx in range(self.base, self.next_idx):
                if idx % MAX_SEQ == ack_val:
                    found_idx = idx
                    break

            if found_idx != -1:
                if found_idx in self.sent_times:
                    sample = time.time() - self.sent_times[found_idx]
                    self._update_rto(sample)

                self.base = found_idx + 1
                self.log.debug(
                    f"ACK received: {ack_val}. New base: {
                        self.base}")
                self.send_event.set()

    def __handle_incoming_finished(self, seq, addr):
        self.log.debug("FIN received")
        with self.lock:
            if seq == self.expected_seq:
                self.log.debug(f"FIN received OK")
                self.expected_seq = (self.expected_seq + 1) % MAX_SEQ
                self.done = True
            else:
                self.log.warning(
                    f"FIN out of order!")

            last_ack = (self.expected_seq - 1) % MAX_SEQ
            ack_pkt = AckSegment(last_ack)
            self.socket.sendto(ack_pkt.to_bytes(), addr)

    # Helpers

    def __handle_timeout(self):
        self.log.warning("Timeout! Retransmitting window...")
        with self.lock:
            self.sent_times.clear()  # Limpiar para recalcular RTT en retransmisión
        self.repeat_event.set()
        self.send_event.set()

# ESTO ESTÁ MAAAAAAL ACÁ HAY QUE USAR EL FINISHED SEGMENT Y HACER EL ACK Y ESO
    def _send_fin(self):
        seq = self.base % MAX_SEQ
        pkt = DataSegment(seq, b"")
        self.socket.sendto(pkt.to_bytes(), self.address)