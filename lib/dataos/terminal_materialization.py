"""Pure Data OS binding for Terminal's directly observed Yahoo daily output.

This leaf deliberately imports no package, engine, filesystem or network code.
The existing adapter supplies the canonical VendorAliasTable reader, listing
parser and exact reference/source evidence. It performs no identity allocation.

The leaf has no clock and no I/O. ``encode_terminal_rows`` and
``terminal_rows_sha256`` import and operate without tzdata. The adapter
records the actual current ``read_at`` of the two reference files and detects
a changed pair during one snapshot; this leaf passes that instant through
verbatim. No reference publication-generation clock or upstream freshness is
available here. The leaf rejects missing or malformed reference inputs and
never derives an age. See ``research/TERMINAL_YAHOO_MATERIALIZATION_2026-10-19.md``.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from collections.abc import Mapping
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

API_VERSION = "dataos.terminal_yahoo_materialization.v1"
ROW_CODEC = "dataos.terminal_ohlc.rows.v1"
OUTPUT_DATASET = "terminal.bars.daily.ohlc_json"
PRODUCER_PATH = "ingest/build_polygon_universe.py"
OWNER_PATH = "lib/dataos/terminal_materialization.py"
IDENTITY_PATH = "lib/dataos/identity.py"
PRODUCER_FILES = (PRODUCER_PATH, "ingest/polygon_bars.py", "ingest/session_anchor.py",
                  "ingest/dataos_materialization.py")
REFERENCE_FILES = ("security_master.parquet", "vendor_aliases.parquet")
VENUES = ("ARCX", "XASE", "XNAS", "XNYS")
MAX_ROWS = 30_000
MAX_SAFE_INTEGER = 2**53 - 1
_SHA = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,19}$")


def _new_york():
    """Resolve America/New_York on demand.

    The encode/hash helpers and import itself do not require tzdata; only this
    call needs the system catalog. A missing or empty catalog surfaces as
    ``None`` so the binder can produce typed ``MATERIALIZATION_CLOCK_INVALID``
    rather than letting ``ZoneInfoNotFoundError`` escape. Real NY/DST semantics
    are preserved when the catalog is present.
    """
    try:
        return ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:
        return None


class MaterializationRefusal(ValueError):
    """A closed source or content condition that cannot fund this binding."""


def _require(condition, code):
    if not condition:
        raise MaterializationRefusal(code)


def _day(value):
    _require(type(value) is str and len(value) == 10, "MATERIALIZATION_ROWS_INVALID")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise MaterializationRefusal("MATERIALIZATION_ROWS_INVALID") from None
    _require(parsed.isoformat() == value, "MATERIALIZATION_ROWS_INVALID")
    return parsed


def _instant(value):
    _require(type(value) is str and len(value) <= 40, "MATERIALIZATION_CLOCK_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise MaterializationRefusal("MATERIALIZATION_CLOCK_INVALID") from None
    _require("T" in value and parsed.tzinfo is not None
             and parsed.utcoffset() is not None, "MATERIALIZATION_CLOCK_INVALID")
    return parsed


def encode_terminal_rows(rows) -> bytes:
    """Normative codec: prefix + uint32 count + (ISO date + 5 binary64 BE) rows.

    Numeric values, including integral-looking floats, have one encoding across
    Python and JavaScript. Volume -0 normalizes to +0. No sorting/coercion occurs.
    The bytes describe normalized values, never original vendor response bytes.
    """
    _require(type(rows) is list and 0 < len(rows) <= MAX_ROWS,
             "MATERIALIZATION_ROWS_INVALID")
    out = bytearray((ROW_CODEC + "\n").encode("ascii"))
    out.extend(struct.pack(">I", len(rows)))
    previous = ""
    for row in rows:
        _require(type(row) is list and len(row) == 6, "MATERIALIZATION_ROWS_INVALID")
        _day(row[0])
        _require(row[0] > previous, "MATERIALIZATION_ROWS_INVALID")
        previous = row[0]
        for value in row[1:]:
            _require(type(value) in (int, float), "MATERIALIZATION_ROWS_INVALID")
            try:
                _require(math.isfinite(value), "MATERIALIZATION_ROWS_INVALID")
            except OverflowError:
                raise MaterializationRefusal("MATERIALIZATION_ROWS_INVALID") from None
        o, h, lo, c, volume = row[1:]
        _require(min(o, h, lo, c) > 0 and h >= max(o, c) and lo <= min(o, c),
                 "MATERIALIZATION_ROWS_INVALID")
        _require(0 <= volume <= MAX_SAFE_INTEGER and int(volume) == volume,
                 "MATERIALIZATION_ROWS_INVALID")
        out.extend(row[0].encode("ascii"))
        out.extend(struct.pack(">5d", o, h, lo, c, 0.0 if volume == 0 else volume))
    return bytes(out)


def terminal_rows_sha256(rows) -> str:
    return hashlib.sha256(encode_terminal_rows(rows)).hexdigest()


def _version(value, repository, expected_paths):
    _require(isinstance(value, Mapping) and value.get("repository") == repository,
             "MATERIALIZATION_CODE_UNATTESTED")
    files = value.get("files_sha256")
    _require(isinstance(files, Mapping) and set(files) == set(expected_paths)
             and all(type(v) is str and _SHA.fullmatch(v) for v in files.values()),
             "MATERIALIZATION_CODE_UNATTESTED")
    commit = value.get("commit")
    _require(commit is None or (type(commit) is str and re.fullmatch(r"[0-9a-f]{40}", commit)),
             "MATERIALIZATION_CODE_UNATTESTED")
    # Only strings enter this JSON digest; there is no cross-runtime float rule.
    normalized = {k: files[k] for k in sorted(files)}
    digest = hashlib.sha256(json.dumps(normalized, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()
    return {"repository": repository, "commit": commit, "files_sha256": normalized,
            "code_version": "sha256:" + digest}


def _reference(value):
    _require(isinstance(value, Mapping), "MATERIALIZATION_REFERENCE_UNAVAILABLE")
    files = value.get("files_sha256")
    _require(isinstance(files, Mapping) and set(files) == set(REFERENCE_FILES)
             and all(type(v) is str and _SHA.fullmatch(v) for v in files.values()),
             "MATERIALIZATION_REFERENCE_UNAVAILABLE")
    _instant(value.get("read_at"))
    # The adapter's current pair is not an attested identity publication generation.
    _require(value.get("generation_attested") is False and value.get("generation_id") is None,
             "MATERIALIZATION_REFERENCE_UNAVAILABLE")
    return {"files_sha256": {k: files[k] for k in REFERENCE_FILES},
            "read_at": value["read_at"], "generation_id": None,
            "generation_attested": False, "historical_availability": "UNATTESTED"}


def bind_terminal_yahoo_materialization(document, *, alias_table, master_records,
                                       parse_listing_key, producer_version,
                                       owner_version, reference, reused=False) -> dict:
    """Return a bound view or typed refusal; never sample time, read or publish.

    alias_table and parse_listing_key are the existing identity owner's reader
    and parser, loaded by the file adapter. CURRENT catalog lookup uses store
    for the output and yahoo_fetch for the request, on the observed venue day.
    No input Boolean, source-name heuristic or prior view qualifies an output.
    """
    try:
        _require(reused is False and isinstance(document, Mapping)
                 and document.get("view") is None, "MATERIALIZATION_REUSE_NOT_FRESH")
        symbol = document.get("t")
        _require(type(symbol) is str and _SYMBOL.fullmatch(symbol),
                 "MATERIALIZATION_IDENTITY_UNRESOLVED")
        observation = document.get("source_observation")
        _require(isinstance(observation, Mapping)
                 and observation.get("producer") == PRODUCER_PATH
                 and observation.get("provider") == "yahoo"
                 and observation.get("qualification") == "OBSERVATION_ONLY"
                 and observation.get("historical_availability") == "UNATTESTED",
                 "MATERIALIZATION_OBSERVATION_ABSENT")
        request = observation.get("request")
        _require(document.get("src") == "yahoo"
                 and document.get("bar_quality") == "real_ohlc"
                 and isinstance(request, Mapping) and request.get("adapter") == "yfinance"
                 and request.get("period") == "max" and request.get("interval") == "1d"
                 and request.get("auto_adjust") is True
                 and request.get("session_dates") == "exchange_local"
                 and request.get("index_timezone") == "America/New_York",
                 "MATERIALIZATION_SOURCE_UNSUPPORTED")
        requested = request.get("symbol")
        _require(type(requested) is str and _SYMBOL.fullmatch(requested),
                 "MATERIALIZATION_IDENTITY_UNRESOLVED")
        adapter = observation.get("adapter_version")
        _require(type(adapter) is str and 0 < len(adapter) <= 100,
                 "MATERIALIZATION_SOURCE_UNSUPPORTED")
        observed = _instant(observation.get("observed_at"))
        ny = _new_york()
        _require(ny is not None, "MATERIALIZATION_CLOCK_INVALID")
        on = observed.astimezone(ny).date()
        rows = document.get("bars")
        digest = terminal_rows_sha256(rows)
        coverage = {"first": rows[0][0], "last": rows[-1][0], "rows": len(rows)}
        _require(_day(rows[-1][0]) <= on, "MATERIALIZATION_CLOCK_INVALID")
        _require(observation.get("coverage") == coverage
                 and observation.get("digest_codec") == "python.json.compact.v1"
                 and observation.get("bars_sha256") == hashlib.sha256(
                     json.dumps(rows, separators=(",", ":"), allow_nan=False).encode()).hexdigest(),
                 "MATERIALIZATION_OBSERVATION_MISMATCH")
        try:
            stored_id = alias_table.resolve("store", symbol, on)
            requested_id = alias_table.resolve("yahoo_fetch", requested, on)
        except (ValueError, TypeError, AttributeError):
            raise MaterializationRefusal("MATERIALIZATION_IDENTITY_UNRESOLVED") from None
        _require(stored_id is not None and requested_id is not None,
                 "MATERIALIZATION_IDENTITY_UNRESOLVED")
        _require(stored_id == requested_id, "MATERIALIZATION_IDENTITY_MISMATCH")
        _require(type(master_records) is list, "MATERIALIZATION_REFERENCE_UNAVAILABLE")
        matches = [row for row in master_records if isinstance(row, Mapping)
                   and row.get("security_id") == stored_id
                   and row.get("superseded_by") is None]
        _require(len(matches) == 1, "MATERIALIZATION_LISTING_AMBIGUOUS")
        row = matches[0]
        try:
            listing = parse_listing_key(row.get("listing_key"))
            listing_country = listing.country
            listing_mic = listing.mic
        except (ValueError, TypeError, AttributeError):
            raise MaterializationRefusal("MATERIALIZATION_IDENTITY_UNRESOLVED") from None
        _require(row.get("country") == "US" and listing_country == "US"
                 and row.get("mic") in VENUES and listing_mic == row.get("mic"),
                 "VENUE_OUT_OF_SCOPE")
        producer = _version(producer_version, "mastermindx-market-intelligence/mastermind-terminal",
                            PRODUCER_FILES)
        owner = _version(owner_version, "mastermindx-market-intelligence/macro",
                         (OWNER_PATH, IDENTITY_PATH))
        identity_reference = _reference(reference)
        materialization = {
            "schema": API_VERSION, "symbol": symbol, "requested_symbol": requested,
            "source": "yahoo", "alias_namespace": "yahoo_fetch",
            "row_codec": ROW_CODEC, "bars_sha256": digest, "coverage": coverage,
            "observation_bars_sha256": observation["bars_sha256"],
            "observed_at": observation["observed_at"], "request": dict(request),
            "adapter_version": adapter, "producer": producer, "owner": owner,
            "identity_reference": identity_reference,
            "historical_availability": "UNATTESTED", "reused": False,
        }
        contract = {
            "schema": "dataos.view_contract.v1", "purpose": "terminal_daily_ohlc",
            "identity_namespace": "US-<MIC>-<CODE>[.N]", "venues": list(VENUES),
            "field_units": {"currency": "USD", "open": "USD/share", "high": "USD/share",
                            "low": "USD/share", "close": "USD/share", "volume": "shares",
                            "volume_convention": "vendor-reported, unattested", "share_basis": "tradj"},
            "adjustment_reference": {"basis": "tradj", "action_revision_set_id": None,
                                     "as_at": None, "vintage": "unattested", "executable": False,
                                     "readout": "vendor total-return proxy — not a printed price"},
            "evidence_mode": {"mode": "CURRENT", "clock": "observed_at", "registry_row": None,
                              "output_registry_row": OUTPUT_DATASET, "dependency_generation_ids": [],
                              "generation_attested": False, "code_version": owner["code_version"]},
            "coverage": coverage, "store_vendor": "yahoo", "materialization": materialization,
        }
        view = {
            "schema": "terminal.ohlc_view.v1", "contract": contract,
            "listing": {"mic": row["mic"], "listing_key": row["listing_key"],
                        "security_id": stored_id},
            "segments": [{"from": rows[0][0], "to": rows[-1][0], "src": "yahoo",
                          "bar_quality": "real_ohlc"}],
            "basis_drift": None, "suspected_breaks": [], "refusal_reasons": [],
        }
        return {"status": "bound", "view": view, "refusal_reasons": []}
    except MaterializationRefusal as exc:
        return {"status": "refused", "view": None, "refusal_reasons": [str(exc)]}
