"""Regression: thousands separators must not create four invented numbers."""

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
