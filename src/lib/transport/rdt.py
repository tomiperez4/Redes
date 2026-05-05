from abc import abstractmethod, ABC
from lib.constants.protocol_constants import ALPHA, BETA
from lib.constants.socket_constants import TIMEOUT


class ReliableProtocol(ABC):
    def __init__(self, socket, log):
        self.socket = socket
        self.log = log

        # RTO
        self.estimated_rtt = -1
        self.dev_rtt = 0
        self.timeout_interval = TIMEOUT

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def send(self, data):
        pass

    @abstractmethod
    def recv(self):
        pass
