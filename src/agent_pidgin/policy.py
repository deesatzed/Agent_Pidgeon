from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_pidgin.protocol import PidginMessage

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "policies" / "default_policy.json"
COMMIT_SHA_PATTERN = re.compile(r"^[a-fA-F0-9]{40}$")
COMMON_BRANCH_REVISIONS = {"main", "master", "develop", "dev", "trunk", "latest"}


@dataclass(frozen=True)
class PidginPolicy:
    require_pinned_revision: bool
    allow_branch_revision: bool
    allowed_artifact_kinds: tuple[str, ...]
    allowed_repos: tuple[str, ...]
    deny_raw_execution: bool
    require_receipts: bool
    sensitive_pointer_prefixes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PidginPolicy":
        return cls(
            require_pinned_revision=bool(payload.get("require_pinned_revision", True)),
            allow_branch_revision=bool(payload.get("allow_branch_revision", False)),
            allowed_artifact_kinds=tuple(str(kind) for kind in payload.get("allowed_artifact_kinds", [])),
            allowed_repos=tuple(str(repo) for repo in payload.get("allowed_repos", [])),
            deny_raw_execution=bool(payload.get("deny_raw_execution", True)),
            require_receipts=bool(payload.get("require_receipts", True)),
            sensitive_pointer_prefixes=tuple(str(prefix) for prefix in payload.get("sensitive_pointer_prefixes", [])),
        )


@dataclass(frozen=True)
class PolicyFinding:
    severity: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }


def load_policy(path: str | Path | None = None) -> PidginPolicy:
    policy_path = Path(path) if path is not None else DEFAULT_POLICY_PATH
    with policy_path.open(encoding="utf-8") as policy_file:
        return PidginPolicy.from_dict(json.load(policy_file))


def enforce_policy(message: PidginMessage, policy: PidginPolicy) -> list[PolicyFinding]:
    findings: list[PolicyFinding] = []

    if message.artifact is None:
        findings.append(
            PolicyFinding(
                severity="error",
                code="MISSING_ARTIFACT",
                message="A Pidgin resolve message must include an artifact target.",
            )
        )
        return findings

    artifact_kind = message.artifact.kind or ""
    if artifact_kind not in policy.allowed_artifact_kinds:
        findings.append(
            PolicyFinding(
                severity="error",
                code="UNKNOWN_ARTIFACT_KIND",
                message=f"Artifact kind '{artifact_kind}' is not allowed by policy.",
            )
        )

    if policy.allowed_repos and message.artifact.repo not in policy.allowed_repos:
        findings.append(
            PolicyFinding(
                severity="error",
                code="UNTRUSTED_REPO",
                message=f"Artifact repo '{message.artifact.repo}' is not in the policy allow-list.",
            )
        )

    if policy.require_pinned_revision and not is_pinned_revision(message.artifact.revision):
        findings.append(
            PolicyFinding(
                severity="error",
                code="UNPINNED_REVISION",
                message="Artifact revision must be a 40-character commit SHA.",
            )
        )
    elif not policy.allow_branch_revision and is_common_branch_revision(message.artifact.revision):
        findings.append(
            PolicyFinding(
                severity="error",
                code="BRANCH_REVISION",
                message=f"Artifact revision '{message.artifact.revision}' looks like a branch name.",
            )
        )

    if policy.deny_raw_execution:
        findings.append(
            PolicyFinding(
                severity="warning",
                code="RAW_EXECUTION_DENIED",
                message=(
                    "Policy permits resolution only; resolved implementation strings must not be executed directly."
                ),
            )
        )

    if policy.require_receipts and _uses_sensitive_pointer(message, policy):
        findings.append(
            PolicyFinding(
                severity="warning",
                code="SENSITIVE_POINTER_RECEIPTS_REQUIRED",
                message="Sensitive pointers are present; receipts are required and will be attached during resolution.",
            )
        )

    return findings


def has_policy_errors(findings: list[PolicyFinding]) -> bool:
    return any(finding.severity == "error" for finding in findings)


def findings_to_dicts(findings: list[PolicyFinding]) -> list[dict[str, str]]:
    return [finding.to_dict() for finding in findings]


def is_pinned_revision(revision: str) -> bool:
    return bool(COMMIT_SHA_PATTERN.match(revision))


def is_common_branch_revision(revision: str) -> bool:
    return revision.lower() in COMMON_BRANCH_REVISIONS


def _uses_sensitive_pointer(message: PidginMessage, policy: PidginPolicy) -> bool:
    return any(step.startswith(prefix) for step in message.steps for prefix in policy.sensitive_pointer_prefixes)
