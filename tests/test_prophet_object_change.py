"""Behavior tests for the presentation-only object what-changed comparison.

These are hermetic examples of supplied owner reads, not production owner
receipts or acceptance evidence.
"""

import copy

import pytest

from engine.prophet_object_change import compare_object_reads


# ---------------------------------------------------------------------------
# Record builders (opaque owner ids; no market schema is invented anywhere)
# ---------------------------------------------------------------------------

BASE_BINDING = {
    "security_id": "SEC-778812",
    "episode_id": "EP-2026-10-11-0A1",
    "candidate_generation_id": "cand-gen-01",
    "market_session": "2026-10-11",
}
CLOCKS_LIVE = {
    "source_time": "2026-10-11T14:00:00Z",
    "observed_time": "2026-10-11T14:00:01+00:00",
    "published_time": "2026-10-11T14:00:02+09:00",
}


def _finalize(record, overrides):
    binding = overrides.pop("binding", {})
    clocks = overrides.pop("clocks", {})
    facts = overrides.pop("facts", {})
    record.update(overrides)
    record["binding"].update(binding)
    record["clocks"].update(clocks)
    record["facts"].update(facts)
    return record


def _quote_record(**overrides):
    record = {
        "object_type": "quote",
        "object_id": "Q-2026-10-11-000042",
        "owner": "market-data-owner",
        "state": "available",
        "binding": dict(BASE_BINDING),
        "source_ref": "native://quotes/Q-2026-10-11-000042?v=1",
        "generation_ref": "genref-quotes-000042-v1",
        "owner_receipt": "receipt-quotes-000042-v1",
        "clocks": dict(CLOCKS_LIVE),
        "facts": {"price": 100.0, "currency": "USD"},
        "review_ref": None,
    }
    return _finalize(record, overrides)


def _assessment_record(**overrides):
    record = {
        "object_type": "assessment",
        "object_id": "ASM-2026-10-11-000017",
        "owner": "risk-assessment-owner",
        "state": "available",
        "binding": dict(BASE_BINDING),
        "source_ref": "native://assessments/ASM-2026-10-11-000017?v=1",
        "generation_ref": "genref-assessments-000017-v1",
        "owner_receipt": "receipt-assessments-000017-v1",
        "clocks": dict(CLOCKS_LIVE),
        "facts": {
            "summary": "Hold above session open; liquidity thin.",
            "evidence_refs": ["ev-0001", "ev-0002"],
            "counterevidence_refs": [],
        },
        "review_ref": "review-2026-10-11-000017",
    }
    return _finalize(record, overrides)


def _plan_record(**overrides):
    record = {
        "object_type": "plan",
        "object_id": "PLAN-2026-10-11-000009",
        "owner": "execution-planner-owner",
        "state": "available",
        "binding": dict(BASE_BINDING),
        "source_ref": "native://plans/PLAN-2026-10-11-000009?v=1",
        "generation_ref": "genref-plans-000009-v1",
        "owner_receipt": "receipt-plans-000009-v1",
        "clocks": dict(CLOCKS_LIVE),
        "facts": {"status": "draft", "change_reason": None, "invalidation": None},
        "review_ref": None,
    }
    return _finalize(record, overrides)


def _assert_unavailable(result, reason):
    assert result == {
        "state": "comparison_unavailable",
        "reason": reason,
        "changed_fields": [],
        "before": None,
        "after": None,
    }


RESULT_KEYS = {"state", "reason", "changed_fields", "before", "after"}


# ---------------------------------------------------------------------------
# Changed: facts drive everything
# ---------------------------------------------------------------------------


def test_quote_price_only_update():
    previous = _quote_record()
    current = _quote_record(facts={"price": 101.25})
    result = compare_object_reads(previous, current)
    assert set(result) == RESULT_KEYS
    assert result["state"] == "changed"
    assert result["reason"] == "facts_changed"
    assert result["changed_fields"] == ["price"]
    assert result["before"]["facts"] == {"price": 100.0, "currency": "USD"}
    assert result["after"]["facts"] == {"price": 101.25, "currency": "USD"}
    # The full records ride along, metadata included.
    assert result["before"]["owner_receipt"] == previous["owner_receipt"]
    assert result["after"]["owner_receipt"] == current["owner_receipt"]


def test_quote_currency_only_change():
    current = _quote_record(facts={"currency": "JPY"})
    result = compare_object_reads(_quote_record(), current)
    assert result["state"] == "changed"
    assert result["changed_fields"] == ["currency"]


def test_quote_changed_fields_are_sorted():
    current = _quote_record(facts={"price": 99.0, "currency": "EUR"})
    result = compare_object_reads(_quote_record(), current)
    assert result["state"] == "changed"
    assert result["changed_fields"] == ["currency", "price"]


def test_assessment_evidence_change():
    previous = _assessment_record()
    current = _assessment_record(
        facts={"evidence_refs": ["ev-0001", "ev-0002", "ev-0003"]}
    )
    result = compare_object_reads(previous, current)
    assert result["state"] == "changed"
    assert result["changed_fields"] == ["evidence_refs"]


def test_assessment_counterevidence_added():
    current = _assessment_record(facts={"counterevidence_refs": ["ce-0001"]})
    result = compare_object_reads(_assessment_record(), current)
    assert result["changed_fields"] == ["counterevidence_refs"]


def test_plan_invalidation_with_reason_kept_verbatim():
    reason_text = "Risk limit breached / 风险限额已触发"
    previous = _plan_record(facts={"change_reason": reason_text})
    current = _plan_record(
        facts={"status": "invalid", "change_reason": reason_text, "invalidation": 2500.0}
    )
    result = compare_object_reads(previous, current)
    assert result["state"] == "changed"
    assert result["reason"] == "facts_changed"
    assert result["changed_fields"] == ["invalidation", "status"]
    # change_reason is an owner fact: identical text on both sides, verbatim.
    assert result["before"]["facts"]["change_reason"] == reason_text
    assert result["after"]["facts"]["change_reason"] == reason_text
    assert result["before"]["facts"]["invalidation"] is None
    assert result["after"]["facts"]["invalidation"] == 2500.0


def test_plan_change_reason_only_change_is_verbatim():
    previous = _plan_record(
        facts={"status": "working", "change_reason": "fills pending / 約定待ち"}
    )
    current = _plan_record(
        facts={"status": "working", "change_reason": "reprice requested / 改価要求"}
    )
    result = compare_object_reads(previous, current)
    assert result["changed_fields"] == ["change_reason"]
    assert result["before"]["facts"]["change_reason"] == "fills pending / 約定待ち"
    assert result["after"]["facts"]["change_reason"] == "reprice requested / 改価要求"


def test_unicode_summary_compared_and_preserved():
    previous = _assessment_record(facts={"summary": "板観察: 直近の売り圧力に注意。"})
    current = _assessment_record(facts={"summary": "板観察: 直近の買い支援が増加。"})
    result = compare_object_reads(previous, current)
    assert result["changed_fields"] == ["summary"]
    assert result["before"]["facts"]["summary"] == "板観察: 直近の売り圧力に注意。"
    assert result["after"]["facts"]["summary"] == "板観察: 直近の買い支援が増加。"


# ---------------------------------------------------------------------------
# Unchanged: identical, and metadata-only movement
# ---------------------------------------------------------------------------


def test_identical_quote_unchanged():
    record = _quote_record()
    result = compare_object_reads(record, copy.deepcopy(record))
    assert set(result) == RESULT_KEYS
    assert result["state"] == "unchanged"
    assert result["reason"] == "facts_unchanged"
    assert result["changed_fields"] == []
    assert result["before"] == record
    assert result["after"] == record


def test_identical_assessment_with_empty_counterevidence_unchanged():
    record = _assessment_record()  # counterevidence_refs == [] is valid
    result = compare_object_reads(record, copy.deepcopy(record))
    assert result["state"] == "unchanged"
    assert result["changed_fields"] == []


def test_metadata_only_movement_is_unchanged():
    previous = _quote_record()
    current = _quote_record(
        source_ref="native://quotes/Q-2026-10-11-000042?v=2",
        generation_ref="genref-quotes-000042-v2",
        owner_receipt="receipt-quotes-000042-v2",
        clocks={
            "source_time": "2026-10-11T15:00:00+00:00",
            "observed_time": "2026-10-11T15:00:01+00:00",
            "published_time": "2026-10-11T15:00:02+00:00",
        },
    )
    result = compare_object_reads(previous, current)
    assert result["state"] == "unchanged"
    assert result["reason"] == "facts_unchanged"
    assert result["changed_fields"] == []
    assert result["before"]["source_ref"] == previous["source_ref"]
    assert result["after"]["source_ref"] == current["source_ref"]
    assert result["before"]["owner_receipt"] == "receipt-quotes-000042-v1"
    assert result["after"]["owner_receipt"] == "receipt-quotes-000042-v2"


def test_null_late_future_clocks_preserved_without_new_time():
    previous = _quote_record(
        clocks={"source_time": None, "observed_time": None, "published_time": None}
    )
    current = _quote_record(
        clocks={
            "source_time": None,
            "observed_time": "2020-01-01T00:00:00+00:00",  # late
            "published_time": "2099-12-31T23:59:59+00:00",  # future
        }
    )
    result = compare_object_reads(previous, current)
    assert result["state"] == "unchanged"
    assert result["reason"] == "facts_unchanged"
    assert result["changed_fields"] == []
    # Verbatim preservation; the module mints no clock of its own.
    assert result["before"]["clocks"] == {
        "source_time": None,
        "observed_time": None,
        "published_time": None,
    }
    assert result["after"]["clocks"] == current["clocks"]


def test_clock_spellings_with_offsets_are_accepted():
    record = _quote_record(
        clocks={
            "source_time": "2026-10-11T23:00:00+09:00",
            "observed_time": "2026-10-11T14:00:01Z",
            "published_time": "2026-10-11T09:00:02-05:00",
        }
    )
    result = compare_object_reads(record, copy.deepcopy(record))
    assert result["state"] == "unchanged"


# ---------------------------------------------------------------------------
# Closed failures: missing / malformed reads
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "broken",
    [
        pytest.param(None, id="none"),
        pytest.param({}, id="empty_dict"),
        pytest.param(["quote"], id="list"),
        pytest.param("available", id="string"),
        pytest.param(7, id="number"),
    ],
)
def test_malformed_previous_read_fails_closed(broken):
    expected = "previous_unavailable" if broken is None else "previous_invalid"
    _assert_unavailable(compare_object_reads(broken, _quote_record()), expected)


def test_missing_previous_read_is_unavailable():
    _assert_unavailable(compare_object_reads(None, _quote_record()), "previous_unavailable")


def test_missing_current_read_is_unavailable():
    _assert_unavailable(compare_object_reads(_quote_record(), None), "current_unavailable")


def test_both_missing_reports_previous_side():
    _assert_unavailable(compare_object_reads(None, None), "previous_unavailable")


def test_failed_current_read_is_unavailable():
    _assert_unavailable(compare_object_reads(_quote_record(), {"facts": {}}), "current_invalid")
    _assert_unavailable(compare_object_reads(_quote_record(), ["quote"]), "current_invalid")
    _assert_unavailable(compare_object_reads(_quote_record(), 3.5), "current_invalid")


def _mutate_current(mutator):
    record = _quote_record()
    mutator(record)
    return record


@pytest.mark.parametrize(
    "mutator",
    [
        pytest.param(lambda r: r.pop("object_id"), id="missing_object_id"),
        pytest.param(lambda r: r.pop("facts"), id="missing_facts"),
        pytest.param(lambda r: r.update(entry="ENTRY_OPEN"), id="unknown_envelope_entry_key"),
        pytest.param(lambda r: r.update(accepted=True), id="unknown_envelope_accepted_key"),
        pytest.param(lambda r: r.update(state="stale"), id="envelope_state_not_available"),
        pytest.param(lambda r: r.update(object_type=["quote"]), id="object_type_list"),
        pytest.param(lambda r: r.update(object_type="synthetic"), id="object_type_unknown"),
        pytest.param(lambda r: r.update(object_id={"ticker": "ACME"}), id="object_id_dict"),
        pytest.param(lambda r: r.update(object_id=""), id="object_id_empty"),
        pytest.param(lambda r: r.update(owner=7), id="owner_number"),
        pytest.param(lambda r: r.update(source_ref=""), id="source_ref_empty"),
        pytest.param(lambda r: r.update(generation_ref=None), id="generation_ref_null"),
        pytest.param(lambda r: r.update(owner_receipt=12345), id="owner_receipt_number"),
        pytest.param(lambda r: r.update(binding=["SEC-1"]), id="binding_list"),
        pytest.param(lambda r: r["binding"].pop("market_session"), id="binding_missing_session"),
        pytest.param(lambda r: r["binding"].update(symbol="ACME"), id="binding_unknown_symbol_key"),
        pytest.param(
            lambda r: r["binding"].update(security_id={"id": "SEC-1"}),
            id="security_id_dict",
        ),
        pytest.param(lambda r: r["binding"].update(episode_id=""), id="episode_id_empty"),
        pytest.param(
            lambda r: r["binding"].update(candidate_generation_id=None),
            id="candidate_generation_id_null",
        ),
        pytest.param(
            lambda r: r["binding"].update(market_session="2026-10-1"),
            id="session_not_padded",
        ),
        pytest.param(
            lambda r: r["binding"].update(market_session="2026-13-01"),
            id="session_month_out_of_range",
        ),
        pytest.param(
            lambda r: r["binding"].update(market_session="2026-02-30"),
            id="session_impossible_date",
        ),
        pytest.param(
            lambda r: r["binding"].update(market_session="20261011"),
            id="session_basic_format",
        ),
        pytest.param(
            lambda r: r["binding"].update(market_session=20261011),
            id="session_number",
        ),
        pytest.param(
            lambda r: r.update(clocks="2026-10-11T14:00:00+00:00"), id="clocks_string"
        ),
        pytest.param(
            lambda r: r["clocks"].pop("published_time"), id="clocks_missing_key"
        ),
        pytest.param(
            lambda r: r["clocks"].update(received_time="2026-10-11T14:00:03+00:00"),
            id="clocks_unknown_key",
        ),
        pytest.param(
            lambda r: r["clocks"].update(observed_time="2026-10-11T14:00:01"),
            id="clock_naive",
        ),
        pytest.param(
            lambda r: r["clocks"].update(published_time="2026-10-11"), id="clock_date_only"
        ),
        pytest.param(
            lambda r: r["clocks"].update(source_time=1739260800), id="clock_epoch_number"
        ),
        pytest.param(lambda r: r["clocks"].update(observed_time=True), id="clock_bool"),
        pytest.param(lambda r: r.update(facts=[("price", 1.0)]), id="facts_list"),
        pytest.param(lambda r: r["facts"].pop("currency"), id="facts_missing_key"),
        pytest.param(
            lambda r: r["facts"].update(entry="ENTRY_OPEN"), id="facts_unknown_authority_key"
        ),
        pytest.param(lambda r: r["facts"].update(price=True), id="price_bool"),
        pytest.param(lambda r: r["facts"].update(price=False), id="price_bool_false"),
        pytest.param(lambda r: r["facts"].update(price=0), id="price_zero"),
        pytest.param(lambda r: r["facts"].update(price=-1.0), id="price_negative"),
        pytest.param(lambda r: r["facts"].update(price="100"), id="price_string"),
        pytest.param(lambda r: r["facts"].update(price=None), id="price_null"),
        pytest.param(lambda r: r["facts"].update(price=float("nan")), id="price_nan"),
        pytest.param(lambda r: r["facts"].update(price=float("inf")), id="price_infinite"),
        pytest.param(lambda r: r["facts"].update(currency=""), id="currency_empty"),
        pytest.param(lambda r: r["facts"].update(currency=None), id="currency_null"),
    ],
)
def test_malformed_current_read_fails_closed(mutator):
    _assert_unavailable(
        compare_object_reads(_quote_record(), _mutate_current(mutator)),
        "current_invalid",
    )


def test_malformed_assessment_facts_fail_closed():
    base = _assessment_record()
    for facts in (
        {"summary": ""},
        {"summary": None},
        {"summary": ["thin"]},
        {"evidence_refs": "ev-0001"},
        {"evidence_refs": [None]},
        {"evidence_refs": ["ev-0001", ""]},
        {"evidence_refs": ["ev-0001", 2]},
        {"counterevidence_refs": {"ce": 1}},
        {"counterevidence_refs": [""]},
    ):
        _assert_unavailable(
            compare_object_reads(base, _assessment_record(facts=facts)),
            "current_invalid",
        )
    missing_summary = _assessment_record()
    missing_summary["facts"].pop("summary")
    _assert_unavailable(compare_object_reads(base, missing_summary), "current_invalid")
    missing_counterevidence = _assessment_record()
    missing_counterevidence["facts"].pop("counterevidence_refs")
    _assert_unavailable(
        compare_object_reads(base, missing_counterevidence), "current_invalid"
    )


def test_malformed_plan_facts_fail_closed():
    base = _plan_record()
    for facts in (
        {"status": ""},
        {"status": None},
        {"status": 3},
        {"change_reason": 7},
        {"change_reason": []},
        {"change_reason": ""},
        {"invalidation": True},
        {"invalidation": -3},
        {"invalidation": "soon"},
        {"invalidation": float("nan")},
    ):
        _assert_unavailable(
            compare_object_reads(base, _plan_record(facts=facts)), "current_invalid"
        )
    missing_invalidation = _plan_record()
    missing_invalidation["facts"].pop("invalidation")
    _assert_unavailable(compare_object_reads(base, missing_invalidation), "current_invalid")


def test_plan_null_reason_and_invalidation_are_valid():
    record = _plan_record()  # change_reason / invalidation both null
    result = compare_object_reads(record, copy.deepcopy(record))
    assert result["state"] == "unchanged"
    assert result["after"]["facts"] == {
        "status": "draft",
        "change_reason": None,
        "invalidation": None,
    }


# ---------------------------------------------------------------------------
# Closed failures: review lineage rules
# ---------------------------------------------------------------------------


def test_assessment_missing_review_lineage_is_unavailable():
    no_review = _assessment_record()
    no_review["review_ref"] = None
    _assert_unavailable(compare_object_reads(_assessment_record(), no_review), "current_invalid")

    prior_no_review = _assessment_record()
    prior_no_review["review_ref"] = None
    _assert_unavailable(compare_object_reads(prior_no_review, _assessment_record()), "previous_invalid")

    empty_review = _assessment_record(review_ref="")
    _assert_unavailable(compare_object_reads(_assessment_record(), empty_review), "current_invalid")


def test_review_ref_forbidden_on_quote_and_plan():
    quoted = _quote_record(review_ref="review-not-allowed")
    _assert_unavailable(compare_object_reads(_quote_record(), quoted), "current_invalid")
    planned = _plan_record(review_ref="review-not-allowed")
    _assert_unavailable(compare_object_reads(_plan_record(), planned), "current_invalid")


# ---------------------------------------------------------------------------
# Closed failures: identity (owner + object + all four binding fields)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "binding_override",
    [
        pytest.param({"security_id": "SEC-999001"}, id="different_security"),
        pytest.param({"episode_id": "EP-2026-10-11-0B2"}, id="different_episode"),
        pytest.param(
            {"candidate_generation_id": "cand-gen-02"},
            id="different_candidate_generation",
        ),
        pytest.param({"market_session": "2026-10-12"}, id="different_market_session"),
    ],
)
def test_same_ticker_like_id_with_different_binding_is_unavailable(binding_override):
    # Ticker-like display text is NOT an identity; binding must match exactly.
    previous = _quote_record(object_id="ACME")
    current = _quote_record(object_id="ACME", binding=binding_override)
    _assert_unavailable(compare_object_reads(previous, current), "identity_mismatch")


def test_owner_change_is_unavailable():
    current = _quote_record(owner="other-market-data-owner")
    _assert_unavailable(compare_object_reads(_quote_record(), current), "identity_mismatch")


def test_object_id_change_is_unavailable():
    current = _quote_record(object_id="Q-2026-10-11-000043")
    _assert_unavailable(compare_object_reads(_quote_record(), current), "identity_mismatch")


def test_object_type_change_is_unavailable():
    current = _plan_record(object_id="Q-2026-10-11-000042")
    _assert_unavailable(compare_object_reads(_quote_record(), current), "identity_mismatch")


def test_market_session_change_only_is_identity_mismatch_not_invalid():
    previous = _quote_record()
    current = _quote_record(
        source_ref="native://quotes/Q-2026-10-11-000042?v=2",
        binding={"market_session": "2026-10-13"},
    )
    _assert_unavailable(compare_object_reads(previous, current), "identity_mismatch")


# ---------------------------------------------------------------------------
# Detachment: inputs and outputs share no mutable data
# ---------------------------------------------------------------------------


def test_mutating_result_does_not_reach_inputs():
    previous = _quote_record()
    current = _quote_record(facts={"price": 101.0})
    previous_snapshot = copy.deepcopy(previous)
    current_snapshot = copy.deepcopy(current)

    result = compare_object_reads(previous, current)
    assert result["before"] == previous_snapshot
    assert result["after"] == current_snapshot

    result["before"]["facts"]["price"] = 12345.0
    result["before"]["binding"]["security_id"] = "MUTATED"
    result["after"]["facts"]["currency"] = "MUT"

    assert previous == previous_snapshot
    assert current == current_snapshot


def test_mutating_inputs_does_not_reach_result():
    previous = _quote_record()
    current = _quote_record(facts={"price": 101.0})

    result = compare_object_reads(previous, current)

    previous["facts"]["price"] = 7.0
    previous["binding"]["security_id"] = "MUTATED"
    current["clocks"]["source_time"] = "2026-10-11T23:59:59+00:00"

    assert result["before"]["facts"]["price"] == 100.0
    assert result["before"]["binding"]["security_id"] == "SEC-778812"
    assert result["after"]["clocks"]["source_time"] == "2026-10-11T14:00:00Z"


@pytest.mark.parametrize("factory,key", [(_quote_record, "price"), (_plan_record, "invalidation")])
def test_unrepresentable_numeric_fact_fails_closed(factory, key):
    previous = factory()
    current = factory(facts={key: 10 ** 1000})
    _assert_unavailable(compare_object_reads(previous, current), "current_invalid")


@pytest.mark.parametrize("key", ["object_id", "owner", "source_ref", "generation_ref", "owner_receipt"])
def test_blank_owner_identity_or_receipt_is_missing(key):
    current = _quote_record(**{key: " \t "})
    _assert_unavailable(compare_object_reads(current, current), "previous_invalid")


def test_blank_review_ref_cannot_establish_lineage():
    current = _assessment_record(review_ref=" \n ")
    _assert_unavailable(compare_object_reads(current, current), "previous_invalid")


@pytest.mark.parametrize("market,currency", [("US", "USD"), ("HK", "HKD"), ("CN", "CNY"), ("CA", "CAD")])
def test_quote_change_does_not_refresh_other_objects_across_markets(market, currency):
    # Opaque test identities: no market-specific native schema is asserted here.
    binding = {"security_id": f"fixture-security-{market}", "episode_id": f"fixture-episode-{market}"}
    quote = _quote_record(binding=binding, facts={"currency": currency})
    assessment = _assessment_record(binding=binding)
    plan = _plan_record(binding=binding)
    current_quote = copy.deepcopy(quote)
    current_quote["facts"]["price"] = 101.0
    current_quote["owner_receipt"] = "new-quote-owner-receipt"
    current_quote["clocks"]["source_time"] = "2026-10-11T15:00:00Z"
    assert compare_object_reads(quote, current_quote)["changed_fields"] == ["price"]
    for record in (assessment, plan):
        result = compare_object_reads(record, copy.deepcopy(record))
        assert result["state"] == "unchanged"
        assert result["after"] == record
        assert "accepted" not in result
        assert "entry_availability" not in result


def test_assessment_lists_are_detached_even_for_same_input_object():
    record = _assessment_record()
    result = compare_object_reads(record, record)
    result["before"]["facts"]["evidence_refs"].append("later")
    assert result["after"]["facts"]["evidence_refs"] == ["ev-0001", "ev-0002"]
    assert record["facts"]["evidence_refs"] == ["ev-0001", "ev-0002"]
