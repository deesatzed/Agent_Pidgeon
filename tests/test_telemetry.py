import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.flight_recorder import FlightRecorder
from agent_pidgin.telemetry import build_otlp_trace_export


def attr_map(attributes: list[dict]) -> dict[str, dict]:
    return {attribute["key"]: attribute["value"] for attribute in attributes}


class TelemetryTests(unittest.TestCase):
    def test_build_otlp_trace_export_maps_events_to_spans(self) -> None:
        recorder = FlightRecorder(trace_id="trace-otel")
        recorder.record_event("agent.goal.received", "agent-a", "Receive goal.", {"goal": "test"})
        recorder.record_event("agent.tool.proposed_call", "agent-a", "Blocked send.", decision="blocked")

        export = build_otlp_trace_export(recorder.trace())

        resource_span = export["resourceSpans"][0]
        resource_attrs = attr_map(resource_span["resource"]["attributes"])
        spans = resource_span["scopeSpans"][0]["spans"]
        first_attrs = attr_map(spans[0]["attributes"])
        second_attrs = attr_map(spans[1]["attributes"])
        self.assertEqual(resource_attrs["service.name"]["stringValue"], "agent-pidgin")
        self.assertEqual(resource_attrs["pidgeon.blocked_event_count"]["intValue"], "1")
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0]["name"], "agent.goal.received")
        self.assertEqual(spans[1]["status"]["message"], "blocked")
        self.assertEqual(first_attrs["pidgeon.event_id"]["stringValue"], "evt-0001")
        self.assertEqual(second_attrs["pidgeon.blocked"]["boolValue"], True)


if __name__ == "__main__":
    unittest.main()
