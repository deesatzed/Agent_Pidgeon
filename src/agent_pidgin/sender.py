from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


class PidginStdioSender:
    def __init__(self, client_factory: Callable[[], Any] | None = None) -> None:
        self.client_factory = client_factory or self._build_default_client

    def _normalize_tool_result(self, result: Any) -> Any:
        if isinstance(result, dict):
            return result
        if getattr(result, "data", None) is not None:
            return result.data
        if getattr(result, "structured_content", None) is not None:
            return result.structured_content
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result

    def _build_default_client(self) -> Any:
        from fastmcp import Client

        receiver_script = Path(__file__).resolve().parents[2] / "servers/pidgin_receiver.py"
        return Client(receiver_script)

    async def send_round_trip(self, payload: dict[str, Any]) -> dict[str, Any]:
        handshake_payload = {
            "message_type": "handshake",
            "message_id": str(payload["message_id"]),
            "sender_id": str(payload["sender_id"]),
            "receiver_id": str(payload["receiver_id"]),
            "created_at": str(payload["created_at"]),
        }
        async with self.client_factory() as client:
            handshake = self._normalize_tool_result(
                await client.call_tool("handshake_pidgin_session", {"payload": handshake_payload})
            )
            result = self._normalize_tool_result(await client.call_tool("resolve_pidgin_message", {"payload": payload}))
        return {
            "handshake": handshake,
            "result": result,
        }
