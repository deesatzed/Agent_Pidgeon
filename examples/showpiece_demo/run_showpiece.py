from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.config import PidginConfig
from agent_pidgin.demo import LocalMountGateway
from agent_pidgin.llm_authoring import draft_contract
from agent_pidgin.policy import enforce_policy, findings_to_dicts, load_policy
from agent_pidgin.protocol import PidginMessage
from agent_pidgin.schema_validator import validate_pidgin_message
from agent_pidgin.semantic_diff import diff_contracts
from agent_pidgin.service import PidginReceiverService

SHOWPIECE_REPO = "waynesatz/agent-pidgin-data"
SHOWPIECE_REVISION = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
REQUIRED_SHOWPIECE_STEPS = [
    "str.trim",
    "str.normalize_unicode",
    "clinical.phi.scrub",
    "clinical.negation.preserve",
    "clinical.uncertainty.annotate",
    "agent.attach_receipts",
    "agent.require_evidence",
]


def run_showpiece(live_llm: bool = False) -> dict[str, Any]:
    demo_dir = Path(__file__).resolve().parent
    request_text = (demo_dir / "plain_language_request.txt").read_text(encoding="utf-8").strip()
    catalog = SeedCatalog.load_default()
    policy = load_policy()

    draft_result, authoring_status = _draft_showpiece_contract(
        request_text=request_text,
        catalog=catalog,
        live_llm=live_llm,
    )
    safe_contract = _prepare_showpiece_contract(draft_result["contract"])

    validation = _validate_contract(safe_contract)
    policy_findings = _policy_findings(safe_contract, policy)
    service = PidginReceiverService(
        mount_gateway=LocalMountGateway(),
        catalog=catalog,
        default_mount_root=PidginConfig.from_env().mount_root,
    )
    resolution = service.resolve_message(safe_contract, config=PidginConfig.from_env(), policy=policy)

    unsafe_contract = json.loads((demo_dir / "unsafe_contract.json").read_text(encoding="utf-8"))
    unsafe_policy_findings = _policy_findings(unsafe_contract, policy)
    unsafe_diff = diff_contracts(safe_contract, unsafe_contract, catalog=catalog)

    selected_pointer_summaries = [catalog.pointer_summary(pointer) for pointer in safe_contract["steps"]]
    return {
        "status": "showpiece_completed",
        "mode": authoring_status["mode"],
        "plain_language_request": request_text,
        "draft": {
            "status": draft_result["status"],
            "authoring": authoring_status,
            "llm_proposal": draft_result["llm_proposal"],
            "contract": safe_contract,
        },
        "schema_validation": validation,
        "policy": {
            "status": "checked",
            "findings": policy_findings,
            "error_count": sum(1 for finding in policy_findings if finding["severity"] == "error"),
            "warning_count": sum(1 for finding in policy_findings if finding["severity"] == "warning"),
        },
        "resolution": resolution,
        "unsafe_change_review": {
            "unsafe_contract": unsafe_contract,
            "policy_findings": unsafe_policy_findings,
            "diff": unsafe_diff,
        },
        "catalog": {
            "catalog_hash": catalog.catalog_hash(),
            "sources": catalog.summary()["sources"],
            "selected_pointers": selected_pointer_summaries,
        },
        "novice_expectations": {
            "what_the_app_does": (
                "It turns a compact semantic contract into an auditable implementation plan with receipts."
            ),
            "what_it_does_not_do": "It does not execute the returned implementation strings.",
            "why_you_want_it": (
                "It lets agents agree on meaning using trusted catalogs instead of vague prompts or invented code."
            ),
            "benefit": (
                "A reviewer can see the schema result, policy warnings, catalog hashes, artifact revision, "
                "resolved pointers, and per-step receipts before any downstream system acts."
            ),
        },
    }


def _draft_showpiece_contract(
    request_text: str,
    catalog: SeedCatalog,
    live_llm: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        draft_result = draft_contract(
            request_text,
            artifact_repo=SHOWPIECE_REPO,
            artifact_revision=SHOWPIECE_REVISION,
            catalog=catalog,
            transport=None if live_llm else _offline_authoring_transport,
        )
    except Exception as exc:
        if not live_llm:
            raise
        draft_result = draft_contract(
            request_text,
            artifact_repo=SHOWPIECE_REPO,
            artifact_revision=SHOWPIECE_REVISION,
            catalog=catalog,
            transport=_offline_authoring_transport,
        )
        return draft_result, {
            "mode": "live_llm_with_fixture_fallback",
            "live_llm_status": "rejected",
            "fallback": "offline_fixture",
            "reason": str(exc),
        }

    return draft_result, {
        "mode": "live_llm" if live_llm else "offline_fixture",
        "live_llm_status": "accepted" if live_llm else "not_requested",
        "fallback": None,
        "reason": "",
    }


def _offline_authoring_transport(_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "steps": REQUIRED_SHOWPIECE_STEPS,
        "rationale": "Use known safety and provenance pointers for clinical-note preparation.",
        "warnings": [
            "This is resolution only, not clinical decision support.",
            "Resolved implementation strings must not be executed directly.",
        ],
    }


def _prepare_showpiece_contract(contract: dict[str, Any]) -> dict[str, Any]:
    prepared = deepcopy(contract)
    prepared["message_id"] = "msg-showpiece-safe-001"
    prepared["created_at"] = "2026-05-07T12:00:00Z"
    prepared["artifact"] = {
        "kind": "repo",
        "repo": SHOWPIECE_REPO,
        "revision": SHOWPIECE_REVISION,
    }

    steps = list(prepared["steps"])
    guardrail_added = [step for step in REQUIRED_SHOWPIECE_STEPS if step not in steps]
    steps.extend(guardrail_added)
    prepared["steps"] = steps

    metadata = dict(prepared.get("metadata", {}))
    metadata.update(
        {
            "demo": "showpiece semantic contract",
            "not_clinical_decision_support": True,
            "showpiece_guardrail_added_steps": guardrail_added,
        }
    )
    prepared["metadata"] = metadata
    validate_pidgin_message(prepared)
    return prepared


def _validate_contract(contract: dict[str, Any]) -> dict[str, str]:
    validate_pidgin_message(contract)
    return {
        "status": "valid",
        "message_id": str(contract["message_id"]),
        "schema": "schemas/pidgin-message.schema.json",
    }


def _policy_findings(contract: dict[str, Any], policy: Any) -> list[dict[str, str]]:
    validate_pidgin_message(contract)
    return findings_to_dicts(enforce_policy(PidginMessage.from_dict(contract), policy))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Agent Pidgin semantic resolver showpiece.")
    parser.add_argument("--live-llm", action="store_true", help="Use OpenRouter for the authoring draft.")
    parser.add_argument("--json", action="store_true", help="Print the complete JSON showpiece result.")
    args = parser.parse_args()

    result = run_showpiece(live_llm=args.live_llm)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("Agent Pidgin showpiece")
    print(f"Status: {result['status']}")
    print(f"Mode: {result['mode']}")
    print(f"Schema: {result['schema_validation']['status']}")
    print(f"Policy: {result['policy']['error_count']} errors, {result['policy']['warning_count']} warnings")
    print(f"Resolution: {result['resolution']['status']}")
    print(f"Resolved steps: {len(result['resolution']['resolution']['resolved_steps'])}")
    print(f"Receipts: {len(result['resolution']['resolution']['receipts'])}")
    print(f"Unsafe change risk: {result['unsafe_change_review']['diff']['risk_level']}")
    print(f"Catalog hash: {result['catalog']['catalog_hash']}")


if __name__ == "__main__":
    main()
