# Agent Pidgin

Deterministic semantic contracts, receipts, and flight-recorder traces for autonomous agents.

Project direction is anchored in [docs/product-framing.md](docs/product-framing.md). Current implementation priorities are tracked in [docs/implementation-roadmap.md](docs/implementation-roadmap.md).

A2A lets agents talk. MCP lets agents use tools. Telemetry records what services did. Agent Pidgin focuses on a different layer: what an agent action means, whether that meaning is allowed, how it changed, and what receipts prove the resolution path.

Agent Pidgin is not an execution engine, A2A clone, MCP clone, or generic observability product. It sits beside those layers as the meaning and provenance layer: semantic pointers, versioned catalogs, policy checks, semantic diffs, receipts, and hash-chained flight-recorder traces.

Useful docs:

- [Wow landing page](docs/landing.html)
- [Non-technical assessment](docs/non-technical-assessment.md)
- [What Agent Pidgin does now](docs/what-agent-pidgin-will-do.md)
- [Autonomous Agent Flight Recorder](docs/autonomous-agent-flight-recorder.md)
- [Why this is not telemetry](docs/why-not-telemetry.md)
- [Why this is not just an auditor agent](docs/why-not-auditor-agent.md)
- [Blog: Catching an Agent Before It Sends the Wrong Email](docs/blog-agent-pidgeon-flight-recorder-demo.md)
- [OpenClaw-class agent strategy](docs/openclaw-class-agent-strategy.md)
- [Architecture](docs/architecture.md)

## What works now

- JSON schemas for resolve messages, handshakes, catalogs, receipts, and AAFR traces.
- Trusted catalog loading for core, clinical-safety, and agent-ops semantic pointers.
- Deterministic policy enforcement for pinned revisions, artifact kinds, raw-execution denial, and sensitive pointer receipts.
- Semantic diffing that flags removed safety primitives, removed control guardrails, artifact drift, and implementation changes.
- Resolution receipts with pointer, type signature, catalog ID/version/hash, implementation hash, artifact revision, resolver version, timestamp, and receipt ID.
- CLI commands for validation, policy checks, resolution, catalog introspection, hashing, semantic diffing, and LLM-assisted authoring/review.
- MCP-style receiver tools and A2A JSON wrapper examples.
- Autonomous Agent Flight Recorder support for goals, memory updates, proposed tool calls, semantic drift, policy decisions, full resolution receipts, and hash-chained traces.
- Dependency-free HTTP sidecar for local preflight gates before skill install, memory update, tool call, and trace rendering.
- Catalog trust helpers for trusted catalog IDs, key revocation, pinned hashes, and HMAC-SHA256 signature verification.
- Reproducible showpiece demos and automated tests.
- Deterministic supplement-coach domain-boundary benchmark with status accuracy, autonomy-tier accuracy, and unsafe-prompt catch-rate metrics.

## Why a software engineer would want this

Use Agent Pidgin when an agent is about to do something important and a log line is not enough.

A normal service trace can tell you that an agent proposed `email.send_customer`. Agent Pidgin can tell you whether that proposal was represented by a schema-valid contract, which semantic guardrails were present, whether any were removed since the last safe plan, whether the artifact revision was pinned, which catalog defined each pointer, and which receipts prove the resolution.

That matters for agent systems because bugs are no longer only exceptions and latency spikes. They can be subtle changes in intent: a memory update weakens a boundary, a tool proposal drops human review, a contract switches from a pinned revision to `main`, or a model says "everything is fine" while the semantic contract says safety steps disappeared.

## Why this is not telemetry

Telemetry is still useful. Agent Pidgin is not trying to replace OpenTelemetry-style spans, logs, metrics, or traces.

The distinction:

| Telemetry | Agent Pidgin |
|---|---|
| Records what happened in services | Checks what an agent action means before or around execution |
| Tracks spans, logs, metrics, errors, latency | Tracks semantic contracts, policy findings, diffs, catalog resolution, receipts |
| Accepts event names as labels | Resolves meaning from trusted catalogs |
| Helps debug runtime behavior | Helps audit agent intent and semantic drift |
| Usually after-the-fact observation | Can block high-risk proposed actions before tools run |

The intended architecture is complementary: Pidgin can emit or feed telemetry, but its job is deterministic semantic verification.

## Why this is not just another auditor agent

A prompted auditor agent gives a model opinion. Agent Pidgin gives a reproducible verdict with provenance.

LLMs may help author, explain, or review contracts. They do not define pointer truth. The trust-critical path is deterministic: schema validation, policy enforcement, catalog lookup, hashing, semantic diffing, receipt generation, and trace-integrity checks.

## Logging & Observability

The project includes structured service logging:
- **Enable Debug Logs:** Set `VERBOSE=1` in your environment or use the `--verbose` flag with CLI commands to see detailed debug output on `stderr`.
- **Timing:** Each resolution request logs duration in milliseconds (`duration_ms`) for basic performance monitoring.
- **Safety:** All sensitive fields (like `HF_TOKEN`) are sanitized and never appear in the logs.

## HF Token Management

For maximum security, the project supports three ways to handle Hugging Face tokens:
1. **Environment Variable:** Set `HF_TOKEN` in your `.env` file for automated environments.
2. **System Login:** If `HF_TOKEN` is not set, `hf-mount` will automatically attempt to use the token stored by `huggingface-cli login`.
3. **Implicit:** For public repositories, no token is required.

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

## Run opt-in stdio integration tests

These tests use the real FastMCP stdio path and `hf-mount`, so they are skipped by default unless explicitly enabled.

```bash
AGENT_PIDGIN_RUN_STDIO_INTEGRATION=1 \
AGENT_PIDGIN_DATA_REPO=openai-community/gpt2 \
AGENT_PIDGIN_DATA_REVISION=main \
AGENT_PIDGIN_ARTIFACT_REPO=openai-community/gpt2 \
AGENT_PIDGIN_ARTIFACT_REVISION=main \
AGENT_PIDGIN_MOUNT_ROOT=/tmp/agent-pidgin \
.venv/bin/python -m unittest tests.test_stdio_integration -v
```

The live integration coverage verifies both:

- a real stdio handshake plus resolve round-trip
- payload `artifact` precedence over conflicting legacy `dataset_*` fields

## Run local demo

```bash
PYTHONPATH=src python3 -m agent_pidgin.cli
```

## Run contract commands

The CLI now supports schema validation, catalog validation, policy checks, resolution, catalog hashing, and semantic diffs.

```bash
agent-pidgin validate-message examples/contracts/sample_message.json --json
agent-pidgin validate-catalog catalogs/core.json --json
agent-pidgin list-catalog --json
agent-pidgin show-pointer clinical.phi.scrub --json
agent-pidgin hash-catalog catalogs/core.json --json
AGENT_PIDGIN_CATALOG_HMAC_SECRET="dev-only-example-secret-do-not-use-in-production" \
  agent-pidgin sign-catalog-hmac catalogs/core.json \
  --key-id key-agent-pidgeon-labs-2026-001 \
  --out /tmp/core.signed.json \
  --json
agent-pidgin verify-catalog-trust /tmp/core.signed.json \
  --trust-root examples/openclaw_class/catalog_trust_root.json \
  --json
agent-pidgin list-catalog \
  --catalog /tmp/core.signed.json \
  --catalog-trust-root examples/openclaw_class/catalog_trust_root.json \
  --json
agent-pidgin policy-check examples/contracts/sample_message.json --json
agent-pidgin resolve examples/contracts/sample_message.json --json
agent-pidgin diff examples/contracts/sample_diff.json --json
```

`resolve` uses the default policy unless `--no-policy` is passed. The default policy rejects unpinned revisions such as `main`, so production-style examples should use a pinned 40-character commit SHA.

Optional LLM-assisted authoring is available through OpenRouter:

```bash
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL="qwen/qwen3.6-flash"
agent-pidgin author-contract examples/llm_authoring/plain_language_request.txt \
  --artifact-repo waynesatz/agent-pidgin-data \
  --artifact-revision aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --json
```

LLM-assisted commands draft, explain, or review contracts. They do not define pointer truth and do not bypass schema validation.

OpenClaw-class sidecar preflight commands are available for local gateways and skill-driven agents:

```bash
agent-pidgin preflight-tool examples/agent_flight_recorder_demo/corrupted_tool_contract.json \
  --previous-contract examples/agent_flight_recorder_demo/safe_tool_contract.json \
  --tool-name email.send_customer \
  --json

agent-pidgin record-memory-update examples/openclaw_class/memory_drift_payload.json --json
agent-pidgin verify-skill examples/openclaw_class/dangerous_skill_manifest.json --json
agent-pidgin verify-skill examples/openclaw_class/dangerous_skill_manifest.json \
  --trust-root examples/openclaw_class/trust_root.json \
  --json
```

`preflight-tool` and `record-memory-update` return non-zero when a proposed action is blocked. `verify-skill` returns non-zero for blocked skill manifests.
`--trust-root` adds publisher, signing-key, and revocation checks to skill verification.

Run the end-to-end OpenClaw-class sidecar showpiece:

```bash
PYTHONPATH=src python3 examples/openclaw_class/run_openclaw_showpiece.py --out-dir /tmp/pidgeon-openclaw
```

That writes a trace JSON file, a text replay, and a static HTML replay report with integrity status, grouped findings, receipt drilldown, and before/after drift panels.
You can also export the same trace as OTLP-style JSON for telemetry ingestion:

```bash
agent-pidgin render-trace /tmp/pidgeon-openclaw/openclaw_trace.json \
  --html-out /tmp/pidgeon-openclaw/openclaw_trace.html \
  --otel-out /tmp/pidgeon-openclaw/openclaw_trace.otel.json
```

Run the offline OpenClaw-class gateway adapter:

```bash
PYTHONPATH=src python3 examples/openclaw_gateway_adapter/run_adapter.py --json
```

Run the local HTTP preflight sidecar:

```bash
PYTHONPATH=src python3 -m agent_pidgin.http_sidecar --host 127.0.0.1 --port 8765
```

Then point the gateway adapter at it:

```bash
PYTHONPATH=src python3 examples/openclaw_gateway_adapter/run_adapter.py \
  --mode http \
  --sidecar-url http://127.0.0.1:8765 \
  --json
```

Run the showpiece regression check used by CI:

```bash
PYTHONPATH=src python3 scripts/check_openclaw_showpiece.py
```

Run the supplement-coach domain-boundary benchmark:

```bash
PYTHONPATH=src python3 scripts/check_supplement_guard_benchmark.py
```

Run a reusable domain-boundary policy benchmark:

```bash
agent-pidgin benchmark-domain-policy \
  examples/supplement_coach/domain_policy.json \
  examples/supplement_coach/benchmark_cases.jsonl \
  --json
```

Preflight one prompt:

```bash
agent-pidgin guard-prompt /tmp/prompt.txt \
  --domain-policy examples/supplement_coach/domain_policy.json \
  --trace-out /tmp/prompt-boundary-trace.json \
  --json
```

## Run the showpiece demo

The showpiece demonstrates the intended product shape end to end: plain-language authoring, schema validation, policy findings, trusted catalog resolution, semantic diff risk review, and receipts.

```bash
PYTHONPATH=src python3 examples/showpiece_demo/run_showpiece.py --json
```

Optional live LLM-assisted authoring uses OpenRouter:

```bash
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL="qwen/qwen3.6-flash"
PYTHONPATH=src python3 examples/showpiece_demo/run_showpiece.py --live-llm --json
```

The demo intentionally returns an auditable implementation plan. It does not execute the resolved implementation strings.

## Run the Autonomous Agent Flight Recorder demo

AAFR is the bigger showpiece direction: a replayable semantic audit layer for autonomous agent goals, memory/context updates, proposed tool calls, policy decisions, semantic drift, and receipts.

```bash
PYTHONPATH=src python3 examples/agent_flight_recorder_demo/run_flight_recorder.py
```

Full JSON trace:

```bash
PYTHONPATH=src python3 examples/agent_flight_recorder_demo/run_flight_recorder.py --json
```

This demo shows a safe agent goal, a corrupted context update, and a later unsafe tool proposal. Pidgeon blocks the unsafe proposal and preserves the trace for replay.

The flight recorder trace is hash-chained. The demo also detects unapproved memory guardrail weakening, high-risk semantic drift, removed control guardrails, and unpinned artifact revisions.

Render a saved trace:

```bash
agent-pidgin render-trace trace.json --html-out trace.html --otel-out trace.otel.json
```

## Run stdio A2A demo

This launches the MCP receiver over stdio, performs a Pidgin handshake, then sends a resolve message through the real MCP client path.

```bash
PYTHONPATH=src python3 scripts/poc_stdio_send.py
```

## Run real mount demo

Copy `.env.example` to your local environment setup, then run:

```bash
PYTHONPATH=src python3 scripts/poc_real_mount.py
```

You can override the target artifact with environment variables such as:

```bash
export AGENT_PIDGIN_DATA_REPO=openai-community/gpt2
export AGENT_PIDGIN_DATA_REVISION=main
export AGENT_PIDGIN_ARTIFACT_REPO=openai-community/gpt2
export AGENT_PIDGIN_ARTIFACT_REVISION=main
```

## Start MCP-style receiver

This requires `fastmcp` to be installed in your project environment.

```bash
PYTHONPATH=src python3 -m agent_pidgin.receiver_cli
```

## Hybrid protocol notes

- `message_type=handshake` requests receiver capabilities and artifact defaults
- `message_type=resolve` requests pointer resolution
- resolve payloads may include an `artifact` object with `kind`, `repo`, and `revision`
- schema-validated resolve payloads require `pidgin_version`, `message_type`, `artifact`, and non-empty `steps`
- legacy `dataset_repo` / `dataset_revision` fields may still be included as compatibility metadata, but the `artifact` object is authoritative
- AAFR trace payloads are validated with `schemas/pidgin-trace.schema.json` and include hash-chained events

## Architecture sketch

```text
Agent A
  |
  | Pidgin semantic contract
  v
A2A/MCP transport
  |
  v
Agent Pidgin Receiver
  |
  | validate schema
  | enforce policy
  | mount artifact
  | resolve pointers
  v
Receipts + resolved implementation plan
```
