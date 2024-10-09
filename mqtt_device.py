import logging
import paho.mqtt.client as mqtt
import time
import random
import psutil

BROKER = "mosquitto"  # Nome do serviço Docker do broker
PORT = 1883
TOPIC = "iot/sensor/temperature"
TOPIC_RESPONSE = "iot/sensor/response"  # Tópico onde o dispositivo recebe a resposta
TOPIC_LATENCY = "iot/sensor/latency"
TOPIC_BANDWIDTH = "iot/sensor/bandwidth"
TOPIC_CPU = "iot/sensor/cpu"

connected = False
start_time = None  # Variável para medir a latência

# Função para simular a temperatura
def get_temperature():
    return round(random.uniform(10.0, 40.0), 2)

# Função para medir o uso de CPU
def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

# Função para medir o uso de memória
def get_memory_usage():
    memory = psutil.virtual_memory()
    return memory.percent

# Função para calcular a largura de banda
def calculate_bandwidth(bytes_sent, bytes_received, interval):
    total_data = bytes_sent + bytes_received
    bandwidth = total_data / interval  # Em bytes por segundo
    return bandwidth

# Callbacks MQTT
def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        print("Connected to MQTT Broker!")
        connected = True
        client.subscribe(TOPIC_RESPONSE)  # Se inscreve no tópico de resposta
        print(f"Subscribed to {TOPIC_RESPONSE}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    print("Disconnected from MQTT Broker")

def on_publish(client, userdata, mid):
    global start_time
    print(f"Message {mid} published.")
    start_time = time.time()  # Inicia a medição de latência ao publicar a mensagem

def on_message(client, userdata, message):
    global start_time
    end_time = time.time()  # Medição de latência termina ao receber resposta
    latency = (end_time - start_time) * 1000  # Latência em milissegundos
    print(f"Latência medida: {latency:.2f} ms")
    client.publish(TOPIC_LATENCY, latency)  # Publica a latência no tópico

# Configurar logging detalhado
logging.basicConfig(level=logging.DEBUG)

# Configurando o cliente MQTT
client = mqtt.Client()

# Definindo callbacks
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish
client.on_message = on_message

# Tentativa de conexão
print(f"Connecting to broker {BROKER} on port {PORT}...")
client.connect(BROKER, PORT)

# Loop para manter a conexão ativa
client.loop_start()

# Espera até a conexão ser estabelecida
while not connected:
    print("Waiting for connection...")
    time.sleep(1)

# Publicando leituras de temperatura, latência, CPU e largura de banda
try:
    while True:
        # Publica a temperatura somente se fora do intervalo [15, 30]
        temperature = get_temperature()
        if temperature < 15 or temperature > 30:
            print(f"Sending temperature: {temperature}°C")
            result = client.publish(TOPIC, temperature)
            result.wait_for_publish()  # Garante que a mensagem foi publicada

        # Coleta e publica o uso de CPU
        cpu_usage = get_cpu_usage()
        result = client.publish(TOPIC_CPU, cpu_usage)
        result.wait_for_publish()
        print(f"Uso de CPU: {cpu_usage}% publicado no tópico {TOPIC_CPU}")

        # Calcula e publica a largura de banda
        current_sent = psutil.net_io_counters().bytes_sent
        current_received = psutil.net_io_counters().bytes_recv
        current_time = time.time()
        interval = current_time - start_time
        bandwidth = calculate_bandwidth(current_sent, current_received, interval)
        result = client.publish(TOPIC_BANDWIDTH, bandwidth)
        result.wait_for_publish()
        print(f"Largura de Banda: {bandwidth} Bps publicado no tópico {TOPIC_BANDWIDTH}")

        # Aguardar antes da próxima medição
        time.sleep(10)

except KeyboardInterrupt:
    print("Exiting...")
finally:
    client.loop_stop()  # Para o loop de background
    client.disconnect()  # Desconecta do broker MQTT