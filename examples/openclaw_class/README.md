# OpenClaw-Class Fixtures

These fixtures show the kinds of payloads an OpenClaw-class gateway can send to Agent Pidgeon before acting.

- `external_email_tool_contract.json` models a customer email send that should verify recipients, require approval, and attach receipts.
- `memory_drift_payload.json` models a memory update that weakens prior safety boundaries.
- `dangerous_skill_manifest.json` models an unsigned marketplace skill requesting shell, filesystem, network, and credential access.
- `shell_command_proposal.json` models a proposed shell command that should be sandboxed and reviewed before execution.
- `trust_root.json` models a local skill verification trust root with trusted publishers, trusted signing keys, and revoked keys.
- `catalog_trust_root.json` models a local catalog trust root with trusted catalog IDs, key revocation, optional pinned hashes, and a dev-only HMAC verifier secret.
- `golden/` contains the current reference trace, text report, and HTML replay for the showpiece.

The files are examples only. They describe proposed actions and semantic contracts; they are not executable tool implementations.

Run the golden check:

```bash
PYTHONPATH=src python3 scripts/check_openclaw_showpiece.py
```

The check compares stable trace shape and report content, not timestamps or hash-chain values.
