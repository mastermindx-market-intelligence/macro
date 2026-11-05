"""Unit tests for :mod:`lib.intl_boe_source`.

The documents below are synthetic.  They reproduce the *shape* of the Bank of
England IADB ``IUDBEDR`` response -- GESMES envelope, ``agg_series`` payload
namespace, ``Cube`` / ``SERIES_COM`` children, ``TIME`` / ``OBS_VALUE`` /
``OBS_CONF`` / ``LAST_UPDATED`` attributes -- without embedding the retained
production response.
"""

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from lib.intl_boe_source import parse_bank_rate_xml  # noqa: E402

GESMES_NS = "http://www.gesmes.org/xml/2002-08-01"
AGG_SERIES_NS = (
    "https://web.prod.iadb.ext.az.cloud.bankofengland.co.uk/website/agg_series"
)

EXPECTED_SCODE = "IUDBEDR"
EXPECTED_DESC = "Official Bank Rate"


# --------------------------------------------------------------------------
# Builders.
# --------------------------------------------------------------------------


def _row(
    date,
    value="3.75",
    conf="N",
    last_updated="2026-01-05 09:30:00",
    extra="",
):
    """Return one observation ``Cube`` element as text."""
    attributes = ['TIME="%s"' % date]
    if value is not None:
        attributes.append('OBS_VALUE="%s"' % value)
    if conf is not None:
        attributes.append('OBS_CONF="%s"' % conf)
    if last_updated is not None:
        attributes.append('LAST_UPDATED="%s"' % last_updated)
    if extra:
        attributes.append(extra)
    return "<Cube %s/>" % " ".join(attributes)


def _document(
    rows=(),
    *,
    scode=EXPECTED_SCODE,
    desc=EXPECTED_DESC,
    country="",
    freq_code="D",
    freq_name="Daily",
    include_freq=True,
    notes=("note one",),
    include_notes=True,
    cat_val="RBASER",
    cat_desc=EXPECTED_DESC,
    include_cat=True,
    envelope_ns=GESMES_NS,
    payload_ns=AGG_SERIES_NS,
    extra_series_cube=False,
):
    """Return a synthetic ``IUDBEDR`` response as bytes."""
    parts = ['<?xml version="1.0" encoding="ISO-8859-1"?>']
    parts.append('<Envelope xmlns="%s">' % envelope_ns)

    series_attributes = ['xmlns="%s"' % payload_ns]
    if scode is not None:
        series_attributes.append('SCODE="%s"' % scode)
    if desc is not None:
        series_attributes.append('DESC="%s"' % desc)
    series_attributes.append('COUNTRY="%s"' % country)
    series_attributes.append('CONCAT="Official Bank Rate "')
    parts.append("<Cube %s>" % " ".join(series_attributes))

    if include_freq:
        parts.append(
            '<Cube FREQ_NAME="%s" FREQ_CODE="%s" FREQ_ORD="1"/>'
            % (freq_name, freq_code)
        )
    if include_notes:
        for note in notes:
            parts.append("<SERIES_COM>%s</SERIES_COM>" % note)
    parts.append(
        '<Cube SERIES_DEF="notes and definitions for Wholesale:Bank of England '
        'base rate" DEF_LOC="http://www.bankofengland.co.uk/statistics/pages/'
        'iadb/notesiadb/wholesale_baserate.aspx"/>'
    )
    if include_cat:
        parts.append(
            '<Cube CAT_NAME="INSTRUMENTS" CAT_VAL="%s" VAL_DESC="%s" CAT_ORD="7"/>'
            % (cat_val, cat_desc)
        )
    parts.append('<Cube FIRST_OBS="1975-01-02" LAST_OBS="2026-11-02">')
    parts.extend(rows)
    parts.append("</Cube>")
    parts.append("</Cube>")

    if extra_series_cube:
        parts.append(
            '<Cube xmlns="%s" SCODE="%s" DESC="%s" COUNTRY="" '
            'CONCAT="Official Bank Rate "><Cube FREQ_NAME="Daily" FREQ_CODE="D" '
            'FREQ_ORD="1"/></Cube>' % (payload_ns, EXPECTED_SCODE, EXPECTED_DESC)
        )

    parts.append("</Envelope>")
    return "".join(parts).encode("utf-8")


# --------------------------------------------------------------------------
# Happy path: identity, metadata, notes, observation shape.
# --------------------------------------------------------------------------


def test_fixed_identity_and_metadata():
    raw = _document([_row("2026-01-02")])
    result = parse_bank_rate_xml(raw)

    assert set(result) == {
        "series_id",
        "market_id",
        "instrument_id",
        "unit",
        "frequency",
        "notes",
        "observations",
    }
    assert result["series_id"] == "IUDBEDR"
    assert result["market_id"] == "GB"
    assert result["instrument_id"] == "bank_rate"
    assert result["unit"] == "percent"
    assert result["frequency"] == "D"


def test_notes_are_the_literal_series_com_strings():
    # The provider transmits the quotation marks as ``&amp;quot;``; the parsed
    # note therefore carries the literal text ``&quot;``.
    note_source = (
        "On the 16th September 1992, the UK leaves the European Exchange Rate "
        "Mechanism.  Please see:\n"
        "http://www.bankofengland.co.uk/archive/Documents/historicpubs/qb/1992/"
        "qb92q4382398.pdf for further explanation on &amp;quot;Black "
        "Wednesday&amp;quot;."
    )
    note_expected = note_source.replace("&amp;quot;", "&quot;")
    raw = _document([_row("2026-01-02")], notes=("Prior to May 2012 ...", note_source))
    result = parse_bank_rate_xml(raw)

    assert result["notes"] == ["Prior to May 2012 ...", note_expected]
    # The literal provider text is preserved: no HTML rendering, no second
    # round of entity expansion and no whitespace munging.
    assert "&quot;Black Wednesday&quot;" in result["notes"][1]
    assert '"Black Wednesday"' not in result["notes"][1]
    assert "\n" in result["notes"][1]
    assert "<" not in result["notes"][1]


def test_observation_fields_and_source_clock_are_retained():
    raw = _document(
        [
            _row("2026-01-02", value="3.75", last_updated="2026-01-05 09:30:00"),
            _row("2026-11-02", value="3.75", last_updated="2026-11-03 09:30:00"),
        ]
    )
    result = parse_bank_rate_xml(raw)

    assert result["observations"] == [
        {
            "date": "2026-01-02",
            "value": 3.75,
            "status": "observed",
            "source_updated_raw": "2026-01-05 09:30:00",
        },
        {
            "date": "2026-11-02",
            "value": 3.75,
            "status": "observed",
            "source_updated_raw": "2026-11-03 09:30:00",
        },
    ]


def test_missing_last_updated_is_null_and_is_not_borrowed():
    raw = _document([_row("2026-01-02", last_updated=None)])
    observation = parse_bank_rate_xml(raw)["observations"][0]

    assert observation["source_updated_raw"] is None
    assert observation["value"] == 3.75
    assert observation["status"] == "observed"


def test_observations_are_sorted_by_date():
    raw = _document(
        [
            _row("2026-11-02"),
            _row("2026-01-05"),
            _row("2026-01-02"),
        ]
    )
    dates = [o["date"] for o in parse_bank_rate_xml(raw)["observations"]]
    assert dates == ["2026-01-02", "2026-01-05", "2026-11-02"]


def test_parsing_is_deterministic():
    raw = _document([_row("2026-01-02"), _row("2026-01-05")])
    assert parse_bank_rate_xml(raw) == parse_bank_rate_xml(raw)


# --------------------------------------------------------------------------
# Withheld / provisional values.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "row",
    [
        _row("2026-01-02", value="3.75", conf="Y"),
        _row("2026-01-02", value="3.75", conf=None),
        _row("2026-01-02", value="3.75", conf="X"),
        _row("2026-01-02", value="3.75", conf="n"),
        _row("2026-01-02", value=None, conf="N"),
        _row("2026-01-02", value="..", conf="N"),
        _row("2026-01-02", value="", conf="N"),
        _row("2026-01-02", value="3.75", conf="N", extra='OBS_STATUS="P"'),
        _row("2026-01-02", value="3.75", conf="N", extra='OBS_STATUS="S"'),
        _row("2026-01-02", value="3.75", conf="N", extra='OBS_PRE="true"'),
    ],
)
def test_withheld_values_are_never_admitted_as_numbers(row):
    observation = parse_bank_rate_xml(_document([row]))["observations"][0]

    assert observation["status"] == "withheld"
    assert observation["value"] is None


# --------------------------------------------------------------------------
# Numeric values.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_value,expected",
    [
        ("3.75", 3.75),
        ("0", 0.0),
        ("0.00", 0.0),
        ("-0.25", -0.25),
        ("-12.5", -12.5),
        ("1e-2", 0.01),
        (" 3.75 ", 3.75),
        (".5", 0.5),
    ],
)
def test_finite_numbers_including_zero_and_negative_are_retained(raw_value, expected):
    raw = _document([_row("2026-01-02", value=raw_value)])
    observation = parse_bank_rate_xml(raw)["observations"][0]

    assert observation["status"] == "observed"
    assert observation["value"] == expected


@pytest.mark.parametrize(
    "raw_value",
    ["abc", "NaN", "nan", "Infinity", "-Infinity", "1_000", "3,75", "3.75%", "1e", "0x10"],
)
def test_malformed_or_non_finite_numbers_are_rejected(raw_value):
    raw = _document([_row("2026-01-02", value=raw_value)])
    with pytest.raises(ValueError):
        parse_bank_rate_xml(raw)


# --------------------------------------------------------------------------
# Identity, frequency and namespace rejections.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"scode": "IUDBEDX"}, "SCODE"),
        ({"scode": None}, "SCODE"),
        ({"desc": "SONIA"}, "description"),
        ({"desc": None}, "description"),
        ({"country": "US"}, "COUNTRY"),
        ({"cat_val": "IUDBEDR"}, "CAT_VAL"),
        ({"cat_desc": "Bank Rate"}, "VAL_DESC"),
        ({"extra_series_cube": True}, "exactly one series Cube"),
    ],
)
def test_wrong_series_identity_is_rejected(kwargs, match):
    with pytest.raises(ValueError, match=match):
        parse_bank_rate_xml(_document([_row("2026-01-02")], **kwargs))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"freq_code": "M"},
        {"freq_name": "Monthly"},
        {"include_freq": False},
    ],
)
def test_non_daily_or_missing_frequency_is_rejected(kwargs):
    with pytest.raises(ValueError, match="FREQ"):
        parse_bank_rate_xml(_document([_row("2026-01-02")], **kwargs))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"envelope_ns": "http://example.invalid/envelope"},
        {"payload_ns": "https://example.invalid/agg_series"},
    ],
)
def test_unexpected_namespaces_are_rejected(kwargs):
    with pytest.raises(ValueError):
        parse_bank_rate_xml(_document([_row("2026-01-02")], **kwargs))


# --------------------------------------------------------------------------
# Malformed payloads.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"   \n  ",
        b"not xml at all",
        b"<Envelope><Cube",
        b"<html><head><title>Error</title></head><body>500</body></html>",
        b"<html>\n<head><title>Service Unavailable</title></head>\n</html>",
        b"<?xml version='1.0'?><Envelope xmlns='http://www.gesmes.org/xml/2002-08-01'/>",
    ],
)
def test_non_iudb_payloads_are_rejected(payload):
    with pytest.raises(ValueError):
        parse_bank_rate_xml(payload)


@pytest.mark.parametrize(
    "payload",
    [
        b"<!DOCTYPE Envelope [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>"
        b"<Envelope xmlns='http://www.gesmes.org/xml/2002-08-01'/>",
        b"<!DOCTYPE Envelope SYSTEM 'http://example.invalid/e.dtd'>"
        b"<Envelope xmlns='http://www.gesmes.org/xml/2002-08-01'/>",
        b"<?xml version='1.0'?><!DOCTYPE foo [<!ENTITY boom 'bang'>]>"
        b"<Envelope xmlns='http://www.gesmes.org/xml/2002-08-01'>&boom;</Envelope>",
    ],
)
def test_dtd_and_entity_declarations_are_rejected(payload):
    with pytest.raises(ValueError):
        parse_bank_rate_xml(payload)


def test_oversized_payload_is_rejected():
    with pytest.raises(ValueError, match="ceiling"):
        parse_bank_rate_xml(b"<Envelope/>" + b" " * (2 * 1024 * 1024))


# --------------------------------------------------------------------------
# Date and duplicate rejections.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "date",
    [
        "2026-02-30",
        "2026-13-01",
        "2026-1-2",
        "02-01-2026",
        "2026-01-02T00:00:00",
        "2026-01-02 09:30:00",
        "20260102",
        "",
    ],
)
def test_malformed_or_invalid_dates_are_rejected(date):
    with pytest.raises(ValueError):
        parse_bank_rate_xml(_document([_row(date)]))


@pytest.mark.parametrize(
    "rows",
    [
        [_row("2026-01-02"), _row("2026-01-02")],
        [_row("2026-01-02", value="3.75"), _row("2026-01-02", value="4.00")],
    ],
)
def test_duplicate_dates_are_rejected(rows):
    with pytest.raises(ValueError, match="duplicate observation date"):
        parse_bank_rate_xml(_document(rows))


def test_observation_outside_the_series_is_rejected():
    raw = (
        '<?xml version="1.0" encoding="ISO-8859-1"?>'
        '<Envelope xmlns="%s">'
        '<Cube xmlns="%s" SCODE="%s" DESC="%s" COUNTRY="" CONCAT="">'
        '<Cube FREQ_NAME="Daily" FREQ_CODE="D" FREQ_ORD="1"/>'
        "</Cube>"
        '<Cube xmlns="%s" TIME="2026-01-02" OBS_VALUE="3.75" OBS_CONF="N"/>'
        "</Envelope>"
        % (
            GESMES_NS,
            AGG_SERIES_NS,
            EXPECTED_SCODE,
            EXPECTED_DESC,
            AGG_SERIES_NS,
        )
    ).encode("utf-8")

    with pytest.raises(ValueError, match="outside the IUDBEDR series"):
        parse_bank_rate_xml(raw)

@pytest.mark.parametrize('encoding', ['utf-16-le', 'utf-16-be'])
def test_encoded_dtd_is_rejected_before_entity_expansion(encoding):
    document = _document([_row('2026-01-02')]).decode('utf-8')
    declaration, body = document.split('?>', 1)
    payload = ('<?xml version="1.0" encoding="UTF-16"?>'
               '<!DOCTYPE Envelope [<!ENTITY note "injected-note">]>'
               + body.replace('note one', '&note;')).encode(encoding)
    with pytest.raises(ValueError, match='document type|entity'):
        parse_bank_rate_xml(payload)

@pytest.mark.parametrize('code', ['A', 'C', 'F', 'L'])
def test_undocumented_observation_status_never_becomes_observed(code):
    result = parse_bank_rate_xml(_document([
        _row('2026-01-02', extra='OBS_STATUS="%s"' % code)]))
    assert result['observations'][0]['value'] is None
    assert result['observations'][0]['status'] == 'withheld'
