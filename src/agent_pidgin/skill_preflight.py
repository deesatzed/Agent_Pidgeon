from __future__ import annotations

from typing import Any

from agent_pidgin.hash_utils import sha256_digest
from agent_pidgin.schema_validator import validate_skill_manifest

DANGEROUS_PERMISSION_KINDS = {"credential", "shell"}
DANGEROUS_PERMISSION_ACCESS = {"execute", "admin"}
DANGEROUS_FILESYSTEM_TARGETS = (".ssh", ".aws", ".env", "secrets", "credentials", "id_rsa")


def verify_skill_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    validate_skill_manifest(manifest)
    findings = _skill_findings(manifest)
    status = "blocked" if any(finding["severity"] == "error" for finding in findings) else "approved"
    return {
        "status": status,
        "skill_id": manifest["skill_id"],
        "version": manifest["version"],
        "publisher": manifest["publisher"],
        "signed": manifest["signed"],
        "manifest_hash": sha256_digest(manifest),
        "capabilities": list(manifest["capabilities"]),
        "permissions": list(manifest["permissions"]),
        "findings": findings,
    }


def _skill_findings(manifest: dict[str, Any]) -> list[dict[str, str]]:
    findings = []
    signed = bool(manifest["signed"])
    permissions = manifest["permissions"]
    if not signed:
        findings.append(
            {
                "severity": "warning",
                "code": "UNSIGNED_SKILL",
                "message": "Skill manifest is not signed by a trusted publisher.",
            }
        )

    for permission in permissions:
        kind = str(permission["kind"])
        access = str(permission["access"])
        target = str(permission["target"])
        if kind in DANGEROUS_PERMISSION_KINDS:
            findings.append(
                {
                    "severity": "error" if not signed else "warning",
                    "code": f"DANGEROUS_{kind.upper()}_PERMISSION",
                    "message": f"Skill requests {kind} {access} access to {target}.",
                }
            )
        if access in DANGEROUS_PERMISSION_ACCESS:
            findings.append(
                {
                    "severity": "error" if not signed else "warning",
                    "code": "DANGEROUS_ACCESS_MODE",
                    "message": f"Skill requests {access} access for {kind}:{target}.",
                }
            )
        if kind == "filesystem" and _targets_secret_path(target):
            findings.append(
                {
                    "severity": "error",
                    "code": "SECRET_PATH_ACCESS",
                    "message": f"Skill requests filesystem access to likely secret path: {target}.",
                }
            )
        if kind == "email" and access == "send":
            findings.append(
                {
                    "severity": "warning",
                    "code": "EXTERNAL_SEND_PERMISSION",
                    "message": "Skill can send email; require external-send preflight before execution.",
                }
            )

    if not findings:
        findings.append(
            {
                "severity": "info",
                "code": "SKILL_PREFLIGHT_PASSED",
                "message": "No dangerous permissions detected.",
            }
        )
    return findings


def _targets_secret_path(target: str) -> bool:
    lowered = target.lower()
    return any(secret in lowered for secret in DANGEROUS_FILESYSTEM_TARGETS)
