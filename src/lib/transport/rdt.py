from abc import abstractmethod, ABC

class ReliableProtocol(ABC):
    def __init__(self, socket, log):
        self.socket = socket
        self.log = log

    @abstractmethod
    def send(self, address, path):
        pass

    @abstractmethod
    def receive(self, address, path):
        pass