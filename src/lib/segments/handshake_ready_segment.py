import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import HSK_FLAG, HSK_TYPE_READY

class HandshakeReadySegment(Segment):
    def __init__(self, seq=0):
        super().__init__(seq)

    def get_flags(self):
        return HSK_FLAG

    def get_payload(self):
        # El primer byte del payload indica que es un READY
        return struct.pack("!B", HSK_TYPE_READY)

    def is_handshake_ready_segment(self):
        return True