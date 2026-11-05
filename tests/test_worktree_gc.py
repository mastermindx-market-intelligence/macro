"""tests/test_worktree_gc.py — hermetic tests for the fleet worktree sweeper.

COVERAGE
  Classification (fail-closed lattice):
   1. clean + old + HEAD ancestor of origin/main → SAFE_MERGED (ancestor proof)
   2. squash-merge: merged-PR proof requires exact headRefOid match → SAFE_MERGED;
      a head that moved past the merged oid stays UNPUSHED
   3. dirty worktree → DIRTY (kept)
   4. unpushed unique commits → UNPUSHED (kept)
   5. fresh activity → RECENT (kept) — age gate reads STRONG signals only
      (reflog entry epochs, session transcript mtimes); neither observer
      stamps on index/HEAD/dir mtimes nor a repo-global reflog-expire sweep
      of logs/HEAD file mtimes may fake recency (both regression-pinned)
   6. `git worktree lock` → LOCKED (kept)
   7. live process cwd inside → LIVE_PROC (kept)
   8. open PR → OPEN_PR (kept) even when clean + old + pushed
   9. pushed + PR states UNAVAILABLE (None) → UNPUSHED (fail-closed);
      pushed + known-empty PR map → SAFE_REMOTE
  10. orphan directory (no registration) → ORPHAN, never deleted by default
  11. process scan unavailable → ERROR verdicts and apply refuses even armed

  Arming / apply:
  12. --apply with armed:false → exit 2, nothing deleted (report still renders)
  13. --apply armed → deletes only SAFE_*, prunes registration, deletes the
      local branch on the merged proof; DIRTY / UNPUSHED / LOCKED survive
  14. max_delete_per_run caps deletions

  Human-driven protection (purely protective; adds refusals only):
  18. a `human_driven_roots` entry beats a VALID landed proof — a tree that is clean,
      old, in scope and an ancestor of origin/main classifies PROTECTED, never SAFE_*
  19. an ARMED apply deletes an ordinary SAFE tree in the same run while the protected
      one survives on disk AND stays registered
  20. the deletion belt refuses a protected path even when a verdict says SAFE — the
      two gates are independent, so removing either one leaves the other standing
  21. the report STATES its protection reach, says NONE CONFIGURED when the key is
      absent, and says so explicitly when a configured list matches nothing (an
      unmounted volume and a mis-spelled path are indistinguishable otherwise)
  22. a config that OMITS `human_driven_roots` inherits the built-in floor rather than
      an empty list -- load_config merges a file over the defaults, so a pre-existing
      config supplies its own `armed: true` while an absent protective key falls back
      to the defaults, resolving arming and protection from different schema eras
  23. an EXPLICIT empty list still overrides that floor -- the default is a floor, not
      a seizure of policy authority from an operator who deliberately emptied it
  24. the report NAMES the config file its policy came from, and flags the implicit
      primary-checkout path -- without it, "NONE configured" is unfalsifiable by its
      reader: it reads as a fact about the fleet when it may be a fact about which
      checkout supplied the config

  Reach (an instrument must state how much it looked at):
  15. the rendered report prints `reach: checked N of M registered worktrees`,
      and names how many sat outside `roots` and were never examined
  16. absent reach metadata OMITS the line rather than inventing a count
  17. apply refusals are PRINTED, grouped by reason — they were counted into
      an exit code and never shown, so `deleted=0 errors=688` was
      indistinguishable from a healthy run with nothing to do

All git activity runs against throwaway repos under tmp_path with a local
bare "origin" — no network, no gh (PR states injected via --pr-states-file),
no real ledger writes (LEDGER_DIR monkeypatched).
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from scripts import worktree_gc as wgc


# ── scaffolding ──────────────────────────────────────────────────────────────

def _git(cwd: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    assert p.returncode == 0, f"git {' '.join(args)} failed: {p.stderr}"
    return p.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> dict:
    """Primary checkout with a local bare origin and a .claude/worktrees root."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)],
                   capture_output=True, check=True)
    primary = tmp_path / "primary"
    primary.mkdir()
    _git(primary, "init", "-b", "main")
    _git(primary, "config", "user.email", "t@t")
    _git(primary, "config", "user.name", "t")
    (primary / "README.md").write_text("hello\n")
    _git(primary, "add", "-A")
    _git(primary, "commit", "-m", "init")
    _git(primary, "remote", "add", "origin", str(origin))
    _git(primary, "push", "-u", "origin", "main")
    (primary / ".claude" / "worktrees").mkdir(parents=True)
    return {"primary": primary, "origin": origin, "root": primary / ".claude" / "worktrees"}


def _add_worktree(repo: dict, name: str, branch: str | None = None) -> Path:
    wt = repo["root"] / name
    args = ["worktree", "add"]
    if branch:
        args += ["-b", branch]
    args += [str(wt), "main"]
    _git(repo["primary"], *args)
    return wt


def _commit_in(wt: Path, fname: str = "extra.txt") -> str:
    (wt / fname).write_text("x\n")
    _git(wt, "add", "-A")
    _git(wt, "config", "user.email", "t@t")
    _git(wt, "config", "user.name", "t")
    _git(wt, "commit", "-m", f"add {fname}")
    return _git(wt, "rev-parse", "HEAD")


def _age(repo: dict, wt: Path, days: float = 30.0) -> None:
    """Backdate every activity source the age probe reads.

    The reflog is aged by rewriting each entry's EMBEDDED epoch — the probe
    reads entry content, not the file mtime (repo-global `reflog expire`
    sweeps make the mtime meaningless; see _reflog_last_epoch).
    """
    old = time.time() - days * 86400
    gitdir = Path(_git(wt, "rev-parse", "--absolute-git-dir"))
    for p in [wt, wt / ".git", gitdir / "HEAD", gitdir / "index"]:
        if p.exists():
            os.utime(p, (old, old))
    reflog = gitdir / "logs" / "HEAD"
    if reflog.exists():
        out = []
        for line in reflog.read_text().splitlines():
            head, sep, msg = line.partition("\t")
            toks = head.split()
            if len(toks) >= 2:
                toks[-2] = str(int(old))
            out.append(" ".join(toks) + sep + msg)
        reflog.write_text("\n".join(out) + "\n")
        os.utime(reflog, (old, old))


def _write_config(tmp_path: Path, **overrides) -> Path:
    cfg = {"armed": False, "min_age_days": 7, "include_open_pr": False,
           "include_orphans": False, "delete_local_branches": True,
           "max_delete_per_run": 200, "pr_limit": 50,
           "roots": [".claude/worktrees"]}
    cfg.update(overrides)
    p = tmp_path / "gc_config.json"
    p.write_text(json.dumps(cfg))
    return p


def _pr_file(tmp_path: Path, states: dict) -> Path:
    p = tmp_path / "pr_states.json"
    p.write_text(json.dumps(states))
    return p


def _run_main(repo: dict, tmp_path: Path, monkeypatch, *, cfg: Path | None = None,
              pr_states: dict | None = None, apply: bool = False,
              procs: dict | None = None, extra: list[str] | None = None) -> tuple[int, dict]:
    """Invoke wgc.main() hermetically; returns (exit_code, json payload)."""
    monkeypatch.setattr(wgc, "LEDGER_DIR", tmp_path / "ledger")
    monkeypatch.setattr(wgc, "session_activity_mtime", lambda path: None)
    if procs is None:
        monkeypatch.setattr(wgc, "proc_cwd_map", lambda roots: {})
    else:
        monkeypatch.setattr(wgc, "proc_cwd_map", lambda roots: procs)
    out = tmp_path / "out.json"
    argv = ["--repo-root", str(repo["primary"]),
            "--config", str(cfg or _write_config(tmp_path)),
            "--no-gh", "--no-sizes", "--json-out", str(out)]
    if pr_states is not None:
        argv += ["--pr-states-file", str(_pr_file(tmp_path, pr_states))]
        argv.remove("--no-gh")
    if apply:
        argv.append("--apply")
    if extra:
        argv += extra
    rc = wgc.main(argv)
    return rc, json.loads(out.read_text())


def _verdict(payload: dict, name: str) -> dict:
    for w in payload["worktrees"]:
        if w["name"] == name:
            return w
    raise AssertionError(f"worktree {name} not in payload")


# ── classification ───────────────────────────────────────────────────────────

def test_ancestor_of_main_clean_old_is_safe_merged(repo, tmp_path, monkeypatch):
    wt = _add_worktree(repo, "done", branch="claude/done")
    _age(repo, wt)
    rc, payload = _run_main(repo, tmp_path, monkeypatch)
    assert rc == 0
    w = _verdict(payload, "done")
    assert w["verdict"] == "SAFE_MERGED"
    assert "ancestor" in w["proof"]


def test_squash_merge_needs_exact_oid_match(repo, tmp_path, monkeypatch):
    wt = _add_worktree(repo, "squashed", branch="claude/squashed")
    head = _commit_in(wt)
    _age(repo, wt)
    # PR merged at exactly this head → safe even though ancestry can't see it.
    rc, payload = _run_main(repo, tmp_path, monkeypatch, pr_states={
        "claude/squashed": {"state": "MERGED", "number": 42, "headRefOid": head}})
    assert _verdict(payload, "squashed")["verdict"] == "SAFE_MERGED"
    # Same PR but the local head moved past the merged oid → fail closed.
    head2 = _commit_in(wt, "after_merge.txt")
    assert head2 != head
    _age(repo, wt)
    rc, payload = _run_main(repo, tmp_path, monkeypatch, pr_states={
        "claude/squashed": {"state": "MERGED", "number": 42, "headRefOid": head}})
    assert _verdict(payload, "squashed")["verdict"] == "UNPUSHED"


def test_dirty_is_kept(repo, tmp_path, monkeypatch):
    wt = _add_worktree(repo, "dirty", branch="claude/dirty")
    (wt / "scratch.txt").write_text("uncommitted\n")
    _age(repo, wt)
    _, payload = _run_main(repo, tmp_path, monkeypatch)
    assert _verdict(payload, "dirty")["verdict"] == "DIRTY"


def test_unpushed_commits_are_kept(repo, tmp_path, monkeypatch):
    wt = _add_worktree(repo, "unpushed", branch="claude/unpushed")
    _commit_in(wt)
    _age(repo, wt)
    _, payload = _run_main(repo, tmp_path, monkeypatch)
    assert _verdict(payload, "unpushed")["verdict"] == "UNPUSHED"


def test_recent_activity_is_kept(repo, tmp_path, monkeypatch):
    _add_worktree(repo, "fresh", branch="claude/fresh")
    _, payload = _run_main(repo, tmp_path, monkeypatch)
    assert _verdict(payload, "fresh")["verdict"] == "RECENT"


def test_observer_stamps_do_not_fake_recency(repo, tmp_path, monkeypatch):
    """Fleet dashboards running plain `git status` rewrite gitdir/index, and
    Finder/.DS_Store bumps the worktree dir mtime — observation, not activity.
    Measured on the Studio: 137/143 dead trees were pinned "fresh" purely by
    such file mtimes while reflog entries and transcripts sat weeks old.
    Only STRONG signals may gate."""
    wt = _add_worktree(repo, "observed", branch="claude/observed")
    _age(repo, wt)
    gitdir = Path(_git(wt, "rev-parse", "--absolute-git-dir"))
    now = time.time()
    for p in [wt, wt / ".git", gitdir / "HEAD", gitdir / "index"]:
        if p.exists():
            os.utime(p, (now, now))
    _, payload = _run_main(repo, tmp_path, monkeypatch)
    w = _verdict(payload, "observed")
    assert w["verdict"] == "SAFE_MERGED", f"observer stamps misread as {w['verdict']}"
    assert w["age_days"] > 7


def test_reflog_file_mtime_sweep_does_not_fake_recency(repo, tmp_path, monkeypatch):
    """Repo-global `reflog expire` rewrites every worktree's logs/HEAD in one
    sweep (measured stamping all 186 Studio trees at 2026-08-04 15:38:24).
    A fresh reflog FILE mtime over old entry epochs must not read as activity."""
    wt = _add_worktree(repo, "expired", branch="claude/expired")
    _age(repo, wt)
    gitdir = Path(_git(wt, "rev-parse", "--absolute-git-dir"))
    now = time.time()
    os.utime(gitdir / "logs" / "HEAD", (now, now))  # the maintenance sweep
    _, payload = _run_main(repo, tmp_path, monkeypatch)
    w = _verdict(payload, "expired")
    assert w["verdict"] == "SAFE_MERGED", f"stale tree misread as {w['verdict']}"
    assert w["age_days"] > 7


def test_locked_is_kept(repo, tmp_path, monkeypatch):
    wt = _add_worktree(repo, "pinned", branch="claude/pinned")
    _git(repo["primary"], "worktree", "lock", "--reason", "session parked", str(wt))
    _age(repo, wt)
    _, payload = _run_main(repo, tmp_path, monkeypatch)
    w = _verdict(payload, "pinned")
    assert w["verdict"] == "LOCKED"
    assert "session parked" in " ".join(w["reasons"])


def test_live_process_is_kept(repo, tmp_path, monkeypatch):
    wt = _add_worktree(repo, "busy", branch="claude/busy")
    _age(repo, wt)
    procs = {str(wt.resolve()): ["123:zsh"]}
    _, payload = _run_main(repo, tmp_path, monkeypatch, procs=procs)
    w = _verdict(payload, "busy")
    assert w["verdict"] == "LIVE_PROC"
    assert w["procs"] == ["123:zsh"]


def test_open_pr_is_kept_even_when_pushed_and_old(repo, tmp_path, monkeypatch):
    wt = _add_worktree(repo, "inflight", branch="claude/inflight")
    _commit_in(wt)
    _git(wt, "push", "-u", "origin", "claude/inflight")
    _age(repo, wt)
    _, payload = _run_main(repo, tmp_path, monkeypatch, pr_states={
        "claude/inflight": {"state": "OPEN", "number": 7, "headRefOid": ""}})
    w = _verdict(payload, "inflight")
    assert w["verdict"] == "OPEN_PR"
    assert "PR #7" in " ".join(w["reasons"])


def test_pushed_fail_closed_without_pr_states_safe_remote_with(repo, tmp_path, monkeypatch):
    wt = _add_worktree(repo, "pushed", branch="claude/pushed")
    _commit_in(wt)
    _git(wt, "push", "-u", "origin", "claude/pushed")
    _age(repo, wt)
    # PR states unavailable (--no-gh, no file) → cannot rule out an open PR.
    _, payload = _run_main(repo, tmp_path, monkeypatch)
    assert _verdict(payload, "pushed")["verdict"] == "UNPUSHED"
    # Known-complete (empty) PR map → provably no open PR → SAFE_REMOTE.
    _, payload = _run_main(repo, tmp_path, monkeypatch, pr_states={})
    w = _verdict(payload, "pushed")
    assert w["verdict"] == "SAFE_REMOTE"
    assert "origin/claude/pushed" in w["proof"]


def test_orphan_dir_reported_not_deleted(repo, tmp_path, monkeypatch):
    orphan = repo["root"] / "husk"
    orphan.mkdir()
    (orphan / "junk.bin").write_text("x")
    old = time.time() - 30 * 86400
    os.utime(orphan, (old, old))
    cfg = _write_config(tmp_path, armed=True)
    rc, payload = _run_main(repo, tmp_path, monkeypatch, cfg=cfg, apply=True)
    assert _verdict(payload, "husk")["verdict"] == "ORPHAN"
    assert orphan.exists(), "orphan must survive apply while include_orphans=false"


def test_proc_scan_failure_fails_closed(repo, tmp_path, monkeypatch):
    wt = _add_worktree(repo, "done", branch="claude/done")
    _age(repo, wt)
    monkeypatch.setattr(wgc, "LEDGER_DIR", tmp_path / "ledger")
    monkeypatch.setattr(wgc, "session_activity_mtime", lambda path: None)
    monkeypatch.setattr(wgc, "proc_cwd_map", lambda roots: None)
    out = tmp_path / "out.json"
    rc = wgc.main(["--repo-root", str(repo["primary"]),
                   "--config", str(_write_config(tmp_path, armed=True)),
                   "--no-gh", "--no-sizes", "--apply", "--json-out", str(out)])
    payload = json.loads(out.read_text())
    assert rc == 2
    assert _verdict(payload, "done")["verdict"] == "ERROR"
    assert wt.exists()


# ── arming / apply ───────────────────────────────────────────────────────────

def test_apply_disarmed_refuses(repo, tmp_path, monkeypatch):
    wt = _add_worktree(repo, "done", branch="claude/done")
    _age(repo, wt)
    rc, payload = _run_main(repo, tmp_path, monkeypatch, apply=True)
    assert rc == 2
    assert wt.exists()
    assert payload["apply"] is None
    assert _verdict(payload, "done")["verdict"] == "SAFE_MERGED"  # report still classified


def test_apply_armed_deletes_only_safe(repo, tmp_path, monkeypatch):
    safe = _add_worktree(repo, "safe", branch="claude/safe")
    _age(repo, safe)
    dirty = _add_worktree(repo, "dirty", branch="claude/dirty")
    (dirty / "scratch.txt").write_text("keep me\n")
    _age(repo, dirty)
    unpushed = _add_worktree(repo, "unpushed", branch="claude/unpushed")
    _commit_in(unpushed)
    _age(repo, unpushed)

    cfg = _write_config(tmp_path, armed=True)
    rc, payload = _run_main(repo, tmp_path, monkeypatch, cfg=cfg, apply=True, pr_states={})
    assert rc == 0
    assert not safe.exists()
    assert dirty.exists() and unpushed.exists()
    assert str(safe) in payload["apply"]["deleted"]
    # registration pruned, merged-proof branch deleted
    listed = _git(repo["primary"], "worktree", "list", "--porcelain")
    assert "safe" not in listed
    branches = _git(repo["primary"], "branch", "--list", "claude/safe")
    assert branches == ""
    assert (tmp_path / "ledger" / "ledger.jsonl").exists()


def test_max_delete_cap(repo, tmp_path, monkeypatch):
    for i in range(3):
        _age(repo, _add_worktree(repo, f"safe{i}", branch=f"claude/safe{i}"))
    cfg = _write_config(tmp_path, armed=True, max_delete_per_run=2)
    rc, payload = _run_main(repo, tmp_path, monkeypatch, cfg=cfg, apply=True, pr_states={})
    assert rc == 0
    assert len(payload["apply"]["deleted"]) == 2
    assert payload["apply"]["skipped_cap"] == 1
    survivors = [w for w in ("safe0", "safe1", "safe2") if (repo["root"] / w).exists()]
    assert len(survivors) == 1


# ── reach: an instrument that never states its subject count ────────────────

def test_report_states_its_reach(repo, tmp_path, monkeypatch, capsys):
    """The report a human reads must say how many worktrees it checked.

    Without this line the report is indistinguishable from one with full coverage: every verdict
    it prints is correct, and the ones it never examined are simply absent.
    """
    _add_worktree(repo, "a", branch="claude/a")
    _add_worktree(repo, "b", branch="claude/b")
    rc, payload = _run_main(repo, tmp_path, monkeypatch, pr_states={})
    assert rc == 0
    out = capsys.readouterr().out
    assert "reach: checked" in out, "the report never states its reach"
    meta = payload["meta"]
    assert f"checked {meta['in_scope']} of {meta['registered_total']}" in out


def test_reach_names_what_it_never_examined():
    """A partial scope must name the gap; full coverage must not invent one."""
    partial = wgc.reach_line({"registered_total": 804, "in_scope": 225, "orphans": 12})
    assert "225 of 804" in partial
    assert "579 outside" in partial and "never examined" in partial
    assert "12 unregistered" in partial

    full = wgc.reach_line({"registered_total": 40, "in_scope": 40, "orphans": 0})
    assert "40 of 40" in full
    assert "outside" not in full, "full coverage must not claim an out-of-scope count"


def test_reach_omitted_not_invented_without_metadata():
    """Missing metadata omits the line. A guessed coverage number is worse than none."""
    meta = {"host": "h", "ts": "t", "mode": "report", "fetch_ok": True,
            "proc_scan": True, "pr_states": "none"}
    md = wgc.render_markdown([], {"armed": False, "min_age_days": 7}, meta)
    assert "reach:" not in md
    assert "| verdict | count | GiB |" in md, "the rest of the report must still render"


def test_apply_refusals_are_printed_not_just_counted():
    """Refusals were counted into an exit code and never shown.

    Grouping is what makes printing possible at all: the measured shape on this host is hundreds
    of identical host-checkout refusals, which would bury the two real errors.
    """
    errs = [f"/Volumes/Mastermind/w{i}: refused — host checkout" for i in range(688)]
    errs += [f"/Users/x/w{i}: refused — outside configured roots" for i in range(3)]
    errs += ["/Users/x/wA: fatal: could not remove", "/Users/x/wB: permission denied"]
    rows = wgc.group_refusals(errs)

    assert any("host checkout: 688" in r for r in rows)
    assert any("outside configured roots: 3" in r for r in rows)
    # identical refusals collapse to one row each, real errors stay individually visible
    assert len(rows) == 5, rows
    assert "fatal: could not remove" in "\n".join(rows)
    assert "permission denied" in "\n".join(rows)


def test_refusal_error_list_is_capped():
    """A long error list must not become the whole report."""
    rows = wgc.group_refusals([f"/p{i}: boom {i}" for i in range(14)])
    assert rows[0].strip() == "error: 14"
    assert rows[-1].strip() == "... and 4 more"
    assert len(rows) == 12, rows


# ── human-driven protection ──────────────────────────────────────────────────

def test_human_driven_root_beats_a_valid_landed_proof(repo, tmp_path, monkeypatch):
    """The proof says the WORK is safe; deleting a checkout destroys the SESSION.

    A ChatGPT-web conversation has no process and no shell, so nothing this tool can probe
    distinguishes "finished" from "its human is about to reply". Landed is therefore necessary
    and not sufficient, and the deny-list has to outrank the proof rather than tie-break with it.
    """
    wt = _add_worktree(repo, "web-session", branch="sol/web-session")
    _age(repo, wt)
    cfg = _write_config(tmp_path, human_driven_roots=[str(repo["root"] / "web-session")])
    rc, payload = _run_main(repo, tmp_path, monkeypatch, cfg=cfg)
    assert rc == 0
    v = _verdict(payload, "web-session")
    assert v["verdict"] == "PROTECTED", v
    assert v["verdict"] not in ("SAFE_MERGED", "SAFE_REMOTE")
    assert any("human_driven_roots" in r for r in v["reasons"]), v["reasons"]


def test_armed_apply_never_deletes_a_protected_tree(repo, tmp_path, monkeypatch):
    """Same run, same proof, opposite outcomes — so the test cannot pass by doing nothing."""
    protected = _add_worktree(repo, "web-session", branch="sol/web-session")
    ordinary = _add_worktree(repo, "agent-lane", branch="claude/agent-lane")
    for wt in (protected, ordinary):
        _age(repo, wt)
    cfg = _write_config(tmp_path, armed=True,
                        human_driven_roots=[str(repo["root"] / "web-session")])
    rc, payload = _run_main(repo, tmp_path, monkeypatch, cfg=cfg, apply=True)
    assert rc == 0
    assert _verdict(payload, "web-session")["verdict"] == "PROTECTED"
    assert _verdict(payload, "agent-lane")["verdict"] in ("SAFE_MERGED", "SAFE_REMOTE")
    # The control: the sweeper really was able to delete in this run.
    assert not ordinary.exists(), "armed apply deleted nothing — the test proves nothing"
    assert protected.exists(), "an armed apply deleted a human-driven checkout"
    listing = _git(repo["primary"], "worktree", "list", "--porcelain")
    assert "web-session" in listing, "protected tree was unregistered"
    assert "agent-lane" not in listing, "the deleted tree is still registered"


def test_the_deletion_belt_refuses_a_protected_path_even_if_a_verdict_says_safe(repo, tmp_path,
                                                                               monkeypatch):
    """Defense in depth, stated as a test: the belt is not a function of the verdict.

    If the classify-side gate is ever removed, reordered, or bypassed by a new verdict, this is
    what still stands between an armed sweeper and a human's working directory.
    """
    monkeypatch.setattr(wgc, "LEDGER_DIR", tmp_path / "ledger")
    wt = _add_worktree(repo, "web-session", branch="sol/web-session")
    w = wgc.Worktree(path=wt, branch="sol/web-session")
    w.verdict = "SAFE_MERGED"          # forced: pretend the gate above never ran
    w.proof = "forced for this test"
    summary = wgc.apply_deletions(
        repo["primary"], [w], {"armed": True, "max_delete_per_run": 200,
                               "delete_local_branches": False},
        [repo["root"]], protected=[repo["root"] / "web-session"])
    assert summary["deleted"] == [], summary
    assert any("human_driven_roots" in e for e in summary["errors"]), summary["errors"]
    assert wt.exists()


def test_the_report_states_its_protection_reach(repo, tmp_path, monkeypatch, capsys):
    _add_worktree(repo, "web-session", branch="sol/web-session")
    cfg = _write_config(tmp_path, human_driven_roots=[str(repo["root"] / "web-session")])
    md = tmp_path / "report.md"
    _run_main(repo, tmp_path, monkeypatch, cfg=cfg, extra=["--md-out", str(md)])
    blob = md.read_text()
    assert "human-driven protection: 1 registration(s) held by 1 `human_driven_roots` entry" in blob
    assert "matched nothing" not in blob


def test_an_unconfigured_deny_list_says_so_rather_than_implying_protection():
    """Absent must not read like present. This is the whole finding of the previous wave."""
    line = wgc.protection_line({"protected_roots": 0, "protected": 0})
    assert "NONE configured" in line
    assert "accidents" in line or "deliberate safeguard" in line


def test_a_configured_deny_list_that_matches_nothing_says_zero():
    """An unmounted volume and a mis-spelled path produce the same 0 — so name the ambiguity."""
    line = wgc.protection_line({"protected_roots": 2, "protected": 0})
    assert "0 registration(s)" in line
    assert "matched nothing" in line
    assert "entries" in line, line


def test_protection_line_omitted_not_invented_without_metadata():
    assert wgc.protection_line({}) is None


def test_main_actually_threads_the_deny_list_into_the_deletion_belt(repo, tmp_path, monkeypatch):
    """The belt is inert unless main passes it — and the classify gate HIDES that.

    Both gates refusing independently is the design, which means a regression in either one is
    invisible from the outcome. This asserts the wiring directly: computing a protection and
    never handing it to the code that deletes is the same defect as computing a reach figure
    and printing it nowhere.
    """
    _add_worktree(repo, "web-session", branch="sol/web-session")
    cfg = _write_config(tmp_path, armed=True,
                        human_driven_roots=[str(repo["root"] / "web-session")])
    seen = {}
    real = wgc.apply_deletions

    def spy(*a, **kw):
        seen.update(kw)
        return real(*a, **kw)

    monkeypatch.setattr(wgc, "apply_deletions", spy)
    _run_main(repo, tmp_path, monkeypatch, cfg=cfg, apply=True)
    assert "protected" in seen, "main never passed protected= to the deletion belt"
    assert seen["protected"], "main passed an EMPTY protection to the belt"
    assert any("web-session" in str(p) for p in seen["protected"]), seen["protected"]


# --- a protective key absent from an older config ---------------------------------------

def test_an_absent_deny_list_key_inherits_the_floor_not_an_empty_list(tmp_path):
    """The defect this wave exists for: absence resolved to the UNPROTECTED value.

    `load_config` is dict(DEFAULT_CONFIG).update(<file>). A config written before this key
    existed therefore contributes its own `armed: true` while the deny-list falls through to
    the defaults -- arming and protection answered from different eras of the schema. That is
    not hypothetical: measured 2026-09-29, the primary checkout's config (branch `feature`,
    7,450 commits behind origin/main) loaded exactly this way, armed and unprotected.
    """
    p = tmp_path / "old.json"
    p.write_text(json.dumps({"armed": True, "roots": [".claude/worktrees"]}))
    cfg = wgc.load_config(tmp_path, str(p))
    assert cfg["armed"] is True, "fixture must reproduce the armed half"
    assert cfg["human_driven_roots"], (
        "an absent protective key resolved to an EMPTY deny-list while arming came from the "
        "file -- this is the armed-and-unprotected state")
    assert wgc.human_driven_protection([tmp_path], cfg), "the floor must survive expansion"


def test_an_explicit_empty_deny_list_still_overrides_the_floor(tmp_path):
    """A floor, not a seizure of authority: an operator who writes [] means [].

    Without this the fix would be unfalsifiable from the operator's side -- there would be no
    way to express "no deny-list" at all, and a default that cannot be turned off is a policy
    the config no longer owns.
    """
    p = tmp_path / "explicit.json"
    p.write_text(json.dumps({"armed": True, "human_driven_roots": []}))
    assert wgc.load_config(tmp_path, str(p))["human_driven_roots"] == []


def test_the_floor_is_not_reachable_by_a_relative_path_trick(tmp_path):
    """The floor entries are absolute, and expand_roots keeps absolutes verbatim.

    Pinned because the sibling `roots` list is repo-RELATIVE and expanded under every host
    checkout; if the floor were ever rewritten in that idiom it would silently expand to
    per-host paths that match nothing.
    """
    cfg = dict(wgc.DEFAULT_CONFIG)
    out = [str(x) for x in wgc.human_driven_protection([tmp_path], cfg)]
    assert out == list(wgc.DEFAULT_CONFIG["human_driven_roots"]), out
    assert all(x.startswith("/") for x in out), out


# --- the report must name the file its policy came from -----------------------------------

def test_policy_source_flags_the_implicit_primary_checkout_path():
    line = wgc.policy_source_line(
        {"config_path": "/some/primary/config/worktree_gc.json", "config_explicit": False})
    assert "/some/primary/config/worktree_gc.json" in line
    assert "fast-forward" in line, line


def test_policy_source_marks_an_explicit_config_as_explicit():
    line = wgc.policy_source_line({"config_path": "/tmp/x.json", "config_explicit": True})
    assert "explicit" in line
    assert "fast-forward" not in line, "an explicit --config carries no staleness caveat"


def test_policy_source_omitted_not_invented_without_metadata():
    assert wgc.policy_source_line({}) is None


def test_the_rendered_report_names_its_policy_source(repo, tmp_path, monkeypatch, capsys):
    """A verdict computed from an unnamed config cannot be checked by its reader."""
    cfg = _write_config(tmp_path, human_driven_roots=[str(repo["root"] / "web-session")])
    _run_main(repo, tmp_path, monkeypatch, cfg=cfg)
    blob = capsys.readouterr().out
    assert "policy source:" in blob
    assert str(cfg) in blob, blob[:400]

