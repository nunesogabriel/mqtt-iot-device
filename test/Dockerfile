# Usa uma imagem base do Python
FROM python:3.9-slim

WORKDIR /app

COPY induce_cpu_load.py /app/induce_cpu_load.py

RUN pip install docker

CMD ["python", "/app/induce_cpu_load.py"]