"""Evidence-bound Tiingo research reader, subordinate to existing Data OS.

A source digest + capture date selects exactly one immutable vendor vintage.
Default purpose is INSPECTION, not a backtest or live canonical API.
RETROSPECTIVE_EXPLORATORY requires an explicit hindsight acknowledgement;
PIT_BACKTEST is always refused here; only a separately admitted canonical
Data OS reader may supply it. Local manifest flags grant no such authority.
No model/ranking/trading publication pathway is added by this module.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from collectors.tiingo_archive import DEFAULT_ARCHIVE, SOURCES, require_external_root
from lib.dataos.tiingo_views import SCHEMA_VERSION

SHA = re.compile(r"^[0-9a-f]{64}$")
PURPOSES = frozenset({"INSPECTION", "RETROSPECTIVE_EXPLORATORY", "PIT_BACKTEST"})


class TiingoViewRefusal(ValueError):
    pass


@dataclass(frozen=True)
class TiingoView:
    source: str
    source_sha256: str
    source_observed_at_utc: str | None
    purpose: str
    pit_backtest_eligible: bool
    redistribution_admitted: bool
    rows: tuple[dict[str, Any], ...]
    authority: str = "RESEARCH_ONLY_VENDOR_SOURCE"
    source_request_path: str | None = None

    def metadata(self) -> dict[str, Any]:
        return {
            "source": self.source, "source_sha256": self.source_sha256,
            "source_observed_at_utc": self.source_observed_at_utc,
            "purpose": self.purpose,
            "pit_backtest_eligible": self.pit_backtest_eligible,
            "redistribution_admitted": self.redistribution_admitted,
            "authority": self.authority, "row_count": len(self.rows),
        }


def _hashed_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _unique_raw_context(base: Path, source: str, day: str, digest: str) -> dict[str, Any]:
    """Quarantine v1 content-key collisions; do not repair or rewrite source data.

    The current producer uses content-only output names. Until that producer is
    repaired, a reader must refuse identical bytes claimed by multiple contexts.
    This consumer safeguard is intentionally not a new receipt/identity authority.
    """
    parent = base / "receipts" / source / day
    contexts: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, file in enumerate(parent.glob(f"*{digest[:24]}*.json")):
        if index >= 2048:
            raise TiingoViewRefusal("too many candidate source contexts")
        if not file.resolve().is_relative_to(base.resolve()) or file.stat().st_size > 1_000_000:
            raise TiingoViewRefusal("source receipt escapes bounded archive evidence")
        try:
            record = json.loads(file.read_text())
        except (ValueError, OSError) as exc:
            raise TiingoViewRefusal("unreadable source context receipt") from exc
        if not isinstance(record, dict) or record.get("raw_sha256") != digest:
            continue
        receipt_source = record.get("source", "boats-firehose")
        if record.get("vendor") != "tiingo" or receipt_source != source:
            raise TiingoViewRefusal("source receipt vendor/family mismatch")
        clock = record.get("observed_at_utc") or record.get("first_received_at_utc")
        key = (receipt_source, record.get("symbol"), record.get("request_path"), clock)
        contexts[key] = record
    if not contexts:
        raise TiingoViewRefusal("source view lacks raw-context evidence")
    if len(contexts) != 1:
        raise TiingoViewRefusal("ambiguous raw contexts; upstream archive repair required")
    return next(iter(contexts.values()))


def read_research_view(source: str, day: str, sha256: str, *,
                       root: Path = DEFAULT_ARCHIVE,
                       purpose: str = "INSPECTION",
                       acknowledge_hindsight: bool = False,
                       max_rows: int = 20_000,
                       check_mount: bool = True) -> TiingoView:
    if source not in SOURCES and source != "boats-firehose":
        raise TiingoViewRefusal("unsupported vendor source ID")
    try:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("noncanonical date")
    except ValueError as exc:
        raise TiingoViewRefusal("invalid observation day") from exc
    if not SHA.fullmatch(sha256):
        raise TiingoViewRefusal("invalid source digest")
    if purpose not in PURPOSES or max_rows < 1 or max_rows > 1_000_000:
        raise TiingoViewRefusal("invalid reader purpose or cap")
    base = require_external_root(root, check_mount=check_mount)
    rel = Path(source) / day / (sha256 + ".parquet")
    path = base / "normalized" / rel
    manifest_file = base / "manifests" / rel.with_suffix(".json")
    if not manifest_file.exists() or not path.is_file():
        raise TiingoViewRefusal("source view lacks artifact-bound evidence")
    try:
        manifest = json.loads(manifest_file.read_text())
    except (ValueError, OSError) as exc:
        raise TiingoViewRefusal("invalid source manifest") from exc
    if not isinstance(manifest, dict) or manifest.get("view_schema") != SCHEMA_VERSION:
        raise TiingoViewRefusal("unsupported research view schema; read-only refusal, no migration")
    expected = (Path("normalized") / rel).as_posix()
    if (manifest.get("source_sha256") != sha256
            or manifest.get("output_path") != expected
            or manifest.get("output_sha256") != _hashed_file(path)
            or manifest.get("source_vendor") != "tiingo"):
        raise TiingoViewRefusal("source view content/manifest integrity mismatch")
    # This L1 research reader is not the canonical Data OS admission owner.
    # An editable local manifest flag can NEVER grant point-in-time eligibility.
    if purpose == "PIT_BACKTEST":
        raise TiingoViewRefusal("PIT_BACKTEST cannot consume unadmitted hindsight data")
    if (manifest.get("pit_backtest_eligible") is not False
            or manifest.get("dataos_identity_admitted") is not False):
        raise TiingoViewRefusal("research manifest cannot assert canonical/PIT admission")
    # A local research manifest is never a licensing/redistribution authority.
    # The user's plan attestation must be mapped through the incumbent rights
    # owner, not an editable flag on a vendor research artifact.
    if manifest.get("redistribution_admitted") is not False:
        raise TiingoViewRefusal("local research manifest cannot grant redistribution rights")
    pit = False
    if purpose == "RETROSPECTIVE_EXPLORATORY" and not acknowledge_hindsight:
        raise TiingoViewRefusal("must acknowledge historical source availability is unknown")
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError as exc:
        raise TiingoViewRefusal("pyarrow missing") from exc
    context = _unique_raw_context(base, source, day, sha256)
    pf = pq.ParquetFile(path)
    if pf.metadata.num_rows > max_rows:
        raise TiingoViewRefusal("row cap exceeded: partition is not bounded for reader")
    rows = pf.read().to_pylist()
    observed = context.get("observed_at_utc") or context.get("first_received_at_utc")
    if (len(rows) != manifest.get("rows")
            or manifest.get("source_observed_at_utc") != observed
            or any(row.get("source_sha256") != sha256
                   or row.get("source_view_schema") != SCHEMA_VERSION
                   or row.get("source_vendor") != "tiingo"
                   or row.get("dataset_source") != source
                   or row.get("source_rights_admitted") is not False
                   or row.get("pit_backtest_eligible") is not False
                   or row.get("dataos_identity_admitted") is not False
                   or row.get("source_observed_at_utc") != observed for row in rows)):
        raise TiingoViewRefusal("view row lineage mismatch")
    symbol = context.get("symbol")
    if symbol is not None and any(
        row.get("ticker_vendor", row.get("ticker_or_permaticker_vendor")) != symbol
        for row in rows
    ):
        raise TiingoViewRefusal("view ticker disagrees with the source context")
    return TiingoView(
        source=source, source_sha256=sha256,
        source_observed_at_utc=manifest.get("source_observed_at_utc"),
        purpose=purpose, pit_backtest_eligible=pit,
        redistribution_admitted=False,
        rows=tuple(rows),
        source_request_path=context.get("request_path"),
    )


@dataclass(frozen=True)
class TiingoResearchHistory:
    """A bounded, explicitly referenced retrospective study; never PIT evidence.

    Each partition was independently read through read_research_view. Sources
    with contradictory revisions refuse the *whole* synthetic series rather
    than silently splicing corrections into a fabricated market-time vintage.
    """
    source: str
    vendor_symbol: str
    start_market_date: str
    end_market_date: str
    observed_before_utc: str
    rows: tuple[dict[str, Any], ...]
    source_partitions: tuple[tuple[str, str], ...]
    identical_overlap_dates: int
    authority: str = "RESEARCH_ONLY_RETROSPECTIVE"
    pit_backtest_eligible: bool = False
    redistribution_admitted: bool = False
    historical_identity_admitted: bool = False
    market_session_completeness_proven: bool = False

    def metadata(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "vendor_symbol": self.vendor_symbol,
            "start_market_date": self.start_market_date,
            "end_market_date": self.end_market_date,
            "observed_before_utc": self.observed_before_utc,
            "source_partitions": len(self.source_partitions),
            "rows": len(self.rows),
            "observed_market_dates": len({row["market_date"] for row in self.rows}),
            "identical_overlap_dates": self.identical_overlap_dates,
            "authority": self.authority,
            "pit_backtest_eligible": False,
            "redistribution_admitted": False,
            "historical_identity_admitted": False,
            "market_session_completeness_proven": False,
            "availability_clock": "SOURCE_CAPTURE_ONLY_NO_PIT",
        }


def read_research_history(
    source: str,
    vendor_symbol: str,
    refs: list[tuple[str, str]] | tuple[tuple[str, str], ...],
    start_market_date: str,
    end_market_date: str,
    observed_before_utc: str,
    *,
    root: Path = DEFAULT_ARCHIVE,
    acknowledge_hindsight: bool = False,
    max_partitions: int = 256,
    max_rows: int = 100_000,
    check_mount: bool = True,
) -> TiingoResearchHistory:
    """Join only caller-selected, authenticated-by-receipt research partitions.

    An observed-before cutoff limits local capture vintages. It is NOT a
    historically known-at or published-at cutoff. Refuse rather than selecting
    conflicting historical corrections or filling unknown market sessions.
    This is not a request planner, download, index, queue or new canonical API.
    """
    from lib.dataos.temporal import utc, TemporalError

    if source not in {"eod-bars", "fund-daily"}:
        raise TiingoViewRefusal("research history currently reviews only EOD or daily fundamentals")
    if not isinstance(vendor_symbol, str) or not vendor_symbol or len(vendor_symbol) > 96:
        raise TiingoViewRefusal("exact vendor symbol required for history assembly")
    if acknowledge_hindsight is not True:
        raise TiingoViewRefusal("historical lookback requires explicit hindsight acknowledgement")
    if (type(max_partitions) is not int or not 1 <= max_partitions <= 512
            or type(max_rows) is not int or not 1 <= max_rows <= 1_000_000):
        raise TiingoViewRefusal("invalid bounded history reader budget")
    if not isinstance(refs, (tuple, list)) or not 1 <= len(refs) <= max_partitions:
        raise TiingoViewRefusal("explicit bounded capture references required")
    if any(not isinstance(ref, (tuple, list)) or len(ref) != 2 for ref in refs):
        raise TiingoViewRefusal("invalid partition reference")
    if any(type(ref[0]) is not str or type(ref[1]) is not str
           or not SHA.fullmatch(ref[1]) for ref in refs):
        raise TiingoViewRefusal("invalid partition capture date/digest types")
    unique_refs = [(ref[0], ref[1]) for ref in refs]
    if len(unique_refs) != len(set(unique_refs)):
        raise TiingoViewRefusal("duplicate capture references cannot prove more data")
    try:
        begin, end = date.fromisoformat(start_market_date), date.fromisoformat(end_market_date)
        if (begin.isoformat() != start_market_date or end.isoformat() != end_market_date
                or begin > end):
            raise ValueError("noncanonical or reversed market date range")
        cutoff = utc(observed_before_utc)
    except (ValueError, TypeError, TemporalError) as exc:
        raise TiingoViewRefusal("invalid research market/capture date or timezone") from exc

    # Economically identical overlap can be de-duplicated, but two different
    # vendor vintages for the same market date must be reviewed separately.
    # No last-write-wins; no current adjusted-price series passed off as PIT.
    evidence: dict[str, tuple[str, Any, tuple[dict[str, Any], ...]]] = {}
    captures: list[tuple[Any, tuple[str, str]]] = []
    overlaps = 0
    for day, digest in unique_refs:
        view = read_research_view(
            source, day, digest, root=root,
            purpose="RETROSPECTIVE_EXPLORATORY", acknowledge_hindsight=True,
            max_rows=max_rows, check_mount=check_mount,
        )
        if not view.source_observed_at_utc:
            raise TiingoViewRefusal("capture missing a timezone-aware availability boundary")
        try:
            captured = utc(view.source_observed_at_utc)
        except (ValueError, TemporalError) as exc:
            raise TiingoViewRefusal("capture has invalid original observation time") from exc
        if captured > cutoff:
            raise TiingoViewRefusal("source capture was not observed by the requested cutoff")
        if captured.date().isoformat() != day:
            raise TiingoViewRefusal("capture day disagrees with original source observation")
        captures.append((captured, (day, digest)))
        from urllib.parse import parse_qs, urlsplit
        if not view.source_request_path:
            raise TiingoViewRefusal("missing original research request context")
        params = parse_qs(urlsplit(view.source_request_path).query, keep_blank_values=True)
        requested: dict[str, date] = {}
        for field in ("startDate", "endDate"):
            if field in params:
                values = params[field]
                if len(values) != 1:
                    raise TiingoViewRefusal("ambiguous original vendor request date bounds")
                try:
                    bound = date.fromisoformat(values[0])
                except ValueError as exc:
                    raise TiingoViewRefusal("invalid original vendor request date bounds") from exc
                if bound.isoformat() != values[0]:
                    raise TiingoViewRefusal("noncanonical original vendor request date bounds")
                requested[field] = bound
        daily: dict[str, list[dict[str, Any]]] = {}
        for row in view.rows:
            claimed = row.get(
                "ticker_vendor" if source == "eod-bars" else "ticker_or_permaticker_vendor"
            )
            if claimed != vendor_symbol:
                raise TiingoViewRefusal("history source partition disagrees with requested vendor ID")
            market_day = row.get("market_date")
            if not isinstance(market_day, str):
                raise TiingoViewRefusal("history row missing canonical vendor market date")
            try:
                market = date.fromisoformat(market_day)
            except ValueError as exc:
                raise TiingoViewRefusal("invalid market date") from exc
            if market.isoformat() != market_day or market > captured.date():
                raise TiingoViewRefusal("future or invalid market date in source capture")
            if (("startDate" in requested and market < requested["startDate"])
                    or ("endDate" in requested and market > requested["endDate"])):
                raise TiingoViewRefusal("market date outside original request window")
            if begin <= market <= end:
                daily.setdefault(market_day, []).append(row)
        for market_day, day_rows in daily.items():
            if source == "eod-bars" and len(day_rows) != 1:
                raise TiingoViewRefusal("more than one EOD bar per market date")
            if source == "fund-daily":
                codes = [r.get("metric_code") for r in day_rows]
                if any(not isinstance(k, str) or not k for k in codes) or len(codes) != len(set(codes)):
                    raise TiingoViewRefusal("ambiguous daily fundamental metric membership")
                day_rows.sort(key=lambda r: r["metric_code"])
            # Exclude only *capture-local* lineage, not changing economic values,
            # date roles, market identity, units or vendor adjustment fields.
            def economic_fields(r: dict[str, Any]) -> dict[str, Any]:
                return {k: v for k, v in r.items() if k not in {
                    "source_sha256", "source_observed_at_utc", "adjustment_asof_utc"
                }}
            try:
                signature = json.dumps(
                    [economic_fields(r) for r in day_rows],
                    sort_keys=True, separators=(",", ":"), allow_nan=False,
                )
            except (TypeError, ValueError) as exc:
                raise TiingoViewRefusal("unverified research value cannot enter longitudinal view") from exc
            previous = evidence.get(market_day)
            if previous is not None:
                if previous[0] != signature:
                    raise TiingoViewRefusal(
                        "conflicting vendor revisions for a market date; choose explicit distinct studies"
                    )
                overlaps += 1
                # When the observations agree, select the most recent *source*
                # receipt by cutoff, without claiming it existed at market time.
                if captured >= previous[1]:
                    evidence[market_day] = (signature, captured, tuple(day_rows))
            else:
                evidence[market_day] = (signature, captured, tuple(day_rows))
        if sum(len(group[2]) for group in evidence.values()) > max_rows:
            raise TiingoViewRefusal("total longitudinal research row cap exceeded")

    final_rows = tuple(
        row for day in sorted(evidence)
        for row in evidence[day][2]
    )
    return TiingoResearchHistory(
        source=source, vendor_symbol=vendor_symbol,
        start_market_date=begin.isoformat(), end_market_date=end.isoformat(),
        observed_before_utc=cutoff.isoformat(),
        rows=final_rows,
        source_partitions=tuple(ref for _, ref in sorted(captures)),
        identical_overlap_dates=overlaps,
    )


@dataclass(frozen=True)
class TiingoStatementTimeline:
    """Vendor-claimed release sequence; never an actual historical PIT ledger."""
    vendor_symbol: str
    start_release_date: str
    end_release_date: str
    observed_before_utc: str
    requested_as_reported: bool
    rows: tuple[dict[str, Any], ...]
    source_partitions: tuple[tuple[str, str], ...]
    identical_report_overlaps: int
    authority: str = "RESEARCH_ONLY_STATEMENT_RELEASE_CLAIMS"
    pit_backtest_eligible: bool = False
    redistribution_admitted: bool = False
    historical_known_at_proven: bool = False
    historical_identity_admitted: bool = False
    report_history_completeness_proven: bool = False

    def metadata(self) -> dict[str, Any]:
        periods = {(row["fiscal_year"], row["fiscal_quarter"]) for row in self.rows}
        releases = {row["statement_public_release_date_vendor"] for row in self.rows}
        return {
            "source": "fund-statements",
            "vendor_symbol": self.vendor_symbol,
            "start_release_date": self.start_release_date,
            "end_release_date": self.end_release_date,
            "observed_before_utc": self.observed_before_utc,
            "as_reported_dimension": (
                "AS_REPORTED_CURRENT_PERIOD" if self.requested_as_reported
                else "LATEST_RESTATED_RETROSPECTIVE"
            ),
            "source_partitions": len(self.source_partitions),
            "rows": len(self.rows),
            "distinct_fiscal_periods": len(periods),
            "distinct_vendor_release_labels": len(releases),
            "identical_report_overlaps": self.identical_report_overlaps,
            "authority": self.authority,
            "source_release_is_vendor_claim": True,
            "historical_known_at_proven": False,
            "historical_identity_admitted": False,
            "pit_backtest_eligible": False,
            "redistribution_admitted": False,
            "report_history_completeness_proven": False,
            "availability_clock": "SOURCE_CAPTURE_ONLY_NO_PIT",
        }


def read_research_statement_timeline(
    vendor_symbol: str,
    refs: list[tuple[str, str]] | tuple[tuple[str, str], ...],
    start_release_date: str,
    end_release_date: str,
    observed_before_utc: str,
    *,
    as_reported: bool,
    root: Path = DEFAULT_ARCHIVE,
    acknowledge_hindsight: bool = False,
    max_partitions: int = 256,
    max_rows: int = 100_000,
    check_mount: bool = True,
) -> TiingoStatementTimeline:
    """Compose exact fund-statement receipts without fabricating filing availability.

    Tiingo's asReported=true is the current period as reported, versus
    asReported=false being later revised Most-Recent. Neither supplies a
    proven original known-at clock; no report is admitted to a PIT backtest.
    Report vintages with different public-release labels remain distinct.
    Same release/fiscal-period observations with different values or metric
    membership are *refused*, not silently overwritten or synthesized.
    """
    from urllib.parse import parse_qs, urlsplit
    from lib.dataos.temporal import utc, TemporalError
    from lib.dataos.tiingo_views import _date as vendor_date

    if not isinstance(vendor_symbol, str) or not vendor_symbol or len(vendor_symbol) > 96:
        raise TiingoViewRefusal("exact vendor symbol required for statement timeline")
    if type(as_reported) is not bool:
        raise TiingoViewRefusal("choose explicit as-reported or restated statement dimension")
    if acknowledge_hindsight is not True:
        raise TiingoViewRefusal("statement timeline requires hindsight acknowledgement")
    if (type(max_partitions) is not int or not 1 <= max_partitions <= 512
            or type(max_rows) is not int or not 1 <= max_rows <= 1_000_000):
        raise TiingoViewRefusal("invalid statement timeline budget")
    if (not isinstance(refs, (tuple, list)) or not 1 <= len(refs) <= max_partitions
            or any(not isinstance(ref, (tuple, list)) or len(ref) != 2 for ref in refs)):
        raise TiingoViewRefusal("explicit bounded statement capture references required")
    if any(type(ref[0]) is not str or type(ref[1]) is not str
           or not SHA.fullmatch(ref[1]) for ref in refs):
        raise TiingoViewRefusal("invalid statement capture reference types")
    refs_checked = [(ref[0], ref[1]) for ref in refs]
    if len(refs_checked) != len(set(refs_checked)):
        raise TiingoViewRefusal("duplicate statement capture references")
    try:
        begin, end = date.fromisoformat(start_release_date), date.fromisoformat(end_release_date)
        if (begin.isoformat() != start_release_date or end.isoformat() != end_release_date
                or begin > end):
            raise ValueError("invalid requested vendor release window")
        cutoff = utc(observed_before_utc)
    except (TypeError, ValueError, TemporalError) as exc:
        raise TiingoViewRefusal("invalid vendor release date or source cutoff") from exc

    groups: dict[tuple[str, int, int, str], tuple[str, Any, tuple[dict[str, Any], ...]]] = {}
    capture_refs: list[tuple[Any, tuple[str, str]]] = []
    identical_overlaps = 0
    for day, digest in refs_checked:
        view = read_research_view(
            "fund-statements", day, digest, root=root,
            purpose="RETROSPECTIVE_EXPLORATORY", acknowledge_hindsight=True,
            max_rows=max_rows, check_mount=check_mount,
        )
        try:
            if not view.source_observed_at_utc:
                raise ValueError("missing source capture")
            captured = utc(view.source_observed_at_utc)
        except (TypeError, ValueError, TemporalError) as exc:
            raise TiingoViewRefusal("original statement capture clock unavailable") from exc
        if captured > cutoff:
            raise TiingoViewRefusal("statement capture after requested observation cutoff")
        if captured.date().isoformat() != day:
            raise TiingoViewRefusal("statement capture day disagrees with source receipt")
        if not view.source_request_path:
            raise TiingoViewRefusal("missing statement source request context")
        query = parse_qs(urlsplit(view.source_request_path).query, keep_blank_values=True)
        if query.get("asReported") != ["true" if as_reported else "false"]:
            raise TiingoViewRefusal("cannot mix unknown/as-reported/restated vendor dimensions")
        request_bounds: dict[str, date] = {}
        for field in ("startDate", "endDate"):
            if field in query:
                values = query[field]
                if len(values) != 1:
                    raise TiingoViewRefusal("ambiguous original statement date filter")
                try:
                    bound = date.fromisoformat(values[0])
                except ValueError as exc:
                    raise TiingoViewRefusal("invalid original statement date filter") from exc
                if bound.isoformat() != values[0]:
                    raise TiingoViewRefusal("noncanonical original statement date filter")
                request_bounds[field] = bound
        capture_refs.append((captured, (day, digest)))

        selected: dict[tuple[str, int, int, str], list[dict[str, Any]]] = {}
        for row in view.rows:
            if (row.get("ticker_or_permaticker_vendor") != vendor_symbol
                    or row.get("requested_as_reported") is not as_reported
                    or row.get("statement_public_release_is_vendor_claim") is not True
                    or row.get("actual_upstream_available_at_utc") is not None):
                raise TiingoViewRefusal("statement row identity, variant or PIT availability claim differs")
            released_text = row.get("statement_public_release_date_vendor")
            try:
                released_date = date.fromisoformat(vendor_date(released_text))
            except (ValueError, TypeError) as exc:
                raise TiingoViewRefusal("invalid claimed statement public-release date") from exc
            if released_date > captured.date():
                raise TiingoViewRefusal("future statement release date in source capture")
            if (("startDate" in request_bounds and released_date < request_bounds["startDate"])
                    or ("endDate" in request_bounds and released_date > request_bounds["endDate"])):
                raise TiingoViewRefusal("statement date outside original vendor request window")
            year, quarter = row.get("fiscal_year"), row.get("fiscal_quarter")
            family, code = row.get("statement_type"), row.get("metric_code")
            if (type(year) is not int or type(quarter) is not int
                    or not 1 <= year <= 9999 or not 0 <= quarter <= 4
                    or not isinstance(family, str) or not family
                    or not isinstance(code, str) or not code):
                raise TiingoViewRefusal("ambiguous statement fiscal period or metric identity")
            if begin <= released_date <= end:
                selected.setdefault((released_text, year, quarter, family), []).append(row)

        for key, report_rows in selected.items():
            codes = [row["metric_code"] for row in report_rows]
            if len(codes) != len(set(codes)):
                raise TiingoViewRefusal("duplicate metric inside the same release/fiscal statement")
            report_rows.sort(key=lambda r: r["metric_code"])
            def economic_fields(row: dict[str, Any]) -> dict[str, Any]:
                return {k: v for k, v in row.items() if k not in {
                    "source_sha256", "source_observed_at_utc",
                    "source_vintage_observed_at_utc",
                }}
            try:
                signature = json.dumps(
                    [economic_fields(r) for r in report_rows],
                    sort_keys=True, separators=(",", ":"), allow_nan=False,
                )
            except (TypeError, ValueError) as exc:
                raise TiingoViewRefusal("unverifiable statement value") from exc
            previous = groups.get(key)
            if previous is not None:
                if previous[0] != signature:
                    raise TiingoViewRefusal(
                        "conflicting statement vintages for the same vendor release and fiscal period"
                    )
                identical_overlaps += 1
                if captured >= previous[1]:
                    groups[key] = (signature, captured, tuple(report_rows))
            else:
                groups[key] = (signature, captured, tuple(report_rows))
        if sum(len(report[2]) for report in groups.values()) > max_rows:
            raise TiingoViewRefusal("total retrospective statement row cap exceeded")

    return TiingoStatementTimeline(
        vendor_symbol=vendor_symbol,
        start_release_date=begin.isoformat(), end_release_date=end.isoformat(),
        observed_before_utc=cutoff.isoformat(),
        requested_as_reported=as_reported,
        rows=tuple(row for key in sorted(groups) for row in groups[key][2]),
        source_partitions=tuple(ref for _, ref in sorted(capture_refs)),
        identical_report_overlaps=identical_overlaps,
    )
