# Stdio Integration Test Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an opt-in unittest that exercises the real FastMCP stdio handshake/resolve round-trip using the hybrid authoritative artifact payload model.

**Architecture:** Add a dedicated integration test module that is skipped by default unless explicitly enabled with an environment flag. The test will construct a hybrid payload, invoke `run_stdio_demo()` through the real stdio sender/receiver path, assert the returned handshake and artifact metadata, and always attempt `hf-mount` cleanup afterward.

**Tech Stack:** Python 3.13, unittest, asyncio, FastMCP, hf-mount

---

### Task 1: Add the opt-in stdio integration test

**Files:**
- Create: `tests/test_stdio_integration.py`

**Step 1: Write the test first**

Add a unittest that:

- skips unless `AGENT_PIDGIN_RUN_STDIO_INTEGRATION=1`
- builds a payload via `build_demo_message()`
- overrides:
  - `artifact.kind`
  - `artifact.repo`
  - `artifact.revision`
  - `dataset_repo`
  - `dataset_revision`
- runs `asyncio.run(run_stdio_demo(payload=payload))`
- asserts:
  - handshake status is `ready`
  - resolve status is `resolved`
  - returned artifact `repo_id` is `openai-community/gpt2`
  - returned artifact `kind` is `repo`
  - returned artifact `mount_path` ends with `/gpt2`
- cleans up `/tmp/agent-pidgin/gpt2` in `finally`

**Step 2: Run the new test in default mode**

Run:

```bash
.venv/bin/python -m unittest tests.test_stdio_integration -v
```

Expected: PASS with the test skipped because the env flag is absent.

**Step 3: Run the new test in enabled mode**

Run:

```bash
AGENT_PIDGIN_RUN_STDIO_INTEGRATION=1 \
AGENT_PIDGIN_DATA_REPO=openai-community/gpt2 \
AGENT_PIDGIN_DATA_REVISION=main \
AGENT_PIDGIN_ARTIFACT_REPO=openai-community/gpt2 \
AGENT_PIDGIN_ARTIFACT_REVISION=main \
AGENT_PIDGIN_MOUNT_ROOT=/tmp/agent-pidgin \
.venv/bin/python -m unittest tests.test_stdio_integration -v
```

Expected: PASS with a real stdio round-trip and cleanup.

### Task 2: Verify default-suite compatibility

**Files:**
- Modify: none unless verification exposes a defect

**Step 1: Run the sender-adjacent suite**

Run:

```bash
.venv/bin/python -m unittest tests.test_sender tests.test_demo tests.test_mcp_app tests.test_stdio_integration -v
```

Expected: PASS, with the integration test skipped by default.

**Step 2: Fix only if necessary**

Only make code changes if verification exposes a real gap in gating, cleanup, or payload wiring.

### Task 3: Run final verification

**Files:**
- Modify: none unless verification exposes a defect

**Step 1: Run the full suite**

Run:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Expected: PASS, with the integration test skipped unless explicitly enabled.

**Step 2: Record results**

Capture:

- default-mode skip behavior
- enabled-mode pass behavior
- final full-suite count

**Step 3: Commit**

```bash
git add tests/test_stdio_integration.py docs/plans/2026-03-25-stdio-integration-design.md docs/plans/2026-03-25-stdio-integration-implementation.md
git commit -m "test: add opt-in stdio integration coverage"
```
