"""Pure Data OS binding for Terminal's directly observed Yahoo daily output.

This leaf deliberately imports no package, engine, filesystem or network code.
The existing adapter supplies the canonical VendorAliasTable reader, listing
parser and exact reference/source evidence. It performs no identity allocation.

The leaf has no clock and no I/O. ``encode_terminal_rows`` and
``terminal_rows_sha256`` import and operate without tzdata. The adapter
records the actual current ``read_at`` of the stock pair or SPY triplet and
detects changed files during one snapshot; this leaf passes that instant through
verbatim. No reference publication-generation clock or upstream freshness is
available here. The separate SPY profile requires complete retained catalog
evidence and an explicit current materialization cutoff; it admits no store alias. The leaf rejects missing or malformed reference inputs and
never derives an age. See ``research/TERMINAL_YAHOO_MATERIALIZATION_2026-10-19.md``.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from collections.abc import Mapping
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

API_VERSION = "dataos.terminal_yahoo_materialization.v1"
SPY_API_VERSION = "dataos.terminal_spy_yahoo_materialization.v1"
ROW_CODEC = "dataos.terminal_ohlc.rows.v1"
OUTPUT_DATASET = "terminal.bars.daily.ohlc_json"
PRODUCER_PATH = "ingest/build_polygon_universe.py"
OWNER_PATH = "lib/dataos/terminal_materialization.py"
IDENTITY_PATH = "lib/dataos/identity.py"
SPY_HELPER_PATH = "lib/dataos/_spy_yahoo_catalog.py"
PRODUCER_FILES = (PRODUCER_PATH, "ingest/polygon_bars.py", "ingest/session_anchor.py",
                  "ingest/dataos_materialization.py")
REFERENCE_FILES = ("security_master.parquet", "vendor_aliases.parquet")
SPY_REFERENCE_FILES = (*REFERENCE_FILES, "_receipt.json")
VENUES = ("ARCX", "XASE", "XNAS", "XNYS")
MAX_ROWS = 30_000
MAX_SAFE_INTEGER = 2**53 - 1
_SHA = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,19}$")
_STRICT_INSTANT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})")


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


def _reference(value, *, expected_files=REFERENCE_FILES, instant_parser=_instant):
    _require(isinstance(value, Mapping), "MATERIALIZATION_REFERENCE_UNAVAILABLE")
    files = value.get("files_sha256")
    _require(isinstance(files, Mapping) and set(files) == set(expected_files)
             and all(type(v) is str and _SHA.fullmatch(v) for v in files.values()),
             "MATERIALIZATION_REFERENCE_UNAVAILABLE")
    instant_parser(value.get("read_at"))
    # The adapter's current snapshot is not an attested identity publication generation.
    _require(value.get("generation_attested") is False and value.get("generation_id") is None,
             "MATERIALIZATION_REFERENCE_UNAVAILABLE")
    return {"files_sha256": {k: files[k] for k in expected_files},
            "read_at": value["read_at"], "generation_id": None,
            "generation_attested": False, "historical_availability": "UNATTESTED"}


def _strict_instant(value):
    """SPY critical clocks cannot silently discard sub-microsecond precision."""
    _require(type(value) is str and _STRICT_INSTANT.fullmatch(value),
             "MATERIALIZATION_CLOCK_INVALID")
    return _instant(value)


def _observation(document, *, reused, instant_parser):
    """Shared unchanged request/content qualification and observed NY bar ceiling."""
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
    observed = instant_parser(observation.get("observed_at"))
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
    return {"symbol": symbol, "requested": requested, "observation": observation,
            "request": request, "adapter": adapter, "observed": observed, "on": on,
            "rows": rows, "digest": digest, "coverage": coverage}


def _listing_record(master_records, security_id, parse_listing_key):
    """Use the existing canonical records and listing parser without allocation."""
    _require(type(master_records) is list, "MATERIALIZATION_REFERENCE_UNAVAILABLE")
    matches = [row for row in master_records if isinstance(row, Mapping)
               and row.get("security_id") == security_id
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
    return row


def _bound_view(inputs, security_id, row, *, producer, owner, identity_reference,
                schema, evidence_clock):
    """One view construction; callers must finish their distinct identity profiles."""
    symbol, requested = inputs["symbol"], inputs["requested"]
    observation, request = inputs["observation"], inputs["request"]
    adapter, digest = inputs["adapter"], inputs["digest"]
    rows, coverage = inputs["rows"], inputs["coverage"]
    materialization = {
        "schema": schema, "symbol": symbol, "requested_symbol": requested,
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
        "evidence_mode": {"mode": "CURRENT", "clock": evidence_clock, "registry_row": None,
                          "output_registry_row": OUTPUT_DATASET, "dependency_generation_ids": [],
                          "generation_attested": False, "code_version": owner["code_version"]},
        "coverage": coverage, "store_vendor": "yahoo", "materialization": materialization,
    }
    view = {
        "schema": "terminal.ohlc_view.v1", "contract": contract,
        "listing": {"mic": row["mic"], "listing_key": row["listing_key"],
                    "security_id": security_id},
        "segments": [{"from": rows[0][0], "to": rows[-1][0], "src": "yahoo",
                      "bar_quality": "real_ohlc"}],
        "basis_drift": None, "suspected_breaks": [], "refusal_reasons": [],
    }
    return {"status": "bound", "view": view, "refusal_reasons": []}


def bind_terminal_yahoo_materialization(document, *, alias_table, master_records,
                                       parse_listing_key, producer_version,
                                       owner_version, reference, reused=False) -> dict:
    """Bind the existing stock profile, retaining its wire/codec and two aliases.

    SPY is reserved for its named catalog profile even if a caller supplies a
    store row that would otherwise make this legacy stock path appear eligible.
    """
    try:
        inputs = _observation(document, reused=reused, instant_parser=_instant)
        symbol, requested, on = inputs["symbol"], inputs["requested"], inputs["on"]
        _require(symbol != "SPY" and requested != "SPY",
                 "MATERIALIZATION_SPY_PROFILE_REQUIRED")
        try:
            stored_id = alias_table.resolve("store", symbol, on)
            requested_id = alias_table.resolve("yahoo_fetch", requested, on)
        except (ValueError, TypeError, AttributeError):
            raise MaterializationRefusal("MATERIALIZATION_IDENTITY_UNRESOLVED") from None
        _require(stored_id != "SEC:US-ARCX-SPY" and requested_id != "SEC:US-ARCX-SPY",
                 "MATERIALIZATION_SPY_PROFILE_REQUIRED")
        _require(stored_id is not None and requested_id is not None,
                 "MATERIALIZATION_IDENTITY_UNRESOLVED")
        _require(stored_id == requested_id, "MATERIALIZATION_IDENTITY_MISMATCH")
        row = _listing_record(master_records, stored_id, parse_listing_key)
        _require(row.get("listing_key") != "US-ARCX-SPY"
                 and row.get("inception_code") != "SPY",
                 "MATERIALIZATION_SPY_PROFILE_REQUIRED")
        producer = _version(producer_version, "mastermindx-market-intelligence/mastermind-terminal",
                            PRODUCER_FILES)
        owner = _version(owner_version, "mastermindx-market-intelligence/macro",
                         (OWNER_PATH, IDENTITY_PATH))
        identity_reference = _reference(reference)
        return _bound_view(inputs, stored_id, row, producer=producer, owner=owner,
                           identity_reference=identity_reference, schema=API_VERSION,
                           evidence_clock="observed_at")
    except MaterializationRefusal as exc:
        return {"status": "refused", "view": None, "refusal_reasons": [str(exc)]}


def bind_terminal_spy_yahoo_materialization(
        document, *, alias_table, alias_records, master_records, parse_listing_key,
        alias_binding_sha256, spy_catalog, producer_version, owner_version, reference,
        catalog_evidence, materialized_at, reused=False) -> dict:
    """Bind only SPY through its complete current catalog receipt and real readers.

    The supplied helper and identity callable must be the adapter's qualified
    owner bytes. The pure leaf validates supplied facts; it cannot attest reads
    or authenticate claimed source hashes itself. It samples no clock and never
    supplies a store alias. Earlier observed prices may be qualified only at the
    caller's later actual materialization cutoff.
    """
    try:
        inputs = _observation(document, reused=reused, instant_parser=_strict_instant)
        _require(inputs["symbol"] == "SPY" and inputs["requested"] == "SPY",
                 "MATERIALIZATION_IDENTITY_UNRESOLVED")
        materialized = _strict_instant(materialized_at)
        producer = _version(producer_version, "mastermindx-market-intelligence/mastermind-terminal",
                            PRODUCER_FILES)
        owner = _version(owner_version, "mastermindx-market-intelligence/macro",
                         (OWNER_PATH, IDENTITY_PATH, SPY_HELPER_PATH))
        identity_reference = _reference(reference, expected_files=SPY_REFERENCE_FILES,
                                        instant_parser=_strict_instant)
        current_read = _strict_instant(identity_reference["read_at"])
        _require(type(catalog_evidence) is dict and bool(catalog_evidence)
                 and type(alias_records) is list and bool(alias_records)
                 and all(type(row) is dict for row in alias_records),
                 "MATERIALIZATION_SPY_CATALOG_INVALID")
        try:
            # The current canonical target and admission must already exist at
            # this actual reference read, not merely by a later wall-clock time.
            spy_catalog.validate_retained(
                catalog_evidence, alias_records, master_records,
                alias_binding_sha256=alias_binding_sha256,
                latest_at=identity_reference["read_at"])
            evidence_digest = spy_catalog.evidence_sha256(catalog_evidence)
        except (ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError):
            raise MaterializationRefusal("MATERIALIZATION_SPY_CATALOG_INVALID") from None
        # The helper preserves the reviewed source grammar. Critical consumer
        # clocks additionally reject precision that datetime would otherwise floor.
        clocks = {key: _strict_instant(catalog_evidence.get(key)) for key in (
            "decision_at", "known_at", "admitted_at", "source_available_at",
            "reference_read_completed_at")}
        admitted = clocks["admitted_at"]
        available = clocks["source_available_at"]
        _require(current_read >= admitted
                 and materialized >= max(inputs["observed"], available, admitted, current_read),
                 "MATERIALIZATION_CLOCK_INVALID")
        # Catalog validity is a UTC admission-date relation. The old NY price
        # observation date remains only the bar ceiling enforced above.
        catalog_day = materialized.astimezone(timezone.utc).date()
        try:
            security_id = alias_table.resolve("yahoo_fetch", "SPY", catalog_day)
        except (ValueError, TypeError, AttributeError):
            raise MaterializationRefusal("MATERIALIZATION_IDENTITY_UNRESOLVED") from None
        _require(security_id is not None, "MATERIALIZATION_IDENTITY_UNRESOLVED")
        _require(security_id == "SEC:US-ARCX-SPY", "MATERIALIZATION_IDENTITY_MISMATCH")
        row = _listing_record(master_records, security_id, parse_listing_key)
        # The retained helper already proves one exact, active canonical target;
        # this explicit profile boundary also pins the parser's expected venue.
        _require(row.get("listing_key") == "US-ARCX-SPY" and row.get("mic") == "ARCX",
                 "MATERIALIZATION_IDENTITY_MISMATCH")
        sealed_rows = [item for item in alias_records
                       if item.get("vendor") == "yahoo_fetch"
                       and item.get("vendor_symbol") == "SPY"
                       and item.get("security_id") == "SEC:US-ARCX-SPY"]
        _require(len(sealed_rows) == 1, "MATERIALIZATION_SPY_CATALOG_INVALID")
        seal = sealed_rows[0].get("binding_sha256")
        _require(type(evidence_digest) is str and _SHA.fullmatch(evidence_digest)
                 and sealed_rows[0].get("evidence_sha256") == evidence_digest
                 and type(seal) is str and _SHA.fullmatch(seal),
                 "MATERIALIZATION_SPY_CATALOG_INVALID")
        catalog_admission = {key: catalog_evidence[key] for key in (
            "schema", "vendor", "symbol", "security_id", "valid_from", "valid_to",
            "known_at", "admitted_at", "source_available_at", "reference_read_completed_at")}
        catalog_admission.update(evidence_sha256=evidence_digest, binding_sha256=seal)
        result = _bound_view(inputs, security_id, row, producer=producer, owner=owner,
                             identity_reference=identity_reference, schema=SPY_API_VERSION,
                             evidence_clock="materialized_at")
        materialization = result["view"]["contract"]["materialization"]
        materialization["materialized_at"] = materialized_at
        materialization["catalog_admission"] = catalog_admission
        # Admission's historical preimage remains in the original receipt. The
        # identity_reference above binds this distinct current triplet read.
        return result
    except MaterializationRefusal as exc:
        return {"status": "refused", "view": None, "refusal_reasons": [str(exc)]}
    except OverflowError:
        return {"status": "refused", "view": None,
                "refusal_reasons": ["MATERIALIZATION_CLOCK_INVALID"]}
