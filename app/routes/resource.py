from flask import Blueprint, request, jsonify
from app.services.docker_service import launch_container, list_containers, stop_container
from app.utils.state import save_state, load_state, update_status

resource_bp = Blueprint('resources', __name__)

@resource_bp.route('/', methods=['POST'])
def create_resource():
    data = request.get_json()
    image = data.get('image', 'ubuntu')
    user = data.get('user','anonymous')
    tag = data.get('tag','default')
    container_id = launch_container(image)
    save_state(container_id,image,user,tag)
    return jsonify({'status': 'created', 'id': container_id}), 201

@resource_bp.route('/', methods=['GET'])
def get_resources():
    query_user = request.args.get('user')
    query_status = request.args.get('status')
    query_tag = request.args.get('tag')

    containers = load_state()
    
    if query_user:
        containers = [c for c in containers if c.get('user') == query_user]
    if query_status:
        containers = [c for c in containers if c.get('status') == query_status]
    if query_tag:
        containers = [c for c in containers if c.get('tag') == query_tag]

    return jsonify(containers), 200

@resource_bp.route('/<container_id>', methods=['DELETE'])
def delete_resource(container_id):
    success = stop_container(container_id)
    if success:
        update_status(container_id, "stopped")
        return jsonify({"status": "stopped", "id": container_id}), 200
    else:
        return jsonify({"status": "not found", "id": container_id}), 404