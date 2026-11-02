"""EW-P4-ACT: the read-only ledger reader, the latest-observation projection and the
builder republish. Offline: no DB, network, real data path, user lookup or send."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from engine import rotation_events as owner
from lib.us_cash_calendar import last_session_on_or_before
from scripts import build_rotation_events as builder


def clock(day, hour=22, minute=0):
    return datetime.fromisoformat(day).replace(hour=hour, minute=minute, tzinfo=timezone.utc)


def packet(day, n, d, **extra):
    end = date.fromisoformat(day)
    start = last_session_on_or_before(last_session_on_or_before(end - timedelta(days=1)) - timedelta(days=1))
    row = {"schema": "ratio_lens.short_horizon.v1", "pair_id": "xlp_vs_smh", "num": "XLP", "den": "SMH",
           "context_group": "defensive_sector", "requested_as_of": day, "value_as_of": day,
           "eligible_2s": True, "basis": "dividend_adjusted_close", "horizons": {"2s": {
               "eligible": True, "sessions": 2, "start": start.isoformat(), "end": day,
               "numerator_return_pct": n, "denominator_return_pct": d,
               "ratio_return_pct": ((1 + n / 100) / (1 + d / 100) - 1) * 100}}}
    return {"schema": "rotation_early_context/v1", "definition_id": "rotation_early_context/1",
            "display_only": True, "as_of": day, "pairs": [row], **extra}


def run_chain(tmp_path, monkeypatch, steps):
    """Record each (day, context) through the real recorder into tmp_path."""
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    root = tmp_path / "rotation_events"
    root.mkdir(exist_ok=True)
    state = root / "state.json"
    if not state.exists():
        state.write_text(json.dumps({"active": {}, "lockout": {}}))
    for day, ctx in steps:
        out = owner.record_early_observation_history({"early_context": ctx}, tmp_path, observed_at=clock(day))
        assert out["status"] == "recorded"
    return owner.read_early_observation_ledger(tmp_path)


def ledger_lines(tmp_path):
    return (tmp_path / "rotation_events" / "events.jsonl").read_text(encoding="utf-8").splitlines()


def test_missing_ledger_is_empty_history_and_no_view(tmp_path):
    assert owner.read_early_observation_ledger(tmp_path) == []
    assert owner.project_latest_observation_view(packet("2026-10-22", 2.0, -1.0), []) is None


def test_baseline_alone_never_projects_a_notice(tmp_path, monkeypatch):
    rows = run_chain(tmp_path, monkeypatch, [("2026-10-21", packet("2026-10-21", -1.0, 1.0))])
    assert len(rows) == 1 and "notification" not in rows[0]
    assert owner.project_latest_observation_view(packet("2026-10-21", -1.0, 1.0), rows) is None


def test_current_notice_projects_exact_notification_and_cross_checked_window(tmp_path, monkeypatch):
    ctx = packet("2026-10-22", 2.0, -1.0,
                 availability={"status": "VERIFIED", "available_at": "2026-10-22T21:00:00+00:00"},
                 coverage={"registered_pairs": 4, "evaluable_2s": 3, "missing_pair_ids": ["a", 7]},
                 lineage={"roots": ["sector_legs", None]})
    rows = run_chain(tmp_path, monkeypatch, [("2026-10-21", packet("2026-10-21", -1.0, 1.0)),
                                             ("2026-10-22", ctx)])
    before = copy.deepcopy((ctx, rows))
    view = owner.project_latest_observation_view(ctx, rows)
    assert (ctx, rows) == before
    tip = rows[-1]
    assert view["schema"] == "rotation_observation_view/v1"
    assert view["notification"] == tip["notification"]
    assert view["notification"] is not tip["notification"]
    assert view["notification"]["kind"] == "observed_change"
    assert view["window_2s"] == {"start": ctx["pairs"][0]["horizons"]["2s"]["start"], "end": "2026-10-22"}
    assert view["horizon_20s"] is None
    assert view["availability"] == {"status": "VERIFIED", "available_at": "2026-10-22T21:00:00+00:00"}
    assert view["coverage"] == {"registered_pairs": 4, "evaluable_2s": 3, "missing_pair_ids": ["a"]}
    assert view["lineage_roots"] == ["sector_legs"]
    assert view["basis"] == "dividend_adjusted_close"
    assert view["previous"] == {"observation_id": rows[0]["observation_id"],
                                "observed_at": rows[0]["observed_at"], "values": rows[0]["values"]}
    stored = ledger_lines(tmp_path)[-1]
    assert view["recorded"] == {"source": "macro.rotation_events.ledger",
                                "ledger": "rotation_events/events.jsonl",
                                "receipt_sha256": hashlib.sha256(stored.encode("utf-8")).hexdigest()}


def test_reversal_is_projected_with_its_own_kind(tmp_path, monkeypatch):
    rows = run_chain(tmp_path, monkeypatch, [("2026-10-21", packet("2026-10-21", 2.0, -1.0)),
                                             ("2026-10-22", packet("2026-10-22", -1.0, 1.0))])
    view = owner.project_latest_observation_view(packet("2026-10-22", -1.0, 1.0), rows)
    assert view["notification"]["kind"] == "reversal"
    assert view["notification"] == rows[-1]["notification"]
    assert view["window_2s"] is not None


def test_stale_notice_keeps_notification_but_drops_current_only_context(tmp_path, monkeypatch):
    rows = run_chain(tmp_path, monkeypatch, [("2026-10-21", packet("2026-10-21", -1.0, 1.0)),
                                             ("2026-10-22", packet("2026-10-22", 2.0, -1.0))])
    later = packet("2026-10-23", 2.0, -1.0, availability={"status": "VERIFIED", "available_at": None},
                   coverage={"registered_pairs": 1, "evaluable_2s": 1, "missing_pair_ids": []},
                   lineage={"roots": ["x"]})
    view = owner.project_latest_observation_view(later, rows)
    assert view["notification"]["event_as_of"] == "2026-10-22"
    assert view["window_2s"] is None and view["horizon_20s"] is None
    assert view["availability"] == {"status": "UNKNOWN", "available_at": None}
    assert view["coverage"] is None and view["lineage_roots"] == []


def test_only_a_chain_tip_can_stand(tmp_path, monkeypatch):
    rows = run_chain(tmp_path, monkeypatch, [("2026-10-21", packet("2026-10-21", -1.0, 1.0)),
                                             ("2026-10-22", packet("2026-10-22", 2.0, -1.0)),
                                             ("2026-10-23", packet("2026-10-23", 3.0, -1.0))])
    assert "notification" in rows[1] and "notification" not in rows[2]
    assert owner.project_latest_observation_view(packet("2026-10-23", 3.0, -1.0), rows) is None


def test_withdrawal_is_projected_without_a_measured_window(tmp_path, monkeypatch):
    rows = run_chain(tmp_path, monkeypatch, [("2026-10-21", packet("2026-10-21", -1.0, 1.0)),
                                             ("2026-10-22", packet("2026-10-22", 2.0, -1.0)),
                                             ("2026-10-23", {})])
    view = owner.project_latest_observation_view({"as_of": "2026-10-23", "pairs": []}, rows)
    assert view["notification"]["kind"] == "data_withdrawal"
    assert view["notification"]["values"] is None
    assert view["window_2s"] is None


def test_window_is_withheld_when_published_values_disagree_with_the_receipt(tmp_path, monkeypatch):
    rows = run_chain(tmp_path, monkeypatch, [("2026-10-21", packet("2026-10-21", -1.0, 1.0)),
                                             ("2026-10-22", packet("2026-10-22", 2.0, -1.0))])
    drifted = packet("2026-10-22", 2.5, -1.0)
    view = owner.project_latest_observation_view(drifted, rows)
    assert view["notification"] == rows[-1]["notification"]
    assert view["window_2s"] is None


def test_twenty_session_horizon_requires_exact_identity(tmp_path, monkeypatch):
    rows = run_chain(tmp_path, monkeypatch, [("2026-10-21", packet("2026-10-21", -1.0, 1.0)),
                                             ("2026-10-22", packet("2026-10-22", 2.0, -1.0))])
    ctx = packet("2026-10-22", 2.0, -1.0)
    good = {"eligible": True, "sessions": 20, "start": "2026-09-24", "end": "2026-10-22",
            "numerator_return_pct": 5.0, "denominator_return_pct": 1.0,
            "ratio_return_pct": ((1.05 / 1.01) - 1) * 100}
    ctx["pairs"][0]["horizons"]["20s"] = good
    hz =owner.project_latest_observation_view(ctx, rows)["horizon_20s"]
    assert hz == {"sessions": 20, "start": "2026-09-24", "end": "2026-10-22",
                  "numerator_return_pct": 5.0, "denominator_return_pct": 1.0,
                  "ratio_return_pct": good["ratio_return_pct"]}
    for bad in ({"ratio_return_pct": 9.0}, {"sessions": 19}, {"eligible": False}, {"end": "2026-10-21"},
                {"start": "2026-9-24"}, {"numerator_return_pct": float("nan")}, {"sessions": 20.0}):
        ctx["pairs"][0]["horizons"]["20s"] = {**good, **bad}
        assert owner.project_latest_observation_view(ctx, rows)["horizon_20s"] is None, bad


def test_non_canonical_ledger_line_refuses_the_whole_read(tmp_path, monkeypatch):
    run_chain(tmp_path, monkeypatch, [("2026-10-21", packet("2026-10-21", -1.0, 1.0)),
                                      ("2026-10-22", packet("2026-10-22", 2.0, -1.0))])
    path = tmp_path / "rotation_events" / "events.jsonl"
    lines = ledger_lines(tmp_path)
    lines[-1] = json.dumps(json.loads(lines[-1]), sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not canonical"):
        owner.read_early_observation_ledger(tmp_path)


def test_reader_never_writes(tmp_path, monkeypatch):
    run_chain(tmp_path, monkeypatch, [("2026-10-21", packet("2026-10-21", -1.0, 1.0)),
                                      ("2026-10-22", packet("2026-10-22", 2.0, -1.0))])
    root = tmp_path / "rotation_events"
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    owner.read_early_observation_ledger(tmp_path)
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


# ---- builder republish ----------------------------------------------------------

@pytest.fixture
def canonical(tmp_path, monkeypatch):
    monkeypatch.setattr(builder.config, "ROOT", tmp_path)
    monkeypatch.setattr(builder.config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(builder.config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.setenv("ROTATION_OBSERVATION_RECORDING_ENABLED", "1")
    root = tmp_path / "data" / "rotation_events"
    root.mkdir(parents=True)
    (root / "state.json").write_text(json.dumps({"active": {}, "lockout": {}}))
    return tmp_path / "data", tmp_path / "site"


def prepare(monkeypatch, ctx, seen_alerts):
    stamp = clock(ctx["as_of"])

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return stamp if tz is not None else stamp.replace(tzinfo=None)
    monkeypatch.setattr(builder, "datetime", Frozen)
    monkeypatch.setattr(builder.sector_legs, "load_registry", lambda: {})
    monkeypatch.setattr(builder.sector_legs, "sector_closes", lambda registry: {})
    monkeypatch.setattr(builder.sector_fragmentation, "compute", lambda *a, **k: {"n_fragmented": 0, "sectors": []})
    payload = {"schema": "rotation_events.v1", "as_of": ctx["as_of"], "active": [], "created_tonight": [],
               "closed_tonight": [], "early_context": ctx}
    monkeypatch.setattr(builder.rotation_events, "run_nightly", lambda *a, **k: copy.deepcopy(payload))

    def alerts(p):
        seen_alerts.append(copy.deepcopy(p))
        return []
    monkeypatch.setattr(builder.rotation_events, "to_alerts", alerts)


def published(site):
    return json.loads((site / "marketdata" / "rotation_events.json").read_text(encoding="utf-8"))


def test_builder_publishes_view_only_after_a_recorded_notice(canonical, monkeypatch):
    data, site = canonical
    seen = []
    prepare(monkeypatch, packet("2026-10-21", -1.0, 1.0), seen)
    first = builder.build()
    assert first["early_observation_recording"] == {"status": "recorded", "receipts": 1, "view": "absent"}
    assert "latest_observation" not in published(site)["early_context"]
    prepare(monkeypatch, packet("2026-10-22", 2.0, -1.0), seen)
    second = builder.build()
    assert second["early_observation_recording"] == {"status": "recorded", "receipts": 1, "view": "published"}
    out = published(site)
    view = out["early_context"]["latest_observation"]
    stored = (data / "rotation_events" / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    assert view["recorded"]["receipt_sha256"] == hashlib.sha256(stored.encode("utf-8")).hexdigest()
    assert view["notification"] == json.loads(stored)["notification"]
    assert {k: v for k, v in out["early_context"].items() if k != "latest_observation"} == \
        packet("2026-10-22", 2.0, -1.0)
    assert all("latest_observation" not in p["early_context"] for p in seen)
    assert not list((site / "marketdata").glob(".rotation_events.*"))


def test_builder_view_failure_leaves_the_legacy_publication_byte_identical(canonical, monkeypatch):
    data, site = canonical
    seen = []
    prepare(monkeypatch, packet("2026-10-21", -1.0, 1.0), seen)
    builder.build()
    prepare(monkeypatch, packet("2026-10-22", 2.0, -1.0), seen)
    captured = {}
    real = builder._record_early_observations

    def spy(payload, **kw):
        captured["before"] = (site / "marketdata" / "rotation_events.json").read_bytes()
        return real(payload, **kw)

    def boom(*a, **k):
        raise RuntimeError("projection failed")
    monkeypatch.setattr(builder, "_record_early_observations", spy)
    monkeypatch.setattr(builder.rotation_events, "project_latest_observation_view", boom)
    result = builder.build()
    assert result["early_observation_recording"] == {"status": "recorded", "receipts": 1, "view": "unavailable"}
    assert (site / "marketdata" / "rotation_events.json").read_bytes() == captured["before"]
    assert not list((site / "marketdata").glob(".rotation_events.*"))


def test_builder_disabled_flag_never_publishes_a_view(canonical, monkeypatch):
    data, site = canonical
    monkeypatch.delenv("ROTATION_OBSERVATION_RECORDING_ENABLED")
    seen = []
    prepare(monkeypatch, packet("2026-10-22", 2.0, -1.0), seen)
    result = builder.build()
    assert result["early_observation_recording"] == {"status": "disabled", "receipts": 0}
    assert "latest_observation" not in published(site)["early_context"]
    assert not (data / "rotation_events" / "events.jsonl").exists()
