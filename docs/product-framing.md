# Agent Pidgin Product Framing

This document is the source of truth for Agent Pidgin's project direction.

## Build Direction

Do not build Agent Pidgin as:

- an execution engine
- an A2A clone
- an MCP clone

Build Agent Pidgin as a semantic contract resolver and semantic flight-recorder layer.

The resolver should:

1. accept compact semantic contracts
2. validate schema
3. enforce policy
4. resolve semantic pointers against trusted catalogs
5. return an auditable implementation plan with receipts

The flight-recorder layer should:

1. record goals, memory/context updates, proposed tool calls, and handoffs as trace events
2. attach contract hashes, payload hashes, semantic diffs, policy findings, and receipt IDs
3. detect unapproved memory guardrail weakening
4. block high-risk semantic drift before downstream tools act
5. produce hash-chained traces that are tamper-evident after generation

The core deliverable is trustworthy resolution and provenance, not raw code execution.

## Product Boundary

Agent Pidgin sits beside transport and tool layers.

A2A is transport and collaboration.

MCP is tools, resources, prompts, and structured tool output.

Agent Pidgin is semantic meaning, policy, provenance, reproducibility, and replayable intent audit.

Agent Pidgin is not generic telemetry. Telemetry records runtime events, spans, metrics, and logs. Agent Pidgin verifies what an agent action means, whether that meaning drifted, whether policy allows it, and which receipts prove the resolution.

Agent Pidgin is not just another auditor agent. LLM reviewers can help explain and triage. They must not be the enforcement authority. Pidgin's trust path is deterministic.

## Design Commitments

Agent Pidgin should keep the trust-critical path deterministic. Schema validation, policy checks, catalog lookup, hashing, semantic diffing, and receipt generation should not depend on an LLM.

LLMs may help users author, explain, compare, or review contracts, but they must not be the source of truth for what a pointer means.

See [parallel-and-llm-authoring.md](parallel-and-llm-authoring.md) for how parallel implementation work and LLM-assisted authoring should fit around the deterministic resolver.

Resolved implementation strings are returned as auditable plan data. They should not be executed by default.

Clinical examples must remain safety-contract demonstrations. They must not make medical diagnosis, treatment, or triage claims.

## Current Implemented Surface

The current build includes:

- JSON schemas for messages, handshakes, catalogs, receipts, and traces
- trusted JSON catalog loading and catalog hashing
- policy enforcement for pinned artifact revisions, artifact kinds, raw execution denial, and sensitive pointer receipt requirements
- semantic diffing for safety-sensitive pointer removals, control guardrail removals, artifact drift, and implementation changes
- resolution receipts with catalog, artifact, implementation, resolver, and timestamp provenance
- CLI commands for validation, resolution, policy checks, diffs, catalog introspection, and LLM-assisted contract authoring/review
- MCP-style tool wrappers and A2A JSON examples around the same service boundary
- Autonomous Agent Flight Recorder traces with memory guardrail detection, high-risk drift blocking, and hash-chain integrity checks
