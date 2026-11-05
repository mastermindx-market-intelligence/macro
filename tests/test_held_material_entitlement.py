"""Held-producer requirement through the existing send-time entitlement seam; no IO."""
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from engine import alert_delivery_drain as drain

NOW = datetime(2026, 10, 19, tzinfo=timezone.utc)
# Captured from the actual planHeldMaterialEvents export using a synthetic owner
# and the existing public AAPL fixture; no real positions or account state.
PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "held_material_outbox_payload.json").read_text())
REQUIRED = PAYLOAD["requires_tier"]


def read(tier, status="active", **extra):
    return drain.TypedRead(drain.READ_OK, [dict(tier=tier, status=status, current_period_end="2099-01-01T00:00:00Z", **extra)])


@pytest.mark.parametrize("tier", ["essential", "insider", "pro", " Essential "])
def test_native_paid_held_requirement_admits_current_and_permanent_legacy_paid(tier):
    assert drain.entitlement_decision(read(tier), NOW, REQUIRED) == "send"


@pytest.mark.parametrize("tier", ["free", "unknown", "plus", ""])
def test_free_unknown_and_non_native_plus_do_not_acquire_paid_access(tier):
    assert drain.entitlement_decision(read(tier), NOW, REQUIRED) == "suppress"


@pytest.mark.parametrize("status", ["canceled", "past_due", "unpaid", "incomplete_expired", "unrecognised"])
def test_lapsed_or_unknown_status_never_sends(status):
    assert drain.entitlement_decision(read("essential", status), NOW, REQUIRED) == "suppress"


def test_entitlement_outage_stays_unevaluable_and_absence_stays_unentitled():
    assert drain.entitlement_decision(drain.TypedRead(drain.READ_UNAVAILABLE, None), NOW, REQUIRED) == "unavailable"
    assert drain.entitlement_decision(drain.TypedRead(drain.READ_OK_ZERO, []), NOW, REQUIRED) == "suppress"


def test_comp_preserves_native_paid_tier_and_unknown_required_tier_fails_closed():
    comp = drain.TypedRead(drain.READ_OK, [{"tier": "insider", "source": "comp", "status": "none", "current_period_end": None}])
    assert drain.entitlement_decision(comp, NOW, REQUIRED) == "send"
    assert drain.entitlement_decision(comp, NOW, "unknown") == "suppress"


def test_catalog_rank_outage_is_unevaluable_not_permission_or_free_fallback(monkeypatch):
    monkeypatch.setattr(drain, "tier_rank", lambda: None)
    assert drain.entitlement_decision(read("essential"), NOW, REQUIRED) == "unavailable"


def test_rank_comes_from_native_catalog_and_unknown_rank_is_not_guessed(monkeypatch, tmp_path):
    from lib import tiers
    (tmp_path / "config").mkdir()
    catalog = tmp_path / "config" / "plans.yml"
    catalog.write_text("tier_rank: [free, essential, pro]\n")
    monkeypatch.setattr(tiers, "ROOT", tmp_path)
    assert tiers.tier_rank() == ("free", "essential", "pro")
    catalog.write_text("tier_rank: [free, essential, essential]\n")
    assert tiers.tier_rank() is None
    catalog.unlink()
    assert tiers.tier_rank() is None


def test_actual_node_producer_contract_is_the_native_minimum_paid_requirement():
    assert PAYLOAD["source"] == "terminal.held_material_event.v1"
    assert PAYLOAD["category"] == "holdings_material_change"
    assert PAYLOAD["authority"] == "notification_only"
    assert REQUIRED == "essential"
