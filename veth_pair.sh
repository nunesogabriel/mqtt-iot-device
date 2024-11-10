#!/bin/bash

# Nome da rede Docker onde o Ryu está
DOCKER_NETWORK="containernet-network"

# Sub-rede para a qual será criada a rota
SUBNET="10.0.1.0/24"

# Verifica se o par de interfaces já existe e remove, se necessário
ip link show veth0 &> /dev/null
if [ $? -eq 0 ]; then
  echo "Removendo interfaces virtuais antigas..."
  sudo ip link delete veth0
fi

# Cria o par de interfaces virtuais veth
echo "Criando par de interfaces virtuais veth0 e veth1..."
sudo ip link add veth0 type veth peer name veth1

# Obtém o ID da bridge do Docker
BRIDGE_ID=$(docker network inspect -f '{{.Id}}' $DOCKER_NETWORK)
BRIDGE_NAME="br-${BRIDGE_ID:0:12}"

# Conecta veth0 à bridge do Docker
echo "Conectando veth0 à bridge do Docker $BRIDGE_NAME..."
sudo brctl addif $BRIDGE_NAME veth0

# Configura as interfaces
echo "Ativando interfaces veth..."
sudo ip link set veth0 up
sudo ip link set veth1 up

# Adiciona rota para a sub-rede especificada através de veth1
echo "Adicionando rota para $SUBNET via veth1..."
sudo ip route add $SUBNET dev veth1

echo "Configuração de veth concluída com sucesso."
