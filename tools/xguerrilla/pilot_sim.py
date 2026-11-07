"""Synthetic regression model for the historical child-harness design.

The fake clock and FakeDriver exercise scheduling, validators, typing and
telemetry. SimulationLeaseStore and SimulationSupervisor are model state, not
incumbent ownership, permission or health. Historical model continuation after
a simulated outage is not live policy or a recovery grant.

Every report declares synthetic_model evidence and live_gate_satisfied=False.
No result here proves the real section 26.9 pilot. Runtime entry points remain
unbound and unavailable. Explicit synthetic configuration must be supplied for
a bounded offline qualification; default persona loading is not itself such
qualification. See GATE.md and RUNBOOK.md."""
from __future__ import annotations

import random
import re
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

from . import config, scheduler, telemetry, typing as typing_mod, validators
from .drivers.base import Driver, DriverError, is_challenge
from .lease import SimulationLeaseStore
from .validators import Draft
from .supervisor import SimulationSupervisor

#: One lead, one conversation, one broadcast — the three roles §26.9 names. The
#: broadcast child is the one a worker outage is allowed to drop.
DEFAULT_CHILDREN = ("wren.mp4", "harperbuilds", "desk.and.dusk")

#: Simulated wall clock origin. Fixed, so the same seed replays the same run.
START = datetime(2026, 11, 9, 0, 0, tzinfo=timezone.utc)

#: A lease is held for the whole write, not just the compose: two workers must
#: never be inside one handle at once, even for a keystroke.
LEASE_TTL_S = 300

#: After a re-login the child stays out of the composer this long (§26.7).
LOGIN_COOLDOWN_S = 120

LOGIN_URL = "https://x.com/login"
HOME_URL = "https://x.com/home"
COMPOSER = "tweet text field"

#: Cooldowns handed to the supervisor when X pushes a wall, then a retirement
#: when the same child is challenged twice.
CHALLENGE_COOL_MIN = 240

#: Speed classes whose IKI medians the audit accepts, as multiples of the
#: persona's own median. Mirrors ``typing.assert_natural`` (§26.5).
BAND_LOW, BAND_HIGH = 0.5, 2.2
# Mirrors typing.assert_natural's cv window. If that band moves, move this one:
# a pilot that passes a distribution the live audit rejects is worse than no pilot.
CV_LOW, CV_HIGH = 0.6, 1.2


LABELS = ("beat-native", "local", "artifact", "adjacent", "opinion")

#: How far back the duplicate and voice checks look. The validator's own window
#: is the last ten posts; the voice window is twenty drafts.
HISTORY_N = 20

CRITERIA = (
    ("children_days_challenges",
     "three children run fourteen days with zero challenges"),
    ("iki_in_band", "IKI histograms stay inside each speed class band"),
    ("label_spread", "at least two labels in each child's thirty posts"),
    ("restart_without_relogin", "one restart is survived without a re-login"),
    ("outage_degraded_recovered",
     "one deliberate worker outage falls through to degraded mode and recovers"),
)


# --------------------------------------------------------------------------
# clock
# --------------------------------------------------------------------------
class SimClock:
    """A clock the simulator sets; nothing ever sleeps."""

    def __init__(self, start: datetime = START):
        self._t = start

    def now(self) -> datetime:
        return self._t

    def set(self, when: datetime) -> None:
        if when > self._t:
            self._t = when



def heartbeat(sup: SimulationSupervisor, when: datetime) -> None:
    """Re-stamp the supervisor's health row.

    ``supervisor.py`` has no ``heartbeat()`` — ``degrade``/``recover`` are the
    only writers — so a live harness has to beat the row itself or every child
    looks stale after ``STALE_HEALTH_S``. The simulator beats it on each slot so
    that "degraded" means the injected outage and nothing else.
    """
    sup.conn.execute("UPDATE health SET updated_at = ? WHERE id = 1", (when.timestamp(),))
    sup.conn.commit()


# --------------------------------------------------------------------------
# the fake driver
# --------------------------------------------------------------------------
class FakeDriver:
    """Implements every ``drivers.base.Driver`` method against memory.

    It records what it was asked to do and folds typed keystrokes into a field
    buffer exactly as a real composer would, so the caller can assert on the
    *post text* rather than on call counts. The knobs in ``inject`` are what a
    bad afternoon looks like:

    ``challenge_after_n``
        the Nth submit raises a verification wall;
    ``expire_session_at``
        the profile's cookie jar is cold from that moment (a datetime);
    ``selector_drift_step`` + ``drift_target``
        the Nth resolve of that target fails, once, as a drifted locator does;
    ``outage_window``
        held here for inspection; the worker loop owns the degradation.
    """

    name = "fake"

    def __init__(self, clock=None, inject: dict | None = None):
        self.clock = clock or SimClock()
        self.inject = dict(inject or {})
        self.running = False
        self.profile_dir: str | None = None
        self.proxy_url: str | None = None
        self.headless = True
        self.url = "about:blank"
        self.title = ""
        self.signed_in = True
        self.challenge: str | None = None
        self.buffer = ""
        self.submits = 0
        self.keystrokes = 0
        self.clicks: list[str] = []
        self.keys: list[str] = []
        self.pasted: list[str] = []
        self.typed: list[str] = []
        self.screenshots: list[str] = []
        self.relogins = 0
        self.login_cooldown_until: datetime | None = None
        self._expiry_fired = False
        n = self.inject.get("challenge_after_n")
        self.pending = sorted([int(n)] if isinstance(n, int) else [int(x) for x in (n or ())])
        self.drift_target = self.inject.get("drift_target", COMPOSER)
        self.drift_remaining = int(self.inject.get("selector_drift_step") or 0)

    # -- lifecycle ---------------------------------------------------------
    def start(self, profile_dir: str, proxy_url: str, headless: bool) -> None:
        if self.running:
            raise DriverError("already started")
        self.running = True
        self.profile_dir = str(profile_dir)
        self.proxy_url = proxy_url
        self.headless = bool(headless)
        self.url = HOME_URL
        self.title = "Home / X"

    def stop(self) -> None:
        self.running = False
        self.buffer = ""

    # -- navigation and reading -------------------------------------------
    def goto(self, url: str) -> None:
        self._live()
        self.url = url
        self.title = "Log in to X" if "login" in url else "Home / X"
        self.buffer = ""

    def snapshot(self) -> dict:
        self._live()
        self._expire_if_due()
        return {"url": self.url, "title": self.title,
                "signed_in": self.signed_in, "challenge": self.challenge}

    def find(self, target: str) -> dict:
        self._live()
        if self.drift_remaining > 0 and target == self.drift_target:
            self.drift_remaining -= 1
            raise DriverError(f"no node matches {target!r} (selector drift)")
        return {"target": target, "x": 320, "y": 180, "found": True}

    # -- acting ------------------------------------------------------------
    def click(self, target: str) -> None:
        self._live()
        self.clicks.append(target)
        if "text field" in target or "compose" in target:
            self.buffer = ""

    def type_plan(self, keys: list) -> None:
        self._live()
        for k in keys:
            kind = getattr(k, "kind", None)
            if kind == "char":
                self.buffer += getattr(k, "text", "")
            elif kind == "backspace":
                self.buffer = self.buffer[:-1]
            else:  # pragma: no cover - typing.py owns the vocabulary
                raise DriverError(f"unknown keystroke kind {kind!r}")
            self.keystrokes += 1
        self.typed.append(self.buffer)

    def paste(self, text: str) -> None:
        self._live()
        self.buffer += text
        self.pasted.append(text)

    def key(self, name: str) -> None:
        self._live()
        self.keys.append(name)
        if name in ("backspace", "delete"):
            self.buffer = self.buffer[:-1]
            return
        if name == "enter" and "login" in self.url:
            self.signed_in = True
            self.challenge = None
            self.relogins += 1
            self.login_cooldown_until = self.clock.now() + timedelta(seconds=LOGIN_COOLDOWN_S)
            self.url = HOME_URL
            self.title = "Home / X"
            return
        if name in ("cmd+enter", "enter"):
            self.submits += 1
            self.url = HOME_URL
            if self.pending and self.submits >= self.pending[0]:
                self.pending.pop(0)
                self.challenge = "Unusual activity — verify it is you"

    def screenshot(self, path: str) -> str:
        self._live()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\nfake")
        self.screenshots.append(str(path))
        return str(path)

    # -- internals ---------------------------------------------------------
    def _live(self) -> None:
        if not self.running:
            raise DriverError("driver is stopped")

    def _expire_if_due(self) -> None:
        when = self.inject.get("expire_session_at")
        if when and not self._expiry_fired and self.clock.now() >= when:
            self._expiry_fired = True
            self.signed_in = False
            self.url = LOGIN_URL
            self.title = "Log in to X"

    def in_cooldown(self) -> bool:
        return bool(self.login_cooldown_until) and self.clock.now() < self.login_cooldown_until


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
@dataclass
class Report:
    days: int = 0
    children: list[str] = field(default_factory=list)
    seed: int = 0
    posts: int = 0
    typed_posts: int = 0
    pasted_posts: int = 0
    per_child_posts: dict[str, int] = field(default_factory=dict)
    per_child_days: dict[str, int] = field(default_factory=dict)
    labels: dict[str, dict[str, int]] = field(default_factory=dict)
    iki: dict[str, dict] = field(default_factory=dict)
    out_of_band: list[str] = field(default_factory=list)
    challenges: int = 0
    relogins: int = 0
    restarts: int = 0
    degraded_windows: list[dict] = field(default_factory=list)
    lease_conflicts: int = 0
    violations_blocked: int = 0
    quarantined_steps: list[str] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)
    holds: list[tuple] = field(default_factory=list)
    telemetry: str = ""
    store_dir: str = ""
    ok: bool = True
    failures: list[str] = field(default_factory=list)
    criteria: dict[str, bool] = field(default_factory=dict)

    def fail(self, key: str, sentence: str) -> None:
        self.ok = False
        self.criteria[key] = False
        self.failures.append(sentence)

    def to_dict(self) -> dict:
        out = {
            "evidence_scope": "synthetic_model",
            "runtime_binding_available": False,
            "live_gate_satisfied": False,
            "days": self.days,
            "children": list(self.children),
            "seed": self.seed,
            "posts": self.posts,
            "typed_posts": self.typed_posts,
            "pasted_posts": self.pasted_posts,
            "per_child_posts": self.per_child_posts,
            "per_child_days": self.per_child_days,
            "labels": self.labels,
            "iki": self.iki,
            "out_of_band": list(self.out_of_band),
            "challenges": self.challenges,
            "relogins": self.relogins,
            "restarts": self.restarts,
            "degraded_windows": self.degraded_windows,
            "lease_conflicts": self.lease_conflicts,
            "violations_blocked": self.violations_blocked,
            "quarantined_steps": list(self.quarantined_steps),
            "skipped": self.skipped,
            "telemetry": self.telemetry,
            "store_dir": self.store_dir,
            "ok": self.ok,
            "failures": list(self.failures),
            "criteria": self.criteria,
        }
        return out


# --------------------------------------------------------------------------
# composing
# --------------------------------------------------------------------------
SUBJECTS = (
    "walked the block home", "shot the last frame twice", "pulled the second pot",
    "watched the queue outside", "took the corner table", "ran at 6am",
    "sat in the patio crowd", "left the bar light on",
    "carried the bag from last week", "made a third attempt",
    "found the room empty", "crossed the street at 11",
    "changed the grind setting", "took the train back", "cleared the desk at 4pm",
    "turned the lamp on", "opened the notebook", "put the phone face down",
    "ran the block", "let the grinder run", "left the tab open", "wrote page one",
    "took the window seat", "drank the cold cup", "answered the late reply",
    "stopped at the corner store", "ran a second lap", "cut a spare key",
    "went the long way round", "waited ten minutes", "paid the cab fare",
)

VERBS = (
    "did more than the preset", "cost less than one ad",
    "kept the bar path honest", "beat the clean version",
    "made the room feel used", "outlasted every app",
    "stopped working at the third rep", "tasted like the bag smells",
    "held the line on price", "took the whole morning",
    "needed a scale, not a machine", "made the queue worth it",
    "got there before the rush", "ran long and nobody minded",
    "turned into a three hour night", "sat on the desk for a week",
    "fixed nothing but felt right", "beat the second monitor",
    "made the walk shorter", "was the only honest thing all day",
    "cost 40 minutes and a cab", "kept nobody waiting",
)

TAILS = (
    "same weight, better bar path", "nobody photographs the good parts",
    "one drink, three hours", "grind finer, buy less",
    "the light did most of the work", "turn the lamp on, put the phone down",
    "the calls went up when spend went down", "the line is the cost of a good room",
    "a notebook outlasts any app", "four o'clock is the honest hour",
    "you can tell a place by its bathroom", "nothing on the menu is worth a queue",
    "the east side is a line now", "protein is a volume problem",
    "the bar is the plan for the week", "one more set, no drama",
    "a scale beats an upgrade", "the flash is the whole trick",
    "page one at four", "the desk is not a personality",
    "the bus is the tell", "there is no app for the fourth hour",
)

#: Appended to a draft the negative control wants rejected: long enough to blow
#: every persona's character cap without adding a sentence.
BAD_SUFFIX = " and then some and then a little more"

_WORD0 = re.compile(r"\s*([A-Za-z'\u2019]+)")


def _first_word(text: str) -> str:
    m = _WORD0.match(text or "")
    return m.group(1).lower() if m else ""


def _casing(text: str, persona) -> str:
    if persona.casing in ("lower", "lower_sometimes"):
        return text.lower()
    if persona.casing == "sentence":
        return text[:1].upper() + text[1:]
    return text


def _compose(persona, rng: random.Random, prev: str, force_voice: bool = False) -> str:
    """One draft-shaped pair, varied enough to clear the duplicate and opener gates.

    The opener is a clause, not a noun phrase, so consecutive posts do not all
    begin with "the" — ``enforce_voice`` fails a child that opens twice on the
    same word (§26.8).
    """
    avoid = _first_word(prev)
    pool = [s for s in SUBJECTS if _first_word(s) != avoid] or list(SUBJECTS)
    subj = rng.choice(pool)
    verb = rng.choice(VERBS)
    voice = force_voice or rng.random() < 0.45

    if voice:
        line = rng.choice(list(persona.pet_phrases) + list(persona.opinions))
        text = f"{subj}. {line}"
        if len(text) > persona.max_chars:
            text = f"{subj}, {rng.choice(TAILS)}"
    elif persona.max_chars < 110:
        text = f"{subj}, {rng.choice(TAILS)}"
    else:
        text = f"{subj} and it {verb}. {rng.choice(TAILS)}"
    return _casing(text, persona)


def _overlong(text: str, persona) -> str:
    while len(text) <= persona.max_chars:
        text += BAD_SUFFIX
    return text


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------
def run_pilot(children=None, days: int = 14, *, seed: int = 7,
              store_dir=None, persona_dir=None, inject: dict | None = None) -> Report:
    """Run the whole pilot in simulation and return the evidence.

    Never sleeps, never opens a browser, never touches the network. ``inject``
    is the failure panel; with none supplied the run is a clean fourteen days
    plus the two things §26.9 requires on purpose: one restart (day 7) and one
    worker outage (days 9-10) that must degrade and recover.
    """
    inject = dict(inject or {})
    personas = config.load_personas(persona_dir)
    handles = [h for h in (children or DEFAULT_CHILDREN)]
    unknown = [h for h in handles if h not in personas]
    if unknown:
        raise KeyError(f"unknown handle(s): {', '.join(unknown)}")
    if days < 1:
        raise ValueError("days must be at least 1")

    start = inject.get("start") or START
    clock = SimClock(start)
    root = Path(store_dir) if store_dir else Path(tempfile.mkdtemp(prefix="xg-pilot-"))
    root.mkdir(parents=True, exist_ok=True)
    tele = str(root / "telemetry.jsonl")
    db = str(root / "state.db")

    report = Report(days=days, children=list(handles), seed=seed,
                    telemetry=tele, store_dir=str(root))
    report.per_child_posts = {h: 0 for h in handles}
    report.per_child_days = {h: 0 for h in handles}
    report.labels = {h: {} for h in handles}
    report.iki = {h: {"n": 0, "median": 0.0, "cv": 0.0, "skew": 0.0} for h in handles}

    sup = SimulationSupervisor(db, personas={h: personas[h] for h in handles})
    leases = [SimulationLeaseStore(db, clock=lambda: clock.now().timestamp()) for _ in range(2)]
    drivers: dict[str, FakeDriver] = {}
    history: dict[str, list[Draft]] = {h: [] for h in handles}
    links_used: dict[str, list[datetime]] = {h: [] for h in handles}
    intervals: dict[str, list[float]] = {h: [] for h in handles}
    day_posts: dict[tuple[str, int], int] = Counter()
    challenge_since: dict[str, int] = Counter()
    voice_seen: dict[str, bool] = {h: False for h in handles}

    defect = report.fail
    restart_day = float(inject.get("restart_day", 7))
    outage = inject.get("outage_window", (9.0, 10.0))
    broken = int(inject.get("break_drafts") or 0)
    drafted = 0
    restarted = False
    outage_open: dict | None = None
    outage_done = False

    def driver_for(handle: str) -> FakeDriver:
        got = drivers.get(handle)
        if got is None:
            got = FakeDriver(clock=clock, inject=inject)
            got.start(str(root / "profiles" / handle), f"proxy://{personas[handle].cell}", True)
            drivers[handle] = got
        return got

    # -- the calendar ------------------------------------------------------
    events: list[tuple[datetime, str, int]] = []
    for d in range(days):
        day = (start + timedelta(days=d)).date()
        for h in handles:
            rng = random.Random(f"{seed}:{h}:{d}")
            for slot in scheduler.plan_day(personas[h], day, rng=rng):
                events.append((slot, h, d))
    events.sort()

    def wall(handle: str, when: datetime) -> None:
        """Record a verification wall: cool the child, retire it on the second."""
        telemetry.record(tele, "challenge", handle=handle,
                         text=drivers[handle].challenge, at_sim=when.isoformat())
        drivers[handle].challenge = None
        report.challenges += 1
        challenge_since[handle] += 1
        if challenge_since[handle] >= 2:
            sup.retire(handle, "challenged twice", now=when)
        else:
            sup.cool(handle, CHALLENGE_COOL_MIN, now=when)
        note_skip("challenge")

    def note_skip(why: str) -> None:
        report.skipped[why] = report.skipped.get(why, 0) + 1

    try:
        for when, handle, day_i in events:
            clock.set(when)
            heartbeat(sup, when)
            persona = personas[handle]

            # restart, once, mid-run — the session must survive it
            if not restarted and when >= start + timedelta(days=restart_day):
                restarted = True
                report.restarts += 1
                for h, old in list(drivers.items()):
                    was = old.signed_in
                    old.stop()
                    new = FakeDriver(clock=clock, inject=inject)
                    new._expiry_fired = old._expiry_fired
                    new.pending = list(old.pending)
                    new.drift_remaining = old.drift_remaining
                    new.start(old.profile_dir or str(root / "profiles" / h), old.proxy_url or "", True)
                    new.signed_in = was
                    drivers[h] = new
                telemetry.record(tele, "restart", children=len(drivers))

            # outage window: degrade on the way in, recover on the way out
            if not outage_done and outage_open is None and when >= start + timedelta(days=float(outage[0])):
                sup.degrade("worker outage", now=when)
                outage_open = {"start": when.isoformat(), "end": None,
                               "recovered": False, "children_blocked": []}
                report.degraded_windows.append(outage_open)
                telemetry.record(tele, "degraded", reason="worker outage",
                                 until=(start + timedelta(days=float(outage[1]))).isoformat())
            if outage_open is not None and not outage_done and when >= start + timedelta(days=float(outage[1])):
                sup.recover(now=when)
                outage_open["end"] = when.isoformat()
                outage_open["recovered"] = True
                outage_done = True
                telemetry.record(tele, "recovered", reason="worker back")

            runnable, why = sup.can_run(handle, now=when)
            if not runnable:
                if outage_open is not None and not outage_done and handle not in outage_open["children_blocked"]:
                    outage_open["children_blocked"].append(handle)
                note_skip(why.split(":")[0])
                continue

            worker = len(report.holds) % 2
            store = leases[worker]
            if not store.acquire(handle, LEASE_TTL_S, meta={"day": day_i, "worker": worker}):
                report.lease_conflicts += 1
                note_skip("lease held")
                continue

            hold_from = clock.now()
            try:
                drv = driver_for(handle)

                # a cold session: re-login once, then stay out of the composer
                snap = drv.snapshot()
                if not snap["signed_in"]:
                    drv.goto(LOGIN_URL)
                    drv.find("sign in")
                    drv.click("sign in")
                    drv.type_plan(typing_mod.plan(persona.handle, persona))
                    drv.key("enter")
                    report.relogins += 1
                    telemetry.record(tele, "session", handle=handle, ok=False, relogin=True,
                                     at_sim=when.isoformat())
                    if drv.in_cooldown():
                        note_skip("login cooldown")
                        continue
                if drv.challenge and is_challenge(drv.challenge):
                    wall(handle, when)
                    continue

                # the composer step, which is the one that drifts
                try:
                    drv.find(COMPOSER)
                except DriverError:
                    if COMPOSER not in report.quarantined_steps:
                        report.quarantined_steps.append(COMPOSER)
                        telemetry.record(tele, "quarantine", step=COMPOSER, handle=handle)
                    note_skip("step quarantined")
                    continue

                # compose until the validators are quiet
                used = [t for t in links_used[handle] if when - t <= timedelta(days=7)]
                links_used[handle] = used
                prev = history[handle][-1].text if history[handle] else ""
                flat = not voice_seen[handle]
                slot = getattr(persona, "link_slot", None)
                is_bad = drafted < broken
                draft: Draft | None = None
                blocked_text = ""
                blocked_why = ""
                for _attempt in range(12):
                    rng = random.Random(f"{seed}:{handle}:{when.isoformat()}:{_attempt}")
                    text = _compose(persona, rng, prev, force_voice=flat)
                    links = []
                    if (slot and len(used) < persona.links_per_week
                            and rng.random() < 0.15):
                        links = [slot]
                    candidate = Draft(text=text, kind="post", links=links)
                    bad = validators.validate(candidate, persona, [d.text for d in history[handle]],
                                              len(used), when)
                    bad += validators.enforce_voice(history[handle] + [candidate], persona)
                    if is_bad and not blocked_text:
                        # one deliberate defect per broken draft: the validators
                        # must catch it, and the corrected text must still post
                        stunted = Draft(text=_overlong(candidate.text, persona),
                                        kind="post", links=links)
                        why = validators.validate(
                            stunted, persona, [d.text for d in history[handle]], len(used), when)
                        if why:
                            blocked_text, blocked_why = stunted.text, why[0]
                    if not bad:
                        draft = candidate
                        break
                drafted += 1
                if blocked_text:
                    report.violations_blocked += 1
                    telemetry.record(tele, "blocked", handle=handle, text=blocked_text,
                                     why=blocked_why, at_sim=when.isoformat())
                if draft is None:
                    note_skip("blocked by validator")
                    continue

                keys = typing_mod.plan(draft.text, persona)
                gaps = [b.t - a.t for a, b in zip(keys, keys[1:])]
                pasted = bool(draft.links) or random.Random(f"{seed}:{handle}:{when.isoformat()}:paste").random() < 0.2

                drv.click(COMPOSER)
                if pasted:
                    drv.paste(draft.text)
                else:
                    drv.type_plan(keys)
                got = drv.buffer
                if got != draft.text:
                    raise DriverError(
                        f"composer text does not match the draft: {got!r} != {draft.text!r}")
                drv.key("cmd+enter")
                if drv.challenge and is_challenge(drv.challenge):
                    wall(handle, when)
                    continue
                posted_at = clock.now()

                history[handle].append(draft)
                history[handle] = history[handle][-HISTORY_N:]
                if draft.links:
                    links_used[handle].append(posted_at)
                if any(p.lower() in draft.text.lower() for p in
                       list(persona.pet_phrases) + list(persona.opinions)):
                    voice_seen[handle] = True

                label = random.Random(f"{seed}:{handle}:{posted_at.isoformat()}:label").choices(
                    LABELS, weights=(45, 25, 15, 10, 5))[0]
                report.posts += 1
                report.per_child_posts[handle] += 1
                day_posts[(handle, day_i)] += 1
                if pasted:
                    report.pasted_posts += 1
                else:
                    report.typed_posts += 1
                report.labels[handle][label] = report.labels[handle].get(label, 0) + 1
                intervals[handle].extend(gaps)

                telemetry.record(tele, "post", handle=handle, text=draft.text,
                                 chars=len(draft.text), paste=pasted, label=label,
                                 at_sim=posted_at.isoformat())
                telemetry.record(tele, "typing", handle=handle, iki=gaps,
                                 keystrokes=len(keys), paste=pasted)
                telemetry.record(tele, "label", handle=handle, label=label)
                telemetry.record(tele, "session", handle=handle, ok=True)
            finally:
                store.release(handle)
                report.holds.append((handle, hold_from, clock.now()))
    finally:
        for d in drivers.values():
            if d.running:
                d.stop()
        if outage_open is not None and not outage_open["recovered"]:
            sup.recover()
        sup.close()

    judge(report, personas, intervals, day_posts)
    return report


# --------------------------------------------------------------------------
# the verdict
# --------------------------------------------------------------------------
def _shape(xs: list[float]) -> dict:
    n = len(xs)
    if n < 2:
        return {"n": n, "median": float(xs[0]) if xs else 0.0, "cv": 0.0, "skew": 0.0}
    med = float(median(xs))
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    sd = var ** 0.5
    skew = sum(((x - mean) / sd) ** 3 for x in xs) / n if sd else 0.0
    return {"n": n, "median": round(med, 1), "cv": round(sd / mean, 3) if mean else 0.0,
            "skew": round(skew, 3)}


def judge(report: Report, personas, intervals, day_posts) -> Report:
    """Fill in per-child statistics and decide every §26.9 criterion.

    Every failure is one plain sentence naming the criterion it breaks, so a red
    gate tells the operator which paragraph of the masterplan failed.
    """
    report.ok = True
    report.failures = []
    report.criteria = {key: True for key, _ in CRITERIA}

    for h in report.children:
        report.iki[h] = _shape(intervals.get(h, []))
        persona = personas[h]
        band = persona.speed["median_ms"] * persona.pause_mult
        lo, hi = band * BAND_LOW, band * BAND_HIGH
        med = report.iki[h]["median"]
        report.iki[h]["band"] = [round(lo, 1), round(hi, 1)]
        if not report.iki[h]["n"] or not (lo <= med <= hi):
            report.out_of_band.append(h)
            report.fail("iki_in_band",
                        f"§26.9 IKI band: {h} median {med:.0f} ms is outside its "
                        f"{lo:.0f}-{hi:.0f} ms band")
        elif not (CV_LOW <= report.iki[h]["cv"] <= CV_HIGH):
            report.out_of_band.append(h)
            report.fail("iki_in_band",
                        f"§26.9 IKI band: {h} cv {report.iki[h]['cv']:.2f} is outside "
                        f"{CV_LOW}-{CV_HIGH} — a fixed-delay smell the median alone "
                        f"cannot catch")
        elif report.iki[h]["skew"] <= 0:
            report.out_of_band.append(h)
            report.fail("iki_in_band",
                        f"§26.9 IKI band: {h} skew {report.iki[h]['skew']:.2f} is not "
                        f"right-skewed — the pauses are symmetric, which no human "
                        f"typing produces")

        days_seen = {d for (hh, d) in day_posts if hh == h}
        report.per_child_days[h] = len(days_seen)
        first30 = list(report.labels[h].values())
        distinct = len([k for k, v in report.labels[h].items() if v])
        if distinct < 2 or sum(first30) < 2:
            report.fail("label_spread",
                        f"§26.9 label spread: {h} showed {distinct} label(s) across "
                        f"{report.per_child_posts[h]} posts, expected two")

    if report.challenges:
        report.fail("children_days_challenges",
                    f"§26.9 zero challenges: the run saw {report.challenges} challenge(s)")
    for h in report.children:
        if report.per_child_days[h] < report.days:
            report.fail("children_days_challenges",
                        f"§26.9 fourteen days: {h} posted on {report.per_child_days[h]} of "
                        f"{report.days} days")
        if not report.per_child_posts[h]:
            report.fail("children_days_challenges",
                        f"§26.9 three children: {h} never posted")
    if len(report.children) < 3:
        report.fail("children_days_challenges",
                    f"§26.9 three children: only {len(report.children)} selected")

    if report.relogins:
        report.fail("restart_without_relogin",
                    f"§26.9 restart: the run needed {report.relogins} re-login(s)")
    if report.restarts < 1:
        report.fail("restart_without_relogin",
                    "§26.9 restart: no restart happened, so nothing was survived")

    if not report.degraded_windows:
        report.fail("outage_degraded_recovered",
                    "§26.9 degraded mode: the deliberate outage never fired")
    for w in report.degraded_windows:
        if not w["recovered"]:
            report.fail("outage_degraded_recovered",
                        "§26.9 degraded mode: the outage never recovered")
        if not w["children_blocked"]:
            report.fail("outage_degraded_recovered",
                        "§26.9 degraded mode: the outage blocked no child, so nothing degraded")
    return report


def criteria_state(report: Report) -> list[dict]:
    """The §26.9 checklist, one row per item, with the sim's verdict."""
    return [{"id": key, "criterion": text, "pass": bool(report.criteria.get(key, True))}
            for key, text in CRITERIA]


def driver_contract_ok(driver=None) -> bool:
    """True when the object satisfies ``drivers.base.Driver`` (runtime protocol)."""
    return isinstance(driver if driver is not None else FakeDriver(), Driver)


__all__ = ["CRITERIA", "DEFAULT_CHILDREN", "FakeDriver", "Report", "SimClock",
           "criteria_state", "driver_contract_ok", "judge", "run_pilot"]
