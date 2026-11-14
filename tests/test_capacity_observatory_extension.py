"""Capacity Fabric observatory — overflow/peak/Claude-lane extension contract.

The incumbent observatory (schema v1) carried routes, requests and usage only.
This extension adds three optional, content-free sections so the admin page can
show family overflow ladders, the Z.ai peak gate, and Claude family-lane budgets:

* ``peak``     — the router's own peak-window scalars (never recomputed here).
* ``overflow`` — family diversion state + configured ladder targets + seat keys.
* ``claude``   — gateway account/family lane budgets, provider-vs-estimated resets.

Backward compatibility is the first law: an old payload without the new sections
must still decode, with the sections null. Hostile or oversized input is dropped
or bounded, never echoed. Local estimates are labelled as estimates in semantics.
"""
from __future__ import annotations

import hashlib
import time

import pytest

from admin.capacity_fabric_schema import (
    MAX_ACCOUNTS, MAX_FAMILIES, MAX_KEYS, SCHEMA, clean_snapshot,
)
from admin import capacity_router


def _epoch():
    return hashlib.sha256(b"observatory-extension").hexdigest()[:24]


def _base(now):
    return {"schema": SCHEMA, "epoch": _epoch(), "started_at": now - 100,
            "generated_at": now, "sequence": 1, "routes": [], "active": [],
            "recent": [], "series": [], "aliases": {}, "totals": {}}


def _overflow(now):
    return {"enabled": True, "version": "fabric-overflow-v1-20261110",
            "diverted_requests": 2211, "diversion_share": 0.2819,
            "diverted_sessions": 139, "diverted_inflight": 0,
            "families": {"deepseek": {"overflowing": True, "signal": "cooldown",
                "overflowing_for_s": 1024.0, "healthy_in_s": 39.4,
                "proactive_window_open": False, "targets": ["glm-5.3-flash"]}},
            "keys": {"morph-ultra-seat-1-deepseek": {"input_tpm_limit": 400000,
                "target": 320000.0, "used_or_reserved": 374301.5,
                "used_pct_of_limit": 93.6, "over_target": True, "cooling_s": 0}},
            "recent": [{"event": "diverted", "kind": "sticky", "family": "deepseek",
                "requested_model": "deepseek-v4.1-flash", "served_model": "glm-5.3-flash",
                "route": "opencode_go_1", "t": now - 10}]}


def _claude(now):
    return {"reachable": True, "observed_at": now - 5, "stranded_family": "fable",
            "preferences": ["max-4:opus"],
            "accounts": [{"id": "9092b3", "label": "max-1", "used_5h": 92.3,
                "budget_5h": 1000, "remaining_5h": 907.7, "inflight": 1,
                "last_status": "ok", "drain": False, "cooldown_until": None,
                "families": {"fable": {"used_weekly": 277.4, "budget_weekly": 4000,
                    "remaining_weekly": 3722.6, "pressure": 0.0924,
                    "cooldown_until": None, "weekly_resets_at": now + 285000,
                    "weekly_reset_source": "provider", "expiring_soon": False}}}]}


def test_old_payload_still_decodes_with_null_sections():
    now = time.time()
    out = clean_snapshot(_base(now))
    assert out["peak"] is None
    assert out["overflow"] is None
    assert out["claude"] is None


def test_new_sections_round_trip_real_shapes():
    now = time.time()
    base = _base(now)
    base.update(peak={"active": True, "tz": "Asia/Shanghai", "start": "14:00",
                      "end": "18:00", "wait_s": 60, "next_send_in_s": 0},
                overflow=_overflow(now), claude=_claude(now))
    out = clean_snapshot(base)
    assert out["peak"]["active"] is True
    assert out["peak"]["tz"] == "Asia/Shanghai"
    fam = out["overflow"]["families"]["deepseek"]
    assert fam["overflowing"] is True and fam["targets"] == ["glm-5.3-flash"]
    key = out["overflow"]["keys"]["morph-ultra-seat-1-deepseek"]
    assert key["over_target"] is True and key["used_pct_of_limit"] == 93.6
    lane = out["claude"]["accounts"][0]["families"]["fable"]
    assert lane["budget_weekly"] == 4000 and lane["weekly_reset_source"] == "provider"
    assert out["claude"]["stranded_family"] == "fable"


def test_secret_like_labels_are_refused():
    now = time.time()
    base = _base(now)
    base["overflow"] = _overflow(now)
    base["overflow"]["families"]["evil"] = {"overflowing": "yes",
                                            "signal": "sk-abcdefghijklmnopqrstuvwx"}
    base["peak"] = {"active": True, "tz": "'; DROP TABLE--"}
    out = clean_snapshot(base)
    assert out["overflow"]["families"]["evil"]["overflowing"] is False
    assert "sk-" not in str(out["overflow"]["families"]["evil"]["signal"])
    assert out["peak"]["tz"] == ""


def test_unknown_reset_source_is_dropped_not_guessed():
    now = time.time()
    base = _base(now)
    base["claude"] = _claude(now)
    base["claude"]["accounts"][0]["families"]["fable"]["weekly_reset_source"] = "guessed"
    out = clean_snapshot(base)
    assert out["claude"]["accounts"][0]["families"]["fable"]["weekly_reset_source"] is None


def test_bounds_truncate_rather_than_reject():
    now = time.time()
    base = _base(now)
    base["overflow"] = _overflow(now)
    base["overflow"]["families"] = {f"f{i}": {"overflowing": False} for i in range(MAX_FAMILIES + 30)}
    base["overflow"]["keys"] = {f"k{i}": {} for i in range(MAX_KEYS + 30)}
    base["claude"] = _claude(now)
    base["claude"]["accounts"] = [{"id": f"a{i}", "label": f"a{i}", "families": {}}
                                  for i in range(MAX_ACCOUNTS + 30)]
    out = clean_snapshot(base)
    assert len(out["overflow"]["families"]) <= MAX_FAMILIES
    assert len(out["overflow"]["keys"]) <= MAX_KEYS
    assert len(out["claude"]["accounts"]) <= MAX_ACCOUNTS


def test_diversion_share_bounded_to_unit_interval():
    now = time.time()
    base = _base(now)
    base["overflow"] = _overflow(now)
    base["overflow"]["diversion_share"] = 7.5
    out = clean_snapshot(base)
    assert out["overflow"]["diversion_share"] is None


def test_semantics_label_estimates_and_gateway_resets():
    now = time.time()
    out = clean_snapshot(_base(now))
    assert "local router estimates" in out["semantics"]["overflow"]
    assert "provider-reported or estimated" in out["semantics"]["claude"]


def test_panel_summary_counts_overflow_and_benched_lanes(tmp_path):
    now = time.time()
    base = _base(now)
    base.update(peak={"active": True}, overflow=_overflow(now), claude=_claude(now))
    # bench one lane so the count is observable
    base["claude"]["accounts"][0]["families"]["fable"]["cooldown_until"] = now + 3600
    snapshot = clean_snapshot(base)
    path = tmp_path / "capacity-router.json"
    path.write_text(__import__("json").dumps(snapshot))
    data = capacity_router.panel(15, path=path, now=now)
    assert data["ok"] is True
    assert data["summary"]["overflowing_families"] == 1
    assert data["summary"]["over_target_keys"] == 1
    assert data["summary"]["benched_lanes"] == 1
    assert data["summary"]["peak_active"] is True


def test_panel_without_extension_reports_zero_counts(tmp_path):
    now = time.time()
    snapshot = clean_snapshot(_base(now))
    path = tmp_path / "capacity-router.json"
    path.write_text(__import__("json").dumps(snapshot))
    data = capacity_router.panel(15, path=path, now=now)
    assert data["ok"] is True
    assert data["summary"]["overflowing_families"] == 0
    assert data["summary"]["benched_lanes"] == 0
    assert data["summary"]["peak_active"] is False