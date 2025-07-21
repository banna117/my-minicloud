import docker

client = docker.from_env()

def launch_container(image_name):
    container = client.containers.run(image_name, detach=True)
    return container.id

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