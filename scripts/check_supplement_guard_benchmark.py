from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

POLICY_PATH = ROOT / "examples/supplement_coach/domain_policy.json"
CASES_PATH = ROOT / "examples/supplement_coach/benchmark_cases.jsonl"


def main() -> None:
    result = check_supplement_guard_benchmark()
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


def check_supplement_guard_benchmark() -> dict[str, object]:
    from scripts.check_domain_boundary_benchmark import check_domain_boundary_benchmark

    return check_domain_boundary_benchmark(POLICY_PATH, CASES_PATH)


if __name__ == "__main__":
    main()
