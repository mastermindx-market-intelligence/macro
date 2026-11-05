"""asia-close.yml — the GH001 qledger-oversize carve-out, ported from #9556.

PR #9556 (merge 861de75dc831054888fa963423510cd13309bb69) fixed the nightly
lane only: when a staged ``data/qledger/claims.jsonl`` grows within 1 MiB of
GitHub's 100 MiB blob limit, GH001 rejects the WHOLE commit it rides, so
``daily.yml``'s market commit unstages the qledger plane (custody snapshot,
park over the push, restore after). ``asia-close.yml`` commits through the
SAME broad ``git add data/ site/qledger/`` after the same qledger grader, but
kept the unprotected shape — and every real asia-close run from 2026-10-17
(39023996637 … 39419107676) died exactly there: ``remote rejected main ->
main (pre-receive hook declined)``, leaving HK/China per-ticker data ~97 h
stale while the collected market bytes sat valid on the runner.

This suite pins the port:

* the carve-out shell inside ``commit collected asia data`` is BYTE-IDENTICAL
  to daily.yml's (same limit, same margin, same custody/withhold contract);
* the park / push / restore steps around the collect push are wired with the
  same gates daily.yml uses, fail closed on the withheld path, and keep the
  lane's collect-failure propagation (no ``if: always()`` step between the
  collect commit and the build — pinned by
  tests/test_tushare_freshness_tripwire.py);
* the later ``commit engine outputs`` broad add cannot re-stage the carved
  bytes (the daily.yml engine-commit unstage idiom);
* cases (a) oversize, (b) small, (c) snapshot-refused run the REAL step body
  verbatim in a temporary git repository.

The execution harness and the carve-out constants are imported from
tests/test_daily_collect_commit_path.py so the two lanes cannot drift apart
in this suite's own plumbing.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_daily_collect_commit_path import (  # noqa: E402
    _MARGIN,
    _LIMIT,
    _carve_seed_gitattributes,
    _eval_commitdata_gate,
    _git,
    _git_env,
    _grow,
    _index_of,
    _read_step_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
ASIA = ROOT / ".github/workflows/asia-close.yml"
DAILY = ROOT / ".github/workflows/daily.yml"

ASIA_COMMIT_STEP = "commit collected asia data"
ASIA_PUSH_STEP = "push asia data"
ASIA_SPINE_STEP = "build china a-share dashboard"
ASIA_ENGINE_COMMIT_STEP = "commit engine outputs"
# Same names as daily.yml (#9556) — the port reuses the steps verbatim.
QLEDGER_PARK_STEP = "park carved qledger bytes outside the push autostash"
QLEDGER_RESTORE_STEP = "restore carved qledger bytes (runner-local, never published here)"

_WITHHELD_ERROR = "::error title=market publication withheld (qledger carve snapshot failed)::"
_CARVE_WARNING = "::warning title=qledger carved out of market commit::"


@pytest.fixture(scope="module")
def asia_steps() -> list[dict]:
    doc = yaml.safe_load(ASIA.read_text())
    steps = doc["jobs"]["asia"]["steps"]
    assert steps, "asia job has no steps — workflow shape changed"
    return steps


def _carve_block(path: Path) -> str:
    """The carve-out shell verbatim: from its comment header to the closing fi."""
    text = path.read_text(encoding="utf-8")
    start = text.index("          # QLEDGER OVERSIZE CARVE-OUT (2026-10-17).")
    end = text.index("\n          if git diff --cached --quiet", start)
    return text[start:end]


# ── structural: the carve-out shell is the daily.yml one ─────────────────────


def test_asia_carve_out_shell_is_byte_identical_to_daily():
    """Port, not redesign: the carve-out block in asia-close.yml must equal
    daily.yml's byte for byte — same limit, same margin, same snapshot,
    unstage, output and withhold contract."""
    assert _carve_block(ASIA) == _carve_block(DAILY)


def test_asia_commit_step_emits_the_daily_commit_contract(asia_steps):
    step = asia_steps[_index_of(asia_steps, ASIA_COMMIT_STEP)]
    assert step.get("id") == "commitdata", (
        "the park/push/restore gates reference steps.commitdata.outputs"
    )
    run = str(step["run"])
    # committed starts false and flips to true only after the market commit —
    # the same last-write-wins contract daily.yml's commitdata step uses.
    assert 'echo "committed=false" >> "$GITHUB_OUTPUT"' in run
    assert 'echo "committed=true" >> "$GITHUB_OUTPUT"' in run
    assert run.index("committed=false") < run.index("qledger_limit=")
    assert run.index("committed=true") > run.index('git commit -m "data: asia collection')
    # same numbers, same measure loop (redundant with byte identity, but a
    # regression here must name the limit, not just "blocks differ")
    assert "qledger_limit=104857600" in run
    assert "qledger_margin=1048576" in run
    assert 'git cat-file -s ":$qpath"' in run
    # the carve shell must NOT be a redesign: unstage only, never revert.
    assert "git reset -q -- data/qledger site/qledger" in run
    assert "checkout -- data/qledger" not in run
    # local checkpoint only — the push moved to its own gated step so the park
    # can sit between commit and push exactly as in daily.yml. (Comments quote
    # `git pull --rebase`, so scan the executable lines, not the prose.)
    body = "\n".join(
        ln for ln in run.splitlines() if ln.strip() and not ln.strip().startswith("#")
    )
    for absent in ("push_retry_init", "push_attempt", "git pull", "git push"):
        assert absent not in body, f"commit step still carries push machinery: {absent}"


def test_asia_carve_custody_steps_are_wired(asia_steps):
    """park between the commit and the push; push gated like daily's
    `push market data`; restore after the push on every outcome — placed after
    the build china spine step so the lane's no-always() span between the
    collect commit and the build (tests/test_tushare_freshness_tripwire.py)
    keeps failing closed on a failed collect."""
    commit_at = _index_of(asia_steps, ASIA_COMMIT_STEP)
    park_at = _index_of(asia_steps, QLEDGER_PARK_STEP)
    push_at = _index_of(asia_steps, ASIA_PUSH_STEP)
    spine_at = _index_of(asia_steps, ASIA_SPINE_STEP)
    restore_at = _index_of(asia_steps, QLEDGER_RESTORE_STEP)
    engine_at = _index_of(asia_steps, ASIA_ENGINE_COMMIT_STEP)
    assert park_at == commit_at + 1, "park must sit immediately after the collect commit"
    assert push_at == park_at + 1, "push must sit immediately after the park"
    assert commit_at < push_at < spine_at < restore_at < engine_at

    park = asia_steps[park_at]
    push = asia_steps[push_at]
    restore = asia_steps[restore_at]
    # daily.yml's gates, minus the `always() &&` prefix on park/push (the
    # propagation pin above); the gates are output-driven and fail closed.
    assert park.get("if") == (
        "steps.commitdata.outputs.committed == 'true' && "
        "steps.commitdata.outputs.qledger_snapshot != ''"
    )
    assert push.get("if") == (
        "steps.commitdata.outputs.committed == 'true' && "
        "(steps.commitdata.outputs.qledger_carved != 'true' || "
        "steps.park.outputs.parked == 'true')"
    )
    # the restore keeps daily's verbatim condition, including always() — it
    # must run after a FAILED push, and it sits outside the pinned span.
    assert restore.get("if") == (
        "always() && steps.commitdata.outputs.qledger_snapshot != ''"
    )
    assert park.get("env", {}).get("QLEDGER_SNAPSHOT") == (
        "${{ steps.commitdata.outputs.qledger_snapshot }}"
    )
    assert restore.get("env", {}).get("QLEDGER_SNAPSHOT") == (
        "${{ steps.commitdata.outputs.qledger_snapshot }}"
    )
    assert park.get("id") == "park" and push.get("id") == "pushdata"

    # the push is the SAME rebase-retry loop that used to live in the commit
    # step: same helper, same label, same give-up tail — and it stages nothing.
    push_run = str(push["run"])
    assert '. "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"' in push_run
    assert 'push_retry_init "asia data"' in push_run
    assert "while push_attempt; do" in push_run
    assert push_run.rstrip().endswith("push_lost")
    assert "git pull --rebase --autostash -X theirs origin main" in push_run
    assert "git add" not in push_run, "the push step must never stage anything"


def test_asia_carve_gates_fail_closed_on_the_withheld_path(asia_steps):
    """On every output combination the carve-out can produce, no publisher
    step may open unless the market commit exists and (on a carved night) the
    park was verified — evaluated through daily's own gate evaluator."""
    commit_at = _index_of(asia_steps, ASIA_COMMIT_STEP)
    park_at = _index_of(asia_steps, QLEDGER_PARK_STEP)
    push_at = _index_of(asia_steps, ASIA_PUSH_STEP)
    restore_at = _index_of(asia_steps, QLEDGER_RESTORE_STEP)

    # sanity: the gates really do open on the states they must serve.
    normal = {"committed": "true"}
    assert _eval_commitdata_gate(
        asia_steps[push_at]["if"], normal, cancelled=False,
    ), "a normal night must push"
    carved_parked = {"committed": "true", "qledger_carved": "true"}
    assert _eval_commitdata_gate(
        asia_steps[push_at]["if"], carved_parked, cancelled=False,
        park_outputs={"parked": "true"},
    ), "a verified park must open the push on a carved night"
    assert _eval_commitdata_gate(
        asia_steps[restore_at]["if"], {"qledger_snapshot": "abc123"}, cancelled=False,
    ), "restore must run whenever a snapshot exists"

    for name, at, cancelled in (
        (QLEDGER_PARK_STEP, park_at, False),
        (ASIA_PUSH_STEP, push_at, False),
        (QLEDGER_RESTORE_STEP, restore_at, False),
    ):
        for outputs in (
            # (c): snapshot refused — everything withheld.
            {"committed": "false", "qledger_withheld": "true"},
            # collect failed / skipped before the commit step.
            {},
        ):
            assert not _eval_commitdata_gate(
                asia_steps[at]["if"], outputs, cancelled=cancelled,
            ), f"{name!r} would run on outputs={outputs!r}"
    # deferred-only night (carve happened, nothing else to commit): the
    # publishers stay closed, but the restore runs — custody must return.
    deferred_only = {"committed": "false", "qledger_carved": "true", "qledger_snapshot": "abc"}
    for name, at in ((QLEDGER_PARK_STEP, park_at), (ASIA_PUSH_STEP, push_at)):
        assert not _eval_commitdata_gate(
            asia_steps[at]["if"], deferred_only, cancelled=False,
        ), f"{name!r} would run on the deferred-only night"
    assert _eval_commitdata_gate(
        asia_steps[restore_at]["if"], deferred_only, cancelled=False,
    ), "restore must return custody on the deferred-only night"
    # a carved night with an UNVERIFIED park never publishes.
    assert not _eval_commitdata_gate(
        asia_steps[push_at]["if"], carved_parked, cancelled=False, park_outputs={},
    ), "push must stay closed until the park verifies"
    # restore DOES run on the deferred-only night (snapshot exists) — custody
    # returns even when no market commit was made (checked above in sanity).


def test_asia_engine_commit_cannot_restage_carved_paths(asia_steps):
    """The single-job tail: `commit engine outputs` runs in THIS workspace,
    after the restore step put the carved bytes back. Its broad
    `git add data/ site/` must be followed by the daily.yml engine-commit
    unstage (W0b idiom) whenever the collect commit carved — a reset BEFORE
    the add would only be re-staged by it."""
    engine = asia_steps[_index_of(asia_steps, ASIA_ENGINE_COMMIT_STEP)]
    assert engine.get("env", {}).get("QLEDGER_CARVED") == (
        "${{ steps.commitdata.outputs.qledger_carved }}"
    )
    run = str(engine["run"])
    guard = 'if [ "$QLEDGER_CARVED" = \'true\' ]; then'
    assert guard in run
    reset = "git reset -q -- data/qledger site/qledger"
    assert reset in run
    assert run.index("git add data/ site/") < run.index(reset), (
        "the unstage must sit AFTER the broad add (a pre-add reset is re-staged)"
    )
    # tolerance: an empty qledger plane must not fail the engine commit.
    reset_block = run[run.index(guard):]
    assert "|| true" in reset_block.split("fi")[0]


# ── execution: the real step body in a temporary git repository ──────────────


def _run_asia_commit(tmp_path, asia_steps, mutate, seed=None):
    """Materialize a fresh git repo, mutate it, and run the verbatim `run:`
    body of the asia collect-commit step. Mirrors the daily harness, with the
    asia base stores and a no-op stub for the Options narrow-roots helper the
    step invokes around its broad add (that fence is another lane's contract;
    the stub keeps the body byte-verbatim without the scripts/ tree)."""
    run = str(asia_steps[_index_of(asia_steps, ASIA_COMMIT_STEP)]["run"])
    assert "${{" not in run, (
        "test harness must run the step body verbatim — if asia-close.yml grew "
        "a ${{ ... }} interpolation, render it through the GitHub env first or "
        "rewrite the test runner; do NOT silently swallow the substitution."
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GITHUB_OUTPUT": str(tmp_path / "gh_output"),
    }
    for k, v in {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }.items():
        env.setdefault(k, v)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, env=env, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, env=env, check=True)
    # Base files: the asia market plane (china/hk per-ticker stores) + the
    # qledger plane, frozen at a known state.
    for rel, body in (
        ("data/china_stocks/000001.parquet", b"v1"),
        ("data/hk_stocks/0001.parquet", b"h1"),
        ("data/qledger/claims.jsonl", b'{"claim_id":"c0"}\n'),
        ("site/qledger/track_record.json", b"{}"),
    ):
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
    subprocess.run(["git", "add", "data", "site"], cwd=repo, env=env, check=True)
    if seed is not None:
        seed(repo, env)
        if (repo / ".gitattributes").exists():
            subprocess.run(["git", "add", ".gitattributes"], cwd=repo, env=env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=repo, env=env, check=True)
    # No-op stub for the Options narrow-roots fence the step invokes.
    stub = repo / "scripts" / "ci" / "options_signal_nightly.sh"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text("#!/usr/bin/env bash\nexit 0\n")
    mutate(repo)
    proc = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", run],
        cwd=repo, env=env, capture_output=True, text=True, timeout=300,
    )
    return proc, _read_step_outputs(tmp_path / "gh_output"), repo


def test_asia_qledger_carve_oversized_ledger_publishes_market_and_withholds_qledger(
    tmp_path, asia_steps,
):
    """Case (a): a staged claims.jsonl over the limit minus margin. The market
    plane commits and pushes-eligible state is reached, the qledger paths are
    reset out of the index (never reverted), the custody snapshot output is
    set and the snapshot commit itself is readable and holds the bytes."""

    def mutate(repo):
        (repo / "data" / "china_stocks" / "000001.parquet").write_bytes(b"v2")
        (repo / "data" / "hk_stocks" / "0001.parquet").write_bytes(b"h2")
        _grow(repo / "data" / "qledger" / "claims.jsonl", _LIMIT + 4096)
        (repo / "site" / "qledger" / "track_record.json").write_bytes(b'{"n":1}')

    base = None

    def mutate_with_base(repo):
        nonlocal base
        base = _git(repo, "rev-parse", "HEAD").stdout.strip()  # the base commit
        mutate(repo)

    proc, outputs, repo = _run_asia_commit(tmp_path, asia_steps, mutate_with_base)
    assert proc.returncode == 0, (
        f"step failed: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    subject = _git(repo, "log", "-1", "--format=%s").stdout
    assert subject.startswith("data: asia collection"), subject
    # Market plane landed (the whole reason the carve-out exists).
    for spec, want in (
        ("HEAD:data/china_stocks/000001.parquet", b"v2"),
        ("HEAD:data/hk_stocks/0001.parquet", b"h2"),
        ("HEAD:data/qledger/claims.jsonl", b'{"claim_id":"c0"}\n'),
        ("HEAD:site/qledger/track_record.json", b"{}"),
    ):
        got = subprocess.run(
            ["git", "show", spec], cwd=repo, env=_git_env(),
            capture_output=True, check=True,
        ).stdout
        assert got == want, f"{spec!r} drifted: {got!r}"
    # No oversized blob may ride HEAD — the GH001 invariant.
    ls = _git(repo, "ls-tree", "-r", "-l", "HEAD").stdout
    oversized = [
        line for line in ls.splitlines()
        if line.split("\t", 1)[0].split()[1] == "blob"
        and int(line.split("\t", 1)[0].split()[3]) > _LIMIT
    ]
    assert not oversized, f"GH001: HEAD still carries a >{_LIMIT}B blob: {oversized}"
    # The qledger paths are RESET (index clean for them), not reverted: the
    # working tree keeps the collected append for the custody snapshot story.
    assert _git(repo, "diff", "--cached", "--quiet", "--",
                "data/qledger", "site/qledger").returncode == 0, (
        "qledger paths still staged after the carve-out"
    )
    assert (repo / "data" / "qledger" / "claims.jsonl").stat().st_size == _LIMIT + 4096
    status = _git(repo, "status", "--porcelain", "--",
                  "data/qledger/claims.jsonl").stdout
    assert "data/qledger/claims.jsonl" in status, (
        f"working-tree ledger should still be modified; got status: {status!r}"
    )
    # Outputs + warning are the user-visible contract.
    assert outputs.get("committed") == "true"
    assert outputs.get("qledger_carved") == "true"
    assert _CARVE_WARNING in proc.stdout
    assert "data/qledger/claims.jsonl" in proc.stdout
    # The custody snapshot output is set, readable, parented on the pre-commit
    # HEAD, and actually holds the carved bytes.
    snapshot = outputs.get("qledger_snapshot")
    assert snapshot, f"qledger_snapshot output missing: {outputs!r}"
    assert _git(repo, "cat-file", "-e", snapshot).returncode == 0, (
        f"snapshot commit {snapshot!r} is not readable"
    )
    assert _git(repo, "rev-parse", f"{snapshot}^").stdout.strip() == base, (
        "snapshot parent must be the pre-commit HEAD"
    )
    size = _git(repo, "cat-file", "-s",
                f"{snapshot}:data/qledger/claims.jsonl").stdout.strip()
    assert int(size) == _LIMIT + 4096, (
        f"snapshot claims blob is {size}B, expected {_LIMIT + 4096}B"
    )


def test_asia_qledger_carve_small_ledger_publishes_as_before(tmp_path, asia_steps):
    """Case (b): a small qledger change must publish exactly as before — the
    carve-out is a safety valve, not a switch that turns the qledger plane
    off forever."""

    def mutate(repo):
        with open(repo / "data" / "qledger" / "claims.jsonl", "ab") as f:
            f.write(b'{"claim_id":"c2"}\n')
        (repo / "site" / "qledger" / "track_record.json").write_bytes(b'{"n":1}')
        (repo / "data" / "china_stocks" / "000001.parquet").write_bytes(b"v2")

    proc, outputs, repo = _run_asia_commit(tmp_path, asia_steps, mutate)
    assert proc.returncode == 0, (
        f"step failed: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert outputs.get("committed") == "true"
    for key in ("qledger_carved", "qledger_snapshot", "qledger_withheld"):
        assert key not in outputs, f"small ledger tripped the carve-out: {outputs!r}"
    new_claims = (repo / "data" / "qledger" / "claims.jsonl").read_bytes()
    head_claims = subprocess.run(
        ["git", "show", "HEAD:data/qledger/claims.jsonl"], cwd=repo,
        env=_git_env(), capture_output=True, check=True,
    ).stdout
    assert head_claims == new_claims, "small ledger growth did not land in HEAD"
    head_tr = subprocess.run(
        ["git", "show", "HEAD:site/qledger/track_record.json"], cwd=repo,
        env=_git_env(), capture_output=True, check=True,
    ).stdout
    assert head_tr == b'{"n":1}'
    assert "qledger carved" not in proc.stdout


def test_asia_qledger_carve_snapshot_failure_withholds_publication(
    tmp_path, asia_steps, monkeypatch,
):
    """Case (c): shim ONLY `git commit-tree` to fail. The step must exit 0
    (collect stays green for the builders), write qledger_withheld=true, no
    committed=true, no qledger_snapshot, leave HEAD and the collected bytes
    untouched, emit the withheld ::error + step summary — so no park, push or
    restore gate can open (pinned in test_asia_carve_gates_fail_closed)."""
    import shutil

    real_git = shutil.which("git")
    assert real_git, "git not on PATH"
    shim_dir = tmp_path / "commit_tree_refused"
    shim_dir.mkdir()
    (shim_dir / "git").write_text(
        "#!/usr/bin/env bash\n"
        "for a in \"$@\"; do\n"
        "  if [ \"$a\" = \"commit-tree\" ]; then\n"
        "    echo \"shim: commit-tree refused (simulated snapshot failure)\" >&2\n"
        "    exit 128\n"
        "  fi\n"
        "done\n"
        f"exec \"{real_git}\" \"$@\"\n"
    )
    (shim_dir / "git").chmod(0o755)
    monkeypatch.setenv("PATH", f"{shim_dir}:{os.environ.get('PATH', '')}")
    summary_path = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))

    watched = (
        "data/qledger/claims.jsonl",
        "site/qledger/track_record.json",
        "data/china_stocks/000001.parquet",
    )
    before = {}

    def mutate(repo):
        (repo / "data" / "china_stocks" / "000001.parquet").write_bytes(b"v2")
        _grow(repo / "data" / "qledger" / "claims.jsonl", _LIMIT + 4096)
        (repo / "site" / "qledger" / "track_record.json").write_bytes(b'{"n":1}')
        before["HEAD"] = _git(repo, "rev-parse", "HEAD").stdout.strip()
        for rel in watched:
            before[rel] = _git(repo, "hash-object", "--no-filters", "--", rel).stdout.strip()

    proc, outputs, repo = _run_asia_commit(
        tmp_path, asia_steps, mutate, seed=_carve_seed_gitattributes,
    )
    assert proc.returncode == 0, (
        f"the withheld path must not fail the collect job: "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert outputs.get("committed") == "false", (
        f"a market commit was made although the carve snapshot failed: {outputs!r}"
    )
    assert "qledger_snapshot" not in outputs, f"no snapshot may be advertised: {outputs!r}"
    assert outputs.get("qledger_withheld") == "true", f"qledger_withheld missing: {outputs!r}"
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == before["HEAD"], (
        "a market commit was made on the withheld path"
    )
    # Collected bytes are left untouched (claims + twin + the market change).
    for rel in watched:
        now = _git(repo, "hash-object", "--no-filters", "--", rel).stdout.strip()
        assert now == before[rel], f"{rel} changed on the withheld path"
    assert (repo / "data" / "qledger" / "claims.jsonl").stat().st_size == _LIMIT + 4096
    # Loud and honest: the ::error names BOTH planes; the summary says the same.
    assert _WITHHELD_ERROR in proc.stdout, f"withheld ::error missing: {proc.stdout!r}"
    assert "NEITHER market data NOR data/qledger + site/qledger is published" in proc.stdout
    assert "data/qledger/claims.jsonl" in proc.stdout
    summary = summary_path.read_text() if summary_path.exists() else ""
    assert "### Market publication withheld: qledger carve snapshot failed" in summary, (
        f"step summary missing the withheld block: {summary!r}"
    )
