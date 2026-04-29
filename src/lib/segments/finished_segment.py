import struct
from lib.segments.segment import Segment
from lib.constants.segment_constants import TYPE_FINISHED

class FinishedSegment(Segment):
    FORMAT = "!B"  # type
    SIZE = struct.calcsize(FORMAT)

    def __init__(self):
        pass

    def to_bytes(self):
        return struct.pack(self.FORMAT, TYPE_FINISHED)

    @staticmethod
    def from_bytes(data):
        return FinishedSegment()

    def is_finished(self):
        return True