"""Unit tests for engine.subsector_rotation_alerts — rotation change-detection."""
from __future__ import annotations

from engine import subsector_rotation_alerts as A


def _payload(subs):
    return {"generated_utc": "2026-06-28 00:00", "subsectors": subs}


def _sub(key, name, quadrant, rs_mom, accel, emerging_score, rs_ratio=0.0, perf=None):
    return {"key": key, "name": name, "theme": "T", "quadrant": quadrant,
            "rs_mom": rs_mom, "accel": accel, "emerging_score": emerging_score,
            "rs_ratio": rs_ratio, "perf": perf or {"1W": 5, "1M": 4, "3M": 3}}


def test_seed_is_silent():
    p = _payload([_sub("a", "A", "improving", 1.5, 4.0, 2.0)])
    assert A.compute_events(p, None) == []
    assert A.compute_events(p, {}) == []


def test_rotate_in_fires_on_flip():
    p = _payload([_sub("a", "A", "improving", 1.5, 4.0, 2.0)])
    prior = {"a": {"quadrant": "lagging", "emerging": False}}
    evs = A.compute_events(p, prior)
    assert len(evs) == 1
    e = evs[0]
    assert e["type"] == "rotation_emerging" and e["asset"] == "a"
    assert e["source"] == "rotation" and e["severity"] == "high"  # score >= 1.8
    assert "Rotating in" in e["headline"]


def test_no_refire_when_already_emerging():
    p = _payload([_sub("a", "A", "improving", 1.5, 4.0, 2.0)])
    prior = {"a": {"quadrant": "improving", "emerging": True}}
    assert A.compute_events(p, prior) == []


def test_rotate_out_fires_when_leader_rolls_over():
    p = _payload([_sub("a", "A", "weakening", -2.0, -1.0, -0.5, rs_ratio=1.5)])
    prior = {"a": {"quadrant": "leading", "emerging": True}}
    evs = A.compute_events(p, prior)
    assert len(evs) == 1 and evs[0]["type"] == "rotation_fading"
    assert "Rolling over" in evs[0]["headline"]


def test_below_bar_does_not_fire():
    # improving but weak score / negative accel → not "emerging".
    p = _payload([_sub("a", "A", "improving", 0.2, -0.5, 0.3)])
    prior = {"a": {"quadrant": "lagging", "emerging": False}}
    assert A.compute_events(p, prior) == []


def test_snapshot_roundtrip():
    p = _payload([_sub("a", "A", "improving", 1.5, 4.0, 2.0)])
    snap = A._snapshot(p)
    assert snap["a"]["emerging"] is True and snap["a"]["quadrant"] == "improving"


# ── turn-lane events (engine.subsector_turn) ───────────────────────────────────
def _turn_sub(key, state, **kw):
    s = _sub(key, key.upper(), "improving", 1.0, 2.0, 1.5)
    s.update({"turn_state": state, "turn_since": "2026-06-28", "n_members": 8,
              "bottom_score": 0.8, "top_score": 0.8, "turn_score": 0.8,
              "dd_from_peak": -14.0, "up_from_trough": 30.0,
              "breadth": {"n": 8, "turn_up": 0.9, "turn_dn": 0.9, "concentrated": False},
              "pace_mkt": {"w1": -1.0}, "legs_up": {}, "legs_dn": {}})
    s.update(kw)
    return s


def test_turn_up_fires_once_on_the_transition():
    p = _payload([_turn_sub("a", "turn_up")])
    prior = {"a": {"name": "A", "theme": "T", "quadrant": "improving", "emerging": True,
                   "turn_state": "bottoming"}}
    evs = [e for e in A.compute_events(p, prior) if e["type"] == "rotation_turn_up"]
    assert len(evs) == 1 and evs[0]["severity"] == "high"
    # already in the state → no re-fire
    prior2 = {"a": {**prior["a"], "turn_state": "turn_up"}}
    assert [e for e in A.compute_events(p, prior2) if e["type"].startswith("rotation_turn")] == []


def test_turn_lane_seeds_silently_when_prior_predates_the_field():
    """A state file written before the turn engine shipped must not fire 11 turns at once."""
    p = _payload([_turn_sub("a", "turn_up"), _turn_sub("b", "turn_down")])
    prior = {"a": {"name": "A", "theme": "T", "quadrant": "improving", "emerging": True},
             "b": {"name": "B", "theme": "T", "quadrant": "weakening", "emerging": False}}
    assert [e for e in A.compute_events(p, prior) if e["type"].startswith("rotation_turn")] == []


def test_turn_severity_needs_size_and_breadth():
    """RC-R5: a one-name move cannot print `high` however violent its score."""
    thin = _turn_sub("t", "turn_up", n_members=2,
                     breadth={"n": 2, "turn_up": 1.0, "turn_dn": 0.0, "concentrated": True})
    assert A._turn_severity(thin, up=True) == "minor"
    narrow = _turn_sub("n", "turn_up", n_members=8,
                       breadth={"n": 8, "turn_up": 0.25, "turn_dn": 0.0, "concentrated": True})
    assert A._turn_severity(narrow, up=True) == "medium"
    assert A._turn_severity(_turn_sub("g", "turn_up"), up=True) == "high"
    # an unconfirmed candidate never reaches high
    assert A._turn_severity(_turn_sub("c", "topping"), up=False) == "minor"


def test_turn_alert_copy_has_no_double_negative_and_follows_the_basis():
    """"fell -40.5%" is a double negative; a leadership-basis node must not say "fell 0%"."""
    price = _turn_sub("p", "turn_up", dd_from_peak=-40.5, basis_up="price")
    lead = _turn_sub("l", "turn_up", dd_from_peak=-0.2, rs_dd_from_peak=-10.9,
                     basis_up="leadership")
    prior = {k: {"name": k, "theme": "T", "quadrant": "improving", "emerging": True,
                 "turn_state": "bottoming"} for k in ("p", "l")}
    evs = {e["asset"]: e for e in A.compute_events(_payload([price, lead]), prior)
           if e["type"] == "rotation_turn_up"}
    assert "fell 40.5%" in evs["p"]["detail"] and "-40.5" not in evs["p"]["detail"]
    assert "gave up 10.9% of its lead" in evs["l"]["detail"]
    assert "fell 0" not in evs["l"]["detail"]
    for e in evs.values():                      # ZH parity, no raw EN state names
        assert "turn_up" not in e["detail_zh"] and "%" in e["detail_zh"]

def test_build_art_dir_isolates_shared_rotation_alert_store(tmp_path, monkeypatch):
    """A scratch/replay build must not write the configured shared alert store."""
    import json

    from scripts import build_rotation_events as builder
    from engine import subsector_rotation_alerts as sra

    configured_data = tmp_path / "configured-data"
    scratch_data = tmp_path / "scratch-data"
    scratch_site = tmp_path / "scratch-site"

    # Keep all real filesystem effects inside this test's temporary directory.
    monkeypatch.setattr(builder.config, "ROOT", tmp_path / "repo")
    monkeypatch.setattr(builder.config, "data_dir", lambda: configured_data)
    monkeypatch.setattr(sra.config, "data_dir", lambda: configured_data)

    monkeypatch.setattr(builder.sector_legs, "load_registry", lambda: {})
    monkeypatch.setattr(builder.sector_legs, "sector_closes", lambda _registry: {})
    monkeypatch.setattr(
        builder.sector_fragmentation,
        "compute",
        lambda _sectors, generated_utc=None: {"n_fragmented": 0, "sectors": []},
    )

    event = {
        "id": "xlk:memory->mag7",
        "sector": "xlk",
        "sector_name_en": "Technology",
        "sector_name_zh": "科技",
        "from_leg": {"key": "memory", "name_en": "Memory", "name_zh": "存储", "tier": 1},
        "to_leg": {"key": "mag7", "name_en": "Mag 7", "name_zh": "七巨头", "tier": 1},
        "started": "2026-10-03",
        "day_n": 1,
        "asof": "2026-10-03",
        "severity": "major",
        "receipts": {},
        "copy_en": "Memory hands off to Mag 7.",
        "copy_zh": "存储向七巨头交棒。",
    }
    payload = {
        "schema": "rotation_events.v1",
        "ok": True,
        "as_of": "2026-10-03",
        "generated_utc": "2026-10-04 04:30 UTC",
        "authority": {
            "tier": "display",
            "may_rank": False,
            "may_gate": False,
            "may_size": False,
            "may_escalate": False,
        },
        "params": {},
        "n_pairs_scanned": 1,
        "active": [event],
        "created_tonight": [event["id"]],
        "closed_tonight": [],
        "coldstart": False,
    }
    monkeypatch.setattr(builder.rotation_events, "run_nightly", lambda *_args, **_kwargs: payload)

    builder.build(
        site=scratch_site,
        art_dir=scratch_data,
        generated_utc="2026-10-04 04:30 UTC",
    )

    configured_alerts = configured_data / "subsector_rotation" / "alerts.jsonl"
    configured_alerts.parent.mkdir(parents=True, exist_ok=True)
    sentinel = '{"id":"existing","ts":"2026-10-01","asset":"existing"}\n'
    configured_alerts.write_text(sentinel)

    # Run once more with an existing configured store: a scratch build must neither
    # read from nor rewrite the incumbent production/configured alert history.
    builder.build(
        site=scratch_site,
        art_dir=scratch_data,
        generated_utc="2026-10-04 04:31 UTC",
    )

    scratch_alerts = scratch_data / "subsector_rotation" / "alerts.jsonl"
    assert configured_alerts.read_text() == sentinel, "scratch build rewrote configured alert store"
    assert scratch_alerts.exists(), "scratch build did not retain its generated alerts"
    rows = [json.loads(line) for line in scratch_alerts.read_text().splitlines() if line.strip()]
    assert [row["asset"] for row in rows] == [event["id"]]
