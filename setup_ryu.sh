#!/bin/bash

# Cria a rede Docker com o subnet especificado
docker network create --subnet=10.0.0.0/24 containernet-network

# Executa o container do Ryu Controller na rede criada
docker run -d --name ryu-controller --net containernet-network --ip 10.0.0.220 -p 6633:6633 ryu-controller

# Executa o docker-compose para subir o cAdvisor em segundo plano
docker-compose -f cadvisor-docker-compose.yml up -d

# Inspeciona a rede criada para verificar detalhes dos containers
docker network inspect containernet-network

# Exibe uma mensagem de sucesso
echo "Rede 'containernet-network' criada, container 'ryu-controller' e cAdvisor em execução."
