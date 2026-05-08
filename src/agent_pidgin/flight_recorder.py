from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.config import PidginConfig
from agent_pidgin.constants import PIDGIN_PROTOCOL_VERSION
from agent_pidgin.domain_guard import evaluate_prompt_boundary
from agent_pidgin.hash_utils import sha256_digest
from agent_pidgin.mount_gateway import build_mount_gateway
from agent_pidgin.policy import PidginPolicy, load_policy
from agent_pidgin.schema_validator import validate_pidgin_message, validate_pidgin_trace
from agent_pidgin.semantic_diff import diff_contracts
from agent_pidgin.service import PidginReceiverService
from agent_pidgin.skill_preflight import verify_skill_manifest


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FlightRecorder:
    trace_id: str = field(default_factory=lambda: f"trace-{uuid4()}")
    catalog: SeedCatalog = field(default_factory=SeedCatalog.load_default)
    policy: PidginPolicy = field(default_factory=load_policy)
    config: PidginConfig = field(default_factory=PidginConfig.from_env)
    mount_gateway: Any | None = None
    mount_gateway_mode: str = "simulated"
    events: list[dict[str, Any]] = field(default_factory=list)
    _cached_service: PidginReceiverService | None = field(default=None, init=False, repr=False)

    def record_event(
        self,
        event_type: str,
        actor: str,
        summary: str,
        payload: dict[str, Any] | None = None,
        parent_event_id: str | None = None,
        decision: str = "observed",
    ) -> dict[str, Any]:
        event_payload = payload or {}
        event = {
            "event_id": f"evt-{len(self.events) + 1:04d}",
            "parent_event_id": parent_event_id,
            "event_type": event_type,
            "actor": actor,
            "timestamp": utc_now(),
            "summary": summary,
            "decision": decision,
            "payload": event_payload,
            "payload_hash": sha256_digest(event_payload),
            "policy_findings": [],
            "receipt_ids": [],
        }
        return self._append_event(event)

    def record_memory_update(
        self,
        actor: str,
        summary: str,
        before: dict[str, Any],
        after: dict[str, Any],
        parent_event_id: str | None = None,
        approved_by: str | None = None,
    ) -> dict[str, Any]:
        memory_diff = diff_memory_guardrails(before=before, after=after, approved_by=approved_by)
        decision = "blocked" if memory_diff["risk_level"] == "high" else "observed"
        if memory_diff["risk_level"] == "medium":
            decision = "drift_detected"
        payload = {
            "before": before,
            "after": after,
            "approved_by": approved_by,
        }
        event = {
            "event_id": f"evt-{len(self.events) + 1:04d}",
            "parent_event_id": parent_event_id,
            "event_type": "agent.memory.proposed_update",
            "actor": actor,
            "timestamp": utc_now(),
            "summary": summary,
            "decision": decision,
            "payload": payload,
            "payload_hash": sha256_digest(payload),
            "policy_findings": [],
            "receipt_ids": [],
            "semantic_diff": memory_diff,
        }
        return self._append_event(event)

    def record_contract_event(
        self,
        event_type: str,
        actor: str,
        summary: str,
        contract: dict[str, Any],
        previous_contract: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        parent_event_id: str | None = None,
    ) -> dict[str, Any]:
        validate_pidgin_message(contract)
        resolution = self._service().resolve_message(contract, config=self.config, policy=self.policy)
        semantic_diff = diff_contracts(previous_contract, contract, catalog=self.catalog) if previous_contract else None
        decision = _decision_for_resolution(resolution, semantic_diff)
        event_payload = payload or {}
        event = {
            "event_id": f"evt-{len(self.events) + 1:04d}",
            "parent_event_id": parent_event_id,
            "event_type": event_type,
            "actor": actor,
            "timestamp": utc_now(),
            "summary": summary,
            "decision": decision,
            "payload": event_payload,
            "payload_hash": sha256_digest(event_payload),
            "contract_hash": sha256_digest(contract),
            "contract": contract,
            "policy_findings": resolution.get("policy_findings", []),
            "resolution_status": str(resolution.get("status", "")),
            "receipt_ids": _receipt_ids(resolution),
            "receipts": _receipts(resolution),
        }
        if semantic_diff is not None:
            event["semantic_diff"] = semantic_diff
            event["previous_contract_hash"] = sha256_digest(previous_contract)
            event["previous_contract"] = previous_contract
        return self._append_event(event)

    def record_skill_install(
        self,
        actor: str,
        summary: str,
        manifest: dict[str, Any],
        parent_event_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = verify_skill_manifest(manifest)
        decision = "blocked" if result["status"] == "blocked" else "resolved"
        event_payload = payload or {}
        event = {
            "event_id": f"evt-{len(self.events) + 1:04d}",
            "parent_event_id": parent_event_id,
            "event_type": "agent.skill.proposed_install",
            "actor": actor,
            "timestamp": utc_now(),
            "summary": summary,
            "decision": decision,
            "payload": event_payload,
            "payload_hash": sha256_digest(event_payload),
            "skill_manifest_hash": result["manifest_hash"],
            "skill_id": result["skill_id"],
            "policy_findings": result["findings"],
            "receipt_ids": [],
        }
        return self._append_event(event)

    def record_prompt_boundary_check(
        self,
        actor: str,
        summary: str,
        prompt: str,
        domain_policy: dict[str, Any],
        conversation_signals: list[dict[str, Any]] | None = None,
        parent_event_id: str | None = None,
    ) -> dict[str, Any]:
        result = evaluate_prompt_boundary(
            prompt,
            domain_policy,
            conversation_signals=conversation_signals,
        )
        decision = "blocked" if result["status"] in {"blocked", "escalate"} else "resolved"
        payload = {
            "domain": result["domain"],
            "topic": result["topic"],
            "prompt_hash": result["prompt_hash"],
            "policy_hash": result["policy_hash"],
            "status": result["status"],
            "autonomy_tier": result["autonomy_tier"],
            "required_response_controls": result["required_response_controls"],
            "conversation_signal_hashes": [sha256_digest(signal) for signal in conversation_signals or []],
        }
        event = {
            "event_id": f"evt-{len(self.events) + 1:04d}",
            "parent_event_id": parent_event_id,
            "event_type": "agent.prompt.boundary_check",
            "actor": actor,
            "timestamp": utc_now(),
            "summary": summary,
            "decision": decision,
            "payload": payload,
            "payload_hash": sha256_digest(payload),
            "policy_findings": result["findings"],
            "receipt_ids": [],
            "domain_guard": result,
        }
        return self._append_event(event)

    def trace(self, status: str | None = None) -> dict[str, Any]:
        trace_status = status or (
            "blocked" if any(event["decision"] == "blocked" for event in self.events) else "completed"
        )
        trace = {
            "pidgin_version": PIDGIN_PROTOCOL_VERSION,
            "trace_id": self.trace_id,
            "status": trace_status,
            "generated_at": utc_now(),
            "events": self.events,
            "summary": self.summary(status=trace_status),
            "trace_hash": sha256_digest([event["event_hash"] for event in self.events]),
        }
        validate_pidgin_trace(trace)
        integrity = validate_trace_integrity(trace)
        if integrity["status"] != "valid":
            raise ValueError(f"Trace integrity failed: {integrity['error']}")
        return trace

    def summary(self, status: str | None = None) -> dict[str, Any]:
        policy_error_events = [
            event
            for event in self.events
            if any(finding.get("severity") == "error" for finding in event.get("policy_findings", []))
        ]
        drift_events = [event for event in self.events if _event_has_drift(event)]
        return {
            "status": status or "recording",
            "event_count": len(self.events),
            "blocked_event_count": sum(1 for event in self.events if event["decision"] == "blocked"),
            "policy_error_event_count": len(policy_error_events),
            "semantic_drift_event_count": len(drift_events),
            "integrity": "hash_chained",
            "receipt_count": sum(len(event.get("receipt_ids", [])) for event in self.events),
        }

    def replay_lines(self) -> list[str]:
        lines = [f"Trace {self.trace_id}"]
        for event in self.events:
            line = f"{event['event_id']} {event['event_type']} [{event['decision']}]: {event['summary']}"
            if event.get("receipt_ids"):
                line += f" receipts={len(event['receipt_ids'])}"
            if event.get("semantic_diff"):
                line += f" diff_risk={event['semantic_diff']['risk_level']}"
            if any(finding.get("severity") == "error" for finding in event.get("policy_findings", [])):
                codes = ",".join(
                    finding["code"] for finding in event["policy_findings"] if finding.get("severity") == "error"
                )
                line += f" policy_errors={codes}"
            lines.append(line)
        return lines

    def _service(self) -> PidginReceiverService:
        if self._cached_service is None:
            self._cached_service = PidginReceiverService(
                mount_gateway=self.mount_gateway or build_mount_gateway(self.config, mode=self.mount_gateway_mode),
                catalog=self.catalog,
                default_mount_root=self.config.mount_root,
            )
        return self._cached_service

    def _append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event["previous_event_hash"] = self.events[-1]["event_hash"] if self.events else None
        event["event_hash"] = _event_hash(event)
        self.events.append(event)
        return event


def build_trace_report(trace: dict[str, Any]) -> str:
    validate_pidgin_trace(trace)
    lines = [
        "Agent Pidgeon Flight Recorder",
        f"Trace: {trace['trace_id']}",
        f"Status: {trace['status']}",
        f"Events: {trace['summary']['event_count']}",
        f"Blocked events: {trace['summary']['blocked_event_count']}",
        f"Semantic drift events: {trace['summary']['semantic_drift_event_count']}",
        f"Receipts: {trace['summary']['receipt_count']}",
        f"Trace hash: {trace['trace_hash']}",
        "",
        "Replay:",
    ]
    for event in trace["events"]:
        line = f"- {event['event_id']} {event['event_type']} [{event['decision']}]: {event['summary']}"
        if event.get("semantic_diff"):
            line += f" (diff risk: {event['semantic_diff']['risk_level']})"
        if event.get("policy_findings"):
            codes = ", ".join(finding["code"] for finding in event["policy_findings"])
            line += f" (policy: {codes})"
        if event.get("receipt_ids"):
            line += f" (receipts: {len(event['receipt_ids'])})"
        lines.append(line)
    return "\n".join(lines)


def _decision_for_resolution(resolution: dict[str, Any], semantic_diff: dict[str, Any] | None) -> str:
    if resolution.get("status") == "policy_failed":
        return "blocked"
    if semantic_diff is not None and semantic_diff.get("risk_level") == "high":
        return "blocked"
    if semantic_diff is not None and semantic_diff.get("risk_level") == "medium":
        return "drift_detected"
    return "resolved"


def _receipt_ids(resolution: dict[str, Any]) -> list[str]:
    receipts = resolution.get("resolution", {}).get("receipts", [])
    if not isinstance(receipts, list):
        return []
    return [str(receipt["receipt_id"]) for receipt in receipts if isinstance(receipt, dict) and "receipt_id" in receipt]


def _receipts(resolution: dict[str, Any]) -> list[dict[str, Any]]:
    receipts = resolution.get("resolution", {}).get("receipts", [])
    if not isinstance(receipts, list):
        return []
    return [dict(receipt) for receipt in receipts if isinstance(receipt, dict)]


def validate_trace_integrity(trace: dict[str, Any]) -> dict[str, str]:
    try:
        validate_pidgin_trace(trace)
        previous_hash = None
        for event in trace["events"]:
            if event.get("previous_event_hash") != previous_hash:
                return {
                    "status": "invalid",
                    "error": f"previous_event_hash mismatch at {event.get('event_id')}",
                }
            expected_hash = _event_hash(event)
            if event.get("event_hash") != expected_hash:
                return {
                    "status": "invalid",
                    "error": f"event_hash mismatch at {event.get('event_id')}",
                }
            previous_hash = expected_hash
        expected_trace_hash = sha256_digest([event["event_hash"] for event in trace["events"]])
        if trace.get("trace_hash") != expected_trace_hash:
            return {
                "status": "invalid",
                "error": "trace_hash mismatch",
            }
    except Exception as exc:
        return {
            "status": "invalid",
            "error": str(exc),
        }
    return {
        "status": "valid",
        "error": "",
    }


def diff_memory_guardrails(
    before: dict[str, Any],
    after: dict[str, Any],
    approved_by: str | None = None,
) -> dict[str, Any]:
    added = []
    removed = []
    changes = []
    risk_notes = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) == after.get(key):
            continue
        if key not in before:
            added.append(key)
            continue
        if key not in after:
            removed.append(key)
            continue
        change = {"field": key, "left": before.get(key), "right": after.get(key)}
        changes.append(change)
        if _weakens_guardrail(key, before.get(key), after.get(key)) and approved_by is None:
            risk_notes.append(f"Memory guardrail weakened without approval: {key}")

    risk_level = "high" if risk_notes else "low"
    return {
        "added": added,
        "removed": removed,
        "changed": changes,
        "risk_level": risk_level,
        "risk_notes": risk_notes,
        "contract_changes": [],
    }


def _weakens_guardrail(key: str, before_value: Any, after_value: Any) -> bool:
    if ("allowed" in key or key.startswith("may_")) and before_value is False and after_value is True:
        return True
    if "required" in key and before_value is True and after_value is False:
        return True
    return False


def _event_has_drift(event: dict[str, Any]) -> bool:
    return event.get("semantic_diff", {}).get("risk_level") in {"medium", "high"}


def _event_hash(event: dict[str, Any]) -> str:
    hashable_event = {key: value for key, value in event.items() if key != "event_hash"}
    return sha256_digest(hashable_event)
