import logging
import paho.mqtt.client as mqtt
import time
import json
import threading
import socket
import os
import sys

BROKER = "10.0.0.237"  # Altere para o IP correto do broker na rede Containernet
PORT = 1883
TOPIC_COLLECT = "iot/sensor/collect"
TOPIC = "iot/sensor/temperature"
TOPIC_RESPONSE = "iot/sensor/response"

connected = False
temperature = None
collect_interval = 5  # Intervalo de coleta padrão em segundos

# Função para obter o IP do container
def get_container_ip():
    try:
        container_ip = socket.gethostbyname(socket.gethostname()).replace(".", "_")
        return container_ip
    except Exception as e:
        print("Erro ao obter o IP do container:", e)
        return "unknown_ip"

# IP do container para uso nas publicações e no tópico de comandos
container_ip = get_container_ip()
TOPIC_COMMANDS = f"iot/sensor/control/{container_ip}"  # Tópico exclusivo para comandos

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        print("Connected to MQTT Broker!")
        connected = True
        client.subscribe(TOPIC_RESPONSE)
        client.subscribe(TOPIC_COLLECT)
        client.subscribe(TOPIC_COMMANDS)  # Inscrição no tópico exclusivo de comandos
        print(f"Subscribed to {TOPIC_RESPONSE}, {TOPIC_COLLECT}, and {TOPIC_COMMANDS}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    print("Disconnected from MQTT Broker")

def on_publish(client, userdata, mid):
    print(f"Message {mid} published.")

# Função para tratar mensagens de comando recebidas do orquestrador
def handle_command(command):
    global collect_interval
    action = command.get("action")

    if action == "reduce_frequency":
        collect_interval = command.get("interval", collect_interval)
        print(f"Reducing data collection frequency to {collect_interval} seconds.")
    elif action == "restart":
        print("Restart command received. Restarting device...")
        os.execv(sys.executable, ['python'] + sys.argv)  # Reinicia o script

def on_message(client, userdata, message):
    global temperature
    if message.topic == TOPIC_COLLECT:
        temperature = float(message.payload.decode('utf-8'))
        print(f"Received temperature on {message.topic}: {temperature}")
    elif message.topic == TOPIC_COMMANDS:
        # Decodifica e trata o comando recebido do orquestrador
        command = json.loads(message.payload.decode('utf-8'))
        print(f"Received command on {message.topic}: {command}")
        handle_command(command)  # Processa o comando
    else:
        response_message = message.payload.decode('utf-8')
        print(f"Received message on {message.topic}: {response_message}")

logging.basicConfig(level=logging.DEBUG)

client = mqtt.Client()

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish
client.on_message = on_message

# Função para aguardar a conexão com o broker MQTT indefinidamente
def wait_for_connection(client):
    global connected
    client.loop_start()
    while not connected:
        try:
            client.connect(BROKER, PORT)
            print(f"Connecting to broker {BROKER} on port {PORT}...")
            while not connected:
                print("Waiting for connection...")
                time.sleep(1)
        except Exception as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)  # Aguarda antes de tentar novamente

print(f"Attempting to connect to broker {BROKER} on port {PORT}...")
wait_for_connection(client)

def publish_temperature(client, thread_id):
    global temperature, collect_interval
    while True:
        if temperature is not None:
            print(f"Thread {thread_id}: Sending temperature: {temperature}°C")
            temperature_data = json.dumps({"container_ip": container_ip, "temperature": temperature})
            result = client.publish(TOPIC, temperature_data)
            result.wait_for_publish()
        
        time.sleep(collect_interval)  # Usa o intervalo de coleta configurado (modificável via comando)

def create_threads(num_threads, client):
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=publish_temperature, args=(client, i))
        threads.append(thread)
        thread.start()

NUM_THREADS = 3

create_threads(NUM_THREADS, client)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")

finally:
    client.loop_stop()
    client.disconnect()
