import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.resolver import PidginResolver


class CatalogTests(unittest.TestCase):
    def test_seed_catalog_loads_trim_and_lowercase(self) -> None:
        catalog = SeedCatalog.load_default()

        trim = catalog.get("str.trim")
        lowercase = catalog.get("str.lowercase")

        self.assertEqual(trim["pointer"], "str.trim")
        self.assertIn("python", trim["implementations"])
        self.assertEqual(lowercase["pointer"], "str.lowercase")

    def test_resolver_returns_ordered_resolution_bundle(self) -> None:
        catalog = SeedCatalog.load_default()
        resolver = PidginResolver(catalog)

        result = resolver.resolve_steps(["str.trim", "str.lowercase"], target_language="python")

        self.assertEqual(result["target_language"], "python")
        self.assertEqual(result["resolved_steps"][0]["pointer"], "str.trim")
        self.assertEqual(result["resolved_steps"][1]["pointer"], "str.lowercase")
        self.assertIn("implementation", result["resolved_steps"][0])

    def test_resolver_rejects_unknown_pointer(self) -> None:
        catalog = SeedCatalog.load_default()
        resolver = PidginResolver(catalog)

        with self.assertRaises(KeyError):
            resolver.resolve_steps(["str.unknown"], target_language="python")


if __name__ == "__main__":
    unittest.main()
