import os

from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.handshake_ready_segment import HandshakeReadySegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol
from lib.logger import Logger
from lib.transport.segments.constants import SW_MAX_RETRIES
import socket as socket_module
import time

SEGMENT_SIZE = 1024
MAX_PACKET_SIZE = SEGMENT_SIZE + DataSegment.HEADER_SIZE
TIMEOUT = 0.1

# Modularizar, agregar retries
class StopAndWait(ReliableProtocol):
    def __init__(self, socket, verbose, quiet):
        super().__init__(socket)
        self.log = Logger('STOP-AND-WAIT', verbose, quiet)
        # Variables para RTO Dinámico
        self.srtt = TIMEOUT
        self.rttvar = TIMEOUT / 2
        self.rto = TIMEOUT

    def _update_rto(self, sample_rtt):
        alpha, beta = 0.125, 0.25
        self.srtt = (1 - alpha) * self.srtt + alpha * sample_rtt
        self.rttvar = (1 - beta) * self.rttvar + beta * abs(self.srtt - sample_rtt)
        self.rto = self.srtt + max(0.02, 4 * self.rttvar)  # Mínimo 50ms para evitar timeouts agresivos

    def send(self, address, path):
        self.socket.settimeout(self.rto)
        seq = 0
        with open(path, "rb") as file:
            while True:
                chunk = file.read(SEGMENT_SIZE)

                if not chunk:
                    self.log.info("End of file reached")
                    pkt = DataSegment(seq, b"", 0)
                    while True:
                        self.socket.sendto(pkt.to_bytes(), address)
                        self.log.info("End of file segment sent")
                        try:
                            raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                            received = Segment.from_bytes(raw)

                            if isinstance(received, AckSegment) and received.ack == seq:
                                self.log.info("Received confirmation ACK segment. End connection")
                                return

                        except socket_module.timeout:
                            self.log.error("Timeout while waiting for ACK segment. Retry")
                            continue

                pkt = DataSegment(seq, chunk, 1)
                retransmitted = False
                retries = 0

                while retries < SW_MAX_RETRIES:
                    start_time = time.time()
                    self.socket.sendto(pkt.to_bytes(), address)
                    self.log.info("Data segment sent")
                    try:
                        raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                        received = Segment.from_bytes(raw)
                        if isinstance(received, AckSegment) and received.ack == seq:
                            # Solo actualizamos RTO si no fue una retransmisión (Karn)
                            if not retransmitted:
                                sample_rtt = time.time() - start_time
                                self._update_rto(sample_rtt)
                                self.socket.settimeout(self.rto)
                                self.log.debug(f"New RTO: {self.rto:.4f}s")

                            self.log.info("Received ACK segment. Equals expected")
                            seq = 1 - seq
                            break
                        self.log.debug("Received ACK segment. Does not equals expected")
                    except socket_module.timeout:
                        retries += 1
                        self.log.error(f"Timeout... retry {retries}/{SW_MAX_RETRIES}")
                        retransmitted = True
                        self.rto = min(self.rto * 2, 4.0)
                        self.socket.settimeout(self.rto)
                        continue
                if retries == SW_MAX_RETRIES:
                    raise Exception("Max retries reached. Connection lost")

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
                            self.log.info("Client disconnected (FINISHED PACKET RECEIVED).")
                            os.remove(temp_file)
                            return

                        if packet.is_handshake_response_segment():
                            if not handshake_done and address == addr:
                                self.log.info("Duplicated handshake response segment received. Re-sending READY segment")
                                ready_pkt = HandshakeReadySegment()
                                self.socket.sendto(ready_pkt.to_bytes(), address)
                            continue

                        if not packet.is_data_segment():
                            self.log.error("Unexpected segment. Retry")
                            continue

                        handshake_done = True
                        self.log.info("Data segment received")
                        if packet.seq == expected_seq:
                            self.log.info("Packets sequence numbers match")
                            data = packet.data
                            output_file.write(data)
                            ack = AckSegment(expected_seq)
                            self.socket.sendto(ack.to_bytes(), address)
                            self.log.info("ACK segment sent")
                            expected_seq = 1 - expected_seq
                            if packet.mf == 0:
                                self.log.info("Final data segment received. End connection")
                                break
                        else:
                            self.log.error("Packet sequence numbers do not match. Letting sender know")
                            ack = AckSegment(1 - expected_seq)
                            self.socket.sendto(ack.to_bytes(), address)
                            self.log.info("ACK segment sent")
                    except socket_module.timeout:
                        if not handshake_done:
                            self.log.info("Timeout waiting for data. Resending READY...")
                            self.socket.sendto(HandshakeReadySegment().to_bytes(), address)
                        else:
                            self.log.debug("Timeout waiting for packet... still listening")
                        continue
            os.rename(temp_file, output_path)
            self.log.info("File transfer complete")
        except Exception as error:
            self.log.error(f"File transfer failed: {error}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
