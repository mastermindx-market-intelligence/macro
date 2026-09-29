#!/usr/bin/env python3
"""Launchd wrapper for the fleet worktree GC — plumbing only, policy never.

WHY A WRAPPER EXISTS AT ALL (2026-08-13). The canonical plist used to invoke
``__REPO_ROOT__/scripts/worktree_gc.py`` with the primary checkout's own config.
Two facts broke that quietly:

  * NOTHING UPDATES THE PRIMARY. It is routinely occupied, dirty, or parked on
    an old commit (house law: sessions must never touch its git state). So the
    operator's arming ratification — a config change merged to MAIN — would
    never reach the launchd job: it would sweep report-only forever, silently,
    while the roots regrew. The first install attempt failed on exactly this
    class of assumption (a repo path that did not exist at the referenced
    vintage).
  * DRIFT IS INVISIBLE. A stale script copy at least fails loudly; a stale
    CONFIG simply makes conservative decisions with no signal that policy and
    practice have diverged.

So this wrapper re-extracts BOTH the tool and the config from ``origin/main``
on every run. The primary checkout serves only as the GIT VANTAGE POINT — the
place worktrees are registered and refs are fetched — which is the one role it
cannot be stale at. Most drift directions in the extracted pair are conservative
(worktree_gc.py is fail-closed at every gate: locked, dirty, unpushed, open-PR,
live-process, young, outside-roots), and a host that cannot READ origin/main
refuses outright: for a deleter, blind means stop.

NOT ALL OF THEM, since 2026-09-29. `human_driven_roots` is a PROTECTIVE key, so
for it an older policy means LESS protection, not more — the direction reverses.
The exposure is bounded, because refs only advance and a fetch that fails falls
back to the last-known origin/main rather than to nothing: once one successful
fetch has seen a deny-list entry, no later staleness can drop it. But during the
window before that first fetch the protection is simply absent, which is why the
protective half of a change must land in an EARLIER commit than the half that
makes deletion reach further.

INSTALLED TO A HOST PATH (~/Library/Application Support/macro-worktree-gc/) by
scripts/install_worktree_gc_launchd.sh, not run from a checkout — the wrapper
itself is the only file that has to be somewhere stable, and it carries no
policy: policy lives on origin/main, which is re-read live.

macOS TCC NOTE. The repo lives under ~/Documents, which macOS shields from
background processes. Launchd jobs get no consent prompt — they just get
``Operation not permitted``. One-time grant required (System Settings →
Privacy & Security → Full Disk Access → add ``/usr/bin/python3``); until it is
granted, every run fail-closes with the message below and deletes nothing.

Stdlib-only, like the tool it launches — no venv, no repo imports.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path("/Users/chriswong/Documents/Cluade/Macro Dashboard")
GIT_TIMEOUT_S = 120
RUN_TIMEOUT_S = 3000   # the sweep walks ~200 trees with per-tree git reads
RECEIPT = Path.home() / "Library/Logs/macro_worktree_gc/last_attempt.json"

# DELIBERATELY NOT RAISED (2026-09-29). Of 13 recorded timeout tracebacks, 9 hit
# RUN_TIMEOUT_S and 4 hit GIT_TIMEOUT_S — so the SWEEP cap is the dominant one and is where
# a future measurement should be aimed. It is still not raised here: a successful sweep
# finishes in ~9 minutes, so a run that exceeds 50 is ~5x slower rather than marginally
# over, and a bigger number would paper over whatever makes it slow. What was actually
# missing is that a timeout said so NOWHERE a reader looks; the receipt below records stage
# and elapsed on every path, which is what makes the NEXT timeout diagnosable rather than
# merely repeated.


def _git(*args: str) -> "subprocess.CompletedProcess[bytes]":
    """Never raise. A timeout comes back as rc=124 so the CALLERS' error paths run.

    This is the defect that made this wrapper's graceful handling unreachable (measured
    2026-09-29). The fetch's "proceeding on last-known origin/main" fallback and the
    fail-closed refusal on an unreadable policy file were both written correctly, and
    NEITHER could ever execute: a 120 s timeout raised straight out of main() before any
    returncode was consulted, so the run died with a traceback instead of the reasoned
    refusal its author wrote. 4 of the 13 recorded tracebacks are exactly this path; the
    other 9 are the sweep's own cap, handled in main().

    Why a git read here can take minutes at all: the clone is a `blob:none` promisor, so
    `git show origin/main:<path>` FETCHES OVER THE NETWORK whenever that blob is cold — and
    the primary is the one checkout nothing ever warms. The wrapper's own anti-staleness
    design (re-read policy from origin/main every run) is what puts a network round trip on
    the critical path. Returning rc=124 keeps that fail-closed, which for a deleter is the
    correct direction: blind means stop, loudly.
    """
    try:
        return subprocess.run(("git", "-C", str(REPO), *args),
                              capture_output=True, timeout=GIT_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=("git", *args), returncode=124, stdout=b"",
            stderr=("git %s timed out after %ds" % (" ".join(args), GIT_TIMEOUT_S)).encode())


def _receipt(stage: str, status: str, detail: str, started: dt.datetime) -> None:
    """Record THIS attempt, on every exit path including the failing ones.

    `last_run.json` is written by the tool and only when a sweep completes, so its name is a
    liar by omission: after a failed run it still holds the last SUCCESSFUL sweep, and any
    monitor built on it reads an old success as today's health. Measured 2026-09-29: 15 of 45
    recorded runs never reached a completion line, and the sole trace of any of them was a
    traceback in launchd.err.log — no ledger row, no json, and `launchctl list` showing a
    bare `1`. An armed deleter that no-ops one day in three has to say so where something
    reads. This file is that place, and it never overwrites `last_run.json`, whose meaning
    (last COMPLETED sweep) other tooling depends on.
    """
    elapsed = (dt.datetime.now(dt.timezone.utc) - started).total_seconds()
    print(f"attempt: stage={stage} status={status} elapsed={elapsed:.1f}s {detail}", flush=True)
    try:
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps({
            "started": started.isoformat(timespec="seconds"),
            "elapsed_s": round(elapsed, 1),
            "stage": stage,
            "status": status,
            "detail": detail,
            "git_timeout_s": GIT_TIMEOUT_S,
            "run_timeout_s": RUN_TIMEOUT_S,
        }, indent=2) + "\n")
    except OSError as exc:
        # The receipt is diagnostics, never a gate: a deleter must not fail to refuse
        # because it could not write a log line.
        print(f"(could not write {RECEIPT}: {exc})", flush=True)


def main() -> int:
    started = dt.datetime.now(dt.timezone.utc)
    print(f"== worktree-gc {started.isoformat(timespec='seconds')} ==", flush=True)
    probe = _git("rev-parse", "--git-dir")
    if probe.returncode != 0:
        detail = probe.stderr.decode(errors="replace").strip()
        print(f"cannot read the primary checkout ({detail!r}).", flush=True)
        if "not permitted" in detail.lower():
            print("This is the macOS TCC wall: grant Full Disk Access to "
                  "/usr/bin/python3 (System Settings → Privacy & Security), "
                  "then `launchctl kickstart` this job to verify.", flush=True)
        elif probe.returncode == 124:
            print("The primary did not answer within GIT_TIMEOUT_S. It is routinely occupied\n"
                  "by other sessions and the clone is a blob:none promisor, so a read here\n"
                  "can wait on a lock or on the network. Refusing is correct; this line\n"
                  "exists so the refusal is legible instead of a traceback.", flush=True)
        _receipt("read-primary", "refused", detail, started)
        return 1

    fetched = _git("fetch", "origin", "main", "--quiet")
    if fetched.returncode != 0:
        print("(fetch failed — proceeding on last-known origin/main)", flush=True)

    with tempfile.TemporaryDirectory(prefix="worktree-gc-") as work:
        tool = Path(work) / "worktree_gc.py"
        cfg = Path(work) / "config.json"
        for target, path in ((tool, "scripts/worktree_gc.py"),
                             (cfg, "config/worktree_gc.json")):
            shown = _git("show", f"origin/main:{path}")
            if shown.returncode != 0 or not shown.stdout:
                print(f"cannot read {path} from origin/main — refusing "
                      "(fail-closed: policy truth unavailable)", flush=True)
                _receipt("extract-policy", "refused",
                         f"{path}: {shown.stderr.decode(errors='replace').strip()[:200]}",
                         started)
                return 1
            target.write_bytes(shown.stdout)

        try:
            run = subprocess.run(
                (sys.executable, str(tool), "--apply",
                 "--repo-root", str(REPO), "--config", str(cfg),
                 "--json-out",
                 str(Path.home() / "Library/Logs/macro_worktree_gc/last_run.json")),
                timeout=RUN_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            # Nothing partial escapes: worktree_gc.py removes one tree at a time, so a
            # kill mid-sweep loses the REST of the sweep, never a half-deleted tree. The
            # cost of this timeout is therefore a silent no-op day, which is precisely
            # what the receipt is for.
            print(f"== worktree-gc TIMED OUT after {RUN_TIMEOUT_S}s — swept nothing further; "
                  "no deletions are half-applied ==", flush=True)
            _receipt("sweep", "timeout", f"exceeded RUN_TIMEOUT_S={RUN_TIMEOUT_S}", started)
            return 3
    print(f"== worktree-gc done rc={run.returncode} ==", flush=True)
    _receipt("sweep", "completed" if run.returncode == 0 else "tool-nonzero",
             f"worktree_gc.py rc={run.returncode}", started)
    return run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
