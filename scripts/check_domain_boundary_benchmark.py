from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run a domain-boundary benchmark.")
    parser.add_argument("domain_policy")
    parser.add_argument("cases_path")
    args = parser.parse_args(argv)
    result = check_domain_boundary_benchmark(args.domain_policy, args.cases_path)
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


def check_domain_boundary_benchmark(domain_policy_path: str | Path, cases_path: str | Path) -> dict[str, Any]:
    from agent_pidgin.domain_guard import benchmark_prompt_boundaries, load_benchmark_cases, load_domain_policy

    policy = load_domain_policy(domain_policy_path)
    cases = load_benchmark_cases(cases_path)
    result = benchmark_prompt_boundaries(cases, policy)
    compact = {
        "status": result["status"],
        "domain": policy["domain"],
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
