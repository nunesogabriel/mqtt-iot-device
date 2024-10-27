#!/bin/bash

# Para parar e remover todos os containers
docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)

# Para remover redes e volumes não utilizados
docker network prune -f
docker network ls
docker volume prune -f

# Para remover todas as imagens, exceto cAdvisor e Prometheus
docker images | grep -v 'gcr.io/cadvisor/cadvisor\|prom/prometheus' | awk '{if (NR!=1) print $3}' | xargs docker rmi -f

# Para remover interfaces de rede específicas
sudo ip link delete s1-eth1
sudo ip link delete mosq-eth0
sudo ip link delete mqtt-eth0
# Remova quaisquer outras interfaces criadas
# sudo ip link delete <outra-interface>

# Para remover bridges OVS
sudo ovs-vsctl del-br s1
sudo ovs-vsctl del-br s2
# Remova quaisquer outras bridges criadas
# sudo ovs-vsctl del-br <outra-bridge>

# Reiniciar o serviço Docker
sudo systemctl restart docker

# Limpeza do Mininet
sudo mn -c