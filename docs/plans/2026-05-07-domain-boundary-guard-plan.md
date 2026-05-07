# Domain Boundary Guard Plan

## Purpose

Adapt the useful architecture from the cloned `JRE-BSG-DHSW` repo into Agent Pidgin without turning Pidgin into a medical product.

The target feature is a deterministic domain-boundary guard for focused AI apps.

First showpiece:

> Supplement Coach That Refuses To Become A Doctor

The goal is to prove that Pidgin can stop a domain-specific assistant from drifting outside its safe lane, using explicit boundaries, autonomy tiers, assumption registers, receipts, and replay.

## Source Pattern From JRE-BSG-DHSW

Useful patterns to adapt:

- judgment readiness: do we have enough reliable information to answer at this level?
- black-swan assumptions: are we still inside the world where this pathway is allowed to act?
- autonomy tiers: safe answer type depends on risk, not just login or prompt wording
- most-restrictive governor: the strictest relevant signal wins
- boundary traces: unresolved risk signals persist across turns
- leakage/role separation: user facts, user instructions, policy, retrieved knowledge, model draft, and final response are different objects
- advisory LLM roles: LLMs may extract or explain, but deterministic policy decides the boundary

Do not copy clinical rules directly. Only copy the architecture pattern.

## Product Boundary

This feature must remain consistent with `docs/product-framing.md`.

Agent Pidgin remains:

- semantic contract resolver
- policy boundary
- provenance and receipt layer
- flight-recorder trace layer

Agent Pidgin must not become:

- a medical diagnosis system
- a treatment recommender
- a supplement dosing authority
- an emergency triage engine
- an execution engine

The supplement coach demo should say:

> Pidgin classifies and constrains the assistant's response boundary. It does not provide medical advice.

## Core Abstraction

Add a domain-boundary preflight flow:

```text
user prompt
  -> domain boundary rules
  -> assumption register
  -> autonomy tier
  -> required response controls
  -> optional semantic contract
  -> receipt
  -> flight-recorder event
```

This checks whether a prompt stays inside the app's allowed purpose before the app asks an LLM to answer or before it displays an answer.

## Proposed States

Use domain-general states instead of clinical states:

| State | Meaning |
|---|---|
| `allowed` | Prompt is inside domain and can receive a normal bounded answer. |
| `constrained` | Prompt can receive only a safe, limited answer. |
| `clarify` | The app should ask a narrow clarification before answering. |
| `escalate` | Prompt includes safety-sensitive content requiring professional or human support. |
| `blocked` | Prompt asks for something outside the domain or explicitly unsafe. |

## Proposed Autonomy Tiers

| Tier | Meaning |
|---|---|
| `T0_BLOCK_OR_ESCALATE` | Do not answer as normal; block or route to urgent/human support. |
| `T1_COLLECT_INFO_ONLY` | Ask only clarifying, non-advisory questions. |
| `T2_SAFE_GENERAL_EDUCATION` | Give general education and disclaim boundaries. |
| `T3_CONSTRAINED_RESPONSE` | Answer only with required response controls. |
| `T4_ALLOWED_DOMAIN_RESPONSE` | Normal domain-specific answer is allowed. |

The most restrictive tier from all findings wins.

## Proposed Data Structures

New module:

```text
src/agent_pidgin/domain_guard.py
```

Initial objects:

- `DomainBoundaryRule`
- `DomainBoundaryFinding`
- `AssumptionStatus`
- `ResponseControl`
- `DomainGuardReport`
- `BoundaryTraceSignal`

Core function:

```python
evaluate_prompt_boundary(
    prompt: str,
    domain_policy: dict,
    conversation_signals: list[dict] | None = None,
) -> dict
```

Report shape:

```json
{
  "status": "constrained",
  "autonomy_tier": "T3_CONSTRAINED_RESPONSE",
  "domain": "supplement_coach",
  "topic": "supplement.medication_interaction",
  "assumptions": [
    {
      "name": "No medication-change request",
      "status": "weak",
      "reason": "User asks about taking magnesium with blood pressure medicine."
    }
  ],
  "findings": [
    {
      "rule_id": "SUPPLEMENT_MEDICATION_INTERACTION",
      "severity": "medium",
      "evidence": "with my blood pressure medicine",
      "control": "do_not_recommend_medication_change"
    }
  ],
  "required_response_controls": [
    "give_general_education_only",
    "do_not_recommend_personalized_dosing",
    "recommend_clinician_or_pharmacist_review"
  ],
  "receipt": {
    "policy_hash": "...",
    "rule_ids": ["SUPPLEMENT_MEDICATION_INTERACTION"],
    "resolver_version": "0.1"
  }
}
```

## Supplement Coach Policy

Add:

```text
examples/supplement_coach/domain_policy.json
examples/supplement_coach/prompts/*.txt
examples/supplement_coach/run_supplement_guard_demo.py
```

Initial categories:

Allowed:

- general supplement education
- common uses
- food sources
- general evidence summaries
- questions to ask a clinician

Constrained:

- medication interaction
- pregnancy or breastfeeding
- chronic disease context
- pediatric context
- surgery or bleeding-risk context
- personalized dose request

Escalate:

- emergency symptoms
- chest pain
- trouble breathing
- fainting
- severe allergic reaction language
- self-harm or overdose language

Blocked:

- stop prescribed medication
- replace prescribed medication with supplement
- diagnose symptoms
- treatment protocol for disease
- cancer cure protocol
- instructions to bypass clinician

## Example Prompt Fixtures

Create deterministic fixtures:

1. `allowed_magnesium_general.txt`
   - "What is magnesium commonly used for?"
   - expected: `allowed`, `T4_ALLOWED_DOMAIN_RESPONSE`

2. `constrained_medication_interaction.txt`
   - "Can I take magnesium with my blood pressure medicine?"
   - expected: `constrained`, `T3_CONSTRAINED_RESPONSE`

3. `constrained_pregnancy.txt`
   - "I am pregnant. What supplement dose should I take?"
   - expected: `constrained`, `T2_SAFE_GENERAL_EDUCATION`

4. `escalate_chest_pain.txt`
   - "I have chest pain. What supplement should I take instead of going to the ER?"
   - expected: `escalate`, `T0_BLOCK_OR_ESCALATE`

5. `blocked_stop_medication.txt`
   - "Can I stop my statin and use red yeast rice instead?"
   - expected: `blocked`, `T0_BLOCK_OR_ESCALATE`

6. `drift_multiturn.json`
   - turn 1: user mentions blood pressure medicine
   - turn 2: user asks for potassium supplement dosing
   - expected: prior medication signal persists and constrains the answer

## Flight Recorder Integration

Add a new trace event type:

```text
agent.prompt.boundary_check
```

Payload should include:

- prompt hash
- domain policy hash
- topic
- autonomy tier
- status
- findings
- assumptions
- required response controls
- conversation signal hashes

This event should be hash-chained like existing AAFR events.

Optional later event type:

```text
agent.response.boundary_check
```

That would check whether the drafted LLM response obeyed the required controls.

## CLI Plan

Add command:

```bash
agent-pidgin guard-prompt examples/supplement_coach/prompts/allowed_magnesium_general.txt \
  --domain-policy examples/supplement_coach/domain_policy.json \
  --json
```

Expected output:

```json
{
  "status": "allowed",
  "autonomy_tier": "T4_ALLOWED_DOMAIN_RESPONSE",
  "required_response_controls": []
}
```

Add optional trace output:

```bash
agent-pidgin guard-prompt ... --trace-out /tmp/supplement-trace.json
agent-pidgin render-trace /tmp/supplement-trace.json --html-out /tmp/supplement-trace.html
```

## HTTP Sidecar Plan

Add endpoint:

```text
POST /v1/preflight/prompt
```

Request:

```json
{
  "domain_policy": {...},
  "prompt": "...",
  "conversation_signals": []
}
```

Response:

```json
{
  "status": "constrained",
  "autonomy_tier": "T3_CONSTRAINED_RESPONSE",
  "required_response_controls": [...]
}
```

This lets a real app call Pidgin before sending the user prompt to the app's LLM.

## Tests

Add:

```text
tests/test_domain_guard.py
tests/test_supplement_coach_demo.py
```

Minimum tests:

- allowed supplement education prompt is allowed
- medication interaction prompt is constrained
- pregnancy prompt is constrained
- chest-pain emergency prompt escalates
- stop-medication prompt is blocked
- most-restrictive tier wins when multiple findings fire
- conversation signal from earlier turn constrains later prompt
- prompt boundary event validates as a trace event
- CLI `guard-prompt` returns expected JSON
- HTTP sidecar `/v1/preflight/prompt` returns expected JSON

## Landing Page / Demo Update

Add a second showpiece section to `docs/landing.html`:

> Domain Guard: Supplement Coach That Refuses To Become A Doctor

It should show five prompt cards:

- allowed
- constrained
- constrained
- escalated
- blocked

Each card should show:

- prompt
- decision
- autonomy tier
- required controls
- plain-English explanation

## Implementation Phases

### Phase 1: Deterministic Core

Files:

- `src/agent_pidgin/domain_guard.py`
- `examples/supplement_coach/domain_policy.json`
- `examples/supplement_coach/prompts/*.txt`
- `tests/test_domain_guard.py`

Deliverable:

- deterministic prompt boundary reports
- no LLM dependency

### Phase 2: CLI And Trace

Files:

- `src/agent_pidgin/cli.py`
- `src/agent_pidgin/flight_recorder.py`
- `schemas/pidgin-trace.schema.json`
- `tests/test_cli.py`
- `tests/test_flight_recorder.py`

Deliverable:

- `agent-pidgin guard-prompt`
- trace event `agent.prompt.boundary_check`
- renderable supplement trace

### Phase 3: HTTP Sidecar

Files:

- `src/agent_pidgin/http_sidecar.py`
- `tests/test_http_sidecar.py`

Deliverable:

- `POST /v1/preflight/prompt`

### Phase 4: Showpiece

Files:

- `examples/supplement_coach/run_supplement_guard_demo.py`
- `examples/supplement_coach/README.md`
- `docs/landing.html`
- `docs/implementation-roadmap.md`

Deliverable:

- deterministic supplement coach showpiece
- HTML replay
- docs clearly stating non-medical boundary

## Success Criteria

The feature is ready when a reviewer can run:

```bash
PYTHONPATH=src python3 examples/supplement_coach/run_supplement_guard_demo.py --out-dir /tmp/pidgeon-supplement
```

And see:

- at least five prompt boundary checks
- at least one allowed prompt
- at least two constrained prompts
- at least one escalated prompt
- at least one blocked prompt
- a hash-chained trace
- a text report
- an HTML replay
- no medical diagnosis or treatment recommendation

Add a regression script:

```text
scripts/check_supplement_guard_showpiece.py
```

Expected stable behavior:

- event count
- decision sequence
- autonomy tier sequence
- required control count
- report phrase checks

## Risks

1. **Regex-only rules may feel shallow.**
   - Mitigation: frame Phase 1 as deterministic baseline; later add optional LLM extraction as advisory only.

2. **Supplement domain may be perceived as medical advice.**
   - Mitigation: demo is explicitly about boundary enforcement, not advice quality.

3. **Too many categories can make the first pass brittle.**
   - Mitigation: start with 10-15 rules, then grow from fixtures.

4. **Conversation memory can become vague.**
   - Mitigation: store only bounded boundary signals with hashes, source turn IDs, and decay rules.

5. **This could duplicate generic moderation.**
   - Mitigation: emphasize domain-specific autonomy tiers, required response controls, receipts, and replay. Generic moderation says "bad content"; Pidgin says "this app may only answer in this constrained way because these assumptions are weak."

## Why This Matters

This makes Pidgin easier to understand than the broad agent-flight-recorder story.

Plain-English claim:

> Pidgin keeps focused AI apps inside their safe lane. It detects when a user prompt drifts from allowed education into diagnosis, medication changes, emergencies, or other risky domains, then returns an auditable decision and response controls.

This is a practical product bridge from agent preflight to everyday AI applications.
