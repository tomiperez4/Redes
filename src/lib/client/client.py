import socket
import struct

from lib.constants.socket_constants import TIMEOUT
from lib.constants.protocol_constants import PROTOCOL_STOP_AND_WAIT
from lib.constants.log_file_constants import CLIENTS_LOG_FILE
from lib.transport.stop_and_wait import StopAndWait
from lib.transport.go_back_n import GoBackN
from lib.logger import Logger

APP_CODE_READY = 100
APP_ERR_NO_SPACE = 201
APP_ERR_FILE_NOT_FOUND = 202
APP_ERR_GENERIC = 200


class Client:
    def __init__(self, server_addr, server_port, verbose, quiet, protocol_id):
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.skt.settimeout(TIMEOUT)
        self.server_dir = (server_addr, server_port)
        self.protocol_id = protocol_id
        self.protocol = None
        self.log = Logger(
            "CLIENT",
            CLIENTS_LOG_FILE,
            verbose=verbose,
            quiet=quiet)
        self.rdt = self._create_rdt()

    def _create_rdt(self):
        if self.protocol_id == PROTOCOL_STOP_AND_WAIT:
            return StopAndWait(self.skt, self.log)
        return GoBackN(self.skt, self.log)

    def connect_to_server(self):
        raise NotImplementedError

    def run_process(self):
        raise NotImplementedError

    def _negotiate_transaction(self, protocol, payload):
        try:
            protocol.send(payload)
            print("hola")
            response = protocol.recv()
            status_code = struct.unpack("!B", response)[0]

            if status_code == APP_ERR_NO_SPACE:
                self.log.error(
                    f"Server's capacity is full. Could not upload your file ({status_code})")
                return None
            elif status_code == APP_ERR_FILE_NOT_FOUND:
                self.log.error(
                    f"File not found. Could not download ({status_code})")
                return None
            elif status_code == APP_ERR_GENERIC:
                self.log.error(
                    f"Unexpected error. Could not download ({status_code})")
                return None
            elif status_code == APP_CODE_READY:
                self.log.info(f"Server is ready. Connection established")
                return protocol

        except Exception as error:
            self.log.error(f"Could not start connection with server: {error}")
            return None
