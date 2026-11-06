"""test_sni_common_equivalence.py — shared SNI libraries vs shipped S1/S2.

SNI-local DRAFT comparison only. This file consumes caller-supplied counts and
committed run JSON; it does not mint issuer or security identifiers and does
not feed a rank, gate, size, signal, escalation, or trade path. Authority
flags stay false. Owners (Data OS identity, Company Event/Earnings, FIF,
Capital Structure, Stock Identity, Options, Research Vault, qledger/Evaluation)
remain the source of those values.
"""
from __future__ import annotations

import importlib.util
import json
import math
import random
import sys
import unicodedata
from pathlib import Path

import pytest

# Import idiom copied from tests/test_sni_s1_stats.py and
# tests/test_sni_s2_stats.py. Common is inserted only when sni_inference is
# not already on sys.path so a PYTHONPATH scratch copy can win (negative
# control).
_REPO = Path(__file__).resolve().parents[1]
_COMMON = str(_REPO / "research/single_name_intelligence/common")
if importlib.util.find_spec("sni_inference") is None:
    sys.path.insert(0, _COMMON)
elif _COMMON not in sys.path:
    # PYTHONPATH already supplies sni_inference (negative-control copy);
    # still need this tree for sni_seal.
    sys.path.append(_COMMON)
sys.path.insert(0, str(_REPO / "research/single_name_intelligence/residual"))
sys.path.insert(
    0, str(_REPO / "research" / "single_name_intelligence" / "event_response")
)

from s1_prereg import build_spec, canonical_json as s1_canonical_json  # noqa: E402
from s1_prereg import prereg_digest as s1_prereg_digest  # noqa: E402
from s1_stats import (  # noqa: E402
    binom_p_one_sided_greater as s1_binom_p_one_sided_greater,
)
from s1_stats import mirror_mean_ci as s1_mirror_mean_ci  # noqa: E402
from s1_stats import sign_test_two_sided as s1_sign_test_two_sided  # noqa: E402
from s2_stats import (  # noqa: E402
    binomial_one_sided_greater as s2_binomial_one_sided_greater,
)
from s2_stats import hit_rate_test as s2_hit_rate_test  # noqa: E402
from s2_stats import mirror_trick_ci as s2_mirror_trick_ci  # noqa: E402
from sni_inference import (  # noqa: E402
    ABSTAIN_INSUFFICIENT_CLUSTERS,
    ABSTAIN_NO_EPISODES,
    binom_p_one_sided_greater,
    cluster_mean_ci,
    sign_test_two_sided,
)
from sni_seal import canonical_json as sni_canonical_json  # noqa: E402
from sni_seal import sha256_text  # noqa: E402

_TOL = 1e-12
_RUNS = _REPO / "research" / "single_name_intelligence" / "runs"
_COMMITTED_PREREG = "c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab"
_SIGN_ZERO_MSG = "sign test on zero non-tied observations is not estimable"


def _canonical_fixtures():
    nfc = unicodedata.normalize("NFC", "e\u0301")
    nfd = unicodedata.normalize("NFD", "é")
    return [
        ("empty_dict", {}),
        ("empty_list", []),
        ("nested_dict", {"b": 2, "a": {"z": 1, "y": [3, 2, 1]}}),
        ("key_order", {"z": 1, "a": 2, "m": 3}),
        ("unicode_nfc", {"t": nfc}),
        ("unicode_nfd", {"t": nfd}),
        ("int_1", {"x": 1}),
        ("float_1", {"x": 1.0}),
        ("neg_zero", {"x": -0.0}),
        ("pos_zero", {"x": 0.0}),
        ("empty_str", {"x": ""}),
        ("long_str", {"x": "a" * 5000}),
        ("list_of_dicts", [{"b": 1, "a": 2}, {"d": 3, "c": 4}]),
        ("cjk", {"x": "合成名"}),
        ("bool_none", {"a": True, "b": False, "c": None}),
        ("nested_list", [1, [2, 3], {"k": [4]}]),
        ("mixed_num", {"i": 0, "f": 0.0, "n": -1, "p": 1.5}),
        ("clef", {"x": "𝄞"}),
        ("combining", {"x": "cafe\u0301"}),
        ("spaced_keys", {" a": 1, "a ": 2, "a": 3}),
        ("empty_nested", {"a": {}, "b": []}),
        ("deep", {"a": {"b": {"c": {"d": [1, {"e": 2}]}}}}),
        ("two_key_list", [{"z": 0, "a": 1}]),
        ("escaped", {"x": "quote\"slash\\tab\t"}),
        ("big_int", {"x": 2 ** 53}),
        ("small_float", {"x": 1e-20}),
        ("true_false_keys_as_values", {"t": True, "f": False, "n": None, "s": "null"}),
        ("list_empty_dict", [{}]),
    ]


def _hit_lists(rng: random.Random):
    out = [
        ("all0", [0, 0, 0, 0]),
        ("all1", [1, 1, 1, 1]),
        ("alternating", [1, 0, 1, 0, 1, 0]),
    ]
    for i in range(50):
        n = rng.randint(1, 40)
        out.append((f"rng_{i}", [rng.randint(0, 1) for _ in range(n)]))
    return out


def _bootstrap_inputs(rng: random.Random):
    inputs = [
        ("empty", [], []),
        ("one_cluster", [1.0, 2.0, 3.0], ["a", "a", "a"]),
        ("two_clusters", [1.0, 2.0, 3.0, 4.0], ["a", "a", "b", "b"]),
        ("three_clusters", [0.1, -0.2, 0.3], ["x", "y", "z"]),
    ]
    while len(inputs) < 20:
        n = rng.randint(4, 20)
        n_c = rng.randint(2, min(8, n))
        vals = [rng.uniform(-1.0, 1.0) for _ in range(n)]
        keys = [f"c{rng.randint(0, n_c - 1)}" for _ in range(n)]
        if len(set(keys)) < 2:
            keys[0] = "cX"
            keys[1] = "cY"
        inputs.append((f"r{len(inputs)}", vals, keys))
    return inputs


def _walk_p_value_nodes(obj, acc):
    if isinstance(obj, dict):
        if "p_value" in obj and isinstance(obj.get("p_value"), (int, float)):
            acc.append(obj)
        for value in obj.values():
            _walk_p_value_nodes(value, acc)
    elif isinstance(obj, list):
        for value in obj:
            _walk_p_value_nodes(value, acc)


def _kn_from_node(node):
    stat = node.get("statistic") if isinstance(node.get("statistic"), dict) else {}
    if "hits" in stat and "n" in stat:
        return ("binom", int(stat["hits"]), int(stat["n"]))
    if "pos" in stat and "neg" in stat:
        return ("sign", int(stat["pos"]), int(stat["neg"]))
    if "hits" in node and "n" in node:
        return ("binom", int(node["hits"]), int(node["n"]))
    if "pos" in node and "neg" in node:
        return ("sign", int(node["pos"]), int(node["neg"]))
    return None


def test_eq_01_one_sided_binomial():
    diffs_s1 = []
    diffs_s2 = []
    max_s1 = 0.0
    max_s2 = 0.0
    n_cells = 0
    for n in range(1, 301):
        for k in range(0, n + 1):
            shared = binom_p_one_sided_greater(k, n)
            s1 = s1_binom_p_one_sided_greater(k, n)
            s2 = s2_binomial_one_sided_greater(k, n)
            d1 = abs(shared - s1)
            d2 = abs(shared - s2)
            n_cells += 1
            if d1 > max_s1:
                max_s1 = d1
            if d2 > max_s2:
                max_s2 = d2
            if d1 >= _TOL:
                diffs_s1.append((k, n, shared, s1, d1))
            if d2 >= _TOL:
                diffs_s2.append((k, n, shared, s2, d2))
    assert n_cells == 45450
    if diffs_s1:
        raise AssertionError(f"s1 cells differ ({len(diffs_s1)}): {diffs_s1[:8]}")
    if diffs_s2:
        raise AssertionError(f"s2 cells differ ({len(diffs_s2)}): {diffs_s2[:8]}")
    assert max_s1 < _TOL
    assert max_s2 < _TOL
    assert max_s1 <= 8.881784197001252e-16 + 1e-18
    assert max_s2 <= 6.661338147750939e-16 + 1e-18


def test_eq_02_sign_test():
    diffs = []
    max_d = 0.0
    n_cells = 0
    for pos in range(0, 121):
        for neg in range(0, 121):
            if pos == 0 and neg == 0:
                continue
            shared = sign_test_two_sided(pos, neg)
            s1 = s1_sign_test_two_sided(pos, neg)
            d = abs(shared - s1)
            n_cells += 1
            if d > max_d:
                max_d = d
            if d >= _TOL:
                diffs.append((pos, neg, shared, s1, d))
    assert n_cells == 14640
    if diffs:
        raise AssertionError(f"sign-test cells differ ({len(diffs)}): {diffs[:8]}")
    assert max_d < _TOL
    assert max_d <= 5.551115123125783e-16 + 1e-18


def test_eq_02_sign_test_pos_neg_zero():
    assert s1_sign_test_two_sided(0, 0) == 1.0
    with pytest.raises(ValueError, match="not estimable") as exc:
        sign_test_two_sided(0, 0)
    assert str(exc.value) == _SIGN_ZERO_MSG


def test_eq_03_s2_hit_rate_test():
    with pytest.raises(ValueError, match="n must be >= 1"):
        s2_hit_rate_test([])

    rng = random.Random(20261013)
    n_round_diff = 0
    for name, hits in _hit_lists(rng):
        res = s2_hit_rate_test(hits)
        k = int(res["hits"])
        n = int(res["n"])
        assert k == int(sum(hits))
        assert n == len(hits)
        shared = binom_p_one_sided_greater(k, n)
        s2_raw = s2_binomial_one_sided_greater(k, n)
        assert abs(s2_raw - shared) < _TOL, (name, k, n, s2_raw, shared)
        reported = res["p_value"]
        rounded = round(shared, 6)
        assert reported == rounded, (name, k, n, reported, shared, rounded)
        if reported != shared:
            n_round_diff += 1
    assert n_round_diff >= 1


def test_eq_04_bootstrap_mirror_ci():
    rng = random.Random(20261013)
    inputs = _bootstrap_inputs(rng)
    assert len(inputs) == 20
    n_numeric_mismatch = 0
    for name, vals, keys in inputs:
        sni = cluster_mean_ci(vals, keys)
        s1 = s1_mirror_mean_ci(vals, keys)
        s2 = s2_mirror_trick_ci(keys, vals)
        n_clusters = len(set(keys))
        if len(vals) == 0:
            assert sni.abstained is True
            assert sni.reason == ABSTAIN_NO_EPISODES
            assert sni.ci_lo is None and sni.ci_hi is None
            assert s1 is None
            assert s2 is None
            continue
        if n_clusters < 2:
            assert sni.abstained is True
            assert sni.reason == ABSTAIN_INSUFFICIENT_CLUSTERS
            assert sni.ci_lo is None and sni.ci_hi is None
            assert s1 is None
            assert s2 is None
            continue
        assert sni.abstained is False
        assert sni.ci_lo is not None and sni.ci_hi is not None
        assert sni.ci_lo <= sni.ci_hi
        assert math.isfinite(sni.ci_lo) and math.isfinite(sni.ci_hi)
        assert s1 is not None and s2 is not None
        assert s1 == s2
        assert s1[0] <= s1[1]
        sni_rounded = [round(sni.ci_lo, 4), round(sni.ci_hi, 4)]
        if sni_rounded != s1:
            n_numeric_mismatch += 1
    assert n_numeric_mismatch >= 1


def test_eq_05_canonical_json():
    fixtures = _canonical_fixtures()
    assert len(fixtures) >= 25
    first_diff = None
    n_body_mismatch = 0
    for name, obj in fixtures:
        sni_b = sni_canonical_json(obj).encode("utf-8")
        s1_b = s1_canonical_json(obj).encode("utf-8")
        if sni_b != s1_b and first_diff is None:
            first_diff = name
        if sni_b == s1_b + b"\n":
            continue
        n_body_mismatch += 1
        raise AssertionError(
            f"canonical body mismatch on {name}: sni={sni_b[:80]!r} s1={s1_b[:80]!r}"
        )
    assert n_body_mismatch == 0
    assert first_diff == "empty_dict"
    nfc = unicodedata.normalize("NFC", "e\u0301")
    nfd = unicodedata.normalize("NFD", "é")
    assert nfc != nfd
    assert sni_canonical_json({"t": nfc}) != sni_canonical_json({"t": nfd})
    assert s1_canonical_json({"t": nfc}) != s1_canonical_json({"t": nfd})
    assert sni_canonical_json({"x": 1}) != sni_canonical_json({"x": 1.0})


def test_eq_05_canonical_json_nan_inf():
    for label, value in (
        ("nan", float("nan")),
        ("inf", float("inf")),
        ("-inf", float("-inf")),
    ):
        obj = {"x": value}
        with pytest.raises(ValueError, match="finite floats"):
            sni_canonical_json(obj)
        s1_text = s1_canonical_json(obj)
        if label == "nan":
            assert s1_text == '{"x":NaN}'
        elif label == "inf":
            assert s1_text == '{"x":Infinity}'
        else:
            assert s1_text == '{"x":-Infinity}'


def test_eq_06_reproduce_committed_p_values():
    json_files = sorted(_RUNS.rglob("*.json"))
    assert json_files, "no run JSON files on disk"
    n_repro = 0
    files_with = []
    files_without_results = []
    max_d = 0.0
    fails = []
    for path in json_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        nodes = []
        _walk_p_value_nodes(data, nodes)
        if not nodes:
            if path.parent.name == "results":
                files_without_results.append(str(path.relative_to(_REPO)))
            continue
        files_with.append((str(path.relative_to(_REPO)), len(nodes)))
        for node in nodes:
            kn = _kn_from_node(node)
            assert kn is not None, (path, node)
            kind, a, b = kn
            committed = float(node["p_value"])
            if kind == "binom":
                got = binom_p_one_sided_greater(a, b)
            else:
                if a == 0 and b == 0:
                    fails.append((str(path), "sign-zero", node))
                    continue
                got = sign_test_two_sided(a, b)
            d = abs(got - committed)
            n_repro += 1
            if d > max_d:
                max_d = d
            if d >= _TOL:
                fails.append((str(path), kind, a, b, committed, got, d))
    print(f"reproduced_committed_values={n_repro}")
    if fails:
        raise AssertionError(f"committed p-value mismatches ({len(fails)}): {fails[:8]}")
    assert n_repro == 144
    assert max_d < _TOL
    names_with = {name for name, _ in files_with}
    assert names_with == {
        "research/single_name_intelligence/runs/s1_residual/results/P01.json",
        "research/single_name_intelligence/runs/s1_residual/results/P02.json",
        "research/single_name_intelligence/runs/s1_residual_v1_1/results/P01.json",
        "research/single_name_intelligence/runs/s1_residual_v1_1/results/P02.json",
    }
    assert "research/single_name_intelligence/runs/s1_residual/results/P03.json" in files_without_results
    assert "research/single_name_intelligence/runs/s2_event_response/results/P04.json" in files_without_results


def test_eq_06_prereg_digest():
    spec = build_spec()
    sni_text = sni_canonical_json(spec)
    s1_text = s1_canonical_json(spec)
    assert sni_text.encode("utf-8") == s1_text.encode("utf-8") + b"\n"
    sni_digest = sha256_text(sni_text)
    s1_digest = s1_prereg_digest(spec)
    committed = json.loads(
        (
            _RUNS / "s1_residual" / "results" / "P01.json"
        ).read_text(encoding="utf-8")
    )["prereg_digest_sha256"]
    assert committed == _COMMITTED_PREREG
    assert s1_digest == committed
    assert sni_digest != committed
    assert sha256_text(sni_text.rstrip("\n")) == committed
