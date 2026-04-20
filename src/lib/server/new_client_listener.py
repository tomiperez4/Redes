import threading

from src.lib.server.client_handler import ClientHandler
from src.lib.transport.segments.segment import Segment
from src.lib.transport.segments.handshake_segment import HandshakeSegment

BUF_SIZE = 1024

class NewClientListener(threading.Thread):
    def __init__(self, socket):
        super().__init__()
        self.socket = socket
        self.clients = {}

    def run(self):
        while True:
            raw, address = self.socket.recvfrom(BUF_SIZE)
            segment = Segment.from_bytes(raw)
            if address not in self.clients:
                if not isinstance(segment, HandshakeSegment):
                    continue
                handshake_segment = HandshakeSegment.from_bytes(segment)
                handler = ClientHandler(self.socket)
                self.clients[address] = handler
                handler.run()

