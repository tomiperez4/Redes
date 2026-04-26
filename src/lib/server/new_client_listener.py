import threading

from lib.logger import Logger
from lib.server.client_handler import ClientHandler
from lib.transport.segments.handshake_response_segment import HandshakeResponseSegment
from lib.transport.segments.segment import Segment

BUF_SIZE = 1024
MAX_CLIENTS = 10

class NewClientListener(threading.Thread):
    def __init__(self, socket, verbose, quiet):
        super().__init__()
        self.socket = socket
        self.clients = {}
        self.lock = threading.Lock()
        self.verbose = verbose
        self.quiet = quiet
        self.log = Logger("CLIENT-LISTENER", verbose, quiet)

    def run(self):
        self.log.info("Listening for new clients")
        while True:
            try:
                raw, address = self.socket.recvfrom(BUF_SIZE)
                self.log.debug(f"Packet received from {address}")
                segment = Segment.from_bytes(raw)

                if address in self.clients and segment.is_handshake_request_segment():
                    h_response = HandshakeResponseSegment(self.clients[address])
                    self.socket.sendto(h_response.to_bytes(), address)
                    continue

                if len(self.clients) >= MAX_CLIENTS:
                    self.log.error("Client limit reached")
                    continue

                if not segment.is_handshake_request_segment():
                    self.log.error("Expected handshake request segment")
                    continue

                self.log.info(f"New client: {address} (total: {len(self.clients)})")

                handler = ClientHandler(
                    address[0],
                    address[1],
                    segment.operation,
                    segment.filename,
                    segment.protocol,
                    self.client_finished,
                    self.verbose,
                    self.quiet
                )

                self.clients[address] = handler.client_socket.getsockname()[1]
                handler.start()

            except Exception as error:
                self.log.error(f"Listener error: {error}")

    def client_finished(self, address):
        with self.lock:
            del self.clients[address]
            self.log.info(f"Client finished (remaining: {len(self.clients)})")