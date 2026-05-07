# What Agent Pidgin Does Now

Agent Pidgin solves a simple but important problem: AI agents need a clearer way to agree on what instructions mean, and operators need a replayable way to see when that meaning changes.

The source of truth for the product direction is [product-framing.md](product-framing.md).

Today, one agent might send another agent a large natural-language prompt:

```text
Clean this text, normalize it, remove private health information, preserve negation,
attach evidence, and only use approved logic.
```

That sounds clear to a person, but it is not precise enough for reliable agent-to-agent work. Two agents can read the same instruction and make different choices. One might remove too much context. Another might miss a safety step. A third might use a newer behavior that was never reviewed.

Agent Pidgin changes that exchange into a compact semantic contract:

```json
{
  "steps": [
    "str.trim",
    "str.normalize_unicode",
    "clinical.phi.scrub",
    "clinical.negation.preserve",
    "agent.attach_receipts"
  ]
}
```

Each short step is a semantic pointer. The receiver resolves those pointers locally against trusted, versioned catalogs instead of guessing what the sender meant.

## What The App Does

Agent Pidgin accepts a structured message from an agent or CLI user, validates it, checks it against policy, resolves the requested semantic steps, and returns an auditable implementation plan.

The app currently:

- Accept compact semantic contracts from agents or command-line users.
- Validate message structure before resolution begins.
- Check policy rules such as whether artifact revisions are pinned and whether sensitive steps require receipts.
- Load trusted catalogs that define pointers like `str.trim`, `clinical.phi.scrub`, and `agent.attach_receipts`.
- Resolve each pointer into a target-language implementation plan.
- Attach receipts showing exactly what was resolved, from which catalog, against which artifact, and when.
- Compare contracts and flag semantic drift, including removed safety primitives and control guardrails.
- Record Autonomous Agent Flight Recorder traces for goals, memory updates, proposed tool calls, policy decisions, diffs, and receipt IDs.
- Detect unapproved memory guardrail weakening, such as changing `external_email_allowed` from `false` to `true`.
- Hash-chain trace events so tampering after trace generation is detectable.
- Expose the same core behavior through a CLI, MCP-style tool surface, and demo scripts.

The important point is that Agent Pidgin does not need to blindly execute implementation strings. Its core job is to produce a trusted, inspectable plan with provenance.

## Why You Would Want It

You would want Agent Pidgin anywhere autonomous agents need to exchange instructions that are more precise than ordinary prompts.

Natural language is flexible, but flexibility becomes a weakness when systems need reproducibility, review, and safety. If an agent says “scrub PHI,” that phrase can hide many choices:

- Should names be removed?
- Should dates be removed?
- Should medical record numbers be removed?
- Should negated clinical statements be preserved?
- Which reviewed implementation should be used?
- Can we prove later what was applied?

Agent Pidgin turns vague instructions into explicit semantic pointers backed by catalogs and receipts.

Instead of trusting that two agents interpret a phrase the same way, they exchange a small contract and resolve it against known artifacts.

## Why A Software Engineer Would Want It

A software engineer would want Agent Pidgin when building or operating autonomous agents that can use tools, update memory, or hand off work to other agents.

It helps answer questions that ordinary logs do not answer cleanly:

- What semantic contract did the agent submit before the tool call?
- Was the contract schema-valid?
- Which policy findings applied?
- Which trusted catalog defined each pointer?
- Did this proposed action remove human review, receipts, evidence, PHI scrubbing, or another guardrail?
- Did memory/context drift weaken an operating boundary?
- Can we detect if a trace was modified after generation?

This gives an SWE a deterministic debugging and governance primitive instead of relying only on prompt text or a second model's opinion.

## How It Benefits Agent Systems

Agent Pidgin gives agent systems four practical benefits.

First, it improves reproducibility. The same message, catalog, and artifact revision should resolve to the same implementation plan.

Second, it improves auditability. Each resolved step can carry a receipt showing the pointer, type signature, selected implementation, catalog hash, artifact revision, resolver version, and resolution time.

Third, it improves safety. Policy checks can reject untrusted artifact kinds, floating branch revisions, missing receipts, or dangerous changes to sensitive workflows.

Fourth, it improves interoperability. Agents can exchange compact contracts instead of long prompts, while each receiver still resolves behavior locally according to its own trusted catalogs and policies.

Fifth, it improves agent debugging. A flight-recorder trace can show the moment where a memory update weakened a guardrail or a later contract removed safety steps.

## Why It Is Novel

Agent Pidgin is novel because it treats agent intent as a structured, resolvable, diffable contract rather than a vague prompt or an after-the-fact log label.

It is not merely telemetry. Telemetry can say that a tool call happened. Pidgin can say whether the proposed tool call had the required semantic guardrails, whether those guardrails changed, and which receipts prove the resolution.

It is not merely an auditor agent. A second LLM can review behavior, but it is still another probabilistic model. Pidgin uses schemas, policies, catalogs, hashes, diffs, and receipts for the enforcement path.

## How It Fits With A2A And MCP

Agent Pidgin is not an A2A replacement and it is not an MCP replacement.

A2A is the transport and collaboration layer: it helps agents communicate.

MCP is the tool and context layer: it helps agents use tools, resources, prompts, and structured outputs.

Agent Pidgin is the meaning layer: it helps agents exchange compact, auditable semantic instructions.

The relationship is:

```text
A2A moves the message.
MCP exposes tools and resources.
Agent Pidgin defines and audits the meaning.
```

## Current Expectation

The current resolver flow is:

```text
Input:
  compact semantic contract

Process:
  validate schema
  enforce policy
  locate trusted artifact
  resolve semantic pointers
  attach receipts

Output:
  trusted implementation plan
  provenance receipts
  policy findings
```

The main value is not that Agent Pidgin runs code. The main value is that it lets autonomous agents exchange small, precise, inspectable instructions instead of relying only on vague prompts.

The current flight-recorder flow is:

```text
Input:
  agent goal, memory update, or proposed tool-call contract

Process:
  hash payload
  validate contract when present
  enforce policy
  resolve trusted pointers
  diff against prior safe intent
  detect guardrail weakening
  hash-chain trace event

Output:
  replayable trace event
  policy findings
  semantic diff
  receipt IDs
  trace hash
```
