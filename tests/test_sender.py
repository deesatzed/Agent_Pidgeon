from pathlib import Path
import asyncio
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.demo import build_demo_message, run_stdio_demo
from agent_pidgin.sender import PidginStdioSender


class FakeClient:
    def __init__(self) -> None:
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def call_tool(self, name, arguments=None, **kwargs):
        self.calls.append((name, arguments or {}))
        if name == "handshake_pidgin_session":
            return {
                "message_id": arguments["payload"]["message_id"],
                "status": "ready",
                "capabilities": {"supported_message_types": ["handshake", "resolve"]},
            }
        if name == "resolve_pidgin_message":
            return {
                "message_id": arguments["payload"]["message_id"],
                "status": "resolved",
            }
        raise AssertionError(f"Unexpected tool call: {name}")


class SenderTests(unittest.TestCase):
    def test_stdio_sender_performs_handshake_then_resolve(self) -> None:
        fake_client = FakeClient()
        sender = PidginStdioSender(client_factory=lambda: fake_client)
        payload = build_demo_message()

        result = asyncio.run(sender.send_round_trip(payload))

        self.assertEqual(fake_client.calls[0][0], "handshake_pidgin_session")
        self.assertEqual(fake_client.calls[1][0], "resolve_pidgin_message")
        self.assertEqual(result["handshake"]["status"], "ready")
        self.assertEqual(result["result"]["message_id"], payload["message_id"])

    def test_stdio_sender_normalizes_structured_tool_results(self) -> None:
        class FakeClientWithStructuredResults(FakeClient):
            async def call_tool(self, name, arguments=None, **kwargs):
                self.calls.append((name, arguments or {}))
                return SimpleNamespace(data={
                    "message_id": arguments["payload"]["message_id"],
                    "status": "ready" if name == "handshake_pidgin_session" else "resolved",
                })

        fake_client = FakeClientWithStructuredResults()
        sender = PidginStdioSender(client_factory=lambda: fake_client)
        payload = build_demo_message()

        result = asyncio.run(sender.send_round_trip(payload))

        self.assertEqual(result["handshake"]["message_id"], payload["message_id"])
        self.assertEqual(result["result"]["status"], "resolved")

    def test_run_stdio_demo_returns_handshake_and_result(self) -> None:
        payload = build_demo_message()

        class FakeSender:
            async def send_round_trip(self, payload):
                return {
                    "handshake": {"status": "ready"},
                    "result": {"message_id": payload["message_id"], "status": "resolved"},
                }

        result = asyncio.run(run_stdio_demo(payload=payload, sender=FakeSender()))

        self.assertEqual(result["handshake"]["status"], "ready")
        self.assertEqual(result["result"]["message_id"], payload["message_id"])


if __name__ == "__main__":
    unittest.main()
