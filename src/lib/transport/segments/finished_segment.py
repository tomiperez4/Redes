from lib.transport.segments.segment import Segment
from lib.constants.segment_constants import FIN_FLAG


class FinishedSegment(Segment):
    """
    Segment used to signal the end of a transmission.
    It does not contain payload.
    """
    def __init__(self, seq=0):
        """
        Initializes a FIN segment.
        """
        super().__init__(seq)

    def get_flags(self):
        return FIN_FLAG

    def get_payload(self):
        return b""

    def is_finished_segment(self):
        return True
