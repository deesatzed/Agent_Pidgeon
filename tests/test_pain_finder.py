import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.pain_finder import PainFinderInput, analyze_pain_finder_csv, score_instruction

ROOT = Path(__file__).resolve().parents[1]


class PainFinderTests(unittest.TestCase):
    def test_scores_messy_clinical_transform_as_strong_candidate(self) -> None:
        result = score_instruction(
            PainFinderInput(
                item_id="clinical-001",
                source_type="clinical_data_request",
                raw_instruction="Clean the clinical note, remove PHI, preserve negation, and return strict JSON.",
            )
        )

        self.assertGreaterEqual(result["pidgin_pain_score"], 10)
        self.assertEqual(result["candidate_contract_type"], "clinical_text_transformation")
        self.assertEqual(result["recommended_next_step"], "convert_to_candidate_pidgin_contract")
        self.assertIn("safety policy version", result["hidden_requirements"])
        self.assertIn("output schema", result["hidden_requirements"])

    def test_scores_plain_instruction_as_not_pidgin_problem(self) -> None:
        result = score_instruction(
            PainFinderInput(
                item_id="plain-001",
                source_type="plain_note",
                raw_instruction="Rename the meeting title to project sync.",
            )
        )

        self.assertLessEqual(result["pidgin_pain_score"], 5)
        self.assertEqual(result["candidate_strength"], "not_a_pidgin_problem")
        self.assertEqual(result["recommended_next_step"], "leave_as_plain_instruction")

    def test_analyzes_fixture_dataset(self) -> None:
        result = analyze_pain_finder_csv(ROOT / "examples/contract_discovery/messy_workflow_examples.csv")

        self.assertEqual(result["status"], "analyzed")
        self.assertEqual(result["item_count"], 6)
        self.assertGreaterEqual(result["strong_candidate_count"], 2)
        self.assertGreater(result["strong_candidate_rate"], 0.3)


if __name__ == "__main__":
    unittest.main()
