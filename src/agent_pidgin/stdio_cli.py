from __future__ import annotations

import asyncio
import json

from agent_pidgin.demo import build_demo_message, run_stdio_demo


def main() -> None:
    payload = build_demo_message()
    result = asyncio.run(run_stdio_demo(payload=payload))
    print(json.dumps({"payload": payload, "round_trip": result}, indent=2))


if __name__ == "__main__":
    main()
