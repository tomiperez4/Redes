import struct
from src.lib.transport.segments.segment import Segment

HANDSHAKE_REQUEST = 2

class HandshakeRequestSegment(Segment):
    HEADER_FORMAT = "!B B B H 4s"
    # type, operation, protocol, reserved, port, host
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, operation, protocol, port, host, filename):
        self.operation = operation      # 0 = upload, 1 = download
        self.protocol = protocol        # 0 = stop and wait, 1 = go back n
        self.port = port
        self.host = host
        self.filename = filename

    def to_bytes(self):
        header = struct.pack(
            self.HEADER_FORMAT,
            HANDSHAKE_REQUEST,
            self.operation,
            self.protocol,
            self.port,
            self.host
        )

        filename_bytes = self.filename.encode("utf-8")
        return header + filename_bytes

    @staticmethod
    def from_bytes(data):
        if len(data) < HandshakeRequestSegment.HEADER_SIZE:
            raise ValueError("Incomplete handshake request")

        type_, operation, protocol, port, host = struct.unpack(
            HandshakeRequestSegment.HEADER_FORMAT,
            data[:HandshakeRequestSegment.HEADER_SIZE]
        )

        if type_ != HANDSHAKE_REQUEST:
            raise ValueError("Not a handshake request")

        filename = data[HandshakeRequestSegment.HEADER_SIZE:]
        filename = filename.decode("utf-8") if filename else None

        return HandshakeRequestSegment(operation, protocol, port, host, filename)

    def is_handshake_request_segment(self):
        return True