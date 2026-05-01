import struct
from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import SYN_FLAG

class SynSegment(Segment):
    PAYLOAD_FORMAT = "!B"

    def __init__(self, protocol, seq=0):
        super().__init__(seq)
        self.protocol = protocol

    def get_flags(self):
        return SYN_FLAG

    def get_payload(self):
        structure = struct.pack("!B", self.protocol)
        return structure

    @staticmethod
    def from_payload(seq, data):
        f_size = struct.calcsize(SynSegment.PAYLOAD_FORMAT)
        fields = struct.unpack(SynSegment.PAYLOAD_FORMAT, data[:f_size])
        protocol = fields
        return SynSegment(
            protocol,
            seq
        )

    def is_syn_segment(self): return True

    def get_protocol(self):
        return self.protocol