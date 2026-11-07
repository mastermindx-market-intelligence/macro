"""Pure parser for the Bank of England IADB ``IUDBEDR`` (Official Bank Rate) XML.

Public API
----------
``parse_bank_rate_xml(raw: bytes) -> dict``
    Bytes in, plain dictionary out.  Nothing else is exported.

What this module is
--------------------
The Bank of England IADB publishes the *Official Bank Rate* under SCODE
``IUDBEDR``.  It is a nominal, officially administered policy rate quoted in
**percent** (the Bank Rate chart axis is a percent axis; ``OBS_VALUE="3.75"``
means 3.75%).  It is *not* SONIA, *not* an effective/midpoint rate and *not* a
market bid/offer.  This module therefore produces a *nominal official
administered policy point* and nothing else.

The parser is deliberately narrow and strict:

* it accepts exactly one shape of document -- the GESMES envelope carrying a
  single ``IUDBEDR`` series in the Bank of England ``agg_series`` namespace --
  and raises :class:`ValueError` for anything else;
* it never fetches, back-fills, interpolates, forward-fills, revises or
  otherwise manufactures an observation or a date;
* it keeps the *economic* date (``TIME``) and the *source* clock
  (``LAST_UPDATED``) strictly apart, and never re-uses the collection time,
  the HTTP time or the local wall clock in place of either;
* it treats a withheld / confidential / suppressed / provisional-only value as
  ``value is None`` with ``status == "withheld"`` -- such a value is never
  admitted as a number.

Purity
------
``parse_bank_rate_xml`` is a pure function of its argument.  It performs no
network access, no filesystem access, no clock read and no environment
lookup; it mutates nothing outside its own arguments; it installs no global
state and it imports no third-party package.  Only the Python standard library
is used.

Rights
------
This module mints no rights, licences, qualifications, admissions, grants or
entitlements of any kind.  The Bank of England database is made available
subject to the terms published at https://www.bankofengland.co.uk/legal (the
database is published under the Open Government Licence); whether and how the
underlying data may be reused is a question for the consuming programme and
its own review, not for this file.  Nothing here states or implies an
official-release freshness promise, and nothing here describes any
"original known" vintage of the series -- only what the supplied bytes say.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, InvalidOperation

__all__ = ["parse_bank_rate_xml"]


# --------------------------------------------------------------------------
# Fixed identity of the series this module is allowed to parse.
# --------------------------------------------------------------------------

#: GESMES envelope namespace of the Bank of England IADB response.
GESMES_NS = "http://www.gesmes.org/xml/2002-08-01"

#: Payload namespace of the Bank of England ``agg_series`` cube tree.  This is
#: the namespace carried by the retained provider response; no other payload
#: namespace is accepted.
AGG_SERIES_NS = (
    "https://web.prod.iadb.ext.az.cloud.bankofengland.co.uk/website/agg_series"
)

EXPECTED_SCODE = "IUDBEDR"
EXPECTED_DESC = "Official Bank Rate"
EXPECTED_FREQ_CODE = "D"
EXPECTED_FREQ_NAME = "Daily"
EXPECTED_CAT_VAL = "RBASER"
EXPECTED_COUNTRY = ("", "GB")

#: Fixed output identity of the produced series.
SERIES_ID = "IUDBEDR"
MARKET_ID = "GB"
INSTRUMENT_ID = "bank_rate"
UNIT = "percent"
FREQUENCY = "D"

#: Hard input ceiling.  A retained ``IUDBEDR`` response is a few tens of
#: kilobytes; anything larger is not a plausible provider response.
MAX_INPUT_BYTES = 2 * 1024 * 1024

_STATUS_OBSERVED = "observed"
_STATUS_WITHHELD = "withheld"

# The retained IUDBEDR provider schema has no OBS_STATUS attribute. No
# undocumented code is granted a settled meaning; any supplied status is
# withheld until an actual provider contract is added.


#: Attribute values that mark a boolean-ish flag as set.
_TRUE_LITERALS = frozenset({"true", "1", "yes", "y"})

#: ``OBS_STATUS`` attribute name; the other two are provisional markers.
_OBS_STATUS_ATTR = "OBS_STATUS"
_PROVISIONAL_ATTRS = ("OBS_PRE", "OBS_PROVISIONAL", "PROVISIONAL")

_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_NUMERIC_RE = re.compile(
    r"^[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$"
)
_DOCTYPE_RE = re.compile(rb"<!DOCTYPE", re.IGNORECASE)
_ENTITY_RE = re.compile(rb"<!ENTITY", re.IGNORECASE)

#: Accepted shapes of the provider's naive source clock.  The clock is never
#: given a time zone and is never converted to UTC.
_SOURCE_CLOCK_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f")


# --------------------------------------------------------------------------
# Small helpers.
# --------------------------------------------------------------------------


def _qn(namespace: str, tag: str) -> str:
    """Return the ElementTree qualified name for ``tag`` in ``namespace``."""
    return "{%s}%s" % (namespace, tag)


def _element_text(element: ET.Element) -> str:
    """Return the literal text content of ``element`` (no HTML rendering)."""
    return "".join(element.itertext())


def _local_name(name: str) -> str:
    """Return the local part of a possibly qualified attribute name."""
    return name.rsplit("}", 1)[-1]


def _as_bytes(raw) -> bytes:
    """Return ``raw`` as :class:`bytes` or raise :class:`TypeError`."""
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, (bytearray, memoryview)):
        return bytes(raw)
    raise TypeError(
        "raw must be bytes, got %s" % type(raw).__name__
    )


class _NoDTDTreeBuilder(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        # Parser-level callback covers UTF-16 as well as ASCII-compatible XML;
        # byte substring matching alone does not protect alternate encodings.
        raise ValueError("IUDBEDR response rejected: document type or entity declarations are not accepted")


def _xml_parser() -> ET.XMLParser:
    return ET.XMLParser(target=_NoDTDTreeBuilder())


def _reject_dtd(payload: bytes) -> None:
    """Reject payloads carrying a DTD or entity declaration."""
    if _DOCTYPE_RE.search(payload) or _ENTITY_RE.search(payload):
        raise ValueError(
            "IUDBEDR response rejected: document type or entity declarations "
            "are not accepted"
        )


def _parse_xml(payload: bytes) -> ET.Element:
    """Parse ``payload`` into an element tree, mapping failures to ValueError."""
    try:
        return ET.fromstring(payload, parser=_xml_parser())
    except ET.ParseError as exc:
        raise ValueError("IUDBEDR response rejected: malformed XML: %s" % exc) from exc
    except UnicodeDecodeError as exc:
        raise ValueError(
            "IUDBEDR response rejected: undecodable XML: %s" % exc
        ) from exc


def _require_envelope(root: ET.Element) -> None:
    """Require the GESMES envelope root element."""
    expected = _qn(GESMES_NS, "Envelope")
    if root.tag != expected:
        raise ValueError(
            "IUDBEDR response rejected: unexpected root element %r, expected %r "
            "(an HTML error page or any non-IADB document is not an IUDBEDR "
            "response)" % (root.tag, expected)
        )


def _series_cubes(root: ET.Element) -> list:
    """Return every payload cube that carries a ``SCODE`` attribute."""
    cube = _qn(AGG_SERIES_NS, "Cube")
    return [el for el in root.iter() if el.tag == cube and "SCODE" in el.attrib]


def _select_series(root: ET.Element) -> ET.Element:
    """Return the single ``IUDBEDR`` series cube."""
    cubes = _series_cubes(root)
    if len(cubes) != 1:
        raise ValueError(
            "IUDBEDR response rejected: expected exactly one series Cube with a "
            "SCODE attribute, found %d" % len(cubes)
        )
    return cubes[0]


def _require_series_identity(series: ET.Element) -> None:
    """Require the series to be exactly ``IUDBEDR`` / Official Bank Rate."""
    scode = series.get("SCODE")
    if scode != EXPECTED_SCODE:
        raise ValueError(
            "IUDBEDR response rejected: unexpected SCODE %r, expected %r"
            % (scode, EXPECTED_SCODE)
        )
    desc = series.get("DESC")
    if desc != EXPECTED_DESC:
        raise ValueError(
            "IUDBEDR response rejected: unexpected series description %r, "
            "expected %r" % (desc, EXPECTED_DESC)
        )
    country = series.get("COUNTRY")
    if country is not None and country.strip() not in EXPECTED_COUNTRY:
        raise ValueError(
            "IUDBEDR response rejected: unexpected COUNTRY %r" % (country,)
        )


def _require_daily_frequency(series: ET.Element) -> None:
    """Require a daily (``FREQ_CODE == "D"``) series."""
    cube = _qn(AGG_SERIES_NS, "Cube")
    freq_cubes = [el for el in series.iter() if el.tag == cube and "FREQ_CODE" in el.attrib]
    if not freq_cubes:
        raise ValueError(
            "IUDBEDR response rejected: missing frequency Cube (no FREQ_CODE)"
        )
    for el in freq_cubes:
        code = el.get("FREQ_CODE")
        if code != EXPECTED_FREQ_CODE:
            raise ValueError(
                "IUDBEDR response rejected: unexpected FREQ_CODE %r, expected %r"
                % (code, EXPECTED_FREQ_CODE)
            )
        name = el.get("FREQ_NAME")
        if name != EXPECTED_FREQ_NAME:
            raise ValueError(
                "IUDBEDR response rejected: unexpected FREQ_NAME %r, expected %r"
                % (name, EXPECTED_FREQ_NAME)
            )


def _require_instrument(series: ET.Element) -> None:
    """Require the declared instrument to be the Official Bank Rate.

    SCODE and DESC establish identity. When an INSTRUMENTS category cube
    is supplied, require its description to agree; absence creates no claim
    about provider coverage or another instrument.
    """
    cube = _qn(AGG_SERIES_NS, "Cube")
    for el in series.iter():
        if el.tag != cube or el.get("CAT_NAME") != "INSTRUMENTS":
            continue
        cat_val = el.get("CAT_VAL")
        if cat_val != EXPECTED_CAT_VAL:
            raise ValueError(
                "IUDBEDR response rejected: unexpected instrument CAT_VAL %r, "
                "expected %r" % (cat_val, EXPECTED_CAT_VAL)
            )
        val_desc = el.get("VAL_DESC")
        if val_desc != EXPECTED_DESC:
            raise ValueError(
                "IUDBEDR response rejected: unexpected instrument VAL_DESC %r, "
                "expected %r" % (val_desc, EXPECTED_DESC)
            )


def _collect_notes(series: ET.Element) -> list:
    """Return the literal ``SERIES_COM`` strings of the series, in order."""
    tag = _qn(AGG_SERIES_NS, "SERIES_COM")
    return [_element_text(child) for child in series if child.tag == tag]


def _parse_date(text: str) -> str:
    """Validate an economic date of the form ``YYYY-MM-DD``."""
    if not _DATE_RE.match(text or ""):
        raise ValueError(
            "IUDBEDR response rejected: malformed observation date %r, expected "
            "YYYY-MM-DD" % (text,)
        )
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            "IUDBEDR response rejected: invalid calendar date %r" % (text,)
        ) from exc
    return text


def _parse_source_clock(raw: str) -> str:
    """Validate the provider's naive source clock and return it unchanged."""
    for fmt in _SOURCE_CLOCK_FORMATS:
        try:
            datetime.strptime(raw, fmt)
        except ValueError:
            continue
        return raw
    raise ValueError(
        "IUDBEDR response rejected: malformed LAST_UPDATED source clock %r"
        % (raw,)
    )


def _parse_numeric(text: str) -> float:
    """Return the finite float value of a provider numeric literal."""
    stripped = text.strip()
    try:
        number = Decimal(stripped)
    except InvalidOperation as exc:
        raise ValueError(
            "IUDBEDR response rejected: malformed numeric value %r" % (text,)
        ) from exc
    if not number.is_finite():
        raise ValueError(
            "IUDBEDR response rejected: non-finite numeric value %r" % (text,)
        )
    try:
        value = float(number)
    except (OverflowError, ValueError) as exc:
        raise ValueError(
            "IUDBEDR response rejected: numeric value out of range %r" % (text,)
        ) from exc
    if not math.isfinite(value):
        raise ValueError(
            "IUDBEDR response rejected: non-finite numeric value %r" % (text,)
        )
    return value


def _is_provisional(observation: ET.Element) -> bool:
    """Return True when the observation is flagged provisional/suppressed."""
    for name, raw in observation.attrib.items():
        local = _local_name(name)
        text = raw.strip()
        if local == _OBS_STATUS_ATTR:
            return True
        elif local in _PROVISIONAL_ATTRS:
            if text.lower() in _TRUE_LITERALS:
                return True
    return False


def _observation_value(observation: ET.Element):
    """Return ``(value, status)`` for one observation cube.

    A numeric value is admitted only when the observation is explicitly
    disclosed (``OBS_CONF="N"``), is not flagged provisional or suppressed,
    and carries a plain, finite numeric literal.  Everything else -- withheld
    or confidential observations, an unknown confidentiality code, a missing
    value, the SDMX missing marker ``..`` and provisional-only values -- is
    reported as ``(None, "withheld")``.
    """
    conf = observation.get("OBS_CONF")
    if conf is None or conf.strip() != "N":
        return None, _STATUS_WITHHELD
    if _is_provisional(observation):
        return None, _STATUS_WITHHELD
    raw_value = observation.get("OBS_VALUE")
    if raw_value is None:
        return None, _STATUS_WITHHELD
    text = raw_value.strip()
    if text in ("", ".."):
        return None, _STATUS_WITHHELD
    if not _NUMERIC_RE.match(text):
        raise ValueError(
            "IUDBEDR response rejected: malformed numeric value %r" % (raw_value,)
        )
    return _parse_numeric(text), _STATUS_OBSERVED


def _collect_observations(root: ET.Element, series: ET.Element) -> list:
    """Return the sorted observation list of the series."""
    cube = _qn(AGG_SERIES_NS, "Cube")
    inside = {id(el) for el in series.iter()}
    observation_cubes = [
        el for el in root.iter() if el.tag == cube and "TIME" in el.attrib
    ]

    observations = []
    seen = {}
    for el in observation_cubes:
        if id(el) not in inside:
            raise ValueError(
                "IUDBEDR response rejected: observation Cube outside the IUDBEDR "
                "series"
            )
        date = _parse_date(el.get("TIME"))
        if date in seen:
            raise ValueError(
                "IUDBEDR response rejected: duplicate observation date %r" % (date,)
            )
        seen[date] = True
        value, status = _observation_value(el)
        raw_clock = el.get("LAST_UPDATED")
        if raw_clock is None or raw_clock.strip() == "":
            source_updated_raw = None
        else:
            source_updated_raw = _parse_source_clock(raw_clock)
        observations.append(
            {
                "date": date,
                "value": value,
                "status": status,
                "source_updated_raw": source_updated_raw,
            }
        )

    observations.sort(key=lambda observation: observation["date"])
    return observations


# --------------------------------------------------------------------------
# Public API.
# --------------------------------------------------------------------------


def parse_bank_rate_xml(raw: bytes) -> dict:
    """Parse a Bank of England ``IUDBEDR`` (Official Bank Rate) XML response.

    Parameters
    ----------
    raw:
        The raw bytes of the retained provider response.

    Returns
    -------
    dict
        A dictionary with the fixed keys ``series_id``, ``market_id``,
        ``instrument_id``, ``unit``, ``frequency``, ``notes`` and
        ``observations``.

        ``notes`` holds the literal ``SERIES_COM`` strings of the response, in
        document order.  ``observations`` holds one dictionary per observation
        with the keys ``date`` (``YYYY-MM-DD``), ``value`` (a finite float, or
        ``None``), ``status`` (``"observed"`` or ``"withheld"``) and
        ``source_updated_raw`` (the provider's ``LAST_UPDATED`` string exactly
        as supplied, or ``None`` when the provider supplied none), sorted by
        date.

    Raises
    ------
    ValueError
        If the payload is not exactly one ``IUDBEDR`` daily series in the
        expected namespaces, or is malformed, or carries a document type or
        entity declaration, or is not XML at all, or is larger than
        :data:`MAX_INPUT_BYTES`.
    TypeError
        If ``raw`` is not bytes-like.
    """
    payload = _as_bytes(raw)

    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError(
            "IUDBEDR response rejected: payload of %d bytes exceeds the %d byte "
            "ceiling" % (len(payload), MAX_INPUT_BYTES)
        )
    if not payload.strip():
        raise ValueError("IUDBEDR response rejected: empty payload")

    _reject_dtd(payload)
    root = _parse_xml(payload)
    _require_envelope(root)

    series = _select_series(root)
    _require_series_identity(series)
    _require_daily_frequency(series)
    _require_instrument(series)

    notes = _collect_notes(series)
    observations = _collect_observations(root, series)

    return {
        "series_id": SERIES_ID,
        "market_id": MARKET_ID,
        "instrument_id": INSTRUMENT_ID,
        "unit": UNIT,
        "frequency": FREQUENCY,
        "notes": notes,
        "observations": observations,
    }
