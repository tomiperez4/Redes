import queue
import threading

from src.lib.transport.stop_and_wait import StopAndWait

CLIENT_TYPE_UPLOAD = 0
CLIENT_TYPE_DOWNLOAD = 1

PROTOCOL_STOP_AND_WAIT = 0
PROTOCOL_GO_BACK_N = 1

class ClientHandler(threading.Thread):
    def __init__(self, socket, client_host, client_port, client_type, filename, protocol_id):
        super().__init__()
        self.socket = socket
        self.client_host = client_host
        self.client_port = client_port
        self.client_type = client_type
        self.filename = filename
        self.protocol = protocol
        self.queue = queue.Queue()

        if protocol_id == PROTOCOL_STOP_AND_WAIT:
            self.protocol = StopAndWait(self.socket)
        else:
            self.protocol = GoBackN(self.socket)

    def run(self):
        """Initializes handler and runs the specified command"""
        address = (self.client_host, self.client_port)
        if self.client_type == CLIENT_TYPE_UPLOAD:
            self.handle_upload(address)
        else:
            self.handle_download(address)

    def handle_upload(self, address):
        """Handles the UPLOAD operation"""
        self.protocol.receive(address, self.filename, self.queue)

    def handle_download(self, address):
        """Handles the DOWNLOAD operation"""
        self.protocol.send(address, self.filename, self.queue)