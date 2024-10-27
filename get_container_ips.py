from flask import Flask, jsonify
import docker

app = Flask(__name__)
client = docker.from_env()

CONTAINER_PREFIX = "mn.mqtt"

@app.route('/get_ips', methods=['GET'])
def get_container_ips():
    container_ips = []
    for container in client.containers.list():
        if container.name.startswith(CONTAINER_PREFIX):
            networks = container.attrs['NetworkSettings']['Networks']
            ip_address = next(iter(networks.values()))['IPAddress'] if networks else None
            container_ips.append({
                "name": container.name,
                "ip": ip_address
            })
    return jsonify(container_ips)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)