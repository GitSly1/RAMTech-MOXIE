import tempfile
import unittest
from pathlib import Path

from moxie.first_slice import ContractError
from moxie.operator_service import OperatorService
from test_operator_service import example


class OperatorWorkflowMOX003Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_two_evidence_records_are_cited(self):
        service = OperatorService(self.root)
        result = service.submit(example(extra_evidence=(("ev-2", "Study", "Conditions vary"),)))
        self.assertEqual(result.brief.evidence_ids, ("ev-1", "ev-2"))
        self.assertEqual(result.qa.disposition, "accepted")

    def test_draft_survives_restart_and_may_be_updated(self):
        service = OperatorService(self.root)
        service.save_draft(example(brief_body="Original"))
        service.save_draft(example(brief_body="Revised"))
        restored = OperatorService(self.root).drafts()
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0].brief_body, "Revised")

    def test_final_review_is_durable_and_not_repeatable(self):
        service = OperatorService(self.root)
        item = service.submit(example()).approval_item
        service.review(item.item_id, "approved", "Ariel", "Evidence checked")
        reopened = OperatorService(self.root)
        self.assertEqual(reopened.pending(), ())
        self.assertEqual(reopened.summary()["reviewed"], 1)
        with self.assertRaises(ContractError):
            reopened.review(item.item_id, "rejected", "Other", "Changing mind")

    def test_review_requires_known_queued_item_identity_and_reason(self):
        service = OperatorService(self.root)
        with self.assertRaises(ContractError):
            service.review("unknown", "approved", "Reviewer", "Valid")
        item = service.submit(example()).approval_item
        with self.assertRaises(ContractError):
            service.review(item.item_id, "approved", "Reviewer", "")
        self.assertEqual(len(service.pending()), 1)


if __name__ == "__main__":
    unittest.main()
