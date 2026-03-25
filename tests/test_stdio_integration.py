from pathlib import Path
import asyncio
import os
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.demo import build_demo_message, run_stdio_demo


class StdioIntegrationTests(unittest.TestCase):
    def _cleanup_mount(self, binary_path: Path, mount_path: str) -> None:
        try:
            subprocess.run(
                [str(binary_path), "stop", str(Path(mount_path).resolve())],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception:
            return

    def test_run_stdio_demo_performs_real_round_trip_when_enabled(self) -> None:
        if os.environ.get("AGENT_PIDGIN_RUN_STDIO_INTEGRATION") != "1":
            self.skipTest("Set AGENT_PIDGIN_RUN_STDIO_INTEGRATION=1 to run the real stdio integration test")

        repo_id = "openai-community/gpt2"
        revision = "main"
        mount_root = os.environ.get("AGENT_PIDGIN_MOUNT_ROOT", "/tmp/agent-pidgin")
        mount_path = str(Path(mount_root) / "gpt2")
        binary_path = Path(os.environ.get("HF_MOUNT_BINARY", str(Path.home() / ".local/bin/hf-mount")))
        if not binary_path.exists():
            self.skipTest(f"hf-mount binary not found at {binary_path}")

        payload = build_demo_message()
        payload["artifact"] = {
            "kind": "repo",
            "repo": repo_id,
            "revision": revision,
        }
        payload["dataset_repo"] = repo_id
        payload["dataset_revision"] = revision

        self._cleanup_mount(binary_path, mount_path)
        try:
            result = asyncio.run(run_stdio_demo(payload=payload))
        finally:
            self._cleanup_mount(binary_path, mount_path)

        self.assertEqual(result["handshake"]["status"], "ready")
        self.assertEqual(result["result"]["status"], "resolved")
        self.assertEqual(result["result"]["artifact"]["repo_id"], repo_id)
        self.assertEqual(result["result"]["artifact"]["kind"], "repo")
        self.assertTrue(result["result"]["artifact"]["mount_path"].endswith("/gpt2"))
        self.assertIn(result["result"]["artifact"]["status"], {"mounted", "already-mounted"})

    def test_run_stdio_demo_prefers_artifact_over_conflicting_legacy_dataset_fields(self) -> None:
        if os.environ.get("AGENT_PIDGIN_RUN_STDIO_INTEGRATION") != "1":
            self.skipTest("Set AGENT_PIDGIN_RUN_STDIO_INTEGRATION=1 to run the real stdio integration test")

        artifact_repo_id = "openai-community/gpt2"
        legacy_repo_id = "waynesatz/agent-pidgin-data"
        revision = "main"
        mount_root = os.environ.get("AGENT_PIDGIN_MOUNT_ROOT", "/tmp/agent-pidgin")
        mount_path = str(Path(mount_root) / "gpt2")
        binary_path = Path(os.environ.get("HF_MOUNT_BINARY", str(Path.home() / ".local/bin/hf-mount")))
        if not binary_path.exists():
            self.skipTest(f"hf-mount binary not found at {binary_path}")

        payload = build_demo_message()
        payload["artifact"] = {
            "kind": "repo",
            "repo": artifact_repo_id,
            "revision": revision,
        }
        payload["dataset_repo"] = legacy_repo_id
        payload["dataset_revision"] = revision

        self._cleanup_mount(binary_path, mount_path)
        try:
            result = asyncio.run(run_stdio_demo(payload=payload))
        finally:
            self._cleanup_mount(binary_path, mount_path)

        self.assertEqual(result["handshake"]["status"], "ready")
        self.assertEqual(result["result"]["status"], "resolved")
        self.assertEqual(result["result"]["artifact"]["repo_id"], artifact_repo_id)
        self.assertNotEqual(result["result"]["artifact"]["repo_id"], legacy_repo_id)
        self.assertEqual(result["result"]["artifact"]["kind"], "repo")
        self.assertTrue(result["result"]["artifact"]["mount_path"].endswith("/gpt2"))
        self.assertIn(result["result"]["artifact"]["status"], {"mounted", "already-mounted"})


if __name__ == "__main__":
    unittest.main()
