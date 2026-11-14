"""Synthetic state models and pure cadence/budget/telemetry contracts."""
from __future__ import annotations
import random
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.xguerrilla import lease, scheduler, telemetry, watchers  # noqa: E402
from tools.xguerrilla.persona import Persona  # noqa: E402

TZ = ZoneInfo("America/Chicago")


class Clock:
    """Injectable wall clock so TTL tests do not sleep."""

    def __init__(self, t: float = 1_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> float:
        self.t += seconds
        return self.t


def make_persona(**kw) -> Persona:
    base = dict(handle="child_07", cell="cell-a", tz="America/Chicago", seed=7,
                hours=(8, 23), idle_day_p=0.0, actions_per_day=18)
    base.update(kw)
    return Persona(**base)


# ---------------------------------------------------------------- leases

def test_two_acquires_cannot_both_win(tmp_path):
    db = tmp_path / "leases.db"
    a, b = lease.SimulationLeaseStore(db), lease.SimulationLeaseStore(db)
    assert a.owner != b.owner

    assert a.acquire("child_07", 120, {"pid": 1}) is True
    assert b.acquire("child_07", 120) is False
    assert a.held_by("child_07") == a.owner
    assert b.held_by("child_07") == a.owner
    assert a.meta("child_07") == {"pid": 1}


def test_same_store_cannot_re_acquire_a_live_lease(tmp_path):
    s = lease.SimulationLeaseStore(tmp_path / "l.db")
    assert s.acquire("h", 60) is True
    assert s.acquire("h", 60) is False


def test_release_only_by_owner(tmp_path):
    db = tmp_path / "l.db"
    a, b = lease.SimulationLeaseStore(db), lease.SimulationLeaseStore(db)
    a.acquire("h", 60)
    assert b.release("h") is False
    assert a.release("h") is True
    assert a.held_by("h") is None
    assert b.acquire("h", 60) is True


def test_expired_lease_is_reacquired(tmp_path):
    db = tmp_path / "l.db"
    clock = Clock()
    a = lease.SimulationLeaseStore(db, clock=clock)
    b = lease.SimulationLeaseStore(db, clock=clock)
    assert a.acquire("h", 10) is True
    clock.advance(11)
    assert a.held_by("h") is None
    assert b.acquire("h", 10) is True
    assert a.acquire("h", 10) is False
    assert a.held_by("h") == b.owner


def test_renew_extends_only_while_live(tmp_path):
    clock = Clock()
    s = lease.SimulationLeaseStore(tmp_path / "l.db", clock=clock)
    assert s.acquire("h", 10) is True
    clock.advance(8)
    assert s.renew("h", 30) is True
    clock.advance(5)                      # past the original TTL, inside the renewal
    assert s.held_by("h") == s.owner
    clock.advance(26)                     # now past the renewal too
    assert s.held_by("h") is None
    assert s.renew("h", 30) is False


def test_sweep_drops_expired_rows(tmp_path):
    clock = Clock()
    s = lease.SimulationLeaseStore(tmp_path / "l.db", clock=clock)
    assert s.acquire("a", 5) and s.acquire("b", 5)
    s.acquire("c", 600)
    assert s.sweep() == 0
    clock.advance(10)
    assert s.sweep() == 2
    assert s.sweep() == 0
    assert s.held_by("c") == s.owner


def test_ttl_must_be_positive(tmp_path):
    s = lease.SimulationLeaseStore(tmp_path / "l.db")
    with pytest.raises(ValueError):
        s.acquire("h", 0)


# ------------------------------------------------------------- scheduler

def test_next_run_stays_inside_the_window():
    p = make_persona()
    now = datetime(2026, 3, 3, 12, 0, tzinfo=TZ)
    nxt = scheduler.next_run(p, now)
    assert nxt > now
    assert nxt.astimezone(TZ).hour >= 8
    assert nxt < datetime(2026, 3, 3, 23, 0, tzinfo=TZ)
    assert nxt.utcoffset() == now.utcoffset()


def test_next_run_before_and_after_hours_returns_window_start():
    p = make_persona()
    early = scheduler.next_run(p, datetime(2026, 3, 3, 6, 30, tzinfo=TZ))
    assert early == datetime(2026, 3, 3, 8, 0, tzinfo=TZ)
    late = scheduler.next_run(p, datetime(2026, 3, 3, 23, 30, tzinfo=TZ))
    assert late == datetime(2026, 3, 4, 8, 0, tzinfo=TZ)


def test_next_run_is_deterministic_for_a_seed():
    p = make_persona(seed=42)
    now = datetime(2026, 3, 3, 12, 0, tzinfo=TZ)
    assert scheduler.next_run(p, now) == scheduler.next_run(make_persona(seed=42), now)
    assert scheduler.next_run(p, now, random.Random(3)) == scheduler.next_run(p, now, random.Random(3))


def test_idle_day_skips_to_the_next_window():
    p = make_persona(idle_day_p=1.0)
    now = datetime(2026, 3, 3, 12, 0, tzinfo=TZ)
    nxt = scheduler.next_run(p, now)
    assert nxt.date() > now.date()
    assert nxt.hour == 8 and nxt.minute == 0


def test_plan_day_count_window_ordering():
    p = make_persona(actions_per_day=12)
    day = date(2026, 3, 3)
    slots = scheduler.plan_day(p, day, random.Random(11))
    assert len(slots) == 12
    assert slots == sorted(slots) and len(set(slots)) == 12
    for slot in slots:
        assert slot.tzinfo is not None
        assert slot.date() == day
        assert 8 <= slot.hour < 23


def test_plan_day_is_deterministic_for_a_fixed_seed():
    day = date(2026, 3, 3)
    a = scheduler.plan_day(make_persona(seed=5), day, random.Random(1234))
    b = scheduler.plan_day(make_persona(seed=5), day, random.Random(1234))
    assert a == b
    # and the seed-derived default is stable too
    assert scheduler.plan_day(make_persona(seed=5), day) == scheduler.plan_day(make_persona(seed=5), day)


def test_plan_day_squeezes_into_a_short_window():
    p = make_persona(actions_per_day=10, hours=(9, 10))
    slots = scheduler.plan_day(p, date(2026, 3, 3), random.Random(2))
    assert len(slots) == 10
    assert slots[0] >= datetime(2026, 3, 3, 9, 0, tzinfo=TZ)
    assert slots[-1] < datetime(2026, 3, 3, 10, 0, tzinfo=TZ)
    assert all(x < y for x, y in zip(slots, slots[1:]))


def test_plan_day_zero_and_idle_opt_in():
    assert scheduler.plan_day(make_persona(actions_per_day=0), date(2026, 3, 3)) == []
    idle = make_persona(idle_day_p=1.0)
    assert scheduler.plan_day(idle, date(2026, 3, 3), honour_idle=True) == []
    assert len(scheduler.plan_day(idle, date(2026, 3, 3))) == 18


# -------------------------------------------------------------- watchers

def test_reaction_delay_stays_in_band_and_follows_kind_order():
    rng = random.Random(99)
    draws = {k: [watchers.reaction_delay(rng, k) for _ in range(500)] for k in watchers.KINDS}
    for kind, xs in draws.items():
        assert all(isinstance(x, int) for x in xs)
        assert all(240 <= x <= 5400 for x in xs), (kind, min(xs), max(xs))
    fast = statistics.median(draws["follow"])
    mention = statistics.median(draws["mention"])
    like = statistics.median(draws["like"])
    assert fast < like and mention < like
    assert fast <= statistics.median(draws["reply"])


def test_budget_refuses_the_third_reaction_in_an_hour():
    b = watchers.ReactionBudget()
    now = datetime(2026, 3, 3, 12, 0, tzinfo=TZ)
    assert b.allow(now, 0, 0) is True
    heap: list[float] = []
    assert b.allow_from(heap, now) is True
    b.pay(heap, now)
    assert b.allow_from(heap, now + timedelta(minutes=10)) is True
    b.pay(heap, now + timedelta(minutes=10))
    assert b.allow_from(heap, now + timedelta(minutes=20)) is False
    # an hour later the hourly ceiling lifts, the daily one has not
    later = now + timedelta(hours=2)
    assert b.allow_from(heap, later) is True
    assert b.allow(later, 8, 0) is False


def test_select_targets_drops_stale_and_already_replied():
    now = datetime(2026, 3, 3, 12, 0, tzinfo=TZ)
    p = make_persona()
    events = [
        watchers.Event("reply", "ghost", "p0", now - timedelta(hours=40)),
        watchers.Event("mention", "answered", "p1", now - timedelta(minutes=20)),
        watchers.Event("follow", "newfan", "p2", now - timedelta(hours=3)),
        watchers.Event("reply", "replier", "p3", now - timedelta(hours=1)),
        watchers.Event("like", "ambient", "p4", now - timedelta(minutes=5)),
        watchers.Event("follow", "newfan", "p5", now - timedelta(hours=2)),
    ]
    budget = watchers.ReactionBudget(max_per_day=8, max_per_hour=3)
    got = watchers.select_targets(events, p, random.Random(1), budget, now, {"answered"})
    actors = [e.actor for e in got]
    assert "ghost" not in actors and "answered" not in actors
    assert actors.count("newfan") == 1
    assert actors[:2] == ["newfan", "replier"]        # weight beats recency
    assert len(got) <= min(budget.max_per_day, budget.max_per_hour)
    assert [e.kind for e in got] == ["follow", "reply", "like"]


def test_select_targets_is_orderable_and_respects_budget():
    now = datetime(2026, 3, 3, 12, 0, tzinfo=TZ)
    p = make_persona()
    events = [watchers.Event("like", f"a{i}", f"p{i}", now - timedelta(minutes=i))
              for i in range(9)]
    tight = watchers.ReactionBudget(max_per_day=1, max_per_hour=5)
    assert len(watchers.select_targets(events, p, random.Random(2), tight, now, set())) == 1
    loose = watchers.ReactionBudget(max_per_day=9, max_per_hour=9)
    got = watchers.select_targets(events, p, random.Random(2), loose, now, set())
    assert len(got) == 9 and [e.actor for e in got] == [f"a{i}" for i in range(9)]


# ------------------------------------------------------------- telemetry

def test_summarise_counts_labels_iki_challenges_and_relogins(tmp_path):
    path = tmp_path / "telemetry" / "run.jsonl"
    telemetry.record(path, "typing", handle="child_07", iki=[100.0, 200.0, 300.0])
    telemetry.record(path, "typing", handle="child_07", iki=[500.0])
    for label in ("auth", "auth", "spam"):
        telemetry.record(path, "label", handle="child_07", label=label)
    telemetry.record(path, "challenge", handle="child_07", kind_detail="arkose")
    telemetry.record(path, "session", handle="child_07", ok=True)
    telemetry.record(path, "session", handle="child_07", ok=False, relogin=True)

    s = telemetry.summarise(path)
    assert s["labels"] == {"auth": 2, "spam": 1}
    assert s["kinds"]["label"] == 3 and s["kinds"]["typing"] == 2
    assert s["challenges"] == 1
    assert s["sessions"] == 2
    assert s["relogin_fraction"] == pytest.approx(0.5)
    assert s["iki_n"] == 4 and s["iki_median"] == pytest.approx(250.0)
    assert s["rows"] == 8


def test_summarise_survives_a_torn_tail(tmp_path):
    path = tmp_path / "t.jsonl"
    telemetry.record(path, "label", label="ok")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write('{"kind": "label", "lab')
    s = telemetry.summarise(path)
    assert s["labels"] == {"ok": 1} and s["rows"] == 1


def test_summarise_missing_file_is_empty(tmp_path):
    s = telemetry.summarise(tmp_path / "nope.jsonl")
    assert s["rows"] == 0 and s["labels"] == {} and s["relogin_fraction"] == 0.0
    assert s["challenges"] == 0


def test_session_ok_uses_the_latest_row_per_handle(tmp_path):
    path = tmp_path / "s.jsonl"
    telemetry.record(path, "session", handle="child_07", ok=True)
    assert telemetry.session_ok(path, "child_07") is True
    telemetry.record(path, "session", handle="child_07", relogin=True)
    assert telemetry.session_ok(path, "child_07") is False
    assert telemetry.session_ok(path, "child_08") is False


def test_record_appends_one_line_and_fsyncs(tmp_path):
    path = tmp_path / "r.jsonl"
    telemetry.record(path, "label", label="a")
    telemetry.record(path, "label", label="b")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2 and telemetry.rows(path)[1]["label"] == "b"
