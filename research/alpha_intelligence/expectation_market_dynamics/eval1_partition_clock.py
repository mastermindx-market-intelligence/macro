#!/usr/bin/env python3
"""EVAL-1 partition clock receipt builder (ITP A9). Outcome-free; read-only at one git rev."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import math
import sys
from collections import Counter
from datetime import datetime, time
from datetime import date as date_cls
from pathlib import Path
from typing import Any

import pandas as pd

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
_root_s = str(ROOT)
if _root_s not in sys.path:
    sys.path.insert(0, _root_s)

import engine.k3e_eval_admission as k3e_eval_admission
import engine.k3e_eval1_forward as k3e_eval1_forward
import lib.nyse_calendar as nyse_calendar

if k3e_eval_admission.is_session is not nyse_calendar.is_session:
    raise RuntimeError("admission calendar must match lib.nyse_calendar.is_session")

_spec = importlib.util.spec_from_file_location("r4_v2_admission", HERE / "r4_v2_admission.py")
if "r4_v2_admission" in sys.modules:
    r4 = sys.modules["r4_v2_admission"]
else:
    r4 = importlib.util.module_from_spec(_spec)
    sys.modules["r4_v2_admission"] = r4
    assert _spec.loader is not None
    _spec.loader.exec_module(r4)

SCHEMA = "itp.eval1_partition_clock.v1"
REGISTRATION_ID = "K3E-EVAL-1-V1"
USED = ("observations", "attempts", "security_master", "vendor_aliases")
FLOOR = k3e_eval1_forward.EPISODE_FLOOR
PURGE = k3e_eval1_forward.PURGE_SESSIONS
assert FLOOR == 100 and PURGE == 63 and r4.QUIET_GAP == 20

VERDICTS = (
    "EVAL1_NOT_ADMITTED",
    "F_DEV_OPEN",
    "PURGE_1",
    "F_VAL_OPEN",
    "PURGE_2",
    "F_HOLD_OPEN",
    "PROSPECTIVE_SHADOW",
)
LABELS = {
    "financial_influence": False,
    "k3e_admissible": False,
    "promotion_eligible": False,
    "promotion_bearing": False,
    "score": None,
    "rank": None,
    "issuer_clock": "REPO_HISTORY_AVAILABILITY",
}
for _k, _v in LABELS.items():
    assert r4.LABELS[_k] == _v

CUTOFF_RULE = (
    "clk = max(system_observed_at, provider_observed_at); cutoff session = first canonical "
    "session whose 16:00 ET close is at or after clk (searchsorted side=left)"
)
ALIAS_RULE = (
    "yahoo; ingested_at <= min(capture, cutoff); valid_from <= capture date < valid_to; "
    "security at capture == security at cutoff"
)
ISSUER_RULE = "known-version clock: newest security_master version with committer time <= cutoff - 24h"
PRIMARY_RULE = (
    "per issuer, variant-S start sessions at most 20 sessions apart chain into one cluster "
    "anchored at its earliest start session; a cluster counts in a partition when its anchor "
    "is at or after the partition start and at or before the close"
)
SECONDARY_RULE = (
    "distinct engine.k3e_eval1_forward.episode_id(issuer, metric, kind:period_end, start session) "
    "over eligible variant-S starts inside the partition window; descriptive only, never closes a partition"
)

_BASE_GAPS = (
    "EARLY_CLOSES_NOT_MODELED_BY_CANONICAL_CALENDAR",
    "PERIOD_KEY_FORM_NOT_CANONICAL_ON_MAIN",
    "ADMISSION_REQUIRES_ORIGIN_MAIN_FRESHNESS_NETWORK",
)


def _gaps(shallow: bool) -> list[str]:
    out = list(_BASE_GAPS)
    if shallow:
        out.append("CLONE_IS_SHALLOW")
    return sorted(out)


def _vc(s: pd.Series) -> list[list[Any]]:
    return sorted(
        [[str(k), int(v)] for k, v in s.value_counts(dropna=False).sort_index().items()],
        key=lambda x: x[0],
    )


def _to_py(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, bool)):
        return obj
    if isinstance(obj, (int,)):
        return int(obj)
    if isinstance(obj, float):
        if math.isfinite(obj):
            raise ValueError(f"unexpected float in doc: {obj}")
        return obj
    if hasattr(obj, "item"):
        return _to_py(obj.item())
    if isinstance(obj, dict):
        return {k: _to_py(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_py(x) for x in obj]
    raise ValueError(f"cannot canonicalize type {type(obj)}")


def canonical(doc: dict) -> str:
    cleaned = _to_py(doc)
    return json.dumps(cleaned, sort_keys=True, indent=1, ensure_ascii=True) + "\n"


def _rev_commit_time_utc(repo: Path, rev_full: str) -> str:
    raw = r4._git(repo, "show", "-s", "--format=%cI", rev_full).decode().strip()
    ts = pd.Timestamp(raw).tz_convert("UTC")
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _refusal_doc(
    rev_full: str,
    rev_commit_time: str,
    refusal_codes: list[str],
    source_main_commit: str | None,
) -> dict:
    return {
        "schema": SCHEMA,
        "registration_id": REGISTRATION_ID,
        "verdict": "EVAL1_NOT_ADMITTED",
        "verdict_enum": list(VERDICTS),
        "rev": rev_full,
        "rev_commit_time": rev_commit_time,
        "labels": dict(LABELS),
        "admission": {
            "admitted": False,
            "refusal_codes": sorted(refusal_codes),
            "source_main_commit": source_main_commit,
        },
        "gaps": _gaps(False),
    }


def _admission_gate(repo: Path, rev_full: str, admission: dict | None) -> tuple[dict | None, dict | None]:
    if admission is None:
        admission = k3e_eval_admission.inspect_eval1_admission(repo)
    codes: list[str] = []
    if admission.get("admitted") is not True:
        reasons = admission.get("reasons") or []
        codes = sorted(reasons) if reasons else ["ADMISSION_REFUSED_WITHOUT_CODE"]
        return None, codes
    if admission.get("source_main_commit") != rev_full:
        return None, ["REV_NOT_ADMISSION_SOURCE_MAIN"]
    boundary = date_cls.fromisoformat(admission["boundary"])
    if not nyse_calendar.is_session(boundary):
        return None, ["ADMISSION_BOUNDARY_NOT_A_SESSION"]
    return admission, []


def build(repo: Path | str, rev: str, admission: dict | None = None) -> dict:
    repo = Path(repo).resolve()
    rev_full = r4._git(repo, "rev-parse", "--verify", rev + "^0").decode().strip()
    rev_commit_time = _rev_commit_time_utc(repo, rev_full)

    admission_raw = admission
    admission_in, refusal_codes = _admission_gate(repo, rev_full, admission)
    if admission_in is None:
        src = None
        if admission_raw is not None:
            src = admission_raw.get("source_main_commit")
        return _refusal_doc(rev_full, rev_commit_time, refusal_codes, src)

    admission = admission_in
    boundary = date_cls.fromisoformat(admission["boundary"])
    boundary_at = datetime.combine(
        boundary, k3e_eval_admission._NYSE_OPEN, tzinfo=nyse_calendar.ET
    ).astimezone(pd.Timestamp.now("UTC").tzinfo)
    boundary_at = pd.Timestamp(boundary_at).tz_convert("UTC")

    shallow = r4._git(repo, "rev-parse", "--is-shallow-repository").decode().strip() == "true"
    source = {}
    for k in USED:
        blob = r4._blob_id(repo, rev_full, r4.PATHS[k])
        source[k] = {"path": r4.PATHS[k], "blob": blob}

    o_raw = pd.read_parquet(io.BytesIO(r4._blob(repo, source["observations"]["blob"])))
    att = pd.read_parquet(io.BytesIO(r4._blob(repo, source["attempts"]["blob"])))
    observations_rows = int(len(o_raw))
    o = o_raw.copy()
    o["clk"] = pd.concat([r4._ts(o.system_observed_at), r4._ts(o.provider_observed_at)], axis=1).max(
        axis=1
    )
    rows_without_clock = int(o.clk.isna().sum())
    o = o[o.clk.notna()].copy()

    if len(o):
        clk_et = o.clk.dt.tz_convert(nyse_calendar.ET)
        cal_start = clk_et.min().date() - pd.Timedelta(days=7)
        cal_end = max(clk_et.max().date(), boundary) + pd.Timedelta(days=400)
    else:
        cal_start = boundary
        cal_end = boundary + pd.Timedelta(days=400)

    def _load_cal(end_d: date_cls) -> tuple[list, pd.DatetimeIndex]:
        cal_l = nyse_calendar.sessions_between(cal_start, end_d)
        closes_l = pd.DatetimeIndex(
            [datetime.combine(d, time(16, 0), tzinfo=nyse_calendar.ET) for d in cal_l]
        )
        return cal_l, closes_l

    cal, closes = _load_cal(cal_end)
    b_pos = cal.index(boundary)

    def ensure_pos(pos: int) -> None:
        nonlocal cal, closes, cal_end
        while pos >= len(cal):
            cal_end = cal_end + pd.Timedelta(days=400)
            cal, closes = _load_cal(cal_end)

    spos = closes.searchsorted(pd.DatetimeIndex(o.clk), side="left")
    if len(spos) and spos.max() >= len(cal):
        ensure_pos(int(spos.max()))
        spos = closes.searchsorted(pd.DatetimeIndex(o.clk), side="left")
    if len(spos) and spos.max() >= len(cal):
        raise RuntimeError("calendar still too short after extension")
    o["spos"] = spos
    o["cutoff_ts"] = closes[spos]
    h = int(spos.max()) if len(o) else None

    va = pd.read_parquet(io.BytesIO(r4._blob(repo, source["vendor_aliases"]["blob"])))
    alias = r4.AliasRule(va)
    kj = ["ticker_compat", "clk", "cutoff_ts"]
    tick = o[kj].drop_duplicates().sort_values(kj, kind="mergesort")
    res = [alias.security(t, c, k) for t, c, k in zip(tick.ticker_compat, tick.clk, tick.cutoff_ts)]
    tick = tick.assign(security_id=[a for a, _ in res], alias_reason=[b for _, b in res])
    o = o.join(tick.set_index(kj), on=kj)

    clock = r4.KnownVersionClock(repo, rev_full)
    key = o.loc[o.security_id.notna(), ["security_id", "cutoff_ts"]].drop_duplicates()
    key = key.sort_values(["security_id", "cutoff_ts"], kind="mergesort")
    vals = [clock.issuer_at(s, c) for s, c in zip(key.security_id, key.cutoff_ts)]
    key = key.assign(iss=[a for a, _, _ in vals], issuer_reason=[b for _, b, _ in vals])
    o = o.join(key.set_index(["security_id", "cutoff_ts"]), on=["security_id", "cutoff_ts"])
    reason = o.alias_reason.where(o.alias_reason.notna(), o.issuer_reason)

    ok = o[o.iss.notna()].copy()
    ev, ep_stats = r4.start_events(ok)
    for col in ("direction", "value", "prev"):
        if col in ev.columns:
            ev = ev.drop(columns=[col])
    s_starts = ev[ev.start_S].copy()

    pre_rows = ok[
        (ok.observation_type == "average")
        & ok.value.notna()
        & ok.period_end.notna()
    ].copy()
    pre_rows["kind"] = pre_rows.horizon_label_raw.str[-1]
    pre_set = set(
        zip(
            pre_rows.loc[(pre_rows.spos == b_pos) & (pre_rows.clk < boundary_at), "iss"],
            pre_rows.loc[(pre_rows.spos == b_pos) & (pre_rows.clk < boundary_at), "metric"],
            pre_rows.loc[(pre_rows.spos == b_pos) & (pre_rows.clk < boundary_at), "kind"],
            pre_rows.loc[(pre_rows.spos == b_pos) & (pre_rows.clk < boundary_at), "period_end"],
        )
    )

    start_excl: Counter[str] = Counter()
    eligible_rows = []
    for _, row in s_starts.iterrows():
        sk = (row.iss, row.metric, row.kind, row.period_end)
        if row.spos < b_pos:
            start_excl["START_BEFORE_PARTITION"] += 1
            continue
        if row.spos == b_pos and sk in pre_set:
            start_excl["START_OBSERVED_BEFORE_BOUNDARY"] += 1
            continue
        eligible_rows.append(row)
    eligible = pd.DataFrame(eligible_rows) if eligible_rows else s_starts.iloc[0:0]

    c_in = s_starts[["iss", "spos"]].copy()
    c_in["direction"] = "NEUTRALIZED"
    c_in["ticker_compat"] = "NEUTRALIZED"
    cl_raw = r4.clusters(c_in)
    clusters_all = [{"iss": t[0], "anchor": int(t[1]), "members": int(t[2])} for t in cl_raw]

    s_at_b = s_starts[s_starts.spos == b_pos]
    pre_by_iss: dict[Any, set] = {}
    for _, row in s_starts.iterrows():
        if row.spos == b_pos:
            sk = (row.iss, row.metric, row.kind, row.period_end)
            if sk in pre_set:
                pre_by_iss.setdefault(row.iss, set()).add("START_OBSERVED_BEFORE_BOUNDARY")

    cluster_excl: Counter[str] = Counter()
    candidates = []
    for c in clusters_all:
        anchor = c["anchor"]
        iss = c["iss"]
        if anchor < b_pos:
            cluster_excl["CLUSTER_ANCHORED_BEFORE_PARTITION"] += 1
            continue
        if anchor == b_pos:
            iss_starts = s_starts[(s_starts.iss == iss) & (s_starts.spos == b_pos)]
            if len(iss_starts) and all(
                (r.iss, r.metric, r.kind, r.period_end) in pre_set for _, r in iss_starts.iterrows()
            ):
                cluster_excl["CLUSTER_ANCHOR_OBSERVED_BEFORE_BOUNDARY"] += 1
                continue
        candidates.append(c)
    candidates.sort(key=lambda x: (x["anchor"], x["iss"]))

    def count_primary(start_pos: int, close_pos: int | None) -> int:
        if close_pos is None:
            return sum(1 for c in candidates if c["anchor"] >= start_pos)
        return sum(1 for c in candidates if start_pos <= c["anchor"] <= close_pos)

    def secondary_n_for(start_pos: int | None, close_pos: int | None, part_start: int) -> int:
        if start_pos is None or h is None or h < part_start:
            return 0
        hi = close_pos if close_pos is not None else h
        if hi < part_start:
            return 0
        ids = set()
        for _, row in eligible.iterrows():
            if row.spos < part_start or row.spos > hi:
                continue
            sess = cal[row.spos].isoformat()
            period = str(row.kind) + ":" + str(row.period_end)
            eid = k3e_eval1_forward.episode_id(str(row.iss), str(row.metric), period, sess)
            ids.add(eid)
        return len(ids)

    partitions: dict[str, Any] = {}
    purge1_close_pos: int | None = None
    purge2_close_pos: int | None = None
    f_hold_close_pos: int | None = None

    def iso_pos(p: int | None) -> str | None:
        if p is None:
            return None
        return cal[p].isoformat()

    def walk_counting(
        name: str, start_pos: int, blocked: bool, *, always_open: bool = False
    ) -> tuple[int | None, int, str, str, int]:
        if blocked:
            return None, 0, "NOT_STARTED", "NOT_STARTED", 0
        if not always_open and (h is None or h < start_pos):
            return None, 0, "NOT_STARTED", "NOT_STARTED", 0
        elig = [c for c in candidates if c["anchor"] >= start_pos]
        if len(elig) >= FLOOR:
            close_pos = elig[FLOOR - 1]["anchor"]
            ensure_pos(close_pos)
            primary = count_primary(start_pos, close_pos)
            return close_pos, primary, "CLOSED", "FLOOR_MET", len(elig)
        primary = len(elig) if h is not None and h >= start_pos else 0
        return None, primary, "OPEN", "INSUFFICIENT_EPISODE_N", len(elig)

    dev_close, dev_primary, dev_state, dev_status, _ = walk_counting(
        "F_DEV", b_pos, False, always_open=True
    )
    if dev_close is not None:
        ensure_pos(dev_close + PURGE + 1)
    dev_sec = secondary_n_for(b_pos, dev_close, b_pos)

    partitions["F_DEV"] = {
        "state": dev_state if dev_state != "NOT_STARTED" else "OPEN",
        "status": dev_status if dev_status != "NOT_STARTED" else "INSUFFICIENT_EPISODE_N",
        "floor": FLOOR,
        "start_session": iso_pos(b_pos),
        "close_session": iso_pos(dev_close),
        "primary_n": dev_primary if dev_state != "NOT_STARTED" else (dev_primary if dev_state == "OPEN" else 0),
        "primary_n_of_floor": str(dev_primary if dev_state != "NOT_STARTED" else 0) + "/" + str(FLOOR),
        "secondary_n": dev_sec,
    }
    if dev_state == "OPEN":
        partitions["F_DEV"]["state"] = "OPEN"
        partitions["F_DEV"]["status"] = "INSUFFICIENT_EPISODE_N"
        partitions["F_DEV"]["primary_n"] = dev_primary
        partitions["F_DEV"]["primary_n_of_floor"] = f"{dev_primary}/{FLOOR}"

    later_blocked = dev_state != "CLOSED"

    purge1_start = purge1_end = None
    purge1_state = "NOT_STARTED"
    val_start_pos: int | None = None
    if dev_close is not None:
        purge1_start = dev_close + 1
        purge1_end = dev_close + PURGE
        ensure_pos(purge1_end)
        purge1_state = "ELAPSED" if h is not None and h >= dev_close + PURGE + 1 else "OPEN"
        val_start_pos = dev_close + PURGE + 1
        purge1_close_pos = purge1_end

    partitions["PURGE_1"] = {
        "state": purge1_state,
        "sessions": PURGE,
        "start_session": iso_pos(purge1_start),
        "end_session": iso_pos(purge1_end),
    }

    val_blocked = later_blocked or purge1_state == "OPEN" or purge1_state == "NOT_STARTED"
    if val_start_pos is not None and purge1_state == "ELAPSED":
        val_blocked = False
    if dev_close is None:
        val_blocked = True
        val_start_pos = None

    val_close, val_primary, val_state, val_status, _ = (
        walk_counting("F_VAL", val_start_pos or 0, val_blocked or val_start_pos is None)
        if val_start_pos is not None and not val_blocked
        else (None, 0, "NOT_STARTED", "NOT_STARTED", 0)
    )
    if val_start_pos is not None and val_blocked and dev_close is not None:
        val_state, val_status = "NOT_STARTED", "NOT_STARTED"
        val_primary = 0
        val_close = None

    partitions["F_VAL"] = {
        "state": val_state,
        "status": val_status,
        "floor": FLOOR,
        "start_session": iso_pos(val_start_pos) if dev_close is not None else None,
        "close_session": iso_pos(val_close),
        "primary_n": val_primary,
        "primary_n_of_floor": f"{val_primary}/{FLOOR}",
        "secondary_n": secondary_n_for(val_start_pos, val_close, val_start_pos or 0)
        if val_state not in ("NOT_STARTED",)
        else 0,
    }

    purge2_start = purge2_end = None
    purge2_state = "NOT_STARTED"
    hold_start_pos: int | None = None
    val_later_blocked = val_state != "CLOSED"
    if val_close is not None:
        purge2_start = val_close + 1
        purge2_end = val_close + PURGE
        ensure_pos(purge2_end)
        purge2_state = "ELAPSED" if h is not None and h >= val_close + PURGE + 1 else "OPEN"
        hold_start_pos = val_close + PURGE + 1
        purge2_close_pos = purge2_end

    partitions["PURGE_2"] = {
        "state": purge2_state if val_close is not None else "NOT_STARTED",
        "sessions": PURGE,
        "start_session": iso_pos(purge2_start),
        "end_session": iso_pos(purge2_end),
    }

    hold_blocked = val_later_blocked or purge2_state != "ELAPSED"
    if hold_start_pos is None:
        hold_blocked = True
    hold_close, hold_primary, hold_state, hold_status, _ = (
        walk_counting("F_HOLD", hold_start_pos or 0, hold_blocked)
        if hold_start_pos is not None and not hold_blocked
        else (None, 0, "NOT_STARTED", "NOT_STARTED", 0)
    )
    if hold_start_pos is not None and hold_blocked:
        hold_state, hold_status = "NOT_STARTED", "NOT_STARTED"
        hold_primary = 0
        hold_close = None
    if hold_close is not None:
        f_hold_close_pos = hold_close

    partitions["F_HOLD"] = {
        "state": hold_state,
        "status": hold_status,
        "floor": FLOOR,
        "start_session": iso_pos(hold_start_pos),
        "close_session": iso_pos(hold_close),
        "primary_n": hold_primary,
        "primary_n_of_floor": f"{hold_primary}/{FLOOR}",
        "secondary_n": secondary_n_for(hold_start_pos, hold_close, hold_start_pos or 0)
        if hold_state not in ("NOT_STARTED",)
        else 0,
    }

    candidate_keys = {(c["iss"], c["anchor"]) for c in candidates}
    for c in clusters_all:
        a = c["anchor"]
        key = (c["iss"], a)
        if key not in candidate_keys:
            continue
        if purge1_start is not None and purge1_end is not None and purge1_start <= a <= purge1_end:
            cluster_excl["CLUSTER_ANCHORED_IN_PURGE_1"] += 1
            candidate_keys.discard(key)
        elif purge2_start is not None and purge2_end is not None and purge2_start <= a <= purge2_end:
            cluster_excl["CLUSTER_ANCHORED_IN_PURGE_2"] += 1
            candidate_keys.discard(key)
        elif f_hold_close_pos is not None and a > f_hold_close_pos:
            cluster_excl["CLUSTER_ANCHORED_AFTER_F_HOLD_CLOSE"] += 1
            candidate_keys.discard(key)

    clusters_total = len(clusters_all)
    cluster_excl_list = sorted([[k, int(v)] for k, v in cluster_excl.items() if v])
    assert sum(v for _, v in cluster_excl_list) + len(candidate_keys) == clusters_total

    verdict = "PROSPECTIVE_SHADOW"
    if partitions["F_HOLD"]["state"] == "CLOSED":
        verdict = "PROSPECTIVE_SHADOW"
    elif partitions["F_HOLD"]["state"] == "OPEN":
        verdict = "F_HOLD_OPEN"
    elif partitions["PURGE_2"]["state"] == "OPEN":
        verdict = "PURGE_2"
    elif partitions["F_VAL"]["state"] == "OPEN":
        verdict = "F_VAL_OPEN"
    elif partitions["PURGE_1"]["state"] == "OPEN":
        verdict = "PURGE_1"
    elif partitions["F_DEV"]["state"] == "OPEN":
        verdict = "F_DEV_OPEN"

    prospective = iso_pos(f_hold_close_pos) if f_hold_close_pos is not None else None

    rows_cross = [
        (int(c["anchor"]), str(c["iss"]) + "|" + str(int(c["anchor"])), int(c["anchor"]))
        for c in candidates
    ]
    res = k3e_eval1_forward.assign_partitions(rows_cross, b_pos)
    disagree = False
    if res["closes"]["F_DEV"] != dev_close or res["closes"]["F_VAL"] != val_close:
        disagree = True
    if res["closes"]["F_HOLD"] != hold_close:
        disagree = True
    if dev_close is not None and res["episode_counts"]["F_DEV"] != partitions["F_DEV"]["primary_n"]:
        disagree = True
    if val_close is not None and res["episode_counts"]["F_VAL"] != partitions["F_VAL"]["primary_n"]:
        disagree = True
    if hold_close is not None and res["episode_counts"]["F_HOLD"] != partitions["F_HOLD"]["primary_n"]:
        disagree = True
    if res["starts"]["F_DEV"] != b_pos:
        disagree = True
    if res["starts"].get("F_VAL") is not None and res["starts"]["F_VAL"] != val_start_pos:
        disagree = True
    if res["starts"].get("F_HOLD") is not None and res["starts"]["F_HOLD"] != hold_start_pos:
        disagree = True
    if disagree:
        raise RuntimeError("ASSIGN_PARTITIONS_DISAGREES")
    cross_check = "engine.k3e_eval1_forward.assign_partitions AGREES"

    mf = admission.get("main_freshness", {})
    main_freshness_proven = bool(mf.get("proven")) if isinstance(mf, dict) else False

    doc = {
        "schema": SCHEMA,
        "registration_id": REGISTRATION_ID,
        "verdict": verdict,
        "verdict_enum": list(VERDICTS),
        "rev": rev_full,
        "rev_commit_time": rev_commit_time,
        "labels": dict(LABELS),
        "admission": {
            "admitted": True,
            "refusal_codes": [],
            "source_main_commit": admission["source_main_commit"],
            "registration_digest": admission["registration_digest"],
            "introduction_commit": admission["introduction_commit"],
            "boundary_session": boundary.isoformat(),
            "boundary_at": boundary_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "main_freshness_proven": main_freshness_proven,
        },
        "source": {
            "observations": source["observations"],
            "attempts": source["attempts"],
            "security_master": source["security_master"],
            "vendor_aliases": source["vendor_aliases"],
        },
        "calendar": {
            "source": "lib.nyse_calendar",
            "close_time_et": "16:00",
            "early_close_model": "NOT_MODELED_BY_CANONICAL_SOURCE",
            "first_session": cal[0].isoformat(),
            "last_session": cal[-1].isoformat(),
            "cutoff_rule": CUTOFF_RULE,
        },
        "corpus": {
            "observations_rows": observations_rows,
            "attempts_rows": int(len(att)),
            "rows_without_clock": rows_without_clock,
            "rows_pre_boundary_history": int((o.spos < b_pos).sum()),
            "rows_post_boundary": int((o.spos >= b_pos).sum()),
            "data_horizon_session": cal[h].isoformat() if h is not None else None,
            "max_system_observed_at": (
                o.system_observed_at.max() if len(o) else None
            ),
            "max_provider_observed_at": (
                o.provider_observed_at.max() if len(o) else None
            ),
            "max_attempt_completed_at": (
                str(r4._ts(att.completed_at).max().strftime("%Y-%m-%dT%H:%M:%SZ"))
                if len(att) and att.completed_at.notna().any()
                else None
            ),
        },
        "identity": {
            "alias_rule": ALIAS_RULE,
            "alias_dec": "DEC:ITP-K3E-ALIAS-CLOCK-BOUNDED-IDENTITY-2026-10-07",
            "issuer_rule": ISSUER_RULE,
            "issuer_dec": "DEC:ITP-R4-ISSUER-AXIS-AS-KNOWN-VERSION-CLOCK-2026-10-07",
            "known_version_guard_hours": 24,
            "clone_is_shallow": shallow,
            "security_master_versions_visible": len(clock.versions),
            "rows_issuer_formed": int(ok.iss.notna().sum()),
            "rows_post_boundary_issuer_formed": int((ok.spos >= b_pos).sum()),
            "rows_without_issuer_by_reason": _vc(reason[o.iss.isna()]),
            "post_boundary_rows_without_issuer_by_reason": _vc(
                reason[(o.iss.isna()) & (o.spos >= b_pos)]
            ),
        },
        "episode_starts": {
            "variant": "S",
            "quiet_gap_sessions": r4.QUIET_GAP,
            "series": ep_stats["series"],
            "series_session_points": ep_stats["series_session_points"],
            "nonzero_same_period_changes": ep_stats["nonzero_same_period_changes"],
            "variant_s_starts_total": int(len(s_starts)),
            "starts_eligible": int(len(eligible)),
            "starts_excluded_by_reason": sorted([[k, int(v)] for k, v in start_excl.items()]),
        },
        "count_unit": {
            "primary": "ISSUER_OVERLAP_CLUSTER",
            "primary_rule": PRIMARY_RULE,
            "secondary": "DISTINCT_EPISODE_ID",
            "secondary_rule": SECONDARY_RULE,
            "floor": FLOOR,
            "purge_sessions": PURGE,
            "clusters_total": clusters_total,
            "clusters_excluded_by_reason": cluster_excl_list,
        },
        "partitions": partitions,
        "prospective_shadow_after_session": prospective,
        "cross_check": cross_check,
        "gaps": _gaps(shallow),
    }
    return doc


def render_md(doc: dict, digest: str) -> str:
    parts = doc["partitions"]
    lines = [
        f"sha256: {digest}",
        f"rev: {doc['rev']}",
        f"verdict: {doc['verdict']}",
        f"boundary_session: {doc['admission']['boundary_session']}",
        f"F_DEV: {parts['F_DEV']['primary_n_of_floor']} secondary_n={parts['F_DEV']['secondary_n']} "
        f"close={parts['F_DEV']['close_session'] or 'open'}",
        f"PURGE_1: {parts['PURGE_1']['start_session']} .. {parts['PURGE_1']['end_session']}",
        f"F_VAL start: {parts['F_VAL']['start_session']}",
        f"gaps: {', '.join(doc['gaps'])}",
        "No outcome field is read or emitted; financial_influence, k3e_admissible and promotion_eligible are false.",
    ]
    return "\n".join(lines) + "\n"


def write(doc: dict, out_dir: Path | str) -> tuple[Path, Path]:
    if doc.get("verdict") == "EVAL1_NOT_ADMITTED":
        raise ValueError("refusal documents are not written to disk")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ny_day = pd.Timestamp(doc["rev_commit_time"]).tz_convert("America/New_York").date().isoformat()
    js = canonical(doc).encode("utf-8")
    digest = hashlib.sha256(js).hexdigest()
    json_path = out_dir / f"EVAL1_PARTITION_CLOCK_{ny_day}.json"
    md_path = out_dir / f"EVAL1_PARTITION_CLOCK_{ny_day}.md"
    json_path.write_bytes(js)
    md_path.write_text(render_md(doc, digest), encoding="ascii")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="EVAL-1 partition clock receipt")
    p.add_argument("--repo", default=str(ROOT))
    p.add_argument("--rev", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    try:
        doc = build(args.repo, args.rev)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if doc.get("verdict") == "EVAL1_NOT_ADMITTED":
        detail = doc.get("admission", {})
        print(canonical(doc), end="")
        adm = k3e_eval_admission.inspect_eval1_admission(Path(args.repo))
        if adm.get("detail"):
            print(adm.get("detail"), file=sys.stderr)
        return 3
    try:
        jp, mp = write(doc, args.out)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(jp)
    print(mp)
    print(doc["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
