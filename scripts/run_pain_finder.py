from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_pidgin.pain_finder import analyze_pain_finder_csv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Score messy workflow language for Pidgin contract-discovery pain.")
    parser.add_argument("csv_path", help="CSV with columns: id, source_type, raw_instruction")
    parser.add_argument("--json", action="store_true", help="Print JSON output. This is the default.")
    args = parser.parse_args()

    print(json.dumps(analyze_pain_finder_csv(args.csv_path), indent=2))


if __name__ == "__main__":
    main()
