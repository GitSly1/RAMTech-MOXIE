"""Focused persistence and fail-closed behavior tests."""
import tempfile
import unittest
from pathlib import Path

from moxie import (
    ContentBrief, ContractError, DurableHumanApprovalQueue, FirstSliceWorkflow,
    QAResult, ResearchEvidence, TrendOpportunity,
)


class DurableQueueTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary.name) / "approvals.sqlite3"
        self.opportunity = TrendOpportunity("trend-001", "Topic", "Audience", "Signal")
        self.evidence = ResearchEvidence("e-001", "trend-001", "Source", "Finding")

    def tearDown(self):
        self.temporary.cleanup()

    def _execute(self, queue, body="An evidence-grounded draft"):
        return FirstSliceWorkflow(queue).execute(
            self.opportunity,
            [self.evidence],
            title="Content title",
            body=body,
            cited_evidence_ids=["e-001"],
        )

    def test_accepted_item_survives_new_queue_instance(self):
        first_queue = DurableHumanApprovalQueue(self.database_path)
        accepted = self._execute(first_queue)
        restarted = DurableHumanApprovalQueue(self.database_path)
        self.assertEqual(restarted.pending(), (accepted.approval_item,))

    def test_rejected_item_never_persisted(self):
        queue = DurableHumanApprovalQueue(self.database_path)
        result = self._execute(queue, body=" ")
        self.assertEqual(result.qa.disposition, "rejected")
        self.assertEqual(DurableHumanApprovalQueue(self.database_path).pending(), ())

    def test_repeat_submission_is_idempotent_across_restarts(self):
        first = self._execute(DurableHumanApprovalQueue(self.database_path))
        second = self._execute(DurableHumanApprovalQueue(self.database_path))
        self.assertEqual(first.approval_item, second.approval_item)
        self.assertEqual(len(DurableHumanApprovalQueue(self.database_path).pending()), 1)

    def test_direct_rejected_submission_is_refused(self):
        queue = DurableHumanApprovalQueue(self.database_path)
        brief = ContentBrief("trend-001", "Title", "Text", ("e-001",))
        with self.assertRaises(ContractError):
            queue.enqueue(brief, QAResult("rejected", ("invalid",)))
        self.assertEqual(queue.pending(), ())


if __name__ == "__main__":
    unittest.main()
