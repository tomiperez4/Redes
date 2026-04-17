import queue

from src.lib.transport.datagrams.ack_datagram import AckDatagram
from src.lib.transport.datagrams.data_datagram import DataDatagram
from src.lib.transport.datagrams.datagram import Datagram

SEGMENT_SIZE = 1024
TIMEOUT = 0.5

class StopAndWait:
    def __init__(self, socket):
        self.socket = socket
        self.seq = 0
        self.send_queue = queue.Queue()

    def send_file(self, data, address, path):
        self.socket.settimeout(TIMEOUT)

        seq = 0
        i = 0

        with open(path, "rb") as file:
            while True:
                chunk = file.read(SEGMENT_SIZE)

                if not chunk:
                    break
                pkt = DataDatagram(seq, chunk, 1 if i + SEGMENT_SIZE < len(data) else 0)
                self.socket.sendto(pkt.to_bytes(), address)

                try:
                    raw, _ = self.socket.recvfrom(SEGMENT_SIZE)
                    received = Datagram.from_bytes(raw)

                    if isinstance(received, AckDatagram) and received.ack == seq:
                        break

                except self.socket.timeout:
                    continue

                i += SEGMENT_SIZE
                seq = 1 - seq

    def receive_file(self, address, output_path):
        expected_seq = 0
        with open(output_path, "wb") as output_file:
            while True:
                raw, addr = self.socket.recvfrom(SEGMENT_SIZE)
                packet = Datagram.from_bytes(raw)

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

