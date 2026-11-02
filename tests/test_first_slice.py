"""MOX-002 acceptance and rejection-path tests (stdlib unittest)."""
import unittest

from moxie import (
    ContractError, FirstSliceWorkflow, HumanApprovalQueue,
    ResearchEvidence, TrendOpportunity, QAResult, ContentBrief,
)


class FirstSliceTests(unittest.TestCase):
    def setUp(self):
        self.opportunity = TrendOpportunity(
            "trend-001", "Useful home content", "Homeowners", "operator research"
        )
        self.evidence = ResearchEvidence(
            "evidence-001", "trend-001", "operator source", "Observed audience interest"
        )
        self.queue = HumanApprovalQueue()
        self.workflow = FirstSliceWorkflow(self.queue)

    def run_slice(self, **overrides):
        kwargs = dict(
            title="Original content brief",
            body="Produce an original, attributable guide.",
            cited_evidence_ids=["evidence-001"],
        )
        kwargs.update(overrides)
        return self.workflow.execute(self.opportunity, [self.evidence], **kwargs)

    def test_successful_end_to_end_human_queue(self):
        outcome = self.run_slice()
        self.assertEqual(outcome.qa.disposition, "accepted")
        self.assertEqual(outcome.brief.evidence_ids, ("evidence-001",))
        self.assertEqual(outcome.evidence[0].opportunity_id, "trend-001")
        self.assertEqual(outcome.approval_item.state, "pending_human_approval")
        self.assertEqual(len(self.queue.pending()), 1)

    def test_rejected_content_never_reaches_approval(self):
        outcome = self.run_slice(body=" ")
        self.assertEqual(outcome.qa.disposition, "rejected")
        self.assertIsNone(outcome.approval_item)
        self.assertEqual(self.queue.pending(), ())

    def test_missing_evidence_fails_closed(self):
        outcome = self.workflow.execute(
            self.opportunity, [], title="Draft", body="Draft", cited_evidence_ids=[]
        )
        self.assertEqual(outcome.qa.disposition, "rejected")
        self.assertEqual(self.queue.pending(), ())

    def test_cross_opportunity_evidence_fails_closed(self):
        mismatched = ResearchEvidence("evidence-001", "other-trend", "source", "finding")
        outcome = self.workflow.execute(
            self.opportunity, [mismatched], title="Draft", body="Draft",
            cited_evidence_ids=["evidence-001"],
        )
        self.assertEqual(outcome.qa.disposition, "rejected")
        self.assertTrue(any("misattributed" in reason for reason in outcome.qa.reasons))
        self.assertEqual(self.queue.pending(), ())

    def test_unknown_citation_fails_closed(self):
        outcome = self.run_slice(cited_evidence_ids=["invented-source"])
        self.assertEqual(outcome.qa.disposition, "rejected")
        self.assertEqual(self.queue.pending(), ())

    def test_queue_rejects_unapproved_direct_insertion(self):
        brief = ContentBrief("trend-001", "Draft", "Text", ("evidence-001",))
        with self.assertRaises(ContractError):
            self.queue.enqueue(brief, QAResult("rejected", ("failed QA",)))
        self.assertEqual(self.queue.pending(), ())

    def test_repeat_accepted_input_is_idempotent(self):
        first = self.run_slice()
        second = self.run_slice()
        self.assertEqual(first.approval_item, second.approval_item)
        self.assertEqual(len(self.queue.pending()), 1)

    def test_invalid_domain_contract_rejected(self):
        with self.assertRaises(ContractError):
            TrendOpportunity("", "topic", "audience", "signal")

    def test_no_publishing_surface(self):
        self.assertFalse(hasattr(self.queue, "publish"))
        self.assertFalse(hasattr(self.workflow, "publish"))


if __name__ == "__main__":
    unittest.main()
