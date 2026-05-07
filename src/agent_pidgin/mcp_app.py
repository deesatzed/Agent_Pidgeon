from __future__ import annotations

from typing import Any

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.config import PidginConfig
from agent_pidgin.hf_mount import HfMountManager
from agent_pidgin.policy import load_policy
from agent_pidgin.service import PidginReceiverService


def create_receiver_service() -> PidginReceiverService:
    config = PidginConfig.from_env()
    return PidginReceiverService(
        mount_gateway=HfMountManager(binary_path=config.hf_mount_binary),
        catalog=SeedCatalog.from_files(config.catalog_paths) if config.catalog_paths else SeedCatalog.load_default(),
        default_mount_root=config.mount_root,
    )


def structured_tool_error(exc: Exception) -> dict[str, Any]:
    return {
        "status": "error",
        "error": {
            "type": exc.__class__.__name__,
            "message": str(exc),
        },
        "resolution": {
            "target_language": None,
            "resolved_steps": [],
            "receipts": [],
        },
        "policy_findings": [],
    }


def resolve_pidgin_message_tool(service: PidginReceiverService, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        config = PidginConfig.from_env()
        policy = load_policy(config.policy_path) if config.enforce_policy else None
        return service.resolve_message(payload, config=config, policy=policy)
    except Exception as exc:
        return structured_tool_error(exc)


def handshake_pidgin_session_tool(
    service: PidginReceiverService,
    payload: dict[str, Any],
    config: PidginConfig,
) -> dict[str, Any]:
    try:
        return service.handshake(payload, config=config)
    except Exception as exc:
        return structured_tool_error(exc)


def list_catalog_tool(catalog: SeedCatalog) -> dict[str, Any]:
    return catalog.summary()


def show_pointer_tool(catalog: SeedCatalog, pointer: str) -> dict[str, Any]:
    try:
        return {
            "status": "pointer_found",
            "concept": catalog.pointer_summary(pointer),
        }
    except Exception as exc:
        return structured_tool_error(exc)


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
            "supported_languages": service.catalog.supported_languages(),
            "supported_pointers": list(service.catalog.concepts.keys()),
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
        return handshake_pidgin_session_tool(service, payload, config)

    @app.tool
    def resolve_pidgin_message(payload: dict[str, Any]) -> dict[str, Any]:
        return resolve_pidgin_message_tool(service, payload)

    @app.tool
    def list_pidgin_catalog() -> dict[str, Any]:
        return list_catalog_tool(service.catalog)

    @app.tool
    def show_pidgin_pointer(pointer: str) -> dict[str, Any]:
        return show_pointer_tool(service.catalog, pointer)

    return app
