import importlib.util
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.flight_recorder import FlightRecorder, build_trace_report, validate_trace_integrity
from agent_pidgin.schema_validator import validate_pidgin_trace

ROOT = Path(__file__).resolve().parents[1]


class RecordingMountGateway:
    def __init__(self) -> None:
        self.calls = []

    def ensure_repo_mounted(self, repo_id: str, mount_path: str, revision: str, hf_token: str | None = None) -> dict:
        self.calls.append({"repo_id": repo_id, "mount_path": mount_path, "revision": revision})
        return {"repo_id": repo_id, "mount_path": mount_path, "revision": revision, "status": "mounted"}


class FlightRecorderTests(unittest.TestCase):
    def test_record_event_builds_valid_trace(self) -> None:
        recorder = FlightRecorder(trace_id="trace-test-001")

        recorder.record_event(
            event_type="agent.goal.received",
            actor="agent-a",
            summary="Receive a test goal.",
            payload={"goal": "test"},
        )
        trace = recorder.trace()

        validate_pidgin_trace(trace)
        self.assertEqual(trace["status"], "completed")
        self.assertEqual(trace["summary"]["event_count"], 1)
        self.assertEqual(trace["summary"]["integrity"], "hash_chained")
        self.assertEqual(validate_trace_integrity(trace)["status"], "valid")
        self.assertEqual(trace["events"][0]["decision"], "observed")
        self.assertIn("event_hash", trace["events"][0])

    def test_trace_integrity_detects_tampering(self) -> None:
        recorder = FlightRecorder(trace_id="trace-test-tamper")
        recorder.record_event("agent.goal.received", "agent-a", "Receive goal.", {"goal": "test"})
        trace = recorder.trace()

        trace["events"][0]["summary"] = "Tampered summary."

        result = validate_trace_integrity(trace)

        self.assertEqual(result["status"], "invalid")
        self.assertIn("event_hash mismatch", result["error"])

    def test_memory_update_blocks_unapproved_guardrail_weakening(self) -> None:
        recorder = FlightRecorder(trace_id="trace-test-memory")

        event = recorder.record_memory_update(
            actor="agent-a",
            summary="Try to weaken memory guardrails.",
            before={"external_email_allowed": False, "human_review_required": True},
            after={"external_email_allowed": True, "human_review_required": False},
        )

        self.assertEqual(event["decision"], "blocked")
        self.assertEqual(event["semantic_diff"]["risk_level"], "high")
        self.assertEqual(len(event["semantic_diff"]["risk_notes"]), 2)

    def test_memory_update_detects_required_and_may_guardrail_names(self) -> None:
        recorder = FlightRecorder(trace_id="trace-test-memory-names")

        event = recorder.record_memory_update(
            actor="agent-a",
            summary="Try to weaken named memory guardrails.",
            before={
                "human_review_required_for_external_send": True,
                "may_read_secret_paths": False,
            },
            after={
                "human_review_required_for_external_send": False,
                "may_read_secret_paths": True,
            },
        )

        self.assertEqual(event["decision"], "blocked")
        self.assertEqual(len(event["semantic_diff"]["risk_notes"]), 2)

    def test_contract_event_resolves_and_records_receipts(self) -> None:
        recorder = FlightRecorder(trace_id="trace-test-002")
        contract = json.loads(
            (ROOT / "examples/agent_flight_recorder_demo/safe_tool_contract.json").read_text(encoding="utf-8")
        )

        event = recorder.record_contract_event(
            event_type="agent.tool.proposed_call",
            actor="agent-a",
            summary="Propose safe call.",
            contract=contract,
        )

        self.assertEqual(event["decision"], "resolved")
        self.assertEqual(event["resolution_status"], "resolved")
        self.assertEqual(len(event["receipt_ids"]), 6)
        self.assertEqual(len(event["receipts"]), 6)
        self.assertEqual(event["receipts"][0]["receipt_id"], event["receipt_ids"][0])
        self.assertIn("catalog_id", event["receipts"][0])
        self.assertEqual(event["policy_findings"][0]["code"], "RAW_EXECUTION_DENIED")

    def test_contract_event_uses_injected_mount_gateway(self) -> None:
        gateway = RecordingMountGateway()
        recorder = FlightRecorder(trace_id="trace-test-gateway", mount_gateway=gateway)
        contract = json.loads(
            (ROOT / "examples/agent_flight_recorder_demo/safe_tool_contract.json").read_text(encoding="utf-8")
        )

        event = recorder.record_contract_event(
            event_type="agent.tool.proposed_call",
            actor="agent-a",
            summary="Propose safe call.",
            contract=contract,
        )

        self.assertEqual(event["decision"], "resolved")
        self.assertEqual(gateway.calls[0]["revision"], "a" * 40)

    def test_skill_install_records_blocked_manifest_event(self) -> None:
        recorder = FlightRecorder(trace_id="trace-test-skill")
        manifest = json.loads(
            (ROOT / "examples/openclaw_class/dangerous_skill_manifest.json").read_text(encoding="utf-8")
        )

        event = recorder.record_skill_install(
            actor="openclaw-gateway",
            summary="Preflight skill install.",
            manifest=manifest,
        )
        trace = recorder.trace()

        self.assertEqual(event["decision"], "blocked")
        self.assertEqual(event["event_type"], "agent.skill.proposed_install")
        self.assertEqual(event["skill_id"], "community/auto-invoice-helper")
        self.assertIn("DANGEROUS_SHELL_PERMISSION", {finding["code"] for finding in event["policy_findings"]})
        self.assertEqual(validate_trace_integrity(trace)["status"], "valid")

    def test_corrupted_contract_policy_failure_is_blocked_and_records_semantic_drift(self) -> None:
        recorder = FlightRecorder(trace_id="trace-test-003")
        safe_contract = json.loads(
            (ROOT / "examples/agent_flight_recorder_demo/safe_tool_contract.json").read_text(encoding="utf-8")
        )
        corrupted_contract = json.loads(
            (ROOT / "examples/agent_flight_recorder_demo/corrupted_tool_contract.json").read_text(encoding="utf-8")
        )

        event = recorder.record_contract_event(
            event_type="agent.tool.proposed_call",
            actor="agent-a",
            summary="Propose unsafe call.",
            contract=corrupted_contract,
            previous_contract=safe_contract,
        )
        trace = recorder.trace()

        self.assertEqual(event["decision"], "blocked")
        self.assertEqual(event["resolution_status"], "policy_failed")
        self.assertEqual(event["semantic_diff"]["risk_level"], "high")
        self.assertIn("previous_contract_hash", event)
        self.assertEqual(event["previous_contract"]["message_id"], safe_contract["message_id"])
        self.assertIn("clinical.phi.scrub", event["semantic_diff"]["removed"])
        self.assertIn("UNPINNED_REVISION", {finding["code"] for finding in event["policy_findings"]})
        self.assertEqual(trace["status"], "blocked")

    def test_high_risk_semantic_drift_blocks_even_without_policy_error(self) -> None:
        recorder = FlightRecorder(trace_id="trace-test-guardrail-drift")
        safe_contract = json.loads(
            (ROOT / "examples/agent_flight_recorder_demo/safe_tool_contract.json").read_text(encoding="utf-8")
        )
        guardrail_removed_contract = dict(safe_contract)
        guardrail_removed_contract["message_id"] = "msg-aafr-guardrail-removed"
        guardrail_removed_contract["steps"] = [
            "str.trim",
            "str.normalize_unicode",
            "clinical.phi.scrub",
            "agent.require_evidence",
        ]

        event = recorder.record_contract_event(
            event_type="agent.tool.proposed_call",
            actor="agent-a",
            summary="Propose call with review and receipt guardrails removed.",
            contract=guardrail_removed_contract,
            previous_contract=safe_contract,
        )

        self.assertEqual(event["decision"], "blocked")
        self.assertEqual(event["resolution_status"], "resolved")
        self.assertEqual(event["semantic_diff"]["risk_level"], "high")
        self.assertIn("agent.request_human_review", event["semantic_diff"]["removed"])

    def test_build_trace_report_includes_replay_decisions(self) -> None:
        recorder = FlightRecorder(trace_id="trace-test-004")
        recorder.record_event("agent.goal.received", "agent-a", "Receive goal.", {"goal": "test"})

        report = build_trace_report(recorder.trace())

        self.assertIn("Agent Pidgeon Flight Recorder", report)
        self.assertIn("evt-0001 agent.goal.received [observed]", report)
        self.assertIn("Trace hash:", report)


class FlightRecorderDemoTests(unittest.TestCase):
    def test_demo_records_corrupted_context_and_blocks_unsafe_action(self) -> None:
        run_demo = load_flight_recorder_demo()

        result = run_demo()
        trace = result["trace"]

        validate_pidgin_trace(trace)
        self.assertEqual(result["status"], "aafr_demo_completed")
        self.assertEqual(trace["status"], "blocked")
        self.assertEqual(trace["summary"]["event_count"], 6)
        self.assertEqual(trace["summary"]["blocked_event_count"], 3)
        self.assertEqual(trace["summary"]["semantic_drift_event_count"], 2)
        self.assertEqual(trace["summary"]["receipt_count"], 6)
        self.assertEqual(validate_trace_integrity(trace)["status"], "valid")
        self.assertIn("where the meaning changed", result["novice_expectations"]["why_you_want_it"])

    def test_openclaw_showpiece_records_skill_memory_and_tool_events(self) -> None:
        run_demo = load_openclaw_showpiece_demo()

        result = run_demo()
        trace = result["trace"]

        validate_pidgin_trace(trace)
        self.assertEqual(result["status"], "openclaw_showpiece_completed")
        self.assertEqual(trace["status"], "blocked")
        self.assertEqual(trace["summary"]["event_count"], 6)
        self.assertGreaterEqual(trace["summary"]["blocked_event_count"], 3)
        self.assertGreaterEqual(trace["summary"]["receipt_count"], 10)
        self.assertEqual(validate_trace_integrity(trace)["status"], "valid")
        self.assertIn("agent.skill.proposed_install", {event["event_type"] for event in trace["events"]})
        self.assertIn("OpenClaw-Class Pidgeon Sidecar Replay", result["html_report"])


def load_flight_recorder_demo():
    script_path = ROOT / "examples/agent_flight_recorder_demo/run_flight_recorder.py"
    spec = importlib.util.spec_from_file_location("flight_recorder_demo", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load flight recorder demo script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_demo


def load_openclaw_showpiece_demo():
    script_path = ROOT / "examples/openclaw_class/run_openclaw_showpiece.py"
    spec = importlib.util.spec_from_file_location("openclaw_showpiece_demo", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load OpenClaw showpiece demo script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_demo


if __name__ == "__main__":
    unittest.main()
