from abc import ABC, abstractmethod

TYPE_DATA = 0
TYPE_ACK = 1


class Datagram(ABC):
    @abstractmethod
    def to_bytes(self):
        pass

    @staticmethod
    def from_bytes(bytes):
        dtype = bytes[0]
        if dtype  == TYPE_DATA:
            return DataDatagram.from_bytes(bytes)
        elif dtype == TYPE_ACK:
            return AckDatagram.from_bytes(bytes)
        else:
            raise ValueError("Unknown datagram type")
