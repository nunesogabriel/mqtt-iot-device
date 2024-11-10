from mininet.net import Containernet
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import RemoteController, Docker
import os
import time

# Removendo interfaces antigas, caso existam
os.system('sudo ip link delete s1-eth2 || true')
os.system('sudo ip link delete s2-eth1 || true')

setLogLevel('debug')

# Criação da rede simulada com Ryu como controlador remoto
net = Containernet(controller=RemoteController)

# Configurando o controlador remoto (Ryu) com IP e porta definidos
info('*** Adding Ryu Controller\n')
c0 = net.addController('c0', controller=RemoteController, ip='10.0.0.220', port=6633)

# Adicionando containers e dispositivos
info('*** Adding server and client containers\n')

# Dispositivo MQTT (Mosquitto Broker)
mosq = net.addDocker('mosq', ip='172.17.0.3', dimage="custom-mosquitto",
                     dcmd="sh -c 'mosquitto -c /mosquitto/config/mosquitto.conf && tail -f /dev/null'",
                     volumes=["/home/desktop-udi-302/mqtt-iot-device/mosquitto/config:/mosquitto/config"],
                     network_mode='containernet-network',
                     cpu_quota=50000,
                     mem_limit="256m")
print("Mosquitto adicionado com sucesso.")

# Dispositivos MQTT simulados
mqtt_devices = []
ips = ['10.0.0.238', '10.0.0.239', '10.0.0.240', '10.0.0.190', '10.0.0.191', '10.0.0.192']
for i, ip in enumerate(ips, start=1):
    mqtt = net.addDocker(f'mqtt{i}', ip=ip,
                         dimage="mqtt-iot-device-mqtt-device",
                         dcmd="bash -c 'python /app/mqtt_device.py && while true; do sha256sum /dev/zero; done'",
                         network_mode='containernet-network',
                         cpu_quota=150000,
                         mem_limit="256m")
    mqtt_devices.append(mqtt)
print("Dispositivos MQTT adicionados com sucesso.")

# Adicionando o roteador de mensagens Camel
routbe = net.addDocker('routbe', ip='10.0.0.241',
                       dimage="iot-router-backend",
                       dcmd="java -Dspring.profiles.active=dev -jar /app/iot-router-backend.jar",
                       network_mode='containernet-network')
print("Camel router adicionado com sucesso.")

# Dispositivo gerador de dados
gerador = net.addDocker('gerador', ip='10.0.0.151', dimage="gerador",
                        dcmd="bash -c 'python /app/temperature.py && while true; do sha256sum /dev/zero; done'",
                        network_mode='containernet-network')

# Setup da rede com redundância e links alternativos
info('*** Setup network with redundancy\n')

# Adicionando switches e links redundantes
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')
s3 = net.addSwitch('s3')  # Switch de backup

# Links redundantes e balanceamento
net.addLink(s1, s2, cls=TCLink, bw=50, delay='100ms', loss=1, jitter='10ms')
net.addLink(s1, s3, cls=TCLink, bw=100, delay='150ms', loss=2, jitter='20ms')
net.addLink(s2, s3, cls=TCLink, bw=50, delay='50ms', jitter='5ms')

# Conectando os containers ao switch com redundância
net.addLink(mosq, s1)
net.addLink(routbe, s1, cls=TCLink, bw=100)
net.addLink(gerador, s1, cls=TCLink, bw=100)

# Conectar os dispositivos MQTT ao switch com largura de banda e latência configurada
for mqtt in mqtt_devices:
    # Cada dispositivo conecta a um switch com uma latência/limite diferente para simular caminhos alternativos
    if mqtt.name in ['mqtt1', 'mqtt2', 'mqtt3']:
        net.addLink(mqtt, s2, cls=TCLink, bw=50, delay='120ms', jitter='15ms')
    else:
        net.addLink(mqtt, s3, cls=TCLink, bw=50, delay='180ms', jitter='25ms')

# Configuração de latência e perda de pacotes nos dispositivos MQTT usando `tc`
for mqtt in mqtt_devices:
    mqtt.cmd('tc qdisc add dev eth0 root netem delay 150ms 20ms loss 2%')

# Iniciando a rede
net.start()

# Configurações adicionais para simulação de failover e balanceamento
info('*** Starting traffic simulation\n')
mqtt_devices[0].cmd('iperf3 -s &')

# Gerando tráfego nos dispositivos restantes
for mqtt in mqtt_devices[1:]:
    mqtt.cmd('iperf3 -c 172.17.0.3 -u -b 50M -t 0 &')

# Iniciando o CLI para monitoramento e teste de failover
CLI(net)
net.stop()