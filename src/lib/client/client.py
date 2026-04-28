import socket

from lib.transport.segments.constants import *
from lib.transport.stop_and_wait import StopAndWait
from lib.transport.go_back_n import GoBackN
from lib.transport.segments.segment import Segment
from lib.logger import Logger

class Client:
    def __init__(self, server_addr, server_port, verbose, quiet, protocol_id):
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.skt.settimeout(SKT_TIMEOUT)
        self.server_dir = (server_addr, server_port)
        self.protocol_id = protocol_id
        self.log = Logger(prefix="CLIENT", verbose=verbose, quiet=quiet, log_file="clients.log")
        self.rdt = self._create_rdt()

    def _create_rdt(self):
        if self.protocol_id == SW_PROTOCOL_ID:
            return StopAndWait(self.skt, self.log)
        return GoBackN(self.skt, self.log)

    def handshake(self, h_packet):
        retry_attempts = 0

        while retry_attempts < UPLOAD_MAX_RETRIES:
            try:
                self.log.info("Sending handshake request to server")
                self.skt.sendto(h_packet.to_bytes(), self.server_dir)
                raw_data, addr = self.skt.recvfrom(SKT_BUFFER_SIZE)
                response = Segment.from_bytes(raw_data)

                if response.is_handshake_response_segment():
                    self.log.info("Received handshake response from server")
                    return self.server_dir[0], response.get_port()

                if response.is_handshake_error_segment():
                    self.log.info("Received handshake error from server. Aborting")
                    self.skt.close()
                    return None

            except socket.timeout:
                retry_attempts += 1
                self.log.warning(f"Handshake response from server not received. Attempt {retry_attempts}/5")
            except Exception as error:
                self.log.warning(f"Unexpected error: {error}")

        self.log.error("Aborting. Max retries reached.")
        self.skt.close()
        return None

    def run_process(self):
        raise NotImplementedError