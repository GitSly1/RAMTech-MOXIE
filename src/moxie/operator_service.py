"""Local operator workflow and minimal, privacy-conscious activity history."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .durable_queue import DurableHumanApprovalQueue
from .first_slice import (
    ContractError,
    FirstSliceResult,
    FirstSliceWorkflow,
    ResearchEvidence,
    TrendOpportunity,
)


def default_data_directory() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".local" / "share") / "RAMTech" / "MOXIE"


@dataclass(frozen=True)
class OperatorSubmission:
    opportunity_id: str
    topic: str
    audience: str
    signal_source: str
    evidence_id: str
    evidence_source: str
    evidence_finding: str
    brief_title: str
    brief_body: str


class ActivityJournal:
    """Append an auditable event for each submission; omit draft and evidence text."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, opportunity_id: str, disposition: str, reasons: tuple[str, ...]) -> None:
        event = {
            "at_utc": datetime.now(timezone.utc).isoformat(),
            "action": "operator_submission",
            "opportunity_id": opportunity_id,
            "disposition": disposition,
            "reasons": list(reasons),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def recent(self, limit: int = 100) -> tuple[dict, ...]:
        if not self.path.exists():
            return ()
        with self.path.open("r", encoding="utf-8") as handle:
            records = [json.loads(line) for line in handle if line.strip()]
        return tuple(reversed(records[-limit:]))


class OperatorService:
    def __init__(self, directory: Path | None = None) -> None:
        root = Path(directory) if directory is not None else default_data_directory()
        root.mkdir(parents=True, exist_ok=True)
        self.queue = DurableHumanApprovalQueue(root / "approvals.sqlite3")
        self.journal = ActivityJournal(root / "activity.jsonl")
        self.workflow = FirstSliceWorkflow(self.queue)

    def submit(self, request: OperatorSubmission) -> FirstSliceResult:
        if not isinstance(request, OperatorSubmission):
            raise ContractError("invalid operator submission")
        try:
            opportunity = TrendOpportunity(
                request.opportunity_id, request.topic, request.audience, request.signal_source
            )
            evidence = ResearchEvidence(
                request.evidence_id, opportunity.opportunity_id,
                request.evidence_source, request.evidence_finding,
            )
        except ContractError as exc:
            self.journal.record(str(request.opportunity_id), "invalid", (str(exc),))
            raise
        result = self.workflow.execute(
            opportunity, [evidence], title=request.brief_title,
            body=request.brief_body, cited_evidence_ids=[evidence.evidence_id],
        )
        self.journal.record(opportunity.opportunity_id, result.qa.disposition, result.qa.reasons)
        return result

    def pending(self):
        return self.queue.pending()

    def activity(self):
        return self.journal.recent()
