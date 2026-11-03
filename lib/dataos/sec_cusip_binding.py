"""A single evidenced SEC CUSIP filing-day binding, using Data OS aliases.

Pure read/composition: no security allocation, identity-store write, publication or
K2-C semantic promotion. Callers retain the exact source objects and real read clocks.
The bounded namespace must not be used as a current-catalog or timeless resolver.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import io
import json
import re
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from lib.dataos.identity import (
    AliasRow, IdentityError, SEC_FILING_CUSIP_VENDOR, VendorAliasTable,
    _aware_utc, _null_to_none, alias_binding_sha256, parse_listing_key,
)


def _checked(raw: bytes, digest: str, bound: int) -> None:
    if (type(raw) is not bytes or not raw or len(raw) > bound
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or hashlib.sha256(raw).hexdigest() != digest):
        raise IdentityError("retained SEC identity source digest/size mismatch")


def _text(element) -> str:
    return " ".join("".join(element.itertext()).split())


def _one(elements, label):
    if len(elements) != 1:
        raise IdentityError("ambiguous or absent SEC " + label)
    return elements[0]


def _name(value: str) -> str:
    return " ".join(value.replace(".", "").casefold().split())


def _registration(raw: bytes, issuer_cik: str, share_class: str, issuer_name: str,
                  *, structured_13d: bool = False):
    # Preserve the original unqualified-common 13G scope. The separate 13D
    # path additionally supports evidenced Class A; never collapse classes.
    class_name = "Common Stock"
    if structured_13d:
        match = re.fullmatch(
            r"(Class A Common Stock|Common Stock)(?:, (?:par value \$[0-9]+(?:\.[0-9]+)? per share|\$[0-9]+(?:\.[0-9]+)? par value per share))?",
            share_class, re.I)
        if match:
            class_name = match.group(1)
        else:
            raise IdentityError("SEC class not supported by this bounded binding")
    elif share_class.casefold() != "common stock":
        raise IdentityError("SEC class not supported by this bounded binding")
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", raw, re.I):
        raise IdentityError("SEC registration entity declarations forbidden")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise IdentityError("malformed SEC registration XML") from exc
    if root.tag != "{http://www.xbrl.org/2003/instance}xbrl":
        raise IdentityError("extracted XBRL registration required")
    facts = {}
    for element in root:
        match = re.fullmatch(r"\{http://xbrl.sec.gov/dei/\d{4}\}([A-Za-z0-9]+)", element.tag)
        if match:
            facts.setdefault(match[1], []).append(element)
    cik = _text(_one(facts.get("EntityCentralIndexKey", []), "registrant CIK"))
    name = _text(_one(facts.get("EntityRegistrantName", []), "registrant name"))
    if cik != issuer_cik or _name(name) != _name(issuer_name):
        raise IdentityError("SEC registration issuer mismatch")
    title_pattern = re.escape(class_name) + (
        r"(?:, (?:par value \$[0-9]+(?:\.[0-9]+)? per share|\$[0-9]+(?:\.[0-9]+)? par value per share))?"
        if structured_13d else r"(?:, par value \$[0-9]+(?:\.[0-9]+)? per share)?")
    titles = [e for e in facts.get("Security12bTitle", [])
              if re.fullmatch(title_pattern, _text(e), re.I)]
    title = _one(titles, "common-stock registration class")
    if structured_13d:
        filing_par = re.search(r"\$([0-9]+(?:\.[0-9]+)?)", share_class)
        registration_par = re.search(r"\$([0-9]+(?:\.[0-9]+)?)", _text(title))
        if filing_par:
            from decimal import Decimal
            if (not registration_par or
                    Decimal(filing_par.group(1)) != Decimal(registration_par.group(1))):
                raise IdentityError("SEC registration par value mismatch")
    context = title.get("contextRef")
    if not context:
        raise IdentityError("SEC registration class context required")
    contexts = [e for e in root.findall("{http://www.xbrl.org/2003/instance}context")
                if e.get("id") == context]
    ctx = _one(contexts, "class context")
    ns = "{http://www.xbrl.org/2003/instance}"
    identifiers = ctx.findall(ns + "entity/" + ns + "identifier")
    identifier = _one(identifiers, "class entity")
    if identifier.get("scheme") != "http://www.sec.gov/CIK" or _text(identifier) != issuer_cik:
        raise IdentityError("SEC class context issuer mismatch")
    period = _one(ctx.findall(ns + "period"), "class period")
    instants = period.findall(ns + "instant")
    starts, ends = period.findall(ns + "startDate"), period.findall(ns + "endDate")
    def day(element):
        value = _text(element)
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("non-ISO reference day")
        return date.fromisoformat(value)
    try:
        if len(instants) == 1 and not starts and not ends:
            reference_date = day(instants[0])
        elif not instants and len(starts) == len(ends) == 1:
            start = day(starts[0])
            reference_date = day(ends[0])
            if start > reference_date:
                raise ValueError("reversed reference period")
        else:
            raise ValueError("ambiguous reference period")
    except ValueError as exc:
        raise IdentityError("malformed SEC class reference date") from exc
    def fact(key):
        return _text(_one([e for e in facts.get(key, []) if e.get("contextRef") == context], key))
    symbol, exchange = fact("TradingSymbol"), fact("SecurityExchangeName")
    exchanges = {"NYSE": "XNYS"}
    if structured_13d:
        exchanges["NASDAQ"] = "XNAS"
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", symbol) or exchange not in exchanges:
        raise IdentityError("unsupported SEC registration listing")
    return symbol, exchanges[exchange], reference_date


def build_sec_cusip_alias(
    filing_raw: bytes, *, filing_sha256: str, filing_retained_at: datetime,
    registration_raw: bytes, registration_sha256: str, registration_retained_at: datetime,
    master_raw: bytes, master_sha256: str, master_retained_at: datetime,
) -> AliasRow:
    """Bind one explicit SEC class through its registration to an existing master row.

    ``known_at`` is the latest actual retained-object read, never filing event time.
    The resulting half-open validity is exactly the filing acceptance day. This does not
    establish intervening history, availability at an earlier decision, or a manager
    strategy. Integrity checks do not independently authenticate caller read clocks;
    source-owner acquisition qualification remains required before publication.
    """
    return _build_sec_alias(
        filing_raw, filing_sha256=filing_sha256, filing_retained_at=filing_retained_at,
        registration_raw=registration_raw, registration_sha256=registration_sha256,
        registration_retained_at=registration_retained_at,
        master_raw=master_raw, master_sha256=master_sha256,
        master_retained_at=master_retained_at, structured_13d=False)


def build_sec13d_cusip_alias(
    filing_raw: bytes, *, filing_sha256: str, filing_retained_at: datetime,
    registration_raw: bytes, registration_sha256: str, registration_retained_at: datetime,
    master_raw: bytes, master_sha256: str, master_retained_at: datetime,
) -> AliasRow:
    """Bind a structured 13D's explicit common-stock class for its assertion day.

    Class A remains distinct from unqualified common stock. This extends the
    evidenced registration route to Nasdaq; it establishes neither continuous
    CUSIP history nor economic ownership, intent, or a quarterly 13F binding.
    """
    return _build_sec_alias(
        filing_raw, filing_sha256=filing_sha256, filing_retained_at=filing_retained_at,
        registration_raw=registration_raw, registration_sha256=registration_sha256,
        registration_retained_at=registration_retained_at,
        master_raw=master_raw, master_sha256=master_sha256,
        master_retained_at=master_retained_at, structured_13d=True)


def _build_sec_alias(
    filing_raw: bytes, *, filing_sha256: str, filing_retained_at: datetime,
    registration_raw: bytes, registration_sha256: str, registration_retained_at: datetime,
    master_raw: bytes, master_sha256: str, master_retained_at: datetime,
    structured_13d: bool,
) -> AliasRow:
    _checked(filing_raw, filing_sha256, 2 * 1024 * 1024)
    _checked(registration_raw, registration_sha256, 8 * 1024 * 1024)
    _checked(master_raw, master_sha256, 16 * 1024 * 1024)
    filing_clock = _aware_utc(filing_retained_at, "known_at")
    reg_clock = _aware_utc(registration_retained_at, "known_at")
    master_clock = _aware_utc(master_retained_at, "known_at")
    if structured_13d:
        from lib.dataos.sec_schedule13d import parse_schedule13d_evidence as parse_evidence
    else:
        from lib.dataos.sec_filing_identity import parse_schedule13g_evidence as parse_evidence
    evidence = parse_evidence(filing_raw, expected_sha256=filing_sha256,
                              retained_at=filing_clock)
    symbol, mic, reference_date = _registration(registration_raw, evidence.issuer_cik,
                                               evidence.share_class, evidence.issuer_name,
                                               structured_13d=structured_13d)
    # The ownership event date is not the start of a CUSIP identity interval.
    # Use only the day this retained filing actually asserted the identity.
    observed_day = evidence.accepted_at.astimezone(ZoneInfo("America/New_York")).date()
    if reference_date > observed_day or reference_date > reg_clock.date():
        raise IdentityError("registration class evidence follows SEC event/read")
    import pandas as pd
    try:
        records = pd.read_parquet(io.BytesIO(master_raw)).to_dict("records")
    except Exception as exc:
        raise IdentityError("invalid canonical master object") from exc
    candidates = [r for r in records if r.get("issuer_cik") == evidence.issuer_cik
                  and r.get("listing_key") == f"US-{mic}-{symbol}"]
    row = _one(candidates, "canonical master security")
    key = parse_listing_key(row["listing_key"])
    if (row.get("issuer_state") != "RESOLVED"
            or _null_to_none(row.get("security_state")) not in (None, "")
            or _null_to_none(row.get("superseded_by")) not in (None, "")
            or row.get("country") != key.country or row.get("mic") != key.mic
            or row.get("inception_code") != key.code
            or not isinstance(row.get("security_id"), str)
            or not row["security_id"].startswith("SEC:")):
        raise IdentityError("canonical master security inactive/inconsistent")
    if sum(r.get("security_id") == row["security_id"] for r in records) != 1:
        raise IdentityError("canonical security identity not unique")
    known = max(evidence.known_at, reg_clock, master_clock)
    vector = {"filing_sha256": filing_sha256, "registration_sha256": registration_sha256,
              "master_sha256": master_sha256, "filing_retained_at": filing_clock.isoformat(),
              "registration_retained_at": reg_clock.isoformat(),
              "master_retained_at": master_clock.isoformat()}
    digest = hashlib.sha256(json.dumps(vector, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    end = observed_day + timedelta(days=1)
    seal = alias_binding_sha256(SEC_FILING_CUSIP_VENDOR, evidence.cusip, row["security_id"],
                                observed_day, end, known, digest)
    alias = AliasRow(SEC_FILING_CUSIP_VENDOR, evidence.cusip, row["security_id"],
                     observed_day, end, known, digest, seal)
    VendorAliasTable([alias])  # use the native ambiguity and sealed-row invariants
    return alias
