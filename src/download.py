import socket

from lib.server.client_handler import CLIENT_TYPE_DOWNLOAD
from src.lib.application.client_parser import ClientParser
from src.lib.transport.stop_and_wait import StopAndWait
from src.lib.transport.segments.segment import Segment
from src.lib.transport.segments.handshake_request_segment import HandshakeRequestSegment
from src.lib.transport.segments.constants import *

# Para probar, dsps hay q modularizar y crear clase client?
def download(server_addr, server_port, dst_path, filename, protocol_str):
    skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    skt.settimeout(SKT_TIMEOUT)

    protocol_id = SW_PROTOCOL_ID if protocol_str == 'sw' else GBN_PROTOCOL_ID

    # lo dejamos por ahora, pero es redundante
    host_bytes = socket.inet_aton(server_addr)
    port_int = int(server_port)

    # No se si port y host son del client o server
    h_packet = HandshakeRequestSegment(
        operation = CLIENT_TYPE_DOWNLOAD,
        protocol = protocol_id,
        port = port_int,
        host = host_bytes,
        filename = filename,
    )

    try:
        skt.sendto(h_packet.to_bytes(), (server_addr, server_port))

        raw_data, _ = skt.recvfrom(SKT_BUFFER_SIZE)
        response = Segment.from_bytes(raw_data)
        if not response.is_handshake_response_segment():
            print("Respuesta inválida del servidor")
            return
        handler_address = (server_addr, response.get_port())

        if protocol_id == SW_PROTOCOL_ID: # Stop & Wait dsps lo cambio
            rdt = StopAndWait(skt)
            rdt.receive(handler_address, dst_path)

    except socket.timeout:
        print("El servidor no responde al handshake.")
    except Exception as error:
        print(f"Error inesperado: {error}")
    finally:
        skt.close()

if __name__ == "__main__":
    parser = ClientParser(is_upload=False)
    args = parser.parse()

    download(args.host, args.port, args.dst, args.name, args.protocol)