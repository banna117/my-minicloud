import json
from pathlib import Path
from datetime import datetime

STATE_FILE = Path('resource_state.json')

def load_state():
    if STATE_FILE.exists():
        with STATE_FILE.open('r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []



def save_state(container_id, image, user, tag, type_, port=None):
    state = load_state()
    url = f"http://localhost:{port}" if port else None
    state.append({
        "id": container_id,
        "status": "running",
        "image": image,
        "user": user,
        "tag": tag,
        "type": type_,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "port": port,
        "url": url
    })
    STATE_FILE.write_text(json.dumps(state, indent=2))

def update_status(container_id, new_status):
    state = load_state()
    for entry in state:
        if entry["id"] == container_id:
            entry["status"] = new_status
            break
    with STATE_FILE.open('w') as f:
        json.dump(state, f, indent=2)