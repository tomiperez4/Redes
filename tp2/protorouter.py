# Import some POX stuff
from pox.core import core                       # Main POX object
import pox.openflow.libopenflow_01 as of        # OpenFlow 1.0 library
from pox.lib.addresses import EthAddr, IPAddr   # Address types
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.tcp import tcp
from pox.lib.packet.udp import udp
from arp_handler import ArpHandler

log = core.getLogger()
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def log_color(color, msg):
    log.info(f"{color}{msg}{RESET}")


PRIVATE_SUBNET = IPAddr("192.168.1.0")      # Red interna
PRIVATE_MASK = 24                           # Máscara de la red interna
PRIVATE_IP = IPAddr("192.168.1.254")        # IP del router en la red privada
PUBLIC_IP = IPAddr("200.0.0.254")           # IP del router en la red pública
PUBLIC_MAC = EthAddr("00:00:00:aa:aa:aa")   # MAC del router hacia la red pública
PRIVATE_MAC = EthAddr("00:00:00:bb:bb:bb")  # MAC del router hacia la red privada
PUBLIC_PORT = 1                             # Puerto del switch conectado a la red pública
MIN_PORT = 49152
MAX_PORT = 65535
NAT_TIMEOUT = 60

class ProtoRouter(object):
    def __init__(self, connection):
        self.connection = connection
        self.arp = ArpHandler(connection, {PRIVATE_IP: PRIVATE_MAC, PUBLIC_IP: PUBLIC_MAC})
        self.arp.on_resolved = self.handle_ip
        self.nat_table = {}       # (nw_proto, src_ip, src_port) -> public_port
        self.nat_reverse = {}     # (nw_proto, public_port) -> (private_ip, private_port, in_port, src_mac)
        self.used_ports = set()   # (nw_proto, port)
        connection.addListeners(self)

    def _handle_PacketIn(self, event):
        if not event.parsed.parsed:
            log.warning("[DROP] PacketIn con trama no reconocida. POX no pudo decodificar el paquete.")
            return
        if event.parsed.type == ethernet.ARP_TYPE:
            self.arp.handle(event)
        elif event.parsed.type == ethernet.IP_TYPE:
            self.handle_ip(event)
        else:
            log_color(YELLOW, f"Paquete ignorado: protocolo distinto de IPv4 o ARP.")

    def _get_public_port(self, nw_proto, private_port):
        port = private_port
        if port < MIN_PORT or port > MAX_PORT:
            port = MIN_PORT
        attempts = 0
        while (nw_proto, port) in self.used_ports:
            port += 1
            if port > MAX_PORT:
                port = MIN_PORT
            attempts += 1
            if attempts > (MAX_PORT - MIN_PORT + 1):
                log.error("No hay puertos disponibles")
                return None
        self.used_ports.add((nw_proto, port))
        return port

    def _handle_FlowRemoved(self, event):
        match = event.ofp.match
        if match.dl_type != 0x800 or match.nw_proto not in (6, 17):
            return

        nw_proto = match.nw_proto
        public_port = None

        if match.nw_src is not None and match.nw_src.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):
            src_ip = match.nw_src
            private_port = match.tp_src
            key = (nw_proto, src_ip, private_port)
            public_port = self.nat_table.get(key)
        elif match.nw_dst == PUBLIC_IP:
            public_port = match.tp_dst

        if public_port is not None:
            rev_key = (nw_proto, public_port)
            if rev_key in self.nat_reverse:
                private_ip, private_port, _, _ = self.nat_reverse[rev_key]
                key = (nw_proto, private_ip, private_port)
                self.nat_table.pop(key, None)
                self.nat_reverse.pop(rev_key, None)
                self.used_ports.discard(rev_key)

                log_color(YELLOW, f"LIMPIEZA: Puerto público {public_port} liberado tras inactividad.")

    def handle_ip(self, event):
        packet = event.parsed
        ip_pkt = packet.payload
        in_port = event.port

        log_color(
            YELLOW, f"RECIBIDO: {ip_pkt.srcip} → {ip_pkt.dstip} | "
            f"MAC: {packet.src} → {packet.dst} | In Port: {in_port}")

        transport = packet.find('tcp')
        nw_proto = ip_pkt.protocol if transport else None
        if transport is None:
            transport = packet.find('udp')
            if transport:
                nw_proto = ip_pkt.protocol

        # --- PAQUETE DE RED PRIVADA (saliente) ---
        if ip_pkt.srcip.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):
            log_color(GREEN, f"SALIENTE: {ip_pkt.srcip} pertenece a la red privada {PRIVATE_SUBNET}/{PRIVATE_MASK}")
            dst_ip = ip_pkt.dstip
            if dst_ip not in self.arp.arp_table:
                log_color(YELLOW, f"MAC de {dst_ip} desconocida, mandando ARP Request")
                self.arp.resolve_or_queue(dst_ip, PUBLIC_IP, PUBLIC_MAC, PUBLIC_PORT, event)
                return

            dst_mac = self.arp.arp_table[dst_ip]

            if transport is not None:
                private_port = transport.srcport
                key = (nw_proto, ip_pkt.srcip, private_port)
                if key in self.nat_table:
                    public_port = self.nat_table[key]
                else:
                    public_port = self._get_public_port(nw_proto, private_port)
                    if public_port is None:
                        log_color(RED, "No hay puertos disponibles, descartando el paquete")
                        return
                    self.nat_table[key] = public_port
                    self.nat_reverse[(nw_proto, public_port)] = (ip_pkt.srcip, private_port, in_port, packet.src)

                # Flujo saliente: traduce IP origen y puerto origen
                fm = of.ofp_flow_mod()
                fm.idle_timeout = NAT_TIMEOUT
                fm.flags = of.OFPFF_SEND_FLOW_REM
                fm.match.dl_type = 0x800
                fm.match.nw_src = ip_pkt.srcip
                fm.match.nw_dst = ip_pkt.dstip
                fm.match.nw_proto = nw_proto
                fm.match.tp_src = private_port
                fm.match.tp_dst = transport.dstport
                fm.match.in_port = in_port

                fm.actions.append(of.ofp_action_dl_addr.set_src(PUBLIC_MAC))
                fm.actions.append(of.ofp_action_dl_addr.set_dst(dst_mac))
                fm.actions.append(of.ofp_action_nw_addr.set_src(PUBLIC_IP))
                if public_port != private_port:
                    fm.actions.append(of.ofp_action_tp_port.set_src(public_port))
                fm.actions.append(of.ofp_action_output(port=PUBLIC_PORT))
                self.connection.send(fm)

                # Flujo entrante: respuestas hacia el host privado
                fm_back = of.ofp_flow_mod()
                fm_back.idle_timeout = NAT_TIMEOUT
                fm_back.flags = of.OFPFF_SEND_FLOW_REM
                fm_back.match.dl_type = 0x800
                fm_back.match.nw_dst = PUBLIC_IP
                fm_back.match.nw_proto = nw_proto
                fm_back.match.tp_dst = public_port
                fm_back.match.in_port = PUBLIC_PORT

                fm_back.actions.append(of.ofp_action_dl_addr.set_src(PRIVATE_MAC))
                fm_back.actions.append(of.ofp_action_dl_addr.set_dst(packet.src))
                fm_back.actions.append(of.ofp_action_nw_addr.set_dst(ip_pkt.srcip))
                if public_port != private_port:
                    fm_back.actions.append(of.ofp_action_tp_port.set_dst(private_port))
                fm_back.actions.append(of.ofp_action_output(port=in_port))
                self.connection.send(fm_back)

                # Reenviar primer paquete traducido
                packet.src = PUBLIC_MAC
                packet.dst = dst_mac
                ip_pkt.srcip = PUBLIC_IP
                if public_port != private_port:
                    transport.srcport = public_port
            else:
                # No es TCP/UDP: solo reescritura MAC
                fm = of.ofp_flow_mod()
                fm.idle_timeout = NAT_TIMEOUT
                fm.match.nw_src = ip_pkt.srcip
                fm.match.dl_type = 0x800
                fm.match.in_port = in_port

                fm.actions.append(of.ofp_action_dl_addr.set_src(PUBLIC_MAC))
                fm.actions.append(of.ofp_action_dl_addr.set_dst(dst_mac))
                fm.actions.append(of.ofp_action_output(port=PUBLIC_PORT))
                self.connection.send(fm)

                fm_back = of.ofp_flow_mod()
                fm_back.idle_timeout = NAT_TIMEOUT
                fm_back.match.nw_src = ip_pkt.dstip
                fm_back.match.nw_dst = ip_pkt.srcip
                fm_back.match.dl_type = 0x800
                fm_back.match.in_port = PUBLIC_PORT

                fm_back.actions.append(of.ofp_action_dl_addr.set_src(PRIVATE_MAC))
                fm_back.actions.append(of.ofp_action_dl_addr.set_dst(packet.src))
                fm_back.actions.append(of.ofp_action_output(port=in_port))
                self.connection.send(fm_back)

                packet.src = PUBLIC_MAC
                packet.dst = dst_mac

            # Reenviar paquete actual
            msg = of.ofp_packet_out()
            msg.data = packet.pack()
            msg.actions.append(of.ofp_action_output(port=PUBLIC_PORT))
            log_color(CYAN, f"ENVIANDO: {ip_pkt.srcip} → {ip_pkt.dstip} | Out Port: {PUBLIC_PORT}")
            self.connection.send(msg)

        # --- PAQUETE DE RED PÚBLICA (entrante) ---
        elif in_port == PUBLIC_PORT:
            if transport is not None:
                public_port = transport.dstport
                rev_key = (nw_proto, public_port)
                if rev_key in self.nat_reverse:
                    private_ip, private_port, priv_port, client_mac = self.nat_reverse[rev_key]
                    log_color(GREEN, f"ENTRANTE: traduciendo {PUBLIC_IP}:{public_port} → {private_ip}:{private_port}")

                    # Buscar MAC del host privado (por src, ya que el host privado nos envió antes)
                    # La MAC del host privado la guardamos en nat_reverse
                    # Instalar flujo entrante si no existe
                    fm_back = of.ofp_flow_mod()
                    fm_back.idle_timeout = NAT_TIMEOUT
                    fm_back.flags = of.OFPFF_SEND_FLOW_REM
                    fm_back.match.dl_type = 0x800
                    fm_back.match.nw_dst = PUBLIC_IP
                    fm_back.match.nw_proto = nw_proto
                    fm_back.match.tp_dst = public_port
                    fm_back.match.in_port = PUBLIC_PORT

                    fm_back.actions.append(of.ofp_action_dl_addr.set_src(PRIVATE_MAC))
                    fm_back.actions.append(of.ofp_action_dl_addr.set_dst(client_mac))
                    fm_back.actions.append(of.ofp_action_nw_addr.set_dst(private_ip))
                    if public_port != private_port:
                        fm_back.actions.append(of.ofp_action_tp_port.set_dst(private_port))
                    fm_back.actions.append(of.ofp_action_output(port=priv_port))
                    self.connection.send(fm_back)

                    # Reenviar paquete actual traducido
                    packet.dst = client_mac
                    packet.src = PRIVATE_MAC
                    ip_pkt.dstip = private_ip
                    if public_port != private_port:
                        transport.dstport = private_port

                    msg = of.ofp_packet_out()
                    msg.data = packet.pack()
                    msg.actions.append(of.ofp_action_output(port=priv_port))
                    self.connection.send(msg)
                else:
                    log_color(RED, f"ENTRANTE: no hay traducción para puerto {public_port}")
            else:
                log_color(RED, f"ENTRANTE: ignorado (no TCP/UDP)")

        else:
            log_color(RED, f"NO MATCH: {ip_pkt.srcip} no pertenece a {PRIVATE_SUBNET}/{PRIVATE_MASK}")


def launch():

    def start_switch(event):
        log_color(YELLOW, f"Iniciando ProtoRouter para Switch {event.connection.dpid}")
        ProtoRouter(event.connection)

    core.openflow.addListenerByName("ConnectionUp", start_switch)
