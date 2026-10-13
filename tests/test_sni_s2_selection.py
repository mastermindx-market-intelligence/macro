"""S2 selection (E3): exact '<br/>'-token matching against profile local_code.

Pins: '40700' never matches '00700'; '80700'/'89988' never select; one
programme of three general-mandate placing rows forms ONE programme; the
category classification table maps the store vocabulary; the census lists the
false-positive class instead of counting it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from s2_selection import (classify_category, derive_programmes,  # noqa: E402
                          near_token_rows, select_rows_for_counter,
                          split_tokens)


def _toks(code: str) -> dict[int, list[str]]:
    return {0: split_tokens(code)}


def test_exact_token_selection() -> None:
    toks = {0: split_tokens("09988<br/>89988"),
            1: split_tokens("00700<br/>80700"),
            2: split_tokens("02018<br/>40700")}
    assert select_rows_for_counter(toks, "09988") == [0]
    assert select_rows_for_counter(toks, "00700") == [1]
    # the token '40700' is not '00700' (and not '09988')
    assert 2 not in select_rows_for_counter(toks, "00700")
    assert 2 not in select_rows_for_counter(toks, "09988")


def test_40700_never_matches_00700_even_as_substring_class() -> None:
    toks = _toks("02018<br/>40700")
    assert select_rows_for_counter(toks, "00700") == []
    near = near_token_rows(toks, "00700", key_form="0700")
    assert [(i, t) for i, t in near] == [(0, "40700")]


def test_substring_never_selects() -> None:
    toks = _toks("100700<br/>007000<br/>00700X")
    assert select_rows_for_counter(toks, "00700") == []


def test_classification_table_maps_store_vocabulary() -> None:
    assert classify_category("final_results") == "results"
    assert classify_category("interim_results") == "results"
    assert classify_category("quarterly_results") == "results"
    assert classify_category("buyback") == "capital_action"
    assert classify_category("general_mandate") == "capital_action"
    # a category the table cannot map is UNCLASSIFIED: listed, never counted
    assert classify_category("shareholder") == "UNCLASSIFIED"
    assert classify_category("something_else") == "UNCLASSIFIED"


def test_one_programme_of_three_rows_is_one_programme() -> None:
    rows = [
        {"id": "12295308", "issuer_key": "alibaba", "counter": "hkd_9988",
         "family": "capital_action", "category": "general_mandate",
         "title": "PROPOSED PLACING OF NEW SHARES UNDER GENERAL MANDATE"},
        {"id": "12295380", "issuer_key": "alibaba", "counter": "hkd_9988",
         "family": "capital_action", "category": "general_mandate",
         "title": "PRICING OF HK$80 BILLION PLACING OF NEW SHARES"},
        {"id": "12300619", "issuer_key": "alibaba", "counter": "hkd_9988",
         "family": "capital_action", "category": "general_mandate",
         "title": "COMPLETION OF PLACING OF NEW SHARES UNDER GENERAL MANDATE"},
        {"id": "12157537", "issuer_key": "alibaba", "counter": "hkd_9988",
         "family": "results", "category": "final_results", "title": "RESULTS"},
    ]
    programmes = derive_programmes(rows)
    assert len(programmes) == 1
    assert programmes[0]["member_ids"] == ["12295308", "12295380", "12300619"]


def test_programme_rule_ignores_non_placing_capital_rows() -> None:
    rows = [{"id": "1", "issuer_key": "alibaba", "counter": "hkd_9988",
             "family": "capital_action", "category": "shareholder",
             "title": "PLACING-LOOKALIKE"}]
    assert derive_programmes(rows) == []
