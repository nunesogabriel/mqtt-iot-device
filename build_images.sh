#!/bin/bash

echo "Building mqtt-iot-device-mqtt-device image..."
docker build -t mqtt-iot-device-mqtt-device -f Dockerfile .
if [ $? -eq 0 ]; then
    echo "Successfully built mqtt-iot-device-mqtt-device image."
else
    echo "Failed to build mqtt-iot-device-mqtt-device image."
    exit 1
fi

echo "Building custom-mosquitto image..."
docker build -t custom-mosquitto -f Dockerfile.mosquitto .
if [ $? -eq 0 ]; then
    echo "Successfully built custom-mosquitto image."
else
    echo "Failed to build custom-mosquitto image."
    exit 1
fi

echo "Building ryu-controller image..."
docker build -t ryu-controller -f Dockerfile.ryu .
if [ $? -eq 0 ]; then
    echo "Successfully built ryu-controller image."
else
    echo "Failed to build ryu-controller image."
    exit 1
fi

echo "Building gerador image..."
docker build -t gerador -f Dockerfile.temperature .
if [ $? -eq 0 ]; then
    echo "Successfully built gerador image."
else
    echo "Failed to build gerador image."
    exit 1
fi

echo "Building ip-fetcher image..."
docker build -t container-ip-fetcher -f Dockerfile.ips .
if [ $? -eq 0 ]; then
    echo "Successfully built container-ip-fetcher image."
else
    echo "Failed to build container-ip-fetcher image."
    exit 1
fi

echo "Building Redis image..."
docker build -t my-redis -f Dockerfile.redis .
if [ $? -eq 0 ]; then
    echo "Successfully built my-redis image."
else
    echo "Failed to build my-redis image."
    exit 1
fi

echo "Building Redis image..."
docker build -t my-prom -f Dockerfile.prometheus .
if [ $? -eq 0 ]; then
    echo "Successfully built my-prom  image."
else
    echo "Failed to build my-prom  image."
    exit 1
fi
