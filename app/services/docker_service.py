import docker, time
client = docker.from_env()

def _get_host_port(container, container_port='5000/tcp', retries=10, delay=0.2):
    for _ in range(retries):
        container.reload()
        ports = (container.attrs.get("NetworkSettings", {}).get("Ports")) or {}
        entry = ports.get(container_port)
        if isinstance(entry, list) and entry and entry[0].get("HostPort"):
            return entry[0]["HostPort"]
        time.sleep(delay)  # 잠깐 대기 후 재시도
    return None

def launch_container(image_name, type_="basic"):
    if type_ == "ai":
        container = client.containers.run(
            image_name,
            detach=True,
            ports={'5000/tcp': None},  # 호스트 임의 포트에 매핑
        )
        host_port = _get_host_port(container, '5000/tcp')
        return container.id, host_port
    else:
        container = client.containers.run(image_name, detach=True)
        return container.id, None
def list_containers():
    containers = client.containers.list()
    return [
        {
            'id': c.short_id,
            'image': c.image.tags,
            'status': c.status,
            'name': c.name
        }
        for c in containers
    ]
def stop_container(container_id):
    try:
        container = client.containers.get(container_id)
        container.stop()
        return True
    except docker.errors.NotFound:
        return False