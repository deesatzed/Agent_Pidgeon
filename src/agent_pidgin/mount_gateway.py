from __future__ import annotations

from typing import Any

from agent_pidgin.config import PidginConfig
from agent_pidgin.hf_mount import HfMountManager


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


def build_mount_gateway(config: PidginConfig, mode: str = "simulated") -> HfMountManager | LocalMountGateway:
    if mode == "simulated":
        return LocalMountGateway()
    if mode == "hf":
        return HfMountManager(binary_path=config.hf_mount_binary)
    if mode == "auto":
        if config.hf_mount_binary.exists():
            return HfMountManager(binary_path=config.hf_mount_binary)
        return LocalMountGateway()
    raise ValueError(f"unsupported mount gateway mode: {mode}")
