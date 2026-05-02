import struct

from lib.application.file_manager import FileManager
from lib.constants.client_constants import CLIENT_TYPE_UPLOAD
from lib.client.client import Client
import os
import math

from lib.transport.rdt_socket import RdtSocket


class UploadClient(Client):
    def __init__(self, server_addr, server_port, verbose,
                 quiet, protocol_id, src_path, filename):
        super().__init__(server_addr, server_port, verbose, quiet, protocol_id)
        self.src_path = src_path
        self.filename = filename

        if not os.path.exists(self.src_path):
            self.log.error(f"File {self.src_path} does not exist")
            return

    def connect_to_server(self):
        filesize_mb = 0
        rdt = RdtSocket(self.skt, self.protocol_id, self.log)
        self.protocol = rdt.connect(self.server_dir)

        try:
            size_in_bytes = os.path.getsize(self.src_path)
            filesize_mb = math.ceil(size_in_bytes / (1024 * 1024))
            self.log.debug(f"File size: {filesize_mb} MB")
        except OSError as error:
            self.log.error(f"Could not get file size: {error}")

        payload = struct.pack(
            "!BQ",
            CLIENT_TYPE_UPLOAD,
            filesize_mb,
        ) + self.filename.encode('utf-8')

        return self._negotiate_transaction(self.protocol, payload)

    def run_process(self):
        if self.connect_to_server() is not None:
            file_manager = FileManager(self.protocol, self.log)
            file_manager.send_file(self.src_path, )