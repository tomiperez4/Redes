import threading

from src.lib.server.client_handler import ClientHandler
from src.lib.transport.segments.segment import Segment
from src.lib.transport.segments.handshake_segment import HandshakeSegment

BUF_SIZE = 1024
MAX_CLIENTS = 10

class NewClientListener(threading.Thread):
    def __init__(self, socket):
        super().__init__()
        self.socket = socket
        self.clients_count = 0
        self.lock = threading.Lock()

    def run(self):
        while True:
            try:
                raw, address = self.socket.recvfrom(BUF_SIZE)
                segment = Segment.from_bytes(raw)

                if self.clients_count >= MAX_CLIENTS or not isinstance(segment, HandshakeSegment):
                    print("Error")
                    continue

                self.clients_count += 1
                handler = ClientHandler(
                    address[0],
                    address[1],
                    segment.type,
                    segment.filename.decode('utf-8'),
                    segment.protocol,
                    self.client_finished
                )
                handler.start()

            except Exception as e:
                print(e)

    def client_finished(self):
        with self.lock:
            self.clients_count -= 1
            print("Client finished")