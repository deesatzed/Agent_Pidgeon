import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.config import PidginConfig


class ConfigTests(unittest.TestCase):
    def test_from_env_uses_project_defaults(self) -> None:
        original = dict(os.environ)
        try:
            for key in [
                "AGENT_PIDGIN_DATA_REPO",
                "AGENT_PIDGIN_DATA_REVISION",
                "AGENT_PIDGIN_ARTIFACT_KIND",
                "AGENT_PIDGIN_ARTIFACT_REPO",
                "AGENT_PIDGIN_ARTIFACT_REVISION",
                "AGENT_PIDGIN_MOUNT_ROOT",
                "HF_MOUNT_BINARY",
                "HF_TOKEN",
            ]:
                os.environ.pop(key, None)

            config = PidginConfig.from_env()

            self.assertEqual(config.dataset_repo, "waynesatz/agent-pidgin-data")
            self.assertEqual(config.dataset_revision, "main")
            self.assertEqual(config.artifact_kind, "repo")
            self.assertEqual(config.artifact_repo, "waynesatz/agent-pidgin-data")
            self.assertEqual(config.artifact_revision, "main")
            self.assertEqual(config.mount_root, "/tmp/agent-pidgin")
            self.assertEqual(config.hf_mount_binary, Path.home() / ".local/bin/hf-mount")
            self.assertIsNone(config.hf_token)
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_from_env_respects_overrides(self) -> None:
        original = dict(os.environ)
        try:
            os.environ["AGENT_PIDGIN_DATA_REPO"] = "openai-community/gpt2"
            os.environ["AGENT_PIDGIN_DATA_REVISION"] = "v1.0"
            os.environ["AGENT_PIDGIN_ARTIFACT_KIND"] = "repo"
            os.environ["AGENT_PIDGIN_ARTIFACT_REPO"] = "openai-community/gpt2"
            os.environ["AGENT_PIDGIN_ARTIFACT_REVISION"] = "v1.0"
            os.environ["AGENT_PIDGIN_MOUNT_ROOT"] = "/tmp/agent-pidgin-future"
            os.environ["HF_MOUNT_BINARY"] = "/tmp/hf-mount"
            os.environ["HF_TOKEN"] = "hf_test"

            config = PidginConfig.from_env()

            self.assertEqual(config.dataset_repo, "openai-community/gpt2")
            self.assertEqual(config.dataset_revision, "v1.0")
            self.assertEqual(config.artifact_kind, "repo")
            self.assertEqual(config.artifact_repo, "openai-community/gpt2")
            self.assertEqual(config.artifact_revision, "v1.0")
            self.assertEqual(config.mount_root, "/tmp/agent-pidgin-future")
            self.assertEqual(config.hf_mount_binary, Path("/tmp/hf-mount"))
            self.assertEqual(config.hf_token, "hf_test")
        finally:
            os.environ.clear()
            os.environ.update(original)


if __name__ == "__main__":
    unittest.main()
