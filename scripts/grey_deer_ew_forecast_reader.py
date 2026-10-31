"""Grey Deer EW-P3 forecast reader STUB, registered by
research/grey_deer/ew_completion_20261031/EW_FORECAST_PREREG_v1_2026-10-31.md
(sections 2 and 11): it parses the two machine lines, checks the prospective-window
and issue-receipt gates, and is always NOT_EXECUTABLE; SCORER_IMPLEMENTED = False
until the full reader lands (prereg section 11.5 step 5). It never scores, never
opens a price store, a label or a grading file, and opens nothing under data/
before the window gate passes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PREREG_RELPATH = "research/grey_deer/ew_completion_20261031/EW_FORECAST_PREREG_v1_2026-10-31.md"
ISSUE_LOG_RELPATH = "data/grey_deer_ew_forecast/issue_log.jsonl"
ISSUE_CONTRACT = "grey_deer_ew_forecast_issue.v1"
FAMILIES = ("grey_deer_ew_mkt_v1", "grey_deer_ew_rs_v1")
DECLARED_BUDGET = 3
REGISTRATION_REASON = (
    "EW-P3 prereg research/grey_deer/ew_completion_20261031/"
    "EW_FORECAST_PREREG_v1_2026-10-31.md: C-MKT/C-RS primary h21; h5/h10 descriptive"
)
SCORER_IMPLEMENTED = False
VERDICT = "NOT_EXECUTABLE"
REFUSALS = (
    "prospective_start_unrecorded",
    "prospective_start_inconsistent",
    "window_not_elapsed",
    "no_receipted_issue",
    "scorer_not_implemented",
)

MERGE_LINE_RE = re.compile(r"^EW_P3_MERGE_DATE_UTC: (UNRECORDED|\d{4}-\d{2}-\d{2})$", re.M)
START_LINE_RE = re.compile(r"^EW_P3_PROSPECTIVE_START: (UNRECORDED|\d{4}-\d{2}-\d{2})$", re.M)

if __name__ == "__main__" and __package__ in (None, ""):  # run by file path
    sys.path.insert(0, str(REPO_ROOT))

from lib import nyse_calendar as cal  # noqa: E402


def parse_machine_lines(text: str) -> tuple[date, date] | None:
    """(merge_date, prospective_start) from the prereg's two machine lines.

    None unless exactly one line matches each pattern, neither is UNRECORDED,
    and both carry a valid ISO calendar date."""
    merges = MERGE_LINE_RE.findall(text)
    starts = START_LINE_RE.findall(text)
    if len(merges) != 1 or len(starts) != 1:
        return None
    if merges[0] == "UNRECORDED" or starts[0] == "UNRECORDED":
        return None
    try:
        return date.fromisoformat(merges[0]), date.fromisoformat(starts[0])
    except ValueError:  # e.g. 2026-13-01 or 2026-02-30
        return None


def first_session_strictly_after(d: date) -> date:
    """Smallest NYSE session date strictly after ``d`` (``d`` itself need not be one)."""
    probe = d + timedelta(days=1)
    for _ in range(30):  # the longest closed stretch is a few days (CAL convention)
        if cal.is_session(probe):
            return probe
        probe += timedelta(days=1)
    raise ValueError("no NYSE session found in the next 30 days — calendar rules broken")


def _first_session_on_or_after(d: date) -> date:
    probe = d
    for _ in range(30):
        if cal.is_session(probe):
            return probe
        probe += timedelta(days=1)
    raise ValueError("no NYSE session found in the next 30 days — calendar rules broken")


def _last_day_of_month(d: date) -> date:
    first_next = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)
    return first_next - timedelta(days=1)


def earliest_first_look(start: date) -> date:
    """The earliest-first-look lower bound L0 (prereg section 11.2)."""
    if not cal.is_session(start):
        raise ValueError(f"prospective start {start.isoformat()} is not an NYSE session")
    a = cal.session_n_forward(start, 251)          # 252-session floor
    b = _first_session_on_or_after(start + timedelta(days=300))  # 300-day floor
    if a is None:
        raise ValueError("calendar could not resolve the 252-session floor")
    t_min = max(a, b)
    m = cal.session_n_forward(t_min, 21)           # h = 21 label maturity
    if m is None:
        raise ValueError("calendar could not resolve the h=21 maturity session")
    return cal.last_session_on_or_before(_last_day_of_month(m))


def window_elapsed(start: date, now_utc: datetime) -> bool:
    """True iff ``now_utc`` is strictly after 16:00 America/New_York on L0."""
    if now_utc.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    l0 = earliest_first_look(start)
    close = datetime.combine(l0, time(16, 0), tzinfo=cal.ET)
    return now_utc.astimezone(cal.ET) > close


def has_receipted_issue(issue_log_path: Path) -> bool:
    """True iff some issue-log row carries the v1 contract receipt with a fingerprint.

    A missing log is False; unparseable or blank lines are skipped, never raised."""
    try:
        with open(issue_log_path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(row, dict):
                    continue
                fingerprint = row.get("model_fingerprint")
                if (row.get("contract") == ISSUE_CONTRACT
                        and isinstance(fingerprint, str) and fingerprint):
                    return True
    except OSError:  # missing file (or unreadable) — fail closed
        return False
    return False


def evaluate(*, prereg_text: str | None = None, now_utc: datetime | None = None,
             issue_log_path: Path | None = None) -> dict:
    """Run the five refusal gates in order and return the first that applies."""
    if prereg_text is None:
        prereg_text = (REPO_ROOT / PREREG_RELPATH).read_text(encoding="utf-8")
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    merge_date: date | None = None
    start: date | None = None
    first_look: date | None = None
    parsed = parse_machine_lines(prereg_text)
    if parsed is None:
        refusal, gate = "prospective_start_unrecorded", 1
    else:
        merge_date, start = parsed
        if start != first_session_strictly_after(merge_date):
            refusal, gate = "prospective_start_inconsistent", 2
        else:
            first_look = earliest_first_look(start)
            if not window_elapsed(start, now_utc):
                refusal, gate = "window_not_elapsed", 3
            else:
                # The issue-log path is resolved ONLY here: nothing under data/
                # is opened, stat'ed or passed to a function before gate 3 passes.
                path = issue_log_path if issue_log_path is not None else (REPO_ROOT / ISSUE_LOG_RELPATH)
                if not has_receipted_issue(path):
                    refusal, gate = "no_receipted_issue", 4
                elif not SCORER_IMPLEMENTED:
                    refusal, gate = "scorer_not_implemented", 5
                else:
                    raise RuntimeError("the EW-P3 stub never scores")

    return {
        "verdict": VERDICT,
        "refusal": refusal,
        "gate": gate,
        "scorer_implemented": SCORER_IMPLEMENTED,
        "merge_date": merge_date.isoformat() if merge_date is not None else None,
        "prospective_start": start.isoformat() if start is not None else None,
        "earliest_first_look": first_look.isoformat() if first_look is not None else None,
        "now_utc": now_utc.isoformat(),
    }


def register_families(ledger) -> list[bool]:
    """Declare the 3-trial budget for both EW-P3 families (prereg section 11.3)."""
    return [ledger.log_declared_budget(DECLARED_BUDGET, family=fam, reason=REGISTRATION_REASON)
            for fam in FAMILIES]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EW-P3 forecast reader stub (always NOT_EXECUTABLE)")
    parser.add_argument("--issue-log", type=Path, default=None,
                        help="issue log path to check at gate 4 (default: the registered path)")
    parser.add_argument("--ledger-path", type=Path, default=None,
                        help="trial-ledger path for --register-families (default: TL DEFAULT_PATH)")
    parser.add_argument("--register-families", action="store_true",
                        help="append the two declared-budget rows and exit")
    args = parser.parse_args(argv)

    if args.register_families:
        from engine.trial_ledger import TrialLedger  # lazy: not an import-time dep
        ledger = (TrialLedger(args.ledger_path) if args.ledger_path is not None
                  else TrialLedger())
        print(json.dumps({"registered": register_families(ledger),
                          "families": list(FAMILIES)}, sort_keys=True))
        return 0

    print(json.dumps(evaluate(issue_log_path=args.issue_log), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
