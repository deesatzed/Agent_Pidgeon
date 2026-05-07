from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from agent_pidgin.cli import contract_from_preflight_payload
from agent_pidgin.flight_recorder import FlightRecorder, build_trace_report
from agent_pidgin.html_report import build_trace_html
from agent_pidgin.schema_validator import validate_pidgin_trace
from agent_pidgin.skill_preflight import verify_skill_manifest
from agent_pidgin.telemetry import build_otlp_trace_export


class SidecarRouter:
    def handle(self, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        if method == "GET" and path == "/health":
            return HTTPStatus.OK, {
                "status": "ok",
                "service": "agent-pidgin-sidecar",
                "execution_mode": "preflight_only",
            }
        if method != "POST":
            return HTTPStatus.METHOD_NOT_ALLOWED, {"status": "error", "error": "method not allowed"}
        body = payload or {}
        try:
            if path == "/v1/preflight/skill":
                return _status_for_result(verify_skill_manifest(_manifest_from_payload(body)))
            if path == "/v1/preflight/memory":
                return _status_for_result(_preflight_memory(body))
            if path == "/v1/preflight/contract":
                return _status_for_result(_preflight_contract(body))
            if path == "/v1/render-trace":
                return HTTPStatus.OK, _render_trace(body)
        except Exception as exc:
            return HTTPStatus.BAD_REQUEST, {"status": "error", "error": str(exc)}
        return HTTPStatus.NOT_FOUND, {"status": "error", "error": "unknown endpoint"}


def create_handler(router: SidecarRouter | None = None) -> type[BaseHTTPRequestHandler]:
    active_router = router or SidecarRouter()

    class AgentPidgeonSidecarHandler(BaseHTTPRequestHandler):
        server_version = "AgentPidgeonSidecar/0.1"

        def do_GET(self) -> None:  # noqa: N802
            self._handle()

        def do_POST(self) -> None:  # noqa: N802
            self._handle()

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _handle(self) -> None:
            payload = None
            if self.command == "POST":
                payload = self._read_json()
                if payload is None:
                    self._write_json(HTTPStatus.BAD_REQUEST, {"status": "error", "error": "invalid JSON body"})
                    return
            status, response = active_router.handle(self.command, self.path.split("?", 1)[0], payload)
            self._write_json(status, response)

        def _read_json(self) -> dict[str, Any] | None:
            content_length = int(self.headers.get("content-length", "0"))
            raw_body = self.rfile.read(content_length) if content_length else b"{}"
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                return None
            return payload if isinstance(payload, dict) else None

        def _write_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(int(status))
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return AgentPidgeonSidecarHandler


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), create_handler())
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Agent Pidgeon HTTP preflight sidecar.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    run_server(host=args.host, port=args.port)


def _manifest_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = payload.get("manifest", payload)
    if not isinstance(manifest, dict):
        raise ValueError("skill preflight requires a manifest object")
    return manifest


def _preflight_memory(payload: dict[str, Any]) -> dict[str, Any]:
    before = payload.get("before", payload.get("memory_before"))
    after = payload.get("after", payload.get("memory_after"))
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("memory preflight requires object fields: before, after")
    recorder = FlightRecorder(trace_id=str(payload.get("trace_id", "trace-http-sidecar-memory")))
    event = recorder.record_memory_update(
        actor=str(payload.get("actor", "openclaw-agent")),
        summary=str(payload.get("summary", "HTTP sidecar memory preflight.")),
        before=before,
        after=after,
        approved_by=payload.get("approved_by"),
    )
    return {"status": event["decision"], "event": event, "trace": recorder.trace()}


def _preflight_contract(payload: dict[str, Any]) -> dict[str, Any]:
    contract = contract_from_preflight_payload(payload)
    previous_payload = payload.get("previous_contract")
    previous_contract = (
        contract_from_preflight_payload(previous_payload) if isinstance(previous_payload, dict) else None
    )
    recorder = FlightRecorder(trace_id=str(payload.get("trace_id", "trace-http-sidecar-contract")))
    event = recorder.record_contract_event(
        event_type=str(payload.get("event_type", "agent.tool.proposed_call")),
        actor=str(payload.get("actor", "openclaw-agent")),
        summary=str(payload.get("summary", "HTTP sidecar contract preflight.")),
        contract=contract,
        previous_contract=previous_contract,
        payload={
            "tool_name": payload.get("tool_name", ""),
            "channel": payload.get("channel", "http"),
        },
    )
    return {"status": event["decision"], "event": event, "trace": recorder.trace()}


def _render_trace(payload: dict[str, Any]) -> dict[str, Any]:
    trace = payload.get("trace")
    if not isinstance(trace, dict):
        raise ValueError("render-trace requires a trace object")
    validate_pidgin_trace(trace)
    formats = set(payload.get("formats", ["text"]))
    response: dict[str, Any] = {"status": "rendered"}
    if "text" in formats:
        response["report"] = build_trace_report(trace)
    if "html" in formats:
        response["html"] = build_trace_html(trace)
    if "otel" in formats:
        response["otel"] = build_otlp_trace_export(trace)
    return response


def _status_for_result(result: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if result.get("status") in {"blocked", "policy_failed"}:
        return HTTPStatus.CONFLICT, result
    if result.get("status") == "error":
        return HTTPStatus.BAD_REQUEST, result
    return HTTPStatus.OK, result


if __name__ == "__main__":
    main()
