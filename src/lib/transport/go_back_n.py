from lib.logger import Logger
from lib.transport.rdt import ReliableProtocol

class GoBackN(ReliableProtocol):
    def __init__(self, socket, verbose, quiet):
        super().__init__(socket)
        self.socket = socket
        self.log = Logger(socket, verbose, quiet)

    def send(self, address, path):
        window_size = 5
        base = 0
        next_seq_num = 0
        packets = self._get_all_packets(path)  # Dividir archivo en segmentos de datos
        total_packets = len(packets)

        while base < total_packets:
            # 1. Enviar paquetes mientras la ventana lo permita
            while next_seq_num < base + window_size and next_seq_num < total_packets:
                self.socket.sendto(packets[next_seq_num].to_bytes(), address)
                if base == next_seq_num:
                    self.socket.settimeout(2.0)  # Iniciar timer para el primer paquete
                next_seq_num += 1

            try:
                # 2. Esperar ACKs
                data, addr = self.socket.recvfrom(1024)
                ack_pkt = Segment.from_bytes(data)

                if ack_pkt.is_ack_segment():
                    # ACKs en GBN son acumulativos
                    # Si recibo ACK 5, significa que el 0,1,2,3 y 4 llegaron bien
                    if ack_pkt.ack >= base:
                        base = ack_pkt.ack + 1
                        if base == next_seq_num:
                            self.socket.settimeout(None)  # Ventana vacía, apago timer
                        else:
                            self.socket.settimeout(2.0)  # Reinicio timer para el nuevo base

            except socket.timeout:
                # 3. REINTENTO: Si hay timeout, vuelvo a enviar TODO desde la base
                self.socket.settimeout(2.0)
                for i in range(base, next_seq_num):
                    self.socket.sendto(packets[i].to_bytes(), address)

    def receive(self, address, output_path):
        expected_seq_num = 0
        with open(output_path, "wb") as f:
            while True:
                try:
                    data, addr = self.socket.recvfrom(1024)
                    segment = Segment.from_bytes(data)

                    if segment.is_data_segment():
                        if segment.seq_num == expected_seq_num:
                            # Llegó el que esperaba: lo guardo y pido el siguiente
                            f.write(segment.data)
                            ack = AckSegment(expected_seq_num)
                            self.socket.sendto(ack.to_bytes(), addr)
                            expected_seq_num += 1

                            if segment.is_last:  # Flag para saber si terminó el archivo
                                break
                        else:
                            # Llegó uno desordenado: lo descarto y mando ACK del último bien recibido
                            # (O no mando nada, pero el ACK acumulativo ayuda al servidor)
                            if expected_seq_num > 0:
                                ack = AckSegment(expected_seq_num - 1)
                                self.socket.sendto(ack.to_bytes(), addr)
                except Exception:
                    break

    def 
def main():
    pass