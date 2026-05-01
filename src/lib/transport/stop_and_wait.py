import socket as socket_module
import threading
import time
from collections import deque

from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol
from lib.constants.socket_constants import MAX_PACKET_SIZE

class StopAndWait(ReliableProtocol):
    def __init__(self, socket, log):
        super().__init__(socket, log)

        # Buffers
        self.send_buffer = deque()
        self.receive_buffer = deque()
        self.lock = threading.Lock()

        # Estado
        self.send_seq = 0
        self.expected_seq = 0
        self.waiting_ack = False
        self.last_pkt_sent = None
        self.address = None

        self.closed = False
        self.done = False

        self.worker_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.worker_thread.start()

    # api pública de sw

    def start(self, address):
        self.address = address
        self.socket.settimeout(0.1)

    def send(self, data):
        with self.lock:
            self.send_buffer.append(data)

    def recv(self):
        while not self.receive_buffer:
            if self.done: return None
            time.sleep(0.01)
        with self.lock:
            return self.receive_buffer.popleft()

    def close(self):
        self.closed = True
        while not self.done:
            time.sleep(0.1)

    # loop principal

    def _main_loop(self):
        last_send_time = 0
        sample_start_time = 0
        while not self.done:
            try:
                try:
                    raw, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
                    seg = Segment.from_bytes(raw)

                    if seg.is_ack_segment():
                        with self.lock:
                            if self.waiting_ack and seg.ack == self.send_seq:
                                sample_rtt = time.time() - sample_start_time
                                self._update_rto(sample_rtt)

                                self.log.debug(f"ACK {seg.ack} recibido. RTT: {sample_rtt:.4f}s. Nuevo RTO: {self.timeout_interval:.4f}s")

                                self.waiting_ack = False
                                self.send_seq = 1 - self.send_seq

                    elif seg.is_data_segment():
                        self._handle_data(seg, addr)

                except socket_module.timeout:
                    pass

                if self.waiting_ack and (time.time() - last_send_time > self.timeout_interval):
                    self.log.warning(f"Timeout! Re-enviando seq={self.send_seq}")
                    self.socket.sendto(self.last_pkt_sent.to_bytes(), self.address)
                    last_send_time = time.time()

                if not self.waiting_ack:
                    with self.lock:
                        if self.send_buffer:
                            data = self.send_buffer.popleft()
                            pkt = DataSegment(self.send_seq, data, 1)
                            self.last_pkt_sent = pkt
                            self.waiting_ack = True

                            sample_start_time = time.time()
                            self.socket.sendto(pkt.to_bytes(), self.address)
                            last_send_time = sample_start_time
                            self.log.debug(f"Enviado seq={self.send_seq}")

                        elif self.closed:
                            # MAAAL HAY QUE USAR FINISHED PACKET
                            pkt = DataSegment(self.send_seq, b"", 0)
                            self.socket.sendto(pkt.to_bytes(), self.address)
                            self.done = True

            except Exception as e:
                self.log.error(f"Error en loop: {e}")

    # manejo de segmentos

    def _handle_segment(self, seg, addr):
        if seg.is_data_segment():
            self._handle_data(seg, addr)
        elif seg.is_ack_segment():
            self._handle_ack(seg.ack)

    def _handle_data(self, seg, addr):
        with self.lock:
            if seg.seq == self.expected_seq:
                self.log.debug(f"Data received: seq={seg.seq}")
                if seg.payload:  # ESTO ESTA MAL HAY QUECAMBIARLO CUANDO USEMOS EL FINISHED PACKET
                    self.receive_buffer.append(seg.payload)
                self.expected_seq = 1 - self.expected_seq


            ack_val = 1 - self.expected_seq
            ack_pkt = AckSegment(ack_val)
            self.socket.sendto(ack_pkt.to_bytes(), addr)

    def _handle_ack(self, ack_val):
        with self.lock:
            if self.waiting_ack and ack_val == self.send_seq:
                self.log.debug(f"ACK received for seq={self.send_seq}")
                self.waiting_ack = False
                self.send_seq = 1 - self.send_seq