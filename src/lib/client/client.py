import socket

from lib.constants.socket_constants import TIMEOUT, BUFFER_SIZE
from lib.constants.protocol_constants import PROTOCOL_STOP_AND_WAIT, MAX_RETRIES
from lib.constants.log_file_constants import CLIENTS_LOG_FILE
from lib.transport.stop_and_wait import StopAndWait
from lib.transport.go_back_n import GoBackN
from lib.segments.segment import Segment
from lib.logger import Logger

class Client:
    def __init__(self, server_addr, server_port, verbose, quiet, protocol_id):
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.skt.settimeout(TIMEOUT)
        self.server_dir = (server_addr, server_port)
        self.protocol_id = protocol_id
        self.log = Logger("CLIENT", CLIENTS_LOG_FILE, verbose=verbose, quiet=quiet)
        self.rdt = self._create_rdt()

    def _create_rdt(self):
        if self.protocol_id == PROTOCOL_STOP_AND_WAIT:
            return StopAndWait(self.skt, self.log)
        return GoBackN(self.skt, self.log)

    def handshake(self, h_packet):
        retry_attempts = 0

        while retry_attempts < MAX_RETRIES:
            try:
                self.log.info("Sending handshake request to server")
                self.skt.sendto(h_packet.to_bytes(), self.server_dir)
                raw_data, addr = self.skt.recvfrom(BUFFER_SIZE)
                response = Segment.from_bytes(raw_data)

                if response.is_handshake_response_segment():
                    self.log.info("Received handshake response from server")
                    return self.server_dir[0], response.get_port(), response.get_size()

                if response.is_handshake_error_segment():
                    self.log.error("Received handshake error from server. Aborting")
                    self.skt.close()
                    return None

            except socket.timeout:
                retry_attempts += 1
                self.log.warning(f"Handshake response from server not received. Attempt {retry_attempts}/5")
            except Exception as error:
                self.log.error(f"Unexpected error: {error}")

        self.log.error("Aborting. Max retries reached.")
        self.skt.close()
        return None

    def run_process(self):
        raise NotImplementedError