from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol
from lib.logger import Logger
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
        self.rto = self.srtt + max(0.05, 4 * self.rttvar)  # Mínimo 50ms para evitar timeouts agresivos

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
                                self.log.info("Received confirmation ACK segment. End conn")
                                return

                        except socket_module.timeout:
                            self.log.error("Timeout while waiting for ACK segment. Retry")
                            continue

                pkt = DataSegment(seq, chunk, 1)
                retransmitted = False
                while True:
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
                        self.log.error(f"Timeout ({self.rto:.4f}s) while waiting for ACK segment. Retry")
                        retransmitted = True
                        # Backoff exponencial al fallar
                        self.rto = min(self.rto * 2, 4.0)
                        self.socket.settimeout(self.rto)
                        continue

    def receive(self, address, output_path):
        expected_seq = 0
        with open(output_path, "wb") as output_file:
            while True:
                raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                packet = Segment.from_bytes(raw)

                if not isinstance(packet, DataSegment):
                    self.log.error("Unexpected data segment. Retry")
                    continue

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
                        self.log.info("Final data segment received. End conn")
                        break
                else:
                    self.log.error("Packet sequence numbers do not match. Let sender know")
                    ack = AckSegment(1 - expected_seq)
                    self.socket.sendto(ack.to_bytes(), address)
                    self.log.info("ACK segment sent")