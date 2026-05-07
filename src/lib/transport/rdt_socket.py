import socket

from lib.common import MAX_HSK_RETRIES, PROTOCOL_GO_BACK_N, PROTOCOL_STOP_AND_WAIT, BUFFER_SIZE
from lib.transport.segments.segment import Segment
from lib.transport.segments.syn_segment import SynSegment
from lib.transport.go_back_n import GoBackN
from lib.transport.stop_and_wait import StopAndWait

class RdtSocket:
    """
    Wrapper for the UDP socket that incorporates an RDT protocol.
    """
    def __init__(self, skt, protocol_id, log):
        self.skt = skt
        self.log = log
        self.protocol_id = protocol_id


    def connect(self, address):
        """
        Connects a client to the server.
        """
        transfer_addr = self._initial_handshake(address)
        if transfer_addr is None:
            return None

        protocol = self._instantiate_protocol(transfer_addr)
        if protocol is None:
            return None
        return protocol


    def _initial_handshake(self, address):
        """
        Initializes the handshake process by sending a SYN segment with the desired protocol
        and waits for a SYN-ACK with the assigned port.
        """
        retry_attempts = 0
        syn_pkt = SynSegment(self.protocol_id)
        while retry_attempts < MAX_HSK_RETRIES:
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
                    f"SYN-ACK segment from server not received. Attempt {retry_attempts}/{MAX_HSK_RETRIES}")
            except Exception as error:
                self.log.error(f"Unexpected error: {error}")

        self.log.error("Handshake failed. Max retries reached.")
        return None

    def _instantiate_protocol(self, address):
        """
        Creates the correct RDT protocol based on protocol_id.
        """
        if self.protocol_id == PROTOCOL_STOP_AND_WAIT:
            return StopAndWait(self.skt, address, self.log.clone("CLIENT (SW)"))
        elif self.protocol_id == PROTOCOL_GO_BACK_N:
            return GoBackN(self.skt, address, self.log.clone("CLIENT (GBN)"))
        return None

