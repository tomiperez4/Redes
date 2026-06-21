import pox.openflow.libopenflow_01 as of
from tp2.config import NAT_TIMEOUT, PUBLIC_MAC, PUBLIC_IP, PRIVATE_MAC, PUBLIC_PORT

def install_flow():
    fm = of.ofp_flow_mod()
    fm.idle_timeout = NAT_TIMEOUT
    fm.flags = of.OFPFF_SEND_FLOW_REM
    return fm

def set_outbound_match(fm, ip_pkt, nw_proto, private_port, transport_pkt, in_port):
    fm.match.dl_type = 0x800
    fm.match.nw_src = ip_pkt.srcip
    fm.match.nw_dst = ip_pkt.dstip
    fm.match.nw_proto = nw_proto
    fm.match.tp_src = private_port
    fm.match.tp_dst = transport_pkt.dstport
    fm.match.in_port = in_port

def set_inbound_match(fm, ip_pkt, nw_proto, transport_pkt, public_port):
    fm.match.dl_type = 0x800
    fm.match.nw_src = ip_pkt.dstip
    fm.match.nw_dst = PUBLIC_IP
    fm.match.nw_proto = nw_proto
    fm.match.tp_src = transport_pkt.dstport
    fm.match.tp_dst = public_port
    fm.match.in_port = PUBLIC_PORT

def set_outbound_actions(fm, dst_mac, public_port):
    fm.actions.append(of.ofp_action_dl_addr.set_src(PUBLIC_MAC))
    fm.actions.append(of.ofp_action_dl_addr.set_dst(dst_mac))
    fm.actions.append(of.ofp_action_nw_addr.set_src(PUBLIC_IP))
    fm.actions.append(of.ofp_action_tp_port.set_src(public_port))
    fm.actions.append(of.ofp_action_output(port=PUBLIC_PORT))

def set_inbound_actions(fm, src_mac, src_ip, private_port, in_port):
    fm.actions.append(of.ofp_action_dl_addr.set_src(PRIVATE_MAC))
    fm.actions.append(of.ofp_action_dl_addr.set_dst(src_mac))
    fm.actions.append(of.ofp_action_nw_addr.set_dst(src_ip))
    fm.actions.append(of.ofp_action_tp_port.set_dst(private_port))
    fm.actions.append(of.ofp_action_output(port=in_port))

def setup_nat_flows(connection, ip_pkt, nw_proto, private_port, transport_pkt, in_port, dst_mac, public_port, packet):
    fm = install_flow()
    set_outbound_match(fm, ip_pkt, nw_proto, private_port, transport_pkt, in_port)
    set_outbound_actions(fm, dst_mac, public_port)

    fm_back = install_flow()
    set_inbound_match(fm_back, ip_pkt, nw_proto, transport_pkt, public_port)
    set_inbound_actions(fm_back, packet.src, ip_pkt.srcip, private_port, in_port)

    connection.send(fm)
    connection.send(fm_back)