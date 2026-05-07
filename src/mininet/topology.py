from mininet.link import TCLink
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import OVSController


class LinearTopology(Topo):
    def build(self):
        client = self.addHost('client')
        server = self.addHost('server')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        self.addLink(client, s1)
        self.addLink(s1, s2)
        self.addLink(server, s2)


if __name__ == '__main__':
    net = Mininet(topo=LinearTopology(), link=TCLink, controller=OVSController)
    net.start()
    CLI(net)
    net.stop()