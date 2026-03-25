from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.protocol import PidginHandshake, PidginMessage


class ProtocolTests(unittest.TestCase):
    def test_pidgin_handshake_from_dict_parses_required_fields(self) -> None:
        payload = {
            "message_type": "handshake",
            "message_id": "msg-hs-001",
            "sender_id": "agent-a",
            "receiver_id": "agent-b",
            "created_at": "2026-03-25T12:30:00Z",
        }

        message = PidginHandshake.from_dict(payload)

        self.assertEqual(message.message_type, "handshake")
        self.assertEqual(message.message_id, "msg-hs-001")

    def test_pidgin_message_from_dict_parses_required_fields(self) -> None:
        payload = {
            "message_id": "msg-001",
            "sender_id": "agent-a",
            "receiver_id": "agent-b",
            "target_language": "python",
            "dataset_repo": "waynesatz/agent-pidgin-data",
            "dataset_revision": "main",
            "steps": ["str.trim", "str.lowercase"],
            "created_at": "2026-03-25T10:30:00Z",
        }

        message = PidginMessage.from_dict(payload)

        self.assertEqual(message.message_id, "msg-001")
        self.assertEqual(message.message_type, "resolve")
        self.assertEqual(message.sender_id, "agent-a")
        self.assertEqual(message.receiver_id, "agent-b")
        self.assertEqual(message.target_language, "python")
        self.assertEqual(message.dataset_repo, "waynesatz/agent-pidgin-data")
        self.assertEqual(message.steps, ["str.trim", "str.lowercase"])

    def test_pidgin_message_from_dict_parses_optional_artifact_target(self) -> None:
        payload = {
            "message_type": "resolve",
            "message_id": "msg-003",
            "sender_id": "agent-a",
            "receiver_id": "agent-b",
            "target_language": "python",
            "artifact": {
                "kind": "repo",
                "repo": "openai-community/gpt2",
                "revision": "main",
            },
            "steps": ["str.trim"],
            "created_at": "2026-03-25T10:35:00Z",
        }

        message = PidginMessage.from_dict(payload)

        self.assertEqual(message.message_type, "resolve")
        self.assertEqual(message.artifact.kind, "repo")
        self.assertEqual(message.artifact.repo, "openai-community/gpt2")
        self.assertEqual(message.artifact.revision, "main")

    def test_pidgin_message_requires_non_empty_steps(self) -> None:
        payload = {
            "message_id": "msg-002",
            "sender_id": "agent-a",
            "receiver_id": "agent-b",
            "target_language": "python",
            "dataset_repo": "waynesatz/agent-pidgin-data",
            "dataset_revision": "main",
            "steps": [],
            "created_at": "2026-03-25T10:30:00Z",
        }

        with self.assertRaises(ValueError):
            PidginMessage.from_dict(payload)


if __name__ == "__main__":
    unittest.main()
