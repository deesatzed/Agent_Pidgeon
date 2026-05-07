from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def extract_pidgin_contract(task: dict[str, Any]) -> dict[str, Any]:
    for artifact in task.get("artifacts", []):
        if artifact.get("kind") == "application/vnd.agent-pidgin.contract+json":
            content = artifact.get("content")
            if isinstance(content, dict):
                return content
    raise ValueError("No Pidgin contract artifact found")


def main() -> None:
    task_path = Path(__file__).with_name("sample_a2a_task.json")
    task = json.loads(task_path.read_text(encoding="utf-8"))
    print(json.dumps(extract_pidgin_contract(task), indent=2))


if __name__ == "__main__":
    main()
