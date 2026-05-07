import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_pidgin.catalog_trust import (
    catalog_trust_metadata,
    load_catalog_trust_root,
    sign_catalog_hmac_sha256,
    signed_catalog_content,
    verify_catalog_hash,
    verify_catalog_hmac_signature,
    verify_catalog_trust,
    verify_catalog_trust_metadata,
)
from agent_pidgin.hash_utils import hash_catalog_content


class CatalogTrustTests(unittest.TestCase):
    def catalog(self, catalog_id: str = "core") -> dict:
        return {
            "catalog_id": catalog_id,
            "version": "0.1.0",
            "concepts": [
                {
                    "pointer": "str.trim",
                    "type_signature": "str -> str",
                    "implementations": {"python": "lambda s: s.strip()"},
                }
            ],
        }

    def trust_root(self, catalog: dict, *, key_id: str = "key-agent-pidgeon-labs-001") -> dict:
        return {
            "require_signature": True,
            "trusted_catalog_ids": [catalog["catalog_id"]],
            "trusted_key_ids": [key_id],
            "revoked_key_ids": [],
            "trusted_catalog_hashes": {
                catalog["catalog_id"]: hash_catalog_content(catalog),
            },
        }

    def finding_codes(self, result: dict) -> set[str]:
        return {finding["code"] for finding in result["findings"]}

    def test_catalog_trust_metadata_hashes_catalog_deterministically(self) -> None:
        catalog = self.catalog()

        metadata = catalog_trust_metadata(catalog, signing_key_id="key-agent-pidgeon-labs-001")

        self.assertEqual(metadata["catalog_id"], "core")
        self.assertEqual(metadata["catalog_version"], "0.1.0")
        self.assertEqual(metadata["catalog_hash"], hash_catalog_content(catalog))
        self.assertEqual(metadata["signing_key_id"], "key-agent-pidgeon-labs-001")

    def test_verify_catalog_hash_reports_match(self) -> None:
        catalog = self.catalog()
        expected_hash = hash_catalog_content(catalog)

        result = verify_catalog_hash(catalog, expected_hash)

        self.assertEqual(result["status"], "matched")
        self.assertTrue(result["matched"])
        self.assertEqual(result["actual_catalog_hash"], expected_hash)

    def test_verify_catalog_hash_reports_mismatch(self) -> None:
        catalog = self.catalog()

        result = verify_catalog_hash(catalog, "0" * 64)

        self.assertEqual(result["status"], "mismatched")
        self.assertFalse(result["matched"])
        self.assertEqual(result["expected_catalog_hash"], "0" * 64)

    def test_verify_catalog_trust_metadata_accepts_trusted_metadata_boundary_warning(self) -> None:
        catalog = self.catalog()
        trust_root = self.trust_root(catalog)
        metadata = catalog_trust_metadata(catalog, signing_key_id="key-agent-pidgeon-labs-001")

        result = verify_catalog_trust_metadata(metadata, trust_root)

        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["signature_verification"], "missing")
        self.assertEqual(self.finding_codes(result), {"SIGNATURE_CRYPTO_NOT_VERIFIED"})
        self.assertRegex(result["trust_root_hash"], r"^[a-f0-9]{64}$")

    def test_verify_catalog_trust_blocks_untrusted_catalog_id(self) -> None:
        catalog = self.catalog("unknown")
        trust_root = self.trust_root(self.catalog("core"))
        metadata = catalog_trust_metadata(catalog, signing_key_id="key-agent-pidgeon-labs-001")

        result = verify_catalog_trust_metadata(metadata, trust_root)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("UNTRUSTED_CATALOG_ID", self.finding_codes(result))

    def test_verify_catalog_trust_blocks_untrusted_signing_key(self) -> None:
        catalog = self.catalog()
        trust_root = self.trust_root(catalog)
        metadata = catalog_trust_metadata(catalog, signing_key_id="key-community-001")

        result = verify_catalog_trust_metadata(metadata, trust_root)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("UNTRUSTED_KEY_ID", self.finding_codes(result))

    def test_verify_catalog_trust_blocks_revoked_signing_key_even_when_trusted(self) -> None:
        catalog = self.catalog()
        trust_root = self.trust_root(catalog, key_id="key-rotated-out-001")
        trust_root["revoked_key_ids"] = ["key-rotated-out-001"]
        metadata = catalog_trust_metadata(catalog, signing_key_id="key-rotated-out-001")

        result = verify_catalog_trust_metadata(metadata, trust_root)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("REVOKED_KEY_ID", self.finding_codes(result))

    def test_verify_catalog_trust_blocks_missing_required_signature_metadata(self) -> None:
        catalog = self.catalog()
        trust_root = self.trust_root(catalog)

        result = verify_catalog_trust(catalog, trust_root)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("SIGNATURE_REQUIRED", self.finding_codes(result))

    def test_verify_catalog_trust_blocks_hash_mismatch(self) -> None:
        catalog = self.catalog()
        trust_root = self.trust_root(catalog)
        metadata = catalog_trust_metadata(catalog, signing_key_id="key-agent-pidgeon-labs-001")
        metadata["catalog_hash"] = "0" * 64

        result = verify_catalog_trust_metadata(metadata, trust_root)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("CATALOG_HASH_MISMATCH", self.finding_codes(result))

    def test_verify_catalog_trust_reads_key_id_from_signature_metadata(self) -> None:
        catalog = self.catalog()
        trust_root = self.trust_root(catalog)
        metadata = catalog_trust_metadata(catalog, signature={"key_id": "key-agent-pidgeon-labs-001"})

        result = verify_catalog_trust_metadata(metadata, trust_root)

        self.assertEqual(result["signing_key_id"], "key-agent-pidgeon-labs-001")
        self.assertEqual(result["status"], "approved")

    def test_hmac_signature_verifies_signed_catalog(self) -> None:
        catalog = self.catalog()
        secret = "test-hmac-secret"
        key_id = "key-agent-pidgeon-labs-001"
        signed_catalog = signed_catalog_content(catalog, key_id=key_id, secret=secret)
        trust_root = self.trust_root(catalog, key_id=key_id)
        trust_root["hmac_sha256_secrets"] = {key_id: secret}

        signature_result = verify_catalog_hmac_signature(signed_catalog, trust_root)
        trust_result = verify_catalog_trust(signed_catalog, trust_root)

        self.assertEqual(signature_result["status"], "verified")
        self.assertEqual(trust_result["status"], "approved")
        self.assertEqual(trust_result["signature_verification"], "verified")
        self.assertEqual(self.finding_codes(trust_result), {"CATALOG_TRUST_METADATA_PASSED"})

    def test_hmac_signature_blocks_tampered_catalog(self) -> None:
        catalog = self.catalog()
        secret = "test-hmac-secret"
        key_id = "key-agent-pidgeon-labs-001"
        signed_catalog = signed_catalog_content(catalog, key_id=key_id, secret=secret)
        signed_catalog["concepts"][0]["type_signature"] = "bytes -> bytes"
        trust_root = self.trust_root(catalog, key_id=key_id)
        trust_root["hmac_sha256_secrets"] = {key_id: secret}

        result = verify_catalog_trust(signed_catalog, trust_root)

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["signature_verification"], "mismatched")
        self.assertIn("CATALOG_SIGNATURE_INVALID", self.finding_codes(result))

    def test_hmac_signature_requires_configured_verification_secret(self) -> None:
        catalog = self.catalog()
        key_id = "key-agent-pidgeon-labs-001"
        metadata = catalog_trust_metadata(
            catalog,
            signature=sign_catalog_hmac_sha256(catalog, key_id=key_id, secret="test-hmac-secret"),
        )
        trust_root = self.trust_root(catalog, key_id=key_id)

        result = verify_catalog_trust_metadata(metadata, trust_root)

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["signature_verification"], "missing_key")
        self.assertIn("SIGNATURE_VERIFICATION_KEY_MISSING", self.finding_codes(result))

    def test_load_catalog_trust_root_requires_json_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trust_path = Path(tmpdir) / "catalog-trust-root.json"
            trust_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "catalog trust root must be a JSON object"):
                load_catalog_trust_root(trust_path)


if __name__ == "__main__":
    unittest.main()
