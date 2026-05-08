# Security Model

Agent Pidgin protects the resolver boundary, not arbitrary downstream execution.

## Guarantees

- Invalid messages fail before resolution.
- Policy can block resolution before artifact mounting.
- Safety-sensitive catalog metadata triggers receipt policy warnings even when the pointer is outside legacy sensitive prefixes.
- Catalog hashes are deterministic.
- Signed skill manifests must include structured signature metadata at schema validation time.
- Receipts record what was resolved, when, and against which artifact revision.
- The default policy rejects unpinned revisions such as `main`.
- High-risk semantic drift blocks proposed contract events in the flight recorder.
- Removed control guardrails such as `agent.request_human_review` and `agent.attach_receipts` are high-risk semantic diff findings.
- `record_memory_update` detects unapproved memory guardrail weakening.
- AAFR traces are hash-chained with `previous_event_hash`, `event_hash`, and `trace_hash`.
- Trace schema validation requires event hashes and the top-level trace hash.
- `validate_trace_integrity` detects trace tampering after generation.
- HTTP sidecar requests are capped at 1 MiB before body read.

## Non-Guarantees

- Agent Pidgin does not sandbox arbitrary code execution.
- Agent Pidgin does not prove that implementation strings are safe to run.
- Agent Pidgin does not replace artifact signing, repository access control, or runtime sandboxing.
- Agent Pidgin does not claim hardware-level tamper-proof logging.
- Local trace hash chaining is tamper-evident, not equivalent to an append-only audit store.
- Agent Pidgin does not expose private chain-of-thought or prove model honesty.
- Simulated mount mode proves preflight semantics and provenance shape, not real artifact availability. Use `--gateway hf` or an injected gateway when real mounting must be demonstrated.

## Safe Use

Use Agent Pidgin to produce an auditable implementation plan. If another system executes implementation strings, that system needs its own sandbox, approval, and runtime controls.

Use AAFR traces to inspect proposed agent behavior before tools act. For production audit guarantees, store trace hashes or signed trace roots in an external append-only system.
