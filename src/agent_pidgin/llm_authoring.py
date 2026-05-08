from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.constants import PIDGIN_PROTOCOL_VERSION
from agent_pidgin.schema_validator import validate_pidgin_message

DEFAULT_OPENROUTER_MODEL = "qwen/qwen3.6-flash"
DEFAULT_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

Transport = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class OpenRouterClient:
    api_key: str
    model: str = DEFAULT_OPENROUTER_MODEL
    base_url: str = DEFAULT_OPENROUTER_URL
    timeout: int = 30

    @classmethod
    def from_env(cls, model: str | None = None) -> "OpenRouterClient":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required for LLM-assisted authoring")
        return cls(api_key=api_key, model=model or os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL))

    def complete(self, messages: list[dict[str, str]], response_format: dict[str, str] | None = None) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://agent-pidgin.local",
                "X-Title": "Agent Pidgin",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter request failed with HTTP {exc.code}: {error_body}") from exc

        return str(response_payload["choices"][0]["message"]["content"])


def draft_contract(
    description: str,
    artifact_repo: str,
    artifact_revision: str,
    artifact_kind: str = "repo",
    target_language: str = "python",
    sender_id: str = "agent-a",
    receiver_id: str = "agent-b",
    catalog: SeedCatalog | None = None,
    client: OpenRouterClient | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    active_catalog = catalog or SeedCatalog.load_default()
    proposal = _call_json_authoring(
        messages=[
            {
                "role": "system",
                "content": _authoring_system_prompt(active_catalog),
            },
            {
                "role": "user",
                "content": description,
            },
        ],
        client=client,
        transport=transport,
    )
    proposed_steps = proposal.get("steps", [])
    if not isinstance(proposed_steps, list):
        raise ValueError("LLM authoring response must include a steps list")

    accepted_steps = [step for step in proposed_steps if isinstance(step, str) and step in active_catalog.concepts]
    rejected_steps = [
        step for step in proposed_steps if not isinstance(step, str) or step not in active_catalog.concepts
    ]
    if not accepted_steps:
        raise ValueError("LLM authoring did not propose any known catalog pointers")

    contract = {
        "pidgin_version": PIDGIN_PROTOCOL_VERSION,
        "message_type": "resolve",
        "message_id": f"msg-{uuid4()}",
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "target_language": target_language,
        "artifact": {
            "kind": artifact_kind,
            "repo": artifact_repo,
            "revision": artifact_revision,
        },
        "steps": accepted_steps,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "authoring_mode": "llm_assisted",
            "model": (client.model if client else os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)),
            "llm_rationale": proposal.get("rationale", ""),
            "llm_warnings": proposal.get("warnings", []),
            "rejected_unknown_steps": rejected_steps,
        },
    }
    validate_pidgin_message(contract)
    return {
        "status": "drafted",
        "contract": contract,
        "llm_proposal": proposal,
    }


def explain_contract(
    contract: dict[str, Any],
    catalog: SeedCatalog | None = None,
    client: OpenRouterClient | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    validate_pidgin_message(contract)
    active_catalog = catalog or SeedCatalog.load_default()
    explanation = _call_text_authoring(
        messages=[
            {
                "role": "system",
                "content": _explain_system_prompt(active_catalog),
            },
            {
                "role": "user",
                "content": json.dumps(contract, indent=2),
            },
        ],
        client=client,
        transport=transport,
    )
    return {
        "status": "explained",
        "explanation": explanation,
    }


def review_contract(
    contract: dict[str, Any],
    catalog: SeedCatalog | None = None,
    client: OpenRouterClient | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    validate_pidgin_message(contract)
    active_catalog = catalog or SeedCatalog.load_default()
    review = _call_json_authoring(
        messages=[
            {
                "role": "system",
                "content": _review_system_prompt(active_catalog),
            },
            {
                "role": "user",
                "content": json.dumps(contract, indent=2),
            },
        ],
        client=client,
        transport=transport,
    )
    return {
        "status": "reviewed",
        "review": review,
    }


def _call_json_authoring(
    messages: list[dict[str, str]],
    client: OpenRouterClient | None,
    transport: Transport | None,
) -> dict[str, Any]:
    if transport is not None:
        return transport({"messages": messages})
    active_client = client or OpenRouterClient.from_env()
    content = active_client.complete(messages, response_format={"type": "json_object"})
    return _parse_json_content(content)


def _call_text_authoring(
    messages: list[dict[str, str]],
    client: OpenRouterClient | None,
    transport: Transport | None,
) -> str:
    if transport is not None:
        payload = transport({"messages": messages})
        return str(payload.get("text", payload.get("content", "")))
    active_client = client or OpenRouterClient.from_env()
    return active_client.complete(messages)


def _parse_json_content(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(content[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object")
    return parsed


def _authoring_system_prompt(catalog: SeedCatalog) -> str:
    return (
        "You draft Agent Pidgin contract steps. Return only JSON with keys steps, rationale, warnings. "
        "The steps value must be a JSON array of exact pointer strings copied from the known pointer list. "
        'Example shape: {"steps":["str.trim","agent.attach_receipts"],"rationale":"...","warnings":[]}. '
        "Use only these known pointers: "
        f"{', '.join(sorted(catalog.concepts))}. "
        "Do not invent pointer meanings. Do not include executable code. "
        "For safety-sensitive workflows, prefer receipts and human-review primitives when relevant."
    )


def _explain_system_prompt(catalog: SeedCatalog) -> str:
    return (
        "Explain an Agent Pidgin contract for a novice. Do not claim it executes code. "
        "Describe that schema, policy, trusted catalogs, catalog hashes, artifact revisions, and receipts "
        "are separate parts of the trust model. Do not call an artifact revision a catalog hash. "
        "Do not claim message_type=resolve finalizes a task; it requests semantic pointer resolution. "
        "Explain only the pointers present in the contract unless asked for broader catalog context. "
        f"Known pointers: {', '.join(sorted(catalog.concepts))}."
    )


def _review_system_prompt(catalog: SeedCatalog) -> str:
    return (
        "Review an Agent Pidgin contract. Return only JSON with keys summary, risks, suggestions. "
        "Check for missing receipt/human-review primitives and unclear safety posture. "
        "Do not recommend clinical primitives unless the contract, artifact, or user context is clinical, "
        "safety-sensitive, or likely to contain PHI. Do not invent pointer meanings. Known pointers: "
        f"{', '.join(sorted(catalog.concepts))}."
    )
