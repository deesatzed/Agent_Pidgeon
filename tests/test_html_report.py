import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.flight_recorder import FlightRecorder
from agent_pidgin.html_report import build_trace_html

ROOT = Path(__file__).resolve().parents[1]


class HtmlReportTests(unittest.TestCase):
    def test_report_shows_integrity_policy_receipts_and_diff_sections(self) -> None:
        recorder = FlightRecorder(trace_id="trace-html-report")
        safe_contract = json.loads(
            (ROOT / "examples/agent_flight_recorder_demo/safe_tool_contract.json").read_text(encoding="utf-8")
        )
        corrupted_contract = json.loads(
            (ROOT / "examples/agent_flight_recorder_demo/corrupted_tool_contract.json").read_text(encoding="utf-8")
        )
        recorder.record_contract_event(
            event_type="agent.tool.proposed_call",
            actor="agent-a",
            summary="Propose safe call.",
            contract=safe_contract,
        )
        recorder.record_contract_event(
            event_type="agent.tool.proposed_call",
            actor="agent-a",
            summary="Propose unsafe call.",
            contract=corrupted_contract,
            previous_contract=safe_contract,
        )

        report = build_trace_html(recorder.trace())

        self.assertIn("Trace integrity", report)
        self.assertIn("valid hash chain", report)
        self.assertIn("Grouped policy findings", report)
        self.assertIn("UNPINNED_REVISION", report)
        self.assertIn("Receipt drilldown", report)
        self.assertIn("receipt-", report)
        self.assertIn("&quot;catalog_id&quot;", report)
        self.assertIn("&quot;implementation_hash&quot;", report)
        self.assertIn("Semantic diff and before/after", report)
        self.assertIn("<strong>Previous contract</strong>", report)
        self.assertIn("<strong>Proposed contract</strong>", report)
        self.assertIn("clinical.phi.scrub", report)
        self.assertIn("Control guardrail removed from workflow: agent.attach_receipts", report)

    def test_report_renders_memory_before_after_panels_when_payload_has_data(self) -> None:
        recorder = FlightRecorder(trace_id="trace-html-memory")
        recorder.record_memory_update(
            actor="agent-a",
            summary="Try to weaken memory guardrails.",
            before={"external_email_allowed": False, "human_review_required": True},
            after={"external_email_allowed": True, "human_review_required": False},
        )

        report = build_trace_html(recorder.trace())

        self.assertIn("Semantic diff and before/after", report)
        self.assertIn("<strong>Before</strong>", report)
        self.assertIn("<strong>After</strong>", report)
        self.assertIn("&quot;external_email_allowed&quot;: false", report)
        self.assertIn("&quot;external_email_allowed&quot;: true", report)
        self.assertIn("Memory guardrail weakened without approval", report)


if __name__ == "__main__":
    unittest.main()
