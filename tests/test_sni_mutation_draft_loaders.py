"""MUT4D killing tests for p04_v2_draft_loader and a8_draft_loader (2026-10-13).

SNI-local DRAFT contract tests. They consume caller-supplied synthetic draft
dicts and the committed DRAFT JSON; they do not mint issuer or security
identifiers and they do not feed a rank, gate, size, signal, escalation, or
trade path. Authority flags stay false. Fixtures are synthetic.

Each test_mut4d_* docstring names one non-equivalent mutant that survived
the pre-existing suite (file:line, original -> mutated).
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
P04_DIR = ROOT / "research" / "single_name_intelligence" / "event_response"
A8_DIR = ROOT / "research" / "single_name_intelligence" / "us_transfer"
P04_JSON = P04_DIR / "P04_V2_PREREG_DRAFT.json"
A8_JSON = A8_DIR / "A8_US_RESIDUAL_TRANSFER_PREREG_DRAFT.json"

if str(P04_DIR) not in sys.path:
    sys.path.insert(0, str(P04_DIR))
if str(A8_DIR) not in sys.path:
    sys.path.insert(0, str(A8_DIR))

import a8_draft_loader as a8_loader  # noqa: E402
import p04_v2_draft_loader as p04_loader  # noqa: E402


def _p04_draft() -> dict:
    return json.loads(P04_JSON.read_text(encoding="utf-8"))


def _a8_draft() -> dict:
    return json.loads(A8_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# p04_v2_draft_loader survivors
# ---------------------------------------------------------------------------


def test_mut4d_p04_v2_draft_loader__check_tune_empty_1() -> None:
    """p04_v2_draft_loader.py:181, `or` -> `and` (membership_table rows fallback)."""
    draft = _p04_draft()
    draft["membership_table"] = {"rows": [{"episode_id": "synthetic-ep-1"}]}
    with pytest.raises(ValueError, match="membership_table is non-empty"):
        p04_loader.validate_draft(draft)


def test_mut4d_p04_v2_draft_loader__check_tune_empty_2() -> None:
    """p04_v2_draft_loader.py:164, `or` -> `and` (TUNE membership_table fallback)."""
    draft = _p04_draft()
    draft["splits"] = dict(draft["splits"])
    draft["splits"]["TUNE"] = {
        "membership": "EMPTY",
        "membership_table": [{"episode_id": "synthetic-ep-1"}],
    }
    with pytest.raises(ValueError, match="splits.TUNE describes members"):
        p04_loader.validate_draft(draft)


def test_mut4d_p04_v2_draft_loader_validate_draft_1() -> None:
    """p04_v2_draft_loader.py:243, `or` -> `and` (requires must be a list)."""
    draft = _p04_draft()
    draft["registration_gate"] = dict(draft["registration_gate"])
    draft["registration_gate"]["requires"] = (p04_loader.REG_SEAL_REQUIREMENT,)
    with pytest.raises(ValueError, match="registration_gate.requires"):
        p04_loader.validate_draft(draft)


def test_mut4d_p04_v2_draft_loader__require_iso_z_1() -> None:
    """p04_v2_draft_loader.py:73, `or` -> `and` (non-str as_of_utc)."""
    with pytest.raises(ValueError, match="as_of_utc"):
        p04_loader.check_episode_as_of(
            None, "2024-01-02T00:00:00Z", "2024-01-01T00:00:00Z"
        )


def test_mut4d_p04_v2_draft_loader_label_for_1() -> None:
    """p04_v2_draft_loader.py:119, `0` -> `1` (episodes == 0 abstention)."""
    assert p04_loader.label_for(0, 2, 153) == "ABSTAIN_NO_EPISODES"
    assert p04_loader.label_for(0, 0, 153) == "ABSTAIN_NO_EPISODES"


def test_mut4d_p04_v2_draft_loader_validate_draft_2() -> None:
    """p04_v2_draft_loader.py:286, `or` -> `and` (TESTED token in ladder text)."""
    draft = _p04_draft()
    draft["abstention_ladder"] = [
        "ABSTAIN_NO_EPISODES TESTED",
        "ABSTAIN_INSUFFICIENT_CLUSTERS",
    ]
    with pytest.raises(ValueError, match="abstention_ladder"):
        p04_loader.validate_draft(draft)


def test_mut4d_p04_v2_draft_loader_label_for_2() -> None:
    """p04_v2_draft_loader.py:115, `or` -> `and` (bool is not an int count)."""
    with pytest.raises(ValueError, match="episodes must be int"):
        p04_loader.label_for(True, 2, 153)
    with pytest.raises(ValueError, match="clusters must be int"):
        p04_loader.label_for(10, False, 153)


def test_mut4d_p04_v2_draft_loader_label_for_3() -> None:
    """p04_v2_draft_loader.py:121, `2` -> `3` (TESTED requires clusters >= 2)."""
    assert p04_loader.label_for(153, 2, 153) == "TESTED"
    assert p04_loader.label_for(500, 2, 153) == "TESTED"
    assert p04_loader.label_for(153, 1, 153) == "ABSTAIN_INSUFFICIENT_CLUSTERS"


def test_mut4d_p04_v2_draft_loader_validate_draft_3() -> None:
    """p04_v2_draft_loader.py:263, `or` -> `and` (budget source must be str)."""
    draft = _p04_draft()
    draft["trial_ledger"] = dict(draft["trial_ledger"])
    draft["trial_ledger"]["declared_budget_floor_source"] = (
        "SEAL_AND_BUDGET.json",
    )
    with pytest.raises(ValueError, match="declared_budget_floor_source"):
        p04_loader.validate_draft(draft)


def test_mut4d_p04_v2_draft_loader_validate_draft_4() -> None:
    """p04_v2_draft_loader.py:269, `or` -> `and` (family_n whitespace-only)."""
    draft = _p04_draft()
    draft["trial_ledger"] = dict(draft["trial_ledger"])
    draft["trial_ledger"]["family_n"] = "   "
    with pytest.raises(ValueError, match="family_n is missing"):
        p04_loader.validate_draft(draft)


def test_mut4d_p04_v2_draft_loader_validate_draft_5() -> None:
    """p04_v2_draft_loader.py:299, `or` -> `and` (min_clusters must be int)."""
    draft = _p04_draft()
    draft["label_semantics"] = deepcopy(draft["label_semantics"])
    draft["label_semantics"]["rule"]["TESTED"]["min_clusters"] = 2.0
    with pytest.raises(ValueError, match="clusters < 2"):
        p04_loader.validate_draft(draft)


def test_mut4d_p04_v2_draft_loader_validate_draft_6() -> None:
    """p04_v2_draft_loader.py:276, `or` -> `and` (labels must be a list)."""
    draft = _p04_draft()
    draft["label_semantics"] = dict(draft["label_semantics"])
    draft["label_semantics"]["labels"] = tuple(p04_loader.LABELS)
    with pytest.raises(ValueError, match="label_semantics.labels"):
        p04_loader.validate_draft(draft)


def test_mut4d_p04_v2_draft_loader_validate_draft_7() -> None:
    """p04_v2_draft_loader.py:306, False -> True (ensure_ascii on identity scan)."""
    draft = _p04_draft()
    # U+0700 json-escapes to \\u0700, which would false-match ASCII '0700'
    # if ensure_ascii were True. The scan must see the raw character.
    draft["synthetic_note"] = "\u0700"
    p04_loader.validate_draft(draft)


# ---------------------------------------------------------------------------
# a8_draft_loader survivors
# ---------------------------------------------------------------------------


def test_mut4d_a8_draft_loader__authority_value_is_truthy_1() -> None:
    """a8_draft_loader.py:133, `return True` -> `return None` (bool True flag)."""
    draft = _a8_draft()
    draft["authority_flags"] = dict(draft["authority_flags"])
    draft["authority_flags"]["rank_authority"] = True
    with pytest.raises(a8_loader.A8DraftRefused) as excinfo:
        a8_loader.validate_draft(draft)
    assert excinfo.value.code == "AUTHORITY_TRUTHY"


def test_mut4d_a8_draft_loader__norm_key_1() -> None:
    """a8_draft_loader.py:127, `return ""` -> `return None` (non-str key)."""
    assert a8_loader._norm_key(1) == ""
    assert a8_loader._norm_key(None) == ""
    assert a8_loader._norm_key(b"rank_authority") == ""


def test_mut4d_a8_draft_loader__refuse_1() -> None:
    """a8_draft_loader.py:120, delete `if code not in REFUSAL_CODES: raise`."""
    with pytest.raises(RuntimeError, match="not in REFUSAL_CODES"):
        a8_loader._refuse("NOT_A_REAL_CODE")


def test_mut4d_a8_draft_loader__authority_value_is_truthy_2() -> None:
    """a8_draft_loader.py:133, True -> False (`return True` of bool True flag)."""
    draft = _a8_draft()
    draft["authority_flags"] = dict(draft["authority_flags"])
    draft["authority_flags"]["gate_authority"] = True
    with pytest.raises(a8_loader.A8DraftRefused) as excinfo:
        a8_loader.validate_draft(draft)
    assert excinfo.value.code == "AUTHORITY_TRUTHY"
    assert a8_loader._authority_value_is_truthy(True) is True
    assert a8_loader._authority_value_is_truthy(False) is False


def test_mut4d_a8_draft_loader_validate_draft_1() -> None:
    """a8_draft_loader.py:203, `or` -> `and` (names must be a list)."""
    draft = _a8_draft()
    draft["names"] = tuple(draft["names"])
    with pytest.raises(a8_loader.A8DraftRefused) as excinfo:
        a8_loader.validate_draft(draft)
    assert excinfo.value.code == "CELL_COUNT_MISMATCH"


def test_mut4d_a8_draft_loader_validate_draft_2() -> None:
    """a8_draft_loader.py:213, `or` -> `and` (then_known must be a list)."""
    draft = _a8_draft()
    draft["then_known"] = tuple(draft["then_known"])
    with pytest.raises(a8_loader.A8DraftRefused) as excinfo:
        a8_loader.validate_draft(draft)
    assert excinfo.value.code == "THEN_KNOWN_INCOMPLETE"
