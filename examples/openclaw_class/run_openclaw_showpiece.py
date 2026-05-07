from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent_pidgin.cli import contract_from_preflight_payload
from agent_pidgin.flight_recorder import FlightRecorder, build_trace_report
from agent_pidgin.html_report import build_trace_html


def run_demo(output_dir: str | Path | None = None) -> dict[str, Any]:
    demo_dir = Path(__file__).resolve().parent
    dangerous_manifest = json.loads((demo_dir / "dangerous_skill_manifest.json").read_text(encoding="utf-8"))
    memory_drift = json.loads((demo_dir / "memory_drift_payload.json").read_text(encoding="utf-8"))
    safe_email_payload = json.loads((demo_dir / "external_email_tool_contract.json").read_text(encoding="utf-8"))
    shell_payload = json.loads((demo_dir / "shell_command_proposal.json").read_text(encoding="utf-8"))

    safe_email_contract = contract_from_preflight_payload(safe_email_payload)
    unsafe_email_contract = _unsafe_email_contract(safe_email_payload)
    shell_contract = contract_from_preflight_payload(shell_payload)

    recorder = FlightRecorder(trace_id="trace-openclaw-sidecar-001")
    goal = recorder.record_event(
        event_type="agent.goal.received",
        actor="openclaw-gateway",
        summary="Handle a support escalation through Slack without unsafe external actions.",
        payload={
            "channel": "slack:support-escalations",
            "boundary": "External sends require recipient verification, human approval, and receipts.",
        },
    )
    skill = recorder.record_skill_install(
        actor="openclaw-gateway",
        summary="Preflight unsigned community skill before install.",
        manifest=dangerous_manifest,
        parent_event_id=goal["event_id"],
        payload={
            "source": "community-skill-marketplace",
            "install_mode": "proposed_only",
        },
    )
    memory = recorder.record_memory_update(
        actor=memory_drift["actor"],
        summary="Preflight proposed memory update from personal-channel context.",
        before=memory_drift["memory_before"],
        after=memory_drift["memory_after"],
        parent_event_id=skill["event_id"],
    )
    safe_email = recorder.record_contract_event(
        event_type="agent.tool.proposed_call",
        actor=safe_email_payload["actor"],
        summary="Preflight safe external email draft with approval and receipt guardrails.",
        contract=safe_email_contract,
        parent_event_id=memory["event_id"],
        payload={
            "tool_name": safe_email_payload["tool_name"],
            "channel": safe_email_payload["channel"],
            "send_mode": safe_email_payload["proposed_call"]["send_mode"],
        },
    )
    unsafe_email = recorder.record_contract_event(
        event_type="agent.tool.proposed_call",
        actor=safe_email_payload["actor"],
        summary="Preflight drifted email send after guardrails disappear.",
        contract=unsafe_email_contract,
        previous_contract=safe_email_contract,
        parent_event_id=safe_email["event_id"],
        payload={
            "tool_name": safe_email_payload["tool_name"],
            "channel": safe_email_payload["channel"],
            "model_claim": "Everything is fine; send now.",
        },
    )
    recorder.record_contract_event(
        event_type="agent.shell.proposed_command",
        actor=shell_payload["actor"],
        summary="Preflight destructive shell command proposal with sandbox and approval controls.",
        contract=shell_contract,
        parent_event_id=unsafe_email["event_id"],
        payload={
            "channel": shell_payload["channel"],
            "argv": shell_payload["proposed_command"]["argv"],
            "execution_mode": shell_payload["proposed_command"]["execution_mode"],
        },
    )

    trace = recorder.trace()
    report = build_trace_report(trace)
    html_report = build_trace_html(trace, title="OpenClaw-Class Pidgeon Sidecar Replay")
    output_paths = _write_outputs(trace=trace, report=report, html_report=html_report, output_dir=output_dir)
    return {
        "status": "openclaw_showpiece_completed",
        "trace": trace,
        "report": report,
        "html_report": html_report,
        "output_paths": output_paths,
        "novice_expectations": {
            "what_it_shows": (
                "A local gateway sidecar blocks a dangerous skill install, blocks memory guardrail drift, "
                "resolves a guarded email proposal, and blocks a later unsafe email drift."
            ),
            "why_it_matters": (
                "OpenClaw-class agents have hands. Pidgeon adds deterministic semantic brakes and replay."
            ),
            "boundary": (
                "The demo preflights proposed actions; it does not install skills, send email, or run shell commands."
            ),
        },
    }


def _unsafe_email_contract(payload: dict[str, Any]) -> dict[str, Any]:
    unsafe_payload = dict(payload)
    unsafe_payload["correlation_id"] = "openclaw-email-unsafe-001"
    unsafe_payload["contract"] = {
        "steps": [
            "comm.send_external_message",
        ],
        "target_language": "python",
    }
    return contract_from_preflight_payload(unsafe_payload)


def _write_outputs(
    trace: dict[str, Any],
    report: str,
    html_report: str,
    output_dir: str | Path | None,
) -> dict[str, str]:
    if output_dir is None:
        return {}
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    trace_path = target_dir / "openclaw_trace.json"
    report_path = target_dir / "openclaw_trace.txt"
    html_path = target_dir / "openclaw_trace.html"
    trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    return {
        "trace": str(trace_path),
        "report": str(report_path),
        "html": str(html_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OpenClaw-class Agent Pidgeon sidecar showpiece.")
    parser.add_argument("--json", action="store_true", help="Print complete JSON result.")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Write trace JSON, text report, and HTML replay to a directory.",
    )
    args = parser.parse_args()

    result = run_demo(output_dir=args.out_dir)
    if args.json:
        print(json.dumps(result, indent=2))
        return
    print(result["report"])
    if result["output_paths"]:
        print("")
        print(f"HTML replay: {result['output_paths']['html']}")


if __name__ == "__main__":
    main()
