"""Consolidated local quality status; provenance is not semantic fact verification."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .evidence_quality import assess_draft


@dataclass(frozen=True)
class ContentQuality:
    status: str
    opportunity_id: str
    issues: tuple[str, ...]
    citation_lines: int
    total_lines: int
    registered: int
    attested: int
    checked_at: str
    notice: str = "Operator attestation and matching citations do not establish claim truth or source entailment."

    def as_record(self) -> dict:
        return asdict(self)


def consolidate(request, sources: tuple[dict, ...]) -> ContentQuality:
    ids = (request.evidence_id,) + tuple(row[0] for row in request.extra_evidence)
    coverage = assess_draft(request.brief_body, ids)
    registered = {source["evidence_id"]: source for source in sources}
    issues = list(coverage.issues)
    valid_sources = 0
    attested = 0
    for identifier in dict.fromkeys(ids):
        entry = registered.get(identifier)
        if entry is None:
            issues.append(f"[{identifier}] has no registered source")
            continue
        valid_sources += 1
        if not entry["verified_by"]:
            issues.append(f"[{identifier}] is registered but lacks operator attestation")
        else:
            attested += 1
    return ContentQuality(
        status="OPERATOR_ACTION_REQUIRED" if issues else "READY_FOR_HUMAN_REVIEW",
        opportunity_id=request.opportunity_id,
        issues=tuple(issues), citation_lines=coverage.cited_segments,
        total_lines=coverage.checked_segments, registered=valid_sources,
        attested=attested, checked_at=datetime.now(timezone.utc).isoformat(),
    )
