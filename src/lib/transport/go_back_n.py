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
    """
    Implementation of the Go-Back-N reliable transport protocol.

    Features:
    - Sliding window for sending multiple packets
    - Cumulative ACKs
    - Retransmission on timeout
    - Concurrent sender and receiver threads
    - Graceful termination with FIN
    """
    def __init__(self, socket, address, log):
        super().__init__(socket, log)

        self.send_buffer = []
        self.receive_queue = deque()
        self.lock = threading.Lock()

        # Sender stuff
        self.base = 0
        self.next_idx = 0
        self.fin_seq = None
        self.sent_times = {}
        self.address = address
        self.retransmitted = set()

        self.socket.settimeout(self.timeout_interval)
        # Receiver stuff
        self.expected_seq = 0

        # Thread stuff
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

    def send(self, data):
        """
        Adds data to the send buffer.
        Data is not sent immediately, but queued and handled asynchronously by the sender thread.
        """
        with self.lock:
            seq = len(self.send_buffer) % MAX_SEQ
            pkt = DataSegment(seq, data)
            self.send_buffer.append(pkt)
        self.send_event.set()

    def recv(self):
        """
        Returns the next received data chunk.
        Blocks until data is available or connection ends.
        """
        while not self.receive_queue:
            if self.done:
                return None
            time.sleep(0.01)
        with self.lock:
            return self.receive_queue.popleft()

    def is_done(self):
        return self.done

    def close(self):
        """
        Sends a FINISHED segment and waits until the connection is closed.
        """
        with self.lock:
            seq = len(self.send_buffer) % MAX_SEQ
            pkt = FinishedSegment(seq)
            self.send_buffer.append(pkt)
            self.closed = True

        self.send_event.set()

        # Block until the receiver confirms the FINISHED packet and sets self.done
        while not self.done:
            time.sleep(0.1)
        self.log.info("Connection closed successfully.")

    def __sender_loop(self):
        """
        Continuously sends packets within the sliding window.

        Handles:
        - window control
        - retransmissions
        - FINISHED transfer completion
        """
        while not self.done:
            self.send_event.wait()
            self.send_event.clear()

            # Check if retransmission is needed
            if self.repeat_event.is_set():
                self.repeat_event.clear()
                with self.lock:
                    self.next_idx = self.base

            while True:
                with self.lock:
                    # If window is full, can't send
                    if self.next_idx >= self.base + WINDOW_SIZE:
                        break

                    # Check if there is no more data to send
                    if self.next_idx >= len(self.send_buffer):
                        if self.closed and self.base == len(self.send_buffer):
                            self.done = True
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
        """
        Continuously receives packets and processes them.

        Handles:
        - incoming data
        - ACKs
        - FIN segments
        - timeout detection
        """
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
                with self.lock:
                    if self.base == self.next_idx:
                        continue
                self.__handle_timeout()

    def __handle_incoming_data(self, seg, addr):
        """
        Handles an incoming DATA segment.

        - Accepts the packet only if it is in order
        - Stores payload in receive queue
        - Updates expected sequence number
        - Always sends a cumulative ACK (last correctly received)
        """
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
        """
        Handles an incoming ACK.

        - Finds the corresponding packet in the send window
        - Updates base (slides the window)
        - Updates RTT estimation if possible
        - Triggers sender to continue sending

        :param ack_val: acknowledged sequence number
        """
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
                self.log.debug(
                    f"ACK received: {ack_val}. New base: {
                        self.base}")
                self.send_event.set()

    def __handle_incoming_finished(self, seq, addr):
        """
        Handles an incoming FIN segment.

        - Verifies correct sequence
        - Marks connection as done
        - Sends final ACK
        """
        self.log.debug("FINISHED segment received")
        with self.lock:
            if seq == self.expected_seq:
                self.log.debug(f"FINISHED segment received OK")
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
        """
        Handles retransmission timeout.

        - Triggers retransmission of the current window
        - Applies exponential backoff to timeout
        - Clears RTT samples for recalculation
        """
        self.log.warning("Timeout! Retransmitting window...")
        self.timeout_interval = self.timeout_interval * 2
        self.socket.settimeout(self.timeout_interval)
        with self.lock:
            for idx in range(self.base, self.next_idx):
                self.retransmitted.add(idx)
            self.sent_times.clear()
        self.repeat_event.set()
        self.send_event.set()