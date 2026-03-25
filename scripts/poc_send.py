from __future__ import annotations

import json

from agent_pidgin.demo import build_demo_message, run_local_demo


if __name__ == "__main__":
    payload = build_demo_message()
    result = run_local_demo(payload=payload)
    print(json.dumps({"payload": payload, "result": result}, indent=2))
