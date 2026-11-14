"""Synthetic contract tests, not evidence of historical or prospective alpha."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from engine.release_actuals import normalize_publication
from engine.release_surprise_confirmation import (
    ACTUALS_PATH, CONSENSUS_PATH, EvidenceError, authority,
    build_confirmation_artifact, build_confirmation_pairs, build_surprise_history,
    digest, instant, normalize_consensus, read_consumer_context, read_jsonl, seal,
)

ASOF = "2026-11-13T22:00:00Z"


def actual_fixture(kind="CPI", *, day="2026-11-10", period="2026-10", headline=0.4, core=0.3):
    stamp = day + "T13:30:00Z"
    month = datetime.strptime(period, "%Y-%m").strftime("%B %Y")
    publication = {
        "event_id": kind.lower() + ":" + day, "type": kind, "date": day,
        "reference_period": month, "data_ready": True,
        "publisher": "U.S. Bureau of Labor Statistics",
        "source_id": "bls_" + kind.lower(),
        "source_url": "https://www.bls.gov/news.release/archives/" + kind.lower() + "_" + day.replace("-", "") + ".htm",
        "source_sha256": digest([kind, day, headline, core]),
        "first_seen_at": day + "T13:30:01Z", "observed_at": day + "T13:30:01Z",
        "source_released_at": stamp, "verified_at": day + "T13:31:00Z",
        "parser": {"name": kind.lower(), "version": 1},
        "actual": {"headline_mom": headline, "core_mom": core, "unit": "percent", "reference_period": month},
    }
    rows = normalize_publication(publication)
    assert rows
    return rows


def poll_fixture(actual, value=0.2, **updates):
    stamp = actual["release_date"]
    row = {
        "schema": "release_consensus.v1", "baseline_kind": "economist_consensus",
        "release": actual["release"], "period": actual["period"],
        "exact_target_id": actual["exact_target_id"], "unit": actual["unit"],
        "value": value, "source_id": "synthetic_poll", "source_url": "https://example.test/poll",
        "source_sha256": "b" * 64, "forecast_at": stamp + "T12:00:00Z",
        "observed_at": stamp + "T12:01:00Z", "recorded_at": stamp + "T12:02:00Z",
        "release_at": actual["source_released_at"], "rights": "redistribution_limited",
        "use_scopes": ["internal_research", "display_derived"], "rights_ref": "synthetic-test-only",
    }
    row.update(updates)
    return row


def history(tmp_path, actuals=None, polls=None, **kwargs):
    actuals = actuals if actuals is not None else actual_fixture()
    polls = polls if polls is not None else [poll_fixture(a) for a in actuals]
    return build_surprise_history(actuals, polls, asof=ASOF, defects_path=tmp_path / "defects.json", **kwargs)


def write_inputs(root, actuals, polls):
    for relative, rows in ((ACTUALS_PATH, actuals), (CONSENSUS_PATH, polls)):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def publish(root, artifact):
    p = root / "data/release_forecast/latest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"schema": "release_forecast.v2", "surprise_confirmation": artifact}))


def test_first_print_poll_join_is_continuous_and_neutral_is_separate(tmp_path):
    actuals = actual_fixture()
    result = history(tmp_path, actuals, [poll_fixture(a, a["actual"]) for a in actuals])
    assert all(e["direction"] == "neutral" and e["surprise"] == 0 for e in result["events"])
    assert all(e["normalization"]["zscore"] is None for e in result["events"])
    hot = history(tmp_path)["events"]
    assert sorted(e["surprise"] for e in hot) == pytest.approx([0.1, 0.2])
    assert all(e["authority"] == authority() for e in hot)


@pytest.mark.parametrize("field,value", [
    ("baseline_kind", "model_forecast"), ("baseline_kind", "prediction_market"),
    ("value", True), ("value", float("nan")), ("value", float("inf")),
    ("value", 10**400), ("value", -(10**400)),
    ("recorded_at", "2026-11-10T12:02:00"), ("source_sha256", "not-a-hash"),
    ("source_url", "http://example.test"), ("rights", "licensed"),
])
def test_bad_poll_never_becomes_consensus(tmp_path, field, value):
    actual = actual_fixture()[0]
    poll = poll_fixture(actual, **{field: value})
    with pytest.raises(EvidenceError):
        normalize_consensus(poll)
    result = history(tmp_path, [actual], [poll])
    assert not result["events"]
    assert result["reason_counts"]


@pytest.mark.parametrize("change", [
    {"recorded_at": "2026-11-10T13:30:00Z"},
    {"recorded_at": "2026-11-10T14:00:00Z"},
    {"release_at": "2026-11-10T14:30:00Z"},
    {"exact_target_id": "cpi_core_mom_printed_first"},
    {"unit": "thousands"}, {"period": "2026-09"},
    {"rights": "unknown", "rights_ref": None, "use_scopes": []},
])
def test_pre_release_target_and_rights_qualification(tmp_path, change):
    actual = actual_fixture()[0]
    assert not history(tmp_path, [actual], [poll_fixture(actual, **change)])["events"]


def test_source_ambiguity_is_not_averaged(tmp_path):
    actual = actual_fixture()[0]
    polls = [poll_fixture(actual), poll_fixture(actual, 0.1, source_id="second_poll")]
    result = history(tmp_path, [actual], polls)
    assert result["reason_counts"]["ambiguous_consensus_sources"] == 1
    chosen = history(tmp_path, [actual], polls, consensus_source_id="second_poll")
    assert chosen["events"][0]["consensus"] == 0.1


def test_receipt_hash_correction_and_conflict(tmp_path):
    actual = actual_fixture()[0]
    old = normalize_consensus(poll_fixture(actual))
    corrected = poll_fixture(actual, 0.1, recorded_at="2026-11-10T12:03:00Z", supersedes_receipt_id=old["receipt_id"])
    assert history(tmp_path, [actual], [old, corrected])["events"][0]["consensus"] == 0.1
    conflicting = poll_fixture(actual, 0.1)
    assert not history(tmp_path, [actual], [old, conflicting])["events"]
    tampered = {**old, "value": 0.8}
    assert not history(tmp_path, [actual], [old, tampered])["events"]


def test_future_poll_does_not_contaminate_earlier_cut(tmp_path):
    actual = actual_fixture()[0]
    old = poll_fixture(actual)
    future = poll_fixture(actual, 0.9, recorded_at="2026-12-01T12:00:00Z")
    result = history(tmp_path, [actual], [old, future])
    assert result["events"][0]["consensus"] == 0.2


def test_invalid_actual_clock_and_correction_candidate_are_excluded(tmp_path):
    actual = actual_fixture()[0]
    for change in ({"source_released_at": None}, {"verified_at": None},
                   {"verified_at": "2026-11-12T13:00:00Z"}, {"row_type": "correction_candidate"}):
        modified = {**actual, **change}
        assert not history(tmp_path, [modified], [poll_fixture(actual)])["events"]


def test_conflicting_first_prints_fail_closed(tmp_path):
    a = actual_fixture()[0]
    b = actual_fixture(headline=0.5)[0]
    result = history(tmp_path, [a, b], [poll_fixture(a)])
    assert result["reason_counts"]["conflicting_first_prints"] == 1


def test_pair_waits_for_second_release_and_keeps_both_clocks(tmp_path):
    actuals = actual_fixture() + actual_fixture("PPI", day="2026-11-13", headline=0.3)
    polls = [poll_fixture(a, 0.4 if a["release"] == "ppi_finaldemand" else 0.2) for a in actuals]
    events = history(tmp_path, actuals, polls)["events"]
    pairs = build_confirmation_pairs(events)
    assert len(pairs) == 2
    assert all(p["known_at"] == "2026-11-13T13:31:00Z" for p in pairs)
    assert all(p["cpi_known_at"] == "2026-11-10T13:31:00Z" for p in pairs)
    assert all(p["quadrant"] == "cpi_hot_ppi_cold" and p["agreement"] is False for p in pairs)
    with pytest.raises(EvidenceError, match="duplicate_release_period"):
        build_confirmation_pairs(events + events[:1])


def test_pair_neutral_is_not_disagreement(tmp_path):
    actuals = actual_fixture() + actual_fixture("PPI", day="2026-11-13", headline=0.2)
    events = history(tmp_path, actuals, [poll_fixture(a) for a in actuals])["events"]
    assert all(p["agreement"] is None for p in build_confirmation_pairs(events))


def test_normalization_uses_only_prior_known_same_source_observations(tmp_path):
    actuals, polls = [], []
    for month, value in ((8, 0.1), (9, 0.3), (10, 0.9), (11, 5.0)):
        row = actual_fixture(day=f"2026-{month:02d}-10", period=f"2026-{month-1:02d}", headline=value)[0]
        actuals.append(row)
        polls.append(poll_fixture(row, 0.2))
    result = history(tmp_path, actuals, polls, min_history=2)
    october = next(e for e in result["events"] if e["period"] == "2026-09")
    assert october["normalization"]["n_prior"] == 2
    assert october["normalization"]["mean_prior"] == pytest.approx(0)
    assert october["normalization"]["sd_prior"] == pytest.approx(0.1414213562)
    assert october["normalization"]["zscore"] == pytest.approx(0.7 / (0.02 ** 0.5))


def test_input_missing_empty_and_corrupt_are_distinct(tmp_path):
    p = tmp_path / "rows.jsonl"
    assert read_jsonl(p)[1]["status"] == "missing"
    p.write_text("")
    assert read_jsonl(p)[1]["status"] == "empty"
    p.write_text('{"bad":NaN}\n')
    assert read_jsonl(p)[1]["status"] == "invalid"
    p.write_text('{"ok":1}\nBROKEN\n')
    assert read_jsonl(p)[0] == []


def test_missing_consensus_survives_real_serialization_to_all_consumers(tmp_path):
    artifact = build_confirmation_artifact(tmp_path, asof=ASOF)
    assert artifact["status"] == "unavailable"
    assert "economist_consensus_history_unavailable" in artifact["reason_codes"]
    publish(tmp_path, artifact)
    for consumer in ("prophet", "sector_intelligence", "event_windows", "release_radar"):
        result = read_consumer_context(tmp_path, consumer=consumer, asof=ASOF)
        assert result["authority"] == authority()
        assert "economist_consensus_history_unavailable" in result["reason_codes"]
        assert result["source_digest"] == artifact["evidence_digest"]


def test_corrupt_input_remains_explicit_at_consumer(tmp_path):
    p = tmp_path / CONSENSUS_PATH
    p.parent.mkdir(parents=True)
    p.write_text("not-json\n")
    artifact = build_confirmation_artifact(tmp_path, asof=ASOF)
    publish(tmp_path, artifact)
    result = read_consumer_context(tmp_path, consumer="prophet", asof=ASOF)
    assert result["status"] == "input_invalid"
    assert result["reason_codes"] == ["input_integrity_failure"]


def test_display_rights_redaction_and_consumer_authority_fence(tmp_path):
    actuals = actual_fixture() + actual_fixture("PPI", day="2026-11-13", headline=0.3)
    polls = [poll_fixture(a) for a in actuals]
    write_inputs(tmp_path, actuals, polls)
    artifact = build_confirmation_artifact(tmp_path, asof=ASOF)
    assert artifact["status"] == "available_descriptive"
    assert all("consensus" not in row and "actual" not in row for row in artifact["latest_releases"])
    publish(tmp_path, artifact)
    assert len(read_consumer_context(tmp_path, consumer="prophet", asof=ASOF)["latest_pairs"]) == 2
    artifact["authority"]["can_trade"] = True
    publish(tmp_path, seal(artifact))
    assert read_consumer_context(tmp_path, consumer="prophet", asof=ASOF)["reason_codes"] == ["authority_ceiling_violation"]


def test_consumer_staleness_future_digest_and_bad_max_age(tmp_path):
    artifact = build_confirmation_artifact(tmp_path, asof=ASOF)
    publish(tmp_path, artifact)
    assert read_consumer_context(tmp_path, consumer="prophet", asof="2026-11-20T00:00:00Z")["reason_codes"] == ["artifact_stale_or_future"]
    assert read_consumer_context(tmp_path, consumer="prophet", asof="2026-11-12T00:00:00Z")["reason_codes"] == ["artifact_stale_or_future"]
    artifact["status"] = "invented"
    publish(tmp_path, artifact)
    assert read_consumer_context(tmp_path, consumer="prophet", asof=ASOF)["reason_codes"] == ["unknown_confirmation_status"]
    with pytest.raises(EvidenceError):
        read_consumer_context(tmp_path, consumer="prophet", asof=ASOF, max_age_hours=float("inf"))


def test_new_incomplete_month_does_not_promote_old_pair_to_current(tmp_path):
    older = actual_fixture(day="2026-10-10", period="2026-09") + actual_fixture("PPI", day="2026-10-13", period="2026-09")
    newer = actual_fixture()
    write_inputs(tmp_path, older + newer, [poll_fixture(a) for a in older])
    artifact = build_confirmation_artifact(tmp_path, asof=ASOF)
    assert artifact["status"] == "historical_context_only"
    assert all(p["freshness"] == "superseded_by_incomplete_period" for p in artifact["latest_pairs"])


def test_internal_research_rights_do_not_imply_display(tmp_path):
    actuals = actual_fixture() + actual_fixture("PPI", day="2026-11-13")
    write_inputs(tmp_path, actuals, [poll_fixture(a, use_scopes=["internal_research"]) for a in actuals])
    artifact = build_confirmation_artifact(tmp_path, asof=ASOF)
    assert artifact["eligible_event_count"] == 3
    assert artifact["latest_releases"] == artifact["latest_pairs"] == []
    assert "derived_display_rights_unavailable" in artifact["reason_codes"]


def test_display_only_license_does_not_authorize_research(tmp_path):
    actual = actual_fixture()[0]
    result = history(tmp_path, [actual], [poll_fixture(actual, rights="display_only")])
    assert not result["events"]
    assert "consensus_invalid:display_only_rights_block_research" in result["reason_counts"]


def test_sealed_but_semantically_inconsistent_pair_is_refused(tmp_path):
    actuals = actual_fixture() + actual_fixture("PPI", day="2026-11-13")
    write_inputs(tmp_path, actuals, [poll_fixture(a) for a in actuals])
    artifact = build_confirmation_artifact(tmp_path, asof=ASOF)
    artifact["latest_pairs"][0]["agreement"] = False
    publish(tmp_path, seal(artifact))
    result = read_consumer_context(tmp_path, consumer="prophet", asof=ASOF)
    assert result["reason_codes"] == ["inconsistent_pair_semantics"]


def test_first_report_clock_cannot_replace_paired_clock(tmp_path):
    actuals = actual_fixture() + actual_fixture("PPI", day="2026-11-13")
    write_inputs(tmp_path, actuals, [poll_fixture(a) for a in actuals])
    artifact = build_confirmation_artifact(tmp_path, asof=ASOF)
    artifact["latest_pairs"][0]["known_at"] = artifact["latest_pairs"][0]["cpi_known_at"]
    publish(tmp_path, seal(artifact))
    assert read_consumer_context(tmp_path, consumer="prophet", asof=ASOF)["reason_codes"] == ["pair_clock_not_second_report"]


def test_digest_tamper_does_not_disclose_unverified_projection(tmp_path):
    artifact = build_confirmation_artifact(tmp_path, asof=ASOF)
    artifact["paired_period_count"] = 999
    publish(tmp_path, artifact)
    assert read_consumer_context(tmp_path, consumer="prophet", asof=ASOF)["reason_codes"] == ["evidence_digest_mismatch"]


def test_nonobject_consumer_artifact_is_unavailable_not_a_consumer_crash(tmp_path):
    path = tmp_path / "data/release_forecast/latest.json"
    path.parent.mkdir(parents=True)
    path.write_text("[]")
    result = read_consumer_context(tmp_path, consumer="prophet", asof=ASOF)
    assert result["status"] == "unavailable" and result["reason_codes"] == ["release_forecast_invalid"]


def publish_overflow_context(root, value, *, asof=ASOF, field="cpi_surprise"):
    """Reseal a real synthetic artifact so numeric semantics, not its hash, fail."""
    actuals = actual_fixture() + actual_fixture("PPI", day="2026-11-13")
    write_inputs(root, actuals, [poll_fixture(a) for a in actuals])
    artifact = build_confirmation_artifact(root, asof=asof)
    assert artifact["latest_pairs"]
    artifact["latest_pairs"][0][field] = value
    publish(root, seal(artifact))


@pytest.mark.parametrize("value", [10**400, -(10**400)])
@pytest.mark.parametrize("field", ["cpi_surprise", "ppi_surprise"])
def test_sealed_numeric_overflow_is_unavailable_to_every_consumer(tmp_path, value, field):
    publish_overflow_context(tmp_path, value, field=field)
    for consumer in ("prophet", "sector_intelligence", "event_windows", "release_radar"):
        result = read_consumer_context(tmp_path, consumer=consumer, asof=ASOF)
        assert result["status"] == "unavailable"
        assert result["reason_codes"] == ["finite_number_required"]
        assert not result["latest_pairs"]
        assert result["authority"] == authority()


@pytest.mark.parametrize("body", [b"", b'{"x":1}\n', b"corrupt\n", b"\xff\n", b"x" * 9])
def test_jsonl_descriptor_uses_same_bounded_parser_and_original_generation(tmp_path, monkeypatch, body):
    import os
    from engine import release_surprise_confirmation as owner

    monkeypatch.setattr(owner, "MAX_INPUT_BYTES", 8)
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(body)
    expected = read_jsonl(path)
    fd = os.open(path, os.O_RDONLY)
    try:
        assert read_jsonl(path, fd=fd) == expected
        assert os.lseek(fd, 0, os.SEEK_CUR) == 0
        path.rename(tmp_path / "original.jsonl")
        path.write_bytes(b'{"y":2}\n')
        assert read_jsonl(path, fd=fd) == expected
        assert read_jsonl(path) != expected
        assert os.lseek(fd, 0, os.SEEK_CUR) == 0
    finally:
        os.close(fd)
