import importlib.util
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.schema_validator import validate_pidgin_message
from agent_pidgin.semantic_diff import diff_payload

ROOT = Path(__file__).resolve().parents[1]


class ExampleTests(unittest.TestCase):
    def test_a2a_wrapper_sample_contains_valid_pidgin_contract(self) -> None:
        task = json.loads((ROOT / "examples/a2a_wrapper/sample_a2a_task.json").read_text(encoding="utf-8"))
        contract = task["artifacts"][0]["content"]

        validate_pidgin_message(contract)

    def test_clinical_safety_demo_contract_is_valid_and_non_diagnostic(self) -> None:
        contract = json.loads((ROOT / "examples/clinical_safety_demo/sample_contract.json").read_text(encoding="utf-8"))

        validate_pidgin_message(contract)

        self.assertTrue(contract["metadata"]["not_clinical_decision_support"])
        self.assertIn("clinical.phi.scrub", contract["steps"])
        self.assertIn("agent.attach_receipts", contract["steps"])

    def test_contract_fixtures_are_valid_and_policy_examples_are_distinct(self) -> None:
        sample = json.loads((ROOT / "examples/contracts/sample_message.json").read_text(encoding="utf-8"))
        unpinned = json.loads((ROOT / "examples/contracts/unpinned_message.json").read_text(encoding="utf-8"))

        validate_pidgin_message(sample)
        validate_pidgin_message(unpinned)

        self.assertEqual(sample["artifact"]["revision"], "a" * 40)
        self.assertEqual(unpinned["artifact"]["revision"], "main")

    def test_contract_diff_fixture_flags_removed_safety_step(self) -> None:
        payload = json.loads((ROOT / "examples/contracts/sample_diff.json").read_text(encoding="utf-8"))

        result = diff_payload(payload)

        self.assertEqual(result["removed"], ["clinical.phi.scrub"])
        self.assertTrue(result["risk_notes"])

    def test_clinical_safety_demo_resolves_with_receipts(self) -> None:
        resolve_sample_contract = load_resolve_sample_contract()

        result = resolve_sample_contract()

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(len(result["resolution"]["resolved_steps"]), 6)
        self.assertEqual(len(result["resolution"]["receipts"]), 6)
        self.assertIn("SENSITIVE_POINTER_RECEIPTS_REQUIRED", {item["code"] for item in result["policy_findings"]})


def load_resolve_sample_contract():
    script_path = ROOT / "examples/clinical_safety_demo/resolve_demo.py"
    spec = importlib.util.spec_from_file_location("clinical_safety_resolve_demo", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load clinical safety demo script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.resolve_sample_contract


if __name__ == "__main__":
    unittest.main()
