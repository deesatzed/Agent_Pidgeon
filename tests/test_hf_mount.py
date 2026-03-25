from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.hf_mount import HfMountManager


class HfMountTests(unittest.TestCase):
    def test_build_start_command_includes_revision_and_mount_point(self) -> None:
        manager = HfMountManager(binary_path=Path("/Users/test/.local/bin/hf-mount"))

        command = manager.build_start_command(
            repo_id="waynesatz/agent-pidgin-data",
            mount_path="/tmp/agent-pidgin-data",
            revision="main",
            hf_token=None,
        )

        self.assertEqual(command[0], "/Users/test/.local/bin/hf-mount")
        self.assertEqual(command[1], "start")
        self.assertIn("repo", command)
        self.assertIn("waynesatz/agent-pidgin-data", command)
        self.assertIn("/tmp/agent-pidgin-data", command)
        self.assertIn("--revision", command)
        self.assertIn("main", command)

    def test_build_start_command_includes_token_when_present(self) -> None:
        manager = HfMountManager(binary_path=Path("/Users/test/.local/bin/hf-mount"))

        command = manager.build_start_command(
            repo_id="waynesatz/agent-pidgin-data",
            mount_path="/tmp/agent-pidgin-data",
            revision="main",
            hf_token="hf_test",
        )

        self.assertEqual(command[:4], ["/Users/test/.local/bin/hf-mount", "start", "--hf-token", "hf_test"])

    def test_ensure_repo_mounted_returns_artifact_metadata(self) -> None:
        calls = []

        def fake_runner(command, capture_output, text, timeout):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="mounted", stderr="")

        manager = HfMountManager(
            binary_path=Path("/Users/test/.local/bin/hf-mount"),
            runner=fake_runner,
        )

        artifact = manager.ensure_repo_mounted(
            repo_id="waynesatz/agent-pidgin-data",
            mount_path="/tmp/agent-pidgin-data",
            revision="main",
        )

        self.assertEqual(artifact["status"], "mounted")
        self.assertEqual(artifact["repo_id"], "waynesatz/agent-pidgin-data")
        self.assertEqual(artifact["mount_path"], "/tmp/agent-pidgin-data")
        self.assertEqual(calls[0][0], "/Users/test/.local/bin/hf-mount")

    def test_ensure_repo_mounted_raises_on_command_failure(self) -> None:
        def fake_runner(command, capture_output, text, timeout):
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")

        manager = HfMountManager(
            binary_path=Path("/Users/test/.local/bin/hf-mount"),
            runner=fake_runner,
        )

        with self.assertRaises(RuntimeError):
            manager.ensure_repo_mounted(
                repo_id="waynesatz/agent-pidgin-data",
                mount_path="/tmp/agent-pidgin-data",
                revision="main",
            )

    def test_ensure_repo_mounted_treats_existing_daemon_as_success(self) -> None:
        def fake_runner(command, capture_output, text, timeout):
            return SimpleNamespace(
                returncode=1,
                stdout="",
                stderr='Error: daemon already running (pid=123) for "/tmp/agent-pidgin-data". Stop it first with: hf-mount stop /tmp/agent-pidgin-data',
            )

        manager = HfMountManager(
            binary_path=Path("/Users/test/.local/bin/hf-mount"),
            runner=fake_runner,
        )

        artifact = manager.ensure_repo_mounted(
            repo_id="waynesatz/agent-pidgin-data",
            mount_path="/tmp/agent-pidgin-data",
            revision="main",
        )

        self.assertEqual(artifact["status"], "already-mounted")
        self.assertEqual(artifact["mount_path"], "/tmp/agent-pidgin-data")

    def test_ensure_repo_mounted_precreates_mount_parent_directory(self) -> None:
        parent_exists_during_runner = []

        def fake_runner(command, capture_output, text, timeout):
            mount_path = Path(command[4])
            parent_exists_during_runner.append(mount_path.parent.exists())
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        with TemporaryDirectory() as temp_dir:
            mount_path = Path(temp_dir) / "nested" / "gpt2"
            manager = HfMountManager(
                binary_path=Path("/Users/test/.local/bin/hf-mount"),
                runner=fake_runner,
            )

            manager.ensure_repo_mounted(
                repo_id="openai-community/gpt2",
                mount_path=str(mount_path),
                revision="main",
            )

        self.assertEqual(parent_exists_during_runner, [True])

    def test_build_stop_command_targets_mount_path(self) -> None:
        manager = HfMountManager(binary_path=Path("/Users/test/.local/bin/hf-mount"))

        command = manager.build_stop_command("/tmp/agent-pidgin-data")

        self.assertEqual(
            command,
            ["/Users/test/.local/bin/hf-mount", "stop", str(Path("/tmp/agent-pidgin-data").resolve())],
        )

    def test_stop_repo_mount_raises_on_command_failure(self) -> None:
        def fake_runner(command, capture_output, text, timeout):
            return SimpleNamespace(returncode=1, stdout="", stderr="stop failed")

        manager = HfMountManager(
            binary_path=Path("/Users/test/.local/bin/hf-mount"),
            runner=fake_runner,
        )

        with self.assertRaises(RuntimeError):
            manager.stop_repo_mount("/tmp/agent-pidgin-data")

    def test_stop_repo_mount_executes_stop_command(self) -> None:
        calls = []

        def fake_runner(command, capture_output, text, timeout):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="stopped", stderr="")

        manager = HfMountManager(
            binary_path=Path("/Users/test/.local/bin/hf-mount"),
            runner=fake_runner,
        )

        manager.stop_repo_mount("/tmp/agent-pidgin-data")

        self.assertEqual(
            calls[0],
            ["/Users/test/.local/bin/hf-mount", "stop", str(Path("/tmp/agent-pidgin-data").resolve())],
        )


if __name__ == "__main__":
    unittest.main()
