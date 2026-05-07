import struct
from abc import ABC, abstractmethod
from lib.transport.segments.constants import SYN_FLAG, ACK_FLAG, FIN_FLAG, SYN_ACK_FLAG


class Segment(ABC):
    """
    Base class for all protocol segments.
    [ seq (1 byte) | flags (1 byte) | payload (variable) ]
    """
    HEADER_FORMAT = "!BB"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, seq):
        """
        Initializes a segment with a seq number.
        """
        self.seq = seq

    @abstractmethod
    def get_flags(self):
        """
        Returns the flags that identify the segment type.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def get_payload(self):
        """
        Returns the payload (data) of the segment.
        Must be implemented by subclasses.
        """
        pass

    def to_bytes(self):
        """
        Serializes the segment into bytes.
        """
        header = struct.pack(self.HEADER_FORMAT, self.seq, self.get_flags())
        return header + self.get_payload()

    @staticmethod
    def from_bytes(data):
        """
        Deserializes raw bytes into the correct Segment subclass.
        """
        if len(data) < Segment.HEADER_SIZE:
            raise ValueError("Data too short")
        seq, flags = struct.unpack(
            Segment.HEADER_FORMAT, data[:Segment.HEADER_SIZE])
        payload = data[Segment.HEADER_SIZE:]
        if flags & SYN_FLAG:
            from lib.transport.segments.syn_segment import SynSegment
            return SynSegment.from_payload(seq, payload)
        if flags & SYN_ACK_FLAG:
            from lib.transport.segments.synack import SynackSegment
            return SynackSegment.from_payload(seq, payload)
        if flags & ACK_FLAG:
            from lib.transport.segments.ack_segment import AckSegment
            return AckSegment(seq)
        if flags & FIN_FLAG:
            from lib.transport.segments.finished_segment import FinishedSegment
            return FinishedSegment(seq)

        from lib.transport.segments.data_segment import DataSegment
        return DataSegment(seq, payload)

    # Helpers
    def is_data_segment(self):
        return False

    def is_ack_segment(self):
        return False

    def is_syn_segment(self):
        return False

    def is_synack_segment(self):
        return False

    def is_finished_segment(self):
        return False