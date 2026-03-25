from __future__ import annotations

from dataclasses import dataclass

from agent_pidgin.catalog import SeedCatalog


@dataclass
class PidginResolver:
    catalog: SeedCatalog

    def resolve_steps(self, steps: list[str], target_language: str) -> dict:
        resolved_steps = []
        for pointer in steps:
            concept = self.catalog.get(pointer)
            implementations = concept["implementations"]
            if target_language not in implementations:
                raise KeyError(f"Unsupported language for {pointer}: {target_language}")
            resolved_steps.append(
                {
                    "pointer": concept["pointer"],
                    "type_signature": concept["type_signature"],
                    "implementation": implementations[target_language],
                }
            )
        return {
            "target_language": target_language,
            "resolved_steps": resolved_steps,
        }
