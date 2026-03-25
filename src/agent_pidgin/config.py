from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PidginConfig:
    dataset_repo: str
    dataset_revision: str
    artifact_kind: str
    artifact_repo: str
    artifact_revision: str
    mount_root: str
    hf_mount_binary: Path
    hf_token: str | None

    @classmethod
    def from_env(cls) -> "PidginConfig":
        dataset_repo = os.environ.get("AGENT_PIDGIN_DATA_REPO", "waynesatz/agent-pidgin-data")
        dataset_revision = os.environ.get("AGENT_PIDGIN_DATA_REVISION", "main")
        return cls(
            dataset_repo=dataset_repo,
            dataset_revision=dataset_revision,
            artifact_kind=os.environ.get("AGENT_PIDGIN_ARTIFACT_KIND", "repo"),
            artifact_repo=os.environ.get("AGENT_PIDGIN_ARTIFACT_REPO", dataset_repo),
            artifact_revision=os.environ.get("AGENT_PIDGIN_ARTIFACT_REVISION", dataset_revision),
            mount_root=os.environ.get("AGENT_PIDGIN_MOUNT_ROOT", "/tmp/agent-pidgin"),
            hf_mount_binary=Path(os.environ.get("HF_MOUNT_BINARY", str(Path.home() / ".local/bin/hf-mount"))),
            hf_token=os.environ.get("HF_TOKEN") or None,
        )
