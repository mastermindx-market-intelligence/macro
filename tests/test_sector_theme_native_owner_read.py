"""Adversarial native-owner P2d seam tests; no source collector or network."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from tests.test_sector_theme_owner_bridge import fixture
from engine.sector_theme_native_owner_read import preview_native_us_theme


def packet():
    p = fixture()
    p["market"]["origin"] = "owner_reported"
    p["original_membership_receipt"] = {"receipt": "test-only-unqualified"}
    p["source_use_request"] = {
        "source_ref": "data/baskets/membership.json",
        "source_sha256": "a" * 64,
        "generation_id": "test-source-generation",
        "purpose": "sector_theme_factor_research",
        "phase": "read_use",
        "market": "us_today",
    }
    return p


def allowed(req):
    return {
        **dict(req), "verdict": "ALLOWED", "registry_revision": "rights_test_revision",
    }


def native_read(members=None, *, count=None):
    def read(basket_id, day, *, suite):
        assert basket_id == "AI_INDUSTRIAL_INFRA"
        assert day == "2026-10-29"
        assert suite == "baskets"
        if count is not None:
            count.append(1)
        return deepcopy(members) if members is not None else deepcopy(fixture()["membership_asof"])
    return read


def test_p2d_01_native_owner_binding_is_still_nonpublishing_research():
    p = packet()
    original = deepcopy(p)
    result = preview_native_us_theme(p, member_read=native_read(), use_read=allowed)
    assert p == original
    assert result["status"] == "RESEARCH_PREVIEW_ONLY"
    assert result["basis"] == "PIT_AS_KNOWN"
    assert result["eligible_for_customer_publication"] is False
    assert result["eligible_for_historical_prediction"] is False
    assert result["trading_or_alert_authority"] is False


def test_p2d_02_rights_denial_never_reads_the_membership_source():
    calls = []
    r = preview_native_us_theme(
        packet(), member_read=native_read(count=calls),
        use_read=lambda req: {**allowed(req), "verdict": "REFUSED"},
    )
    assert r["status"] == "HELD"
    assert "source_use_owner_denied" in r["hold_reasons"]
    assert not calls


def test_p2d_03_rejects_caller_forged_use_verdict_not_native_owner_receipt():
    p = packet()
    p["use_verdict"] = {**allowed(p["source_use_request"]), "registry_revision": "FAKE"}
    r = preview_native_us_theme(p, member_read=native_read(), use_read=allowed)
    assert "caller_rights_verdict_disagrees_with_owner" in r["hold_reasons"]


def test_p2d_04_native_membership_drift_is_not_a_new_original_vintage():
    p = packet()
    native = deepcopy(p["membership_asof"])
    native["members"] = ["AAA", "CCC"]
    r = preview_native_us_theme(p, member_read=native_read(native), use_read=allowed)
    assert "native_membership_owner_disagreement" in r["hold_reasons"]


def test_p2d_05_native_pit_fallback_cannot_masquerade_as_historical_membership():
    p = packet()
    native = deepcopy(p["membership_asof"])
    native.update(pit=False, basis="current_membership", snapshot_date=None)
    r = preview_native_us_theme(p, member_read=native_read(native), use_read=allowed)
    assert "native_membership_not_pit" in r["hold_reasons"]


def test_p2d_06_reject_vendor_source_and_wrong_use_purpose_without_owner_calls():
    for field, bad in (
        ("source_ref", "finviz_themes/vendor"),
        ("purpose", "selection_cohort_internal_capture"),
        ("phase", "capture_write"),
        ("source_sha256", "not-a-sha"),
        ("market", "cn_featured"),
    ):
        p = packet()
        p["source_use_request"][field] = bad
        calls = []
        r = preview_native_us_theme(
            p, member_read=native_read(count=calls),
            use_read=lambda req: (_ for _ in ()).throw(AssertionError("must not call rights")),
        )
        assert r["status"] == "HELD"
        assert "unsupported_source_use_request" in r["hold_reasons"]
        assert not calls


def test_p2d_07_reject_invalid_local_session_date_without_reading_rights():
    p = packet()
    p["membership_asof"]["asof"] = "2026-10-30"  # 29th at 16:00 New York
    r = preview_native_us_theme(
        p,
        member_read=lambda *a, **kw: (_ for _ in ()).throw(AssertionError("read")),
        use_read=lambda req: (_ for _ in ()).throw(AssertionError("rights")),
    )
    assert "native_membership_day_after_local_market_close" in r["hold_reasons"]


def test_p2d_08_missing_original_membership_receipt_still_held():
    p = packet()
    del p["original_membership_receipt"]
    r = preview_native_us_theme(p, member_read=native_read(), use_read=allowed)
    assert r["status"] == "HELD"
    assert "original_membership_receipt_not_authenticated_here" in r["hold_reasons"]


def test_p2d_09_missing_owner_rights_kernel_does_not_fail_open():
    r = preview_native_us_theme(
        packet(), member_read=native_read(),
        use_read=lambda req: (_ for _ in ()).throw(RuntimeError("unavailable")),
    )
    assert "source_use_owner_unavailable" in r["hold_reasons"]


def test_p2d_10_native_membership_reader_exception_held_without_retry():
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("owner unavailable")
    r = preview_native_us_theme(packet(), member_read=fail, use_read=allowed)
    assert "native_membership_owner_unavailable" in r["hold_reasons"]
    assert len(calls) == 1


def test_p2d_11_native_reader_malformed_membership_cannot_crash():
    base = fixture()["membership_asof"]
    for invalid in (None, [], {}, {"members": [dict()]}, {**base, "members": ["AAA", {}]},
                    {**base, "members": ["AAA", "AAA"]}):
        r = preview_native_us_theme(
            packet(), member_read=lambda *args, **kw: deepcopy(invalid),
            use_read=allowed,
        )
        assert r["status"] == "HELD"
        assert r["eligible_for_customer_publication"] is False


def test_p2d_12_synthetic_fixture_never_reads_real_owners():
    p = fixture()
    p["source_use_request"] = packet()["source_use_request"]
    r = preview_native_us_theme(
        p,
        member_read=lambda *a, **kw: (_ for _ in ()).throw(AssertionError("member")),
        use_read=lambda req: (_ for _ in ()).throw(AssertionError("rights")),
    )
    assert "requires_owner_reported_pit_packet" in r["hold_reasons"]


def test_p2d_13_real_owner_verdict_requires_exact_request_echo():
    p = packet()
    def wrong(req):
        return {**allowed(req), "source_ref": "data/other/unknown.json"}
    r = preview_native_us_theme(p, member_read=native_read(), use_read=wrong)
    assert "source_use_owner_denied" in r["hold_reasons"]


def test_p2d_14_requires_exact_native_snapshot_identity():
    p = packet()
    for k, v in (("snapshot_date", "2026-10-29"), ("source_shape", "ths_concept_dump"),
                 ("basket_id", "forged"), ("asof", "2026-10-28")):
        bad = deepcopy(p["membership_asof"])
        bad[k] = v
        r = preview_native_us_theme(p, member_read=native_read(bad), use_read=allowed)
        assert "native_membership_owner_disagreement" in r["hold_reasons"] or (
            "native_membership_not_pit" in r["hold_reasons"]
        )


def test_p2d_15_rights_request_is_purpose_bound_to_house_source():
    calls = []
    def stub(req):
        calls.append(deepcopy(req))
        return allowed(req)
    r = preview_native_us_theme(packet(), member_read=native_read(), use_read=stub)
    assert r["status"] == "RESEARCH_PREVIEW_ONLY"
    assert len(calls) == 1
    assert calls[0]["purpose"] == "sector_theme_factor_research"
    assert calls[0]["source_ref"] == "data/baskets/membership.json"
    assert calls[0]["phase"] == "read_use"


def test_p2d_16_exact_owner_read_does_not_endow_source_receipt_authenticity():
    p = packet()
    p["membership_known_at"] = (datetime(2026,10,30,21,tzinfo=timezone.utc)).isoformat()
    r = preview_native_us_theme(p, member_read=native_read(), use_read=allowed)
    assert "future_market_or_membership_known_at" in r["hold_reasons"]
