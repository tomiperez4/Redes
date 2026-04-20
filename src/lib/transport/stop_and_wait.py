import queue

from src.lib.transport.segments.ack_segment import AckSegment
from src.lib.transport.segments.data_segment import DataSegment
from src.lib.transport.segments.segment import Segment
from src.lib.transport.rdt import ReliableProtocol

SEGMENT_SIZE = 1024
TIMEOUT = 0.5

class StopAndWait(ReliableProtocol):
    def __init__(self, socket):
        super().__init__(socket)
        self.seq = 0

    def send(self, address, path, queue):
        self.socket.settimeout(TIMEOUT)
        seq = 0
        with open(path, "rb") as file:
            while True:
                chunk = file.read(SEGMENT_SIZE)

                if not chunk:
                    pkt = DataDatagram(seq, b"", 0)
                    while True:
                        self.socket.sendto(pkt.to_bytes(), address)
                        try:
                            received = queue.get()

                            if isinstance(received, AckDatagram) and received.ack == seq:
                                return

                        except self.socket.timeout:
                            continue
                pkt = DataDatagram(seq, chunk, 1)
                while True:
                    self.socket.sendto(pkt.to_bytes(), address)
                    try:
                        raw, _ = self.socket.recvfrom(SEGMENT_SIZE)
                        received = Datagram.from_bytes(raw)
                        if isinstance(received, AckDatagram) and received.ack == seq:
                            seq = 1 - seq
                            break
                    except self.socket.timeout:
                        continue

    def receive(self, address, output_path, queue):
        expected_seq = 0
        with open(output_path, "wb") as output_file:
            while True:
                packet = queue.get()
                if isinstance(packet, DataDatagram):
                    if packet.seq == expected_seq:
                        data = packet.data
                        output_file.write(data)
                        ack = AckDatagram(expected_seq)
                        self.socket.sendto(ack.to_bytes(), address)
                        expected_seq = 1 - expected_seq
                        if packet.mf == 0:
                            break
                    else:
                        ack = AckDatagram(1 - expected_seq)
                        self.socket.sendto(ack.to_bytes(), addr)

