"""Killing tests for MUT1A survivors in sni_inference.py and sni_seal.py.

SNI-local DRAFT contract tests. Fixtures are synthetic. Authority flags stay
false. This file does not mint issuer or security identifiers and does not
feed a rank, gate, size, signal, escalation, or trade path.
"""
from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/common"),
)

import sni_inference  # noqa: E402
import sni_seal  # noqa: E402
from sni_inference import (  # noqa: E402
    _BINOM_COMB_FLOAT_LIMIT,
    _Z_ALPHA_0_10,
    _binom_tail_ge,
    _binom_tail_le,
    _logsumexp_exp,
    _percentile_linear,
    _z_for_alpha,
    binom_p_one_sided_greater,
    binom_p_two_sided,
    cluster_mean_ci,
    wilson_ci,
)
from sni_seal import (  # noqa: E402
    AUTHORITY_FLAG_KEYS,
    _HARD_FALSE_AUTHORITY,
    _is_forbidden_authority_key,
    _is_hex64,
    _validate_sealed_at_utc,
    build_seal,
    render_seal_md,
    sha256_bytes,
    sha256_file,
    sha256_text,
    write_seal,
)


def _probe(**overrides):
    kwargs = {
        "lane": "X",
        "protocol_ids": ["P04"],
        "cells": [{"protocol": "P04", "version": 1, "split": "TEST", "h": 1}],
        "budgets": {"P04": 13},
        "input_manifest": [{"path": "a.json", "sha256": "a" * 64}],
        "prereg_digest": "a" * 64,
        "identity_facts": {"issuer_id": None},
        "sealed_at_utc": "2026-10-12T00:00:00Z",
        "repo_ref": "abc",
    }
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# sni_inference survivors
# ---------------------------------------------------------------------------


def test_mut1a_sni_inference_module_1():
    """sni_inference.py:81, 1029 -> 1030 (_BINOM_COMB_FLOAT_LIMIT)."""
    assert _BINOM_COMB_FLOAT_LIMIT == 1029


def test_mut1a_sni_inference_InferenceResult_1():
    """sni_inference.py:88, frozen=True -> False (InferenceResult)."""
    result = wilson_ci(3, 10)
    with pytest.raises(FrozenInstanceError):
        result.n_obs = 0  # type: ignore[misc]


def test_mut1a_sni_inference_InferenceResult_to_dict_1():
    """sni_inference.py:105, return { ... } -> return None (to_dict)."""
    payload = wilson_ci(3, 10).to_dict()
    assert isinstance(payload, dict)
    assert payload["n_obs"] == 10
    assert payload["method"] == "wilson"
    assert payload["abstained"] is False


def test_mut1a_sni_inference__binom_tail_ge_1():
    """sni_inference.py:282, p0 == 1.0 -> p0 == 1.001 (short-circuit)."""
    assert _binom_tail_ge(1, 2000, 1.0) == 1.0
    assert binom_p_one_sided_greater(1, 2000, 1.0) == 1.0


def test_mut1a_sni_inference__binom_tail_le_1():
    """sni_inference.py:290, return 1.0 -> return 1.001 (k >= n)."""
    assert _binom_tail_le(4, 4, 0.5) == 1.0
    assert _binom_tail_le(10, 10, 0.25) == 1.0


def test_mut1a_sni_inference__logsumexp_exp_1():
    """sni_inference.py:246, return 0.0 -> return None (empty logs)."""
    assert _logsumexp_exp([]) == 0.0


def test_mut1a_sni_inference__percentile_linear_1():
    """sni_inference.py:220, return float(xs[0]) -> return None (n == 1)."""
    assert _percentile_linear([4.25], 0.0) == 4.25
    assert _percentile_linear([4.25], 0.99) == 4.25


def test_mut1a_sni_inference__reject_authority_1():
    """sni_inference.py:144, delete if kwargs: raise TypeError."""
    with pytest.raises(TypeError, match="unexpected keyword arguments"):
        wilson_ci(1, 2, not_an_authority_flag=False)


def test_mut1a_sni_inference__require_n_k_1():
    """sni_inference.py:159, n_i < 0 or k_i < 0 -> and."""
    with pytest.raises(ValueError, match="require n >= k >= 0"):
        wilson_ci(-1, 5)


def test_mut1a_sni_inference__require_p0_1():
    """sni_inference.py:177, not finite or not in [0, 1] -> and."""
    with pytest.raises(ValueError, match="p0 must be in \\[0, 1\\]"):
        binom_p_one_sided_greater(1, 4, p0=1.5)


def test_mut1a_sni_inference__z_for_alpha_1():
    """sni_inference.py:206, alpha == 0.1 -> alpha == 0.1001."""
    assert _z_for_alpha(0.1) == _Z_ALPHA_0_10
    result = wilson_ci(5, 10, alpha=0.1)
    assert result.abstained is False
    assert result.ci_lo is not None and result.ci_hi is not None


def test_mut1a_sni_inference_binom_p_two_sided_1():
    """sni_inference.py:526, p0 default 0.5 -> 0.5005."""
    assert binom_p_two_sided.__defaults__[0] == 0.5
    assert binom_p_two_sided(7, 10) == 0.34375
    assert binom_p_two_sided(7, 10) == binom_p_two_sided(7, 10, p0=0.5)


def test_mut1a_sni_inference_cluster_mean_ci_1(monkeypatch):
    """sni_inference.py:416, hi_q = 1.0 - lo_q with 1.0 -> 1.001."""
    seen: list[float] = []
    real = sni_inference._percentile_linear

    def wrapped(samples, q):
        seen.append(q)
        return real(samples, q)

    monkeypatch.setattr(sni_inference, "_percentile_linear", wrapped)
    cluster_mean_ci(
        [1.0, 2.0, 3.0, 4.0],
        ["a", "a", "b", "b"],
        draws=20,
        seed=0,
        alpha=0.05,
    )
    assert seen == [0.025, 0.975]


# ---------------------------------------------------------------------------
# sni_seal survivors
# ---------------------------------------------------------------------------


def test_mut1a_sni_seal_module_1():
    """sni_seal.py:62, False -> True (_HARD_FALSE_AUTHORITY values)."""
    assert set(_HARD_FALSE_AUTHORITY) == set(AUTHORITY_FLAG_KEYS)
    assert all(value is False for value in _HARD_FALSE_AUTHORITY.values())


def test_mut1a_sni_seal__check_identity_id_values_1():
    """sni_seal.py:177, isinstance(key, str) and key.endswith('_id') -> or."""
    seal = build_seal(**_probe(identity_facts={"issuer_id": None, "count": 1}))
    assert seal["identity_facts"]["count"] == 1


def test_mut1a_sni_seal__is_forbidden_authority_key_1():
    """sni_seal.py:139, return False -> True (non-str key)."""
    seal = build_seal(**_probe(extra={1: "synthetic"}))
    assert seal["extra"][1] == "synthetic"


def test_mut1a_sni_seal__is_forbidden_authority_key_2():
    """sni_seal.py:139, return False -> None (non-str key)."""
    assert _is_forbidden_authority_key(1) is False
    assert _is_forbidden_authority_key(None) is False


def test_mut1a_sni_seal__is_hex64_1():
    """sni_seal.py:108, len==64 and all(hex) -> or."""
    assert _is_hex64("aa") is False
    with pytest.raises(ValueError, match="64-char lowercase hex digest"):
        build_seal(**_probe(prereg_digest="aa"))


def test_mut1a_sni_seal__normalize_budgets_1():
    """sni_seal.py:233, n <= 0 -> n <= 1 (protocol budget of 1)."""
    seal = build_seal(**_probe(budgets={"P04": 1}))
    assert seal["budgets"]["P04"] == 1


def test_mut1a_sni_seal__normalize_manifest_1():
    """sni_seal.py:243, delete exact-keys {path, sha256} raise."""
    with pytest.raises(ValueError, match="input_manifest entries must have exactly keys"):
        build_seal(
            **_probe(
                input_manifest=[
                    {"path": "a.json", "sha256": "a" * 64, "extra": "nope"}
                ]
            )
        )


def test_mut1a_sni_seal__parse_cell_1():
    """sni_seal.py:190, delete cell.field must be str or int raise."""
    with pytest.raises(ValueError, match="cell.h must be a string or int"):
        build_seal(
            **_probe(
                cells=[{"protocol": "P04", "version": 1, "split": "TEST", "h": 1.5}]
            )
        )


def test_mut1a_sni_seal__validate_sealed_at_utc_1():
    """sni_seal.py:128, return value -> return None."""
    stamp = "2026-10-12T00:00:00Z"
    assert _validate_sealed_at_utc(stamp) == stamp


def test_mut1a_sni_seal_build_seal_1():
    """sni_seal.py:292, delete empty-lane raise."""
    with pytest.raises(ValueError, match="lane must be a non-empty string"):
        build_seal(**_probe(lane=""))


def test_mut1a_sni_seal_render_seal_md_1():
    """sni_seal.py:488, delete if not isinstance(seal, dict) raise."""
    with pytest.raises(ValueError, match="seal must be a dict"):
        render_seal_md(["not-a-dict"])


def test_mut1a_sni_seal_sha256_bytes_1():
    """sni_seal.py:92, delete sha256_bytes type guard."""
    with pytest.raises(ValueError, match="sha256_bytes requires bytes"):
        sha256_bytes("abc")


def test_mut1a_sni_seal_sha256_file_1(tmp_path):
    """sni_seal.py:104, return sha256_bytes(...) -> return None."""
    path = tmp_path / "blob.bin"
    path.write_bytes(b"synthetic-bytes")
    assert sha256_file(path) == sha256_bytes(b"synthetic-bytes")
    assert isinstance(sha256_file(path), str)
    assert len(sha256_file(path)) == 64


def test_mut1a_sni_seal_sha256_text_1():
    """sni_seal.py:98, delete sha256_text type guard."""
    with pytest.raises(ValueError, match="sha256_text requires str"):
        sha256_text(b"abc")


def test_mut1a_sni_seal_write_seal_1(tmp_path):
    """sni_seal.py:551, delete if not isinstance(seal, dict) raise."""
    with pytest.raises(ValueError, match="seal must be a dict"):
        write_seal(["not-a-dict"], tmp_path)
