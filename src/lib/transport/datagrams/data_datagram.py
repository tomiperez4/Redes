import struct
from src.lib.transport.datagrams.datagram import Datagram

class DataDatagram(Datagram):
    HEADER_FORMAT = "!B B B"  # type, seq_number
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, seq, data, mf):
        self.seq = seq
        self.data = data
        self.mf = mf

    def to_bytes(self):
        header = struct.pack(
            self.HEADER_FORMAT,
            self.seq,
            self.mf
        )

        return header + self.data

    @staticmethod
    def from_bytes(raw):
        type_data, seq, length = struct.unpack(
            DataDatagram.HEADER_FORMAT,
            raw[:DataDatagram.HEADER_SIZE]
        )

        data = raw[
            DataDatagram.HEADER_SIZE :
            DataDatagram.HEADER_SIZE + length
        ]

        return DataDatagram(seq, data)
