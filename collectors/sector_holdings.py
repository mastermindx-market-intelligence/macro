"""Top-N holdings per sector SPDR + their stock prices + light fundamentals.

- Holdings: SSGA's daily holdings XLSX per fund (public investor documents).
  Top N (=20) by weight, upserted into one history parquet per sector. The
  XLSX already lists every holding, so widening N is free (no extra fetch);
  N=20 roughly doubles name coverage for the single-stock library and the
  heatmap's offline cap proxy vs the legacy top-10.
- Stock prices: yahoo batch for the union of all top-N tickers (~160-200
  names), stored under data/stocks/ — full history on backfill (the cycle
  calibration needs it), incremental daily afterwards.
- Fundamentals: best-effort yfinance info fields, weekly cadence, LOW
  CONFIDENCE by design (unofficial API, sparse fields).
"""
from __future__ import annotations

import copy
import hashlib
import io
import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone

import pandas as pd

from collectors.base import Adapter
from lib import config, delisted_symbols, nyse_calendar, store

log = logging.getLogger(__name__)

# How many holdings to keep per sector ETF. The SSGA file carries every holding,
# so this only sets how deep into the tail we store/track. 20 ≈ 75-85% of each
# fund's weight and ~160-200 union names (vs ~110 at top-10). The legacy
# helper names (top10_union/latest_top10) are kept for their callers.
TOP_N = 20

SSGA_XLSX = ("https://www.ssga.com/us/en/intermediary/etfs/library-content/"
             "products/fund-data/etfs/us/holdings-daily-us-en-{fund}.xlsx")

# --- capture provenance -------------------------------------------------------
#
# A holdings snapshot answers "what did the fund hold" but not "where did this
# come from" or "when was it fetched". The capture block records both as
# ordinary scalar columns in the per-fund parquet that already stores the
# snapshot, under one reserved prefix:
#
#   * no DataFrame.attrs — those do not survive the parquet round-trip;
#   * no side-car artifact and no new store — the block travels with the rows
#     it describes, so a row can never be bound to a response that did not
#     produce it;
#   * ONE block per capture, repeated on every row of that capture, so each
#     row is self-describing.
#
# The block records provenance only. It does NOT establish issuer mapping,
# source-use rights, economic causation, historical availability, correction
# history or any sector explanation.
CAPTURE_PREFIX = "capture_"
CAPTURE_SCHEMA_VERSION = "sector_holdings.capture.v1"
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
# Where the index date came from. "issuer_reported" means the issuer's own
# file stated that date; "retrieval_date_fallback" means the file stated none
# and the index date is the retrieval date, which qualifies NOTHING about the
# issuer's effective date; "date_origin_not_recorded" is the honest value for
# rows written before the capture block existed and is never backfilled.
DATE_ORIGIN_ISSUER_REPORTED = "issuer_reported"
DATE_ORIGIN_RETRIEVAL_FALLBACK = "retrieval_date_fallback"
DATE_ORIGIN_NOT_RECORDED = "date_origin_not_recorded"

# The PIT history archive's schema is FIXED at six columns. The capture block
# belongs to the per-fund store; copying it here would silently widen a
# published archive for every snapshot ever taken.
HISTORY_COLUMNS = ("as_of", "etf", "ticker", "name", "weight_pct", "rank")


def _utc_now() -> datetime:
    """The ONE aware-UTC reading a capture is stamped with.

    Every timestamp of one capture comes from a single call of this function,
    so the retrieval instant and the fallback index date can never disagree.
    Nothing else in this module may read the clock.
    """
    return datetime.now(timezone.utc)


def _with_capture_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Every stored frame carries the full reserved capture block.

    Rows written before the capture block existed (or by any other writer) get
    NULL metadata — never the latest capture's values backfilled onto them,
    which would silently date a legacy snapshot to a response that never
    produced it.
    """
    out = frame.copy()
    for column in CAPTURE_COLUMNS:
        if column not in out.columns:
            out[column] = None
    return out


_ISSUER_MONTHS = {
    key.lower(): number
    for number, month in enumerate(
        ("January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"),
        start=1,
    )
    for key in (month, month[:3])
}


def _parse_issuer_date(text: str) -> date:
    """Read a complete calendar date without filling missing components.

    Accepted source forms are ISO YYYY-MM-DD, explicit US month/day/year
    with a four-digit year, and English month-name day[,] year. Numeric
    slash dates always mean month/day/year; no locale or day-first inference.
    Partial dates, relative words and timestamps are not issuer dates.
    """
    iso = re.fullmatch(r"([0-9]{4})-([0-9]{2})-([0-9]{2})", text)
    us = re.fullmatch(r"([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})", text)
    named = re.fullmatch(r"([A-Za-z]+) +([0-9]{1,2}),? +([0-9]{4})", text)
    try:
        if iso:
            year, month, day = map(int, iso.groups())
        elif us:
            month, day, year = map(int, us.groups())
        elif named:
            month = _ISSUER_MONTHS[named[1].lower()]
            day, year = int(named[2]), int(named[3])
        else:
            raise ValueError("complete supported calendar date required")
        return date(year, month, day)
    except (KeyError, ValueError) as error:
        raise ValueError(
            f"holdings issuer as-of date is malformed: {text!r}") from error


def _issuer_as_of(raw: pd.DataFrame, header_row: int) -> date | None:
    """The issuer's own as-of date, or None when the file states none.

    Every "As of" cell above the header row is a claim about the same date, so
    two different claims are a CONFLICT: the capture is refused rather than
    silently resolved to whichever cell happened to come last. A cell that
    cannot be parsed is a MALFORMED claim and is refused too — a file that
    states an unusable date must not fall back to the retrieval date, because
    that would relabel an issuer-stated snapshot as if the issuer had said
    nothing at all.
    """
    if raw.shape[1] < 2:
        return None
    stated: list[date] = []
    for i in range(header_row):
        cell = str(raw.iloc[i, 1])
        if "As of" not in cell:
            continue
        text = cell.replace("As of", "", 1).strip()
        stated.append(_parse_issuer_date(text))
    if not stated:
        return None
    unique = sorted(set(stated))
    if len(unique) > 1:
        raise ValueError("holdings issuer as-of dates conflict: "
                         + ", ".join(d.isoformat() for d in unique))
    return unique[0]


class SectorHoldingsAdapter(Adapter):
    """Daily top-N (=20) holdings snapshots for the 11 sector SPDRs."""

    name = "sector_holdings"
    group = "sector_holdings"

    def __init__(self) -> None:
        self.cfg = config.load()["sponsors"]

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        # N rows share one date, so these tables bypass the store's
        # one-row-per-date upsert and are merged here instead
        ok, errors = 0, []
        for fund in self.cfg["sector_funds"]:
            try:
                snap = self._fetch_fund(fund)
                self._merge_write(fund, snap)
                ok += 1
                time.sleep(0.5)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{fund}: {e}")
        if not ok:
            raise RuntimeError(f"all sector holdings failed: {errors}")
        if errors:
            log.warning("sector_holdings partial: %s", errors)
        s = pd.DataFrame({"funds_ok": [ok]}, index=[pd.Timestamp(date.today())])
        return {"holdings_runs": s}

    def _merge_write(self, fund: str, snap: pd.DataFrame) -> None:
        d = config.data_dir() / self.group
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{fund}.parquet"
        incoming = _with_capture_columns(snap)
        incoming_dates = pd.DatetimeIndex(pd.to_datetime(incoming.index)).unique()
        if not len(incoming_dates):
            raise ValueError(f"sector holdings {fund}: empty capture refused")
        incoming_max = incoming_dates.max()
        if p.exists():
            old = pd.read_parquet(p)
            old.index = pd.to_datetime(old.index)
            stored_max = old.index.max()
            if (stored_max is not None and pd.notna(stored_max)
                    and incoming_max < stored_max):
                # A regressive capture must never be written: the merged file's
                # max date would relabel an older capture as the current one,
                # and the history archiver would then file the STORED tip
                # under the incoming capture's identity. The stored snapshot
                # is preserved exactly as it is.
                raise ValueError(
                    f"sector holdings {fund}: incoming capture dated "
                    f"{incoming_max.date()} is older than the stored snapshot "
                    f"{stored_max.date()} — refused")
            old = old[~old.index.isin(incoming_dates)]  # replace same-day snapshot
            merged = pd.concat([_with_capture_columns(old), incoming]).sort_index()
        else:
            merged = incoming
        order = ([c for c in merged.columns if c not in CAPTURE_COLUMNS]
                 + list(CAPTURE_COLUMNS))
        merged = merged.reindex(columns=order)
        merged.to_parquet(p)
        # PIT history archiver: append-mode dated store for dispersion analysis.
        # Columns: as_of (date), etf (str), ticker, name, weight_pct, rank.
        # Idempotent per (as_of, etf): same-day re-runs drop the old rows first.
        # The archived rows are the incoming capture's OWN rows: the merged
        # file's max date IS the incoming capture's date (a regressive capture
        # was refused above), so the archive can never carry an older
        # capture's identity.
        self._append_history(fund, merged.loc[[incoming_max]])

    def _append_history(self, fund: str, snap: pd.DataFrame) -> None:
        """Append today's snapshot for *fund* to data/sector_holdings/history.parquet.

        Idempotent: if a row for (as_of, etf) already exists it is replaced, not
        duplicated.  ``snap`` carries the per-holding rows indexed by as_of date.

        The archive's schema is FIXED at six columns (as_of, etf, ticker, name,
        weight_pct, rank): the capture block belongs to the per-fund store, and
        copying it here would widen a published archive for every snapshot ever
        taken.
        """
        d = config.data_dir() / self.group
        as_of = snap.index[0].date()
        source = snap.reset_index(drop=True)
        missing = [c for c in HISTORY_COLUMNS[2:] if c not in source.columns]
        if missing:
            raise ValueError("sector holdings history row is missing column(s): "
                             + ", ".join(missing))
        rows = source[list(HISTORY_COLUMNS[2:])].copy()
        rows.insert(0, "as_of", as_of)
        rows.insert(1, "etf", fund)
        hist_path = d / "history.parquet"
        if hist_path.exists():
            old = pd.read_parquet(hist_path)
            extra = [c for c in old.columns if c not in HISTORY_COLUMNS]
            if extra:
                log.warning("sector_holdings history: dropping unexpected column(s): %s",
                            ", ".join(extra))
            old = old[list(HISTORY_COLUMNS)].copy()
            old["as_of"] = pd.to_datetime(old["as_of"]).dt.date
            # Drop rows for same (as_of, etf) to ensure idempotency
            mask = ~((old["as_of"] == as_of) & (old["etf"] == fund))
            old = old[mask]
            rows = pd.concat([old, rows], ignore_index=True)
        rows["as_of"] = pd.to_datetime(rows["as_of"])
        rows = rows.sort_values(["as_of", "etf", "rank"]).reset_index(drop=True)
        rows.to_parquet(hist_path, index=False)

    def _fetch_workbook(self, fund: str) -> bytes:
        """One incumbent HTTP/retry owner for legacy and explicit acquisition."""
        r = self.http_get(SSGA_XLSX.format(fund=fund.lower()), retries=3, timeout=60,
                          headers={"User-Agent": "Mozilla/5.0 (research)"})
        return r.content

    def _fetch_fund(self, fund: str) -> pd.DataFrame:
        """Live acquisition: the incumbent fetch owner plus capture provenance.

        The EXACT response body handed to the parser — the decoded XLSX
        content, not the raw wire bytes — is what a capture is identified by:
        its digest and length travel with every stored row. ONE aware-UTC
        instant is read after the response arrived, so the retrieval time and
        any fallback index date can never disagree.
        """
        content = self._fetch_workbook(fund)
        digest = hashlib.sha256(content).hexdigest()
        retrieved_at = _utc_now()
        if retrieved_at.tzinfo is None:
            raise ValueError("sector holdings capture clock must be an aware datetime")
        retrieved_at = retrieved_at.astimezone(timezone.utc)
        return _snapshot_from_workbook(
            content,
            capture={
                "capture_fund": fund,
                "capture_source_url": SSGA_XLSX.format(fund=fund.lower()),
                "capture_content_sha256": digest,
                "capture_content_bytes": len(content),
                "capture_retrieved_at": retrieved_at,
            })

    @classmethod
    def capture_from_inputs(cls, *, sponsors, evaluated_at: datetime, clock):
        """Acquire detached workbook-bound values; no config/store/history load.

        The caller supplies the captured sponsor choices and observation clock.
        Evaluation, document and observed capture times remain distinct. No
        publication time is inferred from a document date or HTTP response.
        """
        from collections.abc import Mapping
        if not isinstance(sponsors, Mapping) or not callable(clock):
            raise HoldingsCaptureError("holdings_explicit_inputs_required")
        captured_config = copy.deepcopy(dict(sponsors))
        values = captured_config.get("sector_funds")
        if (not isinstance(values, (list, tuple)) or not 0 < len(values) <= 11
                or any(type(f) is not str or re.fullmatch(r"[A-Z0-9]{1,12}", f) is None
                       for f in values) or len(set(values)) != len(values)):
            raise HoldingsCaptureError("holdings_funds_invalid")
        funds = tuple(values)
        evaluated = _holdings_instant(evaluated_at)
        from lib.market_session import market_local_date
        evaluation_day = market_local_date("US", now=evaluated)
        adapter = object.__new__(cls)  # The legacy __init__ loads ambient config.
        snapshots, evidence, workbooks = {}, {}, {}
        previous_capture = evaluated
        for fund in funds:
            raw, acquisition_error = None, None
            try:
                raw = adapter._fetch_workbook(fund)
            except Exception as exc:  # Existing HTTP owner has exhausted its retries.
                acquisition_error = exc
            captured_at = _holdings_instant(clock())
            if captured_at < previous_capture:
                raise HoldingsCaptureError("holdings_capture_clock_regressed")
            previous_capture = captured_at
            fact = {
                "origin": SSGA_XLSX.format(fund=fund.lower()),
                "evaluated_at": evaluated.isoformat(),
                "captured_at": captured_at.isoformat(),
                "published_at": None,
                "document_date": None, "sha256": None, "byte_length": None,
            }
            snapshots[fund], workbooks[fund] = None, None
            if acquisition_error is not None:
                response = getattr(acquisition_error, "response", None)
                fact.update(
                    outcome="absent" if getattr(response, "status_code", None) == 404
                    else "unreadable",
                    reason="http_" + type(acquisition_error).__name__)
            else:
                try:
                    if type(raw) is not bytes or not 0 < len(raw) <= MAX_HOLDINGS_WORKBOOK_BYTES:
                        raise HoldingsCaptureError("holdings_workbook_encoded_bound")
                    workbooks[fund] = raw
                    fact.update(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw))
                    day_limit = min(evaluation_day, market_local_date("US", now=captured_at))
                    snap = _snapshot_from_workbook(raw, strict_day=day_limit)
                    snapshots[fund] = snap.copy(deep=True)
                    fact.update(outcome="present", reason=None,
                                document_date=snap.index[0].date().isoformat())
                except HoldingsCaptureError as exc:
                    fact.update(outcome="malformed", reason=str(exc))
            evidence[fund] = fact
        return SectorHoldingsCapture(
            evaluated, previous_capture, snapshots, evidence, workbooks)


MAX_HOLDINGS_WORKBOOK_BYTES = 8 * 1024 * 1024
MAX_HOLDINGS_XML_BYTES = 32 * 1024 * 1024
MAX_HOLDINGS_ZIP_MEMBERS = 256
MAX_HOLDINGS_ROWS = 10000
MAX_HOLDINGS_COLUMNS = 64
MAX_HOLDINGS_CELLS = 200000


class HoldingsCaptureError(ValueError):
    """An explicit capture cannot establish a bounded, dated holdings value."""


@dataclass(frozen=True)
class SectorHoldingsCapture:
    evaluated_at: datetime
    captured_at: datetime
    _snapshots: dict
    _evidence: dict
    _workbooks: dict

    @property
    def snapshots(self) -> dict:
        return {fund: None if frame is None else frame.copy(deep=True)
                for fund, frame in self._snapshots.items()}

    @property
    def evidence(self) -> dict:
        return copy.deepcopy(self._evidence)

    @property
    def workbooks(self) -> dict:
        return dict(self._workbooks)  # Byte values are immutable.

    @property
    def available(self) -> bool:
        return any(frame is not None for frame in self._snapshots.values())

    def assembly_arguments(self) -> dict:
        return {"holdings": self.snapshots, "holdings_evidence": self.evidence}


def _holdings_instant(value) -> datetime:
    if not isinstance(value, datetime):
        raise HoldingsCaptureError("holdings_aware_instant_required")
    try:
        if value.tzinfo is None or value.utcoffset() is None or pd.isna(value):
            raise ValueError
        return value.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        raise HoldingsCaptureError("holdings_aware_instant_required") from None


def _bounded_holdings_workbook(content: bytes) -> None:
    """Bound the XLSX envelope and worksheet geometry before the real parser."""
    import zipfile
    import xml.etree.ElementTree as ET
    from pathlib import PurePosixPath

    def coordinate(value):
        match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", value)
        if match is None:
            raise HoldingsCaptureError("holdings_workbook_geometry_invalid")
        column = 0
        for letter in match[1]:
            column = column * 26 + ord(letter) - ord("A") + 1
        if column > MAX_HOLDINGS_COLUMNS or int(match[2]) > MAX_HOLDINGS_ROWS:
            raise HoldingsCaptureError("holdings_workbook_geometry_bound")

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if (not 0 < len(members) <= MAX_HOLDINGS_ZIP_MEMBERS
                    or len({m.filename for m in members}) != len(members)
                    or sum(m.file_size for m in members) > MAX_HOLDINGS_XML_BYTES):
                raise HoldingsCaptureError("holdings_workbook_archive_bound")
            cells = 0
            for member in members:
                name = member.filename
                if (member.flag_bits & 1 or name.startswith("/") or "\\" in name
                        or ".." in PurePosixPath(name).parts):
                    raise HoldingsCaptureError("holdings_workbook_archive_invalid")
                with archive.open(member) as stream:
                    raw = stream.read(MAX_HOLDINGS_XML_BYTES + 1)
                if len(raw) != member.file_size or len(raw) > MAX_HOLDINGS_XML_BYTES:
                    raise HoldingsCaptureError("holdings_workbook_archive_bound")
                if name.endswith((".xml", ".rels")):
                    upper = raw.upper()
                    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
                        raise HoldingsCaptureError("holdings_workbook_xml_invalid")
                if not (name.startswith("xl/worksheets/") and name.endswith(".xml")):
                    continue
                for event, element in ET.iterparse(io.BytesIO(raw), events=("start", "end")):
                    if event == "end":
                        element.clear()
                        continue
                    tag = element.tag.rsplit("}", 1)[-1]
                    if tag == "dimension":
                        for endpoint in element.attrib.get("ref", "").split(":"):
                            coordinate(endpoint)
                    elif tag == "row":
                        number = element.attrib.get("r", "")
                        if not number.isdigit() or not 0 < int(number) <= MAX_HOLDINGS_ROWS:
                            raise HoldingsCaptureError("holdings_workbook_geometry_bound")
                    elif tag == "c":
                        coordinate(element.attrib.get("r", ""))
                        cells += 1
                        if cells > MAX_HOLDINGS_CELLS:
                            raise HoldingsCaptureError("holdings_workbook_cell_bound")
    except HoldingsCaptureError:
        raise
    except Exception:
        raise HoldingsCaptureError("holdings_workbook_invalid") from None


def _complete_holdings_date(value: str) -> date:
    """Require all calendar components; never infer a current year/month/day."""
    value = " ".join(value.split())
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y",
                "%d-%b-%Y", "%d-%B-%Y", "%d %b %Y", "%d %B %Y",
                "%b %d %Y", "%B %d %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise HoldingsCaptureError("holdings_document_date_invalid")


def _snapshot_from_workbook(content, *, strict_day: date | None = None,
                            capture: dict | None = None) -> pd.DataFrame:
    """Shared original transform, with strict capture validation around it.

    ``strict_day`` (explicit-inputs acquisition) validates the workbook
    envelope, geometry, identities and the issuer's document date against the
    evaluation day. ``capture`` (live acquisition provenance) carries the
    response identity — url/digest/bytes/retrieved-at — of one live fetch; the
    snapshot's index date then comes from the issuer's own as-of claim,
    refused when malformed or conflicting, or from the labelled retrieval
    fallback, and every row is stamped with the reserved capture block.
    """
    strict = strict_day is not None
    if strict:
        _bounded_holdings_workbook(content)
    try:
        # 'NA' is a real ticker; only genuinely blank cells are missing.
        options = {"nrows": MAX_HOLDINGS_ROWS} if strict else {}
        raw = pd.read_excel(io.BytesIO(content), header=None,
                            keep_default_na=False, na_values=[""], **options)
        if strict and (raw.empty or raw.shape[1] < 2
                       or raw.shape[1] > MAX_HOLDINGS_COLUMNS):
            raise HoldingsCaptureError("holdings_workbook_shape_invalid")
        hdr_idx = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "Name"]
        if not len(hdr_idx):
            raise ValueError("holdings header row not found")
        if strict and len(hdr_idx) != 1:
            raise HoldingsCaptureError("holdings_header_ambiguous")
        issuer_as_of = None
        date_origin = None
        asof = None if (strict or capture is not None) else str(date.today())
        if capture is not None:
            # A stated issuer date is admitted only when it is unambiguous and
            # valid; a malformed or conflicting one refuses the capture before
            # anything is written (see _issuer_as_of).
            issuer_as_of = _issuer_as_of(raw, int(hdr_idx[0]))
            retrieved_at = capture["capture_retrieved_at"]
            if issuer_as_of is None:
                # No issuer date stated: the index date is the retrieval date,
                # deterministically at midnight, and it is LABELLED as a
                # retrieval fallback so it is never read as an issuer-effective
                # date.
                asof = str(retrieved_at.date())
                date_origin = DATE_ORIGIN_RETRIEVAL_FALLBACK
            else:
                asof = str(issuer_as_of)
                date_origin = DATE_ORIGIN_ISSUER_REPORTED
        else:
            dates = []
            for i in range(hdr_idx[0]):
                cell = str(raw.iloc[i, 1])
                if "As of" in cell:
                    date_text = cell.replace("As of", "").strip()
                    parsed = (pd.Timestamp(_complete_holdings_date(date_text)) if strict
                              else pd.to_datetime(date_text))
                    asof = str(parsed.date())
                    dates.append(parsed.date())
            if strict:
                if not dates:
                    raise HoldingsCaptureError("holdings_document_date_missing")
                if len(dates) != 1:
                    raise HoldingsCaptureError("holdings_document_date_ambiguous")
                if dates[0] > strict_day:
                    raise HoldingsCaptureError("holdings_document_date_future")
        df = raw.iloc[hdr_idx[0] + 1:].copy()
        columns = [str(c).strip().lower().replace(" ", "_") for c in raw.iloc[hdr_idx[0]]]
        if strict and (len([c for c in columns if "weight" in c]) != 1
                       or columns.count("ticker") != 1 or columns.count("name") != 1
                       or len(set(c for c in columns if c != "nan")) != len([c for c in columns if c != "nan"])):
            raise HoldingsCaptureError("holdings_columns_ambiguous")
        df.columns = columns
        df = df.rename(columns={"weight": "weight_pct"})
        wcol = next((c for c in df.columns if "weight" in c), None)
        if wcol is None or "ticker" not in df.columns:
            raise ValueError(f"unexpected columns: {list(df.columns)[:6]}")
        if strict:
            members = df[df["ticker"].notna() & (df["ticker"] != "-")]
            identities = []
            for _, row in members.iterrows():
                ticker = row["ticker"]
                if type(ticker) is not str or not 0 < len(ticker.strip()) <= 32 or ticker.strip() == "-":
                    raise HoldingsCaptureError("holdings_identity_invalid")
                identities.append(ticker.strip())
                weight = row[wcol]
                try:
                    number = pd.to_numeric(weight, errors="raise")
                    if isinstance(weight, bool) or not math.isfinite(float(number)) or not 0 <= float(number) <= 100:
                        raise ValueError
                except (TypeError, ValueError, OverflowError):
                    raise HoldingsCaptureError("holdings_weight_invalid") from None
            if len(set(identities)) != len(identities):
                raise HoldingsCaptureError("holdings_identity_duplicate")
        df["weight_pct"] = pd.to_numeric(df[wcol], errors="coerce")
        df = (df.dropna(subset=["weight_pct", "ticker"])
                .query("ticker != '-'")
                .nlargest(TOP_N, "weight_pct"))
        out = pd.DataFrame({
            "ticker": df["ticker"].astype(str).str.strip(),
            "name": df["name"].astype(str).str.strip() if "name" in df.columns else "",
            "weight_pct": df["weight_pct"].round(2),
            "rank": range(1, len(df) + 1),
        })
        out.index = pd.to_datetime([asof] * len(out))
        if strict and out.empty:
            raise HoldingsCaptureError("holdings_snapshot_empty")
        if capture is not None:
            # The same capture block on EVERY incoming row, so each row is
            # self-describing and no separate artifact can drift away from it.
            block = {
                "capture_schema_version": CAPTURE_SCHEMA_VERSION,
                "capture_fund": capture["capture_fund"],
                "capture_source_url": capture["capture_source_url"],
                "capture_content_sha256": capture["capture_content_sha256"],
                "capture_content_bytes": int(capture["capture_content_bytes"]),
                "capture_retrieved_at": capture["capture_retrieved_at"].isoformat(),
                "capture_issuer_as_of": (issuer_as_of.isoformat()
                                         if issuer_as_of is not None else None),
                "capture_date_origin": date_origin,
            }
            for column, value in block.items():
                out[column] = value
        return out
    except HoldingsCaptureError:
        raise
    except Exception:
        if strict:
            raise HoldingsCaptureError("holdings_workbook_parse_failed") from None
        raise


def top10_union() -> list[str]:
    """Union of current top-N holdings tickers across all sectors (price feed).
    (Name kept for back-compat; returns the top-``TOP_N`` union, not just 10.)"""
    d = config.data_dir() / "sector_holdings"
    if not d.exists():
        return []
    tickers: set[str] = set()
    for p in d.glob("*.parquet"):
        df = pd.read_parquet(p)
        if "ticker" not in df.columns or df.empty:
            continue
        df.index = pd.to_datetime(df.index)
        last_day = df.index.max()
        tickers |= set(df.loc[[last_day], "ticker"].astype(str))
    # yahoo notation: BRK.B -> BRK-B
    return sorted(t.replace(".", "-") for t in tickers if t and t != "nan")


def latest_top10(fund: str) -> pd.DataFrame | None:
    df = store.read("sector_holdings", fund)
    if df is None or df.empty:
        return None
    return df.loc[[df.index.max()]].sort_values("rank")


_DEEP_MIN_ROWS = 250  # below this a "healthy" file is a throttled seed stub, not history

# A period='1mo' refresh reaches ~30 calendar days back; a store frozen longer than
# this has no window overlap left to bridge and would strand an interior hole rather
# than heal it — route to period='max' instead. 21 gives the cheap window margin
# under its own ~30-day reach (SATS class: 46 days frozen at the 2026-08-03
# adjudication — see _fetch_universe below for the incident this pairs with).
_MAX_WINDOW_BRIDGE_DAYS = 21


def _dead_tickers() -> frozenset[str]:
    """Ticker set from the dead-name price store (data/edgar/dead_name_prices.parquet,
    long format — see engine/grading.py::load_dead_prices for the same shape/path).
    Absent/unreadable/column-missing degrades to frozenset(): the dead-name registry is
    a CI-collected side artifact, not always present in every checkout, and a name this
    can't classify simply isn't excluded from anything — the retention union in
    _fetch_universe fails safe toward FETCHING, never toward silently dropping a name."""
    p = config.data_dir() / "edgar" / "dead_name_prices.parquet"
    try:
        # columns=["ticker"] alone (~100x cheaper than a full read — the store carries
        # date/close/source too); a missing 'ticker' column raises here as well and
        # lands in the same except, so the column-missing contract is unchanged.
        df = pd.read_parquet(p, columns=["ticker"])
    except Exception as e:  # noqa: BLE001 — absent/corrupt/column-missing must never block retention
        log.debug("stocks: dead_name_prices unreadable (%s) — no names excluded", e)
        return frozenset()
    return frozenset(df["ticker"].astype(str))


def _fetch_universe(current: list[str], stored: list[str], dead: frozenset[str]) -> list[str]:
    """The retention fetch set: today's top-N union PLUS every ticker still on disk
    under data/stocks, minus names confirmed dead.

    2026-08-03 adjudication: top10_union() ALONE regressed a ticker's fetch the moment
    it fell out of every sector SPDR's top-20 — and scripts/build_stock_library.py's
    universe() keeps preferring the frozen deep store over fresher breadth caches, so
    nothing downstream ever noticed the parquet stopped advancing. Measured receipts:
    QCOM (XLK rank 20, exited 2026-07-09) froze at 2026-07-10; HOOD (XLF r20,
    2026-07-09) froze at 07-10; MRVL (XLK r18, 2026-07-10) froze at 07-13; CVNA (XLY
    r19, 2026-07-16) froze at 07-17; WDC (XLK r20, 2026-07-23) froze at 07-24; HON
    (XLI, exited 06-26) froze at 07-17, that tip itself an artifact of the 07-19
    one-shot basis heal (#3096) — 10 to 46 days frozen apiece, forever, with nothing
    watching. A name must keep being fetched for as long as it is still on disk,
    dead-registry names excepted.

    A dead-registry name that is STILL in the current union is fetched anyway — the
    union side always wins. Ticker symbols get reused across unrelated companies over
    time, and refusing to fetch a live top-N holding because an unrelated past company
    once traded under the same string would be a worse defect than the one this
    function exists to fix.

    `dead` must include the exit ledger (lib.delisted_symbols), not just the EDGAR
    dead-name registry — fetch() passes the union of both. The AVB incident
    (2026-08-22 nightly) is why: AvalonBay delisted 2026-08-17 (acquisition), but the
    retention side kept requesting the symbol, and Yahoo had spliced it into the
    acquirer's CONTINUING series — auto_adjust folded the merger exchange ratio
    (×2.793) into every historical bar, the 1mo window disagreed with the stored
    basis, `store.basis_shifted` routed it to a period='max' re-pull, and that
    re-pull rewrote the entire 1994-2026 file onto the successor's basis plus live
    post-delisting successor bars. A delisted feed is not merely useless — it can
    answer with a DIFFERENT instrument's tape, and the basis-rebase path then
    imports it wholesale."""
    return sorted(set(current) | (set(stored) - dead))


def _report_delisted_exclusions(current: list[str], stored: list[str],
                                exited: frozenset[str]) -> list[str]:
    """Disclose the retained-on-disk names excluded from tonight's fetch by their
    config/delisted_symbols.yml exit row (R4 never-silent collectors — the
    collectors/yahoo.py::_report_delisted_exclusions idiom for this lane). A name
    still in TODAY's union is not excluded (union wins, see _fetch_universe) and so
    is not reported here. Bare ::notice at line start (annotation law)."""
    dropped = sorted((set(stored) - set(current)) & exited)
    if dropped:
        rows = delisted_symbols.ledger()
        detail = ", ".join(
            f"{t}(last session {rows.get(t, {}).get('last_session', '?')})"
            for t in dropped[:15])
        more = len(dropped) - min(len(dropped), 15)
        print(f"::notice title=stocks collector delisted::{len(dropped)} symbol(s) not "
              f"requested (exit rows in config/delisted_symbols.yml; a delisted feed "
              f"can return a merger successor's spliced tape — the AVB 2026-08 class): "
              f"{detail}{f', +{more} more' if more > 0 else ''}", flush=True)
    return dropped


def _report_missing_symbols(requested: list[str], returned, current) -> list[str]:
    """Requested-vs-returned reconciliation for one StockPriceAdapter.fetch() run —
    the collectors/yahoo.py::_report_missing_symbols idiom applied to the data/stocks
    lane (R4 never-silent collectors,
    research/ADJUDICATION_20260803_UNIVERSE_SIDE_STORE_FRESHNESS.md §3 chip (1)).

    `_pull()` drops a requested-but-unreturned ticker through a log-only
    `except KeyError`, and the ONLY aggregate backstop is fetch()'s 0.7 floor — so up
    to 30% of the fetch set can return nothing on a given night with no per-name trace
    anywhere in the Actions summary (a logger-prefixed line is not an annotation; see
    the annotation law and tests/test_gh_annotation_line_start.py). _fetch_universe's
    retention makes that hole WIDER, not narrower: the fetch set now carries every
    name still on disk, so without this the store-tip audit's stale_live flag is the
    only thing that would ever notice — one whole night later, and without the reason.

    The union/retained SPLIT is the actionable part, and it is the one thing the yahoo
    lane has no need of. A ticker in TODAY's top-N union that returns nothing is a live
    provider failure against a name the desk is actively holding. A RETAINED ticker
    (still on disk, already out of the union) that returns nothing is the
    delisted-or-renamed candidate set — #4616's law is that delisted is not stale, and
    the exit path for those names is the dead-name registry / the #4622 symbol
    resolution protocol (a rename is a KEY MIGRATION), never an in-place refetch.
    Naming the two apart is what lets the next reader route them correctly instead of
    re-diagnosing the whole list from scratch.

    Bare ::warning at line start (annotation law — never through the logger); returns
    the missing list so a caller/test can assert on it without re-parsing the text."""
    have = set(returned)
    missing = [t for t in requested if t not in have]
    if missing:
        union = set(current)
        n_union = sum(1 for t in missing if t in union)
        n_retained = len(missing) - n_union
        shown = missing[:15]
        more = len(missing) - len(shown)
        print(f"::warning title=stocks collector missing symbols::{len(missing)} of "
              f"{len(requested)} requested ticker(s) returned no data ({n_union} in "
              f"today's top-N union, {n_retained} retained off-union — "
              f"delisted/renamed candidates): {', '.join(shown)}"
              f"{f', +{more} more' if more > 0 else ''}", flush=True)
    return missing


class StockPriceAdapter(Adapter):
    """Daily closes for the union of top-N holdings (cycle engine fuel)."""

    name = "stock_prices"
    group = "stocks"
    overwrite_overlap = True  # yfinance auto_adjust=True → seam-free re-adjust of the refresh window

    def session_calendar_for_series(self, name: str) -> str | None:
        # Holdings may include foreign shares; use the same cash routing as Yahoo.
        from lib.market_session import cash_market_for_symbol
        return cash_market_for_symbol(name)

    def __init__(self) -> None:
        self.ycfg = config.load()["yahoo"]

    def stored_series(self) -> list[str]:
        """Every ticker currently on disk under data/stocks — the retention side of
        _fetch_universe (a name the union has dropped must keep appearing here for
        its store to keep advancing; see _fetch_universe's docstring for the
        incident). Do not hoist the leading-underscore filter into the base Adapter:
        data/intl legitimately stores ^-sanitized stems (_N225, _FTSE) that
        IntlPriceAdapter's base stored_series() must keep returning."""
        d = config.data_dir() / self.group
        if not d.exists():
            return []
        return sorted(p.stem for p in d.glob("*.parquet") if not p.stem.startswith("_"))

    def _needs_full(self, ticker: str, today: pd.Timestamp | None = None) -> bool:
        """A ticker needs a full-history re-fetch when its stored file is missing
        volume for a meaningful share of rows (volume was added to this adapter
        after the price history was first seeded) OR is too shallow to be real
        history — a throttled period='max' seed pull can leave a ~40-row stub that
        a volume-share check alone calls healthy forever (CBRE/ISRG/KMI/MLM,
        2026-05 class) OR has a stored tip older than _MAX_WINDOW_BRIDGE_DAYS calendar
        days — a name _fetch_universe kept in the fetch set after it dropped out of
        top10_union() (or one that simply missed several nights) needs period='max',
        not the cheap period='1mo' window, once the freeze is old enough that the
        window can no longer reach back to the last stored bar (SATS class, 46 days
        frozen at the 2026-08-03 adjudication). Self-heals all three; once deep,
        volume-complete, and current the ticker falls back to the cheap daily window.
        `today` is test-injected; defaults to the current ET calendar date (matches
        scripts/audit_stocks_freshness.py's lag anchor). The tip is parsed
        defensively (NaT / tz-aware index both degrade to True, never a raise) because
        this is called from a bare list comprehension in fetch() with no per-ticker
        try/except — one corrupt stored file must never kill the run for every other
        ticker."""
        old = store.read("stocks", ticker)
        if old is None or old.empty or "volume" not in old.columns:
            return True
        if len(old) < _DEEP_MIN_ROWS:
            return True
        if float(old["volume"].notna().mean()) < 0.95:
            return True
        today = (pd.Timestamp(today).normalize() if today is not None
                 else pd.Timestamp(datetime.now(nyse_calendar.ET).date()))
        tip = pd.Timestamp(old.index.max())
        if pd.isna(tip):
            return True
        if tip.tzinfo is not None:
            tip = tip.tz_localize(None)
        return bool((today - tip.normalize()).days > _MAX_WINDOW_BRIDGE_DAYS)

    def _download(self, batch: list[str], period: str) -> pd.DataFrame:
        import yfinance as yf
        last_exc: Exception | None = None
        for attempt in range(self.ycfg["retries"]):
            try:
                return yf.download(batch, period=period, auto_adjust=True,
                                   progress=False, group_by="ticker", threads=True)
            except Exception as e:  # noqa: BLE001
                last_exc = e
                if attempt < self.ycfg["retries"] - 1:
                    time.sleep(self.ycfg["backoff_base_s"] * (2 ** attempt))
        raise last_exc  # type: ignore[misc]

    def _pull(self, period: str, tlist: list[str], frames: dict[str, pd.DataFrame],
              rebase: list[str] | None, tol: float) -> None:
        """Batched download into *frames*. When *rebase* is a list (the cheap 1mo
        window), a ticker whose window disagrees with its stored closes on the
        overlap dates (store.basis_shifted) was re-adjusted by Yahoo since the last
        pull — an ex-div/split/spin-off re-bases the WHOLE series, so splicing the
        window would strand every pre-window row on the stale basis. The window is
        queued for a period='max' re-pull instead (measured 2026-07: 30/231 stored
        names off basis this way; worst a 5.7% spin-off factor = a fabricated
        -7.8% one-day step inside live 126-bar indicator windows)."""
        for i in range(0, len(tlist), self.ycfg["batch_size"]):
            batch = tlist[i:i + self.ycfg["batch_size"]]
            if not batch:
                continue
            df = self._download(batch, period)
            for t in batch:
                try:
                    cols = [c for c in ["Close", "High", "Low", "Volume"] if c in df[t].columns]
                    sub = df[t][cols].rename(columns={"Close": "close", "High": "high",
                                                      "Low": "low", "Volume": "volume"})
                    sub = sub.dropna(subset=["close"])
                except KeyError:
                    log.warning("stocks: no data for %s", t)
                    continue
                if sub.empty:
                    continue
                if rebase is not None and store.basis_shifted(self.group, t, sub, tol=tol):
                    rebase.append(t)  # discard the window; re-pull full history below
                    continue
                frames[t] = sub

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        current = top10_union()
        if not current:
            raise RuntimeError("no holdings stored yet — run sector_holdings first")
        # Retention: keep fetching every name still on disk even after it exits the
        # top-N union (see _fetch_universe's docstring — the 2026-08-03 freeze
        # incident), minus exit-ledger + dead-registry names (the AVB 2026-08
        # successor-splice incident — same docstring).
        stored = self.stored_series()
        exited = delisted_symbols.tickers()
        tickers = _fetch_universe(current, stored, _dead_tickers() | exited)
        _report_delisted_exclusions(current, stored, exited)
        # daily runs fetch a short window, EXCEPT thin-volume/shallow/stale-tip
        # tickers which get a full-history backfill so a bad seed (or a frozen tip
        # older than the window can bridge) can never silently persist.
        if full_history:
            groups = [("max", tickers)]
        else:
            heal = [t for t in tickers if self._needs_full(t)]
            groups = [("1mo", [t for t in tickers if t not in heal])]
            if heal:
                log.info("stocks: full-history backfill for %d thin/shallow/stale tickers", len(heal))
                groups.append(("max", heal))
        frames: dict[str, pd.DataFrame] = {}
        rebase: list[str] = []
        tol = float(self.ycfg.get("upsert_basis_tol", 1e-3))
        for period, tlist in groups:
            self._pull(period, tlist, frames, rebase if period == "1mo" else None, tol)
        if rebase:
            log.info("stocks: %d name(s) on a re-adjusted basis — refetching "
                     "period='max': %s", len(rebase), rebase[:12])
            try:
                self._pull("max", rebase, frames, None, tol)
            except Exception as e:  # noqa: BLE001 — skip tonight; the guard re-flags next run
                log.warning("stocks: basis refetch failed for %d name(s) (%s) — "
                            "kept out of this run", len(rebase), e)
        # Never-silent: disclose the per-name requested-vs-returned gap BEFORE the
        # aggregate floor decides whether to raise — a run that dies on the floor is
        # exactly the run whose per-name detail is worth having, and a run that
        # survives it can still be hiding up to 30% silent drops.
        _report_missing_symbols(tickers, frames, current)
        if len(frames) < len(tickers) * 0.7:
            raise RuntimeError(f"stocks: only {len(frames)}/{len(tickers)} returned")
        return frames


class StockFundamentalsAdapter(Adapter):
    """Best-effort valuation/quality snapshot per holding. Weekly cadence,
    LOW CONFIDENCE (unofficial yfinance fields, often missing)."""

    name = "stock_fundamentals"
    group = "stock_fundamentals"
    stale_after_days = 12

    FIELDS = {"forwardPE": "fwd_pe", "trailingPE": "pe",
              "profitMargins": "profit_margin", "revenueGrowth": "rev_growth",
              "returnOnEquity": "roe", "dividendYield": "div_yield",
              "marketCap": "mkt_cap"}

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        import yfinance as yf
        tickers = top10_union()
        if not tickers:
            raise RuntimeError("no holdings stored yet")
        rows = []
        today = pd.Timestamp(date.today())
        for t in tickers:
            rec: dict = {"ticker": t}
            try:
                info = yf.Ticker(t).info or {}
                for src, dst in self.FIELDS.items():
                    rec[dst] = info.get(src)
                time.sleep(0.2)
            except Exception as e:  # noqa: BLE001
                log.debug("fundamentals %s: %s", t, e)
            rows.append(rec)
        df = pd.DataFrame(rows).set_index("ticker")
        if df.drop(columns=["mkt_cap"], errors="ignore").notna().sum().sum() < len(tickers):
            log.warning("fundamentals very sparse this run")
        wide = df.unstack().to_frame().T
        wide.index = [today]
        wide.columns = [f"{t}__{f}" for f, t in wide.columns]
        return {"snapshots": wide}


def latest_fundamentals(ticker: str) -> dict:
    df = store.read("stock_fundamentals", "snapshots")
    if df is None or df.empty:
        return {}
    row = df.iloc[-1]
    out = {}
    for col, v in row.items():
        t, _, f = str(col).partition("__")
        if t == ticker and pd.notna(v):
            out[f] = v
    return out
