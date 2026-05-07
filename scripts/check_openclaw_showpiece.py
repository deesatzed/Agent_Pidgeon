from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

GOLDEN_DIR = ROOT / "examples/openclaw_class/golden"
EXPECTED_EVENTS = [
    ("agent.goal.received", "observed"),
    ("agent.skill.proposed_install", "blocked"),
    ("agent.memory.proposed_update", "blocked"),
    ("agent.tool.proposed_call", "resolved"),
    ("agent.tool.proposed_call", "blocked"),
    ("agent.shell.proposed_command", "resolved"),
]
REQUIRED_REPORT_PHRASES = [
    "Agent Pidgeon Flight Recorder",
    "Blocked events: 3",
    "Semantic drift events: 2",
    "DANGEROUS_SHELL_PERMISSION",
]
REQUIRED_HTML_PHRASES = [
    "OpenClaw-Class Pidgeon Sidecar Replay",
    "agent.skill.proposed_install",
    "agent.memory.proposed_update",
    "agent.shell.proposed_command",
]


def main() -> None:
    result = check_showpiece()
    print(json.dumps(result, indent=2))


def check_showpiece() -> dict[str, Any]:
    from examples.openclaw_class.run_openclaw_showpiece import run_demo

    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_demo(output_dir=tmpdir)
        trace = _read_json(Path(tmpdir) / "openclaw_trace.json")
        report = (Path(tmpdir) / "openclaw_trace.txt").read_text(encoding="utf-8")
        html = (Path(tmpdir) / "openclaw_trace.html").read_text(encoding="utf-8")

    golden_trace = _read_json(GOLDEN_DIR / "openclaw_trace.json")
    _assert_trace_shape(trace, golden_trace)
    _assert_contains(report, REQUIRED_REPORT_PHRASES, "text report")
    _assert_contains(html, REQUIRED_HTML_PHRASES, "HTML replay")
    return {
        "status": "passed",
        "trace_id": trace["trace_id"],
        "event_count": trace["summary"]["event_count"],
        "blocked_event_count": trace["summary"]["blocked_event_count"],
        "receipt_count": trace["summary"]["receipt_count"],
        "result_status": result["status"],
    }


def _assert_trace_shape(trace: dict[str, Any], golden_trace: dict[str, Any]) -> None:
    actual_events = [(event["event_type"], event["decision"]) for event in trace["events"]]
    golden_events = [(event["event_type"], event["decision"]) for event in golden_trace["events"]]
    if actual_events != EXPECTED_EVENTS:
        raise AssertionError(f"Unexpected showpiece events: {actual_events}")
    if actual_events != golden_events:
        raise AssertionError(f"Showpiece event shape drifted from golden trace: {actual_events} != {golden_events}")
    expected_summary = {
        "event_count": 6,
        "blocked_event_count": 3,
        "semantic_drift_event_count": 2,
        "receipt_count": 11,
    }
    for key, expected in expected_summary.items():
        if trace["summary"].get(key) != expected:
            raise AssertionError(f"Unexpected summary {key}: {trace['summary'].get(key)} != {expected}")
        if golden_trace["summary"].get(key) != expected:
            raise AssertionError(f"Golden summary {key} is stale: {golden_trace['summary'].get(key)} != {expected}")


def _assert_contains(content: str, phrases: list[str], artifact_name: str) -> None:
    missing = [phrase for phrase in phrases if phrase not in content]
    if missing:
        raise AssertionError(f"{artifact_name} missing expected phrases: {missing}")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
