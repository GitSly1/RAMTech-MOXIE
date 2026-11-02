"""SQLite-backed human-review queue with no channel/publishing authority."""

from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from .first_slice import ApprovalItem, ContentBrief, ContractError, HumanApprovalQueue, QAResult


class DurableHumanApprovalQueue(HumanApprovalQueue):
    """Persist QA-accepted approvals across process restarts.

    Each operation opens its own SQLite transaction. No external API is used.
    """

    def __init__(self, database_path: str | Path) -> None:
        super().__init__()
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as database, database:
            database.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_queue (
                    item_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state = 'pending_human_approval')
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        database = sqlite3.connect(self.database_path, timeout=5)
        database.execute("PRAGMA busy_timeout = 5000")
        return database

    @staticmethod
    def _decode(payload: str) -> ApprovalItem:
        record = json.loads(payload)
        brief = record["brief"]
        qa = record["qa"]
        return ApprovalItem(
            item_id=record["item_id"],
            brief=ContentBrief(
                opportunity_id=brief["opportunity_id"],
                title=brief["title"],
                body=brief["body"],
                evidence_ids=tuple(brief["evidence_ids"]),
            ),
            qa=QAResult(
                disposition=qa["disposition"],
                reasons=tuple(qa["reasons"]),
            ),
            state=record["state"],
        )

    def enqueue(self, brief: ContentBrief, qa: QAResult) -> ApprovalItem:
        # The existing domain gate derives the deterministic item identity.
        item = HumanApprovalQueue().enqueue(brief, qa)
        payload = json.dumps(asdict(item), sort_keys=True, separators=(",", ":"))
        with closing(self._connect()) as database, database:
            database.execute(
                "INSERT OR IGNORE INTO approval_queue(item_id, payload, state) VALUES (?, ?, ?)",
                (item.item_id, payload, item.state),
            )
            row = database.execute(
                "SELECT payload FROM approval_queue WHERE item_id = ?",
                (item.item_id,),
            ).fetchone()
            if row is None or row[0] != payload:
                raise ContractError("durable approval identity collision")
        return item

    def pending(self) -> tuple[ApprovalItem, ...]:
        with closing(self._connect()) as database, database:
            rows = database.execute(
                "SELECT payload FROM approval_queue ORDER BY rowid"
            ).fetchall()
        return tuple(self._decode(payload) for (payload,) in rows)
