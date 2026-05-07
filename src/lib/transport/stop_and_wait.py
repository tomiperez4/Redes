import socket as socket_module
import time

from lib.common import MAX_PACKET_SIZE
from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.finished_segment import FinishedSegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol
from socket import error as sock_err

class StopAndWait(ReliableProtocol):
    """
    Implementation of the Stop-and-Wait reliable transport protocol.

    Features:
    - Sends one packet at a time
    - Waits for ACK before sending next
    - Retransmits on timeout
    - Handles duplicate packets
    """
    def __init__(self, socket, address, log):
        """
        Initializes Stop-and-Wait protocol.
        """
        super().__init__(socket, log)
        self.address = address
        self._send_seq = 0
        self._expected_seq = 0
        self.socket.settimeout(self.timeout_interval)

    def send(self, data: bytes):
        """
        Sends data reliably using Stop-and-Wait ARQ.

        Steps:
        1. Sends data packet
        2. Waits for ACK
        3. If timeout, retransmits
        4. If ACK received, toggle sequence number
        """
        self.__drain_socket()
        pkt = DataSegment(self._send_seq, data)
        retransmitted = False

        while True:
            self.socket.sendto(pkt.to_bytes(), self.address)
            self.log.debug(f"Data sent with seq={self._send_seq}")
            t_send = time.time()

            ack = self.__wait_for_ack(self._send_seq)

            if ack is None:
                retransmitted = True
                self.log.warning(f"Timeout. Resending data with seq={self._send_seq}")
                self.timeout_interval = self.timeout_interval * 2
                self.socket.settimeout(self.timeout_interval)
                continue

            if ack.is_finished_segment():
                self.__handle_fin_segment()
                return 1
            if ack is not None:
                if not retransmitted:
                    self._update_rto(time.time() - t_send)
                self.log.debug(
                    f"ACK {self._send_seq} received. "
                    f"RTO={self.timeout_interval:.4f}s"
                )
                self._send_seq = 1 - self._send_seq
                return 0


    def recv(self):
        """
        Receives data reliably.

        - Accepts in-order packets only
        - Sends ACK for valid packets
        - Ignores duplicates or unexpected segments
        - Handles FIN
        """
        while True:
            seg = self.__try_recv()
            if seg is None:
                continue

            if seg.is_finished_segment():
                self.__handle_fin_segment()
                return None

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
        """
        Gracefully closes the connection.
        Sends FIN repeatedly until ACK is received or timeout occurs.
        """
        self.socket.settimeout(self.timeout_interval)

        fin = FinishedSegment()

        while True:
            self.socket.sendto(fin.to_bytes(), self.address)
            self.log.debug("FINISHED segment sent")

            try:
                raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                seg = Segment.from_bytes(raw)

                if seg.is_ack_segment() and seg.get_ack_number() == 0:
                    self.log.debug("FIN ACK received. Closing socket")
                    self.socket.close()
                    return

            except socket_module.timeout:
                self.log.debug("Timeout. Resending FINISHED segment")
                continue

    # Helpers

    def __drain_socket(self):
        """
        Clears any pending residue in the socket buffer.
        """
        self.socket.setblocking(False)
        try:
            while True:
                self.socket.recvfrom(MAX_PACKET_SIZE)
        except:
            pass
        finally:
            self.socket.settimeout(self.timeout_interval)

    def __wait_for_ack(self, expected_ack):
        """
        Waits for a valid ACK within timeout.
        :return: ACK segment or None if timeout
        """
        deadline = time.time() + self.timeout_interval

        while True:
            remaining = deadline - time.time()
            if remaining < 0:
                return None

            self.socket.settimeout(remaining)
            seg = self.__try_recv()

            if seg is None:
                continue

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
        """
        Attempts to receive a packet.
        :return: parsed Segment or None if timeout
        """
        try:
            raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
            return Segment.from_bytes(raw)
        except socket_module.timeout:
            return None

    def __handle_fin_segment(self):
        """
        Handles FINISHED segment reception and sends final ACKs before closing.
        """
        self.log.info("FIN segment received. Peer is closing")
        end_time = time.time() + 2
        ack = AckSegment(0)

        while time.time() < end_time:
            try:
                self.socket.sendto(ack.to_bytes(), self.address)
                time.sleep(self.timeout_interval)
            except sock_err:
                self.socket.close()
                return None
        return None