import time
import requests
import os

# Alterando o host para 'camel-app' em vez de 'localhost'
camel_app_url = os.getenv('CAMEL_APP_URL', 'http://camel-app:8080/api/v1/sensor/data')

# Simular dados do sensor
sensor_data = {
    "sensorId": "sensor_http_001",
    "temperature": 25.0,
    "humidity": 55
}

while True:
    try:
        response = requests.post(camel_app_url, json=sensor_data)
        response.raise_for_status()
        print(f"Dados enviados com sucesso: {sensor_data}")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar dados: {e}")
    
    # Enviar os dados a cada 10 segundos
    time.sleep(10)
