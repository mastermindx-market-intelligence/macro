"""Private, stdlib-only semantics for the existing SPY Yahoo catalog relation.

Extracted from the reviewed security-master owner; this is no admission writer or
alias resolver. Validate retained evidence with ``validate_retained`` and the
existing canonical alias-binding callable. Inputs and cutoff belong to the caller.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import re


class SpyCatalogError(ValueError):
    """The existing SPY catalog evidence grammar is not satisfied."""


MASTER_COLUMNS = (
    "security_id",
    "issuer_id",
    "issuer_state",
    "issuer_cik",
    "issuer_evidence_snapshot",
    "listing_key",
    "country",
    "mic",
    "inception_code",
    "effective_at",
    "ingested_at",
    "security_state",
    "superseded_by",
)


MASTER_NAME = "security_master.parquet"
ALIASES_NAME = "vendor_aliases.parquet"
RECEIPT_NAME = "_receipt.json"
ISSUER_MASTER_NAME = "issuer_master.parquet"
ISSUER_MIGRATIONS_NAME = "issuer_migrations.parquet"
SECURITY_MIGRATIONS_NAME = "security_migrations.parquet"
_REFERENCE_MAX_BYTES = 2 * 1024 * 1024


_SPY_YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1d&range=1d"
_SPY_ISSUER_URL = "https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy"
_SPY_YAHOO_SCHEMA = "mastermind.spy_yahoo_catalog_sources.v1"
_SPY_YAHOO_META = {
    "symbol": "SPY", "currency": "USD", "exchangeName": "PCX",
    "fullExchangeName": "NYSEArca", "instrumentType": "ETF",
    "exchangeTimezoneName": "America/New_York",
    "longName": "State Street SPDR S&P 500 ETF Trust",
}


_SPY_YAHOO_SCOPE = "CURRENT SPY Yahoo catalog only; source-specific inference"
_SPY_YAHOO_LIMITS = (
    "No Macro stock-store alias or issuer admission",
    "No historical identity, listing-date inference from firstTradeDate, or coverage proof",
    "No adjusted-history qualification, prediction admission, or source-use-rights assertion",
    "Generic Yahoo lookup does not enforce known_at; a closed consumer must validate "
    "this receipt and its actual reference-read/publication cutoff",
)


def reference_ns(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise SpyCatalogError(f"invalid reference {name}")
    return value


def clock_ns(value: object) -> int:
    try:
        clock = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if clock.tzinfo is None or clock.utcoffset() is None:
            raise ValueError("naive")
        delta = clock.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        return ((delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds) * 1000
    except (TypeError, ValueError, OverflowError) as exc:
        raise SpyCatalogError("invalid reference UTC clock") from exc


def clock_iso(ns: int) -> str:
    # Ceiling, never float rounding or truncation that advances availability.
    return (datetime(1970, 1, 1, tzinfo=timezone.utc)
            + timedelta(microseconds=(ns + 999) // 1000)).isoformat()


def evidence_bytes(evidence) -> bytes:
    """Preserve the owner's exact indented JSON, trailing newline and UTF-8 bytes."""
    return (json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def evidence_sha256(evidence) -> str:
    return hashlib.sha256(evidence_bytes(evidence)).hexdigest()


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _validate_source_evidence(evidence: dict, current_master_rows: list[dict],
                              *, latest_at: str):
    """Constructor-stage grammar before the owner attaches its reference preimage.

    This private stage is not retained-evidence or consumer qualification. Full
    validation is mandatory after the existing owner attaches the preimage.
    """
    try:
        required = {
            "schema", "vendor", "symbol", "security_id", "valid_from", "valid_to",
            "known_at", "decision_at", "admitted_at", "source_available_at",
            "reference_read_completed_at", "sources", "yahoo_identity",
            "yahoo_first_trade_date", "issuer_listing", "listing",
            "canonical_target", "scope", "limits",
        }
        if type(evidence) is not dict or set(evidence) != required:
            raise ValueError("incomplete SPY Yahoo evidence")
        if (evidence["schema"] != _SPY_YAHOO_SCHEMA or evidence["vendor"] != "yahoo_fetch"
                or evidence["symbol"] != "SPY" or evidence["security_id"] != "SEC:US-ARCX-SPY"
                or evidence["valid_to"] is not None or evidence["scope"] != _SPY_YAHOO_SCOPE
                or evidence["limits"] != list(_SPY_YAHOO_LIMITS)
                or evidence["yahoo_identity"] != _SPY_YAHOO_META):
            raise ValueError("retained SPY Yahoo profile conflict")
        decision = clock_ns(evidence["decision_at"])
        latest = clock_ns(latest_at)
        read = clock_ns(evidence["reference_read_completed_at"])
        known = clock_iso(decision)
        on = date.fromisoformat(evidence["valid_from"])
        if (not 0 < read <= decision <= latest
                or evidence["decision_at"] != known or evidence["known_at"] != known
                or evidence["admitted_at"] != known
                or evidence["valid_from"] != on.isoformat() or known[:10] != on.isoformat()):
            raise ValueError("retained SPY Yahoo decision clocks conflict")
        first = evidence["yahoo_first_trade_date"]
        if type(first) is not int or not 0 < first <= decision // 1000000000:
            raise ValueError("invalid retained provider firstTradeDate")

        def capture_clock(value):
            # This profile retains actual microsecond capture clocks. Refuse
            # extra precision instead of truncating an availability boundary.
            if not isinstance(value, str) or not re.fullmatch(
                    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value):
                raise ValueError("unsupported SPY capture clock grammar")
            return clock_ns(value)

        urls = {"yahoo": _SPY_YAHOO_URL, "issuer": _SPY_ISSUER_URL}
        if type(evidence["sources"]) is not dict or set(evidence["sources"]) != set(urls):
            raise ValueError("retained SPY source roles conflict")
        completions = []
        for role, url in urls.items():
            capture = evidence["sources"][role]
            if (type(capture) is not dict or set(capture) != {
                    "url", "final_url", "status", "bytes", "sha256",
                    "request_started_at", "read_completed_at"}
                    or capture["url"] != url or capture["final_url"] != url
                    or type(capture["status"]) is not int or capture["status"] != 200
                    or type(capture["bytes"]) is not int or not 0 < capture["bytes"] <= _REFERENCE_MAX_BYTES
                    or not _digest(capture["sha256"])):
                raise ValueError("invalid retained SPY source capture")
            started = capture_clock(capture["request_started_at"])
            completed = capture_clock(capture["read_completed_at"])
            if (not 0 < started <= completed <= decision
                    or clock_iso(started)[:10] != on.isoformat()
                    or clock_iso(completed)[:10] != on.isoformat()):
                raise ValueError("retained SPY source clocks conflict")
            completions.append(completed)
        expected_issuer = {
            "fund_name": _SPY_YAHOO_META["longName"], "observed_on": on.isoformat(),
            "exchange": "NYSE ARCA", "currency": "USD", "symbol": "SPY",
            "listing_date": "1993-01-22", "cusip": "78462F103", "isin": "US78462F1030",
        }
        if evidence["issuer_listing"] != expected_issuer:
            raise ValueError("retained SPY issuer listing conflict")
        listing = evidence["listing"]
        if (type(listing) is not dict or set(listing) != {
                "symbol", "listing_key", "observed_on", "listing_snapshot_sha256",
                "listing_receipt_sha256", "collector_completed_at"}
                or listing["symbol"] != "SPY" or listing["listing_key"] != "US-ARCX-SPY"
                or listing["observed_on"] != on.isoformat()
                or not _digest(listing["listing_snapshot_sha256"])
                or not _digest(listing["listing_receipt_sha256"])):
            raise ValueError("invalid retained SPY listing observation")
        collected = capture_clock(listing["collector_completed_at"])
        if (not 0 < collected <= read or clock_iso(collected)[:10] != on.isoformat()
                or evidence["source_available_at"] != clock_iso(max(*completions, collected))):
            raise ValueError("retained SPY source availability conflict")

        def target(record, cutoff):
            if (type(record) is not dict or set(record) != set(MASTER_COLUMNS)
                    or any(type(v) not in (str, type(None)) for v in record.values())
                    or [record[k] for k in ("security_id", "listing_key", "country", "mic", "inception_code")] !=
                       ["SEC:US-ARCX-SPY", "US-ARCX-SPY", "US", "ARCX", "SPY"]
                    or record["security_state"] is not None or record["superseded_by"] is not None):
                raise ValueError("SPY canonical target needs explicit evidence curation")
            clocks = []
            for key in ("effective_at", "ingested_at"):
                if type(record[key]) is not str:
                    raise ValueError("missing SPY canonical clock")
                # Reject excess precision before datetime can discard fractional digits.
                if re.search(r"[.,]\d{7,}", record[key]) is not None:
                    raise ValueError("unsupported SPY canonical clock precision")
                value = datetime.fromisoformat(record[key].replace("Z", "+00:00"))
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)  # declared UTC Parquet columns
                clocks.append(clock_ns(value.isoformat()))
            if not 0 < clocks[0] <= clocks[1] <= cutoff:
                raise ValueError("SPY canonical target clock conflict")

        target(evidence["canonical_target"], read)
        if type(current_master_rows) is not list or any(type(r) is not dict for r in current_master_rows):
            raise ValueError("current SPY canonical records unavailable")
        matches = [r for r in current_master_rows if r.get("security_id") == "SEC:US-ARCX-SPY"
                   or r.get("listing_key") == "US-ARCX-SPY"]
        if len(matches) != 1:
            raise ValueError("current SPY canonical target missing or ambiguous")
        current = {key: matches[0].get(key) for key in MASTER_COLUMNS}
        target(current, latest)
        if current != evidence["canonical_target"]:
            raise ValueError("SPY canonical target changed; explicit evidence curation required")
    except (KeyError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise SpyCatalogError("invalid SPY Yahoo retained source semantics") from exc


def validate_evidence(evidence: dict, current_master_rows: list[dict], *, latest_at: str):
    """Validate complete retained evidence, including all six preimage records.

    No allow-missing option exists. This function reads only supplied values;
    hashes supplement source/clock/current-target checks and never replace them.
    """
    try:
        if type(evidence) is not dict or "canonical_reference_preimage" not in evidence:
            raise ValueError("incomplete SPY Yahoo evidence")
        source_evidence = {key: value for key, value in evidence.items()
                           if key != "canonical_reference_preimage"}
        _validate_source_evidence(source_evidence, current_master_rows, latest_at=latest_at)
        preimage = evidence["canonical_reference_preimage"]
        filenames = {MASTER_NAME, ALIASES_NAME, ISSUER_MASTER_NAME,
                     ISSUER_MIGRATIONS_NAME, SECURITY_MIGRATIONS_NAME, RECEIPT_NAME}
        if type(preimage) is not dict or set(preimage) != filenames:
            raise ValueError("incomplete SPY canonical preimage")
        for name, record in preimage.items():
            bound = _REFERENCE_MAX_BYTES if name == RECEIPT_NAME else 64 * 1024 * 1024
            if (type(record) is not dict or set(record) != {"bytes", "sha256"}
                    or type(record["bytes"]) is not int or not 0 < record["bytes"] <= bound
                    or not _digest(record["sha256"])):
                raise ValueError("invalid SPY canonical preimage record")
    except (KeyError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise SpyCatalogError("invalid SPY Yahoo retained source semantics") from exc


def validate_retained(evidence: dict | None, alias_rows: list[dict],
                      master_rows: list[dict], *, alias_binding_sha256, latest_at: str):
    """Check the existing alias seal with its caller-supplied canonical function.

    The caller supplies its actual cutoff; this helper does not sample time.
    Nothing here allocates, resolves, writes, publishes, or extends an identity.
    """
    rows = [row for row in alias_rows if row.get("vendor") == "yahoo_fetch"
            and (row.get("vendor_symbol") == "SPY" or row.get("security_id") == "SEC:US-ARCX-SPY")]
    if evidence is None:
        if rows:
            raise SpyCatalogError("SPY Yahoo relation lacks retained source evidence")
        return
    validate_evidence(evidence, master_rows, latest_at=latest_at)
    try:
        if (type(evidence) is not dict or evidence.get("schema") != _SPY_YAHOO_SCHEMA
                or evidence.get("vendor") != "yahoo_fetch" or evidence.get("symbol") != "SPY"
                or evidence.get("security_id") != "SEC:US-ARCX-SPY" or evidence.get("valid_to") is not None
                or evidence.get("decision_at") != evidence.get("known_at")
                or evidence.get("admitted_at") != evidence.get("decision_at") or len(rows) != 1):
            raise ValueError("invalid retained SPY Yahoo identity")
        start = date.fromisoformat(evidence["valid_from"])
        decision = clock_ns(evidence["decision_at"])
        if (start.isoformat() != clock_iso(decision)[:10]
                or not 0 < clock_ns(evidence["source_available_at"]) <= decision
                or not 0 < clock_ns(evidence["reference_read_completed_at"]) <= decision
                or decision > clock_ns(latest_at)):
            raise ValueError("invalid retained SPY Yahoo clocks")
        digest = evidence_sha256(evidence)
        seal = alias_binding_sha256("yahoo_fetch", "SPY", "SEC:US-ARCX-SPY",
                                     start, None, evidence["known_at"], digest)
        row = rows[0]
        expected = {"vendor": "yahoo_fetch", "vendor_symbol": "SPY", "security_id": "SEC:US-ARCX-SPY",
                    "valid_from": start.isoformat(), "valid_to": None, "known_at": evidence["known_at"],
                    "evidence_sha256": digest, "binding_sha256": seal, "alias_kind": None}
        if any(row.get(key) != value for key, value in expected.items()):
            raise ValueError("retained SPY Yahoo alias/evidence mismatch")
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise SpyCatalogError("invalid retained SPY Yahoo binding") from exc
