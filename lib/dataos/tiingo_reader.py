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
        redistribution_admitted=manifest.get("redistribution_admitted") is True,
        rows=tuple(rows),
    )
