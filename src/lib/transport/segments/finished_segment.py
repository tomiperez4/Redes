from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import FIN_FLAG


class FinishedSegment(Segment):
    def __init__(self, seq=0):
        super().__init__(seq)

    def get_flags(self):
        return FIN_FLAG

    def get_payload(self):
        # Un paquete FIN suele no tener payload
        return b""

    def is_finished_segment(self):
        return True
