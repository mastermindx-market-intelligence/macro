"""Full-coverage seal verifier (SCHK) — XREP-01..05.

walk_compare is git-free and never fetches. Regeneration tests skip when the
pinned input_ref is absent (depth-1 CI); a timed-out fetch would leave
.git/shallow.lock and a clean depth-1 fetch would rewrite .git/shallow for
every later job in the CI pack (PR #8893). Never fetch here.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "evaluation"))

from seal_full_check import (  # noqa: E402
    Diff,
    INPUT_REF_DEFAULT,
    KIND_DIFFER,
    KIND_EXTRA,
    KIND_MISSING,
    KIND_ULP,
    ULP_REL_TOL,
    ULP_TEXT_SUFFIXES,
    S1_V1_1_REL,
    S1_V1_1_SEAL_COMMIT_PRE_SQUASH,
    S1_V1_1_TRIAL_LEDGER_PATH,
    S1_V1_TRIAL_LEDGER_PATH,
    S2_V1_1_REL,
    S2_V1_1_TRIAL_LEDGER_PATH,
    S2_V1_TRIAL_LEDGER_PATH,
    XREP03_S1_SEAL_LEDGER_PATH,
    XREP04_S2_SEAL_V1_LEDGER_PATH,
    XREP05_S1_MANIFEST_SEAL_COMMIT,
    check_study,
    rel_files,
    s1_exceptions,
    s2_exceptions,
    ulp_equivalent,
    walk_compare,
)
from seal_full_check import S1_BUILD_SEAL_MODULE, _load_s1_build_seal  # noqa: E402

INPUT_REF = INPUT_REF_DEFAULT


def _assert_regen_accounting(res, committed_rel: str) -> None:
    """ULP-equivalent files are text, never counted identical, and never
    counted as failures. This test suite does NOT claim byte identity of a
    regeneration: the committed seal's byte identity on its cut platform is
    attested by the XREP Linux receipt, and X7-01 showed a Linux x86_64
    numpy 2.x interpreter itself drifts within ULP tolerance on the frozen
    allow-set files."""
    ulp_rels = [d.relpath for d in res.diffs if d.kind == KIND_ULP]
    assert len(ulp_rels) == res.ulp_equivalent
    assert all(r.endswith(ULP_TEXT_SUFFIXES) for r in ulp_rels)
    assert res.failures == len(res.diffs) - res.ulp_equivalent
    assert res.identical + res.ulp_equivalent <= len(rel_files(ROOT / committed_rel))


def _ensure_input_ref() -> None:
    """Depth-1 CI checkouts lack BASE: skip (never ERROR, never fetch).

    A test must not fetch into the shared checkout: a timed-out fetch is
    SIGKILLed and leaves .git/shallow.lock behind, and even a clean depth-1
    fetch rewrites .git/shallow for every later job in the same CI pack
    (PR #8893: ruling-graph's ancestry fetch failed on the stale lock).
    """
    present = subprocess.run(["git", "cat-file", "-e", f"{INPUT_REF}^{{commit}}"],
                             cwd=ROOT, capture_output=True).returncode == 0
    if not present:
        pytest.skip("input ref 5ef7a7f39f99 not present in this checkout (depth-1 CI)")


def test_schk_01_walk_compare_detects_every_diff_kind(tmp_path: Path) -> None:
    committed = tmp_path / "committed"
    produced = tmp_path / "produced"
    (committed / "sub").mkdir(parents=True)
    (produced / "sub").mkdir(parents=True)
    (committed / "only_committed.txt").write_text("c\n", encoding="utf-8")
    (produced / "only_produced.txt").write_text("p\n", encoding="utf-8")
    (committed / "sub" / "same.txt").write_text("ok\n", encoding="utf-8")
    (produced / "sub" / "same.txt").write_text("ok\n", encoding="utf-8")
    (committed / "sub" / "changed.txt").write_text("aaa\n", encoding="utf-8")
    (produced / "sub" / "changed.txt").write_text("bbb\n", encoding="utf-8")

    diffs = walk_compare(committed, produced, {})
    by_kind = {d.kind: d for d in diffs}
    assert len(diffs) == 3
    assert by_kind[KIND_MISSING].relpath == "only_committed.txt"
    assert by_kind[KIND_EXTRA].relpath == "only_produced.txt"
    assert by_kind[KIND_DIFFER].relpath == "sub/changed.txt"


def test_schk_01b_regeneration_rejects_unsafe_or_unexpected_sidecars(
    tmp_path: Path,
) -> None:
    """Only the real zero-byte TrialLedger lock is outside sealed artifacts.

    The default full-tree comparator remains strict. The scratch-run view does
    not mask other extra output, a nonempty lock, or a symlink masquerading as
    the writer's durable lock. This exercises the new policy without touching
    any shared source ledger or using a live writer.
    """
    committed = tmp_path / "committed"
    produced = tmp_path / "produced"
    committed.mkdir()
    produced.mkdir()
    for directory in (committed, produced):
        (directory / "trial_ledger.jsonl").write_text('{"trial":"pinned"}\n')
    lock = produced / ".trial_ledger.jsonl.lock"
    lock.write_bytes(b"")

    assert [(d.kind, d.relpath) for d in walk_compare(committed, produced)] == [
        (KIND_EXTRA, ".trial_ledger.jsonl.lock")
    ]
    assert walk_compare(committed, produced, _regenerated_study=True) == []
    assert lock.is_file()  # The verifier must never remove a durable lock.

    (produced / "unexpected-new-file").write_text("not a seal artifact")
    assert [(d.kind, d.relpath) for d in walk_compare(
        committed, produced, _regenerated_study=True
    )] == [(KIND_EXTRA, "unexpected-new-file")]
    (produced / "unexpected-new-file").unlink()

    lock.write_bytes(b"not an empty advisory-lock sidecar")
    with pytest.raises(ValueError, match="unexpected regenerated trial-ledger lock"):
        walk_compare(committed, produced, _regenerated_study=True)
    lock.unlink()
    lock.symlink_to(produced / "trial_ledger.jsonl")
    with pytest.raises(ValueError, match="unexpected regenerated trial-ledger lock"):
        walk_compare(committed, produced, _regenerated_study=True)


def test_schk_02_named_exception_tolerates_only_its_field(tmp_path: Path) -> None:
    committed = tmp_path / "committed"
    produced = tmp_path / "produced"
    committed.mkdir()
    produced.mkdir()
    base = {
        "lane": "s1_residual",
        "version": "v1.1",
        "input_ref": INPUT_REF,
        "trial_ledger_path": S1_V1_1_TRIAL_LEDGER_PATH,
        "authority_flags": {
            "rank_authority": False, "gate_authority": False,
            "size_authority": False, "signal_authority": False,
            "escalation_authority": False, "trade_authority": False,
        },
    }
    produced_obj = dict(base)
    produced_obj["trial_ledger_path"] = S1_V1_TRIAL_LEDGER_PATH
    (committed / "SEAL_AND_BUDGET.json").write_text(
        json.dumps(base, sort_keys=True) + "\n", encoding="utf-8")
    (produced / "SEAL_AND_BUDGET.json").write_text(
        json.dumps(produced_obj, sort_keys=True) + "\n", encoding="utf-8")

    ok = XREP03_S1_SEAL_LEDGER_PATH(
        committed / "SEAL_AND_BUDGET.json", produced / "SEAL_AND_BUDGET.json")
    assert ok == []

    diffs = walk_compare(committed, produced, {
        "SEAL_AND_BUDGET.json": XREP03_S1_SEAL_LEDGER_PATH,
    })
    assert diffs == []

    produced_obj["version"] = "v9"
    (produced / "SEAL_AND_BUDGET.json").write_text(
        json.dumps(produced_obj, sort_keys=True) + "\n", encoding="utf-8")
    failed = XREP03_S1_SEAL_LEDGER_PATH(
        committed / "SEAL_AND_BUDGET.json", produced / "SEAL_AND_BUDGET.json")
    assert failed
    assert any(d.kind == KIND_DIFFER for d in failed)


def test_schk_03_xrep04_inconsistency_pinned() -> None:
    committed = ROOT / S2_V1_1_REL
    seal = json.loads((committed / "SEAL_AND_BUDGET.json").read_text(encoding="utf-8"))
    lane = json.loads((committed / "LANE_MANIFEST.json").read_text(encoding="utf-8"))
    assert seal["trial_ledger_path"] == S2_V1_TRIAL_LEDGER_PATH
    assert lane["trial_ledger_path"] == S2_V1_1_TRIAL_LEDGER_PATH
    assert XREP04_S2_SEAL_V1_LEDGER_PATH(committed) == []


def test_schk_04_comparator_covers_every_committed_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    for name, rel in (("s1", S1_V1_1_REL), ("s2", S2_V1_1_REL)):
        committed = ROOT / rel
        files = rel_files(committed)
        disk = {p.relative_to(committed).as_posix()
                for p in committed.rglob("*") if p.is_file()}
        assert files == disk
        diffs = walk_compare(committed, empty, {})
        visited = {d.relpath for d in diffs}
        assert visited == files
        assert all(d.kind == KIND_MISSING for d in diffs)
        print(f"{name} committed files visited by walk_compare: {len(files)}")
    print(f"s1 count={len(rel_files(ROOT / S1_V1_1_REL))} "
          f"s2 count={len(rel_files(ROOT / S2_V1_1_REL))}")


# Frozen X7-01 allow-set: the ONLY S1 v1.1 paths that may regenerate
# ulp-equivalent — the nine observations/P03_*.json files the seal CLI
# reported on 2026-10-13 plus results/P03.json, exactly as the CLI prints
# them. Anything else regenerating ulp-equivalent is a failure (schk_05b).
S1_ULP_ALLOW_SET = frozenset({
    "observations/P03_adr_baba_21.json",
    "observations/P03_adr_baba_5.json",
    "observations/P03_adr_baba_63.json",
    "observations/P03_hkd_0700_21.json",
    "observations/P03_hkd_0700_5.json",
    "observations/P03_hkd_0700_63.json",
    "observations/P03_hkd_9988_21.json",
    "observations/P03_hkd_9988_5.json",
    "observations/P03_hkd_9988_63.json",
    "results/P03.json",
})


def _assert_s1_ulp_allow_set(ulp_diffs, committed_dir: Path, produced_dir: Path) -> None:
    """Every ulp-equivalent path is inside the frozen allow-set, and its
    recomputed worst relative difference is within the seal module's own
    ULP_REL_TOL (imported, never restated as a number here)."""
    for d in ulp_diffs:
        assert d.kind == KIND_ULP
        assert d.relpath in S1_ULP_ALLOW_SET, (
            f"ulp-equivalent path {d.relpath!r} is outside the frozen S1 "
            f"allow-set (X7-01): {sorted(S1_ULP_ALLOW_SET)}")
        ok, _n_tok, worst = ulp_equivalent(
            (committed_dir / d.relpath).read_bytes(),
            (produced_dir / d.relpath).read_bytes(),
        )
        assert ok, (
            f"{d.relpath}: classified ulp-equivalent by the comparator but "
            "ulp_equivalent() rejects the byte pair")
        assert worst <= ULP_REL_TOL, (
            f"{d.relpath}: worst relative difference {worst:.3e} exceeds the "
            "seal module tolerance ULP_REL_TOL (imported constant)")


def test_schk_05_full_regeneration_s1(tmp_path: Path) -> None:
    """S1 v1.1 regeneration: zero failures, and float drift confined to the
    frozen allow-set within the module's own tolerance.

    This test does NOT claim byte identity. The committed seal's byte
    identity on Linux x86_64 is attested by the XREP Linux receipt; X7-01
    showed that a Linux x86_64 numpy 2.x interpreter itself regenerates the
    allow-set files ulp-equivalent (worst measured rel 4.76e-12, two orders
    below ULP_REL_TOL), so a live `ulp_equivalent == 0` platform pin was
    asserting something the seal never guaranteed. What the seal DOES
    guarantee — and what is asserted here — is: no failures, every ULP path
    inside the frozen allow-set, each within tolerance, and a complete
    accounting of every compared file."""
    _ensure_input_ref()
    out = tmp_path / "s1"
    res = check_study("s1", ROOT, INPUT_REF, out)
    print(
        f"s1: files compared={res.compared} identical={res.identical} "
        f"named-exception passes={res.named_exception_passes} "
        f"ulp-equivalent={res.ulp_equivalent} failures={res.failures} "
        f"[{res.host_platform}]"
    )
    for d in res.diffs:
        print(f"  {d.kind}: {d.relpath} {d.detail}")
    assert res.failures == 0
    assert res.compared == len(rel_files(ROOT / S1_V1_1_REL))
    assert res.named_exception_passes >= 4  # SEAL json, SEAL md, ledger ts, manifest seal commit
    assert (res.identical + res.named_exception_passes + res.ulp_equivalent
            == res.compared)
    _assert_regen_accounting(res, S1_V1_1_REL)
    _assert_s1_ulp_allow_set(
        [d for d in res.diffs if d.kind == KIND_ULP], ROOT / S1_V1_1_REL, out)


def test_schk_05b_allow_set_is_tight(tmp_path: Path) -> None:
    """NON-WEAKENING companion to schk_05: a ulp-equivalent path OUTSIDE the
    frozen allow-set fails the assertion, and so does an in-set path whose
    difference exceeds the module tolerance. Driven with fabricated Diff
    objects and synthetic byte pairs — no regeneration, no input_ref."""
    committed = tmp_path / "committed"
    produced = tmp_path / "produced"
    (committed / "results").mkdir(parents=True)
    (produced / "results").mkdir(parents=True)
    in_set = "results/P03.json"
    (committed / in_set).write_text(f'{{"m": {_SEAL_TOK}}}\n', encoding="utf-8")
    (produced / in_set).write_text(f'{{"m": {_MAC_TOK}}}\n', encoding="utf-8")

    # in-set and within tolerance: the schk_05 assertion holds
    _assert_s1_ulp_allow_set([Diff(KIND_ULP, in_set, "")], committed, produced)

    # outside the allow-set: fails on membership alone (bytes never read)
    outside = Diff(KIND_ULP, "observations/P99_synthetic_21.json", "")
    with pytest.raises(AssertionError, match="outside the frozen S1"):
        _assert_s1_ulp_allow_set([outside], committed, produced)

    # in-set but beyond the module tolerance: fails the tolerance check
    (committed / in_set).write_text('{"m": 0.123456}\n', encoding="utf-8")
    (produced / in_set).write_text('{"m": 0.123457}\n', encoding="utf-8")
    with pytest.raises(AssertionError):
        _assert_s1_ulp_allow_set([Diff(KIND_ULP, in_set, "")], committed, produced)


def test_schk_05c_tolerance_not_loosened() -> None:
    """The imported tolerance constants equal the values the seal module
    ships: pinned from the module attribute at import AND from an AST read
    of the module source against this test's frozen expectation, so a silent
    edit of either side fails (X7-01 repair: schk_05 now leans on
    ULP_REL_TOL, so the constant itself must be pinned)."""
    import ast

    import seal_full_check as _sfc

    frozen = {"ULP_REL_TOL": 1e-10, "ULP_ABS_TOL": 1e-13}
    for name, want in frozen.items():
        got_attr = getattr(_sfc, name)
        assert got_attr == want, (
            f"seal module {name} is {got_attr!r} at import; the SCHK float "
            "tolerance was loosened")

    src = Path(_sfc.__file__).read_text(encoding="utf-8")
    literals: dict[str, object] = {}
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in frozen:
                    assert isinstance(node.value, ast.Constant), (
                        f"{target.id} must stay a literal constant assignment")
                    literals[target.id] = node.value.value
    assert set(literals) == set(frozen), (
        f"AST read of the seal module found {sorted(literals)}; "
        f"expected {sorted(frozen)}")
    for name, want in frozen.items():
        assert literals[name] == want, (
            f"seal module source assigns {name} = {literals[name]!r}; "
            f"expected the shipped {want!r}")


def test_schk_06_full_regeneration_s2(tmp_path: Path) -> None:
    _ensure_input_ref()
    out = tmp_path / "s2"
    res = check_study("s2", ROOT, INPUT_REF, out)
    print(
        f"s2: files compared={res.compared} identical={res.identical} "
        f"named-exception passes={res.named_exception_passes} "
        f"ulp-equivalent={res.ulp_equivalent} failures={res.failures} "
        f"[{res.host_platform}]"
    )
    for d in res.diffs:
        print(f"  {d.kind}: {d.relpath} {d.detail}")
    assert res.failures == 0
    assert res.compared == len(rel_files(ROOT / S2_V1_1_REL))
    assert res.named_exception_passes >= 2  # ledger ts + XREP-04 pin
    _assert_regen_accounting(res, S2_V1_1_REL)
    # walk_compare used the S2 exception map; XREP-04 is committed-bytes only.
    assert "SEAL_AND_BUDGET.json" not in s2_exceptions()
    assert "LANE_MANIFEST.json" not in s2_exceptions()
    assert "trial_ledger.jsonl" in s1_exceptions()


# Measured macOS arm64 vs seal (Linux) drift, P03 observations, 2026-10-13.
_SEAL_TOK = "1.5031136678667067e-06"
_MAC_TOK = "1.5031136678597679e-06"


def test_schk_07_ulp_classifier_is_narrow() -> None:
    def j(v, n=5) -> bytes:
        return f'{{"horizon": {n}, "mean": {v}, "id": "P03_hkd_0700"}}\n'.encode()

    ok, n_tok, worst = ulp_equivalent(j(_SEAL_TOK), j(_MAC_TOK))
    assert ok and n_tok == 1 and 0 < worst < 1e-10
    assert ulp_equivalent(j("0.25"), j("0.25")) == (True, 0, 0.0)
    # integer token change is never tolerated
    assert not ulp_equivalent(j(_SEAL_TOK, 5), j(_SEAL_TOK, 6))[0]
    # int <-> float spelling change is never tolerated
    assert not ulp_equivalent(j("1"), j("1.0"))[0]
    # structural (non-numeric) change is never tolerated
    assert not ulp_equivalent(j(_SEAL_TOK), j(_SEAL_TOK).replace(b"P03", b"P04"))[0]
    # a float difference beyond tolerance is a real difference
    assert not ulp_equivalent(j("0.123456"), j("0.123457"))[0]
    assert not ulp_equivalent(j("1.0e-05"), j("1.1e-05"))[0]
    # token-count change is never tolerated
    assert not ulp_equivalent(b"[1.0, 2.0]", b"[1.0, 2.0, 3.0]")[0]
    # undecodable bytes are never tolerated
    assert not ulp_equivalent(b"\xff\xfe1.0", b"\xff\xfe1.0000000000001")[0]


def test_schk_08_walk_compare_tolerance_is_opt_in_and_text_only(tmp_path: Path) -> None:
    committed = tmp_path / "committed"
    produced = tmp_path / "produced"
    committed.mkdir()
    produced.mkdir()
    for name in ("obs.json", "obs.parquet"):
        (committed / name).write_text(f'{{"m": {_SEAL_TOK}}}\n', encoding="utf-8")
        (produced / name).write_text(f'{{"m": {_MAC_TOK}}}\n', encoding="utf-8")

    strict = walk_compare(committed, produced, {})
    assert {(d.kind, d.relpath) for d in strict} == {
        (KIND_DIFFER, "obs.json"), (KIND_DIFFER, "obs.parquet")}

    tolerant = walk_compare(committed, produced, {}, ulp_tolerant=True)
    assert {(d.kind, d.relpath) for d in tolerant} == {
        (KIND_ULP, "obs.json"), (KIND_DIFFER, "obs.parquet")}

    # exception-handled files keep their own comparator even when tolerant
    def _refuse(c: Path, p: Path):
        return [] if c.read_bytes() == p.read_bytes() else [
            type(strict[0])(KIND_DIFFER, "obs.json", "exception")]

    via_exc = walk_compare(committed, produced, {"obs.json": _refuse}, ulp_tolerant=True)
    assert (KIND_DIFFER, "obs.json") in {(d.kind, d.relpath) for d in via_exc}


def test_schk_09_s1_builder_survives_event_response_shadowing() -> None:
    """residual/ and event_response/ both ship build_seal.py. A caller that put
    event_response/ ahead on sys.path (test_sni_missing_not_zero does) used to
    make regenerate_s1's bare `import build_seal` bind the S2 builder and die
    with `no attribute 'build_all'`. The loader binds residual/ by file path."""
    sni = ROOT / "research" / "single_name_intelligence"
    event_dir = str(sni / "event_response")
    saved_path = list(sys.path)
    saved_bare = sys.modules.pop("build_seal", None)
    saved_s1 = sys.modules.pop(S1_BUILD_SEAL_MODULE, None)
    try:
        # the real failure order: residual/ present, event_response/ ahead of it
        sys.path.insert(0, str(sni / "residual"))
        sys.path.insert(0, event_dir)
        import build_seal as shadow  # noqa: WPS433

        assert Path(shadow.__file__).resolve().parent == (sni / "event_response").resolve()
        mod = _load_s1_build_seal(ROOT)
        assert hasattr(mod, "build_all")
        assert Path(mod.__file__).resolve() == (sni / "residual" / "build_seal.py").resolve()
        assert sys.modules["build_seal"] is shadow  # the bare name is left alone
        assert _load_s1_build_seal(ROOT) is mod  # cached under its private name
    finally:
        sys.path[:] = saved_path
        sys.modules.pop("build_seal", None)
        sys.modules.pop(S1_BUILD_SEAL_MODULE, None)
        if saved_bare is not None:
            sys.modules["build_seal"] = saved_bare
        if saved_s1 is not None:
            sys.modules[S1_BUILD_SEAL_MODULE] = saved_s1


S1_RESIDUAL_REL = "research/single_name_intelligence/residual"


def _collect_key(node, key: str, out: set[str]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and isinstance(v, str):
                out.add(v)
            _collect_key(v, key, out)
    elif isinstance(node, list):
        for v in node:
            _collect_key(v, key, out)


def test_schk_10_residual_tree_is_the_sealed_v1_1_runner() -> None:
    """S1 receipts stamp code_tree_sha = HEAD:residual/ (run_s1.code_tree_sha),
    so ANY committed edit under residual/ makes v1.1 regeneration differ in
    every results/P0x.json and REPORT.md. The runner is sealed code: a change
    to it is a new registered version with its own seal (v1 -> v1.1 moved the
    stamp 44377b14 -> f9f4bf64), never an edit beneath a sealed run. Fast,
    git-local, and needs no input_ref, so it fires where schk_05 skips."""
    stamps: set[str] = set()
    for p in sorted((ROOT / S1_V1_1_REL / "results").glob("*.json")):
        _collect_key(json.loads(p.read_text(encoding="utf-8")), "code_tree_sha", stamps)
    assert len(stamps) == 1, f"sealed v1.1 results carry {sorted(stamps)}"
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", f"HEAD:{S1_RESIDUAL_REL}"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        pytest.skip("not a git checkout; HEAD:residual unresolvable")
    sealed = next(iter(stamps))
    assert proc.stdout.strip() == sealed, (
        f"HEAD:{S1_RESIDUAL_REL} is {proc.stdout.strip()} but sealed v1.1 "
        f"receipts stamp {sealed}: the S1 runner is sealed — register a new "
        "version instead of editing residual/ under the v1.1 seal"
    )


# --- XREP-05: S1 LANE_MANIFEST.json seal_commit_sha squash exception -------

_SYNTH_MANIFEST = {
    "lane": "s1_residual",
    "version": "v1.1",
    "input_ref": INPUT_REF,
    "authority_flags": {"rank": False, "gate": False, "size": False,
                        "signal": False, "escalation": False, "trade": False},
}


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True) + "\n", encoding="utf-8")


def _regen_seal_commit_sha() -> str:
    """What residual/run_s1.py seal_commit_sha() answers on THIS checkout:
    the last commit that touched the S1 v1.1 seal path (the squash commit on
    any post-PR-9120 clone)."""
    r = subprocess.run(
        ["git", "log", "--format=%H", "-n", "1", "--",
         f"{S1_V1_1_REL}/SEAL_AND_BUDGET.json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0 and r.stdout.strip(), r.stderr
    return r.stdout.strip()


def test_xrep05_passes_on_seal_commit_only_diff(tmp_path: Path) -> None:
    """The real defect shape: the committed manifest carries the pre-squash
    sha, regeneration answers the post-squash git log sha, and XREP-05
    passes (seal blob identical at both commits). Synthetic dirs, no
    regeneration; the produced sha is what this checkout would really
    stamp."""
    src = ROOT / S1_V1_1_REL / "LANE_MANIFEST.json"
    c_obj = json.loads(src.read_text(encoding="utf-8"))
    assert c_obj["seal_commit_sha"] == S1_V1_1_SEAL_COMMIT_PRE_SQUASH
    p_obj = dict(c_obj)
    p_obj["seal_commit_sha"] = _regen_seal_commit_sha()
    assert p_obj["seal_commit_sha"] != S1_V1_1_SEAL_COMMIT_PRE_SQUASH
    c = tmp_path / "committed" / "LANE_MANIFEST.json"
    p = tmp_path / "produced" / "LANE_MANIFEST.json"
    _write_json(c, c_obj)
    _write_json(p, p_obj)
    assert XREP05_S1_MANIFEST_SEAL_COMMIT(c, p) == []
    # the s1_exceptions() registration makes walk_compare report nothing
    assert walk_compare(c.parent, p.parent, s1_exceptions()) == []


def test_xrep05_fails_when_other_field_differs(tmp_path: Path) -> None:
    c_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=S1_V1_1_SEAL_COMMIT_PRE_SQUASH)
    p_obj = dict(c_obj)
    p_obj["version"] = "v9"
    c = tmp_path / "committed" / "LANE_MANIFEST.json"
    p = tmp_path / "produced" / "LANE_MANIFEST.json"
    _write_json(c, c_obj)
    _write_json(p, p_obj)
    diffs = XREP05_S1_MANIFEST_SEAL_COMMIT(c, p)
    assert any(d.kind == KIND_DIFFER for d in diffs)
    assert any("version" in d.detail for d in diffs)


def test_xrep05_fails_when_committed_sha_not_pinned_constant(tmp_path: Path) -> None:
    p_sha = _regen_seal_commit_sha()
    c_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=p_sha)  # real hex, wrong pin
    p_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=p_sha)
    c = tmp_path / "committed" / "LANE_MANIFEST.json"
    p = tmp_path / "produced" / "LANE_MANIFEST.json"
    _write_json(c, c_obj)
    _write_json(p, p_obj)
    diffs = XREP05_S1_MANIFEST_SEAL_COMMIT(c, p)
    assert any(d.kind == KIND_DIFFER for d in diffs)
    assert any("pinned pre-squash" in d.detail for d in diffs)


def test_xrep05_fails_on_nonhex_produced(tmp_path: Path) -> None:
    c_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=S1_V1_1_SEAL_COMMIT_PRE_SQUASH)
    bad_values = (
        "not-a-sha",
        S1_V1_1_SEAL_COMMIT_PRE_SQUASH.upper(),
        S1_V1_1_SEAL_COMMIT_PRE_SQUASH[:-1],
        "z" * 40,
        12345,
    )
    for bad in bad_values:
        p_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=bad)
        c = tmp_path / "committed" / "LANE_MANIFEST.json"
        p = tmp_path / "produced" / "LANE_MANIFEST.json"
        _write_json(c, c_obj)
        _write_json(p, p_obj)
        diffs = XREP05_S1_MANIFEST_SEAL_COMMIT(c, p)
        assert any(d.kind == KIND_DIFFER for d in diffs), f"{bad!r} was accepted"
        assert any("40-char lowercase hex" in d.detail for d in diffs), bad


def test_xrep05_registered_for_s1_manifest_only() -> None:
    assert s1_exceptions().get("LANE_MANIFEST.json") is XREP05_S1_MANIFEST_SEAL_COMMIT
    assert "LANE_MANIFEST.json" not in s2_exceptions()


# --- XREP-05 repair: pinned seal blob -------------------------------------

# A 40-char sha syntactically valid but not an object in this clone. The remote
# returns "not our ref" for this sha (it is not a real commit anywhere). Used
# as the "produced" sha in the refusal tests below.
UNRESOLVABLE_SHA = "0123456789abcdef0123456789abcdef01234567"


class _FakeCompleted:
    """Stand-in for subprocess.CompletedProcess returned by the wrapper.

    Mimics the fields the seal verifier reads from a real CompletedProcess.
    """

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _assert_unresolvable_sha(sha: str) -> None:
    """Best-effort: confirm sha is not an object in this clone.

    CI clones at depth 1 without partial clone, so ``git cat-file -e``
    fails immediately when the object is absent. This dev env is a
    partial clone (``remote.origin.promisor=true``): git may try to
    lazy-fetch missing blobs from the promisor and scan packs slowly.
    The 10s timeout bounds that scan; on timeout we trust the chosen
    deterministic sha (the seat's depth-1 CI will assert properly).
    """
    try:
        r = subprocess.run(
            ["git", "cat-file", "-e", sha],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
    except subprocess.TimeoutExpired:
        # Partial-clone env: cat-file hangs on pack scan for unknown sha.
        return
    assert r.returncode != 0, (
        f"{sha} resolved unexpectedly in this clone; pick another")


def _cat_file_off_wrapper(monkeypatch):
    """Patch ``seal_full_check.subprocess.run`` so any argv containing
    ``cat-file`` returns non-zero (simulates a depth-1 clone lacking the
    pre-squash commit). Every other call is delegated to the real
    ``subprocess.run``, with a 15s timeout so a partial-clone dev env's
    lazy-fetch on an unknown sha does not hang the test (CI is depth-1
    and returns instantly).
    """
    import seal_full_check  # late import: monkeypatch target
    real_run = seal_full_check.subprocess.run

    def _wrapper(argv, *args, **kwargs):
        if any("cat-file" in str(a) for a in argv):
            return _FakeCompleted(
                returncode=1, stderr="cat-file monkeypatched off")
        kwargs.setdefault("timeout", 15)
        try:
            return real_run(argv, *args, **kwargs)
        except subprocess.TimeoutExpired as e:
            return _FakeCompleted(returncode=124, stderr=str(e))

    monkeypatch.setattr(seal_full_check.subprocess, "run", _wrapper)
    return _wrapper


def _timeout_subprocess_wrapper(monkeypatch):
    """Patch ``seal_full_check.subprocess.run`` with a 15s timeout on every
    call so a partial-clone dev env's lazy-fetch on an unknown sha does
    not hang the test (CI is depth-1 and returns instantly). The wrapper
    does not fake any return; it just bounds the call duration.
    """
    import seal_full_check
    real_run = seal_full_check.subprocess.run

    def _wrapper(argv, *args, **kwargs):
        kwargs.setdefault("timeout", 15)
        try:
            return real_run(argv, *args, **kwargs)
        except subprocess.TimeoutExpired as e:
            return _FakeCompleted(returncode=124, stderr=str(e))

    monkeypatch.setattr(seal_full_check.subprocess, "run", _wrapper)
    return _wrapper


def test_xrep05_seal_blob_constant_matches_head() -> None:
    """The pinned S1_V1_1_SEAL_BLOB must equal HEAD's blob at the S1 v1.1
    SEAL_AND_BUDGET.json path. If HEAD's blob drifts, the pin must be
    re-cut (this is the constant-drift catcher)."""
    from seal_full_check import S1_V1_1_SEAL_BLOB
    r = subprocess.run(
        ["git", "rev-parse", f"HEAD:{S1_V1_1_REL}/SEAL_AND_BUDGET.json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == S1_V1_1_SEAL_BLOB, (
        f"HEAD blob {r.stdout.strip()!r} drifted from pinned "
        f"{S1_V1_1_SEAL_BLOB!r}; the pin must be re-cut")


def test_xrep05_fails_on_unresolvable_produced_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A produced sha that is syntactically valid 40-char hex but not an
    object in this clone must produce a KIND_DIFFER Diff whose detail
    contains ``unresolvable``. The pre-squash commit is NOT mocked here;
    this is the produced-side gate. CI clones at depth 1, so no
    git-history reads.
    """
    _assert_unresolvable_sha(UNRESOLVABLE_SHA)

    # Bound git calls so a partial-clone dev env's lazy-fetch on the
    # unresolvable sha does not hang the test. CI (depth-1) returns
    # instantly. The wrapper does not fake any return; it just adds a
    # 15s timeout that yields a non-zero exit on hang.
    _timeout_subprocess_wrapper(monkeypatch)

    c_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=S1_V1_1_SEAL_COMMIT_PRE_SQUASH)
    p_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=UNRESOLVABLE_SHA)
    c = tmp_path / "committed" / "LANE_MANIFEST.json"
    p = tmp_path / "produced" / "LANE_MANIFEST.json"
    _write_json(c, c_obj)
    _write_json(p, p_obj)
    diffs = XREP05_S1_MANIFEST_SEAL_COMMIT(c, p)
    differ = [d for d in diffs if d.kind == KIND_DIFFER]
    assert len(differ) == 1, (
        f"expected exactly one KIND_DIFFER, got {diffs!r}")
    assert "unresolvable" in differ[0].detail, differ[0].detail
    assert UNRESOLVABLE_SHA in differ[0].detail, differ[0].detail


def test_xrep05_checks_blob_when_presquash_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail-first test: when the pre-squash commit object is absent
    (cat-file returns non-zero) AND the produced sha is unresolvable,
    the function MUST raise a Diff. On the base bytes the function
    returns ``[]`` (fail-open); this test FAILS on base and passes only
    after the seal_blob pin is added.
    """
    _cat_file_off_wrapper(monkeypatch)

    c_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=S1_V1_1_SEAL_COMMIT_PRE_SQUASH)
    p_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=UNRESOLVABLE_SHA)
    c = tmp_path / "committed" / "LANE_MANIFEST.json"
    p = tmp_path / "produced" / "LANE_MANIFEST.json"
    _write_json(c, c_obj)
    _write_json(p, p_obj)
    diffs = XREP05_S1_MANIFEST_SEAL_COMMIT(c, p)
    assert any(d.kind == KIND_DIFFER for d in diffs), (
        f"expected a Diff when produced sha is unresolvable and pre-squash "
        f"is absent; got {diffs!r}")


def test_xrep05_still_passes_head_when_presquash_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the pre-squash commit is absent but the produced sha
    resolves to the pinned seal blob (HEAD on every clone, including
    depth-1), the function passes. Same wrapper as the fail-first
    test; produced sha = ``git rev-parse HEAD``. Passes on base by
    accident (function returns ``[]``); the value of this test is the
    contract it locks in after the repair.
    """
    import seal_full_check
    pinned = getattr(seal_full_check, "S1_V1_1_SEAL_BLOB", None)

    head_proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert head_proc.returncode == 0, head_proc.stderr
    head_sha = head_proc.stdout.strip()

    # Sanity (post-repair only): HEAD:SEAL_AND_BUDGET.json resolves to the
    # pinned blob here. On base the sanity is skipped because the constant
    # does not yet exist; the test still passes on base by accident.
    if pinned is not None:
        blob_proc = subprocess.run(
            ["git", "rev-parse", f"{head_sha}:{S1_V1_1_REL}/SEAL_AND_BUDGET.json"],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert blob_proc.returncode == 0, blob_proc.stderr
        assert blob_proc.stdout.strip() == pinned

    _cat_file_off_wrapper(monkeypatch)

    c_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=S1_V1_1_SEAL_COMMIT_PRE_SQUASH)
    p_obj = dict(_SYNTH_MANIFEST, seal_commit_sha=head_sha)
    c = tmp_path / "committed" / "LANE_MANIFEST.json"
    p = tmp_path / "produced" / "LANE_MANIFEST.json"
    _write_json(c, c_obj)
    _write_json(p, p_obj)
    assert XREP05_S1_MANIFEST_SEAL_COMMIT(c, p) == []
