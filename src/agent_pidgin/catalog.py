from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_pidgin.hash_utils import hash_catalog_content
from agent_pidgin.schema_validator import validate_catalog

_DEFAULT_CONCEPTS = {
    "str.trim": {
        "pointer": "str.trim",
        "type_signature": "str -> str",
        "implementations": {
            "python": "lambda s: s.strip()",
            "javascript": "(s) => s.trim()",
        },
    },
    "str.lowercase": {
        "pointer": "str.lowercase",
        "type_signature": "str -> str",
        "implementations": {
            "python": "lambda s: s.lower()",
            "javascript": "(s) => s.toLowerCase()",
        },
    },
    "str.ascii_only": {
        "pointer": "str.ascii_only",
        "type_signature": "str -> str",
        "implementations": {
            "python": "lambda s: ''.join(ch for ch in s if ord(ch) < 128)",
            "javascript": "(s) => s.replace(/[^\\x00-\\x7F]/g, '')",
        },
    },
}

CATALOG_ROOT = Path(__file__).resolve().parents[2] / "catalogs"
DEFAULT_CATALOG_FILES = [
    CATALOG_ROOT / "core.json",
    CATALOG_ROOT / "clinical_safety.json",
    CATALOG_ROOT / "agent_ops.json",
    CATALOG_ROOT / "communications.json",
    CATALOG_ROOT / "filesystem_ops.json",
    CATALOG_ROOT / "shell_ops.json",
    CATALOG_ROOT / "skill_marketplace.json",
    CATALOG_ROOT / "memory_ops.json",
    CATALOG_ROOT / "finance_ops.json",
]


@dataclass(frozen=True)
class SeedCatalog:
    concepts: dict[str, dict[str, Any]]
    sources: tuple[str, ...] = ()
    raw_catalogs: tuple[dict[str, Any], ...] = ()

    @classmethod
    def load_default(cls) -> "SeedCatalog":
        if all(path.exists() for path in DEFAULT_CATALOG_FILES):
            return cls.from_files(DEFAULT_CATALOG_FILES)
        return cls(concepts=_DEFAULT_CONCEPTS.copy(), sources=("python-fallback",))

    @classmethod
    def from_file(cls, path: str | Path) -> "SeedCatalog":
        return cls.from_files([path])

    @classmethod
    def from_files(cls, paths: list[str | Path] | tuple[str | Path, ...]) -> "SeedCatalog":
        concepts: dict[str, dict[str, Any]] = {}
        raw_catalogs: list[dict[str, Any]] = []
        sources: list[str] = []

        for pathlike in paths:
            path = Path(pathlike)
            with path.open(encoding="utf-8") as catalog_file:
                raw_catalog = json.load(catalog_file)
            validate_catalog(raw_catalog)
            raw_catalogs.append(raw_catalog)
            sources.append(str(path))

            for concept in raw_catalog["concepts"]:
                pointer = concept["pointer"]
                if pointer in concepts:
                    raise ValueError(f"Duplicate catalog pointer: {pointer}")
                if not concept.get("implementations"):
                    raise ValueError(f"Missing implementations for pointer: {pointer}")
                concept_record = dict(concept)
                concept_record["catalog_id"] = raw_catalog["catalog_id"]
                concept_record["catalog_version"] = raw_catalog["version"]
                concept_record["catalog_source"] = str(path)
                concepts[pointer] = concept_record

        return cls(concepts=concepts, sources=tuple(sources), raw_catalogs=tuple(raw_catalogs))

    def get(self, pointer: str) -> dict:
        return self.concepts[pointer]

    def supported_languages(self) -> list[str]:
        languages = {language for concept in self.concepts.values() for language in concept.get("implementations", {})}
        return sorted(languages)

    def pointers_for_language(self, target_language: str) -> list[str]:
        return sorted(
            pointer
            for pointer, concept in self.concepts.items()
            if target_language in concept.get("implementations", {})
        )

    def content_for_hash(self) -> Any:
        if self.raw_catalogs:
            return list(self.raw_catalogs)
        return {"concepts": self.concepts}

    def catalog_hash(self) -> str:
        return hash_catalog_content(self.content_for_hash())

    def summary(self) -> dict[str, Any]:
        return {
            "status": "catalog_loaded",
            "catalog_hash": self.catalog_hash(),
            "sources": list(self.sources),
            "catalogs": [
                {
                    "catalog_id": raw_catalog.get("catalog_id"),
                    "version": raw_catalog.get("version"),
                    "description": raw_catalog.get("description", ""),
                    "concept_count": len(raw_catalog.get("concepts", [])),
                }
                for raw_catalog in self.raw_catalogs
            ],
            "concept_count": len(self.concepts),
            "supported_languages": self.supported_languages(),
            "pointers": sorted(self.concepts),
        }

    def pointer_summary(self, pointer: str) -> dict[str, Any]:
        concept = self.get(pointer)
        return {
            "pointer": concept["pointer"],
            "type_signature": concept["type_signature"],
            "description": concept.get("description", ""),
            "safety_sensitive": bool(concept.get("safety_sensitive", False)),
            "supported_languages": sorted(concept.get("implementations", {})),
            "implementation_hashes": {
                language: hash_catalog_content(implementation)
                for language, implementation in concept.get("implementations", {}).items()
            },
            "catalog_id": concept.get("catalog_id", ""),
            "catalog_version": concept.get("catalog_version", ""),
        }
