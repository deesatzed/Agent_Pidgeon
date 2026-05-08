import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.pain_finder import (
    analyze_agent_comparison_csv,
    analyze_catalog_gap_evidence,
    analyze_contract_lift_csv,
    analyze_human_reactions_csv,
    analyze_nanowhale_readiness_csv,
    analyze_pain_finder_csv,
    run_contract_discovery_experiment,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/contract_discovery"


class ContractDiscoveryExperimentTests(unittest.TestCase):
    def test_full_experiment_suite_passes_with_fixture_evidence(self) -> None:
        result = run_contract_discovery_experiment(
            pain_csv=EXAMPLES / "messy_workflow_examples.csv",
            lift_csv=EXAMPLES / "contract_lift_examples.csv",
            comparison_csv=EXAMPLES / "agent_comparison_examples.csv",
            human_csv=EXAMPLES / "human_reaction_examples.csv",
            readiness_csv=EXAMPLES / "nanowhale_readiness_examples.csv",
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["next_decision"], "collect_larger_real_corpus")
        self.assertGreaterEqual(result["corpus"]["strong_candidate_rate"], 0.3)
        self.assertGreaterEqual(result["contract_lift"]["meaningful_lift_rate"], 0.5)
        self.assertGreater(result["agent_comparison"]["missed_requirement_reduction"], 0)
        self.assertGreaterEqual(result["catalog_gap_evidence"]["catalog_gap_count"], 2)

    def test_contract_lift_measures_whether_contracts_expose_missing_obligations(self) -> None:
        result = analyze_contract_lift_csv(EXAMPLES / "contract_lift_examples.csv")

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["item_count"], 6)
        self.assertGreaterEqual(result["meaningful_lift_count"], 4)

    def test_contract_guided_agent_comparison_reduces_missed_requirements(self) -> None:
        result = analyze_agent_comparison_csv(EXAMPLES / "agent_comparison_examples.csv")

        self.assertEqual(result["status"], "passed")
        self.assertGreater(result["missed_requirement_reduction"], 0)
        self.assertGreater(result["unsafe_omission_reduction"], 0)
        self.assertGreaterEqual(result["more_auditable_rate"], 0.8)

    def test_catalog_gap_evidence_is_derived_from_strong_pain_finder_candidates(self) -> None:
        corpus = analyze_pain_finder_csv(EXAMPLES / "messy_workflow_examples.csv")
        result = analyze_catalog_gap_evidence(corpus)

        self.assertEqual(result["status"], "passed")
        self.assertIn("output schema", result["catalog_gap_signals"])
        self.assertIn("safety policy version", result["catalog_gap_signals"])

    def test_human_reaction_and_tiny_model_readiness_are_separate_decisions(self) -> None:
        human = analyze_human_reactions_csv(EXAMPLES / "human_reaction_examples.csv")
        readiness = analyze_nanowhale_readiness_csv(EXAMPLES / "nanowhale_readiness_examples.csv")

        self.assertEqual(human["status"], "passed")
        self.assertGreater(human["clarifying_rate"], human["bureaucratic_rate"])
        self.assertEqual(readiness["status"], "ready_for_trial")
        self.assertGreaterEqual(readiness["ready_domain_count"], 3)


if __name__ == "__main__":
    unittest.main()
