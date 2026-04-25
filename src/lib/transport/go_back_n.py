import socket as socket_module
import threading

from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.segment import Segment
from lib.transport.rdt import ReliableProtocol
from lib.logger import Logger

SEGMENT_SIZE = 1024
MAX_PACKET_SIZE = SEGMENT_SIZE + DataSegment.HEADER_SIZE
TIMEOUT = 0.5
WINDOW_SIZE = 8
MAX_SEQ = 256  # xq el numero de seq tiene q ser un byte


class GoBackN(ReliableProtocol):
    def __init__(self, socket, verbose, quiet):
        super().__init__(socket)
        self.log = Logger('GO-BACK-N', verbose, quiet)

    def send(self, address, path):
        chunks = []
        with open(path, "rb") as f:
            while True:
                chunk = f.read(SEGMENT_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)

        total = len(chunks)
        self.log.info(f"File loaded: {total} chunks")

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
                    self.log.error("Timeout — sending window again")
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
                        next_idx += 1

                    self.socket.sendto(pkt.to_bytes(), address)
                    self.log.info(f"Sent segment idx={idx} seq={seq}")

                with lock:
                    all_sent = (next_idx >= total)
                    window_clear = (base >= total)

                if all_sent and window_clear:
                    _send_fin(base, address)
                    done.set()
                    break

        def ack_receiver_thread():
            nonlocal base, next_idx

            self.socket.settimeout(TIMEOUT)

            while not done.is_set():
                try:
                    raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                    received = Segment.from_bytes(raw)

                    if not received.is_ack_segment():
                        self.log.debug("Non-ACK segment received, ignoring")
                        continue

                    ack_seq = received.ack
                    self.log.info(f"ACK received: ack_seq={ack_seq}")

                    with lock:
                        # como pueden repetirse indices con mismo seq buscamos en el intervalo
                        advanced = False
                        for idx in range(base, next_idx):
                            if idx % MAX_SEQ == ack_seq:
                                if idx + 1 > base:
                                    base = idx + 1
                                    self.log.info(f"Window advanced: base={base}")
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
                    self.log.error("ACK timeout — signaling retransmission")
                    repeat_window.set()
                    send_allowed.set()

        def _send_fin(fin_idx, address):
            fin_seq = fin_idx % MAX_SEQ
            pkt = DataSegment(fin_seq, b"", 0)
            self.socket.settimeout(TIMEOUT)
            while True:
                self.socket.sendto(pkt.to_bytes(), address)
                self.log.info("FIN segment sent")
                try:
                    raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                    seg = Segment.from_bytes(raw)
                    if seg.is_ack_segment() and seg.ack == fin_seq:
                        self.log.info("FIN ACK received — connection closed")
                        return
                except socket_module.timeout:
                    self.log.error("Timeout waiting for FIN ACK, retrying")

        # daemon es para que si muere el thread padre, se mata a los threads hijos, y no queden colgados
        t_sender = threading.Thread(target=sender_thread, daemon=True)
        t_acks = threading.Thread(target=ack_receiver_thread, daemon=True)

        t_sender.start()
        t_acks.start()

        t_sender.join()
        t_acks.join()

        self.log.info("Send complete")

    def receive(self, address, output_path):
        expected_seq = 0
        last_ack = None

        with open(output_path, "wb") as out:
            while True:
                raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                seg = Segment.from_bytes(raw)

                if not seg.is_data_segment():
                    self.log.error("Unexpected segment type, ignoring")
                    continue

                self.log.info(f"Data segment received: seq={seg.seq} mf={seg.mf}")

                if seg.seq == expected_seq:
                    out.write(seg.data)
                    ack = AckSegment(expected_seq)
                    self.socket.sendto(ack.to_bytes(), address)
                    self.log.info(f"ACK sent: ack={expected_seq}")
                    last_ack = expected_seq

                    if seg.mf == 0:
                        self.log.info("Final segment received — connection closed")
                        break

                    expected_seq = (expected_seq + 1) % MAX_SEQ
                else:
                    self.log.error(
                        f"Out-of-order segment: got seq={seg.seq}, "
                        f"expected={expected_seq}"
                    )
                    if last_ack is not None:
                        ack = AckSegment(last_ack)
                        self.socket.sendto(ack.to_bytes(), address)
                        self.log.info(f"Re-sent last ACK: ack={last_ack}")