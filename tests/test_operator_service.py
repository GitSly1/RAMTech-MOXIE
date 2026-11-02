"""Headless acceptance tests for the operator-facing service boundary."""

import tempfile
import unittest
from pathlib import Path

from moxie.first_slice import ContractError
from moxie.operator_service import OperatorService, OperatorSubmission


def example(**overrides):
    data = dict(
        opportunity_id="op-1", topic="Gardening", audience="Home gardeners",
        signal_source="Operator", evidence_id="ev-1", evidence_source="Field note",
        evidence_finding="Soil conditions matter", brief_title="Garden planning",
        brief_body="Check conditions before planting.",
    )
    data.update(overrides)
    return OperatorSubmission(**data)


class OperatorServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_accepted_submission_durable_and_logged(self):
        first = OperatorService(self.root)
        result = first.submit(example())
        self.assertEqual(result.qa.disposition, "accepted")
        reopened = OperatorService(self.root)
        self.assertEqual(len(reopened.pending()), 1)
        self.assertEqual(reopened.activity()[0]["disposition"], "accepted")
        self.assertNotIn("Check conditions", (self.root / "activity.jsonl").read_text())

    def test_repeat_is_idempotent_but_actions_recorded(self):
        service = OperatorService(self.root)
        service.submit(example())
        service.submit(example())
        self.assertEqual(len(service.pending()), 1)
        self.assertEqual(len(service.activity()), 2)

    def test_rejected_brief_never_queued(self):
        service = OperatorService(self.root)
        result = service.submit(example(brief_title=""))
        self.assertEqual(result.qa.disposition, "rejected")
        self.assertEqual(service.pending(), ())
        self.assertEqual(service.activity()[0]["disposition"], "rejected")

    def test_invalid_domain_logged_and_not_queued(self):
        service = OperatorService(self.root)
        with self.assertRaises(ContractError):
            service.submit(example(evidence_source=""))
        self.assertEqual(service.pending(), ())
        self.assertEqual(service.activity()[0]["disposition"], "invalid")


if __name__ == "__main__":
    unittest.main()
