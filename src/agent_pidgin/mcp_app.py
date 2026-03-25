from __future__ import annotations

from typing import Any

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.config import PidginConfig
from agent_pidgin.hf_mount import HfMountManager
from agent_pidgin.service import PidginReceiverService


def create_receiver_service() -> PidginReceiverService:
    config = PidginConfig.from_env()
    return PidginReceiverService(
        mount_gateway=HfMountManager(binary_path=config.hf_mount_binary),
        catalog=SeedCatalog.load_default(),
        default_mount_root=config.mount_root,
    )


def create_mcp_app() -> Any:
    try:
        from fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "fastmcp is required to run the MCP-style receiver. Install project dependencies first."
        ) from exc

    app = FastMCP("agent-pidgin-receiver")
    service = create_receiver_service()
    config = PidginConfig.from_env()

    @app.tool
    def describe_capabilities() -> dict[str, Any]:
        return {
            "receiver_id": "agent-pidgin-receiver",
            "supported_message_types": ["handshake", "resolve"],
            "supported_languages": ["python", "javascript"],
            "supported_pointers": ["str.trim", "str.lowercase", "str.ascii_only"],
            "dataset_repo": config.dataset_repo,
            "dataset_revision": config.dataset_revision,
            "artifact_defaults": {
                "artifact_kind": config.artifact_kind,
                "artifact_repo": config.artifact_repo,
                "artifact_revision": config.artifact_revision,
                "mount_root": config.mount_root,
            },
        }

    @app.tool
    def handshake_pidgin_session(payload: dict[str, Any]) -> dict[str, Any]:
        return service.handshake(payload, config=config)

    @app.tool
    def resolve_pidgin_message(payload: dict[str, Any]) -> dict[str, Any]:
        return service.resolve_message(payload)

    return app
