"""Test driver for the Rotation Core v2 runner (tests only; never a release path).

R25.1(a) makes the runner refuse unless the interpreter runs with `-E`, so every test that goes through `main()` runs
this file in a real subprocess: `python -E tests/rotation_core_v2_driver.py <config.json>`. The config names the
temporary repository and fixtures; the only stubs are the host API (a chain built from the temporary remote's own
history) and the engine-commit check, passed through `main(_ctx=...)`, which the command line never sets.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import rotation_core_v2 as v2  # noqa: E402
from engine import rotation_core_evaluation as rc  # noqa: E402
import scripts.run_rotation_core_v2 as run  # noqa: E402


def host_stub(work, branch):
    """TEST-ONLY host API: the activity chain is the temporary remote's first-parent history from its creation;
    the branch rules and the ruleset are present and active."""
    def api(path, paginate=False):
        if "/activity" in path:
            shas = subprocess.run([v2.tool("git"), "-C", str(work), "rev-list", "--first-parent", "--reverse",
                                   f"refs/remotes/origin/{branch}"], capture_output=True, check=True).stdout.decode().split()
            ref = f"refs/heads/{branch}"
            log = [{"id": 1, "activity_type": "branch_creation", "before": v2.ZERO_SHA, "after": shas[0], "ref": ref,
                    "timestamp": "2026-11-11T00:00:00Z"}]
            log += [{"id": i + 1, "activity_type": "push", "before": shas[i - 1], "after": shas[i], "ref": ref,
                     "timestamp": f"2026-11-11T00:{i // 60:02d}:{i % 60:02d}Z"} for i in range(1, len(shas))]
            return log
        if "/rules/branches/" in path:
            return [{"type": "non_fast_forward"}, {"type": "deletion"}]
        if "/rulesets/" in path:
            return {"id": v2.RULESET_ID, "enforcement": "active", "bypass_actors": [], "updated_at": "stub"}
        raise AssertionError(path)
    return api


def build_ctx(c: dict):
    P = lambda x: Path(x) if x is not None else None
    kw = {k: P(c[k]) for k in ("root", "ledger_path", "release1", "release2", "selection", "ind_d", "ind_full", "fact",
                               "fund_dir", "final_j", "final_m", "stage1_published", "ledger_status_j",
                               "ledger_status_m") if k in c}
    kw.update({k: c[k] for k in ("branch", "remote_url", "anchor", "B") if k in c})
    for k in ("stage1_inputs", "stage2_inputs"):
        if k in c:
            kw[k] = {n: Path(p) for n, p in c[k].items()}
    kw["sealed_paths"] = [Path(p) for p in c.get("sealed_paths", [])]
    kw["sealed_recorded"] = c.get("sealed_recorded", {})
    if c.get("host_stub"):
        kw["host_api"] = host_stub(c["root"], c["branch"])
    if c.get("engine_stub"):
        kw["engine_check"] = lambda commit: None
    return run.Ctx(**kw)


def plant(cfg: dict) -> None:
    """Make the record push after a clean Phase B fail (R25.1(b) / R26.1 tests)."""
    kind = cfg.get("plant")
    if not kind:
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
    ctx = run.Ctx(release1=ROOT / "research/rotation_core/__absent_release_for_tests__.json")
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
