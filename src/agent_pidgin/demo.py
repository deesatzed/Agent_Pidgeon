from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.config import PidginConfig
from agent_pidgin.hf_mount import HfMountManager
from agent_pidgin.sender import PidginStdioSender
from agent_pidgin.service import PidginReceiverService


class LocalMountGateway:
    def ensure_repo_mounted(
        self,
        repo_id: str,
        mount_path: str,
        revision: str,
        hf_token: str | None = None,
    ) -> dict[str, Any]:
        return {
            "repo_id": repo_id,
            "mount_path": mount_path,
            "revision": revision,
            "status": "simulated-mounted",
        }


def build_demo_message() -> dict[str, Any]:
    config = PidginConfig.from_env()
    return {
        "message_id": f"msg-{uuid4()}",
        "sender_id": "agent-a",
        "receiver_id": "agent-b",
        "target_language": "python",
        "artifact": {
            "kind": config.artifact_kind,
            "repo": config.artifact_repo,
            "revision": config.artifact_revision,
        },
        "dataset_repo": config.dataset_repo,
        "dataset_revision": config.dataset_revision,
        "steps": ["str.trim", "str.lowercase", "str.ascii_only"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_local_demo(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    config = PidginConfig.from_env()
    service = PidginReceiverService(
        mount_gateway=LocalMountGateway(),
        catalog=SeedCatalog.load_default(),
        default_mount_root=config.mount_root,
    )
    return service.resolve_message(payload or build_demo_message())


async def run_stdio_demo(
    payload: dict[str, Any] | None = None,
    sender: PidginStdioSender | Any | None = None,
) -> dict[str, Any]:
    active_payload = payload or build_demo_message()
    active_sender = sender or PidginStdioSender()
    return await active_sender.send_round_trip(active_payload)


def run_real_demo(
    mount_gateway: Any | None = None,
    repo_id: str | None = None,
    revision: str | None = None,
    hf_token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = PidginConfig.from_env()
    service = PidginReceiverService(
        mount_gateway=mount_gateway or HfMountManager(binary_path=config.hf_mount_binary),
        catalog=SeedCatalog.load_default(),
        default_mount_root=config.mount_root,
    )
    payload = dict(payload or build_demo_message())
    effective_repo = repo_id or config.dataset_repo
    effective_revision = revision or config.dataset_revision
    artifact_payload = dict(payload.get("artifact") or {})
    artifact_payload["kind"] = artifact_payload.get("kind") or config.artifact_kind
    artifact_payload["repo"] = repo_id or artifact_payload.get("repo") or config.artifact_repo
    artifact_payload["revision"] = revision or artifact_payload.get("revision") or config.artifact_revision
    payload["artifact"] = artifact_payload
    payload["dataset_repo"] = effective_repo
    payload["dataset_revision"] = effective_revision
    return service.resolve_message(payload, hf_token=hf_token or config.hf_token)
