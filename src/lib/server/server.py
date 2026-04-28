import socket
from concurrent.futures import ThreadPoolExecutor

from lib.logger import Logger
from lib.server.new_client_listener import NewClientListener


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
            self.log.info("Starting server")
            self.socket.bind(self.address)
            self.log.info(f"Server listening on {self.address}")
        except Exception as error:
            self.log.error(f"Failed to bind socket: {error}")
            return
        listener = NewClientListener(self.socket, self.log.clone("CLIENT-LISTENER"))
        self.log.debug("Starting NewClientListener thread")
        listener.start()