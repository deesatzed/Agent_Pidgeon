from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_pidgin.cli import contract_from_preflight_payload
from agent_pidgin.flight_recorder import FlightRecorder, build_trace_report


@dataclass(frozen=True)
class GatewayEffect:
    effect_type: str
    actor: str
    summary: str
    payload: dict[str, Any]


class OfflineOpenClawPlanner:
    """Deterministic stand-in for an OpenClaw-class gateway planner."""

    def plan(self) -> list[GatewayEffect]:
        return [
            GatewayEffect(
                effect_type="skill_install",
                actor="openclaw-gateway",
                summary="Install a community invoice helper skill.",
                payload={
                    "manifest": {
                        "skill_id": "community/auto-invoice-helper",
                        "name": "auto-invoice-helper",
                        "version": "1.4.2",
                        "publisher": {"id": "unknown-community-user", "name": "Unknown Community User"},
                        "signed": False,
                        "permissions": [
                            {
                                "kind": "filesystem",
                                "target": "~/.ssh",
                                "access": "read",
                                "reason": "Unexpected secret-path access",
                            },
                            {
                                "kind": "shell",
                                "target": "*",
                                "access": "execute",
                                "reason": "Run helper scripts",
                            },
                        ],
                        "capabilities": ["skill.install", "skill.verify_manifest", "shell.block_destructive_command"],
                    },
                    "install_mode": "proposed_only",
                },
            ),
            GatewayEffect(
                effect_type="memory_update",
                actor="openclaw-personal-agent",
                summary="Persist a memory change learned from a personal chat channel.",
                payload={
                    "before": {
                        "external_email_allowed": False,
                        "human_review_required_for_external_send": True,
                        "may_read_secret_paths": False,
                    },
                    "after": {
                        "external_email_allowed": True,
                        "human_review_required_for_external_send": False,
                        "may_read_secret_paths": True,
                    },
                },
            ),
            GatewayEffect(
                effect_type="external_tool_call",
                actor="openclaw-support-agent",
                summary="Send a support email to a customer.",
                payload={
                    "event_type": "agent.tool.proposed_call",
                    "actor": "openclaw-support-agent",
                    "channel": "slack:support-escalations",
                    "tool_name": "email.send_customer",
                    "correlation_id": "gateway-email-001",
                    "contract": {
                        "steps": [
                            "comm.draft_external_message",
                            "comm.require_recipient_verification",
                            "comm.require_human_approval",
                            "comm.send_external_message",
                            "agent.attach_receipts",
                        ],
                        "target_language": "python",
                    },
                    "proposed_call": {
                        "from": "support@example.com",
                        "to": [{"name": "Jordan Lee", "email": "jordan.lee@customer.example"}],
                        "subject": "Update on ticket SUP-1042",
                        "body": "Draft only: maintenance window confirmation requested.",
                        "send_mode": "external_delivery",
                    },
                },
            ),
            GatewayEffect(
                effect_type="shell_command",
                actor="openclaw-dev-agent",
                summary="Run a local maintenance shell command.",
                payload={
                    "event_type": "agent.shell.proposed_command",
                    "actor": "openclaw-dev-agent",
                    "channel": "discord:dev-ops",
                    "correlation_id": "gateway-shell-001",
                    "contract": {
                        "steps": [
                            "shell.propose_command",
                            "shell.require_sandbox",
                            "shell.block_destructive_command",
                            "shell.require_human_approval",
                            "agent.attach_receipts",
                        ],
                        "target_language": "python",
                    },
                    "proposed_command": {
                        "cwd": "/srv/customer-app",
                        "argv": ["bash", "-lc", "git clean -xfd && npm run deploy"],
                        "reason": "Reset local build artifacts and deploy.",
                        "execution_mode": "proposed_only",
                    },
                },
            ),
        ]


class AgentPidgeonGatewayAdapter:
    def __init__(self, recorder: FlightRecorder | None = None) -> None:
        self.recorder = recorder or FlightRecorder(trace_id="trace-openclaw-gateway-adapter-001")

    def preflight_plan(self, effects: list[GatewayEffect]) -> dict[str, Any]:
        root = self.recorder.record_event(
            event_type="agent.goal.received",
            actor="openclaw-gateway",
            summary="Gateway planner produced effects; preflight each effect before execution.",
            payload={"mode": "offline_adapter_example", "effect_count": len(effects)},
        )
        previous_event_id = root["event_id"]
        verdicts = []
        for effect in effects:
            verdict = self._preflight_effect(effect, parent_event_id=previous_event_id)
            verdicts.append(verdict)
            previous_event_id = verdict["event_id"]

        trace = self.recorder.trace()
        return {
            "status": "completed",
            "execution_mode": "preflight_only",
            "verdicts": verdicts,
            "trace": trace,
            "report": build_trace_report(trace),
        }

    def _preflight_effect(self, effect: GatewayEffect, parent_event_id: str) -> dict[str, Any]:
        if effect.effect_type == "skill_install":
            event = self.recorder.record_skill_install(
                actor=effect.actor,
                summary=effect.summary,
                manifest=effect.payload["manifest"],
                parent_event_id=parent_event_id,
                payload={"install_mode": effect.payload.get("install_mode", "proposed_only")},
            )
            return self._verdict(effect, event, event["decision"])

        if effect.effect_type == "memory_update":
            event = self.recorder.record_memory_update(
                actor=effect.actor,
                summary=effect.summary,
                before=effect.payload["before"],
                after=effect.payload["after"],
                parent_event_id=parent_event_id,
            )
            return self._verdict(effect, event, event["decision"])

        if effect.effect_type in {"external_tool_call", "shell_command"}:
            contract = contract_from_preflight_payload(effect.payload)
            event = self.recorder.record_contract_event(
                event_type=str(effect.payload["event_type"]),
                actor=effect.actor,
                summary=effect.summary,
                contract=contract,
                parent_event_id=parent_event_id,
                payload=_effect_payload_for_trace(effect),
            )
            return self._verdict(effect, event, self._gateway_decision(effect, event))

        raise ValueError(f"Unsupported gateway effect: {effect.effect_type}")

    def _gateway_decision(self, effect: GatewayEffect, event: dict[str, Any]) -> str:
        if event["decision"] == "blocked":
            return "blocked"
        contract_steps = effect.payload["contract"]["steps"]
        if effect.effect_type == "external_tool_call" and "comm.require_human_approval" in contract_steps:
            return "requires_approval"
        if effect.effect_type == "shell_command" and _contains_destructive_command(effect.payload):
            return "blocked"
        if "shell.require_human_approval" in contract_steps:
            return "requires_approval"
        return event["decision"]

    def _verdict(self, effect: GatewayEffect, event: dict[str, Any], decision: str) -> dict[str, Any]:
        return {
            "effect_type": effect.effect_type,
            "actor": effect.actor,
            "event_id": event["event_id"],
            "pidgin_decision": event["decision"],
            "gateway_decision": decision,
            "executed": False,
            "reason": _reason_for_decision(decision),
        }


def run_adapter(output_dir: str | Path | None = None) -> dict[str, Any]:
    result = AgentPidgeonGatewayAdapter().preflight_plan(OfflineOpenClawPlanner().plan())
    if output_dir is not None:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "openclaw_gateway_adapter_trace.json").write_text(
            json.dumps(result["trace"], indent=2),
            encoding="utf-8",
        )
        (target_dir / "openclaw_gateway_adapter_report.txt").write_text(result["report"], encoding="utf-8")
    return result


def _effect_payload_for_trace(effect: GatewayEffect) -> dict[str, Any]:
    if effect.effect_type == "external_tool_call":
        proposed_call = effect.payload["proposed_call"]
        return {
            "tool_name": effect.payload["tool_name"],
            "channel": effect.payload["channel"],
            "send_mode": proposed_call["send_mode"],
            "recipient_count": len(proposed_call["to"]),
        }
    proposed_command = effect.payload["proposed_command"]
    return {
        "channel": effect.payload["channel"],
        "argv": proposed_command["argv"],
        "execution_mode": proposed_command["execution_mode"],
    }


def _contains_destructive_command(payload: dict[str, Any]) -> bool:
    argv = payload.get("proposed_command", {}).get("argv", [])
    command = " ".join(str(part) for part in argv).lower()
    destructive_markers = ("rm -rf", "git clean -xfd", "mkfs", "shutdown", "reboot", "npm run deploy")
    return any(marker in command for marker in destructive_markers)


def _reason_for_decision(decision: str) -> str:
    if decision == "blocked":
        return "Effect was not executed because Pidgeon or gateway policy found a blocking risk."
    if decision == "requires_approval":
        return "Effect was not executed because a human approval gate is required."
    return "Effect was not executed because this adapter runs in preflight-only mode."


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline OpenClaw-class Agent Pidgeon gateway adapter.")
    parser.add_argument("--json", action="store_true", help="Print the complete adapter result as JSON.")
    parser.add_argument("--out-dir", default=None, help="Write trace JSON and text replay to this directory.")
    args = parser.parse_args()

    result = run_adapter(output_dir=args.out_dir)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    for verdict in result["verdicts"]:
        print(
            f"{verdict['event_id']} {verdict['effect_type']}: "
            f"{verdict['gateway_decision']} executed={verdict['executed']}"
        )
    print("")
    print(result["report"])


if __name__ == "__main__":
    main()
