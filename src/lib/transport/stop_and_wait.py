import socket as socket_module
import time
import threading
import queue

from lib.common import MAX_PACKET_SIZE
from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.finished_segment import FinishedSegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol
from lib.transport.segments.data_segment import DataSegment
from socket import error as sock_err


class StopAndWait(ReliableProtocol):
    """
    Implementation of the Stop-and-Wait reliable transport protocol.
    """
    def __init__(self, socket, address, log):
        super().__init__(socket, log)
        self.address = address
        self._send_seq = 0
        self._expected_seq = 0
        self.socket.settimeout(self.timeout_interval)

        self._data_queue = queue.Queue()
        self._ack_queue = queue.Queue()
        self._fin_received = threading.Event()

        self._reader_thread = threading.Thread(target=self.__reader_loop, daemon=True)
        self._reader_thread.start()


    def send(self, data: bytes):
        """
        Sends data reliably using Stop-and-Wait ARQ.

        Steps:
        1. Sends data packet
        2. Waits for ACK
        3. If timeout, retransmits
        4. If ACK received, toggle sequence number
        """
        pkt = DataSegment(self._send_seq, data)
        retransmitted = False

        while True:
            with self._ack_queue.mutex:
                self._ack_queue.queue.clear()

            self.socket.sendto(pkt.to_bytes(), self.address)
            self.log.debug(f"Data sent with seq={self._send_seq}")
            t_send = time.time()

            ack = self.__wait_for_ack(self._send_seq)

            if ack is None:
                retransmitted = True
                self.log.warning(f"Timeout. Resending data with seq={self._send_seq}")
                self.timeout_interval = min(self.timeout_interval * 2, 0.8)
                continue

            if ack.is_finished_segment():
                self.__handle_fin_segment()
                return 1

            if not retransmitted:
                self._update_rto(time.time() - t_send)
            self.log.debug(
                f"ACK {self._send_seq} received. RTO={self.timeout_interval:.4f}s"
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
            try:
                return self._data_queue.get(timeout=0.05)
            except queue.Empty:
                pass

            if self._fin_received.is_set():
                try:
                    return self._data_queue.get_nowait()
                except queue.Empty:
                    return None

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
                # El ACK del FIN también llega por _ack_queue
                seg = self._ack_queue.get(timeout=self.timeout_interval)
                if seg.is_ack_segment() and seg.get_ack_number() == 0:
                    self.log.debug("FIN ACK received. Closing socket")
                    self.socket.close()
                    return
            except queue.Empty:
                self.log.debug("Timeout. Resending FINISHED segment")
                continue


    def __reader_loop(self):
        """
        Classifies each arriving segment:
          - ACK / FIN
          - DATA
        """
        while True:
            try:
                raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
            except socket_module.timeout:
                continue
            except sock_err:
                return  # socket cerrado

            seg = Segment.from_bytes(raw)

            if seg.is_ack_segment():
                self._ack_queue.put(seg)

            elif seg.is_finished_segment():
                # Notifies send() if it was sending, and recv()
                self._ack_queue.put(seg)
                self.__handle_fin_segment()
                self._fin_received.set()
                return

            elif seg.is_data_segment():
                if seg.seq == self._expected_seq:
                    self.log.debug(f"Data received with seq={seg.seq}")
                    ack = AckSegment(self._expected_seq)
                    self.socket.sendto(ack.to_bytes(), self.address)
                    self._expected_seq = 1 - self._expected_seq
                    self._data_queue.put(seg.get_payload())
                else:
                    self.log.debug(
                        f"Out of order: got={seg.seq}, expected={self._expected_seq}. "
                        "Resending last ACK"
                    )
                    last_ack = AckSegment(1 - self._expected_seq)
                    self.socket.sendto(last_ack.to_bytes(), self.address)

            else:
                self.log.debug("Unknown segment type, ignoring")


    def __wait_for_ack(self, expected_ack):
        """
        Waits in _ack_queue until timeout.
        """
        deadline = time.time() + self.timeout_interval

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None

            try:
                seg = self._ack_queue.get(timeout=remaining)
            except queue.Empty:
                return None

            if seg.is_finished_segment():
                return seg

            if seg.is_ack_segment():
                if seg.get_ack_number() == expected_ack:
                    return seg
                self.log.debug(
                    f"Unexpected ACK: got={seg.get_ack_number()}, expected={expected_ack}"
                )

    def __handle_fin_segment(self):
        """
        Handles FINISHED segment reception and sends final ACKs before closing.
        """
        retries = 10
        ack = AckSegment(0)
        while retries > 0:
            try:
                self.socket.sendto(ack.to_bytes(), self.address)
                time.sleep(0.1)
            except sock_err:
                break
            retries -= 1
        self.socket.close()
        return