# Dockerfile para o dispositivo IoT
FROM python:3.9-slim

WORKDIR /app

# Instalar a biblioteca Paho MQTT para Python
RUN pip install --no-cache-dir --upgrade requests psutil paho-mqtt

# Copiar o script para o container
COPY mqtt_device.py http_device.py ./

# Executar o script quando o container iniciar
CMD ["sh", "-c", "python ${DEVICE_SCRIPT}"]