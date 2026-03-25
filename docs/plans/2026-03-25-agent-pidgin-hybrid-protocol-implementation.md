# Agent Pidgin Hybrid Protocol Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a real stdio sender-to-receiver MCP path, a minimal pidgin handshake envelope, and future-facing HF artifact defaults while preserving legacy resolve compatibility.

**Architecture:** Extend the existing protocol with a minimal `message_type` discriminator and handshake payload, keep `PidginReceiverService` as the resolve authority, and add a sender-side stdio MCP client that talks to `servers/pidgin_receiver.py` through `fastmcp`. Preserve the current local demo and resolve payload shape, while expanding config/capability responses with artifact defaults for future HF repos.

**Tech Stack:** Python 3.13, unittest, FastMCP 3.x stdio client/server, hf-mount, editable project venv

---

### Task 1: Extend protocol models for handshake + legacy compatibility

**Files:**
- Modify: `agent-pidgin/src/agent_pidgin/protocol.py`
- Modify: `agent-pidgin/tests/test_protocol.py`

**Step 1: Write the failing test**

```python
def test_handshake_message_from_dict_parses_required_fields(self) -> None:
    payload = {
        "message_type": "handshake",
        "message_id": "msg-hs-001",
        "sender_id": "agent-a",
        "receiver_id": "agent-b",
        "created_at": "2026-03-25T12:30:00Z",
    }
    message = PidginHandshake.from_dict(payload)
    self.assertEqual(message.message_type, "handshake")
```

```python
def test_pidgin_message_defaults_legacy_payload_to_resolve(self) -> None:
    payload = {
        "message_id": "msg-001",
        "sender_id": "agent-a",
        "receiver_id": "agent-b",
        "target_language": "python",
        "dataset_repo": "waynesatz/agent-pidgin-data",
        "dataset_revision": "main",
        "steps": ["str.trim"],
        "created_at": "2026-03-25T12:30:00Z",
    }
    message = PidginMessage.from_dict(payload)
    self.assertEqual(message.message_type, "resolve")
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_protocol -v`
Expected: FAIL because handshake model and `message_type` support do not exist yet.

**Step 3: Write minimal implementation**

Add:

```python
@dataclass(frozen=True)
class PidginHandshake:
    message_type: str
    message_id: str
    sender_id: str
    receiver_id: str
    created_at: str
```

Update `PidginMessage`:

```python
message_type: str = "resolve"
```

Add parsing rules:
- handshake payload validates handshake-required fields only
- resolve payload defaults missing `message_type` to `resolve`
- reject unsupported message types

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_protocol -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agent-pidgin/src/agent_pidgin/protocol.py agent-pidgin/tests/test_protocol.py
git commit -m "feat: add pidgin handshake protocol"
```

### Task 2: Expand config for future HF artifact defaults

**Files:**
- Modify: `agent-pidgin/src/agent_pidgin/config.py`
- Modify: `agent-pidgin/tests/test_config.py`

**Step 1: Write the failing test**

```python
def test_from_env_exposes_future_artifact_defaults(self) -> None:
    config = PidginConfig.from_env()
    self.assertEqual(config.artifact_kind, "repo")
    self.assertEqual(config.artifact_repo, config.dataset_repo)
```
```

```python
def test_from_env_respects_mount_root_override(self) -> None:
    os.environ["AGENT_PIDGIN_MOUNT_ROOT"] = "/tmp/agent-pidgin-future"
    config = PidginConfig.from_env()
    self.assertEqual(config.mount_root, "/tmp/agent-pidgin-future")
```
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_config -v`
Expected: FAIL because the fields do not exist yet.

**Step 3: Write minimal implementation**

Extend `PidginConfig` with:

```python
artifact_kind: str
artifact_repo: str
artifact_revision: str
mount_root: str
receiver_script: Path
```

Env mapping:
- `AGENT_PIDGIN_ARTIFACT_KIND` default `repo`
- `AGENT_PIDGIN_ARTIFACT_REPO` fallback to `AGENT_PIDGIN_DATA_REPO`
- `AGENT_PIDGIN_ARTIFACT_REVISION` fallback to `AGENT_PIDGIN_DATA_REVISION`
- `AGENT_PIDGIN_MOUNT_ROOT` default `/tmp/agent-pidgin`
- `AGENT_PIDGIN_RECEIVER_SCRIPT` default `servers/pidgin_receiver.py`

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_config -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agent-pidgin/src/agent_pidgin/config.py agent-pidgin/tests/test_config.py
git commit -m "feat: add future hf artifact config defaults"
```

### Task 3: Add receiver handshake support and capability payload

**Files:**
- Modify: `agent-pidgin/src/agent_pidgin/service.py`
- Modify: `agent-pidgin/src/agent_pidgin/mcp_app.py`
- Modify: `agent-pidgin/tests/test_service.py`
- Create: `agent-pidgin/tests/test_mcp_app.py`

**Step 1: Write the failing test**

```python
def test_receiver_service_returns_handshake_capabilities(self) -> None:
    service = PidginReceiverService(...)
    result = service.handshake({...})
    self.assertEqual(result["status"], "ready")
    self.assertIn("resolve", result["capabilities"]["supported_message_types"])
```
```

```python
def test_describe_capabilities_includes_future_artifact_defaults(self) -> None:
    capabilities = describe_capabilities()
    self.assertEqual(capabilities["artifact_defaults"]["artifact_kind"], "repo")
```
```

```python
def test_handshake_pidgin_session_returns_ready_status(self) -> None:
    result = handshake_pidgin_session({...})
    self.assertEqual(result["status"], "ready")
```
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_service tests.test_mcp_app -v`
Expected: FAIL because handshake support and richer capability payloads do not exist.

**Step 3: Write minimal implementation**

Add to `PidginReceiverService`:

```python
def handshake(self, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": ...,
        "status": "ready",
        "capabilities": {
            "receiver_id": ...,
            "supported_message_types": ["handshake", "resolve"],
            ...
        },
    }
```

Update MCP app with:
- richer `describe_capabilities()`
- new `handshake_pidgin_session(payload)` tool

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_service tests.test_mcp_app -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agent-pidgin/src/agent_pidgin/service.py agent-pidgin/src/agent_pidgin/mcp_app.py agent-pidgin/tests/test_service.py agent-pidgin/tests/test_mcp_app.py
git commit -m "feat: add pidgin handshake capabilities"
```

### Task 4: Add stdio sender client and end-to-end demo flow

**Files:**
- Create: `agent-pidgin/src/agent_pidgin/sender.py`
- Modify: `agent-pidgin/src/agent_pidgin/demo.py`
- Modify: `agent-pidgin/src/agent_pidgin/__init__.py`
- Create: `agent-pidgin/tests/test_sender.py`
- Create: `agent-pidgin/scripts/poc_stdio_send.py`

**Step 1: Write the failing test**

```python
def test_stdio_sender_performs_handshake_then_resolve(self) -> None:
    sender = PidginStdioSender(client_factory=fake_factory)
    result = asyncio.run(sender.send_round_trip(payload))
    self.assertEqual(fake_client.calls[0][0], "handshake_pidgin_session")
    self.assertEqual(fake_client.calls[1][0], "resolve_pidgin_message")
```
```

```python
def test_run_stdio_demo_returns_handshake_and_result(self) -> None:
    result = asyncio.run(run_stdio_demo(payload=payload, sender=fake_sender))
    self.assertIn("handshake", result)
    self.assertIn("result", result)
```
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_sender -v`
Expected: FAIL because sender/client modules do not exist yet.

**Step 3: Write minimal implementation**

Create a stdio sender client using `fastmcp.Client` and `PythonStdioTransport` or `Client(Path(...))` with:

```python
async def send_round_trip(self, payload: dict[str, Any]) -> dict[str, Any]:
    async with client:
        handshake = await client.call_tool("handshake_pidgin_session", {...})
        result = await client.call_tool("resolve_pidgin_message", {"payload": payload})
        return {"handshake": handshake, "result": result}
```

Add a demo helper and a CLI script printing JSON.

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_sender -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agent-pidgin/src/agent_pidgin/sender.py agent-pidgin/src/agent_pidgin/demo.py agent-pidgin/src/agent_pidgin/__init__.py agent-pidgin/tests/test_sender.py agent-pidgin/scripts/poc_stdio_send.py
git commit -m "feat: add stdio pidgin sender flow"
```

### Task 5: Verify live stdio flow and update docs

**Files:**
- Modify: `agent-pidgin/README.md`
- Modify: `agent-pidgin/.env.example`

**Step 1: Write the failing doc/test expectation**

Add README usage coverage for:
- local demo
- stdio sender demo
- real mount demo
- env overrides for future HF repos

**Step 2: Run verification commands**

Run:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/poc_stdio_send.py
.venv/bin/python -m agent_pidgin.cli
~/.local/bin/hf-mount status
```

Expected:
- all tests PASS
- stdio sender prints handshake + resolve JSON
- local demo still works
- no running daemons remain

**Step 3: Write minimal implementation**

Update docs and env template to include:
- `AGENT_PIDGIN_ARTIFACT_KIND`
- `AGENT_PIDGIN_ARTIFACT_REPO`
- `AGENT_PIDGIN_ARTIFACT_REVISION`
- `AGENT_PIDGIN_MOUNT_ROOT`
- stdio sender usage

**Step 4: Run verification again**

Run the same commands and confirm clean output.

**Step 5: Commit**

```bash
git add agent-pidgin/README.md agent-pidgin/.env.example
git commit -m "docs: document hybrid stdio pidgin flow"
```
