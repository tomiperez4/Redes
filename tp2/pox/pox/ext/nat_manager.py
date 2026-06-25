from ext.logger import log_color, log, YELLOW
from ext.config import MIN_PORT, MAX_PORT, PRIVATE_SUBNET, PRIVATE_MASK
from pox.lib.packet.ipv4 import ipv4

class NatManager(object):
    def __init__(self):
        self.nat_table = {}
        self.used_ports = set()

    def get_or_create_public_port(self, nw_proto, private_ip, private_port):
        """Asigna o reutiliza un puerto público para cierto paquete"""
        key = (nw_proto, private_ip, private_port)

        if key in self.nat_table:
            return self.nat_table[key]

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
                log.error("No hay puertos disponibles en el NAT")
                return None

        self.used_ports.add((nw_proto, port))
        self.nat_table[key] = port
        return port

    def release_port_from_flow(self, match):
        """Libera el puerto público cuando expira la regla OpenFlow."""
        nw_proto = match.nw_proto
        if match.dl_type != 0x800 or nw_proto not in (ipv4.TCP_PROTOCOL, ipv4.UDP_PROTOCOL):
            return

        if match.nw_src is not None and match.nw_src.inNetwork(PRIVATE_SUBNET, PRIVATE_MASK):
            src_ip = match.nw_src
            private_port = match.tp_src
            key = (nw_proto, src_ip, private_port)

            if key in self.nat_table:
                public_port = self.nat_table.pop(key)
                self.used_ports.remove((nw_proto, public_port))
                log_color(YELLOW, f"LIMPIEZA NAT: Puerto público {public_port} liberado.")