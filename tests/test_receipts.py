import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.resolver import PidginResolver


class ReceiptTests(unittest.TestCase):
    def test_each_resolved_step_includes_receipt(self) -> None:
        catalog = SeedCatalog.load_default()
        resolver = PidginResolver(catalog)

        result = resolver.resolve_steps(
            ["str.trim", "str.lowercase"],
            target_language="python",
            artifact_repo="waynesatz/agent-pidgin-data",
            artifact_revision="abc123",
        )

        self.assertEqual(len(result["resolved_steps"]), 2)
        self.assertEqual(len(result["receipts"]), 2)
        self.assertEqual(result["receipts"][0]["artifact_repo"], "waynesatz/agent-pidgin-data")
        self.assertEqual(result["receipts"][0]["artifact_revision"], "abc123")
        self.assertRegex(result["receipts"][0]["catalog_hash"], r"^[a-f0-9]{64}$")
        self.assertRegex(result["receipts"][0]["implementation_hash"], r"^[a-f0-9]{64}$")
        self.assertEqual(result["receipts"][0]["catalog_id"], "core")
        self.assertEqual(result["receipts"][0]["catalog_version"], "0.1.0")
        self.assertEqual(result["resolved_steps"][0]["catalog_id"], "core")
        self.assertRegex(result["resolved_steps"][0]["implementation_hash"], r"^[a-f0-9]{64}$")


if __name__ == "__main__":
    unittest.main()
