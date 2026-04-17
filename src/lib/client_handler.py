import queue
from TPs.Redes.src.lib.datagrams.datagram import Datagram

class ClientHandler:
    def __init__(self, socket):
        self.socket = socket
        self.queue = queue.Queue()

    def run(self):
        while True:
            self.queue.get()