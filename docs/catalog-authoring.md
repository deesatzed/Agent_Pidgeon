# Catalog Authoring

Catalogs define semantic pointers.

Each concept needs:

- `pointer`
- `type_signature`
- `implementations`

Optional fields include:

- `description`
- `safety_sensitive`

Example:

```json
{
  "pointer": "str.trim",
  "type_signature": "str -> str",
  "description": "Remove leading and trailing whitespace.",
  "implementations": {
    "python": "lambda s: s.strip()"
  }
}
```

Authoring rules:

- Keep pointer names stable.
- Treat implementation changes as meaningful contract changes.
- Use semantic diff before removing safety-sensitive pointers.
- Do not add diagnostic clinical behavior to safety catalogs.

Inspect the active catalog:

```bash
agent-pidgin list-catalog --json
agent-pidgin show-pointer str.trim --json
agent-pidgin list-catalog --catalog catalogs/core.json --json
```

## Trust Metadata

Catalog trust checks are deterministic checks. They validate:

- the catalog ID is in `trusted_catalog_ids`
- the signing key ID is in `trusted_key_ids`
- the signing key ID is not in `revoked_key_ids`
- the catalog hash matches `trusted_catalog_hashes[catalog_id]` when pinned
- HMAC-SHA256 catalog signatures when the trust root supplies an `hmac_sha256_secrets[key_id]` verifier secret

The current asymmetric-signature boundary is explicit: `agent_pidgin.catalog_trust` does not perform public-key signature verification yet. It can verify HMAC-SHA256 signatures for local/shared-secret deployments. For other algorithms, a trusted key ID means the metadata names an allowed key; it does not prove the bytes were signed by that key.

Trust roots use this shape:

```json
{
  "require_signature": true,
  "trusted_catalog_ids": ["core"],
  "trusted_key_ids": ["key-agent-pidgeon-labs-2026-001"],
  "revoked_key_ids": ["key-agent-pidgeon-labs-2025-001"],
  "trusted_catalog_hashes": {
    "core": "expected-sha256-hex"
  },
  "hmac_sha256_secrets": {
    "key-agent-pidgeon-labs-2026-001": "dev-only-example-secret"
  }
}
```

HMAC signatures bind the canonical catalog body with the `signature` field removed:

```json
{
  "signature": {
    "algorithm": "hmac-sha256",
    "key_id": "key-agent-pidgeon-labs-2026-001",
    "value": "hex-hmac-sha256"
  }
}
```

Rotation rule: add the new key ID to `trusted_key_ids`, publish catalog metadata using that key ID, then move retired or compromised key IDs to `revoked_key_ids`. Revocation wins over trust if the same key appears in both lists.
