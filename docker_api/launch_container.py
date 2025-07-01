import docker

client = docker.from_env()

def launch_container(image_name):
    container = client.containers.run(image_name, detach=True)
    return container.id