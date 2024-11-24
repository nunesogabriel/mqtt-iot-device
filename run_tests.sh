#!/bin/bash

# Lista de comandos para automação
commands=(
    "mn.mqtt1 mqtt1-eth0 212 60"
    "mn.mqtt2 mqtt2-eth0 208 60"
    "mn.mqtt3 mqtt3-eth0 102 60"
    "mn.mqtt4 mqtt4-eth0 38 60"
    "mn.mqtt5 mqtt5-eth0 21 60"
)

# Função para aplicar a configuração
apply_tc_in_container() {
    local container=$1
    local interface=$2
    local value=$3
    local duration=$4

    tc_command="tc qdisc add dev $interface root netem delay ${value}ms"
    echo "Executando no contêiner $container: $tc_command"
    docker exec "$container" sh -c "$tc_command"

    # Agendar a remoção da configuração após o tempo definido
    (
        sleep "$duration"
        echo "Removendo configuração do contêiner $container na interface $interface..."
        docker exec "$container" sh -c "tc qdisc del dev $interface root" 2>/dev/null || echo "Nenhuma configuração de tc encontrada para a interface $interface no contêiner $container."
    ) &
}

# Automação para a opção 1
echo "=== Automação: Adicionar latência ==="
for cmd in "${commands[@]}"; do
    # Dividir os parâmetros
    read container interface value duration <<< "$cmd"

    # Aplicar configuração
    apply_tc_in_container "$container" "$interface" "$value" "$duration"
done

echo "Automação concluída!"