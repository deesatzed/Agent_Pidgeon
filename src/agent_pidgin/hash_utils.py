from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(content: Any) -> bytes:
    return json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_digest(content: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(content)).hexdigest()


def hash_catalog_content(catalog_content: Any) -> str:
    return sha256_digest(catalog_content)
