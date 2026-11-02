"""Local evidence provenance and explicit operator attestation, not fact checking."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .first_slice import ContractError


class EvidenceRegistry:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._db()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS evidence_sources (
                opportunity_id TEXT NOT NULL, evidence_id TEXT NOT NULL,
                source_type TEXT NOT NULL, source_ref TEXT NOT NULL,
                publication_date TEXT NOT NULL, excerpt TEXT NOT NULL,
                verified_by TEXT, verified_at TEXT,
                PRIMARY KEY(opportunity_id,evidence_id))""")

    def _db(self):
        return sqlite3.connect(self.path, timeout=5)

    def register(self, opportunity_id: str, evidence_id: str, source_type: str,
                 source_ref: str, publication_date: str, excerpt: str) -> None:
        if not all(isinstance(x, str) and x.strip() for x in (opportunity_id, evidence_id, source_type, source_ref, excerpt)):
            raise ContractError("opportunity, evidence ID, source type/reference and excerpt are required")
        if source_type not in ("URL", "Local document", "Operator note"):
            raise ContractError("unsupported evidence source type")
        if source_type == "URL":
            parsed = urlparse(source_ref.strip())
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ContractError("source URL must be absolute HTTP(S)")
        if publication_date:
            try:
                datetime.strptime(publication_date.strip(), "%Y-%m-%d")
            except ValueError as exc:
                raise ContractError("publication date must be YYYY-MM-DD or empty") from exc
        with closing(self._db()) as db, db:
            old = db.execute("SELECT 1 FROM evidence_sources WHERE opportunity_id=? AND evidence_id=?", (opportunity_id.strip(), evidence_id.strip())).fetchone()
            if old:
                raise ContractError("source already registered; evidence entries are immutable after registration")
            db.execute("INSERT INTO evidence_sources VALUES (?,?,?,?,?,?,NULL,NULL)", (
                opportunity_id.strip(), evidence_id.strip(), source_type, source_ref.strip(), publication_date.strip(), excerpt.strip(),
            ))

    def verify(self, opportunity_id: str, evidence_id: str, reviewer: str) -> None:
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ContractError("operator identity is required for evidence attestation")
        with closing(self._db()) as db, db:
            updated = db.execute("""UPDATE evidence_sources SET verified_by=?,verified_at=?
                WHERE opportunity_id=? AND evidence_id=? AND verified_by IS NULL""", (
                    reviewer.strip(), datetime.now(timezone.utc).isoformat(), opportunity_id, evidence_id,
                ))
            if updated.rowcount != 1:
                raise ContractError("evidence absent or already attested")

    def list(self, opportunity_id: str) -> tuple[dict, ...]:
        with closing(self._db()) as db, db:
            rows = db.execute("""SELECT opportunity_id,evidence_id,source_type,source_ref,publication_date,excerpt,verified_by,verified_at
                FROM evidence_sources WHERE opportunity_id=? ORDER BY evidence_id""", (opportunity_id,)).fetchall()
        fields = ("opportunity_id", "evidence_id", "source_type", "source_ref", "publication_date", "excerpt", "verified_by", "verified_at")
        return tuple(dict(zip(fields, row)) for row in rows)
