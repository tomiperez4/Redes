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
            try:
                raw, address = self.socket.recvfrom(BUF_SIZE)
                segment = Segment.from_bytes(raw)
                if address in self.clients:
                    self.clients[address].queue.put(segment)
                    continue
                if isinstance(segment, HandshakeSegment):
                    handler = ClientHandler(
                        self.socket, address[0], address[1], segment.type, segment.filename, segment.protocol
                    )
                    self.clients[address] = handler
                    self.clients[address].queue.put(segment)
                    handler.start()
            except Exception as e:
                print(e)
