from mininet.net import Containernet
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import RemoteController, Docker
import os
import time

# Limpeza de interfaces pré-existentes
os.system('sudo ip link delete s1-eth2 || true')
os.system('sudo ip link delete s2-eth1 || true')

# Definindo o nível de log
setLogLevel('debug')

# Inicializando a rede Containernet com um controlador remoto
net = Containernet(controller=RemoteController, ipBase='10.0.0.0/24', waitConnected=True)

# Adicionando controlador Ryu
info('*** Adding Ryu Controller\n')
c0 = net.addController('c0', controller=RemoteController, ip='10.0.0.220', port=6633)

# Adicionando containers Mosquitto e dispositivos MQTT
info('*** Adding server and client container\n')

print("Adicionando o Mosquitto broker à rede...")
mosq = net.addDocker('mosq', ip='10.0.0.237/24', dimage="custom-mosquitto",
                     dcmd="sh -c 'mosquitto -c /mosquitto/config/mosquitto.conf && tail -f /dev/null'",
                     volumes=["/home/desktop-udi-302/mqtt-iot-device/mosquitto/config:/mosquitto/config"],
                     network_mode='containernet-network',
                     cpu_quota=50000,
                     mem_limit="256m")
print("Mosquitto adicionado com sucesso.")

# Configuração de dispositivos MQTT
print("Adicionando dispositivos MQTT à rede...")
mqtt_devices = []
ips = ['10.0.0.238/24', '10.0.0.239/24', '10.0.0.240/24', '10.0.0.190/24', '10.0.0.191/24', '10.0.0.192/24']
for i, ip in enumerate(ips, start=1):
    mqtt = net.addDocker(f'mqtt{i}',
                         ip=ip,
                         dimage="mqtt-iot-device-mqtt-device",
                         dcmd="bash -c 'python /app/mqtt_device.py && while true; do sha256sum /dev/zero; done'",
                         network_mode='containernet-network',
                         cpu_quota=150000,
                         mem_limit="256m")
    mqtt_devices.append(mqtt)
print("Dispositivos MQTT adicionados com sucesso.")

# Adicionando o Camel Router
print("Adicionando Camel Router")
routbe = net.addDocker('routbe',
                       ip='10.0.0.241/24',
                       dimage="iot-router-backend",
                       dcmd="java -Dspring.profiles.active=dev -jar /app/iot-router-backend.jar",
                       network_mode='containernet-network')
print("Camel router adicionado com sucesso.")

# Adicionando container gerador
gerador = net.addDocker('gerador',
                        ip='10.0.0.151/24',
                        dimage="gerador",
                        dcmd="bash -c 'python /app/temperature.py && while true; do sha256sum /dev/zero; done'",
                        network_mode='containernet-network')

fetch = net.addDocker('ip-fetcher',
                        ip='10.0.0.149',
                        dimage="container-ip-fetcher",
                        ports=[5000],
                        port_bindings={5000: 5000},
                        cap_add=['NET_ADMIN'],
                        network_mode='containernet-network',
                        volumes=['/var/run/docker.sock:/var/run/docker.sock'],
                        dcmd="bash -c 'python /app/get_container_ips.py && while true; do sha256sum /dev/zero; done'")

# Espera para estabilização dos containers
time.sleep(5)

# Configurando e adicionando switch
info('*** Setup network\n')
s1 = net.addSwitch('s1')

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

mosq.cmd("ip addr del 172.17.0.3/8 dev mosq-eth0")
mosq.cmd("ip addr add 10.0.0.237/24 dev mosq-eth0")
mosq.cmd("ip link set eth0 down")
routbe.cmd("ip link set eth0 down")
gerador.cmd("ip link set eth0 down")
fetch.cmd("ip link set eth0 down")

for mqtt in mqtt_devices:
    mqtt.cmd("ip link set eth0 down")

# Constrói e inicia a rede
net.build()
c0.start()
s1.start([c0])


# Iniciando o switch com o controlador
net.build()
c0.start()
s1.start([c0])

# Configurando controle de qualidade para os dispositivos MQTT
# for mqtt in mqtt_devices:
#     mqtt.cmd('tc qdisc add dev eth0 root netem delay 150ms 20ms loss 2%')

# Configurando servidor iperf3 no primeiro dispositivo e clientes nos demais
info('*** Starting to execute commands\n')
# mqtt_devices[0].cmd('iperf3 -s &')

# for mqtt in mqtt_devices[1:]:
#     mqtt.cmd('iperf3 -c 10.0.0.7 -u -b 50M -t 0 &')

# Iniciando CLI para interação e monitoramento
CLI(net)

# Parando a rede após a CLI
net.stop()
