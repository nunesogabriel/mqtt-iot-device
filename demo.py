from mininet.net import Containernet
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import RemoteController, Docker
import os
import time

# Removendo interfaces antigas caso existam
os.system('sudo ip link delete s1-eth2 || true')
os.system('sudo ip link delete s2-eth1 || true')

setLogLevel('debug')

# Criação da rede simulada com Ryu como controlador remoto
net = Containernet(controller=RemoteController)

# Configurando o controlador remoto (Ryu) com IP e porta definidos
info('*** Adding Ryu Controller\n')
c0 = net.addController('c0', controller=RemoteController, ip='10.0.0.220', port=6633)

# time.sleep(15)

info('*** Adding server and client container\n')

# Adicionando o dispositivo IoT simulado à rede (Mosquitto)
print("Adicionando o Mosquitto broker a rede...")
mosq = net.addDocker('mosq', ip='10.0.0.237', dimage="custom-mosquitto",
                          dcmd="sh -c 'mosquitto -c /mosquitto/config/mosquitto.conf && tail -f /dev/null'",
                          volumes=["/home/desktop-udi-302/mqtt-iot-device/mosquitto/config:/mosquitto/config"],
                          network_mode='containernet-network',
                          cpu_quota=50000,
                          mem_limit="256m")
# time.sleep(15)
print("Mosquitto adicionado com sucesso.")

# Adicionando os dispositivos simulados MQTT
print("Adicionando dispositivos MQTT à rede...")
mqtt_devices = []
ips = ['10.0.0.238', '10.0.0.239', '10.0.0.240', '10.0.0.190', '10.0.0.191', '10.0.0.192']
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

# time.sleep(5)
print("Adicionando camel Router")
routbe = net.addDocker('routbe',
                       ip='10.0.0.241',
                       dimage="iot-router-backend",
                       dcmd="java -Dspring.profiles.active=dev -jar /app/iot-router-backend.jar",
                       network_mode='containernet-network')
print("Camel router adicionado com sucesso.")
# time.sleep(5)

gerador = net.addDocker(f'gerador',
                        ip='10.0.0.151',
                        dimage="gerador",
                        dcmd="bash -c 'python /app/temperature.py && while true; do sha256sum /dev/zero; done'",
                        network_mode='containernet-network')

time.sleep(5)
info('*** Setup network\n')
# Adicionar switches
s1 = net.addSwitch('s1')
os.system('sudo ovs-vsctl show')  # Para verificar se a bridge s1 foi criada
print(os.system('sudo ip netns list'))
time.sleep(2)

# Conectar o container 'mosq' ao switch s1
net.addLink(mosq, s1)
time.sleep(2)

# Conectar os dispositivos MQTT ao switch s1 com links limitados e latência simulada
for mqtt in mqtt_devices:
    net.addLink(mqtt, s1, cls=TCLink, bw=50, delay='100ms', jitter='20ms')  # Limitação de largura de banda e latência

# Conectar o container 'iot_router_backend' ao switch s1
net.addLink(routbe, s1, cls=TCLink, bw=100)  # Largura de banda de 100 Mbps para o roteador
net.addLink(gerador, s1, cls=TCLink, bw=100)
net.start()

# Adicionando latência e perda de pacotes nos dispositivos MQTT usando tc
for mqtt in mqtt_devices:
    mqtt.cmd('tc qdisc add dev eth0 root netem delay 150ms 20ms loss 2%')  # Adiciona atraso e perda de pacotes

info('*** Starting to execute commands\n')
mqtt_devices[0].cmd('iperf3 -s &')  # Primeiro dispositivo como servidor iperf3

# Os demais dispositivos geram tráfego
for mqtt in mqtt_devices[1:]:
    mqtt.cmd('iperf3 -c 10.0.0.6 -u -b 50M -t 0 &')  # Gera 50 Mbps continuamente para simular carga

CLI(net)
net.stop()
