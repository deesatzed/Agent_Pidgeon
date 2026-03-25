# HF Layout Wiring Design

## Goal

Align the pidgin resolve flow with the future Hugging Face artifact model without breaking existing payloads, demos, or tests.

## Problem

The project already exposes future-facing config fields:

- `artifact_kind`
- `artifact_repo`
- `artifact_revision`
- `mount_root`

But the runtime resolve path still treats legacy payload fields as authoritative:

- `dataset_repo`
- `dataset_revision`

That means the future artifact model is only partially wired. The handshake advertises artifact defaults, but the resolver still mounts from the legacy dataset fields.

## Approved Approach

Use a hybrid authoritative artifact-target model.

### Rules

1. Resolve payloads may include an optional `artifact` object.
2. The `artifact` object is the preferred future-facing source of truth.
3. Legacy `dataset_repo` and `dataset_revision` remain supported for backward compatibility.
4. If neither payload source is provided, config defaults are used.

## Effective Artifact Precedence

The receiver computes the effective artifact target using this order:

1. `payload.artifact.repo` and `payload.artifact.revision`
2. legacy `payload.dataset_repo` and `payload.dataset_revision`
3. config defaults `artifact_repo` and `artifact_revision`

`artifact_kind` comes from `payload.artifact.kind` when present, otherwise config defaults.

## Protocol Shape

### Legacy-compatible resolve payload

Existing payloads remain valid:

```json
{
  "message_type": "resolve",
  "message_id": "msg-123",
  "sender_id": "agent-a",
  "receiver_id": "agent-b",
  "target_language": "python",
  "dataset_repo": "waynesatz/agent-pidgin-data",
  "dataset_revision": "main",
  "steps": ["str.trim"],
  "created_at": "2026-03-25T00:00:00Z"
}
```

### Future-facing resolve payload

New payloads may include:

```json
{
  "message_type": "resolve",
  "message_id": "msg-123",
  "sender_id": "agent-a",
  "receiver_id": "agent-b",
  "target_language": "python",
  "artifact": {
    "kind": "repo",
    "repo": "waynesatz/agent-pidgin-data",
    "revision": "main"
  },
  "steps": ["str.trim"],
  "created_at": "2026-03-25T00:00:00Z"
}
```

For compatibility during transition, demo payloads may emit both the `artifact` object and the legacy dataset aliases.

## Runtime Behavior

### Receiver

- Parse the optional `artifact` object.
- Derive the effective artifact target using the precedence rules.
- Mount the effective repo and revision.
- Return artifact metadata based on the effective mounted target.

### Handshake

- Continue returning `artifact_defaults`.
- These defaults represent the receiver’s fallback target when the payload does not specify one.

### Demo and Sender

- Demo payload builders should emit the future-facing `artifact` object.
- Backward-compatible `dataset_*` fields may remain during the transition.
- Sender behavior does not need protocol changes beyond passing the richer payload through.

## Testing

Add tests for:

1. protocol parsing of optional `artifact`
2. legacy payload compatibility
3. service precedence behavior:
   - artifact payload overrides dataset payload
   - dataset payload overrides config defaults
   - config defaults are used when neither payload source is present
4. demo payload shape including the new `artifact` object

## Non-Goals

- No hard cutover away from `dataset_*` yet.
- No multi-artifact bundle model yet.
- No repo-internal directory semantics yet.
