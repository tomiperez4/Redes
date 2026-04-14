import struct
from src.lib.transport.datagram import *

class DataDatagram(Datagram):
    HEADER_FORMAT = "!B B H"  # type, seq_number, length
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, seq, data):
        self.type = TYPE_DATA
        self.seq = seq
        self.data = data

    def to_bytes(self):
        length = len(self.data)

        header = struct.pack(
            self.HEADER_FORMAT,
            self.type,
            self.seq,
            length
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
