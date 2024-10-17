# Dockerfile para o dispositivo IoT
FROM python:3.9-slim

WORKDIR /app

# Instalar pacotes de rede e clientes Mosquitto como mosquitto_pub e mosquitto_sub
RUN apt-get update && apt-get install -y iputils-ping curl net-tools iproute2 mosquitto-clients

# Instalar a biblioteca Paho MQTT para Python
RUN pip install --no-cache-dir --upgrade requests psutil paho-mqtt

# Copiar o script para o container
COPY mqtt_device.py ./

# Executar o script diretamente ao iniciar o container
CMD ["python", "/app/mqtt_device.py"]