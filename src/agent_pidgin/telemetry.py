from __future__ import annotations

from datetime import datetime
from typing import Any

from agent_pidgin.schema_validator import validate_pidgin_trace


def build_otlp_trace_export(trace: dict[str, Any]) -> dict[str, Any]:
    """Build dependency-free OTLP/JSON-style spans from a Pidgin trace."""
    validate_pidgin_trace(trace)
    summary = trace.get("summary", {})
    trace_id = _trace_id(trace)
    spans = [_span_for_event(trace_id=trace_id, trace=trace, event=event) for event in trace["events"]]
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        _string_attr("service.name", "agent-pidgin"),
                        _string_attr("service.namespace", "semantic-contract-resolver"),
                        _string_attr("pidgeon.trace_id", str(trace["trace_id"])),
                        _string_attr("pidgeon.trace_status", str(trace["status"])),
                        _string_attr("pidgeon.trace_hash", str(trace["trace_hash"])),
                        _int_attr("pidgeon.event_count", int(summary.get("event_count", 0))),
                        _int_attr("pidgeon.blocked_event_count", int(summary.get("blocked_event_count", 0))),
                        _int_attr("pidgeon.receipt_count", int(summary.get("receipt_count", 0))),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name": "agent_pidgin.flight_recorder",
                            "version": str(trace["pidgin_version"]),
                        },
                        "spans": spans,
                    }
                ],
            }
        ]
    }


def _span_for_event(trace_id: str, trace: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    policy_codes = [
        str(finding.get("code"))
        for finding in event.get("policy_findings", [])
        if isinstance(finding, dict) and finding.get("code")
    ]
    attributes = [
        _string_attr("pidgeon.trace_id", str(trace["trace_id"])),
        _string_attr("pidgeon.event_id", str(event["event_id"])),
        _string_attr("pidgeon.event_type", str(event["event_type"])),
        _string_attr("pidgeon.actor", str(event["actor"])),
        _string_attr("pidgeon.decision", str(event["decision"])),
        _string_attr("pidgeon.summary", str(event["summary"])),
        _string_attr("pidgeon.payload_hash", str(event["payload_hash"])),
        _string_attr("pidgeon.event_hash", str(event["event_hash"])),
        _bool_attr("pidgeon.blocked", event["decision"] == "blocked"),
        _int_attr("pidgeon.receipt_count", len(event.get("receipt_ids", []))),
    ]
    if event.get("contract_hash"):
        attributes.append(_string_attr("pidgeon.contract_hash", str(event["contract_hash"])))
    if event.get("skill_id"):
        attributes.append(_string_attr("pidgeon.skill_id", str(event["skill_id"])))
    if event.get("skill_manifest_hash"):
        attributes.append(_string_attr("pidgeon.skill_manifest_hash", str(event["skill_manifest_hash"])))
    if policy_codes:
        attributes.append(_string_attr("pidgeon.policy_codes", ",".join(policy_codes)))
    if event.get("semantic_diff"):
        attributes.append(_string_attr("pidgeon.semantic_risk_level", str(event["semantic_diff"].get("risk_level"))))

    return {
        "traceId": trace_id,
        "spanId": str(event["event_hash"])[:16],
        "parentSpanId": _parent_span_id(event),
        "name": str(event["event_type"]),
        "kind": 1,
        "startTimeUnixNano": _timestamp_nanos(str(event["timestamp"])),
        "endTimeUnixNano": _timestamp_nanos(str(event["timestamp"])),
        "status": _span_status(event),
        "attributes": attributes,
    }


def _trace_id(trace: dict[str, Any]) -> str:
    return str(trace["trace_hash"])[:32]


def _parent_span_id(event: dict[str, Any]) -> str:
    previous_hash = event.get("previous_event_hash")
    return str(previous_hash)[:16] if previous_hash else ""


def _timestamp_nanos(timestamp: str) -> str:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return str(int(parsed.timestamp() * 1_000_000_000))


def _span_status(event: dict[str, Any]) -> dict[str, Any]:
    if event["decision"] == "blocked":
        return {"code": 2, "message": "blocked"}
    if event["decision"] == "drift_detected":
        return {"code": 2, "message": "semantic drift detected"}
    return {"code": 1}


def _string_attr(key: str, value: str) -> dict[str, Any]:
    return {"key": key, "value": {"stringValue": value}}


def _int_attr(key: str, value: int) -> dict[str, Any]:
    return {"key": key, "value": {"intValue": str(value)}}


def _bool_attr(key: str, value: bool) -> dict[str, Any]:
    return {"key": key, "value": {"boolValue": value}}
