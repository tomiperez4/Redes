import threading

from lib.server.client_handler import ClientHandler
from lib.transport.segments.handshake_error_segment import HandshakeErrorSegment
from lib.transport.segments.handshake_response_segment import HandshakeResponseSegment
from lib.transport.segments.segment import Segment
from lib.server.constants import BUF_SIZE, MAX_CLIENTS, CLIENT_TYPE_UPLOAD, MAX_STORAGE_SIZE, MAX_FILE_SIZE, \
    CLIENT_TYPE_DOWNLOAD
import math
import os

class NewClientListener(threading.Thread):
    def __init__(self, socket, storage_path, log):
        super().__init__()
        self.socket = socket
        self.clients = {}
        self.lock = threading.Lock()
        self.storage_lock = threading.Lock()
        self.current_storage_mb = get_directory_total_size(storage_path)
        self.log = log

    def run(self):
        self.log.info("Listening for new clients")
        while True:
            try:
                raw, address = self.socket.recvfrom(BUF_SIZE)
                self.log.debug(f"Packet received from {address}")
                segment = Segment.from_bytes(raw)
                file_size = 0

                if address in self.clients and segment.is_handshake_request_segment():
                    port, size = self.clients[address]
                    h_response = HandshakeResponseSegment(port, size)
                    self.socket.sendto(h_response.to_bytes(), address)
                    continue

                if len(self.clients) >= MAX_CLIENTS:
                    self._ack_error("Client limit reached", address)
                    continue

                if not segment.is_handshake_request_segment():
                    self.log.warning("Expected handshake request segment")
                    continue

                if segment.operation == CLIENT_TYPE_UPLOAD:
                    if segment.size > MAX_FILE_SIZE:
                        self._ack_error("File size not supported by server", address)
                        continue
                    with self.storage_lock:
                        if self.current_storage_mb + segment.size > MAX_STORAGE_SIZE:
                            self._ack_error("Storage limit reached. Could not upload file", address)
                            continue

                if segment.operation == CLIENT_TYPE_DOWNLOAD:
                    file_path = "./storage/" + segment.filename
                    if not os.path.exists(file_path):
                        self._ack_error(f"File {segment.filename} does not exist", address)
                        continue
                    file_size = os.path.getsize(file_path)

                self.log.info(f"New client: {address} (total: {len(self.clients)})")

                handler = ClientHandler(
                    address[0],
                    address[1],
                    segment.operation,
                    segment.filename,
                    segment.size,
                    segment.protocol,
                    self.client_finished,
                    self.release_storage,
                    self.log.clone(f"CLIENT-HANDLER ({address})"),
                    file_size
                )

                self.clients[address] = (handler.client_socket.getsockname()[1], file_size)
                handler.start()

            except Exception as error:
                self.log.error(f"Listener error: {error}")

    def client_finished(self, address):
        with self.lock:
            del self.clients[address]
            self.log.info(f"Client finished (remaining: {len(self.clients)})")

    def release_storage(self, file_size):
        with self.storage_lock:
            self.current_storage_mb -= file_size
            self.log.info(f"Storage released. Total: {self.current_storage_mb}MB")

    def _ack_error(self, error_msg, address):
        self.log.warning(error_msg)
        h_error = HandshakeErrorSegment()
        self.socket.sendto(h_error.to_bytes(), address)

def get_directory_total_size(directory_path):
    total_bytes = 0

    if not os.path.exists(directory_path):
        return 0

    try:
        with os.scandir(directory_path) as entries:
            for entry in entries:
                if entry.is_file():
                    total_bytes += entry.stat().st_size
    except Exception as e:
        print(f"Failed to get initial storage: {e}")
        return 0

    size_in_mb = math.ceil(total_bytes / (1024 * 1024))
    print(f"Initial storage size: {size_in_mb} MB")
    return size_in_mb