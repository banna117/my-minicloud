from flask import Blueprint, request, jsonify
from app.services.docker_service import launch_container as docker_launch, list_containers, stop_container
from app.utils.state import save_state, load_state, update_status, get_entry, update_fields
from app.services.k8s_service import create_k8s_app, delete_k8s_app, update_image as k8s_update_image, scale_deployment as k8s_scale, get_status as k8s_status

resource_bp = Blueprint('resources', __name__)

# app/routes/resource.py
@resource_bp.route('/', methods=['POST'])
@resource_bp.route('', methods=['POST'])
def create_resource():
    data = request.get_json()
    image = data.get('image', 'ubuntu')
    user = data.get('user', 'anonymous')
    tag = data.get('tag', 'default')
    type_ = data.get('type', 'basic')
    orch  = data.get('orchestrator', 'docker')  # "docker" | "k8s"

    if orch == "k8s":
        # K8s로 배포
        info = create_k8s_app(image=image, container_port=5000)
        rid, port, url = info["id"], info["port"], info["url"]
    else:
        # Docker로 실행
        rid, port = docker_launch(image, type_)    # (container_id, host_port)
        url = f"http://127.0.0.1:{port}" if port else None
    
    save_state(rid, image, user, tag, type_, port,url, orchestrator=orch)

    resp = {"status": "created", "id": rid}
    if port:
        resp["url"] = f"http://127.0.0.1:{port}"
    return jsonify(resp), 201

@resource_bp.route('/', methods=['GET'])
def get_resources():
    query_user = request.args.get('user')
    query_status = request.args.get('status')
    query_tag = request.args.get('tag')
    group_by_user = request.args.get('group_by_user', 'false').lower() == 'true'

    containers = load_state()

    # 필터링
    if query_user:
        containers = [c for c in containers if c.get('user') == query_user]
    if query_status:
        containers = [c for c in containers if c.get('status') == query_status]
    if query_tag:
        containers = [c for c in containers if c.get('tag') == query_tag]

    # 그룹화 (옵션)
    if group_by_user:
        result = {}
        for c in containers:
            user = c.get('user', 'unknown')
            result.setdefault(user, []).append(c)
        return jsonify(result), 200

    return jsonify(containers), 200

@resource_bp.route('/<rid>', methods=['DELETE'])
def delete_resource(rid):
    state = load_state()
    entry = next((e for e in state if e.get("id")==rid), None)
    if not entry:
        return jsonify({"status":"not found","id":rid}), 404

    orch = entry.get("orchestrator","docker")
    if orch == "k8s":
        ok = delete_k8s_app(rid)
    else:
        from app.services.docker_service import stop_container
        ok = stop_container(rid)

    if ok:
        update_status(rid, "stopped")
        return jsonify({"status":"stopped","id":rid}), 200
    else:
        return jsonify({"status":"error","id":rid}), 500
    
def _require_entry(rid):
    entry = get_entry(rid)
    if not entry:
        return None, (jsonify({"error":"not found","id":rid}), 404)
    return entry, None

@resource_bp.route('/<rid>/image', methods=['PATCH'])
def patch_image(rid):
    entry, err = _require_entry(rid)
    if err: return err
    orch = entry.get("orchestrator", "docker")
    new_image = request.get_json().get("image")
    if not new_image:
        return jsonify({"error":"image is required"}), 400

    if orch != "k8s":
        return jsonify({"error":"not implemented for orchestrator", "orchestrator": orch}), 501

    # K8s 이미지 교체 (컨테이너 이름은 k8s_service에서 'ai-container'로 생성함)
    k8s_update_image(deploy_name=rid, container_name="ai-container", new_image=new_image)
    # 상태 파일에도 최신 이미지 반영
    update_fields(rid, image=new_image)
    return jsonify({"status": "rolling_update_started", "id": rid, "image": new_image}), 202


@resource_bp.route('/<rid>/scale', methods=['PATCH'])
def patch_scale(rid):
    entry, err = _require_entry(rid)
    if err: return err
    orch = entry.get("orchestrator", "docker")
    replicas = request.get_json().get("replicas")
    if replicas is None:
        return jsonify({"error":"replicas is required"}), 400

    if orch != "k8s":
        return jsonify({"error":"not implemented for orchestrator", "orchestrator": orch}), 501

    k8s_scale(deploy_name=rid, replicas=int(replicas))
    return jsonify({"status": "scaling", "id": rid, "replicas": int(replicas)}), 202

@resource_bp.route('/<rid>/status', methods=['GET'])
def get_status(rid):
    entry, err = _require_entry(rid)
    if err: return err
    orch = entry.get("orchestrator", "docker")

    if orch == "k8s":
        st = k8s_status(deploy_name=rid)
        # URL/Port가 바뀌었으면 파일에도 반영 (선택)
        if st.get("url"):
            # nodePort만 추출
            import re
            m = re.search(r":(\d+)$", st["url"])
            port = int(m.group(1)) if m else None
            update_fields(rid, url=st["url"], port=port)
        return jsonify({"orchestrator":"k8s", **st}), 200

    # Docker 상태 간단 조회(선택 구현)
    from app.services.docker_service import client as docker_client
    try:
        c = docker_client.containers.get(rid)
        c.reload()
        st = c.attrs.get("State", {})
        return jsonify({"orchestrator":"docker", "id": rid, "state": st}), 200
    except Exception as e:
        return jsonify({"orchestrator":"docker", "id": rid, "error": str(e)}), 404