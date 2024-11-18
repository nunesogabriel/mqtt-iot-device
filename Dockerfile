# Dockerfile para o dispositivo IoT
FROM python:3.9-slim

WORKDIR /app

ENV PATH="/usr/sbin:/sbin:${PATH}"

RUN apt-get update && apt-get install -y \
    iptables \
    stress-ng \
    procps \
    iputils-ping \
    curl \
    net-tools \
    iproute2 \
    mosquitto-clients \
    iperf3 \
    ethtool && \
    rm -rf /var/lib/apt/lists/*  # Limpeza para reduzir o tamanho da imagem

RUN pip install --no-cache-dir --upgrade requests psutil paho-mqtt

COPY mqtt_device.py ./

CMD ["python", "/app/mqtt_device.py"]