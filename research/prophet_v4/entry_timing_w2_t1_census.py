"""Entry Timing W2 — T1 feasibility census (v3). Dates, tickers, lane/tier flags and commit
times ONLY. Reads no price, grade, outcome, excess or paired-race column; the SPY parquet is
opened for its DATE INDEX only (the NYSE session calendar).

Bases:
* screening (always): `payload.opened_session` stand-in, plain ticker join, stamp-grid lags —
  the revision-2 table, kept for comparability.
* freeze basis (``--receipt-sessions``): t_disc = W1 r3 receipt-recovered document
  ``data_session``; a BUY-lane stamp joins an episode only when
  ``VendorAliasTable.resolve("membership", ticker, on=stamp_date)`` returns the episode's
  ``security_id``; lags in NYSE trading sessions; coverage by PRODUCER HEALTH (a stamp date
  with at least one curated-tier row; a session with no healthy stamp is a GAP — the BUY lane is
  classified inside the curated tier, so a zero-curated day cannot admit anyone);
  INCUMBENT_LED (a BUY row in [t_disc-K, t_disc)); interval-censored admission when a gap
  precedes the first BUY stamp (earliest-possible = first gap session, latest = observed stamp).
* ``--commit-walk``: knowability — for every commit of each monthly candidates parquet on
  ``origin/main`` (full history), the EARLIEST commit containing each (stamp_date, ticker)
  BUY row; the knowable session is the first NYSE session whose close (16:00 ET) is strictly
  after commit time + ``--buffer-minutes``.
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path("data/us_prophet_rank")
GEN = ROOT / "episodes/generations/peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9"
COLS = ["stamp_date", "ticker", "tier", "lane", "eligible", "buyable", "featured", "signal_asof"]
ET = ZoneInfo("America/New_York")


def _stamps() -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(str(ROOT / "candidates" / "2026-*.parquet"))):
        d = pd.read_parquet(f, columns=COLS)
        frames.append(d)
    c = pd.concat(frames, ignore_index=True)
    c["stamp_date"] = pd.to_datetime(c["stamp_date"]).dt.strftime("%Y-%m-%d")
    return c


def _opened() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(GEN / "events" / "*.jsonl"))):
        for line in open(f):
            e = json.loads(line)
            if e.get("event_type") == "OPENED":
                p = e.get("payload", {})
                out.append({"episode_id": e.get("episode_id"), "receipt": e.get("source_receipt"),
                            "ticker": p.get("ticker_at_observation"), "opened_session": p.get("opened_session"),
                            "security_id": p.get("security_id")})
    return out


def _sessions() -> list[str]:
    idx = pd.to_datetime(pd.read_parquet("data/yahoo/SPY.parquet", columns=[]).index)
    return sorted(set(idx.strftime("%Y-%m-%d")))


def screening(c: pd.DataFrame, opened: list[dict]) -> dict:
    grid = sorted(set(c["stamp_date"]))
    gi = {d: i for i, d in enumerate(grid)}
    defs = {"curated": c.tier == "curated", "lane_buy": c.lane == "buy", "buyable": c.buyable == True,
            "featured": c.featured == True, "eligible": c.eligible == True}
    res = {}
    for name, mask in defs.items():
        by = c[mask].groupby("ticker")["stamp_date"].apply(sorted).to_dict()
        lags, never, prior = [], 0, 0
        for o in opened:
            s = o["opened_session"]
            ds = by.get(o["ticker"], [])
            prior += any(d < s for d in ds)
            later = [d for d in ds if d >= s]
            if not later:
                never += 1
                continue
            gs = [d for d in grid if d >= s]
            lags.append(gi[later[0]] - gi[gs[0]])
        ser = pd.Series(lags, dtype=float)
        res[name] = {"with_stamp": len(lags), "never": never, "already_before": int(prior),
                     "zero_lag_share": round(float((ser == 0).mean()), 3) if len(ser) else None,
                     "median_lag_grid": float(ser.median()) if len(ser) else None}
    return {"stamp_dates": len(grid), "opened": len(opened), "t1_defs": res,
            "note": "revision-2 screening basis: opened_session stand-in, ticker join, stamp-grid lags"}


def commit_walk(months: list[str], sessions: list[str], buffer_minutes: int) -> dict:
    """earliest commit per (stamp_date, ticker) BUY row -> knowable session."""
    earliest: dict[tuple[str, str], tuple[str, str]] = {}
    n_commits = 0
    for m in months:
        rel = f"data/us_prophet_rank/candidates/{m}.parquet"
        log = subprocess.run(["git", "log", "origin/main", "--full-history", "--reverse", "--format=%H %cI", "--", rel],
                             capture_output=True, text=True, check=True).stdout.split()
        pairs = list(zip(log[0::2], log[1::2]))
        for sha, ctime in pairs:
            n_commits += 1
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
                blob = subprocess.run(["git", "cat-file", "-p", f"{sha}:{rel}"], capture_output=True, check=False)
                if blob.returncode != 0:
                    continue
                tf.write(blob.stdout)
                tmp = tf.name
            try:
                d = pd.read_parquet(tmp, columns=["stamp_date", "ticker", "lane"])
            except Exception:
                continue
            finally:
                Path(tmp).unlink(missing_ok=True)
            d = d[d.lane == "buy"]
            sd = pd.to_datetime(d["stamp_date"]).dt.strftime("%Y-%m-%d")
            for s, t in zip(sd, d["ticker"]):
                key = (s, t)
                if key not in earliest:
                    earliest[key] = (ctime, sha)
    knowable = {}
    for (s, t), (ctime, sha) in earliest.items():
        ct = datetime.fromisoformat(ctime).astimezone(ET) + timedelta(minutes=buffer_minutes)
        # first session whose 16:00 ET close is strictly after ct
        ks = next((d for d in sessions if datetime.fromisoformat(d + "T16:00:00").replace(tzinfo=ET) > ct), None)
        knowable[f"{s}|{t}"] = {"commit": sha[:12], "committed_et": ct.isoformat(), "knowable_session": ks}
    return {"commits_walked": n_commits, "buy_rows": len(earliest), "knowable": knowable}


def freeze_basis(c, opened, receipt_sessions, sessions, *, k, r_from, r_to, walk=None) -> dict:
    sys.path.insert(0, ".")
    from engine.us_candidate_episode_intake import _records_snapshot  # noqa: E402
    from lib.dataos.identity import VendorAliasTable  # noqa: E402
    rows, receipt = _records_snapshot(Path("data/reference/vendor_aliases.parquet"))
    aliases = VendorAliasTable.from_records(rows)
    si = {d: i for i, d in enumerate(sessions)}
    healthy = set(c[c.tier == "curated"]["stamp_date"])
    gaps = [d for d in sessions if r_from <= d and d not in healthy]
    buy = c[c.lane == "buy"].groupby("ticker")["stamp_date"].apply(sorted).to_dict()
    sa_bad = set(map(tuple, c[pd.to_datetime(c["signal_asof"], errors="coerce").dt.strftime("%Y-%m-%d") > c["stamp_date"]][["stamp_date", "ticker"]].values.tolist()))
    counts = {"opened": len(opened), "t_disc_recovered": 0, "t_disc_unrecovered": 0, "t_disc_not_a_session": 0, "in_R": 0,
              "incumbent_led": 0, "t1_identified_exact": 0, "t1_identified_interval": 0, "t1_cash_window_covered": 0,
              "t1_censored_gap_no_stamp": 0, "t1_unknown_signal_asof": 0, "t1_unknown_identity": 0,
              "zero_lag": 0, "knowable_later_than_stamp": 0, "knowable_missing": 0}
    lag_early, lag_obs, by_month, know_shift = [], [], {}, []
    for o in opened:
        s = receipt_sessions.get(o["receipt"])
        if not s:
            counts["t_disc_unrecovered"] += 1
            continue
        counts["t_disc_recovered"] += 1
        if s not in si:
            counts["t_disc_not_a_session"] += 1
            continue
        if not (r_from <= s <= r_to):
            continue
        counts["in_R"] += 1
        i0 = si[s]
        window = sessions[i0: i0 + k + 1]          # t_disc .. t_disc+K
        pre = sessions[max(0, i0 - k): i0]           # t_disc-K .. t_disc-1
        ds = buy.get(o["ticker"], [])
        if any(d in pre for d in ds):
            counts["incumbent_led"] += 1
            continue
        t_cur, unknown = None, None
        for d in window:
            if d not in healthy:
                continue
            if d in ds:
                if (d, o["ticker"]) in sa_bad:
                    unknown = "signal_asof"; break
                if aliases.resolve("membership", o["ticker"], on=date.fromisoformat(d)) != o["security_id"]:
                    unknown = "identity"; break
                t_cur = d
                break
        if unknown:
            counts[f"t1_unknown_{unknown}"] += 1
            continue
        if t_cur is None:
            if any(d not in healthy for d in window):
                counts["t1_censored_gap_no_stamp"] += 1
            else:
                counts["t1_cash_window_covered"] += 1
            continue
        gap_before = [d for d in window if d < t_cur and d not in healthy]
        early = gap_before[0] if gap_before else t_cur
        counts["t1_identified_interval" if gap_before else "t1_identified_exact"] += 1
        lag_early.append(si[early] - i0)
        lag_obs.append(si[t_cur] - i0)
        counts["zero_lag"] += (si[early] - i0) == 0
        by_month[s[:7]] = by_month.get(s[:7], 0) + 1
        if walk is not None:
            kn = walk["knowable"].get(f"{t_cur}|{o['ticker']}")
            if kn is None or kn["knowable_session"] is None:
                counts["knowable_missing"] += 1
            else:
                shift = si.get(kn["knowable_session"], 10**6) - si[t_cur]
                know_shift.append(shift)
                counts["knowable_later_than_stamp"] += shift > 0
    e, ob = pd.Series(lag_early, dtype=float), pd.Series(lag_obs, dtype=float)
    ident = counts["t1_identified_exact"] + counts["t1_identified_interval"]
    return {"basis": "W1 r3 receipt sessions + VendorAliasTable membership join; NYSE trading sessions; producer-health coverage",
            "alias_receipt": receipt, "k_sessions": k, "R": [r_from, r_to],
            "sessions_in_R": len([d for d in sessions if r_from <= d <= r_to]),
            "healthy_stamp_dates_in_R": len([d for d in healthy if r_from <= d <= r_to]),
            "gap_sessions_from_r_from": gaps, "counts": counts,
            "identified_pairs": ident, "identified_by_t_disc_month": by_month,
            "lag_sessions_earliest_possible": {"median": float(e.median()) if len(e) else None, "iqr": [float(e.quantile(.25)), float(e.quantile(.75))] if len(e) else None},
            "lag_sessions_observed_stamp": {"median": float(ob.median()) if len(ob) else None},
            "k_star_candidate_sessions": float(e.median()) if len(e) else None,
            "knowability_shift_sessions": pd.Series(know_shift).value_counts().sort_index().to_dict() if know_shift else None,
            "floor_30_met": ident >= 30}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt-sessions", type=Path)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--r-from", default="2026-08-26")
    ap.add_argument("--r-to", default="2026-10-23")
    ap.add_argument("--commit-walk", action="store_true")
    ap.add_argument("--buffer-minutes", type=int, default=30)
    a = ap.parse_args()
    c, opened, sessions = _stamps(), _opened(), _sessions()
    out = {"screening": screening(c, opened)}
    walk = None
    if a.commit_walk:
        walk = commit_walk(["2026-08", "2026-09", "2026-10"], sessions, a.buffer_minutes)
        out["commit_walk"] = {k: v for k, v in walk.items() if k != "knowable"}
    if a.receipt_sessions:
        raw = json.loads(a.receipt_sessions.read_text())
        out["freeze_basis"] = freeze_basis(c, opened, raw.get("sessions", raw), sessions, k=a.k,
                                           r_from=a.r_from, r_to=a.r_to, walk=walk)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
