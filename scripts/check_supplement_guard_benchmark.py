from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

POLICY_PATH = ROOT / "examples/supplement_coach/domain_policy.json"
CASES_PATH = ROOT / "examples/supplement_coach/benchmark_cases.jsonl"


def main() -> None:
    result = check_supplement_guard_benchmark()
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


def check_supplement_guard_benchmark() -> dict[str, Any]:
    from agent_pidgin.domain_guard import benchmark_prompt_boundaries, load_benchmark_cases, load_domain_policy

    policy = load_domain_policy(POLICY_PATH)
    cases = load_benchmark_cases(CASES_PATH)
    result = benchmark_prompt_boundaries(cases, policy)
    compact = {
        "status": result["status"],
        "case_count": result["case_count"],
        "status_accuracy": result["status_accuracy"],
        "tier_accuracy": result["tier_accuracy"],
        "unsafe_case_count": result["unsafe_case_count"],
        "unsafe_catch_rate": result["unsafe_catch_rate"],
    }
    if result["status"] != "passed":
        compact["failures"] = [
            case
            for case in result["results"]
            if not case["status_match"] or not case["tier_match"] or not case["unsafe_caught"]
        ]
    return compact


if __name__ == "__main__":
    main()
