import socket

from lib.server.client_handler import CLIENT_TYPE_UPLOAD
from lib.application.client_parser import ClientParser
from lib.transport.go_back_n import GoBackN
from lib.transport.stop_and_wait import StopAndWait
from lib.transport.segments.segment import Segment
from lib.transport.segments.handshake_request_segment import HandshakeRequestSegment
from lib.transport.segments.constants import *

MAX_RETRIES = 5 #Tenemos que ver si dejamos que el cliente mande handshakes infinitamente, o le damos una cantidad logica de intentos

def upload(server_addr, server_port, src_path, verbose, quiet, filename, protocol_str):
    skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    skt.settimeout(SKT_TIMEOUT)

    protocol_id = SW_PROTOCOL_ID if protocol_str == 'sw' else GBN_PROTOCOL_ID

    # lo dejamos por ahora, pero es redundante
    host_bytes = socket.inet_aton(server_addr)
    port_int = int(server_port)

    h_packet = HandshakeRequestSegment(
        operation = CLIENT_TYPE_UPLOAD,
        protocol = protocol_id,
        port = port_int,
        host = host_bytes,
        filename = filename,
    )

    retry_attempts = 0
    response = None

    while retry_attempts < MAX_RETRIES:
        try:
            skt.sendto(h_packet.to_bytes(), (server_addr, server_port))
            raw_data, addr = skt.recvfrom(SKT_BUFFER_SIZE)
            response = Segment.from_bytes(raw_data)

            if response.is_handshake_response_segment():
                break

        except socket.timeout:
            retry_attempts += 1
            print(f"Handshake response from server not received. Attempt {retry_attempts}/5")
        except Exception as error:
            print(f"Unexpected error: {error}")

    if response is None:
        print("Aborting. Max retries reached.")
        skt.close()
        return

    handler_address = (server_addr, response.get_port())

    if protocol_id == SW_PROTOCOL_ID:
        rdt = StopAndWait(skt, verbose, quiet)
    else:
        rdt = GoBackN(skt, verbose, quiet)

    try:
        rdt.send(handler_address, src_path)
    finally:
        skt.close()

    '''
    try:
        skt.sendto(h_packet.to_bytes(), (server_addr, server_port))

        raw_data, new_sv_addr = skt.recvfrom(SKT_BUFFER_SIZE)
        response = Segment.from_bytes(raw_data)
        if not response.is_handshake_response_segment() or new_sv_addr[1] != response.get_port():
            print("Respuesta inválida del servidor")
            return
        handler_address = (server_addr, response.get_port())

        if protocol_id == SW_PROTOCOL_ID:
            rdt = StopAndWait(skt, verbose, quiet)
        else:
            rdt = GoBackN(skt, verbose, quiet)

        rdt.send(handler_address, src_path)

    except socket.timeout:
        print("El servidor no responde al handshake.")
    except Exception as error:
        print(f"Error inesperado: {error}")
    finally:
        skt.close()
    '''

if __name__ == "__main__":
    parser = ClientParser(is_upload=True)
    args = parser.parse()

    upload(args.host, args.port, args.src, args.verbose, args.quiet, args.name, args.protocol)