import redis
import logging
from flask import Flask, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

redis_client = redis.Redis(
    host='10.0.0.250',
    port=6379,
    decode_responses=True,
    socket_connect_timeout=30,  # Aumenta o tempo de conexão
    socket_timeout=120,         # Aumenta o tempo de espera por resposta
    retry_on_timeout=True,
    socket_keepalive=True
    # health_check_interval pode ser ajustado ou omitido
)

@app.route('/get_ips', methods=['GET'])
def get_container_ips():
    try:
        # Loga informações sobre o cliente Redis, omitindo o health_check_interval diretamente
        logging.info(f"Redis client configuration: host={redis_client.connection_pool.connection_kwargs['host']}, "
                     f"port={redis_client.connection_pool.connection_kwargs['port']}, "
                     f"socket_timeout={redis_client.connection_pool.connection_kwargs.get('socket_timeout')}")

        # Executa a consulta de chaves no Redis
        container_ips = []
        for key in redis_client.keys("container:*"):
            container_data = redis_client.hgetall(key)
            container_info = {
                "name": container_data.get('name'),
                "ip": container_data.get('ip')
            }
            container_ips.append(container_info)
        
        # Loga o número de chaves encontradas
        logging.info(f"Number of container keys found: {len(container_ips)}")

        return jsonify(container_ips)
    
    except redis.exceptions.ConnectionError as e:
        logging.error(f"Redis connection error: {e}")
        return jsonify({"error": "Redis connection error", "details": str(e)}), 500

@app.route('/test_redis', methods=['GET'])
def test_redis_connection():
    try:
        redis_client.ping()
        return jsonify({"status": "success", "message": "Connected to Redis!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
