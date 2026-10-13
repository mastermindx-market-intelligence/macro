#!/usr/bin/env python3
"""Prophet Learning Loop — US Buy-Board postmortem forensics (masterplan §2, gates G1/G2).

    python -m scripts.prophet_postmortem            # write summary + report
    python -m scripts.prophet_postmortem --dry-run  # print the headline, write nothing

WHAT IT PRODUCES
----------------
  data/prophet_postmortem/summary.json        aggregations + every episode row
  reports/prophet_postmortem_<as_of>.md       the same content rendered for a reader

WHERE EVERY FIELD COMES FROM
----------------------------
  data/us_board_ledger/retro_grades.parquet   board membership back to 2026-06-15 plus
                                              85 columns of signal state at entry.
  data/us_board_ledger/snapshots.jsonl        the board's OWN nightly JSON from
                                              2026-06-30 on — spotlight theme/sector
                                              read, alignment/extension read, entry
                                              plan (stop, chase level), hold state.
                                              Richer than the parquet; used first.
  data/baskets/ohlcv/<T>.parquet, then
  data/yahoo/<T>.parquet, data/stocks/<T>.parquet,
  data/baskets/extras.parquet                 the ADJUSTED rungs, walked FIRST, in that
                                              order, via engine.price_ladder. The board's
                                              universe (~1,579 names) is wider than the
                                              caches' S&P-1500, so extras-universe picks
                                              such as ASTS would otherwise be structurally
                                              ungradeable — held, exited, never scored.
  data/breadth/_closes_cache.parquet (+ smallcap / midcap / russell)
                                              LAST RESORT, first-hit-wins in that order
                                              (the precedence build_stock_library uses).
                                              These caches are NOT dividend-adjusted —
                                              this header claimed they were until
                                              2026-08-06. They are raw closes accrued
                                              forward and re-based only at a full
                                              rebuild, so an episode priced here and
                                              measured against SPY books the name's own
                                              dividend as underperformance. Kept as a
                                              rung because dropping a name deletes the
                                              population this study measures; every
                                              episode carries price_source/price_basis so
                                              the residual is visible on the artifact.
  data/yahoo/SPY.parquet                      benchmark leg (excess return). ALWAYS
                                              back-adjusted — which is exactly why the
                                              name leg has to be too.
  data/baskets/latest.json  VIA GIT HISTORY   theme state AS OF the entry date. The file
                                              is overwritten nightly, so the only way to
                                              know what the desk thought of a theme on
                                              2026-07-09 is to read the blob from the
                                              last commit whose own `as_of` is <= that
                                              date. 69 revisions are available.
  data/baskets/membership.json                ticker -> basket ids. CURRENT membership,
                                              not point-in-time — see MEMBERSHIP DRIFT.

MEMBERSHIP DRIFT (a caveat, printed on the artifact and in the report)
----------------------------------------------------------------------
membership.json is a single current file with no per-date history, so a ticker that
JOINED a basket after an entry date will be credited with that basket's entry-date
state. The theme STATE is point-in-time (git); the ticker->theme MAPPING is not. The
sector-basket leg is unaffected (it derives from the row's own sector at entry), and
the board's own `spotlight.theme.slug` is recorded beside the mapped ids so a reader
can see where the two disagree. Reconstructing membership history is a separate job.

SCORING — WHOSE NUMBERS ARE THESE?
----------------------------------
`engine.track_scoring`, unchanged (gate G4). Next-bar-close fill, forced verdict at
H=10, symmetric maturity gate, and NO stop / NO oscillator target: this study measures
the SIGNAL, so it must not mix in an exit policy. The published US ledger applies its
own exit rule, so the two agree except where that rule fired — e.g. IPGP 2026-07-15
scores -17.9% here and -18.7% in the ledger, which stopped out on day 8. Both are the
same fill and the same window; only the exit differs.

RE-ADMISSION: THE PRIOR-EPISODE SCAN
------------------------------------
`prior_episodes()` compares each entry against EVERY prior run of the same ticker whose
board exit sits inside the 10-session window — not just the immediately preceding one —
and reports one of them by a fixed precedence (buildable open drawdown, then resolved
loss, then the nearest prior as a decided negative). An in-window prior that cannot be
priced makes the row UNDECIDABLE rather than clean, and every row carries its comparison
in `prior_episode` with `prior_matured`, so a reader can see whether the number the leg
fired on is a resolved outcome or an outcome-conditioned mark.

IN-FLIGHT ROWS
--------------
Episodes without H forward bars are marked to the latest close, CLASSIFIED (dropping
them would delete the most recent evidence), and then held in a block that enters no
rate. See engine/postmortem.py rule 4.

A MARK IS NOT A VERDICT, AND THE DIFFERENCE EXPIRES
---------------------------------------------------
Five of the eleven names the operator flagged on the 2026-07-31 board were still open
that night: the number that put them on a worst-rows list was a mark. As the bars
printed, four resolved as losses and FN 07-21 closed its tenth bar at +1.66% after a
-19.31% drawdown. Nothing about the engine changed — the mark was never a prediction and
the verdict is not a correction. Anything downstream that copies a cohort label out of a
board snapshot and pins it as permanent is asserting the future, and it will come true
or not on the tape's schedule rather than the code's (a fixture that did exactly this
broke on 2026-08-06, when `data: daily collection 2026-08-06` completed FN's horizon).
`path_tails` exists so the drawdown survives the verdict that erased it.

NO LLM ANYWHERE (constitution A7). Every label is a threshold rule in engine/postmortem.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import postmortem as pm  # noqa: E402
from engine import track_scoring as ts  # noqa: E402
from engine.price_ladder import is_adjusted as _px_is_adjusted  # noqa: E402

RETRO_REL = Path("data/us_board_ledger/retro_grades.parquet")
SNAPSHOTS_REL = Path("data/us_board_ledger/snapshots.jsonl")
BASKETS_REL = Path("data/baskets/latest.json")
MEMBERSHIP_REL = Path("data/baskets/membership.json")
BENCH_REL = Path("data/yahoo/SPY.parquet")
OUT_REL = Path("data/prophet_postmortem/summary.json")
REPORT_DIR_REL = Path("reports")

#: Close-cache precedence. First cache that carries a ticker wins, matching
#: scripts/build_stock_library.universe — a name present in two caches must resolve to
#: the same series here as it does there, or the postmortem and the library would
#: disagree about the same ticker's price.
CLOSE_CACHE_GROUPS = ("breadth", "smallcap_breadth", "midcap_breadth", "russell_breadth")

#: ADJUSTED RUNGS, walked BEFORE the caches. The board admits a wider universe than the
#: caches cover — Russell plus curated extras, 1,579 names against the caches' S&P-1500 —
#: so an extras-universe name could be picked, held and exited without ever being
#: gradeable: ASTS sat in `tickers_no_price_path` for every episode it ever had (D21,
#: missed-ignitions audit). These stores are where the board itself reads those prices.
BASKET_OHLCV_REL = Path("data/baskets/ohlcv")      # per-ticker OHLCV, deep (2014+)
BASKET_EXTRAS_REL = Path("data/baskets/extras.parquet")   # wide off-index closes (~3y)

#: ERA STAMP — PRICE BASIS, 2026-08-06 (#4698 → this PR).
#:
#: This ladder used to put the four breadth caches FIRST, and the note here used to argue
#: that made it "APPEND-ONLY BY CONSTRUCTION … reordering these, or promoting one above
#: the caches, … is a different change requiring its own era stamp". That is the change,
#: and this is the era stamp.
#:
#: The reason the old order could not stand: the caches are UNADJUSTED (raw closes
#: accrued forward, re-based only at a full rebuild) while `bench` is `data/yahoo/SPY`,
#: which IS back-adjusted. `excess_pct` differences the two, so every episode whose window
#: straddled the name's ex-dividend date booked that name's own payout as underperformance
#: against SPY. THIS SITE WAS THE CONTAMINATED ONE: 796 of 807 resolved episodes (98.6%)
#: were priced from the raw caches, because the caches ran FIRST and cover the S&P 1500.
#:
#: Measured A/B on the same day, same universe, same calendar — only the basis differs:
#: 17 of 524 scored episodes move on `excess_pct`, and EVERY ONE MOVES UP (17 positive,
#: 0 negative) — the signature of the defect, since a swallowed dividend is always a
#: headwind. mean +0.588pp, median +0.480pp, worst +2.16pp (LPG 2026-06-18, −4.83 → −2.67).
#: ZERO episodes changed cohort (loser/winner/neutral), so no published classification
#: moves; what moves is the magnitude every downstream average is computed from.
#:
#: Episodes are NOT re-graded in place: this study regenerates its whole artifact on every
#: run, so the boundary is the artifact's own `method.price_basis` / `price_basis_era`
#: stamp plus the per-episode `price_source`. An artifact carrying no such stamp is era 1
#: (cache-first) and its `excess_pct` is not comparable, row for row, with era 2.
#:
#: COVERAGE: no regression, measured. 4 names (ARWR, FN, HL, TR) have a STALE
#: `baskets/ohlcv` store — it stops 2026-07-10/07-21 while the caches run to 07-31 — and
#: naively preferring it cost 2 episodes their score. `min_last` (see
#: engine.price_ladder.resolve_close) walks the remaining ADJUSTED rungs instead of
#: settling for a stale one, which restores them: n_unscored is 30 before and after, and
#: n_matured goes 526 → 529 because the adjusted stores carry deeper history than the
#: caches. Basis is never traded for coverage — a name with NO adjusted source at all
#: still resolves on the cache and says so via price_basis=unadjusted (103 episodes).
PRICE_BASIS_ERA = "adjusted_first_20260806"
PRICE_BASIS_ERA_BOUNDARY = "2026-08-06"

#: The rung each episode's price path came from, for the coverage receipt. Values are the
#: shared ladder's tags (engine.price_ladder.LADDER) so a receipt names its own basis:
#: `closes_cache_UNADJUSTED` says out loud what `breadth_caches` used to hide.
SOURCE_CACHE = "closes_cache_UNADJUSTED"
SOURCE_BASKET_OHLCV = "baskets_ohlcv"
SOURCE_BASKET_EXTRAS = "baskets_extras"
SOURCE_YAHOO = "yahoo"
SOURCE_DATA_STOCKS = "data_stocks"

#: The lane this study grades. `buy` is the board's actual call; `watch` and `laggards`
#: are context the desk publishes but does not claim as a pick.
LANE = "buy"

SCHEMA = "prophet_postmortem/v1"


# --------------------------------------------------------------------------- #
# input loading
# --------------------------------------------------------------------------- #
def load_closes(root: Path) -> pd.DataFrame:
    """Close matrix, first-hit-wins across CLOSE_CACHE_GROUPS in order."""
    frames: list[pd.DataFrame] = []
    for grp in CLOSE_CACHE_GROUPS:
        p = root / "data" / grp / "_closes_cache.parquet"
        if not p.exists():
            continue
        try:
            frames.append(pd.read_parquet(p))
        except Exception as e:  # noqa: BLE001 — a corrupt cache must not kill the run
            print(f"::warning title=prophet-postmortem::close cache {grp} unreadable ({e})",
                  flush=True)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, axis=1, sort=True)
    out = out.loc[:, ~out.columns.duplicated()]     # first cache wins
    out.index = pd.to_datetime(out.index)
    return out.sort_index()


def close_resolver(root: Path, closes: pd.DataFrame):
    """A memoized per-ticker close resolver, ADJUSTED-FIRST.

    Returns ``resolve(ticker) -> (series | None, source | None)``.

    Rung order (2026-08-06, see PRICE_BASIS_ERA above): ``baskets_ohlcv`` → ``yahoo`` →
    ``data_stocks`` → ``baskets_extras`` → the breadth caches → null. The adjusted rungs
    are delegated to ``engine.price_ladder`` so this study, ``scripts/grade_us_board.py``
    and any future grader share ONE ladder instead of three hand-rolled ones — the
    knowledge that ``engine/desk_grader.py`` already had on 2026-07-04 and that never
    propagated. ``tests/test_price_basis_graders.py`` fails the build if it stops being
    shared.

    The cache stays as the LAST rung rather than being dropped: coverage comes first, and
    a name with no adjusted counterpart is worth grading on a disclosed unadjusted basis
    rather than deleting from the study that exists to measure it. Every episode carries
    the rung it came from (``price_source``) and whether that rung is adjusted
    (``price_basis``), so the residual is measured on the artifact.

    The pre-loaded ``closes`` frame supplies the cache rung so a run does not read the
    ~1,500-column caches twice; the adjusted rungs are lazy and memoized, so a run opens
    only the parquets it actually needs.
    """
    from engine import price_ladder as _pl

    memo: dict[str, tuple["pd.Series | None", "str | None"]] = {}
    data_dir = str(Path(root) / "data")
    # Inject the already-loaded cache panel: it saves a second wide read, and it
    # guarantees the ladder's last rung IS the frame this module reasons about elsewhere
    # (the episode calendar, the coverage receipt) instead of a re-read that could differ.
    books = _pl.make_books(data_dir, cache_frames=[closes])
    # ONE CALENDAR FOR THE WHOLE STUDY. The cache panel's last session is both the
    # freshness floor and the CEILING every rung is clipped to.
    #
    # The ceiling is not cosmetic. Under the old cache-first ladder 796 of 807 episodes
    # were priced from the caches, so every in-flight MARK was struck on the same session.
    # Resolving adjusted-first mixes in stores with different end dates — data/yahoo
    # carries FN to 2026-08-04 while the caches stop at 07-31 — and an unclipped ladder
    # would mark FN four sessions later than its peers purely because its store is
    # fresher. That moved FN@2026-07-21 out of the loser cohort on a data-vintage
    # difference, not on anything the name did. Clipping restores one as-of for all.
    min_last = None
    if closes is not None and not getattr(closes, "empty", True) and len(closes.index):
        min_last = pd.Timestamp(closes.index.max())

    def resolve(ticker: str) -> tuple["pd.Series | None", "str | None"]:
        if ticker in memo:
            return memo[ticker]
        r = _pl.resolve_close(ticker, data_dir=data_dir, asof=min_last,
                              min_last=min_last, _book=books)
        memo[ticker] = (r.series, r.price_source) if r.ok else (None, None)
        return memo[ticker]

    return resolve


def load_bench(root: Path) -> "pd.Series | None":
    p = root / BENCH_REL
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    s = df["close"] if "close" in df.columns else df.iloc[:, 0]
    s = pd.to_numeric(s, errors="coerce").dropna()
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def load_snapshots(root: Path) -> dict[str, dict[str, dict]]:
    """{board_date: {ticker: row}} over EVERY lane.

    Every lane, not just `buy`: the hold-state history that `thesis_break` reads has to
    follow a name after it drops out of `buy` into `watch`, which is exactly when a base
    breaks. Episode membership still comes from the buy lane alone.
    """
    out: dict[str, dict[str, dict]] = {}
    p = root / SNAPSHOTS_REL
    if not p.exists():
        return out
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            d = str(doc.get("as_of") or "")
            if not d:
                continue
            bucket = out.setdefault(d, {})
            for lane in ("buy", "watch", "leaders", "laggards"):
                for row in (doc.get(lane) or []):
                    tk = row.get("ticker")
                    if tk and tk not in bucket:
                        bucket[str(tk)] = row
    return out


def load_retro(root: Path) -> pd.DataFrame:
    p = root / RETRO_REL
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


def board_days(retro: pd.DataFrame, snaps: dict[str, dict[str, dict]],
               root: Path) -> dict[str, set[str]]:
    """{board_date: {ticker}} for the buy lane, unioning both sources.

    The retro ledger reaches back before the snapshot archive starts and the archive
    reaches forward past the last retro grade, so neither source alone covers the
    history. Where they overlap they agree (same nightly artifact, two encodings).
    """
    days: dict[str, set[str]] = {}
    if not retro.empty and {"as_of", "ticker", "lane"} <= set(retro.columns):
        sub = retro[retro["lane"].astype(str) == LANE]
        for d, tk in zip(sub["as_of"], sub["ticker"]):
            days.setdefault(str(d), set()).add(str(tk))
    p = root / SNAPSHOTS_REL
    if p.exists():
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                except json.JSONDecodeError:
                    continue
                d = str(doc.get("as_of") or "")
                if not d:
                    continue
                for row in (doc.get(LANE) or []):
                    if row.get("ticker"):
                        days.setdefault(d, set()).add(str(row["ticker"]))
    return days


# --------------------------------------------------------------------------- #
# git archaeology — theme state at a past date
# --------------------------------------------------------------------------- #
def basket_history(root: Path) -> list[tuple[str, dict[str, dict]]]:
    """[(blob_as_of, {theme_id: theme})] for every committed revision, ascending.

    Keyed on the blob's OWN `as_of`, not the commit date: the render lane commits the
    artifact the morning after it is built, so commit dates run a day ahead of the state
    they carry, and a caller asking "what did the desk think on 07-09" wants the file
    the 07-09 board was built from.

    LOUD on git failure. Silently returning [] would blank every theme reading in the
    artifact and leave the `sector_headwind` label evaluating against nothing — the
    same wrong-and-silent degradation that truncated the US ledger on 2026-07-26.
    """
    proc = subprocess.run(
        ["git", "log", "--format=%H", "--", str(BASKETS_REL)],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git log over {BASKETS_REL} failed (rc={proc.returncode}): "
            f"{proc.stderr.strip()[:300]} — refusing to emit a postmortem whose "
            "entry-time theme context would be silently empty."
        )
    by_asof: dict[str, dict[str, dict]] = {}
    for sha in proc.stdout.split():
        blob = subprocess.run(
            ["git", "show", f"{sha}:{BASKETS_REL}"],
            cwd=root, capture_output=True, text=True, check=False,
        ).stdout
        if not blob:
            continue
        try:
            doc = json.loads(blob)
        except json.JSONDecodeError:
            continue
        asof = str(doc.get("as_of") or "")
        if not asof or asof in by_asof:
            continue          # git log is newest-first; the newest blob per as_of wins
        themes = {
            str(t.get("id")): t
            for t in (doc.get("themes") or [])
            if isinstance(t, dict) and t.get("id")
        }
        if themes:
            by_asof[asof] = themes
    return sorted(by_asof.items())


def themes_as_of(history: list[tuple[str, dict[str, dict]]], date: str
                 ) -> tuple[str | None, dict[str, dict]]:
    """The latest revision whose as_of is <= `date`. ('', {}) when none exists yet."""
    best: tuple[str | None, dict[str, dict]] = (None, {})
    for asof, themes in history:          # ascending
        if asof <= date:
            best = (asof, themes)
        else:
            break
    return best


def membership_map(root: Path) -> dict[str, list[str]]:
    """{ticker: [basket_id, ...]} from the CURRENT membership file (drift caveat above)."""
    p = root / MEMBERSHIP_REL
    if not p.exists():
        return {}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, set[str]] = {}
    for bid, basket in sorted((doc.get("baskets") or {}).items()):
        for member in (basket.get("members") or []):
            tk = member.get("ticker")
            if tk:
                out.setdefault(str(tk), set()).add(str(bid))
    return {tk: sorted(v) for tk, v in sorted(out.items())}


# --------------------------------------------------------------------------- #
# cohort integrity — original source membership + era stamps (descriptive only)
# --------------------------------------------------------------------------- #
# Q02/B22: a receipt of which board definition each existing episode was ORIGINALLY
# admitted under, read from the two original buy-membership sources. Purely additive
# and descriptive: nothing here re-grades, re-partitions or merges episodes, and no
# rank_by is date-inferred, back-filled from the current definition, or renamed into a
# manufactured legacy era — an absent/empty/null-like stamp stays MISSING ATTRIBUTION.
# Every status dict is published on the artifact (`cohort_integrity.sources_read`) so a
# malformed or unreadable source can never look like validated source absence.


def _iso_date_key(value: Any) -> str | None:
    """A strict ISO calendar-date key from a source date value, or None.

    Strings must already be canonical YYYY-MM-DD; pandas/datetime timestamps are
    converted through their OWN calendar date — never stringified into
    "2026-07-01 00:00:00" (a malformed key), never sliced. Anything else, nullish
    spellings included, comes back None for the caller to count and disclose. No
    lexical comparison in the integrity path ever sees a malformed key.
    """
    # pandas NaT is also a datetime instance; reject nulls before native date logic.
    if value is None or value is pd.NaT or value is pd.NA:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        try:
            parsed = datetime.date.fromisoformat(value)
        except ValueError:
            return None
        return value if parsed.isoformat() == value else None
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return None


def _integrity_ticker_key(value: Any) -> str | None:
    """A usable ticker key, or None. Nullish spellings are missing/invalid records,
    never tickers, and are counted and disclosed by the caller."""
    if not isinstance(value, str):
        return None
    if value.strip() in ("", "None", "nan", "NaT", "<NA>", "null"):
        return None
    return value


def load_retro_membership(root: Path) -> tuple[dict[str, dict[str, list[str | None]]], dict]:
    """{date: {ticker: [rank_by|None, ...]}} for the buy lane, ONE entry per source record.

    The ledger stores one row per (as_of, ticker, horizon), so two horizons on one night
    are two records here; a stamp that differs between them is a real same-source,
    same-date conflict and is deliberately NOT deduped away the way `_retro_index`
    dedupes entry-time state for the existing context fields.

    `rank_by` is kept EXACTLY as recorded (pm.integrity_stamp only folds
    true null spellings to missing). A missing `rank_by` COLUMN means every record
    is stamped missing — disclosed in the status, never filled.

    Date keys are strict ISO calendar dates: timestamp values are converted through
    their own date; malformed ones are COUNTED (`n_malformed_dates`) and skipped —
    never stringified into a key any comparison could mis-order.
    """
    status: dict[str, Any] = {
        "source": "retro", "path": str(RETRO_REL), "readable": False, "error": None,
        "n_rows": 0, "n_buy_records": 0, "rank_by_column_present": False,
        "n_invalid_membership_records": 0, "n_malformed_dates": 0,
        "n_missing_stamp_records": 0,
    }
    out: dict[str, dict[str, list[str | None]]] = {}
    p = root / RETRO_REL
    if not p.exists():
        status["error"] = "missing"
        return out, status
    try:
        # Inspect metadata and project only provenance. Receipt-only inspection must
        # not load outcome/return columns even when the original ledger carries them.
        from pyarrow.parquet import read_schema
        available = set(read_schema(p).names)
        required = {"as_of", "ticker", "lane"}
        missing = sorted(required - available)
        if missing:
            status["error"] = "missing_membership_columns: " + ", ".join(missing)
            return out, status
        columns = [name for name in ("as_of", "ticker", "lane", "rank_by")
                   if name in available]
        df = pd.read_parquet(p, columns=columns)
    except Exception as e:  # noqa: BLE001 — an unreadable source is receipt evidence
        status["error"] = f"{type(e).__name__}: {e}"[:300]
        return out, status
    status["readable"] = True
    status["n_rows"] = int(len(df))
    if df.empty:
        return out, status
    # A recorded date with no buy rows still supplies source reach. It must differ
    # from an unobserved date when checking the other source's membership. A
    # malformed date value cannot seed a key; the buy-row pass below counts it.
    for date in df["as_of"]:
        recorded_date = _iso_date_key(date)
        if recorded_date is not None:
            out.setdefault(recorded_date, {})
    sub = df[df["lane"].astype(str) == LANE]
    stamps = sub["rank_by"] if "rank_by" in sub.columns else pd.Series(
        [None] * len(sub), index=sub.index)
    status["rank_by_column_present"] = bool("rank_by" in sub.columns)
    for d, tk, raw in zip(sub["as_of"], sub["ticker"], stamps):
        d_s = _iso_date_key(d)
        if d_s is None:
            status["n_malformed_dates"] += 1
            continue
        tk_s = _integrity_ticker_key(tk)
        if tk_s is None:
            status["n_invalid_membership_records"] += 1
            continue
        stamp = pm.integrity_stamp(raw)
        if stamp is None:
            status["n_missing_stamp_records"] += 1
        out.setdefault(d_s, {}).setdefault(tk_s, []).append(stamp)
        status["n_buy_records"] += 1
    return out, status


def load_snapshot_membership(root: Path) -> tuple[dict[str, dict[str, list[str | None]]], dict]:
    """{date: {ticker: [rank_by|None]}} for the buy lane from snapshots.jsonl.

    The nightly snapshot carries the board-page `rank_by` stamp at the top level
    (written by scripts.grade_us_board.snapshot_today), so every buy-lane ticker on that
    date inherits the SAME recorded page stamp for that date — one record per ticker.
    Buy lane only: non-buy lanes never add integrity membership.

    Malformed lines, lines without a usable `as_of`, malformed dates and invalid
    membership rows are COUNTED on the status instead of being dropped silently, so a
    truncated archive is visible on the receipt. A second document for an already-seen
    date is a DUPLICATE OBSERVATION: identical duplicates are disclosed and harmless,
    but one whose page stamp or buy membership set differs is a same-source conflict
    (`n_conflicting_duplicate_observations`) that blocks clean assignment and per-era
    rates. Original records are never deduped away either way.
    """
    status: dict[str, Any] = {
        "source": "snapshot", "path": str(SNAPSHOTS_REL), "readable": False, "error": None,
        "n_lines": 0, "n_docs": 0, "n_malformed_lines": 0, "n_lines_without_as_of": 0,
        "n_buy_records": 0, "rank_by_column_present": False,
        "n_invalid_membership_records": 0, "n_malformed_dates": 0,
        "n_missing_stamp_records": 0, "n_duplicate_as_of_docs": 0,
        "n_conflicting_duplicate_observations": 0,
        "conflicting_duplicate_dates": [],
    }
    out: dict[str, dict[str, list[str | None]]] = {}
    p = root / SNAPSHOTS_REL
    if not p.exists():
        status["error"] = "missing"
        return out, status
    try:
        fh = p.open(encoding="utf-8")
    except OSError as e:
        status["error"] = f"{type(e).__name__}: {e}"[:300]
        return out, status
    seen: dict[str, tuple[str | None, frozenset[str]]] = {}
    try:
        with fh:
            for line in fh:
                status["n_lines"] += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                except json.JSONDecodeError:
                    status["n_malformed_lines"] += 1
                    continue
                if not isinstance(doc, dict):
                    status["n_malformed_lines"] += 1
                    continue
                d = _iso_date_key(doc.get("as_of"))
                if d is None:
                    status["n_lines_without_as_of"] += 1
                    continue
                status["n_docs"] += 1
                out.setdefault(d, {})
                stamp = pm.integrity_stamp(doc.get("rank_by"))
                if stamp is not None:
                    status["rank_by_column_present"] = True
                buy_rows = doc.get(LANE, [])
                members: set[str] = set()
                if not isinstance(buy_rows, list):
                    status["n_invalid_membership_records"] += 1
                else:
                    for row in buy_rows:
                        if not isinstance(row, dict):
                            status["n_invalid_membership_records"] += 1
                            continue
                        tk = _integrity_ticker_key(row.get("ticker"))
                        if tk is None:
                            status["n_invalid_membership_records"] += 1
                            continue
                        members.add(tk)
                        out.setdefault(d, {}).setdefault(tk, []).append(stamp)
                        status["n_buy_records"] += 1
                        if stamp is None:
                            status["n_missing_stamp_records"] += 1
                if d in seen:
                    status["n_duplicate_as_of_docs"] += 1
                    prev_stamp, prev_members = seen[d]
                    if prev_stamp != stamp or prev_members != frozenset(members):
                        status["n_conflicting_duplicate_observations"] += 1
                        status["conflicting_duplicate_dates"].append(d)
                else:
                    seen[d] = (stamp, frozenset(members))
    except (OSError, UnicodeError) as exc:
        status["error"] = f"{type(exc).__name__}: {exc}"[:300]
        return out, status
    status["readable"] = True
    return out, status


def _integrity_warnings(retro_status: dict, snap_status: dict) -> list[str]:
    """Plain warnings for what the receipt must not hide.

    Read/schema integrity only: a missing `rank_by` column or unstamped records stay
    unknown/partial ATTRIBUTION and are warned about — they are neither an era nor a
    verified absence, and they carry no scientific or promotion meaning either way.
    """
    out: list[str] = []
    for name, st in (("retro", retro_status), ("snapshot", snap_status)):
        if not st.get("readable") or st.get("error"):
            out.append(f"source `{name}` unreadable or missing ({st.get('error')}); "
                       "its stamps are absent, never verified absent")
            continue
        if st.get("n_malformed_lines"):
            out.append(f"source `{name}`: {st['n_malformed_lines']} malformed line(s) "
                       "skipped and counted")
        if st.get("n_lines_without_as_of"):
            out.append(f"source `{name}`: {st['n_lines_without_as_of']} line(s) without "
                       "a usable as_of skipped and counted")
        if st.get("n_malformed_dates"):
            out.append(f"source `{name}`: {st['n_malformed_dates']} malformed/non-ISO "
                       "membership date(s) skipped and counted")
        if st.get("n_invalid_membership_records"):
            out.append(f"source `{name}`: {st['n_invalid_membership_records']} invalid "
                       "membership record(s) skipped and counted")
        if st.get("n_conflicting_duplicate_observations"):
            out.append(f"source `{name}`: "
                       f"{st['n_conflicting_duplicate_observations']} same-date duplicate "
                       "observation(s) with differing stamp or membership sets — clean "
                       "assignment and per-era rates are blocked")
        if st.get("rank_by_column_present") is False:
            out.append(f"source `{name}`: no `rank_by` column — every stamp is missing "
                       "attribution (unknown/partial), never an era")
        elif st.get("n_missing_stamp_records"):
            out.append(f"source `{name}`: {st['n_missing_stamp_records']} membership "
                       "record(s) carry no stamp — missing attribution")
    return out


def _cohort_integrity_block(root: Path, episodes: list[dict], *, as_of: str,
                            include_era_rates: bool = True) -> dict:
    """Build the descriptive integrity block for ``episodes`` (read-only, no scoring).

    ``as_of`` is REQUIRED: the frozen original cut every membership observation is read
    through — the generation path's real board as_of, or a preserved artifact's
    validated as_of. Never the clock, the current config, or the membership sources'
    latest vintage.

    ``episodes`` rows are read for identity only — ticker, entry_date, board_exit_date,
    maturity. On the generation path (`include_era_rates=True`) the descriptive per-era
    summaries are computed by the engine with the existing `pm.aggregate` over those
    already-graded rows. The receipt-only path passes False: no aggregator runs there
    at all.
    """
    retro_m, retro_status = load_retro_membership(root)
    snap_m, snap_status = load_snapshot_membership(root)
    source_complete = all(
        status.get("readable") and not status.get("error")
        and not status.get("n_malformed_lines")
        and not status.get("n_lines_without_as_of")
        and not status.get("n_invalid_membership_records")
        and not status.get("n_malformed_dates")
        and not any(d <= as_of for d in status.get("conflicting_duplicate_dates", []))
        for status in (retro_status, snap_status)
    )
    block = pm.cohort_integrity_block({"retro": retro_m, "snapshot": snap_m}, episodes,
                                      as_of=as_of,
                                      include_era_rates=include_era_rates and source_complete)
    block["sources_read"] = {"retro": retro_status, "snapshot": snap_status}
    block["source_validation"] = {
        "state": "complete" if source_complete else "incomplete",
        "as_of": as_of,
        "meaning": ("Original source READ and schema integrity only — this state "
                    "carries no scientific or promotion authority."),
    }
    if include_era_rates and not source_complete:
        block["per_era_unavailable_reason"] = "original_membership_source_incomplete"
    block["warnings"] = _integrity_warnings(retro_status, snap_status)
    return block


def _validated_inspection_artifact(path: Path) -> tuple[dict, str]:
    """Read and validate a PRESERVED artifact for read-only inspection.

    Refuses — with a clear nonzero SystemExit, BEFORE any scoring, classification,
    aggregation or write — unreadable, undecodable, non-object, foreign-schema,
    invalid-as_of, non-list or empty episode lists, and malformed identity rows.
    Nothing is repaired: an artifact that cannot be validated is not inspected. The
    artifact's own `as_of` is the frozen membership cut for the receipt; it is never
    re-derived from the current sources or the clock.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SystemExit(f"--artifact unreadable: {type(exc).__name__}: {exc}") from None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"--artifact is not decodable UTF-8: {exc}") from None
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--artifact is not decodable JSON: {exc}") from None
    if not isinstance(doc, dict):
        raise SystemExit(
            "--artifact must be a prophet_postmortem/v1 artifact with episode rows "
            f"(a JSON object), got {type(doc).__name__}")
    if doc.get("schema") != SCHEMA:
        raise SystemExit(
            "--artifact must be a prophet_postmortem/v1 artifact with episode rows "
            f"(got schema {doc.get('schema')!r})")
    rows = doc.get("episodes")
    if not isinstance(rows, list) or not rows:
        raise SystemExit(
            "--artifact must be a prophet_postmortem/v1 artifact with a NON-EMPTY "
            "episode list")
    try:
        as_of = pm.iso_calendar_date(doc.get("as_of"), field="artifact as_of")
    except ValueError as exc:
        raise SystemExit(f"--artifact {exc} (prophet_postmortem/v1)") from None
    seen_identity: set[tuple[str, str]] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SystemExit(
                f"--artifact episode row {i} is not an object; malformed identity rows "
                "are refused (prophet_postmortem/v1)")
        ticker = row.get("ticker")
        if not isinstance(ticker, str) or not ticker.strip():
            raise SystemExit(
                f"--artifact episode row {i} has an invalid ticker {ticker!r}; "
                "malformed identity rows are refused (prophet_postmortem/v1)")
        for field in ("entry_date", "board_exit_date"):
            value = row.get(field)
            if field == "board_exit_date" and value is None:
                continue          # None is the actual open sentinel
            try:
                pm.iso_calendar_date(value, field=f"episodes[{i}].{field}")
            except ValueError as exc:
                raise SystemExit(
                    f"--artifact episode row {i}: {exc} (prophet_postmortem/v1)") from None
        entry, exit_ = row["entry_date"], row.get("board_exit_date")
        if entry > as_of:
            raise SystemExit(f"--artifact episode row {i}: entry_date after artifact as_of")
        if exit_ is not None and exit_ <= entry:
            raise SystemExit(f"--artifact episode row {i}: invalid exclusive episode interval")
        identity = (ticker, entry)
        if identity in seen_identity:
            raise SystemExit(f"--artifact episode row {i}: ambiguous repeated episode identity")
        seen_identity.add(identity)
    invalid = [a for a in pm.integrity_assignments({}, rows, as_of=as_of)
               if a.get("unavailable")]
    if invalid:
        raise SystemExit(f"--artifact invalid episode identity or interval: {invalid[0]['unavailable_reason']}")
    return doc, as_of


def _cohort_integrity_only(root: Path, artifact: str | None) -> int:
    """`--cohort-integrity-only`: print the receipt for a PRESERVED artifact, write nothing.

    Reads the artifact's episode list (identity + maturity, strictly validated) and the
    two original membership/stamp sources, and prints the integrity receipt as JSON to
    stdout, read through the PRESERVED artifact's own validated as_of as the frozen
    membership cut. The scorer, the classifier, the aggregator and `build_rows` are
    never called, and no byte is written anywhere — tests pin this by monkeypatching
    every one of those entrypoints to raise and by diffing every input byte (including
    data/us_board_ledger) across the run.
    """
    if not artifact:
        raise SystemExit(
            "--cohort-integrity-only requires --artifact PATH (the preserved "
            "summary.json to inspect read-only)")
    doc, as_of = _validated_inspection_artifact(Path(artifact))
    episodes = [
        {"ticker": r.get("ticker"),
         "entry_date": r.get("entry_date"),
         "board_exit_date": r.get("board_exit_date"),
         "maturity": r.get("maturity")}
        for r in (doc.get("episodes") or [])
    ]
    block = _cohort_integrity_block(root, episodes, as_of=as_of,
                                    include_era_rates=False)
    block["as_of"] = as_of
    block["artifact"] = str(artifact)
    block["receipt_only_note_en"] = (
        "Receipt only: the per-era descriptive summaries are deliberately absent here — "
        "they are computed on generation from full graded rows, and this read-only path "
        "never re-aggregates outcomes. Membership is read through the preserved "
        "artifact's own as_of as the frozen cut.")
    print(json.dumps(block, ensure_ascii=False, indent=1))
    return 0


# --------------------------------------------------------------------------- #
# episode assembly
# --------------------------------------------------------------------------- #
def _retro_index(retro: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """{(as_of, ticker): row} for the buy lane, one row per key (lowest horizon wins —
    the columns this study reads are entry-time state, identical across horizons)."""
    out: dict[tuple[str, str], dict] = {}
    if retro.empty or "lane" not in retro.columns:
        return out
    sub = retro[retro["lane"].astype(str) == LANE]
    if "horizon" in sub.columns:
        sub = sub.sort_values(["as_of", "ticker", "horizon"], kind="stable")
    for rec in sub.to_dict("records"):
        key = (str(rec.get("as_of")), str(rec.get("ticker")))
        out.setdefault(key, rec)
    return out


def _hold_broken(snaps: dict[str, dict[str, dict]], ticker: str,
                 entry_date: str, last_date: str | None) -> dict | None:
    """First board night in (entry_date, last_date] that stamped hold.state == broken."""
    for d in sorted(snaps):
        if d <= entry_date:
            continue
        if last_date is not None and d > last_date:
            break
        row = snaps.get(d, {}).get(ticker)
        state = (((row or {}).get("hold") or {}).get("state")) if row else None
        if str(state or "") == "broken":
            return {"board_date": d, "date": d}
    return None


def _round_trip_counts(rows: list[dict]) -> dict:
    """How many episodes crossed a gate their verdict does not show, by direction.

    `n` is the SET, so the two direction counts may double-count an episode that crossed
    both — `n_crossed_both` is published beside them and the report's sentence reconciles
    (loser + winner - both = n) rather than leaving a reader to guess.
    """
    rt = [r for r in rows if r["path_tails"]]
    lose = [r for r in rt if "loser" in r["path_tails"]]
    win = [r for r in rt if "winner" in r["path_tails"]]
    both = [r for r in rt if len(r["path_tails"]) == 2]
    return {
        "n": len(rt),
        "n_crossed_loser_gate": len(lose),
        "n_crossed_winner_gate": len(win),
        "n_crossed_both": len(both),
        "n_verdict_outside_both_tails": len(
            [r for r in rt if r["cohort"] not in ("loser", "winner")]),
        "loser_gate_pct": pm.LOSER_ABS_PCT,
        "winner_gate_pct": pm.WINNER_ABS_PCT,
    }


def _compact_context(ctx: dict) -> dict:
    """The label-bearing fields only, for the episodes that were genuinely uneventful.

    Both tails keep their full entry context — that is what the learning loop reads — and
    so does any episode whose PATH crossed a gate its verdict does not show (`path_tails`,
    the G3 exit-policy set). The rest keep every field a label keys on (so every label in
    the artifact stays re-derivable by hand) but drop the rest of the nested board
    payload, which is context nobody reads for a name that finished flat AND travelled
    flat. The full record is one deterministic re-run away:
    `python -m scripts.prophet_postmortem`.

    Trimming on the verdict ALONE was the older rule, and it deleted the entry context of
    exactly the episodes the exit-policy question is about — a name that fell 19% and
    closed +1.7% read as "finished flat, nothing to see".
    """
    ext = ctx.get("extension") or {}
    spot = ctx.get("spotlight") or {}
    plan = ctx.get("entry_plan") or {}
    conv = ctx.get("conviction") or {}
    return {
        "compact": True,
        "sector": ctx.get("sector"),
        "basket_asof": ctx.get("basket_asof"),
        "themes": [{"id": t.get("id"), "reco": t.get("reco")}
                   for t in (ctx.get("themes") or [])],
        "sector_basket": {k: (ctx.get("sector_basket") or {}).get(k)
                          for k in ("id", "reco", "label")} if ctx.get("sector_basket") else None,
        "spotlight": {"dir": spot.get("dir"), "sector_stage": spot.get("sector_stage"),
                      "sector_pctile_252d": spot.get("sector_pctile_252d")},
        "extension": {k: ext.get(k) for k in
                      ("overextended", "entry_tier", "ext_risk", "price",
                       "chase_above", "above_chase")},
        "entry_plan": {"status": plan.get("status"), "stop": plan.get("stop"),
                       "hold_state": plan.get("hold_state")},
        "conviction": {"band": conv.get("band"), "alpha": conv.get("alpha")},
    }


def _sessions_between(calendar: pd.DatetimeIndex, a: str, b: str) -> int | None:
    try:
        ia = calendar.searchsorted(pd.Timestamp(a), side="left")
        ib = calendar.searchsorted(pd.Timestamp(b), side="left")
    except (TypeError, ValueError):
        return None
    return int(ib - ia)


def _mark_at(prev: dict, when: str) -> float | None:
    """The prior position's open P/L, in %, on the night the name came back.

    None when the prior episode has no series or no fill price — the input the
    BUILDABLE `open_drawdown_at_readmit` leg is made of. The engine nulls that leg
    rather than reading the absence as "was not under water".
    """
    sc, series = prev["sc"], prev["series"]
    entry_px = (sc or {}).get("entry")
    if series is None or not entry_px:
        return None
    j = series.index.searchsorted(pd.Timestamp(when), side="left")
    if j >= len(series):
        return None
    return (float(series.iloc[j]) / float(entry_px) - 1.0) * 100.0


def _rev(date: Any) -> str:
    """Sort key that puts the LATEST date first inside an ascending `min()`.

    Dates here are fixed-width ISO strings, so inverting each character's code point
    orders them backwards without parsing. Keeps every tie-break deterministic.
    """
    return "".join(chr(255 - ord(ch)) for ch in str(date))


def prior_episodes(scored: list[dict], calendar: "pd.DatetimeIndex"
                   ) -> dict[tuple[str, str], dict]:
    """{(ticker, entry_date): prior-episode comparison} for the `re_admission` label.

    SCANS EVERY PRIOR EPISODE IN THE WINDOW, not just the immediately preceding one.
    Reading `items[i-1]` alone made the label answer a different question than the one
    it prints: a name that came back twice in a fortnight was compared only against its
    latest run, so a qualifying loss two runs back — inside the same 10-session window —
    was invisible. The scan collects every prior run whose board exit sits within
    `READMIT_MAX_SESSIONS` sessions of this entry and then picks ONE to report, by a
    fixed precedence:

      1. a prior that was ALREADY >= 8% under water at the re-admission (the buildable
         leg) — most negative mark wins, latest entry date breaks a tie;
      2. else a prior that RESOLVED to a >= 8% loss (the hindsight leg) — most negative
         outcome wins, latest entry date breaks a tie;
      3. else the NEAREST in-window prior, reported as a decided negative so the reader
         can see what the comparison actually was.

    NULLS, NOT SILENT ZEROS. An in-window prior that could not be scored (no close path)
    is not evidence that the name came back clean, so when no scoreable prior fires the
    row comes back `{"undecidable": "prior_episode_not_scoreable"}` and the engine nulls
    the label and both legs. An entry with NO in-window prior at all gets no key here at
    all, so the caller's lookup yields None — a decided negative that stays in every
    denominator.

    Every row carries `prior_matured`, because an unmatured prior's `outcome_pct` is a
    MARK — outcome-conditioned, and not the same evidence as a resolved loss.
    """
    by_ticker: dict[str, list[dict]] = {}
    for item in scored:
        by_ticker.setdefault(item["ep"]["ticker"], []).append(item)

    out: dict[tuple[str, str], dict] = {}
    for tk, items in sorted(by_ticker.items()):
        items.sort(key=lambda it: (it["ep"]["entry_date"], str(it["ep"].get("exit_date"))))
        for i, cur in enumerate(items):
            cs = str(cur["ep"]["entry_date"])
            cands: list[dict] = []
            n_unscoreable = 0
            for prev in items[:i]:
                prev_exit = str(prev["ep"].get("exit_date") or prev["ep"]["entry_date"])
                gap = _sessions_between(calendar, prev_exit, cs)
                if gap is None or gap > pm.READMIT_MAX_SESSIONS:
                    continue
                if prev["sc"] is None:
                    n_unscoreable += 1
                    continue
                psc = prev["sc"]
                matured = bool(psc.get("matured"))
                cands.append({
                    "entry_date": prev["ep"]["entry_date"],
                    "outcome_pct": psc.get("pnl") if matured else psc.get("mark"),
                    "prior_matured": matured,
                    "sessions_since_prior_exit": gap,
                    "mark_at_readmit_pct": _mark_at(prev, cs),
                })
            n_window = len(cands) + n_unscoreable
            if not n_window:
                continue                      # decided negative: no prior in the window

            open_leg = [c for c in cands
                        if c["mark_at_readmit_pct"] is not None
                        and c["mark_at_readmit_pct"] <= pm.READMIT_LOSS_PCT]
            loss_leg = [c for c in cands
                        if c["outcome_pct"] is not None
                        and c["outcome_pct"] <= pm.READMIT_LOSS_PCT]
            if open_leg:
                pick = min(open_leg, key=lambda c: (float(c["mark_at_readmit_pct"]),
                                                    _rev(c["entry_date"])))
                selected_by = pm.READMIT_LEG_OPEN_DRAWDOWN
            elif loss_leg:
                pick = min(loss_leg, key=lambda c: (float(c["outcome_pct"]),
                                                    _rev(c["entry_date"])))
                selected_by = pm.READMIT_LEG_PRIOR_LOSS
            elif n_unscoreable:
                out[(tk, cs)] = {
                    "undecidable": "prior_episode_not_scoreable",
                    "n_priors_in_window": n_window,
                    "n_priors_unscoreable": n_unscoreable,
                }
                continue
            else:
                pick = min(cands, key=lambda c: (c["sessions_since_prior_exit"],
                                                 _rev(c["entry_date"])))
                selected_by = "nearest_prior_no_leg_fired"
            out[(tk, cs)] = {
                **pick,
                "selected_by": selected_by,
                "n_priors_in_window": n_window,
                "n_priors_unscoreable": n_unscoreable,
            }
    return out


def build_rows(root: Path = ROOT, horizon: int = ts.DEFAULT_HORIZON) -> dict:
    """Score, contextualise and classify every buy-lane episode. Returns the artifact."""
    retro = load_retro(root)
    snaps = load_snapshots(root)
    closes = load_closes(root)
    bench = load_bench(root)
    history = basket_history(root)
    members = membership_map(root)
    retro_by_key = _retro_index(retro)

    days = board_days(retro, snaps, root)
    if not days:
        raise RuntimeError(
            "no board days found in retro_grades.parquet or snapshots.jsonl — "
            "refusing to emit an empty postmortem that would read as 'no losses'."
        )
    episodes = ts.build_episodes(days)
    calendar = bench.index if bench is not None else closes.index

    # ── pass 1: score every episode ───────────────────────────────────────────
    resolve_close = close_resolver(root, closes)
    scored: list[dict] = []
    no_price: list[str] = []
    unresolved: set[str] = set()
    price_sources: dict[str, int] = {}
    for ep in episodes:
        tk, d0 = ep["ticker"], ep["entry_date"]
        series, source = resolve_close(tk)
        if series is None:
            unresolved.add(tk)
        sc = ts.score_episode(series, d0, horizon, bench_close=bench) if series is not None else None
        if sc is None:
            no_price.append(f"{tk}@{d0}")
            scored.append({"ep": ep, "sc": None, "series": None, "source": source})
            continue
        price_sources[source] = price_sources.get(source, 0) + 1
        scored.append({"ep": ep, "sc": sc, "series": series, "source": source})

    # ── pass 2: prior-episode scan, per ticker, in entry order ────────────────
    prior_by_key = prior_episodes(scored, calendar)

    # ── pass 3: context + classification ──────────────────────────────────────
    rows: list[dict] = []
    for item in scored:
        ep, sc, series = item["ep"], item["sc"], item["series"]
        px_source = item.get("source")
        tk, d0 = ep["ticker"], ep["entry_date"]
        snap_row = snaps.get(d0, {}).get(tk)
        retro_row = retro_by_key.get((d0, tk))
        basket_asof, themes = themes_as_of(history, d0)
        ctx = pm.entry_context(snap_row, retro_row, themes, members.get(tk), basket_asof)

        if sc is None:
            maturity, outcome, excess, mark = "unscored", None, None, None
            mae = mfe = held = None
            fill_date = None
        else:
            matured = bool(sc.get("matured"))
            fill_pending = bool(sc.get("fill_pending"))
            maturity = "matured" if matured else ("unscored" if fill_pending else "in_flight")
            outcome = sc.get("pnl") if matured else sc.get("mark")
            excess = sc.get("excess")
            mark = sc.get("mark")
            mae, mfe, held = sc.get("mae"), sc.get("mfe"), sc.get("held")
            fill_date = sc.get("entry_date")

        # Three different reasons a path can be missing, and they must not share a
        # label: only the first is a coverage hole. A name whose fill bar has not
        # printed yet has a perfectly good price series.
        path = None
        path_reason = "no_price_path"
        if series is None:
            path_reason = "no_price_path"
        elif fill_date is None:
            path_reason = "fill_not_yet_printed"
        else:
            path = pm.path_features(
                series, fill_date, held, (ctx.get("entry_plan") or {}).get("stop"))
            if path is None:
                path_reason = "window_too_short"

        broken = _hold_broken(snaps, tk, d0, ep.get("exit_date"))
        prior = prior_by_key.get((tk, d0))
        labels, nulls = pm.classify(
            outcome_pct=outcome, excess_pct=excess, ctx=ctx, path=path,
            hold_broken=broken, prior=prior,
            path_missing_reason=path_reason,
        )

        mae_pct = None if mae is None else round(float(mae), 2)
        mfe_pct = None if mfe is None else round(float(mfe), 2)
        cohort = pm.cohort_of(outcome, excess)

        rows.append({
            "ticker": tk,
            "entry_date": d0,
            "board_exit_date": ep.get("exit_date"),
            "fill_date": fill_date,
            "horizon": horizon,
            "maturity": maturity,
            "outcome_pct": None if outcome is None else round(float(outcome), 2),
            "pnl_pct": (round(float(sc["pnl"]), 2)
                        if sc and sc.get("pnl") is not None else None),
            "excess_pct": None if excess is None else round(float(excess), 2),
            "mark_pct": None if mark is None else round(float(mark), 2),
            "mae_pct": mae_pct,
            "mfe_pct": mfe_pct,
            "held": held,
            "cohort": cohort,
            # Gates the PATH crossed that `cohort` does not show — the exit-policy
            # evidence (G3). Computed off the ROUNDED numbers this row publishes so the
            # flag and the printed MAE/MFE can never disagree at the gate.
            "path_tails": pm.path_tails(cohort, mae_pct, mfe_pct),
            # The prior-episode comparison `re_admission` was decided on, on EVERY row
            # that had one — including the rows where no leg fired and the rows where the
            # prior could not be scored. Written out rather than left inside the label's
            # trigger because a comparison that produced no label is exactly the one a
            # reader cannot otherwise see, and `prior_matured` says whether the number it
            # was compared against is a resolved outcome or an outcome-conditioned mark.
            # None = the scan found no prior run inside the window (a decided negative).
            "prior_episode": prior,
            "entry_context": ctx,
            "labels": labels,
            "labels_null": sorted(nulls, key=lambda d: (d["label"], d["reason"])),
            # PRICE-BASIS STAMP. Which store this episode's NAME leg came from, and
            # whether that store is back-adjusted. `bench` (data/yahoo/SPY) is always
            # adjusted, so `price_basis == "adjusted"` is this row's certificate that
            # `excess_pct` differenced two legs on ONE basis. "unadjusted" means the name
            # had no adjusted counterpart and its own distributions are still booked as
            # underperformance — disclosed per row rather than dropped from the study.
            "price_source": px_source,
            "price_basis": {True: "adjusted", False: "unadjusted"}.get(
                _px_is_adjusted(px_source)),
        })

    rows.sort(key=lambda r: (r["entry_date"], r["ticker"]))
    # Aggregate on the FULL rows, then trim the neutral tail for serialization —
    # never the other way round, or the summary would be computed on a trimmed sample.
    summary = pm.aggregate(rows)
    summary["round_trips"] = _round_trip_counts(rows)
    for r in rows:
        # A verdict outside both tails is NOT on its own a licence to trim: an episode
        # whose path crossed a gate is the exit-policy evidence, and its entry context is
        # the half that says WHY. Compact only the genuinely uneventful.
        if r["cohort"] not in ("loser", "winner") and not r["path_tails"]:
            r["entry_context"] = _compact_context(r["entry_context"])
        # `en`/`zh` per label are pure duplication of summary.taxonomy, once per row.
        for lb in r["labels"]:
            lb.pop("en", None)
            lb.pop("zh", None)
    as_of = max(days)

    coverage = {
        "board_dates": len(days),
        "board_date_first": min(days),
        "board_date_last": as_of,
        "n_episodes": len(rows),
        "n_no_price_path": len(no_price),
        "tickers_no_price_path": sorted({s.split("@")[0] for s in no_price}),
        # TWO DIFFERENT FACTS, and the ladder is why they had to be separated. Before
        # the fallback rungs existed a ticker in `tickers_no_price_path` had no series
        # anywhere, so the two lists were the same list. Now a name can resolve to a
        # perfectly good series whose last bar predates this episode's fill (U, whose
        # store stops 2026-06-29) — a stale STORE, not a missing NAME, and the two want
        # different fixes. `tickers_no_price_series` is the coverage hole; the wider
        # list above stays what it always was, "episodes that could not be scored".
        "tickers_no_price_series": sorted(unresolved),
        "n_tickers_no_price_series": len(unresolved),
        # WHICH RUNG each scored episode's path came from. The counts are the ladder's
        # own receipt: a `baskets_ohlcv` count above zero is the extras-universe class
        # that used to be ungradeable (D21), and a run where every episode resolves
        # from `breadth_caches` says the fallback rungs did nothing that night — both
        # are facts worth being able to read off the artifact rather than infer.
        "price_path_sources": dict(sorted(price_sources.items())),
        "basket_revisions": len(history),
        "basket_asof_first": history[0][0] if history else None,
        "basket_asof_last": history[-1][0] if history else None,
        "snapshot_dates": len(snaps),
        "membership_tickers": len(members),
    }
    caveats = [
        {"id": "membership_drift",
         "en": ("Theme STATE at entry is point-in-time (reconstructed from git history of "
                "data/baskets/latest.json); the ticker-to-theme MAPPING is today's "
                "membership.json, which carries no per-date history. A name that joined a "
                "basket after its entry date is credited with that basket's entry-date "
                "state. The sector-basket leg is unaffected."),
         "zh": ("入场时的主题状态为时点还原（取自 data/baskets/latest.json 的 git 历史）；"
                "而个股与主题的对应关系用的是当前的 membership.json，该文件没有按日期的历史。"
                "若某只股票是在入场日之后才加入某个篮子，会被算上该篮子在入场日的状态。"
                "行业篮子这一条不受影响。")},
        {"id": "mae_is_close_path",
         "en": ("MAE / MFE / gap detection run on daily CLOSES — the caches carry no "
                "intraday lows and no opens, so drawdown and overnight gaps are "
                "UNDER-stated, never over-stated."),
         "zh": ("最大回撤／最大浮盈／跳空识别均基于日收盘价 —— 缓存中没有盘中低点，也没有开盘价，"
                "因此回撤与隔夜跳空只会被低估，不会被高估。")},
        {"id": "overlapping_windows",
         "en": ("Episodes surfaced on the same board night share that night's tape and the "
                "ranker's state — they are one bet, not N. Every share below is reported "
                "over distinct entry DATES as well as over rows."),
         "zh": ("同一晚上榜的标的共享当晚行情与排序器状态 —— 属于一次下注，而非 N 次。"
                "下文每个占比都同时按不同入场日期与按行数两种口径给出。")},
        {"id": "in_flight_excluded_from_rates",
         "en": ("In-flight episodes are marked to the latest close and classified, but "
                "enter no rate and no expectancy — an unresolved position's mark is "
                "outcome-conditioned."),
         "zh": ("尚未到期的记录按最新收盘价标记并参与分类，但不计入任何胜率或期望值 —— "
                "未了结持仓的浮动盈亏会受结果选择影响。")},
        {"id": "measurement_tier_only",
         "en": ("Measurement and display tier only. Nothing here ranks, sizes or gates a "
                "pick. Any rule this suggests is a candidate for its own pre-registered "
                "study, never a live change."),
         "zh": ("仅为测量与展示层。此处内容不参与任何排序、仓位或准入判定。"
                "由此产生的任何规则都必须先走独立的预注册研究，不得直接上线。")},
    ]

    # ── cohort integrity — descriptive source-stamp receipt (strictly additive) ──
    # Re-reads the two ORIGINAL membership sources (the rows above already consumed
    # their entry-state columns through different, deduped indexes) and stamps every
    # episode with the partition its ORIGINAL rank_by record resolves to. Read-only:
    # `summary` above and every field on `rows` are untouched by it. The cut is THIS
    # run's own board as_of — the real existing generation date, never a clock and
    # never the membership sources' latest vintage.
    cohort_integrity = _cohort_integrity_block(root, rows, as_of=as_of)

    return {
        "schema": SCHEMA,
        "as_of": as_of,
        "generated_from": {
            "retro_grades": str(RETRO_REL),
            "snapshots": str(SNAPSHOTS_REL),
            "closes": [f"data/{g}/_closes_cache.parquet" for g in CLOSE_CACHE_GROUPS],
            "closes_fallback": [f"{BASKET_OHLCV_REL}/<TICKER>.parquet",
                                str(BASKET_EXTRAS_REL)],
            "closes_ladder": (
                "the four caches first (first cache carrying the ticker wins), then the "
                "fallback rungs in order — consulted ONLY when no cache carries the "
                "column, so a cache-resolved name grades off the same series it always "
                "did. Per-episode rung counts in coverage.price_path_sources."),
            "benchmark": str(BENCH_REL),
            "baskets_git": str(BASKETS_REL),
            "membership": str(MEMBERSHIP_REL),
        },
        "method": {
            "scorer": "engine.track_scoring (unchanged)",
            "fill": "next session close after the board date",
            "horizon": horizon,
            "exit_rule": "forced verdict at horizon — no stop, no oscillator target",
            "benchmark": "SPY",
            "lane": LANE,
            "llm_used": False,
            # ERA STAMP (see PRICE_BASIS_ERA). An artifact WITHOUT this key was produced
            # by the cache-first ladder: its `excess_pct` differenced an unadjusted name
            # leg against an adjusted SPY, so its rows are not comparable one-for-one
            # with this era's. 17 of 524 scored episodes moved at the boundary, all in
            # the same direction (mean +0.588pp, worst +2.16pp on excess_pct), with zero
            # cohort reclassifications. The old artifact is NOT restated — this study
            # regenerates wholesale, so the stamp is the boundary.
            "price_basis": PRICE_BASIS_ERA,
            "price_basis_era_boundary": PRICE_BASIS_ERA_BOUNDARY,
            "price_ladder": (
                "engine.price_ladder — adjusted-first: baskets_ohlcv → yahoo → "
                "data_stocks → baskets_extras → breadth caches (UNADJUSTED, last resort, "
                "stamped per episode as price_basis=unadjusted)"
            ),
            "detail_policy": (
                "Loser and winner episodes carry their full entry context, as does any "
                "episode whose path crossed a gate its verdict does not show "
                "(`path_tails` non-empty). The remaining neutral and unscored episodes "
                "carry a compact context holding every field a label keys on, so all "
                "labels stay re-derivable; the remaining board payload is dropped. "
                "Per-label EN/ZH copy lives once in summary.taxonomy."
            ),
        },
        "coverage": coverage,
        "caveats": caveats,
        "summary": summary,
        "cohort_integrity": cohort_integrity,
        "episodes": rows,
    }


# --------------------------------------------------------------------------- #
# report rendering
# --------------------------------------------------------------------------- #
def _plain(v: Any) -> str:
    return "—" if v is None else str(v)


def _pct(v: Any) -> str:
    """A percentage cell. A missing number prints an em dash and NOT '—%' — a unit
    glued to an absence reads as a measured zero."""
    return "—" if v is None else f"{v}%"


def render_report(doc: dict) -> str:
    """Render the artifact as a reader-facing markdown report (descriptive only)."""
    s = doc["summary"]
    cov = doc["coverage"]
    out: list[str] = []
    A = out.append

    A(f"# Prophet postmortem — US Buy Board · as of {doc['as_of']}")
    A("")
    A(f"Generated by `python -m scripts.prophet_postmortem` from `{RETRO_REL}` + "
      f"`{SNAPSHOTS_REL}`. Scorer: `engine.track_scoring`, unchanged — next-bar-close "
      f"fill, forced verdict at H={doc['method']['horizon']}, no stop and no target "
      "(this study measures the signal, not an exit policy). **No LLM is used anywhere "
      "in the classification path.** Measurement tier only: nothing here ranks, sizes "
      "or gates a pick.")
    A("")
    A("## Coverage")
    A("")
    A(f"- {cov['n_episodes']} buy-lane episodes across {cov['board_dates']} board dates "
      f"({cov['board_date_first']} → {cov['board_date_last']})")
    A(f"- {s['n_matured']} matured · {s['n_in_flight']} in flight · "
      f"{s['n_unscored']} unscored")
    A(f"- {s['cohorts']['n_losers']} losers · {s['cohorts']['n_winners']} winners · "
      f"{s['cohorts']['n_neutral']} neutral "
      f"(loser gate {s['cohorts']['loser_gate']['abs_pct']}% absolute or "
      f"{s['cohorts']['loser_gate']['excess_pct']}% excess; winner gate "
      f"+{s['cohorts']['winner_gate']['abs_pct']}%)")
    A(f"- {cov['n_no_price_path']} episodes with no close path "
      f"({', '.join(cov['tickers_no_price_path']) or 'none'})")
    A(f"- theme state reconstructed from {cov['basket_revisions']} committed revisions of "
      f"`{BASKETS_REL}` ({cov['basket_asof_first']} → {cov['basket_asof_last']})")
    A("")

    # ── cohort integrity — BEFORE the pooled rates, and additive by contract ──
    # An artifact produced before this block existed carries no `cohort_integrity` key
    # and renders exactly as it always did; a `render_report` over an old frozen doc
    # must never grow this section.
    integrity = doc.get("cohort_integrity")
    if integrity:
        parts_ = integrity.get("partitions") or {}
        A("## Cohort integrity — original source eras (descriptive receipt)")
        A("")
        A("The pooled rates in every section below are the **legacy summary, retained "
          "unchanged for compatibility**. They are **not** a cross-era comparison of "
          "any kind: episodes whose original board definition differs, disagrees or "
          "was never recorded are different board products and are never pooled into "
          "a cross-era rate here. This section is descriptive only — no grade, no "
          "verdict, no promotion read, no winner/loser selection.")
        A("")
        A("| Partition | Episodes | Matured | In flight | Unscored | Entry dates |")
        A("|---|---|---|---|---|---|")
        for name in pm.INTEGRITY_PARTITIONS:
            c = parts_.get(name) or {}
            mat = c.get("maturity") or {}
            A(f"| {name} | {c.get('n_episodes', 0)} | {mat.get('matured', 0)} "
              f"| {mat.get('in_flight', 0)} | {mat.get('unscored', 0)} "
              f"| {c.get('n_entry_dates', 0)} |")
        A("")
        un = (parts_.get(pm.INTEGRITY_UNASSIGNED) or {}).get("n_episodes", 0)
        mx = (parts_.get(pm.INTEGRITY_MIXED) or {}).get("n_episodes", 0)
        cf = (parts_.get(pm.INTEGRITY_CONFLICT) or {}).get("n_episodes", 0)
        pt = (parts_.get(pm.INTEGRITY_PARTIAL) or {}).get("n_episodes", 0)
        A(f"- **{un} unassigned** — no recorded stamp anywhere in the episode's "
          "membership window: missing attribution, never a manufactured legacy era.")
        A(f"- **{pt} partial** — agreeing stamps plus a missing membership stamp "
          "or missing original entry-day attribution (the gap is disclosed, not absorbed).")
        A(f"- **{mx} mixed** — different recorded stamps on different membership days: "
          "an existing episode crossing an era boundary, with its score untouched.")
        A(f"- **{cf} conflict** — differing stamps on the SAME membership date, within "
          "one source (e.g. across horizons) or between the two sources.")
        cut = integrity.get("as_of_cut") or {}
        if cut:
            A(f"- Frozen membership cut: attribution is read only up to the artifact's "
              f"own as_of **{cut.get('as_of')}**; "
              f"{cut.get('n_membership_records_after_cut', 0)} later membership record(s) "
              f"on {len(cut.get('dates_after_cut') or [])} later source date(s) are "
              "excluded from every assignment and disclosed — a later source vintage "
              "never assigns, conflicts or re-eras an episode.")
        gap_rows = [a for a in (integrity.get("episodes") or []) if a.get("observed_gap")]
        if gap_rows:
            A(f"- **{len(gap_rows)} episode(s) with an observed membership gap** — a "
              "recorded in-window board date absent from ALL original sources for that "
              "ticker. Records after the gap belong to a later admission: they are "
              "excluded from attribution and such an episode is never single-assigned "
              "(`observed_gap` on each row names the date and the excluded record count).")
        if integrity.get("membership_conflict_free") is False:
            A(f"- The original sources' membership observations conflict on at least "
              f"one record; per-era descriptive summaries are therefore withheld "
              f"(`{integrity.get('per_era_unavailable_reason')}`).")
        A("")
        per_era = integrity.get("per_era") or {}
        if per_era:
            A("Per-era descriptions — `single` explicitly assigned only. Each "
              "era's full descriptive summary lives in "
              "`cohort_integrity.per_era[<stamp>].aggregate`, computed with the "
              "existing aggregate on that era's episodes ALONE: two eras never share "
              "a rate denominator, nothing pooled is published, and every block is "
              "stamped `descriptive_only` with an explicit no-promotion authority.")
            A("")
            A("| Era stamp (exactly as recorded) | Episodes | Matured | In flight | "
              "Unscored | Entry dates |")
            A("|---|---|---|---|---|---|")
            for era in sorted(per_era):
                wrap = per_era[era]
                agg = wrap.get("aggregate") or {}
                A(f"| `{era}` | {agg.get('n_episodes', 0)} | {agg.get('n_matured', 0)} "
                  f"| {agg.get('n_in_flight', 0)} | {agg.get('n_unscored', 0)} "
                  f"| {agg.get('n_board_dates', 0)} |")
            A("")
        srcs = integrity.get("sources") or {}
        reach = " · ".join(
            f"`{name}` {v.get('n_dates', 0)} dates ({v.get('first_date')} → "
            f"{v.get('last_date')})"
            for name, v in sorted((srcs.get("sources") or {}).items()))
        A(f"Source reach: {reach or 'none'}.")
        A("")
        A(f"- {srcs.get('n_overlap_dates', 0)} board date(s) carried by both sources; "
          f"{len(srcs.get('dates_in_one_source_only') or [])} date(s) reachable by a "
          "single source only — disjoint reach is that source's documented coverage, "
          "NOT a disagreement.")
        A(f"- {srcs.get('n_overlap_dates_with_membership_difference', 0)} overlap "
          "date(s) where the two sources' buy memberships differ; the per-date "
          "retro-only / snapshot-only ticker sets and any stamp disagreements are "
          "listed in `cohort_integrity.sources.membership_on_overlap_dates`.")
        for warning in (integrity.get("warnings") or []):
            A(f"- **WARNING** — {warning}")
        if integrity.get("per_era_unavailable_reason"):
            A(f"- Per-era descriptive summaries unavailable "
              f"(`{integrity['per_era_unavailable_reason']}`): an original membership "
              "source read is incomplete, or the sources' membership observations "
              "conflict — observed stamps cannot stand in for missing or conflicting "
              "ones.")
        A("")

    A("## Failure taxonomy — both tails")
    A("")
    A("Shares are over the episodes on which each label could actually be DECIDED, not "
      "over the whole sample. Rows whose entry state was never recorded are excluded "
      "from that label's denominator and counted in `nulls` — putting them in the "
      "unflagged bucket would silently deflate every rate below.")
    A("")
    A("| Label | Visible at entry | Losers | of decidable losers | Winners | "
      "of decidable winners | loss contribution | loser coverage | nulls |")
    A("|---|---|---|---|---|---|---|---|---|")
    for f in s["label_frequency"]:
        A(f"| `{f['label']}` — {f['en']} | {'yes' if f['visible_at_entry'] else 'no'} "
          f"| {f['n_losers']} / {f['n_losers_evaluated']} "
          f"| {_pct(f['loser_share_pct'])} "
          f"| {f['n_winners']} / {f['n_winners_evaluated']} "
          f"| {_pct(f['winner_share_pct'])} "
          f"| {_pct(f['loss_contribution_pct'])} "
          f"| {f['n_losers_evaluated']} / {f['n_losers_total']} "
          f"({_pct(f['loser_coverage_pct'])}, {_pct(f['decidable_loss_share_pct'])} "
          f"of the loss) | {f['n_null_disclosed']} |")
    A("")
    A(f"`loss contribution` uses ONE denominator on every row — the whole matured-loser "
      f"book, {s['cohorts']['total_loser_loss_pct']:.2f}pp across "
      f"{s['cohorts']['n_losers']} episodes — so the column is comparable down the table "
      "and across runs. Labels are multi-label, so it does not sum to 100%.")
    A("")
    A("`loser coverage` is the honest companion to it: how many of those losers the label "
      "could even be DECIDED on, and what share of the loss book those rows carry. A "
      "label evaluable on a third of the book contributing 18.8% of it is a different "
      "sentence from one with full reach contributing 18.8%. Read the two columns "
      "together; never read contribution alone.")
    A("")
    A("`nulls` counts matured episodes where the label could not be evaluated (no entry "
      "state recorded, no price path, no stop recorded, no benchmark leg, no priceable "
      "prior episode) — those episodes stay in the artifact with the reason named on the "
      "row, and are excluded from that label's denominators above.")
    A("")

    beta = s["diagnostics"]["market_beta_excess_share"]
    if beta["n"]:
        A(f"On `market_beta`: across {beta['n']} matured losers the benchmark-excess loss "
          f"was {beta['min']:.2f}–{beta['max']:.2f} of the absolute loss "
          f"(median {beta['median']:.2f}), never below the {beta['threshold']} threshold. "
          "Over this window the losses were the picks, not the tape.")
        A("")
    idio = s["diagnostics"]["idiosyncratic_split"]
    A(f"On `idiosyncratic`: {idio['n_total']} matured episodes carry it, of which "
      f"{idio['n_fully_checked']} had every other leg checked and "
      f"{idio['n_with_unchecked_legs']} still have an unchecked leg. The second group is "
      "\"not fully looked at\", not \"no pattern found\" — each row's `labels_null` names "
      "the missing leg.")
    A("")

    A("## What a veto would have cost — both sides")
    A("")
    A("What refusing the flagged picks would have avoided, **and what it would have "
      "thrown away**. The winners-forfeited column is the point of the table. Each row is "
      "costed over the episodes where its own trigger was decidable, and `universe` says "
      "how many that is.")
    A("")
    A("**A row is a TRIGGER, not a label.** The `evidence` column says whether that "
      "trigger existed on the night of the pick (`buildable`) or needs a number that only "
      "arrived later (`hindsight upper bound`). The two are not comparable and are never "
      "summed: only a buildable row describes a rule anyone could pre-register.")
    A("")
    A("| Would-be veto | Evidence | Flagged | universe | of universe | Losers avoided "
      "| Loss avoided | **Winners forfeited** | **Gains forfeited** | Net | Dates flagged "
      "| Mean flagged | Mean unflagged |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for v in s["veto_cost"]:
        A(f"| `{v['key']}` | {'buildable' if v['visible_at_entry'] else 'hindsight upper bound'} "
          f"| {v['n_flagged']} | {v['n_universe']} "
          f"| {_pct(v['flagged_share_of_universe_pct'])} "
          f"| {v['n_losers_avoided']} | {v['loss_avoided_pct']:.2f}pp "
          f"| **{v['n_winners_forfeited']}** | **{v['winners_forfeited_pct']:.2f}pp** "
          f"| {v['net_pct_if_vetoed']:+.2f}pp | {v['n_dates_flagged']} "
          f"| {_pct(v['mean_outcome_of_flagged_pct'])} "
          f"| {_pct(v['mean_outcome_of_unflagged_pct'])} |")
    A("")
    for name in sorted({v["label"] for v in s["veto_cost"] if v.get("leg")}):
        legs = [v for v in s["veto_cost"] if v["label"] == name]
        A(f"**`{name}` is {len(legs)} claims, not one**, so it is costed on "
          f"{len(legs)} lines:")
        A("")
        for v in legs:
            if v["visible_at_entry"]:
                zero = (" — it fires **zero** times on this window, and the zero is "
                        "printed rather than dropped: an empty buildable row is the "
                        "finding, and hiding it would leave only the hindsight line on "
                        "the page." if not v["n_flagged"] else ".")
                A(f"- `{v['leg']}` — **buildable**. {v['en']}. The board could read this "
                  f"at entry. Flagged {v['n_flagged']} of the {v['n_universe']} matured "
                  f"episodes it could be decided on{zero}")
            else:
                A(f"- `{v['leg']}` — **hindsight upper bound**. {v['en']}. This needs the "
                  f"earlier episode's RESOLVED outcome, which did not exist on the night "
                  f"the board bought the name back, so the "
                  f"{v['loss_avoided_pct']:.2f}pp on this line is a CEILING on what the "
                  f"pattern could be worth if a buildable trigger is ever found — never "
                  f"the value of a rule. Flagged {v['n_flagged']} of {v['n_universe']} "
                  f"across {v['n_dates_flagged']} entry dates.")
        A("")
    A("`Net` is loss avoided minus gains forfeited, in summed percentage points across "
      "matured episodes — a raw arithmetic counterfactual on equal weights, not a "
      "backtest and not an expectancy. It ignores position sizing, the overlap between "
      "episodes on one board night, and the fact that the same capital cannot take every "
      "pick. Read it as a first-order sanity check on whether a veto is even worth "
      "pre-registering.")
    A("")

    A("## Systemic or anomalous?")
    A("")
    A("A label on nine episodes across one night is one bad night. The same label across "
      "seven nights is a process fault. Distinct entry dates, not row counts, decide.")
    A("")
    A("| Label | Loser dates | of all loser dates | Largest single date | Read |")
    A("|---|---|---|---|---|")
    for v in s["systemic_vs_anomalous"]:
        A(f"| `{v['label']}` | {v['n_dates']} / {v['n_loser_dates_total']} "
          f"| {_pct(v['date_share_pct'])} "
          f"| {_plain(v['max_single_date'])}"
          f"{'' if v['max_single_date'] is None else f" ({_pct(v['max_single_date_share_pct'])} of the label's losers)"}"
          f" | {v['read']} |")
    A("")

    A("## Entry-state splits (matured episodes where the state was recorded)")
    A("")
    A("| Split | n | dates | losers | loss rate | winners | win rate | mean outcome |")
    A("|---|---|---|---|---|---|---|---|")
    for key in sorted(s["cohort_splits"]):
        c = s["cohort_splits"][key]
        A(f"| {key.replace('_', ' ')} | {c['n']} | {c['n_dates']} | {c['n_losers']} "
          f"| {_pct(c['loss_rate_pct'])} | {c['n_winners']} "
          f"| {_pct(c['win_rate_pct'])} | {_pct(c['mean_outcome_pct'])} |")
    A("")

    if s["repeat_offenders"]:
        A("## Repeat offenders")
        A("")
        A("| Ticker | Loser episodes | Entry dates | Total loss | Labels |")
        A("|---|---|---|---|---|")
        for r in s["repeat_offenders"]:
            A(f"| {r['ticker']} | {r['n_loser_episodes']} | {', '.join(r['entry_dates'])} "
              f"| {r['total_loss_pct']:.2f}pp | {', '.join(r['labels'])} |")
        A("")

    # ── the loser book, split by maturity, with counts that RECONCILE ─────────
    # One table pooling matured and marked-to-market rows invites exactly the read the
    # maturity gate exists to prevent, because today's worst open positions sort to the
    # top of it. Two labelled blocks, and a sentence whose numbers add up.
    losers = [r for r in doc["episodes"] if r["cohort"] == "loser"]
    by_maturity = {
        "matured": [r for r in losers if r["maturity"] == "matured"],
        "in_flight": [r for r in losers if r["maturity"] == "in_flight"],
        "unscored": [r for r in losers if r["maturity"] not in ("matured", "in_flight")],
    }
    parts = " + ".join(
        f"**{len(v)} {k.replace('_', ' ')}**" for k, v in by_maturity.items() if v)

    A("## Every loser, with its trigger values")
    A("")
    A(f"{len(losers)} episodes sit in the loser cohort: {parts} = {len(losers)}. The "
      "blocks are listed separately and never pooled. Every rate, share and "
      f"counterfactual above is computed on the matured block alone "
      f"({s['cohorts']['n_losers']} episodes) — a mark on an unresolved position is "
      "outcome-conditioned, and today's worst open names would sort straight to the top "
      "of a pooled table.")
    A("")

    def _loser_table(rows: list[dict]) -> None:
        A("| Ticker | Entry | Outcome | Excess | MAE | MFE | Held | Labels |")
        A("|---|---|---|---|---|---|---|---|")
        for r in sorted(rows, key=lambda r: (r["outcome_pct"]
                                             if r["outcome_pct"] is not None else 0.0)):
            A(f"| {r['ticker']} | {r['entry_date']} "
              f"| {_pct(r['outcome_pct'])} | {_pct(r['excess_pct'])} "
              f"| {_pct(r['mae_pct'])} | {_pct(r['mfe_pct'])} | {_plain(r['held'])} "
              f"| {', '.join(lb['label'] for lb in r['labels']) or '—'} |")
        A("")

    A(f"### Matured losers ({len(by_maturity['matured'])}) — these carry every rate above")
    A("")
    _loser_table(by_maturity["matured"])
    A(f"### In-flight losers ({len(by_maturity['in_flight'])}) — marked, in NO rate")
    A("")
    A("Fewer than H forward bars, so these are marked to the latest close. They are here "
      "because dropping them would delete the most recent evidence — not because they "
      "count. `Outcome` in this block is a MARK, not a result.")
    A("")
    _loser_table(by_maturity["in_flight"])
    if by_maturity["unscored"]:
        A(f"### Unscored losers ({len(by_maturity['unscored'])}) — no fill printed yet")
        A("")
        _loser_table(by_maturity["unscored"])

    infl_block = s["in_flight"]
    A("## In-flight rows (classified, counted in no rate)")
    A("")
    A(f"{infl_block['n']} episodes have fewer than H={doc['method']['horizon']} "
      "forward bars. They are marked to the latest close so the most recent evidence "
      "stays visible, and they enter no rate or expectancy — an unresolved position's "
      "mark is outcome-conditioned in exactly the way the maturity gate exists to "
      "prevent.")
    A("")
    A(f"By the mark: {infl_block['n_losers_marked']} at loser levels · "
      f"{infl_block['n_winners_marked']} at winner levels · "
      f"{infl_block['n_neutral_marked']} neutral · "
      f"{infl_block['n_unscored_marked']} unscored = {infl_block['n']}. The two tails are "
      "tabled below (the loser half repeats the in-flight block above); the neutral "
      "middle is in `summary.json`, not here.")
    A("")
    A("| Ticker | Entry | Mark | MAE | MFE | Held | Labels |")
    A("|---|---|---|---|---|---|---|")
    infl = [r for r in doc["episodes"]
            if r["maturity"] == "in_flight" and r["cohort"] in ("loser", "winner")]
    infl.sort(key=lambda r: (r["outcome_pct"] if r["outcome_pct"] is not None else 0.0))
    for r in infl:
        A(f"| {r['ticker']} | {r['entry_date']} | {_pct(r['outcome_pct'])} "
          f"| {_pct(r['mae_pct'])} | {_pct(r['mfe_pct'])} | {_plain(r['held'])} "
          f"| {', '.join(lb['label'] for lb in r['labels']) or '—'} |")
    A("")

    # ── round trips — the episodes a verdict-keyed table cannot show ──────────
    # Deliberately AFTER the loser book: these rows are not a third maturity block and
    # must never be read into one. They are the same episodes, re-sorted by what the
    # PATH did, and they are the exit policy's evidence rather than a rate.
    rt = s["round_trips"]
    roundtrips = [r for r in doc["episodes"]
                  if r["path_tails"] and r["cohort"] not in ("loser", "winner")]
    A("## Round trips — crossed a gate, finished outside both tails")
    A("")
    A(f"{rt['n']} episodes crossed a gate their verdict does not show: "
      f"{rt['n_crossed_loser_gate']} through the {rt['loser_gate_pct']}% loser gate + "
      f"{rt['n_crossed_winner_gate']} through the +{rt['winner_gate_pct']}% winner gate "
      f"− {rt['n_crossed_both']} that crossed both = {rt['n']}. The "
      f"{rt['n_verdict_outside_both_tails']} whose VERDICT landed outside both tails are "
      "tabled here, because they appear in no other table on this page — a name that "
      "fell 19% and closed +1.7% is `neutral`, and a table keyed on the verdict says "
      "nothing about it.")
    A("")
    A("This block is evidence for the exit-policy question, NOT a rate: it enters no "
      "expectancy and no counterfactual above. A stop would have booked every `loser` "
      "crossing below and forfeited whatever came after it; a target would have banked "
      "every `winner` crossing and given up the rest. Which of those trades is worth "
      "making is measured in G3, not asserted here. These rows keep their FULL entry "
      "context in `summary.json` for that reason.")
    A("")
    A("| Ticker | Entry | Verdict | Crossed | MAE | MFE | Held | Labels |")
    A("|---|---|---|---|---|---|---|---|")
    for r in sorted(roundtrips, key=lambda r: (r["mae_pct"]
                                               if r["mae_pct"] is not None else 0.0)):
        A(f"| {r['ticker']} | {r['entry_date']} | {_pct(r['outcome_pct'])} "
          f"| {', '.join(r['path_tails'])} "
          f"| {_pct(r['mae_pct'])} | {_pct(r['mfe_pct'])} | {_plain(r['held'])} "
          f"| {', '.join(lb['label'] for lb in r['labels']) or '—'} |")
    A("")

    A("## Caveats")
    A("")
    for c in doc["caveats"]:
        A(f"- **{c['id']}** — {c['en']}")
    A("")
    A("---")
    A("")
    A("Review protocol: `docs/PROPHET_POSTMORTEM_PROTOCOL.md`. "
      "Program: `research/PROPHET_LEARNING_LOOP_MASTERPLAN_BY_FABLE.md`.")
    A("")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="US Buy-Board postmortem forensics")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--horizon", type=int, default=ts.DEFAULT_HORIZON)
    ap.add_argument("--out", default=None, help=f"default {OUT_REL}")
    ap.add_argument("--report-dir", default=None, help=f"default {REPORT_DIR_REL}")
    ap.add_argument("--dry-run", action="store_true", help="print the headline, write nothing")
    ap.add_argument("--cohort-integrity-only", action="store_true",
                    help="print only the descriptive cohort-integrity receipt for an "
                         "EXISTING artifact; reads the preserved artifact plus the "
                         "membership sources, never scores, never writes")
    ap.add_argument("--artifact", default=None,
                    help="with --cohort-integrity-only: path to the preserved "
                         "summary.json to inspect")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    # Flag pairing, decided BEFORE any generation path. `--artifact` belongs to the
    # read-only bypass alone, and incompatible explicit generation flags are refused
    # rather than silently ignored.
    if args.artifact and not args.cohort_integrity_only:
        raise SystemExit(
            "--artifact is only meaningful with --cohort-integrity-only (read-only "
            "inspection); refusing to attach it to the generation path")
    if args.cohort_integrity_only:
        incompatible = [flag for flag, given in (
            ("--out", args.out),
            ("--report-dir", args.report_dir),
            ("--dry-run", args.dry_run),
            ("--horizon", args.horizon != ts.DEFAULT_HORIZON),
        ) if given]
        if incompatible:
            raise SystemExit(
                "--cohort-integrity-only never scores and never writes; incompatible "
                "explicit flag(s): " + ", ".join(incompatible))
        return _cohort_integrity_only(root, args.artifact)
    doc = build_rows(root, horizon=args.horizon)
    s = doc["summary"]

    print(f"prophet-postmortem as_of={doc['as_of']} episodes={s['n_episodes']} "
          f"matured={s['n_matured']} in_flight={s['n_in_flight']} "
          f"losers={s['cohorts']['n_losers']} winners={s['cohorts']['n_winners']}")
    for f in s["label_frequency"]:
        print(f"  {f['label']:<16} losers={f['n_losers']:<4} "
              f"({f['loser_share_pct']}%)  winners={f['n_winners']:<4} "
              f"({f['winner_share_pct']}%)  nulls={f['n_null_disclosed']}")
    for v in s["veto_cost"]:
        # `key`, not `label`: two rows share the label `re_admission` and differ only in
        # the leg, and the buildable one is the whole point of printing both.
        print(f"  veto[{v['key']}] {v['variant']} "
              f"flagged={v['n_flagged']}/{v['n_universe']} "
              f"losers_avoided={v['n_losers_avoided']} ({v['loss_avoided_pct']:.2f}pp) "
              f"winners_forfeited={v['n_winners_forfeited']} "
              f"({v['winners_forfeited_pct']:.2f}pp) net={v['net_pct_if_vetoed']:+.2f}pp")

    # GitHub annotations: bare print at line start, flush=True. A logger here would
    # prefix the line and GitHub would silently drop the annotation (house law).
    if doc["coverage"]["n_no_price_path"]:
        _cov = doc["coverage"]
        _gap = _cov.get("tickers_no_price_series") or []
        print(f"::warning title=prophet-postmortem::"
              f"{_cov['n_no_price_path']} episodes unscored — "
              f"their path labels are emitted null, not dropped "
              f"({', '.join(_cov['tickers_no_price_path'][:12])}); of those "
              f"{len(_gap)} ticker(s) resolve to no price series at all after the "
              f"fallback rungs ({', '.join(_gap[:12]) or 'none'}) — the rest have a "
              f"series that does not reach the episode's fill bar", flush=True)
    if not doc["coverage"]["basket_revisions"]:
        print("::warning title=prophet-postmortem::no committed revisions of "
              "data/baskets/latest.json found — entry-time theme context is empty",
              flush=True)

    if args.dry_run:
        return 0

    out_path = Path(args.out) if args.out else root / OUT_REL
    _write_json(out_path, doc)
    report_dir = Path(args.report_dir) if args.report_dir else root / REPORT_DIR_REL
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"prophet_postmortem_{doc['as_of']}.md"
    report_path.write_text(render_report(doc), encoding="utf-8")
    print(f"wrote {out_path} and {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
