# Autonomous Agent Flight Recorder

Agent Pidgeon can support an Autonomous Agent Flight Recorder direction without becoming an execution engine.

AAFR records the semantic intent around an agent's runtime behavior:

- received goals
- proposed memory/context updates
- proposed tool calls
- proposed handoffs
- schema validation
- policy findings
- semantic diffs
- trusted catalog resolution
- receipt IDs

## Role

AAFR is a replayable semantic audit layer. It answers:

- What did the agent ask to do?
- What changed since the previous safe intent?
- Was the proposed action schema-valid?
- Was it allowed by policy?
- Which catalog defined the action's meaning?
- Which receipts prove resolution?

AAFR does not claim:

- tool execution
- model honesty
- private chain-of-thought capture
- hardware-level tamper-proof logging

## Product Fit

This direction keeps the current source-of-truth framing intact. Agent Pidgeon remains a deterministic semantic contract resolver. The flight recorder composes resolver outputs into trace events so an operator can replay what happened.

## First Showpiece

The first demo is `examples/agent_flight_recorder_demo`.

It shows a safe support-agent goal, a safe proposed internal tool call, a corrupted memory update, and a later unsafe proposed external tool call. Pidgeon records the trace, catches semantic drift, records policy findings, and blocks the unsafe action without executing anything.

## Hardening Findings

The first AAFR pass proved the idea, but it had real gaps:

- high-risk semantic drift was visible but was not itself a blocking decision unless policy also failed
- removed control guardrails such as `agent.request_human_review` and `agent.attach_receipts` were not treated as high-risk removals
- memory/context guardrail weakening was recorded as a generic event instead of being detected deterministically
- event payloads had hashes, but the full trace was not hash-chained

Mitigations now in core:

- high-risk semantic drift blocks proposed contract events
- removed control guardrail pointers raise high-risk semantic diff notes
- `record_memory_update` detects unapproved guardrail weakening such as `external_email_allowed: false -> true`
- trace events include `previous_event_hash`, `event_hash`, and a top-level `trace_hash`
- `validate_trace_integrity` detects event tampering and broken hash chains

Remaining gaps:

- hash chaining is tamper-evident after trace generation, not a distributed tamper-proof store
- trace events are local JSON, not yet exported to OpenTelemetry spans
- tool results are not observed yet, only proposed calls
- approved memory writes need a richer approval model than a string `approved_by`
