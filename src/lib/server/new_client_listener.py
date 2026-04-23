import threading

from lib.logger import Logger
from lib.server.client_handler import ClientHandler
from lib.transport.segments.segment import Segment

BUF_SIZE = 1024
MAX_CLIENTS = 10

class NewClientListener(threading.Thread):
    def __init__(self, socket, verbose, quiet):
        super().__init__()
        self.socket = socket
        self.clients_count = 0
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

                if self.clients_count >= MAX_CLIENTS:
                    self.log.error("Client limit reached")
                    continue
                if not segment.is_handshake_request_segment():
                    self.log.error("Invalid segment (not handshake)")
                    continue

                self.clients_count += 1
                self.log.info(f"New client: {address} (total: {self.clients_count})")

                handler = ClientHandler(
                    address[0],
                    address[1],
                    segment.operation,
                    segment.filename,
                    segment.protocol,
                    self.client_finished
                )
                handler.start()

            except Exception as error:
                self.log.error(f"Listener error: {error}")

    def client_finished(self):
        with self.lock:
            self.clients_count -= 1
            self.log.info(f"Client finished (remaining: {self.clients_count})")