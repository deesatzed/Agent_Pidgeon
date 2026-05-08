# Architecture

Agent Pidgin is a deterministic semantic contract resolver plus an Autonomous Agent Flight Recorder layer.

```text
Agent or CLI caller
  |
  | Pidgin semantic contract
  v
Schema validation
  |
  v
Policy enforcement
  |
  v
Trusted catalog lookup
  |
  v
Receipt generation
  |
  v
Auditable implementation plan
```

The resolver returns implementation strings as plan data. It does not execute them by default.

The flight-recorder layer composes resolver outputs into replayable trace events:

```text
Agent runtime
  |
  | goal / memory update / proposed tool call
  v
AAFR recorder
  |
  | hash payload
  | validate contract
  | enforce policy
  | resolve pointers
  | diff against prior intent
  | detect memory guardrail weakening
  | hash-chain event
  v
Replayable trace with policy findings, diffs, receipt IDs, and trace hash
```

## Core Modules

- `protocol.py`: typed message and handshake models
- `schema_validator.py`: JSON Schema validation
- `policy.py`: policy findings and enforcement
- `catalog.py`: JSON catalog loading and pointer lookup
- `resolver.py`: semantic pointer resolution
- `receipt.py`: per-step provenance records
- `semantic_diff.py`: workflow comparison and risk notes
- `catalog_trust.py`: catalog hash, trust-root, and HMAC signature checks
- `config.py`: environment-backed runtime configuration
- `hf_mount.py` and `mount_gateway.py`: real and simulated artifact gateway adapters
- `skill_preflight.py`: skill manifest permission and trust checks
- `service.py`: receiver orchestration boundary
- `flight_recorder.py`: AAFR trace event recording, memory guardrail checks, hash-chain integrity, and replay report generation
- `html_report.py`: static HTML trace replay rendering
- `telemetry.py`: OTLP-style trace export
- `llm_authoring.py`: optional LLM-assisted contract drafting, explanation, and review
- `http_sidecar.py`: dependency-free HTTP preflight sidecar

`PidginReceiverService` is the boundary that callers should use. Transport wrappers must not bypass it.

The default CLI and flight-recorder paths use a simulated mount gateway for deterministic preflight. Real Hugging Face mounting is available through `HfMountManager`, `agent-pidgin resolve --gateway hf`, or explicit gateway injection.

## Novel Boundary

Agent Pidgin is not telemetry. Telemetry records runtime spans, logs, metrics, and errors. Pidgin records and verifies semantic intent: what the agent proposed, what the contract meant, which guardrails changed, which policy findings applied, and which receipts prove resolution.

Agent Pidgin is not an auditor agent. LLMs may author or explain contracts, but the authority comes from deterministic schemas, policies, catalogs, hashes, diffs, and receipts.
