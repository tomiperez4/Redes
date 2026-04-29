import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import TYPE_ACK

class AckSegment(Segment):
    FORMAT = "!B B"  # type, ack
    SIZE = struct.calcsize(FORMAT)

    def __init__(self, ack):
        self.ack = ack

    def to_bytes(self):
        return struct.pack(
            self.FORMAT,
            TYPE_ACK,
            self.ack
        )

    @staticmethod
    def from_bytes(raw):
        type_, ack = struct.unpack(
            AckSegment.FORMAT,
            raw[:AckSegment.SIZE]
        )
        return AckSegment(ack)

    def is_ack_segment(self):
        return True
