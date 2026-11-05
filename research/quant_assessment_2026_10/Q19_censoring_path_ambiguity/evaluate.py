from __future__ import annotations

"""Q19 evaluator: first-passage ambiguity and censoring-aware outcome diagnostics.

RESEARCH ONLY. Reads the pinned, append-only options signal-episode ledgers
(read-only, exact byte prefixes), and writes only under this study directory.

Modes:
  --mode baseline   reproduce the OA-3-style status ruler census (no outcome values)
  --mode primary    the single frozen primary trial (PREREG sections 3-17)

Refuses to run when sha256(PREREG.md) differs from the hash in FREEZE.log.
Every run (including refusals and crashes) is appended to RUNS.log with the
command, exit code, input sha256s and output sha256s.
"""

import argparse
import collections
import csv
import hashlib
import io
import json
import math
import os
import statistics
import sys
import traceback
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine import outcome_first_passage_ambiguity as fp  # noqa: E402

DATA = "/Users/chriswong/Documents/Cluade/macro-main/data"
PREREG = os.path.join(HERE, "PREREG.md")
FREEZE = os.path.join(HERE, "FREEZE.log")
AMEND = os.path.join(HERE, "PREREG_AMENDMENT.md")
RUNS = os.path.join(HERE, "RUNS.log")
RESULTS = os.path.join(HERE, "results")
MODULE = os.path.join(ROOT, "engine", "outcome_first_passage_ambiguity.py")

PINS = [
    ("options_signal_episode/episodes.jsonl", 45982874,
     "a7c53ed59a9fd268470f9b107c8b9665707e31192e23331d2ad9e736f9270652"),
    ("options_signal_episode/checkpoint.json", 3987,
     "b5370e086dba0d86f0c41e95c223b8bf30ba6b56ac8ca5b628df2b51b2392505"),
    ("options_signal_episode/outcomes_session.jsonl", 100471221,
     "fc02c3f6d224ada2179f89fcf09d63866567e4132d6d6738ccc90c012c9b6311"),
    ("options_signal_episode/outcomes_session_parts/part-000001.jsonl", 50327529,
     "a74f35d2d1f73b71e27cfdf0f5b7ae5b11e8750feb853f3eb50aeb2713c52637"),
    ("options_signal_episode/outcomes_session_parts/part-000002.jsonl", 50330070,
     "8e80c5a5d75a253155a94aa5c8c771c21a5ac40e79f1dceeb5fa8960bdc52c40"),
    ("options_signal_episode/outcomes_session_parts/part-000003.jsonl", 50330244,
     "02afa5176952bfb16705d3f2e87b5b3d23aa0d566616d8c14b664c6461a72bab"),
    ("options_signal_episode/outcomes_session_parts/part-000004.jsonl", 50330449,
     "52096168b293aec42ac2f4bc203615903ab8c85fac80e21af21de1dff3b3836b"),
    ("options_signal_episode/outcomes_session_parts/part-000005.jsonl", 50330419,
     "bb1385bd20cf444daadf5125fe47789211d921680e6747c57137a6a57df2ad3f"),
    ("options_signal_episode/outcomes_session_parts/part-000006.jsonl", 50329411,
     "2695f96d57a1c90bab3f056a055a063deeb08928f44c3bb042f7ec384414bab8"),
    ("options_signal_episode/outcomes_session_parts/part-000007.jsonl", 26727345,
     "0fa3ba19ab62321dcc8d11368535e18550635085debcf794da3ef2cfb67513f7"),
]

HORIZONS = ("eod", "1d", "3d", "5d", "10d")
HORIZON_INDEX = {"eod": 0, "1d": 1, "3d": 3, "5d": 5, "10d": 10}
N_TRAIN_DATES = 14
BLOCK_LEN = 5
N_BOOT = 2000
SEED = 19
EFFECT_BAR = 0.01
LOTO_BAR = 0.005
MIN_TEST_UNITS = 200
MIN_TEST_DATES = 5
ATTRITION_FLAG_PP = 0.20
REL_TOL = 1e-9


class PinFailure(Exception):
    pass


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_hash() -> str | None:
    with open(FREEZE, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("sha256:"):
                return line.split(":", 1)[1].strip()
    return None


def read_pinned(rel: str, nbytes: int, digest: str) -> bytes:
    path = os.path.join(DATA, rel)
    if not os.path.exists(path):
        raise PinFailure(f"missing_input:{rel}")
    with open(path, "rb") as fh:
        blob = fh.read(nbytes)
    if len(blob) != nbytes:
        raise PinFailure(f"short_input:{rel}:{len(blob)}<{nbytes}")
    if hashlib.sha256(blob).hexdigest() != digest:
        raise PinFailure(f"sha256_mismatch:{rel}")
    if rel.endswith(".jsonl") and not blob.endswith(b"\n"):
        raise PinFailure(f"prefix_not_line_aligned:{rel}")
    return blob


def epoch(iso: object) -> int | None:
    if not isinstance(iso, str) or not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso).timestamp())
    except ValueError:
        return None


def utc_date(iso: object) -> str | None:
    if not isinstance(iso, str) or not iso:
        return None
    try:
        return datetime.fromisoformat(iso).astimezone(timezone.utc).date().isoformat()
    except ValueError:
        return None


def num(x: object) -> float | None:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    v = float(x)
    return v if math.isfinite(v) else None


def same(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=0.0)


# --------------------------------------------------------------------------- load


def load_episodes(blob: bytes) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in io.BytesIO(blob):
        if not line.strip():
            continue
        r = json.loads(line)
        eid = r.get("episode_id")
        if eid is None or eid in out:
            continue
        out[eid] = {"ticker": r.get("ticker"), "session_date": r.get("session_date"),
                    "decision_at": r.get("decision_at")}
    return out


def compact_row(r: dict) -> dict:
    u = r.get("underlying") or {}
    ev = u.get("evidence") or {}
    ext = ev.get("extrema") or {}
    prov = r.get("provenance") or {}
    return {
        "episode_id": r.get("episode_id"),
        "outcome_id": r.get("outcome_id"),
        "horizon": r.get("horizon"),
        "status": r.get("status"),
        "reason": r.get("reason"),
        "u_status": u.get("status"),
        "matured_at": r.get("matured_at"),
        "label_authority": r.get("label_authority"),
        "price_source": prov.get("price_source"),
        "price_basis": prov.get("price_basis"),
        "source_available_at": prov.get("source_available_at"),
        "entry_time": u.get("entry_time"),
        "entry_bar_time": (ev.get("entry") or {}).get("bar_time"),
        "entry_price": num(u.get("entry_price")),
        "high": num((ext.get("high") or {}).get("value")),
        "low": num((ext.get("low") or {}).get("value")),
    }


def load_rows(blobs: list[bytes]) -> list[dict]:
    rows: list[dict] = []
    for blob in blobs:
        for line in io.BytesIO(blob):
            if line.strip():
                rows.append(compact_row(json.loads(line)))
    return rows


# --------------------------------------------------------------------------- baseline


def run_baseline(episodes: dict, rows: list[dict], checkpoint: dict) -> dict:
    mix = collections.Counter()
    for r in rows:
        mix[(r["horizon"], r["status"], r["reason"])] += 1
    per_h = collections.defaultdict(dict)
    for (h, s, rsn), c in sorted(mix.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        per_h[str(h)][f"{s}|{rsn}"] = c
    ep_h = collections.defaultdict(set)
    oid = collections.Counter()
    eh_dup = collections.Counter()
    for r in rows:
        ep_h[r["episode_id"]].add(r["horizon"])
        oid[r["outcome_id"]] += 1
        eh_dup[(r["episode_id"], r["horizon"])] += 1
    sets = collections.Counter(",".join(h for h in HORIZONS if h in v) or "none"
                               for v in ep_h.values())
    eps_per_day = collections.Counter(e["session_date"] for e in episodes.values())
    ck = checkpoint.get("sessions") or {}
    ck_cmp = {d: {"checkpoint_records": (ck.get(d) or {}).get("records"),
                  "episodes_session_date": eps_per_day.get(d, 0)}
              for d in sorted(set(ck) | set(eps_per_day), key=str)}
    ck_match = sum(1 for v in ck_cmp.values() if v["checkpoint_records"] == v["episodes_session_date"])
    classes = collections.Counter()
    for eid in episodes:
        classes[episode_class(eid, ep_rows_index(rows).get(eid, {}), "10d")[0]] += 1
    return {
        "mode": "baseline",
        "uses_outcome_values": False,
        "episodes_distinct": len(episodes),
        "session_rows": len(rows),
        "episodes_with_session_rows": len(ep_h),
        "episodes_without_session_rows": len(set(episodes) - set(ep_h)),
        "session_rows_without_episode": len(set(ep_h) - set(episodes)),
        "duplicate_outcome_ids": sum(1 for v in oid.values() if v > 1),
        "duplicate_episode_horizon_pairs": sum(1 for v in eh_dup.values() if v > 1),
        "status_reason_mix_by_horizon": per_h,
        "horizon_coverage_sets": dict(sets.most_common()),
        "checkpoint_vs_episodes_by_session_date": ck_cmp,
        "checkpoint_sessions_matching_episode_counts": ck_match,
        "checkpoint_sessions": len(ck),
        "episode_attrition_class_10d": dict(classes),
    }


_IDX_CACHE: dict[int, dict] = {}


def ep_rows_index(rows: list[dict]) -> dict[str, dict[str, list[dict]]]:
    key = id(rows)
    if key not in _IDX_CACHE:
        idx: dict[str, dict[str, list[dict]]] = collections.defaultdict(lambda: collections.defaultdict(list))
        for r in rows:
            idx[r["episode_id"]][r["horizon"]].append(r)
        _IDX_CACHE[key] = idx
    return _IDX_CACHE[key]


def row_complete(r: dict) -> bool:
    return (fp.classify_attrition(r["status"], r["reason"])["class"] == fp.OBSERVED
            and r["u_status"] == "complete" and r["entry_price"] is not None
            and r["high"] is not None and r["low"] is not None and r["entry_time"])


def pick_row(cands: list[dict]) -> tuple[dict | None, str]:
    """One row per (episode, horizon): a unique complete row, else the classification row."""
    comp = [r for r in cands if row_complete(r)]
    if comp:
        first = comp[0]
        for r in comp[1:]:
            if not (same(r["entry_price"], first["entry_price"]) and same(r["high"], first["high"])
                    and same(r["low"], first["low"]) and r["entry_time"] == first["entry_time"]):
                return None, "duplicate_rows_disagree"
        return first, "ok"
    return (cands[0] if cands else None), "ok"


def episode_class(eid: str, by_h: dict[str, list[dict]], horizon: str) -> tuple[str, str | None, dict | None]:
    """(censoring class, reason, chosen row) for one episode at ``horizon``."""
    if not by_h:
        return fp.INFORMATIVE_UNKNOWN, "no_session_row", None
    cands = by_h.get(horizon) or []
    if not cands:
        return fp.ADMINISTRATIVE_PENDING, f"{horizon}_row_absent_shorter_present", None
    row, note = pick_row(cands)
    if row is None:
        return fp.INVALID, note, None
    cls = fp.classify_attrition(row["status"], row["reason"])
    if cls["class"] == fp.OBSERVED and not row_complete(row):
        return fp.INFORMATIVE_UNKNOWN, "underlying_incomplete_or_extrema_missing", row
    return cls["class"], cls["reason"], row


# --------------------------------------------------------------------------- primary


def build_units(episodes: dict, rows: list[dict], horizon: str, finer: tuple[str, ...]) -> dict:
    idx = ep_rows_index(rows)
    fallback_ticker = 0
    paths: dict[tuple, dict] = {}
    for eid in sorted(episodes):
        by_h = idx.get(eid, {})
        cls, reason, row = episode_class(eid, by_h, horizon)
        if not by_h:
            # Amendment A5: no session row -> pseudo-path keyed by (ticker, decision_at rounded
            # up to the next whole UTC hour), dated by session_date; informative_unknown.
            ticker = episodes[eid]["ticker"]
            t_dec = epoch(episodes[eid]["decision_at"])
            key = ("no_session_row", ticker, None if t_dec is None else -(-t_dec // 3600) * 3600,
                   None if t_dec is not None else eid)
            date = episodes[eid]["session_date"]
        else:
            any_row = row or next(r for hs in HORIZONS for r in by_h.get(hs, []))
            ticker = episodes[eid]["ticker"]
            if not ticker:
                ticker = os.path.splitext(os.path.basename(any_row["price_source"] or ""))[0] or None
                fallback_ticker += 1
            key = (ticker, any_row["entry_time"])
            date = utc_date(any_row["entry_time"])
        p = paths.setdefault(key, {"key": key, "ticker": ticker, "date": date, "members": []})
        p["members"].append((eid, cls, reason, row))
    units = []
    reasons_fallback = collections.Counter()
    mixed = 0
    for key, p in paths.items():
        obs = [m for m in p["members"] if m[1] == fp.OBSERVED]
        classes = {m[1] for m in p["members"]}
        if len(classes) > 1:
            mixed += 1
        unit = {"key": key, "ticker": p["ticker"], "date": p["date"],
                "n_episodes": len(p["members"]),
                "n_observed_episodes": len(obs), "state": None, "coarse": None,
                "note": None, "fallback": None, "refined_index": None,
                "max_index": 0}
        if obs:
            r0 = obs[0][3]
            consistent = all(same(m[3]["entry_price"], r0["entry_price"]) and same(m[3]["high"], r0["high"])
                             and same(m[3]["low"], r0["low"]) for m in obs[1:])
            unit["censoring"] = fp.OBSERVED if consistent else fp.INVALID
            unit["reason"] = None if consistent else "path_rows_disagree"
            unit["rep"] = min(m[0] for m in obs)
            unit["rep_row"] = next(m[3] for m in obs if m[0] == unit["rep"])
        elif fp.INFORMATIVE_UNKNOWN in classes:
            unit["censoring"] = fp.INFORMATIVE_UNKNOWN
            unit["reason"] = sorted({m[2] or "" for m in p["members"] if m[1] == fp.INFORMATIVE_UNKNOWN})[0]
        elif fp.INVALID in classes:
            unit["censoring"] = fp.INVALID
            unit["reason"] = sorted({m[2] or "" for m in p["members"] if m[1] == fp.INVALID})[0]
        else:
            unit["censoring"] = fp.ADMINISTRATIVE_PENDING
            unit["reason"] = sorted({m[2] or "" for m in p["members"]})[0]
        # largest horizon index with a complete row among members (for the incidence censoring time)
        best = 0
        for m in p["members"]:
            for hs in HORIZONS:
                if any(row_complete(r) for r in idx.get(m[0], {}).get(hs, [])):
                    best = max(best, HORIZON_INDEX[hs])
        unit["max_index"] = best
        units.append(unit)
    return {"units": units, "fallback_ticker": fallback_ticker, "mixed_class_paths": mixed,
            "reasons_fallback": reasons_fallback}


def assign_states(units: list[dict], rows: list[dict], horizon: str, finer: tuple[str, ...],
                  b: float) -> collections.Counter:
    idx = ep_rows_index(rows)
    fallbacks: collections.Counter = collections.Counter()
    for u in units:
        if u["censoring"] != fp.OBSERVED:
            continue
        top = u["rep_row"]
        e = top["entry_price"]
        upper, lower = e * (1 + b), e * (1 - b)
        coarse = fp.first_passage([(top["high"], top["low"])], upper, lower)["state"]
        u["coarse"] = coarse
        qclock = epoch(top["matured_at"])
        windows = []
        reason = None
        for hs in finer:
            row, note = pick_row(idx.get(u["rep"], {}).get(hs, []))
            if row is None:
                reason = f"{hs}:{note}" if note != "ok" else f"{hs}:missing"
                break
            if not row_complete(row):
                reason = f"{hs}:incomplete:{row['status']}|{row['reason']}"
                break
            if qclock is None:
                reason = "question_clock_unknown"
                break
            t_m, t_s = epoch(row["matured_at"]), epoch(row["source_available_at"])
            ev_clock = None if (t_m is None and t_s is None) else max(x for x in (t_m, t_s) if x is not None)
            ok, why = fp.evidence_admissible(
                qclock, ev_clock,
                rights_ok=(row["label_authority"] == "research_only" and top["label_authority"] == "research_only"
                           and row["price_source"] == top["price_source"]),
                same_entry=(row["entry_time"] == top["entry_time"] and row["entry_bar_time"] == top["entry_bar_time"]
                            and same(row["entry_price"], top["entry_price"])),
                same_price_basis=(row["price_basis"] == top["price_basis"]))
            if not ok:
                reason = f"{hs}:inadmissible:{why}"
                break
            windows.append((row["high"], row["low"]))
        nested = None
        if reason is None:
            windows.append((top["high"], top["low"]))
            try:
                res = fp.first_passage(windows, upper, lower, cumulative=True)
                nested = res["state"]
                if res["window_index"] is not None:
                    u["refined_index"] = HORIZON_INDEX[(finer + (horizon,))[res["window_index"]]]
            except ValueError as exc:
                reason = f"nested:{exc}"
        if reason is not None:
            fallbacks[":".join(reason.split(":")[:2])] += 1
            fallbacks["_detail:" + reason] += 1
            ref = fp.refine_state(coarse, None, False)
        else:
            ref = fp.refine_state(coarse, nested, True)
        u["state"] = ref["state"]
        u["note"] = ref["note"]
        u["fallback"] = reason
        if ref["state"] != fp.AMBIGUOUS and ref["state"] != fp.NEITHER and u["refined_index"] is None:
            u["refined_index"] = HORIZON_INDEX[horizon]
    return fallbacks


def e_counts(units: list[dict]) -> tuple[int, int, int, int]:
    n = num_e = num_ep = amb = 0
    for u in units:
        if u["censoring"] != fp.OBSERVED:
            continue
        n += 1
        if u["coarse"] == fp.AMBIGUOUS:
            amb += 1
            if u["state"] == fp.LOWER_FIRST:
                num_e += 1
            elif u["state"] == fp.UPPER_FIRST:
                num_ep += 1
    return n, num_e, num_ep, amb


def ratio_stat(which: int):
    def stat(blocks: list[list[dict]]) -> float | None:
        flat = [u for blk in blocks for u in blk]
        c = e_counts(flat)
        return (c[which] / c[0]) if c[0] > 0 else None
    return stat


def summarize(units_all: list[dict], horizon: str, train_dates: list[str], test_dates: list[str],
              b: float, fallbacks: collections.Counter, with_boot: bool) -> dict:
    test = [u for u in units_all if u["date"] in set(test_dates)]
    train = [u for u in units_all if u["date"] in set(train_dates)]
    n, ne, nep, amb = e_counts(test)
    obs_test = [u for u in test if u["censoring"] == fp.OBSERVED]
    by_date = collections.defaultdict(list)
    for u in test:
        by_date[u["date"]].append(u)
    obs_dates = [d for d in test_dates if any(u["censoring"] == fp.OBSERVED for u in by_date.get(d, []))]
    blocks = [by_date[d] for d in obs_dates]
    out: dict = {
        "horizon": horizon, "b": b,
        "test": {"n_units": len(test), "n_observed": n, "E_num": ne, "E_p_num": nep,
                 "coarse_ambiguous": amb,
                 "E": ne / n if n else None, "E_p": nep / n if n else None,
                 "coarse_ambiguous_share": amb / n if n else None,
                 "refined_ambiguous_share": (sum(1 for u in obs_test if u["state"] == fp.AMBIGUOUS) / n) if n else None},
        "honest_n": {"test_dates_all": len(test_dates), "test_dates_with_observed": len(obs_dates),
                     "test_tickers_observed": len({u["ticker"] for u in obs_test}),
                     "test_paths_observed": n, "test_paths_all": len(test)},
        "train": {"n_units": len(train), "n_observed": sum(1 for u in train if u["censoring"] == fp.OBSERVED)},
    }
    bunits_coarse = [{"censoring": u["censoring"], "state": u["coarse"] if u["censoring"] == fp.OBSERVED else None}
                     for u in test]
    bunits_ref = [{"censoring": u["censoring"], "state": u["state"] if u["censoring"] == fp.OBSERVED else None}
                  for u in test]
    out["bounds_coarse_B3"] = fp.first_passage_bounds(bunits_coarse)
    out["bounds_refined_proposed"] = fp.first_passage_bounds(bunits_ref)
    obs_c = out["bounds_coarse_B3"]["observed"]
    out["conventions_coarse"] = {"B1_pessimistic_upper_first": obs_c["pessimistic_upper_first"],
                                 "B2_optimistic_upper_first": obs_c["optimistic_upper_first"],
                                 "B3_identified_upper_first_bounds": obs_c["upper_first"]}
    out["fallbacks"] = {k: v for k, v in sorted(fallbacks.items()) if not k.startswith("_detail:")}
    out["fallback_detail"] = {k[8:]: v for k, v in sorted(fallbacks.items()) if k.startswith("_detail:")}
    out["refine_notes"] = dict(collections.Counter(u["note"] for u in obs_test))
    if with_boot:
        out["bootstrap"] = {
            "E": fp.circular_block_bootstrap(blocks, ratio_stat(1), block_len=BLOCK_LEN, n_boot=N_BOOT, seed=SEED),
            "E_p": fp.circular_block_bootstrap(blocks, ratio_stat(2), block_len=BLOCK_LEN, n_boot=N_BOOT, seed=SEED),
            "coarse_ambiguous_share": fp.circular_block_bootstrap(blocks, ratio_stat(3), block_len=BLOCK_LEN,
                                                                  n_boot=N_BOOT, seed=SEED),
            "block_dates": obs_dates,
        }
        tick = sorted({u["ticker"] for u in obs_test}, key=str)
        loto = {}
        for t in tick:
            c = e_counts([u for u in test if u["ticker"] != t])
            loto[str(t)] = c[1] / c[0] if c[0] else None
        vals = [v for v in loto.values() if v is not None]
        out["leave_one_ticker_out"] = {"min_E": min(vals) if vals else None, "by_ticker": loto}
        per_t = collections.defaultdict(lambda: [0, 0, 0])
        for u in obs_test:
            per_t[str(u["ticker"])][0] += 1
            if u["coarse"] == fp.AMBIGUOUS and u["state"] == fp.LOWER_FIRST:
                per_t[str(u["ticker"])][1] += 1
            if u["coarse"] == fp.AMBIGUOUS:
                per_t[str(u["ticker"])][2] += 1
        out["per_ticker"] = {k: {"n_observed": v[0], "E_num": v[1], "coarse_ambiguous": v[2]}
                             for k, v in sorted(per_t.items())}
        # episode-weighted E (secondary)
        w_n = sum(u["n_observed_episodes"] for u in obs_test)
        w_e = sum(u["n_observed_episodes"] for u in obs_test
                  if u["coarse"] == fp.AMBIGUOUS and u["state"] == fp.LOWER_FIRST)
        out["episode_weighted"] = {"n_observed_episodes": w_n, "E": w_e / w_n if w_n else None}
        out["per_date"] = {d: {"n_units": len(by_date.get(d, [])),
                               "n_observed": sum(1 for u in by_date.get(d, []) if u["censoring"] == fp.OBSERVED),
                               "E_num": sum(1 for u in by_date.get(d, []) if u["censoring"] == fp.OBSERVED
                                            and u["coarse"] == fp.AMBIGUOUS and u["state"] == fp.LOWER_FIRST)}
                           for d in test_dates}
    return out


def incidence(test_units: list[dict]) -> dict:
    cu = []
    for u in test_units:
        c = u["censoring"]
        if c == fp.OBSERVED:
            st = u["state"]
            ev = {"upper_first": "upper", "lower_first": "lower", "ambiguous": "ambiguous"}.get(st)
            t = u["refined_index"] if ev is not None and u["refined_index"] is not None else 10
            cu.append({"time": float(t), "event": ev, "censoring": fp.OBSERVED})
        elif c == fp.ADMINISTRATIVE_PENDING:
            cu.append({"time": float(u["max_index"]), "event": None, "censoring": c})
        else:
            cu.append({"time": 0.0, "event": None, "censoring": c})
    return fp.cumulative_incidence(
        cu, [0, 1, 3, 5, 10],
        censoring_assumption={"noninformative": True,
                              "basis": "10d-pending units are censored by the vintage calendar cutoff"})


def run_primary(episodes: dict, rows: list[dict]) -> tuple[dict, list[dict]]:
    built = build_units(episodes, rows, "10d", ("eod", "1d", "3d", "5d"))
    units = built["units"]
    dates = sorted({u["date"] for u in units if u["date"]})
    train_dates, test_dates = dates[:N_TRAIN_DATES], dates[N_TRAIN_DATES:]
    widths = [(u["rep_row"]["high"] - u["rep_row"]["low"]) / (2 * u["rep_row"]["entry_price"])
              for u in units if u["censoring"] == fp.OBSERVED and u["date"] in set(train_dates)]
    if not widths:
        return {"verdict": "INSUFFICIENT_DATA", "reason": "no observed TRAIN units"}, units
    b = float(statistics.median(widths))
    fb = assign_states(units, rows, "10d", ("eod", "1d", "3d", "5d"), b)
    primary = summarize(units, "10d", train_dates, test_dates, b, fb, with_boot=True)
    primary["train_dates"] = train_dates
    primary["test_dates"] = test_dates
    primary["n_train_widths"] = len(widths)
    primary["ticker_fallbacks"] = built["fallback_ticker"]
    primary["mixed_class_paths"] = built["mixed_class_paths"]
    primary["undated_units"] = sum(1 for u in units if not u["date"])
    pdc = collections.defaultdict(collections.Counter)
    for u in units:
        pdc[str(u["date"])][u["censoring"]] += 1
    primary["per_date_classes_all"] = {d: dict(c) for d, c in sorted(pdc.items())}
    epc = collections.Counter()
    for u in units:
        epc[u["censoring"]] += u["n_episodes"]
    primary["episode_counts_by_path_class"] = dict(epc)
    primary["path_counts_by_class"] = dict(collections.Counter(u["censoring"] for u in units))
    test_units = [u for u in units if u["date"] in set(test_dates)]
    primary["cumulative_incidence_test"] = incidence(test_units)

    # Secondary: 5d horizon with the same b (never verdict-bearing)
    built5 = build_units(episodes, rows, "5d", ("eod", "1d", "3d"))
    fb5 = assign_states(built5["units"], rows, "5d", ("eod", "1d", "3d"), b)
    sec5 = summarize(built5["units"], "5d", train_dates, test_dates, b, fb5, with_boot=False)
    sec5["bootstrap_E"] = fp.circular_block_bootstrap(
        [[u for u in built5["units"] if u["date"] == d] for d in test_dates
         if any(u["censoring"] == fp.OBSERVED for u in built5["units"] if u["date"] == d)],
        ratio_stat(1), block_len=BLOCK_LEN, n_boot=N_BOOT, seed=SEED)
    primary["secondary_5d"] = sec5

    # Verdict (PREREG section 15)
    t = primary["test"]
    hn = primary["honest_n"]
    boot = primary["bootstrap"]["E"]
    loto = primary["leave_one_ticker_out"]["min_E"]
    if t["n_observed"] < MIN_TEST_UNITS or hn["test_dates_with_observed"] < MIN_TEST_DATES:
        verdict, why = "INSUFFICIENT_DATA", "TEST observed units < 200 or TEST dates < 5"
    elif boot.get("status") == "ok" and boot["lo"] >= EFFECT_BAR and loto is not None and loto >= LOTO_BAR:
        verdict, why = "KEEP", "95% lower bound of E >= 1.0pp and LOTO min E >= 0.5pp"
    else:
        verdict, why = "REJECT", "95% lower bound of E < 1.0pp or LOTO min E < 0.5pp"
    full = primary["bounds_refined_proposed"]
    w_obs = full["observed"]["upper_first"][1] - full["observed"]["upper_first"][0]
    w_full = full["full_denominator"]["upper_first"][1] - full["full_denominator"]["upper_first"][0]
    primary["falsifier_b"] = {"observed_width": w_obs, "full_denominator_width": w_full,
                              "excess": w_full - w_obs, "attrition_dominates": (w_full - w_obs) > ATTRITION_FLAG_PP}
    primary["verdict"] = verdict
    primary["verdict_reason"] = why
    return primary, units


# --------------------------------------------------------------------------- io


def write_json(name: str, obj: dict) -> str:
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return path


def write_attrition_csv(units: list[dict], test_dates: list[str]) -> str:
    path = os.path.join(RESULTS, "attrition.csv")
    tset = set(test_dates)
    # Units with no entry date sit in neither split (PREREG_AMENDMENT_ADDENDUM_B.md B1);
    # they are labelled UNDATED, never folded into TRAIN.
    cnt = collections.Counter(
        (("UNDATED" if not u["date"] else "TEST" if u["date"] in tset else "TRAIN"), u["censoring"],
         u.get("reason") or "")
        for u in units)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["split", "censoring_class", "reason", "n_paths"])
        for (s, c, r), n in sorted(cnt.items()):
            w.writerow([s, c, r, n])
    return path


def append_runs(cmd: str, code: int, inputs: dict, outputs: dict, note: str, utc: str | None) -> None:
    with open(RUNS, "a", encoding="utf-8") as fh:
        fh.write("---\n")
        fh.write(f"utc: {utc or 'not-supplied'}\n")
        fh.write(f"command: {cmd}\n")
        fh.write(f"exit_code: {code}\n")
        fh.write(f"note: {note}\n")
        fh.write("inputs_sha256:\n")
        for k, v in inputs.items():
            fh.write(f"  {k}: {v}\n")
        fh.write("outputs_sha256:\n")
        for k, v in outputs.items():
            fh.write(f"  {k}: {v}\n")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("baseline", "primary"), required=True)
    ap.add_argument("--utc", default=None, help="caller-supplied UTC stamp for RUNS.log (no clock read)")
    ap.add_argument("--purpose", default=None,
                    help="declared purpose recorded in RUNS.log (e.g. a reproducibility re-run)")
    args = ap.parse_args(argv)
    cmd = "python3.12 evaluate.py " + " ".join(argv)
    inputs: dict = {}
    outputs: dict = {}
    code = 1
    note = ""
    try:
        inputs["PREREG.md"] = sha256_file(PREREG)
        inputs["evaluate.py"] = sha256_file(os.path.abspath(__file__))
        inputs["engine/outcome_first_passage_ambiguity.py"] = sha256_file(MODULE)
        if os.path.exists(AMEND):
            inputs["PREREG_AMENDMENT.md"] = sha256_file(AMEND)
        for extra in ("PREREG_AMENDMENT_ADDENDUM_B.md", "PREREG_AMENDMENT_ADDENDUM_C.md"):
            if os.path.exists(os.path.join(HERE, extra)):
                inputs[extra] = sha256_file(os.path.join(HERE, extra))
        fz = frozen_hash()
        if fz is None or fz != inputs["PREREG.md"]:
            note = f"REFUSED: PREREG.md sha256 {inputs['PREREG.md']} != FREEZE.log {fz}"
            print(note, file=sys.stderr)
            code = 2
            return code
        blobs = {}
        try:
            for rel, nb, dg in PINS:
                blobs[rel] = read_pinned(rel, nb, dg)
                inputs["data/" + rel] = f"{dg} (prefix {nb} bytes)"
        except PinFailure as exc:
            note = f"INSUFFICIENT_DATA: {exc}"
            outputs["results/primary.json" if args.mode == "primary" else "results/baseline.json"] = sha256_file(
                write_json(f"{args.mode}.json", {"verdict": "INSUFFICIENT_DATA", "missing_input": str(exc)}))
            code = 3
            return code
        episodes = load_episodes(blobs.pop("options_signal_episode/episodes.jsonl"))
        checkpoint = json.loads(blobs.pop("options_signal_episode/checkpoint.json"))
        rows = load_rows([blobs[k] for k in sorted(blobs)])
        blobs.clear()
        if args.mode == "baseline":
            res = run_baseline(episodes, rows, checkpoint)
            outputs["results/baseline.json"] = sha256_file(write_json("baseline.json", res))
            note = "baseline reproduced"
        else:
            res, units = run_primary(episodes, rows)
            outputs["results/primary.json"] = sha256_file(write_json("primary.json", res))
            if res.get("test_dates") is not None:
                outputs["results/attrition.csv"] = sha256_file(write_attrition_csv(units, res["test_dates"]))
            note = f"verdict={res.get('verdict')}"
            if args.purpose:
                note += f"; purpose={args.purpose}"
        print(note)
        code = 0
        return code
    except Exception:
        note = "CRASH: " + traceback.format_exc().strip().splitlines()[-1]
        traceback.print_exc()
        code = 1
        return code
    finally:
        append_runs(cmd, code, inputs, outputs, note, args.utc)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
