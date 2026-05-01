import struct
from abc import ABC, abstractmethod
from lib.transport.segments.constants import *


class Segment(ABC):
    HEADER_FORMAT = "!BB"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, seq):
        self.seq = seq

    @abstractmethod
    def get_flags(self):
        # Cada subclase mete los flags que necesita
        pass

    @abstractmethod
    def get_payload(self):
        pass

    def to_bytes(self):
        header = struct.pack(self.HEADER_FORMAT, self.seq, self.get_flags())
        return header + self.get_payload()

    @staticmethod
    def from_bytes(data):
        if len(data) < Segment.HEADER_SIZE:
            raise ValueError("Data too short")

        seq, flags = struct.unpack(Segment.HEADER_FORMAT, data[:Segment.HEADER_SIZE])
        payload = data[Segment.HEADER_SIZE:]

        if flags & SYN_ACK_FLAG:
            from lib.transport.segments.synack import SynackSegment
            return SynackSegment.from_payload(seq, payload)
        if flags & SYN_FLAG:
            from lib.transport.segments.syn_segment import SynSegment
            return SynSegment.from_payload(seq, payload)
        if flags & ACK_FLAG:
            from lib.transport.segments.ack_segment import AckSegment
            return AckSegment(seq)
        if flags & FIN_FLAG:
            from lib.transport.segments.finished_segment import FinishedSegment
            return FinishedSegment(seq)

        from lib.transport.segments.data_segment import DataSegment
        return DataSegment(seq, payload, bool(flags & MF_FLAG))

    # Helpers de interfaz
    def is_data_segment(self):
        return False

    def is_ack_segment(self):
        return False

    def is_handshake_request_segment(self):
        return False

    def is_handshake_response_segment(self):
        return False

    def is_handshake_ready_segment(self):
        return False

    def is_handshake_error_segment(self):
        return False

    def is_finished(self):
        return False

    def is_syn_segment(self):
        return False

    def is_synack_segment(self):
        return False