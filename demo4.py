from mininet.net import Containernet
from mininet.cli import CLI
from mininet.link import TCLink, Intf
from mininet.log import info, setLogLevel
from mininet.node import RemoteController, Docker
import os
import time
import subprocess
import redis
import docker
import uuid

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
s1 = net.addSwitch('s1', protocols="OpenFlow13")

net.build()
c0.start()
s1.start([c0])

s1.cmd("ovs-vsctl set Bridge s1 protocols=OpenFlow13")

# Constrói e inicia a rede
subprocess.run(['ip', 'link', 'add', 's1-docker', 'type', 'veth', 'peer', 'name', 'docker-s1'])
subprocess.run(['ip', 'link', 'add', 'host-s1', 'type', 'veth', 'peer', 'name', 's1-host'])
subprocess.run(['ip', 'link', 'set', 'host-s1', 'up'])
subprocess.run(['ip', 'link', 'set', 's1-host', 'up'])
subprocess.run(['ip', 'link', 'set', 'host-s1', 'nomaster'])
# _intf = Intf('s1-host', node=s1)

# Configurando IP no host
subprocess.run(['ip', 'addr', 'add', '10.0.0.220/24', 'dev', 'host-s1'])

s1.cmd('ovs-vsctl add-port s1 s1-host')
s1.cmd('ovs-vsctl add-port s1 s1-docker')

subprocess.run(['ip', 'link', 'set', 's1-docker', 'up'])
subprocess.run(['ip', 'link', 'set', 'docker-s1', 'up'])

Intf('s1-docker', node=s1)

client = docker.from_env()
network = client.networks.get('containernet-network')

# Obtém o nome da ponte com um valor padrão
bridge_name = network.attrs['Options'].get('com.docker.network.bridge.name', 'default_bridge_name')

# Verifica se o nome da ponte foi encontrado ou se está usando o valor padrão
if bridge_name != 'default_bridge_name':
    print(f"Bridge name found: {bridge_name}")
else:
    # Caso não encontre o nome da ponte nas opções, constrói o nome baseado no ID da rede
    network_id = network.id[:12]  # Usa os primeiros 12 caracteres do ID
    bridge_name = f"br-{network_id}"
    print(f"Bridge name not found in options, assuming default naming convention: {bridge_name}")

subprocess.run(['brctl', 'addif', bridge_name, 'docker-s1'])
# Adicionando containers Mosquitto e dispositivos MQTT
info('*** Adding server and client container\n')

print("Adicionando o Mosquitto broker à rede...")
mosq = net.addDocker('mosq', dimage="custom-mosquitto",
                     dcmd="sh -c 'mosquitto -c /mosquitto/config/mosquitto.conf && tail -f /dev/null'",
                     volumes=["/home/desktop-udi-302/mqtt-iot-device/mosquitto/config:/mosquitto/config"],
                    #  network_mode='containernet-network',
                     network_mode="none",
                     cpu_quota=400000,
                     mem_limit="512m")
print("Mosquitto adicionado com sucesso.")

# Configuração de dispositivos MQTT
print("Adicionando dispositivos MQTT à rede...")
mqtt_devices = []
# ips = ['10.0.0.70/24', '10.0.0.71/24', '10.0.0.72/24', '10.0.0.73/24', '10.0.0.74/24', '10.0.0.75/24', '10.0.0.76/24', '10.0.0.77/24', '10.0.0.78/24', '10.0.0.79/24']
# for i, ip in enumerate(ips, start=1):
#     mqtt = net.addDocker(f'mqtt{i}',
#                         #  ip=ip,
#                          dimage="mqtt-iot-device-mqtt-device",
#                          dcmd="bash -c 'python /app/mqtt_device.py && while true; do sha256sum /dev/zero; done'",
#                         #  network_mode='containernet-network',
#                          cpu_quota=50000,
#                          network_mode="none",
#                          environment={"DEVICE_ID": str(uuid.uuid4())},
#                          mem_limit="256m")
#     mqtt_devices.append(mqtt)
# print("Dispositivos MQTT adicionados com sucesso.")

ips = ['10.0.0.70/24', '10.0.0.71/24', '10.0.0.72/24']
for i, ip in enumerate(ips, start=1):
    mqtt = net.addDocker(f'mqtt{i}',
                        #  ip=ip,
                         dimage="mqtt-iot-device-mqtt-device",
                         dcmd="bash -c 'python /app/mqtt_device.py && while true; do sha256sum /dev/zero; done'",
                        #  network_mode='containernet-network',
                         cpu_quota=150000,
                         network_mode="none",
                         environment={"DEVICE_ID": str(uuid.uuid4())},
                         mem_limit="256m")
    mqtt_devices.append(mqtt)
print("Dispositivos MQTT adicionados com sucesso.")

# Adicionando o Camel Router
print("Adicionando Camel Router")
# camel = net.addDocker('camel',
#                     #    ip='10.0.0.241/24',
#                        dimage="iot-router-backend",
#                        network_mode="none",
#                     #    network_mode='containernet-network',
#                        dcmd="bash -c 'sleep 60 && java -Dspring.profiles.active=dev -jar /app/iot-router-backend.jar'")
# print("Camel router adicionado com sucesso.")

# Adicionando container gerador
gerador = net.addDocker('gerador',
                        # ip='10.0.0.151/24',
                        dimage="gerador",
                        network_mode="none",
                        cpu_quota=50000,
                        # network_mode='containernet-network',
                        dcmd="bash -c 'python /app/temperature.py && while true; do sha256sum /dev/zero; done'")

fetch = net.addDocker('ip-fetcher',
                        # ip='10.0.0.149',
                        dimage="container-ip-fetcher",
                        ports=[5000],
                        port_bindings={5000: 5000},
                        cap_add=['NET_ADMIN'],
                        network_mode="none",
                        cpu_quota=50000,
                        # network_mode='containernet-network',
                        volumes=['/var/run/docker.sock:/var/run/docker.sock'],
                        dcmd="bash -c 'python /app/get_container_ips.py && while true; do sha256sum /dev/zero; done'")

redis_container = net.addDocker('redis',
                                dimage="my-redis",
                                # ip='10.0.0.250/24',
                                dcmd="redis-server /usr/local/etc/redis/redis.conf",
                                volumes=["/home/desktop-udi-302/mqtt-iot-device/redis/redis.conf:/usr/local/etc/redis/redis.conf", "/home/desktop-udi-302/mqtt-iot-device/appendonly:/data"])
net.addLink(redis_container, s1)
  
# Espera para estabilização dos containers
time.sleep(15)

# Conectando Mosquitto ao switch
net.addLink(mosq, s1)

# Conectando dispositivos MQTT ao switch com configurações de largura de banda e latência
for mqtt in mqtt_devices:
    # net.addLink(mqtt, s1, cls=TCLink, bw=10)
    net.addLink(mqtt, s1)
    info(f'*** Linked {mqtt.name} to switch s1\n')

# Conectando Camel Router e Gerador com largura de banda de 100 Mbps
# net.addLink(camel, s1)
net.addLink(gerador, s1)
net.addLink(fetch, s1)

redis_container.setIP('10.0.0.250/24', intf='redis-eth0')
mosq.setIP('10.0.0.237/24', intf='mosq-eth0')
# camel.setIP('10.0.0.241/24', intf='camel-eth0')
gerador.setIP('10.0.0.151/24', intf='gerador-eth0')
fetch.setIP('10.0.0.149/24', intf='ip-fetcher-eth0')

# ips = ['10.0.0.70/24', '10.0.0.71/24', '10.0.0.72/24', '10.0.0.73/24', '10.0.0.74/24', '10.0.0.75/24', '10.0.0.76/24', '10.0.0.77/24', '10.0.0.78/24', '10.0.0.79/24']
ips = ['10.0.0.70/24', '10.0.0.71/24', '10.0.0.72/24']
for mqtt, ip in zip(mqtt_devices, ips):
    mqtt.setIP(ip, intf=f'{mqtt.name}-eth0')

info('*** Starting to execute commands\n')

# containers = [mosq, camel, gerador, fetch] + mqtt_devices
containers = [mosq, fetch, gerador, redis_container] + mqtt_devices

redis_container.cmd("ip route add 10.0.0.250 dev redis-eth0")
redis_container.cmd(f"ip route add default dev {redis_container.name}-eth0")

RYU_INTERNAL_IP = '10.0.0.220'

for container in containers:
    container_name = container.name
    # Remover qualquer rota padrão existente
    container.cmd("ip route del default || true")
    # Adicionar rota para o Ryu via interface conectada ao switch
    container.cmd(f"ip route add {RYU_INTERNAL_IP} dev {container_name}-eth0")
    # Adicionar rota para a rede 10.0.0.0/24 via interface conectada ao switch
    container.cmd(f"ip route add 10.0.0.0/24 dev {container_name}-eth0")

    container.cmd(f"ip route add 172.20.0.0/16 via 10.0.0.220 dev {container_name}-eth0")

print(redis_container.IP())  # Confirme o IP real do Redis container
redis_client = redis.Redis(host='10.0.0.250', port=6379)

print("Recover containers")
for name, node in net.nameToNode.items():
    if isinstance(node, Docker) and "mqtt" in name:
        ip_address = node.IP()
        container_name = name
        aux = 'mn.' + container_name
        container_env = node.dcli.inspect_container(aux)["Config"]["Env"]

        # Converte as variáveis de ambiente para um dicionário
        env_dict = {env.split('=')[0]: env.split('=')[1] for env in container_env}
        
        # Armazena os dados no Redis
        redis_data = {
            "name": container_name,
            "ip": ip_address,
            **env_dict  # Adiciona as variáveis de ambiente como campos
        }

        redis_client.hset(f"container:{container_name}", mapping=redis_data)
        print(f"Container {container_name} armazenado no Redis com IP {ip_address}")

CLI(net)

# Parando a rede após a CLI
net.stop()