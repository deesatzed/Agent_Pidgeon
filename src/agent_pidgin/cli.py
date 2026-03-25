from __future__ import annotations

import json

from agent_pidgin.demo import run_local_demo


def main() -> None:
    print(json.dumps(run_local_demo(), indent=2))


if __name__ == "__main__":
    main()
