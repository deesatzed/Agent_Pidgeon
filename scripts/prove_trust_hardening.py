from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_pidgin.catalog import SeedCatalog  # noqa: E402
from agent_pidgin.cli import contract_from_preflight_payload  # noqa: E402
from agent_pidgin.flight_recorder import FlightRecorder, validate_trace_integrity  # noqa: E402
from agent_pidgin.http_sidecar import MAX_REQUEST_BODY_BYTES, PayloadTooLargeError, create_handler  # noqa: E402
from agent_pidgin.policy import enforce_policy, load_policy  # noqa: E402
from agent_pidgin.protocol import PidginMessage  # noqa: E402
from agent_pidgin.schema_validator import validate_pidgin_trace, validate_skill_manifest  # noqa: E402


class ProofMountGateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def ensure_repo_mounted(
        self,
        repo_id: str,
        mount_path: str,
        revision: str,
        hf_token: str | None = None,
    ) -> dict[str, str]:
        self.calls.append({"repo_id": repo_id, "mount_path": mount_path, "revision": revision})
        return {
            "repo_id": repo_id,
            "mount_path": mount_path,
            "revision": revision,
            "status": "mounted-via-proof-gateway",
        }


def main() -> None:
    proof = {
        "status": "passed",
        "checks": {
            "gateway_injection": _prove_gateway_injection(),
            "preflight_requires_artifact_provenance": _prove_preflight_requires_artifact_provenance(),
            "catalog_safety_metadata_policy": _prove_catalog_safety_metadata_policy(),
            "signed_manifest_schema": _prove_signed_manifest_schema(),
            "trace_hash_schema": _prove_trace_hash_schema(),
            "http_body_limit": _prove_http_body_limit(),
        },
    }
    print(json.dumps(proof, indent=2))


def _prove_gateway_injection() -> dict[str, Any]:
    gateway = ProofMountGateway()
    recorder = FlightRecorder(trace_id="trace-proof-gateway", mount_gateway=gateway)
    contract = _load_json("examples/agent_flight_recorder_demo/safe_tool_contract.json")

    event = recorder.record_contract_event(
        event_type="agent.tool.proposed_call",
        actor="proof-agent",
        summary="Prove injected gateway is used for contract resolution.",
        contract=contract,
    )
    trace = recorder.trace()

    _assert(event["decision"] == "resolved", "injected gateway contract should resolve")
    _assert(gateway.calls, "injected gateway was not called")
    _assert(event["receipts"], "resolved event should include receipts")
    _assert(validate_trace_integrity(trace)["status"] == "valid", "trace integrity should validate")
    return {
        "event_decision": event["decision"],
        "gateway_status": "mounted-via-proof-gateway",
        "gateway_call_count": len(gateway.calls),
        "receipt_count": len(event["receipts"]),
        "trace_integrity": "valid",
    }


def _prove_preflight_requires_artifact_provenance() -> dict[str, Any]:
    payload = _load_json("examples/openclaw_class/external_email_tool_contract.json")
    contract = contract_from_preflight_payload(payload)
    missing_artifact_payload = {
        "correlation_id": "proof-missing-artifact",
        "contract": {
            "steps": ["comm.send_external_message"],
            "target_language": "python",
        },
    }

    blocked_message = ""
    try:
        contract_from_preflight_payload(missing_artifact_payload)
    except ValueError as exc:
        blocked_message = str(exc)

    _assert(blocked_message, "preflight payload without artifact provenance should fail")
    _assert(contract["artifact"]["revision"] == "a" * 40, "normalized contract should preserve fixture revision")
    return {
        "valid_fixture_revision": contract["artifact"]["revision"],
        "missing_artifact_error": blocked_message,
    }


def _prove_catalog_safety_metadata_policy() -> dict[str, Any]:
    payload = _load_json("examples/openclaw_class/external_email_tool_contract.json")
    contract = contract_from_preflight_payload(payload)
    message = PidginMessage.from_dict(contract)
    findings = enforce_policy(message, load_policy(), catalog=SeedCatalog.load_default())
    codes = [finding.code for finding in findings]

    _assert("SENSITIVE_POINTER_RECEIPTS_REQUIRED" in codes, "catalog safety metadata did not trigger receipts")
    return {
        "pointer": "comm.send_external_message",
        "finding_codes": codes,
    }


def _prove_signed_manifest_schema() -> dict[str, Any]:
    invalid_manifest = {
        "skill_id": "trusted/proof-skill",
        "name": "Proof Skill",
        "version": "1.0.0",
        "publisher": {"id": "trusted", "name": "Trusted Publisher"},
        "signed": True,
        "permissions": [{"kind": "network", "target": "tickets.internal", "access": "read"}],
        "capabilities": ["json.parse"],
    }
    valid_manifest = dict(invalid_manifest)
    valid_manifest["signature"] = {"key_id": "key-trusted-001", "algorithm": "ed25519", "value": "proof"}

    blocked_message = ""
    try:
        validate_skill_manifest(invalid_manifest)
    except ValueError as exc:
        blocked_message = str(exc)

    validate_skill_manifest(valid_manifest)
    _assert(blocked_message, "signed manifest without signature should fail schema validation")
    return {
        "unsigned_signature_claim_error": blocked_message,
        "valid_signed_manifest": "accepted",
    }


def _prove_trace_hash_schema() -> dict[str, Any]:
    trace = {
        "pidgin_version": "0.1",
        "trace_id": "trace-proof-missing-event-hash",
        "status": "completed",
        "generated_at": "2026-05-07T12:00:00Z",
        "events": [
            {
                "event_id": "evt-0001",
                "parent_event_id": None,
                "event_type": "agent.goal.received",
                "actor": "proof-agent",
                "timestamp": "2026-05-07T12:00:00Z",
                "summary": "Missing event hash should fail.",
                "decision": "observed",
                "payload": {},
                "payload_hash": "a" * 64,
                "previous_event_hash": None,
            }
        ],
        "trace_hash": "b" * 64,
    }

    blocked_message = ""
    try:
        validate_pidgin_trace(trace)
    except ValueError as exc:
        blocked_message = str(exc)

    _assert(blocked_message, "trace event without event_hash should fail schema validation")
    return {"missing_event_hash_error": blocked_message}


def _prove_http_body_limit() -> dict[str, Any]:
    handler_type = create_handler()
    handler = object.__new__(handler_type)
    handler.headers = {"content-length": str(MAX_REQUEST_BODY_BYTES + 1)}
    handler.rfile = BytesIO(b"{}")

    blocked_message = ""
    try:
        handler._read_json()
    except PayloadTooLargeError as exc:
        blocked_message = str(exc)

    _assert(blocked_message, "oversized HTTP body should be rejected before read")
    return {
        "limit_bytes": MAX_REQUEST_BODY_BYTES,
        "oversized_error": blocked_message,
    }


def _load_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    main()
