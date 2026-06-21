# Import some POX stuff
from pox.core import core                       # Main POX object
import pox.openflow.libopenflow_01 as of        # OpenFlow 1.0 library
from pox.lib.addresses import EthAddr, IPAddr   # Address types
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.ethernet import ETHER_BROADCAST
from pox.lib.packet.arp import arp
from pox.lib.packet.ipv4 import ipv4

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
NAT_TIMEOUT = 10

class ProtoRouter(object):
    def __init__(self, connection):
        self.connection = connection
        self.arp_table = {}
        self.pending = {}
        self.nat_table = {}       # (nw_proto, src_ip, src_port) -> public_port
        self.used_ports = set()   # (nw_proto, port)
        connection.addListeners(self)

    def _handle_PacketIn(self, event):
        if not event.parsed.parsed:
            log.warning("[DROP] PacketIn con trama no reconocida. POX no pudo decodificar el paquete.")
            return
        if event.parsed.type == ethernet.ARP_TYPE:
            self.handle_arp(event)
        elif event.parsed.type == ethernet.IP_TYPE:
            self.handle_ip(event)
        else:
            log_color(YELLOW, f"Paquete ignorado: protocolo distinto de IPv4 o ARP.")

    def handle_arp(self, event):
        eth = event.parsed
        arp_pkt = eth.payload

        # Aprender la MAC del que pregunta
        self.arp_table[arp_pkt.protosrc] = arp_pkt.hwsrc
        log_color(CYAN, f"ARP aprendido: {arp_pkt.protosrc} -> {arp_pkt.hwsrc}")

        if arp_pkt.opcode == arp.REQUEST:
            # Chequeo si es para alguna de nuestras IP
            if arp_pkt.protodst == PRIVATE_IP:
                self.send_arp_reply(event, arp_pkt, PRIVATE_MAC)
            elif arp_pkt.protodst == PUBLIC_IP:
                self.send_arp_reply(event, arp_pkt, PUBLIC_MAC)
            else:
                log_color(YELLOW, f"ARP Request para {arp_pkt.protodst}, no es nuestro")

        elif arp_pkt.opcode == arp.REPLY:
            # Se respondió nuestro ARP Request: procesamos pendientes
            ip = arp_pkt.protosrc
            if ip in self.pending:
                log_color(GREEN, f"ARP resuelto {ip} -> {arp_pkt.hwsrc}, procesando pendientes")
                for pending_event in self.pending.pop(ip):
                    self.handle_ip(pending_event)

    def send_arp_reply(self, event, arp_req, our_mac):
        """Responde un ARP Request con nuestra MAC"""
        arp_reply = arp()
        arp_reply.opcode = arp.REPLY
        arp_reply.hwsrc = our_mac              # MAC del router
        arp_reply.hwdst = arp_req.hwsrc        # MAC de quien preguntó
        arp_reply.protosrc = arp_req.protodst  # IP del router
        arp_reply.protodst = arp_req.protosrc  # IP del que preguntó

        eth = ethernet()
        eth.type = ethernet.ARP_TYPE
        eth.src = our_mac
        eth.dst = arp_req.hwsrc
        eth.payload = arp_reply

        msg = of.ofp_packet_out()
        msg.data = eth.pack()
        msg.actions.append(of.ofp_action_output(port=event.port))
        self.connection.send(msg)
        log_color(GREEN, f"ARP Reply: {arp_req.protodst} está en {our_mac} → enviado a {arp_req.protosrc}")

    def send_arp_request(self, ip_target, src_ip, src_mac, out_port):
        """Manda un ARP Request para resolver una IP"""
        arp_req = arp()
        arp_req.opcode = arp.REQUEST
        arp_req.hwsrc = src_mac
        arp_req.hwdst = EthAddr("ff:ff:ff:ff:ff:ff")
        arp_req.protosrc = src_ip
        arp_req.protodst = ip_target

        eth = ethernet()
        eth.type = ethernet.ARP_TYPE
        eth.src = src_mac
        eth.dst = ETHER_BROADCAST
        eth.payload = arp_req

        msg = of.ofp_packet_out()
        msg.data = eth.pack()
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(msg)
        log_color(CYAN, f"ARP Request enviado: ¿quién tiene la IP {ip_target}?")

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
        nw_proto = match.nw_proto

        if match.dl_type != 0x800 or nw_proto not in (ipv4.TCP_PROTOCOL, ipv4.UDP_PROTOCOL):
            return

        if match.nw_src is not None and match.nw_src.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):
            src_ip = match.nw_src
            private_port = match.tp_src
            key = (nw_proto, src_ip, private_port)
            if key in self.nat_table:
                public_port = self.nat_table.pop(key)
                self.used_ports.add((nw_proto, public_port))
                log_color(YELLOW, f"LIMPIEZA: Puerto público {public_port} liberado.")

    def handle_ip(self, event):
        packet = event.parsed
        ip_pkt = packet.payload
        in_port = event.port

        log_color(
            YELLOW, f"RECIBIDO: {ip_pkt.srcip} → {ip_pkt.dstip} | "
            f"MAC: {packet.src} → {packet.dst} | In Port: {in_port}")

        dst_ip = ip_pkt.dstip

        # Si no conocemos la MAC pausamos y preguntamos
        if dst_ip not in self.arp_table:
            log_color(YELLOW, f"MAC desconocida para {dst_ip}. Encolando paquete y mandando ARP Request")
            if dst_ip not in self.pending:
                self.pending[dst_ip] = []
            self.pending[dst_ip].append(event)

            if dst_ip.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):
                self.send_arp_request(dst_ip, PRIVATE_IP, PRIVATE_MAC, of.OFPP_FLOOD)
            else:
                self.send_arp_request(dst_ip, PUBLIC_IP, PUBLIC_MAC, PUBLIC_PORT)
            return
        dst_mac = self.arp_table[dst_ip]

        transport_pkt = ip_pkt.next
        nw_proto = ip_pkt.protocol

        # paquete saliente
        if ip_pkt.srcip.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):
            log_color(GREEN, f"MATCH: {ip_pkt.srcip} pertenece a la red privada {PRIVATE_SUBNET}/{PRIVATE_MASK}")

            if nw_proto in (ipv4.TCP_PROTOCOL, ipv4.UDP_PROTOCOL):
                private_port = transport_pkt.srcport
                key = (nw_proto, ip_pkt.srcip, private_port)
                # asignar puerto publico
                if key in self.nat_table:
                    public_port = self.nat_table[key]
                else:
                    public_port = self._get_public_port(nw_proto, private_port)
                    if public_port is None:
                        log_color(RED, "DROP: No hay puertos públicos disponibles")
                        return
                    self.nat_table[key] = public_port
                log_color(GREEN, f"NAT SALIENTE: {ip_pkt.srcip}:{private_port} → {PUBLIC_IP}:{public_port}")

                # Instalar Flujo Saliente
                fm = of.ofp_flow_mod()
                fm.idle_timeout = NAT_TIMEOUT
                fm.flags = of.OFPFF_SEND_FLOW_REM
                # Filtro (Saliente)
                fm.match.dl_type = 0x800
                fm.match.nw_src = ip_pkt.srcip
                fm.match.nw_dst = ip_pkt.dstip
                fm.match.nw_proto = nw_proto
                fm.match.tp_src = private_port
                fm.match.tp_dst = transport_pkt.dstport
                fm.match.in_port = in_port
                # Acción (Saliente)
                fm.actions.append(of.ofp_action_dl_addr.set_src(PUBLIC_MAC))
                fm.actions.append(of.ofp_action_dl_addr.set_dst(dst_mac))
                fm.actions.append(of.ofp_action_nw_addr.set_src(PUBLIC_IP))
                fm.actions.append(of.ofp_action_tp_port.set_src(public_port))
                fm.actions.append(of.ofp_action_output(port=PUBLIC_PORT))
                self.connection.send(fm)

                # Instalar Flujo Entrante (para respuesta)
                fm_back = of.ofp_flow_mod()
                fm_back.idle_timeout = NAT_TIMEOUT
                fm_back.flags = of.OFPFF_SEND_FLOW_REM
                # Filtro (Entrante)
                fm.match.dl_type = 0x800
                fm.match.nw_src = ip_pkt.srcip
                fm.match.nw_dst = ip_pkt.dstip
                fm.match.nw_proto = nw_proto
                fm.match.tp_src = private_port
                fm.match.tp_dst = transport_pkt.dstport
                fm_back.match.in_port = PUBLIC_PORT
                # Acción (Entrante)
                fm_back.actions.append(of.ofp_action_dl_addr.set_src(PRIVATE_MAC))
                fm_back.actions.append(of.ofp_action_dl_addr.set_dst(packet.src))
                fm_back.actions.append(of.ofp_action_nw_addr.set_dst(ip_pkt.srcip))
                fm_back.actions.append(of.ofp_action_tp_port.set_dst(transport_pkt.srcport))
                fm_back.actions.append(of.ofp_action_output(port=in_port))
                self.connection.send(fm_back)

                packet.src = PUBLIC_MAC
                packet.dst = dst_mac
                msg = of.ofp_packet_out()
                msg.data = packet.pack()
                msg.actions.append(of.ofp_action_output(port=PUBLIC_PORT))
                log_color(CYAN,
                          f"ENVIANDO: {ip_pkt.srcip} → {ip_pkt.dstip} | MAC: {PUBLIC_MAC} → {dst_mac} | Out Port: {PUBLIC_PORT}")
                self.connection.send(msg)
            else:
                return
        else:
            log_color(RED, f"NO MATCH: {ip_pkt.srcip} no pertenece a {PRIVATE_SUBNET}/{PRIVATE_MASK}")


def launch():

    def start_switch(event):
        log_color(YELLOW, f"Iniciando ProtoRouter para Switch {event.connection.dpid}")
        ProtoRouter(event.connection)

    core.openflow.addListenerByName("ConnectionUp", start_switch)
