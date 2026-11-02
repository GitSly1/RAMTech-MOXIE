import csv
import tempfile
import unittest
from pathlib import Path

from moxie.batch_import import CSV_FIELDS, import_drafts_csv
from moxie.first_slice import ContractError
from moxie.operator_service import OperatorService


class BatchImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = OperatorService(self.root)
        self.source = self.root / "drafts.csv"

    def write_rows(self, rows, headers=CSV_FIELDS):
        with self.source.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def row(identifier="op-1"):
        return dict(opportunity_id=identifier, topic="Gardening", audience="Growers",
                    signal_source="Operator", evidence_id="ev-1", evidence_source="Local note",
                    evidence_finding="Soil matters", brief_title="Garden", brief_body="Draft body")

    def test_import_is_durable_drafts_only(self):
        self.write_rows([self.row("op-1"), self.row("op-2")])
        report = import_drafts_csv(self.source, self.service)
        self.assertEqual((report.imported, report.rejected), (2, 0))
        reopened = OperatorService(self.root)
        self.assertEqual(len(reopened.drafts()), 2)
        self.assertEqual(reopened.pending(), ())

    def test_invalid_rows_and_duplicates_are_rejected_without_overwrite(self):
        bad = self.row("op-2")
        bad["evidence_source"] = ""
        self.write_rows([self.row("op-1"), self.row("op-1"), bad])
        report = import_drafts_csv(self.source, self.service)
        self.assertEqual((report.imported, report.rejected), (1, 2))
        self.assertEqual(len(self.service.drafts()), 1)
        self.assertEqual(len(self.service.activity()), 3)

    def test_schema_mismatch_fails_before_writing(self):
        self.write_rows([{key: value for key, value in self.row().items() if key != "brief_body"}], headers=CSV_FIELDS[:-1])
        with self.assertRaises(ContractError):
            import_drafts_csv(self.source, self.service)
        self.assertEqual(self.service.drafts(), ())

    def test_existing_draft_is_not_overwritten(self):
        self.write_rows([self.row("op-1")])
        import_drafts_csv(self.source, self.service)
        report = import_drafts_csv(self.source, self.service)
        self.assertEqual((report.imported, report.rejected), (0, 1))


if __name__ == "__main__":
    unittest.main()
