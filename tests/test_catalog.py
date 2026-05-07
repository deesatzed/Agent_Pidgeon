import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.hash_utils import hash_catalog_content
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
        self.assertEqual(result["receipts"][0]["pointer"], "str.trim")
        self.assertEqual(result["receipts"][0]["target_language"], "python")

    def test_resolver_rejects_unknown_pointer(self) -> None:
        catalog = SeedCatalog.load_default()
        resolver = PidginResolver(catalog)

        with self.assertRaises(KeyError):
            resolver.resolve_steps(["str.unknown"], target_language="python")

    def test_catalog_hash_is_stable_for_reordered_keys(self) -> None:
        left = {"b": 2, "a": {"d": 4, "c": 3}}
        right = {"a": {"c": 3, "d": 4}, "b": 2}

        self.assertEqual(hash_catalog_content(left), hash_catalog_content(right))

    def test_catalog_loader_detects_duplicate_pointers(self) -> None:
        catalog_one = {
            "catalog_id": "one",
            "version": "0.1.0",
            "concepts": [
                {
                    "pointer": "str.trim",
                    "type_signature": "str -> str",
                    "implementations": {"python": "lambda s: s.strip()"},
                }
            ],
        }
        catalog_two = {
            "catalog_id": "two",
            "version": "0.1.0",
            "concepts": [
                {
                    "pointer": "str.trim",
                    "type_signature": "str -> str",
                    "implementations": {"python": "lambda s: s.strip()"},
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            left = Path(tmpdir) / "left.json"
            right = Path(tmpdir) / "right.json"
            left.write_text(json.dumps(catalog_one), encoding="utf-8")
            right.write_text(json.dumps(catalog_two), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate catalog pointer"):
                SeedCatalog.from_files([left, right])

    def test_catalog_summary_exposes_sources_and_pointers(self) -> None:
        catalog = SeedCatalog.load_default()

        summary = catalog.summary()

        self.assertEqual(summary["status"], "catalog_loaded")
        self.assertRegex(summary["catalog_hash"], r"^[a-f0-9]{64}$")
        self.assertIn("str.trim", summary["pointers"])
        self.assertIn("python", summary["supported_languages"])
        self.assertGreaterEqual(summary["concept_count"], 3)

    def test_pointer_summary_omits_implementation_strings(self) -> None:
        catalog = SeedCatalog.load_default()

        summary = catalog.pointer_summary("str.trim")

        self.assertEqual(summary["pointer"], "str.trim")
        self.assertEqual(summary["type_signature"], "str -> str")
        self.assertIn("python", summary["supported_languages"])
        self.assertRegex(summary["implementation_hashes"]["python"], r"^[a-f0-9]{64}$")
        self.assertNotIn("implementations", summary)


if __name__ == "__main__":
    unittest.main()
