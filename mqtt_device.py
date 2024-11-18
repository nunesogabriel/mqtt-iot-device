import logging
import paho.mqtt.client as mqtt
import time
import json
import threading
import os
import sys
import requests
import uuid
from queue import Queue, Empty

# Configuração do Broker e Tópicos
BROKER = "10.0.0.237"  # Altere para o IP correto do broker
PORT = 1883
TOPIC_COLLECT = "iot/sensor/collect"
TOPIC = "iot/sensor/temperature"
API_IPS = "http://10.0.0.149:5000/get_ips"
API_PROMETHEUS = "http://10.0.0.99:8000"

# Variáveis Globais e Configurações
connected = False
temperature = None
collect_interval = 5  # Intervalo de coleta em segundos
device_id = os.getenv("DEVICE_ID", f"device-{uuid.uuid4().hex[:8]}")

# Fila para Publicação
publish_queue = Queue()

# Lock para sincronizar o acesso à variável global
lock = threading.Lock()

# Configuração do Logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Função para obter o IP do container
def get_container_ip():
    """
    Consulta a API configurada para obter o IP do container associado ao DEVICE_ID.
    """
    while True:
        try:
            logger.info("Tentando conectar à API para DEVICE_ID %s...", device_id)
            response = requests.get(API_IPS, timeout=5)
            response.raise_for_status()

            devices = response.json()
            for device in devices:
                if device["device_id"] == device_id:
                    ip = device["ip"].replace(".", "")
                    logger.info("IP do container obtido: %s", ip)
                    return ip
            logger.warning("DEVICE_ID %s não encontrado na lista retornada pela API.", device_id)
        except requests.exceptions.RequestException as e:
            logger.error("Erro ao consultar a API: %s", e)
            time.sleep(30)

# Obter o IP do container e configurar o tópico exclusivo
container_ip = get_container_ip()
TOPIC_COMMANDS = f"iot/sensor/control/{container_ip}"  # Tópico exclusivo para comandos

# Função para tratar conexões com o broker
def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
        connected = True
        client.subscribe(TOPIC_COLLECT)  # Inscrição no tópico de coleta
        client.subscribe(TOPIC_COMMANDS)  # Inscrição no tópico de comandos
        logger.info(f"Subscribed to {TOPIC_COLLECT} and {TOPIC_COMMANDS}")
    else:
        logger.error(f"Failed to connect to broker, return code {rc}")

def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    logger.warning(f"Disconnected from MQTT Broker with code {rc}")

# Função para tratar mensagens recebidas
def on_message(client, userdata, message):
    global temperature
    if message.topic == TOPIC_COLLECT:
        new_temperature = float(message.payload.decode('utf-8'))
        temperature = new_temperature
        try:
            publish_queue.put_nowait(new_temperature)  # Adiciona a temperatura na fila
            logger.info(f"Received temperature: {new_temperature}°C")
        except Queue.Full:
            logger.warning("Fila cheia! Ignorando nova temperatura.")
    elif message.topic == TOPIC_COMMANDS:
        command = json.loads(message.payload.decode('utf-8'))
        logger.info(f"Received command: {command}")
        handle_command(command)

# Função para tratar comandos recebidos
def handle_command(command):
    global collect_interval
    action = command.get("action")
    if action == "reduce_frequency":
        collect_interval = command.get("interval", collect_interval)
        logger.info(f"Reduced data collection interval to {collect_interval} seconds.")
    elif action == "restart":
        logger.info("Restart command received. Restarting...")
        os.execv(sys.executable, ['python'] + sys.argv)

# Função para publicar mensagens da fila
def publisher_thread(client):
    while True:
        try:
            temp = publish_queue.get(timeout=10)  # Aguarda e pega a próxima mensagem da fila
            temperature_data = json.dumps({"container_ip": container_ip, "temperature": temp})
            
            # Publica a mensagem
            result = client.publish(TOPIC, temperature_data, qos=1)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.warning(f"Erro ao publicar mensagem: {mqtt.error_string(result.rc)}")
            else:
                logger.info(f"Published temperature: {temp}°C to topic {TOPIC}")

                try:
                    requests.post(f"{API_PROMETHEUS}/increment")
                    requests.post(f"{API_PROMETHEUS}/set_interval", json={"interval": collect_interval, "ip": container_ip})
                except requests.exceptions.RequestException as e:
                    logger.error(f"Erro ao atualizar métricas Prometheus: {e}")
                
            time.sleep(collect_interval)
        except Empty:
            logger.debug("Fila vazia, aguardando mensagens.")
        except Exception as e:
            logger.error(f"Erro inesperado ao publicar mensagem: {e}")

def monitor_connection(client):
    while True:
        if client.is_connected():
            logger.info("Cliente está conectado ao broker.")
        else:
            logger.warning("Cliente desconectado do broker.")
        time.sleep(10)

# Função principal para conectar ao broker e gerenciar o loop MQTT
def main():
    global connected

    client = mqtt.Client(client_id=device_id, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Configuração de reconexão automática
    client.reconnect_delay_set(min_delay=1, max_delay=10)

    try:
        logger.info(f"Connecting to MQTT broker at {BROKER}:{PORT}...")
        client.connect(BROKER, PORT, 60)

        # Inicia a thread para publicação
        threading.Thread(target=publisher_thread, args=(client,), daemon=True).start()
        threading.Thread(target=monitor_connection, args=(client,), daemon=True).start()

        # Mantém o loop MQTT ativo
        client.loop_start()

        # Mantém a aplicação rodando
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Exiting...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
