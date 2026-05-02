import shutil
import struct

from lib.application.file_manager import FileManager
from lib.transport.rdt_socket import RdtSocket
from lib.constants.client_constants import CLIENT_TYPE_DOWNLOAD
from lib.client.client import Client


class DownloadClient(Client):
    def __init__(self, server_addr, server_port, verbose,
                 quiet, protocol_id, dst_path, filename):
        super().__init__(server_addr, server_port, verbose, quiet, protocol_id)
        self.dst_path = dst_path
        self.filename = filename

    def connect_to_server(self):
        size_in_bytes = 0
        rdt = RdtSocket(self.skt, self.protocol_id, self.log)
        self.protocol = rdt.connect(self.server_dir)

        payload = struct.pack(
            "!BQ",
            CLIENT_TYPE_DOWNLOAD,
            size_in_bytes,
        ) + self.filename.encode('utf-8')

        return self._negotiate_transaction(self.protocol, payload)

    def run_process(self):
        self.connect_to_server()
        file_manager = FileManager(self.protocol, self.log)
        file_manager.receive_file(self.dst_path)

def has_enough_space(file_size):
    total, used, free = shutil.disk_usage(".")
    return free >= file_size
