"""Killing tests for MUT3A survivors in sni_eval_ledger.py and seal_full_check.py.

SNI-local DRAFT contract tests. Fixtures are synthetic. Authority flags stay
false. This file does not mint issuer or security identifiers and does not
feed a rank, gate, size, signal, escalation, or trade path.
"""
from __future__ import annotations

import json
import sys
import types
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/evaluation"),
)

import seal_full_check  # noqa: E402
from sni_eval_ledger import (  # noqa: E402
    BUDGET,
    REGISTER,
    EvalLedger,
    LedgerRefused,
    LedgerRow,
    _canonical,
)
from seal_full_check import (  # noqa: E402
    KIND_DIFFER,
    S1_V1_1_TRIAL_LEDGER_PATH,
    S2_V1_1_TRIAL_LEDGER_PATH,
    S2_V1_TRIAL_LEDGER_PATH,
    ULP_REL_TOL,
    XREP03_S1_SEAL_LEDGER_PATH,
    XREP04_S2_SEAL_V1_LEDGER_PATH,
    Diff,
    StudyResult,
    _porcelain,
    _prepare_s1_imports,
    _s1_ledger_exception,
    _s2_ledger_exception,
    check_study,
    input_ref_present,
    main,
    regenerate_s1,
    regenerate_s2,
    rel_files,
    s1_exceptions,
    s2_exceptions,
)

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "a" * 64


def _led(tmp_path, name="eval.jsonl"):
    return EvalLedger(tmp_path / name)


def _prep(led, family_id="fam-a", n=2):
    led.append(REGISTER, {
        "family_id": family_id,
        "protocol": "sni.v0",
        "version": "1",
        "split": "test",
        "h": 21,
        "prereg_digest": DIGEST,
    })
    led.append(BUDGET, {"family_id": family_id, "declared_trials": n})


def _xrep03_json_pair(tmp_path, committed_extra=None, produced_extra=None):
    committed = tmp_path / "committed"
    produced = tmp_path / "produced"
    committed.mkdir()
    produced.mkdir()
    base = {
        "lane": "s1_residual",
        "version": "v1.1",
        "trial_ledger_path": S1_V1_1_TRIAL_LEDGER_PATH,
    }
    c_obj = dict(base)
    p_obj = dict(base)
    p_obj["trial_ledger_path"] = "research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl"
    if committed_extra:
        c_obj.update(committed_extra)
    if produced_extra:
        p_obj.update(produced_extra)
    (committed / "SEAL_AND_BUDGET.json").write_text(
        json.dumps(c_obj, sort_keys=True) + "\n", encoding="utf-8")
    (produced / "SEAL_AND_BUDGET.json").write_text(
        json.dumps(p_obj, sort_keys=True) + "\n", encoding="utf-8")
    return committed / "SEAL_AND_BUDGET.json", produced / "SEAL_AND_BUDGET.json"


def _xrep04_dir(tmp_path, seal_path=S2_V1_TRIAL_LEDGER_PATH, lane_path=S2_V1_1_TRIAL_LEDGER_PATH):
    d = tmp_path / "s2"
    d.mkdir()
    (d / "SEAL_AND_BUDGET.json").write_text(
        json.dumps({"trial_ledger_path": seal_path}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (d / "LANE_MANIFEST.json").write_text(
        json.dumps({"trial_ledger_path": lane_path}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return d


# ---------------------------------------------------------------------------
# sni_eval_ledger survivors
# ---------------------------------------------------------------------------


def test_mut3a_sni_eval_ledger_EvalLedger_assert_replay_equal_1(tmp_path):
    """sni_eval_ledger.py:799, not A or not B -> not A and not B (assert_replay_equal)."""
    led = _led(tmp_path)
    _prep(led)
    led._incremental["counts"]["rows"] = 999999
    with pytest.raises(LedgerRefused) as ei:
        led.assert_replay_equal()
    assert ei.value.code == "REPLAY_MISMATCH"


def test_mut3a_sni_eval_ledger_LedgerRefused_init_1():
    """sni_eval_ledger.py:146, delete if code not in REFUSAL_CODES: raise ValueError."""
    with pytest.raises(ValueError, match="unknown refusal code"):
        LedgerRefused("NOT_A_REAL_CODE")


def test_mut3a_sni_eval_ledger_LedgerRow_to_dict_1():
    """sni_eval_ledger.py:163, return { ... } -> return None (LedgerRow.to_dict)."""
    row = LedgerRow(
        seq=1,
        kind=REGISTER,
        written_at_utc="2020-01-01T00:00:00Z",
        payload={"family_id": "fam-a"},
        prev_hash=None,
        row_hash="b" * 64,
    )
    payload = row.to_dict()
    assert isinstance(payload, dict)
    assert payload["seq"] == 1
    assert payload["kind"] == REGISTER
    assert payload["payload"]["family_id"] == "fam-a"
    assert payload["prev_hash"] is None
    assert payload["row_hash"] == "b" * 64


def test_mut3a_sni_eval_ledger__canonical_1():
    """sni_eval_ledger.py:188, sort_keys=True -> False (_canonical)."""
    text = _canonical({"b": 1, "a": 2})
    assert text.index('"a"') < text.index('"b"')


# ---------------------------------------------------------------------------
# seal_full_check survivors
# ---------------------------------------------------------------------------


def test_mut3a_seal_full_check_module_1():
    """seal_full_check.py:109, ULP_REL_TOL 1e-10 -> 1.001e-10."""
    assert ULP_REL_TOL == 1e-10


def test_mut3a_seal_full_check_Diff_1():
    """seal_full_check.py:117, frozen=True -> False (Diff)."""
    diff = Diff(KIND_DIFFER, "a.txt")
    with pytest.raises(FrozenInstanceError):
        diff.kind = "x"  # type: ignore[misc]


def test_mut3a_seal_full_check_StudyResult_1():
    """seal_full_check.py:128, identical: int = 0 -> 1 (StudyResult default)."""
    assert StudyResult(name="s1").identical == 0


def test_mut3a_seal_full_check_StudyResult_2():
    """seal_full_check.py:129, named_exception_passes: int = 0 -> 1 (StudyResult default)."""
    assert StudyResult(name="s1").named_exception_passes == 0


def test_mut3a_seal_full_check_XREP04_S2_SEAL_V1_LEDGER_PATH_1(tmp_path):
    """seal_full_check.py:363, Path / 'SEAL_AND_BUDGET.json' -> Path * str."""
    d = _xrep04_dir(tmp_path)
    assert XREP04_S2_SEAL_V1_LEDGER_PATH(d) == []


def test_mut3a_seal_full_check_XREP04_S2_SEAL_V1_LEDGER_PATH_2(tmp_path):
    """seal_full_check.py:375, got_lane != S2_V1_1_TRIAL_LEDGER_PATH -> ==."""
    d = _xrep04_dir(tmp_path, lane_path="not-the-pinned-v1.1-path")
    diffs = XREP04_S2_SEAL_V1_LEDGER_PATH(d)
    assert diffs
    assert any(x.relpath == "LANE_MANIFEST.json" for x in diffs)


def test_mut3a_seal_full_check__porcelain_1():
    """seal_full_check.py:449, subprocess text=True -> False (_porcelain)."""
    out = _porcelain(ROOT)
    assert isinstance(out, str)


def test_mut3a_seal_full_check__porcelain_2():
    """seal_full_check.py:451, return r.stdout -> return None (_porcelain)."""
    out = _porcelain(ROOT)
    assert out is not None


def test_mut3a_seal_full_check__prepare_s1_imports_1():
    """seal_full_check.py:468, p / 'research' -> p * 'research' (_prepare_s1_imports)."""
    got = _prepare_s1_imports(ROOT)
    assert isinstance(got, Path)


def test_mut3a_seal_full_check__s1_ledger_exception_1(tmp_path, monkeypatch):
    """seal_full_check.py:394, return [Diff(...)] -> return None (_s1_ledger_exception)."""
    fake = types.ModuleType("run_s1")
    fake._ledger_equal = lambda committed, produced: False
    monkeypatch.setitem(sys.modules, "run_s1", fake)
    committed = tmp_path / "c.jsonl"
    produced = tmp_path / "p.jsonl"
    committed.write_text("{}\n", encoding="utf-8")
    produced.write_text("{}\n", encoding="utf-8")
    diffs = _s1_ledger_exception(committed, produced)
    assert diffs is not None
    assert len(diffs) == 1
    assert diffs[0].kind == KIND_DIFFER
    assert diffs[0].relpath == "trial_ledger.jsonl"


def test_mut3a_seal_full_check__s2_ledger_exception_1(tmp_path):
    """seal_full_check.py:415, json.dumps(la) != json.dumps(lb) -> == (_s2_ledger_exception)."""
    committed = tmp_path / "c.jsonl"
    produced = tmp_path / "p.jsonl"
    committed.write_text('{"forecast_id":"f1","ts":"t"}\n', encoding="utf-8")
    produced.write_text('{"forecast_id":"f2","ts":"t"}\n', encoding="utf-8")
    diffs = _s2_ledger_exception(committed, produced)
    assert diffs
    assert diffs[0].kind == KIND_DIFFER


def test_mut3a_seal_full_check__s2_ledger_exception_rows_1(tmp_path):
    """seal_full_check.py:412, return out -> return None (_s2_ledger_exception.rows)."""
    committed = tmp_path / "c.jsonl"
    produced = tmp_path / "p.jsonl"
    committed.write_text('{"forecast_id":"f1"}\n', encoding="utf-8")
    produced.write_text('{"forecast_id":"f2"}\n', encoding="utf-8")
    diffs = _s2_ledger_exception(committed, produced)
    assert diffs is not None
    assert len(diffs) == 1
    assert diffs[0].kind == KIND_DIFFER


def test_mut3a_seal_full_check__xrep03_json_1(tmp_path):
    """seal_full_check.py:311, k in p_rest and values differ -> or (_xrep03_json)."""
    committed, produced = _xrep03_json_pair(tmp_path, produced_extra={"version": "v9"})
    diffs = XREP03_S1_SEAL_LEDGER_PATH(committed, produced)
    assert diffs
    assert "changed=['version']" in diffs[0].detail


def test_mut3a_seal_full_check__xrep03_md_1(tmp_path):
    """seal_full_check.py:343, c_rest != p_rest -> == (_xrep03_md)."""
    committed = tmp_path / "SEAL_AND_BUDGET.md"
    produced = tmp_path / "out.md"
    committed.write_text(
        f"- trial_ledger_path: {S1_V1_1_TRIAL_LEDGER_PATH}\n- version: v1.1\n",
        encoding="utf-8",
    )
    produced.write_text(
        "- trial_ledger_path: other/path.jsonl\n- version: v9\n",
        encoding="utf-8",
    )
    diffs = XREP03_S1_SEAL_LEDGER_PATH(committed, produced)
    assert diffs
    assert any("other than trial_ledger_path" in d.detail for d in diffs)


def test_mut3a_seal_full_check__xrep03_md_split_1(tmp_path):
    """seal_full_check.py:329, line.split(':', 1) -> split(':', 2) (_xrep03_md.split)."""
    committed = tmp_path / "SEAL_AND_BUDGET.md"
    produced = tmp_path / "out.md"
    weird = S1_V1_1_TRIAL_LEDGER_PATH + ":extra"
    committed.write_text(
        f"- trial_ledger_path: {weird}\n- version: v1.1\n",
        encoding="utf-8",
    )
    produced.write_text(
        f"- trial_ledger_path: {S1_V1_1_TRIAL_LEDGER_PATH}\n- version: v1.1\n",
        encoding="utf-8",
    )
    diffs = XREP03_S1_SEAL_LEDGER_PATH(committed, produced)
    assert diffs
    assert any("trial_ledger_path" in d.detail for d in diffs)


def test_mut3a_seal_full_check_check_study_1(tmp_path, monkeypatch):
    """seal_full_check.py:587, named_ok = 0 -> 1 (check_study)."""
    monkeypatch.setattr(seal_full_check, "regenerate_s1", lambda *a, **k: None)
    out = tmp_path / "out"
    res = check_study("s1", ROOT, "abc", out)
    assert res.named_exception_passes == 0


def test_mut3a_seal_full_check_input_ref_present_1():
    """seal_full_check.py:443, returncode == 0 -> == 1 (input_ref_present)."""
    assert input_ref_present(ROOT, "HEAD") is True


def test_mut3a_seal_full_check_main_1(tmp_path, monkeypatch, capsys):
    """seal_full_check.py:682, return 1 -> return 2 (main, failures path)."""
    monkeypatch.setattr(seal_full_check, "input_ref_present", lambda *a, **k: True)
    monkeypatch.setattr(seal_full_check, "_porcelain", lambda *a, **k: "")
    monkeypatch.setattr(seal_full_check, "_print_result", lambda *a, **k: None)
    monkeypatch.setattr(
        seal_full_check,
        "check_study",
        lambda *a, **k: StudyResult(name="s1", failures=1),
    )
    rc = main(["--study", "s1", "--repo-root", str(tmp_path)])
    assert rc == 1


def test_mut3a_seal_full_check_regenerate_s1_1(tmp_path):
    """seal_full_check.py:491, mkdir(..., exist_ok=True) -> False (regenerate_s1)."""
    out = tmp_path / "out"
    out.mkdir()
    try:
        regenerate_s1(ROOT, "abc", out)
    except FileExistsError:
        pytest.fail("exist_ok=True must accept a pre-created out_dir")
    except Exception:
        return


def test_mut3a_seal_full_check_regenerate_s2_1(tmp_path):
    """seal_full_check.py:526, repo_root / 'research' -> repo_root * 'research'."""
    out = tmp_path / "out"
    try:
        regenerate_s2(ROOT, "abc", out)
    except TypeError:
        pytest.fail("regenerate_s2 path join must use Path division")
    except Exception:
        return


def test_mut3a_seal_full_check_rel_files_1(tmp_path):
    """seal_full_check.py:174, return out -> return None (rel_files, missing root)."""
    missing = tmp_path / "no-such-dir"
    got = rel_files(missing)
    assert got == set()


def test_mut3a_seal_full_check_s1_exceptions_1():
    """seal_full_check.py:424, return { ... } -> return None (s1_exceptions)."""
    ex = s1_exceptions()
    assert isinstance(ex, dict)
    assert "SEAL_AND_BUDGET.json" in ex
    assert "SEAL_AND_BUDGET.md" in ex
    assert "trial_ledger.jsonl" in ex


def test_mut3a_seal_full_check_s2_exceptions_1():
    """seal_full_check.py:432, return { ... } -> return None (s2_exceptions)."""
    ex = s2_exceptions()
    assert isinstance(ex, dict)
    assert "trial_ledger.jsonl" in ex
