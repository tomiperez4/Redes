import socket as socket_module
import time

from lib.constants.socket_constants import MAX_PACKET_SIZE
from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.finished_segment import FinishedSegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol

INITIAL_TIMEOUT = 0.5
ALPHA = 0.125
BETA = 0.25


class StopAndWait(ReliableProtocol):
    def __init__(self, socket, address, log):
        super().__init__(socket, log)
        self.address = address
        self._send_seq = 0
        self._expected_seq = 0
        self._timeout = INITIAL_TIMEOUT
        self._srtt = None
        self._rttvar = None
        self.socket.settimeout(self._timeout)

    # -------------------------------------------------------------------------
    # API pública
    # -------------------------------------------------------------------------

    def send(self, data: bytes):
        """
        Arma el segmento, lo envía y bloquea hasta recibir el ACK correcto.
        Retransmite ante timeout. Avanza send_seq al confirmar.
        """
        pkt = DataSegment(self._send_seq, data)

        while True:
            self.socket.sendto(pkt.to_bytes(), self.address)
            self.log.debug(f"Enviado seq={self._send_seq}")
            t_send = time.time()

            ack = self.__wait_for_ack(self._send_seq)

            if ack is not None:
                self.__update_rto(time.time() - t_send)
                self.log.debug(
                    f"ACK {self._send_seq} recibido. "
                    f"RTO={self._timeout:.4f}s"
                )
                self._send_seq = 1 - self._send_seq
                return

            self.log.warning(f"Timeout. Re-enviando seq={self._send_seq}")

    def recv(self):
        """
        Bloquea hasta recibir un DataSegment con el seq esperado.
        Descarta fuera de orden y re-envía el último ACK.
        Avanza expected_seq al aceptar. Devuelve el payload.
        """
        while True:
            seg = self.__try_recv()
            if seg is None:
                continue

            if seg.is_finished_segment():
                ack = AckSegment(self._expected_seq)
                self.socket.sendto(ack.to_bytes(), self.address)
                end_time = time.time() + 2

                while time.time() < end_time:
                    seg_rep = self.__try_recv()

                    if seg_rep and seg_rep.is_finished_segment():
                        self.log.debug("FIN retransmitido recibido, reenviando ACK")
                        self.socket.sendto(ack.to_bytes(), self.address)

                self.socket.close()
                self.log.info("Received Finished segment. Socket closed")
                return None

            if not seg.is_data_segment():
                self.log.debug("Segmento inesperado, ignorando")
                continue

            if seg.seq == self._expected_seq:
                self.log.debug(f"Data recibida: seq={seg.seq}")
                ack = AckSegment(self._expected_seq)
                self.socket.sendto(ack.to_bytes(), self.address)
                self.log.debug(f"ACK enviado: ack={self._expected_seq}")
                self._expected_seq = 1 - self._expected_seq
                return seg.get_payload()
            else:
                self.log.debug(
                    f"Fuera de orden: got={seg.seq}, "
                    f"esperado={self._expected_seq}. Re-enviando último ACK"
                )
                last_ack = AckSegment(1 - self._expected_seq)
                self.socket.sendto(last_ack.to_bytes(), self.address)

    def close(self):
        self.socket.settimeout(self._timeout)

        fin = FinishedSegment(self._send_seq)

        while True:
            self.socket.sendto(fin.to_bytes(), self.address)
            self.log.debug("FIN enviado")

            try:
                raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                seg = Segment.from_bytes(raw)

                if seg.is_ack_segment() and seg.get_ack_number() == self._send_seq:
                    self.log.debug("FIN ACK recibido. Cerrando.")
                    self.socket.close()
                    return

            except socket_module.timeout:
                self.log.debug("Timeout esperando ACK, reintentando FIN")
                continue

    # -------------------------------------------------------------------------
    # Helpers privados
    # -------------------------------------------------------------------------

    def __wait_for_ack(self, expected_ack):
        """
        Espera un ACK con ack==expected_ack hasta agotar el timeout.
        Descarta cualquier otro segmento que llegue mientras espera.
        Devuelve el AckSegment o None si hubo timeout.
        """
        deadline = time.time() + self._timeout

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None

            self.socket.settimeout(remaining)
            seg = self.__try_recv()

            if seg is None:
                return None

            if seg.is_ack_segment():
                if seg.get_ack_number() == expected_ack:
                    return seg
                self.log.debug(
                    f"ACK inesperado: got={seg.get_ack_number()}, esperado={expected_ack}"
                )
                continue

            # Cualquier otra cosa se ignora mientras esperamos el ACK
            self.log.debug("Segmento no esperado durante wait_for_ack, ignorando")

    def __try_recv(self):
        try:
            raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
            return Segment.from_bytes(raw)
        except socket_module.timeout:
            return None

    def __update_rto(self, sample_rtt: float):
        if self._srtt is None:
            self._srtt = sample_rtt
            self._rttvar = sample_rtt / 2
        else:
            self._rttvar = (
                (1 - BETA) * self._rttvar
                + BETA * abs(self._srtt - sample_rtt)
            )
            self._srtt = (1 - ALPHA) * self._srtt + ALPHA * sample_rtt

        self._timeout = self._srtt + 4 * self._rttvar
        self.socket.settimeout(self._timeout)