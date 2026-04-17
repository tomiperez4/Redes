from abc import ABC, abstractmethod
from src.lib.transport.datagrams.data_datagram import DataDatagram
from src.lib.transport.datagrams.ack_datagram import AckDatagram

TYPE_DATA = 0
TYPE_ACK = 1

class Datagram(ABC):
    @abstractmethod
    def to_bytes(self):
        pass

    @staticmethod
    def from_bytes(data):
        dtype = data[0]
        if dtype  == TYPE_DATA:
            return DataDatagram.from_bytes(data)
        elif dtype == TYPE_ACK:
            return AckDatagram.from_bytes(data)
        else:
            raise ValueError("Unknown datagram type")