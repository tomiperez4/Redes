import queue
import threading

from src.lib.transport.stop_and_wait import StopAndWait

CLIENT_TYPE_UPLOAD = 0
CLIENT_TYPE_DOWNLOAD = 1

PROTOCOL_STOP_AND_WAIT = 0
PROTOCOL_GO_BACK_N = 1

class ClientHandler(threading.Thread):
    def __init__(self, socket, client_host, client_port, client_type, filename, protocol):
        super().__init__()
        self.socket = socket
        self.queue = queue.Queue()
        self.client_host = client_host
        self.client_port = client_port
        self.client_type = client_type
        self.filename = filename
        self.protocol = protocol

    def run(self):
        if self.protocol == PROTOCOL_STOP_AND_WAIT:
            rdt = StopAndWait(self.socket)
        else:
            rdt = GoBackN(self.socket)

        if type == CLIENT_TYPE_UPLOAD:
            self.handle_upload(rdt, self.filename)
        else:
            self.handle_download(rdt, self.filename)