from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

RESOLVER_VERSION = "0.1.0"


@dataclass(frozen=True)
class ReceiptContext:
    target_language: str
    catalog_hash: str
    artifact_repo: str
    artifact_revision: str
    resolver_version: str = RESOLVER_VERSION


def build_resolution_receipt(resolved_step: dict[str, Any], context: ReceiptContext) -> dict[str, str]:
    return {
        "pointer": str(resolved_step["pointer"]),
        "type_signature": str(resolved_step["type_signature"]),
        "target_language": context.target_language,
        "implementation": str(resolved_step["implementation"]),
        "implementation_hash": str(resolved_step["implementation_hash"]),
        "catalog_hash": context.catalog_hash,
        "catalog_id": str(resolved_step.get("catalog_id", "")),
        "catalog_version": str(resolved_step.get("catalog_version", "")),
        "artifact_repo": context.artifact_repo,
        "artifact_revision": context.artifact_revision,
        "resolver_version": context.resolver_version,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "receipt_id": f"receipt-{uuid4()}",
    }
