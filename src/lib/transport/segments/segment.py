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
        # Cada clase responde sus propias flags según su tipo
        header = struct.pack(self.HEADER_FORMAT, self.seq, self.get_flags())
        return header + self.get_payload()

    @staticmethod
    def from_bytes(data):
        if len(data) < Segment.HEADER_SIZE:
            raise ValueError("Data too short")

        seq, flags = struct.unpack(Segment.HEADER_FORMAT, data[:Segment.HEADER_SIZE])
        payload = data[Segment.HEADER_SIZE:]

        if flags & HSK_FLAG:
            return Segment._parse_handshake(seq, flags, payload)
        if flags & ACK_FLAG:
            from lib.transport.segments.ack_segment import AckSegment
            return AckSegment(seq)
        if flags & FIN_FLAG:
            from lib.transport.segments.finished_segment import FinishedSegment
            return FinishedSegment(seq)

        from lib.transport.segments.data_segment import DataSegment
        return DataSegment(seq, payload, bool(flags & MF_FLAG))

    @staticmethod
    def _parse_handshake(seq, flags, payload):
        hsk_type = payload[0]
        inner = payload[1:]
        if hsk_type == HSK_TYPE_REQUEST:
            from lib.transport.segments.handshake_request_segment import HandshakeRequestSegment
            return HandshakeRequestSegment.from_payload(seq, inner)
        elif hsk_type == HSK_TYPE_RESPONSE:
            from lib.transport.segments.handshake_response_segment import HandshakeResponseSegment
            return HandshakeResponseSegment.from_payload(seq, inner)
        elif hsk_type == HSK_TYPE_READY:
            from lib.transport.segments.handshake_ready_segment import HandshakeReadySegment
            return HandshakeReadySegment(seq)
        elif hsk_type == HSK_TYPE_ERROR:
            from lib.transport.segments.handshake_error_segment import HandshakeErrorSegment
            return HandshakeErrorSegment(seq)
        raise ValueError("Unknown HSK type")

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