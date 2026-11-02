import tempfile
import unittest
from pathlib import Path

from moxie.operator_service import OperatorService
from test_operator_service import example


class MOX009ContentQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = OperatorService(Path(self.temp.name))

    def test_missing_provenance_flags_even_when_citations_exist(self):
        quality = self.service.content_quality(example(brief_body="Check soil [ev-1]."))
        self.assertEqual(quality.status, "OPERATOR_ACTION_REQUIRED")
        self.assertTrue(any("no registered source" in issue for issue in quality.issues))

    def test_attested_source_with_coverage_yields_review_ready_not_truth_claim(self):
        self.service.register_evidence("op-1", "ev-1", "Operator note", "Garden notes", "", "Soil matters")
        unverified = self.service.content_quality(example(brief_body="Check soil [ev-1]."))
        self.assertEqual(unverified.registered, 1)
        self.assertEqual(unverified.attested, 0)
        self.service.attest_evidence("op-1", "ev-1", "Ariel")
        ready = self.service.content_quality(example(brief_body="Check soil [ev-1]."))
        self.assertEqual(ready.status, "READY_FOR_HUMAN_REVIEW")
        self.assertIn("do not establish claim truth", ready.notice)

    def test_submitted_brief_retains_immutable_quality_snapshot(self):
        request = example(brief_body="Check soil [ev-1].")
        self.service.register_evidence("op-1", "ev-1", "Operator note", "Garden notes", "", "Soil matters")
        self.service.attest_evidence("op-1", "ev-1", "Ariel")
        item = self.service.submit(request).approval_item
        before = self.service.quality_snapshot(item.item_id)
        self.assertEqual(before["status"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(OperatorService(Path(self.temp.name)).quality_snapshot(item.item_id), before)
        self.service.submit(request)
        self.assertEqual(self.service.quality_snapshot(item.item_id), before)


if __name__ == "__main__":
    unittest.main()
