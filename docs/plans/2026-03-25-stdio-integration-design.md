# Stdio Integration Test Design

## Goal

Add an automated, opt-in integration test that exercises the real FastMCP stdio sender-to-receiver round-trip while preserving the default test suite's speed and determinism.

## Problem

The project now supports the hybrid authoritative artifact target model:

- resolve payloads may include `artifact.kind`, `artifact.repo`, and `artifact.revision`
- legacy `dataset_repo` and `dataset_revision` remain supported
- the receiver resolves the effective artifact target using payload artifact, then legacy dataset fields, then config defaults

This behavior is covered by unit tests and has been verified manually with a live stdio smoke. However, the repo does not yet contain an automated test that proves the real stdio sender, FastMCP transport, receiver entrypoint, and `hf-mount` integration continue to work together end-to-end.

## Constraints

- The default unittest suite must remain reliable on machines that do not have the required runtime tools installed.
- The test should avoid brittle stdout parsing when possible.
- The test should explicitly exercise the hybrid payload shape, not just the legacy dataset aliases.
- Cleanup must leave `hf-mount` daemons stopped after the test completes.

## Options Considered

### Option 1: API-level opt-in integration test

Add a unittest module that:

- is skipped unless an environment flag enables it
- constructs a payload with both `artifact` and legacy dataset aliases
- calls `asyncio.run(run_stdio_demo(payload=...))`
- asserts handshake and resolve success
- asserts the returned artifact metadata points at the expected public repo
- stops the mount daemon in `finally`

#### Pros

- Exercises the real stdio sender/receiver path
- Avoids brittle CLI log parsing
- Fits the existing unittest structure
- Keeps the test narrowly focused on integration behavior

#### Cons

- Still depends on local FastMCP and `hf-mount` runtime availability when enabled

### Option 2: CLI-level subprocess integration test

Add a test that runs `scripts/poc_stdio_send.py` as a subprocess and parses its JSON output.

#### Pros

- Covers the CLI wrapper in addition to the transport

#### Cons

- More brittle because FastMCP startup logs may mix with output
- Adds avoidable parsing complexity

### Option 3: Manual script-only verification

Rely on a documented shell smoke test rather than a repo test.

#### Pros

- Simple operationally

#### Cons

- Provides no automated regression protection
- Easy to skip accidentally

## Approved Approach

Use **Option 1: API-level opt-in integration test**.

## Test Shape

### File

- `tests/test_stdio_integration.py`

### Gate

The test runs only when:

- `AGENT_PIDGIN_RUN_STDIO_INTEGRATION=1`

Otherwise it is skipped with a clear reason.

### Payload

The test starts from `build_demo_message()` and then overrides both representations of the artifact target:

- `artifact.repo`
- `artifact.revision`
- `dataset_repo`
- `dataset_revision`

This ensures the test exercises the hybrid authoritative payload model instead of relying only on backward-compatible aliases.

### Artifact Target

Use a public repo that works for live smoke coverage:

- `openai-community/gpt2`
- revision `main`

### Assertions

The test should verify:

- handshake status is `ready`
- resolve status is `resolved`
- returned artifact `repo_id` is `openai-community/gpt2`
- returned artifact `mount_path` ends with `/gpt2`
- returned artifact `kind` is `repo`

### Cleanup

Use `hf-mount stop /tmp/agent-pidgin/gpt2` in a `finally` block.

Cleanup should not hide the real failure if the round-trip fails first.

## Non-Goals

- No always-on live integration in the default suite
- No CLI parsing test unless a separate regression justifies it later
- No new workflow or CI wiring in this step

## Success Criteria

1. The new integration test is skipped by default.
2. When explicitly enabled, it exercises the real stdio handshake and resolve round-trip.
3. The test validates the hybrid authoritative artifact path.
4. Existing unit tests remain green.
5. `hf-mount` state is cleaned up after execution.
