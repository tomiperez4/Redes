import socket as socket_module
from lib.logger import Logger
from lib.transport.rdt import ReliableProtocol
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.segment import Segment
from lib.transport.segments.ack_segment import AckSegment

SEGMENT_SIZE = 1024
MAX_PACKET_SIZE = 1027
WINDOW_SIZE = 10
TIMEOUT = 2.0

class GoBackN(ReliableProtocol):
    def __init__(self, socket, verbose, quiet):
        super().__init__(socket)
        self.socket = socket
        self.log = Logger(socket, verbose, quiet)

    def send(self, address, path):
        base = 0
        next_seq_num = 0
        seq = 0
        packets = []

        with open(path, "rb") as f:
            while True:
                chunk = f.read(SEGMENT_SIZE)
                if not chunk:
                    break
                packets.append(DataSegment(seq, chunk, 1))
                seq += 1

        packets.append(DataSegment(seq, b"", 0))
        total_packets = len(packets)

        while base < total_packets:
            while next_seq_num < base + WINDOW_SIZE and next_seq_num < total_packets:
                self.socket.sendto(packets[next_seq_num].to_bytes(), address)
                if base == next_seq_num:
                    self.socket.settimeout(TIMEOUT)
                next_seq_num += 1

            try:
                data, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
                ack_pkt = Segment.from_bytes(data)

                if ack_pkt.is_ack_segment() and ack_pkt.ack >= base:
                    base = ack_pkt.ack + 1
                    if base == next_seq_num:
                        self.socket.settimeout(None)
                    else:
                        self.socket.settimeout(TIMEOUT)

            except socket_module.timeout:
                next_seq_num = base

    def receive(self, address, output_path):
        expected_seq_num = 0
        with open(output_path, "wb") as f:
            while True:
                try:
                    data, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
                    segment = Segment.from_bytes(data)

                    if segment.is_data_segment():
                        if segment.seq_num == expected_seq_num:
                            f.write(segment.data)
                            ack = AckSegment(expected_seq_num)
                            self.socket.sendto(ack.to_bytes(), addr)
                            expected_seq_num += 1

                            if segment.mf == 0:
                                break
                        else:
                            if expected_seq_num > 0:
                                ack = AckSegment(expected_seq_num - 1) 
                                self.socket.sendto(ack.to_bytes(), addr)
                except Exception:
                    break