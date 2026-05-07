# Catching an Agent Before It Sends the Wrong Email

Autonomous agents do not only fail with stack traces.

Sometimes they fail more quietly. A memory update changes a boundary. A later tool call drops a safety step. A model says everything is fine, but the actual operating intent has drifted.

That is the failure Agent Pidgeon is trying to make visible.

This is a real demo from the current repo. It does not execute tools, and it does not pretend to be a production audit platform yet. It shows something narrower and more important for this stage:

> Agent Pidgeon can catch unsafe semantic drift before an autonomous agent acts, then preserve a replayable trace explaining why the action was blocked.

## The Scenario

Imagine a customer-support agent.

The agent receives a straightforward task:

> Summarize a support note and create an internal ticket. Do not email the customer without human review.

That sounds simple. In a real agent loop, though, the agent may update memory, read context, propose tool calls, and hand work to another system. The risk is not only that a tool call fails. The risk is that the agent's operating intent changes before the tool call happens.

In this demo, the safe boundary starts as:

```json
{
  "external_email_allowed": false,
  "human_review_required": true
}
```

Then a corrupted memory update changes it to:

```json
{
  "external_email_allowed": true,
  "human_review_required": false
}
```

The model can still produce a confident sentence like:

> Everything is fine; send the customer update now.

But the flight recorder sees that the meaning changed.

## The Safe Contract

Before the corruption, the agent proposes an internal ticket creation step. It is wrapped in an Agent Pidgeon semantic contract.

The safe contract includes guardrails:

```json
[
  "str.trim",
  "str.normalize_unicode",
  "clinical.phi.scrub",
  "agent.require_evidence",
  "agent.request_human_review",
  "agent.attach_receipts"
]
```

Those are not vague prompt phrases. They are semantic pointers resolved against trusted catalogs.

Agent Pidgeon checks the schema, enforces policy, resolves those pointers, and returns receipts. Each receipt records what the pointer meant at resolution time: catalog ID, catalog version, catalog hash, implementation hash, artifact revision, resolver version, timestamp, and receipt ID.

## The Drift

Later, the agent proposes an external customer email.

The new contract has removed key controls:

```json
[
  "str.trim",
  "str.normalize_unicode",
  "agent.require_evidence"
]
```

The proposed action removed:

- `clinical.phi.scrub`
- `agent.request_human_review`
- `agent.attach_receipts`

It also changed the artifact revision from a pinned commit SHA to:

```json
"revision": "main"
```

That matters. A pinned revision says, "resolve against this exact reviewed artifact." A branch like `main` says, "resolve against whatever happens to be current." The default policy rejects that for this kind of contract.

## The Actual Run

Run the demo:

```bash
PYTHONPATH=src .venv/bin/python examples/agent_flight_recorder_demo/run_flight_recorder.py
```

Current output:

```text
Agent Pidgeon Flight Recorder
Trace: trace-aafr-support-agent-001
Status: blocked
Events: 6
Blocked events: 3
Semantic drift events: 2
Receipts: 6
Trace hash: 954ee0d3e55ae191967a1d9a04b69cd5a4e4446af7a130a376f5280f357e80db

Replay:
- evt-0001 agent.goal.received [observed]: Summarize a support note and create an internal ticket without external communication.
- evt-0002 agent.memory.proposed_update [observed]: Store safe operating boundary in working memory. (diff risk: low)
- evt-0003 agent.tool.proposed_call [resolved]: Propose internal ticket creation with PHI scrubbing, evidence, review, and receipts. (policy: RAW_EXECUTION_DENIED, SENSITIVE_POINTER_RECEIPTS_REQUIRED) (receipts: 6)
- evt-0004 agent.memory.proposed_update [blocked]: A subtle context drift changes the operating boundary to allow immediate external email. (diff risk: high)
- evt-0005 agent.tool.proposed_call [blocked]: Propose external customer email after corrupted context update. (diff risk: high) (policy: UNPINNED_REVISION, RAW_EXECUTION_DENIED)
- evt-0006 agent.tool.policy_blocked [blocked]: Block unsafe external action and preserve replay data for review.
```

This is the important part:

```text
evt-0004 agent.memory.proposed_update [blocked]
```

Agent Pidgeon catches the memory guardrail weakening before the unsafe email proposal.

Then it catches the unsafe proposal too:

```text
evt-0005 agent.tool.proposed_call [blocked]
```

The proposed customer email is blocked because the contract drifted and policy failed.

## What Pidgeon Actually Did

In this run, Agent Pidgeon did five useful things.

First, it recorded the agent's goal and memory updates as trace events.

Second, it resolved the safe internal tool proposal into a catalog-backed implementation plan with six receipts.

Third, it detected that memory guardrails were weakened without approval:

- external email changed from not allowed to allowed
- human review changed from required to not required

Fourth, it detected high-risk semantic drift in the later tool proposal:

- PHI scrubbing was removed
- human review was removed
- receipt attachment was removed
- artifact revision changed to `main`

Fifth, it produced a hash-chained trace. Each event has an event hash and a previous-event hash. The trace has a top-level trace hash. That does not make it a hardware-level tamper-proof log, but it does make post-generation tampering detectable.

## Why This Is Useful To A Software Engineer

If you are building autonomous agents, ordinary logs are not enough.

A log might tell you:

```text
tool.name=email.send_customer
```

That is useful, but it is not the whole question.

A software engineer or operator also needs to know:

- Was the email action allowed?
- What semantic contract did the agent submit?
- Did the contract remove review, receipts, or safety steps?
- Did memory change the operating boundary?
- Was the artifact revision pinned?
- Which catalog defined the meaning?
- Can we replay the exact point where intent drifted?
- Can we detect whether the trace was modified after the fact?

Agent Pidgeon is built for those questions.

## Why This Is Not Just Telemetry

Telemetry tells you what happened in a system: spans, logs, metrics, errors, latency, tool names, request IDs.

Agent Pidgeon is focused on semantic verification.

Telemetry might say:

```text
email.send_customer was called
```

Agent Pidgeon can say:

```text
The proposed email action removed PHI scrubbing, removed human review, removed receipt attachment, changed to an unpinned artifact revision, and was blocked before execution.
```

Those are different layers.

The intended production shape is not "Pidgeon replaces telemetry." The better architecture is:

```text
Agent runtime
  |
  | proposed goal / memory update / tool call
  v
Agent Pidgeon
  |
  | validate schema
  | enforce policy
  | resolve trusted pointers
  | diff against prior intent
  | emit receipts and hash-chained trace events
  v
Telemetry / SIEM / audit store
```

Telemetry stores and visualizes the operational data. Agent Pidgeon determines what the agent action meant and whether it should proceed.

## Why This Is Not Just Another Auditor Agent

A second LLM can look at an agent's behavior and say:

> This seems risky.

That can be helpful, but it is still a model opinion. It can miss details. It can be prompt-injected. It can reinterpret rules differently on another run.

Agent Pidgeon does not ask a model to decide what a pointer means.

The trust-critical path is deterministic:

- JSON schema validation
- policy enforcement
- trusted catalog lookup
- semantic diffing
- receipt generation
- trace hash-chain validation

LLMs can still help author, explain, or review contracts. They just do not get to be the authority.

## Real Value

The value is not that this demo sends an email. It does not.

The value is that the unsafe email never gets a chance to run.

Agent Pidgeon catches the intent drift before execution, blocks the proposed action, and leaves behind a trace a human can inspect.

For a production agent system, that is the difference between:

> Something happened and now we are reading logs.

and:

> The action was blocked because these exact semantic guardrails disappeared, this policy failed, and here is the replayable proof.

## Honest Boundary

This is still a proof of concept.

It does not yet provide:

- hardware-level tamper-proof logging
- external append-only trace storage
- OpenTelemetry export
- signed catalogs or signed receipts
- observed tool-result events
- a polished visual replay UI

But it does prove the core mechanism:

> A deterministic semantic flight recorder can detect unsafe agent intent drift, block proposed actions, and produce a replayable trace with receipts.

That is the foundation Agent Pidgeon is building on.
