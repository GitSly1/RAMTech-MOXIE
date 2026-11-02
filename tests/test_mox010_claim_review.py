import tempfile
import unittest
from pathlib import Path

from moxie.first_slice import ContractError
from moxie.operator_service import OperatorService
from test_operator_service import example


class MOX010ClaimReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = OperatorService(Path(self.temp.name))

    def test_claims_extract_and_operator_decision_persists(self):
        request = example(brief_body="Soil matters [ev-1].\nOther statement without citation.")
        self.service.register_evidence("op-1", "ev-1", "Operator note", "Field notes", "", "Soil matters")
        self.service.attest_evidence("op-1", "ev-1", "Ariel")
        claims = self.service.claim_lines(request)
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0][0].cited_ids, ("ev-1",))
        self.service.review_claim(request, claims[0][0].claim_id, "supported_by_operator", "Ariel", "Matches note")
        reopened = OperatorService(Path(self.temp.name)).claim_lines(request)
        self.assertEqual(reopened[0][1]["decision"], "supported_by_operator")

    def test_uncited_or_unattested_source_cannot_be_marked_supported(self):
        request = example(brief_body="Soil matters [ev-1].\nAnother claim.")
        claims = self.service.claim_lines(request)
        with self.assertRaises(ContractError):
            self.service.review_claim(request, claims[0][0].claim_id, "supported_by_operator", "Ariel", "Reviewed")
        with self.assertRaises(ContractError):
            self.service.review_claim(request, claims[1][0].claim_id, "supported_by_operator", "Ariel", "Reviewed")
        self.service.review_claim(request, claims[1][0].claim_id, "needs_more_research", "Ariel", "Missing reference")

    def test_editing_claim_does_not_reuse_old_decision(self):
        request = example(brief_body="Soil matters [ev-1].")
        original = self.service.claim_lines(request)[0][0]
        self.service.review_claim(request, original.claim_id, "needs_more_research", "Ariel", "Needs check")
        edited = example(brief_body="Soil is important [ev-1].")
        self.assertIsNone(self.service.claim_lines(edited)[0][1])
        with self.assertRaises(ContractError):
            self.service.review_claim(edited, original.claim_id, "needs_more_research", "Ariel", "Stale")


if __name__ == "__main__":
    unittest.main()
