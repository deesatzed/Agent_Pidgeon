---
description: run the opt-in live stdio integration tests for agent-pidgin
---
1. Confirm you are working from the `agent-pidgin` project root and that the project venv exists at `.venv`.

2. Verify the required runtime tools are available:
   - `.venv/bin/python --version`
   - `~/.local/bin/hf-mount status || true`

3. Run the default integration module once to confirm the live tests are skipped unless explicitly enabled:
   - `.venv/bin/python -m unittest tests.test_stdio_integration -v`
   - Expected result: `OK (skipped=2)`.

4. Run the live stdio integration tests with the public artifact target:
   - `AGENT_PIDGIN_RUN_STDIO_INTEGRATION=1 AGENT_PIDGIN_DATA_REPO=openai-community/gpt2 AGENT_PIDGIN_DATA_REVISION=main AGENT_PIDGIN_ARTIFACT_REPO=openai-community/gpt2 AGENT_PIDGIN_ARTIFACT_REVISION=main AGENT_PIDGIN_MOUNT_ROOT=/tmp/agent-pidgin .venv/bin/python -m unittest tests.test_stdio_integration -v`
   - Expected result: both tests pass.

5. Run the full default suite to confirm the opt-in coverage does not disturb the normal test path:
   - `.venv/bin/python -m unittest discover -s tests -v`
   - Expected result: `OK (skipped=2)` for the stdio integration module.

6. Clean up the live mount daemon if it is still present:
   - `~/.local/bin/hf-mount stop /tmp/agent-pidgin/gpt2 || true`
   - `~/.local/bin/hf-mount status || true`
   - Expected result: no running daemon for `/tmp/agent-pidgin/gpt2`.

7. Package the handoff using the changed files list:
   - `README.md`
   - `tests/test_stdio_integration.py`
   - `docs/plans/2026-03-25-stdio-integration-design.md`
   - `docs/plans/2026-03-25-stdio-integration-implementation.md`
   - `.windsurf/workflows/live-stdio-integration-test.md`
