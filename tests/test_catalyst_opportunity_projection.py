"""Synthetic projection/reader conformance. Not market or production proof."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from engine.catalyst_opportunity.projection import build_opportunity_view, MAX_THEMES
from engine.catalyst_opportunity.reader import read_current_view, SOURCE_PATH, MAX_BYTES

NOW = datetime(2026, 10, 17, 15, tzinfo=timezone.utc)


def row(tid="defense", **updates):
    value = dict(id=tid, name="Defense", name_zh="Defense ZH", category="Industrial",
                 label="emerging", heat="idle", rel_5d=.015, pct50=.6,
                 rank=8, momentum_score=.4)
    value.update(updates)
    return value


def pulse(*rows, **updates):
    rows = list(rows) if rows else [row()]
    value = dict(schema=1, as_of="2026-10-16", region="us", n_themes=len(rows), themes=rows)
    value.update(updates)
    return value


def view(data, **overrides):
    kwargs = dict(assessed_at=NOW, received_at=NOW)
    kwargs.update(overrides)
    return build_opportunity_view(data, **kwargs)


def put(tmp_path, data):
    p = tmp_path / SOURCE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))
    return p


def test_market_only_case_is_useful_without_news_and_does_not_mutate():
    raw = pulse()
    original = deepcopy(raw)
    result = view(raw)
    assert raw == original
    assert result["status"] == "ready"
    case = result["cases"][0]
    assert case["origin"] == "market" and case["discovery_state"] == "provisional_watch"
    assert case["event"]["status"] == case["entry"]["status"] == "unavailable"
    assert not any(case["authority"].values()) and not any(result["authority"].values())
    assert result["coverage"]["complete"] is True
    assert result["source"]["precision"] == "date"
    assert result["source"]["historical_availability_proven"] is False


def test_leadership_is_distinct_from_emergence_and_has_caution():
    case = view(pulse(row(label="dominant", heat="hot", pct50=.75)))["cases"][0]
    assert case["watch_kind"] == "leadership_watch"
    assert "EXTENSION_NOT_CHECKED" in [c["code"] for c in case["cautions"]]


def test_weak_theme_remains_in_inventory_not_watch():
    result = view(pulse(row(label="deteriorating", heat="broken", pct50=0, rel_5d=-.05)))
    assert result["status"] == "empty" and result["cases"] == []
    assert result["coverage"]["valid"] == 1 and len(result["inventory"]) == 1


def test_healthy_zero_population_is_distinct_from_unavailable():
    empty = view(pulse(themes=[], n_themes=0))
    missing = view(None)
    assert empty["status"] == "empty" and empty["coverage"]["complete"]
    assert missing["status"] == "unavailable" and not missing["coverage"]["complete"]


def test_stale_source_is_not_disguised_as_live():
    result = view(pulse(as_of="2026-10-14"))
    assert result["status"] == "stale"
    assert result["source"]["age_calendar_days"] == 3
    assert result["cases"][0]["observation_status"] == "stale"
    assert result["cases"][0]["cautions"][0]["code"] == "DATED_OBSERVATION"


@pytest.mark.parametrize("raw", [None, False, {}, [], {"as_of":"bad"}])
def test_invalid_source_is_an_explicit_unavailable(raw):
    assert view(raw)["status"] == "unavailable"


@pytest.mark.parametrize("change", [{"schema":True}, {"schema":2}, {"region":"cn"}])
def test_closed_owner_contract(change):
    assert view(pulse(**change))["reason_codes"] == ["UNSUPPORTED_SOURCE_CONTRACT"]


def test_future_generation_noninterference_includes_counts_hash_and_status():
    a = pulse(as_of="2026-10-18")
    b = pulse(as_of="2027-01-01", schema=False, themes=[{"unsafe": "data"}] * 1500)
    assert view(a) == view(b)
    assert view(a)["source"] is None and view(a)["coverage"]["observed"] == 0


def test_future_receipt_cannot_be_backdated_using_source_date():
    future = NOW + timedelta(seconds=1)
    assert view(pulse(), received_at=future) == view({"corrupt":True}, received_at=future)
    assert view(pulse(), received_at=None)["reason_codes"] == ["RECEIPT_UNAVAILABLE"]


@pytest.mark.parametrize("which", ["assessed_at", "received_at"])
def test_naive_clock_refused(which):
    with pytest.raises(ValueError):
        view(pulse(), **{which:NOW.replace(tzinfo=None)})


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), "0.5", 10**999])
def test_bad_measurement_refuses_only_affected_row(bad):
    result = view(pulse(row(rel_5d=bad), row("energy_complex")))
    assert result["status"] == "partial"
    assert [c["theme_id"] for c in result["cases"]] == ["energy_complex"]
    assert result["refusals"][0]["reason"] == "INVALID_METRIC"


@pytest.mark.parametrize("value", [-.01, 1.001, True])
def test_breadth_fraction_denominator_is_not_guessed(value):
    assert view(pulse(row(pct50=value)))["coverage"]["refused"] == 1


def test_missing_breadth_is_not_zero_or_an_invented_leadership_signal():
    result = view(pulse(row(label="dominant", heat="hot", pct50=None)))
    assert result["cases"] == [] and result["coverage"]["valid"] == 1


def test_duplicate_theme_rows_never_choose_an_arbitrary_winner():
    result = view(pulse(row(), row(rel_5d=.9), row("energy_complex")))
    assert result["coverage"]["refused"] == 2
    assert [c["theme_id"] for c in result["cases"]] == ["energy_complex"]


def test_unsafe_identity_and_links_do_not_enter_view():
    result = view(pulse(row("../secret"), row(href="javascript:alert(1)", source_url="http://127.0.0.1")))
    assert result["coverage"]["refused"] == 1
    raw = json.dumps(result)
    assert "javascript:" not in raw and "127.0.0.1" not in raw and "../secret" not in raw


def test_order_and_values_preserved_without_a_new_score():
    result = view(pulse(row("energy_complex", rank=12), row(rank=1)))
    assert [c["theme_id"] for c in result["cases"]] == ["energy_complex", "defense"]
    assert result["cases"][0]["metrics"]["rank"] == 12
    assert "score" not in result["cases"][0]


def test_case_identity_survives_revisions_but_generation_changes():
    a, b = view(pulse()), view(pulse(row(rel_5d=.03)))
    assert a["cases"][0]["id"] == b["cases"][0]["id"]
    assert a["generation"] != b["generation"]


def test_repeated_transport_read_is_not_new_market_evidence():
    a = view(pulse())
    b = view(pulse(), assessed_at=NOW+timedelta(seconds=30), received_at=NOW+timedelta(seconds=30))
    assert a["generation"] == b["generation"]
    assert a["assessed_at"] != b["assessed_at"]


def test_incomplete_denominator_is_not_complete():
    result = view(pulse(n_themes=100))
    assert result["status"] == "partial"
    assert result["reason_codes"] == ["PARTIAL_POPULATION"]


@pytest.mark.parametrize("declared", [None, True, "1", -1])
def test_unknown_denominator_does_not_claim_missing_observations(declared):
    result = view(pulse(n_themes=declared))
    assert result["status"] == "partial"
    assert result["coverage"]["declared"] is None
    assert result["coverage"]["complete"] is False
    assert result["coverage"]["valid"] == 1
    assert result["reason_codes"] == ["UNKNOWN_POPULATION"]


def test_absent_denominator_remains_unknown():
    source = pulse()
    del source["n_themes"]
    assert view(source)["reason_codes"] == ["UNKNOWN_POPULATION"]


def test_unknown_denominator_does_not_hide_refused_rows():
    result = view(pulse(row(rel_5d=True), row("energy_complex"), n_themes=None))
    assert result["coverage"]["refused"] == 1
    assert result["reason_codes"] == ["UNKNOWN_POPULATION", "PARTIAL_POPULATION"]


def test_population_bound_refuses_not_truncates():
    assert view(pulse(themes=[row()]*(MAX_THEMES+1)))["reason_codes"] == ["INVALID_SOURCE_POPULATION"]


def test_real_file_reader_stamps_receipt_after_read_and_preserves_source_date(tmp_path):
    p = put(tmp_path, pulse(as_of="2026-10-14"))
    result = read_current_view(tmp_path, clock=lambda:NOW)
    assert result["status"] == "stale"
    assert result["source"]["received_at"] == "2026-10-17T15:00:00Z"
    import hashlib
    assert result["source"]["content_sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()


def test_reader_absent_corrupt_duplicate_and_oversized_input(tmp_path):
    assert read_current_view(tmp_path, clock=lambda:NOW)["status"] == "unavailable"
    p = put(tmp_path, {})
    for raw in ['not json', '{"as_of":"2026-10-16","as_of":"2026-10-17"}', '{"v": NaN}', ' '*(MAX_BYTES+1)]:
        p.write_text(raw)
        result = read_current_view(tmp_path, clock=lambda:NOW)
        assert result["status"] == "unavailable"
        assert str(tmp_path) not in json.dumps(result)


def test_reader_symlink_refused(tmp_path):
    p = put(tmp_path, pulse())
    target = tmp_path / "other.json"
    p.rename(target)
    p.symlink_to(target)
    assert read_current_view(tmp_path, clock=lambda:NOW)["status"] == "unavailable"


@pytest.mark.parametrize("change", [{"label":[]}, {"label":{}}, {"heat":[]}, {"heat":{}}])
def test_malformed_states_do_not_crash_other_rows(change):
    result = view(pulse(row(**change), row("energy_complex")))
    assert result["coverage"]["refused"] == 1
    assert len(result["cases"]) == 1


@pytest.mark.parametrize("date_value", ["20261016", "2026-W42-5", "2026-02-30"])
def test_date_precision_is_exact(date_value):
    assert view(pulse(as_of=date_value))["reason_codes"] == ["SOURCE_DATE_UNAVAILABLE"]
