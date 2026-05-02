import socket
import struct

from lib.constants.protocol_constants import MAX_RETRIES, PROTOCOL_GO_BACK_N, PROTOCOL_STOP_AND_WAIT
from lib.constants.socket_constants import BUFFER_SIZE
from lib.transport.segments.segment import Segment
from lib.transport.segments.syn_segment import SynSegment
from lib.transport.go_back_n import GoBackN
from lib.transport.stop_and_wait import StopAndWait

# Status code
APP_RES_FORMAT = "!B"  # 1 byte unsigned


class RdtSocket:
    def __init__(self, skt, protocol_id, log):
        self.skt = skt
        self.log = log
        self.protocol_id = protocol_id

    def connect(self, address):
        transfer_addr = self._initial_handshake(address)
        if transfer_addr is None:
            return None

        protocol = self._instantiate_protocol()
        if protocol is None:
            return None
        protocol.start(transfer_addr)
        return protocol

    def _initial_handshake(self, address):
        retry_attempts = 0
        syn_pkt = SynSegment(self.protocol_id)
        while retry_attempts < MAX_RETRIES:
            try:
                self.log.info("Sending SYN segment to server")
                self.skt.sendto(syn_pkt.to_bytes(), address)
                raw_data, addr = self.skt.recvfrom(BUFFER_SIZE)
                response = Segment.from_bytes(raw_data)

                if response.is_synack_segment():
                    self.log.info("Received SYN-ACK segment from server")
                    return address[0], response.get_port()

            except socket.timeout:
                retry_attempts += 1
                self.log.warning(
                    f"SYN-ACK segment from server not received. Attempt {retry_attempts}/5")
            except Exception as error:
                self.log.error(f"Unexpected error: {error}")

        self.log.error("Handshake failed. Max retries reached.")
        return None

    def _instantiate_protocol(self):
        if self.protocol_id == PROTOCOL_STOP_AND_WAIT:
            return StopAndWait(self.skt, self.log)
        elif self.protocol_id == PROTOCOL_GO_BACK_N:
            return GoBackN(self.skt, self.log)
        return None

