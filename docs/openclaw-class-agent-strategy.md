# OpenClaw-Class Agent Strategy

OpenClaw-class agents are local-first or self-hosted autonomous assistants that connect chat channels, models, memory, skills, files, browsers, APIs, and scheduled background work.

Examples include OpenClaw itself, former/alternate naming around Clawdbot or Moltbot, and adjacent products that follow the same pattern: a gateway process receives messages from chat or app channels, asks a model what to do, and invokes tools or skills on the user's machine or infrastructure.

This is a high-need category for Agent Pidgeon because OpenClaw-class agents do real work:

- send messages
- read email
- manage calendars
- browse the web
- run scripts
- read and write files
- install community skills
- update persistent memory
- run scheduled heartbeat tasks
- coordinate across channels such as WhatsApp, Telegram, Discord, Slack, Teams, iMessage, and web chat

The core risk is not only that a tool fails. The deeper risk is that an autonomous agent's meaning drifts before the tool runs.

Agent Pidgeon should become the semantic preflight and flight-recorder sidecar for this whole class of systems.

## Positioning

OpenClaw-class platforms provide hands.

Agent Pidgeon provides semantic brakes, receipts, and replay.

```text
OpenClaw-class gateway
  |
  | goal / memory update / skill install / proposed tool call
  v
Agent Pidgeon sidecar
  |
  | schema validation
  | policy enforcement
  | skill and tool semantic contracts
  | memory guardrail checks
  | semantic diffs
  | catalog resolution
  | receipts
  | hash-chained flight-recorder trace
  v
allow / block / require approval
```

Pidgeon should not compete with OpenClaw. It should be the deterministic trust layer that OpenClaw-class agents can call before acting.

## OpenClaw-Class Variants And Pidgeon Uses

| Variant | What the agent does | Main risk | Pidgeon use |
|---|---|---|---|
| Personal local assistant | Runs on a laptop or homelab and acts through chat | private data exposure, accidental action | local preflight sidecar and trace store |
| Channel gateway | Connects WhatsApp, Slack, Teams, Discord, Telegram, iMessage, web chat | same command interpreted differently across channels | channel-specific semantic contracts and receipts |
| Skill marketplace | Installs community skills or Markdown-described automations | malicious or overbroad skills | skill manifest verification, permission diff, signed catalog mapping |
| Email/calendar assistant | Reads, drafts, sends, schedules | external communication without approval | human-review, external-send, and recipient-change guardrails |
| File/shell/browser automation | Reads files, edits files, runs scripts, browses sites | exfiltration, destructive commands, prompt-injected browsing | action preflight, sandbox policy, command/category contracts |
| Persistent memory agent | Stores user preferences and long-term facts | memory poisoning and boundary weakening | `record_memory_update` guardrail checks and memory drift receipts |
| Heartbeat or scheduled agent | Acts proactively on a timer | unattended action loops | scheduled-action contracts, recurring approval windows, run receipts |
| Multi-channel team agent | Coordinates work across several workspaces | identity confusion, data crossing boundaries | actor/channel identity binding and cross-channel policy |
| Local model variant | Uses Ollama or other local models | lower reliability, different behavior per model | model-independent deterministic policy and receipts |
| Cloud model variant | Uses GPT, Claude, Gemini, Grok, etc. | provider drift, prompt injection, data handling | provider-agnostic contract enforcement |
| Mobile node variant | Acts from a phone or paired device | constrained UI, hidden approvals | compact approval cards with semantic diff summaries |
| Enterprise clone | Remy/Gemini/Copilot-style internal assistants | scale, compliance, sanctioned vs shadow agents | registry integration, policy packs, audit trace export |
| Home automation variant | Controls lights, locks, alarms, IoT | physical-world action | high-risk physical-action policy and approval contracts |
| Finance/procurement variant | Pays vendors, updates accounts, approves invoices | fraud and regulated transactions | payment guardrail packs, evidence requirements, signed approvals |
| Support/customer ops variant | Emails customers, refunds accounts, changes tickets | customer harm and data leakage | external communication preflight and replayable blocked traces |

## Concrete Integration Surfaces

### 1. Gateway Sidecar

Run Pidgeon next to an OpenClaw-class gateway.

The gateway sends proposed actions to Pidgeon before execution:

```json
{
  "event_type": "agent.tool.proposed_call",
  "actor": "openclaw-support-agent",
  "channel": "slack",
  "tool_name": "email.send_customer",
  "contract": {
    "steps": [
      "comm.external_send",
      "agent.request_human_review",
      "agent.attach_receipts"
    ]
  }
}
```

Pidgeon returns:

- `resolved`
- `blocked`
- `drift_detected`
- `requires_approval`

### 2. Skill Install Preflight

Before a community skill is installed, Pidgeon checks:

- requested permissions
- declared semantic capabilities
- external network access
- file access
- shell access
- credential access
- whether the skill manifest is signed
- whether the skill maps to approved catalog pointers

Output:

```text
Install blocked: skill requests shell access and credential file access without signed publisher trust.
```

### 3. Memory Update Guardrails

OpenClaw-class agents often persist memory. That is useful and dangerous.

Pidgeon should inspect proposed memory updates:

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

Current core can already block this pattern through `record_memory_update`.

### 4. Channel-Aware Contracts

The same user intent can arrive through Slack, WhatsApp, Telegram, or Teams. Pidgeon should let policy depend on channel:

- personal WhatsApp can draft but not send work email
- Slack support channel can create tickets but not refund accounts
- Teams finance channel can propose payment review but not approve payment

### 5. Scheduled Heartbeat Preflight

For proactive agents that act on a timer, Pidgeon should require a recurring-action contract:

- what task can run
- what tools can be invoked
- what data can be touched
- what expiry window applies
- what receipt count is expected
- what conditions require fresh human approval

## Catalogs To Add

To support OpenClaw-class variants, add catalogs beyond `core`, `clinical_safety`, and `agent_ops`.

### `catalogs/communications.json`

Pointers:

- `comm.draft_external_message`
- `comm.send_external_message`
- `comm.require_recipient_verification`
- `comm.block_sensitive_external_send`
- `comm.require_human_approval`

### `catalogs/filesystem_ops.json`

Pointers:

- `fs.read_user_file`
- `fs.write_user_file`
- `fs.delete_user_file`
- `fs.require_path_allowlist`
- `fs.block_secret_paths`

### `catalogs/shell_ops.json`

Pointers:

- `shell.propose_command`
- `shell.block_destructive_command`
- `shell.require_sandbox`
- `shell.require_human_approval`

### `catalogs/skill_marketplace.json`

Pointers:

- `skill.install`
- `skill.verify_manifest`
- `skill.require_signed_publisher`
- `skill.diff_permissions`
- `skill.block_credential_access`

### `catalogs/memory_ops.json`

Pointers:

- `memory.propose_update`
- `memory.block_guardrail_weakening`
- `memory.require_approval_for_boundary_change`
- `memory.attach_change_receipt`

### `catalogs/finance_ops.json`

Pointers:

- `finance.verify_vendor_identity`
- `finance.block_bank_detail_change`
- `finance.require_dual_approval`
- `finance.require_invoice_evidence`
- `finance.block_payment_execution`

## Product UX

The integration must be easy enough for a gateway developer to adopt in an afternoon.

Target API:

```python
from agent_pidgin import preflight

decision = preflight.tool_call(
    actor="openclaw-support-agent",
    channel="slack",
    tool_name="email.send_customer",
    contract=contract,
    previous_contract=last_safe_contract,
)

if decision.blocked:
    return decision.explain()
```

Target CLI:

```bash
agent-pidgin preflight-tool examples/openclaw/email_send_contract.json --json
agent-pidgin record-memory-update examples/openclaw/memory_drift.json --json
agent-pidgin verify-skill examples/openclaw/community_skill_manifest.json --json
```

Target UI:

```text
OpenClaw action blocked

Tool: email.send_customer
Channel: Slack
Reason: external-send guardrail removed
Policy: UNPINNED_REVISION, HUMAN_REVIEW_REQUIRED
Trace: trace-...
What changed:
  - removed agent.request_human_review
  - removed agent.attach_receipts
  - memory changed external_email_allowed false -> true
```

## Monitoring UX

For OpenClaw-class systems, the dashboard should show:

- active agents
- channels connected
- skills installed
- blocked actions
- memory guardrail weakening attempts
- skills blocked before install
- unpinned artifact attempts
- external sends blocked
- shell/file actions requiring approval
- trace integrity status
- receipt count by agent

This should export to telemetry systems, but Pidgeon remains the semantic authority.

## Breakthrough Showpiece

The next strongest showpiece is:

> "The local assistant tried to install a community skill and send a customer email. Pidgeon stopped both before execution."

Flow:

1. User installs a community skill from a marketplace.
2. Skill requests file, shell, and credential access.
3. Pidgeon blocks install because publisher is unsigned and permission diff is high risk.
4. Agent later receives a support task.
5. Safe memory requires human review before external email.
6. Context drift weakens the review boundary.
7. Agent proposes sending an email.
8. Pidgeon blocks the memory update and the external send.
9. Replay UI shows both failures in one trace.

This is stronger than a generic agent demo because OpenClaw-class systems are local, popular, extensible, skill-driven, and connected to real channels.

## Next Implementation Steps

1. Add OpenClaw-class catalogs for communications, filesystem, shell, skills, memory, and finance.
2. Add example contracts under `examples/openclaw_class/`.
3. Add `record_skill_install` to `flight_recorder.py`.
4. Add deterministic skill manifest schema.
5. Add policy rules for signed publisher, dangerous permissions, external send, shell access, and credential paths.
6. Add CLI commands:
   - `preflight-tool`
   - `record-memory-update`
   - `verify-skill`
   - `render-trace`
7. Add a local HTML replay report for the OpenClaw-class demo.
8. Add OpenTelemetry export after the JSON trace stabilizes.
9. Add docs showing sidecar deployment beside an OpenClaw Gateway.
10. Add tests for malicious skill install, memory drift, external send, shell command proposal, and trace tampering.

## Boundary

Agent Pidgeon should not claim to secure OpenClaw itself or any particular OpenClaw deployment.

The accurate claim is:

> Pidgeon can provide deterministic semantic preflight, drift detection, receipts, and replay for OpenClaw-class agents before tools, skills, memory updates, and channel actions execute.
