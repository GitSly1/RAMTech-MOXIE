import unittest

from moxie.evidence_quality import assess_draft
from moxie.operator_service import OperatorSubmission, OperatorService
from test_operator_service import example


class EvidenceQualityTests(unittest.TestCase):
    def test_known_citations_cover_each_line(self):
        report = assess_draft("Plant according to local soil [EV-001].\nMulch may retain moisture [EV-002].", ("EV-001", "EV-002"))
        self.assertEqual(report.status, "CITATION_COVERAGE_PRESENT")
        self.assertEqual(report.cited_segments, 2)
        self.assertEqual(report.issues, ())

    def test_uncited_and_unknown_references_flagged(self):
        report = assess_draft("Claim without citation.\nAnother claim [OTHER].", ("EV-001",))
        self.assertEqual(report.status, "REQUIRES_OPERATOR_REVIEW")
        self.assertTrue(any("line 1" in issue for issue in report.issues))
        self.assertTrue(any("unknown evidence" in issue for issue in report.issues))

    def test_verify_marker_is_not_evidence(self):
        report = assess_draft("More yield [VERIFY].", ("EV-001",))
        self.assertTrue(any("explicitly marked" in issue for issue in report.issues))

    def test_operator_service_passes_all_evidence_ids(self):
        service = OperatorService.__new__(OperatorService)
        request = example(brief_body="Soil [ev-1].\nMulch [ev-2].", extra_evidence=(("ev-2", "Notes", "Mulch"),))
        report = service.check_evidence(request)
        self.assertEqual(report.issues, ())


if __name__ == "__main__":
    unittest.main()
