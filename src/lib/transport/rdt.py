from abc import abstractmethod, ABC

class ReliableProtocol(ABC):
    def __init__(self, socket):
        self.socket = socket

    @abstractmethod
    def send(self, address, path):
        pass

    @abstractmethod
    def receive(self, address, path):
        pass