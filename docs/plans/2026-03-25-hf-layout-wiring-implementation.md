# HF Layout Wiring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the future-facing Hugging Face artifact model authoritative for resolve requests while preserving backward compatibility with legacy `dataset_*` payload fields.

**Architecture:** Introduce an optional `artifact` object on resolve payloads, teach the protocol and receiver service to compute an effective artifact target using precedence rules, and keep legacy dataset aliases working during the transition. Update demo payload generation and tests so the new artifact shape is exercised without breaking current behavior.

**Tech Stack:** Python 3.13, unittest, FastMCP, dataclasses

---

### Task 1: Add protocol coverage for the optional artifact payload

**Files:**
- Modify: `tests/test_protocol.py`
- Modify: `src/agent_pidgin/protocol.py`

**Step 1: Write the failing test**

Add a test that passes a resolve payload containing:

```python
{
    "message_type": "resolve",
    "message_id": "msg-123",
    "sender_id": "agent-a",
    "receiver_id": "agent-b",
    "target_language": "python",
    "artifact": {
        "kind": "repo",
        "repo": "openai-community/gpt2",
        "revision": "main",
    },
    "steps": ["str.trim"],
    "created_at": "2026-03-25T00:00:00Z",
}
```

Assert that parsing succeeds and exposes the artifact fields.

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_protocol -v
```

Expected: FAIL because `PidginMessage` does not yet parse or expose the optional artifact structure.

**Step 3: Write minimal implementation**

In `src/agent_pidgin/protocol.py`, add a small artifact dataclass or equivalent typed structure and make `PidginMessage.from_dict()` parse the optional `artifact` object without breaking legacy payloads.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m unittest tests.test_protocol -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_protocol.py src/agent_pidgin/protocol.py
git commit -m "feat: parse future artifact payloads"
```

### Task 2: Add precedence tests for effective artifact resolution

**Files:**
- Modify: `tests/test_service.py`
- Modify: `src/agent_pidgin/service.py`
- Modify: `src/agent_pidgin/config.py` (only if helper logic belongs there)

**Step 1: Write the failing tests**

Add tests covering three cases:

```python
# artifact payload overrides dataset payload
payload = {
    ...,
    "artifact": {"kind": "repo", "repo": "openai-community/gpt2", "revision": "main"},
    "dataset_repo": "waynesatz/agent-pidgin-data",
    "dataset_revision": "main",
}
```

```python
# dataset payload used when artifact payload absent
payload = {
    ...,
    "dataset_repo": "waynesatz/agent-pidgin-data",
    "dataset_revision": "main",
}
```

```python
# config defaults used when neither artifact nor dataset payload is present
payload = {
    ...,
    "steps": ["str.trim"],
}
```

Assert that `ensure_repo_mounted()` receives the expected repo and revision in each case.

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_service -v
```

Expected: FAIL because `resolve_message()` currently mounts only `dataset_repo` and `dataset_revision`.

**Step 3: Write minimal implementation**

In `src/agent_pidgin/service.py`, add a helper that derives the effective artifact target using precedence:

1. payload `artifact`
2. legacy `dataset_*`
3. config `artifact_*`

Use the effective target for mount path derivation and mount execution.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m unittest tests.test_service -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_service.py src/agent_pidgin/service.py src/agent_pidgin/config.py
git commit -m "feat: resolve effective artifact targets"
```

### Task 3: Update demo payloads to emit the future-facing artifact object

**Files:**
- Modify: `tests/test_demo.py`
- Modify: `src/agent_pidgin/demo.py`

**Step 1: Write the failing test**

Add a test asserting `build_demo_message()` includes:

```python
"artifact": {
    "kind": "repo",
    "repo": expected_repo,
    "revision": expected_revision,
}
```

and still includes legacy `dataset_repo` / `dataset_revision` aliases for compatibility.

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_demo -v
```

Expected: FAIL because demo payloads currently only emit legacy dataset fields.

**Step 3: Write minimal implementation**

Update `build_demo_message()` so it includes the new `artifact` object based on `PidginConfig` while preserving the legacy aliases.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m unittest tests.test_demo -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_demo.py src/agent_pidgin/demo.py
git commit -m "feat: emit future artifact payloads in demos"
```

### Task 4: Verify compatibility across sender and MCP app surfaces

**Files:**
- Modify: `tests/test_sender.py` (only if needed)
- Modify: `tests/test_mcp_app.py` (only if needed)
- Modify: `README.md`
- Modify: `.env.example`

**Step 1: Write any missing failing compatibility tests**

If current tests do not prove compatibility well enough, add assertions that sender and handshake flows continue to work with the richer payload shape.

**Step 2: Run targeted tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_mcp_app tests.test_sender tests.test_demo -v
```

Expected: PASS, or FAIL only where compatibility assumptions need tightening.

**Step 3: Write minimal implementation or doc updates**

Only add code if a compatibility test exposes a real gap. Otherwise update docs to reflect the new hybrid payload model and precedence rules.

**Step 4: Run targeted tests to verify they pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_mcp_app tests.test_sender tests.test_demo -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_sender.py tests/test_mcp_app.py tests/test_demo.py README.md .env.example
git commit -m "docs: describe hybrid artifact payload compatibility"
```

### Task 5: Full verification

**Files:**
- Modify: none unless verification exposes a real defect
- Test: `tests/`

**Step 1: Run the full suite**

Run:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Expected: PASS with all tests green.

**Step 2: Run the stdio demo smoke**

Run:

```bash
AGENT_PIDGIN_DATA_REPO=openai-community/gpt2 \
AGENT_PIDGIN_DATA_REVISION=main \
AGENT_PIDGIN_ARTIFACT_REPO=openai-community/gpt2 \
AGENT_PIDGIN_ARTIFACT_REVISION=main \
AGENT_PIDGIN_MOUNT_ROOT=/tmp/agent-pidgin \
.venv/bin/python scripts/poc_stdio_send.py
```

Expected: handshake succeeds, resolve succeeds, and output shows the effective artifact metadata.

**Step 3: Clean up any running daemon**

Run:

```bash
~/.local/bin/hf-mount stop /tmp/agent-pidgin/gpt2 || true
```

Expected: mount daemon is stopped or already absent.

**Step 4: Record verification results**

Document the final test count and the stdio smoke outcome in your handoff.

**Step 5: Commit**

```bash
git add .
git commit -m "feat: wire hybrid HF artifact targeting"
```
