import struct
from lib.transport.segments.segment import Segment
from lib.constants.segment_constants import SYN_FLAG


class SynSegment(Segment):
    """
    Segment used to initiate a connection.
    """
    PAYLOAD_FORMAT = "!B"

    def __init__(self, protocol, seq=0):
        """
        Initializes a SYN segment including the protocol the client wants to use.
        """
        super().__init__(seq)
        self.protocol = protocol

    def get_flags(self):
        """
        Returns the SYN flag to identify this segment type.
        """
        return SYN_FLAG

    def get_payload(self):
        """
        Serializes the payload.
        """
        structure = struct.pack("!B", self.protocol)
        return structure

    @staticmethod
    def from_payload(seq, data):
        """
        Deserializes payload into a SynSegment.
        """
        f_size = struct.calcsize(SynSegment.PAYLOAD_FORMAT)
        protocol = struct.unpack(SynSegment.PAYLOAD_FORMAT, data[:f_size])[0]
        return SynSegment(
            protocol,
            seq
        )

    def is_syn_segment(self): return True

    def get_protocol(self):
        return self.protocol
