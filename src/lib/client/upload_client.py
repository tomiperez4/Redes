import socket
import time

from lib.transport.segments.handshake_request_segment import HandshakeRequestSegment
from lib.transport.segments.finished_segment import FinishedSegment
from lib.constants.client_constants import CLIENT_TYPE_UPLOAD
from lib.client.client import Client
import os
import math

class UploadClient(Client):
    def __init__(self, server_addr, server_port, verbose, quiet, protocol_id, src_path, filename):
        super().__init__(server_addr, server_port, verbose, quiet, protocol_id)
        self.src_path = src_path
        self.filename = filename

        if not os.path.exists(self.src_path):
            self.log.error(f"File {self.src_path} does not exist")
            return

    def run_process(self):
        try:
            size_in_bytes = os.path.getsize(self.src_path)
            filesize_mb = math.ceil(size_in_bytes / (1024 * 1024))
            self.log.debug(f"File size: {filesize_mb} MB")
        except OSError as e:
            self.log.error(f"Could not get file size: {e}")
            return

        h_packet = HandshakeRequestSegment(
            operation = CLIENT_TYPE_UPLOAD,
            protocol = self.protocol_id,
            port = int(self.server_dir[1]),
            host = socket.inet_aton(self.server_dir[0]),
            filename = self.filename,
            size = filesize_mb,
        )

        result = self.handshake(h_packet)
        if result is None:
            return
        host, port, file_size = result
        handler_address = (host, port)

        try:
            start_time = time.time()
            self.rdt.send(handler_address, self.src_path)
            end_time = time.time()
            elapsed = end_time - start_time
            self.log.debug("Packet sent successfully")
            self.log.info(f"Upload completed in {elapsed:.4f} seconds")
            print(f"Upload completed in {elapsed:.4f} seconds")
        except Exception as error:
            self.log.error(f"Connection lost: {error}. Sending FINISHED packet to server...")
            fin = FinishedSegment()
            self.skt.sendto(fin.to_bytes(), handler_address)
        finally:
            self.skt.close()