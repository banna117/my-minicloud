import json
from pathlib import Path

STATE_FILE = Path('resource_state.json')

def load_state():
    if STATE_FILE.exists():
        with STATE_FILE.open('r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_state(container_id):
    state = load_state()
    state.append({'id': container_id})
    with STATE_FILE.open('w') as f:
        json.dump(state, f, indent=2)