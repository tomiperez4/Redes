import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import EthAddr
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.ethernet import ETHER_BROADCAST
from pox.lib.packet.arp import arp
from ext.logger import *

class ArpHandler(object):
    def __init__(self, connection, our_addresses):
        self.connection = connection
        self.our_addresses = our_addresses  # {IPAddr: EthAddr} (IPs que el router responde)
        self.arp_table = {}                 # IPAddr -> EthAddr
        self.pending = {}                   # IPAddr -> [event, ...]
        self.on_resolved = None             # callback(event) invocado por cada pendiente

    def handle(self, event):
        """Procesa un paquete ARP: aprende MACs, responde requests y procesa replies"""
        eth = event.parsed
        arp_pkt = eth.payload

        # Aprender la MAC del que pregunta
        self.arp_table[arp_pkt.protosrc] = arp_pkt.hwsrc
        log_color(CYAN, f"ARP aprendido: {arp_pkt.protosrc} -> {arp_pkt.hwsrc}")

        if arp_pkt.opcode == arp.REQUEST:
            our_mac = self.our_addresses.get(arp_pkt.protodst)
            if our_mac:
                self.send_reply(event, arp_pkt, our_mac)
            else:
                log_color(YELLOW, f"ARP Request para {arp_pkt.protodst}, no es nuestro")

        elif arp_pkt.opcode == arp.REPLY:
            # Alguien respondió nuestro ARP Request, entonces procesamos pendientes
            ip = arp_pkt.protosrc
            if ip in self.pending:
                log_color(GREEN, f"ARP resuelto {ip} -> {arp_pkt.hwsrc}, procesando pendientes")
                events = self.pending.pop(ip)
                if self.on_resolved:
                    for pending_event in events:
                        self.on_resolved(pending_event)

    def resolve_or_queue(self, ip_target, src_ip, src_mac, out_port, event):
        """Si no se conoce la MAC correspondiente a ip_target, se encola el paquete y manda un ARP Request (una sola vez por IP)"""
        if ip_target not in self.pending:
            self.pending[ip_target] = []
            self.send_request(ip_target, src_ip, src_mac, out_port)
        self.pending[ip_target].append(event)

    def send_reply(self, event, arp_req, our_mac):
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

    def send_request(self, ip_target, src_ip, src_mac, out_port):
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