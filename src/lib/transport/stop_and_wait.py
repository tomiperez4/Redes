import os

from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.handshake_ready_segment import HandshakeReadySegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol
from lib.constants.protocol_constants import MAX_RETRIES, ALPHA, BETA
from lib.constants.socket_constants import BUFFER_SIZE, TIMEOUT, MAX_PACKET_SIZE
import socket as socket_module
import time

class StopAndWait(ReliableProtocol):
    def __init__(self, socket, log):
        super().__init__(socket, log)
        self.estimated_rtt = TIMEOUT
        self.dev_rtt = 0
        self.timeout_interval = TIMEOUT

    def _update_rto(self, sample_rtt):
        self.estimated_rtt = (1 - ALPHA) * self.estimated_rtt + ALPHA * sample_rtt
        self.dev_rtt = (1 - BETA) * self.dev_rtt + BETA * abs(self.estimated_rtt - sample_rtt)
        self.timeout_interval = self.estimated_rtt + 4 * self.dev_rtt

# Send ---------------------------------------------------------------------------------------------------
    def send(self, address, path):
        self.socket.settimeout(self.timeout_interval)
        seq = 0

        try:
            with open(path, "rb") as file:
                while True:
                    chunk = file.read(BUFFER_SIZE)

                    if not chunk:
                        self.log.debug("End of file reached")
                        self._send_final_data_segment(seq, address)
                        return
                    self._reliable_send(seq, chunk, 1, address)
                    seq = 1 - seq
        except Exception as error:
            self.log.error(f"Transfer failed: {error}")
            raise

    def _reliable_send(self, seq, data, mf, address):
        pkt = DataSegment(seq, data, mf)
        retries = 0
        retransmitted = False

        while retries < MAX_RETRIES:
            start_time = time.time()
            self.socket.sendto(pkt.to_bytes(), address)
            self.log.debug(f"Segment sent (seq={seq}, mf={mf})")

            try:
                if self._wait_for_specific_ack(seq):
                    if not retransmitted:
                        self._handle_rto_update(time.time() - start_time)
                    return True

            except socket_module.timeout:
                retries += 1
                retransmitted = True
                self._handle_timeout_backoff(retries)

        raise Exception("Max retries reached. Connection lost")

    def _wait_for_specific_ack(self, expected_seq):
        raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
        received = Segment.from_bytes(raw)

        if received.is_ack_segment() and received.ack == expected_seq:
            self.log.debug("Received ACK segment matches expected seq")
            return True

        self.log.debug("Received ACK segment does not match")
        return False

    def _send_final_data_segment(self, seq, address):
        pkt = DataSegment(seq, b"", 0)
        while True:
            self.socket.sendto(pkt.to_bytes(), address)
            self.log.debug("End of file segment sent")
            try:
                raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                received = Segment.from_bytes(raw)

                if received.is_ack_segment() and received.ack == seq:
                    self.log.debug("Received confirmation ACK segment. End connection")
                    return

            except socket_module.timeout:
                self.log.warning("Timeout while waiting for ACK segment. Retry")
                continue

    def _handle_rto_update(self, sample_rtt):
        self._update_rto(sample_rtt)
        self.socket.settimeout(self.timeout_interval)
        self.log.debug(f"New RTO: {self.timeout_interval:.4f}s")

    def _handle_timeout_backoff(self, retry_count):
        self.log.warning(f"Timeout... retry {retry_count}/{MAX_RETRIES}")
        self.timeout_interval = self.estimated_rtt + max(0.1, 4 * self.dev_rtt)
        self.socket.settimeout(self.timeout_interval)

# Receive ------------------------------------------------------------------------------------------------
    def receive(self, address, output_path):
        handshake_done = False
        expected_seq = 0
        temp_file = output_path + ".tmp"

        try:
            with open(temp_file, "wb") as output_file:
                while True:
                    try:
                        raw, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
                        packet = Segment.from_bytes(raw)

                        if packet.is_finished():
                            self._handle_early_disconnect(temp_file)
                            return

                        if packet.is_handshake_response_segment():
                            self._handle_handshake_retry(handshake_done, address, addr)
                            continue

                        if not packet.is_data_segment():
                            self.log.warning("Unexpected segment. Retry")
                            continue

                        handshake_done = True
                        finished, expected_seq = self._process_data_packet(packet, expected_seq, address, output_file)
                        if finished:
                            break
                    except socket_module.timeout:
                        self.log.warning("Timeout waiting for packet... still listening")
                        continue
            os.rename(temp_file, output_path)
            self.log.info("File transfer complete")
        except Exception as error:
            self._cleanup_error(temp_file, error)

    def _handle_early_disconnect(self, temp_file):
        self.log.debug("Client disconnected (FINISHED PACKET RECEIVED).")
        if os.path.exists(temp_file):
            os.remove(temp_file)

    def _handle_handshake_retry(self, handshake_done, target_addr, sender_addr):
        if not handshake_done and target_addr == sender_addr:
            self.log.debug("Duplicated handshake response. Re-sending READY")
            ready_pkt = HandshakeReadySegment()
            self.socket.sendto(ready_pkt.to_bytes(), target_addr)

    def _process_data_packet(self, packet, expected_seq, address, output_file):
        self.log.debug(f"Data segment received (Seq: {packet.seq})")

        if packet.seq == expected_seq:
            self.log.debug("Packets sequence numbers match")
            output_file.write(packet.data)
            self._send_ack(expected_seq, address)

            new_expected_seq = 1 - expected_seq

            if packet.mf == 0:
                self.log.debug("Final data segment received.")
                return True, new_expected_seq
            return False, new_expected_seq
        else:
            self.log.warning("Sequence mismatch. Sending ACK for previous packet")
            self._send_ack(1 - expected_seq, address)
            return False, expected_seq

    def _send_ack(self, seq, address):
        ack = AckSegment(seq)
        self.socket.sendto(ack.to_bytes(), address)
        self.log.debug(f"ACK {seq} sent")

    def _cleanup_error(self, temp_file, error):
        self.log.error(f"File transfer failed: {error}")
        if os.path.exists(temp_file):
            os.remove(temp_file)