# OpenClaw Gateway Adapter Example

This is a small offline adapter showing an OpenClaw-class gateway planner calling Agent Pidgeon before four effects:

- community skill install
- persistent memory update
- external email/tool call
- shell command

The planner is deterministic and local. It never installs a skill, mutates memory, sends email, or runs a shell command. The default mode records a Pidgeon flight trace in-process, then returns gateway verdicts that an OpenClaw-class runner can use before dispatching real effects.

Run it from the repository root:

```bash
PYTHONPATH=src python examples/openclaw_gateway_adapter/run_adapter.py
```

Run it against the HTTP sidecar:

```bash
PYTHONPATH=src python -m agent_pidgin.http_sidecar --host 127.0.0.1 --port 8765
PYTHONPATH=src python examples/openclaw_gateway_adapter/run_adapter.py \
  --mode http \
  --sidecar-url http://127.0.0.1:8765 \
  --json
```

Write replay artifacts:

```bash
PYTHONPATH=src python examples/openclaw_gateway_adapter/run_adapter.py --out-dir /tmp/openclaw-pidgeon
```

Expected gateway decisions:

```text
skill_install: blocked
memory_update: blocked
external_tool_call: requires_approval
shell_command: blocked
```

The code path uses existing Agent Pidgeon APIs:

- `FlightRecorder.record_skill_install`
- `FlightRecorder.record_memory_update`
- `FlightRecorder.record_contract_event`
- `contract_from_preflight_payload` for CLI-compatible tool and shell payloads

The HTTP mode uses these sidecar endpoints:

- `POST /v1/preflight/skill`
- `POST /v1/preflight/memory`
- `POST /v1/preflight/contract`
