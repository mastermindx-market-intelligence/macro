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
import io
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from collectors.tiingo_archive import (DEFAULT_ARCHIVE, SOURCES, TiingoArchiveError,
    require_external_root, validate_receipt, receipt_identity)
from scripts.tiingo_materialize import BoundedTiingoRead, verified_raw
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
    source_observation_clock_contract: str | None = None

    def metadata(self) -> dict[str, Any]:
        result = {
            "source": self.source, "source_sha256": self.source_sha256,
            "source_observed_at_utc": self.source_observed_at_utc,
            "purpose": self.purpose,
            "pit_backtest_eligible": self.pit_backtest_eligible,
            "redistribution_admitted": self.redistribution_admitted,
            "authority": self.authority, "row_count": len(self.rows),
        }
        if self.source_observation_clock_contract is not None:
            result["source_observation_clock_contract"] = self.source_observation_clock_contract
        return result


def _hashed_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _unique_raw_context(base: Path, source: str, day: str, digest: str, *, receipt_id: str | None = None,
                        receipt_path: Path | None = None,
                        read_context: BoundedTiingoRead | None = None) -> dict[str, Any]:
    """Quarantine v1 content-key collisions; do not repair or rewrite source data.

    The current producer uses content-only output names. Until that producer is
    repaired, a reader must refuse identical bytes claimed by multiple contexts.
    This consumer safeguard is intentionally not a new receipt/identity authority.
    """
    parent = base / "receipts" / source / day
    contexts: dict[tuple[Any, ...], dict[str, Any]] = {}
    matching = 0
    if read_context is not None:
        if receipt_path is None or receipt_id is None or not SHA.fullmatch(receipt_id):
            raise TiingoViewRefusal("bounded acquisition requires an exact receipt path and identity")
        if read_context.relative(Path(receipt_path).parent) != read_context.relative(parent):
            raise TiingoViewRefusal("receipt hint is outside the selected source day")
        files = [Path(receipt_path)]
    elif receipt_path is not None:
        # A hint is valid only for an exact content-addressed receipt selection.
        # It cannot narrow a raw-digest query and hide conflicting contexts.
        if receipt_id is None or not SHA.fullmatch(receipt_id):
            raise TiingoViewRefusal("receipt path requires exact receipt identity")
        if (receipt_path.is_symlink() or receipt_path.parent.resolve() != parent.resolve()
                or not receipt_path.is_file()):
            raise TiingoViewRefusal("receipt hint is outside the selected source day")
        files = [receipt_path]
    else:
        files = list(parent.glob(f"*{digest[:24]}*.json"))
        if not files:
            # Exact receipt IDs can also select a retained legacy content path.
            files = parent.glob("*.json")
    for file in files:
        if read_context is None:
            if not file.resolve().is_relative_to(base.resolve()) or file.stat().st_size > 1_000_000:
                raise TiingoViewRefusal("source receipt escapes bounded archive evidence")
        try:
            record = (read_context.read_metadata(read_context.relative(file))
                      if read_context is not None else json.loads(file.read_text()))
        except (ValueError, OSError) as exc:
            raise TiingoViewRefusal("unreadable source context receipt") from exc
        if not isinstance(record, dict):
            raise TiingoViewRefusal("invalid source context receipt")
        identity = receipt_identity(record)
        if record.get("raw_sha256") != digest and identity != digest:
            continue
        if receipt_id is not None and identity != receipt_id:
            continue
        matching += 1
        if matching > 2048:
            raise TiingoViewRefusal("too many candidate source contexts")
        try:
            validate_receipt(record)
        except (TiingoArchiveError, TypeError, ValueError, KeyError) as exc:
            raise TiingoViewRefusal("source receipt identity/context mismatch") from exc
        receipt_source = record.get("source", "boats-firehose")
        if record.get("vendor") != "tiingo" or receipt_source != source:
            raise TiingoViewRefusal("source receipt vendor/family mismatch")
        clock = record.get("observed_at_utc") or record.get("first_received_at_utc")
        key = (receipt_source, record.get("symbol"), record.get("request_path"), clock)
        contexts[key] = record
    if not contexts:
        raise TiingoViewRefusal("source view lacks artifact-bound raw-context evidence")
    if len(contexts) != 1:
        raise TiingoViewRefusal("ambiguous raw contexts; upstream archive repair required")
    return next(iter(contexts.values()))


def read_research_view(source: str, day: str, sha256: str, *,
                       root: Path = DEFAULT_ARCHIVE,
                       purpose: str = "INSPECTION",
                       acknowledge_hindsight: bool = False,
                       max_rows: int = 20_000,
                       check_mount: bool = True,
                       receipt_path: Path | None = None,
                       read_context: BoundedTiingoRead | None = None) -> TiingoView:
    if source not in SOURCES and source != "boats-firehose":
        raise TiingoViewRefusal("unsupported vendor source ID")
    try:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("noncanonical date")
    except ValueError as exc:
        raise TiingoViewRefusal("invalid observation day") from exc
    if not SHA.fullmatch(sha256):
        raise TiingoViewRefusal("invalid source digest")
    if (purpose not in PURPOSES
            or (read_context is not None and type(max_rows) is not int)
            or max_rows < 1 or max_rows > 1_000_000):
        raise TiingoViewRefusal("invalid reader purpose or cap")
    base = (read_context.assert_root(root, check_mount=check_mount)
            if read_context is not None else require_external_root(root, check_mount=check_mount))
    lookup_digest, selected_receipt = sha256, None
    direct_manifest = base / "manifests" / source / day / (sha256 + ".json")
    direct = None
    if read_context is not None:
        direct = read_context.read_metadata(read_context.relative(direct_manifest), missing_ok=True)
        direct_exists = direct is not None
    else:
        if direct_manifest.is_symlink() or not direct_manifest.resolve().is_relative_to(base.resolve()):
            raise TiingoViewRefusal("research source view path is not confined to the archive")
        direct_exists = direct_manifest.is_file()
        if direct_exists:
            try:
                direct = json.loads(direct_manifest.read_text())
            except (OSError, ValueError) as exc:
                raise TiingoViewRefusal("invalid source manifest") from exc
    if direct_exists:
        if isinstance(direct, dict) and direct.get("source_receipt_id") == sha256:
            lookup_digest, selected_receipt = direct.get("source_sha256"), sha256
            if not isinstance(lookup_digest, str) or not SHA.fullmatch(lookup_digest):
                raise TiingoViewRefusal("source view content/manifest integrity mismatch")
    if receipt_path is not None:
        # With a hint, the public selector is always the exact receipt ID.
        selected_receipt = sha256
    context = _unique_raw_context(base, source, day, lookup_digest,
                                  receipt_id=selected_receipt, receipt_path=receipt_path,
                                  read_context=read_context)
    identity = receipt_identity(context)
    raw_digest = context["raw_sha256"]
    artifact_id = sha256
    if (not direct_exists if read_context is not None
            else not (base / "manifests" / source / day / (artifact_id + ".json")).is_file()):
        # An exact receipt may select a retained unambiguous legacy content path.
        artifact_id = raw_digest if sha256 == identity else identity
    rel = Path(source) / day / (artifact_id + ".parquet")
    path = base / "normalized" / rel
    manifest_file = base / "manifests" / rel.with_suffix(".json")
    # A locally editable manifest/hash is not sufficient if a symlink can
    # redirect a research read onto another filesystem or escaped directory.
    normalized_bytes = None
    if read_context is not None:
        try:
            manifest = (direct if direct_exists and artifact_id == sha256 else
                        read_context.read_metadata(read_context.relative(manifest_file)))
            normalized_bytes = read_context.read_normalized(read_context.relative(path))
        except FileNotFoundError as exc:
            raise TiingoViewRefusal("source view lacks artifact-bound evidence") from exc
    else:
        base_real = base.resolve()
        if (manifest_file.is_symlink() or path.is_symlink()
                or not manifest_file.resolve().is_relative_to(base_real)
                or not path.resolve().is_relative_to(base_real)):
            raise TiingoViewRefusal("research source view path is not confined to the archive")
        if not manifest_file.exists() or not path.is_file():
            raise TiingoViewRefusal("source view lacks artifact-bound evidence")
        try:
            manifest = json.loads(manifest_file.read_text())
        except (ValueError, OSError) as exc:
            raise TiingoViewRefusal("invalid source manifest") from exc
    if not isinstance(manifest, dict) or manifest.get("view_schema") != SCHEMA_VERSION:
        raise TiingoViewRefusal("unsupported research view schema; read-only refusal, no migration")
    expected = (Path("normalized") / rel).as_posix()
    if source == "boats-firehose":
        from lib.dataos.temporal import utc
        try:
            if utc(context["last_received_at_utc"]) < utc(context["first_received_at_utc"]):
                raise ValueError("inverted source interval")
        except (ValueError, TypeError, KeyError) as exc:
            raise TiingoViewRefusal("BOATS source receipt bounds invalid") from exc
        try:
            body = (verified_raw(base, context, read_context=read_context)
                    if read_context is not None else verified_raw(base, context))
        except (TiingoArchiveError, OSError, ValueError, EOFError) as exc:
            raise TiingoViewRefusal("BOATS source raw integrity invalid") from exc
        counts = context.get("counts")
        if (not isinstance(counts, dict)
                or any(type(v) is not int or v < 0 for v in counts.values())
                or sum(counts.values()) != len(body.splitlines())):
            raise TiingoViewRefusal("BOATS source raw line count differs from receipt")
    legacy = "source_receipt_id" not in manifest and "receipt_id" not in context
    if (manifest.get("source_sha256") != raw_digest
            or (not legacy and manifest.get("source_receipt_id") != identity)
            or manifest.get("output_path") != expected
            or manifest.get("output_sha256") != (
                hashlib.sha256(normalized_bytes).hexdigest() if read_context is not None
                else _hashed_file(path))
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
    # The original raw receipt must STILL resolve to byte-identical source
    # evidence. A valid Parquet/manifest pair cannot hide corrupted raw gzip.
    # This invokes only the already-existing bounded, read-only verifier;
    # nothing is reconstructed, repaired, fetched, or written to the lake.
    try:
        source_body = (verified_raw(base, context, read_context=read_context)
                       if read_context is not None else verified_raw(base, context))
        length = context.get("raw_bytes")
        if type(length) is not int or length != len(source_body):
            raise TiingoViewRefusal("source raw receipt byte-length mismatch")
    except (TiingoArchiveError, OSError, ValueError, KeyError, TypeError, EOFError) as exc:
        raise TiingoViewRefusal("source raw byte integrity could not be verified") from exc
    pf = pq.ParquetFile(io.BytesIO(normalized_bytes) if read_context is not None else path)
    if read_context is not None:
        metadata = pf.metadata
        file_rows = metadata.num_rows
        if type(file_rows) is not int or file_rows < 0:
            raise TiingoViewRefusal("strict Parquet file row count is invalid")
        if file_rows > max_rows:
            raise TiingoViewRefusal("row cap exceeded: partition is not bounded for reader")
        group_count = metadata.num_row_groups
        if type(group_count) is not int or group_count < 0:
            raise TiingoViewRefusal("strict Parquet row-group count is invalid")
        group_rows = 0
        for index in range(group_count):
            count = metadata.row_group(index).num_rows
            if type(count) is not int or count < 0:
                raise TiingoViewRefusal("strict Parquet row-group row count is invalid")
            group_rows += count
            if group_rows > max_rows:
                raise TiingoViewRefusal("row cap exceeded: Parquet row groups exceed reader allowance")
        if group_rows != file_rows:
            raise TiingoViewRefusal("strict Parquet file and row-group row counts disagree")
        # Bound declared rows before decoding, then recheck the decoded table
        # before conversion to Python rows. Neither check bounds decoded bytes/RSS.
        table = pf.read()
        table_rows = table.num_rows
        if (type(table_rows) is not int or table_rows < 0
                or table_rows > max_rows or table_rows != file_rows):
            raise TiingoViewRefusal("strict Parquet decoded row count is inconsistent or over cap")
        rows = table.to_pylist()
    else:
        if pf.metadata.num_rows > max_rows:
            raise TiingoViewRefusal("row cap exceeded: partition is not bounded for reader")
        rows = pf.read().to_pylist()
    observed = context.get("observed_at_utc") or context.get("first_received_at_utc")
    if (len(rows) != manifest.get("rows")
            or manifest.get("source_observed_at_utc") != observed
            or any(row.get("source_sha256") != raw_digest
                   or (legacy and "source_receipt_id" in row)
                   or (not legacy and row.get("source_receipt_id") != identity)
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
        source=source, source_sha256=raw_digest,
        source_observed_at_utc=manifest.get("source_observed_at_utc"),
        purpose=purpose, pit_backtest_eligible=pit,
        redistribution_admitted=False,
        rows=tuple(rows),
        source_request_path=context.get("request_path"),
        source_observation_clock_contract=context.get("observation_clock_contract"),
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
                    "source_sha256", "source_receipt_id", "source_observed_at_utc", "adjustment_asof_utc"
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
                    "source_sha256", "source_receipt_id", "source_observed_at_utc",
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


def read_research_statement_comparison(
    vendor_symbol: str,
    as_reported_ref: tuple[str, str],
    restated_ref: tuple[str, str],
    start_release_date: str,
    end_release_date: str,
    observed_before_utc: str,
    *,
    root: Path = DEFAULT_ARCHIVE,
    acknowledge_hindsight: bool = False,
    max_rows: int = 100_000,
    check_mount: bool = True,
) -> dict[str, Any]:
    """Compare two exact statement captures without selecting a revision winner.

    Fiscal period/section/metric alignment is a research comparison of vendor
    values, not canonical identity, common publication time or a proven
    restatement event. Multiple release claims stay unpaired, and both original
    rows retain their source receipts, capture clocks and vendor release labels.
    Neither missing metrics nor release-label changes imply when a change occurred.
    """
    sides = {}
    for name, ref, dimension in (
        ("as_reported", as_reported_ref, True),
        ("restated", restated_ref, False),
    ):
        sides[name] = read_research_statement_timeline(
            vendor_symbol, [ref], start_release_date, end_release_date,
            observed_before_utc, as_reported=dimension, root=root,
            acknowledge_hindsight=acknowledge_hindsight, max_partitions=1,
            max_rows=max_rows, check_mount=check_mount,
        )
    indexed: dict[str, dict[tuple[int, int, str, str], list[dict[str, Any]]]] = {}
    for name, timeline in sides.items():
        groups: dict[tuple[int, int, str, str], list[dict[str, Any]]] = {}
        for row in timeline.rows:
            key = (row["fiscal_year"], row["fiscal_quarter"],
                   row["statement_type"], row["metric_code"])
            groups.setdefault(key, []).append(row)
        indexed[name] = groups
    keys = sorted(indexed["as_reported"].keys() | indexed["restated"].keys())
    if len(keys) > max_rows:
        raise TiingoViewRefusal("statement comparison row cap exceeded")
    counts = {status: 0 for status in (
        "SAME_VENDOR_VALUE", "DIFFERENT_VENDOR_VALUE",
        "ONLY_IN_AS_REPORTED_CAPTURE", "ONLY_IN_RESTATED_CAPTURE",
        "AMBIGUOUS_RELEASES", "VENDOR_IDENTITY_CONFLICT",
    )}
    rows = []
    for year, quarter, family, code in keys:
        key = (year, quarter, family, code)
        left = indexed["as_reported"].get(key, [])
        right = indexed["restated"].get(key, [])
        if len(left) > 1 or len(right) > 1:
            status = "AMBIGUOUS_RELEASES"
        elif not left:
            status = "ONLY_IN_RESTATED_CAPTURE"
        elif not right:
            status = "ONLY_IN_AS_REPORTED_CAPTURE"
        elif (left[0].get("permaticker_vendor") is not None
              and right[0].get("permaticker_vendor") is not None
              and left[0]["permaticker_vendor"] != right[0]["permaticker_vendor"]):
            status = "VENDOR_IDENTITY_CONFLICT"
        else:
            status = ("SAME_VENDOR_VALUE" if left[0]["metric_value"] == right[0]["metric_value"]
                      else "DIFFERENT_VENDOR_VALUE")
        counts[status] += 1
        rows.append({
            "fiscal_year": year, "fiscal_quarter": quarter,
            "statement_type": family, "metric_code": code,
            "comparison_status": status,
            "as_reported_rows": left, "restated_rows": right,
        })
    return {
        "source": "fund-statements", "vendor_symbol": vendor_symbol,
        "comparison_basis": "VENDOR_FISCAL_PERIOD_SECTION_METRIC_VALUES",
        "as_reported": sides["as_reported"].metadata(),
        "restated": sides["restated"].metadata(),
        "capture_references": {
            name: [list(ref) for ref in timeline.source_partitions]
            for name, timeline in sides.items()
        },
        "comparison_counts": counts,
        "comparison_rows": rows,
        "release_labels_preserved": True,
        "revision_event_or_materiality_proven": False,
        "historical_known_at_proven": False,
        "historical_identity_admitted": False,
        "pit_backtest_eligible": False,
        "redistribution_admitted": False,
        "report_history_completeness_proven": False,
        "availability_clock": "SOURCE_CAPTURE_ONLY_NO_PIT",
    }
