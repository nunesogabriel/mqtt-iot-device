#!/bin/bash

# Função para exibir o menu
show_menu() {
    echo "=== Gerenciamento de Condições de Rede com tc em Contêineres ==="
    echo "1) Adicionar latência"
    echo "2) Adicionar perda de pacotes"
    echo "3) Adicionar jitter"
    echo "4) Latência flutuante"
    echo "5) Limpar configurações"
    echo "6) Sair"
    echo -n "Escolha uma opção: "
}

# Função para aplicar regras de tc dentro do contêiner
apply_tc_in_container() {
    local container=$1
    local action=$2
    local interface=$3
    local value=$4
    local duration=$5

    # Montar o comando tc
    case $action in
        latency)
            tc_command="tc qdisc add dev $interface root netem delay ${value}ms"
            ;;
        loss)
            tc_command="tc qdisc add dev $interface root netem loss $value%"
            ;;
        jitter)
            tc_command="tc qdisc add dev $interface root netem delay 50ms ${value}ms"
            ;;
    esac

    echo "Executando no contêiner $container: $tc_command"
    docker exec "$container" sh -c "$tc_command"

    # Agendar a remoção da configuração após o tempo definido
    (
        sleep "$duration"
        echo "Removendo configuração do contêiner $container na interface $interface..."
        docker exec "$container" sh -c "tc qdisc del dev $interface root" 2>/dev/null || echo "Nenhuma configuração de tc encontrada para a interface $interface no contêiner $container."
    ) &
}

# Função para limpar configurações de tc dentro do contêiner
clear_tc_in_container() {
    local container=$1
    local interface=$2
    echo "Limpando configurações de tc no contêiner $container na interface $interface..."
    docker exec "$container" sh -c "tc qdisc del dev $interface root" 2>/dev/null || echo "Nenhuma configuração de tc encontrada para a interface $interface no contêiner $container."
}

# Função para aplicar latência flutuante
apply_fluctuating_latency() {
    local container=$1
    local interface=$2
    local latency1=$3
    local latency2=$4
    local interval=$5
    local duration=$6

    echo "Iniciando latência flutuante no contêiner $container (alternando entre ${latency1}ms e ${latency2}ms a cada ${interval}s por $duration segundos)..."

    # Função em segundo plano para alternar as latências
    (
        end_time=$((SECONDS + duration))
        while [ $SECONDS -lt $end_time ]; do
            echo "Aplicando ${latency1}ms no contêiner $container..."
            docker exec "$container" sh -c "tc qdisc change dev $interface root netem delay ${latency1}ms" 2>/dev/null || \
            docker exec "$container" sh -c "tc qdisc add dev $interface root netem delay ${latency1}ms"

            sleep "$interval"

            echo "Aplicando ${latency2}ms no contêiner $container..."
            docker exec "$container" sh -c "tc qdisc change dev $interface root netem delay ${latency2}ms"

            sleep "$interval"
        done

        echo "Removendo configuração de latência flutuante no contêiner $container..."
        docker exec "$container" sh -c "tc qdisc del dev $interface root" 2>/dev/null || echo "Nenhuma configuração de tc encontrada para a interface $interface no contêiner $container."
    ) &
}

# Loop principal
while true; do
    show_menu
    read option

    case $option in
        1) # Adicionar latência
            read container interface value duration
            apply_tc_in_container "$container" "latency" "$interface" "$value" "$duration"
            ;;
        2) # Adicionar perda de pacotes
            read container interface value duration
            apply_tc_in_container "$container" "loss" "$interface" "$value" "$duration"
            ;;
        3) # Adicionar jitter
            read container interface value duration
            apply_tc_in_container "$container" "jitter" "$interface" "$value" "$duration"
            ;;
        4) # Latência flutuante
            echo "Digite os parâmetros (container interface latência1 latência2 intervalo duração):"
            read container interface latency1 latency2 interval duration
            apply_fluctuating_latency "$container" "$interface" "$latency1" "$latency2" "$interval" "$duration"
            ;;
        5) # Limpar configurações
            read container interface
            clear_tc_in_container "$container" "$interface"
            ;;
        6) # Sair
            echo "Saindo..."
            exit 0
            ;;
        *) # Opção inválida
            echo "Opção inválida. Tente novamente."
            ;;
    esac
done