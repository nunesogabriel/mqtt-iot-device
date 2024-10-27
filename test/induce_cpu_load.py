import docker
import os

client = docker.from_env()
container_name = os.getenv("TARGET_CONTAINER", "mn.mqtt1")  # Nome do container definido pela variável de ambiente

def induce_cpu_load(duration=30):
    try:
        container = client.containers.get(container_name)
        print(f"Induzindo carga de CPU em {container_name} por {duration} segundos...")
        container.exec_run(f"stress-ng --cpu 1 --timeout {duration}s")
        print(f"Carga de CPU finalizada em {container_name}.")
    except Exception as e:
        print(f"Erro ao tentar induzir carga de CPU em {container_name}: {e}")

induce_cpu_load(180)
