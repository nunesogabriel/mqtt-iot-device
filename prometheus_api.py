from flask import Flask, request, jsonify
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Flask App
app = Flask(__name__)

# Métricas Prometheus
published_messages = Counter(
    'mqtt_published_messages_total', 
    'Total de mensagens publicadas pelo dispositivo'
)

publish_interval = Gauge(
    'mqtt_publish_interval_seconds', 
    'Intervalo atual de coleta e envio em segundos',
    ['ip']  # Adiciona IP como label
)

@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Endpoint para expor as métricas para Prometheus.
    """
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/increment', methods=['POST'])
def increment():
    """
    Incrementa o contador de mensagens publicadas.
    """
    published_messages.inc()
    return jsonify({"status": "success", "message": "Counter incremented"}), 200

@app.route('/set_interval', methods=['POST'])
def set_interval():
    """
    Atualiza o valor do intervalo de publicação.
    """
    data = request.json
    interval = data.get("interval")
    ip = data.get("ip")
    if interval is None:
        return jsonify({"status": "error", "message": "Missing 'interval' in request"}), 400

    publish_interval.labels(ip=ip).set(interval)
    return jsonify({"status": "success", "message": f"Interval set to {interval}"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)