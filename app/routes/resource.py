from flask import Blueprint, request, jsonify
from app.services.docker_service import launch_container, list_containers
from app.utils.state import save_state, load_state

resource_bp = Blueprint('resources', __name__)

@resource_bp.route('/', methods=['POST'])
def create_resource():
    data = request.get_json()
    image = data.get('image', 'ubuntu')
    container_id = launch_container(image)
    save_state(container_id)
    return jsonify({'status': 'created', 'id': container_id}), 201

@resource_bp.route('/', methods=['GET'])
def get_resources():
    containers = list_containers()
    return jsonify(containers), 200