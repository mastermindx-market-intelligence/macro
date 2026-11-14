"""Sector holdings coverage feed (sector_holdings.coverage.v1) — Options R1 W2B, section L-W2B-MACRO.

Sector Central lists a fund's top holdings but never says what share of the
fund they are, because the three natural numbers have three DIFFERENT
denominators: how many names are listed (count coverage), what share of the
fund's weight they carry (fund-weight coverage), and how concentrated the top
of the list is (top-three concentration, of the fund and of the listed
sample). This emitter produces that feed from the committed
data/sector_holdings parquet store for the Terminal's strict reader — ANY
deviation from the output contract makes the reader drop the whole file, so
tests/test_sector_holdings_coverage.py re-checks every rule of it.

The store keeps only the TOP 20 BY WEIGHT per fund, so the fund's total
holding count is unknown today. It is emitted as ``null`` with
``total_unknown: true`` — never 0 (which would read as "the fund holds
nothing") and never the listed count or 20 (which would read as "the fund
holds exactly these"). When a real total source appears, pass ``total=`` and
the same fields turn numeric.

The build_sector_central hook calls emit_holdings_coverage_additive(), which
is additive and never fatal: any failure logs at warning and returns None.

The feed is published atomically: the bytes are staged in a same-directory
temporary sibling and moved onto the destination with one replace, so a failed
or interrupted write leaves the previously published feed exactly as it was.

Run: python -m scripts.build_sector_holdings_coverage --out <path>
(In the sparse session worktree the dry run MUST pass --out; the default
writes under site/, which this checkout never writes.)
"""
from __future__ import annotations

import argparse
import errno
import json
import logging
import math
import numbers
import os
import re
import stat
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
# Unconditional repo-root pin (tests/test_check_script_import_pinning.py): a guarded insert is
# not a pin, because a foreign package ahead of an already-present root still wins.
sys.path.insert(0, str(ROOT))

from lib import config, nyse_calendar, store  # noqa: E402

log = logging.getLogger(__name__)

SCHEMA = "sector_holdings.coverage.v1"
SOURCE = "sector_holdings parquet store (issuer top 20 by weight)"

TICKER = re.compile(r"^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)?$")
MAX_LISTED = 60

# --- capture provenance (owner-local receipt) --------------------------------
#
# The per-fund store carries one reserved capture block per capture (see
# collectors/sector_holdings.py). These constants MIRROR the producer's
# contract; tests/test_sector_holdings_coverage.py asserts the two lists are
# identical, so the mirror cannot drift silently. The published
# sector_holdings.coverage.v1 feed is a CLOSED contract and does NOT carry any
# of this — the receipt is owner-local, for a later admission decision.
CAPTURE_PREFIX = "capture_"
CAPTURE_SCHEMA_VERSION = "sector_holdings.capture.v1"
# Exact requested source, mirrored under the same producer-contract drift test.
SSGA_XLSX = ("https://www.ssga.com/us/en/intermediary/etfs/library-content/"
             "products/fund-data/etfs/us/holdings-daily-us-en-{fund}.xlsx")
CAPTURE_COLUMNS = (
    "capture_schema_version",
    "capture_fund",
    "capture_source_url",
    "capture_content_sha256",
    "capture_content_bytes",
    "capture_retrieved_at",
    "capture_issuer_as_of",
    "capture_date_origin",
)
DATE_ORIGIN_ISSUER_REPORTED = "issuer_reported"
DATE_ORIGIN_RETRIEVAL_FALLBACK = "retrieval_date_fallback"
DATE_ORIGIN_NOT_RECORDED = "date_origin_not_recorded"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# What a receipt may and may not say. A capture consistency check proves that
# the rows came from one identified response — nothing more.
CAPTURE_LIMITATION = (
    "capture consistency is not issuer mapping, source-use rights, economic "
    "causation, historical availability, correction history or a sector explanation")


def _sector_funds() -> list[str]:
    """The collector's fund list, read from the same place the collector reads it
    (collectors/sector_holdings.py iterates config.load()["sponsors"]["sector_funds"])."""
    return [str(f) for f in config.load()["sponsors"]["sector_funds"]]


FUNDS: list[str] = _sector_funds()


def load_snapshots(funds: Sequence[str]) -> dict[str, pd.DataFrame | None]:
    """Exactly the store read the collector's latest_top10 performs, per fund:
    store.read("sector_holdings", fund). The frames stay RAW (full history,
    index = as_of datetime, columns ticker/name/weight_pct/rank) — the
    latest-date slice is coverage_for_fund's job. A fund whose read is absent
    or raises maps to None (logged at warning), never a raise."""
    out: dict[str, pd.DataFrame | None] = {}
    for fund in funds:
        try:
            snap = store.read("sector_holdings", fund)
        except Exception as e:  # noqa: BLE001 — one bad file must not sink the feed
            log.warning("holdings coverage: %s store read failed: %s", fund, e)
            out[fund] = None
            continue
        if snap is None:
            log.warning("holdings coverage: %s has no stored snapshot", fund)
        out[fund] = snap
    return out


def _latest_rows(snapshot: pd.DataFrame) -> pd.DataFrame:
    """The rows of the snapshot's latest index date.

    ONE selector for the whole module: the coverage block and the capture
    receipt must describe the SAME rows, so they cannot drift apart.
    """
    idx = pd.to_datetime(snapshot.index)
    return snapshot.loc[idx == idx.max()]


def coverage_for_fund(fund: str, snapshot: pd.DataFrame | None, *, asof: date,
                      total: int | None = None) -> dict:
    """One fund's coverage block. Pure: reads the frame it is handed, never the
    store or the clock. ``total`` is the fund's total holding count when a
    source knows it; None (unknown) is today's store-wide truth."""
    if snapshot is None or snapshot.empty:
        return {"fund": fund, "as_of": asof.isoformat(), "n_holdings_total": None,
                "total_unknown": True, "listed": [],
                "coverage": {"count": {"listed": 0, "total": None}, "weight_pct": 0.0,
                             "concentration": {"top3_of_fund_pct": None,
                                               "top3_of_sample_pct": None}}}
    last = pd.to_datetime(snapshot.index).max()
    rows = _latest_rows(snapshot)
    tickers = rows["ticker"].astype(str).str.strip().str.upper()
    weights = pd.to_numeric(rows["weight_pct"], errors="coerce").astype(float)
    # The ticker gate is part of `keep`: CASH_USD-style rows, blanks and
    # non-symbols are dropped here, before any ranking happens.
    keep = (tickers.map(lambda t: bool(TICKER.fullmatch(t)))
            & np.isfinite(weights) & (weights >= 0))
    dropped = int((~keep).sum())
    if dropped:
        log.info("holdings coverage: %s dropped %d row(s) (non-ticker or bad weight)",
                 fund, dropped)
    work = (pd.DataFrame({"ticker": tickers[keep].to_numpy(),
                          "weight_pct": weights[keep].to_numpy()})
            .sort_values("weight_pct", ascending=False)
            .drop_duplicates("ticker", keep="first")  # keep the larger weight
            .sort_values(["weight_pct", "ticker"], ascending=[False, True],
                         kind="mergesort")
            .head(MAX_LISTED))
    # rank = position + 1 — never the stored rank column, which has gaps after drops
    listed = [{"ticker": str(r.ticker), "weight_pct": round(float(r.weight_pct), 2),
               "rank": n} for n, r in enumerate(work.itertuples(index=False), start=1)]
    weight = round(sum(row["weight_pct"] for row in listed), 2)
    if total is not None and total < len(listed):
        log.warning("holdings coverage: %s total=%d is below the %d listed rows "
                    "— treating as unknown", fund, total, len(listed))
        total = None
    # total stays None when unknown — the listed count (and the store's
    # top-20 cap) is never a substitute for the fund's real total.
    if len(listed) < 3:
        top3 = None
        top3_share = None
    else:
        top3 = round(sum(row["weight_pct"] for row in listed[:3]), 2)
        top3_share = None if weight == 0 else round(top3 / weight * 100, 2)
    return {"fund": fund, "as_of": last.date().isoformat(),
            "n_holdings_total": total, "total_unknown": total is None,
            "listed": listed,
            "coverage": {"count": {"listed": len(listed), "total": total},
                         "weight_pct": weight,
                         "concentration": {"top3_of_fund_pct": top3,
                                           "top3_of_sample_pct": top3_share}}}


# --- capture receipt (owner-local; NOT part of the published v1 feed) ---------
#
# The receipt binds a fund's latest stored snapshot to the capture that
# produced it: which response, which bytes, which retrieval instant, and
# where the index date came from. It is deliberately humble about what it
# proves: a capture binds ROWS TO A RESPONSE. It does not admit the issuer,
# the source-use rights, the economics, the historical availability, the
# correction history or any sector explanation — and it never claims the
# response body, the original publication time or a revision lineage that the
# capture does not carry.


def _is_null(value) -> bool:
    """True for None, pd.NA, NaT and NaN — but never for a non-scalar."""
    if value is None or value is pd.NA:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _parse_utc_timestamp(value) -> datetime | None:
    """An aware-UTC timestamp, or None. A naive stamp is NOT accepted: a
    retrieval instant without a zone cannot be bound to an index date."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        return None
    return parsed


def _parse_iso_date(value) -> date | None:
    """An ISO calendar date, or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _empty_capture() -> dict:
    """The withheld capture block: no field is ever guessed."""
    return {"schema_version": None, "fund": None, "source_url": None,
            "content_sha256": None, "content_bytes": None, "retrieved_at": None,
            "issuer_as_of": None, "date_origin": None}


def _unavailable_lineage(kind: str) -> dict:
    """An explicitly UNAVAILABLE revision/supersession lineage.

    A capture records ONE response. It never establishes what preceded it,
    what superseded it, or whether the issuer ever corrected it — and a
    same-date replacement is a replacement, not a revision.
    """
    return {"status": "unavailable", "kind": kind, "predecessor": None,
            "successor": None,
            "reason": "the capture records one response and carries no "
                      "revision or supersession evidence"}


def _validate_capture_row(values: dict, fund: str, index_day: date) -> tuple[dict | None, list[str]]:
    """One selected row's capture block: (normalised values, problems).

    An empty ``problems`` list means the block is internally valid. Values is
    None with no problems means the row carries no capture at all (a legacy
    row) — that is a different state from a malformed block, and it is
    reported as such.
    """
    if all(_is_null(value) for value in values.values()):
        return None, []
    problems: list[str] = []
    schema = values["capture_schema_version"]
    if not isinstance(schema, str) or schema != CAPTURE_SCHEMA_VERSION:
        problems.append(f"schema version {schema!r} is not {CAPTURE_SCHEMA_VERSION!r}")
    source_fund = values["capture_fund"]
    if not isinstance(source_fund, str) or source_fund != fund:
        problems.append(f"source fund {source_fund!r} is not {fund!r}")
    url = values["capture_source_url"]
    expected_url = SSGA_XLSX.format(fund=fund.lower()) if fund in FUNDS else None
    if not isinstance(url, str) or expected_url is None or url != expected_url:
        problems.append("source url is not the canonical https url for this fund")
    digest = values["capture_content_sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        problems.append("content digest is not a lowercase sha256 hex digest")
    nbytes = values["capture_content_bytes"]
    # A parquet round-trip widens an int column that carries nulls (legacy
    # rows beside a captured row) to float64, so an exact-integer float is
    # the SAME count — a fractional or negative one is not a count at all.
    if isinstance(nbytes, bool) or not isinstance(nbytes, numbers.Real):
        problems.append("content byte count is not a non-negative integer")
    elif not float(nbytes).is_integer() or int(nbytes) < 0:
        problems.append("content byte count is not a non-negative integer")
    retrieved_at = _parse_utc_timestamp(values["capture_retrieved_at"])
    if retrieved_at is None:
        problems.append("retrieved_at is not an aware utc timestamp")
    raw_as_of = values["capture_issuer_as_of"]
    issuer_as_of = _parse_iso_date(raw_as_of)
    if not _is_null(raw_as_of) and issuer_as_of is None:
        problems.append("issuer as-of is not an iso date")
    origin = values["capture_date_origin"]
    if origin not in (DATE_ORIGIN_ISSUER_REPORTED, DATE_ORIGIN_RETRIEVAL_FALLBACK):
        problems.append(f"date origin {origin!r} is not a native capture origin")
    # Date bindings: the index date must be the date the capture claims.
    if origin == DATE_ORIGIN_ISSUER_REPORTED:
        if issuer_as_of is None:
            problems.append("issuer-reported origin without an issuer as-of date")
        elif issuer_as_of != index_day:
            problems.append(f"issuer as-of {issuer_as_of.isoformat()} is not the "
                            f"indexed date {index_day.isoformat()}")
    elif origin == DATE_ORIGIN_RETRIEVAL_FALLBACK:
        if not _is_null(raw_as_of):
            problems.append("retrieval-date fallback carries an issuer as-of date")
        elif retrieved_at is not None and retrieved_at.date() != index_day:
            problems.append(f"retrieval-date fallback index {index_day.isoformat()} "
                            f"is not the retrieval date {retrieved_at.date().isoformat()}")
    if problems:
        return None, problems
    return {
        "capture_schema_version": schema,
        "capture_fund": source_fund,
        "capture_source_url": url,
        "capture_content_sha256": digest,
        "capture_content_bytes": int(nbytes),
        "capture_retrieved_at": values["capture_retrieved_at"],
        "capture_issuer_as_of": raw_as_of,
        "capture_date_origin": origin,
    }, []


def source_receipt_for_fund(fund: str, snapshot: pd.DataFrame | None) -> dict:
    """The capture receipt bound to one fund's latest stored snapshot.

    Pure: reads the frame it is handed, never the store and never the clock.

    The metadata is validated across ALL the selected (latest-date) rows
    BEFORE any holdings filter or de-duplication — a capture that describes
    only some of the rows it claims is not a consistent capture, and a filter
    that drops rows first would hide exactly that disagreement.

    ``status`` is one of:

    ``consistent``
        every selected row carries the same well-formed capture block;
    ``missing``
        no selected row carries one (legacy rows — their date origin was never
        recorded and is reported as such, never backfilled);
    ``mixed``
        some selected rows carry one and others do not, or the populated rows
        disagree about the digest, the retrieval instant, the issuer date or
        the origin;
    ``malformed``
        a capture is present but invalid (schema, timestamp, digest, byte
        count, source fund or date binding).

    Anything but ``consistent`` WITHHOLDS the capture block: the receipt
    reports the state, never a first-winner's values.
    """
    receipt = {
        "fund": fund,
        "as_of": None,
        "status": "missing",
        "capture": _empty_capture(),
        "reasons": [],
        "issuer_effective_date_qualified": False,
        "original_available_at": None,
        "historically_admissible": False,
        "source_body_retained": False,
        "revision_lineage": _unavailable_lineage("revision"),
        "supersession_lineage": _unavailable_lineage("supersession"),
        "limitation": CAPTURE_LIMITATION,
    }
    if snapshot is None or snapshot.empty:
        receipt["capture"]["date_origin"] = DATE_ORIGIN_NOT_RECORDED
        receipt["reasons"].append("no stored snapshot")
        return receipt
    rows = _latest_rows(snapshot)
    index_day = pd.to_datetime(snapshot.index).max().date()
    receipt["as_of"] = index_day.isoformat()
    if not any(column in rows.columns for column in CAPTURE_COLUMNS):
        receipt["capture"]["date_origin"] = DATE_ORIGIN_NOT_RECORDED
        receipt["reasons"].append(
            "capture block absent — legacy rows, date origin not recorded")
        return receipt
    incomplete = [column for column in CAPTURE_COLUMNS if column not in rows.columns]
    if incomplete:
        receipt["status"] = "malformed"
        receipt["reasons"].append("capture block is incomplete, missing: "
                                  + ", ".join(incomplete))
        return receipt
    populated: list[dict] = []
    empty_rows = 0
    problems: list[str] = []
    for _, row in rows.iterrows():
        values = {column: row[column] for column in CAPTURE_COLUMNS}
        row_values, row_problems = _validate_capture_row(values, fund, index_day)
        if row_problems:
            problems.extend(row_problems)
            continue
        if row_values is None:
            empty_rows += 1
            continue
        populated.append(row_values)
    if problems:
        receipt["status"] = "malformed"
        receipt["reasons"].extend(sorted(set(problems)))
        return receipt
    if not populated:
        receipt["capture"]["date_origin"] = DATE_ORIGIN_NOT_RECORDED
        receipt["reasons"].append(
            "no selected row carries a capture — legacy rows, date origin not recorded")
        return receipt
    if empty_rows:
        receipt["status"] = "mixed"
        receipt["reasons"].append(
            f"{empty_rows} of {len(rows)} selected row(s) carry no capture")
        return receipt
    disagreements = [column for column in CAPTURE_COLUMNS
                     if len({row[column] for row in populated}) > 1]
    if disagreements:
        receipt["status"] = "mixed"
        receipt["reasons"].append("capture fields disagree across the selected "
                                  "rows: " + ", ".join(disagreements))
        return receipt
    first = populated[0]
    receipt["status"] = "consistent"
    receipt["capture"] = {
        "schema_version": first["capture_schema_version"],
        "fund": first["capture_fund"],
        "source_url": first["capture_source_url"],
        "content_sha256": first["capture_content_sha256"],
        "content_bytes": first["capture_content_bytes"],
        "retrieved_at": first["capture_retrieved_at"],
        "issuer_as_of": first["capture_issuer_as_of"],
        "date_origin": first["capture_date_origin"],
    }
    # Only an issuer-stated date qualifies as an issuer-effective date; a
    # retrieval-date fallback says nothing about the issuer's effective date.
    receipt["issuer_effective_date_qualified"] = (
        first["capture_date_origin"] == DATE_ORIGIN_ISSUER_REPORTED)
    return receipt


def coverage_with_source_receipt(fund: str, snapshot: pd.DataFrame | None, *,
                                  asof: date, total: int | None = None) -> dict:
    """The coverage block and its capture receipt as ONE bound selection.

    The receipt is computed FIRST — on the same latest-date rows the coverage
    block uses, and before the holdings filter and de-duplication — so a
    capture is never validated on a subset of the rows it claims to describe.
    The coverage block is the existing one, unchanged: the same weight and
    count denominators, the same unknown total holding count, the same
    fund-versus-sample semantics.
    """
    receipt = source_receipt_for_fund(fund, snapshot)
    coverage = coverage_for_fund(fund, snapshot, asof=asof, total=total)
    return {"coverage": coverage, "receipt": receipt}


def build_holdings_coverage(snapshots: Mapping[str, pd.DataFrame | None], *,
                            funds: Sequence[str] = FUNDS,
                            asof: date | None = None,
                            source: str = SOURCE) -> dict:
    """The whole feed: meta + one block per fund in FUNDS order. meta.asOf is
    the max of the explicitly given date (if any) and every fund's snapshot
    date; with no dated snapshot anywhere it falls back to the calendar's
    expected last session. Empty funds take meta.asOf as their as_of, so every
    fund's as_of is <= meta.asOf by construction."""
    fund_dates: dict[str, date | None] = {}
    for fund in funds:
        snap = snapshots.get(fund)
        fund_dates[fund] = (None if snap is None or snap.empty
                            else pd.to_datetime(snap.index).max().date())
    candidates = [d for d in fund_dates.values() if d is not None]
    if asof is not None:
        candidates.append(asof)
    meta_asof = max(candidates) if candidates else nyse_calendar.expected_last_session()
    out_funds = [coverage_for_fund(fund, snapshots.get(fund),
                                   asof=fund_dates[fund] or meta_asof)
                 for fund in funds]
    return {"meta": {"schema": SCHEMA, "asOf": meta_asof.isoformat(), "source": source},
            "funds": out_funds}


def _publish_mode(destination: Path) -> int:
    """The mode the published file must carry.

    An existing destination keeps its own mode: a served artifact must not
    silently change permissions because it was rewritten. A destination that
    does not exist yet gets the mode a normal create would give (0666 minus this
    process's umask), because tempfile.mkstemp's 0600 would leave the feed
    unreadable to the static site. Neither branch ever widens the permissions
    the destination already had.

    ONLY a genuinely absent destination may take that default mode. Any other
    metadata failure (EIO, ESTALE, EACCES) leaves the destination's real mode
    UNKNOWN, so it propagates instead of being read as "absent": guessing the
    default there would replace a restricted 0600 file with a 0644 one and
    silently widen its permissions.
    """
    try:
        return stat.S_IMODE(destination.stat().st_mode)
    except FileNotFoundError:
        pass
    umask = os.umask(0)  # read it once; this builder is single-threaded
    os.umask(umask)
    return 0o666 & ~umask


def _reject_symlink_destination(destination: Path) -> None:
    """Refuse to publish onto a symlink.

    os.replace onto a symlink path REPLACES the link itself with a regular
    file: the file the link pointed at keeps its old bytes while the served
    feed quietly stops being the one that was written. A dangling link would
    be replaced just the same. Neither is a publication the caller asked for,
    so both are refused loudly and the link is left exactly as it was.
    """
    if os.path.islink(destination):
        raise FileExistsError(errno.EEXIST,
                              "destination is a symlink; refusing to replace it",
                              str(destination))


def _fsync_parent_dir(directory: Path) -> None:
    """Best-effort durability for the rename itself.

    This runs AFTER os.replace already published the feed: there is nothing to
    roll back, so a failure here is logged, not raised — raising here would
    misreport a successful publication as a failure and invite a duplicate
    write over an already-good file.
    """
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError as exc:
        log.warning("holdings coverage: parent dir fsync open failed: %s", exc)
        return
    try:
        os.fsync(fd)
    except OSError as exc:
        log.warning("holdings coverage: parent dir fsync failed: %s", exc)
    finally:
        os.close(fd)


def _validate_weight_contract(feed: Mapping) -> None:
    """Reject weights the Terminal's strict reader would reject, before touching output."""
    for fund in feed["funds"]:
        listed = fund["listed"]
        for row in listed:
            pct = row["weight_pct"]
            if (isinstance(pct, bool) or not isinstance(pct, (int, float))
                    or not math.isfinite(pct) or not 0 <= pct <= 100):
                raise ValueError(
                    f"holdings coverage: {fund['fund']} invalid listed weight "
                    f"{row['ticker']}={pct}")
        coverage_pct = fund["coverage"]["weight_pct"]
        listed_sum = round(sum(row["weight_pct"] for row in listed), 2)
        if (isinstance(coverage_pct, bool)
                or not isinstance(coverage_pct, (int, float))
                or not math.isfinite(coverage_pct)
                or not 0 <= coverage_pct <= 100.0001
                or abs(coverage_pct - listed_sum) > 0.01):
            raise ValueError(
                f"holdings coverage: {fund['fund']} invalid aggregate weight "
                f"{coverage_pct} (listed sum {listed_sum})")


def write_holdings_coverage(path: Path, feed: dict) -> None:
    """Publish the feed atomically: the destination is replaced in one step or
    not at all, so an interrupted write can never leave the last good feed
    truncated or half-written. The bytes are exactly the ones the Terminal
    reader expects — compact JSON, no trailing newline.

    The weight-contract gate (#10193) runs first and exactly once, before any
    output mutation: a feed the Terminal's strict reader would reject never
    reaches the filesystem, so the previously published feed, its mode and its
    directory are all left exactly as they were.
    """
    _validate_weight_contract(feed)
    path = Path(path)
    # Serialize before the parent exists: a serialization error must not create
    # a directory or leave an output behind.
    payload = json.dumps(feed, separators=(",", ":"), ensure_ascii=False)
    # Both destination checks come BEFORE anything is created or staged: a
    # refusal must leave the previously published feed, its mode and its
    # directory exactly as they were.
    _reject_symlink_destination(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = _publish_mode(path)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
    _fsync_parent_dir(path.parent)


def emit_holdings_coverage_additive(fdir: Path, *, snapshots_loader=None,
                                    log=None) -> Path | None:
    """Additive hook target for build_sector_central: build + write the feed
    under *fdir*, or return None on ANY failure. Never raises."""
    lg = log if log is not None else logging.getLogger(__name__)
    loader = snapshots_loader if snapshots_loader is not None else (
        lambda: load_snapshots(FUNDS))
    try:
        feed = build_holdings_coverage(loader())
        out = Path(fdir) / "sector_holdings_coverage.json"
        write_holdings_coverage(out, feed)
        return out
    except Exception as e:  # noqa: BLE001 — a failed side feed must never break the host build
        lg.warning("holdings coverage: feed skipped: %s", e)
        return None


def _fmt(v) -> str:
    return "null" if v is None else str(v)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit the sector holdings coverage feed (Options R1 W2B).")
    default_out = ROOT / config.load()["storage"]["site_dir"] / "sectordata" / (
        "sector_holdings_coverage.json")
    parser.add_argument("--out", default=str(default_out),
                        help="output path for sector_holdings_coverage.json")
    args = parser.parse_args(argv)
    try:
        feed = build_holdings_coverage(load_snapshots(FUNDS))
        write_holdings_coverage(Path(args.out), feed)
    except Exception as e:  # noqa: BLE001 — same fail-soft contract as the hook
        log.error("holdings coverage: emit failed: %s", e)
        return 1
    for f in feed["funds"]:
        c = f["coverage"]
        total = "unknown" if f["total_unknown"] else f["n_holdings_total"]
        print(f"{f['fund']} as_of={f['as_of']} listed={c['count']['listed']} "
              f"weight={c['weight_pct']}% "
              f"top3={_fmt(c['concentration']['top3_of_fund_pct'])}% total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
