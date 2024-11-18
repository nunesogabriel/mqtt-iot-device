#!/bin/bash

# Cria a rede Docker com o subnet especificado
NETWORK_NAME="containernet-network"
SUBNET="172.20.0.0/16"

# Verificar se a rede já existe
if docker network ls --filter "name=^${NETWORK_NAME}$" --format "{{.Name}}" | grep -qw "${NETWORK_NAME}"; then
    echo "A rede '${NETWORK_NAME}' já existe. Nenhuma ação será tomada."
else
    echo "A rede '${NETWORK_NAME}' não existe. Criando a rede..."
    docker network create --subnet="${SUBNET}" "${NETWORK_NAME}"
    if [ $? -eq 0 ]; then
        echo "Rede '${NETWORK_NAME}' criada com sucesso."
    else
        echo "Erro ao criar a rede '${NETWORK_NAME}'."
        exit 1
    fi
fi

# Executa o container do Ryu Controller na rede criada
# docker run -d --name ryu-controller --net containernet-network --ip 10.0.0.220 -p 6633:6633 -p 8080:8080 ryu-controller
# docker run -d --name ryu-controller --network host ryu-controller
docker run -d --name ryu_simple_switch -p 6633:6633 -p 8080:8080 ryu-controller

# Executa o docker-compose para subir o cAdvisor em segundo plano
docker-compose -f cadvisor-docker-compose.yml up -d

# Inspeciona a rede criada para verificar detalhes dos containers
docker network inspect containernet-network

# Exibe uma mensagem de sucesso
echo "Rede 'containernet-network' criada, container 'ryu-controller' e cAdvisor em execução."
