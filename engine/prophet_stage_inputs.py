"""engine/prophet_stage_inputs.py — the GOVERNED point-in-time inputs for the
Prophet × Stage hold-leash and its forward shadow.

WHY THIS MODULE EXISTS (R0-C, earnings/company-event suite Wave 0).
``engine/prophet_bridge.py`` (production origination) and
``engine/prophet_stage_shadow.py`` (the nightly forward shadow) both used to
``import engine.prophet_stage_fusion`` — a RESEARCH BACKTEST HARNESS — to reach six
small point-in-time primitives. That made a 2022-26 backtest module a live
dependency of nightly plan origination: a split-brain in which a research edit could
move a shipped plan and a production edit could move a frozen research result.

This module owns those primitives. ``prophet_stage_fusion`` now imports them FROM
here and re-exports them, so every published PSF/PSQ result stays reproducible
against identical code while production no longer depends on the harness.

WHAT LIVES HERE. Only inputs — reads and point-in-time lookups. No arm membership,
no win-rate statistics, no bootstrap, no verdicts. Nothing here ranks, sizes, gates,
or scores anything; the leash that consumes these values is owned by
``prophet_bridge`` and its authority is documented there.

WHERE THE EARNINGS-CALL SOURCE COMES FROM (read this before trusting an EC-negative).
The governed evidence is EquityDesk's native earnings-call table: one row per
``(document_ticker, fiscal_quarter, fiscal_year, call_date)`` carrying
``earnings_call_sent`` on the desk's own ~−10..30 scale. It reaches a host through an
ORDERED LADDER of native stores, strongest first (``EC_SOURCE_TIERS``):

``r2_history``   ``data/earnings_calls/history.parquet`` — the canonical R2-transported
                 migration of the full EquityDesk numeric archive. It is published by
                 ``scripts/publish_earnings_r2.py`` as an immutable generation under
                 ``earnings_calls/generations/<generation_id>/`` and restored by
                 ``scripts/fetch_earnings_scores.py``, which validates md5/bytes/rows/
                 tickers against ``earnings_calls/manifest.json`` before promoting it.
                 ``engine/earnings_qual.py`` has consumed this exact store, at this
                 exact tier name, since SGA W4; this module now reads the SAME file
                 rather than a second copy of it.
``legacy_full_history``
                 ``data/stage_analysis/backfill/earnings_calls.parquet`` — the original
                 one-time local import (``scripts/import_equitydesk_full.py``). It is
                 gitignored and has no publisher, so it exists only on the importing
                 workstation. It stays first-class as a cold-start fallback and its
                 rows are byte-identical in meaning to the tier above.

WHY THE LADDER EXISTS. Until this repair the join resolved ONLY the legacy path. That
path is gitignored, was never committed, and has no fetch/publish pair, so on every CI
and deploy host the file was simply absent: the EC join returned an empty table, every
lookup answered ``None``, and the promoted hold-tilt could not become eligible — the
production logs of 2026-09-17 say exactly that. The R2 store carrying the same native
table was already being fetched on the same runner for a different consumer. Nothing
new is created here: the ladder points this consumer at the plane that already exists.

WHAT IS NOT IN THE LADDER, AND WHY. ``engine/earnings_qual.py`` carries two further
cold-start tiers (``committed_overview_fallback``, ``committed_score_seed_fallback``).
Those are PROJECTIONS — ``_normalise_earnings_source`` reverse-calibrates a −1..1 score
into the desk scale with ``sent * 18 + 12`` — so they are a different construction, not
the same evidence at a different address. A promoted gate may not silently start
reading a synthesized value, so this module admits NATIVE stores only.
``tests/test_prophet_earnings_source_restore.py`` pins the ladder as exactly the native
prefix of the earnings_qual ladder, in the same order, so the two cannot drift apart.

THE CORRECTION CONTRACT, AND THE ONE RESIDUAL THIS RESTORE DOES NOT CLOSE.
EquityDesk revises calls: ``updated_at`` is the correction clock, and
``scripts/import_equitydesk_full.py`` resolves it upstream of BOTH tiers — one winner per
``(document_ticker, fiscal_quarter, fiscal_year, call_date)`` by ``max(updated_at)``, then
``created_at``, ``id``, source position, with every rejected id written to
``data/quality/earnings_import_reconciliation.json``. So each store holds one row per
corrected call, and the only time rule THIS layer applies is ``call_date < entry_date``.
That rule is unchanged, and it answers identically on either tier — pinned by
``test_point_in_time_and_correction_selection_are_identical_across_tiers``.

The residual, stated rather than papered over, and scoped to what it actually is: because
the selected row is the LATEST correction, a value read for an entry date can in principle
reflect a revision published after that date. Two of the three paths are NOT exposed.
Live origination runs at wall-clock now, so it can only ever see corrections that already
exist. The forward shadow tags each entry exactly once and never re-tags
(``prophet_stage_shadow.tag_entries``: "idempotent — the tag is PIT-fixed"), so a later
correction cannot reach a row already in its ledger. What remains is narrow and real: the
gap between an entry's signal date and the first nightly that tags it, and the
``clock_retag`` overlay, which deliberately recomputes an older entry's PIT tag against
today's table. The live R2 tier makes that window continuously current rather than frozen
at a snapshot date. Filtering on ``updated_at`` would close it, and would also be a
STRICTER point-in-time rule than the one the leash was promoted under, so it is
deliberately NOT done here: that is a prereg amendment, not a data-availability repair.

THE FAIL-OPEN IS UNCHANGED. When no tier answers, the table is empty, every lookup is
``None``, and the leash stays 1.0 — a missing source never raises and never tilts. A
tier that exists but FAILS its generation-manifest contract is rejected by name rather
than used, and the rejection is reported: ``resolve_ec_source`` /
``load_ec_table_with_source`` return ``state``/``tier``/``reason``/``rejected`` so a
starved negative, a malformed source and an honest negative stay three different
answers instead of one.

``EC_SENT_GATE = 24`` is calibrated to EquityDesk's native ~−10..30
``earnings_call_sent`` (12 is the documented neutral midpoint). It is NOT
comparable to a 0–100 gauge, and it is NOT comparable to this repo's own
-1..1 ``sentiment`` in ``data/earnings_calls/scores.parquet`` (a different
artifact with a sibling name). Re-pointing this join at another field would
silently re-scale a promoted signal's construction, which is a
promotion-gauntlet violation rather than a repair. Values outside the native
range are rejected with a warning (never silently re-scaled).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from engine import grading, weinstein_stage

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Frozen shared constants. These mirror research/PROPHET_STAGE_FUSION_PREREG.md  #
# §2-§4 and are re-exported by engine.prophet_stage_fusion, so the research      #
# harness and the production leash read ONE definition of each. Changing a value #
# here changes both — it needs a prereg amendment row, not a code review.        #
# --------------------------------------------------------------------------- #
STAGE2 = 2                                 # Weinstein Stage-2 (advancing)
FRESH_WEEKS_MAX = 10                       # §2 B-fresh: weeks_in_stage <= 10
EC_SENT_GATE = 24                          # §2 arm C: earnings_call_sent >= 24 (native ~−10..30)
EC_SENT_NATIVE_MIN = -10                   # EquityDesk native floor (inclusive)
EC_SENT_NATIVE_MAX = 30                    # EquityDesk native ceiling (inclusive)
BENCH_TICKER = "SPY"                       # §2 bench

# §3 two ruler parameterizations.
PARAM_CLEAN15_126 = dict(liftoff_mult=grading.LIFTOFF_15, liftoff_horizon=grading.LIFTOFF_HORIZON_126)
PARAM_CLEAN8_21 = dict(liftoff_mult=grading.LIFTOFF_8, liftoff_horizon=grading.LIFTOFF_HORIZON_21)

# §4 forward-metric horizons.
FWD_HORIZONS = (21, 63, 126)

# --------------------------------------------------------------------------- #
# EC source state — the honest-negative / starved-negative split.               #
# --------------------------------------------------------------------------- #
EC_SOURCE_AVAILABLE = "available"
EC_SOURCE_UNAVAILABLE = "unavailable"

EC_ABSENT_REASON = (
    "no earnings-call source on this host — neither the R2-transported EquityDesk "
    "history (data/earnings_calls/history.parquet, restored by "
    "scripts/fetch_earnings_scores.py) nor the local-only backfill "
    "(data/stage_analysis/backfill/earnings_calls.parquet) is present, so every "
    "earnings lookup answers null"
)

_EC_COLUMNS = ["ticker", "call_date", "earnings_call_sent"]

# The source columns every native EquityDesk store must carry. A store missing any of
# them is unreadable, not silently partial.
_EC_SOURCE_COLUMNS = ["document_ticker", "call_date", "earnings_call_sent"]

# --------------------------------------------------------------------------- #
# The native-store ladder (strongest first).                                    #
#                                                                               #
# Each entry is (tier, path-parts-relative-to-data_dir, validate_transport).     #
# ``validate_transport`` marks the tiers that arrive through the earnings R2     #
# generation plane and therefore carry a sibling ``manifest.json`` commit marker #
# that must hold before the payload may be used. The legacy tier is a local      #
# import with no manifest and is validated only by being readable.               #
#                                                                               #
# ORDER IS LOAD-BEARING and mirrors engine.earnings_qual's own ladder: two       #
# production consumers of "the EquityDesk earnings archive" must never disagree  #
# about which file that is. Pinned by tests/test_prophet_earnings_source_restore #
# ::test_prophet_tiers_are_the_native_prefix_of_the_earnings_qual_ladder.        #
# --------------------------------------------------------------------------- #
EC_TIER_R2_HISTORY = "r2_history"
EC_TIER_LEGACY = "legacy_full_history"
EC_TIER_EXPLICIT = "explicit"

EC_SOURCE_TIERS: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    (EC_TIER_R2_HISTORY, ("earnings_calls", "history.parquet"), True),
    (EC_TIER_LEGACY, ("stage_analysis", "backfill", "earnings_calls.parquet"), False),
)

# The manifest block name the transported history is published under. Must match
# scripts/publish_earnings_r2.py / scripts/fetch_earnings_scores.py.
EC_TRANSPORT_BLOCK = "history"


def _in_native_ec_range(value: float) -> bool:
    return EC_SENT_NATIVE_MIN <= value <= EC_SENT_NATIVE_MAX


def _reject_out_of_native_ec_sent(value: float) -> float | None:
    """Return ``value`` if it is on the native ~−10..30 desk scale; else warn and None.

    Fail-open: a foreign scale must not silently become a leash input. Matches the
    module's existing ``log.warning`` idiom — never a hard crash on a bad row.
    """
    if not _in_native_ec_range(value):
        log.warning(
            "psi: earnings_call_sent %s outside native ~%.0f..%.0f — treating as null",
            value, EC_SENT_NATIVE_MIN, EC_SENT_NATIVE_MAX,
        )
        return None
    return value


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _display_path(p: Path) -> str:
    """Repo-relative when possible, so the string is identical on every host and
    safe to publish inside a plan artifact."""
    try:
        return str(Path(p).resolve().relative_to(_repo_root()))
    except Exception:  # noqa: BLE001
        return str(p)


def _ec_data_dir() -> Path:
    from lib import config  # noqa: PLC0415
    return Path(config.data_dir())


def ec_source_path(ec_path: str | Path | None = None) -> Path:
    """The DECLARED canonical earnings-call table path.

    Unchanged by the ladder repair and deliberately so: this is the path the promoted
    construction names, the path a reader is pointed at when nothing is present, and the
    path the R0-C authority pin asserts against. It is NOT necessarily the path a given
    host reads — ask ``resolve_ec_source`` for that.
    """
    if ec_path is not None:
        return Path(ec_path)
    return _ec_data_dir() / "stage_analysis" / "backfill" / "earnings_calls.parquet"


def ec_source_candidates(
    ec_path: str | Path | None = None,
) -> list[tuple[str, Path, bool]]:
    """``[(tier, path, validate_transport)]`` — the native stores, strongest first.

    An explicit ``ec_path`` collapses the ladder to that one file (the research-harness
    and fixture shape): a caller who names a file means that file.
    """
    if ec_path is not None:
        return [(EC_TIER_EXPLICIT, Path(ec_path), False)]
    root = _ec_data_dir()
    return [(tier, root.joinpath(*parts), transported)
            for tier, parts, transported in EC_SOURCE_TIERS]


def _transport_manifest_beside(path: Path) -> dict | None:
    """The generation commit marker published next to a transported payload."""
    try:
        payload = json.loads((path.parent / "manifest.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def _transport_generation(path: Path) -> dict | None:
    """``{generation_id, published_at}`` for a transported store, when disclosed.

    Vintage disclosure only — it never enters the eligibility test. It is what lets a
    grader say WHICH generation produced a reading rather than only that one existed.
    """
    manifest = _transport_manifest_beside(path)
    if manifest is None:
        return None
    block = manifest.get(EC_TRANSPORT_BLOCK)
    out = {
        "generation_id": manifest.get("generation_id"),
        # publish_earnings_r2._synth_manifest stamps the publish time as "built";
        # the other two names are accepted so an older or hand-written marker still
        # discloses a vintage instead of silently reporting none.
        "published_at": (manifest.get("built") or manifest.get("generated_at")
                         or manifest.get("published_at")),
        "rows": (block or {}).get("rows") if isinstance(block, dict) else None,
    }
    return out if any(v is not None for v in out.values()) else None


def _validate_transport(frame: pd.DataFrame, path: Path) -> tuple[bool | None, str | None]:
    """Hold the transported payload to the SAME generation contract its fetcher uses.

    Delegates to ``engine.earnings_qual.validate_transport_frame`` — one definition of
    the earnings transport contract for the whole repo, never a second copy of it.
    ``None`` means "no manifest beside this store" (a hand-placed or fixture file), which
    is accepted exactly as engine.earnings_qual accepts it. ``False`` is an explicit
    contract failure and the candidate must be rejected rather than used.

    THE MANIFEST IS THE PAYLOAD'S SIBLING, FULL STOP. The delegate falls back to a
    repo-layout guess (``<root>/data/earnings_calls/manifest.json``) when no sibling
    exists, and ``lib.config.data_dir()`` is configurable — it is only conventionally
    named ``data``. Under a data root the guess cannot reconstruct, that fallback would
    judge this payload against a DIFFERENT generation's commit marker: a valid store
    rejected, or worse, one blessed by a manifest that does not describe it. So the
    sibling is resolved here and the fallback is never reachable.
    """
    if not (path.parent / "manifest.json").exists():
        return None, "manifest_absent"
    try:
        from engine import earnings_qual  # noqa: PLC0415
        return earnings_qual.validate_transport_frame(
            frame, path, EC_TRANSPORT_BLOCK, root=path.parent,
        )
    except Exception as e:  # noqa: BLE001
        # A validator that cannot run must not silently bless the payload.
        return False, f"transport validator unavailable: {e}"


def resolve_ec_source(ec_path: str | Path | None = None) -> dict:
    """Existence-only source record — no parquet read, safe to call anywhere.

    Returns ``{"state", "path", "tier", "reason", "generation"}`` where ``state`` is
    ``available`` or ``unavailable``, ``tier`` names WHICH native store answered, and
    ``reason`` is None when a source is present. This is the field that lets a reader
    tell an honest EC-negative from a starved one.

    Existence-only is deliberate — the forward shadow calls this per summary — so a
    present-but-contract-failing store still reports ``available`` here. The authoritative
    record, which rejects such a store by name, is the one returned by
    ``load_ec_table_with_source``.
    """
    try:
        candidates = ec_source_candidates(ec_path)
    except Exception as e:  # noqa: BLE001
        return {"state": EC_SOURCE_UNAVAILABLE, "path": None, "tier": None,
                "generation": None,
                "reason": f"earnings-call source path unresolvable: {e}"}
    for tier, path, transported in candidates:
        if not path.exists():
            continue
        return {
            "state": EC_SOURCE_AVAILABLE,
            "path": _display_path(path),
            "tier": tier,
            "generation": _transport_generation(path) if transported else None,
            "reason": None,
        }
    declared = candidates[0][1] if len(candidates) == 1 else ec_source_path()
    return {"state": EC_SOURCE_UNAVAILABLE, "path": _display_path(declared),
            "tier": None, "generation": None, "reason": EC_ABSENT_REASON}


def _read_ec_candidate(path: Path) -> pd.DataFrame:
    """Read one native store's three governed columns. Raises on an unusable store."""
    return pd.read_parquet(path, columns=list(_EC_SOURCE_COLUMNS))


def _normalise_ec_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Source columns -> the frozen (ticker, call_date, earnings_call_sent) contract.

    The native ~-10..30 range check is applied HERE, before any consumer sees a value, so
    a foreign scale can never reach the gate no matter which tier produced it.
    """
    out = pd.DataFrame({
        "ticker": df["document_ticker"].astype(str),
        "call_date": pd.to_datetime(df["call_date"], errors="coerce"),
        "earnings_call_sent": pd.to_numeric(df["earnings_call_sent"], errors="coerce"),
    }).dropna(subset=["call_date"])
    sent = out["earnings_call_sent"]
    oob = sent.notna() & ((sent < EC_SENT_NATIVE_MIN) | (sent > EC_SENT_NATIVE_MAX))
    if bool(oob.any()):
        n = int(oob.sum())
        log.warning(
            "psi: dropping %s earnings_call_sent values outside native ~%.0f..%.0f",
            n, EC_SENT_NATIVE_MIN, EC_SENT_NATIVE_MAX,
        )
        out.loc[oob, "earnings_call_sent"] = pd.NA
    return out.sort_values("call_date").reset_index(drop=True)


def load_ec_table_with_source(
    ec_path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    """``(table, source_record)`` in ONE read, over the native-store ladder.

    The table is the same fail-open frame ``load_ec_table`` has always returned (empty on
    absence or unreadability, never a raise). The record is the AUTHORITATIVE one: it adds
    ``rows`` and ``tier``, and it downgrades ``state`` to ``unavailable`` when every
    present store was unreadable or failed its generation contract. Each such failure is
    listed by tier in ``rejected`` — a rejected source is disclosed, never silently equal
    to an absent one.
    """
    try:
        candidates = ec_source_candidates(ec_path)
    except Exception as e:  # noqa: BLE001
        return pd.DataFrame(columns=_EC_COLUMNS), {
            "state": EC_SOURCE_UNAVAILABLE, "path": None, "tier": None,
            "generation": None, "rows": 0, "rejected": [],
            "reason": f"earnings-call source path unresolvable: {e}",
        }

    rejected: list[dict] = []
    for tier, path, transported in candidates:
        if not path.exists():
            continue
        rel = _display_path(path)
        try:
            raw = _read_ec_candidate(path)
        except Exception as e:  # noqa: BLE001
            log.warning("psi: earnings_calls unreadable (%s) — EC join degrades to n=0", e)
            rejected.append({"tier": tier, "path": rel,
                             "reason": f"earnings-call source unreadable: {e}"})
            continue
        if transported:
            ok, why = _validate_transport(raw, path)
            if ok is False:
                log.warning(
                    "psi: %s rejected by its generation manifest (%s) — trying next tier",
                    rel, why,
                )
                rejected.append({"tier": tier, "path": rel,
                                 "reason": f"earnings-call source rejected: {why}"})
                continue
        out = _normalise_ec_frame(raw)
        return out, {
            "state": EC_SOURCE_AVAILABLE, "path": rel, "tier": tier,
            "generation": _transport_generation(path) if transported else None,
            "reason": None, "rows": int(len(out)), "rejected": rejected,
        }

    declared = candidates[0][1] if len(candidates) == 1 else ec_source_path()
    if rejected:
        reason = "; ".join(r["reason"] for r in rejected)
        path_rel = rejected[0]["path"]
    else:
        reason = EC_ABSENT_REASON
        path_rel = _display_path(declared)
        log.warning("psi: earnings_calls parquet absent (%s) — EC join degrades to n=0",
                    path_rel)
    return pd.DataFrame(columns=_EC_COLUMNS), {
        "state": EC_SOURCE_UNAVAILABLE, "path": path_rel, "tier": None,
        "generation": None, "reason": reason, "rows": 0, "rejected": rejected,
    }


def load_ec_table(ec_path: str | Path | None = None) -> pd.DataFrame:
    """Load the earnings-call table, or an EMPTY frame if no tier answers (fail-open, §5).

    Columns kept: ticker (from ``document_ticker``), call_date (datetime),
    earnings_call_sent. When no native store is present the frame is empty so arm C
    simply yields n=0 (the harness must degrade, never crash — the fail-open-on-absent-EC
    test). Callers that need to DISCLOSE the absence should use
    ``load_ec_table_with_source`` instead of inferring it from an empty frame.
    """
    return load_ec_table_with_source(ec_path)[0]


def ec_sent_at_entry(ec_by_ticker: dict[str, pd.DataFrame], ticker: str, entry_date) -> float | None:
    """Most-recent ``earnings_call_sent`` with ``call_date < entry_date`` for ``ticker``.

    STRICTLY-BEFORE (call_date < entry_date, §7 look-ahead control): a call printed on the
    entry day itself is NOT usable (its sentiment would not be known pre-fill). Returns None
    when the ticker has no prior call (arm C then excludes the fire). Never raises.
    """
    g = ec_by_ticker.get(str(ticker))
    if g is None or g.empty:
        return None
    ed = pd.Timestamp(entry_date)
    prior = g[g["call_date"] < ed]
    if prior.empty:
        return None
    v = prior["earnings_call_sent"].iloc[-1]  # g is call_date-sorted → last is most-recent
    if pd.isna(v):
        return None
    return _reject_out_of_native_ec_sent(float(v))


def ec_index(ec_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """{ticker -> call_date-sorted frame} for fast per-fire most-recent lookup."""
    if ec_df is None or ec_df.empty:
        return {}
    out: dict[str, pd.DataFrame] = {}
    for tk, g in ec_df.groupby("ticker"):
        out[str(tk)] = g.sort_values("call_date").reset_index(drop=True)
    return out


# --------------------------------------------------------------------------- #
# PIT stage lookup at an entry date (look-ahead-safe).                          #
# --------------------------------------------------------------------------- #
def stage_at_entry(close: pd.Series, volume: pd.Series | None,
                   bench_close: pd.Series, entry_date) -> tuple[int, int, int]:
    """PIT (stage, weeks_in_stage, n_completed_weeks) at ``entry_date``.

    LOOK-AHEAD GUARD (§7): inputs are TRUNCATED to the entry bar — the close (and bench,
    and volume) are sliced to ``<= entry_date`` before classification, so the weekly stage
    can only see completed weeks on-or-before the entry. Returns (0, 0, n_weeks) for a
    too-young name (< 45 completed weeks). Never raises.
    """
    try:
        ed = pd.Timestamp(entry_date)
        c = close[close.index <= ed]
        v = volume[volume.index <= ed] if volume is not None and len(volume) else None
        b = bench_close[bench_close.index <= ed] if bench_close is not None and len(bench_close) else bench_close
        res = weinstein_stage.classify(c, v, b)
        return int(res.get("stage", 0) or 0), int(res.get("weeks_in_stage", 0) or 0), int(res.get("n_weeks", 0) or 0)
    except Exception as e:  # noqa: BLE001
        log.warning("psi: stage_at_entry failed (%s)", e)
        return 0, 0, 0


# --------------------------------------------------------------------------- #
# Price loaders (§2 union: baskets/ohlcv ∪ data/stocks; bench = data/yahoo/SPY). #
# --------------------------------------------------------------------------- #
def _read_ohlcv(path: Path) -> pd.DataFrame | None:
    try:
        df = pd.read_parquet(path)
    except Exception:  # noqa: BLE001
        return None
    if df is None or df.empty or "close" not in df.columns:
        return None
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:  # noqa: BLE001
            return None
    return df


def load_ticker_prices(ticker: str, data_root: Path) -> tuple[pd.Series | None, pd.Series | None]:
    """(close, volume) daily series for a ticker, preferring baskets/ohlcv then data/stocks
    (the §2 union; the deep stocks store extends late-IPO history). Fail-open → (None, None)."""
    for sub in ("baskets/ohlcv", "stocks"):
        p = Path(data_root) / sub / f"{ticker}.parquet"
        if not p.exists():
            continue
        df = _read_ohlcv(p)
        if df is None:
            continue
        close = df["close"].dropna()
        vol = df["volume"].dropna() if "volume" in df.columns else None
        if len(close):
            return close, vol
    return None, None


def load_bench_close(data_root: Path) -> pd.Series | None:
    """SPY daily close (data/yahoo/SPY.parquet) — the single §2 benchmark. Fail-open → None."""
    p = Path(data_root) / "yahoo" / f"{BENCH_TICKER}.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
    except Exception:  # noqa: BLE001
        return None
    if df is None or df.empty:
        return None
    col = "close" if "close" in df.columns else ("close_price" if "close_price" in df.columns else None)
    if col is None:
        return None
    s = df[col].dropna()
    return s if len(s) else None
