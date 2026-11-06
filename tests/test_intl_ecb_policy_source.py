"""ECB deposit facility native CSV: one pure parser and its refusals.

Every response in this file is synthetic except the three native rows quoted
verbatim below, which are the exact header and three raw selected rows of the
pinned ECB response (2026-08-28, 2026-09-30 and 2026-11-04).  No live ECB
query is made and no acquisition is attempted: the retained 3,020,522-byte
response is not on this host, so the full ten-thousand-row series is *not*
exercised here.  The composition owner parses the retained bytes once, after
source verification.
"""

from __future__ import annotations

import ast
import csv
import inspect
import io
import json
from datetime import date, timedelta

import pytest

from lib import intl_ecb_policy_source as ecb


# --------------------------------------------------------------------------
# The exact native header and three raw selected rows of the pinned response.
# --------------------------------------------------------------------------

NATIVE_HEADER = (
    "KEY,FREQ,REF_AREA,CURRENCY,PROVIDER_FM,INSTRUMENT_FM,PROVIDER_FM_ID,"
    "DATA_TYPE_FM,TIME_PERIOD,OBS_VALUE,OBS_STATUS,OBS_CONF,OBS_PRE_BREAK,"
    "OBS_COM,TIME_FORMAT,BREAKS,COLLECTION,COMPILING_ORG,DISS_ORG,DOM_SER_IDS,"
    "FM_CONTRACT_TIME,FM_COUPON_RATE,FM_IDENTIFIER,FM_LOT_SIZE,FM_MATURITY,"
    "FM_OUTS_AMOUNT,FM_PUT_CALL,FM_STRIKE_PRICE,PUBL_MU,PUBL_PUBLIC,"
    "UNIT_INDEX_BASE,COMPILATION,COVERAGE,DECIMALS,SOURCE_AGENCY,SOURCE_PUB,"
    "TITLE,TITLE_COMPL,UNIT,UNIT_MULT\n"
)

NATIVE_ROW_1 = (
    'FM.D.U2.EUR.4F.KR.DFR.LEV,D,U2,EUR,4F,KR,DFR,LEV,2026-08-28,2.25,A,F,,,'
    'P1D,,E,4F0,,,,,,,,,,,,,,,,7,,,Deposit facility - date of changes (raw '
    'data) - Level,"Euro area (changing composition) - Key interest rate - '
    'Deposit facility - date of changes (raw data) - Level - Euro, provided '
    'by ECB",PCPA,0\n'
)

NATIVE_ROW_2 = (
    'FM.D.U2.EUR.4F.KR.DFR.LEV,D,U2,EUR,4F,KR,DFR,LEV,2026-09-30,2.5,A,F,,,'
    'P1D,,E,4F0,,,,,,,,,,,,,,,,7,,,Deposit facility - date of changes (raw '
    'data) - Level,"Euro area (changing composition) - Key interest rate - '
    'Deposit facility - date of changes (raw data) - Level - Euro, provided '
    'by ECB",PCPA,0\n'
)

NATIVE_ROW_3 = (
    'FM.D.U2.EUR.4F.KR.DFR.LEV,D,U2,EUR,4F,KR,DFR,LEV,2026-11-04,2.5,A,F,,,'
    'P1D,,E,4F0,,,,,,,,,,,,,,,,7,,,Deposit facility - date of changes (raw '
    'data) - Level,"Euro area (changing composition) - Key interest rate - '
    'Deposit facility - date of changes (raw data) - Level - Euro, provided '
    'by ECB",PCPA,0\n'
)

NATIVE_ROWS = NATIVE_ROW_1 + NATIVE_ROW_2 + NATIVE_ROW_3

#: The same native shape, reduced to the fifteen columns the parser reads.
#: Used where a wide fixture would breach the byte ceiling for no reason.
MINIMAL_HEADER = (
    "KEY,FREQ,REF_AREA,CURRENCY,PROVIDER_FM,INSTRUMENT_FM,PROVIDER_FM_ID,"
    "DATA_TYPE_FM,TIME_PERIOD,OBS_VALUE,OBS_STATUS,OBS_CONF,UNIT,UNIT_MULT,"
    "TIME_FORMAT\n"
)

_HEADER_FIELDS = next(csv.reader(io.StringIO(NATIVE_HEADER)))
_COLUMN_INDEX = {name: position for position, name in enumerate(_HEADER_FIELDS)}


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def _fields(text):
    """Return the CSV fields of one record."""
    return next(csv.reader(io.StringIO(text)))


def _line(fields):
    """Return one CSV record, terminated by a newline."""
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerow(fields)
    return buffer.getvalue()


def _native_row(day="2026-08-28", **overrides):
    """Return one native-width row on ``day``, with the named columns replaced."""
    fields = _fields(NATIVE_ROW_1)
    fields[_COLUMN_INDEX["TIME_PERIOD"]] = day
    for column, value in overrides.items():
        fields[_COLUMN_INDEX[column]] = value
    return _line(fields)


def _minimal_row(date_text, value="2.25", status="A", confidentiality="F"):
    """Return one narrow row carrying only the fifteen read columns."""
    return _line(
        [
            "FM.D.U2.EUR.4F.KR.DFR.LEV", "D", "U2", "EUR", "4F", "KR", "DFR",
            "LEV", date_text, value, status, confidentiality, "PCPA", "0", "P1D",
        ]
    )


def _parse(rows, header=NATIVE_HEADER):
    """Parse one native response built from ``header`` and ``rows``."""
    return ecb.parse_ecb_policy_csv((header + rows).encode("utf-8"))


# --------------------------------------------------------------------------
# The verbatim native rows
# --------------------------------------------------------------------------


def test_the_verbatim_native_rows_parse_to_their_native_values():
    parsed = _parse(NATIVE_ROWS)
    assert parsed["series_id"] == "D.U2.EUR.4F.KR.DFR.LEV"
    assert parsed["market_id"] == "EZ"
    assert parsed["instrument_id"] == "deposit_facility"
    assert parsed["unit"] == "percent"
    assert parsed["frequency"] == "D"
    assert [
        (observation["date"], observation["value"], observation["status"])
        for observation in parsed["observations"]
    ] == [
        ("2026-08-28", 2.25, "observed"),
        ("2026-09-30", 2.5, "observed"),
        ("2026-11-04", 2.5, "observed"),
    ]


def test_the_native_rows_keep_their_raw_status_and_confidentiality():
    parsed = _parse(NATIVE_ROWS)
    for observation in parsed["observations"]:
        assert observation["source_status_raw"] == "A"
        assert observation["source_confidentiality_raw"] == "F"


def test_the_native_percent_is_returned_unscaled_and_undifferenced():
    parsed = _parse(NATIVE_ROWS)
    assert parsed["unit"] == "percent"
    assert [observation["value"] for observation in parsed["observations"]] == [
        2.25,
        2.5,
        2.5,
    ]


def test_the_row_builder_reproduces_the_verbatim_native_row():
    assert _native_row() == NATIVE_ROW_1


def test_the_observations_are_sorted_by_date():
    parsed = _parse(NATIVE_ROW_3 + NATIVE_ROW_1 + NATIVE_ROW_2)
    assert [observation["date"] for observation in parsed["observations"]] == [
        "2026-08-28",
        "2026-09-30",
        "2026-11-04",
    ]


def test_no_date_is_invented_and_no_value_is_carried_forward():
    parsed = _parse(NATIVE_ROW_1 + _native_row(TIME_PERIOD="2026-06-30",
                                                OBS_VALUE="3"))
    assert [observation["date"] for observation in parsed["observations"]] == [
        "2026-06-30",
        "2026-08-28",
    ]
    assert [observation["value"] for observation in parsed["observations"]] == [
        3.0,
        2.25,
    ]


# --------------------------------------------------------------------------
# Withheld, provisional, confidential, unknown and missing values
# --------------------------------------------------------------------------

WITHHELD_CASES = [
    ("C", "F", "2.5"),
    ("A", "C", "2.5"),
    ("P", "F", "2.5"),
    ("A", "P", "2.5"),
    ("E", "F", "2.5"),
    ("X", "F", "2.5"),
    ("A", "X", "2.5"),
    ("", "F", "2.5"),
    ("A", "", "2.5"),
    ("A", "F", ""),
]


@pytest.mark.parametrize("status, confidentiality, value", WITHHELD_CASES)
def test_a_withheld_observation_carries_no_number(status, confidentiality,
                                                 value):
    parsed = _parse(NATIVE_ROW_1 + _native_row(
        day="2026-12-01", OBS_STATUS=status, OBS_CONF=confidentiality,
        OBS_VALUE=value))
    withheld = parsed["observations"][1]
    assert withheld["value"] is None
    assert withheld["value"] != 0
    assert withheld["status"] == "withheld"
    assert withheld["source_status_raw"] == status
    assert withheld["source_confidentiality_raw"] == confidentiality


def test_the_observed_rows_of_a_withheld_response_are_untouched():
    parsed = _parse(NATIVE_ROW_1 + _native_row(day="2026-12-01",
                                                OBS_STATUS="C"))
    assert parsed["observations"][0]["value"] == 2.25
    assert parsed["observations"][0]["status"] == "observed"


@pytest.mark.parametrize("value, expected", [
    ("0", 0.0),
    ("0.0", 0.0),
    ("-0.5", -0.5),
    ("-2.5", -2.5),
])
def test_zero_and_negative_native_values_are_preserved(value, expected):
    parsed = _parse(NATIVE_ROW_1 + _native_row(day="2026-12-01",
                                                OBS_VALUE=value))
    observation = parsed["observations"][1]
    assert observation["value"] == expected
    assert observation["status"] == "observed"


def test_a_padded_status_code_is_the_same_code_and_is_kept_raw():
    parsed = _parse(NATIVE_ROW_1 + _native_row(day="2026-12-01",
                                                OBS_STATUS=" A "))
    observation = parsed["observations"][1]
    assert observation["value"] == 2.25
    assert observation["source_status_raw"] == " A "


# --------------------------------------------------------------------------
# Dimensions, units and multipliers -- checked on every row
# --------------------------------------------------------------------------

WRONG_DIMENSIONS = [
    ("KEY", "FM.D.U2.EUR.4F.KR.MRO.LEV"),
    ("FREQ", "M"),
    ("REF_AREA", "U1"),
    ("CURRENCY", "USD"),
    ("PROVIDER_FM", "5F"),
    ("INSTRUMENT_FM", "MR"),
    ("PROVIDER_FM_ID", "MR"),
    ("DATA_TYPE_FM", "AVG"),
    ("UNIT", "PCPB"),
    ("UNIT_MULT", "1"),
    ("TIME_FORMAT", "P1M"),
]


@pytest.mark.parametrize("column, value", WRONG_DIMENSIONS)
def test_every_row_must_carry_the_pinned_dimensions(column, value):
    # The wrong dimension is on the LAST row: this is not a first-row check.
    rows = NATIVE_ROW_1 + NATIVE_ROW_2 + _native_row(**{column: value})
    with pytest.raises(ValueError):
        _parse(rows)


def test_a_second_source_inside_one_response_is_rejected():
    rows = NATIVE_ROW_1 + _native_row(PROVIDER_FM="5F", PROVIDER_FM_ID="MR")
    with pytest.raises(ValueError):
        _parse(rows)


def test_a_changed_unit_or_multiplier_is_rejected():
    with pytest.raises(ValueError):
        _parse(NATIVE_ROW_1 + _native_row(UNIT="PCPB"))
    with pytest.raises(ValueError):
        _parse(NATIVE_ROW_1 + _native_row(UNIT_MULT="1"))


# --------------------------------------------------------------------------
# Header structure and ragged rows
# --------------------------------------------------------------------------


def test_a_duplicate_column_header_is_rejected():
    header = NATIVE_HEADER.replace("OBS_VALUE,", "OBS_VALUE,OBS_VALUE,", 1)
    with pytest.raises(ValueError, match="duplicate column header"):
        _parse(NATIVE_ROWS, header=header)


def test_a_missing_column_header_is_rejected():
    header = NATIVE_HEADER.replace("OBS_STATUS,", "", 1)
    with pytest.raises(ValueError, match="missing column header"):
        _parse(NATIVE_ROWS, header=header)


def test_a_ragged_row_with_too_few_fields_is_rejected():
    short = _line(_fields(NATIVE_ROW_2)[:-1])
    with pytest.raises(ValueError, match="ragged row"):
        _parse(NATIVE_ROW_1 + short)


def test_a_ragged_row_with_too_many_fields_is_rejected():
    long = NATIVE_ROW_2.rstrip("\n") + ",one field too many\n"
    with pytest.raises(ValueError, match="ragged row"):
        _parse(NATIVE_ROW_1 + long)


def test_the_native_metadata_columns_are_accepted_and_ignored():
    # The verbatim native header already carries forty columns, of which the
    # parser reads fifteen; none of the rest is surfaced.
    parsed = _parse(NATIVE_ROWS)
    assert len(_HEADER_FIELDS) == 40
    assert set(parsed["observations"][0]) == {
        "date",
        "value",
        "status",
        "source_status_raw",
        "source_confidentiality_raw",
    }


def test_an_extra_column_is_accepted_and_ignored():
    header = NATIVE_HEADER.replace("UNIT_MULT\n", "UNIT_MULT,NEW_METADATA_COLUMN\n")
    rows = "".join(
        line.rstrip("\n") + ",ignored\n" for line in NATIVE_ROWS.splitlines()
    )
    parsed = _parse(rows, header=header)
    assert len(parsed["observations"]) == 3
    assert parsed["observations"][0]["value"] == 2.25


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------


def test_a_duplicate_date_is_rejected():
    with pytest.raises(ValueError, match="duplicate observation date"):
        _parse(NATIVE_ROW_1 + NATIVE_ROW_1)


@pytest.mark.parametrize("malformed", [
    "2026-8-28",
    "28-08-2026",
    "20260828",
    "2026-08-28T00:00:00",
    "",
    "not-a-date",
])
def test_a_malformed_date_is_rejected(malformed):
    with pytest.raises(ValueError):
        _parse(NATIVE_ROW_1 + _native_row(TIME_PERIOD=malformed))


def test_an_impossible_calendar_date_is_rejected():
    with pytest.raises(ValueError, match="invalid calendar date"):
        _parse(NATIVE_ROW_1 + _native_row(TIME_PERIOD="2026-02-30"))


# --------------------------------------------------------------------------
# Numbers
# --------------------------------------------------------------------------


@pytest.mark.parametrize("malformed", [
    "2,25",
    "2.5%",
    "two point five",
    "1_0",
    "0x1p3",
    "nan",
    "NaN",
    "inf",
    "-inf",
    "Infinity",
    "1e999",
    "True",
    "false",
    "yes",
])
def test_a_malformed_or_nonfinite_number_is_rejected(malformed):
    with pytest.raises(ValueError):
        _parse(NATIVE_ROW_1 + _native_row(OBS_VALUE=malformed))


def test_a_malformed_number_is_rejected_even_on_a_withheld_row():
    with pytest.raises(ValueError):
        _parse(NATIVE_ROW_1 + _native_row(OBS_STATUS="C", OBS_VALUE="nan"))


def test_a_number_is_never_emitted_as_a_nan_or_an_infinity():
    parsed = _parse(NATIVE_ROWS)
    for observation in parsed["observations"]:
        assert observation["value"] is None or (
            observation["value"] == observation["value"]
            and observation["value"] not in (float("inf"), float("-inf"))
        )


# --------------------------------------------------------------------------
# Bounds
# --------------------------------------------------------------------------


def test_a_payload_above_the_byte_ceiling_is_rejected():
    assert ecb.MAX_INPUT_BYTES == 8 * 1024 * 1024
    with pytest.raises(ValueError, match="byte ceiling"):
        ecb.parse_ecb_policy_csv(b"x" * (ecb.MAX_INPUT_BYTES + 1))


def test_the_retained_native_size_sits_inside_the_byte_ceiling():
    assert 3_020_522 < ecb.MAX_INPUT_BYTES


def test_more_rows_than_the_row_ceiling_is_rejected():
    dates = [
        (date(1999, 1, 1) + timedelta(days=offset)).isoformat()
        for offset in range(ecb.MAX_ROWS + 1)
    ]
    payload = (
        MINIMAL_HEADER
        + "".join(_minimal_row(day) for day in dates)
    ).encode("utf-8")
    # The row ceiling is what bites here, not the byte ceiling.
    assert len(payload) <= ecb.MAX_INPUT_BYTES
    with pytest.raises(ValueError, match="row ceiling"):
        ecb.parse_ecb_policy_csv(payload)


def test_exactly_the_row_ceiling_is_accepted():
    dates = [
        (date(1999, 1, 1) + timedelta(days=offset)).isoformat()
        for offset in range(ecb.MAX_ROWS)
    ]
    payload = (
        MINIMAL_HEADER
        + "".join(_minimal_row(day) for day in dates)
    ).encode("utf-8")
    parsed = ecb.parse_ecb_policy_csv(payload)
    assert len(parsed["observations"]) == ecb.MAX_ROWS


def test_a_response_of_the_pinned_shape_and_size_is_parsed():
    # A synthetic stand-in with the row count and the row width of the
    # retained response (ten thousand one hundred seventy native rows, about
    # three megabytes).  This is NOT the retained response: it says nothing
    # about the contents of the real bytes.
    first = date(1999, 1, 1)
    rows = [
        _native_row(day=(first + timedelta(days=offset)).isoformat())
        for offset in range(10_170)
    ]
    payload = (NATIVE_HEADER + "".join(rows)).encode("utf-8")
    assert len(payload) < ecb.MAX_INPUT_BYTES
    parsed = ecb.parse_ecb_policy_csv(payload)
    assert len(parsed["observations"]) == 10_170
    assert parsed["observations"][0]["date"] == "1999-01-01"
    assert parsed["observations"][0]["value"] == 2.25


# --------------------------------------------------------------------------
# Encoding, line endings and CSV mechanics
# --------------------------------------------------------------------------


def test_a_utf8_bom_is_permitted():
    payload = b"\xef\xbb\xbf" + (NATIVE_HEADER + NATIVE_ROWS).encode("utf-8")
    parsed = ecb.parse_ecb_policy_csv(payload)
    assert len(parsed["observations"]) == 3


def test_crlf_line_endings_are_read():
    payload = (NATIVE_HEADER + NATIVE_ROWS).replace("\n", "\r\n").encode("utf-8")
    parsed = ecb.parse_ecb_policy_csv(payload)
    assert len(parsed["observations"]) == 3
    assert parsed["observations"][0]["value"] == 2.25


def test_a_newline_inside_a_quoted_field_stays_one_field():
    row = _native_row(
        day="2026-12-01",
        TITLE_COMPL="Euro area (changing composition)\nwith a newline, provided by ECB",
    )
    parsed = _parse(NATIVE_ROW_1 + row)
    assert len(parsed["observations"]) == 2


def test_a_trailing_blank_line_is_tolerated():
    parsed = _parse(NATIVE_ROWS + "\n")
    assert len(parsed["observations"]) == 3


def test_an_interior_blank_line_is_rejected():
    with pytest.raises(ValueError, match="blank row"):
        _parse(NATIVE_ROW_1 + "\n" + NATIVE_ROW_2)


def test_a_payload_that_is_not_utf8_is_rejected():
    with pytest.raises(ValueError):
        ecb.parse_ecb_policy_csv(b"\xff\xfe\x00KEY,FREQ\n")


def test_an_empty_payload_is_rejected():
    with pytest.raises(ValueError):
        ecb.parse_ecb_policy_csv(b"")


def test_a_payload_with_no_observation_row_is_rejected():
    with pytest.raises(ValueError):
        ecb.parse_ecb_policy_csv(NATIVE_HEADER.encode("utf-8"))


def test_a_non_bytes_payload_is_rejected():
    with pytest.raises(TypeError):
        ecb.parse_ecb_policy_csv("KEY,FREQ\n")


# --------------------------------------------------------------------------
# Purity
# --------------------------------------------------------------------------


def test_no_publication_or_vintage_clock_is_fabricated():
    parsed = _parse(NATIVE_ROWS)
    assert set(parsed) == {
        "series_id",
        "market_id",
        "instrument_id",
        "unit",
        "frequency",
        "observations",
    }
    for observation in parsed["observations"]:
        assert set(observation) == {
            "date",
            "value",
            "status",
            "source_status_raw",
            "source_confidentiality_raw",
        }


def test_the_parsed_result_is_json_serialisable_without_nan():
    parsed = _parse(NATIVE_ROWS)
    assert json.loads(json.dumps(parsed, allow_nan=False))["observations"][0][
        "value"
    ] == 2.25


def test_the_parser_is_a_pure_function_of_its_bytes():
    payload = (NATIVE_HEADER + NATIVE_ROWS).encode("utf-8")
    assert ecb.parse_ecb_policy_csv(payload) == ecb.parse_ecb_policy_csv(payload)


def test_the_parser_installs_no_global_state():
    limit = csv.field_size_limit()
    _parse(NATIVE_ROWS)
    assert csv.field_size_limit() == limit


def test_the_parser_never_acquires_reads_a_clock_or_needs_a_third_party_package():
    source = inspect.getsource(ecb)
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.update(
                "%s.%s" % (module, alias.name) if module else alias.name
                for alias in node.names
            )
    forbidden = (
        "socket", "http", "urllib", "requests", "httpx", "aiohttp", "urllib3",
        "ftplib", "smtplib", "telnetlib", "xmlrpc", "pandas", "numpy", "polars",
        "pyarrow",
    )
    assert not [name for name in imported if name.startswith(forbidden)]
    assert "urlopen" not in source
    assert "datetime.now" not in source and "utcnow" not in source
    assert "time.time" not in source
    assert "open(" not in source
    assert "os.environ" not in source
