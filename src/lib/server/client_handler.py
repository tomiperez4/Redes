import threading
import socket
import os

from lib.segments.handshake_response_segment import HandshakeResponseSegment
from lib.segments.segment import Segment
from lib.transport.stop_and_wait import StopAndWait
from lib.transport.go_back_n import GoBackN
from lib.constants.client_constants import *
from lib.constants.protocol_constants import PROTOCOL_STOP_AND_WAIT, PROTOCOL_GO_BACK_N
from lib.constants.socket_constants import BUFFER_SIZE

class ClientHandler(threading.Thread):
    def __init__(self, client_host, client_port, client_type, filename, size,
                 protocol_id, on_finish, release_storage, log, file_size):
        super().__init__()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.bind(('', 0))
        self.client_host = client_host
        self.client_port = client_port
        self.client_type = client_type
        self.dest_file_path = "./storage/" + filename # cambiarlo
        self.size = size
        self.on_finish = on_finish
        self.release_storage = release_storage
        self.log = log
        self.file_size = file_size

        if protocol_id == PROTOCOL_STOP_AND_WAIT:
            self.protocol = StopAndWait(self.client_socket, self.log.clone("STOP-AND-WAIT"))
        elif protocol_id == PROTOCOL_GO_BACK_N:
            self.protocol = GoBackN(self.client_socket, self.log.clone("GO-BACK-N"))
        else:
            self.log.error(f"Unknown protocol id: {protocol_id}")
            raise ValueError("Unknown protocol")

    def run(self):
        """Initializes handler and runs the specified command"""
        address = (self.client_host, self.client_port)

        port = self.client_socket.getsockname()[1]
        response = HandshakeResponseSegment(port, self.file_size)

        self.client_socket.sendto(response.to_bytes(), address)

        try:
            if self.client_type == CLIENT_TYPE_UPLOAD:
                self.log.info("Uploading file...")
                self.handle_upload(address)
            elif self.client_type == CLIENT_TYPE_DOWNLOAD:
                self.log.info("Downloading file...")
                self.handle_download(address)
            else:
                self.log.error(f"Unknown client type: {self.client_type}")
                raise ValueError("Unknown client type")
        finally:
            self.on_finish((self.client_host, self.client_port))
            self.client_socket.close()

    def handle_upload(self, address):
        """Handles the UPLOAD operation"""
        self.protocol.receive(address, self.dest_file_path)
        if not os.path.exists(self.dest_file_path) or os.path.getsize(self.dest_file_path) != self.size:
            self.release_storage()

    def handle_download(self, address):
        """Handles the DOWNLOAD operation"""
        while True:
            raw, _ = self.client_socket.recvfrom(BUFFER_SIZE)
            segment = Segment.from_bytes(raw)

            if segment.is_handshake_error_segment():
                self.log.info("Client rejected download (no space)")
                return

            if segment.is_handshake_ready_segment():
                break


        self.protocol.send(address, self.dest_file_path)
