"""Test driver for the Rotation Core v2 runner (tests only; never a release path).

R25.1(a) makes the runner refuse unless the interpreter runs with `-E`, so every test that goes through `main()` runs
this file in a real subprocess: `python -E tests/rotation_core_v2_driver.py <config.json>`. The config names the
temporary repository and fixtures; the only stubs are the host API (a chain built from the temporary remote's own
history) and the engine-commit check, passed through `main(_ctx=...)`, which the command line never sets.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM_TMP = os.path.realpath("/tmp")
PATH_KEYS = ("root", "ledger_path", "release1", "release2", "selection", "ind_d", "ind_full", "fact", "fund_dir",
             "final_j", "final_m", "stage1_published", "selection_rerun_j", "selection_rerun_m", "ledger_status_j",
             "ledger_status_m")
MAP_KEYS = ("stage1_inputs", "stage2_inputs")
LIST_KEYS = ("sealed_paths",)
OTHER_KEYS = ("branch", "remote_url", "sealed_recorded", "anchor", "B", "host_stub", "engine_stub")
REQUIRED_CTX_KEYS = PATH_KEYS + MAP_KEYS + LIST_KEYS + OTHER_KEYS


def _under_tmp(p) -> bool:
    r = os.path.realpath(str(p))
    return r == SYSTEM_TMP or r.startswith(SYSTEM_TMP + os.sep)


def check_config_paths(cfg: dict) -> None:
    """R27.1(c)/R28.5: BEFORE importing the runner: the config names every required key (no key falls back to
    anything), and every path value (each path key, every value of both input maps, every sealed path, the remote,
    and the driver's own outputs) lies under the system temporary directory."""
    c = cfg.get("ctx")
    if not isinstance(c, dict) or any(k not in c for k in REQUIRED_CTX_KEYS):
        raise SystemExit("refused: the driver config must name every context key (R28.5)")
    if "://" in str(c["remote_url"]):                    # R32.5: a URL remote refuses on its own, before the path rule
        raise SystemExit("refused: the driver accepts only a local remote path (R32.5)")
    if any(not isinstance(c[k], dict) for k in MAP_KEYS) or any(not isinstance(c[k], list) for k in LIST_KEYS):
        raise SystemExit("refused: malformed driver config (R28.5)")
    paths = [c[k] for k in PATH_KEYS] + [p for k in MAP_KEYS for p in c[k].values()] + \
        [p for k in LIST_KEYS for p in c[k]] + [c["remote_url"]] + \
        [cfg[k] for k in ("origin", "out", "capture_keys") if cfg.get(k)]
    if any(not _under_tmp(p) for p in paths):
        raise SystemExit(f"refused: the driver accepts only paths under {SYSTEM_TMP} (R27.1(c), R28.5)")


if __name__ == "__main__":
    _cfg = json.loads(Path(sys.argv[1]).read_text())
    if _cfg.get("mode") == "real_hooks":                 # a wholly-real context with an absent release: out under /tmp
        if not _under_tmp(_cfg.get("out", "/")):
            raise SystemExit("refused: the driver accepts only paths under /tmp (R27.1(c))")
    else:
        check_config_paths(_cfg)

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))                         # R31.6(b)

from engine import rotation_core_v2 as v2  # noqa: E402
from engine import rotation_core_evaluation as rc  # noqa: E402
import scripts.run_rotation_core_v2 as run  # noqa: E402


def host_stub(work, branch):
    """TEST-ONLY host API: the activity chain is the temporary remote's first-parent history from its creation;
    the branch rules and the ruleset are present and active."""
    def api(path, paginate=False):
        if "/activity" in path:
            shas = v2._git("rev-list", "--first-parent", "--reverse", f"refs/remotes/origin/{branch}",
                           root=work).stdout.decode().split()               # R29.4: the constructed environment
            ref = f"refs/heads/{branch}"
            log = [{"id": 1, "activity_type": "branch_creation", "before": v2.ZERO_SHA, "after": shas[0], "ref": ref,
                    "timestamp": "2026-11-11T00:00:00Z"}]
            log += [{"id": i + 1, "activity_type": "push", "before": shas[i - 1], "after": shas[i], "ref": ref,
                     "timestamp": f"2026-11-11T00:{i // 60:02d}:{i % 60:02d}Z"} for i in range(1, len(shas))]
            return log
        if "/rules/branches/" in path:
            return [{"type": "non_fast_forward"}, {"type": "deletion"}]
        if "/rulesets/" in path:
            return {"id": v2.RULESET_ID, "enforcement": "active", "bypass_actors": [], "updated_at": "stub",
                    "stub": True}
        raise AssertionError(path)
    return api


def build_ctx(c: dict):
    """Every field explicit (R28.1); the only stubs are the host API and the engine-commit check."""
    P = Path
    return run.Ctx(**{k: P(c[k]) for k in PATH_KEYS},
                   stage1_inputs={n: P(p) for n, p in c["stage1_inputs"].items()},
                   stage2_inputs={n: P(p) for n, p in c["stage2_inputs"].items()},
                   sealed_paths=[P(p) for p in c["sealed_paths"]], sealed_recorded=c["sealed_recorded"],
                   branch=c["branch"], remote_url=c["remote_url"], anchor=c["anchor"], B=c["B"],
                   host_api=host_stub(c["root"], c["branch"]) if c["host_stub"] else None,
                   engine_check=(lambda commit: None) if c["engine_stub"] else v2.check_engine_commit)


def plant(cfg: dict) -> None:
    """Make the record push after a clean Phase B fail (R25.1(b) / R26.1 tests)."""
    kind = cfg.get("plant")
    if not kind:
        return
    if kind == "bypass_worktree_check":                  # R31.1(d): show what START records when (c) is skipped
        run._check_worktree_against_head = lambda *a, **k: None
        return
    if kind == "spy_order":                              # R33: order of strict checks, reads and late imports
        log = Path(cfg["out"])
        real_shadow, real_vl, real_io = run.refuse_shadowed_modules, run.verified_ledger, v2.io_check
        real_v2_shadow = v2.refuse_shadowed_modules
        state = {"mods": set(sys.modules)}

        def w(line):
            with open(log, "a") as f:
                f.write(line + "\n")

        def new_since():
            new = sorted(set(sys.modules) - state["mods"])
            return " new_before=[" + " ".join(new) + "]"

        def shadow(*a, **k):
            w("shadow" + new_since()); out = real_shadow(*a, **k); state["mods"] = set(sys.modules)
            return out

        def v2_shadow(*a, **k):
            w("record_shadow" + new_since()); out = real_v2_shadow(*a, **k); state["mods"] = set(sys.modules)
            return out

        def vl(*a, **k):
            out = real_vl(*a, **k); w("verified_ledger_done")
            return out

        def io_spy(path, k):
            w(f"io {k}")
            return real_io(path, k)
        run.refuse_shadowed_modules, run.verified_ledger, v2.io_check = shadow, vl, io_spy
        v2.refuse_shadowed_modules = v2_shadow
        import atexit
        atexit.register(lambda: w("late_imports " + " ".join(sorted(set(sys.modules) - state["mods"]))))
        return
    if kind == "spy_io":                                 # R31.2: record io_check and hashing order
        log = Path(cfg["out"])
        real_io, real_sha = v2.io_check, v2.sha256_file

        def io_spy(path, k):
            with open(log, "a") as f:
                f.write(f"io {k} {path}\n")
            return real_io(path, k)

        def sha_spy(path):
            with open(log, "a") as f:
                f.write(f"sha {path}\n")
            return real_sha(path)
        v2.io_check, v2.sha256_file = io_spy, sha_spy
        return
    origin = Path(cfg["origin"])
    orig = run.pre1998_stats

    def wrapped(*a, **k):
        res = orig(*a, **k)
        if kind == "fetch_fail_before_gate":
            origin.rename(origin.with_name(origin.name + ".gone"))
        elif kind == "reject_push_before_gate":
            h = origin / "hooks" / "pre-receive"
            h.write_text("#!/bin/sh\nexit 1\n"); h.chmod(0o755)
        return res
    run.pre1998_stats = wrapped


def capture_keys(path):
    orig = rc.stationary_bootstrap_indices
    keys = []

    def spy(n, b, block, seed):
        keys.append(list(seed.spawn_key) if hasattr(seed, "spawn_key") else seed)
        return orig(n, b, block, seed)
    rc.stationary_bootstrap_indices = spy
    import atexit
    atexit.register(lambda: Path(path).write_text(json.dumps(keys)))


def real_hooks(cfg: dict) -> int:
    """R26.2/R24.5: the real host check and the real engine-commit check, with only the stage-1 release path
    replaced by an absent path inside the repository (so nothing sealed can run)."""
    calls = {}
    real_host, real_s1 = v2.host_checks, v2.stage1_release

    def host_spy(*a, **k):
        calls["host_api_is_none"] = (a[2] if len(a) > 2 else k.get("api")) is None
        rec = real_host(*a, **k)
        calls["ruleset_id"] = rec["ruleset_id"]
        return rec

    def s1_spy(*a, **k):
        calls["engine_check_is_real"] = k.get("engine_check") is v2.check_engine_commit
        return real_s1(*a, **k)
    v2.host_checks, v2.stage1_release = host_spy, s1_spy
    real_io = v2.io_check
    calls["input_reads"] = 0

    def io_spy(path, kind):
        if kind == "read":
            calls["input_reads"] += 1                    # R31.4: no input file is opened in this mode
        return real_io(path, kind)
    v2.io_check = io_spy
    # a wholly-REAL supplied context: the real fields, with only the stage-1 release path replaced by an absent one
    real = run._real_ctx()
    kw = {k: getattr(real, k) for k in run.CTX_FIELDS}
    kw["release1"] = ROOT / "research/rotation_core/__absent_release_for_tests__.json"
    ctx = run.Ctx(**kw)
    try:
        run.main(["--stage", "pre1998"], _ctx=ctx)
        calls["refusal"] = None
    except v2.SealedRefusal as e:
        calls["refusal"] = str(e)
    Path(cfg["out"]).write_text(json.dumps(calls))
    return 0


def main() -> int:
    cfg = json.loads(Path(sys.argv[1]).read_text())
    if cfg.get("mode") == "real_hooks":
        return real_hooks(cfg)
    if cfg.get("capture_keys"):
        capture_keys(cfg["capture_keys"])
    plant(cfg)
    return run.main(cfg["argv"], _ctx=build_ctx(cfg["ctx"]))


if __name__ == "__main__":
    raise SystemExit(main())
