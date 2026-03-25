from pathlib import Path
import asyncio
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.mcp_app import create_mcp_app


class McpAppTests(unittest.TestCase):
    def test_create_mcp_app_exposes_handshake_and_resolve_tools(self) -> None:
        app = create_mcp_app()

        tool_names = {tool.name for tool in asyncio.run(app.list_tools())}

        self.assertIn("describe_capabilities", tool_names)
        self.assertIn("handshake_pidgin_session", tool_names)
        self.assertIn("resolve_pidgin_message", tool_names)


if __name__ == "__main__":
    unittest.main()
