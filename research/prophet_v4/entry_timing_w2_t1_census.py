"""Entry Timing W2 — T1 feasibility census (v5). Dates, tickers, lane/tier flags and commit
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
* ``--commit-walk``: knowability — for every FIRST-PARENT commit of each monthly candidates
  parquet on ``origin/main`` (arrival on main, not a side-branch committer time), the FIRST
  blob carrying each stamp_date fixes that session's lane state (its BUY rows, its curated
  coverage, its signal_asof) and its knowable session: the first NYSE session whose close
  (16:00 ET) is strictly after the arrival time + ``--buffer-minutes``. A later blob that
  changes the BUY set of an already-carried stamp_date is a HEAL: that session is a GAP
  (lane state not as practised). Every monthly parquet that ever existed on main is walked.
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
                            "security_id": p.get("security_id"), "identity_epoch": p.get("identity_epoch"),
                            "recorded_at": e.get("recorded_at")})
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


def _candidate_months() -> list[str]:
    out = subprocess.run(["git", "log", "origin/main", "--first-parent", "--name-only", "--format=", "--",
                          "data/us_prophet_rank/candidates/"], capture_output=True, text=True, check=True).stdout.split()
    return sorted({Path(x).stem for x in out if x.endswith(".parquet") and Path(x).stem.startswith("2026-")})


def commit_walk(months: list[str] | None, sessions: list[str], buffer_minutes: int) -> dict:
    """First-arrival lane state on origin/main (first-parent history, oldest first). Per
    stamp_date the FIRST blob carrying it fixes: the BUY rows as first committed, whether any
    curated-tier row existed (producer-health coverage), the BUY rows whose signal_asof exceeded
    stamp_date, and the arrival commit -> knowable session. A later blob whose BUY set for that
    stamp_date differs is a HEAL and the session is reported in ``healed_stamp_dates``."""
    months = months or _candidate_months()
    first_arrival: dict[str, tuple[str, str]] = {}
    first_curated: dict[str, bool] = {}
    buy_at_first: dict[str, set[str]] = {}
    sa_bad: set[tuple[str, str]] = set()
    healed: dict[str, dict] = {}
    n_commits = 0
    for m in months:
        rel = f"data/us_prophet_rank/candidates/{m}.parquet"
        log = subprocess.run(["git", "log", "origin/main", "--first-parent", "--reverse", "--format=%H %cI", "--", rel],
                             capture_output=True, text=True, check=True).stdout.split()
        for sha, ctime in zip(log[0::2], log[1::2]):
            n_commits += 1
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
                blob = subprocess.run(["git", "cat-file", "-p", f"{sha}:{rel}"], capture_output=True, check=False)
                if blob.returncode != 0:
                    continue
                tf.write(blob.stdout)
                tmp = tf.name
            try:
                d = pd.read_parquet(tmp, columns=["stamp_date", "ticker", "lane", "tier", "signal_asof"])
            except Exception:
                continue
            finally:
                Path(tmp).unlink(missing_ok=True)
            d["sd"] = pd.to_datetime(d["stamp_date"]).dt.strftime("%Y-%m-%d")
            cur = set(d[d.tier == "curated"]["sd"])
            b = d[d.lane == "buy"]
            sa = pd.to_datetime(b["signal_asof"], errors="coerce").dt.strftime("%Y-%m-%d")
            buy_now: dict[str, set[str]] = {}
            for sd, t in zip(b["sd"], b["ticker"]):
                buy_now.setdefault(sd, set()).add(t)
            for sd in set(d["sd"]):
                if sd not in first_arrival:
                    first_arrival[sd] = (ctime, sha)
                    first_curated[sd] = sd in cur
                    buy_at_first[sd] = buy_now.get(sd, set())
                    for t, a in zip(b[b.sd == sd]["ticker"], sa[b.sd == sd]):
                        if isinstance(a, str) and a > sd:
                            sa_bad.add((sd, t))
                elif buy_now.get(sd, set()) != buy_at_first[sd] and sd not in healed:
                    healed[sd] = {"heal_commit": sha[:12], "heal_committed": ctime,
                                  "buy_added": len(buy_now.get(sd, set()) - buy_at_first[sd]),
                                  "buy_removed": len(buy_at_first[sd] - buy_now.get(sd, set()))}
    knowable = {}
    for sd, (ctime, sha) in first_arrival.items():
        ct, ks = _knowable(ctime, sessions, buffer_minutes)
        knowable[sd] = {"commit": sha[:12], "arrived_et": ct.isoformat(), "knowable_session": ks}
    buy_first = sorted((sd, t) for sd, ts in buy_at_first.items() for t in ts)
    return {"basis": "first-parent arrival on origin/main; lane state = first blob per stamp_date; a later BUY-set change = HEAL (GAP)",
            "months_walked": months, "commits_walked": n_commits, "buy_rows_first_blob": len(buy_first),
            "stamp_dates_seen": len(first_arrival), "healthy_stamp_dates_first_commit": sum(first_curated.values()),
            "healed_stamp_dates": healed, "knowable": knowable, "buy_first": buy_first,
            "first_curated": first_curated, "sa_bad_first": sorted(sa_bad)}


TURN_WATCH_DIR = "data/us_prophet_rank/episode_inputs/turn_watch"


def _knowable(ctime: str, sessions: list[str], buffer_minutes: int):
    ct = datetime.fromisoformat(ctime).astimezone(ET) + timedelta(minutes=buffer_minutes)
    ks = next((d for d in sessions if datetime.fromisoformat(d + "T16:00:00").replace(tzinfo=ET) > ct), None)
    return ct, ks


def document_walk(sessions: list[str], buffer_minutes: int) -> dict:
    """earliest origin/main commit per turn_watch document receipt -> knowable session.

    Mirrors W1 r3's receipt recovery (every blob of the directory, digest verified through
    the ONE canonical digest) but walks FIRST-PARENT history so the instant is the document's
    ARRIVAL on main (a side-branch committer time can predate arrival); k(t_disc) is
    as-arrived, not as-dated."""
    sys.path.insert(0, ".")
    from hashlib import sha256
    from engine.us_candidate_episode_intake import canonical_json  # noqa: E402
    log = subprocess.run(["git", "log", "origin/main", "--first-parent", "--reverse", "--format=%H %cI", "--", TURN_WATCH_DIR],
                         capture_output=True, text=True, check=True).stdout.split()
    earliest: dict[str, tuple[str, str, str]] = {}
    seen: set[str] = set()
    for sha, ctime in zip(log[0::2], log[1::2]):
        tree = subprocess.run(["git", "ls-tree", "-r", sha, "--", TURN_WATCH_DIR], capture_output=True, text=True, check=True).stdout
        for line in tree.splitlines():
            blob = line.split("\t", 1)[0].split()[2]
            if blob in seen:
                continue
            seen.add(blob)
            raw = subprocess.run(["git", "cat-file", "-p", blob], capture_output=True, check=True).stdout
            try:
                doc = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(doc, dict) or not isinstance(doc.get("content_sha256"), str) or not isinstance(doc.get("data_session"), str):
                continue
            expected = sha256(canonical_json({k: v for k, v in doc.items() if k != "content_sha256"}).encode("utf-8")).hexdigest()
            if expected != doc["content_sha256"]:
                continue
            receipt = f"sha256:{doc['content_sha256']}"
            if receipt not in earliest:
                earliest[receipt] = (ctime, sha, doc["data_session"][:10])
    knowable = {}
    for receipt, (ctime, sha, ds) in earliest.items():
        ct, ks = _knowable(ctime, sessions, buffer_minutes)
        knowable[receipt] = {"commit": sha[:12], "arrived_et": ct.isoformat(), "data_session": ds, "knowable_session": ks}
    return {"basis": "first-parent arrival on origin/main", "commits_walked": len(log) // 2, "blobs": len(seen), "receipts": len(earliest), "knowable": knowable}


def freeze_basis(c, opened, receipt_sessions, sessions, *, k, r_from, r_to, walk=None, dwalk=None, k_fixed=2) -> dict:
    """v5: security-first identity join over EVERY window session for EVERY unit (uniform span;
    all candidate symbols of a multi-symbol security are tested), lane state and coverage from
    the first-arrival blobs (a healed session is a GAP; HEAD is never read for lane state),
    INCUMBENT_LED and INCUMBENT_LED_UNKNOWN (pre-window gap OR pre-window identity unknown),
    T1 executable only when the BUY row's knowable session k(c_cur) <= t_disc + K, exact /
    interval / cash / censored / unknown admission, exact-basis lags and k*, as-arrived
    knowability for both arms, the EXECUTABLE lead, the OPENED payload's recording instant
    against the T0 fill instant, and the distinct-session counts the block bootstrap floors use."""
    import functools
    from hashlib import sha256
    sys.path.insert(0, ".")
    from engine.us_candidate_episode_intake import _records_snapshot  # noqa: E402
    from lib.dataos.identity import VendorAliasTable  # noqa: E402
    alias_path = Path("data/reference/vendor_aliases.parquet")
    rows, receipt = _records_snapshot(alias_path)
    aliases = VendorAliasTable.from_records(rows)
    si = {d: i for i, d in enumerate(sessions)}
    head_healthy = set(c[c.tier == "curated"]["stamp_date"])
    head_buy = set(map(tuple, c[c.lane == "buy"][["stamp_date", "ticker"]].values.tolist()))
    if walk is not None:
        healed = set(walk["healed_stamp_dates"])
        healthy = {d for d, cur in walk["first_curated"].items() if cur and d not in healed}
        buy = {tuple(x) for x in walk["buy_first"] if x[0] not in healed}
        sa_bad = set(map(tuple, walk["sa_bad_first"]))
        knowable_stamp = {d: v["knowable_session"] for d, v in walk["knowable"].items()}
        lane_basis = "first-arrival blob per stamp_date (first-parent origin/main); healed sessions are GAPs; HEAD never read"
    else:
        sa = pd.to_datetime(c["signal_asof"], errors="coerce").dt.strftime("%Y-%m-%d")
        healed, healthy, buy, knowable_stamp = set(), head_healthy, head_buy, {}
        sa_bad = set(map(tuple, c[(c.tier == "curated") & (sa > c["stamp_date"])][["stamp_date", "ticker"]].values.tolist()))
        lane_basis = "HEAD working tree (screening only — not a freeze basis)"
    disagreement = {"buy_rows_head_not_first": len(head_buy - buy), "buy_rows_first_not_head": len(buy - head_buy),
                    "healthy_dates_head_not_first": sorted(head_healthy - healthy), "healthy_dates_first_not_head": sorted(healthy - head_healthy),
                    "healed_stamp_dates": sorted(healed)}
    gaps = [d for d in sessions if r_from <= d <= r_to and d not in healthy]
    counts = {"opened": len(opened), "t_disc_recovered": 0, "t_disc_unrecovered": 0, "t_disc_not_a_session": 0, "in_R": 0,
              "incumbent_led": 0, "incumbent_led_unknown": 0, "incumbent_led_unknown_pre_gap": 0, "incumbent_led_unknown_pre_identity": 0,
              "t1_identified_exact": 0, "t1_identified_interval": 0, "t1_cash_window_covered": 0,
              "t1_censored_gap_no_stamp": 0, "t1_unknown_signal_asof": 0, "t1_unknown_identity": 0,
              "t1_buy_stamp_inside_k_but_knowable_outside": 0,
              "exact_zero_lag": 0, "exact_knowable_missing": 0, "exact_disc_knowable_missing": 0,
              "exact_knowable_later_than_stamp": 0, "exact_disc_knowable_later_than_session": 0,
              "exact_symbol_differs_from_ticker_at_observation": 0, "exact_multi_symbol_security": 0,
              "recorded_at_missing": 0, "recorded_at_le_t0_fill": 0, "recorded_at_gt_t0_fill": 0}

    # security-first join: candidate symbols come from the alias RECORDS (the clocked reverse lookup
    # returns UNAVAILABLE for this namespace) and EVERY candidate is confirmed by the forward resolver.
    # Membership records carry no validity window, so the per-session resolve is the current snapshot.
    reverse: dict[str, list[str]] = {}
    for r in rows:
        if r.get("vendor") == "membership" and r.get("alias_kind") is None and r.get("security_id") and r.get("vendor_symbol"):
            reverse.setdefault(r["security_id"], []).append(r["vendor_symbol"])
    alias_ingested_at = max((str(r.get("ingested_at")) for r in rows if r.get("vendor") == "membership" and r.get("ingested_at")), default=None)
    multi_symbol = sum(1 for v in reverse.values() if len(v) > 1)

    @functools.lru_cache(maxsize=None)
    def syms(sid: str, d: str) -> tuple[str, ...]:
        return tuple(cand for cand in reverse.get(sid, []) if aliases.resolve("membership", cand, on=date.fromisoformat(d)) == sid)

    def t0_fill_instant(receipt_id: str):
        dk = (dwalk or {}).get("knowable", {}).get(receipt_id)
        if not dk or not dk["knowable_session"]:
            return None
        j = si.get(dk["knowable_session"])
        if j is None or j + 1 >= len(sessions):
            return None
        return datetime.fromisoformat(sessions[j + 1] + "T16:00:00").replace(tzinfo=ET)

    lag_exact, lag_interval_obs, lag_interval_early, by_month_exact = [], [], [], {}
    t1_shift, t0_shift, exec_lead, exec_lead_strict = [], [], [], []
    sessions_exact, sessions_primary, cohort = set(), set(), {}
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
        fill0 = t0_fill_instant(o["receipt"])
        if not o.get("recorded_at"):
            counts["recorded_at_missing"] += 1
        elif fill0 is not None:
            ra = datetime.fromisoformat(str(o["recorded_at"]).replace("Z", "+00:00"))
            counts["recorded_at_le_t0_fill" if ra <= fill0 else "recorded_at_gt_t0_fill"] += 1
        window = sessions[i0: i0 + k + 1]
        k_limit = sessions[min(i0 + k, len(sessions) - 1)]
        pre = sessions[max(0, i0 - k): i0]
        sid = o["security_id"]
        led, pre_gap, pre_unknown = False, False, False
        for d in pre:
            if d not in healthy:
                pre_gap = True
                continue
            ts = syms(sid, d)
            if not ts:
                pre_unknown = True
                continue
            if any((d, t) in buy for t in ts):
                led = True
                break
        if led:
            counts["incumbent_led"] += 1
            continue
        if pre_gap or pre_unknown:
            counts["incumbent_led_unknown"] += 1
            counts["incumbent_led_unknown_pre_gap"] += pre_gap
            counts["incumbent_led_unknown_pre_identity"] += pre_unknown
        strict = not pre_gap and not pre_unknown
        # uniform span: identity is tested on EVERY healthy window session for EVERY unit
        if any(not syms(sid, d) for d in window if d in healthy):
            counts["t1_unknown_identity"] += 1
            continue
        t_cur, t_sym, unknown, gap_before = None, None, None, []
        for d in window:
            if d not in healthy:
                gap_before.append(d)
                continue
            hit = [t for t in syms(sid, d) if (d, t) in buy]
            if hit:
                if any((d, t) in sa_bad for t in hit):
                    unknown = "signal_asof"
                    break
                if walk is not None and (knowable_stamp.get(d) is None or knowable_stamp[d] > k_limit):
                    counts["t1_buy_stamp_inside_k_but_knowable_outside"] += 1
                    break   # not executable inside K: falls to cash / censored below
                t_cur, t_sym = d, hit[0]
                break
        if unknown:
            counts[f"t1_unknown_{unknown}"] += 1
            continue
        if t_cur is None:
            counts["t1_censored_gap_no_stamp" if gap_before else "t1_cash_window_covered"] += 1
            if not gap_before and strict:
                sessions_primary.add(s)
                cohort[s] = cohort.get(s, 0) + 1
            continue
        if gap_before:
            counts["t1_identified_interval"] += 1
            lag_interval_obs.append(si[t_cur] - i0)
            lag_interval_early.append(si[gap_before[0]] - i0)
            continue
        counts["t1_identified_exact"] += 1
        counts["exact_zero_lag"] += (si[t_cur] - i0) == 0
        counts["exact_symbol_differs_from_ticker_at_observation"] += t_sym != o["ticker"]
        counts["exact_multi_symbol_security"] += len(reverse.get(sid, [])) > 1
        by_month_exact[s[:7]] = by_month_exact.get(s[:7], 0) + 1
        lag_exact.append(si[t_cur] - i0)
        if strict:
            sessions_exact.add(s)
            sessions_primary.add(s)
            cohort[s] = cohort.get(s, 0) + 1
        if walk is None or dwalk is None:
            continue
        ks1 = knowable_stamp.get(t_cur)
        dk = dwalk["knowable"].get(o["receipt"])
        if ks1 is None:
            counts["exact_knowable_missing"] += 1
        if dk is None or dk["knowable_session"] is None:
            counts["exact_disc_knowable_missing"] += 1
        if ks1 is None or not dk or dk["knowable_session"] is None:
            continue
        sh1 = si.get(ks1, 10**6) - si[t_cur]
        sh0 = si.get(dk["knowable_session"], 10**6) - i0
        t1_shift.append(sh1)
        t0_shift.append(sh0)
        counts["exact_knowable_later_than_stamp"] += sh1 > 0
        counts["exact_disc_knowable_later_than_session"] += sh0 > 0
        lead = (si[t_cur] + sh1) - (i0 + sh0)   # t_exec(T1) - t_exec(T0): both fill one session after their knowable session
        exec_lead.append(lead)
        if strict:
            exec_lead_strict.append(lead)

    def _dist(v):
        return pd.Series(v).value_counts().sort_index().to_dict() if v else None

    def _stats(v):
        if not v:
            return None
        x = pd.Series(v, dtype=float)
        return {"n": int(len(x)), "median": float(x.median()), "iqr": [float(x.quantile(.25)), float(x.quantile(.75))], "distribution": _dist(v)}

    ex = pd.Series(lag_exact, dtype=float)
    k_star = float(ex.median()) if len(ex) else None
    n12 = {"healthy_stamp_dates_head": len(head_healthy), "healthy_stamp_dates_first_commit": len(healthy),
           "stamp_dates_total": int(c["stamp_date"].nunique()),
           "curated_rows_per_stamp_median": float(c[c.tier == "curated"].groupby("stamp_date").size().median()),
           "buy_rows_per_stamp_median": float(c[c.lane == "buy"].groupby("stamp_date").size().median()),
           "last_healthy_stamp_date": max(healthy) if healthy else None}
    return {"basis": "W1 r3 receipt sessions; VendorAliasTable membership join, security-first (record-derived candidates confirmed by resolve() on every window session, all candidates of a multi-symbol security); NYSE trading sessions; producer-health coverage on first-arrival blobs",
            "lane_state_basis": lane_basis, "head_vs_first_commit_disagreement": disagreement,
            "alias_receipt": receipt, "alias_parquet_sha256": sha256(alias_path.read_bytes()).hexdigest(),
            "alias_knowledge_time": {"membership_rows_latest_ingested_at": alias_ingested_at, "membership_securities_with_multiple_symbols": multi_symbol, "note": "membership records carry no validity window; the join uses the current snapshot (knowledge time = its ingest), a disclosed look-ahead on identity labels only; the snapshot sha is pinned per look"},
            "identity_epoch_enforced_by_table_api": False,
            "k_sessions": k, "k_fixed_sessions": k_fixed, "R": [r_from, r_to],
            "sessions_in_R": len([d for d in sessions if r_from <= d <= r_to]),
            "healthy_sessions_in_R": len([d for d in healthy if r_from <= d <= r_to]),
            "gap_sessions_in_R": gaps, "counts": counts, "stamp_facts": n12,
            "identified_exact_by_t_disc_month": by_month_exact,
            "distinct_t_disc_sessions_primary_strict": len(sessions_primary),
            "distinct_t_disc_sessions_exact_strict": len(sessions_exact),
            "primary_strict_units_per_session": _stats(list(cohort.values())),
            "lag_sessions_exact": _stats(lag_exact),
            "lag_sessions_interval_observed_stamp": _stats(lag_interval_obs),
            "lag_sessions_interval_earliest_possible": _stats(lag_interval_early),
            "k_star_sessions_exact_basis": k_star,
            "t2m_identified": (k_star is not None and k_star not in (0, k_fixed)),
            "t1_knowability_shift_sessions_exact": _dist(t1_shift),
            "t0_knowability_shift_sessions_exact": _dist(t0_shift),
            "executable_lead_sessions_exact": _stats(exec_lead),
            "executable_lead_sessions_exact_strict": _stats(exec_lead_strict)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt-sessions", type=Path)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--r-from", default="2026-08-26")
    ap.add_argument("--r-to", default="2026-10-23")
    ap.add_argument("--commit-walk", action="store_true")
    ap.add_argument("--buffer-minutes", type=int, default=30)
    ap.add_argument("--document-walk", action="store_true")
    a = ap.parse_args()
    c, opened, sessions = _stamps(), _opened(), _sessions()
    out = {"screening": screening(c, opened)}
    walk = None
    if a.commit_walk:
        walk = commit_walk(None, sessions, a.buffer_minutes)
        out["commit_walk"] = {k: v for k, v in walk.items() if k not in ("knowable", "buy_first", "first_curated", "sa_bad_first")}
    dwalk = None
    if a.document_walk:
        dwalk = document_walk(sessions, a.buffer_minutes)
        out["document_walk"] = {k: v for k, v in dwalk.items() if k != "knowable"}
    if a.receipt_sessions:
        raw = json.loads(a.receipt_sessions.read_text())
        out["freeze_basis"] = freeze_basis(c, opened, raw.get("sessions", raw), sessions, k=a.k,
                                           r_from=a.r_from, r_to=a.r_to, walk=walk, dwalk=dwalk)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
