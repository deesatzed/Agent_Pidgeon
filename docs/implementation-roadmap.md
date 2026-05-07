# Agent Pidgin Implementation Roadmap

This roadmap is subordinate to [product-framing.md](product-framing.md). If a task conflicts with product framing, product framing wins.

## Scope Guardrails

Agent Pidgin resolves semantic contracts. It does not execute resolved implementation strings by default.

Agent Pidgin may integrate with A2A and MCP, but only as transport/tool surfaces around the resolver.

The trust-critical path must remain deterministic: schema validation, policy enforcement, catalog lookup, hashing, semantic diffing, and receipt generation.

## Current Build State

Done:

- README/product framing for Agent Pidgin as the semantic meaning/provenance layer
- JSON schemas for message, handshake, artifact, catalog, and receipt
- schema validator module
- JSON catalog loader with duplicate pointer detection
- core, clinical safety, and agent ops catalogs
- deterministic catalog hashing
- per-step resolution receipts
- policy file and policy enforcement
- semantic diff module
- real CLI commands for validation, resolution, hashing, diffing, and policy checks
- catalog introspection through CLI and MCP metadata tools
- configurable catalog loading through CLI and environment
- configurable policy enforcement for MCP/server mode through environment
- MCP structured response wrappers
- A2A JSON wrapper example
- documentation set covering architecture, protocol, security, receipts, catalogs, A2A, MCP, parallel processing, and LLM-assisted authoring
- clinical safety demo with a non-diagnostic contract and receipts
- full-contract semantic diff with risk levels
- receipt catalog ID/version and implementation hashes
- optional OpenRouter/Qwen LLM-assisted authoring, explanation, and review
- reproducible showpiece demo covering authoring, validation, policy, resolution, receipts, and unsafe-change review
- Autonomous Agent Flight Recorder trace schema, recorder module, replay report, and corrupted-context demo
- hash-chained AAFR traces with trace-integrity validation
- deterministic detection of unapproved memory guardrail weakening
- high-risk semantic drift blocking for proposed contract events
- docs explaining why Pidgin is not telemetry and not just another auditor agent
- OpenClaw-class agent strategy covering local gateways, channel agents, skill marketplaces, memory, heartbeat tasks, tool actions, and enterprise clones
- unit coverage for schema validation, catalog loading, hashing, receipts, policy, semantic diff, and CLI

## Tight Next Tasks

1. **OpenClaw-class sidecar**
   - Add catalogs for communications, filesystem, shell, skill marketplace, memory, and finance actions.
   - Add example contracts under `examples/openclaw_class/`.
   - Add skill manifest schema and deterministic skill install preflight.
   - Add CLI commands for `preflight-tool`, `record-memory-update`, and `verify-skill`.
   - Add docs for deploying Pidgeon as a sidecar beside an OpenClaw-class gateway.

2. **AAFR next hardening**
   - Add stable trace fixtures for the flight recorder demo.
   - Add a richer HTML timeline view beside the terminal report.
   - Add event types for tool result observation and approved memory writes.
   - Add optional trace export compatible with OpenTelemetry-style spans.
   - Add signed trace roots or external append-only storage integration.

3. **Showpiece hardening**
   - Add a CLI alias for the showpiece if repeated demo runs need a shorter command.
   - Add a compact human-readable report output beside the full JSON payload.
   - Keep the offline fixture as the deterministic test path and live OpenRouter as optional.

4. **Trust hardening**
   - Add catalog version pinning in contracts.
   - Add external catalog artifact verification.
   - Add optional signed catalog and signed receipt checks.

5. **Authoring review loop**
   - Let LLM-assisted authoring return explicit rejected/missing safety requirements.
   - Add deterministic guardrail checks for domain-specific required pointers.
   - Keep schema, policy, and catalog resolution as the authority.

6. **Developer experience**
   - Add golden JSON fixtures for the showpiece.
   - Add examples for catalog authors adding a new pointer safely.
   - Add a short operator guide for reviewing receipts.

## Later Tasks

- A2A SDK adapter only after the JSON wrapper proves useful.
- MCP resource exposure for catalogs only after structured tool output is stable.
- Catalog version pinning and external artifact verification improvements.

## Non-Goals

- Building a general execution runtime
- Running resolved implementation strings by default
- Replacing A2A transport
- Replacing MCP tools/resources
- Making clinical diagnosis or treatment recommendations
