"""Local draft and human-decision persistence, separate from RVSC QA governance."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .first_slice import ContractError


class OperatorStore:
    def __init__(self, database_path: Path) -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS operator_drafts (opportunity_id TEXT PRIMARY KEY, payload TEXT NOT NULL, saved_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS operator_decisions (item_id TEXT PRIMARY KEY, decision TEXT NOT NULL CHECK (decision IN ('approved','rejected')), reviewer TEXT NOT NULL, reason TEXT NOT NULL, decided_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS draft_versions (version_id INTEGER PRIMARY KEY AUTOINCREMENT, opportunity_id TEXT NOT NULL, payload TEXT NOT NULL, saved_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS quality_snapshots (item_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=5)

    def save_draft(self, request) -> None:
        if not isinstance(request.opportunity_id, str) or not request.opportunity_id.strip():
            raise ContractError("opportunity ID required to save draft")
        stamp = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(asdict(request), ensure_ascii=False)
        with closing(self._connect()) as db, db:
            old = db.execute("SELECT payload FROM operator_drafts WHERE opportunity_id = ?", (request.opportunity_id.strip(),)).fetchone()
            if old is not None and json.loads(old[0]) == json.loads(payload):
                return
            db.execute(
                "INSERT INTO operator_drafts VALUES (?, ?, ?) ON CONFLICT(opportunity_id) DO UPDATE SET payload=excluded.payload, saved_at=excluded.saved_at",
                (request.opportunity_id.strip(), payload, stamp),
            )
            db.execute("INSERT INTO draft_versions(opportunity_id,payload,saved_at) VALUES (?,?,?)", (request.opportunity_id.strip(), payload, stamp))

    def draft_versions(self, opportunity_id: str) -> tuple[dict, ...]:
        with closing(self._connect()) as db, db:
            rows = db.execute("SELECT version_id,payload,saved_at FROM draft_versions WHERE opportunity_id=? ORDER BY version_id DESC", (opportunity_id,)).fetchall()
        return tuple(dict(version_id=row[0], payload=json.loads(row[1]), saved_at=row[2]) for row in rows)

    def save_quality_snapshot(self, item_id: str, report: dict) -> None:
        payload = json.dumps(report, sort_keys=True)
        with closing(self._connect()) as db, db:
            db.execute("INSERT OR IGNORE INTO quality_snapshots(item_id,payload) VALUES (?,?)", (item_id, payload))
            prior = db.execute("SELECT payload FROM quality_snapshots WHERE item_id=?", (item_id,)).fetchone()
            if prior is None:
                raise ContractError("quality snapshot was not persisted")

    def quality_snapshot(self, item_id: str) -> dict | None:
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT payload FROM quality_snapshots WHERE item_id=?", (item_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def drafts(self) -> tuple[dict, ...]:
        with closing(self._connect()) as db, db:
            rows = db.execute("SELECT payload FROM operator_drafts ORDER BY saved_at DESC, opportunity_id").fetchall()
        return tuple(json.loads(row[0]) for row in rows)

    def decide(self, item_id: str, decision: str, reviewer: str, reason: str, valid_ids: set[str]) -> None:
        if item_id not in valid_ids:
            raise ContractError("item not in deterministic QA approval queue")
        if decision not in ("approved", "rejected"):
            raise ContractError("unsupported review decision")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ContractError("reviewer identity required")
        if not isinstance(reason, str) or not reason.strip():
            raise ContractError("review reason required")
        with closing(self._connect()) as db, db:
            try:
                db.execute(
                    "INSERT INTO operator_decisions VALUES (?, ?, ?, ?, ?)",
                    (item_id, decision, reviewer.strip(), reason.strip(), datetime.now(timezone.utc).isoformat()),
                )
            except sqlite3.IntegrityError as exc:
                raise ContractError("item already has a final human decision") from exc

    def decisions(self) -> dict[str, dict]:
        with closing(self._connect()) as db, db:
            rows = db.execute("SELECT item_id, decision, reviewer, reason, decided_at FROM operator_decisions").fetchall()
        return {row[0]: dict(zip(("item_id", "decision", "reviewer", "reason", "decided_at"), row)) for row in rows}
