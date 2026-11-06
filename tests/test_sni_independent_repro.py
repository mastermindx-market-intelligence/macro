"""Independent reproduction of SNI v1.1 registered HIT/RETURN statistics.

This file is an SNI-local DRAFT comparison. It CONSUMES committed
observation files and committed result JSON owned by the S1/S2 runners,
Stock Identity / Data OS (opaque episode_key / issuer_key strings), and
the registered evaluation loop. It does not mint, derive, or guess
canonical HK/US issuer or security identifiers. It does not feed a
ranker, gate, sizer, signal, escalation, or trade path.

This is a reproduction of registered hit/return statistics. It is not
probabilistic forecast support.

Authority flags stay false. refuse_authority_true raises if a caller
passes any of them as true.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
S1_RUN = REPO_ROOT / "research" / "single_name_intelligence" / "runs" / "s1_residual_v1_1"
S2_RUN = REPO_ROOT / "research" / "single_name_intelligence" / "runs" / "s2_event_response_v1_1"
REVIEW_DOC = (
    REPO_ROOT
    / "research"
    / "single_name_intelligence"
    / "reviews"
    / "INDEPENDENT_REPRO_2026-10-13.md"
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
)

FORECAST_PHRASES = (
    "forecast support",
    "probabilistic forecast",
    "calibrated",
    "predictive power",
    "validated",
)

# ---------------------------------------------------------------------------
# Authority
# ---------------------------------------------------------------------------


def refuse_authority_true(flags):
    """Consume owner-supplied flags; raise if any authority bit is true."""
    if not isinstance(flags, dict):
        return flags
    for key in AUTHORITY_KEYS:
        if key in flags and flags[key] is True:
            raise ValueError(
                f"refusing {key}=True; IRP has no rank/gate/size/signal/"
                "escalation/trade authority"
            )
    return flags


def walk_authority_flags(obj, path=""):
    found = []
    if isinstance(obj, dict):
        refuse_authority_true(obj)
        for key, val in obj.items():
            here = f"{path}.{key}" if path else key
            if key in AUTHORITY_KEYS:
                found.append((here, val))
            found.extend(walk_authority_flags(val, here))
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            found.extend(walk_authority_flags(val, f"{path}[{i}]"))
    return found


# ---------------------------------------------------------------------------
# Loaders (paths injectable for mutants)
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


# ---------------------------------------------------------------------------
# Combinatorics (independent of production; Fraction then float)
# ---------------------------------------------------------------------------


def binom_tail_ge(k, n):
    """P(X >= k) for X ~ Bin(n, 1/2), exact via math.comb, as Fraction."""
    if n < 0:
        raise ValueError("n must be >= 0")
    if k <= 0:
        return Fraction(1)
    if k > n:
        return Fraction(0)
    num = sum(math.comb(n, i) for i in range(k, n + 1))
    return Fraction(num, 2 ** n)


def p_one_sided_greater(hits, n):
    return float(binom_tail_ge(hits, n))


def p_sign_two_sided(pos, neg):
    n = pos + neg
    if n == 0:
        return 1.0
    b = max(pos, neg)
    return float(min(Fraction(1), 2 * binom_tail_ge(b, n)))


def sign_of(x):
    if x is None:
        return 0
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


# ---------------------------------------------------------------------------
# S1 block parsing and counting
# ---------------------------------------------------------------------------


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


def _s1_p01p02_honest_and_excl(rows, split_wanted, baseline):
    """Re-derived P01/P02 counting.

    literal_rows = every observation row in the (protocol, subject, h) file.
    purged / quarantine counters are file-level (every PURGED_* / QUARANTINE
    split label in the file), matching the registered blocks.
    Analysis membership for a TRAIN/TUNE block uses time_split.
    Listed abstentions (resolver-none, fill-mismatch, missing-endpoint) leave
    the honest set. direction 0 is listed in detail and leaves the honest set
    but is not added to excluded_listed. exact-zero excess is a non-hit that
    stays in the honest set (ties_non_hit).
    """
    literal = len(rows)
    purged = sum(1 for r in rows if str(r.get("split") or "").startswith("PURGED"))
    quarantine = sum(
        1 for r in rows if str(r.get("split") or "").startswith("QUARANTINE")
    )
    excl = {
        "excluded_listed": 0,
        "confounded": 0,
        "absorbed": 0,
        "purged": purged,
        "quarantine": quarantine,
        "detail": {
            "abstain_resolver_none": 0,
            "abstain_fill_mismatch": 0,
            "abstain_missing_endpoint": 0,
            "direction_0_abstain": 0,
            "ties_non_hit": 0,
        },
    }
    honest = []
    for row in rows:
        if row.get("time_split") != split_wanted:
            continue
        split_lab = str(row.get("split") or "")
        manifest = str(row.get("manifest_split") or "")
        abstention = str(row.get("abstention") or "")
        if split_lab.startswith("PURGED") or manifest.startswith("PURGED"):
            continue
        if split_lab.startswith("QUARANTINE") or manifest.startswith("QUARANTINE"):
            continue
        blob = f"{split_lab}|{manifest}|{abstention}"
        listed = None
        if "ABSTAIN_RESOLVER_NONE" in blob:
            listed = "abstain_resolver_none"
        elif "ABSTAIN_FILL_MISMATCH" in blob:
            listed = "abstain_fill_mismatch"
        elif "ABSTAIN_MISSING_ENDPOINT" in blob:
            listed = "abstain_missing_endpoint"
        if listed is None and row.get("excess") is None:
            listed = "abstain_missing_endpoint"
        if listed is not None:
            excl["detail"][listed] += 1
            excl["excluded_listed"] += 1
            continue
        if baseline == "always_long":
            direction = row.get("always_long_direction")
        else:
            direction = row.get("trail63_direction")
        if direction is None or direction == 0:
            excl["detail"]["direction_0_abstain"] += 1
            continue
        if row.get("excess") == 0:
            excl["detail"]["ties_non_hit"] += 1
        honest.append(row)
    return literal, honest, excl


def repro_s1_p01p02_block(rows, meta):
    literal, honest, excl = _s1_p01p02_honest_and_excl(
        rows, meta["split"], meta["baseline"]
    )
    n = len(honest)
    cluster_n = len({r.get("anchor_session_date") for r in honest})
    if meta["h0"] == "H0_1":
        hits = 0
        for row in honest:
            if meta["baseline"] == "always_long":
                direction = row.get("always_long_direction")
            else:
                direction = row.get("trail63_direction")
            if sign_of(row.get("excess")) == direction:
                hits += 1
        statistic = {
            "hits": hits,
            "n": n,
            "hit_rate": round(hits / n, 6) if n else None,
        }
        p_value = p_one_sided_greater(hits, n) if n else None
    else:
        pos = sum(1 for r in honest if r.get("excess") is not None and r["excess"] > 0)
        neg = sum(1 for r in honest if r.get("excess") is not None and r["excess"] < 0)
        zeros = sum(1 for r in honest if r.get("excess") == 0)
        statistic = {"pos": pos, "neg": neg, "zeros_excluded": zeros}
        p_value = p_sign_two_sided(pos, neg)
    return {
        "honest_n": n,
        "cluster_n": cluster_n,
        "literal_rows": literal,
        "exclusions": excl,
        "statistic": statistic,
        "p_value": p_value,
        "gap": None,
    }


def repro_s1_p03_block(rows, meta):
    prev_name, next_name = P03_PAIR[meta["pair"]]
    models_present = {r.get("model") for r in rows}
    if next_name not in models_present:
        return {
            "honest_n": 0,
            "cluster_n": 0,
            "literal_rows": len(rows),
            "exclusions": {
                "excluded_listed": 0,
                "confounded": 0,
                "absorbed": 0,
                "purged": 0,
                "quarantine": 0,
                "detail": {"pair_incomplete": 0, "challenger_not_ok": 0},
            },
            "statistic": {"delta_R2": None, "paired_units": 0},
            "p_value": None,
            "gap": (
                "IRP-GAP: P03 IPCA model rows not committed in observations/ "
                f"({meta['protocol']}_{meta['subject']}_{meta['horizon']}.json "
                "has M0/M1/M2 only)"
            ),
        }
    by = {}
    for row in rows:
        by.setdefault(row["episode_key"], {})[row["model"]] = row
    purged = sum(1 for r in rows if str(r.get("split") or "").startswith("PURGED"))
    quarantine = sum(
        1 for r in rows if str(r.get("split") or "").startswith("QUARANTINE")
    )
    pair_incomplete = 0
    ds = []
    sum_r2 = 0.0
    honest_keys = []
    split = meta["split"]
    for ep, md in by.items():
        prev = md.get(prev_name)
        nxt = md.get(next_name)
        if prev is None or prev.get("split") != split:
            continue
        if prev.get("abstention") != "OK":
            continue
        if (
            nxt is None
            or nxt.get("split") != split
            or nxt.get("abstention") != "OK"
        ):
            pair_incomplete += 1
            continue
        r = prev["r__oc"]
        d = (r - prev["common__oc"]) ** 2 - (r - nxt["common__oc"]) ** 2
        ds.append(d)
        sum_r2 += r * r
        honest_keys.append(ep)
    n = len(honest_keys)
    delta = (sum(ds) / sum_r2) if sum_r2 else None
    excl = {
        "excluded_listed": pair_incomplete,
        "confounded": 0,
        "absorbed": 0,
        "purged": purged,
        "quarantine": quarantine,
        "detail": {"pair_incomplete": pair_incomplete, "challenger_not_ok": 0},
    }
    return {
        "honest_n": n,
        "cluster_n": n,
        "literal_rows": len(rows),
        "exclusions": excl,
        "statistic": {
            "delta_R2": None if delta is None else delta,
            "paired_units": n,
        },
        "p_value": None,
        "gap": None,
    }


def repro_s1_block(meta, obs_dir=None):
    rows = load_s1_obs(
        meta["protocol"], meta["subject"], meta["horizon"], obs_dir=obs_dir
    )
    if meta["protocol"] == "P03":
        return repro_s1_p03_block(rows, meta)
    return repro_s1_p01p02_block(rows, meta)


def _field_diff(protocol, block, field, expected, got, diffs):
    if expected != got:
        diffs.append(
            {
                "protocol": protocol,
                "block": block,
                "field": field,
                "expected": expected,
                "got": got,
            }
        )


def compare_s1_counts_one(protocol, block_name, result_obj=None, obs_dir=None):
    """Return (diffs, gap_reason). diffs empty and gap_reason set => GAP."""
    if result_obj is None:
        result_obj = load_s1_result(protocol)
    registered = result_obj["blocks"][block_name]
    meta = parse_s1_block_name(block_name)
    got = repro_s1_block(meta, obs_dir=obs_dir)
    if got["gap"]:
        return [], got["gap"]
    diffs = []
    _field_diff(protocol, block_name, "honest_n", registered["honest_n"], got["honest_n"], diffs)
    _field_diff(
        protocol, block_name, "cluster_n", registered["cluster_n"], got["cluster_n"], diffs
    )
    _field_diff(
        protocol,
        block_name,
        "literal_rows",
        registered["literal_rows"],
        got["literal_rows"],
        diffs,
    )
    reg_ex = registered["exclusions"]
    for key in ("excluded_listed", "confounded", "absorbed", "purged", "quarantine"):
        _field_diff(
            protocol,
            block_name,
            f"exclusions.{key}",
            reg_ex[key],
            got["exclusions"][key],
            diffs,
        )
    for key, val in reg_ex.get("detail", {}).items():
        _field_diff(
            protocol,
            block_name,
            f"exclusions.detail.{key}",
            val,
            got["exclusions"]["detail"].get(key),
            diffs,
        )
    reg_stat = registered["test"]["statistic"]
    got_stat = got["statistic"]
    for key, val in reg_stat.items():
        if key == "delta_R2":
            g = got_stat.get("delta_R2")
            if g is None or abs(g - val) > 5e-9:
                _field_diff(protocol, block_name, f"statistic.{key}", val, g, diffs)
            continue
        _field_diff(protocol, block_name, f"statistic.{key}", val, got_stat.get(key), diffs)
    return diffs, None


def compare_s1_pvalue_one(protocol, block_name, result_obj=None, obs_dir=None):
    if result_obj is None:
        result_obj = load_s1_result(protocol)
    registered = result_obj["blocks"][block_name]
    if "p_value" not in registered.get("test", {}):
        return [], None
    meta = parse_s1_block_name(block_name)
    got = repro_s1_block(meta, obs_dir=obs_dir)
    if got["gap"]:
        return [], got["gap"]
    diffs = []
    reg_p = registered["test"]["p_value"]
    got_p = got["p_value"]
    if got_p is None or abs(got_p - reg_p) > 1e-12:
        diffs.append(
            {
                "protocol": protocol,
                "block": block_name,
                "field": "p_value",
                "expected": reg_p,
                "got": got_p,
            }
        )
    alpha = registered["test"]["alpha"]
    reg_reject = bool(reg_p <= alpha)
    got_reject = bool(got_p <= alpha) if got_p is not None else None
    if reg_reject != got_reject:
        diffs.append(
            {
                "protocol": protocol,
                "block": block_name,
                "field": "reject_at_alpha",
                "expected": reg_reject,
                "got": got_reject,
            }
        )
    return diffs, None


def format_diff(d):
    return (
        f"{d['protocol']}/{d['block']}/{d['field']}: "
        f"expected={d['expected']!r} got={d['got']!r}"
    )


def iter_s1_blocks():
    out = []
    for protocol in ("P01", "P02", "P03"):
        result = load_s1_result(protocol)
        for name in result["blocks"]:
            out.append((protocol, name))
    return out


def s1_block_is_ipca(block_name):
    return block_name.split("|")[-1].startswith("IPCA")


# ---------------------------------------------------------------------------
# S2
# ---------------------------------------------------------------------------


def s2_horizon_int(hkey):
    return int(str(hkey).lstrip("h"))


def repro_s2_cell(episodes, protocol, split, hkey):
    """Counts that episodes.jsonl can support.

    honest_n PRIMARY = graded (census_only is false) episodes with matching
    protocol, split, horizon. census-only issuer rows never enter honest-N.
    QUARANTINE is listed and never evaluated: registered honest_n is 0; this
    reproduction follows the result file (0 graded QUARANTINE rows exist).
    cluster_n PRIMARY = distinct cluster_key among those graded rows.
    purged / confounded / absorbed are graded-only flags.
    literal_row_count and excluded_and_listed identities are not present in
    episodes.jsonl (GAP).
    """
    h = s2_horizon_int(hkey)
    graded = [
        e
        for e in episodes
        if e.get("protocol_id") == protocol
        and e.get("split") == split
        and int(e.get("horizon")) == h
        and not e.get("census_only")
    ]
    honest_n = len(graded)
    cluster_n = len({e.get("cluster_key") for e in graded})
    purged = sum(1 for e in graded if e.get("purged"))
    confounded = sum(1 for e in graded if e.get("confounded"))
    absorbed = sum(1 for e in graded if e.get("absorbed") or e.get("absorbed_count"))
    quarantine = 0
    if honest_n == 0:
        test_token = "ABSTAIN_NO_EPISODES"
    elif cluster_n < 2:
        test_token = "ABSTAIN_INSUFFICIENT_CLUSTERS"
    else:
        test_token = "TESTABLE"
    return {
        "honest_n_PRIMARY": honest_n,
        "cluster_n_PRIMARY": cluster_n,
        "confounded": confounded,
        "absorbed": absorbed,
        "purged": purged,
        "quarantine": quarantine,
        "test_token": test_token,
        "event_count": honest_n,
    }


def iter_s2_cells():
    cells = []
    for protocol in ("P04", "P05", "P06"):
        result = load_s2_result(protocol)
        for split, payload in result["splits"].items():
            if split == "TEST":
                cells.append((protocol, split, None))
                continue
            for hkey in payload:
                cells.append((protocol, split, hkey))
    return cells


def compare_s2_core(protocol, split, hkey, result_obj=None, episodes=None):
    if result_obj is None:
        result_obj = load_s2_result(protocol)
    if episodes is None:
        episodes = load_s2_episodes()
    diffs = []
    gaps = []
    if split == "TEST":
        registered = result_obj["splits"]["TEST"]
        expected = "none (prospective only; REG §2 registration gate not met)"
        if registered != expected:
            diffs.append(
                {
                    "protocol": protocol,
                    "block": "TEST",
                    "field": "TEST",
                    "expected": expected,
                    "got": registered,
                }
            )
        return diffs, gaps
    cell = result_obj["splits"][split][hkey]
    got = repro_s2_cell(episodes, protocol, split, hkey)
    block = f"{split}/{hkey}"
    _field_diff(
        protocol,
        block,
        "honest_n.PRIMARY",
        cell["honest_n"]["PRIMARY"],
        got["honest_n_PRIMARY"],
        diffs,
    )
    _field_diff(
        protocol,
        block,
        "cluster_n.PRIMARY",
        cell["cluster_n"]["PRIMARY"],
        got["cluster_n_PRIMARY"],
        diffs,
    )
    vis = cell["visible_exclusions"]
    for key in ("confounded", "absorbed", "purged", "quarantine"):
        _field_diff(protocol, block, f"exclusions.{key}", vis[key], got[key], diffs)
    gaps.append(
        {
            "protocol": protocol,
            "block": block,
            "field": "literal_row_count",
            "reason": (
                "IRP-GAP: S2 literal_row_count source not committed in "
                "observations/episodes.jsonl"
            ),
        }
    )
    gaps.append(
        {
            "protocol": protocol,
            "block": block,
            "field": "excluded_and_listed",
            "reason": (
                "IRP-GAP: S2 excluded_and_listed identities not committed in "
                "observations/episodes.jsonl"
            ),
        }
    )
    return diffs, gaps


def compare_s2_stats(protocol, split, hkey, result_obj=None, episodes=None):
    if result_obj is None:
        result_obj = load_s2_result(protocol)
    if episodes is None:
        episodes = load_s2_episodes()
    diffs = []
    if split == "TEST":
        return diffs
    cell = result_obj["splits"][split][hkey]
    got = repro_s2_cell(episodes, protocol, split, hkey)
    block = f"{split}/{hkey}"
    _field_diff(protocol, block, "test", cell["test"], got["test_token"], diffs)
    fam = cell.get("family_row") or {}
    if "abstention_state" in fam:
        _field_diff(
            protocol,
            block,
            "family_row.abstention_state",
            fam["abstention_state"],
            got["test_token"],
            diffs,
        )
    if "event_count" in fam:
        _field_diff(
            protocol,
            block,
            "family_row.event_count",
            fam["event_count"],
            got["event_count"],
            diffs,
        )
    # Hit/excess: committed episodes carry no numeric excess for v1.1
    # (RETIRED-CONTAMINATED / census-only / absent). Registered hit is null
    # wherever a baseline episode exists.
    for bname, bval in (cell.get("baselines") or {}).items():
        if not isinstance(bval, dict):
            continue
        for ep in bval.get("episodes") or []:
            if ep.get("hit") is not None:
                diffs.append(
                    {
                        "protocol": protocol,
                        "block": block,
                        "field": f"baselines.{bname}.hit",
                        "expected": None,
                        "got": ep.get("hit"),
                    }
                )
    return diffs


# ---------------------------------------------------------------------------
# AST guard
# ---------------------------------------------------------------------------


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
# Mutants
# ---------------------------------------------------------------------------


def mutant_m1_hit_plus_one(tmp_path):
    src = S1_RUN / "results" / "P01.json"
    dst_dir = tmp_path / "results"
    dst_dir.mkdir()
    obj = load_json(src)
    name = next(
        n for n in obj["blocks"] if n.endswith("|always_long|H0_1") and "|h=5|TRAIN|" in n
    )
    obj["blocks"][name]["test"]["statistic"]["hits"] += 1
    dest = dst_dir / "P01.json"
    dest.write_text(json.dumps(obj), encoding="utf-8")
    diffs, gap = compare_s1_counts_one("P01", name, result_obj=obj)
    return diffs, gap


def mutant_m2_pvalue_perturb(tmp_path):
    src = S1_RUN / "results" / "P01.json"
    obj = load_json(src)
    name = next(
        n for n in obj["blocks"] if n.endswith("|always_long|H0_1") and "|h=5|TRAIN|" in n
    )
    obj["blocks"][name]["test"]["p_value"] += 1e-9
    diffs, gap = compare_s1_pvalue_one("P01", name, result_obj=obj)
    return diffs, gap


def mutant_m3_drop_obs_row(tmp_path):
    obs_dir = tmp_path / "observations"
    obs_dir.mkdir()
    src = S1_RUN / "observations" / "P01_adr_baba_5.json"
    rows = load_json(src)
    dropped = rows[:-1]
    (obs_dir / "P01_adr_baba_5.json").write_text(
        json.dumps(dropped), encoding="utf-8"
    )
    result = load_s1_result("P01")
    name = next(
        n
        for n in result["blocks"]
        if n.endswith("|always_long|H0_1") and "|h=5|TRAIN|" in n
    )
    diffs, gap = compare_s1_counts_one("P01", name, result_obj=result, obs_dir=obs_dir)
    return diffs, gap


# hashlib is in the allowed import set; pin the comparison identity of one
# observation file so a silent empty-read would surface.
_OBS_FINGERPRINT_PATH = S1_RUN / "observations" / "P01_adr_baba_5.json"
OBS_SHA256 = hashlib.sha256(_OBS_FINGERPRINT_PATH.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_irp_00_no_production_imports():
    source = Path(__file__).read_text(encoding="utf-8")
    hits = production_import_violations(source)
    assert hits == [], f"production imports in IRP test: {hits}"


def _irp_01_params():
    params = []
    for protocol, name in iter_s1_blocks():
        marks = []
        if s1_block_is_ipca(name):
            marks.append(
                pytest.mark.xfail(
                    strict=True,
                    reason=(
                        "IRP-GAP: P03 IPCA model rows not committed in "
                        "observations/"
                    ),
                )
            )
        params.append(pytest.param(protocol, name, marks=marks, id=f"{protocol}::{name}"))
    return params


@pytest.mark.parametrize("protocol,block_name", _irp_01_params())
def test_irp_01_s1_counts(protocol, block_name):
    diffs, gap = compare_s1_counts_one(protocol, block_name)
    if gap:
        pytest.fail(gap)
    assert diffs == [], "\n".join(format_diff(d) for d in diffs)


def _irp_02_params():
    params = []
    for protocol, name in iter_s1_blocks():
        result = load_s1_result(protocol)
        if "p_value" not in result["blocks"][name].get("test", {}):
            continue
        params.append(pytest.param(protocol, name, id=f"{protocol}::{name}"))
    return params


@pytest.mark.parametrize("protocol,block_name", _irp_02_params())
def test_irp_02_s1_pvalues(protocol, block_name):
    diffs, gap = compare_s1_pvalue_one(protocol, block_name)
    if gap:
        pytest.fail(gap)
    assert diffs == [], "\n".join(format_diff(d) for d in diffs)


def _irp_03_params():
    params = []
    for protocol, split, hkey in iter_s2_cells():
        if split == "TEST":
            params.append(
                pytest.param(protocol, split, hkey, "core", id=f"{protocol}::TEST")
            )
            continue
        params.append(
            pytest.param(
                protocol, split, hkey, "core", id=f"{protocol}::{split}/{hkey}::core"
            )
        )
        params.append(
            pytest.param(
                protocol,
                split,
                hkey,
                "literal_row_count",
                marks=pytest.mark.xfail(
                    strict=True,
                    reason=(
                        "IRP-GAP: S2 literal_row_count source not committed in "
                        "observations/episodes.jsonl"
                    ),
                ),
                id=f"{protocol}::{split}/{hkey}::literal",
            )
        )
        listed_marks = []
        # P06 registered listed identities are empty; that field MATCHES
        # episodes.jsonl (no identities). P04/P05 list identities that are
        # not in episodes.jsonl — GAP.
        if protocol in ("P04", "P05"):
            listed_marks.append(
                pytest.mark.xfail(
                    strict=True,
                    reason=(
                        "IRP-GAP: S2 excluded_and_listed identities not committed "
                        "in observations/episodes.jsonl"
                    ),
                )
            )
        params.append(
            pytest.param(
                protocol,
                split,
                hkey,
                "excluded_and_listed",
                marks=listed_marks,
                id=f"{protocol}::{split}/{hkey}::listed",
            )
        )
    return params


@pytest.mark.parametrize("protocol,split,hkey,aspect", _irp_03_params())
def test_irp_03_s2_counts(protocol, split, hkey, aspect):
    result = load_s2_result(protocol)
    episodes = load_s2_episodes()
    if aspect == "core":
        diffs, _gaps = compare_s2_core(
            protocol, split, hkey, result_obj=result, episodes=episodes
        )
        assert diffs == [], "\n".join(format_diff(d) for d in diffs)
        return
    if split == "TEST":
        pytest.fail("TEST split has no numeric count aspect")
    cell = result["splits"][split][hkey]
    if aspect == "literal_row_count":
        # episodes.jsonl cannot produce the registered literal_row_count.
        n_lines = sum(
            1
            for e in episodes
            if e.get("protocol_id") == protocol
            and e.get("split") == split
            and int(e.get("horizon")) == s2_horizon_int(hkey)
        )
        assert n_lines == cell["literal_row_count"], (
            f"{protocol}/{split}/{hkey}/literal_row_count: "
            f"expected={cell['literal_row_count']!r} got={n_lines!r} "
            "(IRP-GAP: source not in episodes.jsonl)"
        )
        return
    if aspect == "excluded_and_listed":
        listed = cell["visible_exclusions"]["excluded_and_listed"]
        count = cell["visible_exclusions"]["excluded_and_listed_count"]
        # No identity strings of this form exist on episode rows.
        assert listed == [] and count == 0, (
            f"{protocol}/{split}/{hkey}/excluded_and_listed: "
            f"expected={listed!r} count={count!r} got=[]/0 "
            "(IRP-GAP: identities not in episodes.jsonl)"
        )
        return
    raise AssertionError(f"unknown aspect {aspect}")


def _irp_04_params():
    params = []
    for protocol, split, hkey in iter_s2_cells():
        if split == "TEST":
            continue
        params.append(
            pytest.param(protocol, split, hkey, id=f"{protocol}::{split}/{hkey}")
        )
    return params


@pytest.mark.parametrize("protocol,split,hkey", _irp_04_params())
def test_irp_04_s2_stats(protocol, split, hkey):
    diffs = compare_s2_stats(protocol, split, hkey)
    assert diffs == [], "\n".join(format_diff(d) for d in diffs)


def test_irp_05_no_forecast_language():
    text = REVIEW_DOC.read_text(encoding="utf-8")
    marker = "## What this does NOT prove"
    assert marker in text, "review doc missing 'What this does NOT prove' section"
    head, _sep, _tail = text.partition(marker)
    lowered = head.lower()
    found = [p for p in FORECAST_PHRASES if p in lowered]
    assert found == [], f"forbidden phrases outside the NOT-prove section: {found}"


def test_irp_06_authority_false():
    for protocol in ("P01", "P02", "P03"):
        found = walk_authority_flags(load_s1_result(protocol), protocol)
        for path, val in found:
            assert val is False, f"{path} expected False got {val!r}"
    for protocol in ("P04", "P05", "P06"):
        found = walk_authority_flags(load_s2_result(protocol), protocol)
        assert found, f"{protocol} result file has no authority flags"
        for path, val in found:
            assert val is False, f"{path} expected False got {val!r}"


@pytest.mark.parametrize(
    "kind",
    ["m1_hit_plus_one", "m2_pvalue_perturb", "m3_drop_obs_row"],
)
def test_irp_07_mutants_are_caught(kind, tmp_path):
    if kind == "m1_hit_plus_one":
        diffs, gap = mutant_m1_hit_plus_one(tmp_path)
    elif kind == "m2_pvalue_perturb":
        diffs, gap = mutant_m2_pvalue_perturb(tmp_path)
    elif kind == "m3_drop_obs_row":
        diffs, gap = mutant_m3_drop_obs_row(tmp_path)
    else:
        raise AssertionError(kind)
    assert gap is None, gap
    assert diffs, f"{kind} produced no DIFF (comparison is blind)"
    # fingerprint still reads the committed file, not the mutant
    assert (
        hashlib.sha256(_OBS_FINGERPRINT_PATH.read_bytes()).hexdigest() == OBS_SHA256
    )
    assert copy.deepcopy({"kind": kind})["kind"] == kind
