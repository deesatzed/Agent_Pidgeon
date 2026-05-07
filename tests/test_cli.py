import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.cli import run
from agent_pidgin.flight_recorder import FlightRecorder


def write_json(directory: str, name: str, payload: dict) -> str:
    path = Path(directory) / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def valid_message(revision: str = "a" * 40) -> dict:
    return {
        "pidgin_version": "0.1",
        "message_type": "resolve",
        "message_id": "msg-cli-001",
        "sender_id": "agent-a",
        "receiver_id": "agent-b",
        "target_language": "python",
        "artifact": {
            "kind": "repo",
            "repo": "waynesatz/agent-pidgin-data",
            "revision": revision,
        },
        "steps": ["str.trim"],
        "created_at": "2026-03-25T10:30:00Z",
    }


class CliTests(unittest.TestCase):
    def invoke(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = run(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_validate_message_returns_zero_for_valid_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_json(tmpdir, "message.json", valid_message())

            code, stdout, stderr = self.invoke(["validate-message", path, "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["status"], "valid")

    def test_list_catalog_returns_pointer_metadata(self) -> None:
        code, stdout, stderr = self.invoke(["list-catalog", "--language", "python", "--json"])

        result = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(result["status"], "catalog_loaded")
        self.assertEqual(result["language_filter"], "python")
        self.assertIn("str.trim", result["pointers"])

    def test_show_pointer_returns_hashes_not_implementation_strings(self) -> None:
        code, stdout, stderr = self.invoke(["show-pointer", "str.trim", "--json"])

        result = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(result["status"], "pointer_found")
        self.assertEqual(result["concept"]["pointer"], "str.trim")
        self.assertNotIn("implementations", result["concept"])

    def test_list_catalog_accepts_explicit_catalog_path(self) -> None:
        code, stdout, stderr = self.invoke(["list-catalog", "--catalog", "catalogs/core.json", "--json"])

        result = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(result["concept_count"], 9)
        self.assertNotIn("clinical.phi.scrub", result["pointers"])

    def test_policy_check_returns_nonzero_for_unpinned_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_json(tmpdir, "message.json", valid_message(revision="main"))

            code, stdout, stderr = self.invoke(["policy-check", path, "--json"])

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["status"], "policy_failed")

    def test_resolve_returns_receipts_for_pinned_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_json(tmpdir, "message.json", valid_message())

            code, stdout, stderr = self.invoke(["resolve", path, "--json"])

        result = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["resolution"]["receipts"][0]["artifact_revision"], "a" * 40)

    def test_diff_command_flags_removed_safety_pointer(self) -> None:
        payload = {
            "left_steps": ["str.trim", "clinical.phi.scrub"],
            "right_steps": ["str.trim"],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_json(tmpdir, "diff.json", payload)

            code, stdout, stderr = self.invoke(["diff", path, "--json"])

        result = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(result["diff"]["removed"], ["clinical.phi.scrub"])

    def test_author_contract_requires_openrouter_key(self) -> None:
        original = dict(os.environ)
        try:
            os.environ.pop("OPENROUTER_API_KEY", None)
            with tempfile.TemporaryDirectory() as tmpdir:
                request_path = Path(tmpdir) / "request.txt"
                request_path.write_text("Trim text and attach receipts.", encoding="utf-8")

                code, stdout, stderr = self.invoke(
                    [
                        "author-contract",
                        str(request_path),
                        "--artifact-repo",
                        "waynesatz/agent-pidgin-data",
                        "--artifact-revision",
                        "a" * 40,
                        "--json",
                    ]
                )

            self.assertEqual(code, 1)
            self.assertEqual(stdout, "")
            self.assertIn("OPENROUTER_API_KEY", stderr)
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_preflight_tool_blocks_high_risk_drift(self) -> None:
        safe = valid_message()
        safe["steps"] = ["str.trim", "clinical.phi.scrub", "agent.request_human_review"]
        proposed = dict(safe)
        proposed["message_id"] = "msg-cli-proposed"
        proposed["steps"] = ["str.trim"]
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_path = write_json(tmpdir, "safe.json", safe)
            proposed_path = write_json(tmpdir, "proposed.json", proposed)

            code, stdout, stderr = self.invoke(
                [
                    "preflight-tool",
                    proposed_path,
                    "--previous-contract",
                    safe_path,
                    "--tool-name",
                    "email.send_customer",
                    "--json",
                ]
            )

        result = json.loads(stdout)
        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["event"]["semantic_diff"]["risk_level"], "high")

    def test_record_memory_update_blocks_guardrail_weakening(self) -> None:
        payload = {
            "before": {
                "external_email_allowed": False,
                "human_review_required": True,
            },
            "after": {
                "external_email_allowed": True,
                "human_review_required": False,
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_json(tmpdir, "memory.json", payload)

            code, stdout, stderr = self.invoke(["record-memory-update", path, "--json"])

        result = json.loads(stdout)
        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["event"]["semantic_diff"]["risk_level"], "high")

    def test_verify_skill_blocks_unsigned_dangerous_manifest(self) -> None:
        manifest = {
            "skill_id": "community/dangerous-mailer",
            "name": "Dangerous Mailer",
            "version": "0.1.0",
            "publisher": {"id": "community", "name": "Community"},
            "signed": False,
            "permissions": [
                {"kind": "shell", "target": "*", "access": "execute"},
                {"kind": "credential", "target": "~/.aws/credentials", "access": "read"},
            ],
            "capabilities": ["email.send_customer"],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_json(tmpdir, "skill.json", manifest)

            code, stdout, stderr = self.invoke(["verify-skill", path, "--json"])

        result = json.loads(stdout)
        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(result["status"], "blocked")
        self.assertIn("DANGEROUS_SHELL_PERMISSION", {finding["code"] for finding in result["findings"]})

    def test_render_trace_prints_flight_recorder_report(self) -> None:
        recorder = FlightRecorder(trace_id="trace-cli-render")
        recorder.record_event("agent.goal.received", "agent-a", "Receive goal.", {"goal": "test"})
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_json(tmpdir, "trace.json", recorder.trace())

            code, stdout, stderr = self.invoke(["render-trace", path])

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Agent Pidgeon Flight Recorder", stdout)

    def test_render_trace_can_write_html_report(self) -> None:
        recorder = FlightRecorder(trace_id="trace-cli-html")
        recorder.record_event("agent.goal.received", "agent-a", "Receive goal.", {"goal": "test"})
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = write_json(tmpdir, "trace.json", recorder.trace())
            html_path = str(Path(tmpdir) / "trace.html")

            code, stdout, stderr = self.invoke(["render-trace", trace_path, "--html-out", html_path, "--json"])

            html_content = Path(html_path).read_text(encoding="utf-8")

        result = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(result["status"], "rendered")
        self.assertIn("Agent Pidgeon Trace Replay", html_content)


if __name__ == "__main__":
    unittest.main()
