import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import HSK_FLAG, HSK_TYPE_REQUEST

class HandshakeRequestSegment(Segment):
    PAYLOAD_FORMAT = "!BBHBH4s"

    def __init__(self, operation, protocol, size, port, host, filename, seq=0):
        super().__init__(seq)
        self.operation, self.protocol, self.size = operation, protocol, size
        self.port, self.host, self.filename = port, host, filename

    def get_flags(self):
        return HSK_FLAG

    def get_payload(self):
        prefix = struct.pack("!B", HSK_TYPE_REQUEST)
        fixed = struct.pack(self.PAYLOAD_FORMAT, self.operation, self.protocol,
                           self.size, self.port, self.host)
        return prefix + fixed + self.filename.encode("utf-8")

    @staticmethod
    def from_payload(seq, data):
        f_size = struct.calcsize(HandshakeRequestSegment.PAYLOAD_FORMAT)
        fields = struct.unpack(HandshakeRequestSegment.PAYLOAD_FORMAT, data[:f_size])
        name = data[f_size:].decode("utf-8")
        return HandshakeRequestSegment(seq, *fields, name)

    def is_handshake_request_segment(self): return True