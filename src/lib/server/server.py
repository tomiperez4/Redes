import socket
from concurrent.futures import ThreadPoolExecutor
from lib.server.client_listener import ClientListener


class Server:
    def __init__(self, host, port, workers, storage, log):
        self.address = (host, port)
        self.storage = storage
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clients = {}
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self.log = log

    def start(self):
        try:
            self.socket.bind(self.address)
            self.log.debug(f"Server listening on {self.address}")
        except Exception as error:
            self.log.error(f"Failed to bind socket: {error}")
            return

        try:
            listener = ClientListener(self.socket, self.storage, self.log.clone("CLIENT-LISTENER"))
            listener.start()
        except Exception as error:
            self.log.error(f"Failed to start Client Listener: {error}")
        except KeyboardInterrupt:
            self.log.info("Shutting down server")