import struct
from lib.transport.segments.segment import Segment

HANDSHAKE_READY = 4

class HandshakeReadySegment(Segment):
    FORMAT = "!B"  # type

    def __init__(self):
        pass

    def to_bytes(self):
        return struct.pack(
            self.FORMAT,
            HANDSHAKE_READY)

    @staticmethod
    def from_bytes(data):
        return HandshakeReadySegment()

    def is_handshake_ready_segment(self):
        return True