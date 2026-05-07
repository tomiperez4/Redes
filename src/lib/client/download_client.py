import shutil
import struct
import time

from lib.transport.file_manager import FileManager
from lib.transport.rdt_socket import RdtSocket
from lib.client.constants import CLIENT_TYPE_DOWNLOAD
from lib.client.client import Client


class DownloadClient(Client):
    """
    Client that downloads a file from the server.
    """
    def __init__(self, server_addr, server_port, verbose,
                 quiet, protocol_id, dst_path, filename):
        """
        Initializes the download client with the parameters obtained from the command line.
        """
        super().__init__(server_addr, server_port, verbose, quiet, protocol_id)
        self.dst_path = dst_path
        self.filename = filename

    def connect_to_server(self):
        """
        Establishes connection with the server and requests the file.
        Because this is a download and not an upload operation, the 'size_in_bytes' field is omitted
        by setting it to zero.
        """
        size_in_bytes = 0
        rdt = RdtSocket(self.skt, self.protocol_id, self.log)
        self.protocol = rdt.connect(self.server_addr)

        payload = struct.pack(
            "!BQ",
            CLIENT_TYPE_DOWNLOAD,
            size_in_bytes,
        ) + self.filename.encode('utf-8')

        return self._negotiate_transaction(self.protocol, payload)

    def run_process(self):
        """"
        Executes the download process.
        If the server accepts the request, it receives the file and saves it to the destination path.
        """
        start_time = 0
        file_size = self.connect_to_server()
        if file_size is not None:
            file_manager = FileManager(self.protocol, self.log)
            start_time = time.time()
            file_manager.receive_file(self.dst_path, file_size)
        end_time = time.time()
        duration = end_time - start_time
        self.log.info(f"Download completed in {duration:.2f} seconds")

def has_enough_space(file_size):
    """
    Checks if there is enough disk space to store the file.
    """
    total, used, free = shutil.disk_usage(".")
    return free >= file_size
