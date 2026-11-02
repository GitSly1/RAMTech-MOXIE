"""MOX-002 deterministic headless flow. No network, publishing, or credentials."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal, Sequence


class ContractError(ValueError):
    """Invalid domain input or unauthorized queue transition."""


def required(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be nonempty text")
    return value.strip()


@dataclass(frozen=True)
class TrendOpportunity:
    opportunity_id: str
    topic: str
    audience: str
    signal_source: str

    def __post_init__(self) -> None:
        for field in ("opportunity_id", "topic", "audience", "signal_source"):
            object.__setattr__(self, field, required(getattr(self, field), field))


@dataclass(frozen=True)
class ResearchEvidence:
    evidence_id: str
    opportunity_id: str
    source: str
    finding: str

    def __post_init__(self) -> None:
        for field in ("evidence_id", "opportunity_id", "source", "finding"):
            object.__setattr__(self, field, required(getattr(self, field), field))


@dataclass(frozen=True)
class ContentBrief:
    opportunity_id: str
    title: str
    body: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class QAResult:
    disposition: Literal["accepted", "rejected"]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ApprovalItem:
    item_id: str
    brief: ContentBrief
    qa: QAResult
    state: Literal["pending_human_approval"] = "pending_human_approval"


@dataclass(frozen=True)
class FirstSliceResult:
    opportunity: TrendOpportunity
    evidence: tuple[ResearchEvidence, ...]
    brief: ContentBrief
    qa: QAResult
    approval_item: ApprovalItem | None


class HumanApprovalQueue:
    """Append-only in-memory review queue; deliberately no publishing action."""

    def __init__(self) -> None:
        self._items: dict[str, ApprovalItem] = {}

    def enqueue(self, brief: ContentBrief, qa: QAResult) -> ApprovalItem:
        if qa.disposition != "accepted" or qa.reasons:
            raise ContractError("only QA-accepted briefs may enter human approval")
        identity = (brief.opportunity_id, brief.title, brief.body, brief.evidence_ids)
        digest = sha256(repr(identity).encode("utf-8")).hexdigest()[:16]
        item_id = f"{brief.opportunity_id}:{digest}"
        prior = self._items.get(item_id)
        if prior is not None:
            if prior.brief != brief:
                raise ContractError("approval identity collision")
            return prior
        item = ApprovalItem(item_id, brief, qa)
        self._items[item_id] = item
        return item

    def pending(self) -> tuple[ApprovalItem, ...]:
        return tuple(self._items.values())


class FirstSliceWorkflow:
    """Research evidence -> content brief -> deterministic QA -> human queue."""

    def __init__(self, queue: HumanApprovalQueue | None = None) -> None:
        self.queue = queue if queue is not None else HumanApprovalQueue()

    def execute(
        self,
        opportunity: TrendOpportunity,
        evidence: Sequence[ResearchEvidence],
        *,
        title: str,
        body: str,
        cited_evidence_ids: Sequence[str],
    ) -> FirstSliceResult:
        if not isinstance(opportunity, TrendOpportunity):
            raise ContractError("invalid opportunity contract")
        if not isinstance(evidence, (tuple, list)) or not all(
            isinstance(item, ResearchEvidence) for item in evidence
        ):
            raise ContractError("invalid research evidence contract")
        if not isinstance(cited_evidence_ids, (tuple, list)) or not all(
            isinstance(item, str) for item in cited_evidence_ids
        ):
            raise ContractError("invalid citation contract")

        research = tuple(evidence)
        citations = tuple(cited_evidence_ids)
        brief = ContentBrief(
            opportunity.opportunity_id,
            title if isinstance(title, str) else "",
            body if isinstance(body, str) else "",
            citations,
        )
        reasons: list[str] = []
        if not brief.title.strip():
            reasons.append("empty content title")
        if not brief.body.strip():
            reasons.append("empty content body")
        if not research:
            reasons.append("missing research evidence")
        if not citations:
            reasons.append("missing evidence citations")
        evidence_by_id: dict[str, ResearchEvidence] = {}
        for item in research:
            if item.evidence_id in evidence_by_id:
                reasons.append(f"duplicate evidence identifier: {item.evidence_id}")
            evidence_by_id[item.evidence_id] = item
            if item.opportunity_id != opportunity.opportunity_id:
                reasons.append(f"misattributed evidence: {item.evidence_id}")
        if len(set(citations)) != len(citations):
            reasons.append("duplicate evidence citations")
        for citation in citations:
            item = evidence_by_id.get(citation)
            if item is None:
                reasons.append(f"unverified citation: {citation}")
            elif item.opportunity_id != opportunity.opportunity_id:
                reasons.append(f"misattributed citation: {citation}")
        qa = QAResult("rejected" if reasons else "accepted", tuple(dict.fromkeys(reasons)))
        approval = self.queue.enqueue(brief, qa) if qa.disposition == "accepted" else None
        return FirstSliceResult(opportunity, research, brief, qa, approval)
