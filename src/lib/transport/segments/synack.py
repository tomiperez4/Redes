import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import SYN_ACK_FLAG


class SynackSegment(Segment):
    PAYLOAD_FORMAT = "!H"

    def __init__(self, port, seq=0):
        super().__init__(seq)
        self.port = port

    def get_flags(self):
        return SYN_ACK_FLAG

    def get_payload(self):
        structure = struct.pack("!H", self.port)
        return structure

    @staticmethod
    def from_payload(seq, data):
        f_size = struct.calcsize(SynackSegment.PAYLOAD_FORMAT)
        port = struct.unpack(SynackSegment.PAYLOAD_FORMAT, data[:f_size])[0]
        return SynackSegment(
            port,
            seq
        )

    def is_synack_segment(self):
        return True

    def get_port(self):
        return self.port
