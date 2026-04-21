import socket

from src.lib.application.client_parser import ClientParser
from src.lib.transport.stop_and_wait import StopAndWait
from src.lib.transport.segments.handshake_segment import HandshakeSegment

# Para probar, dsps hay q modularizar y crear clase client?
def download(server_addr, server_port, dst_path, filename, protocol_str):
    skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    skt.settimeout(2.0)

    protocol_id = 0 if protocol_str == 'sw' else 1

    host_bytes = socket.inet_aton(server_addr)
    port_int = int(server_port)

    # No se si port y host son del client o server
    h_packet = HandshakeSegment.create_client_handshake(
        filename=filename,
        protocol=protocol_id,
        type=1, # 1 = DOWNLOAD
        port=port_int,
        host=host_bytes,
    )

    try:
        skt.sendto(h_packet.to_bytes(), (server_addr, server_port))

        raw_data, handler_address = skt.recvfrom(1024)


        if protocol_id == 0: # Stop & Wait dsps lo cambio
            rdt = StopAndWait(skt)
            rdt.receive(handler_address, dst_path)
            
    except socket.timeout:
        print("El servidor no responde al handshake.")
    finally:
        skt.close()

if __name__ == "__main__":
    parser = ClientParser(is_upload=False)
    args = parser.parse()

    download(args.host, args.port, args.dst, args.name, args.protocol)