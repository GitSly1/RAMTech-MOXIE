"""Deterministic citation coverage report; no claim of external truth verification."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .first_slice import ContractError


REF_PATTERN = re.compile(r"\[([^\[\]\r\n]{1,80})\]")
VERIFY = "VERIFY"


@dataclass(frozen=True)
class EvidenceQualityReport:
    status: str
    checked_segments: int
    cited_segments: int
    issues: tuple[str, ...]
    notice: str = "Citation coverage only. Source accuracy and claim support require human verification."


def assess_draft(body: str, evidence_ids: tuple[str, ...]) -> EvidenceQualityReport:
    if not isinstance(body, str) or not body.strip():
        raise ContractError("draft body is required for evidence review")
    valid = {item.strip() for item in evidence_ids if isinstance(item, str) and item.strip()}
    issues: list[str] = []
    segments = 0
    cited = 0
    # Check each nonempty paragraph, checklist item, or line independently.
    for line_number, raw in enumerate(body.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#") or line.lower() in ("checklist", "draft prose"):
            continue
        # A single label alone is not a factual claim; all other prose is treated conservatively.
        if not re.search(r"[a-zA-Z]", line):
            continue
        segments += 1
        references = [match.group(1).strip() for match in REF_PATTERN.finditer(line)]
        usable = [ref for ref in references if ref in valid]
        for ref in references:
            if ref == VERIFY:
                issues.append(f"line {line_number}: model explicitly marked content for verification")
            elif ref not in valid:
                issues.append(f"line {line_number}: unknown evidence reference [{ref}]")
        if not usable:
            issues.append(f"line {line_number}: no recognized evidence citation")
        else:
            cited += 1
    if segments == 0:
        issues.append("no substantive draft segments found")
    return EvidenceQualityReport(
        status="REQUIRES_OPERATOR_REVIEW" if issues else "CITATION_COVERAGE_PRESENT",
        checked_segments=segments, cited_segments=cited,
        issues=tuple(dict.fromkeys(issues)),
    )
