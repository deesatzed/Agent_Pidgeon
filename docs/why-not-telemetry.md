# Why Agent Pidgin Is Not Telemetry

Agent Pidgin is designed to complement telemetry, not replace it.

Telemetry answers operational questions:

- Which service ran?
- Which tool was called?
- How long did it take?
- Did it error?
- Which logs, metrics, and spans were emitted?

Agent Pidgin answers semantic governance questions:

- What did the agent propose to do?
- Was that proposal represented as a schema-valid contract?
- Which trusted catalog defined the meaning?
- Which policy findings applied?
- Did the semantic plan drift from the previous safe plan?
- Were safety or control guardrails removed?
- Which artifact revision was referenced?
- Which receipts prove the resolution path?
- Has the trace been tampered with after generation?

## Concrete Difference

A telemetry span might say:

```text
tool.name=email.send_customer
status=ok
duration_ms=118
```

An Agent Pidgin flight-recorder event can say:

```text
event=agent.tool.proposed_call
decision=blocked
reason=high-risk semantic drift
removed=clinical.phi.scrub, agent.request_human_review, agent.attach_receipts
policy_error=UNPINNED_REVISION
trace_hash=...
```

Both are useful, but they live at different layers.

Telemetry records runtime behavior. Agent Pidgin verifies semantic intent and provenance.

## Why It Matters For Agents

Autonomous agents fail differently from ordinary backend services. A service bug often appears as an exception, bad response, timeout, or resource issue. Agent failures can appear as semantic drift:

- a memory update silently changes "do not send externally" to "send now"
- a tool proposal removes human review
- a workflow drops receipt attachment
- an artifact target changes from a pinned commit SHA to `main`
- a model summary says the action is safe while the contract shows removed controls

Generic telemetry can record these as events if someone already knew what labels to emit. Agent Pidgin provides the deterministic contract, diff, policy, and receipt machinery that makes those events meaningful.

## How They Fit Together

The intended production shape is:

```text
Agent runtime
  |
  | proposed goal / memory update / tool call
  v
Agent Pidgin
  |
  | validate schema
  | enforce policy
  | resolve catalog pointers
  | diff against prior intent
  | emit receipts and hash-chained trace events
  v
Telemetry / SIEM / audit store
```

In this architecture, telemetry stores and visualizes events. Agent Pidgin determines what those events mean and whether a proposed action should proceed.
