"""Offline CSV opportunity intake. Valid rows become drafts, never approvals."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .first_slice import ContractError
from .operator_service import OperatorService, OperatorSubmission


CSV_FIELDS = (
    "opportunity_id", "topic", "audience", "signal_source", "evidence_id",
    "evidence_source", "evidence_finding", "brief_title", "brief_body",
)


@dataclass(frozen=True)
class BatchImportReport:
    imported: int
    rejected: int
    issues: tuple[str, ...]


def import_drafts_csv(source: str | Path, service: OperatorService) -> BatchImportReport:
    """Validate header and rows, preserving existing drafts and review queue."""
    imported = 0
    rejected = 0
    issues: list[str] = []
    seen = {draft.opportunity_id for draft in service.drafts()}
    with Path(source).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ContractError("CSV must have a unique header row")
        missing = set(CSV_FIELDS) - set(reader.fieldnames)
        if missing:
            raise ContractError("CSV missing required columns: " + ", ".join(sorted(missing)))
        if set(reader.fieldnames) != set(CSV_FIELDS):
            raise ContractError("CSV has unrecognized columns")
        for line, row in enumerate(reader, start=2):
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ContractError("incorrect number of columns")
                if any(not row[field].strip() for field in CSV_FIELDS):
                    raise ContractError("required fields cannot be blank")
                request = OperatorSubmission(**{field: row[field].strip() for field in CSV_FIELDS})
                if request.opportunity_id in seen:
                    raise ContractError("duplicate or existing opportunity ID")
                service.save_draft(request)
                seen.add(request.opportunity_id)
                imported += 1
            except (ContractError, ValueError) as exc:
                rejected += 1
                reason = f"line {line}: {exc}"
                issues.append(reason)
                service.journal.record(str(row.get("opportunity_id") or ""), "csv_rejected", (reason,))
    return BatchImportReport(imported, rejected, tuple(issues))
