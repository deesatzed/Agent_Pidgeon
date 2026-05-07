import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.llm_authoring import draft_contract, explain_contract, review_contract


class LlmAuthoringTests(unittest.TestCase):
    def test_draft_contract_validates_known_steps_and_rejects_unknown_suggestions(self) -> None:
        def fake_transport(payload):
            return {
                "steps": ["str.trim", "agent.attach_receipts", "unknown.pointer"],
                "rationale": "Use known cleanup and receipt primitives.",
                "warnings": ["Unknown pointer should be ignored."],
            }

        result = draft_contract(
            description="Clean text and keep receipts.",
            artifact_repo="waynesatz/agent-pidgin-data",
            artifact_revision="a" * 40,
            transport=fake_transport,
        )

        contract = result["contract"]
        self.assertEqual(result["status"], "drafted")
        self.assertEqual(contract["steps"], ["str.trim", "agent.attach_receipts"])
        self.assertEqual(contract["metadata"]["rejected_unknown_steps"], ["unknown.pointer"])

    def test_explain_contract_uses_transport_without_api_key(self) -> None:
        def fake_transport(payload):
            return {"text": "This contract trims text and attaches provenance."}

        result = explain_contract(
            {
                "pidgin_version": "0.1",
                "message_type": "resolve",
                "message_id": "msg-001",
                "sender_id": "agent-a",
                "receiver_id": "agent-b",
                "target_language": "python",
                "artifact": {
                    "kind": "repo",
                    "repo": "waynesatz/agent-pidgin-data",
                    "revision": "a" * 40,
                },
                "steps": ["str.trim"],
                "created_at": "2026-03-25T10:30:00Z",
            },
            transport=fake_transport,
        )

        self.assertEqual(result["status"], "explained")
        self.assertIn("provenance", result["explanation"])

    def test_review_contract_returns_structured_review(self) -> None:
        def fake_transport(payload):
            return {
                "summary": "Looks valid.",
                "risks": [],
                "suggestions": ["Consider agent.attach_receipts."],
            }

        result = review_contract(
            {
                "pidgin_version": "0.1",
                "message_type": "resolve",
                "message_id": "msg-001",
                "sender_id": "agent-a",
                "receiver_id": "agent-b",
                "target_language": "python",
                "artifact": {
                    "kind": "repo",
                    "repo": "waynesatz/agent-pidgin-data",
                    "revision": "a" * 40,
                },
                "steps": ["str.trim"],
                "created_at": "2026-03-25T10:30:00Z",
            },
            transport=fake_transport,
        )

        self.assertEqual(result["status"], "reviewed")
        self.assertEqual(result["review"]["summary"], "Looks valid.")


if __name__ == "__main__":
    unittest.main()
