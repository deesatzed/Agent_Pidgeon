from __future__ import annotations

from typing import Any

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.hash_utils import sha256_digest

SAFETY_SENSITIVE_PREFIXES = ("clinical.", "phi.")
CONTROL_GUARDRAIL_POINTERS = {
    "agent.attach_receipts",
    "agent.request_human_review",
    "agent.require_evidence",
    "agent.reject_untrusted_artifact",
}


def diff_step_lists(
    left_steps: list[str],
    right_steps: list[str],
    left_catalog: SeedCatalog | None = None,
    right_catalog: SeedCatalog | None = None,
    target_language: str = "python",
) -> dict[str, Any]:
    left_set = set(left_steps)
    right_set = set(right_steps)

    added = [step for step in right_steps if step not in left_set]
    removed = [step for step in left_steps if step not in right_set]
    changed = _changed_steps(
        sorted(left_set & right_set),
        left_catalog=left_catalog,
        right_catalog=right_catalog,
        target_language=target_language,
    )

    risk_notes = _risk_notes(removed=removed, changed=changed)
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "risk_level": _risk_level(risk_notes=risk_notes, changed=changed),
        "risk_notes": risk_notes,
    }


def diff_payload(payload: dict[str, Any], catalog: SeedCatalog | None = None) -> dict[str, Any]:
    left_contract = _contract_from_payload(payload, "left")
    right_contract = _contract_from_payload(payload, "right")
    target_language = str(
        payload.get("target_language")
        or left_contract.get("target_language")
        or right_contract.get("target_language")
        or "python"
    )
    step_diff = diff_step_lists(
        _steps_from_contract(left_contract),
        _steps_from_contract(right_contract),
        left_catalog=catalog,
        right_catalog=catalog,
        target_language=target_language,
    )
    contract_changes = _contract_changes(left_contract, right_contract)
    risk_notes = [*step_diff["risk_notes"], *_contract_risk_notes(contract_changes)]
    return {
        **step_diff,
        "contract_changes": contract_changes,
        "risk_notes": risk_notes,
        "risk_level": _risk_level(risk_notes=risk_notes, changed=step_diff["changed"]),
    }


def diff_contracts(
    left_contract: dict[str, Any],
    right_contract: dict[str, Any],
    catalog: SeedCatalog | None = None,
) -> dict[str, Any]:
    return diff_payload(
        {
            "left_contract": left_contract,
            "right_contract": right_contract,
        },
        catalog=catalog,
    )


def _contract_from_payload(payload: dict[str, Any], side: str) -> dict[str, Any]:
    contract_key = f"{side}_contract"
    if contract_key in payload and isinstance(payload[contract_key], dict):
        return payload[contract_key]
    return {
        "steps": _steps_from_payload(payload, side),
        "target_language": payload.get("target_language"),
    }


def _steps_from_contract(contract: dict[str, Any]) -> list[str]:
    steps = contract.get("steps")
    if not isinstance(steps, list) or not all(isinstance(step, str) for step in steps):
        raise ValueError("contract.steps must be a list of pointer strings")
    return steps


def _contract_changes(left_contract: dict[str, Any], right_contract: dict[str, Any]) -> list[dict[str, Any]]:
    changes = []
    for field in ["target_language", "pidgin_version"]:
        if left_contract.get(field) != right_contract.get(field):
            changes.append(
                {
                    "field": field,
                    "left": left_contract.get(field),
                    "right": right_contract.get(field),
                }
            )

    left_artifact = left_contract.get("artifact") if isinstance(left_contract.get("artifact"), dict) else {}
    right_artifact = right_contract.get("artifact") if isinstance(right_contract.get("artifact"), dict) else {}
    for field in ["kind", "repo", "revision"]:
        if left_artifact.get(field) != right_artifact.get(field):
            changes.append(
                {
                    "field": f"artifact.{field}",
                    "left": left_artifact.get(field),
                    "right": right_artifact.get(field),
                }
            )
    return changes


def _contract_risk_notes(contract_changes: list[dict[str, Any]]) -> list[str]:
    notes = []
    for change in contract_changes:
        if change["field"] == "artifact.revision":
            notes.append("Artifact revision changed; verify catalog and artifact provenance before reuse.")
        elif change["field"] == "artifact.repo":
            notes.append("Artifact repo changed; verify trust policy before reuse.")
        elif change["field"] == "target_language":
            notes.append("Target language changed; implementation selection may differ.")
    return notes


def _risk_level(risk_notes: list[str], changed: list[dict[str, str]]) -> str:
    if any(
        "Safety-sensitive" in note or "Control guardrail" in note or "Artifact repo changed" in note
        for note in risk_notes
    ):
        return "high"
    if risk_notes or changed:
        return "medium"
    return "low"


def _steps_from_payload(payload: dict[str, Any], side: str) -> list[str]:
    direct_key = f"{side}_steps"
    contract_key = f"{side}_contract"
    if direct_key in payload:
        steps = payload[direct_key]
    elif contract_key in payload and isinstance(payload[contract_key], dict):
        steps = payload[contract_key].get("steps")
    else:
        raise ValueError(f"Missing {direct_key} or {contract_key}.steps")

    if not isinstance(steps, list) or not all(isinstance(step, str) for step in steps):
        raise ValueError(f"{direct_key} must be a list of pointer strings")
    return steps


def _changed_steps(
    common_steps: list[str],
    left_catalog: SeedCatalog | None,
    right_catalog: SeedCatalog | None,
    target_language: str,
) -> list[dict[str, str]]:
    if left_catalog is None or right_catalog is None:
        return []

    changed = []
    for pointer in common_steps:
        left = left_catalog.get(pointer)
        right = right_catalog.get(pointer)
        if left.get("type_signature") != right.get("type_signature"):
            changed.append(
                {
                    "pointer": pointer,
                    "reason": "type_signature",
                    "left": str(left.get("type_signature")),
                    "right": str(right.get("type_signature")),
                }
            )
            continue

        left_impl = left.get("implementations", {}).get(target_language)
        right_impl = right.get("implementations", {}).get(target_language)
        if left_impl != right_impl:
            changed.append(
                {
                    "pointer": pointer,
                    "reason": "implementation_hash",
                    "left": sha256_digest(left_impl),
                    "right": sha256_digest(right_impl),
                }
            )
    return changed


def _risk_notes(removed: list[str], changed: list[dict[str, str]]) -> list[str]:
    notes = []
    for pointer in removed:
        if _is_safety_sensitive(pointer):
            notes.append(f"Safety-sensitive primitive removed from workflow: {pointer}")
        elif pointer in CONTROL_GUARDRAIL_POINTERS:
            notes.append(f"Control guardrail removed from workflow: {pointer}")

    for item in changed:
        pointer = item["pointer"]
        if _is_safety_sensitive(pointer):
            notes.append(f"Safety-sensitive primitive changed: {pointer} ({item['reason']})")
        elif pointer in CONTROL_GUARDRAIL_POINTERS:
            notes.append(f"Control guardrail changed: {pointer} ({item['reason']})")

    return notes


def _is_safety_sensitive(pointer: str) -> bool:
    return pointer.startswith(SAFETY_SENSITIVE_PREFIXES)
