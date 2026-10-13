"""Pure tests for deterministic ticker-news annotation."""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from engine.news_events import classify_event, extract_numbers
from engine.qbus_news_annotate import annotate_row, derivative_permitted


_CONTRACT = "Defense contractor wins $2.4B Navy contract for destroyer program"
_UNMATCHED = "Warehouse inventory climbed 12.5% during the quiet season"
_EARNINGS_TEASER = (
    "Amazon posts Q3 earnings that beat analyst estimates and records $88.8 million"
)
_FIGURE_KEYS = ["usd", "percentages", "eps", "guidance_range", "count"]
_ANNOTATION_KEYS = [
    "schema",
    "event_type",
    "figures",
    "evidence",
    "basis",
    "annotator_version",
    "derivation",
]


def _nested_keys(value):
    found = set()
    if isinstance(value, dict):
        found.update(value)
        for item in value.values():
            found |= _nested_keys(item)
    elif isinstance(value, list):
        for item in value:
            found |= _nested_keys(item)
    return found


def _write_receipt(path: Path, capabilities) -> None:
    path.write_text(
        json.dumps(
            {
                "status": "denied",
                "schema": "not-a-qualified-receipt",
                "capabilities": capabilities,
            }
        ),
        encoding="utf-8",
    )


def test_known_event_headline_maps_type_and_figures():
    """Mutation: drop ``event_type`` or keep ``usd_all`` and this fails."""
    classified = classify_event(_CONTRACT)
    assert classified is not None
    ann = annotate_row(_CONTRACT, None)

    assert ann is not None
    assert ann["event_type"] == "contract_award"
    assert ann["event_type"] == classified["event_type"]
    assert ann["evidence"]["matched_pattern"] == classified["matched"]
    assert ann["figures"]["usd"] == pytest.approx(classified["numbers"]["usd"])
    assert ann["figures"]["usd"] == pytest.approx(2_400_000_000)
    assert ann["basis"] == "headline"
    assert list(ann["figures"]) == _FIGURE_KEYS
    assert "usd_all" not in ann["figures"]
    json.dumps(ann)


def test_unmatched_headline_has_null_type_and_figures():
    """Mutation: return None on an unmatched headline and this fails."""
    assert classify_event(_UNMATCHED) is None
    ann = annotate_row(_UNMATCHED, "")

    assert ann is not None
    assert ann["event_type"] is None
    assert ann["evidence"]["matched_pattern"] is None
    assert ann["basis"] == "headline"
    assert list(ann["figures"]) == _FIGURE_KEYS
    assert ann["figures"]["percentages"] == [12.5]
    assert ann["figures"] == {
        key: extract_numbers(_UNMATCHED)[key] for key in _FIGURE_KEYS
    }


def test_served_teaser_changes_basis_type_and_figures():
    """Mutation: ignore teaser, or treat an empty teaser as served, and this fails."""
    headline_only = annotate_row(_UNMATCHED, None)
    blank_teaser = annotate_row(_UNMATCHED, "")
    with_teaser = annotate_row(_CONTRACT, _EARNINGS_TEASER)
    classified = classify_event(_CONTRACT, _EARNINGS_TEASER)

    assert headline_only["basis"] == "headline"
    assert headline_only["event_type"] is None
    assert blank_teaser["basis"] == "headline"
    assert blank_teaser["figures"]["usd"] is None
    assert classified is not None
    assert with_teaser["basis"] == "headline+teaser"
    assert with_teaser["event_type"] == "contract_award"
    assert with_teaser["evidence"]["matched_pattern"] == classified["matched"]
    # The dollar amount exists only in the teaser. Title-only classification of
    # the contract headline is $2.4B; the teaser adds $88.8 million as usd_all,
    # while the first usd remains the title amount. Use a teaser-only number on
    # an unmatched title to prove the teaser text is in the figure basis.
    teaser_only_number = annotate_row(
        "Nvidia launches accelerator",
        "records a cash balance of $88.8 million",
    )
    assert classify_event("Nvidia launches accelerator") is None
    assert teaser_only_number["basis"] == "headline+teaser"
    assert teaser_only_number["event_type"] is None
    assert teaser_only_number["figures"]["usd"] == pytest.approx(88_800_000)
    assert annotate_row("Nvidia launches accelerator", None)["figures"]["usd"] is None


def test_teaser_can_supply_the_event_when_the_headline_does_not():
    """Mutation: call classify_event(title) even when a teaser was served."""
    title = "Nvidia launches accelerator"
    ann = annotate_row(title, _EARNINGS_TEASER)
    classified = classify_event(title, _EARNINGS_TEASER)

    assert classified is not None
    assert classified["event_type"] == "earnings_result"
    assert ann["event_type"] == "earnings_result"
    assert ann["basis"] == "headline+teaser"
    assert ann["figures"]["usd"] == pytest.approx(88_800_000)
    assert ann["evidence"]["matched_pattern"] == classified["matched"]


def test_empty_title_returns_none_even_when_teaser_has_an_event():
    """Mutation: classify the teaser when the title is missing and this fails."""
    assert annotate_row(None, _EARNINGS_TEASER) is None
    assert annotate_row("", _EARNINGS_TEASER) is None
    assert annotate_row(None, None) is None
    assert annotate_row(12, _EARNINGS_TEASER) is None  # type: ignore[arg-type]


def test_annotation_omits_direction_confidence_and_extra_keys():
    """Mutation: copy ``direction`` or ``confidence`` from classify_event."""
    ann = annotate_row(_CONTRACT, _EARNINGS_TEASER)
    classified = classify_event(_CONTRACT, _EARNINGS_TEASER)

    assert classified is not None
    assert classified["direction"]
    assert classified["confidence"]
    assert _nested_keys(ann).isdisjoint({"direction", "confidence", "usd_all"})
    assert list(ann) == _ANNOTATION_KEYS
    assert list(ann["evidence"]) == ["matched_pattern"]
    assert ann["schema"] == "ticker_news.annotation.v1"
    assert ann["annotator_version"] == "qbus_news_annotate.v1"
    assert ann["derivation"] == "deterministic_pattern"
    assert ann["basis"] in {"headline", "headline+teaser"}


def test_annotate_row_rejects_a_body_argument():
    """Mutation: add a body parameter and pass it to classify_event."""
    params = inspect.signature(annotate_row).parameters
    assert list(params) == ["title", "teaser"]
    with pytest.raises(TypeError):
        annotate_row(  # type: ignore[call-arg]
            _CONTRACT,
            None,
            body="secret story body with $9.9 billion",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        ("true", False),
        ("True", False),
        (1, False),
        (None, False),
    ],
)
def test_derivative_permitted_requires_literal_true(tmp_path, value, expected):
    """Mutation: truthiness (``== True`` or ``bool(value)``) accepts the string."""
    path = tmp_path / "rights.json"
    _write_receipt(path, {"derivative_processing": value})
    assert derivative_permitted(path) is expected


def test_derivative_permitted_missing_capability_is_false(tmp_path):
    """Mutation: default a missing flag to True."""
    path = tmp_path / "rights.json"
    _write_receipt(path, {"headline_display": True})
    assert derivative_permitted(path) is False


def test_derivative_permitted_bad_shape_is_false(tmp_path):
    """Mutation: index capabilities without a type check and this raises or passes."""
    missing_caps = tmp_path / "missing-caps.json"
    missing_caps.write_text("{}", encoding="utf-8")
    not_object = tmp_path / "list.json"
    not_object.write_text("[true]", encoding="utf-8")
    bad_caps = tmp_path / "caps.json"
    bad_caps.write_text(
        json.dumps({"capabilities": ["derivative_processing"]}),
        encoding="utf-8",
    )
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")

    assert derivative_permitted(missing_caps) is False
    assert derivative_permitted(not_object) is False
    assert derivative_permitted(bad_caps) is False
    assert derivative_permitted(invalid) is False


def test_derivative_permitted_unreadable_file_is_false(tmp_path):
    """Mutation: let a missing path raise instead of returning False."""
    missing = tmp_path / "no-such-receipt.json"
    directory = tmp_path / "receipt-dir"
    directory.mkdir()
    assert derivative_permitted(missing) is False
    assert derivative_permitted(directory) is False
    assert derivative_permitted(None) is False


def test_derivative_permitted_does_not_requalify(tmp_path):
    """Mutation: require status approved / a known schema and this fails.

    Qualification stays in load_rights_receipt. This function only reads the
    derivative boolean, including from a receipt that would not qualify.
    """
    path = tmp_path / "rights.json"
    _write_receipt(path, {"derivative_processing": True})
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["status"] == "denied"
    assert raw["schema"] != "qbus.news_rights_receipt.v1"
    assert derivative_permitted(path) is True
