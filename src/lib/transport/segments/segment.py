from abc import ABC, abstractmethod

from src.lib.transport.segments.ack_segment import AckSegment
from src.lib.transport.segments.data_segment import DataSegment
from src.lib.transport.segments.handshake_segment import HandshakeSegment

TYPE_ACK = 0
TYPE_DATA = 1
TYPE_HANDSHAKE = 2


class Segment(ABC):
    @abstractmethod
    def to_bytes(self):
        pass

    @staticmethod
    def from_bytes(data):
        dtype = data[0]
        if dtype == TYPE_ACK:
            return AckSegment.from_bytes(data)
        elif dtype == TYPE_DATA:
            return DataSegment.from_bytes(data)
        elif dtype == TYPE_HANDSHAKE:
            return HandshakeSegment.from_bytes(data)
        else:
            raise ValueError("Unknown segment")

    @staticmethod
    def is_data_segment():
        return False

    @staticmethod
    def is_ack_segment():
        return False

    @staticmethod
    def is_handshake_segment():
        return False