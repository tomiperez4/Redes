import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import TYPE_HANDSHAKE_ERROR

class HandshakeErrorSegment(Segment):
    FORMAT = "!B"  # type

    def __init__(self):
        pass

    def to_bytes(self):
        return struct.pack(
            self.FORMAT,
            TYPE_HANDSHAKE_ERROR)

    @staticmethod
    def from_bytes(data):
        return HandshakeErrorSegment()

    def is_handshake_error_segment(self):
        return True