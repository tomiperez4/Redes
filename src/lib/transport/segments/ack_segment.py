from lib.transport.segments.segment import Segment
from lib.constants.segment_constants import ACK_FLAG


class AckSegment(Segment):
    """
    Segment used to acknowledge received data.
    Contains the acknowledgment number (ack).
    """
    def __init__(self, ack_number):
        super().__init__(ack_number)
        self.ack = ack_number

    def get_flags(self):
        return ACK_FLAG

    def get_payload(self):
        return b""

    def is_ack_segment(self):
        return True

    def get_ack_number(self):
        return self.ack
