# Import some POX stuff
from pox.core import core                       # Main POX object
import pox.openflow.libopenflow_01 as of        # OpenFlow 1.0 library
from pox.lib.addresses import EthAddr, IPAddr   # Address types
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.ethernet import ETHER_BROADCAST
from pox.lib.packet.arp import arp

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

class ProtoRouter(object):
    def __init__(self, connection):
        self.connection = connection
        self.arp_table = {}
        self.pending = {}
        connection.addListeners(self)

    def _handle_PacketIn(self, event):
        if not event.parsed.parsed:
            log.warning("[DROP] PacketIn con trama no reconocida. POX no pudo decodificar el paquete.")
            return
        if event.parsed.type == ethernet.ARP_TYPE:
            self.handle_arp(event)

        if event.parsed.type == ethernet.IP_TYPE:
            self.handle_ip(event)
        else:
            log_color(YELLOW, f"Paquete ignorado: protocolo distinto de IPv4.")

    def handle_arp(self, event):
        eth = event.parsed
        arp_pkt = eth.payload

        # Aprender la MAC del que pregunta (siempre)
        self.arp_table[arp_pkt.protosrc] = arp_pkt.hwsrc
        log_color(CYAN, f"ARP aprendido: {arp_pkt.protosrc} -> {arp_pkt.hwsrc}")

        if arp_pkt.opcode == arp.REQUEST:
            # ¿Es para alguna de nuestras IP?
            if arp_pkt.protodst == PRIVATE_IP:
                self.send_arp_reply(event, arp_pkt, PRIVATE_MAC)
            elif arp_pkt.protodst == PUBLIC_IP:
                self.send_arp_reply(event, arp_pkt, PUBLIC_MAC)
            else:
                log_color(YELLOW, f"ARP Request para {arp_pkt.protodst}, no es nuestro")

        elif arp_pkt.opcode == arp.REPLY:
            # Alguien respondió nuestro ARP Request — procesar pendientes
            ip = arp_pkt.protosrc
            if ip in self.pending:
                log_color(GREEN, f"ARP resuelto {ip} -> {arp_pkt.hwsrc}, procesando pendientes")
                for pending_event in self.pending.pop(ip):
                    self.handle_ip(pending_event)

    def send_arp_reply(self, event, arp_req, our_mac):
        """Responde un ARP Request con nuestra MAC."""
        arp_reply = arp()
        arp_reply.opcode = arp.REPLY
        arp_reply.hwsrc = our_mac
        arp_reply.hwdst = arp_req.hwsrc
        arp_reply.protosrc = arp_req.protodst  # nuestra IP
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
        """Manda un ARP Request para resolver una IP."""
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
        log_color(CYAN, f"ARP Request enviado: ¿quién tiene {ip_target}?")


    def handle_ip(self, event):
        packet = event.parsed
        ip_pkt = packet.payload
        in_port = event.port

        log_color(
            YELLOW, f"RECIBIDO: {ip_pkt.srcip} → {ip_pkt.dstip} | "
            f"MAC: {packet.src} → {packet.dst} | In Port: {in_port}")

        if ip_pkt.srcip.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):

            log_color(GREEN, f"MATCH: {ip_pkt.srcip} pertenece a la red privada {PRIVATE_SUBNET}/{PRIVATE_MASK}")
            dst_ip = ip_pkt.dstip
            if dst_ip not in self.arp_table:
                log_color(YELLOW, f"MAC de {dst_ip} desconocida, mandando ARP Request")
                if dst_ip not in self.pending:
                    self.pending[dst_ip] = []
                    self.send_arp_request(dst_ip, PUBLIC_IP, PUBLIC_MAC, PUBLIC_PORT)
                self.pending[dst_ip].append(event)
                return

            dst_mac = self.arp_table[dst_ip]
            log_color(GREEN, f"Procesando paquete saliente con destino MAC: {dst_mac}")

            # Instalar Flujo Saliente
            fm = of.ofp_flow_mod()
            fm.idle_timeout = 10

            # Filtro (Saliente)
            fm.match.nw_src = ip_pkt.srcip
            fm.match.dl_type = 0x800  # IPv4
            fm.match.in_port = in_port

            # Acción (Saliente)
            fm.actions.append(of.ofp_action_dl_addr.set_src(PUBLIC_MAC))
            fm.actions.append(of.ofp_action_dl_addr.set_dst(dst_mac))
            fm.actions.append(of.ofp_action_output(port=PUBLIC_PORT))
            self.connection.send(fm)

            # Instalar Flujo Entrante (para respuesta)
            fm_back = of.ofp_flow_mod()
            fm_back.idle_timeout = 10

            # Filtro (Entrante)
            fm_back.match.nw_src = ip_pkt.dstip
            fm_back.match.nw_dst = ip_pkt.srcip
            fm_back.match.dl_type = 0x800  # IPv4
            fm_back.match.in_port = PUBLIC_PORT

            # Acción (Entrante)
            fm_back.actions.append(of.ofp_action_dl_addr.set_src(PRIVATE_MAC))
            fm_back.actions.append(of.ofp_action_dl_addr.set_dst(packet.src))
            fm_back.actions.append(of.ofp_action_output(port=in_port))
            self.connection.send(fm_back)

            # Reenviar paquete actual con MACs actualizadas (Los posteriores pasan por flujo)
            packet.src = PUBLIC_MAC
            packet.dst = dst_mac
            msg = of.ofp_packet_out()
            msg.data = packet.pack()
            msg.actions.append(of.ofp_action_output(port=PUBLIC_PORT))
            log_color(CYAN, f"ENVIANDO: {ip_pkt.srcip} → {ip_pkt.dstip} | MAC: {PUBLIC_MAC} → {dst_mac} | Out Port: {PUBLIC_PORT}")
            self.connection.send(msg)

        else:
            log_color(RED, f"NO MATCH: {ip_pkt.srcip} no pertenece a {PRIVATE_SUBNET}/{PRIVATE_MASK}")


def launch():

    def start_switch(event):
        log_color(YELLOW, f"Iniciando ProtoRouter para Switch {event.connection.dpid}")
        ProtoRouter(event.connection)

    core.openflow.addListenerByName("ConnectionUp", start_switch)
