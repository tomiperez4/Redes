from abc import ABC, abstractmethod
from lib.transport.segments.constants import *


class Segment(ABC):
    @abstractmethod
    def to_bytes(self):
        pass

    @staticmethod
    def from_bytes(data):
        from lib.transport.segments.ack_segment import AckSegment
        from lib.transport.segments.data_segment import DataSegment
        from lib.transport.segments.finished_segment import FinishedSegment
        from lib.transport.segments.handshake_request_segment import HandshakeRequestSegment
        from lib.transport.segments.handshake_response_segment import HandshakeResponseSegment
        from lib.transport.segments.handshake_ready_segment import HandshakeReadySegment
        from lib.transport.segments.handshake_error_segment import HandshakeErrorSegment

        if not data:
            raise ValueError("Empty data")

        dtype = data[0]

        if dtype == TYPE_ACK:
            return AckSegment.from_bytes(data)

        elif dtype == TYPE_DATA:
            return DataSegment.from_bytes(data)

        elif dtype == TYPE_FINISHED:
            return FinishedSegment.from_bytes(data)

        elif dtype == TYPE_HANDSHAKE_REQUEST:
            return HandshakeRequestSegment.from_bytes(data)

        elif dtype == TYPE_HANDSHAKE_RESPONSE:
            return HandshakeResponseSegment.from_bytes(data)

        elif dtype == TYPE_HANDSHAKE_READY:
            return HandshakeReadySegment.from_bytes(data)

        elif dtype == TYPE_HANDSHAKE_ERROR:
            return HandshakeErrorSegment.from_bytes(data)

        else:
            raise ValueError(f"Unknown segment type: {dtype}")

    # Helpers
    def is_data_segment(self):
        return False

    def is_ack_segment(self):
        return False

    def is_handshake_response_segment(self):
        return False

    def is_handshake_request_segment(self):
        return False

    def is_handshake_ready_segment(self):
        return False

    def is_handshake_error_segment(self):
        return False

    def is_finished(self):
        return False