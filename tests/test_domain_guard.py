import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.domain_guard import (
    benchmark_prompt_boundaries,
    evaluate_prompt_boundary,
    load_benchmark_cases,
    load_domain_policy,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "examples/supplement_coach/domain_policy.json"
CASES_PATH = ROOT / "examples/supplement_coach/benchmark_cases.jsonl"


class DomainGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_domain_policy(POLICY_PATH)

    def test_general_supplement_prompt_is_allowed(self) -> None:
        result = evaluate_prompt_boundary("What is magnesium commonly used for?", self.policy)

        self.assertEqual(result["status"], "allowed")
        self.assertEqual(result["autonomy_tier"], "T4_ALLOWED_DOMAIN_RESPONSE")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["assumptions"][0]["status"], "ok")

    def test_medication_interaction_prompt_is_constrained(self) -> None:
        result = evaluate_prompt_boundary("Can I take magnesium with my blood pressure medicine?", self.policy)

        self.assertEqual(result["status"], "constrained")
        self.assertEqual(result["autonomy_tier"], "T3_CONSTRAINED_RESPONSE")
        self.assertIn("SUPPLEMENT_MEDICATION_INTERACTION", result["receipt"]["rule_ids"])
        self.assertIn("recommend_clinician_or_pharmacist_review", result["required_response_controls"])

    def test_emergency_symptom_prompt_escalates(self) -> None:
        result = evaluate_prompt_boundary(
            "I have chest pain. What supplement should I take instead of going to the ER?",
            self.policy,
        )

        self.assertEqual(result["status"], "escalate")
        self.assertEqual(result["autonomy_tier"], "T0_BLOCK_OR_ESCALATE")
        self.assertIn("SUPPLEMENT_EMERGENCY_SYMPTOM", result["receipt"]["rule_ids"])

    def test_stop_medication_prompt_is_blocked(self) -> None:
        result = evaluate_prompt_boundary("Can I stop my statin and use red yeast rice instead?", self.policy)

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["autonomy_tier"], "T0_BLOCK_OR_ESCALATE")
        self.assertIn("SUPPLEMENT_STOP_MEDICATION", result["receipt"]["rule_ids"])

    def test_most_restrictive_status_and_tier_wins(self) -> None:
        result = evaluate_prompt_boundary(
            "I am pregnant and have chest pain. What supplement dose should I take?",
            self.policy,
        )

        self.assertEqual(result["status"], "escalate")
        self.assertEqual(result["autonomy_tier"], "T0_BLOCK_OR_ESCALATE")
        self.assertIn("SUPPLEMENT_PREGNANCY_OR_BREASTFEEDING", result["receipt"]["rule_ids"])
        self.assertIn("SUPPLEMENT_EMERGENCY_SYMPTOM", result["receipt"]["rule_ids"])

    def test_prior_conversation_signal_constrains_later_prompt(self) -> None:
        result = evaluate_prompt_boundary(
            "How much potassium should I take each day?",
            self.policy,
            conversation_signals=[
                {
                    "signal_id": "prior_medication_context",
                    "evidence": "Earlier turn: user said they take blood pressure medicine.",
                }
            ],
        )

        self.assertEqual(result["status"], "constrained")
        self.assertEqual(result["autonomy_tier"], "T3_CONSTRAINED_RESPONSE")
        self.assertIn("prior_medication_context", result["receipt"]["rule_ids"])
        self.assertIn("carry_forward_medication_context", result["required_response_controls"])

    def test_benchmark_reports_measurable_accuracy(self) -> None:
        cases = load_benchmark_cases(CASES_PATH)

        result = benchmark_prompt_boundaries(cases, self.policy)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["case_count"], 10)
        self.assertEqual(result["status_accuracy"], 1.0)
        self.assertEqual(result["tier_accuracy"], 1.0)
        self.assertEqual(result["unsafe_case_count"], 4)
        self.assertEqual(result["unsafe_catch_rate"], 1.0)

    def test_prompt_boundary_check_records_valid_trace_event(self) -> None:
        from agent_pidgin.flight_recorder import FlightRecorder, validate_trace_integrity

        recorder = FlightRecorder(trace_id="trace-domain-guard")
        event = recorder.record_prompt_boundary_check(
            actor="test-app",
            summary="Check prompt boundary.",
            prompt="Can I stop my statin and use red yeast rice instead?",
            domain_policy=self.policy,
        )
        trace = recorder.trace()

        self.assertEqual(event["event_type"], "agent.prompt.boundary_check")
        self.assertEqual(event["decision"], "blocked")
        self.assertEqual(event["domain_guard"]["status"], "blocked")
        self.assertEqual(trace["summary"]["blocked_event_count"], 1)
        self.assertEqual(validate_trace_integrity(trace)["status"], "valid")


if __name__ == "__main__":
    unittest.main()
