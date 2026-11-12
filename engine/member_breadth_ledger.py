"""engine.member_breadth_ledger — the nightly member-level breadth forward record.

WHAT IT IS. The forward half of the group-breadth evidence base: one row per
S&P 500 member ticker per session, accrued night after night into
``data/breadth/member_breadth_ledger.parquet`` (append-only, keep-FIRST per
``(date, ticker)``). The RECONSTRUCTED history of the same measures lives in
``engine/group_breadth_history.py`` — rebuilt from historical closes — while
this ledger keeps recording forward from tonight on, per the Historical
Reconstruction Protocol §4.2/§4.6 (one code path, keep recording forward).
The rows are produced by ``group_breadth_history.member_rows`` — the same
functions that build the history — so the nightly record and the
reconstruction cannot drift apart. ``collectors/breadth.py`` calls this after
its normal breadth build; nothing here computes anything new.

SCHEMA (exactly these columns, in this order):

  date               str   ISO date of the session (the ledger's PIT key half 1)
  ticker             str   member symbol (the ledger's PIT key half 2)
  group              str   group label (GICS sector) assigned for that session
  has_200_sessions   bool  ticker has a defined 200-session average that session
  above_200          bool  its close is strictly above that average
  source_asof        str|None  the ticker's own latest close date on/before date

DISCIPLINE. Append-only, keep-FIRST per (date, ticker): a past night's member
row is NEVER rewritten — the point-in-time invariant. A batch must carry a
single date; appends of a NEW date only (a date newer than everything already
in the ledger, or an empty ledger).

B11 fences (same order as ``engine/cycle_forward_log.py``), each returning 0
with a log.warning and no write, all before any write:

  1. lane   — refuse unless ``ledger_lane.nightly_advance_enabled()``
              (COLLECT_LANE=nightly, the daily.yml engine-job sentinel). A
              replay-band or interactive run renders, it must not stamp.
  2. future — any row dated after today's UTC date is a clock skew or a
              fabricated stamp; it must never occupy a real day's keep-FIRST
              slot. Refuses the whole batch.
  3. replay — a batch dated OLDER than the newest date already in the ledger
              is a stale session backfilled after a newer one was observed.
              An EQUAL date falls through to keep-FIRST (new tickers on the
              same night append; existing (date, ticker) rows keep the first
              write).

Never raises: every failure is logged and returns 0. A prior ledger that
cannot be read is left untouched and nothing is written (unlike
cycle_forward_log, which starts fresh): one night must never overwrite the
append-only record.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from engine.ledger_lane import nightly_advance_enabled

log = logging.getLogger(__name__)

# The ledger's exact schema — column set AND order. ``member_rows`` (window=200)
# emits exactly this; batches are re-ordered to it before the write.
SCHEMA: tuple[str, ...] = ("date", "ticker", "group", "has_200_sessions",
                           "above_200", "source_asof")

_LEDGER_NAME = "member_breadth_ledger.parquet"


def _utc_today() -> str:
    """Today's UTC date as an ISO string — the future fence's clock."""
    return datetime.now(timezone.utc).date().isoformat()


def _iso_date(value) -> str | None:
    """Best-effort strict ISO date (YYYY-MM-DD); None when unparseable.

    ``member_rows`` stamps ``date().isoformat()`` strings, so None is a
    degenerate input — the batch is refused rather than guessed at."""
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except (TypeError, ValueError):
        return None


def append_member_rows(rows: pd.DataFrame, path: Path | None = None) -> int:
    """Append one night's member rows to the breadth member ledger.

    ``rows`` is a DataFrame from ``group_breadth_history.member_rows`` (schema
    above; extra columns are dropped, missing columns refuse the batch).
    ``path`` overrides the ledger location (tests); default
    ``data/breadth/member_breadth_ledger.parquet`` via ``lib.config.data_dir()``.

    Returns the number of rows in the submitted batch (0 on any error, empty
    input, or a B11 refusal — lane / future / replay; the module docstring has
    the census). Never raises.
    """
    try:
        return _append(rows, path)
    except Exception as e:  # noqa: BLE001
        log.warning("member_breadth_ledger: append failed: %s", e)
        return 0


def _append(rows, path: Path | None) -> int:
    if not isinstance(rows, pd.DataFrame) or rows.empty:
        return 0

    # B11 fence 1 — lane. The live ledger advances only from the nightly
    # engine lane (HOUSE-U5: nightly is the SOLE advancer of data/ forward
    # ledgers); an off-lane run must not stamp.
    if not nightly_advance_enabled():
        log.warning("member_ledger_lane_refused (COLLECT_LANE/US_LANE != nightly) "
                    "— live ledger not advanced")
        return 0

    missing = [c for c in SCHEMA if c not in rows.columns]
    if missing:
        log.warning("member_breadth_ledger: missing column(s) %s — skipped", missing)
        return 0
    new = rows.reset_index(drop=True).loc[:, list(SCHEMA)]

    # A batch is ONE night. Zero or several distinct dates (or any unparseable
    # one) have no single PIT slot to occupy — refuse rather than guess.
    dates = [_iso_date(v) for v in new["date"]]
    if any(d is None for d in dates):
        log.warning("member_breadth_ledger: unparseable date in batch — skipped")
        return 0
    batch_d = sorted(set(dates))
    if len(batch_d) != 1:
        log.warning("member_breadth_ledger: batch carries %d distinct dates (%s) — "
                    "one night per append — skipped", len(batch_d), batch_d[:4])
        return 0
    batch_d = batch_d[0]

    # B11 fence 2 — future. A row dated after today's UTC date must never take
    # a real day's keep-FIRST slot.
    if batch_d > _utc_today():
        log.warning("member_breadth_future_refused date=%s is after today — "
                    "live ledger not advanced", batch_d)
        return 0

    if path is None:
        try:
            from lib import config
            path = config.data_dir() / "breadth" / _LEDGER_NAME
        except Exception as e:  # noqa: BLE001
            log.warning("member_breadth_ledger: cannot resolve data dir: %s", e)
            return 0

    prior = pd.DataFrame()
    if path.exists():
        try:
            prior = pd.read_parquet(path)
        except Exception as e:  # noqa: BLE001
            # An existing ledger that cannot be read is NEVER replaced: doing so
            # would overwrite the append-only forward record with one night.
            log.warning("member_breadth_ledger: cannot read prior ledger (%s) — "
                        "refusing to write; ledger left untouched", e)
            return 0

    # B11 fence 3 — replay. An older session must not be backfilled after a
    # newer one was observed; an equal date falls through to keep-FIRST below.
    if not prior.empty and "date" in prior.columns:
        prior_dates = [d for d in (_iso_date(x) for x in prior["date"]) if d]
        if prior_dates and batch_d < max(prior_dates):
            log.warning("member_breadth_replay_refused date=%s predates newest "
                        "prior stamp %s — live ledger not advanced",
                        batch_d, max(prior_dates))
            return 0

    combined = (pd.concat([prior, new], ignore_index=True) if not prior.empty
                else new)

    # keep-FIRST invariant: a row for (date, ticker) already in the ledger is
    # NEVER overwritten — the first write wins.
    combined = combined.drop_duplicates(subset=["date", "ticker"], keep="first")

    path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(path, index=False)
    return len(new)
