from mininet.net import Containernet
from mininet.cli import CLI
from mininet.link import TCLink, Intf
from mininet.log import info, setLogLevel
from mininet.node import RemoteController, Docker
import os
import time
import subprocess

# Limpeza de interfaces pré-existentes
os.system('sudo ip link delete s1-eth2 || true')
os.system('sudo ip link delete s2-eth1 || true')

# Definindo o nível de log
setLogLevel('debug')

# Inicializando a rede Containernet com um controlador remoto
net = Containernet(controller=RemoteController, ipBase='10.0.0.0/24', waitConnected=True)

# Adicionando controlador Ryu
info('*** Adding Ryu Controller\n')
c0 = net.addController('c0', controller=RemoteController, ip='172.17.0.2', port=6633)

# Configurando e adicionando switch
info('*** Setup network\n')
s1 = net.addSwitch('s1')

net.build()
c0.start()
s1.start([c0])

# Constrói e inicia a rede
subprocess.run(['ip', 'link', 'add', 'host-s1', 'type', 'veth', 'peer', 'name', 's1-host'])
subprocess.run(['ip', 'link', 'set', 'host-s1', 'up'])
subprocess.run(['ip', 'link', 'set', 's1-host', 'up'])
subprocess.run(['ip', 'link', 'set', 'host-s1', 'nomaster'])
# _intf = Intf('s1-host', node=s1)

# Configurando IP no host
subprocess.run(['ip', 'addr', 'add', '10.0.0.220/24', 'dev', 'host-s1'])

s1.cmd('ovs-vsctl add-port s1 s1-host')

# Adicionando containers Mosquitto e dispositivos MQTT
info('*** Adding server and client container\n')

print("Adicionando o Mosquitto broker à rede...")
mosq = net.addDocker('mosq', dimage="custom-mosquitto",
                     dcmd="sh -c 'mosquitto -c /mosquitto/config/mosquitto.conf && tail -f /dev/null'",
                     volumes=["/home/desktop-udi-302/mqtt-iot-device/mosquitto/config:/mosquitto/config"],
                    #  network_mode='containernet-network',
                     network_mode="none",
                     cpu_quota=50000,
                     mem_limit="256m")
print("Mosquitto adicionado com sucesso.")

# Configuração de dispositivos MQTT
print("Adicionando dispositivos MQTT à rede...")
mqtt_devices = []
ips = ['10.0.0.238/24', '10.0.0.239/24', '10.0.0.240/24', '10.0.0.190/24', '10.0.0.191/24', '10.0.0.192/24']
for i, ip in enumerate(ips, start=1):
    mqtt = net.addDocker(f'mqtt{i}',
                        #  ip=ip,
                         dimage="mqtt-iot-device-mqtt-device",
                         dcmd="bash -c 'python /app/mqtt_device.py && while true; do sha256sum /dev/zero; done'",
                        #  network_mode='containernet-network',
                         cpu_quota=150000,
                         network_mode="none",
                         mem_limit="256m")
    mqtt_devices.append(mqtt)
print("Dispositivos MQTT adicionados com sucesso.")

# Adicionando o Camel Router
print("Adicionando Camel Router")
routbe = net.addDocker('routbe',
                    #    ip='10.0.0.241/24',
                       dimage="iot-router-backend",
                       network_mode="none",
                    #    network_mode='containernet-network',
                       dcmd="bash -c 'sleep 60 && java -Dspring.profiles.active=dev -jar /app/iot-router-backend.jar'")
print("Camel router adicionado com sucesso.")

# Adicionando container gerador
gerador = net.addDocker('gerador',
                        # ip='10.0.0.151/24',
                        dimage="gerador",
                        network_mode="none",
                        # network_mode='containernet-network',
                        dcmd="bash -c 'python /app/temperature.py && while true; do sha256sum /dev/zero; done'")

fetch = net.addDocker('ip-fetcher',
                        # ip='10.0.0.149',
                        dimage="container-ip-fetcher",
                        ports=[5000],
                        port_bindings={5000: 5000},
                        cap_add=['NET_ADMIN'],
                        network_mode="none",
                        # network_mode='containernet-network',
                        volumes=['/var/run/docker.sock:/var/run/docker.sock'],
                        dcmd="bash -c 'python /app/get_container_ips.py && while true; do sha256sum /dev/zero; done'")

# Espera para estabilização dos containers
time.sleep(5)

# Conectando Mosquitto ao switch
net.addLink(mosq, s1)

# Conectando dispositivos MQTT ao switch com configurações de largura de banda e latência
for mqtt in mqtt_devices:
    net.addLink(mqtt, s1)
    info(f'*** Linked {mqtt.name} to switch s1\n')

# Conectando Camel Router e Gerador com largura de banda de 100 Mbps
net.addLink(routbe, s1)
net.addLink(gerador, s1)
net.addLink(fetch, s1)

mosq.setIP('10.0.0.237/24', intf='mosq-eth0')
routbe.setIP('10.0.0.241/24', intf='routbe-eth0')
gerador.setIP('10.0.0.151/24', intf='gerador-eth0')
fetch.setIP('10.0.0.149/24', intf='ip-fetcher-eth0')

ips = ['10.0.0.238/24', '10.0.0.239/24', '10.0.0.240/24', '10.0.0.190/24', '10.0.0.191/24', '10.0.0.192/24']
for mqtt, ip in zip(mqtt_devices, ips):
    mqtt.setIP(ip, intf=f'{mqtt.name}-eth0')

# mosq.cmd("ip addr del 172.17.0.3/8 dev mosq-eth0")
# mosq.cmd("ip addr add 10.0.0.237/24 dev mosq-eth0")
# mosq.cmd("ip link set eth0 down")
# routbe.cmd("ip link set eth0 down")
# gerador.cmd("ip link set eth0 down")
# fetch.cmd("ip link set eth0 down")

# for mqtt in mqtt_devices:
#     mqtt.cmd("ip link set eth0 down")

# Configurando controle de qualidade para os dispositivos MQTT
# for mqtt in mqtt_devices:
#     mqtt.cmd('tc qdisc add dev eth0 root netem delay 150ms 20ms loss 2%')

# Configurando servidor iperf3 no primeiro dispositivo e clientes nos demais
info('*** Starting to execute commands\n')
# mqtt_devices[0].cmd('iperf3 -s &')

# for mqtt in mqtt_devices[1:]:
#     mqtt.cmd('iperf3 -c 10.0.0.7 -u -b 50M -t 0 &')

# Iniciando CLI para interação e monitoramento

containers = [mosq, routbe, gerador, fetch] + mqtt_devices

RYU_INTERNAL_IP = '10.0.0.220'

for container in containers:
    container_name = container.name
    # Remover qualquer rota padrão existente
    container.cmd("ip route del default || true")
    # Adicionar rota para o Ryu via interface conectada ao switch
    container.cmd(f"ip route add {RYU_INTERNAL_IP} dev {container_name}-eth0")
    # Adicionar rota para a rede 10.0.0.0/24 via interface conectada ao switch
    container.cmd(f"ip route add 10.0.0.0/24 dev {container_name}-eth0")

# mosq.cmd(f"ip route add {RYU_INTERNAL_IP} dev {mosq.name}-eth0")
# routbe.cmd(f"ip route add {RYU_INTERNAL_IP} dev {routbe.name}-eth0")
# gerador.cmd(f"ip route add {RYU_INTERNAL_IP} dev {gerador.name}-eth0")
# fetch.cmd(f"ip route add {RYU_INTERNAL_IP} dev {fetch.name}-eth0")

# for mqtt in mqtt_devices:
#     mqtt.cmd(f"ip route add {RYU_INTERNAL_IP} dev {mqtt.name}-eth0")

CLI(net)

# Parando a rede após a CLI
net.stop()
