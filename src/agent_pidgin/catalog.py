from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class SeedCatalog:
    concepts: dict[str, dict]

    @classmethod
    def load_default(cls) -> "SeedCatalog":
        return cls(concepts=_DEFAULT_CONCEPTS.copy())

    def get(self, pointer: str) -> dict:
        return self.concepts[pointer]
