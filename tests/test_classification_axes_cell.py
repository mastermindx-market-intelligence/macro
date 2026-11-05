"""AxisCell v1 contract (WS:GMI-THEME-GRAPH Taxonomy V2, lane L00).

Display/context records only. These tests pin the frozen cell shape, the
status/reason/value rules, subject-id grammar reused from
``engine.theme_graph.identity``, and agreement with the JSON Schema on the
violations the schema can express. Forbidden value keys and the point-in-time
rule are Python-only; the schema is required to leave them alone.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.classification_axes import cell as cell_mod
from engine.classification_axes.cell import (
    AXES,
    FORBIDDEN_VALUE_KEY_WORDS,
    LABELS,
    REASON_CODES,
    SCHEMA_VERSION,
    STATUSES,
    THEME_SUBJECT_RE,
    AxisCellError,
    available,
    company_parts,
    make_cell,
    missing,
    parse_subject,
    to_json,
    validate_cell,
)
from engine.theme_graph.identity import (
    NON_BASKET_SUITES,
    SUITE_MARKET,
    basket_node_id,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "classification_axes" / "axis_cell.v1.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)

# Frozen table. The module constants are checked against this, not the other
# way around, so a drifted REASON_CODES cannot make the matrix agree with itself.
EXPECTED_REASONS: dict[str, tuple[str, ...]] = {
    "available": (),
    "unknown": ("value_missing", "history_not_supported"),
    "unavailable": ("owner_missing", "owner_unavailable", "owner_degraded"),
    "stale": ("owner_stale",),
    "not_applicable": ("not_applicable", "retired_entity", "superseded_entity"),
    "rights_blocked": ("rights_blocked",),
}
EXPECTED_AXES = (
    "sic_industry",
    "geography",
    "macro_sensitivity",
    "business_model",
    "lifecycle",
    "value_chain",
)
EXPECTED_STATUSES = (
    "available",
    "unknown",
    "unavailable",
    "stale",
    "not_applicable",
    "rights_blocked",
)
EXPECTED_LABELS = frozenset({
    "proxy_not_micro_membership",
    "NO_MAPPING",
    "source_local",
    "house_curated",
    "read_time_composition",
})
CELL_KEYS = frozenset({
    "schema_version",
    "axis",
    "subject_id",
    "status",
    "reason_code",
    "value",
    "unit",
    "observed_at",
    "effective_at",
    "as_of",
    "freshness",
    "quality",
    "labels",
    "source",
    "provenance",
    "rights_context",
})
SOURCE = {
    "owner": "engine.classification_axes.cell",
    "artifact": "engine/classification_axes/cell.py",
    "field": None,
}
AS_OF = "2026-10-11"

_ALL_CODES: tuple[object, ...] = (None,) + tuple(
    dict.fromkeys(code for codes in EXPECTED_REASONS.values() for code in codes)
)
ALLOWED: list[tuple[str, object]] = []
DISALLOWED: list[tuple[str, object]] = []
for _status, _codes in EXPECTED_REASONS.items():
    _allowed = set(_codes)
    for _code in _ALL_CODES:
        _ok = _code is None if _status == "available" else _code in _allowed
        (ALLOWED if _ok else DISALLOWED).append((_status, _code))


def _pair_id(pair: tuple[str, object]) -> str:
    status, reason = pair
    return f"{status}-{'null' if reason is None else reason}"


def _raw(**overrides: object) -> dict:
    """A hand-built cell. Defaults are an available reading with a scalar value."""
    cell: dict = {
        "schema_version": SCHEMA_VERSION,
        "axis": "sic_industry",
        "subject_id": "co:us:AAPL",
        "status": "available",
        "reason_code": None,
        "value": "3674",
        "unit": None,
        "observed_at": None,
        "effective_at": None,
        "as_of": AS_OF,
        "freshness": None,
        "quality": "display_only",
        "labels": [],
        "source": dict(SOURCE),
        "provenance": [],
        "rights_context": None,
    }
    cell.update(overrides)
    return cell


def _value_for(status: str, *, stale_value: object = "3674") -> object:
    if status == "available":
        return "3674"
    if status == "stale":
        return stale_value
    return None


def _built(status: str, reason: object, **overrides: object) -> dict:
    value = overrides.pop("value", _value_for(status))
    kwargs = dict(
        axis="sic_industry",
        subject_id="co:us:AAPL",
        status=status,
        reason_code=reason,
        value=value,
        as_of=AS_OF,
        source=dict(SOURCE),
    )
    kwargs.update(overrides)
    return make_cell(**kwargs)


def test_constants_match_the_frozen_contract():
    assert SCHEMA_VERSION == "axis_cell.v1"
    assert AXES == EXPECTED_AXES
    assert STATUSES == EXPECTED_STATUSES
    assert REASON_CODES == EXPECTED_REASONS
    assert LABELS == EXPECTED_LABELS
    assert FORBIDDEN_VALUE_KEY_WORDS == (
        "weight", "share", "score", "rank", "exposure_pct",
    )
    assert THEME_SUBJECT_RE.pattern == r"^theme:[a-z0-9][a-z0-9_]{1,62}$"
    assert issubclass(AxisCellError, ValueError)
    assert len(ALLOWED) == 11
    assert len(DISALLOWED) == 55
    assert "quality" not in inspect.signature(make_cell).parameters


@pytest.mark.parametrize("status,reason", ALLOWED, ids=[_pair_id(pair) for pair in ALLOWED])
def test_allowed_pair_builds_and_validates(status, reason):
    cell = _built(status, reason)
    assert set(cell) == CELL_KEYS
    assert cell["status"] == status
    assert cell["reason_code"] == reason
    assert cell["quality"] == "display_only"
    assert cell["schema_version"] == "axis_cell.v1"
    assert validate_cell(cell) == []
    assert VALIDATOR.is_valid(cell)


@pytest.mark.parametrize("status,reason", DISALLOWED, ids=[_pair_id(pair) for pair in DISALLOWED])
def test_disallowed_pair_refused_by_make_cell_and_validate_cell(status, reason):
    value = _value_for(status)
    raw = _raw(status=status, reason_code=reason, value=value)
    problems = validate_cell(raw)
    assert problems
    assert any("reason" in problem for problem in problems)
    with pytest.raises(AxisCellError) as caught:
        _built(status, reason, value=value)
    assert caught.value.problems
    assert not VALIDATOR.is_valid(raw)


@pytest.mark.parametrize("value", ["3674", None])
def test_stale_accepts_value_or_null(value):
    cell = _built("stale", "owner_stale", value=value)
    assert cell["value"] is value or cell["value"] == value
    assert validate_cell(cell) == []
    assert VALIDATOR.is_valid(cell)


@pytest.mark.parametrize(
    "status,reason",
    [
        ("unknown", "value_missing"),
        ("unknown", "history_not_supported"),
        ("unavailable", "owner_missing"),
        ("unavailable", "owner_unavailable"),
        ("unavailable", "owner_degraded"),
        ("not_applicable", "not_applicable"),
        ("not_applicable", "retired_entity"),
        ("not_applicable", "superseded_entity"),
        ("rights_blocked", "rights_blocked"),
    ],
)
def test_non_stale_missing_status_rejects_a_value(status, reason):
    raw = _raw(status=status, reason_code=reason, value="present")
    assert any("value" in problem for problem in validate_cell(raw))
    with pytest.raises(AxisCellError):
        _built(status, reason, value="present")
    assert not VALIDATOR.is_valid(raw)


def test_available_rejects_null_value():
    raw = _raw(status="available", reason_code=None, value=None)
    assert any("value" in problem for problem in validate_cell(raw))
    with pytest.raises(AxisCellError):
        _built("available", None, value=None)
    assert not VALIDATOR.is_valid(raw)


@pytest.mark.parametrize(
    "value",
    ["text", 3, 1.5, True, False, ["a", 1], {"count": 3, "member_count": 2}],
)
def test_json_value_types_are_allowed_when_available(value):
    cell = _built("available", None, value=value)
    assert validate_cell(cell) == []
    assert VALIDATOR.is_valid(cell)
    assert json.loads(to_json(cell))["value"] == value


def test_forbidden_key_nested_in_a_list_inside_a_dict_is_refused():
    raw = _raw(value={"rows": [{"Exposure_Pct": 1}]})
    problems = validate_cell(raw)
    assert problems
    assert any("Exposure_Pct" in problem or "forbidden" in problem.lower() for problem in problems)
    with pytest.raises(AxisCellError):
        _built("available", None, value={"rows": [{"Exposure_Pct": 1}]})


def test_count_keys_are_allowed():
    cell = _built("available", None, value={"count": 3, "member_count": 2})
    assert validate_cell(cell) == []


@pytest.mark.parametrize(
    "key",
    ["Weight", "SHARE", "score", "rank", "exposure_pct", "share_of_voice", "My_Rank"],
)
def test_forbidden_key_words_are_case_insensitive_substrings(key):
    raw = _raw(value={"outer": [{key: 1}]})
    assert validate_cell(raw)
    with pytest.raises(AxisCellError):
        _built("available", None, value={key: 1})


def test_plain_exposure_and_member_count_are_not_forbidden():
    cell = _built("available", None, value={"exposure": "sector", "member_count": 2})
    assert validate_cell(cell) == []


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf"), {"rows": [float("nan")]}, {"x": float("inf")}],
)
def test_nan_and_inf_are_refused(value):
    raw = _raw(value=value)
    problems = validate_cell(raw)
    assert problems
    assert any("JSON" in problem or "serialis" in problem for problem in problems)
    with pytest.raises(AxisCellError):
        _built("available", None, value=value)


@pytest.mark.parametrize(
    "status,reason,observed_at,effective_at,ok",
    [
        ("available", None, "2026-10-12", None, False),
        ("available", None, None, "2026-10-12", False),
        ("available", None, "2026-10-12T00:00:00Z", None, False),
        ("stale", "owner_stale", "2026-10-12", None, False),
        ("stale", "owner_stale", None, "2026-10-12T15:00:00+00:00", False),
        ("available", None, "2026-10-11", None, True),
        ("available", None, "2026-10-11T23:59:59Z", None, True),
        ("available", None, "2026-10-10", "2026-10-11", True),
        ("unknown", "value_missing", "2026-10-12", "2026-12-01", True),
        ("unavailable", "owner_missing", "2026-10-12", None, True),
        ("not_applicable", "retired_entity", None, "2027-01-01", True),
    ],
)
def test_point_in_time_rule(status, reason, observed_at, effective_at, ok):
    value = _value_for(status)
    raw = _raw(
        status=status,
        reason_code=reason,
        value=value,
        observed_at=observed_at,
        effective_at=effective_at,
    )
    problems = validate_cell(raw)
    if ok:
        assert problems == []
        assert VALIDATOR.is_valid(raw)
    else:
        assert any("after as_of" in problem for problem in problems)
        with pytest.raises(AxisCellError):
            _built(
                status,
                reason,
                value=value,
                observed_at=observed_at,
                effective_at=effective_at,
            )


@pytest.mark.parametrize("as_of", ["2026-13-01", "20261001", None, "2026-02-30", "2026-04-31", "2026-10-11T00:00:00Z", ""])
def test_bad_as_of_is_refused(as_of):
    raw = _raw(as_of=as_of)
    problems = validate_cell(raw)
    assert problems
    assert any("as_of" in problem for problem in problems)
    with pytest.raises(AxisCellError):
        make_cell(
            axis="sic_industry",
            subject_id="co:us:AAPL",
            status="available",
            value="3674",
            as_of=as_of,
            source=dict(SOURCE),
        )
    assert not VALIDATOR.is_valid(raw)


@pytest.mark.parametrize("as_of", ["2024-02-29", "2000-02-29", "2026-01-31", "0001-01-01"])
def test_real_calendar_dates_are_accepted_as_as_of(as_of):
    cell = _built("available", None, as_of=as_of)
    assert validate_cell(cell) == []
    assert VALIDATOR.is_valid(cell)


@pytest.mark.parametrize(
    "labels",
    [
        ["source_local", "NO_MAPPING"],
        ["NO_MAPPING", "NO_MAPPING"],
        ["not_a_label"],
        ["house_curated", "house_curated", "NO_MAPPING"],
        "NO_MAPPING",
    ],
)
def test_validate_cell_refuses_bad_labels(labels):
    raw = _raw(labels=labels)
    problems = validate_cell(raw)
    assert problems
    assert any("label" in problem.lower() for problem in problems)
    assert not VALIDATOR.is_valid(raw)


def test_make_cell_sorts_and_dedupes_labels():
    cell = make_cell(
        axis="geography",
        subject_id="co:us:AAPL",
        status="available",
        value="US",
        as_of=AS_OF,
        source=dict(SOURCE),
        labels=["source_local", "NO_MAPPING", "NO_MAPPING", "house_curated"],
    )
    assert cell["labels"] == ["NO_MAPPING", "house_curated", "source_local"]
    assert validate_cell(cell) == []
    assert VALIDATOR.is_valid(cell)


def test_make_cell_still_refuses_an_unknown_label():
    with pytest.raises(AxisCellError):
        _built("available", None, labels=["nope"])
    assert validate_cell(_raw(labels=["nope"]))


@pytest.mark.parametrize(
    "garbage",
    [None, [], "x", {"value": object()}, {}, 1, 1.0],
)
def test_validate_cell_never_raises(garbage):
    problems = validate_cell(garbage)
    assert isinstance(problems, list)
    assert problems


@pytest.mark.parametrize(
    "subject_id,kind,rest",
    [
        ("co:us:AAPL", "co", "us:AAPL"),
        ("co:hk:0700", "co", "hk:0700"),
        ("co:us:FB#2", "co", "us:FB#2"),
        ("theme:ai_compute", "theme", "ai_compute"),
        ("etf:SMH", "etf", "SMH"),
    ],
)
def test_parse_subject_accepts(subject_id, kind, rest):
    assert parse_subject(subject_id) == (kind, rest)


def test_parse_subject_accepts_a_real_basket_suite():
    suite = "baskets"
    assert suite in SUITE_MARKET
    assert suite not in NON_BASKET_SUITES
    subject_id = basket_node_id(suite, "semis")
    assert subject_id == "basket:baskets:semis"
    assert parse_subject(subject_id) == ("basket", "baskets:semis")
    ths_suite = "baskets_china_ths"
    assert ths_suite in SUITE_MARKET and ths_suite not in NON_BASKET_SUITES
    ths_id = basket_node_id(ths_suite, "chip")
    assert parse_subject(ths_id) == ("basket", "baskets_china_ths:chip")


@pytest.mark.parametrize(
    "subject_id",
    [
        "ltheme:finviz:x",
        "ltheme:ths:885001",
        "basket:finviz_themes:x",
        "basket:ths_concepts:x",
        "basket:unknown_suite:x",
        "etf:smh lower",
        "etf:smh",
        "theme:Bad-Slug",
        "theme:a",
        "foo:bar",
        "",
        None,
        12,
        "co:us:",
        "co:eu:AAPL",
        "etf:",
        "basket:baskets:",
    ],
)
def test_parse_subject_refuses(subject_id):
    with pytest.raises(AxisCellError) as caught:
        parse_subject(subject_id)
    assert caught.value.problems
    assert all(isinstance(item, str) and item for item in caught.value.problems)


def test_company_parts_splits_market_symbol_and_epoch():
    assert company_parts("co:us:AAPL") == ("us", "AAPL", None)
    assert company_parts("co:us:FB#2") == ("us", "FB", 2)
    assert type(company_parts("co:us:FB#2")[2]) is int
    assert company_parts("co:hk:0700") == ("hk", "0700", None)
    assert company_parts("co:us:BRK.B") == ("us", "BRK.B", None)
    assert company_parts("co:us:BRK.B#3") == ("us", "BRK.B", 3)


@pytest.mark.parametrize("subject_id", ["theme:ai_compute", "etf:SMH", "basket:baskets:semis", "nope", None])
def test_company_parts_refuses_non_company_ids(subject_id):
    with pytest.raises(AxisCellError):
        company_parts(subject_id)


def test_to_json_is_byte_stable_and_sorts_keys():
    cell = make_cell(
        axis="value_chain",
        subject_id="theme:ai_compute",
        status="available",
        value={"zeta": 1, "alpha": {"b": 2, "a": ["café"]}},
        as_of=AS_OF,
        source={"owner": "o", "artifact": "a.py", "field": "k"},
        provenance=["second", "first"],
        labels=["source_local"],
        unit="text",
    )
    first = to_json(cell)
    second = to_json(cell)
    assert first == second
    assert isinstance(first, str)
    loaded = json.loads(first)
    assert loaded == cell
    assert list(loaded) == sorted(loaded)
    assert list(loaded["value"]) == ["alpha", "zeta"]
    assert list(loaded["value"]["alpha"]) == ["a", "b"]
    assert "café" in first
    assert "\\u" not in first
    assert cell["provenance"] == ["second", "first"]


def test_quality_cannot_be_overridden():
    cell = _built("available", None)
    assert cell["quality"] == "display_only"
    hand = dict(cell)
    hand["quality"] = "authoritative"
    problems = validate_cell(hand)
    assert any("display_only" in problem for problem in problems)
    assert not VALIDATOR.is_valid(hand)
    with pytest.raises(TypeError):
        make_cell(
            axis="sic_industry",
            subject_id="co:us:AAPL",
            status="available",
            value="3674",
            as_of=AS_OF,
            source=dict(SOURCE),
            quality="authoritative",
        )


def test_schema_document_and_agreement_on_the_shared_vector():
    assert SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert SCHEMA["$id"] == "axis_cell.v1"
    assert SCHEMA["title"]
    description = SCHEMA["description"]
    assert "engine/classification_axes/cell.py::validate_cell" in description
    assert "forbidden" in description.lower()
    assert "point-in-time" in description.lower()
    assert SCHEMA["additionalProperties"] is False
    Draft202012Validator.check_schema(SCHEMA)

    vector: list[tuple[str, dict, bool]] = []
    for status, reason in ALLOWED:
        vector.append((f"allowed {status}/{reason}", _built(status, reason), True))
    vector.append(("stale null", _built("stale", "owner_stale", value=None), True))
    vector.append(("stale value", _built("stale", "owner_stale", value={"count": 1}), True))
    for status, reason in DISALLOWED:
        vector.append((
            f"disallowed {status}/{reason}",
            _raw(status=status, reason_code=reason, value=_value_for(status)),
            False,
        ))
    vector.append(("available null value", _raw(value=None), False))
    vector.append((
        "unknown with value",
        _raw(status="unknown", reason_code="value_missing", value="x"),
        False,
    ))
    vector.append((
        "unavailable with value",
        _raw(status="unavailable", reason_code="owner_missing", value=1),
        False,
    ))
    vector.append((
        "not_applicable with value",
        _raw(status="not_applicable", reason_code="not_applicable", value=True),
        False,
    ))
    vector.append((
        "rights_blocked with value",
        _raw(status="rights_blocked", reason_code="rights_blocked", value=[]),
        False,
    ))
    for bad in ("2026-13-01", "20261001", None):
        vector.append((f"as_of {bad!r}", _raw(as_of=bad), False))
    vector.append(("labels unsorted", _raw(labels=["source_local", "NO_MAPPING"]), False))
    vector.append(("labels duplicate", _raw(labels=["NO_MAPPING", "NO_MAPPING"]), False))
    vector.append(("labels unknown", _raw(labels=["not_a_label"]), False))
    vector.append(("quality authoritative", _raw(quality="authoritative"), False))
    vector.append(("schema_version drifted", _raw(schema_version="axis_cell.v0"), False))
    vector.append(("status unknown-token", _raw(status="bogus", reason_code=None), False))

    mismatches = []
    for name, candidate, expect in vector:
        py_ok = validate_cell(candidate) == []
        schema_ok = VALIDATOR.is_valid(candidate)
        if py_ok != expect or schema_ok != expect or py_ok != schema_ok:
            mismatches.append((name, expect, py_ok, schema_ok, validate_cell(candidate)))
    assert mismatches == []


def test_schema_leaves_python_only_rules_to_validate_cell():
    forbidden = _raw(value={"rows": [{"Exposure_Pct": 1}]})
    assert validate_cell(forbidden)
    assert VALIDATOR.is_valid(forbidden)
    future = _raw(observed_at="2026-10-12")
    assert any("after as_of" in problem for problem in validate_cell(future))
    assert VALIDATOR.is_valid(future)


def test_wrappers_and_reexports():
    got = available(
        axis="lifecycle",
        subject_id="co:hk:0700",
        value="operating",
        as_of=AS_OF,
        source=dict(SOURCE),
        provenance=("ledger",),
    )
    assert got["status"] == "available"
    assert got["reason_code"] is None
    assert got["provenance"] == ["ledger"]
    stale = missing(
        axis="lifecycle",
        subject_id="co:hk:0700",
        status="stale",
        reason_code="owner_stale",
        as_of=AS_OF,
        source=dict(SOURCE),
        value="operating",
    )
    assert stale["value"] == "operating"
    assert validate_cell(stale) == []
    with pytest.raises(AxisCellError) as caught:
        missing(
            axis="lifecycle",
            subject_id="co:hk:0700",
            status="available",
            reason_code=None,
            as_of=AS_OF,
            source=dict(SOURCE),
        )
    assert caught.value.problems

    import engine.classification_axes as pkg
    exported = [
        "SCHEMA_VERSION", "AXES", "STATUSES", "REASON_CODES", "LABELS",
        "FORBIDDEN_VALUE_KEY_WORDS", "AxisCellError", "make_cell", "available",
        "missing", "validate_cell", "parse_subject", "company_parts", "to_json",
    ]
    for name in exported:
        assert getattr(pkg, name) is getattr(cell_mod, name)
    init_src = Path(pkg.__file__).read_text(encoding="utf-8")
    assert "import *" not in init_src
    cell_src = Path(cell_mod.__file__).read_text(encoding="utf-8")
    assert "from engine.theme_graph.identity import" in cell_src
    assert "import scripts" not in cell_src
    assert "from scripts" not in cell_src
    assert "finviz_themes" in cell_src
    assert "ths_concepts" in cell_src


@pytest.mark.parametrize(
    "freshness,schema_rejects",
    [
        ({"age_days": -1, "max_age_days": 1}, True),
        ({"age_days": 0, "max_age_days": 0}, True),
        ({"age_days": True, "max_age_days": 1}, True),
        # JSON Schema's integer type counts an integral float as an integer.
        # Python still refuses it; the schema cannot see the distinction.
        ({"age_days": 1.0, "max_age_days": 5}, False),
        ({"age_days": 1}, True),
        ({"age_days": 1, "max_age_days": 5, "extra": 1}, True),
        ([], True),
        ("0", True),
    ],
)
def test_freshness_shape_is_refused(freshness, schema_rejects):
    raw = _raw(freshness=freshness)
    assert any("freshness" in problem for problem in validate_cell(raw))
    assert VALIDATOR.is_valid(raw) is not schema_rejects


def test_freshness_shape_is_accepted():
    cell = _built("available", None, freshness={"age_days": 0, "max_age_days": 1})
    assert validate_cell(cell) == []
    assert VALIDATOR.is_valid(cell)


@pytest.mark.parametrize(
    "source",
    [
        None,
        {},
        {"owner": "", "artifact": "a", "field": None},
        {"owner": "o", "artifact": "", "field": None},
        {"owner": "o", "artifact": "a", "field": 1},
        {"owner": "o", "artifact": "a"},
        {"owner": "o", "artifact": "a", "field": None, "extra": 1},
        ["o", "a", None],
    ],
)
def test_source_shape_is_refused(source):
    raw = _raw(source=source)
    assert any("source" in problem for problem in validate_cell(raw))
    assert not VALIDATOR.is_valid(raw)


def test_source_field_may_be_a_string():
    cell = _built(
        "available",
        None,
        source={"owner": "engine.theme_graph.store", "artifact": "engine/theme_graph/store.py", "field": "market_scope"},
    )
    assert validate_cell(cell) == []
    assert VALIDATOR.is_valid(cell)


@pytest.mark.parametrize("provenance", ["note", [""], ["ok", ""], ["ok", 1], None])
def test_provenance_must_be_a_list_of_non_empty_strings(provenance):
    raw = _raw(provenance=provenance)
    assert any("provenance" in problem for problem in validate_cell(raw))


def test_make_cell_copies_provenance_to_a_list():
    cell = _built("available", None, provenance=("alpha", "beta"))
    assert cell["provenance"] == ["alpha", "beta"]
    assert validate_cell(cell) == []


@pytest.mark.parametrize(
    "rights",
    [
        {},
        {"license_class": "", "basis": "statute"},
        {"license_class": "public", "basis": ""},
        {"license_class": "public"},
        {"license_class": "public", "basis": "statute", "extra": 1},
        "public",
    ],
)
def test_rights_context_shape_is_refused(rights):
    raw = _raw(rights_context=rights)
    assert any("rights" in problem for problem in validate_cell(raw))
    assert not VALIDATOR.is_valid(raw)


def test_rights_context_constant_is_accepted():
    cell = _built(
        "available",
        None,
        rights_context={"license_class": "public_domain", "basis": "government_statistics"},
        observed_at="2026-10-11",
        effective_at="2026-01-15 00:00:00",
        unit="iso3166",
    )
    assert validate_cell(cell) == []
    assert VALIDATOR.is_valid(cell)


def test_missing_and_extra_keys_are_reported():
    raw = _raw()
    raw.pop("unit")
    raw["note"] = "no"
    problems = validate_cell(raw)
    assert any("missing" in problem and "unit" in problem for problem in problems)
    assert any("extra" in problem and "note" in problem for problem in problems)
    assert not VALIDATOR.is_valid(raw)


@pytest.mark.parametrize("unit", [1, 1.0, ["name"], {"u": "x"}])
def test_unit_must_be_string_or_null(unit):
    raw = _raw(unit=unit)
    assert any("unit" in problem for problem in validate_cell(raw))
    assert not VALIDATOR.is_valid(raw)


@pytest.mark.parametrize(
    "subject_id",
    ["co:us:AAPL", "co:hk:0700", "co:us:FB#2", "theme:ai_compute", "basket:baskets:semis", "etf:SMH"],
)
def test_every_accepted_subject_can_be_a_cell(subject_id):
    cell = _built("unknown", "value_missing", value=None, subject_id=subject_id)
    assert validate_cell(cell) == []
    assert VALIDATOR.is_valid(cell)


def test_vendor_subjects_cannot_be_cells():
    for subject_id in ("ltheme:finviz:x", "ltheme:ths:885001", "basket:finviz_themes:x", "basket:ths_concepts:x"):
        with pytest.raises(AxisCellError):
            _built("unknown", "value_missing", value=None, subject_id=subject_id)
        assert validate_cell(_raw(subject_id=subject_id, status="unknown", reason_code="value_missing", value=None))


def test_observed_at_calendar_and_prefix_rules():
    assert validate_cell(_raw(observed_at="2026-02-30"))
    assert validate_cell(_raw(observed_at="2026-01-15extra"))
    assert validate_cell(_raw(observed_at=20260115))
    good = _built("available", None, observed_at="2026-10-11T00:00:00+00:00", effective_at="2024-02-29")
    assert validate_cell(good) == []
    assert VALIDATOR.is_valid(good)
    assert not VALIDATOR.is_valid(_raw(observed_at="2026-02-30"))


def test_rich_cell_round_trips_through_schema():
    cell = make_cell(
        axis="geography",
        subject_id="theme:ai_compute",
        status="available",
        value={"regions": ["US", "CN"], "count": 2, "member_count": 2},
        as_of=AS_OF,
        source={
            "owner": "engine.theme_graph.store",
            "artifact": "engine/theme_graph/store.py",
            "field": "market_scope",
        },
        unit="iso3166",
        observed_at="2026-10-11T00:00:00Z",
        effective_at="2026-01-15",
        freshness={"max_age_days": 30, "age_days": 0},
        labels=["read_time_composition", "house_curated", "house_curated"],
        provenance=["config/theme_crosswalk.yml", "operator"],
        rights_context={"license_class": "public_domain", "basis": "government_statistics"},
    )
    assert cell["labels"] == ["house_curated", "read_time_composition"]
    assert validate_cell(cell) == []
    assert VALIDATOR.is_valid(cell)
    assert json.loads(to_json(cell)) == cell
