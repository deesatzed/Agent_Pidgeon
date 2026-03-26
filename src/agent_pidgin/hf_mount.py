from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

Runner = Callable[..., object]


@dataclass(frozen=True)
class HfMountManager:
    binary_path: Path
    runner: Runner = subprocess.run

    def build_start_command(
        self,
        repo_id: str,
        mount_path: str,
        revision: str,
        hf_token: str | None,
    ) -> list[str]:
        command = [str(self.binary_path), "start"]
        if hf_token:
            command.extend(["--hf-token", hf_token])
        command.extend(["repo", repo_id, mount_path, "--revision", revision])
        return command

    def build_stop_command(self, mount_path: str) -> list[str]:
        return [str(self.binary_path), "stop", str(Path(mount_path).resolve())]

    def ensure_repo_mounted(
        self,
        repo_id: str,
        mount_path: str,
        revision: str,
        hf_token: str | None = None,
    ) -> dict[str, str]:
        Path(mount_path).parent.mkdir(parents=True, exist_ok=True)
        command = self.build_start_command(
            repo_id=repo_id,
            mount_path=mount_path,
            revision=revision,
            hf_token=hf_token,
        )
        result = self.runner(command, capture_output=True, text=True, timeout=30)
        if getattr(result, "returncode", 1) != 0:
            error_text = getattr(result, "stderr", "hf-mount failed") or "hf-mount failed"
            if "daemon already running" in error_text:
                return {
                    "repo_id": repo_id,
                    "mount_path": mount_path,
                    "revision": revision,
                    "status": "already-mounted",
                }
            raise RuntimeError(error_text)
        return {
            "repo_id": repo_id,
            "mount_path": mount_path,
            "revision": revision,
            "status": "mounted",
        }

    def stop_repo_mount(self, mount_path: str) -> None:
        command = self.build_stop_command(mount_path)
        result = self.runner(command, capture_output=True, text=True, timeout=30)
        if getattr(result, "returncode", 1) != 0:
            error_text = getattr(result, "stderr", "hf-mount stop failed") or "hf-mount stop failed"
            raise RuntimeError(error_text)
