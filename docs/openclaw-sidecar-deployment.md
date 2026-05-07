# OpenClaw Sidecar Deployment

Agent Pidgeon should run beside an OpenClaw-class gateway as a deterministic preflight sidecar. The gateway keeps planning and tool ownership. Pidgeon receives proposed effects before execution, validates the semantic contract, records a hash-chained trace, and returns a decision the gateway can enforce.

```text
chat/app event -> OpenClaw gateway planner -> Agent Pidgeon sidecar -> allow/block/approval -> tool runner
```

## Adapter Shape

Use `examples/openclaw_gateway_adapter/run_adapter.py` as the minimal integration pattern:

1. The gateway planner emits typed proposed effects.
2. Skill installs call `FlightRecorder.record_skill_install`.
3. Memory writes call `FlightRecorder.record_memory_update`.
4. External tool and shell calls use CLI-compatible payloads normalized by `contract_from_preflight_payload`.
5. The gateway enforces the returned verdict before invoking any real tool.

Run the offline example:

```bash
PYTHONPATH=src python examples/openclaw_gateway_adapter/run_adapter.py --json
```

## HTTP Sidecar

Run the dependency-free local HTTP sidecar:

```bash
PYTHONPATH=src python -m agent_pidgin.http_sidecar --host 127.0.0.1 --port 8765
```

Installed environments can also use:

```bash
agent-pidgin-sidecar --host 127.0.0.1 --port 8765
```

Endpoints:

- `GET /health`
- `POST /v1/preflight/skill`
- `POST /v1/preflight/memory`
- `POST /v1/preflight/contract`
- `POST /v1/render-trace`

Blocked preflights return HTTP `409` with the same JSON verdict body. Malformed payloads return HTTP `400`. The sidecar is preflight-only and has no endpoint for executing skills, tools, shell commands, or sends.

## Deployment Pattern

For a local or self-hosted OpenClaw-class agent, deploy Pidgeon in the same trust boundary as the gateway:

- Same host or container pod as the gateway.
- Read-only access to policy and catalog files.
- Write access only to the trace/receipt output directory.
- No direct permission to execute gateway tools.
- Gateway-owned enforcement of `blocked` and `requires_approval` decisions.

The sidecar should be called before these high-impact effects:

- skill installation or upgrade
- persistent memory updates
- external email, chat, calendar, ticketing, browser, or API calls
- shell commands and file mutations

## Effect Contracts

External tools and shell commands should be passed as Pidgeon resolve contracts:

```json
{
  "event_type": "agent.tool.proposed_call",
  "actor": "openclaw-support-agent",
  "channel": "slack:support-escalations",
  "tool_name": "email.send_customer",
  "correlation_id": "gateway-email-001",
  "contract": {
    "steps": [
      "comm.draft_external_message",
      "comm.require_recipient_verification",
      "comm.require_human_approval",
      "comm.send_external_message",
      "agent.attach_receipts"
    ],
    "target_language": "python"
  }
}
```

For shell proposals, include `shell.require_sandbox`, `shell.block_destructive_command`, `shell.require_human_approval`, and `agent.attach_receipts` in the contract. Keep the proposed command in payload metadata and execute it only after the gateway accepts the sidecar verdict.

## Verdict Handling

Treat the sidecar as a pre-execution gate:

- `blocked`: do not execute; show the policy or semantic diff reason.
- `requires_approval`: pause and collect human approval before executing.
- `drift_detected`: pause or downgrade to review if the contract changed meaning.
- `resolved`: the semantic contract resolved; the gateway may continue if its own policy also passes.

Keep the gateway fail-closed. If the sidecar is unavailable, malformed, or returns an unknown decision for a high-impact effect, the gateway should not execute that effect.

## Trace Operations

Persist traces next to gateway run IDs so incidents can be replayed:

```bash
PYTHONPATH=src python examples/openclaw_gateway_adapter/run_adapter.py --out-dir ./artifacts/openclaw-run-001
```

The trace JSON is suitable for later rendering with:

```bash
agent-pidgin render-trace ./artifacts/openclaw-run-001/openclaw_gateway_adapter_trace.json
```

Do not store secrets in contracts or trace payloads. Store references, hashes, recipient counts, command argv, and approval IDs instead.
