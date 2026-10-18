#!/usr/bin/env python3
"""R4 dry-run receipt V2 builder: which R4 cells reach the preregistered N floor before EVAL-1.

Deterministic. Reads only git objects at one pinned origin/main revision plus a read-only
snapshot of the price-pressure owner's massive_stock_day store. Writes the receipt JSON and its
Markdown rendering into --out-dir. Never writes into data/ or site/.

Rules (seat commission B5, 2026-10-07):
  * corpus: K3E expectation observations/attempts blobs at --rev; every clock strictly before
    the EVAL-1 boundary 2026-10-07T13:30Z.
  * issuer axis: DEC:ITP-R4-ISSUER-AXIS-AS-KNOWN-VERSION-CLOCK-2026-10-07. For a cutoff C the
    known version is the newest security_master blob on --rev's first-parent history with
    committer time <= C - 24h; every field is read from that one version
    (clock label REPO_HISTORY_AVAILABILITY).
  * security axis: yahoo vendor_aliases rows with ingested_at <= min(capture, cutoff), a validity
    window covering the capture date, and the same security at capture and at cutoff.
  * episodes: average consensus, series (issuer, metric, q/y, period_end); variant S (observed
    20-session quiet) is PRIMARY, variant L is a labelled SENSITIVITY; issuer overlap clustering
    chains starts <= 20 sessions apart.
  * windows: h in (5, 21, 63) NYSE sessions after the cutoff session; COMPLETE only if every bar
    is <= the last pre-boundary session; otherwise RIGHT_CENSORED_AT_BOUNDARY.
  * MKT-1: owner-native residual (engine.price_pressure.response_export over the owner's
    LSR panel/derive), computed on a panel sliced to sessions <= the last pre-boundary session.
  * floors: >= 100 issuer episodes overall and >= 25 per subgroup; effect statistics only for
    cells at the floor.

Nothing here is promotion-bearing: financial_influence, k3e_admissible and promotion_eligible
are false everywhere; there is no score and no rank.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

SCHEMA = "itp.r4_dryrun_receipt.v2"
RECEIPT_ID = "R4_DRYRUN_RECEIPT_V2_2026-10-07"
BOUNDARY = pd.Timestamp("2026-10-07T13:30:00Z")
LAST_PRE_BOUNDARY_SESSION = dt.date(2026, 10, 6)
HOLDOUT_END = "2026-08-21"
QUIET_GAP = 20
FLOOR_OVERALL = 100
FLOOR_SUBGROUP = 25
HORIZONS = (5, 21, 63)
KNOWN_VERSION_GUARD = pd.Timedelta(hours=24)
CALENDAR_START = dt.date(2026, 6, 1)
NYSE_HOLIDAYS = (dt.date(2026, 6, 19), dt.date(2026, 7, 3), dt.date(2026, 9, 7))
CLOSE_UTC_HOUR = 20  # 16:00 America/New_York during EDT; no early close in the calendar span
SUBGROUPS = (
    ("metric", "EPS"), ("metric", "revenue"),
    ("period", "0q"), ("period", "+1q"), ("period", "0y"), ("period", "+1y"),
)
VERDICTS = (
    "R4_ADMISSIBLE_DESCRIPTIVE",
    "R4_INSUFFICIENT_N_PRE_BOUNDARY",
    "R4_BLOCKED_NO_OWNER_RESIDUAL_FRAME",
    "R4_BLOCKED_NO_ISSUER_EPISODES",
    "R4_BLOCKED_CALENDAR_MISMATCH",
)
PATHS = dict(
    observations="data/revisions/expectation_observations.parquet",
    attempts="data/revisions/expectation_attempts.parquet",
    security_master="data/reference/security_master.parquet",
    vendor_aliases="data/reference/vendor_aliases.parquet",
    ticker_sectors="data/breadth/ticker_sectors.parquet",
    price_pressure_latest="data/price_pressure/latest.json",
)
LABELS = dict(
    era="INTER_ERA_GAP",
    era_note="between the EVAL-0 holdout end 2026-08-21 and the EVAL-1 boundary 2026-10-07T13:30Z",
    promotion_bearing=False,
    cohort_filter="COHORT_FILTER_UNAVAILABLE",
    coupling_ceiling="COMPONENTS_ONLY",
    rights="UNKNOWN",
    financial_influence=False,
    k3e_admissible=False,
    promotion_eligible=False,
    score=None,
    rank=None,
    issuer_clock="REPO_HISTORY_AVAILABILITY",
)


# ---------------------------------------------------------------- git (read-only)
def _git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True).stdout


def _blob_id(repo: Path, rev: str, path: str) -> str:
    return _git(repo, "rev-parse", rev + ":" + path).decode().strip()


def _blob(repo: Path, oid: str) -> bytes:
    return _git(repo, "cat-file", "blob", oid)


def _history(repo: Path, rev: str, path: str) -> list:
    """First-parent publication history of one path: [(commit, committer_time_utc, blob, log_index)]."""
    txt = _git(repo, "log", "--first-parent", "-m", "--raw", "--no-abbrev",
               "--format=C %H %cI", rev, "--", path).decode()
    out, cur = [], None
    for line in txt.splitlines():
        if line.startswith("C "):
            _, cid, t = line.split()
            cur = (cid, pd.Timestamp(t).tz_convert("UTC"))
        elif line.startswith(":") and cur is not None:
            new = line.split()[3]
            if set(new) != set("0"):
                out.append((cur[0], cur[1], new, len(out)))
    return out


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- calendar
def hand_calendar() -> list:
    days = pd.bdate_range(CALENDAR_START, LAST_PRE_BOUNDARY_SESSION)
    return [d.date() for d in days if d.date() not in NYSE_HOLIDAYS]


def session_close(d: dt.date) -> pd.Timestamp:
    return pd.Timestamp(d).tz_localize("UTC") + pd.Timedelta(hours=CLOSE_UTC_HOUR)


# ---------------------------------------------------------------- issuer clock (DEC)
class KnownVersionClock:
    """security_master as known at a cutoff: newest version with committer time <= C - 24h."""

    def __init__(self, repo: Path, rev: str):
        self.versions = _history(repo, rev, PATHS["security_master"])
        self.repo = repo
        self._frames = dict()

    def version_for(self, cutoff_ts: pd.Timestamp):
        limit = cutoff_ts - KNOWN_VERSION_GUARD
        best = None
        for cid, ct, blob, idx in self.versions:
            if ct <= limit and (best is None or ct > best[1] or (ct == best[1] and idx < best[3])):
                best = (cid, ct, blob, idx)
        return best

    def frame(self, blob: str) -> pd.DataFrame:
        if blob not in self._frames:
            self._frames[blob] = pd.read_parquet(io.BytesIO(_blob(self.repo, blob))).set_index("security_id")
        return self._frames[blob]

    def issuer_at(self, security_id, cutoff_ts: pd.Timestamp):
        """Return (issuer_id, reason, version_blob). Every field from the one known version."""
        v = self.version_for(cutoff_ts)
        if v is None:
            return None, "MAPPING_NOT_PUBLISHED_BY_CUTOFF", None
        sm = self.frame(v[2])
        if security_id not in sm.index:
            return None, "SECURITY_NOT_IN_MASTER", v[2]
        m = sm.loc[security_id]
        if isinstance(m, pd.DataFrame):
            m = m.iloc[-1]
        state = m.get("security_state") if "security_state" in sm.columns else None
        if isinstance(state, str) and state:
            return None, "SECURITY_SUPERSEDED", v[2]
        if "issuer_state" not in sm.columns:
            return None, "ISSUER_STATE_COLUMN_ABSENT", v[2]
        if m.issuer_state != "RESOLVED" or not isinstance(m.issuer_id, str) or not m.issuer_id:
            return None, "ISSUER_STATE_" + str(m.issuer_state), v[2]
        if m.country != "US":
            return None, "NON_US_SEPARATE_SUBGROUP", v[2]
        return m.issuer_id, None, v[2]


# ---------------------------------------------------------------- alias rule (as data)
class AliasRule:
    """yahoo vendor_aliases: ingested_at <= min(capture, cutoff); window covers capture; same security at cutoff."""

    def __init__(self, va: pd.DataFrame):
        y = va[va.vendor == "yahoo"].copy()
        y["ing"] = pd.to_datetime(y.ingested_at, utc=True)
        y["vf"] = [pd.Timestamp(x).date() if _present(x) else None for x in y.valid_from]
        y["vt"] = [pd.Timestamp(x).date() if _present(x) else None for x in y.valid_to]
        y = y.sort_values(["vendor_symbol", "security_id", "ing"], kind="mergesort")
        self.rows = dict((k, list(g[["security_id", "ing", "vf", "vt"]].itertuples(index=False)))
                         for k, g in y.groupby("vendor_symbol", sort=True))
        self.yahoo_rows = int(len(y))

    def _at(self, sym, at_ts, cut_ts):
        rows = self.rows.get(sym)
        if rows is None:
            return None, "NO_YAHOO_ALIAS_ROW"
        ok, reason = [], "ALIAS_INGESTED_AFTER_CAPTURE"
        d = at_ts.date()
        for sid, ing, vf, vt in rows:
            if ing > at_ts or ing > cut_ts:
                continue
            if (vf is not None and d < vf) or (vt is not None and d >= vt):
                reason = "ALIAS_WINDOW_NOT_COVERING_CAPTURE"
                continue
            ok.append(sid)
        if len(set(ok)) == 1:
            return ok[0], None
        if len(set(ok)) > 1:
            return None, "ALIAS_AMBIGUOUS"
        return None, reason

    def security(self, sym, capture_ts, cutoff_ts):
        s_cap, why = self._at(sym, capture_ts, cutoff_ts)
        if s_cap is None:
            return None, why
        s_cut, _ = self._at(sym, cutoff_ts, cutoff_ts)
        if s_cut != s_cap:
            return None, "SECURITY_IDENTITY_UNRESOLVED_AT_CUTOFF"
        return s_cap, None


def _present(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x)) and not pd.isna(x)


def _vc(s: pd.Series) -> dict:
    return dict((str(k), int(v)) for k, v in s.value_counts(dropna=False).sort_index().items())


# ---------------------------------------------------------------- episodes
SERIES_KEYS = ["iss", "metric", "kind", "period_end"]


def start_events(ok: pd.DataFrame) -> tuple:
    """Same-period consensus changes and their S/L episode-start flags (B4 definition, accepted)."""
    d = ok[(ok.observation_type == "average") & ok.value.notna() & ok.period_end.notna()].copy()
    d["kind"] = d.horizon_label_raw.str[-1]
    d = d.sort_values(SERIES_KEYS + ["spos", "clk", "observation_id"], kind="mergesort")
    d = d.drop_duplicates(SERIES_KEYS + ["spos"], keep="last")
    g = d.groupby(SERIES_KEYS, sort=True)
    d["prev"] = g.value.shift(1)
    d["first_spos"] = g.spos.transform("min")
    tol = 1e-9 * np.maximum(1.0, np.abs(d.prev.fillna(0.0)))
    chg = d.prev.notna() & (np.abs(d.value - d.prev) > tol)
    ev = d[chg].copy()
    ev["direction"] = np.where(ev.value > ev.prev, "UP", "DOWN")
    ev["prev_ev"] = ev.groupby(SERIES_KEYS, sort=True).spos.shift(1)
    first_change = ev.prev_ev.isna()
    gap_ok = ev.prev_ev.notna() & (ev.spos - ev.prev_ev > QUIET_GAP)
    ev["start_L"] = first_change | gap_ok
    ev["start_S"] = (first_change & (ev.spos - ev.first_spos > QUIET_GAP)) | gap_ok
    stats = dict(
        series=int(g.ngroups),
        series_session_points=int(len(d)),
        nonzero_same_period_changes=int(len(ev)),
        series_with_any_change=int(ev.groupby(SERIES_KEYS).ngroups) if len(ev) else 0,
    )
    return ev, stats


def clusters(st: pd.DataFrame) -> list:
    """Issuer overlap clustering: per issuer, chain start sessions <= QUIET_GAP apart.

    Returns [(issuer, anchor_spos, member_identity_count, anchor_ticker, anchor_direction)], sorted.
    The anchor is the earliest start session in the cluster; its ticker is the smallest ticker
    among the anchor-session starts; direction is UP, DOWN or MIXED over the anchor-session starts.
    """
    out = []
    for iss, g in st.groupby("iss", sort=True):
        ss = sorted(set(int(x) for x in g.spos))
        groups, cur = [], [ss[0]]
        for a, b in zip(ss, ss[1:]):
            if b - a > QUIET_GAP:
                groups.append(cur)
                cur = [b]
            else:
                cur.append(b)
        groups.append(cur)
        for grp in groups:
            anchor = grp[0]
            members = g[g.spos.isin(grp)]
            at_anchor = g[g.spos == anchor]
            dirs = sorted(set(at_anchor.direction))
            out.append((iss, anchor, int(len(members)), str(min(at_anchor.ticker_compat)),
                        dirs[0] if len(dirs) == 1 else "MIXED"))
    return out


def _scope_rows(st: pd.DataFrame, scope) -> pd.DataFrame:
    if scope is None:
        return st
    col, val = scope
    return st[st.metric == val] if col == "metric" else st[st.horizon_label_raw == val]


def _scope_name(scope) -> str:
    return "overall" if scope is None else scope[0] + "=" + scope[1]


def effect_summary(vals: list, dirs: list) -> dict:
    a = np.array(vals, dtype=float)
    out = dict(
        statistic="owner residual log return over the window (LSR_P0_CUM_LOG1P_RESIDUAL_DELTA)",
        n=int(len(a)),
        mean=round(float(a.mean()), 8),
        median=round(float(np.median(a)), 8),
        sd=round(float(a.std(ddof=1)), 8) if len(a) > 1 else None,
        share_positive=round(float((a > 0).mean()), 6),
        by_anchor_direction=dict(),
    )
    for k in ("UP", "DOWN", "MIXED"):
        sel = a[[x == k for x in dirs]] if len(a) else a
        out["by_anchor_direction"][k] = dict(
            n=int(len(sel)),
            mean=round(float(sel.mean()), 8) if len(sel) else None,
        )
    return out


# ---------------------------------------------------------------- MKT-1 (owner-native residual)
def store_manifest(store: Path) -> dict:
    """sha256 over sorted (relpath, size, sha256) of every regular file in the snapshot."""
    h = hashlib.sha256()
    files, total = 0, 0
    for p in sorted(x for x in store.rglob("*") if x.is_file()):
        b = p.read_bytes()
        rel = p.relative_to(store).as_posix()
        h.update((rel + "\t" + str(len(b)) + "\t" + _sha256(b) + "\n").encode())
        files += 1
        total += len(b)
    return dict(manifest_sha256=h.hexdigest(), files=files, bytes=total)


def path_a_assessment(latest_raw: bytes, blob: str) -> dict:
    doc = json.loads(latest_raw)
    frame_keys = sorted(k for k in doc if k in ("cum", "residual_frame", "resid", "residuals", "panel"))
    events = len(doc.get("open_events") or []) + len(doc.get("recently_resolved") or [])
    return dict(
        artifact=PATHS["price_pressure_latest"],
        blob=blob,
        schema=doc.get("schema"),
        generated_at=doc.get("generated_utc"),
        last_session=doc.get("asof"),
        per_name_per_session_residual_frame=bool(frame_keys),
        shock_event_rows=events,
        decision="PATH_A_USABLE" if frame_keys else "PATH_A_UNAVAILABLE_NO_PER_NAME_RESIDUAL_FRAME",
    )


def owner_state(repo: Path, store: Path, sectors_raw: bytes, workdir: Path):
    """Owner panel + derive over the read-only snapshot, sliced to sessions <= the last pre-boundary session."""
    sys.path.insert(0, str(repo))
    from engine.price_pressure import detect as _detect  # noqa: E402 - owner seam
    from engine.price_pressure import panel as _panel  # noqa: E402
    from engine.price_pressure import response_export as _rx  # noqa: E402

    cache = workdir / "panel_cache"
    data_dir = workdir / "owner_inputs"
    (data_dir / "breadth").mkdir(parents=True, exist_ok=True)
    (data_dir / "breadth" / "ticker_sectors.parquet").write_bytes(sectors_raw)
    pan = _panel.load_panel(cache, store)
    raw_last = pd.Timestamp(pan["close"].index.max()).date()
    cut = pd.Timestamp(LAST_PRE_BOUNDARY_SESSION)
    sliced = dict((k, v[v.index <= cut]) for k, v in pan.items())
    d = _detect.derive_frames(sliced, data_dir)
    sessions = [pd.Timestamp(x).date() for x in d["sessions"]]
    info = dict(
        seam="engine.price_pressure.panel.load_panel -> engine.price_pressure.detect.derive_frames -> "
             "engine.price_pressure.response_export.export_market_response",
        response_schema=_rx.SCHEMA,
        response_model=_rx.RESPONSE_MODEL,
        panel_names=int(pan["close"].shape[1]),
        store_last_bar_session=str(raw_last),
        post_boundary_bars_in_store=bool(raw_last >= BOUNDARY.date()),
        frame_first_session=str(sessions[0]) if sessions else None,
        frame_last_session=str(sessions[-1]) if sessions else None,
        sliced_to=str(LAST_PRE_BOUNDARY_SESSION),
    )
    return d, sessions, _rx, info


# ---------------------------------------------------------------- build
def _ts(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, format="ISO8601")


def build(repo: Path, rev: str, store, snapshot_receipt, workdir: Path) -> dict:
    repo = Path(repo).resolve()
    rev_full = _git(repo, "rev-parse", rev + "^{commit}").decode().strip()
    shallow = _git(repo, "rev-parse", "--is-shallow-repository").decode().strip() == "true"
    blobs = dict((k, _blob_id(repo, rev_full, p)) for k, p in PATHS.items())
    raw = dict((k, _blob(repo, blobs[k])) for k in PATHS if k != "security_master")

    cal = hand_calendar()
    closes = pd.DatetimeIndex([session_close(d) for d in cal])
    last_pos = cal.index(LAST_PRE_BOUNDARY_SESSION)

    # corpus + clocks
    o = pd.read_parquet(io.BytesIO(raw["observations"]))
    att = pd.read_parquet(io.BytesIO(raw["attempts"]))
    o["clk"] = pd.concat([_ts(o.system_observed_at), _ts(o.provider_observed_at)], axis=1).max(axis=1)
    pos = closes.searchsorted(pd.DatetimeIndex(o.clk), side="left")
    drop = pd.Series(None, index=o.index, dtype=object)
    drop[o.clk < session_close(cal[0]) - pd.Timedelta(days=1)] = "CLOCK_BEFORE_CALENDAR_START"
    drop[o.clk >= BOUNDARY] = "CLOCK_AT_OR_AFTER_BOUNDARY"
    drop[(pos >= len(cal)) & drop.isna()] = "CUTOFF_AT_OR_AFTER_BOUNDARY"
    keep = drop.isna().values
    corpus = dict(
        observations_rows=int(len(o)),
        attempts_rows=int(len(att)),
        attempts_status=_vc(att.status),
        rows_dropped_by_boundary_rule=_vc(drop[~keep]),
        max_system_observed_at=str(_ts(o.system_observed_at).max()),
        max_provider_observed_at=str(_ts(o.provider_observed_at).max()),
        max_attempt_attempted_at=str(_ts(att.attempted_at).max()),
        max_attempt_completed_at=str(_ts(att.completed_at).max()),
        issuer_ref_nonnull_rows=int(o.issuer_ref.notna().sum()),
        security_ref_nonnull_rows=int(o.security_ref.notna().sum()),
    )
    o = o[keep].copy()
    o["spos"] = pos[keep]
    o["cutoff_ts"] = closes[o.spos.values]
    o["cutoff_session"] = [cal[i] for i in o.spos]
    corpus["max_decision_cutoff"] = str(o.cutoff_ts.max())
    corpus["cutoff_sessions"] = _vc(pd.Series([str(x) for x in o.cutoff_session]))

    # security axis (alias rule as data)
    va = pd.read_parquet(io.BytesIO(raw["vendor_aliases"]))
    alias = AliasRule(va)
    kj = ["ticker_compat", "clk", "cutoff_ts"]
    tick = o[kj].drop_duplicates().sort_values(kj, kind="mergesort")
    res = [alias.security(t, c, k) for t, c, k in zip(tick.ticker_compat, tick.clk, tick.cutoff_ts)]
    tick = tick.assign(security_id=[a for a, _ in res], alias_reason=[b for _, b in res])
    o = o.join(tick.set_index(kj), on=kj)

    # issuer axis (DEC known-version clock)
    clock = KnownVersionClock(repo, rev_full)
    key = o.loc[o.security_id.notna(), ["security_id", "cutoff_ts"]].drop_duplicates()
    key = key.sort_values(["security_id", "cutoff_ts"], kind="mergesort")
    vals = [clock.issuer_at(s, c) for s, c in zip(key.security_id, key.cutoff_ts)]
    key = key.assign(iss=[a for a, _, _ in vals], issuer_reason=[b for _, b, _ in vals])
    o = o.join(key.set_index(["security_id", "cutoff_ts"]), on=["security_id", "cutoff_ts"])
    reason = o.alias_reason.where(o.alias_reason.notna(), o.issuer_reason)
    versions_used = dict()
    for cs in sorted(set(o.cutoff_session)):
        v = clock.version_for(session_close(cs))
        versions_used[str(cs)] = None if v is None else dict(commit=v[0], committer_time=str(v[1]), blob=v[2])
    identity = dict(
        alias_rule="yahoo; ingested_at <= min(capture, cutoff); valid_from <= capture date < valid_to; "
                   "security at capture == security at cutoff",
        alias_source_blob=blobs["vendor_aliases"],
        yahoo_alias_rows=alias.yahoo_rows,
        issuer_clock="REPO_HISTORY_AVAILABILITY",
        issuer_rule="DEC:ITP-R4-ISSUER-AXIS-AS-KNOWN-VERSION-CLOCK-2026-10-07",
        known_version_guard_hours=24,
        security_master_tip_blob=blobs["security_master"],
        security_master_versions_visible=len(clock.versions),
        security_master_first_visible=[clock.versions[-1][0], str(clock.versions[-1][1])] if clock.versions else None,
        clone_is_shallow=shallow,
        known_version_by_cutoff_session=versions_used,
        rows_in_scope=int(len(o)),
        rows_issuer_formed=int(o.iss.notna().sum()),
        rows_excluded_by_reason=_vc(reason[o.iss.isna()]),
        distinct_issuers=int(o.iss.nunique()),
        distinct_tickers_issuer_formed=int(o[o.iss.notna()].ticker_compat.nunique()),
    )
    ok = o[o.iss.notna()].copy()
    ev, ep_stats = start_events(ok)
    return dict(rev=rev_full, blobs=blobs, raw=raw, cal=cal, last_pos=last_pos, corpus=corpus,
                identity=identity, ev=ev, ep_stats=ep_stats)


def cells(core: dict, mkt) -> list:
    """One row per (variant, h, scope). mkt is (owner_state, sessions, rx) or None."""
    ev, cal, last_pos = core["ev"], core["cal"], core["last_pos"]
    rows, cache = [], dict()
    for variant, role in (("S", "PRIMARY"), ("L", "SENSITIVITY_VIOLATES_20_QUIET_SESSION_LAW")):
        st = ev[ev["start_" + variant]]
        for scope in (None,) + SUBGROUPS:
            sub = _scope_rows(st, scope)
            cl = clusters(sub) if len(sub) else []
            anchors = _vc(pd.Series([str(cal[c[1]]) for c in cl], dtype=object)) if cl else dict()
            for h in HORIZONS:
                complete = [c for c in cl if c[1] + h <= last_pos]
                floor = FLOOR_OVERALL if scope is None else FLOOR_SUBGROUP
                avail, dirs, refusals = [], [], dict()
                for iss, anchor, _m, ticker, direction in complete:
                    k = (ticker, anchor, h)
                    if k not in cache:
                        if mkt is None:
                            cache[k] = (None, "OWNER_RESIDUAL_FRAME_NOT_RUN")
                        else:
                            r = mkt[2].export_market_response(
                                mkt[0], ticker=ticker, start_session=str(cal[anchor]),
                                end_session=str(cal[anchor + h]))
                            rr = r["residual_response"]
                            if rr["state"] == "AVAILABLE_UNQUALIFIED":
                                cache[k] = (rr["log_residual"], None)
                            else:
                                cache[k] = (None, "+".join(sorted(set(rr["reasons"]))) or "UNAVAILABLE")
                    val, why = cache[k]
                    if why is None:
                        avail.append(val)
                        dirs.append(direction)
                    else:
                        refusals[why] = refusals.get(why, 0) + 1
                n_complete, n_avail = len(complete), len(avail)
                meets = variant == "S" and n_avail >= floor
                if variant != "S":
                    status = "NOT_ESTIMATED_SENSITIVITY_COUNTS_ONLY"
                elif meets:
                    status = "ESTIMATED_DESCRIPTIVE"
                else:
                    status = "NOT_ESTIMATED_BELOW_FLOOR"
                row = dict(
                    variant=variant,
                    role=role,
                    h=h,
                    scope=_scope_name(scope),
                    floor=floor,
                    episode_identities=int(len(sub)),
                    effective_n=int(len(cl)),
                    anchor_sessions=anchors,
                    complete=n_complete,
                    right_censored_at_boundary=int(len(cl) - n_complete),
                    complete_residual_available=n_avail,
                    residual_unavailable_by_reason=dict(sorted(refusals.items())),
                    complete_meets_floor=bool(n_complete >= floor),
                    meets_floor=bool(meets),
                    shortfall_vs_floor=int(max(0, floor - n_avail)),
                    effect_status=status,
                    labels=dict(LABELS),
                )
                if status == "ESTIMATED_DESCRIPTIVE":
                    row["effect"] = effect_summary(avail, dirs)
                rows.append(row)
    return rows


def verdict(rows: list, mkt_ok: bool, calendar_ok: bool) -> tuple:
    s = [r for r in rows if r["variant"] == "S"]
    if not calendar_ok:
        return "R4_BLOCKED_CALENDAR_MISMATCH", "hand NYSE calendar disagrees with the owner panel sessions"
    if not any(r["effective_n"] for r in s):
        return "R4_BLOCKED_NO_ISSUER_EPISODES", "no S issuer episodes formed before the boundary"
    by_h = dict()
    for r in s:
        by_h.setdefault(r["h"], []).append(r)
    complete_ok = [h for h, rs in sorted(by_h.items()) if all(r["complete_meets_floor"] for r in rs)]
    if complete_ok and not mkt_ok:
        return "R4_BLOCKED_NO_OWNER_RESIDUAL_FRAME", "COMPLETE counts meet the floor at h=%s but the owner residual frame is unavailable" % complete_ok
    admissible = [h for h, rs in sorted(by_h.items()) if all(r["meets_floor"] for r in rs)]
    if admissible:
        return "R4_ADMISSIBLE_DESCRIPTIVE", "S meets every floor with COMPLETE windows at h=%s" % admissible
    return "R4_INSUFFICIENT_N_PRE_BOUNDARY", "no horizon has S COMPLETE episodes with an owner residual at the floor overall and in every subgroup"


def shortfall_table(rows: list) -> list:
    out = []
    for r in rows:
        if r["variant"] != "S":
            continue
        out.append(dict(h=r["h"], scope=r["scope"], floor=r["floor"], effective_n=r["effective_n"],
                        complete=r["complete"], complete_residual_available=r["complete_residual_available"],
                        shortfall_vs_floor=r["shortfall_vs_floor"], meets_floor=r["meets_floor"]))
    return out


def assemble(repo: Path, rev: str, store, snapshot_receipt, workdir: Path) -> dict:
    core = build(repo, rev, store, snapshot_receipt, workdir)
    path_a = path_a_assessment(core["raw"]["price_pressure_latest"], core["blobs"]["price_pressure_latest"])
    mkt, mkt_info, snap = None, None, None
    calendar_ok = True
    if store is not None:
        snap = json.loads(Path(snapshot_receipt).read_text()) if snapshot_receipt else dict()
        man = store_manifest(Path(store))
        if snap.get("manifest_sha256") and snap["manifest_sha256"] != man["manifest_sha256"]:
            raise SystemExit("snapshot manifest sha256 does not match its receipt")
        d, sessions, rx, mkt_info = owner_state(repo, Path(store), core["raw"]["ticker_sectors"], workdir)
        mkt = (d, sessions, rx)
        span = [s for s in sessions if CALENDAR_START <= s <= LAST_PRE_BOUNDARY_SESSION]
        hand = [s for s in core["cal"] if sessions and s >= sessions[0]]
        calendar_ok = span == hand
        mkt_info["calendar_cross_check"] = dict(
            hand_sessions=len(hand), owner_sessions=len(span), equal=calendar_ok,
            only_hand=[str(x) for x in sorted(set(hand) - set(span))],
            only_owner=[str(x) for x in sorted(set(span) - set(hand))],
        )
        mkt_info["snapshot"] = dict(snap, recomputed=man)
    rows = cells(core, mkt)
    v, why = verdict(rows, mkt is not None, calendar_ok)
    doc = dict(
        schema=SCHEMA,
        receipt_id=RECEIPT_ID,
        question="Given the corpus available before the EVAL-1 boundary, which R4 cells reach the preregistered N floor?",
        verdict=v,
        verdict_reason=why,
        verdict_enum=list(VERDICTS),
        verdict_rule="ADMISSIBLE only if, at some h, the S overall cell reaches 100 and every one of the six subgroup "
                     "cells reaches 25, counting COMPLETE windows that carry an owner residual",
        labels=dict(LABELS),
        not_promotion_bearing=True,
        boundary=dict(eval1_boundary=str(BOUNDARY), last_pre_boundary_session=str(LAST_PRE_BOUNDARY_SESSION),
                      holdout_end=HOLDOUT_END, rule="no bar on or after 2026-10-07; every clock strictly before the boundary"),
        source=dict(repository="mastermindx-market-intelligence/macro", revision=core["rev"], blobs=core["blobs"]),
        corpus=core["corpus"],
        identity=core["identity"],
        episode_law=dict(
            effective_n="distinct issuer episodes after issuer overlap clustering (starts <= 20 sessions apart chain)",
            identity="issuer + metric + horizon/fiscal period (q|y, period_end) + episode-start NYSE session",
            primary_variant="S: a start needs an observed 20-session quiet (first observed change only after > 20 "
                            "observed sessions of the series, or a gap > 20 sessions since the previous change)",
            sensitivity_variant="L: left-censored first changes count; violates the preregistered 20-quiet-session law",
            cutoff="NYSE close at or after max(system_observed_at, provider_observed_at); label starts strictly after it",
            anchor="cluster anchor = earliest start session; residual ticker = smallest ticker among anchor-session starts",
            quiet_gap_sessions=QUIET_GAP,
            floors=dict(overall=FLOOR_OVERALL, per_subgroup=FLOOR_SUBGROUP),
            subgroups=[a + "=" + b for a, b in SUBGROUPS],
            horizons_sessions=list(HORIZONS),
            series_stats=core["ep_stats"],
        ),
        calendar=dict(kind="hand NYSE calendar, weekdays minus holidays, close 20:00Z (EDT)",
                      start=str(CALENDAR_START), end=str(LAST_PRE_BOUNDARY_SESSION),
                      holidays=[str(x) for x in NYSE_HOLIDAYS], sessions=len(core["cal"])),
        mkt1=dict(
            frame="owner-native residual market response (T6)",
            path_a=path_a,
            path_used="b" if mkt is not None else "none",
            path_b=mkt_info,
            ticker_sectors_blob=core["blobs"]["ticker_sectors"],
            ticker_sectors_note="peer basis uses the ticker_sectors blob at the pinned revision (one version, not as-known); outcome side only",
        ),
        shortfall=shortfall_table(rows),
        cells=rows,
        v1_untouched=["R4_DRYRUN_RECEIPT_2026-10-06.json", "R4_DRYRUN_RECEIPT_2026-10-06.md", "r4_dryrun_receipt_check.py"],
        trial_consumption="NONE",
    )
    return _clean(doc)


def _clean(x):
    if isinstance(x, dict):
        return dict((str(k), _clean(v)) for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        f = float(x)
        return round(f, 10) if math.isfinite(f) else None
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def render_md(doc: dict, json_sha256: str) -> str:
    L = doc["labels"]
    m = doc["mkt1"]
    pb = m.get("path_b") or dict()
    out = [
        "# R4 dry-run receipt V2 (2026-10-07)",
        "",
        "Generated by `r4_v2_admission.py` from `R4_DRYRUN_RECEIPT_V2_2026-10-07.json` (sha256 `%s`)." % json_sha256,
        "Do not edit by hand.",
        "",
        "**Question.** %s" % doc["question"],
        "",
        "**Verdict: `%s`.** %s." % (doc["verdict"], doc["verdict_reason"]),
        "",
        "Rule: %s." % doc["verdict_rule"],
        "",
        "## Labels (header and every row)",
        "",
        "- era `%s` (%s); not promotion-bearing" % (L["era"], L["era_note"]),
        "- `%s`; coupling ceiling `%s`; rights `%s`" % (L["cohort_filter"], L["coupling_ceiling"], L["rights"]),
        "- financial_influence, k3e_admissible and promotion_eligible are all false; no score, no rank",
        "- issuer clock `%s` (DEC:ITP-R4-ISSUER-AXIS-AS-KNOWN-VERSION-CLOCK-2026-10-07)" % L["issuer_clock"],
        "",
        "## Source",
        "",
        "- origin/main revision `%s`" % doc["source"]["revision"],
    ]
    for k, v in sorted(doc["source"]["blobs"].items()):
        out.append("- `%s` blob `%s`" % (k, v))
    c = doc["corpus"]
    out += [
        "- EVAL-1 boundary %s; last pre-boundary session %s; no bar on or after 2026-10-07" % (
            doc["boundary"]["eval1_boundary"], doc["boundary"]["last_pre_boundary_session"]),
        "- max system clock %s; max provider clock %s; max decision cutoff %s" % (
            c["max_system_observed_at"], c["max_provider_observed_at"], c["max_decision_cutoff"]),
        "- max attempt clocks: attempted %s, completed %s" % (c["max_attempt_attempted_at"], c["max_attempt_completed_at"]),
        "",
        "## Identity",
        "",
    ]
    i = doc["identity"]
    out += [
        "- %d rows in scope; %d issuer-formed; %d issuers; %d tickers" % (
            i["rows_in_scope"], i["rows_issuer_formed"], i["distinct_issuers"], i["distinct_tickers_issuer_formed"]),
        "- excluded rows stay in the denominators: " + ", ".join("%s %d" % kv for kv in sorted(i["rows_excluded_by_reason"].items())),
        "- security_master versions visible: %d (clone shallow: %s)" % (i["security_master_versions_visible"], i["clone_is_shallow"]),
        "",
        "## MKT-1 frame",
        "",
        "- path (a) `%s` blob `%s`, generated %s, last session %s: %s" % (
            m["path_a"]["artifact"], m["path_a"]["blob"], m["path_a"]["generated_at"], m["path_a"]["last_session"], m["path_a"]["decision"]),
        "- path used: `%s`" % m["path_used"],
    ]
    if pb:
        snap = pb.get("snapshot") or dict()
        rec = snap.get("recomputed") or dict()
        out += [
            "- seam: %s" % pb["seam"],
            "- residual schema `%s`, model `%s`; frame %s to %s (sliced to %s); store last bar %s" % (
                pb["response_schema"], pb["response_model"], pb["frame_first_session"], pb["frame_last_session"],
                pb["sliced_to"], pb["store_last_bar_session"]),
            "- snapshot manifest sha256 `%s` (%s files, %s bytes)" % (rec.get("manifest_sha256"), rec.get("files"), rec.get("bytes")),
            "- calendar cross-check against owner sessions: equal=%s" % pb["calendar_cross_check"]["equal"],
        ]
    out += [
        "",
        "## Counts, variant S (PRIMARY)",
        "",
        "Every row carries the labels above. `avail` = COMPLETE windows with an owner residual.",
        "",
        "| h | scope | floor | episodes (eff. N) | COMPLETE | RIGHT_CENSORED_AT_BOUNDARY | avail | shortfall | effect |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in doc["cells"]:
        if r["variant"] != "S":
            continue
        eff = "estimated (n=%d, mean %.6f)" % (r["effect"]["n"], r["effect"]["mean"]) if "effect" in r else "not estimated"
        out.append("| %d | %s | %d | %d | %d | %d | %d | %d | %s |" % (
            r["h"], r["scope"], r["floor"], r["effective_n"], r["complete"], r["right_censored_at_boundary"],
            r["complete_residual_available"], r["shortfall_vs_floor"], eff))
    out += [
        "",
        "## Counts, variant L (SENSITIVITY; violates the 20-quiet-session law; counts only)",
        "",
        "| h | scope | episodes (eff. N) | COMPLETE | RIGHT_CENSORED_AT_BOUNDARY | avail |",
        "|---|---|---|---|---|---|",
    ]
    for r in doc["cells"]:
        if r["variant"] != "L":
            continue
        out.append("| %d | %s | %d | %d | %d | %d |" % (
            r["h"], r["scope"], r["effective_n"], r["complete"], r["right_censored_at_boundary"], r["complete_residual_available"]))
    out += [
        "",
        "## Scope",
        "",
        "Descriptive admission census only. No trial is consumed, nothing is written to data/ or site/, and the v1 "
        "receipt and its checker are untouched.",
        "",
    ]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--rev", required=True)
    ap.add_argument("--store", default=None, help="read-only snapshot of the owner's massive_stock_day store")
    ap.add_argument("--snapshot-receipt", default=None)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="r4v2_") as td:
        doc = assemble(Path(a.repo), a.rev, a.store, a.snapshot_receipt, Path(td))
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    body = (json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode()
    (out / (RECEIPT_ID + ".json")).write_bytes(body)
    (out / (RECEIPT_ID + ".md")).write_text(render_md(doc, _sha256(body)))
    print(doc["verdict"], _sha256(body))
    return 0


if __name__ == "__main__":
    sys.exit(main())
