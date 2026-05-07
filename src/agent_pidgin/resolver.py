from __future__ import annotations

from dataclasses import dataclass

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.hash_utils import hash_catalog_content
from agent_pidgin.receipt import ReceiptContext, build_resolution_receipt


@dataclass
class PidginResolver:
    catalog: SeedCatalog

    def resolve_steps(
        self,
        steps: list[str],
        target_language: str,
        artifact_repo: str = "unknown",
        artifact_revision: str = "unknown",
    ) -> dict:
        resolved_steps = []
        receipts = []
        receipt_context = ReceiptContext(
            target_language=target_language,
            catalog_hash=self.catalog.catalog_hash(),
            artifact_repo=artifact_repo,
            artifact_revision=artifact_revision,
        )
        for pointer in steps:
            concept = self.catalog.get(pointer)
            implementations = concept["implementations"]
            if target_language not in implementations:
                raise KeyError(f"Unsupported language for {pointer}: {target_language}")
            resolved_step = {
                "pointer": concept["pointer"],
                "type_signature": concept["type_signature"],
                "implementation": implementations[target_language],
                "implementation_hash": hash_catalog_content(implementations[target_language]),
                "catalog_id": concept.get("catalog_id", ""),
                "catalog_version": concept.get("catalog_version", ""),
            }
            resolved_steps.append(resolved_step)
            receipts.append(build_resolution_receipt(resolved_step, receipt_context))
        return {
            "target_language": target_language,
            "resolved_steps": resolved_steps,
            "receipts": receipts,
        }
