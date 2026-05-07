import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]


class ShowpieceTests(unittest.TestCase):
    def test_offline_showpiece_resolves_with_receipts_and_flags_unsafe_change(self) -> None:
        run_showpiece = load_showpiece_runner()

        result = run_showpiece(live_llm=False)

        self.assertEqual(result["status"], "showpiece_completed")
        self.assertEqual(result["mode"], "offline_fixture")
        self.assertEqual(result["schema_validation"]["status"], "valid")
        self.assertEqual(result["policy"]["error_count"], 0)
        self.assertEqual(result["resolution"]["status"], "resolved")
        self.assertEqual(len(result["resolution"]["resolution"]["resolved_steps"]), 7)
        self.assertEqual(len(result["resolution"]["resolution"]["receipts"]), 7)
        self.assertEqual(result["unsafe_change_review"]["diff"]["risk_level"], "high")
        self.assertIn("clinical.phi.scrub", result["unsafe_change_review"]["diff"]["removed"])
        self.assertIn(
            "UNPINNED_REVISION",
            {finding["code"] for finding in result["unsafe_change_review"]["policy_findings"]},
        )

    def test_showpiece_contract_records_llm_guardrails(self) -> None:
        run_showpiece = load_showpiece_runner()

        result = run_showpiece(live_llm=False)
        contract = result["draft"]["contract"]

        self.assertTrue(contract["metadata"]["not_clinical_decision_support"])
        self.assertEqual(contract["metadata"]["showpiece_guardrail_added_steps"], [])
        self.assertIn("agent.attach_receipts", contract["steps"])
        self.assertEqual(
            result["novice_expectations"]["what_it_does_not_do"],
            "It does not execute the returned implementation strings.",
        )

    def test_live_showpiece_falls_back_when_llm_returns_no_known_pointers(self) -> None:
        module = load_showpiece_module()
        original_draft_contract = module.draft_contract

        def rejecting_live_draft(*args, **kwargs):
            if kwargs.get("transport") is None:
                raise ValueError("LLM authoring did not propose any known catalog pointers")
            return original_draft_contract(*args, **kwargs)

        module.draft_contract = rejecting_live_draft
        try:
            result = module.run_showpiece(live_llm=True)
        finally:
            module.draft_contract = original_draft_contract

        self.assertEqual(result["mode"], "live_llm_with_fixture_fallback")
        self.assertEqual(result["draft"]["authoring"]["live_llm_status"], "rejected")
        self.assertEqual(result["resolution"]["status"], "resolved")


def load_showpiece_runner():
    return load_showpiece_module().run_showpiece


def load_showpiece_module():
    script_path = ROOT / "examples/showpiece_demo/run_showpiece.py"
    spec = importlib.util.spec_from_file_location("showpiece_demo", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load showpiece demo script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
