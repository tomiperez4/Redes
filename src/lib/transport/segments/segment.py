from abc import ABC, abstractmethod

# ELIMINADO: El import de HandshakeSegment de aquí arriba

TYPE_ACK = 0
TYPE_DATA = 1
TYPE_HANDSHAKE = 2


class Segment(ABC):
    @abstractmethod
    def to_bytes(self):
        pass

    @staticmethod
    def from_bytes(data):
        # Todos los imports específicos se hacen acá adentro (Local Imports)
        from src.lib.transport.segments.ack_segment import AckSegment
        from src.lib.transport.segments.data_segment import DataSegment
        from src.lib.transport.segments.handshake_segment import HandshakeSegment

        if not data:
            raise ValueError("Empty data")

        dtype = data[0]
        if dtype == TYPE_ACK:
            return AckSegment.from_bytes(data)
        elif dtype == TYPE_DATA:
            return DataSegment.from_bytes(data)
        elif dtype == TYPE_HANDSHAKE:
            return HandshakeSegment.from_bytes(data)
        else:
            raise ValueError(f"Unknown segment type: {dtype}")

    # Métodos de ayuda
    def is_data_segment(self):
        return False

    def is_ack_segment(self):
        return False

    def is_handshake_segment(self):
        return False