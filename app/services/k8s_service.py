# app/services/k8s_service.py
from kubernetes import client, config
import random, string, os
from typing import Dict, Any
NAMESPACE = "mincloud"
SERVICE_TYPE = "NodePort"   # 로컬 개발 편의. Ingress 쓰면 LoadBalancer/ClusterIP로 바꿔도 됨

def _rand_name(prefix="ai"):
    return f"{prefix}-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

def _ensure_kube():
    # 1) 명시적 kubeconfig + context
    kubeconfig = os.environ.get("KUBECONFIG", os.path.expanduser("~/.kube/config"))
    context = os.environ.get("KUBE_CONTEXT", "minikube")
    config.load_kube_config(config_file=kubeconfig, context=context)

    # 2) (선택) 프록시 제거
    for k in ("HTTPS_PROXY","https_proxy","HTTP_PROXY","http_proxy"):
        os.environ.pop(k, None)

    # 3) 간단한 ping (실패시 명확한 에러 메시지)
    try:
        client.VersionApi().get_code()
    except Exception as e:
        raise RuntimeError(f"Kubernetes API connect failed. Check minikube status & kubeconfig. Detail: {e}")

def create_k8s_app(image: str, container_port: int = 5000):
    _ensure_kube()
    apps = client.AppsV1Api()
    core = client.CoreV1Api()

    name = _rand_name("ai-inf")
    labels = {"app": name}

    # 1) Deployment
    dep = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=name, namespace=NAMESPACE, labels=labels),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels=labels),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=labels),
                spec=client.V1PodSpec(containers=[
                    client.V1Container(
                        name="ai-container",
                        image=image,
                        image_pull_policy="IfNotPresent",
                        ports=[client.V1ContainerPort(container_port=container_port, name="http")],
                        readiness_probe=client.V1Probe(
                            http_get=client.V1HTTPGetAction(path="/healthz", port="http"),
                            initial_delay_seconds=10, period_seconds=5, timeout_seconds=2, failure_threshold=6
                        ),
                        liveness_probe=client.V1Probe(
                            http_get=client.V1HTTPGetAction(path="/healthz", port="http"),
                            initial_delay_seconds=20, period_seconds=10, timeout_seconds=2, failure_threshold=3
                        ),
                        resources=client.V1ResourceRequirements(
                            requests={"cpu": "200m", "memory": "256Mi"},
                            limits={"cpu": "1", "memory": "1Gi"}
                        )
                    )
                ])
            )
        )
    )
    apps.create_namespaced_deployment(namespace=NAMESPACE, body=dep)

    # 2) Service (NodePort 자동 할당)
    svc = client.V1Service(
        metadata=client.V1ObjectMeta(name=name, namespace=NAMESPACE, labels=labels),
        spec=client.V1ServiceSpec(
            type=SERVICE_TYPE,
            selector=labels,
            ports=[client.V1ServicePort(port=container_port, target_port="http")]
        )
    )
    core.create_namespaced_service(namespace=NAMESPACE, body=svc)

    # 3) 접속 URL 계산 (minikube 환경 기준)
    # NodePort 읽기
    svc_obj = core.read_namespaced_service(name=name, namespace=NAMESPACE)
    node_port = svc_obj.spec.ports[0].node_port
    url = f"http://127.0.0.1:{node_port}"  # minikube service --url 로 터널 열면 그 URL도 가능

    # 반환: 우리가 state.json에 저장할 ‘id’로 Deployment/Service 이름 재사용
    return {"id": name, "port": node_port, "url": url}

def delete_k8s_app(name: str):
    _ensure_kube()
    apps = client.AppsV1Api()
    core = client.CoreV1Api()
    # Service 먼저 삭제
    try:
        core.delete_namespaced_service(name=name, namespace=NAMESPACE)
    except Exception:
        pass
    # Deployment 삭제 → RS/Pod 함께 정리
    try:
        apps.delete_namespaced_deployment(name=name, namespace=NAMESPACE)
    except Exception:
        pass
    return True

def update_image(deploy_name: str, container_name: str, new_image: str) -> bool:
    """Deployment의 컨테이너 이미지를 새 태그로 교체 (롤링 업데이트)."""
    _ensure_kube()
    apps = client.AppsV1Api()
    # patch body: spec.template.spec.containers[].image 변경
    body = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {"name": container_name, "image": new_image}
                    ]
                }
            }
        }
    }
    apps.patch_namespaced_deployment(name=deploy_name, namespace=NAMESPACE, body=body)
    return True

def scale_deployment(deploy_name: str, replicas: int) -> bool:
    """replicas 개수 조정."""
    _ensure_kube()
    apps = client.AppsV1Api()
    body = {"spec": {"replicas": replicas}}
    apps.patch_namespaced_deployment_scale(name=deploy_name, namespace=NAMESPACE, body=body)
    return True

def get_status(deploy_name: str) -> Dict[str, Any]:
    """배포 및 서비스 상태 요약."""
    _ensure_kube()
    apps = client.AppsV1Api()
    core = client.CoreV1Api()

    d = apps.read_namespaced_deployment(name=deploy_name, namespace=NAMESPACE)
    desired = d.spec.replicas or 0
    ready = d.status.ready_replicas or 0
    updated = d.status.updated_replicas or 0
    available = d.status.available_replicas or 0

    # Service는 배포명과 동일하게 만든 가정
    try:
        s = core.read_namespaced_service(name=deploy_name, namespace=NAMESPACE)
        node_port = s.spec.ports[0].node_port
        url = f"http://127.0.0.1:{node_port}" if node_port else None
    except Exception:
        node_port, url = None, None

    return {
        "id": deploy_name,
        "desired": desired,
        "ready": ready,
        "updated": updated,
        "available": available,
        "url": url
    }
