from abc import ABC, abstractmethod

TYPE_ACK = 0
TYPE_DATA = 1
TYPE_HANDSHAKE_REQUEST = 2
TYPE_HANDSHAKE_RESPONSE = 3


class Segment(ABC):
    @abstractmethod
    def to_bytes(self):
        pass

    @staticmethod
    def from_bytes(data):
        from src.lib.transport.segments.ack_segment import AckSegment
        from src.lib.transport.segments.data_segment import DataSegment
        from src.lib.transport.segments.handshake_request_segment import HandshakeRequestSegment
        from src.lib.transport.segments.handshake_response_segment import HandshakeResponseSegment

        if not data:
            raise ValueError("Empty data")

        dtype = data[0]

        if dtype == TYPE_ACK:
            return AckSegment.from_bytes(data)

        elif dtype == TYPE_DATA:
            return DataSegment.from_bytes(data)

        elif dtype == TYPE_HANDSHAKE_REQUEST:
            return HandshakeRequestSegment.from_bytes(data)

        elif dtype == TYPE_HANDSHAKE_RESPONSE:
            return HandshakeResponseSegment.from_bytes(data)

        else:
            raise ValueError(f"Unknown segment type: {dtype}")

    # Métodos de ayuda
    def is_data_segment(self):
        return False

    def is_ack_segment(self):
        return False

    def is_handshake_response_segment(self):
        return False

    def is_handshake_request_segment(self):
        return False