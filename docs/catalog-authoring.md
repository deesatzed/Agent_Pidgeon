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
