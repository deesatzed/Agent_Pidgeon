import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.config import PidginConfig
from agent_pidgin.policy import enforce_policy, has_policy_errors, load_policy
from agent_pidgin.protocol import PidginMessage
from agent_pidgin.service import PidginReceiverService


def message_payload(revision: str = "a" * 40, kind: str = "repo") -> dict:
    return {
        "pidgin_version": "0.1",
        "message_type": "resolve",
        "message_id": "msg-policy-001",
        "sender_id": "agent-a",
        "receiver_id": "agent-b",
        "target_language": "python",
        "artifact": {
            "kind": kind,
            "repo": "waynesatz/agent-pidgin-data",
            "revision": revision,
        },
        "steps": ["str.trim"],
        "created_at": "2026-03-25T10:30:00Z",
    }


class RecordingMountGateway:
    def __init__(self) -> None:
        self.calls = []

    def ensure_repo_mounted(self, repo_id: str, mount_path: str, revision: str, hf_token: str | None = None) -> dict:
        self.calls.append({"repo_id": repo_id, "mount_path": mount_path, "revision": revision})
        return {"repo_id": repo_id, "mount_path": mount_path, "revision": revision, "status": "mounted"}


class PolicyTests(unittest.TestCase):
    def test_default_policy_rejects_main_branch_revision(self) -> None:
        message = PidginMessage.from_dict(message_payload(revision="main"))

        findings = enforce_policy(message, load_policy())

        self.assertTrue(has_policy_errors(findings))
        self.assertIn("UNPINNED_REVISION", {finding.code for finding in findings})

    def test_default_policy_rejects_unknown_artifact_kind(self) -> None:
        message = PidginMessage.from_dict(message_payload(kind="unknown"))

        findings = enforce_policy(message, load_policy())

        self.assertTrue(has_policy_errors(findings))
        self.assertIn("UNKNOWN_ARTIFACT_KIND", {finding.code for finding in findings})

    def test_policy_failure_prevents_mount_and_returns_structured_response(self) -> None:
        gateway = RecordingMountGateway()
        service = PidginReceiverService(
            mount_gateway=gateway,
            catalog=SeedCatalog.load_default(),
            default_mount_root="/tmp/agent-pidgin",
        )

        result = service.resolve_message(
            message_payload(revision="main"),
            policy=load_policy(),
            config=PidginConfig(
                dataset_repo="waynesatz/agent-pidgin-data",
                dataset_revision="main",
                artifact_kind="repo",
                artifact_repo="waynesatz/agent-pidgin-data",
                artifact_revision="main",
                mount_root="/tmp/agent-pidgin",
                hf_mount_binary=Path("/tmp/hf-mount"),
                hf_token=None,
            ),
        )

        self.assertEqual(result["status"], "policy_failed")
        self.assertEqual(gateway.calls, [])
        self.assertEqual(result["resolution"]["resolved_steps"], [])
        self.assertIn("UNPINNED_REVISION", {finding["code"] for finding in result["policy_findings"]})


if __name__ == "__main__":
    unittest.main()
