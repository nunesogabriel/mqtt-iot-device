import paho.mqtt.client as mqtt
import time
import random

BROKER_ADDRESS = "10.0.0.237"
BROKER_PORT = 1883
TOPIC = "iot/sensor/collect"

client = mqtt.Client()

client.reconnect_delay_set(min_delay=1, max_delay=10)

connected = False

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        print("Conectado ao broker MQTT.")
        connected = True
    else:
        print(f"Falha na conexão com o broker, código: {rc}")

def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    print(f"Desconectado do broker MQTT, código: {rc}. Tentando reconectar...")

def connect_to_broker():
    global connected
    while not connected:
        try:
            print(f"Tentando conectar ao broker MQTT em {BROKER_ADDRESS}:{BROKER_PORT}...")
            client.connect(BROKER_ADDRESS, BROKER_PORT, keepalive=120)
            client.loop_start()
            time.sleep(2)
        except Exception as e:
            print(f"Erro ao conectar ao broker: {e}. Tentando novamente em 5 segundos...")
            time.sleep(5)

def read_temperature():
    return round(random.uniform(20.0, 30.0), 2)

client.on_connect = on_connect
client.on_disconnect = on_disconnect

connect_to_broker()

try:
    while True:
        if connected:
            temperature = read_temperature()
            client.publish(TOPIC, temperature)
            print(f"Temperatura publicada: {temperature} °C")
        else:
            print("Aguardando reconexão...")
            connect_to_broker() 
        time.sleep(4)

except KeyboardInterrupt:
    print("Publicação interrompida pelo usuário.")

finally:
    client.loop_stop()
    client.disconnect()