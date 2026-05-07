# OpenClaw-Class Fixtures

These fixtures show the kinds of payloads an OpenClaw-class gateway can send to Agent Pidgeon before acting.

- `external_email_tool_contract.json` models a customer email send that should verify recipients, require approval, and attach receipts.
- `memory_drift_payload.json` models a memory update that weakens prior safety boundaries.
- `dangerous_skill_manifest.json` models an unsigned marketplace skill requesting shell, filesystem, network, and credential access.
- `shell_command_proposal.json` models a proposed shell command that should be sandboxed and reviewed before execution.

The files are examples only. They describe proposed actions and semantic contracts; they are not executable tool implementations.
