"""Deterministic trend intake and evidence generation; no external side effects.

Only caller-supplied evidence is accepted. The module never retrieves, invents,
publishes, or purchases anything. Its immutable records are JSON serializable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True)
class TrendOpportunity:
    opportunity_id: str
    topic: str
    audience: str
    platform: str
    observed_at: str
    signals: tuple[str, ...]
    source_refs: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "TrendOpportunity":
        if not isinstance(value, dict):
            raise ValueError("trend opportunity must be an object")
        expected = set(cls.__dataclass_fields__)
        if set(value) != expected:
            raise ValueError("trend opportunity fields must match the contract")
        fields = ("opportunity_id", "topic", "audience", "platform", "observed_at")
        if any(not isinstance(value[k], str) or not value[k].strip() for k in fields):
            raise ValueError("required trend fields must be nonempty strings")
        for key in ("signals", "source_refs"):
            items = value[key]
            if not isinstance(items, (list, tuple)) or not items:
                raise ValueError(f"{key} must be a nonempty sequence")
            if any(not isinstance(item, str) or not item.strip() for item in items):
                raise ValueError(f"{key} values must be nonempty strings")
        return cls(**{**{k: value[k].strip() for k in fields},
                      "signals": tuple(item.strip() for item in value["signals"]),
                      "source_refs": tuple(item.strip() for item in value["source_refs"])})


@dataclass(frozen=True)
class ResearchEvidence:
    artifact_id: str
    opportunity_id: str
    topic: str
    audience: str
    platform: str
    observed_at: str
    observations: tuple[str, ...]
    source_refs: tuple[str, ...]
    evidence_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def research_opportunity(opportunity: TrendOpportunity) -> ResearchEvidence:
    """Transform user-provided observations into a reproducible evidence record.

    This is evidence *organization*, not independent fact verification.
    Source references are preserved without claiming to have consulted them.
    """
    canonical = json.dumps(asdict(opportunity), sort_keys=True, separators=(",", ":"))
    artifact_id = "research-" + sha256(canonical.encode("utf-8")).hexdigest()[:20]
    return ResearchEvidence(
        artifact_id=artifact_id,
        opportunity_id=opportunity.opportunity_id,
        topic=opportunity.topic,
        audience=opportunity.audience,
        platform=opportunity.platform,
        observed_at=opportunity.observed_at,
        observations=opportunity.signals,
        source_refs=opportunity.source_refs,
        evidence_status="USER_SUPPLIED_UNVERIFIED",
    )
