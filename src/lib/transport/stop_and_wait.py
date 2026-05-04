import socket as socket_module
import time

from lib.constants.socket_constants import MAX_PACKET_SIZE
from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.finished_segment import FinishedSegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol

INITIAL_TIMEOUT = 0.5

class StopAndWait(ReliableProtocol):
    def __init__(self, socket, address, log):
        super().__init__(socket, log)
        self.address = address
        self._send_seq = 0
        self._expected_seq = 0
        self._timeout = INITIAL_TIMEOUT
        self._srtt = None
        self._rttvar = None
        self.socket.settimeout(self._timeout)

    # Public API

    def send(self, data: bytes):
        pkt = DataSegment(self._send_seq, data)

        while True:
            self.socket.sendto(pkt.to_bytes(), self.address)
            self.log.debug(f"Data sent with seq={self._send_seq}")
            t_send = time.time()

            ack = self.__wait_for_ack(self._send_seq)

            if ack.is_finished_segment():
                self.__handle_fin_segment()
                return 1
            if ack is not None:
                self._update_rto(time.time() - t_send)
                self.log.debug(
                    f"ACK {self._send_seq} received. "
                    f"RTO={self._timeout:.4f}s"
                )
                self._send_seq = 1 - self._send_seq
                return 0

            self.log.warning(f"Timeout. Resending data with seq={self._send_seq}")

    def recv(self):
        while True:
            seg = self.__try_recv()
            if seg is None:
                continue

            if seg.is_finished_segment():
                self.__handle_fin_segment()

            if not seg.is_data_segment():
                self.log.debug("Unexpected segment. Keep trying to receive data")
                continue

            if seg.seq == self._expected_seq:
                self.log.debug(f"Data received with seq={seg.seq}")
                ack = AckSegment(self._expected_seq)
                self.socket.sendto(ack.to_bytes(), self.address)
                self.log.debug(f"ACK sent for seq={self._expected_seq}")
                self._expected_seq = 1 - self._expected_seq
                return seg.get_payload()
            else:
                self.log.debug(
                    f"Out of order: got={seg.seq}, "
                    f"expected={self._expected_seq}. Resending ACK for expected seq"
                )
                last_ack = AckSegment(1 - self._expected_seq)
                self.socket.sendto(last_ack.to_bytes(), self.address)

    def close(self):
        self.socket.settimeout(self._timeout)

        fin = FinishedSegment(self._send_seq)

        while True:
            self.socket.sendto(fin.to_bytes(), self.address)
            self.log.debug("FIN sent")

            try:
                raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                seg = Segment.from_bytes(raw)

                if seg.is_ack_segment() and seg.get_ack_number() == self._send_seq:
                    self.log.debug("FIN ACK received. Closing socket")
                    self.socket.close()
                    return

            except socket_module.timeout:
                self.log.debug("Timeout. Resending FIN segment")
                continue

    # Helpers

    def __wait_for_ack(self, expected_ack):
        deadline = time.time() + self._timeout

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None

            self.socket.settimeout(remaining)
            seg = self.__try_recv()

            if seg is None:
                return None

            if seg.is_finished_segment():
                return seg

            if seg.is_ack_segment():
                if seg.get_ack_number() == expected_ack:
                    return seg
                self.log.debug(
                    f"Unexpected ACK: got={seg.get_ack_number()}, expected={expected_ack}"
                )
                continue

            self.log.debug("Unexpected segment. Keep trying to receive ACK")

    def __try_recv(self):
        try:
            raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
            return Segment.from_bytes(raw)
        except socket_module.timeout:
            return None

    def __handle_fin_segment(self):
        self.log.info("FIN segment received. Peer is closing")
        ack = AckSegment(self._expected_seq)
        self.socket.sendto(ack.to_bytes(), self.address)
        end_time = time.time() + 2

        while time.time() < end_time:
            seg_rep = self.__try_recv()

            if seg_rep and seg_rep.is_finished_segment():
                self.log.debug("Retransmitted FIN received, resending ACK")
                self.socket.sendto(ack.to_bytes(), self.address)

        self.socket.close()
        self.log.info("Received FIN packet. Socket closed")
        return None
    '''
    def __update_rto(self, sample_rtt: float):
        if self._srtt is None:
            self._srtt = sample_rtt
            self._rttvar = sample_rtt / 2
        else:
            self._rttvar = (
                (1 - BETA) * self._rttvar
                + BETA * abs(self._srtt - sample_rtt)
            )
            self._srtt = (1 - ALPHA) * self._srtt + ALPHA * sample_rtt

        self._timeout = self._srtt + 4 * self._rttvar
        self.socket.settimeout(self._timeout)
    '''
