from lib.transport.segments.segment import Segment
from lib.transport.segments.constants import MF_FLAG

class DataSegment(Segment):
    def __init__(self, seq, data, mf=False):
        super().__init__(seq)
        self.data = data
        self.mf = mf

    def get_flags(self):
        return MF_FLAG if self.mf else 0

    def get_payload(self):
        return self.data

    def is_data_segment(self): return True