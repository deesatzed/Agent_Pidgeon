import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.flight_recorder import FlightRecorder
from agent_pidgin.http_sidecar import SidecarRouter


class HttpSidecarTests(unittest.TestCase):
    def test_router_health_and_skill_preflight(self) -> None:
        router = SidecarRouter()
        health_status, health = router.handle("GET", "/health")
        blocked_status, blocked = router.handle(
            "POST",
            "/v1/preflight/skill",
            {
                "manifest": {
                    "skill_id": "community/shell-runner",
                    "name": "Shell Runner",
                    "version": "0.1.0",
                    "publisher": {"id": "community", "name": "Community"},
                    "signed": False,
                    "permissions": [{"kind": "shell", "target": "*", "access": "execute"}],
                    "capabilities": ["shell.propose_command"],
                }
            },
        )

        self.assertEqual(health_status, 200)
        self.assertEqual(health["execution_mode"], "preflight_only")
        self.assertEqual(blocked_status, 409)
        self.assertEqual(blocked["status"], "blocked")

    def test_router_preflights_memory_and_renders_trace(self) -> None:
        router = SidecarRouter()
        memory_status, memory = router.handle(
            "POST",
            "/v1/preflight/memory",
            {
                "before": {"external_email_allowed": False, "human_review_required": True},
                "after": {"external_email_allowed": True, "human_review_required": False},
            },
        )
        render_status, render = router.handle(
            "POST",
            "/v1/render-trace",
            {"trace": memory["trace"], "formats": ["text", "html", "otel"]},
        )

        self.assertEqual(memory_status, 409)
        self.assertEqual(memory["status"], "blocked")
        self.assertEqual(render_status, 200)
        self.assertIn("Agent Pidgeon Flight Recorder", render["report"])
        self.assertIn("Agent Pidgeon Trace Replay", render["html"])
        self.assertIn("resourceSpans", render["otel"])

    def test_router_preflights_contract(self) -> None:
        router = SidecarRouter()
        recorder = FlightRecorder(trace_id="trace-test-contract")
        status, result = router.handle(
            "POST",
            "/v1/preflight/contract",
            {
                "trace_id": recorder.trace_id,
                "event_type": "agent.tool.proposed_call",
                "tool_name": "email.send_customer",
                "contract": {
                    "steps": [
                        "comm.draft_external_message",
                        "comm.require_human_approval",
                        "agent.attach_receipts",
                    ],
                    "target_language": "python",
                },
            },
        )

        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["trace"]["summary"]["receipt_count"], 3)


if __name__ == "__main__":
    unittest.main()
