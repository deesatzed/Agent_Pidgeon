from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

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
        return _gateway_decision_for_effect(effect=effect, pidgin_decision=str(event["decision"]))

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


class HttpPidgeonSidecarClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8765",
        post_json: Callable[[str, dict[str, Any]], tuple[int, dict[str, Any]]] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.post_json = post_json or self._post_json

    def preflight_effect(self, effect: GatewayEffect) -> dict[str, Any]:
        endpoint, payload = _sidecar_request_for_effect(effect)
        status_code, response = self.post_json(endpoint, payload)
        if not isinstance(response, dict):
            raise ValueError("sidecar response must be a JSON object")
        response.setdefault("http_status", status_code)
        return response

    def _post_json(self, endpoint: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{endpoint}",
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


class AgentPidgeonHttpGatewayAdapter:
    def __init__(self, sidecar_client: HttpPidgeonSidecarClient | None = None) -> None:
        self.sidecar_client = sidecar_client or HttpPidgeonSidecarClient()

    def preflight_plan(self, effects: list[GatewayEffect]) -> dict[str, Any]:
        verdicts = []
        sidecar_results = []
        for effect in effects:
            response = self.sidecar_client.preflight_effect(effect)
            sidecar_results.append(_sidecar_result_summary(response))
            verdicts.append(_http_verdict(effect=effect, response=response))
        return {
            "status": "completed",
            "execution_mode": "preflight_only",
            "transport": "http_sidecar",
            "sidecar_url": self.sidecar_client.base_url,
            "verdicts": verdicts,
            "sidecar_results": sidecar_results,
        }


def _gateway_decision_for_effect(effect: GatewayEffect, pidgin_decision: str) -> str:
    if pidgin_decision == "blocked":
        return "blocked"
    if effect.effect_type in {"external_tool_call", "shell_command"}:
        contract_steps = effect.payload["contract"]["steps"]
    else:
        contract_steps = []
    if effect.effect_type == "external_tool_call" and "comm.require_human_approval" in contract_steps:
        return "requires_approval"
    if effect.effect_type == "shell_command" and _contains_destructive_command(effect.payload):
        return "blocked"
    if "shell.require_human_approval" in contract_steps:
        return "requires_approval"
    return pidgin_decision


def _http_verdict(effect: GatewayEffect, response: dict[str, Any]) -> dict[str, Any]:
    pidgin_decision = str(response.get("status", "error"))
    gateway_decision = _gateway_decision_for_effect(effect=effect, pidgin_decision=pidgin_decision)
    event = response.get("event") if isinstance(response.get("event"), dict) else {}
    return {
        "effect_type": effect.effect_type,
        "actor": effect.actor,
        "event_id": str(event.get("event_id", "")),
        "pidgin_decision": pidgin_decision,
        "gateway_decision": gateway_decision,
        "http_status": response.get("http_status"),
        "executed": False,
        "reason": _reason_for_decision(gateway_decision),
    }


def _sidecar_result_summary(response: dict[str, Any]) -> dict[str, Any]:
    event = response.get("event") if isinstance(response.get("event"), dict) else {}
    trace = response.get("trace") if isinstance(response.get("trace"), dict) else {}
    summary = trace.get("summary") if isinstance(trace.get("summary"), dict) else {}
    return {
        "status": response.get("status"),
        "http_status": response.get("http_status"),
        "event_id": event.get("event_id"),
        "event_type": event.get("event_type"),
        "trace_id": trace.get("trace_id"),
        "blocked_event_count": summary.get("blocked_event_count"),
        "receipt_count": summary.get("receipt_count"),
    }


def _sidecar_request_for_effect(effect: GatewayEffect) -> tuple[str, dict[str, Any]]:
    base_payload = {
        "actor": effect.actor,
        "summary": effect.summary,
        "trace_id": f"trace-openclaw-http-{effect.effect_type}",
    }
    if effect.effect_type == "skill_install":
        return "/v1/preflight/skill", {
            **base_payload,
            "manifest": effect.payload["manifest"],
            "install_mode": effect.payload.get("install_mode", "proposed_only"),
        }
    if effect.effect_type == "memory_update":
        return "/v1/preflight/memory", {
            **base_payload,
            "before": effect.payload["before"],
            "after": effect.payload["after"],
        }
    if effect.effect_type in {"external_tool_call", "shell_command"}:
        return "/v1/preflight/contract", {**effect.payload, **base_payload}
    raise ValueError(f"Unsupported gateway effect: {effect.effect_type}")


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


def run_adapter(
    output_dir: str | Path | None = None,
    mode: str = "local",
    sidecar_url: str = "http://127.0.0.1:8765",
    sidecar_client: HttpPidgeonSidecarClient | None = None,
) -> dict[str, Any]:
    effects = OfflineOpenClawPlanner().plan()
    if mode == "local":
        result = AgentPidgeonGatewayAdapter().preflight_plan(effects)
    elif mode == "http":
        client = sidecar_client or HttpPidgeonSidecarClient(base_url=sidecar_url)
        result = AgentPidgeonHttpGatewayAdapter(sidecar_client=client).preflight_plan(effects)
    else:
        raise ValueError(f"Unsupported adapter mode: {mode}")
    _write_outputs(result=result, output_dir=output_dir)
    return result


def _write_outputs(result: dict[str, Any], output_dir: str | Path | None) -> None:
    if output_dir is None:
        return
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "openclaw_gateway_adapter_result.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    if result.get("trace"):
        (target_dir / "openclaw_gateway_adapter_trace.json").write_text(
            json.dumps(result["trace"], indent=2),
            encoding="utf-8",
        )
    if result.get("report"):
        (target_dir / "openclaw_gateway_adapter_report.txt").write_text(str(result["report"]), encoding="utf-8")


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OpenClaw-class Agent Pidgeon gateway adapter.")
    parser.add_argument("--mode", choices=["local", "http"], default="local")
    parser.add_argument("--sidecar-url", default="http://127.0.0.1:8765")
    parser.add_argument("--json", action="store_true", help="Print the complete adapter result as JSON.")
    parser.add_argument("--out-dir", default=None, help="Write adapter outputs to this directory.")
    args = parser.parse_args()

    result = run_adapter(output_dir=args.out_dir, mode=args.mode, sidecar_url=args.sidecar_url)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    for verdict in result["verdicts"]:
        print(
            f"{verdict['event_id']} {verdict['effect_type']}: "
            f"{verdict['gateway_decision']} executed={verdict['executed']}"
        )
    if result.get("report"):
        print("")
        print(result["report"])


if __name__ == "__main__":
    main()
