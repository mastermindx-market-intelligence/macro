#!/usr/bin/env python3
"""Run the frozen Prophet beta-first evaluation and write ``site/prophet/beta_evaluation.json``.

Usage:
    python scripts/run_prophet_beta_evaluation.py [--prices-dir DIR] [--out PATH] [--bootstrap B]

Refuses to run unless ``research/prophet_v4/beta_first_evaluation/protocol_header_v1.json``
hashes to ``engine.prophet_beta_evaluation.FROZEN_HEADER_SHA256``.

Prices: per-ticker ``<TICKER>.parquet`` files with an adjusted ``close`` and raw
``close_price`` column (the repo's ``data/yahoo`` layout). ``--prices-dir`` defaults to the
repo's ``data/yahoo`` when present, else ``$PROPHET_EVAL_PRICES``. Raw vendor bytes are read,
never written into the repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import prophet_beta_evaluation as ev  # noqa: E402

LABELS = {
    "C1_passive_market": "Passive market (SPY)",
    "C2_simple_participation": "Simple participation (SPY above 200-day average, else cash)",
    "C3_sector_allocation_only": "Sector allocation only (top-3 sector ETFs)",
    "C4_member_selection_only": "Member selection only (sector-neutral S&P 1500 names)",
    "C5_joint_sector_and_name": "Joint sector + member (top-3 sectors x top names)",
    "C6_exact_incumbent_prophet": "Incumbent Prophet book, as built",
    "C7_independent_emergence": "Prophet plans outside leading sectors",
    "C6A_context_aligned_prophet": "Prophet plans inside leading sectors (diagnostic)",
    "X6_exposure_matched_reference": "Exposure-weight arithmetic reference only (SPY/BIL at the book's invested weight)",
}


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_artifact_atomic(out: Path, text: str) -> None:
    """Write the artifact via temp file + rename so readers never see a partial.

    A crash or timeout mid-write leaves at most a ``.beta_evaluation.tmp.*``
    sibling behind; the previous committed artifact stays intact until the
    rename. The nightly step removes stale temp siblings before each run.
    """
    tmp = out.with_name(f".beta_evaluation.tmp.{os.getpid()}")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, out)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def git(*args) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def load_jsonl(p: Path) -> tuple[list[dict], int]:
    """Parse JSONL, skipping blank lines and ``#`` documentation comments.

    The malformed-row counter is reserved for actual bad data rows; schema comment
    headers are not data defects (review NOTE).
    """
    rows, bad = [], 0
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            bad += 1
    return rows, bad


def load_prices(tickers, prices_dir: Path, cal: pd.DatetimeIndex, root: Path, pin: str):
    """Load per-ticker parquets with every byte verified against the data pin.

    A ticker absent from the pin is counted missing (it has no pinned price data at
    all). A local file is used only when its git blob id equals the pin's blob id;
    otherwise the exact pinned blob is read instead (audit RUN-D ZWS finding: the
    pre-correction run counted a ticker missing whose pinned blob exists).
    """
    import io as _io
    ls = subprocess.run(["git", "--no-optional-locks", "-C", str(root), "ls-tree", "-r", pin,
                         "data/yahoo"], capture_output=True, text=True)
    if ls.returncode != 0:
        raise SystemExit(f"cannot read the data pin {pin} tree for data/yahoo: {ls.stderr.strip()}")
    pin_ids: dict[str, str] = {}
    for line in ls.stdout.splitlines():
        meta, path = line.split("\t", 1)
        pin_ids[path.split("/")[-1][:-8]] = meta.split()[2]
    reader = subprocess.Popen(["git", "--no-optional-locks", "-C", str(root), "cat-file", "--batch"],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    def pin_blob(path: str) -> bytes | None:
        reader.stdin.write(f"{pin}:{path}\n".encode()); reader.stdin.flush()
        info = reader.stdout.readline().decode().strip().split()
        if len(info) != 3 or info[1] != "blob":
            return None
        b = reader.stdout.read(int(info[2]))
        reader.stdout.read(1)
        return b
    adj, raw, missing, from_pin = {}, {}, [], []
    digest = hashlib.sha256()
    for t in sorted(set(tickers)):
        rel = f"data/yahoo/{t}.parquet"
        pid_ = pin_ids.get(t)
        if pid_ is None:
            missing.append(t)          # no pinned price data exists for this ticker
            continue
        b = None
        f = prices_dir / f"{t}.parquet"
        if f.exists():
            loc = subprocess.run(["git", "--no-optional-locks", "-C", str(root), "hash-object",
                                  str(f)], capture_output=True, text=True).stdout.strip()
            if loc == pid_:
                b = f.read_bytes()
        if b is None:
            b = pin_blob(rel)
            if b is None:
                raise SystemExit(f"data pin {pin} lacks a readable blob for {rel}")
            from_pin.append(t)
        digest.update(t.encode() + b"\0" + hashlib.sha256(b).digest())
        d = pd.read_parquet(_io.BytesIO(b))
        d.index = pd.to_datetime(d.index)
        d = d[~d.index.duplicated(keep="last")].sort_index()
        adj[t] = d["close"].reindex(cal)
        raw[t] = (d["close_price"] if "close_price" in d.columns else d["close"]).reindex(cal)
    reader.stdin.close(); reader.wait()
    return pd.DataFrame(adj), pd.DataFrame(raw), missing, digest.hexdigest(), from_pin


class PinnedInputs:
    """Non-price inputs read from the frozen data pin; local bytes never substitute.

    The pre-correction runner read the working tree's copies and recorded their hashes
    without comparing them to the pin (audit RUN-D input-bytes finding). Here every
    plans/ledger/corrections/quarantine/disclosures/membership/sectors blob is read at
    the pin; a blob absent from the pin aborts the run (fail closed).
    """

    def __init__(self, root: Path, pin: str):
        self.root, self.pin = root, pin
        self._proc = subprocess.Popen(["git", "--no-optional-locks", "-C", str(root),
                                       "cat-file", "--batch"],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.sha: dict[str, str] = {}

    LOGICAL = {   # validator-safe names (raw paths contain a forbidden substring)
        "site/prophet/index.json": "plans_index",
        "data/prophet/ledger.jsonl": "resolution_log",
        "data/prophet/ledger_corrections.jsonl": "resolution_corrections",
        "data/prophet/ledger_quarantine.json": "resolution_quarantine",
        "data/prophet/plan_corrections.jsonl": "plan_corrections",
        "data/prophet/backfill_disclosures.json": "backfill_disclosures",
        "data/breadth/sp1500_pit_membership.parquet": "pit_membership",
        "data/breadth/sp1500_pit_sectors.parquet": "pit_sectors",
    }

    def blob(self, rel: str) -> bytes:
        self._proc.stdin.write(f"{self.pin}:{rel}\n".encode()); self._proc.stdin.flush()
        info = self._proc.stdout.readline().decode().strip().split()
        if len(info) != 3 or info[1] != "blob":
            raise SystemExit(f"data pin {self.pin} lacks required input {rel}")
        b = self._proc.stdout.read(int(info[2]))
        self._proc.stdout.read(1)
        self.sha[self.LOGICAL.get(rel, rel)] = hashlib.sha256(b).hexdigest()
        return b

    def text(self, rel: str) -> str:
        return self.blob(rel).decode("utf-8")

    def json(self, rel: str):
        return json.loads(self.text(rel))

    def jsonl(self, rel: str) -> tuple[list[dict], int]:
        rows, bad = [], 0
        for line in self.text(rel).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                bad += 1
        return rows, bad

    def close(self) -> None:
        try:
            self._proc.stdin.close(); self._proc.wait()
        except OSError:
            pass


def _pp(x: float | None, signed: bool = True) -> str:
    if x is None:
        return "n/a"
    return f"{x * 100:+.1f} pp" if signed else f"{x * 100:.1f}%"


def _pct(x: float | None) -> str:
    """A standalone return is a percentage, not a percentage-point difference."""
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def _ci_pp(c) -> str:
    return "n/a" if not c else f"[{c[0] * 100:+.1f}, {c[1] * 100:+.1f}] pp"


def plain_words(a: dict) -> tuple[list[str], list[str]]:
    """Plain-language headline and limitations computed from the artifact's own numbers."""
    c = {r["id"]: r for r in a["comparators"]}
    k = {r["id"]: r for r in a["contrasts"]["rows"]}
    c6, w = c["C6_exact_incumbent_prophet"], a["window"]
    d6 = a["post_hoc_diagnostics"]["C6_exact_incumbent_prophet"]
    es = a["event_study"]["horizons"]
    pop = a["population"]["excluded_cohort"]
    head = [
        f"Release level: descriptive only (L0). The predeclared global minimum for any accepted historical claim "
        f"requires all of: 252 sessions (this window has {w['sessions']}), an 8% SPY drawdown (deepest here is "
        f"{_pct(w['spy_max_drawdown'])}) and 150 resolved positions (this window has "
        f"{c6['sample']['resolved']} — the only gate that passes). Two of three fail, so every job stays L0.",
        f"Market over the window: SPY {_pct(w['spy_total_return'])} total return, deepest drawdown {_pct(w['spy_max_drawdown'])}.",
        f"Population: live-published plans only. {pop['era_plans_excluded']} outage-reconstructed plans that no user "
        f"could see on their nominal publication dates are excluded from every headline number (deviation D5); "
        f"the superseded as-run numbers are retained under sensitivity.superseded_as_run.",
        f"Corrected {a['correction']['date']} after a two-run independent audit: final-close trade costs are now "
        f"charged and price bytes are verified against the data pin (v1 C6 total was "
        f"{_pct(a['correction']['figures_superseded']['C6_exact_incumbent_prophet']['total_net_return'])}). "
        f"Superseded figures sit beside the corrected ones; the verdict — L0, not distinguishable from passive — "
        f"is unchanged.",
        f"Incumbent Prophet book (as built, {c6['sample']['positions']} positions): {_pct(c6['total_net_return'])} net, "
        f"{_pp(c6['vs_passive_market']['total_diff'])} versus SPY, 95% CI {_ci_pp(c6['vs_passive_market']['total_diff_ci95'])}. "
        f"The interval includes zero: this is not evidence of outperformance, and the sample is far too short.",
        f"Beta capture: beta {c6['beta_vs_market']:.2f} (95% CI {c6['beta_ci95'][0]:.2f} to {c6['beta_ci95'][1]:.2f}), "
        f"mean invested weight {c6['mean_invested'] * 100:.0f}%; upside capture {c6['upside_capture']:.2f}, "
        f"downside capture {c6['downside_capture']:.2f}.",
        f"Without its largest single contributor ({d6['without_top_contributor']['dropped_asset']}) the book is "
        f"{_pp(d6['without_top_contributor']['excess_total_vs_spy'])} versus SPY "
        f"(CI {_ci_pp(d6['without_top_contributor']['excess_total_ci95'])}); without the three largest "
        f"({', '.join(d6['without_top3_contributors']['dropped_assets'])}) it is "
        f"{_pp(d6['without_top3_contributors']['excess_total_vs_spy'])} — the sign of the whole result rests on "
        f"three names.",
        f"Live-published plans held for a fixed 21 sessions without Prophet's exits differed from SPY by "
        f"{_pp(es['21']['excess_vs_spy']['mean'])} on average (date-cluster CI {_ci_pp(es['21']['excess_vs_spy']['ci95_date_cluster'])}); "
        + ("most of that gap was the stock versus its own sector ETF, not the sector choice."
         if abs(es["21"]["stock_minus_sector_etf"]["mean"]) > abs(es["21"]["sector_etf_minus_spy"]["mean"])
         else "most of that gap came from the sector choice, not the stock versus its sector."),
        f"That stock-versus-sector number has two floors under it. An average point-in-time member of the same "
        f"sector trailed its own cap-weighted fund by "
        f"{_pp(a['event_study']['member_benchmark']['horizons']['21']['equal_weight_member_minus_sector_etf']['mean'])} "
        f"at 21 sessions — that floor is the yardstick, not member choice. The picks sat a further "
        f"{_pp(a['event_study']['member_benchmark']['horizons']['21']['stock_minus_equal_weight_members']['mean'])} "
        f"below that average member (CI "
        f"{_ci_pp(a['event_study']['member_benchmark']['horizons']['21']['stock_minus_equal_weight_members']['ci95_date_cluster'])}); "
        f"a random-member placebo over the same dates and sectors lands inside "
        f"{_pp(a['event_study']['member_benchmark']['horizons']['21']['placebo_random_same_sector']['p2_5'])} to "
        f"{_pp(a['event_study']['member_benchmark']['horizons']['21']['placebo_random_same_sector']['p97_5'])}. "
        f"The independent diagnosis attributes more of the remainder to the characteristics of what was picked "
        f"(short-term bounce, medium-term laggards, off-index speculative names); what is left does not survive "
        f"its multiplicity correction. No claim of negative member selection, and no claim of its absence.",
        "Sector rotation alone, sector-neutral member selection alone and their combination did not beat SPY on this "
        f"window (K3 {_pp(k['K3']['ann_diff'])}/yr, K4 {_pp(k['K4']['ann_diff'])}/yr, K5 {_pp(k['K5']['ann_diff'])}/yr "
        "annualised; none significant after Holm). Insignificant results mean value is not shown, not that there is none.",
        "The exposure-matched reference (X6) is an exposure-weight arithmetic reference only: it matches risky weight "
        "alone, and because the book is essentially fully invested, K2 nearly repeats the SPY comparison (K1) and "
        "cannot identify member-selection value.",
        "Prophet plans inside leading sectors did better than plans outside them in this window "
        f"(K7 {_pp(k['K7']['ann_diff'])}/yr annualised, Holm p {k['K7']['p_holm']:.2f}); this is not significant"
        + (" and its largest contributor is the same single name." if
           a["post_hoc_diagnostics"]["C6A_context_aligned_prophet"]["without_top_contributor"]["dropped_asset"]
           == d6["without_top_contributor"]["dropped_asset"] else "."),
        "Nothing here shows that sector context or member selection adds value beyond market participation.",
    ]
    lim = [
        f"Short sample: one {a['window']['sessions']}-session window (SPY {_pp(a['window']['spy_total_return'])}); "
        "no rebound or crash regime was observed.",
        "Annualised differentials from 63 daily returns are very noisy; read total-window differences and their intervals.",
        f"Population (deviation D5): {pop['era_plans_excluded']} outage-reconstructed plans "
        f"({pop['of_which_replayed_receipted_bake']} receipted replays, "
        f"{pop['of_which_synthetic_board_reconstructions']} synthetic-board reconstructions) are excluded because "
        "their earliest auditable availability is after their nominal publication session; the correction was made "
        "after outcomes were seen, follows a rule that predates the evaluation, and lowers the headline.",
        "X6 is an exposure-weight arithmetic reference, not a selection-matched comparator: it matches only risky "
        "weight, so K2 nearly repeats K1. A comparator matched on eligible cohort, concentration, sector/factor "
        "exposure, timing and costs requires a new pre-declared protocol; X6 is not replaced retrospectively.",
        f"Undated conversions: {len(a['population']['undated_conversions']['ids'])} era plans are terminal-state "
        f"'converted' with no dated fill in the snapshot; the C6 rule enters them at publication because the "
        f"header's literal text admits it. Excluding every one of them moves the book to "
        f"{_pct(a['sensitivity']['excluding_undated_conversions']['total_net_return'])} total, "
        f"{_pp(a['sensitivity']['excluding_undated_conversions']['excess_total_vs_spy'])} versus SPY "
        f"(CI {_ci_pp(a['sensitivity']['excluding_undated_conversions']['excess_total_ci95'])}, still spans zero). "
        f"Found by the 2026-11-11 independent audit; the sensitivity is not part of the frozen protocol.",
        f"Missing held marks: {a['coverage']['held_path_gaps']} held positions own assets whose close series stops "
        f"inside the window (delistings); the primary book zero-fills them (held flat), which flatters the book "
        f"relative to an unknown true price. A total-loss stress "
        f"({_pct(a['sensitivity']['missing_marks_total_loss_stress']['total_net_return'])} total, "
        f"{_pp(a['sensitivity']['missing_marks_total_loss_stress']['excess_total_vs_spy'])} versus SPY, CI "
        f"{_ci_pp(a['sensitivity']['missing_marks_total_loss_stress']['excess_total_ci95'])}) bounds the damage; "
        f"the affected positions are listed in coverage.held_path_gap_positions.",
        "Coverage basis: the 95%+ priced-share gate is measured on ENTRY marks only. It says nothing about marks "
        "after entry — the gapped held positions above are priced at entry and then run flat, so the gate passes "
        "while held-path completeness is a separate, disclosed quantity.",
        "Cost conventions (header-decided, stated plainly): costs are per side on traded notional at trade close, "
        "including the terminal trade (corrected 2026-11-11); C1 is 100% SPY held through the window with no "
        "terminal sale; the uninvested weight earns BIL without fee; X6 is arithmetic and cost-free by definition; "
        "annualisation is arithmetic (mean daily differential x 252) throughout.",
        f"Yardstick: the event study's stock-minus-sector-ETF leg grades picks against a cap-weighted fund. The "
        f"equal-weight member benchmark (event_study.member_benchmark, added 2026-11-11) shows an average "
        f"same-sector member trailing that fund by "
        f"{_pp(a['event_study']['member_benchmark']['horizons']['21']['equal_weight_member_minus_sector_etf']['mean'])} "
        f"at 21 sessions and "
        f"{_pp(a['event_study']['member_benchmark']['horizons']['42']['equal_weight_member_minus_sector_etf']['mean'])} "
        f"at 42; that share of the published leg is the yardstick, not member choice.",
        f"Off-index names: {a['sensitivity']['off_index_picks']['published_plans_off_index']} published plans "
        f"({a['sensitivity']['off_index_picks']['published_plans_off_index'] / max(a['sensitivity']['off_index_picks']['published_plans_total'], 1) * 100:.0f}% "
        f"of them) name stocks outside the point-in-time S&P 1500 at the signal date and carried "
        f"{_pp(a['sensitivity']['off_index_picks']['horizons']['21']['contribution_to_mean_gap'])} of the "
        f"21-session mean gap; the membership file records no change after 2026-06-02, so late-window non-membership "
        f"is uncertain in both directions (see sensitivity.off_index_picks.membership_file_limits).",
        a["population"]["mrna"]["price_authentication"] + "; it affects any population that admits the replayed plans.",
        "S&P 1500 point-in-time membership has no recorded change after 2026-06-02; "
        f"{len(a['coverage']['member_universe_missing_price_files'])} point-in-time members had no price file and were excluded.",
        "Sector labels are current-basis GICS, not the classification in force at each date.",
        "Prophet plans are read from the 2026-11-09 plan snapshot, not each plan's as-published bytes; entries use the "
        "publication clock and close-only fills, so results differ from the plan record's own same-bar outcomes.",
        "Model book: equal weight across open positions (per position, not per distinct ticker; no same-ticker "
        "overlaps occur in this sample, so the two coincide here). It is not user holdings, a portfolio "
        "recommendation or sizing advice.",
        "The event-study date-cluster intervals treat publication dates as independent although nearby dates share "
        "overlapping market paths, so those intervals are likely too narrow.",
        "Issuer-excluded peer counts are unavailable: identity is the listing ticker only.",
        "The eight catalog sleeves cannot be evaluated: plans carry no sleeve link. admission_class strata are reported instead.",
    ]
    return head, lim


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", default=None)
    ap.add_argument("--out", default=str(ROOT / "site/prophet/beta_evaluation.json"))
    ap.add_argument("--bootstrap", type=int, default=None)
    args = ap.parse_args(argv)

    header = ev.verify_header(ROOT / ev.HEADER_REL_PATH)          # refuses on mismatch
    st = header["statistics"]
    B = args.bootstrap or 10000
    seed = 20261110
    block, block_alt = 10, int(st["block_length_sensitivity"])
    win0 = pd.Timestamp(header["window"]["first_return_close"])
    win1 = pd.Timestamp(header["window"]["last_close"])
    warm = pd.Timestamp(header["window"]["warmup_from"])
    first_decision = pd.Timestamp("2026-08-07")
    sector_map = header["sector_map"]
    deviations: list[dict] = [
        {"id": "D1", "kind": "naming", "when": "before outcome access",
         "what": "reason/key names derived from 'ledger' renamed to 'recorded_*' / 'resolution_log'",
         "why": "lane-8 validator forbids key substrings incl. 'edge' (contained in 'ledger'); no method change"},
        {"id": "D2", "kind": "added_diagnostic", "when": "after outcome access",
         "what": "post_hoc_diagnostics: per-asset contribution concentration, concurrent position counts, Prophet books re-run without their single largest contributor",
         "why": "the C6 book's result was visibly driven by one name; disclosed as descriptive only, cannot change any release level or threshold"},
        {"id": "D3", "kind": "implementation_note", "when": "after outcome access",
         "what": "v1 (superseded): the last scheduled rule rebalance (decision 2026-11-05) executed at the final "
                 "close 2026-11-06 and its trading cost had no following return day and was not charged; corrected "
                 "2026-11-11 (see D6): the terminal trade cost is now charged against the final day's realised return "
                 "for every book whose target vector is defined at the final close",
         "why": "header schedule executes while t+1 <= last close; the v1 omission was at most one rebalance "
                "(< 0.1 pp for C3-C5); the correction charges it instead of approximating it away"},
        {"id": "D4", "kind": "presentation", "when": "after outcome access",
         "what": "event-study horizons with fewer than 5 distinct publication dates are marked status=too_few_dates",
         "why": "H=63 matured for a single publication date; a one-cluster bootstrap interval is degenerate and must not be displayed as uncertainty"},
        {"id": "D5", "kind": "population_correction", "when": "after outcome access (2026-11-10)",
         "what": None,   # filled in below, once the before/after numbers are computed
         "why": "the runner had treated backfilled plans as if historically published although their earliest auditable "
                "availability is their backfill receipt, after their nominal publication session (e.g. MRNA-BULL-20260616 "
                "entered at the 2026-08-10 close although instantiated 2026-08-11T05:32Z). research/PROPHET_OUTAGE_BACKFILL_2026_08.md "
                "forbids presenting reconstructed picks as live historical calls; that rule predates this evaluation. "
                "Correction made after outcomes were seen and it lowers the headline. Source: independent review "
                "REVIEW_beta_evaluation.md (sha256 6296bf4cb77d09e47f1311dbd46cd915a794e050ce7460a228ad821e7b13541a), "
                "BLOCKER finding, accepted by the programme CEO."},
        {"id": "D6", "kind": "implementation_note", "when": "after publication (2026-11-11)", "what": None,
         "why": None},   # engine-fee correction from the independent audit; filled in below
        {"id": "D7", "kind": "added_diagnostic", "when": "after publication (2026-11-11)", "what": None,
         "why": None},   # equal-weight member benchmark beside the cap-weighted ETF yardstick; filled below
        {"id": "D8", "kind": "added_diagnostic", "when": "after publication (2026-11-11)", "what": None,
         "why": None},   # off-index (non-S&P-1500) picks after-the-fact sensitivity; filled below
    ]

    prices_dir = Path(args.prices_dir or (ROOT / "data/yahoo" if (ROOT / "data/yahoo/SPY.parquet").exists()
                                          else os.environ.get("PROPHET_EVAL_PRICES", "")))
    spy = pd.read_parquet(prices_dir / "SPY.parquet")
    spy.index = pd.to_datetime(spy.index)
    cal = spy.index[(spy.index >= warm) & (spy.index <= win1)]
    dates = list(cal[(cal >= win0) & (cal <= win1)])
    assert len(dates) == header["window"]["sessions_inclusive"], len(dates)

    # inputs — every non-price input is read from the frozen data pin (audit RUN-D:
    # the pre-correction run recorded the header pin but read unverified working-tree
    # bytes; the pin and the tree happened to agree byte-for-byte, which is now proven)
    pin = header["data_pin"]["macro_commit"]
    pinned = PinnedInputs(ROOT, pin)
    idx_rel, led_rel = "site/prophet/index.json", "data/prophet/ledger.jsonl"
    index = pinned.json(idx_rel)
    plans = index["plans"]
    led_rows, led_bad = pinned.jsonl(led_rel)
    ledger = {r["id"]: dict(r) for r in led_rows}
    corr_rows, _ = pinned.jsonl("data/prophet/ledger_corrections.jsonl")
    applied_corr = 0
    for c in corr_rows:
        if c.get("field") == "close_date" and c.get("corrects_id") in ledger:
            ledger[c["corrects_id"]]["close_date"] = c.get("new_value")
            applied_corr += 1
    quarantine = {q["id"] for q in pinned.json("data/prophet/ledger_quarantine.json")["quarantined"]}
    for q in quarantine:
        ledger.pop(q, None)
    plan_corr_rows, _ = pinned.jsonl("data/prophet/plan_corrections.jsonl")
    corrected_ids = frozenset(r.get("corrects_id") for r in plan_corr_rows if r.get("corrects_id"))
    import io as _io
    pit = pd.read_parquet(_io.BytesIO(pinned.blob("data/breadth/sp1500_pit_membership.parquet")))
    pits = pd.read_parquet(_io.BytesIO(pinned.blob("data/breadth/sp1500_pit_sectors.parquet")))
    pit_label = {}
    for tk, g in pits.sort_values("membership_start").groupby("ticker"):
        lab = next((s for s in g["sector"] if isinstance(s, str) and s), None)
        if lab:
            pit_label[tk] = lab
    sector_of_ticker = {tk: sector_map.get(lab) for tk, lab in pit_label.items() if sector_map.get(lab)}

    era = [p for p in plans if p.get("selection_era") == ev.INCUMBENT_ERA]

    # ── origination cohorts, detected from the data (deviation D5) ────────────────
    # Non-live (outage-backfilled) plans may not be presented as live historical
    # calls (research/PROPHET_OUTAGE_BACKFILL_2026_08.md). The stamped
    # origination_mode set must equal the disclosure artifact's minted set in BOTH
    # directions; a mismatch is a data defect, not a judgment call.
    bf_disc = pinned.json("data/prophet/backfill_disclosures.json")
    window_kind = {w["id"]: w.get("kind") for w in bf_disc["windows"]}
    minted: dict[str, str] = {}      # plan_id -> window kind (replay | reconstruction)
    for w in bf_disc["backfills"]:
        for m in w["minted"]:
            minted[m["plan_id"]] = window_kind.get(w["id"], w.get("kind"))
    stamped = {p["id"] for p in plans if ev.is_backfilled(p)}
    if stamped != set(minted):
        raise SystemExit(f"origination receipts disagree with stamped plans: "
                         f"stamped-not-minted={sorted(stamped - set(minted))} "
                         f"minted-not-stamped={sorted(set(minted) - stamped)}")
    # every stamped plan must carry its backfill execution receipt
    missing_receipt = [p["id"] for p in plans if ev.is_backfilled(p) and not p.get("backfill_executed_at")]
    if missing_receipt:
        raise SystemExit(f"backfilled plans without backfill_executed_at receipt: {missing_receipt}")
    era_ids = {p["id"] for p in era}
    not_live = frozenset(stamped & era_ids)                     # primary-population exclusions
    replay_ids = {pid for pid, kind in minted.items() if kind == "replay"}
    recon_ids = {pid for pid, kind in minted.items() if kind != "replay"}
    replay_avail = {p["id"]: ev.auditable_first_availability(p) for p in era
                    if p["id"] in replay_ids}
    by_mode: dict[str, int] = {}
    for p in era:
        if ev.is_backfilled(p):
            m = str(p.get("origination_mode"))
            by_mode[m] = by_mode.get(m, 0) + 1

    plan_etf, disagreements, unmapped = {}, 0, 0
    for p in era:
        br = ((p.get("board_read") or {}).get("fields") or {}).get("sector") or {}
        br_lab = br.get("value") if br.get("state") == "available" else None
        pl = pit_label.get(p["asset"])
        if pl and br_lab and sector_map.get(pl) != sector_map.get(br_lab):
            disagreements += 1
        lab = pl or br_lab
        plan_etf[p["id"]] = sector_map.get(lab) if lab else None
        unmapped += plan_etf[p["id"]] is None

    act = pit[(pit["start_date"] <= win1) & (pit["end_date"].isna() | (pit["end_date"] >= first_decision))]
    tickers = set(ev.SECTOR_ETFS) | {ev.BENCH, ev.CASH} | {p["asset"] for p in era} | set(act["ticker"])
    closes, raw, missing, price_digest, prices_from_pin = load_prices(tickers, prices_dir, cal, ROOT, pin)
    rets = closes.pct_change(fill_method=None)
    tradable = closes.notna()
    cash_r = rets[ev.CASH].fillna(0.0)

    def bps(mult):
        etfs = set(ev.SECTOR_ETFS) | {ev.BENCH, ev.CASH}
        return lambda a: (header["execution"]["cost_bps_per_side"]["etf"] if a in etfs
                          else header["execution"]["cost_bps_per_side"]["stock"]) * mult

    # rule targets
    sched = ev.rule_schedule(cal, first_decision, win1, 21)
    t1 = ev.targets_c1(sched)
    t2 = ev.targets_c2(closes, cal, first_decision, win1)
    t3, c3_picks = ev.targets_c3(closes, cal, first_decision, win1)
    pre = cal[cal <= first_decision][-253:]
    sw = ev.style_weights(rets.loc[pre[1:], ev.BENCH], rets.loc[pre[1:], list(ev.SECTOR_ETFS)])
    t4, t5, uni_audit = ev.targets_c4_c5(closes, raw, cal, first_decision, win1, act, sector_of_ticker, sw)

    # Prophet positions — primary population is LIVE-PUBLISHED plans only (deviation D5):
    # the 16 outage-reconstructed era plans are excluded with reason not_live_origination.
    positions, excl, extra = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1,
                                                not_live_ids=not_live)
    pos_nc, excl_nc, _ = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1,
                                            excluded_ids=corrected_ids, not_live_ids=not_live)
    # sensitivity (a): the 13 receipted replays admitted from the first session at/after
    # their actual backfill_executed_at; the 3 synthetic-board reconstructions never admitted.
    pos_s1, excl_s1, _ = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1,
                                            not_live_ids=frozenset(recon_ids & era_ids),
                                            avail_floor=replay_avail)
    # superseded as-run population (the v1 population, retained verbatim; never the headline)
    pos_asrun, _, extra_asrun = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1)
    backfilled_entered_asrun = sorted({p.plan_id for p in pos_asrun} & not_live)
    subsets = {
        "C6_exact_incumbent_prophet": positions,
        "C7_independent_emergence": [p for p in positions if p.aligned is False],
        "C6A_context_aligned_prophet": [p for p in positions if p.aligned is True],
    }
    for cls in ("patience", "confirmation", "early_turn_starter"):
        subsets[f"S_{cls}"] = [p for p in positions if p.admission_class == cls]
    subsets["S6_drop_corrected"] = pos_nc

    targets = {"C1_passive_market": t1, "C2_simple_participation": t2,
               "C3_sector_allocation_only": t3, "C4_member_selection_only": t4,
               "C5_joint_sector_and_name": t5}
    for k, ps in subsets.items():
        targets[k] = ev.prophet_targets(ps, dates)

    books = {k: ev.simulate_book(dates, rets, cash_r, t, tradable, bps(1.0)) for k, t in targets.items()}
    books2 = {k: ev.simulate_book(dates, rets, cash_r, t, tradable, bps(2.0)) for k, t in targets.items()}

    rdates = pd.DatetimeIndex(dates[1:])
    rm = rets.loc[rdates, ev.BENCH].to_numpy()
    rc = cash_r.loc[rdates].to_numpy()
    inv6 = books["C6_exact_incumbent_prophet"].invested.to_numpy()
    rx6 = inv6 * rm + (1 - inv6) * rc
    inv3 = books["C3_sector_allocation_only"].invested.to_numpy()
    rx3 = inv3 * rm + (1 - inv3) * rc
    series = {k: b.net.to_numpy() for k, b in books.items()}
    series["X6_exposure_matched_reference"] = rx6
    series2 = {k: b.net.to_numpy() for k, b in books2.items()}
    series2["X6_exposure_matched_reference"] = rx6
    n = len(rm)
    idx10 = ev.stationary_bootstrap_indices(n, B, block, seed)
    idx21 = ev.stationary_bootstrap_indices(n, B, block_alt, seed)

    # comparator rows
    comp_rows = []
    order = list(ev.COMPARATOR_IDS) + ["C6A_context_aligned_prophet", "X6_exposure_matched_reference"]
    for cid in order:
        r = series[cid]
        pm = ev.point_metrics(r, rm, rc)
        vs = ev.bootstrap_vs(r, rm, rm, rc, idx10)
        b = books.get(cid)
        row = {"id": cid, "label": LABELS[cid], "status": "evaluated", "reason": None,
               "definition": header["comparators"][cid], **pm,
               "vs_passive_market": {**{k: vs[k] for k in ("ann_diff", "ann_diff_ci95", "total_diff",
                                                        "total_diff_ci95", "p_one_sided")},
                                  "reference_basis": "SPY total-return index, gross of costs (the costed passive "
                                                     "book is C1; it differs only by its one entry cost)"},
               "beta_ci95": vs["beta_ci95"], "upside_capture_ci95": vs["upside_capture_ci95"],
               "downside_capture_ci95": vs["downside_capture_ci95"],
               "window": {"first_return_close": str(win0.date()), "last_close": str(win1.date()),
                          "daily_returns": n}}
        if b is not None:
            traded = b.traded.to_numpy()
            row.update({"mean_invested": float(b.invested.mean()),
                        "time_in_market": float((b.invested > 1e-9).mean()),
                        "annual_turnover": float(traded.sum() / 2 * ev.TRADING_DAYS / n),
                        "costs_paid_total": float(-b.cost.sum()),
                        "no_fill_signals": int(b.no_fill), "stale_asset_days": int(b.stale_asset_days),
                        "no_entry_periods": int((b.invested <= 1e-9).sum())})
            row["at_2x_costs"] = {"total_net_return": ev.compound(series2[cid]),
                                  "ann_excess_vs_spy": float(np.mean(series2[cid] - rm) * ev.TRADING_DAYS)}
        else:
            row.update({"mean_invested": float(inv6.mean()), "time_in_market": float((inv6 > 0).mean()),
                        "annual_turnover": None, "costs_paid_total": 0.0, "no_fill_signals": 0,
                        "no_entry_periods": int((inv6 <= 1e-9).sum()),
                        "note": "reference series, no costs charged"})
        if cid in subsets:
            ps = subsets[cid]
            row["sample"] = {"positions": len(ps), "distinct_assets": len({p.asset for p in ps}),
                             "censored_open_at_window_end": sum(p.censored for p in ps),
                             "resolved": sum(not p.censored for p in ps)}
            row["hit_rate_vs_spy"] = ev.position_hits(ps, closes)
        comp_rows.append(row)

    # halves (descriptive)
    half = n // 2 + 1  # 32 returns in the first half per header
    halves = {}
    for cid in order:
        r = series[cid]
        halves[cid] = {"first": ev.point_metrics(r[:half], rm[:half], rc[:half]),
                       "second": ev.point_metrics(r[half:], rm[half:], rc[half:])}

    # contrasts
    fam = header["statistics"]["confirmatory_family_holm_alpha_0.05"]
    pairs = {"K1": ("C6_exact_incumbent_prophet", "C1_passive_market"),
             "K2": ("C6_exact_incumbent_prophet", "X6_exposure_matched_reference"),
             "K3": ("C3_sector_allocation_only", "C1_passive_market"),
             "K4": ("C4_member_selection_only", "C1_passive_market"),
             "K5": ("C5_joint_sector_and_name", "C4_member_selection_only"),
             "K6": ("C5_joint_sector_and_name", "C3_sector_allocation_only"),
             "K7": ("C6A_context_aligned_prophet", "C7_independent_emergence"),
             "K8": ("C2_simple_participation", "C1_passive_market")}

    def run_contrasts(ser, idx):
        out = {}
        for k, (a, b_) in pairs.items():
            out[k] = ev.bootstrap_vs(ser[a], ser[b_], rm, rc, idx)
        return out

    con = run_contrasts(series, idx10)
    hol = ev.holm({k: v["p_one_sided"] for k, v in con.items()})
    con21 = run_contrasts(series, idx21)
    hol21 = ev.holm({k: v["p_one_sided"] for k, v in con21.items()})
    con2 = run_contrasts(series2, idx10)
    contrasts = {}
    for k, (a, b_) in pairs.items():
        c = con[k]
        contrasts[k] = {"id": k, "a": a, "b": b_, "header_definition": fam[k],
                        "ann_diff": c["ann_diff"], "ann_diff_ci95": c["ann_diff_ci95"],
                        "total_diff": c["total_diff"], "total_diff_ci95": c["total_diff_ci95"],
                        **hol[k],
                        "block21": {"ann_diff_ci95": con21[k]["ann_diff_ci95"], **hol21[k]},
                        "at_2x_costs": {"ann_diff": con2[k]["ann_diff"],
                                        "ann_diff_ci95": con2[k]["ann_diff_ci95"]}}
    sec_pairs = {f"S_{c}": c for c in ("patience", "confirmation", "early_turn_starter")}
    sec_con = {k: ev.bootstrap_vs(series[k], rm, rm, rc, idx10) for k in sec_pairs}
    sec_hol = ev.holm({k: v["p_one_sided"] for k, v in sec_con.items()})
    secondary = {k: {"stratum": c, "positions": len(subsets[k]), "ann_diff_vs_spy": sec_con[k]["ann_diff"],
                     "ann_diff_ci95": sec_con[k]["ann_diff_ci95"], "beta_vs_market":
                     ev.point_metrics(series[k], rm, rc)["beta_vs_market"],
                     "mean_invested": float(books[k].invested.mean()), **sec_hol[k]}
                 for k, c in sec_pairs.items()}
    k3x = ev.bootstrap_vs(series["C3_sector_allocation_only"], rx3, rm, rc, idx10)

    # attribution
    attribution = {}
    for cid in ("C6_exact_incumbent_prophet", "C7_independent_emergence", "C6A_context_aligned_prophet"):
        attribution[cid] = ev.attribution_bridge(books[cid], rets, cash_r, ev.asset_sector_map(subsets[cid]))
        attribution[cid]["unit"] = "fraction (0.01 = 1 percentage point)"

    # post-hoc descriptive diagnostics (deviation D2: added after outcome access; no threshold change)
    diagnostics = {"label": "POST_HOC_DESCRIPTIVE_DIAGNOSTIC (not in the frozen header; cannot change any release level)"}
    for cid in ("C6_exact_incumbent_prophet", "C7_independent_emergence", "C6A_context_aligned_prophet"):
        contrib = ev.asset_contributions(books[cid], rets)
        pos_sum = float(contrib[contrib > 0].sum())
        top = contrib.index[-1] if len(contrib) else None
        drop = [p for p in subsets[cid] if p.asset != top]
        bk = ev.simulate_book(dates, rets, cash_r, ev.prophet_targets(drop, dates), tradable, bps(1.0))
        r_drop = bk.net.to_numpy()
        vs_drop = ev.bootstrap_vs(r_drop, rm, rm, rc, idx10)
        top3 = list(contrib.index[::-1][:3])
        drop3 = [p for p in subsets[cid] if p.asset not in top3]
        bk3 = ev.simulate_book(dates, rets, cash_r, ev.prophet_targets(drop3, dates), tradable, bps(1.0))
        r_d3 = bk3.net.to_numpy()
        vs_d3 = ev.bootstrap_vs(r_d3, rm, rm, rc, idx10)
        diagnostics[cid] = {
            "concurrent_positions": ev.concurrency(subsets[cid], dates),
            "top_contributors": [{"asset": a, "gross_contribution": float(v)} for a, v in contrib.iloc[::-1][:5].items()],
            "bottom_contributors": [{"asset": a, "gross_contribution": float(v)} for a, v in contrib.iloc[:5].items()],
            "top5_share_of_positive_contribution": (float(contrib.iloc[-5:].sum()) / pos_sum) if pos_sum > 0 else None,
            "without_top_contributor": {"dropped_asset": top, "total_net_return": ev.compound(r_drop),
                                        "excess_total_vs_spy": vs_drop["total_diff"],
                                        "excess_total_ci95": vs_drop["total_diff_ci95"],
                                        "ann_excess_vs_spy": vs_drop["ann_diff"],
                                        "ann_excess_ci95": vs_drop["ann_diff_ci95"],
                                        "beta_vs_market": ev.point_metrics(r_drop, rm, rc)["beta_vs_market"]},
            "without_top3_contributors": {"dropped_assets": top3,
                                          "reason": "independent-audit RUN-D 2026-11-11: concentration check; "
                                                    "the three largest positive gross contributors removed together",
                                          "total_net_return": ev.compound(r_d3),
                                          "excess_total_vs_spy": vs_d3["total_diff"],
                                          "excess_total_ci95": vs_d3["total_diff_ci95"],
                                          "ann_excess_vs_spy": vs_d3["ann_diff"],
                                          "ann_excess_ci95": vs_d3["ann_diff_ci95"],
                                          "beta_vs_market": ev.point_metrics(r_d3, rm, rc)["beta_vs_market"]},
        }

    # event study (policy-free, LIVE-PUBLISHED era plans published in-window; D5)
    pub = extra["pub_sessions"]
    es = ev.event_study(pub, {p["id"]: p["asset"] for p in era}, plan_etf, closes, cal, win1, B, seed)
    for h, v in es.items():
        if v.get("n_dates", 0) and v["n_dates"] < 5:
            v["status"] = "too_few_dates"
    # as-run event study retained for the superseded block (same seed -> v1 numbers)
    es_asrun = ev.event_study(extra_asrun["pub_sessions"], {p["id"]: p["asset"] for p in era},
                              plan_etf, closes, cal, win1, B, seed)
    for h, v in es_asrun.items():
        if v.get("n_dates", 0) and v["n_dates"] < 5:
            v["status"] = "too_few_dates"

    # ── independent diagnosis 2026-11-11: equal-weight member benchmark beside the ETF ──
    # yardstick correction: a cap-weighted sector fund is not what an average member did;
    # the frozen event-study numbers above are untouched, this block sits beside them.
    era_assets = {p["id"]: p["asset"] for p in era}
    es_mb = ev.member_benchmark_event_study(pub, era_assets, plan_etf, closes, raw, cal, win1,
                                            pit, sector_of_ticker, B, seed)

    # per-plan rows (same ruler) for the off-index after-the-fact sensitivity
    er = ev.event_rows(pub, era_assets, plan_etf, closes, cal, win1)

    def _cluster_ci(sub: pd.DataFrame, col: str, B_: int = B, sd: int = 20261111) -> dict:
        v = sub[col].dropna()
        if len(v) == 0:
            return {"mean": None, "n": 0, "n_dates": 0, "ci95_date_cluster": None}
        gb = sub.dropna(subset=[col]).groupby("date")[col]
        sums = gb.sum().to_numpy()
        cnts = gb.count().to_numpy()
        r = np.random.default_rng(sd)
        dr = r.integers(0, len(sums), size=(B_, len(sums)))
        boots = sums[dr].sum(axis=1) / np.maximum(cnts[dr].sum(axis=1), 1)
        return {"mean": float(v.mean()), "n": int(len(v)), "n_dates": int(len(sums)),
                "ci95_date_cluster": [float(np.percentile(boots, 2.5)),
                                      float(np.percentile(boots, 97.5))]}

    # off-index: asset not a point-in-time S&P 1500 member at the signal session
    members_at: dict[pd.Timestamp, set] = {}
    offidx: set[str] = set()
    for pid, P in pub.items():
        s = ev.session_on_or_before(cal, P - pd.Timedelta(days=1))
        if s is None:
            continue
        if s not in members_at:
            act = pit[(pit["start_date"] <= s) & (pit["end_date"].isna() | (pit["end_date"] > s))]
            members_at[s] = set(act["ticker"])
        if era_assets.get(pid) not in members_at[s]:
            offidx.add(pid)
    off_index = {
        "label": "AFTER-THE-FACT SENSITIVITY (independent diagnosis 2026-11-11) — not part of the frozen protocol",
        "definition": "picks whose stock is not a point-in-time S&P 1500 member at the plan's signal session "
                      "(PIT membership start_date <= s < end_date or open); counted and graded separately",
        "published_plans_off_index": len(offidx),
        "published_plans_total": len(pub),
        "entered_positions_off_index": sum(1 for p in positions if p.plan_id in offidx),
        "horizons": {},
        "membership_file_limits": "the PIT membership file has no recorded change after "
                                  f"{max(pit['start_date'].max(), pit['end_date'].max()).date()}; for signal dates "
                                  "after that, 'not a member' can mean 'membership unknown', not certainly absent "
                                  "(unrecorded additions and deletions both possible). Foreign ADRs (e.g. ASML, AZN, "
                                  "NVO) are correctly non-members; sector labels are current-basis, not as-issued.",
    }
    for h in (21, 42):
        sub = er[(er["h"] == h)].dropna(subset=["sel"])
        off_rows = sub[sub["plan"].isin(offidx)]
        mem_rows = sub[~sub["plan"].isin(offidx)]
        a, o, m = _cluster_ci(sub, "sel"), _cluster_ci(off_rows, "sel"), _cluster_ci(mem_rows, "sel")
        off_index["horizons"][str(h)] = {
            "all_plans": a, "off_index_picks": o, "sp1500_member_picks": m,
            "off_index_share_of_matured": (len(off_rows) / len(sub)) if len(sub) else None,
            "contribution_to_mean_gap": (a["mean"] - m["mean"]) if (a["mean"] is not None and m["mean"] is not None) else None,
            "contribution_note": "mean gap with all plans minus mean gap with member picks only, per-plan equal weight",
        }

    # coverage
    entered_seen = len(positions) + sum(v for k, v in excl.items()
                                        if k in ("no_fill_no_close_at_entry",))
    classified = len(positions) + sum(excl.values())
    spy_mdd = ev.max_drawdown(rm)
    l0_checks = {"classified_share": classified / max(extra["era_plans"], 1),
                 "priced_share": len(positions) / max(entered_seen, 1)}
    c6row = next(r for r in comp_rows if r["id"] == "C6_exact_incumbent_prophet")
    c6vs = ev.bootstrap_vs(series["C6_exact_incumbent_prophet"], rm, rm, rc, idx10)
    rel = ev.release_assessment(
        header, window_sessions=len(dates), spy_mdd=spy_mdd,
        resolved_positions=c6row["sample"]["resolved"], c6=c6row, c6_vs_c1=c6vs,
        c6_stress={"ann_diff": c6row["at_2x_costs"]["ann_excess_vs_spy"]},
        contrasts={k: {"p_holm": v["p_holm"], "ann_diff": v["ann_diff"]} for k, v in contrasts.items()},
        stress_contrasts={k: {"ann_diff": v["at_2x_costs"]["ann_diff"]} for k, v in contrasts.items()},
        k3_vs_exposure=k3x, l0_checks=l0_checks)

    c3_failed = 0
    c3_total = 0
    keys = sorted(c3_picks)
    for i, x in enumerate(keys):
        end = keys[i + 1] if i + 1 < len(keys) else win1
        for s in c3_picks[x]:
            c3_total += 1
            if closes.at[end, s] / closes.at[x, s] < closes.at[end, ev.BENCH] / closes.at[x, ev.BENCH]:
                c3_failed += 1

    # ── deviation D5 blocks: origination population, sensitivity, superseded as-run ──
    # sensitivity (a): replays admitted from their auditable availability (never the headline)
    book_s1 = ev.simulate_book(dates, rets, cash_r, ev.prophet_targets(pos_s1, dates), tradable, bps(1.0))
    r_s1 = book_s1.net.to_numpy()
    vs_s1 = ev.bootstrap_vs(r_s1, rm, rm, rc, idx10)
    mrna_s1 = next((p for p in pos_s1 if p.plan_id == "MRNA-BULL-20260616"), None)
    mrna_asrun = next((p for p in pos_asrun if p.plan_id == "MRNA-BULL-20260616"), None)

    # superseded as-run books: the v1 population, recomputed with the same pinned engine,
    # seed, prices and costs so nothing is hidden and the numbers can be compared directly.
    asrun_subsets = {
        "C6_exact_incumbent_prophet": pos_asrun,
        "C7_independent_emergence": [p for p in pos_asrun if p.aligned is False],
        "C6A_context_aligned_prophet": [p for p in pos_asrun if p.aligned is True],
    }
    asrun_rows, asrun_books = {}, {}
    for cid, ps in asrun_subsets.items():
        # legacy fee behaviour (terminal trade cost dropped): these rows preserve the v1
        # published superseded numbers byte-for-byte; the corrected primary books above
        # now charge the terminal trade (deviation D6)
        b = ev.simulate_book(dates, rets, cash_r, ev.prophet_targets(ps, dates), tradable, bps(1.0),
                             charge_terminal_trade_cost=False)
        asrun_books[cid] = b
        r = b.net.to_numpy()
        vs = ev.bootstrap_vs(r, rm, rm, rc, idx10)
        asrun_rows[cid] = {
            "positions": len(ps),
            "total_net_return": ev.compound(r),
            "excess_total_vs_spy": vs["total_diff"], "excess_total_ci95": vs["total_diff_ci95"],
            "ann_excess_vs_spy": vs["ann_diff"], "ann_excess_ci95": vs["ann_diff_ci95"],
            "beta_vs_market": ev.point_metrics(r, rm, rc)["beta_vs_market"],
            "hit_rate_vs_spy": ev.position_hits(ps, closes),
        }
    inv6_asrun = asrun_books["C6_exact_incumbent_prophet"].invested.to_numpy()
    rx6_asrun = inv6_asrun * rm + (1 - inv6_asrun) * rc
    k1_asrun = ev.bootstrap_vs(asrun_books["C6_exact_incumbent_prophet"].net.to_numpy(),
                               series["C1_passive_market"], rm, rc, idx10)
    k2_asrun = ev.bootstrap_vs(asrun_books["C6_exact_incumbent_prophet"].net.to_numpy(), rx6_asrun, rm, rc, idx10)
    k7_asrun = ev.bootstrap_vs(asrun_books["C6A_context_aligned_prophet"].net.to_numpy(),
                               asrun_books["C7_independent_emergence"].net.to_numpy(), rm, rc, idx10)
    exec_by_kind: dict[str, set] = {}
    for p in era:
        if ev.is_backfilled(p):
            exec_by_kind.setdefault(minted[p["id"]], set()).add(str(p["backfill_executed_at"]))

    # undated conversions (audit RUN-D): terminal-state 'converted' with no dated fill
    undated_ids = ev.undated_converted_ids(era)

    population = {
        "primary": "live-published incumbent-era plans only (deviation D5): every C6/C7/C6A position, "
                   "event-study plan, attribution leg, coverage count and contrast in this artifact uses this population",
        "excluded_cohort": {
            "reason": ev.NOT_LIVE_EXCLUSION_REASON + ": outage-reconstructed plans are not live historical "
                      "publications and may never be presented as live historical calls "
                      "(research/PROPHET_OUTAGE_BACKFILL_2026_08.md)",
            "detection": "plan rows' origination_mode startswith outage_backfill, each carrying a "
                         "backfill_executed_at receipt, cross-checked in both directions against the minted "
                         "sets in data/prophet/backfill_disclosures.json; the run refuses on any disagreement; "
                         "no hard-coded id list",
            "era_plans_excluded": len(not_live),
            "of_which_replayed_receipted_bake": len(replay_ids & era_ids),
            "of_which_synthetic_board_reconstructions": len(recon_ids & era_ids),
            "origination_mode_counts": by_mode,
            "backfill_executed_at_by_kind": {k: sorted(v) for k, v in exec_by_kind.items()},
            "plan_ids": sorted(not_live),
            "census_basis": "all plans minted with an outage_backfill origination_mode, any era",
            "overall_minted_outage_backfill": len(minted),
            "overall_of_which_replayed_receipted_bake": sum(1 for v in minted.values() if v == "replay"),
            "overall_of_which_synthetic_board_reconstructions": sum(1 for v in minted.values() if v == "reconstruction"),
            "outside_selection_era": sorted(set(minted) - era_ids),
            "era_minted_outage_backfill": len(minted.keys() & era_ids),
            "would_have_entered_positions_as_run": len(backfilled_entered_asrun),
            "would_have_entered_ids_as_run": backfilled_entered_asrun,
        },
        "mrna": {
            "note": "MRNA-BULL-20260616 (origination_mode outage_backfill_2026_08_09, instantiated "
                    "2026-08-11T05:32:28Z) is NOT in the primary book: as run it entered at the 2026-08-10 "
                    "close, a session before it existed for any user.",
            "as_run_entry": str(mrna_asrun.entry.date()) if mrna_asrun else None,
            "in_sensitivity_a": mrna_s1 is not None,
            "sensitivity_a_entry": str(mrna_s1.entry.date()) if mrna_s1 else None,
            "price_authentication": "the 2026-08-19 one-day close move of +177% (62.96 -> 174.38; raw and "
                                    "adjusted closes agree; volume 199,252,300) was, at publication, present "
                                    "only in the single price cache used by this runner. Two post-publication "
                                    "second-source checks (independent audit RUN-D 2026-11-11) now authenticate "
                                    "it: a ChartExchange end-of-day sweep reproduces the 62.96 -> 174.38 closes, "
                                    "and a Yahoo live-chart API pull matches all 64 window sessions for MRNA. "
                                    "Both are audit evidence gathered after outcomes were seen, labelled as such, "
                                    "and change no frozen number; the v1 caveat is retained here superseded.",
        },
        "undated_conversions": {
            "count": len(undated_ids),
            "ids": sorted(undated_ids),
            "basis": "era plans with entry_zone_state.state == 'converted' and no truthy dated fill field; the "
                     "snapshot records terminal state only, so their conversion session is unknowable from it",
            "primary_treatment": "entered at publication session P under the header's literal C6 rule (E = first "
                                 "session >= max(P, filled_date if present); an absent filled_date falls back to P)",
            "sensitivity": "sensitivity.excluding_undated_conversions removes every one of them",
        },
        "review": {"file": "REVIEW_beta_evaluation.md (independent scientific review, 2026-11-10)",
                   "sha256": "6296bf4cb77d09e47f1311dbd46cd915a794e050ce7460a228ad821e7b13541a"},
    }

    # ── independent-audit RUN-D sensitivities (2026-11-11), computed on this engine ──
    # (a) conversions: the snapshot records terminal state only; a converted plan with
    #     no dated fill cannot be shown convertible at its publication session.
    pos_fx, excl_fx, _ = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1,
                                            excluded_ids=undated_ids, not_live_ids=not_live)
    book_fx = ev.simulate_book(dates, rets, cash_r, ev.prophet_targets(pos_fx, dates), tradable, bps(1.0))
    r_fx = book_fx.net.to_numpy()
    vs_fx = ev.bootstrap_vs(r_fx, rm, rm, rc, idx10)
    # (b) missing held marks: primary zero-fills them (flat); stress writes each gapped
    #     position to a total loss at its first missing close.
    held_gaps = ev.held_path_gaps(positions, closes)
    held_gaps_rows = [{"plan_id": g["plan_id"], "asset": g["asset"], "entry": str(g["entry"].date()),
                       "first_missing_close": str(g["first_missing_close"].date()),
                       "missing_sessions": g["missing_sessions"]} for g in held_gaps]
    rets_loss = ev.first_gap_total_loss_rets(rets, positions, closes)
    book_tl = ev.simulate_book(dates, rets_loss, cash_r,
                               ev.prophet_targets(positions, dates), tradable, bps(1.0))
    r_tl = book_tl.net.to_numpy()
    vs_tl = ev.bootstrap_vs(r_tl, rm, rm, rc, idx10)

    # pre-correction primary C6 (terminal trade cost dropped) — retained verbatim in
    # the correction block; must reproduce the published -3.1382%/+1.5077 pp exactly
    book_c6_pre = ev.simulate_book(dates, rets, cash_r, targets["C6_exact_incumbent_prophet"],
                                   tradable, bps(1.0), charge_terminal_trade_cost=False)
    r_c6_pre = book_c6_pre.net.to_numpy()
    vs_c6_pre = ev.bootstrap_vs(r_c6_pre, rm, rm, rc, idx10)

    undated_gap_n = sum(1 for g in held_gaps if g["plan_id"] in undated_ids)

    sensitivity = {
        "label": "SENSITIVITY — separately labelled, never the headline; descriptive only (L0)",
        "backfill_replays_admitted_after_availability": {
            "definition": f"the {len(replay_ids & era_ids)} receipted replays of the 2026-08-09 bake admitted "
                          f"from the first session at/after their actual backfill_executed_at "
                          f"({sorted(exec_by_kind.get('replay', set()))[0] if exec_by_kind.get('replay') else 'n/a'}); "
                          f"the {len(recon_ids & era_ids)} synthetic-board reconstructions "
                          f"({', '.join(sorted(recon_ids & era_ids))}) never admitted",
            "excluded_from_this_variant": excl_s1,
            "positions": len(pos_s1),
            "total_net_return": ev.compound(r_s1),
            "excess_total_vs_spy": vs_s1["total_diff"], "excess_total_ci95": vs_s1["total_diff_ci95"],
            "ann_excess_vs_spy": vs_s1["ann_diff"], "ann_excess_ci95": vs_s1["ann_diff_ci95"],
            "beta_vs_market": ev.point_metrics(r_s1, rm, rc)["beta_vs_market"],
            "mean_invested": float(book_s1.invested.mean()),
            "hit_rate_vs_spy": ev.position_hits(pos_s1, closes),
        },
        "superseded_as_run": {
            "reason": "v1 as-run population included the 16 outage-reconstructed plans as if historically "
                      "published; superseded by the deviation-D5 primary correction, which lowers the headline. "
                      "Retained verbatim so nothing is hidden; never render as the current result.",
            "same_engine_seed_prices_costs": True,
            "C6_exact_incumbent_prophet": asrun_rows["C6_exact_incumbent_prophet"],
            "C7_independent_emergence": asrun_rows["C7_independent_emergence"],
            "C6A_context_aligned_prophet": asrun_rows["C6A_context_aligned_prophet"],
            "contrasts": {
                "K1_C6_minus_C1": k1_asrun, "K2_C6_minus_X6": k2_asrun, "K7_C6A_minus_C7": k7_asrun,
            },
            "attribution_C6": ev.attribution_bridge(asrun_books["C6_exact_incumbent_prophet"], rets, cash_r,
                                                    ev.asset_sector_map(asrun_subsets["C6_exact_incumbent_prophet"])),
            "event_study_h21": es_asrun["21"],
            "event_study_h42": es_asrun["42"],
        },
        "excluding_undated_conversions": {
            "definition": f"the {len(undated_ids)} incumbent-era plans whose entry_zone_state.state == "
                          f"'converted' but whose snapshot records no dated fill (no truthy filled_date or "
                          f"other date/_at field); because the snapshot is not a vintage, the conversion "
                          f"session cannot be established from recorded_at alone. {len(undated_ids) - undated_gap_n} of "
                          f"them held without missing marks through the window and are removed with "
                          f"their whole position; the variant keeps every other rule of C6 unchanged. Added by "
                          f"the 2026-11-11 independent audit; not part of the frozen protocol.",
            "excluded_from_this_variant": excl_fx,
            "positions": len(pos_fx),
            "total_net_return": ev.compound(r_fx),
            "excess_total_vs_spy": vs_fx["total_diff"], "excess_total_ci95": vs_fx["total_diff_ci95"],
            "ann_excess_vs_spy": vs_fx["ann_diff"], "ann_excess_ci95": vs_fx["ann_diff_ci95"],
            "beta_vs_market": ev.point_metrics(r_fx, rm, rc)["beta_vs_market"],
            "mean_invested": float(book_fx.invested.mean()),
            "hit_rate_vs_spy": ev.position_hits(pos_fx, closes),
        },
        "missing_marks_total_loss_stress": {
            "definition": f"{len(positions)} entered positions hold assets whose close series stops inside "
                          f"the window (delistings; snapshot keeps the plan open). The primary book zero-fills "
                          f"missing held marks (position runs flat). This stress instead writes a total loss "
                          f"(-100%) at each position's first missing close and lets drift remove the weight; "
                          f"it is a deliberate worst case, not an estimate. Added by the 2026-11-11 "
                          f"independent audit; not part of the frozen protocol.",
            "positions": len(positions),
            "total_net_return": ev.compound(r_tl),
            "excess_total_vs_spy": vs_tl["total_diff"], "excess_total_ci95": vs_tl["total_diff_ci95"],
            "ann_excess_vs_spy": vs_tl["ann_diff"], "ann_excess_ci95": vs_tl["ann_diff_ci95"],
            "beta_vs_market": ev.point_metrics(r_tl, rm, rc)["beta_vs_market"],
            "mean_invested": float(book_tl.invested.mean()),
            "gapped_positions": held_gaps_rows,
        },
        "off_index_picks": off_index,
    }

    # fill D5's what with the concrete before -> after numbers
    d5 = next(d for d in deviations if d["id"] == "D5")
    c6_now = next(r for r in comp_rows if r["id"] == "C6_exact_incumbent_prophet")
    a6_old = asrun_rows["C6_exact_incumbent_prophet"]

    def _p4(x):
        return f"{x * 100:+.4f}%"

    def _p4pp(x):
        return f"{x * 100:+.4f} pp"

    def _ci4(c):
        return f"[{c[0] * 100:+.3f}, {c[1] * 100:+.3f}]"

    d5["what"] = (
        f"primary population corrected to live-published plans only: {len(not_live)} outage-reconstructed "
        f"incumbent-era plans ({len(replay_ids & era_ids)} receipted replays of the 2026-08-09 bake instantiated "
        f"2026-08-11T05:32:28Z; {len(recon_ids & era_ids)} synthetic-board reconstructions of the never-published "
        f"2026-08-11 board executed 2026-08-13T13:31:33Z) excluded from C6/C7/C6A, the all-published-plans event "
        f"study, attribution, coverage counts and every contrast using them (reason "
        f"{ev.NOT_LIVE_EXCLUSION_REASON}, detected from origination_mode/backfill_executed_at and the disclosure "
        f"receipts, never a hard-coded id list). Before -> after: C6 total {_p4(a6_old['total_net_return'])} -> "
        f"{_p4(c6_now['total_net_return'])}; C6 vs SPY {_p4pp(a6_old['excess_total_vs_spy'])} -> "
        f"{_p4pp(c6_now['vs_passive_market']['total_diff'])} (CI {_ci4(a6_old['excess_total_ci95'])} -> "
        f"{_ci4(c6_now['vs_passive_market']['total_diff_ci95'])} pp); C6 positions {a6_old['positions']} -> "
        f"{c6_now['sample']['positions']}; K1 {_p4pp(k1_asrun['ann_diff'])} -> "
        f"{_p4pp(contrasts['K1']['ann_diff'])}/yr; K2 {_p4pp(k2_asrun['ann_diff'])} -> "
        f"{_p4pp(contrasts['K2']['ann_diff'])}/yr; K7 {_p4pp(k7_asrun['ann_diff'])} -> "
        f"{_p4pp(contrasts['K7']['ann_diff'])}/yr; event study H=21 "
        f"{_p4pp(es_asrun['21']['excess_vs_spy']['mean'])} -> {_p4pp(es['21']['excess_vs_spy']['mean'])} "
        f"(n {es_asrun['21']['excess_vs_spy']['n']} -> {es['21']['excess_vs_spy']['n']}, dates "
        f"{es_asrun['21']['n_dates']} -> {es['21']['n_dates']}). The superseded population is retained verbatim "
        f"under sensitivity.superseded_as_run; sensitivity (a) admits the {len(replay_ids & era_ids)} replays only "
        f"from their auditable availability and admits the synthetic-board reconstructions never."
    )

    # ── dated correction (2026-11-11): terminal trade cost charged; superseded retained ──
    d6v = next(d for d in deviations if d["id"] == "D6")
    c6_pre = {
        "positions": c6row["sample"]["positions"],
        "total_net_return": ev.compound(r_c6_pre),
        "excess_total_vs_spy": vs_c6_pre["total_diff"], "excess_total_ci95": vs_c6_pre["total_diff_ci95"],
        "ann_excess_vs_spy": vs_c6_pre["ann_diff"], "ann_excess_ci95": vs_c6_pre["ann_diff_ci95"],
        "beta_vs_market": ev.point_metrics(r_c6_pre, rm, rc)["beta_vs_market"],
        "costs_paid_total": float(book_c6_pre.cost.sum()),
    }
    d6v["what"] = (
        f"engine correction: simulate_book now charges the final-close trade cost (a target vector defined at the "
        f"last session implies a trade whose cost the v1 engine computed but never consumed, because no d+1 return "
        f"existed to carry it). The cost is charged against the final day's realised net return. Affected books: "
        f"C3/C4/C5 (last scheduled rebalance), C6/C7/C6A (terminal closes incl. liquidation of names that stop "
        f"trading); C1 (100% SPY held through, no terminal sale) and C2/X6 (no final trade beyond the daily "
        f"target series already costed) are unaffected. Before -> after on the corrected population: C6 total "
        f"{_p4(c6_pre['total_net_return'])} -> {_p4(c6row['total_net_return'])}; C6 vs SPY "
        f"{_p4pp(c6_pre['excess_total_vs_spy'])} -> {_p4pp(c6vs['total_diff'])} "
        f"(CI {_ci4(c6_pre['excess_total_ci95'])} -> {_ci4(c6vs['total_diff_ci95'])} pp); C6 costs "
        f"{c6_pre['costs_paid_total'] * 100:.4f}% -> {c6row['costs_paid_total'] * 100:.4f}% of NAV. K1 "
        f"{_p4pp(ev.bootstrap_vs(r_c6_pre, series['C1_passive_market'], rm, rc, idx10)['ann_diff'])} -> "
        f"{_p4pp(contrasts['K1']['ann_diff'])}/yr. Every superseded figure is retained verbatim in this "
        f"artifact's correction block and in sensitivity.superseded_as_run."
    )
    d6v["why"] = (
        "found by two independent re-derivations after publication (independent audit RUN-D 2026-11-11; second "
        "re-derivation by a different model, Kimi). The v1 behaviour silently dropped a real cost the engine had "
        "already computed; the fix makes the book pay what its own target vector says it trades. The verdict "
        "(L0, descriptive, not distinguishable from passive) is unchanged: every shifted interval still spans zero "
        "by a wide margin. Protocol header, population rules, comparators, seeds and the data pin are untouched "
        "(header sha256 3be32166…2ada verified before the run)."
    )

    # D7/D8 fills (diagnosis-driven yardstick correction and off-index sensitivity)
    d7v = next(d for d in deviations if d["id"] == "D7")
    mb21, mb42 = es_mb.get("21", {}), es_mb.get("42", {})
    d7v["what"] = (
        f"event_study.member_benchmark added beside the frozen stock-minus-sector-ETF leg: at each horizon the "
        f"equal-weight mean of point-in-time eligible same-sector members on the same signal date (C4 eligibility, "
        f"names published that day excluded), the stock minus that member benchmark with a date-cluster interval, "
        f"and a placebo distribution of random same-sector members showing what no selection looks like. "
        f"H=21: equal-weight member mean vs ETF {_p4pp(mb21.get('equal_weight_member_minus_sector_etf', {}).get('mean') or 0)} "
        f"(CI {_ci4(mb21.get('equal_weight_member_minus_sector_etf', {}).get('ci95_date_cluster') or [0, 0])}); "
        f"stock vs member benchmark {_p4pp(mb21.get('stock_minus_equal_weight_members', {}).get('mean') or 0)} "
        f"(CI {_ci4(mb21.get('stock_minus_equal_weight_members', {}).get('ci95_date_cluster') or [0, 0])}); "
        f"placebo 95% range {_p4pp(mb21.get('placebo_random_same_sector', {}).get('p2_5', 0))} to "
        f"{_p4pp(mb21.get('placebo_random_same_sector', {}).get('p97_5', 0))} versus the observed "
        f"{_p4pp(mb21.get('stock_minus_sector_etf', {}).get('mean') or 0)}. The frozen event-study numbers are "
        f"unchanged; this block decomposes the same leg into yardstick drag plus stock-versus-peers."
    )
    d7v["why"] = (
        "independent diagnosis of the stock-minus-sector gap (2026-11-11, /tmp/prophet-eval-diagnosis/REPORT.md, "
        "reproduced on this engine with this runner's own code; diagnosis figures used only as cross-check): a "
        "cap-weighted sector fund is not what an average member of the sector did in this window, so part of the "
        "published stock-minus-sector-ETF leg is the yardstick, not member choice. Descriptive only; adds no "
        "threshold, changes no release level, and makes no claim of negative selection or of its absence."
    )
    d8v = next(d for d in deviations if d["id"] == "D8")
    o21, o42 = off_index["horizons"].get("21", {}), off_index["horizons"].get("42", {})
    d8v["what"] = (
        f"sensitivity.off_index_picks added: {off_index['published_plans_off_index']} of "
        f"{off_index['published_plans_total']} published plans name a stock that is not a point-in-time S&P 1500 "
        f"member at its signal session. At H=21 their stock-minus-sector-ETF mean is "
        f"{_p4pp(o21.get('off_index_picks', {}).get('mean') or 0)} (n {o21.get('off_index_picks', {}).get('n')}) "
        f"versus {_p4pp(o21.get('sp1500_member_picks', {}).get('mean') or 0)} for member picks; excluding them "
        f"moves the all-plan mean from {_p4pp(o21.get('all_plans', {}).get('mean') or 0)} to "
        f"{_p4pp(o21.get('sp1500_member_picks', {}).get('mean') or 0)}. At H=42: "
        f"{_p4pp(o42.get('off_index_picks', {}).get('mean') or 0)} versus "
        f"{_p4pp(o42.get('sp1500_member_picks', {}).get('mean') or 0)}. Membership-file limits restated in the "
        f"block: no recorded change after 2026-06-02, so late-window 'not a member' can mean 'membership unknown'."
    )
    d8v["why"] = (
        "the same independent diagnosis found roughly a quarter to a third of the event-study gap carried by "
        "off-index picks (quantum, space, crypto-mining and similar names), which have no true cap-weighted sector "
        "yardstick. Reported as a labelled after-the-fact sensitivity on the same ruler; recomputed on this engine, "
        "diagnosis figures used only as cross-check. Descriptive only."
    )

    correction = {
        "correction": True,
        "date": "2026-11-11",
        "supersedes": "site/prophet/beta_evaluation.json as of commit c3d967b9fd (v1, 2026-11-10)",
        "what_changed": "two confirmed engine defects corrected (final-close trade cost charged; price-cache files "
                        "now verified byte-for-byte against the data pin and one false-missing ticker, ZWS, "
                        "restored), plus disclosure and labelling corrections; no frozen rule, seed, comparator, "
                        "population rule or data pin changed",
        "figures_superseded": {
            "reason_each": "final-close trade costs now charged (deviation D6); each superseded row below was "
                           "computed with the v1 engine on the same population, prices, seed and costs",
            "C6_exact_incumbent_prophet": c6_pre,
            "verdict_unchanged": True,
            "verdict_reason": "L0 descriptive stands: the window still fails the predeclared L1 minimum "
                              "(64 < 252 sessions, SPY max drawdown 5.92% < 8%) and every headline CI spans zero "
                              "before and after the correction",
        },
        "label": "CORRECTION — found by an independent audit after publication and not part of the frozen protocol",
    }
    independent_audit = {
        "label": "INDEPENDENT AUDIT (post-publication, 2026-11-11) — not part of the frozen protocol",
        "runs": [
            {"name": "ChatGPT Pro run D (PRO_RUN_D, 2026-11-11)", "report": "macro issue #11014 / PRO_RUN_D_answer.md",
             "scope": "full re-derivation from the data pin with independent code"},
            {"name": "Kimi re-derivation (REPORT_RUN_D, 2026-11-11)", "report": "REPORT_RUN_D.md",
             "scope": "independent unblinding re-derivation of the same artifact"},
            {"name": "Stock-minus-sector diagnosis (Opus, 2026-11-11)", "report": "tmp/prophet-eval-diagnosis/REPORT.md",
             "scope": "independent diagnosis of the stock-minus-sector gap; yardstick (equal-weight member) and "
                      "off-index findings, folded in as deviations D7/D8 and recomputed on this engine"},
        ],
        "what_agreed": [
            "every event-study horizon mean reproduced to 8 decimal places by both runs",
            "fee timing on all non-terminal trades is correct (cost applied to the next day's return)",
            "C1 passive identity reproduced exactly (SPY total minus one entry cost)",
            "the 78 undated conversions, the gapped held marks and the top-three contribution concentration "
            "were independently identified by both runs with matching counts",
        ],
        "what_changed": [
            "engine: final-close trade cost now charged (deviation D6; confirmed defect, both runs)",
            "runner: price files verified against the data pin blob ids; ZWS was false-missing in v1 (cache bytes "
            "match the pin; the ticker was eligible but never selected, so no frozen number moves; missing-file "
            "census 36 -> 35)",
            "disclosure: coverage basis, undated conversions, missing held marks, MRNA authentication and the "
            "minted-plan census restated (see limitations and population blocks)",
            "yardstick: event_study.member_benchmark added beside the frozen event study (equal-weight same-sector "
            "member benchmark plus random-member placebo; deviation D7) and sensitivity.off_index_picks added "
            "(deviation D8) — both from the stock-minus-sector diagnosis and recomputed on this engine",
        ],
        "added_sensitivities": ["excluding_undated_conversions", "missing_marks_total_loss_stress",
                                "post_hoc_diagnostics.*.without_top3_contributors",
                                "off_index_picks", "event_study.member_benchmark"],
        "adjudication": "research/prophet_v4/beta_first_evaluation/ADJUDICATION_RUN_D.md (one row per finding, "
                        "verdict, evidence, commit)",
    }

    code_commit = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain", "--", "engine/prophet_beta_evaluation.py",
                "scripts/run_prophet_beta_evaluation.py")
    artifact = {
        "schema": ev.SCHEMA,
        "view": "STRATEGY_EVALUATION_VIEW",
        "protocol_ref": ev.HEADER_REL_PATH,
        "protocol": {"id": header["protocol_id"], "header_sha256": ev.FROZEN_HEADER_SHA256,
                     "header_commit": ev.HEADER_COMMIT, "frozen_on": header["frozen_on"]},
        "code": {"commit": code_commit, "harness_dirty": bool(dirty),
                 "module": "engine/prophet_beta_evaluation.py",
                 "runner": "scripts/run_prophet_beta_evaluation.py",
                 "bootstrap": {"B": B, "seed": seed, "mean_block": block, "sensitivity_block": block_alt}},
        "data_clocks": {
            "macro_data_commit": header["data_pin"]["macro_commit"],
            "plans_index": {"path": "site/prophet/index.json",
                            "sha256": pinned.sha["plans_index"], "read_from": f"data pin {pin[:8]}",
                            "asof": index.get("asof"), "source_asof": index.get("source_asof"),
                            "computed_at": index.get("computed_at")},
            "resolution_log": {"path": "data/prophet/ledger.jsonl", "sha256": pinned.sha["resolution_log"],
                       "rows": len(led_rows), "malformed_lines_skipped": led_bad,
                       "max_asof": max(r.get("asof", "") for r in led_rows),
                       "close_date_corrections_applied": applied_corr,
                       "quarantined_ids_removed": len(quarantine)},
            "pit_membership": {"path": "data/breadth/sp1500_pit_membership.parquet",
                               "sha256": pinned.sha["pit_membership"],
                               "read_from": f"data pin {pin[:8]}",
                               "last_recorded_change": str(max(pit["start_date"].max(), pit["end_date"].max()).date())},
            "prices": {"source": "data/yahoo per-ticker parquet (adjusted close)", "tickers_loaded": closes.shape[1],
                       "digest_sha256": price_digest, "missing_files": len(missing),
                       "last_close_used": str(win1.date()),
                       "pin_verified": True,
                       "pin_verification": "every per-ticker parquet used is byte-compared to the pin's git blob id "
                                           "(git hash-object); a differing local file is replaced by the pin blob. "
                                           "v1 trusted the cache directory (audit RUN-D); the pin's own blob ids now "
                                           "decide",
                       "read_from_pin_blobs": prices_from_pin,
                       "pinned_input_sha256": pinned.sha},
        },
        "market": "US", "benchmark": ev.BENCH, "currency": "USD",
        "return_basis": "total_return_adjusted_close", "cash_instrument": ev.CASH,
        "costs_bp_per_side": header["execution"]["cost_bps_per_side"],
        "window": {"first_return_close": str(win0.date()), "last_close": str(win1.date()),
                   "sessions": len(dates), "daily_returns": n,
                   "spy_total_return": ev.compound(rm), "spy_max_drawdown": spy_mdd},
        "release": rel,
        "correction": correction,
        "independent_audit": independent_audit,
        "comparators": comp_rows,
        "contrasts": {"family": "confirmatory K1-K8, Holm alpha 0.05, one-sided (a beats b)",
                      "rows": list(contrasts.values())},
        "secondary_contrasts": {"family": "admission_class strata vs SPY, Holm alpha 0.05", "rows": secondary},
        "exposure_matched_reference": {"definition": header["comparators"]["X6_exposure_matched_reference"],
                                       "invested_fraction": float(inv6.mean()),
                                       "c6_minus_reference": contrasts["K2"],
                                       "c3_minus_reference": {k: k3x[k] for k in ("ann_diff", "ann_diff_ci95", "p_one_sided")}},
        "attribution": attribution,
        "event_study": {"ruler": "engine.grading.forward_metrics next-bar fill; fixed horizons in sessions; policy-free",
                        "population": "all LIVE-PUBLISHED incumbent-era plans with a publication session in the window "
                                      "(entered or not); outage-reconstructed plans excluded (deviation D5)",
                        "plans": len(pub), "excluded_backfilled_plans": len(not_live), "horizons": es,
                        "member_benchmark": {
                            "label": "YARDSTICK CORRECTION (independent diagnosis 2026-11-11) — beside the frozen "
                                     "event study, not part of it; changes no frozen number",
                            "why": "the stock-minus-sector-ETF leg grades every pick against a cap-weighted fund; in "
                                   "this window the average point-in-time member of a sector trailed its own fund, "
                                   "so part of that leg is the yardstick, not member choice",
                            "universe_rule": "point-in-time S&P 1500 members at the signal session (start<=s<end or "
                                             "open), sector label present, >=126 valid closes, raw close >= $5 "
                                             "(the header's own C4 eligibility), a matured outcome at the horizon, "
                                             "and no plan published on that asset that day",
                            "same_ruler_and_population": True,
                            "decomposition_identity": "stock - sector ETF = (equal-weight member mean - sector ETF) "
                                                      "+ (stock - equal-weight member mean), per plan, exact",
                            "horizons": es_mb,
                        }},
        "stability_halves": halves,
        "post_hoc_diagnostics": diagnostics,
        "population": population,
        "sensitivity": sensitivity,
        "failed_leaders": {"c3_sector_picks": c3_total, "lagged_spy_over_hold": c3_failed},
        "rebounds": {"status": "not_evaluable",
                     "reason": "window holds no SPY drawdown deep enough for a rebound test (see window.spy_max_drawdown)"
                     if spy_mdd > -0.08 else "see stability_halves"},
        "coverage": {
            "era_plans": extra["era_plans"],
            "evaluated_positions": len(positions),
            "excluded": excl,
            "entry_shifted_to_publication": extra["entry_shifted_to_publication"],
            "exit_basis": {"recorded_close_date": extra["exit_ledger"], "mechanical_published_levels":
                           extra["exit_mechanical"], "censored_open_at_window_end": extra["censored"]},
            "classified_share": l0_checks["classified_share"],
            "priced_share": l0_checks["priced_share"],
            "priced_share_basis": "entered positions with a valid close at entry (entry marks only). Marks after "
                                  "entry are a separate question: held assets whose close series stops inside the "
                                  "window are zero-filled (held flat) in the primary book — see "
                                  "coverage.held_path_gaps and sensitivity.missing_marks_total_loss_stress",
            "held_path_gap_positions": held_gaps_rows,
            "held_path_gaps": len(held_gaps),
            "held_path_complete_positions": len(positions) - len(held_gaps),
            "resolved_at_or_before_split": {
                "total": excl["resolved_at_or_before_follower_fill"],
                "entered_at_final_close": extra["entered_at_final_close"],
                "resolved_before_follower_fill": extra["resolved_before_follower_fill"],
            },
            "sector": {"unmapped_plans": unmapped, "label_source_disagreements": disagreements,
                       "labels_basis": "current-basis GICS (not era-correct)"},
            "c7_c6a_split": {"outside_leading": len(subsets["C7_independent_emergence"]),
                             "inside_leading": len(subsets["C6A_context_aligned_prophet"]),
                             "unmapped": sum(p.aligned is None for p in positions)},
            "member_universe_by_rebalance": uni_audit,
            "member_universe_missing_price_files": sorted(t for t in missing if t in set(act["ticker"])),
            "c4_sector_weights": {k: float(v) for k, v in sw.items()},
            "issuer_excluded_peers": {"status": "unavailable",
                                      "reason": "listing-ticker identity only; no issuer master join in this harness, so issuer-excluded peer counts are not supportable"},
            "drop_corrected_sensitivity": {"positions": len(pos_nc), "excluded": excl_nc},
        },
        "claims": {
            "observed_relative_performance": {"status": "descriptive",
                                              "basis": "realised window returns with bootstrap CIs; L0 only"},
            "estimated_exposure_residual": {"status": "descriptive",
                                            "basis": "OLS beta/intercept on 63 daily returns; not a validated factor model"},
            "participation_attribution": {"status": "model_book_accounting",
                                          "basis": "equal-weight model book of published plans; not actual holdings or user portfolios"},
            "incremental_selection_value": {"status": "not_established",
                                            "basis": "sample below the predeclared L1 minimum"},
        },
        "limitations": [],
        "deviations": deviations,
        **ev.AUTHORITY,
    }
    artifact["headline"], artifact["limitations"] = plain_words(artifact)
    artifact["release"]["overall_level"] = min(
        (j["level"] for j in artifact["release"]["jobs"].values()),
        key=lambda lv: artifact["release"]["levels_defined"].index(lv)
        if lv in artifact["release"]["levels_defined"] else -1)
    artifact = ev.json_safe(artifact)
    bad = ev.assert_no_forbidden_keys(artifact)
    if bad:
        raise SystemExit(f"forbidden key names: {bad}")
    write_artifact_atomic(Path(args.out),
                          json.dumps(artifact, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
