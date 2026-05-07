import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]


def load_adapter_module():
    script_path = ROOT / "examples/openclaw_gateway_adapter/run_adapter.py"
    spec = importlib.util.spec_from_file_location("openclaw_gateway_adapter", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load OpenClaw gateway adapter example")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class OpenClawGatewayAdapterTests(unittest.TestCase):
    def test_adapter_preflights_four_effects_without_executing_them(self) -> None:
        module = load_adapter_module()

        result = module.run_adapter()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["execution_mode"], "preflight_only")
        self.assertEqual(len(result["verdicts"]), 4)
        self.assertTrue(all(verdict["executed"] is False for verdict in result["verdicts"]))
        self.assertEqual(
            {verdict["effect_type"]: verdict["gateway_decision"] for verdict in result["verdicts"]},
            {
                "skill_install": "blocked",
                "memory_update": "blocked",
                "external_tool_call": "requires_approval",
                "shell_command": "blocked",
            },
        )

    def test_adapter_records_a_hash_chained_trace_for_each_preflight(self) -> None:
        module = load_adapter_module()

        result = module.run_adapter()
        trace = result["trace"]

        self.assertEqual(trace["summary"]["event_count"], 5)
        self.assertEqual(
            [event["event_id"] for event in trace["events"]],
            [f"evt-{index:04d}" for index in range(1, 6)],
        )
        self.assertEqual(
            [event["event_type"] for event in trace["events"][1:]],
            [
                "agent.skill.proposed_install",
                "agent.memory.proposed_update",
                "agent.tool.proposed_call",
                "agent.shell.proposed_command",
            ],
        )
        self.assertGreaterEqual(trace["summary"]["blocked_event_count"], 2)
        self.assertIn("Agent Pidgeon Flight Recorder", result["report"])


if __name__ == "__main__":
    unittest.main()
