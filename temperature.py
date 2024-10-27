import paho.mqtt.client as mqtt
import time
import random

BROKER_ADDRESS = "10.0.0.5"
BROKER_PORT = 1883
TOPIC = "iot/sensor/collect"

client = mqtt.Client()

client.connect(BROKER_ADDRESS, BROKER_PORT)

def read_temperature():
    return round(random.uniform(20.0, 30.0), 2)

try:
    while True:
        temperature = read_temperature()
        client.publish(TOPIC, temperature)
        print(f"Temperatura publicada: {temperature} °C")
        time.sleep(1)

except KeyboardInterrupt:
    print("Publicação interrompida pelo usuário.")

client.disconnect()
