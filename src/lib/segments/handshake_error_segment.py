import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import HSK_FLAG, HSK_TYPE_ERROR

class HandshakeErrorSegment(Segment):
    def __init__(self, seq=0):
        super().__init__(seq)

    def get_flags(self):
        return HSK_FLAG

    def get_payload(self):
        return struct.pack("!B", HSK_TYPE_ERROR)

    def is_handshake_error_segment(self):
        return True