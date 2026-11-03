"""Independent reproduction of SNI v1.1 sealed block-bootstrap CIs (IRP-GAP4).

This file is an SNI-local DRAFT comparison. It CONSUMES committed
observation files and sealed result JSON owned by the S1/S2 runners,
Stock Identity / Data OS (opaque episode_key / issuer_key strings), and
the registered evaluation loop. It does not mint, derive, or guess
canonical HK/US issuer or security identifiers. It does not feed a
ranker, gate, sizer, signal, escalation, or trade path.

Independence: this test does not import the SNI wrappers that produced
the sealed numbers. It calls engine.grading_stats.block_bootstrap_ci
directly on arrays built from committed observation files, with the
registered draws/seed/stat read from PREREG_SPEC.json.

This is a reproduction of a registered interval. It is not statistical
validity, not an acceptance-row move, and not probabilistic forecast
support.

Authority flags stay false. refuse_authority_true raises if a caller
passes any of them as true.
"""
from __future__ import annotations

import ast
import functools
import json
import re
from pathlib import Path

import numpy as np
import pytest

from engine.grading_stats import block_bootstrap_ci

REPO_ROOT = Path(__file__).resolve().parents[1]
S1_RUN = REPO_ROOT / "research" / "single_name_intelligence" / "runs" / "s1_residual_v1_1"
S2_RUN = (
    REPO_ROOT / "research" / "single_name_intelligence" / "runs" / "s2_event_response_v1_1"
)

AUTHORITY_KEYS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

P03_PAIR = {
    "M1_vs_M0": ("M0", "M1"),
    "M2_vs_M1": ("M1", "M2"),
    "IPCA_vs_M1": ("M1", "IPCA"),
}

FORBIDDEN_IMPORT_PREFIXES = (
    "research.single_name_intelligence.residual",
    "research.single_name_intelligence.event_response",
    "research.single_name_intelligence.common",
    "research.single_name_intelligence.evaluation",
    "tests.test_sni_independent_repro",
)

_DRAWS_SEED_RE = re.compile(r"draws/seed \((\d+)/(\d+)\)")


# ---------------------------------------------------------------------------
# Authority
# ---------------------------------------------------------------------------


def refuse_authority_true(flags):
    """Consume owner-supplied flags; raise if any authority bit is true."""
    if not isinstance(flags, dict):
        return flags
    for key in AUTHORITY_KEYS:
        if flags.get(key) is True:
            raise ValueError(
                f"refusing {key}=True; IRP-GAP4 has no rank/gate/size/signal/"
                "escalation/trade authority"
            )
        short = key[: -len("_authority")]
        if flags.get(short) is True:
            raise ValueError(
                f"refusing {short}=True; IRP-GAP4 has no rank/gate/size/signal/"
                "escalation/trade authority"
            )
    return flags


def walk_authority_flags(obj, path=""):
    found = []
    if isinstance(obj, dict):
        refuse_authority_true(obj)
        for key, val in obj.items():
            here = f"{path}.{key}" if path else key
            if key in AUTHORITY_KEYS or key in {k[: -len("_authority")] for k in AUTHORITY_KEYS}:
                found.append((here, val))
            found.extend(walk_authority_flags(val, here))
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            found.extend(walk_authority_flags(val, f"{path}[{i}]"))
    return found


# ---------------------------------------------------------------------------
# Loaders (copied small idiom; not imported from test_sni_independent_repro)
# ---------------------------------------------------------------------------


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def s1_obs_path(protocol, subject, horizon, obs_dir=None):
    obs_dir = Path(obs_dir) if obs_dir is not None else S1_RUN / "observations"
    return obs_dir / f"{protocol}_{subject}_{horizon}.json"


def load_s1_obs(protocol, subject, horizon, obs_dir=None):
    return load_json(s1_obs_path(protocol, subject, horizon, obs_dir=obs_dir))


def load_s1_result(protocol, results_dir=None):
    results_dir = Path(results_dir) if results_dir is not None else S1_RUN / "results"
    return load_json(results_dir / f"{protocol}.json")


def load_s2_result(protocol, results_dir=None):
    results_dir = Path(results_dir) if results_dir is not None else S2_RUN / "results"
    return load_json(results_dir / f"{protocol}.json")


def load_s2_episodes(path=None):
    path = Path(path) if path is not None else S2_RUN / "observations" / "episodes.jsonl"
    rows = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def parse_s1_block_name(name):
    parts = name.split("|")
    protocol = parts[0]
    subject = parts[1]
    horizon = int(parts[2].split("=")[1])
    if protocol == "P03":
        split_raw, pair = parts[3], parts[4]
        return {
            "protocol": protocol,
            "subject": subject,
            "horizon": horizon,
            "split_raw": split_raw,
            "split": "TRAIN" if split_raw.startswith("TRAIN") else "TUNE",
            "baseline": None,
            "h0": None,
            "pair": pair,
        }
    split_raw, baseline, h0 = parts[3], parts[4], parts[5]
    if split_raw.startswith("TRAIN"):
        split = "TRAIN"
    elif split_raw.startswith("TUNE"):
        split = "TUNE"
    else:
        split = split_raw
    return {
        "protocol": protocol,
        "subject": subject,
        "horizon": horizon,
        "split_raw": split_raw,
        "split": split,
        "baseline": baseline,
        "h0": h0,
        "pair": None,
    }


def iter_s1_blocks():
    out = []
    for protocol in ("P01", "P02", "P03"):
        result = load_s1_result(protocol)
        for name in result["blocks"]:
            out.append((protocol, name))
    return out


def s1_block_is_ipca(block_name):
    return block_name.split("|")[-1].startswith("IPCA")


def iter_s2_ci_cells():
    out = []
    for protocol in ("P04", "P05", "P06"):
        result = load_s2_result(protocol)
        for split, cells in result["splits"].items():
            if split == "TEST" or not isinstance(cells, dict):
                continue
            for hkey, cell in cells.items():
                if isinstance(cell, dict) and "ci" in cell:
                    out.append((protocol, split, hkey))
    return out


# ---------------------------------------------------------------------------
# Registered parameters (PREREG_SPEC, not engine defaults)
# ---------------------------------------------------------------------------


def registered_boot_params():
    spec = load_json(S1_RUN / "PREREG_SPEC.json")
    refuse_authority_true(spec.get("authority_flags") or {})
    trick = spec["mirror_trick"]
    construction = trick["construction"]
    match = _DRAWS_SEED_RE.search(construction)
    if match is None:
        raise AssertionError(
            "PREREG_SPEC.json mirror_trick.construction does not pin draws/seed"
        )
    if "stat='mean'" not in construction and 'stat="mean"' not in construction:
        raise AssertionError(
            "PREREG_SPEC.json mirror_trick.construction does not pin stat='mean'"
        )
    return {
        "draws": int(match.group(1)),
        "seed": int(match.group(2)),
        "stat": "mean",
        "block": trick["block"],
        "cluster_variable": trick["cluster_variable"],
        "construction": construction,
        "source": (
            "research/single_name_intelligence/runs/s1_residual_v1_1/"
            "PREREG_SPEC.json key mirror_trick.construction"
        ),
    }


# ---------------------------------------------------------------------------
# Mirror-trick panel and input shaping (first principles; no SNI import)
# ---------------------------------------------------------------------------


def mirror_trick_panel(vals, cluster_keys):
    # Mirror trick (sealing: residual/s1_stats.py:70-74 and residual/run_s1.py:690):
    # dates=concat(k,k), vals=concat(x,-x), mask=concat([True]*n,[False]*n),
    # so block_bootstrap_ci's (cond mean − base mean) gap equals mean(x).
    x = np.asarray(list(vals), dtype=float)
    n = int(x.size)
    if n == 0:
        return None, None, None
    keys = list(cluster_keys)
    dates = np.array(keys + keys)
    vv = np.concatenate([x, -x])
    mask = np.concatenate([np.ones(n, dtype=bool), np.zeros(n, dtype=bool)])
    return dates, vv, mask


def call_registered_ci(vals, cluster_keys, params=None):
    params = params if params is not None else registered_boot_params()
    dates, vv, mask = mirror_trick_panel(vals, cluster_keys)
    if dates is None:
        return None
    return block_bootstrap_ci(
        dates,
        vv,
        mask,
        draws=params["draws"],
        seed=params["seed"],
        stat=params["stat"],
    )


def p01p02_excess_series(rows, split, baseline):
    """P01/P02 usable excess series.

    Shaping from residual/run_s1.py:352-375, 422-427: manifest_split == split,
    abstention == OK, direction != 0; vals = excess; dates = anchor_session_date.
    """
    usable = []
    for row in rows:
        if row.get("manifest_split") != split:
            continue
        if row.get("abstention") != "OK":
            continue
        if baseline == "always_long":
            direction = row.get("always_long_direction")
        else:
            direction = row.get("trail63_direction")
        if direction == 0:
            continue
        usable.append(row)
    vals = [row["excess"] for row in usable]
    dates = [row["anchor_session_date"] for row in usable]
    return vals, dates


def p03_d_series(rows, split, prev_name, next_name):
    """P03 paired d_i series.

    Shaping from residual/run_s1.py:671-690: prev split/OK/r__oc, next OK/common__oc;
    d = (r − common_prev)^2 − (r − common_next)^2; cluster = next.anchor_session_date.
    """
    models = {row.get("model") for row in rows}
    if next_name not in models:
        return None
    by_model = {}
    for row in rows:
        by_model.setdefault(row["model"], {})[row["episode_key"]] = row
    prev_rows = by_model.get(prev_name, {})
    next_rows = by_model.get(next_name, {})
    paired = []
    for episode_key, prev in prev_rows.items():
        if prev.get("split") != split:
            continue
        if prev.get("abstention") != "OK" or prev.get("r__oc") is None:
            continue
        nxt = next_rows.get(episode_key)
        if nxt is None or nxt.get("abstention") != "OK" or nxt.get("common__oc") is None:
            continue
        paired.append((prev, nxt))
    vals = [
        (prev["r__oc"] - prev["common__oc"]) ** 2
        - (prev["r__oc"] - nxt["common__oc"]) ** 2
        for prev, nxt in paired
    ]
    dates = [nxt["anchor_session_date"] for prev, nxt in paired]
    return vals, dates


@functools.lru_cache(maxsize=None)
def reproduce_s1_ci(protocol, subject, horizon, split, extra):
    rows = load_s1_obs(protocol, subject, horizon)
    if protocol == "P03":
        prev_name, next_name = P03_PAIR[extra]
        series = p03_d_series(rows, split, prev_name, next_name)
        if series is None:
            return ("GAP", "IRP-GAP4: P03 IPCA model rows not committed in observations/")
        vals, dates = series
    else:
        vals, dates = p01p02_excess_series(rows, split, extra)
    ci = call_registered_ci(vals, dates)
    return ("OK", (ci, len(vals)))


def reproduce_block_ci(protocol, block_name):
    meta = parse_s1_block_name(block_name)
    extra = meta["pair"] if protocol == "P03" else meta["baseline"]
    return reproduce_s1_ci(
        meta["protocol"], meta["subject"], meta["horizon"], meta["split"], extra
    )


def assert_ci_bitwise(sealed, got, block_name):
    """Sealed ci95 is a JSON-decoded float list; require bitwise equality."""
    assert got == sealed, (
        f"{block_name}: sealed {sealed!r} reproduced {got!r} "
        "(IRP-F4 disagreement; bitwise equality of JSON-decoded floats)"
    )


def production_import_violations(source):
    tree = ast.parse(source)
    hits = []

    def consider(name, node):
        if not name:
            return
        for prefix in FORBIDDEN_IMPORT_PREFIXES:
            if name == prefix or name.startswith(prefix + "."):
                hits.append(f"{name} (line {node.lineno})")
                return
        last = name.split(".")[-1]
        if last.startswith("s1_") or last.startswith("s2_") or last.startswith("sni_"):
            hits.append(f"{name} (line {node.lineno})")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                consider(alias.name, node)
        elif isinstance(node, ast.ImportFrom):
            consider(node.module, node)
            for alias in node.names:
                consider(alias.name, node)
                if node.module:
                    consider(f"{node.module}.{alias.name}", node)
    return hits


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_irp_gap4_00_no_sni_wrapper_imports():
    source = Path(__file__).read_text(encoding="utf-8")
    hits = production_import_violations(source)
    assert hits == [], f"SNI wrapper / independent-repro imports: {hits}"


def test_irp_gap4_01_refuse_authority_true():
    for key in AUTHORITY_KEYS:
        with pytest.raises(ValueError, match="refusing"):
            refuse_authority_true({key: True})
        short = key[: -len("_authority")]
        with pytest.raises(ValueError, match="refusing"):
            refuse_authority_true({short: True})
    flags = {key: False for key in AUTHORITY_KEYS}
    assert refuse_authority_true(flags) is flags
    walk_authority_flags(
        load_json(S1_RUN / "PREREG_SPEC.json").get("authority_flags") or {}
    )
    walk_authority_flags(
        load_json(S1_RUN / "SEAL_AND_BUDGET.json").get("authority_flags") or {}
    )


def test_irp_gap4_02_registered_params_from_prereg():
    params = registered_boot_params()
    assert params["draws"] == 800
    assert params["seed"] == 7
    assert params["stat"] == "mean"
    assert params["block"] == "one non-overlapping anchor unit (h+1 sessions >= h)"
    citations = load_json(S1_RUN / "PREREG_SPEC.json")["engine_citations"][
        "engine/grading_stats.py"
    ]
    # BOOT_DRAWS/BOOT_SEED in engine_citations are line numbers, not values.
    assert citations["BOOT_DRAWS"] == 43
    assert citations["BOOT_SEED"] == 44
    assert citations["block_bootstrap_ci"] == 121


def _s1_ci_params():
    params = []
    for protocol, name in iter_s1_blocks():
        marks = []
        if s1_block_is_ipca(name):
            marks.append(
                pytest.mark.xfail(
                    strict=True,
                    reason=(
                        "IRP-GAP4: P03 IPCA model rows not committed in "
                        "observations/"
                    ),
                )
            )
        params.append(
            pytest.param(protocol, name, marks=marks, id=f"{protocol}::{name}")
        )
    return params


@pytest.mark.parametrize("protocol,block_name", _s1_ci_params())
def test_irp_gap4_03_s1_ci_interval(protocol, block_name):
    sealed = load_s1_result(protocol)["blocks"][block_name]["ci"]["ci95"]
    status, payload = reproduce_block_ci(protocol, block_name)
    if status == "GAP":
        pytest.fail(payload)
    got, n_input = payload
    assert n_input >= 0
    assert_ci_bitwise(sealed, got, block_name)


def _p03_s0_params():
    params = []
    for protocol, name in iter_s1_blocks():
        if protocol != "P03":
            continue
        marks = []
        if s1_block_is_ipca(name):
            marks.append(
                pytest.mark.xfail(
                    strict=True,
                    reason=(
                        "IRP-GAP4: P03 IPCA model rows not committed in "
                        "observations/"
                    ),
                )
            )
        params.append(pytest.param(name, marks=marks, id=name))
    return params


@pytest.mark.parametrize("block_name", _p03_s0_params())
def test_irp_gap4_04_p03_s0_ci_lower_bound(block_name):
    sealed = load_s1_result("P03")["blocks"][block_name]["ci"]["ci95"]
    status, payload = reproduce_block_ci("P03", block_name)
    if status == "GAP":
        pytest.fail(payload)
    got, _n = payload
    assert got is not None and sealed is not None
    assert got[0] == sealed[0], (
        f"{block_name} S0 lower bound sealed {sealed[0]!r} reproduced {got[0]!r}"
    )


def _s2_ci_params():
    params = []
    for protocol, split, hkey in iter_s2_ci_cells():
        params.append(
            pytest.param(
                protocol,
                split,
                hkey,
                marks=pytest.mark.xfail(
                    strict=True,
                    reason=(
                        "IRP-GAP4: S2 episode excess values not committed in "
                        "observations/episodes.jsonl"
                    ),
                ),
                id=f"{protocol}::{split}/{hkey}",
            )
        )
    return params


@pytest.mark.parametrize("protocol,split,hkey", _s2_ci_params())
def test_irp_gap4_05_s2_ci_interval(protocol, split, hkey):
    sealed = load_s2_result(protocol)["splits"][split][hkey]["ci"]
    episodes = load_s2_episodes()
    numeric = []
    for row in episodes:
        if row.get("protocol_id") != protocol:
            continue
        if row.get("split") != split:
            continue
        if int(row.get("horizon")) != int(str(hkey).lstrip("h")):
            continue
        if row.get("census_only") is True:
            continue
        outcome = row.get("outcome") or {}
        excess = outcome.get("excess", row.get("excess"))
        if excess is not None:
            numeric.append(excess)
    if not numeric:
        pytest.fail(
            "IRP-GAP4: S2 episode excess values not committed in "
            f"observations/episodes.jsonl (sealed ci={sealed!r})"
        )
    cluster = [
        row.get("cluster_key")
        for row in episodes
        if row.get("protocol_id") == protocol
        and row.get("split") == split
        and int(row.get("horizon")) == int(str(hkey).lstrip("h"))
        and row.get("census_only") is not True
    ]
    got = call_registered_ci(numeric, cluster)
    assert_ci_bitwise(sealed, got, f"{protocol}/{split}/{hkey}")


def test_irp_gap4_06_determinism():
    params = registered_boot_params()
    rows = load_s1_obs("P01", "adr_baba", 5)
    vals, dates = p01p02_excess_series(rows, "TRAIN", "always_long")
    first = call_registered_ci(vals, dates, params=params)
    second = call_registered_ci(vals, dates, params=params)
    assert first is not None
    assert first == second
    other = dict(params)
    other["seed"] = params["seed"] + 1
    alt = call_registered_ci(vals, dates, params=other)
    # Different seed produced a different interval on this series.
    # If it had not, that would be a finding, not a failure.
    if alt == first:
        pytest.xfail(
            "IRP-F4: different seed produced an identical interval on "
            "P01 adr_baba h=5 TRAIN always_long"
        )
    assert alt != first


def test_irp_gap4_07_mirror_trick_first_principles_synthetic():
    params = registered_boot_params()
    vals = [0.25, 0.25, 0.25, 0.25]
    keys = ["d0", "d1", "d2", "d3"]
    dates, vv, mask = mirror_trick_panel(vals, keys)
    cond = float(np.mean(vv[mask]))
    base = float(np.mean(vv))
    assert abs(cond - 0.25) <= 1e-12
    assert abs(base) <= 1e-12
    assert abs((cond - base) - 0.25) <= 1e-12
    ci = block_bootstrap_ci(
        dates,
        vv,
        mask,
        draws=params["draws"],
        seed=params["seed"],
        stat=params["stat"],
    )
    assert ci == [0.25, 0.25]


def test_irp_gap4_08_census_complete():
    s1_n = 0
    s1_ipca = 0
    s2_n = 0
    for protocol, name in iter_s1_blocks():
        s1_n += 1
        if s1_block_is_ipca(name):
            s1_ipca += 1
        sealed = load_s1_result(protocol)["blocks"][name]["ci"]["ci95"]
        assert isinstance(sealed, list) and len(sealed) == 2
    for _protocol, _split, _hkey in iter_s2_ci_cells():
        s2_n += 1
    assert s1_n == 114
    assert s1_ipca == 6
    assert s2_n == 27
    assert (s1_n - s1_ipca) + s1_ipca + s2_n == 141
