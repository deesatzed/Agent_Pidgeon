import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.semantic_diff import diff_contracts, diff_step_lists


class SemanticDiffTests(unittest.TestCase):
    def test_diff_step_lists_flags_removed_safety_pointer(self) -> None:
        result = diff_step_lists(
            ["str.trim", "clinical.phi.scrub"],
            ["str.trim"],
        )

        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], ["clinical.phi.scrub"])
        self.assertEqual(result["changed"], [])
        self.assertEqual(result["risk_level"], "high")
        self.assertIn("clinical.phi.scrub", result["risk_notes"][0])

    def test_diff_step_lists_reports_added_pointer(self) -> None:
        result = diff_step_lists(["str.trim"], ["str.trim", "agent.attach_receipts"])

        self.assertEqual(result["added"], ["agent.attach_receipts"])
        self.assertEqual(result["removed"], [])
        self.assertEqual(result["risk_level"], "low")

    def test_diff_step_lists_flags_removed_control_guardrail(self) -> None:
        result = diff_step_lists(
            ["str.trim", "agent.request_human_review"],
            ["str.trim"],
        )

        self.assertEqual(result["removed"], ["agent.request_human_review"])
        self.assertEqual(result["risk_level"], "high")
        self.assertIn("Control guardrail removed", result["risk_notes"][0])

    def test_diff_contracts_reports_artifact_and_language_changes(self) -> None:
        left = {
            "target_language": "python",
            "artifact": {
                "kind": "repo",
                "repo": "waynesatz/agent-pidgin-data",
                "revision": "a" * 40,
            },
            "steps": ["str.trim"],
        }
        right = {
            "target_language": "javascript",
            "artifact": {
                "kind": "repo",
                "repo": "waynesatz/other-catalog",
                "revision": "b" * 40,
            },
            "steps": ["str.trim"],
        }

        result = diff_contracts(left, right)

        self.assertEqual(result["risk_level"], "high")
        self.assertIn("artifact.repo", {change["field"] for change in result["contract_changes"]})
        self.assertIn("target_language", {change["field"] for change in result["contract_changes"]})


if __name__ == "__main__":
    unittest.main()
