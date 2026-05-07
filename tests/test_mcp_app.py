import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.mcp_app import create_mcp_app, list_catalog_tool, resolve_pidgin_message_tool, show_pointer_tool
from agent_pidgin.service import PidginReceiverService


class NoopMountGateway:
    def ensure_repo_mounted(self, repo_id: str, mount_path: str, revision: str, hf_token: str | None = None) -> dict:
        return {"repo_id": repo_id, "mount_path": mount_path, "revision": revision, "status": "mounted"}


class McpAppTests(unittest.TestCase):
    def test_create_mcp_app_exposes_handshake_and_resolve_tools(self) -> None:
        app = create_mcp_app()

        tool_names = {tool.name for tool in asyncio.run(app.list_tools())}

        self.assertIn("describe_capabilities", tool_names)
        self.assertIn("handshake_pidgin_session", tool_names)
        self.assertIn("resolve_pidgin_message", tool_names)
        self.assertIn("list_pidgin_catalog", tool_names)
        self.assertIn("show_pidgin_pointer", tool_names)

    def test_resolve_pidgin_message_tool_returns_structured_error(self) -> None:
        service = PidginReceiverService(
            mount_gateway=NoopMountGateway(),
            catalog=SeedCatalog.load_default(),
            default_mount_root="/tmp/agent-pidgin",
        )

        result = resolve_pidgin_message_tool(service, {"message_type": "resolve"})

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["resolution"]["resolved_steps"], [])
        self.assertEqual(result["resolution"]["receipts"], [])
        self.assertEqual(result["policy_findings"], [])
        self.assertIn("message", result["error"])

    def test_catalog_tools_return_read_only_metadata(self) -> None:
        catalog = SeedCatalog.load_default()

        list_result = list_catalog_tool(catalog)
        show_result = show_pointer_tool(catalog, "str.trim")

        self.assertEqual(list_result["status"], "catalog_loaded")
        self.assertIn("str.trim", list_result["pointers"])
        self.assertEqual(show_result["status"], "pointer_found")
        self.assertNotIn("implementations", show_result["concept"])


if __name__ == "__main__":
    unittest.main()
