import socket as socket_module
import threading
import time
from collections import deque

from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol
from lib.common import MAX_SEQ, WINDOW_SIZE, MAX_PACKET_SIZE, MAX_GBN_RETRIES
from lib.transport.segments.finished_segment import FinishedSegment
from socket import error as sock_err


class GoBackN(ReliableProtocol):
    def __init__(self, socket, address, log):
        super().__init__(socket, log)

        self.send_buffer = []
        self.receive_queue = deque()
        self.lock = threading.Lock()

        # Sender stuff
        self.base = 0
        self.next_idx = 0
        self.sent_times = {}
        self.address = address
        self.retransmitted = set()

        self.fin_seq = -1

        self.socket.settimeout(self.timeout_interval)

        # Receiver stuff
        self.expected_seq = 0

        # Thread stuff
        self.closed = False
        self.done = False
        self.send_event = threading.Event()
        self.repeat_event = threading.Event()

        self.sender_thread = threading.Thread(target=self.__sender_loop, daemon=True)
        self.receiver_thread = threading.Thread(target=self.__receiver_loop, daemon=True)

        self.sender_thread.start()
        self.receiver_thread.start()

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
        self.closed = True
        self.send_event.set()

        while True:
            with self.lock:
                buffer_flushed = self.base >= len(self.send_buffer)
            if buffer_flushed:
                break
            time.sleep(0.05)

        with self.lock:
            self.fin_seq = len(self.send_buffer) % MAX_SEQ
        fin_pkt = FinishedSegment(self.fin_seq)

        retries = 0

        while retries < MAX_GBN_RETRIES:
            try:
                self.socket.sendto(fin_pkt.to_bytes(), self.address)
                self.log.debug(f"FINISHED segment sent with seq={self.fin_seq} (attempt {retries + 1}/{MAX_GBN_RETRIES})")
            except sock_err:
                self.log.debug("Socket error sending FINISHED segment, shutting down")
                self.done = True
                return

            deadline = time.time() + self.timeout_interval
            while time.time() < deadline:
                if self.done:
                    self.log.info("Connection closed successfully.")
                    return
                time.sleep(0.01)

            retries += 1
            self.log.warning(f"FIN timeout, retrying ({retries}/{MAX_GBN_RETRIES})")

        self.log.warning("Max FIN retries reached, assuming peer is gone")
        self.done = True

    def __sender_loop(self):
        while not self.done:
            self.send_event.wait()
            self.send_event.clear()

            if self.repeat_event.is_set():
                self.repeat_event.clear()
                with self.lock:
                    self.next_idx = self.base

            while True:
                with self.lock:
                    if self.next_idx >= self.base + WINDOW_SIZE:
                        break
                    if self.next_idx >= len(self.send_buffer):
                        break

                    pkt = self.send_buffer[self.next_idx]
                    seq = self.next_idx % MAX_SEQ

                    if self.next_idx not in self.sent_times and self.next_idx not in self.retransmitted:
                        self.sent_times[self.next_idx] = time.time()

                    current_idx = self.next_idx
                    self.next_idx += 1

                self.socket.sendto(pkt.to_bytes(), self.address)
                self.log.debug(f"Sent idx={current_idx} seq={seq}")

    def __receiver_loop(self):
        while not self.done:
            try:
                raw, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
                seg = Segment.from_bytes(raw)

                if seg.is_data_segment():
                    self.__handle_incoming_data(seg, addr)
                elif seg.is_ack_segment():
                    if self.closed and self.fin_seq != -1 and seg.seq == self.fin_seq:
                        self.log.debug("FIN ACK received, closing")
                        self.done = True
                        return
                    self.__handle_incoming_ack(seg.seq)
                elif seg.is_finished_segment():
                    self.__handle_incoming_finished(seg.seq, addr)

            except socket_module.timeout:
                with self.lock:
                    if self.base == self.next_idx:
                        continue
                self.__handle_timeout()

            except sock_err:
                self.done = True
                self.socket.close()
                return

    def __handle_incoming_data(self, seg, addr):
        with self.lock:
            if seg.seq == self.expected_seq:
                self.log.debug(f"Data received in order: seq={seg.seq}")
                self.receive_queue.append(seg.get_payload())
                self.expected_seq = (self.expected_seq + 1) % MAX_SEQ
            else:
                self.log.warning(f"Out of order! Got {seg.seq}, expected {self.expected_seq}")

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
                if found_idx in self.sent_times and found_idx not in self.retransmitted:
                    sample = time.time() - self.sent_times[found_idx]
                    self._update_rto(sample)

                old_base = self.base
                self.base = found_idx + 1

                for idx in range(old_base, self.base):
                    self.sent_times.pop(idx, None)
                    self.retransmitted.discard(idx)

                self.log.debug(f"ACK received: {ack_val}. New base: {self.base}")
                self.send_event.set()

    def __handle_incoming_finished(self, seq, addr):
        self.log.debug(f"FINISHED segment received with seq={seq}")
        with self.lock:
            self.done = True
            ack_pkt = AckSegment(seq)
        retries = 0

        while retries < MAX_GBN_RETRIES:
            try:
                self.socket.sendto(ack_pkt.to_bytes(), addr)
                self.log.debug(f"FIN ACK sent (ack={seq}) (attempt {retries + 1}/{MAX_GBN_RETRIES})")
            except sock_err:
                self.log.debug("Socket error sending FIN ACK, shutting down")
                return

            time.sleep(self.timeout_interval)
            retries += 1

        self.log.warning("Max FIN ACK retries reached, assuming peer received it")

    def __handle_timeout(self):
        self.log.warning("Timeout! Retransmitting window...")
        self.timeout_interval = min(self.timeout_interval * 2, 0.8)
        self.socket.settimeout(self.timeout_interval)
        with self.lock:
            for idx in range(self.base, self.next_idx):
                self.retransmitted.add(idx)
            self.sent_times.clear()
        self.repeat_event.set()
        self.send_event.set()