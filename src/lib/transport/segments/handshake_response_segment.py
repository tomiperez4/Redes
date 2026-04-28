import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import TYPE_HANDSHAKE_RESPONSE

class HandshakeResponseSegment(Segment):
    FORMAT = "!B H I"  # type, port, file size
    SIZE = struct.calcsize(FORMAT)

    def __init__(self, port, size):
        self.port = port
        self.size = size

    def to_bytes(self):
        return struct.pack(
            self.FORMAT,
            TYPE_HANDSHAKE_RESPONSE,
            self.port,
            self.size
        )

    @staticmethod
    def from_bytes(data):
        if len(data) < HandshakeResponseSegment.SIZE:
            raise ValueError("Incomplete handshake response")

        type_, port, size = struct.unpack(
            HandshakeResponseSegment.FORMAT,
            data[:HandshakeResponseSegment.SIZE]
        )

        if type_ != TYPE_HANDSHAKE_RESPONSE:
            raise ValueError("Not a handshake response")

        return HandshakeResponseSegment(port, size)

    def is_handshake_response_segment(self):
        return True

    def get_port(self):
        return self.port

    def get_size(self):
        return self.size