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
    INPUT_REF_DEFAULT,
    KIND_DIFFER,
    KIND_EXTRA,
    KIND_MISSING,
    KIND_ULP,
    ULP_TEXT_SUFFIXES,
    S1_V1_1_REL,
    S1_V1_1_TRIAL_LEDGER_PATH,
    S1_V1_TRIAL_LEDGER_PATH,
    S2_V1_1_REL,
    S2_V1_1_TRIAL_LEDGER_PATH,
    S2_V1_TRIAL_LEDGER_PATH,
    XREP03_S1_SEAL_LEDGER_PATH,
    XREP04_S2_SEAL_V1_LEDGER_PATH,
    check_study,
    rel_files,
    s1_exceptions,
    s2_exceptions,
    ulp_equivalent,
    walk_compare,
)

INPUT_REF = INPUT_REF_DEFAULT


def _assert_regen_accounting(res, committed_rel: str) -> None:
    """ULP-equivalent files are text, never counted identical, and never on
    the Linux x86_64 platform the seal was cut on (byte identity is pinned
    there by the XREP receipt)."""
    import platform as _pf

    ulp_rels = [d.relpath for d in res.diffs if d.kind == KIND_ULP]
    assert len(ulp_rels) == res.ulp_equivalent
    assert all(r.endswith(ULP_TEXT_SUFFIXES) for r in ulp_rels)
    assert res.failures == len(res.diffs) - res.ulp_equivalent
    assert res.identical + res.ulp_equivalent <= len(rel_files(ROOT / committed_rel))
    if _pf.system() == "Linux" and _pf.machine() == "x86_64":
        assert res.ulp_equivalent == 0, "seal platform must reproduce byte-identically"


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


def test_schk_05_full_regeneration_s1(tmp_path: Path) -> None:
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
    assert res.named_exception_passes >= 3  # SEAL json, SEAL md, ledger ts
    _assert_regen_accounting(res, S1_V1_1_REL)


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
