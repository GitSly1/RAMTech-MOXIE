import tempfile
import unittest
from pathlib import Path

from moxie.first_slice import ContractError
from moxie.operator_service import OperatorService


class MOX008EvidenceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = OperatorService(self.root)

    def test_registered_sources_remain_unverified_until_explicit_attestation(self):
        self.service.register_evidence("demo", "ev-1", "Operator note", "field notes", "", "Soil matters")
        record = OperatorService(self.root).evidence_sources("demo")[0]
        self.assertIsNone(record["verified_by"])
        self.service.attest_evidence("demo", "ev-1", "Ariel")
        record = OperatorService(self.root).evidence_sources("demo")[0]
        self.assertEqual(record["verified_by"], "Ariel")
        self.assertTrue(record["verified_at"])
        self.assertEqual([event["disposition"] for event in self.service.activity()][:2], ["evidence_attested", "evidence_registered"])

    def test_attestation_requires_identity_and_cannot_be_repeated(self):
        self.service.register_evidence("demo", "ev-1", "Operator note", "field notes", "", "Finding")
        with self.assertRaises(ContractError):
            self.service.attest_evidence("demo", "ev-1", "")
        self.service.attest_evidence("demo", "ev-1", "Ariel")
        with self.assertRaises(ContractError):
            self.service.attest_evidence("demo", "ev-1", "Other")

    def test_source_is_immutable_and_bad_url_is_rejected(self):
        with self.assertRaises(ContractError):
            self.service.register_evidence("demo", "ev-1", "URL", "not-a-url", "2026-11-02", "Finding")
        self.assertEqual(self.service.evidence_sources("demo"), ())
        self.service.register_evidence("demo", "ev-1", "URL", "https://example.org/research", "2026-11-02", "Finding")
        with self.assertRaises(ContractError):
            self.service.register_evidence("demo", "ev-1", "URL", "https://example.org/other", "2026-11-02", "Changed")


if __name__ == "__main__":
    unittest.main()
