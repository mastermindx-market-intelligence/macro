"""Regression: thousands separators must not create four invented numbers."""

import pytest

from engine.marketing.copywriter import _extract_number_tokens, validate_copy


def _number_violations(text: str, whitelist: list[str]) -> list[str]:
    return [
        v for v in validate_copy("Weekly claims", text, {
            "type": "macro", "numbers_whitelist": whitelist,
        }) if "number '" in v or "level '" in v
    ]


def test_comma_grouped_source_count_is_one_token():
    text = "Weekly claims reached 221,000, up from 219,000."
    assert _extract_number_tokens(text) == ["221,000", "219,000"]
    assert _number_violations(text, ["221,000", "219,000"]) == []


def test_big_count_and_decimal_price_remain_whole_tokens():
    text = "The total was $7,600,000 at a quoted price of $1,234.50."
    assert _extract_number_tokens(text) == ["7,600,000", "1,234.50"]
    assert _number_violations(text, ["7,600,000", "1,234.50"]) == []


def test_grouped_and_ungrouped_are_numeric_equivalents_only():
    text = "Weekly claims reached 221,000, up from 219,000."
    assert _number_violations(text, ["221000", "219000"]) == []
    assert _number_violations(text, ["221,001", "219000"])


def test_generated_new_number_remains_unlicensed():
    text = "Weekly claims reached 222,000, up from 219,000."
    assert _number_violations(text, ["221,000", "219,000"]) == [
        "number '222,000' not in whitelist"
    ]


def test_regular_pcts_and_prices_keep_their_prior_tokens():
    text = "At 41.25, the move was -3.4% and volume reached 2.5x normal."
    assert _extract_number_tokens(text) == ["41.25", "-3.4%", "2.5x"]


def test_malformed_grouping_cannot_pretend_to_be_221000():
    text = "Weekly claims reached 22,1000."
    assert _number_violations(text, ["221,000"])


@pytest.mark.parametrize("malformed,licensed", [
    ("221,000,00", "221,000"),
    ("1,000,00", "1,000"),
    ("1,,000", "1,000"),
    ("1000,000", "1,000,000"),
    ("1,000.00.5", "1,000.00"),
    ("1,234.50,00", "1,234.50"),
    (".5,000", "5,000"),
    ("-.5,000", "5,000"),
    ("--1,000", "-1,000"),
    ("1,000k%", "1,000k"),
    ("1,000%%", "1,000%"),
])
def test_malformed_grouped_run_cannot_borrow_a_licensed_fragment(malformed, licensed):
    text = f"The reported total was {malformed}."
    assert _extract_number_tokens(text) == [malformed]
    assert _number_violations(text, [licensed])
    assert _number_violations(text, [malformed])


def test_malformed_source_grouping_does_not_license_its_comma_stripped_value():
    assert _number_violations("The reported total was 22,100,000.", ["221,000,00"])


@pytest.mark.parametrize("text,tokens", [
    ("The total was 1,000, up from 900.", ["1,000", "900"]),
    ("The quote was $1,234.50.", ["1,234.50"]),
    ("The moves were -1,000.25% and +2,000k.", ["-1,000.25%", "+2,000k"]),
    ("The observed range was 1,000–2,000.", ["1,000", "2,000"]),
])
def test_grouped_punctuation_signs_units_and_range_keep_complete_tokens(text, tokens):
    assert _extract_number_tokens(text) == tokens
    assert _number_violations(text, tokens) == []
    assert _number_violations(text, [token.replace(",", "") for token in tokens]) == []
