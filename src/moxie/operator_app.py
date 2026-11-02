"""Standard-library Windows desktop operator UI; intentionally no publishing actions."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .first_slice import ContractError
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
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)
        self.intake = ttk.Frame(self.tabs, padding=12)
        self.approvals = ttk.Frame(self.tabs, padding=12)
        self.history = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.intake, text="Opportunity & Brief")
        self.tabs.add(self.approvals, text="Pending Human Review")
        self.tabs.add(self.history, text="Activity History")
        self._build_intake()
        self._build_approvals()
        self._build_history()
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
        ttk.Label(self.intake, text="Draft body").pack(anchor="w", pady=(10, 3))
        self.body = tk.Text(self.intake, height=9, wrap="word")
        self.body.pack(fill="both", expand=True)
        ttk.Button(self.intake, text="Evaluate & Queue for Human Review", command=self.submit).pack(
            anchor="e", pady=(10, 4)
        )
        self.outcome = tk.StringVar(value="Complete the fields, then evaluate. No content is published.")
        ttk.Label(self.intake, textvariable=self.outcome, wraplength=900).pack(anchor="w")

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

    def submit(self) -> None:
        values = {key: entry.get().strip() for key, entry in self.fields.items()}
        request = OperatorSubmission(**values, brief_body=self.body.get("1.0", "end-1c"))
        try:
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

    def refresh(self) -> None:
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
