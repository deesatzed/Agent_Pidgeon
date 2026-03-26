import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.config import PidginConfig
from agent_pidgin.service import PidginReceiverService


class RecordingMountGateway:
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


class ServiceTests(unittest.TestCase):
    def test_receiver_service_returns_handshake_capabilities(self) -> None:
        gateway = RecordingMountGateway()
        service = PidginReceiverService(
            mount_gateway=gateway,
            catalog=SeedCatalog.load_default(),
            default_mount_root="/tmp/agent-pidgin",
        )

        result = service.handshake(
            {
                "message_type": "handshake",
                "message_id": "msg-hs-101",
                "sender_id": "agent-a",
                "receiver_id": "agent-b",
                "created_at": "2026-03-25T12:35:00Z",
            },
            config=PidginConfig.from_env(),
        )

        self.assertEqual(result["message_id"], "msg-hs-101")
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["capabilities"]["supported_message_types"], ["handshake", "resolve"])
        self.assertEqual(result["capabilities"]["artifact_defaults"]["mount_root"], "/tmp/agent-pidgin")
        self.assertEqual(gateway.calls, [])

    def test_receiver_service_mounts_and_resolves_message(self) -> None:
        gateway = RecordingMountGateway()
        service = PidginReceiverService(
            mount_gateway=gateway,
            catalog=SeedCatalog.load_default(),
            default_mount_root="/tmp/agent-pidgin",
        )

        result = service.resolve_message(
            {
                "message_id": "msg-101",
                "sender_id": "agent-a",
                "receiver_id": "agent-b",
                "target_language": "python",
                "dataset_repo": "waynesatz/agent-pidgin-data",
                "dataset_revision": "main",
                "steps": ["str.trim", "str.lowercase"],
                "created_at": "2026-03-25T10:40:00Z",
            }
        )

        self.assertEqual(result["message_id"], "msg-101")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["artifact"]["repo_id"], "waynesatz/agent-pidgin-data")
        self.assertEqual(result["resolution"]["resolved_steps"][0]["pointer"], "str.trim")
        self.assertEqual(gateway.calls[0]["mount_path"], "/tmp/agent-pidgin/agent-pidgin-data")

    def test_receiver_service_prefers_artifact_payload_over_legacy_dataset_fields(self) -> None:
        gateway = RecordingMountGateway()
        service = PidginReceiverService(
            mount_gateway=gateway,
            catalog=SeedCatalog.load_default(),
            default_mount_root="/tmp/agent-pidgin",
        )

        result = service.resolve_message(
            {
                "message_type": "resolve",
                "message_id": "msg-102",
                "sender_id": "agent-a",
                "receiver_id": "agent-b",
                "target_language": "python",
                "artifact": {
                    "kind": "repo",
                    "repo": "openai-community/gpt2",
                    "revision": "main",
                },
                "dataset_repo": "waynesatz/agent-pidgin-data",
                "dataset_revision": "main",
                "steps": ["str.trim"],
                "created_at": "2026-03-25T10:45:00Z",
            },
            config=PidginConfig(
                dataset_repo="waynesatz/agent-pidgin-data",
                dataset_revision="main",
                artifact_kind="repo",
                artifact_repo="waynesatz/agent-pidgin-data",
                artifact_revision="main",
                mount_root="/tmp/agent-pidgin",
                hf_mount_binary=Path("/Users/test/.local/bin/hf-mount"),
                hf_token=None,
            ),
        )

        self.assertEqual(result["artifact"]["repo_id"], "openai-community/gpt2")
        self.assertEqual(gateway.calls[0]["repo_id"], "openai-community/gpt2")
        self.assertEqual(gateway.calls[0]["mount_path"], "/tmp/agent-pidgin/gpt2")

    def test_receiver_service_falls_back_to_config_artifact_defaults(self) -> None:
        gateway = RecordingMountGateway()
        service = PidginReceiverService(
            mount_gateway=gateway,
            catalog=SeedCatalog.load_default(),
            default_mount_root="/tmp/agent-pidgin",
        )

        result = service.resolve_message(
            {
                "message_type": "resolve",
                "message_id": "msg-103",
                "sender_id": "agent-a",
                "receiver_id": "agent-b",
                "target_language": "python",
                "steps": ["str.trim"],
                "created_at": "2026-03-25T10:50:00Z",
            },
            config=PidginConfig(
                dataset_repo="waynesatz/legacy-dataset",
                dataset_revision="legacy-main",
                artifact_kind="repo",
                artifact_repo="openai-community/gpt2",
                artifact_revision="main",
                mount_root="/tmp/agent-pidgin",
                hf_mount_binary=Path("/Users/test/.local/bin/hf-mount"),
                hf_token=None,
            ),
        )

        self.assertEqual(result["artifact"]["repo_id"], "openai-community/gpt2")
        self.assertEqual(gateway.calls[0]["revision"], "main")
        self.assertEqual(gateway.calls[0]["mount_path"], "/tmp/agent-pidgin/gpt2")


if __name__ == "__main__":
    unittest.main()
