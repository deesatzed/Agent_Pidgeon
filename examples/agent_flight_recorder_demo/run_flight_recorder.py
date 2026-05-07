from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent_pidgin.flight_recorder import FlightRecorder, build_trace_report


def run_demo() -> dict[str, Any]:
    demo_dir = Path(__file__).resolve().parent
    safe_contract = json.loads((demo_dir / "safe_tool_contract.json").read_text(encoding="utf-8"))
    corrupted_contract = json.loads((demo_dir / "corrupted_tool_contract.json").read_text(encoding="utf-8"))

    recorder = FlightRecorder(trace_id="trace-aafr-support-agent-001")
    goal = recorder.record_event(
        event_type="agent.goal.received",
        actor="support-agent",
        summary="Summarize a support note and create an internal ticket without external communication.",
        payload={
            "goal": "Create internal ticket only.",
            "operator_boundary": "Do not email the customer without human review.",
        },
    )
    memory = recorder.record_memory_update(
        actor="support-agent",
        summary="Store safe operating boundary in working memory.",
        parent_event_id=goal["event_id"],
        before={},
        after={
            "external_email_allowed": False,
            "human_review_required": True,
        },
    )
    safe_tool = recorder.record_contract_event(
        event_type="agent.tool.proposed_call",
        actor="support-agent",
        summary="Propose internal ticket creation with PHI scrubbing, evidence, review, and receipts.",
        parent_event_id=memory["event_id"],
        contract=safe_contract,
        payload={
            "tool_name": "ticket.create_internal",
            "model_claim": "This is an internal-only action.",
        },
    )
    corrupt_memory = recorder.record_memory_update(
        actor="support-agent",
        summary="A subtle context drift changes the operating boundary to allow immediate external email.",
        parent_event_id=safe_tool["event_id"],
        before={
            "external_email_allowed": False,
            "human_review_required": True,
        },
        after={
            "external_email_allowed": True,
            "human_review_required": False,
        },
    )
    unsafe_tool = recorder.record_contract_event(
        event_type="agent.tool.proposed_call",
        actor="support-agent",
        summary="Propose external customer email after corrupted context update.",
        parent_event_id=corrupt_memory["event_id"],
        contract=corrupted_contract,
        previous_contract=safe_contract,
        payload={
            "tool_name": "email.send_customer",
            "model_claim": "Everything is fine; send the customer update now.",
        },
    )
    recorder.record_event(
        event_type="agent.tool.policy_blocked",
        actor="agent-pidgeon",
        summary="Block unsafe external action and preserve replay data for review.",
        parent_event_id=unsafe_tool["event_id"],
        decision="blocked",
        payload={
            "blocked_event_id": unsafe_tool["event_id"],
            "reason": "Semantic drift plus policy failure.",
            "operator_action": "Review trace before retrying with a pinned artifact and restored guardrails.",
        },
    )

    trace = recorder.trace()
    return {
        "status": "aafr_demo_completed",
        "trace": trace,
        "report": build_trace_report(trace),
        "novice_expectations": {
            "what_the_app_does": (
                "It records a replayable timeline of agent intent, memory changes, proposed tool calls, "
                "policy decisions, semantic diffs, and receipts."
            ),
            "why_you_want_it": (
                "When an autonomous agent goes wrong, you can see where the meaning changed before a tool acts."
            ),
            "benefit": (
                "Security and operators get an inspectable flight recorder instead of only trusting "
                "the model's summary."
            ),
            "boundary": "This demo does not execute tools and does not claim hardware-level tamper-proof logging.",
            "hardening": (
                "The trace is hash-chained, high-risk contract drift blocks proposed actions, and memory guardrail "
                "weakening is detected before accepting the update."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Agent Pidgeon Autonomous Agent Flight Recorder demo.")
    parser.add_argument("--json", action="store_true", help="Print the complete JSON trace result.")
    args = parser.parse_args()

    result = run_demo()
    if args.json:
        print(json.dumps(result, indent=2))
        return
    print(result["report"])


if __name__ == "__main__":
    main()
