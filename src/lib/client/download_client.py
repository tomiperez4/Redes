import socket

from lib.transport.segments.handshake_request_segment import HandshakeRequestSegment
from lib.transport.segments.handshake_ready_segment import HandshakeReadySegment
from lib.transport.segments.finished_segment import FinishedSegment
from lib.server.client_handler import CLIENT_TYPE_DOWNLOAD
from lib.client.client import Client

class DownloadClient(Client):
    def __init__(self, server_addr, server_port, verbose, quiet, protocol_id, dst_path, filename):
        super().__init__(server_addr, server_port, verbose, quiet, protocol_id)
        self.dst_path = dst_path
        self.filename = filename

    def run_process(self):
        h_packet = HandshakeRequestSegment(
            operation = CLIENT_TYPE_DOWNLOAD,
            protocol = self.protocol_id,
            port = int(self.server_dir[1]),
            host = socket.inet_aton(self.server_dir[0]),
            filename = self.filename,
            size = 0
        )

        handler_address = self.handshake(h_packet)
        if handler_address is None:
            return

        ready_packet = HandshakeReadySegment()
        try:
            self.skt.sendto(ready_packet.to_bytes(), handler_address)
            self.log.info("Ready segment sent. Waiting data from server...")
            self.rdt.receive(handler_address, self.dst_path)
        except Exception as error:
            self.log.info(f"Connection lost: {error}. Sending FINISHED packet to server...")
            fin = FinishedSegment()
            self.skt.sendto(fin.to_bytes(), handler_address)
        finally:
            self.skt.close()
