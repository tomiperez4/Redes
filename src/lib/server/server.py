import socket
from concurrent.futures import ThreadPoolExecutor

from lib.logger import Logger
from lib.server.new_client_listener import NewClientListener


class Server:
    def __init__(self, host, port, workers, storage, verbose, quiet):
        self.address = (host, port)
        self.storage = storage
        self.verbose = verbose
        self.quiet = quiet
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clients = {}
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self.log = Logger("SERVER", verbose, quiet)

    def start(self):
        try:
            self.log.info("Starting server")
            self.socket.bind(self.address)
            self.log.info(f"Server listening on {self.address}")
        except Exception as error:
            self.log.error(f"Failed to bind socket: {error}")
            return
        listener = NewClientListener(self.socket, self.verbose, self.client)
        self.log.debug("Starting NewClientListener thread")
        listener.start()