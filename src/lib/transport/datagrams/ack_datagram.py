import struct
from src.lib.transport.datagrams.datagram import Datagram

class AckDatagram(Datagram):
    FORMAT = "!B B"  # type, ack
    SIZE = struct.calcsize(FORMAT)

    def __init__(self, ack):
        self.ack = ack

    def to_bytes(self):
        return struct.pack(
            self.FORMAT,
            self.ack
        )

    @staticmethod
    def from_bytes(raw):
        type_, ack = struct.unpack(
            AckDatagram.FORMAT,
            raw[:AckDatagram.SIZE]
        )

        return AckDatagram(ack)
