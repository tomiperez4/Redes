import socket
import struct

from lib.common import TIMEOUT, CLIENTS_LOG_FILE
from lib.server.constants import ERR_NO_SPACE, ERR_FILE_NOT_FOUND, ERR_GENERIC, CODE_READY
from lib.logger import Logger


class Client:
    def __init__(self, server_ip, server_port, verbose, quiet, protocol_id):
        """
        Initializes the client.
        """
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.skt.settimeout(TIMEOUT)
        self.server_addr = (server_ip, server_port)
        self.protocol_id = protocol_id
        self.protocol = None
        self.log = Logger(
            "CLIENT",
            CLIENTS_LOG_FILE,
            verbose=verbose,
            quiet=quiet)

    def connect_to_server(self):
        """
        Establishes a connection with the server.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    def run_process(self):
        """
        Executes the main client operation (upload/download).
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    def _negotiate_transaction(self, protocol, payload):
        """
        Sends a request to the server and waits for its response indicating that the operation can continue, or else fails.
        :return:
            - file_size if server is ready
            - None if an error occurs
        """
        try:
            protocol.send(payload)
            response = protocol.recv()

            if response is None:
                raise ConnectionError("Unexpected connection error")

            status_code, file_size = struct.unpack("!BQ", response)

            if status_code == ERR_NO_SPACE:
                self.log.error(
                    f"Server's capacity is full. Could not upload ({status_code})")
                return None
            elif status_code == ERR_FILE_NOT_FOUND:
                self.log.error(
                    f"File not found. ({status_code})")
                return None
            elif status_code == ERR_GENERIC:
                self.log.error(
                    f"Operation failed. ({status_code})")
                return None
            elif status_code == CODE_READY:
                self.log.info(f"Server is ready. Connection established ({status_code})")
                return file_size
            else:
                self.log.error(f"Unknown status code received: {status_code}")

        except Exception as error:
            self.log.error(f"Could not start connection with server: {error}")
            return None
