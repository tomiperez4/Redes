import socket
import threading

from lib.transport.segments.segment import Segment
from lib.constants.socket_constants import BUFFER_SIZE
from lib.transport.segments.synack import SynackSegment
from lib.transport.segments.finished_segment import FinishedSegment
from lib.constants.server_constants import MAX_CLIENTS
from lib.constants.protocol_constants import PROTOCOL_GO_BACK_N, PROTOCOL_STOP_AND_WAIT
from lib.transport.stop_and_wait import StopAndWait
from lib.transport.go_back_n import GoBackN


class RdtListener:
    def __init__(self, skt, log):
        self.skt = skt
        self.log = log
        self.clients = {}
        self.client_lock = threading.Lock()

    def handle_incoming(self):
        try:
            raw, address = self.skt.recvfrom(BUFFER_SIZE)
            self.log.debug(f"Packet received from {address}")
            segment = Segment.from_bytes(raw)

            if address in self.clients and segment.is_syn_segment():

                with self.client_lock:
                    port = self.clients[address]
                    h_response = SynackSegment(port)
                    self.skt.sendto(h_response.to_bytes(), address)
                    return None, None
            if len(self.clients) >= MAX_CLIENTS:
                self._ack_error("Client limit reached", address)
                return None

            if not segment.is_syn_segment():
                self.log.warning("Expected handshake request segment")
                return None
            protocol_type = segment.get_protocol()
            # Assign new port for incoming client
            socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            socket_client.bind((self.skt.getsockname()[0], 0))

            with self.client_lock:
                port = socket_client.getsockname()[1]
                self.clients[address] = port

                syn_ack = SynackSegment(port)
                self.skt.sendto(syn_ack.to_bytes(), address)

            return self._initialize_protocol(
                protocol_type, socket_client), address

        except Exception as error:
            self.log.error(f"RDTListener error: {error}")

    def _ack_error(self, error_msg, address):
        self.log.warning(error_msg)
        h_error = FinishedSegment()
        self.skt.sendto(h_error.to_bytes(), address)

    def _initialize_protocol(self, protocol_type, socket_client):
        if protocol_type == PROTOCOL_GO_BACK_N:
            return GoBackN(socket_client, self.log.clone("GO-BACK-N"))
        elif protocol_type == PROTOCOL_STOP_AND_WAIT:
            return StopAndWait(socket_client, self.log.clone("STOP_AND_WAIT"))
        else:
            self.log.error(f"Unknown protocol type: {protocol_type}")
            return None

    def remove_client(self, address):
        with self.client_lock:
            del self.clients[address]
            self.log.info(f"Client finished (remaining: {len(self.clients)})")
