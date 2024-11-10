from mininet.net import Containernet
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import RemoteController, OVSSwitch
import time

setLogLevel('debug')

# Inicializando a rede Containernet com um controlador remoto
net = Containernet(controller=RemoteController, ipBase='10.0.0.0', waitConnected=True)

# Adicionando o controlador Ryu
info('*** Adding Ryu Controller\n')
c0 = net.addController('c0', controller=RemoteController, ip='172.17.0.1', port=6633)

# Adicionando o Mosquitto broker
info('*** Adding Mosquitto Broker\n')
mosq = net.addDocker('mosq', ip='10.0.0.237', dimage="custom-mosquitto",
                     dcmd="sh -c 'mosquitto -c /mosquitto/config/mosquitto.conf && tail -f /dev/null'",
                     volumes=["/home/desktop-udi-302/mqtt-iot-device/mosquitto/config:/mosquitto/config"],
                    #  network_mode='containernet-network',
                     cpu_quota=50000,
                     cap_add=['NET_ADMIN'],
                     mem_limit="256m")

# Adicionando dispositivos MQTT
info('*** Adding MQTT Devices\n')
mqtt_devices = []
# ips = ['10.0.0.238', '10.0.0.239', '10.0.0.240', '10.0.0.190', '10.0.0.191', '10.0.0.192']
ips = ['10.0.0.238']
for i, ip in enumerate(ips, start=1):
    mqtt = net.addDocker(f'mqtt{i}', ip=ip, dimage="mqtt-iot-device-mqtt-device",
                         dcmd="bash -c 'python /app/mqtt_device.py && while true; do sha256sum /dev/zero; done'",
                        #  network_mode='containernet-network',
                         cpu_quota=150000,
                         cap_add=['NET_ADMIN'],
                         mem_limit="256m")
    mqtt_devices.append(mqtt)

# Adicionando o Camel Router
info('*** Adding Camel Router\n')
routbe = net.addDocker('routbe', ip='10.0.0.241', dimage="iot-router-backend",
                       dcmd="java -Dspring.profiles.active=dev -jar /app/iot-router-backend.jar",
                       cap_add=['NET_ADMIN'])

# Adicionando container gerador
info('*** Adding Temperature Generator\n')
gerador = net.addDocker('gerador', ip='10.0.0.151', dimage="gerador",
                        dcmd="bash -c 'python /app/temperature.py && while true; do sha256sum /dev/zero; done'",
                        cap_add=['NET_ADMIN'])

fetch = net.addDocker('ip-fetcher',
                        ip='10.0.0.149',
                        dimage="container-ip-fetcher",
                        ports=[5000],
                        port_bindings={5000: 5000},
                        cap_add=['NET_ADMIN'],
                        volumes=['/var/run/docker.sock:/var/run/docker.sock'],
                        dcmd="bash -c 'python /app/get_container_ips.py && while true; do sha256sum /dev/zero; done'")

# Tempo de estabilização para todos os containers
time.sleep(5)

# Configuração da rede e adição do switch
info('*** Setting up network and adding switch\n')
s1 = net.addSwitch('s1')  # Definindo o suporte ao OpenFlow 1.3 para o switch

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
mosq.cmd("ip addr add 10.0.0.237 dev mosq-eth0")
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

# Espera para que as interfaces estejam completamente ativas
time.sleep(5)

# Configura IPs com máscara de sub-rede  para todos os dispositivos
# info('*** Configuring IPs with  subnet mask\n')
# mosq.cmd("ip link set dev eth0 down")
# mosq.cmd("ip addr flush dev eth0")
# mosq.cmd("ip addr flush dev mosq-eth0")
# mosq.cmd("ip addr add 172.17.0.3 dev mosq-eth0")

# for i, mqtt in enumerate(mqtt_devices, start=1):
#     mqtt.cmd("ip link set dev eth0 down")
#     mqtt.cmd("ip addr flush dev eth0")  # Limpa IPs residuais de eth0
#     mqtt.cmd(f"ip addr flush dev mqtt{i}-eth0")
#     mqtt.cmd(f"ip addr add {ips[i-1]} dev mqtt{i}-eth0")

# routbe.cmd("ip link set dev eth0 down")
# routbe.cmd("ip addr flush dev eth0")
# routbe.cmd("ip addr flush dev routbe-eth0")
# routbe.cmd("ip addr add 10.0.0.241 dev routbe-eth0")

# gerador.cmd("ip link set dev eth0 down")
# gerador.cmd("ip addr flush dev eth0")
# gerador.cmd("ip addr flush dev gerador-eth0")
# gerador.cmd("ip addr add 10.0.0.151 dev gerador-eth0")

# Configura servidor iperf3 no primeiro dispositivo e clientes nos demais
info('*** Starting iperf3 server and clients\n')
# mqtt_devices[0].cmd('iperf3 -s &')

# for mqtt in mqtt_devices[1:]:
#     mqtt.cmd(f'iperf3 -c {mqtt_devices[0].IP()} -u -b 50M -t 0 &')

# Iniciando a CLI para interação e monitoramento
info('*** Starting CLI\n')
CLI(net)

# Parando a rede após a CLI
info('*** Stopping network\n')
net.stop()