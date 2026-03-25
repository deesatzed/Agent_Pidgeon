# Agent Pidgin Hybrid Protocol Upgrade Design

## Objective

Extend the existing HF_MOUNT + MCP-style A2A PoC with a real stdio sender-to-receiver path, a minimal handshake/capability exchange, and a cleaner future-facing Hugging Face artifact configuration model while preserving the current resolve flow.

## Scope

This design adds three capabilities:

1. A sender-side stdio MCP client that can talk to the existing receiver process.
2. A minimal pidgin protocol discriminator for `handshake` and `resolve` message flows.
3. A future-facing artifact configuration model that preserves compatibility with the current `dataset_repo` and `dataset_revision` fields.

## Non-Goals

- No session persistence beyond one stdio client interaction.
- No workflow orchestration or multi-step negotiation state machine.
- No removal of the existing resolve payload shape.
- No hard dependency on a private HF repo existing yet.

## Design Options Considered

### 1. Minimal MCP-native

Use the MCP tool layer directly without changing the protocol envelope.

- Pros: smallest change, lowest risk.
- Cons: handshake remains outside the pidgin protocol and future protocol evolution stays awkward.

### 2. Hybrid Protocol Upgrade

Add a minimal envelope discriminator, keep MCP tools as the transport surface, and preserve backward compatibility.

- Pros: best balance of realism, compatibility, and implementation scope.
- Cons: adds a small amount of protocol branching.

### 3. Richer Negotiation Model

Add explicit negotiation/session primitives and richer artifact descriptors now.

- Pros: most future-extensible.
- Cons: overbuilt for the current PoC.

## Chosen Approach

Implement the Hybrid Protocol Upgrade.

## Architecture

### Protocol Layer

Introduce a minimal envelope family:

- `message_type="resolve"` for the current resolution request flow.
- `message_type="handshake"` for capability and artifact-default discovery.

Backward compatibility rule:

- If `message_type` is missing, treat the payload as a legacy resolve request.

### Artifact Configuration Layer

Retain the current fields:

- `dataset_repo`
- `dataset_revision`

Add a future-facing artifact descriptor returned by configuration and handshake responses:

- `artifact_kind` (initially `repo`)
- `artifact_repo`
- `artifact_revision`
- `mount_root`

Compatibility rule:

- resolve requests continue to accept `dataset_repo` and `dataset_revision`
- receiver capability responses expose both legacy and future-facing fields where useful

### Receiver Layer

Keep the current `PidginReceiverService` as the authoritative resolve path.

Add a small handshake path that returns:

- receiver identity
- supported message types
- supported languages
- supported pointers
- artifact defaults
- transport hint (`stdio`)

The MCP app will expose:

- `describe_capabilities()` for compatibility
- `handshake_pidgin_session(payload)` for protocol-native handshake
- `resolve_pidgin_message(payload)` for resolution

### Sender Layer

Add a sender-side client module that uses `fastmcp.Client` over stdio to launch/connect to `servers/pidgin_receiver.py`.

Sender responsibilities:

1. start stdio MCP client
2. perform handshake tool call
3. send resolve payload
4. return a structured round-trip record including handshake and resolution results

### CLI Layer

Add a dedicated CLI/script entry point for stdio end-to-end smoke runs.

Expected flow:

1. build demo resolve payload
2. handshake over stdio
3. resolve over stdio
4. print combined result as JSON

## Data Flow

### Handshake

Sender -> stdio MCP client -> `handshake_pidgin_session(payload)` -> receiver capability response

### Resolve

Sender -> stdio MCP client -> `resolve_pidgin_message(payload)` -> receiver service -> hf-mount gateway -> resolver -> structured resolution response

## Error Handling

- Invalid handshake payloads raise `ValueError` with explicit missing/invalid fields.
- Invalid resolve payloads continue using existing validation behavior.
- stdio client startup errors surface as sender runtime errors.
- receiver capability mismatch is reported in the sender result before attempting resolve when possible.

## Testing Strategy

Add or update tests for:

1. protocol parsing for handshake and legacy resolve compatibility
2. MCP handshake response shape
3. stdio sender client orchestration using an injectable MCP client factory
4. future-facing config defaults and overrides
5. end-to-end stdio smoke using the local Python 3.13 venv

## Rollout Plan

1. Extend protocol/config models.
2. Add receiver handshake support.
3. Add sender stdio client and CLI/demo flow.
4. Verify with unit tests and local stdio smoke.
5. Preserve existing local demo and real-mount demo behavior.
