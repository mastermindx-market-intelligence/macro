"""Synthetic pilot-model regressions, not the real section 26.9 gate.

Temporary generated persona/link files pass through the actual loader. Fake
clock/driver/model results confer no live or incumbent runtime authority."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from tools.xguerrilla import config, gate, pilot_sim, telemetry
from tools.xguerrilla.drivers import base
from tools.xguerrilla.lease import SimulationLeaseStore
from tools.xguerrilla.typing import plan

DRIVER_METHODS = ("start", "goto", "snapshot", "find", "click", "type_plan",
                  "paste", "key", "screenshot", "stop")
CHILD = "harperbuilds"



@pytest.fixture(scope="module", autouse=True)
def _synthetic_configuration(synthetic_xg_config):
    """Redirect the actual loader's dynamic paths, not the loader or its result."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(config, "PERSONAS_DIR", str(synthetic_xg_config.personas))
        patch.setattr(config, "LINKS_PATH", str(synthetic_xg_config.links))
        yield

@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    """One full clean run, shared by the criteria-shaped tests (it is expensive)."""
    store = tmp_path_factory.mktemp("clean")
    return pilot_sim.run_pilot(list(pilot_sim.DEFAULT_CHILDREN), 14,
                               store_dir=str(store))


def run(tmp_path, children=(CHILD,), days=3, inject=None, seed=7):
    return pilot_sim.run_pilot(list(children), days, seed=seed,
                               store_dir=str(tmp_path / f"run{len(list(tmp_path.iterdir()))}"),
                               inject=inject)


def driver():
    drv = pilot_sim.FakeDriver()
    drv.start("/tmp/profile", "", True)
    return drv


# --------------------------------------------------------------------------
# driver contract
# --------------------------------------------------------------------------
def test_fake_driver_implements_the_whole_protocol_and_stops_cleanly():
    drv = pilot_sim.FakeDriver()
    assert [m for m in DRIVER_METHODS if not callable(getattr(drv, m, None))] == []
    assert base.Driver is not None
    drv.start("/tmp/profile", "", True)
    drv.stop()
    with pytest.raises(base.DriverError):
        drv.goto(pilot_sim.HOME_URL)


def test_fake_driver_folds_plans_and_pastes_into_the_exact_text():
    persona = config.load_personas()[CHILD]
    text = "one drink, three hours"
    drv = driver()
    drv.goto(pilot_sim.HOME_URL)
    drv.click(pilot_sim.COMPOSER)
    drv.type_plan(plan(text, persona))
    assert drv.keystrokes > 0 and drv.buffer == text
    drv.key("backspace")
    assert drv.buffer == text[:-1]
    drv.paste(" -- and then some")
    assert drv.pasted == [" -- and then some"]
    assert drv.buffer == text[:-1] + " -- and then some"
    snap = drv.snapshot()
    assert set(snap) == {"url", "title", "signed_in", "challenge"}
    assert snap["signed_in"] is True and snap["challenge"] is None
    drv.key("cmd+enter")
    assert drv.submits == 1 and drv.typed


# --------------------------------------------------------------------------
# determinism
# --------------------------------------------------------------------------
def _behaviour(report):
    doc = report.to_dict()
    doc.pop("telemetry", None)
    doc.pop("store_dir", None)
    return json.dumps(doc, sort_keys=True, default=str)


def test_the_sim_is_seeded_so_runs_replay_but_seeds_differ(tmp_path):
    assert _behaviour(run(tmp_path, days=2)) == _behaviour(run(tmp_path, days=2))
    assert _behaviour(run(tmp_path, days=2, seed=7)) != _behaviour(run(tmp_path, days=2, seed=99))


# --------------------------------------------------------------------------
# the clean fourteen days
# --------------------------------------------------------------------------
def test_fourteen_days_post_for_every_child_across_a_restart(clean):
    assert clean.days == 14 and clean.restarts >= 1
    for h in clean.children:
        assert clean.per_child_days[h] == 14, h
        assert clean.per_child_posts[h] >= 30, h
    rows = telemetry.rows(clean.telemetry)
    assert "restart" in [r["kind"] for r in rows]


def test_clean_run_is_green_with_no_challenges_and_no_relogin(clean):
    assert clean.challenges == 0 and clean.relogins == 0
    assert clean.ok is True and clean.failures == []
    assert set(clean.criteria) == {k for k, _ in pilot_sim.CRITERIA}
    sessions = [r for r in telemetry.rows(clean.telemetry) if r["kind"] == "session"]
    assert sessions and all(r["ok"] for r in sessions)
    assert telemetry.session_ok(clean.telemetry, CHILD) is True


def test_every_child_shows_two_labels(clean):
    for h in clean.children:
        assert len(clean.labels[h]) >= 2, (h, clean.labels[h])


def test_iki_medians_sit_inside_their_class_band(clean):
    for h in clean.children:
        iki = clean.iki[h]
        lo, hi = iki["band"]
        assert iki["n"] > 0 and lo <= iki["median"] <= hi, (h, iki)
    assert clean.out_of_band == []


# --------------------------------------------------------------------------
# faults: challenges
# --------------------------------------------------------------------------
def test_injected_challenge_is_counted_cools_the_child_and_it_finishes(tmp_path):
    report = run(tmp_path, days=5, inject={"challenge_after_n": 2})
    assert report.challenges == 1
    assert report.skipped.get("challenge", 0) >= 1
    assert [r["handle"] for r in telemetry.rows(report.telemetry)
            if r["kind"] == "challenge"] == [CHILD]
    assert report.per_child_days[CHILD] >= 4 and report.posts >= 10


def test_challenge_fails_the_zero_challenge_criterion(tmp_path):
    report = run(tmp_path, days=2, inject={"challenge_after_n": 1})
    assert report.ok is False
    assert any("zero challenges" in f for f in report.failures)


def test_two_challenges_retire_the_child(tmp_path):
    report = run(tmp_path, days=6, inject={"challenge_after_n": [1, 2]})
    assert report.challenges == 2
    assert report.per_child_days[CHILD] <= 1 and report.posts < 30


# --------------------------------------------------------------------------
# faults: session expiry
# --------------------------------------------------------------------------
def test_session_expiry_costs_one_relogin_and_no_post_in_the_cooldown(tmp_path):
    when = pilot_sim.START + timedelta(days=1, hours=6)
    report = run(tmp_path, days=3, inject={"expire_session_at": when})
    assert report.relogins == 1
    assert report.skipped.get("login cooldown", 0) >= 1
    later = [datetime.fromisoformat(r["at_sim"]) for r in telemetry.rows(report.telemetry)
             if r["kind"] == "post" and datetime.fromisoformat(r["at_sim"]) >= when]
    assert later and (min(later) - when).total_seconds() >= pilot_sim.LOGIN_COOLDOWN_S


# --------------------------------------------------------------------------
# faults: worker outage and degraded mode
# --------------------------------------------------------------------------
def test_outage_degrades_then_recovers(clean):
    assert len(clean.degraded_windows) == 1
    window = clean.degraded_windows[0]
    assert window["recovered"] is True and window["children_blocked"] == ["desk.and.dusk"]
    assert clean.skipped.get("degraded", 0) > 0


def test_outage_drops_only_the_broadcast_child_and_work_resumes(clean):
    start = datetime.fromisoformat(clean.degraded_windows[0]["start"])
    end = datetime.fromisoformat(clean.degraded_windows[0]["end"])
    inside = [h for (h, when, _) in clean.holds if start <= when <= end]
    assert "desk.and.dusk" not in inside
    assert "wren.mp4" in inside
    assert [h for (h, when, _) in clean.holds if when > end and h == "desk.and.dusk"]


# --------------------------------------------------------------------------
# faults: selector drift
# --------------------------------------------------------------------------
def test_selector_drift_quarantines_the_step_and_the_child_stays_runnable(tmp_path):
    report = run(tmp_path, days=2, inject={"selector_drift_step": 1})
    assert report.quarantined_steps == [pilot_sim.COMPOSER]
    assert report.skipped.get("step quarantined", 0) == 1
    assert report.per_child_days[CHILD] == 2 and report.posts >= 5


def test_repeated_drift_streak_keeps_the_child_working(tmp_path):
    report = run(tmp_path, days=2, inject={"selector_drift_step": 3})
    assert report.skipped.get("step quarantined", 0) == 3
    assert report.per_child_days[CHILD] == 2


# --------------------------------------------------------------------------
# leases
# --------------------------------------------------------------------------
def test_two_workers_race_and_exactly_one_wins(tmp_path):
    db = tmp_path / "leases.db"
    a = SimulationLeaseStore(str(db), clock=lambda: pilot_sim.START.timestamp())
    b = SimulationLeaseStore(str(db), clock=lambda: pilot_sim.START.timestamp())
    assert a.acquire(CHILD, 60) is True
    assert b.acquire(CHILD, 60) is False
    token = a.held_by(CHILD)
    assert token and token != CHILD and b.held_by(CHILD) == token
    a.release(CHILD)
    assert b.acquire(CHILD, 60) is True


def test_one_worker_per_handle_and_one_touch_per_minute(clean):
    by_handle: dict[str, list[tuple]] = {}
    for handle, start, end in clean.holds:
        by_handle.setdefault(handle, []).append((start, end))
    for handle, spans in by_handle.items():
        spans.sort()
        for (s1, e1), (s2, _e2) in zip(spans, spans[1:]):
            assert e1 <= s2, (handle, s1, e1, s2)
        minutes = [s.replace(second=0, microsecond=0) for (s, _e) in spans]
        assert len(minutes) == len(set(minutes)), handle


# --------------------------------------------------------------------------
# validators and post content
# --------------------------------------------------------------------------
def test_validators_block_a_bad_draft_and_the_corrected_one_still_posts(tmp_path):
    report = run(tmp_path, days=2, inject={"break_drafts": 3})
    assert report.violations_blocked == 3
    blocked = [r for r in telemetry.rows(report.telemetry) if r["kind"] == "blocked"]
    assert len(blocked) == 3 and all(r["why"] for r in blocked)
    assert report.posts >= 30 and report.per_child_days[CHILD] == 2


def test_every_post_is_typed_or_pasted_and_fits_the_persona(clean):
    assert clean.typed_posts + clean.pasted_posts == clean.posts
    assert clean.typed_posts > 0
    personas = config.load_personas()
    for row in telemetry.rows(clean.telemetry):
        if row["kind"] == "post":
            assert len(row["text"]) <= personas[row["handle"]].max_chars
            assert row["text"].strip() == row["text"]


# --------------------------------------------------------------------------
# gate CLI
# --------------------------------------------------------------------------
def test_gate_sim_exits_zero_on_a_clean_run(capsys, store_dir):
    assert gate.main(["sim", "--store-dir", store_dir]) == gate.EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["ok"] is True and doc["days"] == 14
    assert doc["evidence_scope"] == "synthetic_model"
    assert doc["runtime_binding_available"] is False
    assert doc["live_gate_satisfied"] is False


def test_gate_criteria_names_every_criterion(capsys, store_dir):
    assert gate.main(["criteria", "--store-dir", store_dir]) == gate.EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert [c["id"] for c in doc["criteria"]] == [k for k, _ in pilot_sim.CRITERIA]
    assert all(c["pass"] for c in doc["criteria"])


def test_gate_sim_fails_with_a_named_sentence_when_a_criterion_breaks(capsys, monkeypatch):
    real = pilot_sim.run_pilot

    def broken(*args, **kwargs):
        report = real(*args, **kwargs)
        report.challenges = 3
        report.ok = False
        report.failures = ["§26.9 zero challenges: the run saw 3 challenge(s)"]
        report.criteria["children_days_challenges"] = False
        return report

    monkeypatch.setattr(gate, "run_pilot", broken)
    assert gate.main(["sim"]) == gate.EXIT_FAILED
    doc = json.loads(capsys.readouterr().out)
    assert doc["ok"] is False
    assert doc["failures"][0].startswith("§26.9 zero challenges")


def test_gate_reports_exit_two_when_the_harness_itself_breaks(capsys, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("sqlite is gone")

    monkeypatch.setattr(gate, "run_pilot", boom)
    assert gate.main(["sim"]) == gate.EXIT_HARNESS
    assert "sqlite is gone" in json.loads(capsys.readouterr().out)["error"]


def test_gate_drill_passes(capsys):
    assert gate.main(["drill"]) == gate.EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["ok"] is True
    assert {d["drill"] for d in doc["drills"]} == {
        "challenge", "retire-on-second-wall", "session-expiry",
        "worker-outage", "selector-drift"}


@pytest.fixture(scope="module")
def store_dir(tmp_path_factory):
    return str(tmp_path_factory.mktemp("gate-store"))
