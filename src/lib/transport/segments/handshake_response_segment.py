import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import HSK_FLAG, HSK_TYPE_RESPONSE

class HandshakeResponseSegment(Segment):
    PAYLOAD_FORMAT = "!HI"

    def __init__(self, port, size, seq=0):
        super().__init__(seq)
        self.port, self.size = port, size

    def get_flags(self):
        return HSK_FLAG

    def get_payload(self):
        prefix = struct.pack("!B", HSK_TYPE_RESPONSE)
        data = struct.pack(self.PAYLOAD_FORMAT, self.port, self.size)
        return prefix + data

    @staticmethod
    def from_payload(seq, data):
        port, size = struct.unpack(HandshakeResponseSegment.PAYLOAD_FORMAT, data)
        return HandshakeResponseSegment(seq, port, size)

    def is_handshake_response_segment(self): return True