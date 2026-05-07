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


if __name__ == "__main__":
    unittest.main()
