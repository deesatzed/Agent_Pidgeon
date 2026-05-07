# Protocol

Pidgin messages are compact semantic contracts.

Minimal resolve message:

```json
{
  "pidgin_version": "0.1",
  "message_type": "resolve",
  "message_id": "msg-001",
  "sender_id": "agent-a",
  "receiver_id": "agent-b",
  "target_language": "python",
  "artifact": {
    "kind": "repo",
    "repo": "namespace/repo",
    "revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "steps": ["str.trim"],
  "created_at": "2026-03-25T10:30:00Z"
}
```

The response includes:

- `status`
- `artifact`
- `resolution.target_language`
- `resolution.resolved_steps`
- `resolution.receipts`
- `policy_findings`

Resolved implementation strings are not executable authority. The catalog hash and receipt fields are the audit trail.

## Flight Recorder Trace

AAFR traces use `schemas/pidgin-trace.schema.json`.

Each trace contains:

- `trace_id`
- `status`
- `events`
- `summary`
- `trace_hash`

Each event includes:

- event and parent IDs
- event type
- actor
- decision
- payload hash
- optional contract and contract hash
- optional policy findings
- optional semantic diff
- optional receipt IDs
- `previous_event_hash`
- `event_hash`

Trace hashes are tamper-evident after generation. They are not a substitute for an external append-only audit store.
