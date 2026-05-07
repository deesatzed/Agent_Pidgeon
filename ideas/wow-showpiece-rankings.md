# Wow Showpiece Rankings

Saved: 2026-05-07

## Baseline Ranking

Success means a credible demo can be built with the current Agent Pidgeon direction. Wow chance means a serious AI, agent, security, or enterprise audience would quickly understand why it matters and might share or use it.

| Rank | Showpiece idea | Success chance | Wow / noticed / used chance | Notes |
|---:|---|---:|---:|---|
| 1 | Agent Trust Firewall for A2A/MCP | 88% | 82% | Intercepts an agent handoff, validates schema, enforces policy, resolves pointers, blocks unsafe drift. |
| 2 | Before/After Unsafe Agent Handoff Demo | 92% | 78% | Shows a normal-looking task that removes PHI scrubbing or changes artifact revision, then Pidgeon catches it. |
| 3 | Receipts Flight Recorder for Agents | 84% | 76% | Timeline showing who requested what, which catalog resolved it, hashes, policy findings, and receipts. |
| 4 | MCP Context Diet / Semantic Compression Demo | 72% | 80% | Compares giant prompt/tool context against compact semantic contracts with auditability. |
| 5 | Enterprise Agent Governance Gate | 78% | 73% | Policy packs for allowed repos, pinned revisions, sensitive pointer rules, rejected contracts, approval-ready receipts. |
| 6 | LLM-Assisted Contract Authoring Studio | 80% | 70% | Plain language to contract, with unknown pointers rejected and trusted catalog resolution preserved. |
| 7 | Clinical Safety Preflight, Non-Diagnostic | 82% | 68% | PHI scrub, negation preservation, uncertainty annotation, and receipts; useful but must be carefully framed. |
| 8 | Supply Chain / Release Safety Resolver | 68% | 72% | Agent requests deploy/update; Pidgeon resolves tests, CVE check, approval, rollback, and receipt requirements. |
| 9 | Multi-Agent Semantic Contract Exchange | 65% | 69% | Same contract travels through A2A wrapper, MCP tool, CLI, and resolver with identical receipts. |
| 10 | CAD / Manufacturing Review Gate | 45% | 62% | Later idea; could be strong with domain catalogs and visual review, but not first showpiece. |

## Rethink

These are useful, but not all are big enough. The sharper showpiece is not just "Pidgeon resolves contracts." It is:

> Agent Pidgeon as the semantic audit layer for autonomous agents.

The strongest version is a verifiable agentic logging and debugging layer: every tool call, memory update, context mutation, and agent handoff is wrapped in a compact semantic contract. Pidgeon validates the contract, enforces policy, resolves trusted meanings, diffs changes, and emits receipts before or alongside execution.

Pidgeon should not claim to be a hardware-level tamper-proof logger yet. It can be the deterministic semantic layer that makes such logs meaningful and reviewable.

## Revised Top Showpiece

Name: **Agent Pidgeon Flight Recorder**

Tagline:

> OpenTelemetry for agent intent, memory, and tool calls, with semantic receipts.

Demo story:

1. An autonomous agent receives a goal.
2. It proposes memory/context updates and tool calls.
3. Each proposal is represented as a compact Pidgeon semantic contract.
4. Pidgeon validates schema and policy.
5. Pidgeon resolves trusted semantic pointers and emits receipts.
6. A subtle context corruption enters the trace.
7. The agent starts chaining unsafe actions.
8. Pidgeon flags the semantic drift, unsafe memory delta, untrusted pointer, or unpinned artifact before the damage spreads.
9. A debugger UI replays the whole sequence with receipts.

Why this is more wow:

- It solves a real production fear: autonomous agents acting in opaque loops.
- It gives security teams something concrete: replayable, inspectable, policy-checked traces.
- It positions Pidgeon beside MCP/A2A instead of competing with them.
- It gives a novice an easy analogy: a black box flight recorder and debugger for AI agents.

Estimated success chance: 76%

Estimated wow / noticed / used chance: 88%

Why success is not higher:

- We need a trace schema for tool calls, memory updates, and context diffs.
- We need a replay UI or at least a high-quality terminal/HTML timeline.
- We need careful language: Pidgeon proves semantic resolution and provenance, not model truth or hardware tamper-proofing.

## Best Immediate Build

Build a deterministic local showpiece called `agent_flight_recorder_demo`.

It should include:

- a benign agent loop
- a corrupted context/memory injection
- a sequence of proposed tool calls
- Pidgeon semantic contracts for each proposed action
- policy decisions
- semantic diffs
- receipts
- a replayable JSON trace
- a human-readable timeline report

The decisive "wow" moment:

> The model says everything is fine, but the Pidgeon trace shows exactly where intent drift entered and which semantic guardrail blocked the next unsafe action.
