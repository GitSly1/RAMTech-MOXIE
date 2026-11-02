"""Local operator workflow and minimal, privacy-conscious activity history."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .durable_queue import DurableHumanApprovalQueue
from .evidence_quality import EvidenceQualityReport, assess_draft
from .evidence_registry import EvidenceRegistry
from .operator_store import OperatorStore
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
    extra_evidence: tuple[tuple[str, str, str], ...] = ()


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
        self.store = OperatorStore(root / "operator.sqlite3")
        self.registry = EvidenceRegistry(root / "evidence.sqlite3")
        self.journal = ActivityJournal(root / "activity.jsonl")
        self.workflow = FirstSliceWorkflow(self.queue)

    def submit(self, request: OperatorSubmission) -> FirstSliceResult:
        if not isinstance(request, OperatorSubmission):
            raise ContractError("invalid operator submission")
        try:
            opportunity = TrendOpportunity(
                request.opportunity_id, request.topic, request.audience, request.signal_source
            )
            evidence = [ResearchEvidence(
                request.evidence_id, opportunity.opportunity_id,
                request.evidence_source, request.evidence_finding,
            )]
            evidence.extend(
                ResearchEvidence(identifier, opportunity.opportunity_id, source, finding)
                for identifier, source, finding in request.extra_evidence
            )
        except ContractError as exc:
            self.journal.record(str(request.opportunity_id), "invalid", (str(exc),))
            raise
        result = self.workflow.execute(
            opportunity, evidence, title=request.brief_title,
            body=request.brief_body, cited_evidence_ids=[item.evidence_id for item in evidence],
        )
        self.journal.record(opportunity.opportunity_id, result.qa.disposition, result.qa.reasons)
        return result

    def pending(self):
        decisions = self.store.decisions()
        return tuple(item for item in self.queue.pending() if item.item_id not in decisions)

    def save_draft(self, request: OperatorSubmission) -> None:
        if not isinstance(request, OperatorSubmission):
            raise ContractError("invalid operator draft")
        self.store.save_draft(request)
        self.journal.record(request.opportunity_id, "draft_saved", ())

    def drafts(self) -> tuple[OperatorSubmission, ...]:
        return tuple(
            OperatorSubmission(**{**row, "extra_evidence": tuple(tuple(x) for x in row.get("extra_evidence", ()))})
            for row in self.store.drafts()
        )

    def draft_versions(self, opportunity_id: str) -> tuple[dict, ...]:
        return self.store.draft_versions(opportunity_id)

    def review(self, item_id: str, decision: str, reviewer: str, reason: str) -> None:
        valid = {item.item_id for item in self.queue.pending()}
        self.store.decide(item_id, decision, reviewer, reason, valid)
        self.journal.record(item_id, "human_" + decision, ("reviewer: " + reviewer.strip(), "reason: " + reason.strip()))

    def summary(self) -> dict[str, int]:
        return {"drafts": len(self.drafts()), "awaiting_review": len(self.pending()), "reviewed": len(self.store.decisions())}

    def check_evidence(self, request: OperatorSubmission) -> EvidenceQualityReport:
        ids = (request.evidence_id,) + tuple(row[0] for row in request.extra_evidence)
        return assess_draft(request.brief_body, ids)

    def register_evidence(self, opportunity_id: str, evidence_id: str, source_type: str,
                          source_ref: str, publication_date: str, excerpt: str) -> None:
        self.registry.register(opportunity_id, evidence_id, source_type, source_ref, publication_date, excerpt)
        self.journal.record(opportunity_id, "evidence_registered", ("evidence: " + evidence_id,))

    def attest_evidence(self, opportunity_id: str, evidence_id: str, reviewer: str) -> None:
        self.registry.verify(opportunity_id, evidence_id, reviewer)
        self.journal.record(opportunity_id, "evidence_attested", ("evidence: " + evidence_id, "operator: " + reviewer.strip()))

    def evidence_sources(self, opportunity_id: str) -> tuple[dict, ...]:
        return self.registry.list(opportunity_id)

    def reviewed(self) -> tuple[dict, ...]:
        decisions = self.store.decisions()
        queued = {item.item_id: item for item in self.queue.pending()}
        return tuple(
            {**decision, "brief": queued[item_id].brief}
            for item_id, decision in decisions.items() if item_id in queued
        )

    def activity(self):
        return self.journal.recent()
