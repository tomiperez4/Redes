import socket
from concurrent.futures import ThreadPoolExecutor
from TPs.Redes.src.lib.client_handler import ClientHandler

class Server:
    def __init__(self, host, port, workers):
        self.address = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clients = {}
        self.executor = ThreadPoolExecutor(max_workers=workers)

    def start(self):
        self.socket.bind(self.address)
        while True:
            data, address = self.socket.recvfrom(1024)
            if address not in self.clients:
                handler = ClientHandler(self.socket)
                self.clients[address] = handler
                self.executor.submit(handler.run)
            self.clients[address].queue(data)