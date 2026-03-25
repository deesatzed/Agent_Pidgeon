from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Protocol

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.config import PidginConfig
from agent_pidgin.protocol import PidginHandshake, PidginMessage
from agent_pidgin.resolver import PidginResolver


class MountGateway(Protocol):
    def ensure_repo_mounted(
        self,
        repo_id: str,
        mount_path: str,
        revision: str,
        hf_token: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass
class PidginReceiverService:
    mount_gateway: MountGateway
    catalog: SeedCatalog
    default_mount_root: str = "/tmp/agent-pidgin"

    def handshake(self, payload: dict[str, Any], config: PidginConfig) -> dict[str, Any]:
        message = PidginHandshake.from_dict(payload)
        return {
            "message_id": message.message_id,
            "status": "ready",
            "capabilities": {
                "receiver_id": message.receiver_id,
                "supported_message_types": ["handshake", "resolve"],
                "supported_languages": ["python", "javascript"],
                "supported_pointers": list(self.catalog.concepts.keys()),
                "artifact_defaults": {
                    "artifact_kind": config.artifact_kind,
                    "artifact_repo": config.artifact_repo,
                    "artifact_revision": config.artifact_revision,
                    "mount_root": self.default_mount_root,
                },
            },
        }

    def resolve_message(
        self,
        payload: dict[str, Any],
        hf_token: str | None = None,
        config: PidginConfig | None = None,
    ) -> dict[str, Any]:
        message = PidginMessage.from_dict(payload)
        active_config = config or PidginConfig.from_env()
        effective_kind, effective_repo, effective_revision = self._effective_artifact_target(
            message,
            active_config,
        )
        mount_path = self._mount_path_for_repo(effective_repo, mount_root=active_config.mount_root)
        artifact = dict(
            self.mount_gateway.ensure_repo_mounted(
                repo_id=effective_repo,
                mount_path=mount_path,
                revision=effective_revision,
                hf_token=hf_token,
            )
        )
        artifact.setdefault("kind", effective_kind)
        resolution = PidginResolver(self.catalog).resolve_steps(
            message.steps,
            target_language=message.target_language,
        )
        return {
            "message_id": message.message_id,
            "status": "resolved",
            "artifact": artifact,
            "resolution": resolution,
        }

    def _effective_artifact_target(
        self,
        message: PidginMessage,
        config: PidginConfig,
    ) -> tuple[str, str, str]:
        if message.artifact is not None:
            return (
                message.artifact.kind or config.artifact_kind,
                message.artifact.repo,
                message.artifact.revision,
            )
        if message.dataset_repo is not None and message.dataset_revision is not None:
            return (
                config.artifact_kind,
                message.dataset_repo,
                message.dataset_revision,
            )
        return (
            config.artifact_kind,
            config.artifact_repo,
            config.artifact_revision,
        )

    def _mount_path_for_repo(self, repo_id: str, mount_root: str | None = None) -> str:
        repo_leaf = repo_id.split("/")[-1]
        return str(PurePosixPath(mount_root or self.default_mount_root) / repo_leaf)
