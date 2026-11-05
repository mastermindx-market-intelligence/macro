"""M6D mutation-sweep killing tests for the seal_full_check CLI surface.

Targets the surviving mutants of the 2026-10-14 sweep over the owned site
range of research/single_name_intelligence/evaluation/seal_full_check.py
(functions ``main``, ``_print_result``, ``_walk_authority``,
``_load_s1_build_seal``). Each test's docstring names the exact mutant
(file:line, original -> mutated) it was written to kill; every kill claim was
re-verified by re-applying that mutant and watching this file fail.

No git-history reads and no network here (CI is depth-1); the CLI is driven
only with fake/absent input refs and tmp_path roots, never against the
committed runs/ tree in write mode.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "evaluation"))

import seal_full_check as sfc  # noqa: E402
from seal_full_check import StudyResult, S1_BUILD_SEAL_MODULE  # noqa: E402


class _Proc:
    def __init__(self, returncode: int, stdout, stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_m6d_seal_full_check_main_1(tmp_path: Path) -> None:
    """Mutant seal_full_check.py:665 `required=True` -> `required=False`.

    With --study no longer required, argparse must not exit; the unmutated
    CLI refuses to guess a study and exits 2 via argparse.
    """
    with pytest.raises(SystemExit) as ei:
        sfc.main(["--repo-root", str(tmp_path)])
    assert ei.value.code == 2


def test_m6d_seal_full_check_main_2(tmp_path: Path, monkeypatch, capsys) -> None:
    """Mutants seal_full_check.py:679 `capture_output=True` -> False and
    `text=True` -> False (two True constants on that line).

    The git rev-parse probe must capture and decode; the fake honours the
    kwargs so a flipped flag yields None/bytes stdout and blows up before
    the REFUSED line can be printed.
    """
    def fake_run(cmd, **kw):
        out = str(tmp_path) + "\n"
        if kw.get("capture_output") is False:
            return _Proc(0, None, None)
        if kw.get("text") is False:
            return _Proc(0, out.encode(), b"")
        return _Proc(0, out, "")

    monkeypatch.setattr(sfc, "input_ref_present", lambda root, ref: False)
    rc = sfc.main(["--study", "s1"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "SEAL FULL CHECK: REFUSED" in captured.out
    assert "not inside a git checkout" not in captured.err


def test_m6d_seal_full_check_main_3(tmp_path: Path, monkeypatch, capsys) -> None:
    """Mutants seal_full_check.py:681 `proc.returncode != 0` -> `!= 1` and
    `!=` -> `==`: a successful git probe must not be treated as failure."""
    def fake_run(cmd, **kw):
        return _Proc(0, str(tmp_path) + "\n", "")

    monkeypatch.setattr(sfc, "input_ref_present", lambda root, ref: False)
    rc = sfc.main(["--study", "s1"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "not inside a git checkout" not in captured.err
    assert "SEAL FULL CHECK: REFUSED" in captured.out


def test_m6d_seal_full_check_main_4(tmp_path: Path, monkeypatch, capsys) -> None:
    """Mutant seal_full_check.py:683 `return 2` -> `return 3`: a failed git
    rev-parse must exit exactly 2 with the stderr hint."""
    monkeypatch.setattr(
        sfc.subprocess, "run", lambda cmd, **kw: _Proc(1, "", "fatal: not a git repo")
    )
    rc = sfc.main(["--study", "s1"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "not inside a git checkout" in captured.err


def test_m6d_seal_full_check_main_5(tmp_path: Path, monkeypatch, capsys) -> None:
    """Mutants seal_full_check.py:688 `return 2` -> `return 3` and
    `return 2` -> `return None`: an absent input_ref must exit exactly 2
    (never fetched)."""
    monkeypatch.setattr(sfc, "input_ref_present", lambda root, ref: False)
    rc = sfc.main(["--study", "s1", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "SEAL FULL CHECK: REFUSED" in captured.out
    assert "never fetched" in captured.out


def test_m6d_seal_full_check_main_6(tmp_path: Path, monkeypatch, capsys) -> None:
    """Mutants seal_full_check.py:690 `args.study == "all"` -> `!=`;
    :693 `failed = False` -> `True`; :726 `return 0` -> `return 1`.

    With input_ref, porcelain and check_study faked, --study all must visit
    exactly (s1, s2) and exit 0 with the OK line.
    """
    seen: list[str] = []

    def fake_check(name, repo_root, input_ref, tmp, strict_bytes=False):
        seen.append(name)
        return StudyResult(name=name, compared=2, identical=2)

    monkeypatch.setattr(sfc, "input_ref_present", lambda root, ref: True)
    monkeypatch.setattr(sfc, "_porcelain", lambda root: "PORC")
    monkeypatch.setattr(sfc, "check_study", fake_check)
    rc = sfc.main(["--study", "all", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert seen == ["s1", "s2"]
    assert "SEAL FULL CHECK: OK" in captured.out


def test_m6d_seal_full_check_main_7(tmp_path: Path, monkeypatch, capsys) -> None:
    """Mutants seal_full_check.py:718 `results[0]` -> `results[1]` and
    :724 `return 0` -> `return 1`: a clean single study with ulp-equivalent
    files must exit 0 with the float-equivalent OK line."""
    monkeypatch.setattr(sfc, "input_ref_present", lambda root, ref: True)
    monkeypatch.setattr(sfc, "_porcelain", lambda root: "PORC")
    monkeypatch.setattr(
        sfc, "check_study",
        lambda name, repo_root, input_ref, tmp, strict_bytes=False:
            StudyResult(name=name, compared=2, identical=0, ulp_equivalent=2),
    )
    rc = sfc.main(["--study", "s1", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "float-equivalent" in captured.out


def test_m6d_seal_full_check_main_8(tmp_path: Path, monkeypatch, capsys) -> None:
    """Mutants seal_full_check.py:707 `after != before` -> `==` and
    :711 `return 1` -> `return 2`: porcelain drift after regeneration must
    exit exactly 1 with DIFFERS on stderr."""
    monkeypatch.setattr(sfc, "input_ref_present", lambda root, ref: True)
    monkeypatch.setattr(sfc, "_porcelain", lambda root: "PORC-BEFORE")
    state = {"n": 0}

    def drift(root):
        state["n"] += 1
        return "PORC-BEFORE" if state["n"] == 1 else "PORC-AFTER"

    monkeypatch.setattr(sfc, "_porcelain", drift)
    monkeypatch.setattr(
        sfc, "check_study",
        lambda name, repo_root, input_ref, tmp, strict_bytes=False:
            StudyResult(name=name, compared=2, identical=2),
    )
    rc = sfc.main(["--study", "s1", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "SEAL FULL CHECK: DIFFERS" in captured.err


def test_m6d_seal_full_check__walk_authority_1() -> None:
    """Mutant seal_full_check.py:154 `or` -> `and` in the authority-key
    match: a truthy authority flag under any of the three spellings must
    still be refused."""
    with pytest.raises(ValueError, match="not literal False"):
        sfc.refuse_nonfalse_authority({"trade_authority": True})
    with pytest.raises(ValueError, match="not literal False"):
        sfc.refuse_nonfalse_authority({"gate": 1})
    with pytest.raises(ValueError, match="not literal False"):
        sfc.refuse_nonfalse_authority({"nested": {"whatever_authority": "yes"}})


def test_m6d_seal_full_check__load_s1_build_seal_1(tmp_path: Path, monkeypatch) -> None:
    """Mutant seal_full_check.py:499 `or` -> `and` in the spec guard: an
    unloadable build_seal spec must raise ImportError, not dereference a
    None spec or limp on."""
    import importlib.util

    monkeypatch.setattr(
        importlib.util, "spec_from_file_location",
        lambda name, path: None,
    )
    with pytest.raises(ImportError, match="cannot load S1 seal builder"):
        sfc._load_s1_build_seal(tmp_path)


def test_m6d_seal_full_check__load_s1_build_seal_2(monkeypatch) -> None:
    """Mutant seal_full_check.py:496 `and` -> `or` in the cached-module
    check: a cached module whose __file__ is NOT residual/build_seal.py must
    be ignored and the real S1 builder loaded."""
    fake = types.ModuleType(S1_BUILD_SEAL_MODULE)
    fake.__file__ = "/elsewhere/event_response/build_seal.py"
    # setitem restores the pre-test entry (or its absence) at teardown, even
    # after the loader replaces the fake with the real builder.
    monkeypatch.setitem(sys.modules, S1_BUILD_SEAL_MODULE, fake)
    monkeypatch.syspath_prepend(
        str(ROOT / "research" / "single_name_intelligence" / "residual"))
    mod = sfc._load_s1_build_seal(ROOT)
    assert mod is not fake
    assert mod.__file__ == str(
        (ROOT / "research" / "single_name_intelligence" / "residual"
         / "build_seal.py").resolve()
    )
    assert hasattr(mod, "build_all")
