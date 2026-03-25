from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.demo import build_demo_message, run_local_demo, run_real_demo


class DemoTests(unittest.TestCase):
    def test_build_demo_message_targets_future_hf_repo(self) -> None:
        message = build_demo_message()

        self.assertEqual(message["dataset_repo"], "waynesatz/agent-pidgin-data")
        self.assertEqual(message["artifact"]["kind"], "repo")
        self.assertEqual(message["artifact"]["repo"], "waynesatz/agent-pidgin-data")
        self.assertEqual(message["artifact"]["revision"], "main")
        self.assertEqual(message["target_language"], "python")
        self.assertEqual(message["steps"], ["str.trim", "str.lowercase", "str.ascii_only"])

    def test_run_local_demo_returns_resolved_status(self) -> None:
        result = run_local_demo()

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["artifact"]["repo_id"], "waynesatz/agent-pidgin-data")
        self.assertEqual(result["resolution"]["resolved_steps"][0]["pointer"], "str.trim")

    def test_run_local_demo_preserves_explicit_message_id(self) -> None:
        payload = build_demo_message()
        payload["message_id"] = "msg-preserved"

        result = run_local_demo(payload=payload)

        self.assertEqual(result["message_id"], "msg-preserved")

    def test_run_real_demo_uses_supplied_mount_gateway_and_repo_override(self) -> None:
        class RecordingGateway:
            def __init__(self) -> None:
                self.calls = []

            def ensure_repo_mounted(self, repo_id: str, mount_path: str, revision: str, hf_token: str | None = None) -> dict:
                self.calls.append(
                    {
                        "repo_id": repo_id,
                        "mount_path": mount_path,
                        "revision": revision,
                        "hf_token": hf_token,
                    }
                )
                return {
                    "repo_id": repo_id,
                    "mount_path": mount_path,
                    "revision": revision,
                    "status": "mounted",
                }

        gateway = RecordingGateway()

        result = run_real_demo(
            mount_gateway=gateway,
            repo_id="openai-community/gpt2",
            revision="main",
        )

        self.assertEqual(result["artifact"]["repo_id"], "openai-community/gpt2")
        self.assertEqual(gateway.calls[0]["repo_id"], "openai-community/gpt2")
        self.assertEqual(result["status"], "resolved")


if __name__ == "__main__":
    unittest.main()
