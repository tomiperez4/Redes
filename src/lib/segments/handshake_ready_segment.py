import struct
from lib.segments.segment import Segment
from lib.constants.segment_constants import TYPE_HANDSHAKE_READY

class HandshakeReadySegment(Segment):
    FORMAT = "!B"  # type

    def __init__(self):
        pass

    def to_bytes(self):
        return struct.pack(
            self.FORMAT,
            TYPE_HANDSHAKE_READY)

    @staticmethod
    def from_bytes(data):
        return HandshakeReadySegment()

    def is_handshake_ready_segment(self):
        return True