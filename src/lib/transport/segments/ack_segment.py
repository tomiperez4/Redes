import struct
from src.lib.transport.segments.segment import Segment

class AckSegment(Segment):
    FORMAT = "!B B"  # type, ack
    SIZE = struct.calcsize(FORMAT)

    def __init__(self, ack):
        self.ack = ack

    def to_bytes(self):
        return struct.pack(
            self.FORMAT,
            self.ack
        )

    @staticmethod
    def from_bytes(raw):
        type_, ack = struct.unpack(
            AckSegment.FORMAT,
            raw[:AckSegment.SIZE]
        )
        return AckSegment(ack)

    @staticmethod
    def is_ack_segment():
        return True
