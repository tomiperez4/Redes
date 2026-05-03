import struct

from lib.application.file_manager import FileManager
from lib.constants.client_constants import CLIENT_TYPE_UPLOAD
from lib.client.client import Client
import os

from lib.transport.rdt_socket import RdtSocket


class UploadClient(Client):
    def __init__(self, server_ip, server_port, verbose,
                 quiet, protocol_id, src_path, filename):
        super().__init__(server_ip, server_port, verbose, quiet, protocol_id)
        self.src_path = src_path
        self.filename = filename

        if not os.path.exists(self.src_path):
            self.log.error(f"File {self.src_path} does not exist")
            return

    def connect_to_server(self):
        size_in_bytes = 0
        rdt = RdtSocket(self.skt, self.protocol_id, self.log)
        self.protocol = rdt.connect(self.server_addr)

        try:
            size_in_bytes = os.path.getsize(self.src_path)
            self.log.debug(f"File size: {size_in_bytes}B")
        except OSError as error:
            self.log.error(f"Could not get file size: {error}")

        payload = struct.pack(
            "!BQ",
            CLIENT_TYPE_UPLOAD,
            size_in_bytes,
        ) + self.filename.encode('utf-8')

        return self._negotiate_transaction(self.protocol, payload)

    def run_process(self):
        if self.connect_to_server() is not None:
            file_manager = FileManager(self.protocol, self.log)
            file_manager.send_file(self.src_path)