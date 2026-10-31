"""Russell 2000 internal breadth + constituent close matrix.

Fourth BreadthAdapter subclass (after S&P 500 breadth.py, S&P 600
smallcap_breadth.py, and S&P MidCap 400 midcap_breadth.py). Expands the
dossier universe from the S&P 1500 to ∪ Russell 2000 (+~1,273 net-new names).

CONSTITUENT SOURCE — Finviz screener (idx_rut), NOT Wikipedia:
  The Russell 2000 has no free constituent table on Wikipedia. We source
  constituents from data/finviz_screener/idx_rut.json, which is written
  nightly in collect.py's us_scope block (the same Finviz fetch that powers
  the Nasdaq/Russell subsector desks). Row fields: ticker / company / sector.

STALE-JSON GUARD (never-shrink-the-ledger):
  If idx_rut.json is absent, older than 7 days, or has fewer than 1,600 rows
  (the sanity floor), we keep whatever constituents.parquet was last committed
  rather than shrinking the universe on a bad scrape. A ::warning is emitted.

CLOSES WINDOW — 2 years (vs sp600's ~3y, cost control):
  ~1,900 names × 2y in ≤250-ticker chunks. Chunks are capped at 250 to avoid
  Yahoo batch throttle (the sibling uses 80 from the shared yahoo.batch_size;
  we override to 250 here — still conservative for the larger universe).

FIRST-NIGHT BACKFILL NOTE:
  ~1,900 names × 2y of closes = significant download; the adapter time-boxes
  via the same per-batch time.sleep(1) pacing from the base class. If a run
  is interrupted mid-backfill the partial _closes_cache.parquet is persisted
  and the next run's incremental path (1mo tail) fills the gap. Self-healing.

Outputs (data/russell_breadth/):
  constituents.parquet — ticker-indexed: name, sector
  _closes_cache.parquet — wide date×ticker close matrix (gitignored; CI cache)
  breadth.parquet — breadth aggregates (free byproduct; nothing consumes yet)
"""
from __future__ import annotations

import json
import logging
import math
import time

import pandas as pd

from collectors.breadth import BreadthAdapter
from lib import config

log = logging.getLogger(__name__)

# Finviz idx_rut.json must have at least this many rows to be trusted.
# The live Russell 2000 carries ~2,000 names; 1,600 gives a comfortable
# margin against scrape truncation.
_CONSTITUENTS_FLOOR = 1_600

# Maximum age (days) for the finviz JSON before we prefer the cached parquet.
_JSON_MAX_AGE_DAYS = 7

# Russell 2000 download chunk cap — larger than the shared yahoo.batch_size
# (80) since the R2k universe is ~2× the S&P 600 and yfinance handles 250-
# ticker batches reliably. Overrides the base class batch_size from yahoo cfg.
_CHUNK_SIZE = 250

# Breadth compute: drop rows where fewer than this many tickers reported
# (analogous to compute_updown's n_reporting >= 300 for S&P 500, scaled for
# ~1,900-member R2k universe).
_N_REPORTING_FLOOR = 1_200


def _load_finviz_json() -> dict | None:
    """Return the idx_rut.json payload, or None when absent/unreadable."""
    path = config.data_dir() / "finviz_screener" / "idx_rut.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        log.warning("russell_breadth: could not read idx_rut.json: %s", e)
        return None


def _json_age_days(payload: dict) -> float:
    """Compute age in days of an idx_rut.json payload from its as_of field."""
    try:
        as_of = pd.Timestamp(payload["as_of"], tz="UTC")
        return (pd.Timestamp.now("UTC") - as_of).total_seconds() / 86400.0
    except Exception:  # noqa: BLE001
        return float("inf")


class RussellBreadthAdapter(BreadthAdapter):
    """Russell 2000 breadth — mirrors SmallCapBreadthAdapter exactly except
    for the constituent source (Finviz idx_rut.json instead of Wikipedia),
    a 2-year closes window, a ≥1,600-row JSON sanity floor, and a ≥1,200
    n_members breadth-output floor."""

    name = "russell_breadth"
    group = "russell_breadth"
    session_calendar = "US"  # observation dates follow the cash/Connect session

    def __init__(self) -> None:
        self.cfg = config.load()["russell_breadth"]
        self.ycfg = config.load()["yahoo"]
        self.cache_path = config.data_dir() / "russell_breadth" / "_closes_cache.parquet"

    # ------------------------------------------------------------------
    # Constituent sourcing — Finviz idx_rut.json, not Wikipedia
    # ------------------------------------------------------------------

    def constituents(self) -> pd.DataFrame:
        """Load Russell 2000 constituents from data/finviz_screener/idx_rut.json.

        Falls back to the previously committed constituents.parquet when the
        JSON is absent, stale (>7d), or has fewer than _CONSTITUENTS_FLOOR rows.
        Raises only when BOTH the JSON and the fallback parquet are unavailable.
        """
        payload = _load_finviz_json()
        cpath = self.cache_path.parent / "constituents.parquet"

        # Evaluate freshness and size of the JSON
        if payload is not None:
            age = _json_age_days(payload)
            n = payload.get("n", 0) or 0
            if age > _JSON_MAX_AGE_DAYS:
                # Bare print, NOT a logger call: GitHub only parses a workflow command when
                # "::" STARTS the line, and this module's logging format prefixes every
                # record (e.g. "WARNING ::warning ..."), which silently drops the annotation.
                print(f"::warning:: russell_breadth: idx_rut.json is {age:.1f} days old "
                      f"(threshold {_JSON_MAX_AGE_DAYS}) — using committed "
                      "constituents.parquet to avoid stale-scrape universe shrink",
                      flush=True)
                payload = None
            elif n < _CONSTITUENTS_FLOOR:
                print(f"::warning:: russell_breadth: idx_rut.json has only {n} rows (floor "
                      f"{_CONSTITUENTS_FLOOR}) — using committed constituents.parquet to "
                      "avoid bad-scrape universe shrink",
                      flush=True)
                payload = None

        if payload is not None:
            rows = payload.get("rows", [])
            members = pd.DataFrame([
                {"symbol": r["ticker"], "name": r["company"], "sector": r["sector"]}
                for r in rows
                if r.get("ticker")
            ])
            if not members.empty:
                log.info("russell_breadth: loaded %d constituents from idx_rut.json", len(members))
                # Same symbol normalization the Wikipedia-sourced siblings get via
                # _repair (BRK.B -> BRK-B, junk-symbol drop) — keeps page keys aligned.
                return self._repair(members[["symbol", "name", "sector"]])

        # Fallback: previously committed constituents.parquet (never-shrink semantics)
        if cpath.exists():
            try:
                prior = pd.read_parquet(cpath).reset_index()
                # The parquet is indexed by symbol; reset gives us 'symbol' as a column.
                if "symbol" not in prior.columns and "index" in prior.columns:
                    prior = prior.rename(columns={"index": "symbol"})
                log.warning(
                    "russell_breadth: falling back to %d committed constituents "
                    "(idx_rut.json absent or rejected)",
                    len(prior),
                )
                return prior[["symbol", "name", "sector"]]
            except Exception as e:  # noqa: BLE001
                raise RuntimeError(
                    "russell_breadth: idx_rut.json unusable AND constituents.parquet "
                    f"unreadable: {e}"
                ) from e
        raise RuntimeError(
            "russell_breadth: idx_rut.json absent/unusable and no committed "
            "constituents.parquet — cannot seed the universe"
        )

    def constituents_checked(self, members: pd.DataFrame) -> pd.DataFrame:
        """Russell 2000 sanity floor: ≥1,600 names (mirrors sp600's ≥450 pattern)."""
        if members.empty or len(members) < _CONSTITUENTS_FLOOR:
            raise ValueError(
                f"russell_breadth constituents list suspicious: {len(members)} rows "
                f"(floor {_CONSTITUENTS_FLOOR})"
            )
        return members

    # ------------------------------------------------------------------
    # Closes download — 250-ticker chunks, 2-year window
    # ------------------------------------------------------------------

    def _download_closes(self, tickers: list[str], period: str) -> pd.DataFrame:
        """Override to use _CHUNK_SIZE=250 instead of the shared yahoo batch_size=80.

        The R2k universe is ~2× the S&P 600; 250-ticker chunks keep each
        yfinance batch well inside Yahoo's throttle zone while halving the
        wall-clock vs using batch_size=80. All other retry/backoff/extras
        logic inherited from the base class is preserved by patching ycfg."""
        # The canonical cache belongs to BreadthAdapter.fetch AFTER successful
        # source validation/merge. Historically this override wrote a 1mo Yahoo
        # response straight to that path before the base 80% coverage check,
        # destroying a recoverable whole-window cache on a partial provider read.
        # Only an actual cache-MISSING first backfill may save a partial seed.
        cache_path = getattr(self, "cache_path", None)
        had_cache = cache_path is not None and cache_path.exists()
        # Freeze one owner-provided *completed* session before any provider I/O.
        # A slow batch spanning the next close may not borrow that later date.
        completed = None
        if len(tickers) >= _CONSTITUENTS_FLOOR:
            from lib import nyse_calendar
            completed = nyse_calendar.expected_last_session()
        orig_bs = self.ycfg.get("batch_size", 80)
        self.ycfg = {**self.ycfg, "batch_size": _CHUNK_SIZE}
        try:
            closes = super()._download_closes(tickers, period)
        finally:
            self.ycfg = {**self.ycfg, "batch_size": orig_bs}

        # Cold-start resilience is intentional, but it is NOT a general write
        # permission. Only seed an absent cache from a historical backfill. A
        # normal 1mo refresh or split-seam re-pull cannot overwrite an existing
        # complete cache before the base owner accepts/publishes the final merge.
        if not had_cache and period != "1mo":
            try:
                if closes is not None and not closes.empty and cache_path is not None:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    closes.to_parquet(cache_path)
            except Exception as exc:  # noqa: BLE001
                log.debug("russell_breadth: first-backfill partial persist skipped: %s", exc)

        # Valid data at any historical date is not proof of THIS completed
        # session's closes. Yahoo can return a successful but partially empty
        # DataFrame; the inherited global column-count test only checks whether
        # members EVER reported. For a normal large-universe refresh, require the
        # incumbent completed-session calendar and ≥80% finite positive closes.
        # Fail before fetch() can publish a mixed/stale cache as collector=ok.
        # An absent-cache first backfill may persist its partial recovery seed
        # above, but still MUST report source failure until this check passes.
        # Tiny seam re-pulls are optional source repairs, not full-universe
        # qualification; don't apply a 1,600-name threshold to them.
        if completed is not None:
            matching = [] if closes is None else [
                pos for pos, stamp in enumerate(closes.index)
                if pd.Timestamp(stamp).date() == completed
            ]
            valid_count = 0
            if len(matching) == 1:
                row = closes.iloc[matching[0]]
                for symbol in tickers:
                    value = row.get(symbol)
                    try:
                        price = float(value)
                    except (ValueError, TypeError):
                        continue
                    if math.isfinite(price) and price > 0:
                        valid_count += 1
            needed = (4 * len(tickers) + 4) // 5  # ceil(80%), integer-safe
            if valid_count < needed:
                raise RuntimeError(
                    "russell_breadth completed-session close coverage "
                    f"{valid_count}/{len(tickers)} < {needed} on {completed}; "
                    "refusing incomplete refresh before cache publication"
                )

        return closes

    # ------------------------------------------------------------------
    # Breadth compute — n_members floor for the R2k universe
    # ------------------------------------------------------------------

    def compute(self, closes: pd.DataFrame) -> pd.DataFrame:
        """Call the base compute then drop rows with fewer than _N_REPORTING_FLOOR
        tickers reporting (analogous to compute_updown's ≥300 floor for S&P 500,
        scaled to the ~1,900-member Russell universe)."""
        out = super().compute(closes)
        if not out.empty:
            out = out[out["n_members"] >= _N_REPORTING_FLOOR]
        return out
