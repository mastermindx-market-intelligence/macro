"""Report which earnings-call store Prophet will actually read on THIS host.

WHY THIS EXISTS. The Prophet hold-leash's earnings arm (``engine/prophet_bridge.py``
via ``engine/prophet_stage_inputs.py``) reads EquityDesk's native
``earnings_call_sent``. Until 2026-09-18 it resolved exactly one path —
``data/stage_analysis/backfill/earnings_calls.parquet`` — which is gitignored, was never
committed and has no publisher, so on every CI and deploy host the file was absent, the
EC join returned an empty table, and the promoted tilt could never become eligible. The
starvation was real but only visible as a ``::warning`` emitted deep inside a 15-minute
build step, and only AFTER the plans had already been written.

The same native table already reaches the runner as
``data/earnings_calls/history.parquet``, restored by ``scripts/fetch_earnings_scores.py``
from the earnings R2 generation plane that ``engine/earnings_qual.py`` has consumed since
SGA W4. ``prophet_stage_inputs`` now reads that ladder. This script prints the resolved
state as a first-class Actions annotation immediately after hydration and BEFORE Prophet
originates, so "the cohort was starved tonight" is legible at the top of the run instead
of being reconstructed from plan JSON afterwards.

AUTHORITY: none. This reports; it never fetches, writes, gates or changes a plan. Exit
code is 0 in every case — an absent source is the documented fail-open, not an error.

Run: python3 scripts/report_prophet_earnings_source.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def report() -> int:
    try:
        import engine.prophet_stage_inputs as psi
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=prophet-earnings-source::cannot import the Prophet "
              f"earnings inputs module ({e}) — source state unknown", flush=True)
        return 0

    try:
        table, record = psi.load_ec_table_with_source()
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=prophet-earnings-source::earnings source load raised "
              f"({e}) — Prophet will originate with no earnings reading", flush=True)
        return 0

    state = str(record.get("state") or "")
    rejected = record.get("rejected") or []
    for item in rejected:
        print(f"::warning title=prophet-earnings-source::tier "
              f"{item.get('tier')} at {item.get('path')} was NOT used — "
              f"{item.get('reason')}", flush=True)

    if state != psi.EC_SOURCE_AVAILABLE:
        print(f"::warning title=prophet-earnings-source::{record.get('reason')}; "
              "tonight's Prophet plans will each carry ec_source_state=unavailable and "
              "the Stage hold-tilt cannot become eligible (leash pinned at 1.0)",
              flush=True)
        return 0

    generation = record.get("generation") or {}
    tickers = 0
    try:
        tickers = int(table["ticker"].dropna().astype(str).nunique())
    except Exception:  # noqa: BLE001
        pass
    print(
        "::notice title=prophet-earnings-source::earnings-call source AVAILABLE — "
        f"tier={record.get('tier')} path={record.get('path')} "
        f"rows={record.get('rows')} tickers={tickers} "
        f"generation={generation.get('generation_id')} "
        f"gate=earnings_call_sent>={psi.EC_SENT_GATE} "
        f"(native ~{psi.EC_SENT_NATIVE_MIN}..{psi.EC_SENT_NATIVE_MAX})",
        flush=True,
    )
    summary = {
        "state": state,
        "tier": record.get("tier"),
        "path": record.get("path"),
        "rows": record.get("rows"),
        "tickers": tickers,
        "generation": generation or None,
        "rejected": rejected,
    }
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(report())
