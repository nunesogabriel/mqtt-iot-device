from mininet.net import Containernet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.log import info

def setup_cpu_test_topology():
    # Criação da rede simulada com Ryu como controlador remoto
    net = Containernet(controller=RemoteController)

    # Configurando o controlador remoto (Ryu) com IP e porta definidos
    info('*** Adding Ryu Controller\n')
    c0 = net.addController('c0', controller=RemoteController, ip='10.0.0.220', port=6633)

    # Adicionando um switch central para interconexão dos dispositivos
    s1 = net.addSwitch('s1')
    s1.attach('veth1')

    # Configurações de Limite de CPU e Memória
    mosquitto_cpu_quota = 25000    # 25% de um núcleo
    mqtt_device_cpu_quota = 30000  # 30% de um núcleo
    gerador_cpu_quota = 40000      # 40% de um núcleo
    mem_limit = "128m"             # 128 MB de memória

    # Dispositivo MQTT (Mosquitto Broker) com limite de CPU e memória
    mosq = net.addDocker(
        'mosq',
        ip='172.17.0.3',
        dimage="custom-mosquitto",
        dcmd="sh -c 'mosquitto -c /mosquitto/config/mosquitto.conf && tail -f /dev/null'",
        volumes=["/home/desktop-udi-302/mqtt-iot-device/mosquitto/config:/mosquitto/config"],
        network_mode='containernet-network',
        cpu_quota=mosquitto_cpu_quota,
        mem_limit=mem_limit
    )
    net.addLink(mosq, s1, cls=TCLink)
    print("Mosquitto adicionado com sucesso.")

    # Dispositivos MQTT simulados com limites de CPU e memória
    mqtt_devices = []
    ips = ['10.0.0.238', '10.0.0.239', '10.0.0.240', '10.0.0.190', '10.0.0.191', '10.0.0.192']
    for i, ip in enumerate(ips, start=1):
        mqtt = net.addDocker(
            f'mqtt{i}',
            ip=ip,
            dimage="mqtt-iot-device-mqtt-device",
            dcmd="bash -c 'python /app/mqtt_device.py && while true; do openssl speed; done'",
            network_mode='containernet-network',
            cpu_quota=mqtt_device_cpu_quota,
            mem_limit=mem_limit
        )
        mqtt_devices.append(mqtt)
        net.addLink(mqtt, s1, cls=TCLink)
    print("Dispositivos MQTT adicionados com sucesso.")

    # Adicionando o roteador de mensagens Camel com limitações padrão
    routbe = net.addDocker(
        'routbe',
        ip='10.0.0.241',
        dimage="iot-router-backend",
        dcmd="java -Dspring.profiles.active=dev -jar /app/iot-router-backend.jar",
        network_mode='containernet-network'
    )
    net.addLink(routbe, s1, cls=TCLink)
    print("Camel router adicionado com sucesso.")

    # Dispositivo gerador de dados com limite de CPU e memória
    gerador = net.addDocker(
        'gerador',
        ip='10.0.0.151',
        dimage="gerador",
        dcmd="bash -c 'python /app/temperature.py && while true; do sha256sum /dev/zero; done'",
        network_mode='containernet-network',
        cpu_quota=gerador_cpu_quota,
        mem_limit=mem_limit
    )
    net.addLink(gerador, s1, cls=TCLink)
    print("Dispositivo gerador de dados adicionado com sucesso.")

    # Inicia a rede
    net.start()
    print("Rede iniciada para teste de CPU e memória com Ryu como controlador remoto. Aguardando...")

    # Mantém o script em execução para testes
    net.interact()

    # Para a rede após finalizar o teste
    net.stop()

if __name__ == '__main__':
    setup_cpu_test_topology()