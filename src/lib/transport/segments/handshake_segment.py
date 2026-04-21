import socket
import struct

from src.lib.transport.segments.segment import Segment

HANDSHAKE_TYPE = 2

SERVER_ROLE = 0
CLIENT_ROLE = 1

class HandshakeSegment(Segment):
    HEADER_FORMAT = "!B B B B H 4s"  # handshake_type, role, type download or upload, protocol, port, host
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, role, type, protocol, port, host, filename):
        self.role = role
        self.type = type
        self.protocol = protocol
        self.port = port
        self.host = host
        self.filename = filename

    def to_bytes(self):
        header = struct.pack(
            self.HEADER_FORMAT,
            HANDSHAKE_TYPE,
            self.role,
            self.type,
            self.protocol,
            self.port,
            self.host
        )
        if self.filename is not None:
            return header + self.filename.encode('utf-8')
        return header

    @staticmethod
    def from_bytes(data):
        header_size = HandshakeSegment.HEADER_SIZE

        if len(data) < header_size:
            raise ValueError("Incomplete handshake segment")

        handshake_type, role, type_, protocol, port, host = struct.unpack(
            HandshakeSegment.HEADER_FORMAT,
            data[:header_size]
        )

        if handshake_type != HANDSHAKE_TYPE:
            raise ValueError("Not a handshake segment")

        filename = data[header_size:] if len(data) > header_size else None

        return HandshakeSegment(role, type_, protocol, port, host, filename)

    @staticmethod
    def create_server_handshake(port):
        role = SERVER_ROLE
        #these fields are going to be ignored by clients
        type = 0
        protocol = 0
        host = socket.inet_aton('0.0.0.0')

        return HandshakeSegment(role, type, protocol, port, host, None)

    @staticmethod
    def create_client_handshake(filename, protocol, type, port, host):
        return HandshakeSegment(CLIENT_ROLE, type, protocol, port, host, filename)

    @staticmethod
    def is_handshake_segment():
        return True