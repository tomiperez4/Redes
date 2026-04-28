import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import TYPE_HANDSHAKE_REQUEST

class HandshakeRequestSegment(Segment):
    HEADER_FORMAT = "!B B H B H 4s"
    # type, operation, protocol, size, reserved, port, host
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, operation, protocol, size, port, host, filename):
        self.operation = operation      # 0 = upload, 1 = download
        self.protocol = protocol        # 0 = stop and wait, 1 = go back n
        self.port = port
        self.size = size                # Represents file size in MB
        self.host = host
        self.filename = filename

    def to_bytes(self):
        header = struct.pack(
            self.HEADER_FORMAT,
            TYPE_HANDSHAKE_REQUEST,
            self.operation,
            self.protocol,
            self.size,
            self.port,
            self.host
        )

        filename_bytes = self.filename.encode("utf-8")
        return header + filename_bytes

    @staticmethod
    def from_bytes(data):
        if len(data) < HandshakeRequestSegment.HEADER_SIZE:
            raise ValueError("Incomplete handshake request")

        type_, operation, protocol, size, port, host = struct.unpack(
            HandshakeRequestSegment.HEADER_FORMAT,
            data[:HandshakeRequestSegment.HEADER_SIZE]
        )

        if type_ != TYPE_HANDSHAKE_REQUEST:
            raise ValueError("Not a handshake request")

        filename = data[HandshakeRequestSegment.HEADER_SIZE:]
        filename = filename.decode("utf-8") if filename else None

        return HandshakeRequestSegment(operation, protocol, size, port, host, filename)

    def is_handshake_request_segment(self):
        return True