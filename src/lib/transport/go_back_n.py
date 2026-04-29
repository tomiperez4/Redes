import os
import socket as socket_module
import threading
import time

from lib.segments.ack_segment import AckSegment
from lib.segments.data_segment import DataSegment
from lib.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol
from lib.constants.protocol_constants import MAX_SEQ, WINDOW_SIZE
from lib.constants.socket_constants import BUFFER_SIZE, MAX_PACKET_SIZE, TIMEOUT


# Hay que revisar esto. Faltan retries, y hay ciertas cosas raras en el codigo
class GoBackN(ReliableProtocol):
    def __init__(self, socket, log):
        super().__init__(socket, log)
        self.srtt = TIMEOUT
        self.rttvar = TIMEOUT / 2
        self.rto = TIMEOUT
        self.sent_times = {}

    def _update_rto(self, sample_rtt):
        alpha, beta = 0.125, 0.25
        self.srtt = (1 - alpha) * self.srtt + alpha * sample_rtt
        self.rttvar = (1 - beta) * self.rttvar + beta * abs(self.srtt - sample_rtt)
        self.rto = self.srtt + max(0.1, 4 * self.rttvar)
        self.socket.settimeout(self.rto)

    def send(self, address, path):
        chunks = []
        with open(path, "rb") as f:
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)

        total = len(chunks)
        self.log.debug(f"File loaded: {total} chunks")

        # python maneja de una variables atomicas para lectura
        base = 0
        next_idx = 0
        lock = threading.Lock()

        send_allowed = threading.Event()
        send_allowed.set()

        repeat_window = threading.Event()

        done = threading.Event()

        def sender_thread():
            nonlocal base, next_idx

            while True:
                send_allowed.wait()
                send_allowed.clear()

                if done.is_set():
                    break

                if repeat_window.is_set():
                    repeat_window.clear()
                    self.log.warning("Timeout ? sending window again")
                    with lock:
                        next_idx = base

                while True:
                    with lock:
                        if next_idx >= total or next_idx >= base + WINDOW_SIZE:
                            break
                        idx = next_idx
                        seq = idx % MAX_SEQ
                        chunk = chunks[idx]
                        pkt = DataSegment(seq, chunk, 1)

                        # Se trackean los tiempos de los paquetes mandados
                        if idx not in self.sent_times:
                            self.sent_times[idx] = time.time()

                        next_idx += 1

                    self.socket.sendto(pkt.to_bytes(), address)
                    self.log.debug(f"Sent segment idx={idx} seq={seq}")

                with lock:
                    all_sent = (next_idx >= total)
                    window_clear = (base >= total)

                if all_sent and window_clear:
                    _send_fin(base, address)
                    done.set()
                    break

        def ack_receiver_thread():
            nonlocal base, next_idx

            self.socket.settimeout(self.rto)

            while not done.is_set():
                try:
                    raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                    received = Segment.from_bytes(raw)

                    if not received.is_ack_segment():
                        self.log.debug("Non-ACK segment received, ignoring")
                        continue

                    ack_seq = received.ack
                    self.log.debug(f"ACK received: ack_seq={ack_seq}")

                    with lock:
                        advanced = False
                        for idx in range(base, next_idx):
                            if idx % MAX_SEQ == ack_seq:
                                # Update Dynamic RTO
                                if idx in self.sent_times:
                                    sample_rtt = time.time() - self.sent_times[idx]
                                    self._update_rto(sample_rtt)

                                    # Clean up confirmation times
                                    to_del = [i for i in self.sent_times if i <= idx]
                                    for i in to_del:
                                        self.sent_times.pop(i, None)

                                if idx + 1 > base:
                                    base = idx + 1
                                    self.log.debug(f"Window advanced: base={base}")
                                    advanced = True
                                break

                    if advanced:
                        send_allowed.set()

                    with lock:
                        if base >= total:
                            send_allowed.set()
                            break

                except socket_module.timeout:
                    # timeout, no se recibio el ack esperado, se setea el repeat_window para mandar la ventana
                    self.log.warning(f"ACK timeout ({self.rto:.4f}s) ? signaling retransmission")

                    with lock:
                        self.sent_times.clear()  # Karn: avoid RTT ambiguity
                        self.rto = min(self.rto * 2, 8.0)  # Exponential backoff
                        self.socket.settimeout(self.rto)

                    repeat_window.set()
                    send_allowed.set()

        def _send_fin(fin_idx, address):
            fin_seq = fin_idx % MAX_SEQ
            pkt = DataSegment(fin_seq, b"", 0)
            self.socket.settimeout(self.rto)
            while True:
                self.socket.sendto(pkt.to_bytes(), address)
                self.log.debug("FIN segment sent")
                try:
                    raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                    seg = Segment.from_bytes(raw)
                    if seg.is_ack_segment() and seg.ack == fin_seq:
                        self.log.debug("FIN ACK received ? connection closed")
                        return
                except socket_module.timeout:
                    self.log.warning("Timeout waiting for FIN ACK, retrying")

        # daemon es para que si muere el thread padre, se mata a los threads hijos, y no queden colgados
        t_sender = threading.Thread(target=sender_thread, daemon=True)
        t_acks = threading.Thread(target=ack_receiver_thread, daemon=True)

        t_sender.start()
        t_acks.start()

        t_sender.join()
        t_acks.join()

        self.log.debug("Send complete")

    def receive(self, address, output_path):
        handshake_done = False
        expected_seq = 0
        last_ack = None
        temp_file = output_path + ".tmp"

        try:
            with open(temp_file, "wb") as out:
                while True:
                    raw, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
                    seg = Segment.from_bytes(raw)

                    if seg.is_finished():
                        self.log.debug("Client disconnected (FINISHED PACKET RECEIVED).")
                        os.remove(temp_file)
                        return

                    '''
                    if seg.is_handshake_response_segment():
                        if not handshake_done and address == addr:
                            self.log.debug("Duplicated handshake response segment received. Re-sending READY segment")
                            ready_pkt = HandshakeReadySegment()
                            self.socket.sendto(ready_pkt.to_bytes(), address)
                        continue
                    '''
                    if not seg.is_data_segment():
                        self.log.warning("Unexpected segment type, ignoring")
                        continue

                    handshake_done = True
                    self.log.debug(f"Data segment received: seq={seg.seq} mf={seg.mf}")

                    if seg.seq == expected_seq:
                        out.write(seg.data)
                        ack = AckSegment(expected_seq)
                        self.socket.sendto(ack.to_bytes(), address)
                        self.log.debug(f"ACK sent: ack={expected_seq}")
                        last_ack = expected_seq

                        if seg.mf == 0:
                            self.log.debug("Final segment received. Connection closed")
                            break

                        expected_seq = (expected_seq + 1) % MAX_SEQ
                    else:
                        self.log.warning(
                            f"Out-of-order segment: got seq={seg.seq}, "
                            f"expected={expected_seq}"
                        )
                        if last_ack is not None:
                            ack = AckSegment(last_ack)
                            self.socket.sendto(ack.to_bytes(), address)
                            self.log.debug(f"Re-sent last ACK: ack={last_ack}")
            os.rename(temp_file, output_path)
            self.log.debug("File transfer complete")
        except Exception as error:
            self.log.error(f"File transfer failed: {error}")
            if os.path.exists(temp_file):
                os.remove(temp_file)