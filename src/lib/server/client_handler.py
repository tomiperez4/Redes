import threading
import os
import struct

from lib.transport.file_manager import FileManager
from lib.client.constants import CLIENT_TYPE_UPLOAD, CLIENT_TYPE_DOWNLOAD
from lib.server.constants import MAX_STORAGE_SIZE, MAX_FILE_SIZE, RES_FORMAT, CODE_READY, ERR_NO_SPACE, \
ERR_GENERIC, ERR_FILE_NOT_FOUND, ERR_SIZE_LIMIT_EXCEEDED


class ClientHandler(threading.Thread):
    """
    Handles a single client connection.
    """
    def __init__(self, address, protocol, storage_path, shutdown_event, log, on_finish_callback=None, on_update_storage=None, access_storage=None):
        """
        Initializes the client handler.
        """
        super().__init__()
        self.address = address
        self.protocol = protocol
        self.storage_path = storage_path
        self.shutdown_event = shutdown_event
        self.log = log
        self.on_finish_callback = on_finish_callback
        self.on_update_storage = on_update_storage
        self.access_storage = access_storage

    def run(self):
        """
        Validates and executes the client's chosen operation.
        """
        payload = self.protocol.recv()
        op_type, file_size, filename = self._get_data(payload)
        self.log.info(f"Client {self.address} requested operation {op_type} on {filename} ({file_size} bytes)")
        file_manager = FileManager(self.protocol, self.log.clone("CLIENT (FILE MANAGER)"), shutdown_event=self.shutdown_event)
        path = self.storage_path + "/" + filename

        if op_type == CLIENT_TYPE_DOWNLOAD:
            if not self._validate_download(filename):
                return
            size = _get_file_size(path)
            response_seg = struct.pack(
                RES_FORMAT,
                CODE_READY,
                    size
            )
            self.protocol.send(response_seg)
            file_manager.send_file(path)
        elif op_type == CLIENT_TYPE_UPLOAD:
            valid, net_size = self._validate_upload(file_size, filename)
            if not valid:
                return
            response_seg = struct.pack(
                RES_FORMAT,
                CODE_READY,
                0
            )
            self.protocol.send(response_seg)
            file_manager.receive_file(path, file_size)
            self.on_update_storage(net_size)
        else:
            self.log.error(f"Unknown operation type: {op_type}")
            self._end_conn(ERR_GENERIC)

        self.on_finish_callback(self.address)

    def _get_data(self, payload):
        """
        Parses client request payload.
        """
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
        """
        Validates that the file is in storage.
        """
        if not self._file_exists(filename):
            self.log.error(f"File not found: {filename}")
            self._end_conn(ERR_FILE_NOT_FOUND)
            return False
        return True

    def _validate_upload(self, file_size, filename):
        """
        Validates that the upload file size is less than or equal to MAX_FILE_SIZE and
        that there is enough storage to save the file.
        """
        if file_size > MAX_FILE_SIZE:
            self.log.error(f"File too large. Maximum file size is {MAX_FILE_SIZE / (1024 * 1024)} MB")
            self._end_conn(ERR_SIZE_LIMIT_EXCEEDED)
            return False, 0

        path = self.storage_path + "/" + filename
        existing_size = os.path.getsize(path) if os.path.exists(path) else 0
        net_size = file_size - existing_size

        if self._is_storage_full(net_size):
            self.log.error(f"Not enough storage to upload.")
            self._end_conn(ERR_NO_SPACE)
            return False, 0

        return True, net_size

    def _file_exists(self, filename):
        """
        Validates that the file exists.
        """
        file_path = self.storage_path + "/" + filename
        if not os.path.exists(file_path):
            return False
        return True

    def _is_storage_full(self, net_size):
        """
        Evaluates if the storage is currently full.
        """
        if net_size <= 0:
            return False
        current_storage = self.access_storage()
        return current_storage + net_size > MAX_STORAGE_SIZE

    def _end_conn(self, status_code):
        """
        Ends the connection by sending a response segment to the client.
        """
        response_seg = struct.pack(
            RES_FORMAT,
            status_code,
            0
        )
        self.protocol.send(response_seg)
        self.on_finish_callback(self.address)

def _get_file_size(file_path):
    """
    Returns the file size in bytes.
    """
    return os.path.getsize(file_path)