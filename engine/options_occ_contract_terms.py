"""engine/options_occ_contract_terms.py — bounded OCC DDS FIXML full-snapshot terms decoder.

Pure, deterministic decoding of ONE ``SecDef`` product-definition snapshot plus
ONE ``SecList`` series snapshot into exact normalized option contract terms.

EVIDENCE DECODING ONLY.  This module closes missing parsing machinery; it does not admit a
source, authenticate a feed, observe availability, or grant market-data authority.  It never
emits ``options.contract_terms_observation/v1`` and never invents an effective timestamp:
``source_available_at``/``source_observed_at``/``effective_timestamp_binding`` are null and
``source_authenticated``/``consumer_admitted`` are false by construction.

Source facts implemented (OCC DDS DeveloperReference I v4.6, August 2026):
  * ``SecDef@BizDt/RptID/Ccy`` and its ONE direct ``Instrmt@Sym/Desc/CFI/StrkCcy/StrkMult/
    Mult/StrkValu``.  ``Mult`` is the premium multiplier; ``StrkMult`` scales the strike and
    ``StrkValu`` is the strike amount per unit.  They are not interchangeable and none is
    defaulted; this first interface requires ``StrkMult == 1`` instead of guessing scaled
    contract identity.
  * Direct ``Undly`` siblings, one deliverable component each: ``Sym``, ``CFI``, ``Qty`` and
    optional ``ID``/``Src``/``CashAmt``/``CashTyp``/``SetMeth``/``SettlStat``/``AllocPct``.
    Every component is preserved, in document order, with its raw attributes.
  * ``SecList@BizDt/RptID``; each direct ``SecL``/``Instrmt`` supplies ``Sym``, ``MatDt``,
    ``MMY`` (YYYYMMDD), ``StrkPx``, ``CFI``.
  * CFI positions: 1 ``O`` option; 2 ``C``/``P`` (a product may be ``X``); 3 ``A``/``E``
    exercise style; 4 ``S`` equity / ``I`` index; 5 ``P`` physical / ``C`` cash;
    6 ``S`` standard / ``N`` nonstandard.  Any other value is refused, never reinterpreted.
  * ``Instrmt/Evnt``: ``EventTyp`` 5 activation ``Dt``, 6 inactivation ``Dt``, 100 closing-only
    exchange ``Txt``.
  * Every date is a LocalMktDate DAY value: no timezone conversion, no clock, no I/O.
  * ``SecDefUpd``/``SecListUpd`` are incremental delta records and are refused; nothing is
    silently applied.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date
from decimal import Decimal
from xml.etree import ElementTree

from engine.options_nbbo_cohort import NbboCohortError, validate_contract

__all__ = ["TermsDecodeError", "decode_contract_terms", "SCHEMA", "ALLOWED_NAMESPACES",
           "MAX_INPUT_BYTES", "CONTRACT_FIELDS"]

SCHEMA = "options.occ_contract_terms_decoded/v1"
CONTRACT_FIELDS = frozenset({"root", "expiration", "right", "strike", "strike_millis", "occ_symbol"})
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_NUMERIC_CHARS = 50
ALLOWED_NAMESPACES = frozenset({
    "",
    "http://www.fixprotocol.org/FIXML-4-4",
    "http://www.fixprotocol.org/FIXML-5-0-SP2",
})
_INCREMENTAL_TAGS = frozenset({"SecDefUpd", "SecListUpd"})
_WRAPPER_TAGS = frozenset({"FIXML", "Batch"})
_SERIES_TAGS = frozenset({"SecL"})
_DESCRIPTIONS = frozenset({"STAN", "BINY", "FLEX", "RNGE"})
_CFI_STYLE = frozenset({"A", "E"})
_CFI_CLASS = frozenset({"S", "I"})
_CFI_SETTLE = frozenset({"P", "C"})
_CFI_STANDARD = frozenset({"S", "N"})
_CFI_RE = re.compile(r"\A[A-Z]{6}\Z")
_PLAIN_DECIMAL_RE = re.compile(r"\A-?[0-9]+(?:\.[0-9]+)?\Z")
_LOCAL_MKT_DATE_RE = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_MMY_RE = re.compile(r"\A[0-9]{8}\Z")
_STANDARD_CFI_RE = re.compile(r"\AO[CPX]ASPS\Z")
_EQUITY_UNDLY_CFI_RE = re.compile(r"\AEXXXXX\Z")


class TermsDecodeError(ValueError):
    """Malformed, ambiguous, missing, or unsupported contract terms in a full snapshot."""


def _local(name: str) -> str:
    """Return the namespace-local part of an element tag or attribute name."""
    if name.startswith("{"):
        _, _, local = name[1:].partition("}")
        return local
    return name


def _namespace(name: str) -> str:
    if name.startswith("{"):
        return name[1:].partition("}")[0]
    return ""


def _fail(message: str) -> "TermsDecodeError":
    return TermsDecodeError(message)


def _attribute(element: ElementTree.Element, name: str, field: str) -> str:
    value = element.get(name)
    if value is None:
        raise _fail(f"{field}: missing {name}")
    return value


def _present(element: ElementTree.Element, name: str, field: str) -> str:
    """Required attribute whose literal value is preserved even when empty."""
    return _attribute(element, name, field)


def _identifier(element: ElementTree.Element, name: str, field: str) -> str:
    value = _attribute(element, name, field)
    if not value.strip():
        raise _fail(f"{field}: {name} must be non-empty")
    return value


def _decimal(text: str, field: str, *, positive: bool) -> Decimal:
    if len(text) > MAX_NUMERIC_CHARS or not _PLAIN_DECIMAL_RE.match(text):
        raise _fail(f"{field}: {text!r} is not a plain finite decimal string")
    value = Decimal(text)
    if not value.is_finite():
        raise _fail(f"{field}: {text!r} is not finite")
    if positive and value <= 0:
        raise _fail(f"{field}: {text!r} must be positive")
    return value


def _canonical(value: Decimal) -> str:
    """Exact canonical decimal string; never scientific notation, never context-rounded."""
    if value == 0:
        return "0"
    sign, digits, exponent = value.as_tuple()
    numerals = "".join(str(digit) for digit in digits)
    if exponent >= 0:
        text = numerals + "0" * exponent
    else:
        frac = -exponent
        padded = numerals.rjust(frac + 1, "0")
        text = f"{padded[:-frac]}.{padded[-frac:]}".rstrip("0").rstrip(".")
    return ("-" if sign else "") + text


def _day(text: str, field: str) -> str:
    if not isinstance(text, str) or not _LOCAL_MKT_DATE_RE.match(text):
        raise _fail(f"{field}: {text!r} is not a LocalMktDate YYYY-MM-DD day value")
    try:
        date.fromisoformat(text)
    except ValueError:
        raise _fail(f"{field}: {text!r} is not a valid calendar day")
    return text


def _as_date(text: str) -> date:
    return date.fromisoformat(text)


def _cfi(value: str, field: str, rights: frozenset) -> str:
    if not _CFI_RE.match(value):
        raise _fail(f"{field}: CFI {value!r} must be six ASCII letters")
    if value[0] != "O":
        raise _fail(f"{field}: CFI category {value[0]!r} is not an option (O)")
    if value[1] not in rights:
        raise _fail(f"{field}: CFI call/put {value[1]!r} is not one of {sorted(rights)}")
    for index, allowed, label in ((2, _CFI_STYLE, "exercise style"), (3, _CFI_CLASS, "classification"),
                                  (4, _CFI_SETTLE, "settlement"), (5, _CFI_STANDARD, "standard")):
        if value[index] not in allowed:
            raise _fail(f"{field}: unsupported CFI {label} {value[index]!r}")
    return value


def _check_namespaces(root: ElementTree.Element, label: str) -> None:
    for element in root.iter():
        for name in (element.tag, *element.attrib):
            namespace = _namespace(name)
            if namespace not in ALLOWED_NAMESPACES:
                shown = namespace or "(absent)"
                raise _fail(f"{label}: namespace {shown!r} is not allowlisted")


def _reject_children(element: ElementTree.Element, allowed: frozenset, field: str) -> None:
    """Refuse any structure this interface does not read instead of silently dropping it."""
    for child in element:
        if _local(child.tag) not in allowed:
            raise _fail(f"{field}: unexpected child element {_local(child.tag)!r}; this interface reads "
                        f"attributes on {sorted(allowed) or 'no children'}")


def _undly_cfi(value: str, field: str) -> str:
    if not _CFI_RE.match(value):
        raise _fail(f"{field}: {value!r} is not a six-letter CFI code")
    return value


def _events(element: ElementTree.Element, field: str) -> tuple:
    """Activation/inactivation day values plus closing-only exchange names."""
    activation = inactivation = None
    closing: list = []
    for child in element:
        if _local(child.tag) != "Evnt":
            continue
        _reject_children(child, frozenset(), f"{field} Evnt")
        event_typ = _attribute(child, "EventTyp", f"{field} Evnt")
        if not event_typ.isdigit():
            raise _fail(f"{field} Evnt: EventTyp {event_typ!r} is not a non-negative integer")
        if event_typ == "5":
            if activation is not None:
                raise _fail(f"{field} Evnt: duplicate activation (EventTyp 5) is ambiguous")
            activation = _day(_attribute(child, "Dt", f"{field} Evnt EventTyp=5"),
                              f"{field} Evnt EventTyp=5 Dt")
        elif event_typ == "6":
            if inactivation is not None:
                raise _fail(f"{field} Evnt: duplicate inactivation (EventTyp 6) is ambiguous")
            inactivation = _day(_attribute(child, "Dt", f"{field} Evnt EventTyp=6"),
                                f"{field} Evnt EventTyp=6 Dt")
        elif event_typ == "100":
            closing.append(_identifier(child, "Txt", f"{field} Evnt EventTyp=100"))
    if activation is None:
        raise _fail(f"{field}: missing explicit activation date (Evnt EventTyp=5)")
    if inactivation is not None and _as_date(inactivation) < _as_date(activation):
        raise _fail(f"{field}: contradictory interval, inactivation {inactivation} "
                    f"precedes activation {activation}")
    return activation, inactivation, closing


def _parse_snapshot(raw: bytes, label: str, expected: str) -> ElementTree.Element:
    if type(raw) is not bytes:
        raise _fail(f"{label}: expected bytes, got {type(raw).__name__}")
    if not raw:
        raise _fail(f"{label}: empty document")
    if len(raw) > MAX_INPUT_BYTES:
        raise _fail(f"{label}: {len(raw)} bytes exceeds the {MAX_INPUT_BYTES} byte full-snapshot limit")
    if b"\x00" in raw:
        raise _fail(f"{label}: NUL bytes/non-UTF-8 encoding refused")
    lowered = raw.lower()
    if b"<!doctype" in lowered:
        raise _fail(f"{label}: DOCTYPE refused; no entity resolution is performed")
    if b"<!entity" in lowered:
        raise _fail(f"{label}: ENTITY declaration refused; no entity resolution is performed")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _fail(f"{label}: not UTF-8 encoded ({error.reason})")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        raise _fail(f"{label}: malformed XML ({error})")
    if not isinstance(root.tag, str):
        raise _fail(f"{label}: unsupported prolog node")
    _check_namespaces(root, label)
    tags = {_local(element.tag) for element in root.iter()}
    incremental = tags & _INCREMENTAL_TAGS
    if incremental:
        raise _fail(f"{label}: {sorted(incremental)[0]} is an incremental update record; full snapshots only")
    if _local(root.tag) == expected:
        return root
    if _local(root.tag) in _WRAPPER_TAGS:
        pending = [root]
        found = []
        while pending:
            wrapper = pending.pop()
            for element in wrapper:
                tag = _local(element.tag)
                if tag == expected:
                    found.append(element)
                elif tag in _WRAPPER_TAGS:
                    pending.append(element)
                else:
                    raise _fail(f"{label}: unexpected wrapper child {tag!r}")
        if not found:
            raise _fail(f"{label}: {_local(root.tag)} wrapper contains no {expected}")
        if len(found) > 1:
            raise _fail(f"{label}: {_local(root.tag)} wrapper contains {len(found)} "
                        f"{expected} records; ambiguous")
        return found[0]
    raise _fail(f"{label}: expected {expected} or a FIXML/Batch wrapper, got {_local(root.tag)}")


def _normalize_contract(contract: dict) -> dict:
    """Reuse the suite's exact identity; never synthesize missing OCC fields."""
    try:
        return validate_contract(contract)
    except (NbboCohortError, TypeError, ValueError) as error:
        raise _fail(f"contract: {error}") from error


def _parties(instrument: ElementTree.Element) -> list[dict]:
    """Retain declared exchange/clearing metadata, without granting authority."""
    parties = []
    for party in instrument:
        if _local(party.tag) != "Pty":
            continue
        _reject_children(party, frozenset({"Sub"}), "Instrmt Pty")
        for child in party:
            _reject_children(child, frozenset(), "Instrmt Pty Sub")
        parties.append({"attributes": dict(party.attrib),
                        "sub_ids": [dict(child.attrib) for child in party]})
    return parties


def _allocation(text: str | None) -> Decimal | None:
    if text is None:
        return None
    value = _decimal(text, "Undly AllocPct", positive=False)
    if not Decimal(0) <= value <= Decimal(100):
        raise _fail("Undly AllocPct must be between 0 and 100")
    return value


def _decode_product(snapshot: ElementTree.Element, root_symbol: str) -> dict:
    field = "SecDef"
    _reject_children(snapshot, frozenset({"Instrmt", "Undly"}), field)
    instruments = [child for child in snapshot if _local(child.tag) == "Instrmt"]
    if len(instruments) != 1:
        raise _fail(f"{field}: expected exactly one direct Instrmt, found {len(instruments)}")
    undlys = [child for child in snapshot if _local(child.tag) == "Undly"]
    if not undlys:
        raise _fail(f"{field}: missing direct Undly deliverable component")
    instrument = instruments[0]
    _reject_children(instrument, frozenset({"Evnt", "Pty"}), f"{field} Instrmt")
    symbol = _present(instrument, "Sym", f"{field} Instrmt")
    if symbol != root_symbol:
        raise _fail(f"{field} Instrmt: Sym {symbol!r} does not match contract root {root_symbol!r}")
    description = _identifier(instrument, "Desc", f"{field} Instrmt")
    if description not in _DESCRIPTIONS:
        raise _fail(f"{field} Instrmt: unsupported Desc {description!r}")
    components = []
    for undly in undlys:
        _reject_children(undly, frozenset({"UndAID"}), f"{field} Undly")
        for alternate in undly:
            _reject_children(alternate, frozenset(), f"{field} Undly UndAID")
        cash_amount_text = undly.get("CashAmt")
        allocation_text = undly.get("AllocPct")
        components.append({
            "symbol": _present(undly, "Sym", f"{field} Undly"),
            "cfi": _undly_cfi(_present(undly, "CFI", f"{field} Undly"), f"{field} Undly CFI"),
            "quantity": _decimal(_attribute(undly, "Qty", f"{field} Undly"),
                                 f"{field} Undly Qty", positive=True),
            "id": undly.get("ID"),
            "src": undly.get("Src"),
            "cash_amount": None if cash_amount_text is None else _decimal(
                cash_amount_text, f"{field} Undly CashAmt", positive=False),
            "cash_type": undly.get("CashTyp"),
            "settlement_method": undly.get("SetMeth"),
            "settlement_status": undly.get("SettlStat"),
            "allocation_percent": _allocation(allocation_text),
            "pending_alternate_ids": [dict(child.attrib) for child in undly],
            "raw_attributes": dict(undly.attrib),
        })
    activation, inactivation, closing = _events(instrument, f"{field} Instrmt")
    return {
        "business_date": _day(_attribute(snapshot, "BizDt", f"{field} BizDt"), f"{field} BizDt"),
        "report_id": _identifier(snapshot, "RptID", f"{field} RptID"),
        "currency": _identifier(snapshot, "Ccy", f"{field} Ccy"),
        "symbol": symbol,
        "description": description,
        "cfi": _cfi(_present(instrument, "CFI", f"{field} Instrmt"), f"{field} Instrmt",
                    frozenset({"C", "P", "X"})),
        "strike_currency": _identifier(instrument, "StrkCcy", f"{field} Instrmt StrkCcy"),
        "premium_multiplier": _decimal(_attribute(instrument, "Mult", f"{field} Instrmt"),
                                       f"{field} Instrmt Mult", positive=True),
        "strike_multiplier": _decimal(_attribute(instrument, "StrkMult", f"{field} Instrmt"),
                                      f"{field} Instrmt StrkMult", positive=True),
        "strike_value": _decimal(_attribute(instrument, "StrkValu", f"{field} Instrmt"),
                                 f"{field} Instrmt StrkValu", positive=True),
        "deliverable_components": components,
        "activation_date": activation,
        "inactivation_date": inactivation,
        "closing_only_exchanges": closing,
        "raw_attributes": dict(instrument.attrib),
        "parties": _parties(instrument),
    }


def _decode_series(snapshot: ElementTree.Element, contract: dict) -> dict:
    field = "SecList"
    _reject_children(snapshot, _SERIES_TAGS, field)
    candidates = []
    instruments = []
    for group in snapshot:
        _reject_children(group, frozenset({"Instrmt"}), f"{field} SecL")
        if group.attrib or len(group) != 1:
            raise _fail(f"{field} SecL: expected one nested Instrmt and no attributes")
        instruments.append(group[0])
    for child in instruments:
        _reject_children(child, frozenset({"Evnt"}), f"{field} Instrmt")
        mat_dt = _day(_attribute(child, "MatDt", f"{field} series"), f"{field} series MatDt")
        mmy = _attribute(child, "MMY", f"{field} series MMY")
        if not _MMY_RE.match(mmy):
            raise _fail(f"{field} series: MMY {mmy!r} is not YYYYMMDD")
        try:
            mmy_date = date(int(mmy[0:4]), int(mmy[4:6]), int(mmy[6:8]))
        except ValueError:
            raise _fail(f"{field} series: MMY {mmy!r} is not a valid calendar day")
        if mmy_date != _as_date(mat_dt):
            raise _fail(f"{field} series: MMY {mmy} disagrees with MatDt {mat_dt}")
        activation, inactivation, closing = _events(child, f"{field} series")
        candidates.append({
            "symbol": _present(child, "Sym", f"{field} series"),
            "maturity_date": mat_dt,
            "mmy": mmy,
            "strike_price": _decimal(_attribute(child, "StrkPx", f"{field} series"),
                                     f"{field} series StrkPx", positive=True),
            "cfi": _cfi(_present(child, "CFI", f"{field} series"), f"{field} series",
                        frozenset({"C", "P"})),
            "report_id": child.get("RptID"),
            "activation_date": activation,
            "inactivation_date": inactivation,
            "closing_only_exchanges": closing,
            "raw_attributes": dict(child.attrib),
        })
    if not candidates:
        raise _fail(f"{field}: contains no series records")
    matches = [item for item in candidates
               if item["symbol"] == contract["root"]
               and item["cfi"][1] == ("C" if contract["right"] == "call" else "P")
               and item["maturity_date"] == contract["expiration"]
               and item["strike_price"] == Decimal(contract["strike"])]
    if not matches:
        raise _fail(f"{field}: no series matches root/right/expiry/strike exactly")
    if len(matches) > 1:
        raise _fail(f"{field}: {len(matches)} series match the same contract; ambiguous even if identical")
    series = matches[0]
    series["business_date"] = _day(_attribute(snapshot, "BizDt", f"{field} BizDt"), f"{field} BizDt")
    series["document_report_id"] = _identifier(snapshot, "RptID", f"{field} RptID")
    series["report_id"] = series["report_id"] or series["document_report_id"]
    series["candidate_count"] = len(candidates)
    return series


def _require_cfi_agreement(product_cfi: str, series_cfi: str) -> None:
    for index, label in ((0, "category"), (2, "exercise style"), (3, "classification"),
                         (4, "settlement"), (5, "standard")):
        if product_cfi[index] != series_cfi[index]:
            raise _fail(f"CFI {label} disagrees: product {product_cfi} vs series {series_cfi}")
    if product_cfi[1] != "X" and product_cfi[1] != series_cfi[1]:
        raise _fail(f"CFI call/put disagrees: product {product_cfi} vs series {series_cfi}")


def _standard_100_share_terms(product: dict, series: dict) -> bool:
    """True only for explicitly parsed standard American equity physical 100-share terms.

    Describes the decoded terms only; it is never an eligibility, admission, or tradability
    judgement, and it is never inferred from root shape or from an absent adjustment memo.
    """
    components = product["deliverable_components"]
    if not (_STANDARD_CFI_RE.match(product["cfi"]) and _STANDARD_CFI_RE.match(series["cfi"])):
        return False
    if product["description"] != "STAN":
        return False
    if product["currency"] != "USD" or product["strike_currency"] != "USD":
        return False
    if product["premium_multiplier"] != Decimal(100) or product["strike_multiplier"] != Decimal(1):
        return False
    if product["strike_value"] != Decimal(100) or len(components) != 1:
        return False
    component = components[0]
    if not _EQUITY_UNDLY_CFI_RE.match(component["cfi"]):
        return False
    if component["quantity"] != Decimal(100):
        return False
    if component["cash_amount"] is not None or component["cash_type"] is not None:
        return False
    return bool(component["symbol"].strip())


def decode_contract_terms(product_xml: bytes, series_xml: bytes, *, contract: dict) -> dict:
    """Decode one SecDef product snapshot and one SecList series snapshot into exact terms.

    Raises TermsDecodeError for malformed, ambiguous, missing, or unsupported terms.
    Deterministic: existing suite identity validator, no clocks, no filesystem or network access, no defaults.
    """
    wanted = _normalize_contract(contract)
    product_snapshot = _parse_snapshot(product_xml, "product_xml", "SecDef")
    series_snapshot = _parse_snapshot(series_xml, "series_xml", "SecList")
    product = _decode_product(product_snapshot, wanted["root"])
    series = _decode_series(series_snapshot, wanted)
    if product["business_date"] != series["business_date"]:
        raise _fail(f"business-date mismatch: product {product['business_date']} vs "
                    f"series {series['business_date']}")
    if product["strike_multiplier"] != Decimal(1):
        raise _fail(f"StrkMult {_canonical(product['strike_multiplier'])} is not 1; "
                    "scaled contract identity is not decoded by this interface")
    _require_cfi_agreement(product["cfi"], series["cfi"])
    exchanges: list = []
    for name in (*product["closing_only_exchanges"], *series["closing_only_exchanges"]):
        if name not in exchanges:
            exchanges.append(name)
    return {
        "schema": SCHEMA,
        "contract": wanted,
        "source_business_date": product["business_date"],
        "product_report_id": product["report_id"],
        "series_report_id": series["report_id"],
        "product_cfi": product["cfi"],
        "series_cfi": series["cfi"],
        "product_description": product["description"],
        "currency": product["currency"],
        "strike_currency": product["strike_currency"],
        "premium_multiplier": _canonical(product["premium_multiplier"]),
        "strike_multiplier": _canonical(product["strike_multiplier"]),
        "strike_value": _canonical(product["strike_value"]),
        "series_strike_price": _canonical(series["strike_price"]),
        "series_maturity_month_year": series["mmy"],
        "deliverable_components": [
            {
                "symbol": component["symbol"],
                "cfi": component["cfi"],
                "quantity": _canonical(component["quantity"]),
                "id": component["id"],
                "src": component["src"],
                "cash_amount": None if component["cash_amount"] is None
                else _canonical(component["cash_amount"]),
                "cash_type": component["cash_type"],
                "settlement_method": component["settlement_method"],
                "settlement_status": component["settlement_status"],
                "allocation_percent": None if component["allocation_percent"] is None
                else _canonical(component["allocation_percent"]),
                "raw_attributes": component["raw_attributes"],
                "pending_alternate_ids": component["pending_alternate_ids"],
            }
            for component in product["deliverable_components"]
        ],
        "product_activation_date": product["activation_date"],
        "product_inactivation_date": product["inactivation_date"],
        "series_activation_date": series["activation_date"],
        "series_inactivation_date": series["inactivation_date"],
        "closing_only_exchanges": exchanges,
        "standard_100_share_terms": _standard_100_share_terms(product, series),
        "date_basis": "LocalMktDate day values; no timezone conversion and no invented timestamps",
        "source_available_at": None,
        "source_observed_at": None,
        "source_authenticated": False,
        "consumer_admitted": False,
        "effective_timestamp_binding": None,
        "inputs": {
            "product": {"sha256": hashlib.sha256(product_xml).hexdigest(), "bytes": len(product_xml)},
            "series": {"sha256": hashlib.sha256(series_xml).hexdigest(), "bytes": len(series_xml)},
        },
        "product_parties": product["parties"],
        "raw_product_attributes": product["raw_attributes"],
        "raw_series_attributes": series["raw_attributes"],
    }
