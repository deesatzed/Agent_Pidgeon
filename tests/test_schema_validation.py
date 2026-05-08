import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.schema_validator import (
    validate_catalog,
    validate_pidgin_handshake,
    validate_pidgin_message,
    validate_pidgin_trace,
    validate_skill_manifest,
)


def valid_message() -> dict:
    return {
        "pidgin_version": "0.1",
        "message_type": "resolve",
        "message_id": "msg-001",
        "sender_id": "agent-a",
        "receiver_id": "agent-b",
        "target_language": "python",
        "artifact": {
            "kind": "repo",
            "repo": "waynesatz/agent-pidgin-data",
            "revision": "abc123",
        },
        "steps": ["str.trim"],
        "created_at": "2026-03-25T10:30:00Z",
    }


class SchemaValidationTests(unittest.TestCase):
    def test_validate_pidgin_message_accepts_valid_message(self) -> None:
        validate_pidgin_message(valid_message())

    def test_validate_pidgin_message_rejects_missing_version(self) -> None:
        payload = valid_message()
        payload.pop("pidgin_version")

        with self.assertRaisesRegex(ValueError, "pidgin_version"):
            validate_pidgin_message(payload)

    def test_validate_pidgin_message_rejects_bad_message_type(self) -> None:
        payload = valid_message()
        payload["message_type"] = "execute"

        with self.assertRaisesRegex(ValueError, "message_type"):
            validate_pidgin_message(payload)

    def test_validate_pidgin_message_rejects_empty_steps(self) -> None:
        payload = valid_message()
        payload["steps"] = []

        with self.assertRaisesRegex(ValueError, "steps"):
            validate_pidgin_message(payload)

    def test_validate_pidgin_message_rejects_malformed_artifact(self) -> None:
        payload = valid_message()
        payload["artifact"] = {"kind": "repo", "repo": "bad repo", "revision": "main"}

        with self.assertRaisesRegex(ValueError, "artifact.repo"):
            validate_pidgin_message(payload)

    def test_validate_pidgin_message_rejects_unsupported_target_language(self) -> None:
        payload = valid_message()
        payload["target_language"] = "ruby"

        with self.assertRaisesRegex(ValueError, "target_language"):
            validate_pidgin_message(payload)

    def test_validate_pidgin_handshake_accepts_valid_handshake(self) -> None:
        validate_pidgin_handshake(
            {
                "pidgin_version": "0.1",
                "message_type": "handshake",
                "message_id": "msg-hs-001",
                "sender_id": "agent-a",
                "receiver_id": "agent-b",
                "created_at": "2026-03-25T10:30:00Z",
            }
        )

    def test_validate_catalog_accepts_valid_catalog(self) -> None:
        validate_catalog(
            {
                "catalog_id": "test",
                "version": "0.1.0",
                "concepts": [
                    {
                        "pointer": "str.trim",
                        "type_signature": "str -> str",
                        "implementations": {"python": "lambda s: s.strip()"},
                    }
                ],
            }
        )

    def test_validate_pidgin_trace_accepts_valid_trace(self) -> None:
        validate_pidgin_trace(
            {
                "pidgin_version": "0.1",
                "trace_id": "trace-001",
                "status": "completed",
                "generated_at": "2026-05-07T12:00:00Z",
                "events": [
                    {
                        "event_id": "evt-0001",
                        "parent_event_id": None,
                        "event_type": "agent.goal.received",
                        "actor": "agent-a",
                        "timestamp": "2026-05-07T12:00:00Z",
                        "summary": "Receive goal.",
                        "decision": "observed",
                        "payload": {"goal": "test"},
                        "payload_hash": "a" * 64,
                        "previous_event_hash": None,
                        "event_hash": "b" * 64,
                    }
                ],
                "trace_hash": "c" * 64,
            }
        )

    def test_validate_skill_manifest_accepts_valid_manifest(self) -> None:
        validate_skill_manifest(
            {
                "skill_id": "community/test-skill",
                "name": "Test Skill",
                "version": "0.1.0",
                "publisher": {
                    "id": "community",
                    "name": "Community",
                },
                "signed": True,
                "signature": {"key_id": "key-community-001", "algorithm": "ed25519", "value": "test-signature"},
                "permissions": [
                    {
                        "kind": "email",
                        "target": "customer",
                        "access": "send",
                    }
                ],
                "capabilities": ["comm.send_external_message"],
            }
        )

    def test_validate_skill_manifest_rejects_signed_without_signature(self) -> None:
        with self.assertRaisesRegex(ValueError, "signature"):
            validate_skill_manifest(
                {
                    "skill_id": "community/test-skill",
                    "name": "Test Skill",
                    "version": "0.1.0",
                    "publisher": {
                        "id": "community",
                        "name": "Community",
                    },
                    "signed": True,
                    "permissions": [
                        {
                            "kind": "email",
                            "target": "customer",
                            "access": "send",
                        }
                    ],
                    "capabilities": ["comm.send_external_message"],
                }
            )

    def test_validate_pidgin_trace_rejects_event_without_hash(self) -> None:
        trace = {
            "pidgin_version": "0.1",
            "trace_id": "trace-001",
            "status": "completed",
            "generated_at": "2026-05-07T12:00:00Z",
            "events": [
                {
                    "event_id": "evt-0001",
                    "parent_event_id": None,
                    "event_type": "agent.goal.received",
                    "actor": "agent-a",
                    "timestamp": "2026-05-07T12:00:00Z",
                    "summary": "Receive goal.",
                    "decision": "observed",
                    "payload": {"goal": "test"},
                    "payload_hash": "a" * 64,
                    "previous_event_hash": None,
                }
            ],
            "trace_hash": "c" * 64,
        }
        with self.assertRaisesRegex(ValueError, "event_hash"):
            validate_pidgin_trace(trace)


if __name__ == "__main__":
    unittest.main()
