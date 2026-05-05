import sys
import os
import time
from time import perf_counter
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSController

class LinearTopology(Topo):
    def build(self):
        client = self.addHost('client')
        server = self.addHost('server')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        self.addLink(client, s1)
        self.addLink(s1, s2, loss=10)
        self.addLink(server, s2)


def run(mode, protocol, file):
    net = Mininet(topo=LinearTopology(), link=TCLink, controller=OVSController)
    net.start()

    client = net.get('client')
    server = net.get('server')

    filename = os.path.basename(file)

    server.cmd(
        f'python3 ../start_server.py -H {server.IP()} -p 8000 -s ../storage -q &'
    )

    storage_path = "../storage"
    final_path = os.path.join(storage_path, filename)

    start = perf_counter()

    if mode == "upload":
        client.cmd(
            f'python3 ../upload.py -H {server.IP()} -p 8000 -s {file} -n {filename} -r {protocol}'
        )

    elif mode == "download":
        client.cmd(
            f'python3 ../download.py -H {server.IP()} -p 8000 -n {filename} -r {protocol}'
        )

    total_time = perf_counter() - start

    while not os.path.exists(final_path):
        time.sleep(0.1)

    net.stop()
    return total_time

if __name__ == '__main__':
    mode = sys.argv[1]
    protocol = sys.argv[2]
    file = sys.argv[3]

    t = run(mode, protocol, file)
    print(f'Time to completion: {t} sec')