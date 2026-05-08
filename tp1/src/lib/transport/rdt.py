from abc import abstractmethod, ABC
from lib.common import ALPHA, BETA, TIMEOUT


class ReliableProtocol(ABC):
    """
    Abstract base class for reliable transport protocols.
    """

    def __init__(self, socket, log):
        """
        Initializes the protocol for a specific socket.
        """
        self.socket = socket
        self.log = log

        self.estimated_rtt = -1
        self.dev_rtt = 0
        self.timeout_interval = TIMEOUT

    def _update_rto(self, sample):
        """
        Updates the retransmission timeout (RTO) using RTT samples.
        """
        if self.estimated_rtt < 0:
            self.estimated_rtt = sample
        else:
            self.estimated_rtt = (1 - ALPHA) * self.estimated_rtt + ALPHA * sample

        self.dev_rtt = (1 - BETA) * self.dev_rtt + BETA * abs(
            self.estimated_rtt - sample
        )
        self.timeout_interval = self.estimated_rtt + 4 * self.dev_rtt
        self.socket.settimeout(self.timeout_interval)

    @abstractmethod
    def close(self):
        """Closes the connection."""
        pass

    @abstractmethod
    def send(self, data):
        """Sends data reliably."""
        pass

    @abstractmethod
    def recv(self):
        """Receives data reliably."""
        pass
