"""Synthetic harness regression gate; no runtime or live acceptance.

sim, criteria and drill evaluate the historical model with FakeDriver.
Exit 0 concerns model checks only; exit 1 is a model failure and exit 2 is
a model exception. Every output labels synthetic evidence, unavailable runtime
binding and an unsatisfied live gate. See GATE.md for the prospective real scope."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from . import pilot_sim, telemetry
from .pilot_sim import CRITERIA, DEFAULT_CHILDREN, START, run_pilot

EXIT_OK, EXIT_FAILED, EXIT_HARNESS = 0, 1, 2

#: The drill's child. A conversation child, so a degraded mode *pauses* it and
#: a wall on it is visible in the shortening post history.
DRILL_CHILD = "harperbuilds"


def _fresh(children=None, **kwargs) -> pilot_sim.Report:
    store = kwargs.pop("store_dir", None) or tempfile.mkdtemp(prefix="xg-gate-")
    return run_pilot(children or DEFAULT_CHILDREN, 14, seed=kwargs.pop("seed", 7),
                     store_dir=store, inject=kwargs.pop("inject", None), **kwargs)


def _emit(doc: dict) -> None:
    doc = {**doc, "evidence_scope": "synthetic_model",
           "runtime_binding_available": False, "live_gate_satisfied": False}
    json.dump(doc, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


# --------------------------------------------------------------------------
# sim
# --------------------------------------------------------------------------
def cmd_sim(args) -> int:
    report = _fresh(seed=args.seed, store_dir=args.store_dir)
    doc = report.to_dict()
    _emit(doc)
    return EXIT_OK if report.ok else EXIT_FAILED


# --------------------------------------------------------------------------
# criteria
# --------------------------------------------------------------------------
def cmd_criteria(args) -> int:
    report = _fresh(seed=args.seed, store_dir=args.store_dir)
    rows = pilot_sim.criteria_state(report)
    doc = {
        "spec": "research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md §26.9",
        "evidence": {"posts": report.posts, "challenges": report.challenges,
                     "relogins": report.relogins,
                     "degraded_windows": len(report.degraded_windows),
                     "restarts": report.restarts,
                     "telemetry": report.telemetry},
        "ok": report.ok,
        "criteria": rows,
        "failures": report.failures,
    }
    _emit(doc)
    return EXIT_OK if report.ok else EXIT_FAILED


# --------------------------------------------------------------------------
# drill
# --------------------------------------------------------------------------
def _drill_challenge() -> dict:
    """A wall on the third write: the child must cool and the run must go on."""
    report = _fresh([DRILL_CHILD], inject={"challenge_after_n": 3})
    cooled = report.skipped.get("cooling until", 0) + report.skipped.get("challenge", 0)
    return {
        "drill": "challenge",
        "expect": "one wall counted, child withheld, remaining days still posted",
        "pass": bool(report.challenges == 1 and cooled and report.posts > 0
                     and report.per_child_days[DRILL_CHILD] >= 1),
        "challenges": report.challenges,
        "posts_after": report.posts,
        "days_for_child": report.per_child_days[DRILL_CHILD],
    }


def _drill_two_walls() -> dict:
    """A second wall retires the child rather than cooling it forever."""
    report = _fresh([DRILL_CHILD], inject={"challenge_after_n": [2, 4]})
    return {
        "drill": "retire-on-second-wall",
        "expect": "two walls, second one retires the child",
        "pass": bool(report.challenges == 2
                     and report.per_child_days[DRILL_CHILD] < report.days),
        "challenges": report.challenges,
        "days_for_child": report.per_child_days[DRILL_CHILD],
    }


def _drill_session() -> dict:
    """A cold cookie jar: exactly one re-login, and no write inside the cooldown."""
    when = START + timedelta(days=3, hours=9)
    report = _fresh([DRILL_CHILD], inject={"expire_session_at": when})
    posts = [datetime.fromisoformat(r["at_sim"]) for r in telemetry.rows(report.telemetry)
             if r.get("kind") == "post" and r.get("handle") == DRILL_CHILD
             and r.get("at_sim")]
    after = [t for t in posts if t >= when]
    wait = (min(after) - when).total_seconds() if after else -1.0
    return {
        "drill": "session-expiry",
        "expect": "exactly one re-login, no post inside the 120 s cooldown",
        "pass": bool(report.relogins == 1 and report.skipped.get("login cooldown", 0) >= 1
                     and wait >= pilot_sim.LOGIN_COOLDOWN_S),
        "relogins": report.relogins,
        "cooldown_skips": report.skipped.get("login cooldown", 0),
        "first_post_after_s": wait,
        "posts_after_expiry": len(after),
    }


def _drill_outage() -> dict:
    """The worker dies mid-run: broadcast drops, lead and conversation survive."""
    report = _fresh()
    windows = report.degraded_windows
    blocked = windows[0]["children_blocked"] if windows else []
    recovered = bool(windows and windows[0]["recovered"])
    start = datetime.fromisoformat(windows[0]["start"]) if windows else None
    after = [h for h in report.holds if start and h[1] > start]
    return {
        "drill": "worker-outage",
        "expect": "broadcast child blocked, degradation reported, recovery, work resumes",
        "pass": bool(blocked == ["desk.and.dusk"] and recovered
                     and report.skipped.get("degraded", 0) > 0 and after),
        "blocked": blocked,
        "recovered": recovered,
        "degraded_skips": report.skipped.get("degraded", 0),
    }


def _drill_drift() -> dict:
    """A drifted locator: the step is quarantined, the child is not retired."""
    report = _fresh([DRILL_CHILD], inject={"selector_drift_step": 1})
    return {
        "drill": "selector-drift",
        "expect": "composer quarantined once, child still runnable afterwards",
        "pass": bool(report.quarantined_steps
                     and report.skipped.get("step quarantined", 0) == 1
                     and report.per_child_days[DRILL_CHILD] >= report.days - 1),
        "quarantined": report.quarantined_steps,
        "days_for_child": report.per_child_days[DRILL_CHILD],
    }


DRILLS = (_drill_challenge, _drill_two_walls, _drill_session, _drill_outage, _drill_drift)


def cmd_drill(args) -> int:
    rows = [d() for d in DRILLS]
    ok = all(r["pass"] for r in rows)
    _emit({"ok": ok, "drills": rows})
    return EXIT_OK if ok else EXIT_FAILED


# --------------------------------------------------------------------------
# entry
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gate", description=(__doc__ or "pilot gate").splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, help_ in (
            ("sim", cmd_sim, "run the 14-day simulation and print the evidence"),
            ("criteria", cmd_criteria, "print model criteria; never a live acceptance result"),
            ("drill", cmd_drill, "run the deliberate-failure drills")):
        sp = sub.add_parser(name, help=help_)
        sp.set_defaults(fn=fn)
        if name != "drill":
            sp.add_argument("--seed", type=int, default=7)
            sp.add_argument("--store-dir", default=None,
                            help="keep the sqlite/JSONL evidence in this directory")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.fn(args))
    except Exception as exc:  # a crash must not look like a red gate
        _emit({"error": f"{type(exc).__name__}: {exc}", "cmd": args.cmd})
        return EXIT_HARNESS


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["EXIT_FAILED", "EXIT_HARNESS", "EXIT_OK", "CRITERIA", "build_parser", "main"]
Path  # re-exported for callers that monkeypatch a store directory
