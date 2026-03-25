# agent-pidgin

A small proof of concept for A2A pidgin communication using `hf-mount` and an MCP-style receiver.

## What this PoC proves

- A structured pidgin message contract
- A receiver service that mounts a pinned HF artifact and resolves a tiny concept set locally
- A local round-trip demo aligned to the future repos:
  - `waynesatz/agent-pidgin-data`
  - `waynesatz/pidgin-resolver`

## Seed pointers

- `str.trim`
- `str.lowercase`
- `str.ascii_only`

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

## Run opt-in stdio integration tests

These tests use the real FastMCP stdio path and `hf-mount`, so they are skipped by default unless explicitly enabled.

```bash
AGENT_PIDGIN_RUN_STDIO_INTEGRATION=1 \
AGENT_PIDGIN_DATA_REPO=openai-community/gpt2 \
AGENT_PIDGIN_DATA_REVISION=main \
AGENT_PIDGIN_ARTIFACT_REPO=openai-community/gpt2 \
AGENT_PIDGIN_ARTIFACT_REVISION=main \
AGENT_PIDGIN_MOUNT_ROOT=/tmp/agent-pidgin \
.venv/bin/python -m unittest tests.test_stdio_integration -v
```

The live integration coverage verifies both:

- a real stdio handshake plus resolve round-trip
- payload `artifact` precedence over conflicting legacy `dataset_*` fields

## Run local demo

```bash
PYTHONPATH=src python3 -m agent_pidgin.cli
```

## Run stdio A2A demo

This launches the MCP receiver over stdio, performs a pidgin handshake, then sends a resolve message through the real MCP client path.

```bash
PYTHONPATH=src python3 scripts/poc_stdio_send.py
```

## Run real mount demo

Copy `.env.example` to your local environment setup, then run:

```bash
PYTHONPATH=src python3 scripts/poc_real_mount.py
```

You can override the target artifact with environment variables such as:

```bash
export AGENT_PIDGIN_DATA_REPO=openai-community/gpt2
export AGENT_PIDGIN_DATA_REVISION=main
export AGENT_PIDGIN_ARTIFACT_REPO=openai-community/gpt2
export AGENT_PIDGIN_ARTIFACT_REVISION=main
```

## Start MCP-style receiver

This requires `fastmcp` to be installed in your project environment.

```bash
PYTHONPATH=src python3 -m agent_pidgin.receiver_cli
```

## Hybrid protocol notes

- `message_type=handshake` requests receiver capabilities and artifact defaults
- `message_type=resolve` requests pointer resolution
- resolve payloads may include an `artifact` object with `kind`, `repo`, and `revision`
- effective artifact precedence is: payload `artifact` -> legacy `dataset_repo` / `dataset_revision` -> receiver config defaults
- legacy resolve payloads without `message_type` still work and default to `resolve`
