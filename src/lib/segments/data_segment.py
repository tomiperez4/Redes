import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import TYPE_DATA

class DataSegment(Segment):
    HEADER_FORMAT = "!B B B"  # type, seq_number, mf
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, seq, data, mf):
        self.seq = seq
        self.data = data
        self.mf = mf

    def to_bytes(self):
        header = struct.pack(
            self.HEADER_FORMAT,
            TYPE_DATA,
            self.seq,
            self.mf
        )

        return header + self.data

    @staticmethod
    def from_bytes(data):
        type_data, seq, mf = struct.unpack(
            DataSegment.HEADER_FORMAT,
            data[:DataSegment.HEADER_SIZE]
        )

        payload = data[DataSegment.HEADER_SIZE:]

        return DataSegment(seq, payload, mf)

    def is_data_segment(self):
        return True