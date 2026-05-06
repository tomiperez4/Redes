from lib.transport.segments.segment import Segment


class DataSegment(Segment):
    """
    Segment used to transfer application data.
    Payload is variable and contains the actual file data.
    """
    def __init__(self, seq, data):
        """
        Initializes a data segment containing the given data.
        """
        super().__init__(seq)
        self.data = data

    def get_flags(self):
        return 0

    def get_payload(self):
        return self.data

    def is_data_segment(self): return True
