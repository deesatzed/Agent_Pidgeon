from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.config import PidginConfig
from agent_pidgin.demo import LocalMountGateway, run_local_demo
from agent_pidgin.flight_recorder import FlightRecorder, build_trace_report
from agent_pidgin.hash_utils import hash_catalog_content
from agent_pidgin.llm_authoring import draft_contract, explain_contract, review_contract
from agent_pidgin.policy import enforce_policy, findings_to_dicts, has_policy_errors, load_policy
from agent_pidgin.protocol import PidginMessage
from agent_pidgin.schema_validator import validate_catalog, validate_pidgin_message, validate_pidgin_trace
from agent_pidgin.semantic_diff import diff_payload
from agent_pidgin.service import PidginReceiverService
from agent_pidgin.skill_preflight import verify_skill_manifest


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(run(argv))


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command is None:
        print(json.dumps(run_local_demo(), indent=2))
        return 0

    try:
        result = args.func(args)
    except Exception as exc:
        if getattr(args, "json", False):
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2), file=sys.stderr)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1

    if result is not None:
        print_result(result, as_json=getattr(args, "json", False))
    return _exit_code_for_result(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-pidgin")
    subparsers = parser.add_subparsers(dest="command")

    validate_message = subparsers.add_parser("validate-message")
    validate_message.add_argument("path")
    validate_message.add_argument("--json", action="store_true")
    validate_message.set_defaults(func=cmd_validate_message)

    validate_catalog_parser = subparsers.add_parser("validate-catalog")
    validate_catalog_parser.add_argument("path")
    validate_catalog_parser.add_argument("--json", action="store_true")
    validate_catalog_parser.set_defaults(func=cmd_validate_catalog)

    list_catalog = subparsers.add_parser("list-catalog")
    list_catalog.add_argument("--catalog", action="append", default=[])
    list_catalog.add_argument("--language", default=None)
    list_catalog.add_argument("--json", action="store_true")
    list_catalog.set_defaults(func=cmd_list_catalog)

    show_pointer = subparsers.add_parser("show-pointer")
    show_pointer.add_argument("pointer")
    show_pointer.add_argument("--catalog", action="append", default=[])
    show_pointer.add_argument("--json", action="store_true")
    show_pointer.set_defaults(func=cmd_show_pointer)

    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("path")
    resolve.add_argument("--catalog", action="append", default=[])
    resolve.add_argument("--policy", default=None)
    resolve.add_argument("--no-policy", action="store_true")
    resolve.add_argument("--json", action="store_true")
    resolve.set_defaults(func=cmd_resolve)

    hash_catalog = subparsers.add_parser("hash-catalog")
    hash_catalog.add_argument("path")
    hash_catalog.add_argument("--json", action="store_true")
    hash_catalog.set_defaults(func=cmd_hash_catalog)

    diff = subparsers.add_parser("diff")
    diff.add_argument("path")
    diff.add_argument("--catalog", action="append", default=[])
    diff.add_argument("--json", action="store_true")
    diff.set_defaults(func=cmd_diff)

    policy_check = subparsers.add_parser("policy-check")
    policy_check.add_argument("path")
    policy_check.add_argument("--policy", default=None)
    policy_check.add_argument("--json", action="store_true")
    policy_check.set_defaults(func=cmd_policy_check)

    author_contract = subparsers.add_parser("author-contract")
    author_contract.add_argument("description_path")
    author_contract.add_argument("--artifact-repo", required=True)
    author_contract.add_argument("--artifact-revision", required=True)
    author_contract.add_argument("--artifact-kind", default="repo")
    author_contract.add_argument("--target-language", default="python")
    author_contract.add_argument("--sender-id", default="agent-a")
    author_contract.add_argument("--receiver-id", default="agent-b")
    author_contract.add_argument("--catalog", action="append", default=[])
    author_contract.add_argument("--json", action="store_true")
    author_contract.set_defaults(func=cmd_author_contract)

    explain_contract_parser = subparsers.add_parser("explain-contract")
    explain_contract_parser.add_argument("path")
    explain_contract_parser.add_argument("--catalog", action="append", default=[])
    explain_contract_parser.add_argument("--json", action="store_true")
    explain_contract_parser.set_defaults(func=cmd_explain_contract)

    review_contract_parser = subparsers.add_parser("review-contract")
    review_contract_parser.add_argument("path")
    review_contract_parser.add_argument("--catalog", action="append", default=[])
    review_contract_parser.add_argument("--json", action="store_true")
    review_contract_parser.set_defaults(func=cmd_review_contract)

    preflight_tool = subparsers.add_parser("preflight-tool")
    preflight_tool.add_argument("contract_path")
    preflight_tool.add_argument("--previous-contract", default=None)
    preflight_tool.add_argument("--actor", default="openclaw-agent")
    preflight_tool.add_argument("--tool-name", default="unknown")
    preflight_tool.add_argument("--channel", default="local")
    preflight_tool.add_argument("--summary", default="Preflight proposed tool call.")
    preflight_tool.add_argument("--json", action="store_true")
    preflight_tool.set_defaults(func=cmd_preflight_tool)

    record_memory = subparsers.add_parser("record-memory-update")
    record_memory.add_argument("path")
    record_memory.add_argument("--actor", default="openclaw-agent")
    record_memory.add_argument("--summary", default="Preflight proposed memory update.")
    record_memory.add_argument("--approved-by", default=None)
    record_memory.add_argument("--json", action="store_true")
    record_memory.set_defaults(func=cmd_record_memory_update)

    verify_skill = subparsers.add_parser("verify-skill")
    verify_skill.add_argument("manifest_path")
    verify_skill.add_argument("--json", action="store_true")
    verify_skill.set_defaults(func=cmd_verify_skill)

    render_trace = subparsers.add_parser("render-trace")
    render_trace.add_argument("trace_path")
    render_trace.add_argument("--json", action="store_true")
    render_trace.set_defaults(func=cmd_render_trace)

    return parser


def cmd_validate_message(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.path)
    validate_pidgin_message(payload)
    return {"status": "valid", "path": args.path}


def cmd_validate_catalog(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.path)
    validate_catalog(payload)
    SeedCatalog.from_file(args.path)
    return {"status": "valid", "path": args.path}


def cmd_list_catalog(args: argparse.Namespace) -> dict[str, Any]:
    catalog = load_catalog_from_args(args)
    summary = catalog.summary()
    if args.language:
        summary["language_filter"] = args.language
        summary["pointers"] = catalog.pointers_for_language(args.language)
    return summary


def cmd_show_pointer(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pointer_found",
        "concept": load_catalog_from_args(args).pointer_summary(args.pointer),
    }


def cmd_resolve(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.path)
    validate_pidgin_message(payload)
    policy = None if args.no_policy else load_policy(args.policy)
    config = PidginConfig.from_env()
    service = PidginReceiverService(
        mount_gateway=LocalMountGateway(),
        catalog=load_catalog_from_args(args),
        default_mount_root=config.mount_root,
    )
    return service.resolve_message(payload, config=config, policy=policy)


def cmd_hash_catalog(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.path)
    validate_catalog(payload)
    return {
        "status": "hashed",
        "path": args.path,
        "catalog_hash": hash_catalog_content(payload),
    }


def cmd_diff(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.path)
    return {
        "status": "diffed",
        "diff": diff_payload(payload, catalog=load_catalog_from_args(args)),
    }


def cmd_policy_check(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.path)
    validate_pidgin_message(payload)
    message = PidginMessage.from_dict(payload)
    findings = enforce_policy(message, load_policy(args.policy))
    status = "policy_failed" if has_policy_errors(findings) else "policy_passed"
    return {
        "status": status,
        "policy_findings": findings_to_dicts(findings),
    }


def cmd_author_contract(args: argparse.Namespace) -> dict[str, Any]:
    description = Path(args.description_path).read_text(encoding="utf-8")
    return draft_contract(
        description=description,
        artifact_repo=args.artifact_repo,
        artifact_revision=args.artifact_revision,
        artifact_kind=args.artifact_kind,
        target_language=args.target_language,
        sender_id=args.sender_id,
        receiver_id=args.receiver_id,
        catalog=load_catalog_from_args(args),
    )


def cmd_explain_contract(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.path)
    return explain_contract(payload, catalog=load_catalog_from_args(args))


def cmd_review_contract(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.path)
    return review_contract(payload, catalog=load_catalog_from_args(args))


def cmd_preflight_tool(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.contract_path)
    contract = contract_from_preflight_payload(payload)
    previous_contract = (
        contract_from_preflight_payload(read_json(args.previous_contract)) if args.previous_contract else None
    )
    recorder = FlightRecorder()
    event = recorder.record_contract_event(
        event_type="agent.tool.proposed_call",
        actor=args.actor,
        summary=args.summary,
        contract=contract,
        previous_contract=previous_contract,
        payload={
            "tool_name": payload.get("tool_name", args.tool_name) if isinstance(payload, dict) else args.tool_name,
            "channel": payload.get("channel", args.channel) if isinstance(payload, dict) else args.channel,
        },
    )
    return {
        "status": event["decision"],
        "event": event,
        "trace": recorder.trace(),
    }


def cmd_record_memory_update(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.path)
    before = payload.get("before", payload.get("memory_before"))
    after = payload.get("after", payload.get("memory_after"))
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("memory update payload must include object fields: before, after")
    recorder = FlightRecorder()
    event = recorder.record_memory_update(
        actor=args.actor,
        summary=str(payload.get("summary") or args.summary),
        before=before,
        after=after,
        approved_by=args.approved_by or payload.get("approved_by"),
    )
    return {
        "status": event["decision"],
        "event": event,
        "trace": recorder.trace(),
    }


def cmd_verify_skill(args: argparse.Namespace) -> dict[str, Any]:
    payload = read_json(args.manifest_path)
    manifest = payload.get("manifest", payload) if isinstance(payload, dict) else payload
    return verify_skill_manifest(manifest)


def cmd_render_trace(args: argparse.Namespace) -> dict[str, Any] | str:
    trace = read_json(args.trace_path)
    validate_pidgin_trace(trace)
    report = build_trace_report(trace)
    if args.json:
        return {
            "status": "rendered",
            "report": report,
        }
    return report


def read_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as payload_file:
        return json.load(payload_file)


def load_catalog_from_args(args: argparse.Namespace) -> SeedCatalog:
    catalog_paths = getattr(args, "catalog", None) or []
    if catalog_paths:
        return SeedCatalog.from_files([Path(path) for path in catalog_paths])
    return SeedCatalog.load_default()


def contract_from_preflight_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if "pidgin_version" in payload:
        return payload
    contract = payload.get("contract")
    if not isinstance(contract, dict):
        raise ValueError("preflight payload must be a Pidgin contract or include a contract object")
    if "pidgin_version" in contract:
        return contract
    if "steps" not in contract:
        raise ValueError("preflight contract object must include steps")
    config = PidginConfig.from_env()
    return {
        "pidgin_version": "0.1",
        "message_type": "resolve",
        "message_id": str(payload.get("correlation_id", "msg-openclaw-preflight")),
        "sender_id": str(payload.get("actor", "openclaw-agent")),
        "receiver_id": "agent-pidgeon",
        "target_language": str(contract.get("target_language", "python")),
        "artifact": {
            "kind": str(contract.get("artifact", {}).get("kind", config.artifact_kind)),
            "repo": str(contract.get("artifact", {}).get("repo", config.artifact_repo)),
            "revision": str(contract.get("artifact", {}).get("revision", "a" * 40)),
        },
        "steps": contract["steps"],
        "created_at": str(payload.get("created_at", "2026-05-07T12:00:00Z")),
        "metadata": {
            "source": "openclaw_class_preflight",
            "channel": payload.get("channel", "local"),
            "tool_name": payload.get("tool_name", ""),
        },
    }


def print_result(result: Any, as_json: bool) -> None:
    if as_json or isinstance(result, dict | list):
        print(json.dumps(result, indent=2))
    else:
        print(str(result))


def _exit_code_for_result(result: Any) -> int:
    if isinstance(result, dict) and result.get("status") in {"error", "policy_failed"}:
        return 1
    if isinstance(result, dict) and result.get("status") == "blocked":
        return 1
    return 0


if __name__ == "__main__":
    main()
