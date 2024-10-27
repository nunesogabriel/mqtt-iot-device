import logging
import paho.mqtt.client as mqtt
import time
import psutil
import json 
import threading 

BROKER = "10.0.0.5" 
PORT = 1883
TOPIC_COLLECT = "iot/sensor/collect"
TOPIC = "iot/sensor/temperature"
TOPIC_RESPONSE = "iot/sensor/response"  
TOPIC_LATENCY = "iot/sensor/latency"
TOPIC_BANDWIDTH = "iot/sensor/bandwidth"
TOPIC_CPU = "iot/sensor/cpu"

connected = False
start_time = time.time() 

temperature = None 


def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

def calculate_bandwidth(bytes_sent, bytes_received, interval):
    total_data = bytes_sent + bytes_received
    bandwidth_bps = (total_data / interval) * 8  # Convertendo para bits por segundo
    if bandwidth_bps >= 1_000_000:
        return round(bandwidth_bps / 1_000_000, 2), "Mbps"
    else:
        return round(bandwidth_bps / 1000, 2), "kbps"

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        print("Connected to MQTT Broker!")
        connected = True
        client.subscribe(TOPIC_RESPONSE)  # Se inscreve no tópico de resposta
        client.subscribe(TOPIC_COLLECT)  # Se inscreve no tópico de coleta de temperatura
        print(f"Subscribed to {TOPIC_RESPONSE} and {TOPIC_COLLECT}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    print("Disconnected from MQTT Broker")

def on_publish(client, userdata, mid):
    print(f"Message {mid} published.")

# Callback para imprimir a mensagem recebida no tópico de resposta ou coleta
def on_message(client, userdata, message):
    global temperature
    if message.topic == TOPIC_COLLECT:
        temperature = float(message.payload.decode('utf-8'))
        print(f"Received temperature on {message.topic}: {temperature}")
    else:
        response_message = message.payload.decode('utf-8')
        print(f"Received message on {message.topic}: {response_message}")

logging.basicConfig(level=logging.DEBUG)

client = mqtt.Client()

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish
client.on_message = on_message

print(f"Connecting to broker {BROKER} on port {PORT}...")
client.connect(BROKER, PORT)

client.loop_start()

while not connected:
    print("Waiting for connection...")
    time.sleep(1)

def publish_data(client, thread_id):
    global start_time, temperature
    while True:
        current_time = time.time()
        interval = current_time - start_time

        if temperature is not None:
            print(f"Thread {thread_id}: Sending temperature: {temperature}°C")
            temperature_data = json.dumps({"temperature": temperature})
            result = client.publish(TOPIC, temperature_data)
            result.wait_for_publish()
        
        cpu_usage = get_cpu_usage()
        cpu_data = json.dumps({"cpu_usage": cpu_usage})
        result = client.publish(TOPIC_CPU, cpu_data)
        result.wait_for_publish()
        print(f"Thread {thread_id}: CPU Usage: {cpu_usage}%")

        current_sent = psutil.net_io_counters().bytes_sent
        current_received = psutil.net_io_counters().bytes_recv

        bandwidth, unit = calculate_bandwidth(current_sent, current_received, interval)
        bandwidth_data = json.dumps({"bandwidth": bandwidth, "unit": unit})
        result = client.publish(TOPIC_BANDWIDTH, bandwidth_data)
        result.wait_for_publish()
        print(f"Thread {thread_id}: Bandwidth: {bandwidth} {unit}")

        latency = round(interval * 1000, 2)
        latency_data = json.dumps({"latency": latency})
        result = client.publish(TOPIC_LATENCY, latency_data)
        result.wait_for_publish()
        print(f"Thread {thread_id}: Latency: {latency} ms")

        start_time = time.time()

        time.sleep(5)

def create_threads(num_threads, client):
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=publish_data, args=(client, i))
        threads.append(thread)
        thread.start()
    
NUM_THREADS = 20

create_threads(NUM_THREADS, client)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")

finally:
    client.loop_stop()
    client.disconnect()
