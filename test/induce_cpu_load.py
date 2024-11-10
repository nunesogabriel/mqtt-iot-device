import docker
import os

# Cria o cliente Docker
client = docker.from_env()

# Lista de containers alvo para aplicar a carga de CPU
# Você pode definir uma lista específica ou usar uma variável de ambiente com os nomes separados por vírgula
container_names = os.getenv("TARGET_CONTAINERS", "mn.mqtt1,mn.mqtt2,mn.mqtt3,mn.mqtt4,mn.mqtt5,mn.mqtt6").split(",")

# Função para induzir carga de CPU em múltiplos containers
def induce_cpu_load(containers, duration=30):
    for container_name in containers:
        try:
            container = client.containers.get(container_name.strip())
            print(f"Induzindo carga de CPU em {container_name} por {duration} segundos...")
            container.exec_run(f"stress-ng --cpu 1 --timeout {duration}s", detach=True)
            print(f"Carga de CPU iniciada em {container_name}.")
        except Exception as e:
            print(f"Erro ao tentar induzir carga de CPU em {container_name}: {e}")

# Definindo a duração (em segundos) para a carga de CPU
duration = 900  # 30 minutos

# Executa a carga de CPU nos containers especificados
induce_cpu_load(container_names, duration)