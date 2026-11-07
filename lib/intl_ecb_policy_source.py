"""Pure parser for the ECB deposit facility (DFR) native CSV response.

Public API
----------
``parse_ecb_policy_csv(raw: bytes) -> dict``
    Bytes in, plain dictionary out.  Nothing else is exported.

What this module is
--------------------
The ECB Data Portal publishes the *deposit facility* -- key
``D.U2.EUR.4F.KR.DFR.LEV`` of dataset ``FM`` -- as an SDMX-CG CSV response.
The level is a nominal, officially administered policy rate quoted in
**percent** (``OBS_VALUE="2.25"`` means 2.25%); it is *not* a market
bid/offer, *not* an effective or midpoint rate and *not* a compounded rate.
This module therefore produces a *nominal official administered policy point*
and nothing else: the native number is returned unchanged -- no scaling, no
differencing, no rebasing, no rounding of the published level.

The parser is deliberately narrow and strict:

* it accepts exactly one shape of document -- the ECB SDMX-CG CSV whose
  header carries the pinned dimension columns -- and raises
  :class:`ValueError` for anything else;
* it checks the recognised dimensions on **every** row, so a second source,
  a second instrument, a changed unit or a changed multiplier cannot ride
  along inside one response;
* it never fetches, back-fills, interpolates, forward-fills, revises or
  otherwise manufactures an observation or a date -- every returned date is a
  date the provider supplied, and there is no nearest-date lookup;
* it states no publication, vintage or update clock at all, because the
  native response states none: the returned dictionary carries no such field
  and the parser never derives one from a date or from the header;
* it treats a withheld, confidential, provisional or unknown-code value as
  ``value is None`` with ``status == "withheld"`` -- such a value is never
  admitted as a number, and never as a zero;
* it rejects a malformed or nonfinite numeric literal wherever it appears,
  including on a row whose status would withhold the value anyway, so a
  nonfinite number can never enter the output by any route.

Only the two native codes that the pinned response actually uses may carry a
number: ``OBS_STATUS == "A"`` together with ``OBS_CONF == "F"``.  Every other
status or confidentiality code -- including a code this module does not
document -- is withheld, because an undocumented code grants nothing.

Purity
------
``parse_ecb_policy_csv`` is a pure function of its argument.  It performs no
network access, no filesystem access, no clock read and no environment
lookup; it mutates nothing outside its own arguments; it installs no global
state; and it imports no third-party package.  Only the Python standard
library is used -- the CSV is read with :mod:`csv`, so a newline inside a
quoted field is read as one field.

Rights
------
This module mints no rights, licences, qualifications, admissions, grants or
entitlements of any kind.  Whether the ECB data may be reused is a question
for the consuming programme and its own review, not for this file; the
reuse of this source is qualified separately from this parser.  Nothing here
states or implies an official-release freshness promise, and nothing here
describes any "original known" vintage of the series -- only what the
supplied bytes say.
"""

from __future__ import annotations

import csv
import io
import math
import re
from collections import Counter
from datetime import date as _calendar_date
from decimal import Decimal, InvalidOperation

__all__ = ["parse_ecb_policy_csv"]


# --------------------------------------------------------------------------
# Fixed identity of the series this module is allowed to parse.
# --------------------------------------------------------------------------

#: Series identity of the produced series (the key without the ``FM`` dataset
#: prefix), as the existing ECB deposit carrier names it.
SERIES_ID = "D.U2.EUR.4F.KR.DFR.LEV"

#: The dataset-qualified key every row of the pinned response carries.
DATASET_KEY = "FM.D.U2.EUR.4F.KR.DFR.LEV"

#: Fixed output identity of the produced series.
MARKET_ID = "EZ"
INSTRUMENT_ID = "deposit_facility"
UNIT = "percent"
FREQUENCY = "D"

#: Hard input ceiling.  The retained native response is about three
#: megabytes; anything larger is not a plausible provider response.
MAX_INPUT_BYTES = 8 * 1024 * 1024

#: Hard observation ceiling.  The retained native response carries about ten
#: thousand observations; anything larger is not a plausible provider
#: response.
MAX_ROWS = 32_000

_STATUS_OBSERVED = "observed"
_STATUS_WITHHELD = "withheld"

#: The only native status / confidentiality pair that may carry a number.
#: The pinned response reports ``OBS_STATUS="A"`` and ``OBS_CONF="F"`` on
#: every one of its rows; any other code is withheld.
_ADMITTED_STATUS = "A"
_ADMITTED_CONF = "F"

#: Dimensions that must hold, on every row, for the response to be the
#: pinned series.  The pairs are ``(column, expected value)``.
_REQUIRED_DIMENSIONS = (
    ("KEY", DATASET_KEY),
    ("FREQ", "D"),
    ("REF_AREA", "U2"),
    ("CURRENCY", "EUR"),
    ("PROVIDER_FM", "4F"),
    ("INSTRUMENT_FM", "KR"),
    ("PROVIDER_FM_ID", "DFR"),
    ("DATA_TYPE_FM", "LEV"),
    ("UNIT", "PCPA"),
    ("UNIT_MULT", "0"),
    ("TIME_FORMAT", "P1D"),
)

#: Columns that must be present in the header.  Any further column the
#: native response carries (its metadata columns) is accepted and ignored:
#: it is never surfaced, because the returned shape is fixed.
_REQUIRED_COLUMNS = (
    "KEY",
    "FREQ",
    "REF_AREA",
    "CURRENCY",
    "PROVIDER_FM",
    "INSTRUMENT_FM",
    "PROVIDER_FM_ID",
    "DATA_TYPE_FM",
    "TIME_FORMAT",
    "TIME_PERIOD",
    "OBS_VALUE",
    "OBS_STATUS",
    "OBS_CONF",
    "UNIT",
    "UNIT_MULT",
)

_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_NUMERIC_RE = re.compile(
    r"^[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$"
)


# --------------------------------------------------------------------------
# Small helpers.
# --------------------------------------------------------------------------


def _as_bytes(raw) -> bytes:
    """Return ``raw`` as :class:`bytes` or raise :class:`TypeError`."""
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, (bytearray, memoryview)):
        return bytes(raw)
    raise TypeError("raw must be bytes, got %s" % type(raw).__name__)


def _decode(payload: bytes) -> str:
    """Return the payload as text; a UTF-8 BOM is permitted and stripped."""
    try:
        return payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "ECB deposit facility response rejected: payload is not valid UTF-8: %s"
            % exc
        ) from exc


def _read_records(text: str) -> list:
    """Return the CSV records of ``text``; malformed CSV is rejected."""
    stream = io.StringIO(text, newline="")
    try:
        return list(csv.reader(stream, strict=True))
    except csv.Error as exc:
        raise ValueError(
            "ECB deposit facility response rejected: malformed CSV: %s" % exc
        ) from exc


def _header_index(header: list) -> dict:
    """Return the column index of every header name of ``header``."""
    names = [cell.strip() for cell in header]
    counts = Counter(names)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    if duplicates:
        raise ValueError(
            "ECB deposit facility response rejected: duplicate column header(s) %s"
            % ", ".join(repr(name) for name in duplicates)
        )
    missing = [column for column in _REQUIRED_COLUMNS if column not in counts]
    if missing:
        raise ValueError(
            "ECB deposit facility response rejected: missing column header(s) %s"
            % ", ".join(repr(name) for name in missing)
        )
    return {name: position for position, name in enumerate(names)}


def _parse_date(text: str) -> str:
    """Validate an economic date of the form ``YYYY-MM-DD`` and return it."""
    if not _DATE_RE.match(text or ""):
        raise ValueError(
            "ECB deposit facility response rejected: malformed observation date "
            "%r, expected YYYY-MM-DD" % (text,)
        )
    try:
        _calendar_date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            "ECB deposit facility response rejected: invalid calendar date %r"
            % (text,)
        ) from exc
    return text


def _parse_numeric(text: str) -> float:
    """Return the finite float value of a native numeric literal.

    The literal must be a plain decimal number.  ``nan``, ``inf``,
    ``infinity``, hexadecimal floats, digit-group underscores and any
    boolean-like word are not numbers here: they are rejected rather than
    coerced, so a nonfinite value can never enter the output.
    """
    stripped = text.strip()
    if not _NUMERIC_RE.match(stripped):
        raise ValueError(
            "ECB deposit facility response rejected: malformed numeric value %r"
            % (text,)
        )
    try:
        number = Decimal(stripped)
    except InvalidOperation as exc:
        raise ValueError(
            "ECB deposit facility response rejected: malformed numeric value %r"
            % (text,)
        ) from exc
    if not number.is_finite():
        raise ValueError(
            "ECB deposit facility response rejected: nonfinite numeric value %r"
            % (text,)
        )
    try:
        value = float(number)
    except (OverflowError, ValueError) as exc:
        raise ValueError(
            "ECB deposit facility response rejected: numeric value out of range %r"
            % (text,)
        ) from exc
    if not math.isfinite(value):
        raise ValueError(
            "ECB deposit facility response rejected: nonfinite numeric value %r"
            % (text,)
        )
    return value


# --------------------------------------------------------------------------
# Public API.
# --------------------------------------------------------------------------


def parse_ecb_policy_csv(raw: bytes) -> dict:
    """Parse an ECB deposit facility native CSV response.

    Parameters
    ----------
    raw:
        The raw bytes of the retained provider response.

    Returns
    -------
    dict
        A dictionary with the fixed keys ``series_id``, ``market_id``,
        ``instrument_id``, ``unit``, ``frequency`` and ``observations``.

        ``observations`` holds one dictionary per supplied data row, with the
        keys ``date`` (``YYYY-MM-DD``, exactly as supplied), ``value`` (a
        finite float, or ``None``), ``status`` (``"observed"`` or
        ``"withheld"``), ``source_status_raw`` (the provider's ``OBS_STATUS``
        cell exactly as supplied) and ``source_confidentiality_raw`` (the
        provider's ``OBS_CONF`` cell exactly as supplied), sorted by date.

        A value is admitted only when the row reports ``OBS_STATUS == "A"``
        and ``OBS_CONF == "F"`` and carries a plain finite number.  Every
        other status or confidentiality code, and an allowed row whose value
        is missing or blank, yields ``value is None`` and
        ``status == "withheld"``.  The raw status and confidentiality cells
        are preserved on every row, so a withheld row still says why.

        The returned dictionary states no publication, vintage or update
        clock: the native response carries none, and none is derived from a
        date or from the header.

    Raises
    ------
    ValueError
        If the payload is not a UTF-8 CSV of the pinned series -- for example
        a missing or duplicated column header, a ragged row, a wrong
        dimension, unit or multiplier on any row, a malformed or duplicate
        date, a malformed or nonfinite number, an empty payload or one with
        no observation row -- or if it is larger than
        :data:`MAX_INPUT_BYTES` or carries more than :data:`MAX_ROWS`
        observation rows.
    TypeError
        If ``raw`` is not bytes-like.
    """
    payload = _as_bytes(raw)

    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError(
            "ECB deposit facility response rejected: payload of %d bytes "
            "exceeds the %d byte ceiling" % (len(payload), MAX_INPUT_BYTES)
        )
    if not payload.strip():
        raise ValueError(
            "ECB deposit facility response rejected: empty payload"
        )

    records = _read_records(_decode(payload))
    if not records:
        raise ValueError(
            "ECB deposit facility response rejected: empty payload"
        )

    header = records[0]
    if len(header) == 1 and not header[0].strip():
        raise ValueError(
            "ECB deposit facility response rejected: empty header row"
        )
    index = _header_index(header)

    rows = records[1:]
    # A trailing blank line is tolerated; a blank line inside the data block
    # is not a record and is rejected as a ragged row below.
    while rows and not rows[-1]:
        rows.pop()
    for position, row in enumerate(rows, start=2):
        if not row:
            raise ValueError(
                "ECB deposit facility response rejected: blank row %d"
                % position
            )
    if not rows:
        raise ValueError(
            "ECB deposit facility response rejected: no observation rows"
        )
    if len(rows) > MAX_ROWS:
        raise ValueError(
            "ECB deposit facility response rejected: %d observation rows "
            "exceed the %d row ceiling" % (len(rows), MAX_ROWS)
        )

    observations = []
    seen_dates = set()
    for position, row in enumerate(rows, start=2):
        if len(row) != len(header):
            raise ValueError(
                "ECB deposit facility response rejected: ragged row %d: "
                "expected %d fields, found %d"
                % (position, len(header), len(row))
            )
        for column, expected in _REQUIRED_DIMENSIONS:
            actual = row[index[column]]
            if actual.strip() != expected:
                raise ValueError(
                    "ECB deposit facility response rejected: row %d carries "
                    "%s=%r, expected %r"
                    % (position, column, actual, expected)
                )

        date = _parse_date(row[index["TIME_PERIOD"]])
        if date in seen_dates:
            raise ValueError(
                "ECB deposit facility response rejected: duplicate observation "
                "date %r" % (date,)
            )
        seen_dates.add(date)

        status_raw = row[index["OBS_STATUS"]]
        confidentiality_raw = row[index["OBS_CONF"]]
        value_raw = row[index["OBS_VALUE"]]

        # A malformed or nonfinite literal is rejected wherever it appears:
        # the parser never emits a nonfinite number and never drops one
        # silently.  A missing or blank value is not a malformed value.
        value = None if not value_raw.strip() else _parse_numeric(value_raw)

        admitted = (
            status_raw.strip() == _ADMITTED_STATUS
            and confidentiality_raw.strip() == _ADMITTED_CONF
            and value is not None
        )
        observations.append(
            {
                "date": date,
                "value": value if admitted else None,
                "status": _STATUS_OBSERVED if admitted else _STATUS_WITHHELD,
                "source_status_raw": status_raw,
                "source_confidentiality_raw": confidentiality_raw,
            }
        )

    observations.sort(key=lambda observation: observation["date"])

    return {
        "series_id": SERIES_ID,
        "market_id": MARKET_ID,
        "instrument_id": INSTRUMENT_ID,
        "unit": UNIT,
        "frequency": FREQUENCY,
        "observations": observations,
    }
