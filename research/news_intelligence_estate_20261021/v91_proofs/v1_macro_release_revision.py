#!/usr/bin/env python3
"""V91 vertical proof V1 — Macro release and revision (masterplan §9.1 row).

Offline, deterministic evidence for masterplan §9.1 vertical V1
(research/news_intelligence_estate_20261021/MASTERPLAN.md:471): exact
release/period/units with first print versus revision, a dated expectation or
honestly labelled alternative benchmark, no fabricated consensus, later
revisions retained, and whether radar, news and Brain agree. Rung
COMMITTED_ARTIFACT: the tracked ALFRED all-vintage parquet files under
data/fred_vintage/release_targets/ are read (never regenerated or written)
through the repository producers, and every property is decided only by what
this run observes — PROVEN requires both the positive behaviour on a SYNTH
input or committed artifact and a discriminating negative in the same run.

No network, no model call, no wall clock in anything printed; every temp
artifact lives under --scratch. Unexpected producer failures crash the script;
only a producer's own refusal is caught, and only to observe that refusal.

Output (parsed by tests/test_v91_vertical_proofs.py):

    V1 P<k> <PROVEN|PARTIAL|ABSENT|HUMAN_GATE> <evidence>
    V1 SUMMARY proven=<a> partial=<b> absent=<c> human_gate=<d> rung=COMMITTED_ARTIFACT

PYTHONPATH is not required (ROOT is resolved from __file__):

    python3 research/news_intelligence_estate_20261021/v91_proofs/v1_macro_release_revision.py --scratch <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Committed artifacts this proof opens (the harness skips the proof when one
# is absent, e.g. in a sparse worktree without data/fred_vintage).
REQUIRED_ARTIFACTS = (
    "data/fred_vintage/release_targets/PAYEMS_all_vintages.parquet",
    "data/fred_vintage/release_targets/CPIAUCSL_all_vintages.parquet",
)

# Releases chosen for the first-print proofs. Only the release date and
# reference month are constants here; every value printed below is computed
# from the committed parquet in this run, never copied from a producer output.
PAYEMS_PERIOD = "2026-05"   # first print on the 2026-06-05 vintage, later revised
PAYEMS_RELEASE = "2026-06-05"
CPI_PERIOD = "2025-09"      # released 2025-10-24, revised in later vintages
CPI_RELEASE = "2025-10-24"

FOREVER = date(9999, 12, 31)


def _or_na(value: float | None, spec: str) -> str:
    """Format an observed float, or say it was absent (never crash on a gap)."""
    return format(value, spec) if value is not None else "n/a"


# --------------------------------------------------------------- independent ----
def _prior_month(month: str) -> str:
    year, mon = (int(part) for part in month.split("-"))
    return f"{year - 1}-12" if mon == 1 else f"{year}-{mon - 1:02d}"


def _raw_rows(frame: pd.DataFrame) -> list[tuple[str, pd.Timestamp, date, float]]:
    """Plain vintage rows (month, realtime_start, realtime_end, value).

    This is the independent path's view of the committed store: selection and
    arithmetic below never call the producer's own ``_row_active_on`` or its
    subtraction; only the file itself is read through the repository loader.
    """
    return [
        (
            row.period.strftime("%Y-%m"),
            row.realtime_start,
            row.realtime_end,
            float(row.value),
        )
        for row in frame.itertuples(index=False)
    ]


def _active_on(
    rows: list[tuple[str, pd.Timestamp, date, float]], month: str, release: pd.Timestamp
) -> list[tuple[str, pd.Timestamp, date, float]]:
    """Independent window selection: rows whose realtime window contains the day."""
    return [
        row
        for row in rows
        if row[0] == month and row[1] <= release and row[2] >= release.date()
    ]


def _earliest(
    rows: list[tuple[str, pd.Timestamp, date, float]], month: str
) -> list[tuple[str, pd.Timestamp, date, float]]:
    """The first print for a month: the earliest realtime_start vintage."""
    sel = [row for row in rows if row[0] == month]
    if not sel:
        return []
    first_start = min(row[1] for row in sel)
    return [row for row in sel if row[1] == first_start]


def _open_vintage(
    rows: list[tuple[str, pd.Timestamp, date, float]], month: str
) -> list[tuple[str, pd.Timestamp, date, float]]:
    """The latest revised value: the open-ended (9999-12-31) vintage."""
    return [row for row in rows if row[0] == month and row[2] == FOREVER]


def _window(row: tuple[str, pd.Timestamp, date, float]) -> str:
    return f"{row[1].strftime('%Y-%m-%d')}..{row[2].isoformat()}"


def _indep_payroll_change(
    rows: list[tuple[str, pd.Timestamp, date, float]], month: str, release: pd.Timestamp
) -> float | None:
    """level(reference month) - level(prior month), both from the same vintage
    active on the release date — computed here, not by the producer."""
    current = _active_on(rows, month, release)
    prior = _active_on(rows, _prior_month(month), release)
    if len(current) != 1 or len(prior) != 1:
        return None
    return float(Decimal(str(current[0][3])) - Decimal(str(prior[0][3])))


def _indep_percent_mom(
    rows: list[tuple[str, pd.Timestamp, date, float]], month: str, release: pd.Timestamp
) -> float | None:
    """percent month-over-month from the same vintage's two levels (float math,
    a deliberately different arithmetic path from the producer's Decimals)."""
    current = _active_on(rows, month, release)
    prior = _active_on(rows, _prior_month(month), release)
    if len(current) != 1 or len(prior) != 1:
        return None
    return (current[0][3] / prior[0][3] - 1.0) * 100.0


# --------------------------------------------------------------- properties ----
def v1_p1(stores: dict, raw: dict) -> str:
    """P1 Exact release, period and units, first print kept (not the revision)."""
    from engine.release_target_truth import reconstruct_release_target

    pay_rel = pd.Timestamp(PAYEMS_RELEASE)
    prod_pay = reconstruct_release_target(
        stores["PAYEMS"], series_id="PAYEMS", period=PAYEMS_PERIOD, release_date=PAYEMS_RELEASE
    )
    indep_pay = _indep_payroll_change(raw["PAYEMS"], PAYEMS_PERIOD, pay_rel)
    pay_latest_cur = _open_vintage(raw["PAYEMS"], PAYEMS_PERIOD)
    pay_latest_pri = _open_vintage(raw["PAYEMS"], _prior_month(PAYEMS_PERIOD))
    latest_pay = (
        float(Decimal(str(pay_latest_cur[0][3])) - Decimal(str(pay_latest_pri[0][3])))
        if len(pay_latest_cur) == 1 and len(pay_latest_pri) == 1
        else None
    )

    cpi_rel = pd.Timestamp(CPI_RELEASE)
    prod_cpi = reconstruct_release_target(
        stores["CPIAUCSL"], series_id="CPIAUCSL", period=CPI_PERIOD, release_date=CPI_RELEASE
    )
    indep_cpi = _indep_percent_mom(raw["CPIAUCSL"], CPI_PERIOD, cpi_rel)
    cpi_latest_cur = _open_vintage(raw["CPIAUCSL"], CPI_PERIOD)
    cpi_latest_pri = _open_vintage(raw["CPIAUCSL"], _prior_month(CPI_PERIOD))
    latest_cpi = (
        (cpi_latest_cur[0][3] / cpi_latest_pri[0][3] - 1.0) * 100.0
        if len(cpi_latest_cur) == 1 and len(cpi_latest_pri) == 1
        else None
    )

    pay_ok = (
        prod_pay["status"] == "ok"
        and prod_pay["period"] == PAYEMS_PERIOD
        and prod_pay["prior_period"] == _prior_month(PAYEMS_PERIOD)
        and prod_pay["release_date"] == PAYEMS_RELEASE
        and prod_pay["unit"] == "thousands"
        and indep_pay is not None
        and abs(float(prod_pay["payroll_change_thousands"]) - indep_pay) < 1e-9
    )
    pay_neg = (
        pay_ok
        and latest_pay is not None
        and abs(latest_pay - indep_pay) > 1e-9
        and abs(float(prod_pay["payroll_change_thousands"]) - latest_pay) > 1e-9
    )
    cpi_ok = (
        prod_cpi["status"] == "ok"
        and prod_cpi["period"] == CPI_PERIOD
        and prod_cpi["release_date"] == CPI_RELEASE
        and prod_cpi["unit"] == "percent"
        and indep_cpi is not None
        and abs(float(prod_cpi["latent_change"]) - indep_cpi) < 1e-9
    )
    cpi_neg = (
        cpi_ok
        and latest_cpi is not None
        and abs(latest_cpi - indep_cpi) > 1e-9
        and abs(float(prod_cpi["latent_change"]) - latest_cpi) > 1e-9
    )
    verdict = "PROVEN" if pay_ok and pay_neg and cpi_ok and cpi_neg else "PARTIAL"
    prod_pay_change = prod_pay.get("payroll_change_thousands")
    prod_cpi_change = prod_cpi.get("latent_change")
    evidence = (
        f"PAYEMS {PAYEMS_PERIOD} rel {PAYEMS_RELEASE}: producer "
        f"{_or_na(float(prod_pay_change) if prod_pay_change is not None else None, '+.1f')}k "
        f"unit={prod_pay.get('unit')} equals indep same-vintage "
        f"{_or_na(indep_pay, '+.1f')}k, latest-vintage {_or_na(latest_pay, '+.1f')}k "
        f"differs and producer kept first print; CPIAUCSL {CPI_PERIOD} rel "
        f"{CPI_RELEASE}: producer "
        f"{_or_na(float(prod_cpi_change) if prod_cpi_change is not None else None, '.4f')}% "
        f"unit={prod_cpi.get('unit')} equals indep, latest-vintage "
        f"{_or_na(latest_cpi, '.4f')}% differs. "
        "engine/release_target_truth.py:194 tests/test_release_target_truth.py:108"
    )
    print(f"V1 P1 {verdict} {evidence}")
    return verdict


def v1_p2(stores: dict, raw: dict) -> str:
    """P2 First print versus revision: radar takes current+prior from one vintage."""
    from engine.release_target_truth import reconstruct_release_target

    release = pd.Timestamp(PAYEMS_RELEASE)
    prior_month = _prior_month(PAYEMS_PERIOD)
    prod = reconstruct_release_target(
        stores["PAYEMS"], series_id="PAYEMS", period=PAYEMS_PERIOD, release_date=PAYEMS_RELEASE
    )
    same_vintage = _active_on(raw["PAYEMS"], prior_month, release)
    first_print = _earliest(raw["PAYEMS"], prior_month)
    latest = _open_vintage(raw["PAYEMS"], prior_month)
    radar_half = (
        prod["status"] == "ok"
        and len(same_vintage) == 1
        and len(first_print) == 1
        and len(latest) == 1
        and float(prod["prior_level_same_vintage"]) == same_vintage[0][3]
        and prod["basis"] == "same_release_vintage"
        and prod["cross_vintage_fallback_used"] is False
        and len({same_vintage[0][3], first_print[0][3], latest[0][3]}) == 3
    )
    verdict = "PARTIAL" if radar_half else "ABSENT"
    prior_used = prod.get("prior_level_same_vintage")
    prior_used = float(prior_used) if prior_used is not None else None
    first_level = first_print[0][3] if first_print else None
    latest_level = latest[0][3] if latest else None
    evidence = (
        f"radar half observed: PAYEMS {PAYEMS_PERIOD} rel {PAYEMS_RELEASE} "
        f"prior_level_same_vintage={_or_na(prior_used, '.1f')} is the release-vintage "
        f"row, distinct from prior first print {_or_na(first_level, '.1f')} and latest "
        f"{_or_na(latest_level, '.1f')}; news half unexercised offline: macro_surprise "
        "reads FRED latest-revised only (network). engine/release_target_truth.py:194 "
        "engine/macro_surprise.py:8 tests/test_release_target_truth.py:45"
    )
    print(f"V1 P2 {verdict} {evidence}")
    return verdict


def v1_p3(scratch: Path) -> str:
    """P3 Dated expectation or honestly labelled alternative benchmark."""
    from engine.release_market_context import get_kalshi_implied

    # SYNTH kalshi bracket-ladder store. The stated expectation comes from the
    # input itself: the fresher summary row says implied_median 0.30, an older
    # summary row says 0.12 (latest asof must win), and a non-summary bracket
    # row must be ignored. Stamps are live dates because the producer's MRI-R33
    # staleness gate judges the parquet's stamp column against the real clock
    # (the repo fixtures follow the same discipline); no date is printed.
    fresh = date.today().isoformat()
    older = (date.today() - timedelta(days=2)).isoformat()
    cols = [
        "asof_date", "release_type", "period", "strike", "p_survival", "price_type",
        "is_summary", "implied_median", "p_above_lowest_strike",
        "monotonicity_corrected", "n_brackets", "event_ticker", "close_time",
    ]
    rows = [
        [older, "cpi", "2026-06", float("nan"), None, "summary", True,
         0.12, 0.61, False, 7, "KXCPI-SYNTH", None],
        [fresh, "cpi", "2026-06", float("nan"), None, "summary", True,
         0.30, 0.58, False, 7, "KXCPI-SYNTH", None],
        [fresh, "cpi", "2026-06", 0.3, 0.42, "mid", False,
         None, None, None, None, "KXCPI-SYNTH", None],
    ]
    path = scratch / "SYNTH_kalshi_releases.parquet"
    pd.DataFrame(rows, columns=cols).to_parquet(path, index=False)

    out = get_kalshi_implied("cpi_headline", "2026-06", path)
    missing = get_kalshi_implied("cpi_headline", "2026-06", scratch / "absent.parquet")
    positive = (
        out is not None
        and out.get("source") == "kalshi"
        and abs(float(out.get("implied_median")) - 0.30) < 1e-9
        and str(out.get("asof")) == fresh
        and int(out.get("n_brackets")) == 7
    )
    negative = missing is None
    verdict = "PROVEN" if positive and negative else "PARTIAL"
    got = "None" if out is None else f"{float(out['implied_median']):.2f}"
    evidence = (
        f"SYNTH kalshi ladder (2 summary rows 0.12 older/0.30 fresh + 1 bracket row): "
        f"producer returned source=kalshi implied_median={got} asof=fresh stamp "
        f"n_brackets=7 (dated, labelled, 0.30 stated by the SYNTH row); missing parquet "
        f"-> {type(missing).__name__}, no invented expectation. "
        "engine/release_market_context.py:331 tests/test_release_market_context.py:534"
    )
    print(f"V1 P3 {verdict} {evidence}")
    return verdict


def v1_p4() -> str:
    """P4 No fabricated consensus: MRI-R5 'benchmark' never 'consensus'."""
    from engine.rates_inflation_command import _build_inflation_row, _build_market_check

    market_check = _build_market_check(
        {"implied": {"m1": 25.0}, "implied_bp_12m": -25.0,
         "headline_en": "SYNTH path", "headline_zh": "SYNTH-zh"},
        {"asof": "2026-10-30", "events": [{
            "key": "synth_ev", "label_en": "SYNTH CPI event", "label_zh": "SYNTH-zh",
            "top": {"outcome": "hot", "prob": 0.62, "chg_pp": 0.1},
        }]},
    )
    label_ok = (
        market_check["prediction_markets"]["events"][0]["type"] == "market_implied_benchmark"
        and "benchmark" in market_check["benchmark_note_en"]
        and "consensus" not in json.dumps(market_check, ensure_ascii=False).lower()
    )
    # Discriminating negative: feed a SYNTH string carrying the banned EN and ZH
    # words through a display-row producer and watch whether anything refuses it.
    synth_consensus = "SYNTH consensus 共识 regime"
    row = _build_inflation_row(
        {"state": {"inflation": {"regime": synth_consensus}, "expectations": {}}}, []
    )
    passthrough = row.get("regime") == synth_consensus
    if label_ok and not passthrough:
        verdict = "PROVEN"
        detail = "runtime guard refused/scrubbed the SYNTH consensus string"
    elif label_ok and passthrough:
        verdict = "PARTIAL"
        detail = "SYNTH string 'consensus/共识' passed through _build_inflation_row verbatim; no runtime guard exists"
    else:
        verdict = "ABSENT"
        detail = "benchmark labelling not emitted for the SYNTH input"
    evidence = (
        f"market_check labels SYNTH event type=market_implied_benchmark with benchmark "
        f"note, no consensus in output; but {detail}. Ban is the RIC-R9 docstring law "
        "plus the render test only. engine/rates_inflation_command.py:18 "
        "engine/rates_inflation_command.py:1432 tests/test_release_radar_render.py:124"
    )
    print(f"V1 P4 {verdict} {evidence}")
    return verdict


def v1_p5(raw: dict) -> str:
    """P5 Later revision retained in the committed all-vintage store."""
    rows = [row for row in raw["PAYEMS"] if row[0] == PAYEMS_PERIOD]
    rows.sort(key=lambda row: row[1])
    distinct = sorted({row[3] for row in rows})
    first = rows[0] if rows else None
    last = rows[-1] if rows else None
    retained = (
        first is not None
        and len(distinct) >= 2
        and first[3] != last[3]
        and _window(first) != _window(last)
    )
    verdict = "PARTIAL" if retained else "ABSENT"
    first_txt = f"{first[3]:.1f} window {_window(first)}" if first else "n/a"
    last_txt = f"{last[3]:.1f} window {_window(last)}" if last else "n/a"
    evidence = (
        f"PAYEMS {PAYEMS_PERIOD} keeps {len(distinct)} distinct vintage values: first "
        f"print {first_txt}, later {last_txt}; news path keeps only the latest revised "
        "level (macro_surprise), so retention is radar-side. "
        "engine/release_target_truth.py:163 tests/test_release_target_truth.py:339"
    )
    print(f"V1 P5 {verdict} {evidence}")
    return verdict


def v1_p6(news_pulls_truth: bool) -> str:
    """P6 Radar and news macro explanation agree (shared target source)."""
    radar_src = (ROOT / "scripts" / "build_release_forecast.py").read_text(encoding="utf-8")
    import_lines = [
        index + 1
        for index, line in enumerate(radar_src.splitlines())
        if "from engine.release_target_truth import" in line
    ]
    radar_half = bool(import_lines)
    news_separate = not news_pulls_truth
    verdict = "PARTIAL" if radar_half and news_separate else "ABSENT"
    first_import = import_lines[0] if import_lines else 0
    evidence = (
        f"radar half observed (P1/P2 producer outputs): radar targets come from "
        f"engine.release_target_truth, imported at "
        f"scripts/build_release_forecast.py:{first_import}; news half shares no target: "
        f"fresh import of engine.macro_surprise left truth unloaded "
        f"(sys.modules pull={news_pulls_truth}), news consumes macro_surprise at "
        "scripts/build_news.py:340; no shared agreement artifact, source probe only. "
        "no-test"
    )
    print(f"V1 P6 {verdict} {evidence}")
    return verdict


def v1_p7() -> str:
    """P7 Brain answer agrees: does any app/ module read the radar artifact?"""
    app_files = sorted((ROOT / "app").glob("*.py"))
    readers = [
        path.name for path in app_files
        if "release_forecast" in path.read_text(encoding="utf-8", errors="replace")
    ]
    verdict = "ABSENT" if not readers else "PARTIAL"
    evidence = (
        f"probe: {len(readers)} of {len(app_files)} app modules mention "
        f"release_forecast{'' if not readers else ' (' + ','.join(readers) + ')'}; the "
        "Brain run surface registers and pumps answer streams with no radar read "
        "(nearest code app/brain_runs.py:214); the only release_forecast consumer is "
        "the signed-in browser fetch at templates/dashboard.html.j2:11546. no-test"
    )
    print(f"V1 P7 {verdict} {evidence}")
    return verdict


def v1_p8() -> str:
    """P8 The displayed release radar is a signed-in surface."""
    lines = (ROOT / "config" / "site_access.yml").read_text(encoding="utf-8").splitlines()
    hits = [
        index for index, line in enumerate(lines, 1)
        if line.strip() == "- /macrodata/"
    ]
    tier = ""
    if hits:
        for line in lines[: hits[0]]:
            stripped = line.strip()
            if line and not line[0].isspace() and stripped.endswith(":"):
                tier = stripped[:-1]
    gated = bool(hits) and tier not in {"public", "anonymous"}
    verdict = "HUMAN_GATE" if gated else "PARTIAL"
    gate_line = hits[0] if hits else 0
    evidence = (
        f"radar JSON serves at /macrodata/release_forecast.json; prefix /macrodata/ is "
        f"gated under tier '{tier}' at config/site_access.yml:{gate_line} — an "
        "authenticated session is required (templates/dashboard.html.j2:11546 fetch); "
        "the offline proof stops at the committed artifact. "
        "config/site_access.yml:714 tests/test_release_radar_render.py:157"
    )
    print(f"V1 P8 {verdict} {evidence}")
    return verdict


# --------------------------------------------------------------------- main ----
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", default=None, help="directory for all temp artifacts")
    args = parser.parse_args()
    scratch = Path(args.scratch) if args.scratch else Path(tempfile.mkdtemp())
    scratch.mkdir(parents=True, exist_ok=True)

    # P6 news-half isolation probe, observed BEFORE this script imports
    # engine.release_target_truth for the radar half (P1/P2/P5).
    import engine.macro_surprise  # noqa: F401 — import graph is the observation
    news_pulls_truth = "engine.release_target_truth" in sys.modules

    from engine.release_target_truth import load_full_vintage_parquets

    stores: dict[str, pd.DataFrame] = {}
    raw: dict[str, list[tuple[str, pd.Timestamp, date, float]]] = {}
    for series in ("PAYEMS", "CPIAUCSL"):
        path = ROOT / "data" / "fred_vintage" / "release_targets" / f"{series}_all_vintages.parquet"
        stores[series] = load_full_vintage_parquets(path, series_id=series)
        raw[series] = _raw_rows(stores[series])

    verdicts = [
        v1_p1(stores, raw),
        v1_p2(stores, raw),
        v1_p3(scratch),
        v1_p4(),
        v1_p5(raw),
        v1_p6(news_pulls_truth),
        v1_p7(),
        v1_p8(),
    ]
    tally = {"PROVEN": 0, "PARTIAL": 0, "ABSENT": 0, "HUMAN_GATE": 0}
    for verdict in verdicts:
        tally[verdict] += 1
    print(
        f"V1 SUMMARY proven={tally['PROVEN']} partial={tally['PARTIAL']} "
        f"absent={tally['ABSENT']} human_gate={tally['HUMAN_GATE']} "
        "rung=COMMITTED_ARTIFACT"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
