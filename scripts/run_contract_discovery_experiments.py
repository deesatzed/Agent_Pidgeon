from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_pidgin.pain_finder import run_contract_discovery_experiment  # noqa: E402


def main() -> None:
    examples = ROOT / "examples/contract_discovery"
    parser = argparse.ArgumentParser(description="Run deterministic Agent Pidgin contract-discovery proof experiments.")
    parser.add_argument(
        "--pain-csv",
        default=examples / "messy_workflow_examples.csv",
        type=Path,
        help="CSV with messy workflow instructions.",
    )
    parser.add_argument(
        "--lift-csv",
        default=examples / "contract_lift_examples.csv",
        type=Path,
        help="CSV scoring whether contract conversion exposed value.",
    )
    parser.add_argument(
        "--comparison-csv",
        default=examples / "agent_comparison_examples.csv",
        type=Path,
        help="CSV comparing raw-instruction and contract-guided agent behavior.",
    )
    parser.add_argument(
        "--human-csv",
        default=examples / "human_reaction_examples.csv",
        type=Path,
        help="CSV capturing whether humans found the contract clarifying.",
    )
    parser.add_argument(
        "--readiness-csv",
        default=examples / "nanowhale_readiness_examples.csv",
        type=Path,
        help="CSV estimating tiny local model intake readiness by domain.",
    )
    args = parser.parse_args()

    result = run_contract_discovery_experiment(
        pain_csv=args.pain_csv,
        lift_csv=args.lift_csv,
        comparison_csv=args.comparison_csv,
        human_csv=args.human_csv,
        readiness_csv=args.readiness_csv,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
