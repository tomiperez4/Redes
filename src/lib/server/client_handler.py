import threading
import os
import struct

from lib.application.file_manager import FileManager
from lib.constants.client_constants import CLIENT_TYPE_UPLOAD, CLIENT_TYPE_DOWNLOAD
from lib.constants.server_constants import MAX_STORAGE_SIZE, MAX_FILE_SIZE

# Status code
APP_CODE_READY = 100
APP_ERR_NO_SPACE = 201
APP_ERR_FILE_NOT_FOUND = 202
APP_ERR_GENERIC = 200

APP_RES_FORMAT = "!BQ"  # 1 byte unsigned

class ClientHandler(threading.Thread):
    def __init__(self, address, protocol, storage_path, shutdown_event, log, on_finish_callback=None, on_update_storage=None, access_storage=None):
        super().__init__()
        self.address = address
        self.protocol = protocol
        self.storage_path = storage_path
        self.shutdown_event = shutdown_event
        self.log = log
        self.on_finish_callback = on_finish_callback
        self.on_update_storage=on_update_storage
        self.access_storage = access_storage

    def run(self):
        payload = self.protocol.recv()

        op_type, file_size, filename = self._get_data(payload)
        file_manager = FileManager(self.protocol, self.log.clone("CLIENT (FILE MANAGER)"), shutdown_event=self.shutdown_event)
        path = self.storage_path + "/" + filename

        if op_type == CLIENT_TYPE_DOWNLOAD:
            if not self._validate_download(filename):
                return
            self.on_update_storage(file_size)
            size = _get_file_size(path)
            response_seg = struct.pack(
                APP_RES_FORMAT,
                APP_CODE_READY,
                    size
            )
            self.protocol.send(response_seg)
            file_manager.send_file(path)
        if op_type == CLIENT_TYPE_UPLOAD:
            if not self._validate_upload(file_size, filename):
                return
            self.on_update_storage(file_size)
            response_seg = struct.pack(
                APP_RES_FORMAT,
                APP_CODE_READY,
                0
            )
            self.protocol.send(response_seg)
            file_manager.receive_file(path, file_size)

        self.on_finish_callback(self.address)

    def _get_data(self, payload):
        header_format = "!BQ"
        header_size = struct.calcsize(header_format)
    
        try:
            header_data = payload[:header_size]
            oper_type, file_size = struct.unpack(header_format, header_data)
            filename = payload[header_size:].decode('utf-8')
    
            return oper_type, file_size, filename
    
        except Exception as error:
            self.log.error(f"Failed to parse payload: {error}")
            return None

    def _validate_download(self, filename):
        if not self._file_exists(filename):
            self.log.error(f"File not found: {filename}")
            self._end_conn(APP_ERR_FILE_NOT_FOUND)
            return False

        return True

    def _validate_upload(self, file_size, filename):
        if self._is_storage_full(file_size):
            self.log.error(f"Not enough storage to up: {filename}")
            self._end_conn(APP_ERR_NO_SPACE)
            return False
        return True
    
    def _file_exists(self, filename):
        file_path = self.storage_path + "/" + filename
        if not os.path.exists(file_path):
            return False
        return True

    def _is_storage_full(self, file_size):
        current_storage = self.access_storage()
        if current_storage + file_size > MAX_STORAGE_SIZE:
            return True
        return False

    def _end_conn(self, status_code):
        response_seg = struct.pack(
            APP_RES_FORMAT,
            status_code,
            0
        )
        self.protocol.send(response_seg)
        self.on_finish_callback(self.address)

def _get_file_size(file_path):
    return os.path.getsize(file_path)