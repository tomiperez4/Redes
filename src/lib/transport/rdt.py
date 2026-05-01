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

    def _update_rto(self, sample):
        if self.estimated_rtt < 0:
            self.estimated_rtt = sample
        else:
            self.estimated_rtt = (1 - ALPHA) * self.estimated_rtt + ALPHA * sample

        self.dev_rtt = (1 - BETA) * self.dev_rtt + BETA * abs(self.estimated_rtt - sample)
        self.timeout_interval = self.estimated_rtt + 4 * self.dev_rtt
        self.socket.settimeout(self.timeout_interval)

    @abstractmethod
    def start(self, address):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def send(self, data):
        pass

    @abstractmethod
    def recv(self):
        pass

    #@abstractmethod
    #def send(self, address, path):
    #    pass

    #@abstractmethod
    #def receive(self, address, path):
    #    pass