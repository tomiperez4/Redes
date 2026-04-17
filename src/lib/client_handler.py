import queue
from src.lib.transport.datagrams.datagram import Datagram

class ClientHandler:
    def __init__(self, socket):
        self.socket = socket
        self.queue = queue.Queue()

    def run(self):
        while True:
            data = self.queue.get()
            datagram = Datagram.from_bytes(data)