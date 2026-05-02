import socket
import os
import math
import threading

from concurrent.futures import ThreadPoolExecutor
from lib.transport.rdt_listener import RdtListener
from lib.server.client_handler import ClientHandler


class Server:
    def __init__(self, host, port, workers, storage_path, log):
        self.address = (host, port)

        # Storage
        self.storage_path = storage_path
        self.current_storage_mb = get_directory_total_size(self.storage_path)
        self.update_storage_lock = threading.Lock()
        self.access_storage_lock = threading.Lock()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clients = {}
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self.log = log

    def start(self):
        try:
            self.socket.bind(self.address)
            self.log.debug(f"Server listening on {self.address}")
        except Exception as error:
            self.log.error(f"Failed to bind socket: {error}")
            return

        try:
            listener = RdtListener(self.socket, self.log.clone("RDT-LISTENER"))
            while True:
                protocol, address = listener.handle_incoming()
                if not protocol:
                    continue
                self.log.info(
                    f"New client: {address} (total: {len(self.clients)})")
                client_handler = ClientHandler(
                    address,
                    protocol,
                    self.storage_path,
                    self.log.clone("CLIENT-HANDLER"),
                    on_finish_callback = listener.remove_client,
                    on_update_storage=self.update_storage,
                    access_storage=self.access_storage
                )
                client_handler.start()

        except Exception as error:
            self.log.error(f"Failed to start Client Listener: {error}")

    def update_storage(self, size_to_add):
        with self.update_storage_lock:
            self.current_storage_mb += size_to_add
            self.log.info(f"Storage updated: {self.current_storage_mb} MB")

    def access_storage(self):
        with self.access_storage_lock:
            return self.current_storage_mb

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
    return size_in_mb
