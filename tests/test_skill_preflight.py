import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.skill_preflight import verify_skill_manifest


class SkillPreflightTests(unittest.TestCase):
    def test_unsigned_shell_skill_is_blocked(self) -> None:
        result = verify_skill_manifest(
            {
                "skill_id": "community/shell-runner",
                "name": "Shell Runner",
                "version": "0.1.0",
                "publisher": {"id": "community", "name": "Community"},
                "signed": False,
                "permissions": [
                    {
                        "kind": "shell",
                        "target": "*",
                        "access": "execute",
                    }
                ],
                "capabilities": ["shell.propose_command"],
            }
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("DANGEROUS_SHELL_PERMISSION", {finding["code"] for finding in result["findings"]})

    def test_signed_low_risk_skill_is_approved(self) -> None:
        result = verify_skill_manifest(
            {
                "skill_id": "trusted/ticket-reader",
                "name": "Ticket Reader",
                "version": "1.0.0",
                "publisher": {"id": "trusted", "name": "Trusted Publisher"},
                "signed": True,
                "permissions": [
                    {
                        "kind": "network",
                        "target": "tickets.internal",
                        "access": "read",
                    }
                ],
                "capabilities": ["json.parse"],
            }
        )

        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["findings"][0]["code"], "SKILL_PREFLIGHT_PASSED")

    def test_trust_root_blocks_untrusted_publisher(self) -> None:
        result = verify_skill_manifest(
            {
                "skill_id": "community/ticket-reader",
                "name": "Ticket Reader",
                "version": "1.0.0",
                "publisher": {"id": "community", "name": "Community"},
                "signed": True,
                "signature": {"key_id": "key-community-001"},
                "permissions": [
                    {
                        "kind": "network",
                        "target": "tickets.internal",
                        "access": "read",
                    }
                ],
                "capabilities": ["json.parse"],
            },
            trust_root={
                "require_signature": True,
                "trusted_publishers": ["trusted"],
                "trusted_key_ids": ["key-trusted-001"],
                "revoked_key_ids": [],
            },
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("UNTRUSTED_PUBLISHER", {finding["code"] for finding in result["findings"]})

    def test_trust_root_allows_trusted_signed_low_risk_skill(self) -> None:
        result = verify_skill_manifest(
            {
                "skill_id": "trusted/ticket-reader",
                "name": "Ticket Reader",
                "version": "1.0.0",
                "publisher": {"id": "trusted", "name": "Trusted Publisher"},
                "signed": True,
                "signature": {"key_id": "key-trusted-001"},
                "permissions": [
                    {
                        "kind": "network",
                        "target": "tickets.internal",
                        "access": "read",
                    }
                ],
                "capabilities": ["json.parse"],
            },
            trust_root={
                "require_signature": True,
                "trusted_publishers": ["trusted"],
                "trusted_key_ids": ["key-trusted-001"],
                "revoked_key_ids": [],
            },
        )

        self.assertEqual(result["status"], "approved")
        self.assertIsNotNone(result["trust_root_hash"])


if __name__ == "__main__":
    unittest.main()
