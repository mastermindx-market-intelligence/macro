"""ROR-1 issued-forecast ledger audit — source behavior, not financial skill.

Consumes an immutable published JSONL source by exact path.  This identifies
suppressed forecaster states, never promotes them or creates an alert.  Runs of
adjacent *recorded rows* are NOT continuous exchange sessions; no missing
trading days are inferred and no forward outcomes are imputed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


SEVERE = frozenset({"elevated", "risk-off"})


def analyze(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    previous = ""
    for i, row in enumerate(rows):
        day = row.get("asof")
        if not isinstance(day, str):
            raise ValueError(f"Missing/non-text asof at row {i}")
        try:
            date.fromisoformat(day)
        except ValueError as exc:
            raise ValueError(f"Bad source session {day!r} at row {i}") from exc
        if previous and day <= previous:
            raise ValueError(f"Non-monotonic or duplicate source session: {previous} then {day}")
        previous = day
        if row.get("gate_clamped") is True and row.get("state_ungated") == row.get("state"):
            raise ValueError(f"Gate claimed to clamp without changing state on {day}")

    suppressed: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    by_ungated: dict[str, int] = {}
    current_run: dict[str, Any] | None = None
    for row in rows:
        un = row.get("state_ungated")
        is_suppressed = (
            row.get("gate_clamped") is True
            and un in SEVERE
            and row.get("state") not in SEVERE
            and not row.get("alert", False)
        )
        if is_suppressed:
            suppressed.append(row)
            by_ungated[un] = by_ungated.get(un, 0) + 1
            if current_run is None:
                current_run = {
                    "first": row["asof"], "last": row["asof"],
                    "records": 1, "continuity": "recorded_rows_only",
                }
            else:
                current_run["last"] = row["asof"]
                current_run["records"] += 1
        else:
            if current_run is not None:
                runs.append(current_run)
                current_run = None
    if current_run is not None:
        runs.append(current_run)

    def issued(x: dict[str, Any]) -> bool:
        return isinstance(x.get("forecast_issue"), dict) and bool(x["forecast_issue"])
    def known(x: dict[str, Any]) -> bool:
        return x.get("graded") is not None

    issue_stamps = []
    for r in suppressed:
        x = r.get("forecast_issue") or {}
        s = x.get("issued_at")
        if isinstance(s, str) and s:
            try:
                datetime.fromisoformat(s.replace("Z", "+00:00"))
                issue_stamps.append(s)
            except ValueError:
                pass

    return {
        "scope": "source_ledger_behavior_not_forecast_skill",
        "n_records": len(rows),
        "n_graded": sum(known(x) for x in rows),
        "n_issued": sum(issued(x) for x in rows),
        "n_unknown_ungated": sum("state_ungated" not in x or x["state_ungated"] is None for x in rows),
        "n_public_alert": sum(bool(x.get("alert")) for x in rows),
        "n_suppressed": len(suppressed),
        "n_issued_suppressed": sum(issued(x) for x in suppressed),
        "n_suppressed_with_known_outcome": sum(known(x) for x in suppressed),
        "n_suppressed_ungraded": sum(not known(x) for x in suppressed),
        "suppressed_by_ungated_state": {k:by_ungated[k] for k in sorted(by_ungated)},
        "suppression_runs": runs,
        "first_suppressed_source_session": suppressed[0]["asof"] if suppressed else None,
        "last_suppressed_source_session": suppressed[-1]["asof"] if suppressed else None,
        "first_dated_suppression_issuance": min(issue_stamps) if issue_stamps else None,
        "last_dated_suppression_issuance": max(issue_stamps) if issue_stamps else None,
        "suppressed_precision": None,  # suppressed != issued alert; grading not predictive proof
        "limitation": (
            "Recorded source rows are not all expected NYSE sessions. "
            "A clamped ungated state is not a validated drawdown forecast, "
            "and the ledger contains no authenticated delivery receipt."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    raw = args.jsonl.read_bytes()
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    report = analyze(records)
    report["source"] = {
        "path": str(args.jsonl), "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
        "bytes": len(raw), "first": records[0]["asof"] if records else None,
        "last": records[-1]["asof"] if records else None,
    }
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        if args.out.exists():
            raise FileExistsError(f"Refusing to overwrite existing receipt: {args.out}")
        args.out.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()