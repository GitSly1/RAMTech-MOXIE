"""Claim-line evidence traceability and immutable human decisions."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .evidence_quality import REF_PATTERN
from .first_slice import ContractError


@dataclass(frozen=True)
class ClaimLine:
    claim_id: str
    line_number: int
    text: str
    cited_ids: tuple[str, ...]


def extract_claims(opportunity_id: str, body: str) -> tuple[ClaimLine, ...]:
    claims = []
    for line_number, raw in enumerate(body.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.lower() in ("checklist", "draft prose"):
            continue
        if not any(letter.isalpha() for letter in line):
            continue
        citations = tuple(match.group(1).strip() for match in REF_PATTERN.finditer(line))
        identity = f"{opportunity_id}\x00{line_number}\x00{line}".encode("utf-8")
        claim_id = hashlib.sha256(identity).hexdigest()[:24]
        claims.append(ClaimLine(claim_id, line_number, line, citations))
    return tuple(claims)


class ClaimReviewStore:
    DECISIONS = ("supported_by_operator", "unsupported_by_operator", "needs_more_research")

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS claim_decisions (
                claim_id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL,
                claim_text TEXT NOT NULL, citations TEXT NOT NULL,
                decision TEXT NOT NULL, reviewer TEXT NOT NULL, reason TEXT NOT NULL,
                reviewed_at TEXT NOT NULL)""")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def decide(self, opportunity_id: str, claim: ClaimLine, decision: str,
               reviewer: str, reason: str, allowed_ids: set[str]) -> None:
        if decision not in self.DECISIONS:
            raise ContractError("unknown claim-review decision")
        if not reviewer.strip() or not reason.strip():
            raise ContractError("claim reviewer and reason are required")
        if decision == "supported_by_operator" and (not claim.cited_ids or any(ref not in allowed_ids for ref in claim.cited_ids)):
            raise ContractError("supported decision requires known cited evidence IDs")
        with closing(self._connect()) as db, db:
            try:
                db.execute("INSERT INTO claim_decisions VALUES (?,?,?,?,?,?,?,?)", (
                    claim.claim_id, opportunity_id, claim.text, ",".join(claim.cited_ids), decision,
                    reviewer.strip(), reason.strip(), datetime.now(timezone.utc).isoformat(),
                ))
            except sqlite3.IntegrityError as exc:
                raise ContractError("claim already has an immutable decision") from exc

    def decisions(self, claims: tuple[ClaimLine, ...]) -> dict[str, dict]:
        if not claims:
            return {}
        ids = [claim.claim_id for claim in claims]
        placeholders = ",".join("?" for _ in ids)
        with closing(self._connect()) as db, db:
            rows = db.execute(
                f"SELECT claim_id, decision, reviewer, reason, reviewed_at FROM claim_decisions WHERE claim_id IN ({placeholders})", ids,
            ).fetchall()
        return {row[0]: {"decision": row[1], "reviewer": row[2], "reason": row[3], "reviewed_at": row[4]} for row in rows}
