"""PB-D cohort mechanics on explicitly synthetic, non-certified schedules.

The pure upstream quality-integrity verifier is replaced by a strict wire test
double.  The cohort's own Q/cut/issuer/time binding remains real.  Native evidence
and reviewer validation belong to test_pb_d_quality and the offline CLI join.
Nothing in these fixtures is an enrolled observation or calendar certification.
"""

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from zoneinfo import ZoneInfo

import pytest

from engine import pb_d_cohort as cohort


NY = ZoneInfo("America/New_York")
LABEL_SPEC = "PB_D_EVENT_QUALITY_LABEL_SPEC/v1.0"
SPRING_DATES = """
2026-03-02 2026-03-03 2026-03-04 2026-03-05 2026-03-06
2026-03-09 2026-03-10 2026-03-11 2026-03-12 2026-03-13
2026-03-16 2026-03-17 2026-03-18 2026-03-19 2026-03-20
2026-03-23 2026-03-24 2026-03-25 2026-03-26 2026-03-27
2026-03-30 2026-03-31 2026-04-01 2026-04-02 2026-04-06
2026-04-07 2026-04-08 2026-04-09 2026-04-10 2026-04-13
2026-04-14 2026-04-15 2026-04-16 2026-04-17
""".split()
FALL_DATES = """
2026-10-26 2026-10-27 2026-10-28 2026-10-29 2026-10-30
2026-11-02 2026-11-03 2026-11-04 2026-11-05 2026-11-06
2026-11-09 2026-11-10 2026-11-11 2026-11-12 2026-11-13
2026-11-16 2026-11-17 2026-11-18 2026-11-19 2026-11-20
2026-11-23 2026-11-24 2026-11-25 2026-11-27 2026-11-30
2026-12-01 2026-12-02 2026-12-03 2026-12-04 2026-12-07
2026-12-08 2026-12-09 2026-12-10 2026-12-11 2026-12-14
2026-12-15 2026-12-16 2026-12-17 2026-12-18 2026-12-21
2026-12-22 2026-12-23 2026-12-24 2026-12-28 2026-12-29
2026-12-30 2026-12-31
""".split()


def utc(stamp):
    return stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def resign_wire(receipt):
    receipt.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


@pytest.fixture(autouse=True)
def quality_wire_validator(monkeypatch):
    def valid(receipt):
        if not isinstance(receipt, dict):
            return False
        body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        return (receipt.get("schema") == "synthetic_cohort_quality_wire_test.v1"
                and type(receipt.get("q")) is str
                and receipt["q"] in {"TRUE", "FALSE", "UNKNOWN"}
                and receipt.get("receipt_sha256") == digest(body))
    monkeypatch.setattr(cohort, "_verify_quality_receipt", valid)


def schedule(dates=SPRING_DATES, *, early_closes=None):
    """Fabricate a fully explicit session list; do not infer calendar authority."""
    early_closes = early_closes or {}
    return {
        "calendar_id": "XNYS", "timezone": "America/New_York",
        "source_id": "synthetic-test-schedule-not-a-calendar-source", "version": "fixture-v1",
        "validation_receipt_id": "synthetic-test-attestation-only", "validated": True,
        "validated_at": "2026-01-01T00:00:00Z",
        "coverage_start": dates[0], "coverage_end": dates[-1],
        "sessions": [{
            "session_date": day,
            "market_open": datetime.combine(date.fromisoformat(day), time(9, 30), NY).isoformat(),
            "market_close": datetime.combine(date.fromisoformat(day), early_closes.get(day, time(16)), NY).isoformat(),
        } for day in dates],
    }


def versions():
    return {
        "board_population": "synthetic-published-usv3-buy-v1",
        "technical": "synthetic-native-t2-attestation-v1", "config_digest": "a" * 64,
        "attention": "legacy-compact-retained-n-recent-v1", "label_spec": LABEL_SPEC,
        "benchmark_mapping": "synthetic-frozen-sector-map-v1",
        "price_convention": "synthetic-declared-adjusted-convention-v1",
    }


def row(number, day="2026-03-05", **changes):
    clock = cohort.decision_clock(schedule(), day)
    issuer = f"cik:{number:010d}"
    result = {
        "observation_id": f"synthetic:{issuer}:{day}", "canonical_issuer_id": issuer,
        "ticker_at_cut": f"SYNTH{number}", "emitted_tier": "T2",
        "technical_attested": True, "technical_receipt_id": f"native-receipt-{number}-{day}",
        "native_event_id": f"native-event-{number}",
        "native_event_date": clock["board_session_date"],
        "native_t2_age": 0, "native_t2_age_unit": "native_2D_ticks",
        "sector": "Technology", "sector_benchmark": "XLK", "benchmark_mapping_complete": True,
        "attention_n_recent": 3, "attention_coverage_complete": True,
    }
    result.update(changes)
    return result


def wire_quality(record, clock, q):
    cut = datetime.fromisoformat(clock["cut_at_utc"].replace("Z", "+00:00"))
    return resign_wire({
        "schema": "synthetic_cohort_quality_wire_test.v1", "spec_version": LABEL_SPEC,
        "issuer_id": record["canonical_issuer_id"], "decision_cut": clock["cut_at_utc"],
        "freshness_start": clock["freshness_start_utc"],
        "completed_at": utc(cut - timedelta(minutes=1)), "q": q, "q_reasons": [],
    })


def cut(day="2026-03-05", rows=None, states=None):
    rows = rows if rows is not None else [row(1, day), row(2, day)]
    states = states if states is not None else ["TRUE", "FALSE"]
    clock = cohort.decision_clock(schedule(), day)
    stamp = datetime.fromisoformat(clock["cut_at_utc"].replace("Z", "+00:00"))
    return {
        "decision_date": day,
        "board_receipt": {
            "receipt_id": f"synthetic-board-{day}", "population": "us_prophet_v3", "lane": "buy",
            "published": True, "board_session_date": clock["board_session_date"],
            "price_session_date": clock["board_session_date"],
            "board_as_of_at": clock["board_session_close_at_utc"],
            "price_as_of_at": clock["board_session_close_at_utc"],
            "generated_at": utc(stamp - timedelta(hours=1)),
            "received_at": utc(stamp - timedelta(minutes=30)),
            "source_snapshot_sha256": "b" * 64, "price_source_vintage": "synthetic-price-vintage",
            "versions": versions(),
        },
        "rows": rows,
        "quality_by_observation": {
            record["observation_id"]: wire_quality(record, clock, state)
            for record, state in zip(rows, states) if state is not None
        },
    }


def packet(cuts=None):
    cuts = cuts if cuts is not None else [cut()]
    days = sorted(item["decision_date"] for item in cuts)
    return {
        "operation_key": cohort.OPERATION_KEY, "cohort_id": "SYNTHETIC-NOT-ENROLLED",
        "first_cut_date": days[0], "through_cut_date": days[-1],
        "versions": versions(), "schedule": schedule(), "cuts": cuts,
    }


def freeze(value=None):
    return cohort.freeze_cohort(packet() if value is None else value)["manifest"]


def test_cut_dst_spring_and_fall_use_new_york_zone():
    before = cohort.decision_clock(schedule(), "2026-03-06")
    after = cohort.decision_clock(schedule(), "2026-03-09")
    assert before["cut_at_utc"] == "2026-03-06T14:15:00Z"
    assert after["cut_at_utc"] == "2026-03-09T13:15:00Z"
    assert after["freshness_start_utc"] == "2026-03-04T14:15:00Z"
    assert after["board_session_date"] == "2026-03-06"
    assert cohort.decision_clock(schedule(FALL_DATES), "2026-10-30")["cut_at_utc"] == "2026-10-30T13:15:00Z"
    assert cohort.decision_clock(schedule(FALL_DATES), "2026-11-02")["cut_at_utc"] == "2026-11-02T14:15:00Z"


def test_entry_and_exits_are_explicit_session_closes_not_calendar_days():
    clock = cohort.decision_clock(schedule(), "2026-03-06")
    assert clock["entry_session_date"] == "2026-03-06"
    assert clock["entry_close_at_utc"] == "2026-03-06T21:00:00Z"
    assert clock["exits"]["H1"] == {"session_date": "2026-03-09", "close_at_utc": "2026-03-09T20:00:00Z"}
    assert clock["exits"]["H5"]["session_date"] == "2026-03-13"
    assert clock["exits"]["H21"]["session_date"] == "2026-04-07"


def test_explicit_holiday_gap_and_early_close_are_not_filled_in():
    supplied = schedule(FALL_DATES, early_closes={"2026-11-27": time(13)})
    clock = cohort.decision_clock(supplied, "2026-11-27")
    assert clock["board_session_date"] == "2026-11-25"
    assert clock["freshness_start_utc"] == "2026-11-23T14:15:00Z"
    assert clock["entry_close_at_utc"] == "2026-11-27T18:00:00Z"
    assert clock["exits"]["H1"]["session_date"] == "2026-11-30"
    with pytest.raises(cohort.CohortInputError, match="not in the supplied"):
        cohort.decision_clock(supplied, "2026-11-26")


@pytest.mark.parametrize("mutation", [
    lambda s: s.update(validated=False),
    lambda s: s.update(validated_at="2026-03-05T14:15:00.000001Z"),
    lambda s: s["sessions"][3].update(market_close="2026-03-05"),
    lambda s: s["sessions"].insert(4, deepcopy(s["sessions"][3])),
    lambda s: s["sessions"][3].update(market_close="2026-03-06T00:30:00-05:00"),
    lambda s: s.update(sessions=s["sessions"][:10]),
])
def test_schedule_refuses_missing_validation_malformed_or_incomplete_clocks(mutation):
    supplied = schedule()
    mutation(supplied)
    with pytest.raises(cohort.CohortInputError):
        cohort.decision_clock(supplied, "2026-03-05")


def test_cannot_invent_prior_freshness_cuts():
    with pytest.raises(cohort.CohortInputError, match="three prior"):
        cohort.decision_clock(schedule(), "2026-03-04")


def test_actual_receipt_exactly_at_cut_is_available_but_one_microsecond_late_is_not():
    data = packet()
    data["cuts"][0]["board_receipt"]["received_at"] = "2026-03-05T14:15:00Z"
    assert freeze(data)["accounting"]["frozen_pairs"] == 1
    data["cuts"][0]["board_receipt"]["received_at"] = "2026-03-05T14:15:00.000001Z"
    result = freeze(data)
    assert result["first_t2"] == []
    assert result["accounting"]["quarantined_board_cuts"] == 1
    assert "BOARD_OR_PRICE_UNAVAILABLE_AT_CUT" in result["board_receipts"][0]["issues"]


@pytest.mark.parametrize("field,value", [
    ("board_session_date", "2026-03-03"),
    ("price_session_date", "2026-03-05"),
    ("price_as_of_at", "2026-03-05T21:00:00Z"),
    ("generated_at", "2026-03-05"),
    ("generated_at", "2026-03-05T15:00:00Z"),
    ("published", False),
    ("population", "pre_cap_market_wide"),
    ("lane", "sell"),
])
def test_stale_future_date_only_or_wrong_population_boards_are_quarantined(field, value):
    data = packet()
    data["cuts"][0]["board_receipt"][field] = value
    result = freeze(data)
    assert result["first_t2"] == []
    assert result["pairs"] == []
    assert result["board_receipts"][0]["receipt_admissible"] is False


def test_missing_required_board_metadata_is_a_gap_not_a_complete_empty_board():
    data = packet()
    del data["cuts"][0]["board_receipt"]["received_at"]
    result = freeze(data)
    assert result["accounting"]["quarantined_board_cuts"] == 1
    assert result["accounting"]["first_observed_t2"] == 0


def test_first_t2_unknown_consumes_slot_before_later_favorable_quality(monkeypatch):
    original = cut(rows=[row(1), row(2)], states=[None, "FALSE"])
    later = cut("2026-03-06", [row(1, "2026-03-06"), row(3, "2026-03-06")], ["TRUE", "FALSE"])
    inspected = []
    original_validator = cohort._verify_quality_receipt
    def record_reads(receipt):
        inspected.append((receipt["issuer_id"], receipt["decision_cut"]))
        return original_validator(receipt)
    monkeypatch.setattr(cohort, "_verify_quality_receipt", record_reads)
    result = freeze(packet([original, later]))
    first = next(record for record in result["first_t2"] if record["canonical_issuer_id"] == row(1)["canonical_issuer_id"])
    assert first["q"] == "UNKNOWN" and first["decision_date"] == "2026-03-05"
    assert first["primary_slot_consumed"] is True
    assert result["accounting"]["repeated_t2_excluded"] == 1
    assert result["pairs"] == []
    assert (row(1)["canonical_issuer_id"], "2026-03-06T14:15:00Z") not in inspected


def test_t1_precedence_is_taken_from_emitted_classification_not_native_fields():
    earlier = cut(rows=[row(1, emitted_tier="T1")], states=["TRUE"])
    later = cut("2026-03-06", [row(1, "2026-03-06"), row(2, "2026-03-06")], ["TRUE", "FALSE"])
    result = freeze(packet([earlier, later]))
    assert result["first_t2"][0]["decision_date"] == "2026-03-06"
    assert result["other_observations"][0]["emitted_tier"] == "T1"
    assert result["accounting"]["frozen_pairs"] == 1


@pytest.mark.parametrize("changes", [
    {"native_t2_age": None}, {"native_t2_age": 3},
    {"native_t2_age_unit": "calendar_days"}, {"technical_attested": None},
    {"native_event_id": None}, {"native_event_date": "2026-03-05"},
])
def test_first_t2_technical_quarantine_is_retained_and_not_replaced(changes):
    earlier = cut(rows=[row(1, **changes)], states=["TRUE"])
    later = cut("2026-03-06", [row(1, "2026-03-06")], ["TRUE"])
    result = freeze(packet([earlier, later]))
    assert len(result["first_t2"]) == 1
    assert result["first_t2"][0]["matching_eligible"] is False
    assert result["accounting"]["repeated_t2_excluded"] == 1


@pytest.mark.parametrize("count,coverage,expected", [(2, True, "FALSE"), (3, True, "TRUE"),
                                                       (0, False, "UNKNOWN"), (None, True, "UNKNOWN")])
def test_raw_attention_keeps_frozen_n_recent_semantics(count, coverage, expected):
    result = freeze(packet([cut(rows=[row(1, attention_n_recent=count, attention_coverage_complete=coverage)], states=["TRUE"])]))
    assert result["first_t2"][0]["raw_attention"] == expected


@pytest.mark.parametrize("field,value,reason", [
    ("completed_at", "2026-03-05T14:15:00.000001Z", "QUALITY_COMPLETED_AFTER_CUT"),
    ("completed_at", None, "QUALITY_INCOMPLETE_AT_CUT"),
    ("issuer_id", "cik:0000000099", "QUALITY_ISSUER_MISMATCH"),
    ("decision_cut", "2026-03-05T14:14:00Z", "QUALITY_CUT_MISMATCH"),
    ("freshness_start", "2026-03-03T14:15:00Z", "QUALITY_FRESHNESS_WINDOW_MISMATCH"),
    ("spec_version", "future-unfrozen-spec", "QUALITY_LABEL_SPEC_VERSION_MISMATCH"),
    ("q", True, "INVALID_QUALITY_RECEIPT"),
])
def test_quality_binding_late_unknown_and_strict_tristate(field, value, reason):
    data = packet()
    quality = next(iter(data["cuts"][0]["quality_by_observation"].values()))
    quality[field] = value
    resign_wire(quality)
    result = freeze(data)
    assert result["first_t2"][0]["q"] == "UNKNOWN"
    assert reason in result["first_t2"][0]["q_reasons"]
    assert result["pairs"] == []


def test_tampered_quality_hash_cannot_become_a_control():
    data = packet()
    quality = data["cuts"][0]["quality_by_observation"][row(2)["observation_id"]]
    quality["q"] = "TRUE"
    result = freeze(data)
    assert result["first_t2"][1]["q"] == "UNKNOWN"
    assert result["accounting"]["eligible_q_false"] == 0


def test_exact_matching_uses_hash_order_one_to_one_without_replacement():
    records = [row(number) for number in range(1, 6)]
    result = freeze(packet([cut(rows=records, states=["TRUE", "TRUE", "TRUE", "FALSE", "FALSE"])]))
    key = lambda r: hashlib.sha256(f"{cohort.OPERATION_KEY}|SYNTHETIC-NOT-ENROLLED|{r['canonical_issuer_id']}".encode()).hexdigest()
    treated = sorted(records[:3], key=key)
    controls = sorted(records[3:], key=key)
    assert [(pair["q1_observation_id"], pair["q0_observation_id"]) for pair in result["pairs"]] == [
        (t["observation_id"], c["observation_id"]) for t, c in zip(treated, controls)
    ]
    assert len({pair["q0_issuer_id"] for pair in result["pairs"]}) == 2
    assert result["accounting"]["primary_matched_support_fraction"] == pytest.approx(2 / 3)
    assert any(row["reasons"] == ["NO_CONTROL_IN_EXACT_STRATUM"] for row in result["unmatched"])


@pytest.mark.parametrize("change", [
    {"sector": "Energy", "sector_benchmark": "XLE"},
    {"attention_n_recent": 2}, {"native_t2_age": 1},
])
def test_no_widening_of_sector_attention_or_native_age_strata(change):
    result = freeze(packet([cut(rows=[row(1), row(2, **change)], states=["TRUE", "FALSE"])]))
    assert result["pairs"] == []
    assert result["accounting"]["eligible_q_true"] == 1
    assert result["accounting"]["primary_matched_support_fraction"] == 0


def test_no_control_reuse_or_cross_date_matching():
    day1 = cut(rows=[row(1), row(2)], states=["TRUE", "FALSE"])
    day2 = cut("2026-03-06", [row(3, "2026-03-06"), row(2, "2026-03-06")], ["TRUE", "FALSE"])
    result = freeze(packet([day1, day2]))
    assert len(result["pairs"]) == 1
    assert result["accounting"]["eligible_q_true"] == 2
    assert result["accounting"]["primary_matched_support_fraction"] == 0.5


def test_inconsistent_frozen_benchmark_mapping_quarantines_the_sector():
    result = freeze(packet([cut(rows=[row(1), row(2, sector_benchmark="WRONG")])]))
    assert result["pairs"] == []
    assert all("INCONSISTENT_SECTOR_BENCHMARK_MAPPING" in r["matching_exclusion_reasons"] for r in result["first_t2"])


def test_missing_earlier_board_makes_later_firstness_unknown():
    missing = cut(rows=[], states=[])
    missing["board_receipt"] = None
    later = cut("2026-03-06")
    result = freeze(packet([missing, later]))
    assert result["accounting"]["first_observed_t2"] == 2
    assert result["accounting"]["firstness_unknown"] == 2
    assert result["pairs"] == []
    assert all(record["primary_slot_consumed"] for record in result["first_t2"])


def test_owner_native_continuous_history_can_resolve_a_prefix_gap_before_first_observation():
    missing = cut(rows=[], states=[])
    missing["board_receipt"] = None
    later = cut("2026-03-06")
    for record in later["rows"]:
        record["firstness_history"] = {
            "receipt_id": "synthetic-native-history-absence-receipt", "owner": "us_prophet_v3",
            "canonical_issuer_id": record["canonical_issuer_id"],
            "coverage_first_cut_date": "2026-03-05", "coverage_through_cut_date": "2026-03-05",
            "coverage_complete": True, "no_prior_t2": True,
            "generated_at": "2026-03-06T13:00:00Z", "observed_at": "2026-03-06T13:01:00Z",
            "source_snapshot_sha256": "c" * 64,
        }
    result = freeze(packet([missing, later]))
    assert len(result["pairs"]) == 1
    assert all(row["firstness"] == "OWNER_NATIVE_HISTORY_ATTESTATION" for row in result["first_t2"])
    later["rows"][0]["firstness_history"]["coverage_through_cut_date"] = "2026-03-04"
    assert freeze(packet([missing, later]))["pairs"] == []


def test_cannot_omit_a_scheduled_cut_then_claim_firstness():
    data = packet([cut(), cut("2026-03-09")])
    with pytest.raises(cohort.CohortInputError, match="every scheduled cut"):
        cohort.freeze_cohort(data)


def test_version_change_ends_era_even_if_the_old_version_returns():
    first = cut(rows=[], states=[])
    changed = cut("2026-03-06", rows=[], states=[])
    changed["board_receipt"]["versions"]["technical"] = "changed-native-technical-era"
    reverted = cut("2026-03-09")
    result = freeze(packet([first, changed, reverted]))
    assert result["era_ended_before_cut"] == "2026-03-06"
    assert result["first_t2"] == []
    assert result["accounting"]["quarantined_board_cuts"] == 2


def test_input_order_does_not_change_hash_or_pairs_and_input_is_not_mutated():
    data = packet([cut(), cut("2026-03-06", [row(3, "2026-03-06"), row(4, "2026-03-06")])])
    before = deepcopy(data)
    frozen = cohort.freeze_cohort(data)
    assert data == before
    data["cuts"].reverse()
    for item in data["cuts"]:
        item["rows"].reverse()
        item["quality_by_observation"] = dict(reversed(list(item["quality_by_observation"].items())))
    assert cohort.freeze_cohort(data) == frozen
    assert cohort.verify_manifest(frozen)


@pytest.mark.parametrize("field", ["entry_status", "h5_spy_excess", "outcomes", "adjusted_close"])
def test_selection_api_rejects_outcomes_and_entry_status(field):
    data = packet()
    data["cuts"][0]["rows"][0][field] = 1
    with pytest.raises(cohort.CohortInputError, match="unsupported fields"):
        cohort.freeze_cohort(data)


def test_board_outcome_fields_are_not_retained_as_archival_metadata():
    data = packet()
    data["cuts"][0]["board_receipt"]["future_returns"] = [99]
    with pytest.raises(cohort.CohortInputError, match="outcome data"):
        cohort.freeze_cohort(data)


@pytest.mark.parametrize("history", [["outcome_h5_pp", 999], "outcomes", 999, False, {}])
def test_unused_optional_history_cannot_smuggle_untyped_metadata_on_complete_prefix(history):
    data = packet()
    data["cuts"][0]["rows"][0]["firstness_history"] = history
    with pytest.raises(cohort.CohortInputError, match="firstness_history"):
        cohort.freeze_cohort(data)


@pytest.mark.parametrize("change", [
    {"coverage_complete": "true"}, {"no_prior_t2": 1},
    {"generated_at": "2026-03-05"}, {"source_snapshot_sha256": ["future_outcome", 99]},
    {"outcome_h5_pp": 999},
])
def test_unused_history_mapping_is_strictly_typed_on_every_path(change):
    data = packet()
    history = {
        "receipt_id": "synthetic-native-history", "owner": "us_prophet_v3",
        "canonical_issuer_id": row(1)["canonical_issuer_id"],
        "coverage_first_cut_date": "2026-03-05", "coverage_through_cut_date": "2026-03-05",
        "coverage_complete": True, "no_prior_t2": True,
        "generated_at": "2026-03-05T13:00:00Z", "observed_at": "2026-03-05T13:01:00Z",
        "source_snapshot_sha256": "c" * 64,
    }
    history.update(change)
    data["cuts"][0]["rows"][0]["firstness_history"] = history
    with pytest.raises(cohort.CohortInputError, match="firstness_history"):
        cohort.freeze_cohort(data)


def test_duplicate_canonical_issuer_or_observation_identity_needs_owner_resolution():
    data = packet()
    data["cuts"][0]["rows"][1]["canonical_issuer_id"] = row(1)["canonical_issuer_id"]
    with pytest.raises(cohort.CohortInputError, match="duplicate canonical issuer"):
        cohort.freeze_cohort(data)
    data = packet()
    data["cuts"][0]["rows"][1]["observation_id"] = row(1)["observation_id"]
    with pytest.raises(cohort.CohortInputError, match="observation_id must be unique"):
        cohort.freeze_cohort(data)


def correction():
    return {
        "correction_id": "synthetic-correction-1", "target_observation_id": row(1)["observation_id"],
        "original_claim_id": "existing-claim-1", "reason": "Supplied source revision changes later context",
        "correction_type": "SOURCE_REVISION", "available_at": "2026-03-06T12:00:00Z",
        "observed_at": "2026-03-06T12:01:00Z", "corrected_receipt_sha256": "d" * 64,
    }


def test_corrections_append_provenance_without_rewriting_primary_q_or_pairs():
    original = cohort.freeze_cohort(packet())
    before = deepcopy(original)
    revised = cohort.append_correction(original, correction())
    assert original == before
    assert revised["manifest"] == original["manifest"]
    assert revised["manifest_sha256"] == original["manifest_sha256"]
    assert cohort.verify_manifest(revised)
    integrity = correction()
    integrity.update(correction_id="synthetic-correction-2", correction_type="DATA_INTEGRITY_EXCEPTION",
                     observed_at="2026-03-07T12:01:00Z")
    twice = cohort.append_correction(revised, integrity)
    assert len(twice["manifest"]["pairs"]) == 1
    assert twice["corrections"][1]["previous_correction_sha256"] == twice["corrections"][0]["correction_sha256"]
    assert cohort.verify_manifest(twice)
    with pytest.raises(cohort.CohortInputError, match="already exists"):
        cohort.append_correction(revised, correction())


def test_manifest_or_correction_tampering_fails_integrity_check():
    frozen = cohort.freeze_cohort(packet())
    modified = deepcopy(frozen)
    modified["manifest"]["first_t2"][0]["q"] = "FALSE"
    assert not cohort.verify_manifest(modified)
    with pytest.raises(cohort.CohortInputError, match="modified original"):
        cohort.append_correction(modified, correction())
    revised = cohort.append_correction(frozen, correction())
    revised["corrections"][0]["correction"]["reason"] = "changed without an append"
    assert not cohort.verify_manifest(revised)


def test_omission_rematches_complete_original_pool_and_admits_previously_unused_control():
    records = [row(number) for number in range(1, 6)]
    original = cohort.freeze_cohort(packet([cut(rows=records, states=["TRUE", "TRUE", "FALSE", "FALSE", "FALSE"])]))
    before = deepcopy(original)
    control_ids = [record["canonical_issuer_id"] for record in sorted(records[2:], key=lambda record:
        cohort.issuer_order_hash(cohort.OPERATION_KEY, "SYNTHETIC-NOT-ENROLLED", record["canonical_issuer_id"]))]
    original_controls = {pair["q0_issuer_id"] for pair in original["manifest"]["pairs"]}
    assert control_ids[2] not in original_controls
    derived = cohort.rematch_omission(original, [control_ids[0]])
    assert original == before
    assert derived["parent_manifest_sha256"] == original["manifest_sha256"]
    assert derived["omitted_issuer_ids"] == [control_ids[0]]
    assert derived["eligible_q1_count"] == 2 and derived["eligible_q0_count"] == 2
    assert len(derived["pairs"]) == 2
    assert {pair["q0_issuer_id"] for pair in derived["pairs"]} == set(control_ids[1:])
    assert control_ids[2] in {pair["q0_issuer_id"] for pair in derived["pairs"]}
    assert len([pair for pair in original["manifest"]["pairs"] if pair["q0_issuer_id"] != control_ids[0]]) == 1
    body = {key: value for key, value in derived.items() if key != "receipt_sha256"}
    assert derived["receipt_sha256"] == digest(body)
    assert set(derived["authority_flags"].values()) == {False}


def test_omission_never_reclassifies_or_replaces_original_first_observations():
    first = cut(rows=[row(1), row(2), row(3)], states=[None, "TRUE", "FALSE"])
    later = cut("2026-03-06", [row(1, "2026-03-06")], ["TRUE"])
    original = cohort.freeze_cohort(packet([first, later]))
    derived = cohort.rematch_omission(original, [row(2)["canonical_issuer_id"]])
    assert derived["eligible_q1_count"] == 0
    assert derived["pairs"] == []
    assert row(1, "2026-03-06")["observation_id"] not in derived["retained_observation_ids"]
    assert original["manifest"]["first_t2"][0]["q"] == "UNKNOWN"


@pytest.mark.parametrize("omitted", [
    ["cik:0000000999"], ["cik:0000000001", "cik:0000000001"],
    "cik:0000000001", [True],
])
def test_omission_rejects_unknown_duplicate_or_malformed_issuer_ids(omitted):
    with pytest.raises(cohort.CohortInputError):
        cohort.rematch_omission(cohort.freeze_cohort(packet()), omitted)


def test_empty_omission_is_an_explicit_unchanged_pool_and_modified_parent_is_refused():
    original = cohort.freeze_cohort(packet())
    derived = cohort.rematch_omission(original, [])
    assert derived["omitted_issuer_ids"] == []
    assert derived["pairs"] == original["manifest"]["pairs"]
    original["manifest"]["pairs"].clear()
    with pytest.raises(cohort.CohortInputError, match="modified original"):
        cohort.rematch_omission(original, [])


def test_all_frozen_artifacts_remain_unenrolled_and_owner_claims_are_not_signatures():
    frozen = cohort.freeze_cohort(packet())
    manifest = frozen["manifest"]
    assert manifest["research_only"] is True
    assert manifest["enrollment_status"] == "NOT_ENROLLED"
    assert set(manifest["authority_flags"].values()) == {False}
    assert "supplied_owner_receipts_only" in manifest["provenance_scope"]
    assert "structural_checks_only" in manifest["schedule"]["validation_scope"]
    manifest["authority_flags"]["entry"] = True
    frozen["manifest_sha256"] = digest(manifest)
    assert not cohort.verify_manifest(frozen)
