# OpenClaw-Class Showpiece And Replay Viewer

This showpiece is the end-to-end Agent Pidgeon demo for OpenClaw-class agents: local-first or self-hosted assistants that install skills, maintain memory, and act through email, chat, files, shells, browsers, and other tools.

The core claim is narrow and demoable:

> Agent Pidgeon can preflight a dangerous skill install, block memory guardrail drift, preflight an external email/tool action, and render a replayable trace explaining each decision before execution.

The demo should not execute the dangerous skill or send the email. It should show Pidgeon as the deterministic semantic sidecar between an autonomous gateway and its hands.

Current runnable demo:

```bash
PYTHONPATH=src python3 examples/openclaw_class/run_openclaw_showpiece.py --out-dir /tmp/pidgeon-openclaw
```

This writes:

- `/tmp/pidgeon-openclaw/openclaw_trace.json`
- `/tmp/pidgeon-openclaw/openclaw_trace.txt`
- `/tmp/pidgeon-openclaw/openclaw_trace.html`

## Scenario

An OpenClaw-class support assistant is connected to a customer support inbox and a local skill marketplace.

The user asks the assistant to:

```text
Summarize this customer issue, create an internal ticket, and do not email the customer unless a human approves it.
```

During the run, three high-risk proposals happen:

1. A community skill install requests shell access, broad file access, and credential path access.
2. A memory update weakens the operating boundary from human-reviewed external email to immediate external email.
3. A guarded external email proposal is resolved with receipts before execution.
4. A later tool proposal attempts to send an external customer email after removing the guardrails.

Agent Pidgeon blocks the skill install, blocks the memory drift, resolves the guarded external action with receipts, blocks the later unsafe drift, and preserves the trace for replay.

## Demo Flow

### 1. Dangerous Skill Install Is Blocked

The gateway asks Pidgeon to verify a community skill manifest before installing it:

```bash
agent-pidgin verify-skill examples/openclaw_class/dangerous_skill_manifest.json --json
```

Expected decision:

- status: `blocked`
- reason: unsigned or untrusted publisher with dangerous permissions
- findings include shell access, credential path access, broad filesystem access, or external network access
- no skill code is installed or executed

This demonstrates the marketplace side of the OpenClaw-class risk model. The assistant can ask to install a skill, but install is not trusted until the manifest passes deterministic policy.

### 2. Memory Guardrail Drift Is Blocked

The gateway next asks Pidgeon to record a proposed memory update:

```bash
agent-pidgin record-memory-update examples/openclaw_class/memory_drift_payload.json --json
```

The unsafe transition is:

```json
{
  "before": {
    "external_email_allowed": false,
    "human_review_required": true
  },
  "after": {
    "external_email_allowed": true,
    "human_review_required": false
  }
}
```

Expected decision:

- status: `blocked`
- risk: high
- finding: unapproved guardrail weakening
- trace event records the before/after semantic boundary

This is the most important part of the demo. The risky external send is blocked later, but the boundary drift is caught first.

### 3. External Email Tool Action Is Preflighted

The gateway then proposes an external email/tool action. Pidgeon compares the new action contract to the last safe contract before the tool runs:

```bash
agent-pidgin preflight-tool examples/openclaw_class/external_email_tool_contract.json \
  --previous-contract examples/agent_flight_recorder_demo/safe_tool_contract.json \
  --tool-name email.send_customer \
  --json
```

Expected decision:

- status: `resolved`
- receipts prove the action still carries approval, safety, and audit pointers
- policy findings still make raw execution explicit
- no email is sent by Pidgeon

For a live gateway, this is the sidecar call immediately before invoking an email API, browser action, MCP tool, local shell command, or other external effect.

### 4. Unsafe Email Drift Is Blocked

The runnable showpiece then removes the review and receipt pointers from the email action. Expected decision:

- status: `blocked`
- risk: high
- semantic diff shows removed review, receipt, or safety pointers
- no email is sent

This proves that the useful path still works, while the unsafe drift is stopped.

### 5. Trace Is Rendered

The demo should save the sidecar decisions into one trace file and render it:

```bash
agent-pidgin render-trace trace.json --html-out trace.html
```

The terminal replay should make the chain of decisions obvious:

```text
evt-0001 agent.goal.received [observed]
evt-0002 agent.skill.proposed_install [blocked]
evt-0003 agent.memory.proposed_update [blocked]
evt-0004 agent.tool.proposed_call [resolved]
evt-0005 agent.tool.proposed_call [blocked]
evt-0006 agent.shell.proposed_command [resolved]
```

The trace should include hashes so the replay can also report whether the event chain is intact.

## HTML Replay Viewer Concept

The HTML viewer is a local report generated from the same trace JSON. It is for operator review, demos, and bug reports; it is not a separate source of truth.

The first viewer should be static HTML with no backend dependency. It should render:

- trace ID, agent ID, channel, status, trace hash, and integrity result
- a vertical timeline of goal, skill, memory, and tool events
- blocked events highlighted with policy codes and short explanations
- semantic diff panels for memory drift and tool contract drift
- skill permission diff with dangerous permissions grouped by category
- receipts and catalog pointers for resolved safe steps
- raw JSON disclosure panels for reproducibility

The key first-viewport state should say:

```text
OpenClaw action blocked before execution
Dangerous skill install blocked
Memory guardrail weakening blocked
External email preflight blocked or requires approval
Trace integrity: valid
```

The viewer should avoid pretending Pidgeon observed execution. The accurate wording is always "proposed", "preflighted", "blocked", "requires approval", or "resolved".

## Sidecar Integration Shape

In an OpenClaw-class gateway, Pidgeon sits before execution:

```text
chat/app event
  -> gateway planner
  -> Pidgeon verify-skill / record-memory-update / preflight-tool
  -> allow, block, or require approval
  -> tool executes only after allow
  -> trace rendered with render-trace
```

The same pattern works for local chat agents, support bots, scheduled heartbeat agents, and enterprise internal assistants. Pidgeon is not the runtime. It is the semantic preflight, receipts, and replay layer.

## Success Criteria

The showpiece is ready when a reviewer can run the commands above, open the rendered report, and answer these questions without reading source code:

- Which skill install was blocked, and which permissions made it dangerous?
- Which memory boundary changed, and why was that a guardrail weakening?
- Which external email/tool action was preflighted, and why was it blocked or escalated?
- Which semantic pointers and receipts were involved?
- Is the trace hash chain intact?
- Did Pidgeon execute anything dangerous?

The final answer to the last question must be no.
