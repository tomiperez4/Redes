import socket
from concurrent.futures import ThreadPoolExecutor
from src.lib.server.new_client_listener import NewClientListener


class Server:
    def __init__(self, host, port, workers):
        self.address = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clients = {}
        self.executor = ThreadPoolExecutor(max_workers=workers)

    def start(self):
        self.socket.bind(self.address)
        NewClientHandler = NewClientListener(self.clients)