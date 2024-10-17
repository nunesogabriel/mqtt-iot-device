from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel
import os
import time

os.system('sudo ip link delete s1-eth2 || true')
os.system('sudo ip link delete s2-eth1 || true')

setLogLevel('debug')

# Criação da rede simulada
net = Containernet(controller=Controller)
net.addController('c0')

info('*** Adding server and client container\n')

# Adicionando o dispositivo IoT simulado à rede (Mosquitto)
print("Adicionando o Mosquitto broker a rede...")
mosq = net.addDocker('mosq', ip='10.0.0.237', dimage="custom-mosquitto",
                          dcmd="sh -c 'mosquitto -c /mosquitto/config/mosquitto.conf && tail -f /dev/null'",
                          volumes=["/home/desktop-udi-302/mqtt-iot-device/mosquitto/config:/mosquitto/config"])
time.sleep(15)
print("Mosquitto adicionado com sucesso.")

print("Adicionando mqtt device a rede...")
mqtt = net.addDocker('mqtt', 
                     ip='10.0.0.238', 
                     dimage="mqtt-iot-device-mqtt-device",
                     dcmd="python /app/mqtt_device.py")
print("mqtt device adicionado com sucesso.")

print("Adicionando camel-app")
routbe = net.addDocker('routbe', 
                       ip='10.0.0.239', 
                       dimage="iot-router-backend",
                       dcmd="java -Dspring.profiles.active=dev -jar /app/iot-router-backend.jar")
print("Camel-App adicionado com sucesso.")

info('*** Setup network\n')

# Adicionar switches
s1 = net.addSwitch('s1')

# Conectar o container 'mosq' ao switch s1
net.addLink(mosq, s1)
# Conectar o container 'mqtt_device' ao switch s1 com interfaces nomeadas corretamente
net.addLink(mqtt, s1)
# Conectar o container 'iot_router_backend' ao switch s1
net.addLink(routbe, s1)
net.start()
info('*** Starting to execute commands\n')
print("*** Testing connectivity")
# result = mqtt.cmd('ping -c 3 10.0.0.239')  # Ping do mqtt_device para o iot_router_backend
# print(result)
CLI(net)
net.stop()