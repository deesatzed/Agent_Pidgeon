from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_pidgin.hash_utils import hash_catalog_content, sha256_digest


def load_catalog_trust_root(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as trust_file:
        trust_root = json.load(trust_file)
    if not isinstance(trust_root, dict):
        raise ValueError("catalog trust root must be a JSON object")
    return trust_root


def catalog_trust_metadata(
    catalog_content: dict[str, Any],
    *,
    signing_key_id: str | None = None,
    signature: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "catalog_id": str(catalog_content.get("catalog_id", "")),
        "catalog_version": str(catalog_content.get("version", "")),
        "catalog_hash": hash_catalog_content(catalog_content),
    }
    if signing_key_id is not None:
        metadata["signing_key_id"] = signing_key_id
    if signature is not None:
        metadata["signature"] = dict(signature)
    return metadata


def verify_catalog_hash(catalog_content: dict[str, Any], expected_hash: str) -> dict[str, Any]:
    actual_hash = hash_catalog_content(catalog_content)
    return {
        "status": "matched" if actual_hash == expected_hash else "mismatched",
        "expected_catalog_hash": expected_hash,
        "actual_catalog_hash": actual_hash,
        "matched": actual_hash == expected_hash,
    }


def verify_catalog_trust_metadata(metadata: dict[str, Any], trust_root: dict[str, Any]) -> dict[str, Any]:
    findings = _catalog_trust_findings(metadata, trust_root)
    status = "blocked" if any(finding["severity"] == "error" for finding in findings) else "approved"
    return {
        "status": status,
        "catalog_id": str(metadata.get("catalog_id", "")),
        "catalog_version": str(metadata.get("catalog_version", "")),
        "catalog_hash": str(metadata.get("catalog_hash", "")),
        "signing_key_id": _signing_key_id(metadata),
        "trust_root_hash": sha256_digest(trust_root),
        "signature_verification": "not_implemented",
        "findings": findings,
    }


def verify_catalog_trust(catalog_content: dict[str, Any], trust_root: dict[str, Any]) -> dict[str, Any]:
    metadata = catalog_trust_metadata(catalog_content)
    return verify_catalog_trust_metadata(metadata, trust_root)


def _catalog_trust_findings(metadata: dict[str, Any], trust_root: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    catalog_id = str(metadata.get("catalog_id", ""))
    catalog_hash = str(metadata.get("catalog_hash", ""))
    signing_key_id = _signing_key_id(metadata)
    trusted_catalog_ids = {str(catalog) for catalog in trust_root.get("trusted_catalog_ids", [])}
    trusted_key_ids = {str(key) for key in trust_root.get("trusted_key_ids", [])}
    revoked_key_ids = {str(key) for key in trust_root.get("revoked_key_ids", [])}
    pinned_hashes = _catalog_hash_pins(trust_root)
    require_signature = bool(trust_root.get("require_signature", True))

    if not catalog_id:
        findings.append(
            {
                "severity": "error",
                "code": "MISSING_CATALOG_ID",
                "message": "Catalog trust metadata must include a catalog_id.",
            }
        )
    elif trusted_catalog_ids and catalog_id not in trusted_catalog_ids:
        findings.append(
            {
                "severity": "error",
                "code": "UNTRUSTED_CATALOG_ID",
                "message": f"Catalog {catalog_id} is not in the configured trust root.",
            }
        )

    if require_signature and not signing_key_id:
        findings.append(
            {
                "severity": "error",
                "code": "SIGNATURE_REQUIRED",
                "message": "Trust root requires catalog signing metadata with a key ID.",
            }
        )
    if signing_key_id and trusted_key_ids and signing_key_id not in trusted_key_ids:
        findings.append(
            {
                "severity": "error",
                "code": "UNTRUSTED_KEY_ID",
                "message": f"Signing key {signing_key_id} is not trusted.",
            }
        )
    if signing_key_id and signing_key_id in revoked_key_ids:
        findings.append(
            {
                "severity": "error",
                "code": "REVOKED_KEY_ID",
                "message": f"Signing key {signing_key_id} has been revoked.",
            }
        )
    if signing_key_id:
        findings.append(
            {
                "severity": "warning",
                "code": "SIGNATURE_CRYPTO_NOT_VERIFIED",
                "message": (
                    "Catalog signing metadata was checked, but cryptographic signature verification is not implemented."
                ),
            }
        )

    if not catalog_hash:
        findings.append(
            {
                "severity": "error",
                "code": "MISSING_CATALOG_HASH",
                "message": "Catalog trust metadata must include a catalog_hash.",
            }
        )
    elif catalog_id in pinned_hashes and catalog_hash != pinned_hashes[catalog_id]:
        findings.append(
            {
                "severity": "error",
                "code": "CATALOG_HASH_MISMATCH",
                "message": f"Catalog hash for {catalog_id} does not match the configured trust root.",
            }
        )

    if not findings:
        findings.append(
            {
                "severity": "info",
                "code": "CATALOG_TRUST_METADATA_PASSED",
                "message": "Catalog ID, signing key ID, revocation list, and catalog hash checks passed.",
            }
        )
    return findings


def _signing_key_id(metadata: dict[str, Any]) -> str:
    if metadata.get("signing_key_id") is not None:
        return str(metadata.get("signing_key_id", ""))
    signature = metadata.get("signature") if isinstance(metadata.get("signature"), dict) else {}
    return str(signature.get("key_id", ""))


def _catalog_hash_pins(trust_root: dict[str, Any]) -> dict[str, str]:
    pinned_hashes = trust_root.get("trusted_catalog_hashes", {})
    if isinstance(pinned_hashes, dict):
        return {str(catalog_id): str(catalog_hash) for catalog_id, catalog_hash in pinned_hashes.items()}
    return {}
