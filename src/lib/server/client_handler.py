import threading
import socket

from lib.transport.segments.handshake_response_segment import HandshakeResponseSegment
from lib.transport.stop_and_wait import StopAndWait

# Constantes generales
CLIENT_TYPE_UPLOAD = 0
CLIENT_TYPE_DOWNLOAD = 1

PROTOCOL_STOP_AND_WAIT = 0
PROTOCOL_GO_BACK_N = 1

class ClientHandler(threading.Thread):
    def __init__(self, client_host, client_port, client_type, filename, protocol_id, on_finish):
        super().__init__()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.bind(('', 0))
        self.client_host = client_host
        self.client_port = client_port
        self.client_type = client_type
        self.filename = "./storage/" + filename # cambiarlo
        self.protocol = StopAndWait(self.client_socket) # Dsps lo cambiamos cuando este GoBackN
        self.on_finish = on_finish
        #self.queue = queue.Queue()

        if protocol_id == PROTOCOL_STOP_AND_WAIT:
            self.protocol = StopAndWait(self.client_socket)
        #else:
            #self.protocol = GoBackN(self.client_socket)

    def run(self):
        """Initializes handler and runs the specified command"""
        address = (self.client_host, self.client_port)

        port = self.client_socket.getsockname()[1]
        response = HandshakeResponseSegment(port)

        self.client_socket.sendto(response.to_bytes(), address)

        try:
            if self.client_type == CLIENT_TYPE_UPLOAD:
                self.handle_upload(address)
            else:
                self.handle_download(address)
        finally:
            self.on_finish()
            self.client_socket.close()

    def handle_upload(self, address):
        """Handles the UPLOAD operation"""
        self.protocol.receive(address, self.filename)

    def handle_download(self, address):
        """Handles the DOWNLOAD operation"""
        self.protocol.send(address, self.filename)
