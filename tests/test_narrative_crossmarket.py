"""Cross-market narrative cross-reference — gates + structure (display-only).

Pure-function tests over a synthetic site/ tree (no real caches needed): the canon crosswalk,
the region-specificity exclusion, the macro-regime-alignment flag, the China↔HK co-listing flag,
and the 'hotter elsewhere' suppression under regime divergence.
"""
from __future__ import annotations

import json

from engine import narrative_crossmarket as xm


def _write_market(site, data_dir, region, themes, quad=None):
    d = site / xm._BASKETS_DATA[region]
    d.mkdir(parents=True, exist_ok=True)
    (d / "baskets.json").write_text(json.dumps({"theme_intel": {"as_of": "2026-06-19", "themes": themes}}))
    if quad is not None:
        rd = data_dir / ("regime" if region == "us" else f"{region}_regime")
        rd.mkdir(parents=True, exist_ok=True)
        (rd / "latest.json").write_text(json.dumps({"quad": quad}))


def _theme(bid, name, score, label="neutral", accel=0.0, rel=0.0):
    return {"id": bid, "name": name, "name_zh": name, "score": score, "label": label,
            "reco": "hold", "accel_z": accel, "perf": {"20d": {"rel": rel}}}


def _setup(tmp_path, monkeypatch):
    site = tmp_path / "site"
    data = tmp_path / "data"
    monkeypatch.setattr(xm.config, "data_dir", lambda: data)
    # US (Q1) and China (Q3) both run semis; canada (Q1) runs gold; HK runs autos (co-listed w/ china)
    _write_market(site, data, "us", [_theme("ai_semiconductors", "US Semis", 80, "dominant", 1.0)], quad="Q1")
    _write_market(site, data, "china", [_theme("cn_semis", "CN Semis", 55, "neutral"),
                                        _theme("cn_autos", "CN Autos", 60, "emerging", 1.0)], quad="Q3")
    _write_market(site, data, "hk", [_theme("hk_ev", "HK EV", 50, "neutral")], quad="Q2")
    _write_market(site, data, "canada", [_theme("ca_gold", "CA Gold", 70, "dominant")], quad="Q1")
    return site


def test_region_specificity_excludes_domestic_themes(tmp_path, monkeypatch):
    site = _setup(tmp_path, monkeypatch)
    cm = xm.compute_crossmarket(site)
    # banks / housing / utilities etc. are NOT in the canon → never get a chip
    domestic = {"regional_banks", "cn_banks", "hk_banks", "ca_banks", "housing", "ca_reits", "hk_gaming"}
    for region, themes in cm["links"].items():
        assert not (set(themes) & domestic), f"{region} leaked a domestic theme into the crosswalk"


def test_regime_caveat_flags_divergent_macro(tmp_path, monkeypatch):
    site = _setup(tmp_path, monkeypatch)
    cm = xm.compute_crossmarket(site)
    # China(Q3) ↔ US(Q1) semis cross-ref must carry the regime caveat
    cn = cm["links"]["china"]["cn_semis"]
    us_ref = next(o for o in cn["others"] if o["region"] == "us")
    assert us_ref["regime_caveat"] is True
    assert us_ref["co_listed"] is False


def test_co_listing_flags_china_hk(tmp_path, monkeypatch):
    site = _setup(tmp_path, monkeypatch)
    cm = xm.compute_crossmarket(site)
    cn = cm["links"]["china"]["cn_autos"]
    hk_ref = next(o for o in cn["others"] if o["region"] == "hk")
    assert hk_ref["co_listed"] is True


def test_hotter_elsewhere_suppressed_under_regime_divergence(tmp_path, monkeypatch):
    site = _setup(tmp_path, monkeypatch)
    cm = xm.compute_crossmarket(site)
    # CN Semis (55) vs US Semis (80, dominant) — would be "hotter", but US is in a DIFFERENT regime
    # (Q1 vs Q3) so it must NOT be claimed as a clean early-detection.
    cn = cm["links"]["china"]["cn_semis"]
    assert "us" not in cn["hotter_elsewhere"]


def test_disclaimer_and_quads_present(tmp_path, monkeypatch):
    site = _setup(tmp_path, monkeypatch)
    cm = xm.compute_crossmarket(site)
    assert "NOT a validated signal" in cm["disclaimer"]["en"]
    assert cm["quads"]["us"] == "Q1" and cm["quads"]["china"] == "Q3"
    assert cm["quads"]["intl"] is None                      # intl has no single regime


# China consumer contracts, not validation of profitable lead-lag or Buy Now admission.
from datetime import datetime, timezone

import pytest

_CONTEXT_NOW = datetime(2026, 9, 21, 10, tzinfo=timezone.utc)


def _context_site(tmp_path, *, us_date="2026-09-18", cn_date="2026-09-21", us_rows=None, cn_rows=None):
    site = tmp_path / "site"
    if us_rows is None:
        us_rows = [{**_theme("ai_semiconductors", "US Semis", 82, "dominant"), "reco": "accumulate"}]
    if cn_rows is None:
        cn_rows = [{**_theme("cn_semis", "CN Semis", 54, "emerging"), "reco": "enter",
                    "textures": {"clean_entry": {"flag": False}}}]
    for region, as_of, rows in (("us", us_date, us_rows), ("china", cn_date, cn_rows)):
        d = site / xm._BASKETS_DATA[region]
        d.mkdir(parents=True, exist_ok=True)
        (d / "baskets.json").write_text(json.dumps({"theme_intel": {"as_of": as_of, "themes": rows}}))
    return site


def _context(site, now=_CONTEXT_NOW, **kwargs):
    return xm.compute_china_us_context(site, observed_at=now, **kwargs)


def test_cn_context_connects_exact_ids_with_distinct_source_receipts(tmp_path):
    result = _context(_context_site(tmp_path))
    row = result["themes"]["cn_semis"]
    assert result["status"] == "CURRENT"
    assert row["observation_state"] == "US_STRENGTH_LOCAL_CONFIRMING"
    assert row["local"]["id"] == "cn_semis"
    assert row["us_analogs"][0]["id"] == "ai_semiconductors"
    assert row["relationship"] == {"kind": "theme_analog", "canon": "semiconductors", "exact_member_link": False}
    assert result["sources"]["us"]["observation_session"] == "2026-09-18"
    assert result["sources"]["china"]["observation_session"] == "2026-09-21"
    assert len(result["sources"]["us"]["sha256"]) == len(result["crosswalk_sha256"]) == 64


def test_cn_context_retains_constructive_stance_without_a_fresh_clean_entry(tmp_path):
    site = _context_site(tmp_path)
    before = _context(site)["themes"]["cn_semis"]
    p = site / "chinabasketdata" / "baskets.json"
    data = json.loads(p.read_text())
    data["theme_intel"]["themes"][0]["textures"]["clean_entry"]["flag"] = True
    p.write_text(json.dumps(data))
    after = _context(site)["themes"]["cn_semis"]
    assert before["local"]["clean_entry"] is False and after["local"]["clean_entry"] is True
    assert before["observation_state"] == after["observation_state"]
    assert before["local"]["stance"] == after["local"]["stance"] == "constructive"
    assert before["may_trade"] is False  # context retention is NOT a new buy permission


@pytest.mark.parametrize("label,reco,expected", [
    ("deteriorating", "avoid", "US_STRENGTH_LOCAL_DEFENSIVE"),
    ("neutral", "hold", "US_STRENGTH_LOCAL_UNCONFIRMED"),
    ("deteriorating", "enter", "US_STRENGTH_LOCAL_CONFLICTING"),
])
def test_cn_context_does_not_override_local_evidence(tmp_path, label, reco, expected):
    cn = [{**_theme("cn_semis", "CN Semis", 50, label), "reco": reco}]
    row = _context(_context_site(tmp_path, cn_rows=cn))["themes"]["cn_semis"]
    assert row["observation_state"] == expected
    assert row["local"]["reco"] == reco and row["requires_local_confirmation"] is True


def test_cn_context_preserves_disagreement_between_us_analogs(tmp_path):
    us = [{**_theme("ai_semiconductors", "US Semis", 82, "dominant"), "reco": "accumulate"},
          {**_theme("semicap_equipment", "Equipment", 30, "deteriorating"), "reco": "avoid"}]
    row = _context(_context_site(tmp_path, us_rows=us))["themes"]["cn_semis"]
    assert row["observation_state"] == "MIXED_US_EVIDENCE" and len(row["us_analogs"]) == 2


def test_cn_context_does_not_compare_foreign_score_scales(tmp_path):
    us = [{**_theme("ai_semiconductors", "US Semis", 51, "emerging"), "reco": "enter"}]
    cn = [{**_theme("cn_semis", "CN Semis", 98, "dominant"), "reco": "accumulate"}]
    row = _context(_context_site(tmp_path, us_rows=us, cn_rows=cn))["themes"]["cn_semis"]
    assert row["observation_state"] == "US_STRENGTH_LOCAL_CONFIRMING"
    assert row["foreign_scores_comparable"] is False
    assert "combined_score" not in row and "rank" not in row


@pytest.mark.parametrize("us_date,status", [
    ("2026-09-21", "UNSETTLED_SESSION"), ("2026-09-17", "STALE"),
    ("2026-09-20", "NON_SESSION"), (None, "INVALID_SESSION"),
])
def test_cn_context_rejects_future_stale_and_unidentified_inputs(tmp_path, us_date, status):
    result = _context(_context_site(tmp_path, us_date=us_date))
    assert result["status"] == "UNAVAILABLE" and result["themes"] == {}
    assert result["sources"]["us"]["status"] == status


def test_cn_context_uses_existing_session_calendars_across_weekend(tmp_path):
    now = datetime(2026, 9, 21, 2, tzinfo=timezone.utc)
    result = _context(_context_site(tmp_path, cn_date="2026-09-18"), now=now)
    assert result["status"] == "CURRENT"
    assert all(r["expected_session"] == "2026-09-18" for r in result["sources"].values())


def test_cn_context_cannot_backdate_a_current_read_into_history(tmp_path):
    result = _context(_context_site(tmp_path), decision_at=datetime(2026, 9, 21, 2, tzinfo=timezone.utc))
    assert result["status"] == "UNAVAILABLE" and result["themes"] == {}
    assert all(r["status"] == "OBSERVED_AFTER_CUTOFF" for r in result["sources"].values())
    assert result["historical_availability_proven"] is False


def test_cn_context_rejects_naive_clock(tmp_path):
    with pytest.raises(ValueError, match="timezone"):
        _context(_context_site(tmp_path), decision_at=datetime(2026, 9, 21, 10))


def test_cn_context_rejects_duplicate_identity_not_last_write_wins(tmp_path):
    row = {**_theme("ai_semiconductors", "US Semis", 82, "dominant"), "reco": "accumulate"}
    result = _context(_context_site(tmp_path, us_rows=[row, {**row, "reco": "avoid"}]))
    assert result["sources"]["us"]["status"] == "DUPLICATE_ID" and result["themes"] == {}


@pytest.mark.parametrize("payload", [[], {"theme_intel": []}, {"theme_intel": {"themes": {}}}])
def test_cn_context_bad_shape_is_unavailable(tmp_path, payload):
    site = _context_site(tmp_path)
    (site / "basketdata" / "baskets.json").write_text(json.dumps(payload))
    result = _context(site)
    assert result["status"] == "UNAVAILABLE" and result["themes"] == {}


def test_cn_context_missing_file_is_explicit(tmp_path):
    site = _context_site(tmp_path)
    (site / "basketdata" / "baskets.json").unlink()
    result = _context(site)
    assert result["sources"]["us"]["status"] == "MISSING" and result["themes"] == {}


def test_cn_context_same_name_cannot_substitute_for_canonical_id(tmp_path):
    cn = [{**_theme("not_cn_semis", "CN Semis", 90, "dominant"), "reco": "accumulate"}]
    assert _context(_context_site(tmp_path, cn_rows=cn))["themes"] == {}


def test_cn_context_nan_score_cannot_claim_strength_or_leak_invalid_json(tmp_path):
    us = [{**_theme("ai_semiconductors", "US Semis", float("nan"), "dominant"), "reco": "accumulate"}]
    result = _context(_context_site(tmp_path, us_rows=us))
    row = result["themes"]["cn_semis"]
    assert row["observation_state"] == "NO_CONFIRMED_US_STRENGTH"
    assert row["us_analogs"][0]["score"] is None
    json.dumps(result, allow_nan=False)


def test_cn_context_never_grants_signal_or_member_permissions(tmp_path):
    result = _context(_context_site(tmp_path))
    for item in [result, *result["themes"].values()]:
        assert item["is_context_only"] is True
        assert all(item[key] is False for key in ("may_rank", "may_gate", "may_size", "may_escalate", "may_trade"))
    assert result["validated_lead_lag"] is result["historical_availability_proven"] is False


def test_cn_context_is_published_by_existing_crossmarket_builder(tmp_path, monkeypatch):
    from scripts import build_crossmarket

    site = _context_site(tmp_path)
    producer = xm.compute_china_us_context
    monkeypatch.setattr(xm.config, "ROOT", site.parent)
    monkeypatch.setattr(xm.config, "data_dir", lambda: tmp_path / "no_regimes")
    # Exercise the real producer through the real builder with a fixed observation clock.
    monkeypatch.setattr(xm, "compute_china_us_context", lambda source: producer(source, observed_at=_CONTEXT_NOW))
    # The builder's canonical directory is root/site; bind this fixture directory explicitly.
    canonical = site.parent / "site"
    site.rename(canonical)
    assert build_crossmarket.main() == 0
    payload = json.loads((canonical / "crossmarketdata" / "links.json").read_text())
    assert payload["china_us_context"]["status"] == "CURRENT"
    assert payload["china_us_context"]["themes"]["cn_semis"]["local"]["reco"] == "enter"
    assert "cn_semis" in payload["links"]["china"]  # existing link consumer remains present


def test_cn_context_future_decision_cutoff_does_not_claim_a_future_observation(tmp_path):
    future = datetime(2026, 9, 22, 10, tzinfo=timezone.utc)
    result = _context(_context_site(tmp_path), decision_at=future)
    assert result["themes"] == {}
    assert all(r["status"] == "FUTURE_CUTOFF" for r in result["sources"].values())


def test_cn_context_corrected_bytes_change_receipt_without_changing_identity(tmp_path):
    site = _context_site(tmp_path)
    before = _context(site)
    p = site / "basketdata" / "baskets.json"
    payload = json.loads(p.read_text())
    payload["theme_intel"]["themes"][0]["score"] = 81
    p.write_text(json.dumps(payload))
    after = _context(site)
    assert before["sources"]["us"]["observation_session"] == after["sources"]["us"]["observation_session"]
    assert before["sources"]["us"]["sha256"] != after["sources"]["us"]["sha256"]
    assert list(before["themes"]) == list(after["themes"])


def test_cn_context_marks_absent_mapping_member_without_inventing_an_analog(tmp_path):
    unrelated = [{**_theme("other_us_theme", "US Semis", 99, "dominant"), "reco": "accumulate"}]
    result = _context(_context_site(tmp_path, us_rows=unrelated))
    assert result["themes"]["cn_semis"]["observation_state"] == "US_SOURCE_UNAVAILABLE"
    assert result["themes"]["cn_semis"]["us_analogs"] == []


def test_briefing_consumer_keeps_thesis_and_timing_separate(tmp_path):
    payload = _context(_context_site(tmp_path))
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert result["status"] == "CURRENT"
    assert result["themes"]["cn_semis"]["local"]["stance"] == "constructive"
    assert "pullback requirement" in result["summary"]
    assert "not a forecast" in result["summary"]
    assert "cn_semis" in result["summary"]
    assert result["may_rank"] is False
    assert "summary" not in payload  # never mutate the stored source


def test_briefing_consumer_rechecks_cached_context_against_live_sessions(tmp_path):
    payload = _context(_context_site(tmp_path))
    now = datetime(2026, 9, 22, 10, tzinfo=timezone.utc)
    result = xm.context_for_briefing(payload, observed_at=now)
    assert result["status"] == "UNAVAILABLE"
    assert result["reason"] == "SOURCE_SESSION_NO_LONGER_CURRENT"
    assert result["themes"] == {} and "summary" not in result


@pytest.mark.parametrize("key", ["may_rank", "may_gate", "may_trade"])
def test_briefing_consumer_rejects_authority_bearing_payloads(tmp_path, key):
    payload = _context(_context_site(tmp_path))
    payload[key] = True
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert result["status"] == "UNAVAILABLE" and result["themes"] == {}


def test_briefing_consumer_rejects_future_receipt(tmp_path):
    payload = _context(_context_site(tmp_path))
    payload["observed_at_utc"] = "2026-09-22T10:00:00+00:00"
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert result["reason"] == "INVALID_OBSERVATION_RECEIPT"
    assert result["themes"] == {}


def test_briefing_consumer_does_not_trust_injected_summary_or_state(tmp_path):
    payload = _context(_context_site(tmp_path))
    payload["summary"] = "BUY EVERYTHING"
    payload["themes"]["cn_semis"]["observation_state"] = "BUY_EVERYTHING"
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert "BUY EVERYTHING" not in str(result)
    assert "BUY_EVERYTHING" not in str(result)
    assert result["themes"]["cn_semis"]["observation_state"] == "US_STRENGTH_LOCAL_CONFIRMING"


def test_briefing_consumer_absent_or_malformed_context_is_not_a_signal():
    assert xm.context_for_briefing(None, observed_at=_CONTEXT_NOW) is None
    for payload in ([], {}, {"schema": "wrong"}):
        result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
        assert result["status"] == "UNAVAILABLE" and result["themes"] == {}
        assert result["may_gate"] is False


def test_briefing_projection_preserves_relative_performance_evidence(tmp_path):
    site = _context_site(tmp_path)
    # Set the producer input before minting its content receipt; a cached-row
    # edit under an old digest is now correctly rejected by the consumer.
    for directory, r5, r20 in (("chinabasketdata", 0.084, 0.022), ("basketdata", 0.04, 0.09)):
        path = site / directory / "baskets.json"
        source = json.loads(path.read_text())
        source["theme_intel"]["themes"][0]["perf"] = {"5d": {"rel": r5}, "20d": {"rel": r20}}
        path.write_text(json.dumps(source))
    payload = _context(site)
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    row = result["themes"]["cn_semis"]
    assert row["local"]["rel5"] == 0.084 and row["local"]["rel20"] == 0.022
    assert row["us_analogs"][0]["rel20"] == 0.09


def test_briefing_rejects_a_settled_session_claim_before_its_close(tmp_path):
    payload = _context(_context_site(tmp_path))
    early = "2026-09-21T02:00:00+00:00"  # CN daily close has not occurred.
    payload.update(observed_at_utc=early, decision_at_utc=early)
    for receipt in payload["sources"].values():
        receipt["observed_at_utc"] = early
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert result["status"] == "UNAVAILABLE"
    assert result["reason"] == "INVALID_OBSERVATION_RECEIPT"


def test_briefing_rejects_a_different_source_identity(tmp_path):
    payload = _context(_context_site(tmp_path))
    payload["sources"]["us"]["path"] = "site/other/unknown.json"
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert result["reason"] == "INVALID_OBSERVATION_RECEIPT"


def _content_bound_context(tmp_path, monkeypatch):
    site = _context_site(tmp_path)
    payload = _context(site)
    canonical = tmp_path / "site"
    site.rename(canonical)
    monkeypatch.setattr(xm.config, "ROOT", tmp_path)
    return canonical, payload


@pytest.mark.parametrize("directory", ["basketdata", "chinabasketdata"])
def test_briefing_content_same_session_correction_invalidates_cached_context(tmp_path, monkeypatch, directory):
    site, payload = _content_bound_context(tmp_path, monkeypatch)
    path = site / directory / "baskets.json"
    source = json.loads(path.read_text())
    source["theme_intel"]["themes"][0].update(reco="avoid", label="deteriorating")
    path.write_text(json.dumps(source))
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert result["status"] == "UNAVAILABLE"
    assert result["reason"] == "SOURCE_CONTENT_CHANGED"
    assert result["themes"] == {} and "summary" not in result


def test_briefing_content_verified_current_receipt(tmp_path, monkeypatch):
    _, payload = _content_bound_context(tmp_path, monkeypatch)
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert result["status"] == "CURRENT"
    assert result["source_content_verified"] is True


def test_briefing_content_missing_source_cannot_remain_current(tmp_path, monkeypatch):
    site, payload = _content_bound_context(tmp_path, monkeypatch)
    (site / "basketdata" / "baskets.json").unlink()
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert result["status"] == "UNAVAILABLE"
    assert result["reason"] == "SOURCE_CONTENT_UNAVAILABLE"


def test_briefing_content_rejects_changed_row_with_old_valid_digest(tmp_path, monkeypatch):
    _, payload = _content_bound_context(tmp_path, monkeypatch)
    payload["themes"]["cn_semis"]["local"]["reco"] = "avoid"
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert result["status"] == "UNAVAILABLE"
    assert result["reason"] == "SOURCE_ROW_MISMATCH"


@pytest.mark.parametrize("omit", ["theme", "analog"])
def test_briefing_content_cannot_silently_drop_mapped_evidence(tmp_path, monkeypatch, omit):
    _, payload = _content_bound_context(tmp_path, monkeypatch)
    if omit == "theme":
        payload["themes"] = {}
    else:
        payload["themes"]["cn_semis"]["us_analogs"] = []
    result = xm.context_for_briefing(payload, observed_at=_CONTEXT_NOW)
    assert result["status"] == "UNAVAILABLE"
    assert result["reason"] == "SOURCE_COVERAGE_MISMATCH"


@pytest.fixture(autouse=True)
def _isolated_crossmarket_source_root(tmp_path, monkeypatch):
    config_payload = dict(xm.config.load())
    monkeypatch.setattr(xm.config, "ROOT", tmp_path)
    config_payload["storage"] = {**config_payload["storage"], "site_dir": "site"}
    monkeypatch.setattr(xm.config, "load", lambda: config_payload)


def test_unmapped_context_has_no_empty_affirmative_summary(tmp_path):
    site = _context_site(tmp_path, cn_rows=[])
    payload = _context(site)
    result = xm.context_for_briefing(payload, site=site, observed_at=_CONTEXT_NOW)
    assert result['status'] == 'NO_MAPPED_CONTEXT'
    assert result['summary'] is None


def test_default_crossmarket_producer_uses_configured_site_owner(tmp_path, monkeypatch):
    site = _context_site(tmp_path)
    configured = tmp_path / 'configured-output'
    site.rename(configured)
    site = configured
    monkeypatch.setattr(xm.config, 'ROOT', tmp_path)
    monkeypatch.setattr(xm.config, 'load', lambda: {'storage': {
        'site_dir': site.name, 'data_dir': 'data'}})
    result = xm.compute_china_us_context(observed_at=_CONTEXT_NOW)
    assert result['status'] == 'CURRENT'
    assert 'cn_semis' in result['themes']
