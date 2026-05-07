from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_pidgin.hash_utils import sha256_digest
from agent_pidgin.schema_validator import validate_skill_manifest

DANGEROUS_PERMISSION_KINDS = {"credential", "shell"}
DANGEROUS_PERMISSION_ACCESS = {"execute", "admin"}
DANGEROUS_FILESYSTEM_TARGETS = (".ssh", ".aws", ".env", "secrets", "credentials", "id_rsa")


def load_skill_trust_root(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as trust_file:
        trust_root = json.load(trust_file)
    if not isinstance(trust_root, dict):
        raise ValueError("skill trust root must be a JSON object")
    return trust_root


def verify_skill_manifest(manifest: dict[str, Any], trust_root: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_skill_manifest(manifest)
    findings = _skill_findings(manifest, trust_root=trust_root)
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
        "trust_root_hash": sha256_digest(trust_root) if trust_root else None,
        "findings": findings,
    }


def _skill_findings(manifest: dict[str, Any], trust_root: dict[str, Any] | None = None) -> list[dict[str, str]]:
    findings = []
    signed = bool(manifest["signed"])
    permissions = manifest["permissions"]
    if trust_root is not None:
        findings.extend(_trust_root_findings(manifest, trust_root))
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


def _trust_root_findings(manifest: dict[str, Any], trust_root: dict[str, Any]) -> list[dict[str, str]]:
    findings = []
    publisher_id = str(manifest["publisher"]["id"])
    signature = manifest.get("signature") if isinstance(manifest.get("signature"), dict) else {}
    key_id = str(signature.get("key_id", ""))
    trusted_publishers = {str(publisher) for publisher in trust_root.get("trusted_publishers", [])}
    trusted_key_ids = {str(key) for key in trust_root.get("trusted_key_ids", [])}
    revoked_key_ids = {str(key) for key in trust_root.get("revoked_key_ids", [])}
    require_signature = bool(trust_root.get("require_signature", True))

    if require_signature and not manifest["signed"]:
        findings.append(
            {
                "severity": "error",
                "code": "SIGNATURE_REQUIRED",
                "message": "Trust root requires a signed skill manifest.",
            }
        )
    if trusted_publishers and publisher_id not in trusted_publishers:
        findings.append(
            {
                "severity": "error",
                "code": "UNTRUSTED_PUBLISHER",
                "message": f"Publisher {publisher_id} is not in the configured trust root.",
            }
        )
    if manifest["signed"] and trusted_key_ids and key_id not in trusted_key_ids:
        findings.append(
            {
                "severity": "error",
                "code": "UNTRUSTED_KEY_ID",
                "message": f"Signing key {key_id or '<missing>'} is not trusted.",
            }
        )
    if key_id and key_id in revoked_key_ids:
        findings.append(
            {
                "severity": "error",
                "code": "REVOKED_KEY_ID",
                "message": f"Signing key {key_id} has been revoked.",
            }
        )
    return findings


def _targets_secret_path(target: str) -> bool:
    lowered = target.lower()
    return any(secret in lowered for secret in DANGEROUS_FILESYSTEM_TARGETS)
