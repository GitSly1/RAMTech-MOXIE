"""Standard-library Windows desktop operator UI; intentionally no publishing actions."""

from __future__ import annotations

import tkinter as tk
import queue
import threading
from tkinter import filedialog, messagebox, ttk

from .batch_import import import_drafts_csv
from .first_slice import ContractError
from .local_drafter import FORMATS, TONES, draft_with_ollama
from .operator_service import OperatorService, OperatorSubmission


class OperatorApp(ttk.Frame):
    def __init__(self, root: tk.Tk, service: OperatorService) -> None:
        super().__init__(root, padding=14)
        self.service = service
        self.pack(fill="both", expand=True)
        root.title("RAMTech MOXIE | Local Operator")
        root.geometry("1050x740")
        ttk.Label(self, text="MOXIE — Operator Workspace", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(
            self,
            text="Local-only • Deterministic QA • Human approval pending • No publishing capability",
        ).pack(anchor="w", pady=(1, 12))
        self.summary_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.summary_var, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)
        self.intake = ttk.Frame(self.tabs, padding=12)
        self.approvals = ttk.Frame(self.tabs, padding=12)
        self.history = ttk.Frame(self.tabs, padding=12)
        self.completed = ttk.Frame(self.tabs, padding=12)
        self.sources = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.intake, text="Opportunity & Brief")
        self.tabs.add(self.approvals, text="Pending Human Review")
        self.tabs.add(self.history, text="Activity History")
        self.tabs.add(self.completed, text="Completed Reviews")
        self.tabs.add(self.sources, text="Evidence Sources")
        self._build_intake()
        self._build_approvals()
        self._build_history()
        self._build_completed()
        self._build_sources()
        self.refresh()

    def _build_intake(self) -> None:
        form = ttk.Frame(self.intake)
        form.pack(fill="x")
        field_specs = (
            ("opportunity_id", "Opportunity ID"),
            ("topic", "Topic"),
            ("audience", "Audience"),
            ("signal_source", "Opportunity signal source"),
            ("evidence_id", "Evidence ID"),
            ("evidence_source", "Evidence source"),
            ("evidence_finding", "Evidence finding"),
            ("brief_title", "Draft title"),
        )
        self.fields: dict[str, ttk.Entry] = {}
        for row, (key, label) in enumerate(field_specs):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 16), pady=4)
            entry = ttk.Entry(form, width=92)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            self.fields[key] = entry
        form.columnconfigure(1, weight=1)
        ttk.Label(self.intake, text="Additional evidence (optional): one line per record, ID | Source | Finding").pack(anchor="w", pady=(6, 2))
        self.additional = tk.Text(self.intake, height=3, wrap="none")
        self.additional.pack(fill="x")
        ttk.Label(self.intake, text="Draft body").pack(anchor="w", pady=(10, 3))
        self.body = tk.Text(self.intake, height=5, wrap="word")
        self.body.pack(fill="both", expand=True)
        buttons = ttk.Frame(self.intake)
        buttons.pack(fill="x", pady=(8, 4))
        ttk.Label(buttons, text="Saved draft:").pack(side="left")
        self.draft_id = tk.StringVar()
        self.draft_selector = ttk.Combobox(buttons, textvariable=self.draft_id, state="readonly", width=22)
        self.draft_selector.pack(side="left", padx=5)
        ttk.Button(buttons, text="Load", command=self.load_draft).pack(side="left")
        ttk.Button(buttons, text="Versions", command=self.show_versions).pack(side="left", padx=(4, 0))
        ttk.Button(buttons, text="Import CSV", command=self.import_csv).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Check Evidence", command=self.check_evidence).pack(side="left", padx=(8, 0))
        self.ai_button = ttk.Button(buttons, text="Local Ollama Draft", command=self.local_draft)
        self.ai_button.pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Save Draft", command=self.save_draft).pack(side="right", padx=(4, 0))
        ttk.Button(buttons, text="Evaluate & Queue for Human Review", command=self.submit).pack(side="right")
        self.outcome = tk.StringVar(value="Complete the fields, then evaluate. No content is published.")
        ttk.Label(self.intake, textvariable=self.outcome, wraplength=900).pack(anchor="w")
        options = ttk.Frame(self.intake)
        options.pack(fill="x", pady=(3, 0))
        ttk.Label(options, text="AI output:").pack(side="left")
        self.ai_format = tk.StringVar(value=FORMATS[0])
        ttk.Combobox(options, textvariable=self.ai_format, values=FORMATS, state="readonly", width=24).pack(side="left", padx=5)
        ttk.Label(options, text="Tone:").pack(side="left", padx=(8, 0))
        self.ai_tone = tk.StringVar(value=TONES[0])
        ttk.Combobox(options, textvariable=self.ai_tone, values=TONES, state="readonly", width=18).pack(side="left", padx=5)
        ttk.Label(options, text="AI citations and claims require operator verification.").pack(side="left", padx=8)

    def _build_approvals(self) -> None:
        ttk.Button(self.approvals, text="Refresh", command=self.refresh).pack(anchor="e", pady=(0, 8))
        self.approval_tree = ttk.Treeview(
            self.approvals, columns=("id", "title", "state"), show="headings", height=12
        )
        for name, width in (("id", 290), ("title", 420), ("state", 190)):
            self.approval_tree.heading(name, text=name.replace("_", " ").title())
            self.approval_tree.column(name, width=width)
        self.approval_tree.pack(fill="both", expand=True)
        self.approval_tree.bind("<<TreeviewSelect>>", self._show_selected)
        controls = ttk.Frame(self.approvals)
        controls.pack(fill="x", pady=(8, 0))
        ttk.Label(controls, text="Reviewer:").pack(side="left")
        self.reviewer = ttk.Entry(controls, width=19)
        self.reviewer.pack(side="left", padx=4)
        ttk.Label(controls, text="Reason:").pack(side="left")
        self.review_reason = ttk.Entry(controls, width=44)
        self.review_reason.pack(side="left", padx=4, fill="x", expand=True)
        ttk.Button(controls, text="Approve", command=lambda: self.review("approved")).pack(side="left", padx=4)
        ttk.Button(controls, text="Reject", command=lambda: self.review("rejected")).pack(side="left")
        ttk.Label(self.approvals, text="Selected brief (read-only)").pack(anchor="w", pady=(8, 3))
        self.detail = tk.Text(self.approvals, height=9, state="disabled", wrap="word")
        self.detail.pack(fill="both", expand=True)
        self._pending = ()

    def _build_history(self) -> None:
        ttk.Button(self.history, text="Refresh", command=self.refresh).pack(anchor="e", pady=(0, 8))
        self.history_tree = ttk.Treeview(
            self.history, columns=("time", "opportunity", "result", "reason"), show="headings"
        )
        for name, width in (("time", 240), ("opportunity", 170), ("result", 120), ("reason", 460)):
            self.history_tree.heading(name, text=name.title())
            self.history_tree.column(name, width=width)
        self.history_tree.pack(fill="both", expand=True)

    def _build_completed(self) -> None:
        ttk.Button(self.completed, text="Refresh", command=self.refresh).pack(anchor="e")
        self.completed_tree = ttk.Treeview(self.completed, columns=("item", "decision", "reviewer", "date"), show="headings", height=11)
        for column, width in (("item", 340), ("decision", 110), ("reviewer", 210), ("date", 230)):
            self.completed_tree.heading(column, text=column.title())
            self.completed_tree.column(column, width=width)
        self.completed_tree.pack(fill="both", expand=True)
        self.completed_tree.bind("<<TreeviewSelect>>", self._show_completed)
        ttk.Label(self.completed, text="Recorded decision and brief (read-only)").pack(anchor="w", pady=4)
        self.completed_detail = tk.Text(self.completed, height=9, state="disabled", wrap="word")
        self.completed_detail.pack(fill="both", expand=True)
        self._completed = ()

    def _build_sources(self) -> None:
        ttk.Label(self.sources, text="Record source provenance for the opportunity shown in Opportunity & Brief. Attestation is an operator statement, not independent verification.", wraplength=910).pack(anchor="w", pady=(0, 10))
        form = ttk.Frame(self.sources)
        form.pack(fill="x")
        fields = (("source_evidence_id", "Evidence ID"), ("source_ref", "Source URL / document path / note reference"),
                  ("publication_date", "Publication date (YYYY-MM-DD, optional)"),
                  ("source_excerpt", "Evidence excerpt / finding"), ("source_reviewer", "Attesting operator"))
        self.source_fields = {}
        for row, (key, label) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
            field = ttk.Entry(form, width=78)
            field.grid(row=row, column=1, sticky="ew", pady=5)
            self.source_fields[key] = field
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Source type").grid(row=len(fields), column=0, sticky="w", pady=5)
        self.source_type = tk.StringVar(value="Operator note")
        ttk.Combobox(form, textvariable=self.source_type, values=("URL", "Local document", "Operator note"), state="readonly", width=28).grid(row=len(fields), column=1, sticky="w", pady=5)
        actions = ttk.Frame(self.sources)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="Refresh Opportunity Sources", command=self.refresh_sources).pack(side="left")
        ttk.Button(actions, text="Register Source", command=self.register_source).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Attest Selected Source", command=self.attest_source).pack(side="right")
        self.sources_tree = ttk.Treeview(self.sources, columns=("id", "type", "reference", "status", "reviewer"), show="headings", height=12)
        for key, width in (("id", 130), ("type", 120), ("reference", 310), ("status", 130), ("reviewer", 150)):
            self.sources_tree.heading(key, text=key.title())
            self.sources_tree.column(key, width=width)
        self.sources_tree.pack(fill="both", expand=True)
        self._sources = ()

    def refresh_sources(self) -> None:
        opportunity_id = self.fields["opportunity_id"].get().strip()
        self._sources = self.service.evidence_sources(opportunity_id) if opportunity_id else ()
        for row in self.sources_tree.get_children():
            self.sources_tree.delete(row)
        for i, record in enumerate(self._sources):
            self.sources_tree.insert("", "end", iid=str(i), values=(
                record["evidence_id"], record["source_type"], record["source_ref"],
                "ATTESTED" if record["verified_by"] else "UNVERIFIED", record["verified_by"] or "",
            ))

    def register_source(self) -> None:
        try:
            self.service.register_evidence(
                self.fields["opportunity_id"].get().strip(),
                self.source_fields["source_evidence_id"].get().strip(), self.source_type.get(),
                self.source_fields["source_ref"].get().strip(),
                self.source_fields["publication_date"].get().strip(),
                self.source_fields["source_excerpt"].get().strip(),
            )
        except (ContractError, OSError, ValueError) as exc:
            messagebox.showerror("Register Evidence Source", str(exc))
            return
        self.refresh_sources()

    def attest_source(self) -> None:
        selected = self.sources_tree.selection()
        if not selected:
            messagebox.showwarning("Evidence Attestation", "Select one registered source.")
            return
        record = self._sources[int(selected[0])]
        if not messagebox.askyesno("Confirm source attestation", "Have you personally checked the source and its recorded excerpt? This attestation is final and does not independently verify truth."):
            return
        try:
            self.service.attest_evidence(record["opportunity_id"], record["evidence_id"], self.source_fields["source_reviewer"].get())
        except (ContractError, OSError, ValueError) as exc:
            messagebox.showerror("Evidence Attestation", str(exc))
            return
        self.refresh_sources()

    def local_draft(self) -> None:
        try:
            request = self._request()
            evidence = ((request.evidence_id, request.evidence_finding),) + tuple(
                (row[0], row[2]) for row in request.extra_evidence
            )
            if not request.topic or not request.audience or any(not id_ or not finding for id_, finding in evidence):
                raise ContractError("enter topic, audience and evidence before drafting")
        except ContractError as exc:
            messagebox.showerror("Local drafting", str(exc))
            return
        self.ai_button.configure(state="disabled")
        self.outcome.set("Local Ollama drafting in progress (one request, up to 65 seconds)...")
        self._ai_results: queue.Queue = queue.Queue(maxsize=1)
        selected_format, selected_tone = self.ai_format.get(), self.ai_tone.get()
        def worker():
            try:
                self._ai_results.put((True, draft_with_ollama(request.topic, request.audience, evidence, content_format=selected_format, tone=selected_tone)))
            except Exception as exc:
                self._ai_results.put((False, str(exc)))
        threading.Thread(target=worker, daemon=True).start()
        self.after(150, self._finish_local_draft)

    def _finish_local_draft(self) -> None:
        try:
            success, value = self._ai_results.get_nowait()
        except queue.Empty:
            self.after(150, self._finish_local_draft)
            return
        self.ai_button.configure(state="normal")
        if not success:
            self.outcome.set(f"Local draft failed: {value}")
            return
        if self.body.get("1.0", "end-1c").strip():
            if not messagebox.askyesno("Replace draft body?", "Local Ollama returned a draft. Replace the current body? No content has been saved or approved."):
                self.outcome.set("Local draft discarded; existing text preserved.")
                return
        self.body.delete("1.0", "end")
        self.body.insert("1.0", value)
        self.outcome.set("Ollama draft inserted for operator editing. Verify claims before QA and approval.")

    def submit(self) -> None:
        try:
            request = self._request()
            report = self.service.check_evidence(request)
            if report.issues:
                self.service.journal.record(request.opportunity_id, "evidence_check_blocked", report.issues)
                self.outcome.set("Evidence check found unresolved citations; submit blocked. Use Check Evidence for details.")
                messagebox.showwarning("Evidence check blocks submission", "\n".join(report.issues[:12]) + "\n\n" + report.notice)
                return
            result = self.service.submit(request)
        except (ContractError, OSError, ValueError) as exc:
            self.outcome.set(f"Not queued: {exc}")
            messagebox.showerror("MOXIE submission", str(exc))
            self.refresh()
            return
        if result.qa.disposition == "accepted":
            self.outcome.set(f"Accepted by deterministic QA; queued for HUMAN review: {result.approval_item.item_id}")
        else:
            self.outcome.set("Rejected by deterministic QA: " + "; ".join(result.qa.reasons))
        self.refresh()

    def check_evidence(self) -> None:
        try:
            request = self._request()
            report = self.service.check_evidence(request)
        except (ContractError, ValueError) as exc:
            messagebox.showerror("Evidence Quality", str(exc))
            return
        self.service.journal.record(request.opportunity_id, "evidence_check", report.issues)
        message = (
            f"Status: {report.status}\n"
            f"Recognized citations: {report.cited_segments}/{report.checked_segments} draft lines\n\n"
            + ("\n".join(report.issues[:15]) if report.issues else "No missing/unknown citations detected in checked lines.")
            + "\n\n" + report.notice
        )
        records = {row["evidence_id"]: row for row in self.service.evidence_sources(request.opportunity_id)}
        all_ids = (request.evidence_id,) + tuple(row[0] for row in request.extra_evidence)
        message += "\n\nRegistered source status:\n" + "\n".join(
            f"[{identifier}] " + (
                "ATTESTED by " + records[identifier]["verified_by"] if identifier in records and records[identifier]["verified_by"]
                else "UNVERIFIED (no operator attestation)"
            ) for identifier in all_ids
        )
        messagebox.showinfo("Evidence Quality", message)

    def _request(self) -> OperatorSubmission:
        values = {key: entry.get().strip() for key, entry in self.fields.items()}
        extra = []
        for line_number, line in enumerate(self.additional.get("1.0", "end-1c").splitlines(), 1):
            if not line.strip():
                continue
            parts = tuple(part.strip() for part in line.split("|", 2))
            if len(parts) != 3 or not all(parts):
                raise ContractError(f"additional evidence line {line_number} requires ID | Source | Finding")
            extra.append(parts)
        return OperatorSubmission(**values, brief_body=self.body.get("1.0", "end-1c"), extra_evidence=tuple(extra))

    def save_draft(self) -> None:
        try:
            self.service.save_draft(self._request())
            self.outcome.set("Draft saved locally. You can reopen it after restarting MOXIE.")
            self.refresh()
        except (ContractError, OSError, ValueError) as exc:
            messagebox.showerror("Save Draft", str(exc))

    def import_csv(self) -> None:
        selected = filedialog.askopenfilename(
            title="Import MOXIE opportunity drafts", filetypes=[("CSV files", "*.csv")]
        )
        if not selected:
            return
        try:
            report = import_drafts_csv(selected, self.service)
        except (ContractError, OSError, UnicodeError) as exc:
            messagebox.showerror("CSV import", str(exc))
            return
        self.refresh()
        summary = f"CSV imported {report.imported} drafts; rejected {report.rejected} rows. No drafts queued or published."
        self.outcome.set(summary)
        if report.issues:
            messagebox.showwarning("CSV import completed", summary + "\n\n" + "\n".join(report.issues[:8]))
        else:
            messagebox.showinfo("CSV import completed", summary)

    def load_draft(self) -> None:
        found = next((item for item in self.service.drafts() if item.opportunity_id == self.draft_id.get()), None)
        if found is None:
            return
        for key, entry in self.fields.items():
            entry.delete(0, "end")
            entry.insert(0, getattr(found, key))
        self.body.delete("1.0", "end")
        self.body.insert("1.0", found.brief_body)
        self.additional.delete("1.0", "end")
        self.additional.insert("1.0", "\n".join(" | ".join(row) for row in found.extra_evidence))
        self.outcome.set("Draft restored; review its fields before evaluation.")

    def show_versions(self) -> None:
        opportunity_id = self.draft_id.get() or self.fields["opportunity_id"].get().strip()
        versions = self.service.draft_versions(opportunity_id)
        if not versions:
            messagebox.showinfo("Draft Versions", "No saved versions for this opportunity.")
            return
        popup = tk.Toplevel(self)
        popup.title("Saved Draft Versions — " + opportunity_id)
        popup.geometry("770x490")
        ttk.Label(popup, text="Select a saved version (read-only until restored):").pack(anchor="w", padx=12, pady=8)
        selector = ttk.Combobox(popup, state="readonly", values=[f"{row['version_id']} | {row['saved_at']}" for row in versions], width=64)
        selector.pack(fill="x", padx=12)
        preview = tk.Text(popup, wrap="word", state="disabled")
        preview.pack(fill="both", expand=True, padx=12, pady=8)
        def display(_event=None):
            if selector.current() < 0:
                return
            record = versions[selector.current()]["payload"]
            preview.configure(state="normal")
            preview.delete("1.0", "end")
            preview.insert("1.0", record["brief_body"])
            preview.configure(state="disabled")
        selector.bind("<<ComboboxSelected>>", display)
        selector.current(0)
        display()
        def restore():
            if selector.current() < 0:
                return
            record = versions[selector.current()]["payload"]
            if not messagebox.askyesno("Restore version", "Load this earlier version into the form? Save Draft to retain the change.", parent=popup):
                return
            for key, entry in self.fields.items():
                entry.delete(0, "end")
                entry.insert(0, record[key])
            self.body.delete("1.0", "end")
            self.body.insert("1.0", record["brief_body"])
            self.additional.delete("1.0", "end")
            self.additional.insert("1.0", "\n".join(" | ".join(row) for row in record.get("extra_evidence", ())))
            self.outcome.set("Earlier draft version restored to editor; click Save Draft to preserve it.")
            popup.destroy()
        ttk.Button(popup, text="Restore to Editor", command=restore).pack(anchor="e", padx=12, pady=(0, 10))

    def review(self, decision: str) -> None:
        selected = self.approval_tree.selection()
        if not selected:
            messagebox.showwarning("Human Review", "Select a pending brief first.")
            return
        item = self._pending[int(selected[0])]
        if not messagebox.askyesno("Confirm decision", f"Record {decision} for {item.item_id}? This decision is final and does not publish content."):
            return
        try:
            self.service.review(item.item_id, decision, self.reviewer.get(), self.review_reason.get())
        except (ContractError, OSError, ValueError) as exc:
            messagebox.showerror("Human Review", str(exc))
            return
        self.review_reason.delete(0, "end")
        self.refresh()

    def refresh(self) -> None:
        summary = self.service.summary()
        self.summary_var.set(f"Saved drafts: {summary['drafts']}    Awaiting human review: {summary['awaiting_review']}    Reviewed: {summary['reviewed']}")
        self.draft_selector.configure(values=[item.opportunity_id for item in self.service.drafts()])
        self._pending = self.service.pending()
        for item in self.approval_tree.get_children():
            self.approval_tree.delete(item)
        for i, item in enumerate(self._pending):
            self.approval_tree.insert("", "end", iid=str(i), values=(item.item_id, item.brief.title, item.state))
        self._set_detail("")
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for event in self.service.activity():
            self.history_tree.insert(
                "", "end", values=(
                    event["at_utc"], event["opportunity_id"], event["disposition"],
                    "; ".join(event["reasons"]),
                ),
            )
        self._completed = self.service.reviewed()
        for row in self.completed_tree.get_children():
            self.completed_tree.delete(row)
        for i, row in enumerate(self._completed):
            self.completed_tree.insert("", "end", iid=str(i), values=(row["item_id"], row["decision"], row["reviewer"], row["decided_at"]))

    def _show_completed(self, _event: object) -> None:
        selected = self.completed_tree.selection()
        if not selected:
            return
        row = self._completed[int(selected[0])]
        brief = row["brief"]
        value = (
            f"Decision: {row['decision']}\nReviewer: {row['reviewer']}\n"
            f"Reason: {row['reason']}\nTimestamp: {row['decided_at']}\n"
            f"Citations: {', '.join(brief.evidence_ids)}\n\n{brief.title}\n\n{brief.body}"
        )
        self.completed_detail.configure(state="normal")
        self.completed_detail.delete("1.0", "end")
        self.completed_detail.insert("1.0", value)
        self.completed_detail.configure(state="disabled")

    def _set_detail(self, content: str) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", content)
        self.detail.configure(state="disabled")

    def _show_selected(self, _event: object) -> None:
        selected = self.approval_tree.selection()
        if not selected:
            return
        item = self._pending[int(selected[0])]
        self._set_detail(
            f"Opportunity: {item.brief.opportunity_id}\n"
            f"Evidence citations: {', '.join(item.brief.evidence_ids)}\n"
            f"State: {item.state}\n\n{item.brief.title}\n\n{item.brief.body}"
        )


def main() -> None:
    root = tk.Tk()
    OperatorApp(root, OperatorService())
    root.mainloop()


if __name__ == "__main__":
    main()
