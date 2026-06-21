from pox.core import core                       # Main POX object
import pox.openflow.libopenflow_01 as of        # OpenFlow 1.0 library
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.ipv4 import ipv4
from tp2.logger import log_color, log, RED, GREEN, YELLOW, CYAN
from tp2.config import *
from tp2.arp_handler import ArpHandler
from tp2.nat_manager import NatManager
from tp2 import flow_manager


class ProtoRouter(object):
    def __init__(self, connection):
        self.connection = connection
        self.arp = ArpHandler(connection, {PRIVATE_IP: PRIVATE_MAC, PUBLIC_IP: PUBLIC_MAC})
        self.arp.on_resolved = self.handle_ip
        self.nat = NatManager()

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


    def _handle_FlowRemoved(self, event):
        self.nat.release_port_from_flow(event.ofp.match)

    def handle_ip(self, event):
        packet = event.parsed
        ip_pkt = packet.payload
        in_port = event.port

        log_color(
            YELLOW, f"RECIBIDO: {ip_pkt.srcip} → {ip_pkt.dstip} | "
            f"MAC: {packet.src} → {packet.dst} | In Port: {in_port}")

        dst_ip = ip_pkt.dstip

        # Si no conocemos la MAC pausamos y preguntamos
        if dst_ip not in self.arp.arp_table:
            log_color(YELLOW, f"MAC desconocida para {dst_ip}. Encolando paquete y mandando ARP Request")
            if dst_ip.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):
                self.arp.resolve_or_queue(dst_ip, PRIVATE_IP, PRIVATE_MAC, of.OFPP_FLOOD, event)
            else:
                self.arp.resolve_or_queue(dst_ip, PUBLIC_IP, PUBLIC_MAC, PUBLIC_PORT, event)
            return
        dst_mac = self.arp.arp_table[dst_ip]

        transport_pkt = ip_pkt.next
        nw_proto = ip_pkt.protocol

        # paquete saliente
        if ip_pkt.srcip.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):
            log_color(GREEN, f"MATCH: {ip_pkt.srcip} pertenece a la red privada {PRIVATE_SUBNET}/{PRIVATE_MASK}")

            if nw_proto in (ipv4.TCP_PROTOCOL, ipv4.UDP_PROTOCOL):
                private_port = transport_pkt.srcport
                public_port = self.nat.get_or_create_public_port(nw_proto, ip_pkt.srcip, private_port)

                if public_port is None:
                    log_color(RED, "DROP: No hay puertos públicos disponibles")
                    return

                log_color(GREEN, f"NAT SALIENTE: {ip_pkt.srcip}:{private_port} → {PUBLIC_IP}:{public_port}")

                flow_manager.setup_nat_flows(
                    self.connection, ip_pkt, nw_proto, private_port,
                    transport_pkt, in_port, dst_mac, public_port, packet
                )

                packet.src = PUBLIC_MAC
                packet.dst = dst_mac
                ip_pkt.srcip = PUBLIC_IP
                transport_pkt.srcport = public_port
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
