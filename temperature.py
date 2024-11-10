import paho.mqtt.client as mqtt
import time
import random

BROKER_ADDRESS = "10.0.0.237"
BROKER_PORT = 1883
TOPIC = "iot/sensor/collect"

client = mqtt.Client()

def connect_to_broker():
    while True:
        try:
            client.connect(BROKER_ADDRESS, BROKER_PORT)
            print("Conectado ao broker MQTT.")
            break
        except Exception as e:
            print(f"Falha ao conectar ao broker: {e}. Tentando novamente em 5 segundos...")
            time.sleep(5)

def read_temperature():
    return round(random.uniform(20.0, 30.0), 2)

# Tenta conectar até que o broker fique online
connect_to_broker()

try:
    while True:
        temperature = read_temperature()
        client.publish(TOPIC, temperature)
        print(f"Temperatura publicada: {temperature} °C")
        time.sleep(1)

except KeyboardInterrupt:
    print("Publicação interrompida pelo usuário.")

client.disconnect()