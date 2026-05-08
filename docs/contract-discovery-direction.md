# Contract Discovery Direction

Agent Pidgin's next direction is contract discovery: finding messy workflow language that should become an explicit semantic contract.

The core product remains the deterministic resolver and flight recorder. Pidgin validates, enforces, resolves, receipts, diffs, and records. A model-assisted intake layer may propose candidate contracts, but it must never become the authority for pointer meaning, policy enforcement, or audit truth.

## Product Thesis

Organizations already have semantic contracts, but many are trapped inside ambiguous natural language.

Examples:

- "Clean this clinical note but preserve meaning."
- "Refactor the repo but don't break anything."
- "Run step 1, then truncate staging."
- "Send the customer update after approval."
- "Route urgent patient messages safely."

These instructions often hide exact steps, safety requirements, approval gates, evidence needs, and audit obligations. Pidgin's opportunity is to expose that hidden semantic debt and make it explicit, testable, auditable, and enforceable.

## Two Product Modes

### Resolver Mode

Input: a compact semantic contract.

Pidgin:

1. validates schema
2. enforces policy
3. resolves trusted catalog pointers
4. attaches receipts
5. records a hash-chained trace

This is the trust-critical path.

### Discovery Mode

Input: messy workflow language.

Pidgin-adjacent tooling:

1. scores whether the instruction hides semantic obligations
2. identifies ambiguity, risk, audit need, local terminology, and automation potential
3. suggests candidate contract types and hidden requirements
4. routes strong candidates toward contract authoring

This mode does not execute and does not decide policy. It decides whether the language is worth converting into a candidate contract.

## Nanowhale Framing

Nanowhale or another tiny local model is not better than Agent Pidgin.

It may become useful only as a cheap local intake compiler:

```text
messy workflow text
        ↓
local model proposes candidate contract/event
        ↓
strict schema validation
        ↓
Agent Pidgin validates, resolves, enforces, receipts, and traces
```

The model proposes. Pidgin decides.

Do not fine-tune a small model until the pain is proven with real examples. First prove that natural-language workflow text repeatedly contains hidden contract obligations.

## Validation Experiment

Collect 50-200 real messy workflow examples from agent instructions, issue tickets, clinical data transformation requests, EHR/informatics requests, SQL/SSIS tasks, support tickets, policy exceptions, and handoff notes.

Score each example from 0-16 across:

- ambiguity
- risk
- repeatability
- need for audit
- need for exact steps
- local terminology
- current friction
- automation potential

Interpretation:

- `0-5`: not a Pidgin problem
- `6-9`: weak or maybe useful
- `10-13`: good contract-discovery candidate
- `14-16`: excellent candidate

Continue if a meaningful cluster scores 10+ and humans agree the contract form exposes missing assumptions, safety constraints, evidence needs, or catalog gaps.

## First MVP

Build **Pidgin Pain Finder**:

```text
CSV: id, source_type, raw_instruction
        ↓
deterministic pain scoring
        ↓
JSON report with score, reasons, hidden requirements, and recommended next step
```

This is not the final product. It is the proof-of-pain instrument.

## Decision Rule

For any workflow, ask:

> Would a wrong but plausible interpretation of this instruction cause rework, risk, policy violation, unsafe automation, or loss of auditability?

If yes, it may belong in Pidgin's contract-discovery surface.
