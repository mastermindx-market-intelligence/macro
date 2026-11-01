"""Entry Timing W2 — freeze inputs and the machine freeze (registration r8, §2–§7).

Reads DATES AND IDS ONLY: the registration's YAML block, the per-unit census dump, the SPY
session calendar (date index) and each exact pair's price-panel DATE INDEX (``columns=[]``).
No close, grade, outcome, excess or paired-race column is opened. Writes
``research/prophet_v4/entry_timing_w2/PREREG.json`` (the machine freeze mirroring §2–§7).

Freeze inputs produced here:
* T3 availability gate (§4): for each R exact pair, the panel index must hold every one of
  the ``T3_LOOKBACK_SESSIONS`` NYSE sessions ending at ``t_disc - 1`` (``session_missing``
  = a calendar session absent from the ticker's index); T3 joins the P Holm family only if
  >= 90% of exact pairs pass.
* R maturity session (§7): first session after max over R units and arms of t_exec + H,
  with t_exec(T0) = k_disc + 1, t_exec(T1) = k_cur + 1 (exact pairs), t_exec(T2) = k_disc + 3
  (observed), and the T3 bound t_disc + K + 1 (T3's own t_exec is not observable without a
  close read, so its latest admissible fill is used). Sessions after the calendar's last
  date are projected on the weekday calendar minus the declared NYSE holidays.
* Entitlement exclusion list (§2): pinned as supplied; none exists in the repository at the
  freeze, so the pinned list is empty and every later list applies from its own pin date.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd
import yaml

REG = Path("research/prophet_v4/ENTRY_TIMING_W2_DESIGN_REGISTRATION_2026-10-31.md")
UNITS = Path("research/prophet_v4/entry_timing_w2_units_2026-10-31.json")
CENSUS = Path("research/prophet_v4/entry_timing_w2_t1_census_2026-10-31.json")
OUT = Path("research/prophet_v4/entry_timing_w2/PREREG.json")
PANEL = "data/yahoo/{ticker}.parquet"
CAL = "data/yahoo/SPY.parquet"
# union_admission reads completed 3-session buckets and refuses fewer than 40 of them
# (engine/us_early_turn.py: ``len(tf_close) < 40`` -> None; MIN_BARS = 90 daily closes).
T3_LOOKBACK_SESSIONS = 120
T3_GATE_SHARE = 0.90
NYSE_HOLIDAYS_AHEAD = ["2026-11-26", "2026-12-25", "2027-01-01", "2027-01-18", "2027-02-15"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def yaml_block(text: str) -> dict:
    y = text[text.rfind("```yaml") + 7:]
    return yaml.safe_load(y[: y.find("```")])


def calendar() -> list[str]:
    idx = pd.to_datetime(pd.read_parquet(CAL, columns=[]).index)
    return sorted(set(idx.strftime("%Y-%m-%d")))


def extend(sessions: list[str], through: int) -> list[str]:
    """Project sessions past the calendar's last date (weekdays minus declared holidays)."""
    out = list(sessions)
    d = dt.date.fromisoformat(out[-1])
    while len(out) < through + 1:
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d.isoformat() not in NYSE_HOLIDAYS_AHEAD:
            out.append(d.isoformat())
    return out


def t3_gate(units: list[dict], sessions: list[str]) -> dict:
    si = {s: i for i, s in enumerate(sessions)}
    rows = []
    for u in units:
        if u["status"] != "IDENTIFIED_EXACT":
            continue
        end = si[u["t_disc"]] - 1
        need = sessions[end - T3_LOOKBACK_SESSIONS + 1: end + 1]
        p = Path(PANEL.format(ticker=u["ticker"]))
        if not p.exists():
            rows.append({"episode_id": u["episode_id"], "ticker": u["ticker"], "t_disc": u["t_disc"],
                         "panel": "absent", "missing_sessions": len(need), "pass": False})
            continue
        have = set(pd.to_datetime(pd.read_parquet(p, columns=[]).index).strftime("%Y-%m-%d"))
        missing = [d for d in need if d not in have]
        rows.append({"episode_id": u["episode_id"], "ticker": u["ticker"], "t_disc": u["t_disc"],
                     "panel": "present", "missing_sessions": len(missing), "first_missing": missing[:3],
                     "pass": not missing})
    n = len(rows)
    ok = sum(r["pass"] for r in rows)
    return {"rule": f"panel DATE INDEX holds every one of the {T3_LOOKBACK_SESSIONS} NYSE sessions ending at t_disc - 1 "
                    f"(3-session buckets x 40 = {T3_LOOKBACK_SESSIONS}; MIN_BARS 90 daily) for >= {T3_GATE_SHARE:.0%} of R exact pairs; "
                    "dates only, no close read",
            "exact_pairs": n, "pairs_passing": ok, "share": (ok / n) if n else None,
            "t3_in_p_family": bool(n and ok / n >= T3_GATE_SHARE), "pairs": rows}


def maturity(units: list[dict], sessions: list[str], K: int, H: int) -> dict:
    si = {s: i for i, s in enumerate(sessions)}
    latest = {"T0": -1, "T1": -1, "T2": -1, "T3_bound": -1}
    for u in units:
        if u["status"] in ("INCUMBENT_LED", "UNKNOWN_IDENTITY") or u["status"].startswith("UNKNOWN"):
            continue
        kd = si.get(u["k_disc"]) if u.get("k_disc") else None
        if kd is not None:
            latest["T0"] = max(latest["T0"], kd + 1)
            latest["T2"] = max(latest["T2"], kd + 3)
        if u["status"] == "IDENTIFIED_EXACT" and u.get("k_cur") in si:
            latest["T1"] = max(latest["T1"], si[u["k_cur"]] + 1)
        latest["T3_bound"] = max(latest["T3_bound"], si[u["t_disc"]] + K + 1)
    observed = max(latest["T0"], latest["T1"], latest["T2"])
    with_t3 = max(observed, latest["T3_bound"])
    ext = extend(sessions, with_t3 + H + 1)
    return {"rule": "first session after max over R units and arms of t_exec + H; t_exec(T0)=k_disc+1, t_exec(T1)=k_cur+1, "
                    "t_exec(T2)=k_disc+3 observed; T3 uses its latest admissible fill t_disc+K+1 (its own t_exec needs a close read)",
            "H_sessions": H, "K_sessions": K,
            "latest_t_exec": {k: (ext[v] if v >= 0 else None) for k, v in latest.items()},
            "maturity_session_observed_arms": ext[observed + H + 1],
            "maturity_session_with_t3_bound": ext[with_t3 + H + 1],
            "projected_sessions_after_calendar_end": {"calendar_last": sessions[-1], "holidays_declared": NYSE_HOLIDAYS_AHEAD}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--review-head", required=True, help="commit the independent review PASSED")
    ap.add_argument("--review-note", required=True)
    ap.add_argument("--exclusion-list", type=Path, help="Data OS owner's entitlement exclusion list (JSON list of security_id); none = empty pin")
    a = ap.parse_args()
    text = REG.read_text(encoding="utf-8")
    frozen = yaml_block(text)
    units_doc = json.loads(UNITS.read_text())
    units = units_doc["units"]
    sessions = calendar()
    K = int(frozen["decision_window_K_sessions"]); H = int(frozen["horizon_sessions"])
    excl = json.loads(a.exclusion_list.read_text()) if a.exclusion_list else []
    census = json.loads(CENSUS.read_text())
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    doc = {
        "schema": "us.prophet_entry_timing_w2_freeze/v1",
        "status": "FROZEN",
        "frozen_date": "2026-10-31",
        "freeze_commit": None,   # written by the commit that follows this record (see registration header)
        "registration": {"path": str(REG), "revision": 8, "sha256_at_freeze": sha256(REG), "schema": frozen["schema"]},
        "independent_review": {"head_passed": a.review_head, "note": a.review_note},
        "authority": frozen["authority"],
        "parents": frozen["parents"],
        "census": {"path": str(CENSUS), "version": census["provenance"]["census_version"], "sha256": sha256(CENSUS),
                   "walk_sha": census["freeze_basis"]["origin_main_sha"], "inputs": census.get("inputs"),
                   "units_path": str(UNITS), "units_sha256": sha256(UNITS), "units_walk_sha": units_doc["walk_sha"],
                   "counts": census["freeze_basis"]["counts"]},
        "entitlement_exclusion": {"owner_role": "Data OS owner", "pinned_security_ids": excl, "count": len(excl),
                                  "source": str(a.exclusion_list) if a.exclusion_list else
                                  "none exists in the repository at the freeze (searched docs/, research/, config/, engine/, scripts/ for an entitlement exclusion list); "
                                  "a list supplied later is pinned at its own look and never applied retroactively to a look already taken"},
        "t3_availability_gate": t3_gate(units, sessions),
        "r_maturity": maturity(units, sessions, K, H),
        "frozen_fields": frozen,
        "frozen_at_head": head,
        "reads": "dates, ids and the price-panel DATE INDEX only; no close/outcome column opened",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, default=str) + "\n", encoding="utf-8")
    g = doc["t3_availability_gate"]; m = doc["r_maturity"]
    print(json.dumps({"t3": {k: g[k] for k in ("exact_pairs", "pairs_passing", "share", "t3_in_p_family")},
                      "maturity": {k: m[k] for k in ("latest_t_exec", "maturity_session_observed_arms", "maturity_session_with_t3_bound")},
                      "exclusions": doc["entitlement_exclusion"]["count"], "reg_sha": doc["registration"]["sha256_at_freeze"][:12]}, indent=1))


if __name__ == "__main__":
    main()
