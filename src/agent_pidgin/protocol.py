from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PidginArtifactTarget:
    kind: str | None
    repo: str
    revision: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PidginArtifactTarget":
        required_fields = ["repo", "revision"]
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise ValueError(f"Missing required artifact fields: {', '.join(missing)}")
        return cls(
            kind=str(payload["kind"]) if "kind" in payload and payload["kind"] is not None else None,
            repo=str(payload["repo"]),
            revision=str(payload["revision"]),
        )


@dataclass(frozen=True)
class PidginHandshake:
    message_type: str
    message_id: str
    sender_id: str
    receiver_id: str
    created_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PidginHandshake":
        required_fields = ["message_type", "message_id", "sender_id", "receiver_id", "created_at"]
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        if str(payload["message_type"]) != "handshake":
            raise ValueError("message_type must be handshake")
        return cls(
            message_type="handshake",
            message_id=str(payload["message_id"]),
            sender_id=str(payload["sender_id"]),
            receiver_id=str(payload["receiver_id"]),
            created_at=str(payload["created_at"]),
        )


@dataclass(frozen=True)
class PidginMessage:
    message_type: str
    message_id: str
    sender_id: str
    receiver_id: str
    target_language: str
    dataset_repo: str | None
    dataset_revision: str | None
    artifact: PidginArtifactTarget | None
    steps: list[str]
    created_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PidginMessage":
        message_type = str(payload.get("message_type", "resolve"))
        if message_type != "resolve":
            raise ValueError("message_type must be resolve")

        required_fields = [
            "message_id",
            "sender_id",
            "receiver_id",
            "target_language",
            "steps",
            "created_at",
        ]
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        steps = payload["steps"]
        if not isinstance(steps, list) or not steps or not all(isinstance(step, str) and step for step in steps):
            raise ValueError("steps must be a non-empty list of pointer strings")

        artifact_payload = payload.get("artifact")
        artifact = None
        if artifact_payload is not None:
            if not isinstance(artifact_payload, dict):
                raise ValueError("artifact must be an object when provided")
            artifact = PidginArtifactTarget.from_dict(artifact_payload)

        return cls(
            message_type=message_type,
            message_id=str(payload["message_id"]),
            sender_id=str(payload["sender_id"]),
            receiver_id=str(payload["receiver_id"]),
            target_language=str(payload["target_language"]),
            dataset_repo=str(payload["dataset_repo"]) if payload.get("dataset_repo") is not None else None,
            dataset_revision=str(payload["dataset_revision"]) if payload.get("dataset_revision") is not None else None,
            artifact=artifact,
            steps=steps,
            created_at=str(payload["created_at"]),
        )
