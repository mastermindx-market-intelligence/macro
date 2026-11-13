"""Typed read harness — descriptive tables by regime TYPE.

WHAT THIS IS
------------
A small, self-contained harness. Given

  1. a file of per-session regime TYPE labels and channel flags, and
  2. a list of catalogue turns (date, series, cluster id),

it prints

  OUTPUT 1 (default): a plain description by type value and by flag state —
      share of sessions, session count, turns on those sessions, distinct
      clusters — per era, plus the per-era unavailable share of each flag and
      the per-era core-U share, each against Addendum A's 40% line.

  OUTPUT 2 (guarded, per leg): for one boolean daily alert series, the catch
      share of clusters within [-21,+5] sessions of a top turn (alert shifted
      t+1) and the false-call rate per year of sessions, per type cell.

WHAT THIS IS NOT
----------------
* It defines no type. B/N/D/S/U, the reason codes and the six flag states are
  name strings taken from the Research Director's frozen spec; every value in
  the input is read as an opaque label, never recomputed, extended or invented.
* It applies no decision. Addendum A's 40% line is *reported*, never applied.
* It has been tested only on SYNTHETIC labels and SYNTHETIC turns. No real type
  file, no real turn file and no real leg series has been read by this module.
* It is paper-only research plumbing. It sizes, ranks and executes nothing.

INPUT FORMAT (see COLUMNS / TURN_COLUMNS / ALERT_COLUMNS below)
---------------------------------------------------------------
Column *names* are a single constant at the top of this file. If the RD's real
file spells a column differently, change the string on the right-hand side of
COLUMNS only; no logic below reads a literal column name.

  types  (CSV or parquet): date, core_label, core_reason,
          flag_rate, flag_real_rate, flag_credit, flag_credit_level,
          flag_dollar, flag_easing
    core_label          one of B N D S U (exclusive, one per session)
    core_reason         required for U: MISSING_INPUT | CONFLICTING_STRUCTURE |
                        ENTRY_CONFIRMATION; must be empty for B/N/D/S
    flag_*              present | absent | unavailable
                        (flag_easing may also be PRICE_STRESS_EASING_PARTIAL)

  turns  (CSV or parquet): date, series, cluster_id, and optionally kind
    kind, when present, defaults every row to a top turn only when the column
    is absent; when present only rows with kind == "top" are read.

  alerts (CSV or parquet, OUTPUT 2 only): date, alert   (boolean or 0/1)

Strictness: unknown label/state values, duplicate dates, a blank flag value, a
turn with no cluster id and a non-U label carrying a reason code all raise.
Any date on or after 2024-01-02 raises, anywhere.

GUARD (OUTPUT 2)
----------------
`per_leg_table` refuses to run unless it is called with `synthetic=True` or
with `ledger_path` + `row_id`, where that row exists in the JSONL ledger and
its JSON has `"typed_read_joint": true` and `"approved_by_rd": true`.
The flags are read from the row itself, or from the row's `primary_spec`
object — see `_ledger_flag`.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Column map — the ONLY place a column name appears. Adjust the values to the
# RD's real file; the logic below never reads a literal column name.
# --------------------------------------------------------------------------
COLUMNS = {
    "date": "date",
    "core_label": "core_label",
    "core_reason": "core_reason",
    "flag_rate": "flag_rate",
    "flag_real_rate": "flag_real_rate",
    "flag_credit": "flag_credit",
    "flag_credit_level": "flag_credit_level",
    "flag_dollar": "flag_dollar",
    "flag_easing": "flag_easing",
}
# The RD's type_history_v1.parquet (TYPE_HISTORY_FORMAT.md, format version 1). The date is the
# parquet index; `pub_label` is the label a read uses (never `raw_label`); `reason` is the
# published-U reason; the harness's `credit` flag is the RD's `credit_pressure`.
RD_V1_COLUMNS = {
    "date": "date",
    "core_label": "pub_label",
    "core_reason": "reason",
    "flag_rate": "flag_rate",
    "flag_real_rate": "flag_real_rate",
    "flag_credit": "flag_credit_pressure",
    "flag_credit_level": "flag_credit_level",
    "flag_dollar": "flag_dollar",
    "flag_easing": "flag_easing",
}
TURN_COLUMNS = {"date": "date", "series": "series", "cluster_id": "cluster_id",
                "kind": "kind"}          # "kind" is optional in the file
ALERT_COLUMNS = {"date": "date", "alert": "alert"}

# --------------------------------------------------------------------------
# Frozen names and constants (from the RD's frozen spec; this module defines
# nothing of its own and applies no decision).
# --------------------------------------------------------------------------
CORE_LABELS = ("B", "N", "D", "S", "U")
U_REASONS = ("MISSING_INPUT", "CONFLICTING_STRUCTURE", "ENTRY_CONFIRMATION")
FLAG_KEYS = ("rate", "real_rate", "credit", "credit_level", "dollar", "easing")
FLAG_COLUMNS = tuple("flag_" + k for k in FLAG_KEYS)
FLAG_STATES = ("present", "absent", "unavailable")
PRICE_STRESS_EASING_PARTIAL = "PRICE_STRESS_EASING_PARTIAL"
FLAG_STATES_BY_KEY = {
    k: FLAG_STATES + ((PRICE_STRESS_EASING_PARTIAL,) if k == "easing" else ())
    for k in FLAG_KEYS
}

MIN_CLUSTERS = 8            # cells with fewer distinct clusters: counts only
SESSIONS_PER_YEAR = 252     # denominator for "per year of sessions"
LAST_INPUT_DATE = pd.Timestamp("2024-01-02")   # exclusive: refuse >= this
COVERAGE_LINE = 0.40        # Addendum A §2: reported, never applied
CATCH_PRE = 21              # sessions before a turn
CATCH_POST = 5              # sessions after a turn
SHIFT_SESSIONS = 1          # decision at close t is used at t+1
REQUIRE_U_REASON = True     # see README "spec ambiguities"


@dataclass(frozen=True)
class Era:
    name: str
    start: pd.Timestamp
    end: pd.Timestamp


def era(name: str, start: str, end: str) -> Era:
    """Build an Era from date strings (inclusive bounds)."""
    return Era(name, pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize())


DEFAULT_ERAS = (
    era("PRE", "2006-01-03", "2019-12-31"),
    era("D", "2020-01-02", "2023-12-29"),
)


class TypedReadError(ValueError):
    """Input violates the declared format."""


class GuardRefusal(RuntimeError):
    """The per-leg read was not authorised."""


# --------------------------------------------------------------------------
# Reading and validation
# --------------------------------------------------------------------------
def _read_table(path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise TypedReadError(f"input not found: {p}")
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(p)
    if suffix in (".parquet", ".pq"):
        df = pd.read_parquet(p)
        if df.index.name is not None and df.index.name not in df.columns:
            df = df.reset_index()      # a dated index (the RD's file) becomes a column
        return df
    raise TypedReadError(f"unsupported input type (use .csv or .parquet): {p}")


def _parse_dates(values, what: str) -> pd.Series:
    if values.isna().any():
        raise TypedReadError(f"{what}: blank date value")
    try:
        d = pd.to_datetime(values, errors="raise")
    except (ValueError, TypeError) as exc:      # noqa: BLE001
        raise TypedReadError(f"{what}: unparseable date ({exc})") from exc
    if getattr(d.dt, "tz", None) is not None:
        d = d.dt.tz_localize(None)
    d = d.dt.normalize()
    if d.isna().any():
        raise TypedReadError(f"{what}: blank date value")
    return d


def _refuse_post_cutoff(dates: pd.Series, what: str) -> None:
    bad = dates >= LAST_INPUT_DATE
    if bad.any():
        sample = sorted({x.date().isoformat() for x in dates[bad]})[:5]
        raise TypedReadError(
            f"{what}: {int(bad.sum())} date(s) on or after "
            f"{LAST_INPUT_DATE.date()} are refused (sealed); first: {sample}")


def _require_columns(df: pd.DataFrame, mapping: dict, what: str) -> None:
    missing = [v for v in mapping.values() if v not in df.columns]
    if missing:
        raise TypedReadError(f"{what}: missing required column(s) {missing}")


def _as_text(s: pd.Series, what: str) -> pd.Series:
    out = s.astype("string").str.strip()
    if out.isna().any():
        raise TypedReadError(f"{what}: blank value(s) at rows "
                             f"{list(np.flatnonzero(out.isna().to_numpy()))[:5]}")
    return out


def _bad_values(series: pd.Series, allowed) -> list:
    uniq = sorted(set(series.tolist()) - set(allowed))
    return uniq


def validate_types(df: pd.DataFrame, columns: dict | None = None) -> pd.DataFrame:
    """Validate a types frame; return it with date as a sorted unique index.
    `columns` maps harness names to the file's names (default COLUMNS)."""
    cmap = COLUMNS if columns is None else columns
    _require_columns(df, cmap, "types")
    df = df[list(cmap.values())].rename(columns={v: k for k, v in cmap.items()})
    keep = ["date", "core_label", "core_reason", *FLAG_COLUMNS]
    df = df[keep].copy()

    df["date"] = _parse_dates(df["date"], "types")
    _refuse_post_cutoff(df["date"], "types")
    dup = df["date"].duplicated()
    if dup.any():
        sample = sorted({x.date().isoformat() for x in df.loc[dup, "date"]})[:5]
        raise TypedReadError(f"types: duplicate date(s) {sample}")

    df["core_label"] = _as_text(df["core_label"], "types.core_label")
    bad = _bad_values(df["core_label"], CORE_LABELS)
    if bad:
        raise TypedReadError(f"types.core_label: unknown label(s) {bad}; "
                             f"allowed {list(CORE_LABELS)}")

    reason_raw = df["core_reason"].astype("string").str.strip()
    reason_raw = reason_raw.fillna("")
    bad = _bad_values(reason_raw, ("", *U_REASONS))
    if bad:
        raise TypedReadError(f"types.core_reason: unknown reason code(s) {bad}; "
                             f"allowed {list(U_REASONS)} or empty")
    is_u = df["core_label"].eq("U")
    has_reason = reason_raw.ne("")
    if (has_reason & ~is_u).any():
        rows = list(np.flatnonzero((has_reason & ~is_u).to_numpy()))[:5]
        raise TypedReadError(
            f"types: non-U label carries a reason code at row(s) {rows}"
            f" ({sorted(set(df['core_label'][has_reason & ~is_u]))})")
    if REQUIRE_U_REASON and (is_u & ~has_reason).any():
        rows = list(np.flatnonzero((is_u & ~has_reason).to_numpy()))[:5]
        raise TypedReadError(f"types: U without a reason code at row(s) {rows}; "
                             f"set REQUIRE_U_REASON=False to relax")
    df["core_reason"] = reason_raw

    for col in FLAG_COLUMNS:
        key = col[5:]
        allowed = FLAG_STATES_BY_KEY[key]
        df[col] = _as_text(df[col], f"types.{col}")
        bad = _bad_values(df[col], allowed)
        if bad:
            raise TypedReadError(f"types.{col}: unknown state(s) {bad}; "
                                 f"allowed {list(allowed)}")

    out = df.set_index("date").sort_index()
    out.attrs["typed_read_validated"] = True
    return out


def load_types(path, columns: dict | None = None, expect_sha256: str | None = None) -> pd.DataFrame:
    """Load and validate a types file. With expect_sha256, refuse a file whose bytes differ."""
    if expect_sha256 is not None:
        import hashlib
        got = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if got != expect_sha256:
            raise TypedReadError(f"types file sha256 {got} differs from the pin {expect_sha256}")
    return validate_types(_read_table(path), columns)


def validate_turns(df: pd.DataFrame) -> pd.DataFrame:
    """Validate a turns frame; return date/series/cluster_id (and kind)."""
    need = {k: v for k, v in TURN_COLUMNS.items() if k != "kind"}
    _require_columns(df, need, "turns")
    df = df.rename(columns={v: k for k, v in TURN_COLUMNS.items() if v in df.columns})
    cols = ["date", "series", "cluster_id"] + (["kind"] if "kind" in df.columns else [])
    df = df[cols].copy()

    df["date"] = _parse_dates(df["date"], "turns")
    _refuse_post_cutoff(df["date"], "turns")
    df["series"] = _as_text(df["series"], "turns.series")
    df["cluster_id"] = _as_text(df["cluster_id"], "turns.cluster_id")
    if "kind" in df.columns:
        df["kind"] = _as_text(df["kind"], "turns.kind")
        unexpected = sorted(set(df["kind"].tolist()) - {"top", "bottom"})
        if unexpected:
            raise TypedReadError(f"turns.kind: unknown value(s) {unexpected}")
        df = df[df["kind"].eq("top")].copy()
    df = df.sort_values(["date", "series", "cluster_id"]).reset_index(drop=True)
    if df.empty:
        raise TypedReadError("turns: no top turns in the input")
    return df


def load_turns(path) -> pd.DataFrame:
    return validate_turns(_read_table(path))


def validate_alerts(df: pd.DataFrame) -> pd.Series:
    """Validate an alerts frame; return a sorted boolean Series indexed by date."""
    _require_columns(df, ALERT_COLUMNS, "alerts")
    df = df.rename(columns={v: k for k, v in ALERT_COLUMNS.items()})[["date", "alert"]]
    df["date"] = _parse_dates(df["date"], "alerts")
    _refuse_post_cutoff(df["date"], "alerts")
    dup = df["date"].duplicated()
    if dup.any():
        sample = sorted({x.date().isoformat() for x in df.loc[dup, "date"]})[:5]
        raise TypedReadError(f"alerts: duplicate date(s) {sample}")
    a = df["alert"]
    if pd.api.types.is_bool_dtype(a):
        vals = a.to_numpy(dtype=bool)
    else:
        num = pd.to_numeric(a, errors="coerce")
        if num.isna().any() or not num.isin([0, 1]).all():
            raise TypedReadError("alerts.alert: values must be boolean or 0/1")
        vals = num.to_numpy(dtype=bool)
    return pd.Series(vals, index=pd.DatetimeIndex(df["date"]), name="alert").sort_index()


def load_alerts(path) -> pd.Series:
    return validate_alerts(_read_table(path))


# --------------------------------------------------------------------------
# Eras
# --------------------------------------------------------------------------
def normalise_eras(eras=None) -> tuple:
    out = DEFAULT_ERAS if eras is None else tuple(eras)
    for e in out:
        if not isinstance(e, Era):
            raise TypedReadError(f"era entry is not an Era: {e!r}")
        if e.end < e.start:
            raise TypedReadError(f"era {e.name}: end {e.end.date()} < start {e.start.date()}")
        if e.end >= LAST_INPUT_DATE:
            raise TypedReadError(f"era {e.name}: end {e.end.date()} is on or after the "
                                 f"sealed cutoff {LAST_INPUT_DATE.date()}")
    names = [e.name for e in out]
    if len(set(names)) != len(names):
        raise TypedReadError(f"era names must be unique: {names}")
    return out


# --------------------------------------------------------------------------
# OUTPUT 1 — description by type value and by flag state
# --------------------------------------------------------------------------
def _ensure_types(types: pd.DataFrame) -> pd.DataFrame:
    """Accept either an already-validated frame or a raw one and validate it."""
    if types.attrs.get("typed_read_validated") is True:
        return types
    if types.index.name == "date":
        types = types.reset_index()
    return validate_types(types)


def _dimensions(types: pd.DataFrame) -> list:
    dims = [("core_label", types["core_label"], CORE_LABELS)]
    for key in FLAG_KEYS:
        col = "flag_" + key
        dims.append((col, types[col], FLAG_STATES_BY_KEY[key]))
    return dims


def describe(types: pd.DataFrame, turns: pd.DataFrame, eras=None) -> dict:
    """Descriptive cells per era × dimension × value. Applies no decision."""
    types = _ensure_types(types)
    eras = normalise_eras(eras)
    sessions = types.index
    n_sessions = {e.name: int(((sessions >= e.start) & (sessions <= e.end)).sum())
                  for e in eras}

    labelled = turns.merge(types.reset_index(), on="date", how="inner")
    # a turn whose date is not a labelled session is excluded from every cell
    unlabelled_turns = int(len(turns) - len(labelled))
    unlabelled_clusters = int(len(set(turns["cluster_id"]) - set(labelled["cluster_id"])))

    # RD FORMAT_RULINGS_001 #4: a cluster takes the published label and flags of its
    # EARLIEST turn's session; turns are still counted under their own session's label.
    first = labelled.sort_values("date").drop_duplicates("cluster_id", keep="first")
    multi_label = labelled.groupby("cluster_id")["core_label"].nunique()
    multi_label_ids = set(multi_label[multi_label > 1].index)

    cells = []
    multi = []
    for e in eras:
        in_era = (sessions >= e.start) & (sessions <= e.end)
        t_era = labelled[(labelled["date"] >= e.start) & (labelled["date"] <= e.end)]
        c_era = first[(first["date"] >= e.start) & (first["date"] <= e.end)]
        multi.append({"era": e.name, "clusters": int(len(c_era)),
                      "multi_core_label_clusters":
                          int(c_era["cluster_id"].isin(multi_label_ids).sum())})
        n_era = n_sessions[e.name]
        for dim_name, values, order in _dimensions(types):
            s_series = values[in_era]
            for val in order:
                n_sess = int(s_series.eq(val).sum())
                sel = t_era[t_era[dim_name].eq(val)]
                n_clusters = int(c_era[dim_name].eq(val).sum())
                cells.append({
                    "era": e.name,
                    "dimension": dim_name,
                    "value": val,
                    "sessions": n_sess,
                    "session_share": (n_sess / n_era) if n_era else None,
                    "turns": int(len(sel)),
                    "clusters": n_clusters,
                    "suppressed": n_clusters < MIN_CLUSTERS,
                })

    coverage = []
    for e in eras:
        in_era = (sessions >= e.start) & (sessions <= e.end)
        n_era = n_sessions[e.name]
        sub = types[in_era]
        u = sub["core_label"].eq("U")
        u_share = float(u.sum()) / n_era if n_era else None
        reasons = {r: int((sub.loc[u, "core_reason"] == r).sum()) for r in U_REASONS}
        flags = []
        for key in FLAG_KEYS:
            col = "flag_" + key
            unavailable = int(sub[col].eq("unavailable").sum())
            share = unavailable / n_era if n_era else None
            flags.append({"flag": key, "unavailable": unavailable,
                          "unavailable_share": share,
                          "within_line": (share is not None and share <= COVERAGE_LINE)})
        coverage.append({
            "era": e.name,
            "sessions": n_era,
            "u_sessions": int(u.sum()),
            "u_share": u_share,
            "u_share_within_line": (u_share is not None and u_share <= COVERAGE_LINE),
            "u_reasons": reasons,
            "flags": flags,
        })

    return {"eras": [{"name": e.name, "start": str(e.start.date()), "end": str(e.end.date())}
                     for e in eras],
            "sessions_total": int(len(types)),
            "turns_total": int(len(turns)),
            "unlabelled_turns": unlabelled_turns,
            "unlabelled_clusters": unlabelled_clusters,
            "coverage_line": COVERAGE_LINE,
            "min_clusters": MIN_CLUSTERS,
            "cells": cells,
            "multi_label_clusters": multi,
            "coverage": coverage}


def _pct(x) -> str:
    return "—" if x is None else f"{100.0 * x:.1f}%"


def render_output1(result: dict) -> str:
    """Render OUTPUT 1 as plain markdown tables."""
    L = []
    A = L.append
    A("# Typed read — description by type (descriptive only; no decision applied)")
    A("")
    A(f"Sessions: {result['sessions_total']}. Turns: {result['turns_total']} "
      f"({result['unlabelled_turns']} on unlabelled sessions, excluded from cells; "
      f"{result['unlabelled_clusters']} cluster(s) affected).")
    A(f"Cells with fewer than {result['min_clusters']} distinct clusters print counts "
      f"only — no share, no rate.")
    A("")
    for cov in result["coverage"]:
        A(f"## Era {cov['era']}")
        A("")
        A(f"- sessions: {cov['sessions']}")
        reasons = ", ".join(f"{k} {v}" for k, v in cov["u_reasons"].items())
        A(f"- core U share: {_pct(cov['u_share'])} ({cov['u_sessions']} sessions; "
          f"{reasons}) — ≤{_pct(result['coverage_line'])}: "
          f"{'yes' if cov['u_share_within_line'] else 'no'}")
        for f in cov["flags"]:
            A(f"- {f['flag']} unavailable share: {_pct(f['unavailable_share'])} "
              f"({f['unavailable']} sessions) — ≤{_pct(result['coverage_line'])}: "
              f"{'yes' if f['within_line'] else 'no'}")
        A("")
        for m in result.get("multi_label_clusters", []):
            if m["era"] == cov["era"]:
                A(f"- clusters (by earliest turn): {m['clusters']}; clusters whose turns carry "
                  f"more than one core label: {m['multi_core_label_clusters']} (description)")
        A("- easing PRICE_STRESS_EASING_PARTIAL counts as available for the line "
          "(FORMAT_RULINGS_001 #2); its share is its own row below")
        A("")
        A("| dimension | value | sessions | session share | turns (own session) | "
          "clusters (earliest turn) | cell note |")
        A("|---|---|---|---|---|---|---|")
        for c in result["cells"]:
            if c["era"] != cov["era"]:
                continue
            note = "counts only" if c["suppressed"] else ""
            share = "—" if c["suppressed"] else _pct(c["session_share"])
            A(f"| {c['dimension']} | {c['value']} | {c['sessions']} | {share} | "
              f"{c['turns']} | {c['clusters']} | {note} |")
        A("")
    return "\n".join(L)


# --------------------------------------------------------------------------
# GUARD for OUTPUT 2
# --------------------------------------------------------------------------
def _ledger_flag(row: dict, key: str) -> bool:
    """True when the row carries `key: true`, at top level or in primary_spec."""
    if row.get(key) is True:
        return True
    spec = row.get("primary_spec")
    return isinstance(spec, dict) and spec.get(key) is True


def check_guard(*, synthetic: bool = False, ledger_path=None, row_id=None) -> dict:
    """Authorise a per-leg read. Raises GuardRefusal otherwise."""
    if synthetic:
        return {"mode": "synthetic"}
    if ledger_path is None or row_id is None:
        raise GuardRefusal(
            "per-leg read refused: call with synthetic=True (synthetic data only) or "
            "with ledger_path + row_id of a ledger row carrying typed_read_joint=true "
            "and approved_by_rd=true")
    p = Path(ledger_path)
    if not p.exists():
        raise GuardRefusal(f"per-leg read refused: ledger not found: {p}")
    found = None
    with p.open() as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GuardRefusal(f"per-leg read refused: ledger line {n} is not JSON "
                                   f"({exc})") from exc
            if isinstance(row, dict) and row.get("id") == row_id:
                found = row
                break
    if found is None:
        raise GuardRefusal(f"per-leg read refused: ledger row {row_id!r} not found in {p}")
    missing = [k for k in ("typed_read_joint", "approved_by_rd") if not _ledger_flag(found, k)]
    if missing:
        raise GuardRefusal(f"per-leg read refused: ledger row {row_id!r} lacks "
                           f"{missing} == true")
    return {"mode": "ledger", "row_id": row_id}


# --------------------------------------------------------------------------
# OUTPUT 2 — per-leg catch and false calls by type cell
# --------------------------------------------------------------------------
def _catch_and_false(alerts: pd.Series, types: pd.DataFrame, turns: pd.DataFrame, *,
                     eras, pre: int, post: int) -> dict:
    cal = pd.DatetimeIndex(types.index)
    n = len(cal)

    # declared t+1 shift: the decision at close t is used at t+1. Alerts present in
    # the calendar; a session with no alert row (or a gap) reads as off.
    raw = np.zeros(n, dtype=bool)
    pos = cal.get_indexer(pd.DatetimeIndex(alerts.index))
    ok = pos >= 0
    raw[pos[ok]] = alerts.to_numpy(dtype=bool)[ok]
    used = np.zeros(n, dtype=bool)
    if n > 1:
        used[1:] = raw[:-1]
    prev = np.zeros(n, dtype=bool)
    prev[1:] = used[:-1]
    starts = used & ~prev
    prefix = np.concatenate([[0], np.cumsum(used.astype(np.int64))])

    def on_in(lo: int, hi: int) -> bool:
        lo = max(0, lo)
        hi = min(n - 1, hi)
        if lo > hi:
            return False
        return int(prefix[hi + 1] - prefix[lo]) > 0

    labels = types["core_label"].to_numpy()
    flags = {("flag_" + k): types["flag_" + k].to_numpy() for k in FLAG_KEYS}

    tpos = cal.get_indexer(pd.DatetimeIndex(turns["date"]))
    t_ok = tpos >= 0

    # a cluster's cell is the cell of its EARLIEST turn date (documented choice)
    cluster_first: dict[str, int] = {}
    cluster_positions: dict[str, list[int]] = {}
    for cid, p in zip(turns["cluster_id"].to_numpy()[t_ok], tpos[t_ok]):
        cid = str(cid)
        cluster_positions.setdefault(cid, []).append(int(p))
        if cid not in cluster_first or p < cluster_first[cid]:
            cluster_first[cid] = int(p)
    for cid in cluster_positions:
        cluster_positions[cid] = sorted(set(cluster_positions[cid]))

    caught = {cid: any(on_in(p - pre, p + post) for p in ps)
              for cid, ps in cluster_positions.items()}
    turn_positions = np.array(sorted({int(p) for p in tpos[t_ok]}), dtype=np.int64)

    def near_a_turn(s: int) -> bool:
        if turn_positions.size == 0:
            return False
        return bool(np.any((turn_positions >= s - pre) & (turn_positions <= s + post)))

    cells = []
    for e in eras:
        in_era = (cal >= e.start) & (cal <= e.end)
        n_era = int(in_era.sum())
        cluster_in_era = {cid: p for cid, p in cluster_first.items() if in_era[p]}
        start_positions = np.flatnonzero(starts & in_era)
        false_by_pos = {int(s): not near_a_turn(int(s)) for s in start_positions}

        dims = [("core_label", labels)] + [(f"flag_{k}", flags[f"flag_{k}"]) for k in FLAG_KEYS]
        for dim_name, arr in dims:
            order = CORE_LABELS if dim_name == "core_label" else \
                FLAG_STATES_BY_KEY[dim_name[5:]]
            for val in order:
                sess_mask = in_era & (arr == val)
                n_sess = int(sess_mask.sum())
                cids = [cid for cid, p in cluster_in_era.items() if arr[p] == val]
                n_clusters = len(cids)
                n_caught = sum(1 for cid in cids if caught[cid])
                false_calls = sum(1 for s, f in false_by_pos.items() if f and arr[s] == val)
                sess_years = n_sess / SESSIONS_PER_YEAR
                cells.append({
                    "era": e.name,
                    "dimension": dim_name,
                    "value": val,
                    "sessions": n_sess,
                    "clusters": n_clusters,
                    "caught": n_caught,
                    "catch_share": (n_caught / n_clusters) if n_clusters else None,
                    "false_calls": false_calls,
                    "false_per_session_year": (false_calls / sess_years) if sess_years else None,
                    "suppressed": n_clusters < MIN_CLUSTERS,
                })
        cells.append({"era": e.name, "dimension": "__era__", "value": "ALL",
                      "sessions": n_era,
                      "clusters": len(cluster_in_era),
                      "caught": sum(1 for cid in cluster_in_era if caught[cid]),
                      "catch_share": (sum(1 for cid in cluster_in_era if caught[cid])
                                      / len(cluster_in_era)) if cluster_in_era else None,
                      "false_calls": sum(1 for f in false_by_pos.values() if f),
                      "false_per_session_year": (
                          sum(1 for f in false_by_pos.values() if f) / (n_era / SESSIONS_PER_YEAR)
                          if n_era else None),
                      "suppressed": len(cluster_in_era) < MIN_CLUSTERS})

    return {"sessions": n, "clusters": len(cluster_positions),
            "catch_window": [-pre, post], "shift_sessions": SHIFT_SESSIONS,
            "cells": cells}


def per_leg_table(alerts, turns, types: pd.DataFrame, *,
                  synthetic: bool = False, ledger_path=None, row_id=None,
                  eras=None, pre: int = CATCH_PRE, post: int = CATCH_POST) -> dict:
    """OUTPUT 2. Guarded: synthetic data, or a ledger row authorising the join."""
    guard = check_guard(synthetic=synthetic, ledger_path=ledger_path, row_id=row_id)
    types = _ensure_types(types)
    eras = normalise_eras(eras)
    if isinstance(alerts, pd.DataFrame):
        alerts = validate_alerts(alerts)
    else:
        alerts = validate_alerts(pd.DataFrame({"date": alerts.index,
                                               "alert": alerts.to_numpy()}))
    turns = validate_turns(turns)
    res = _catch_and_false(alerts, types, turns, eras=eras, pre=pre, post=post)
    res["guard"] = guard
    res["definition"] = (
        "alert used at s = declared series at s-1 (t+1 shift); a cluster is caught when "
        f"any used-ON session lies in [{-pre},{post}] sessions of any of its turn dates; "
        "an ON-start (used-ON after used-OFF) is a false call when no turn date lies in "
        f"[{-pre},{post}] sessions of it; rate = false calls per {SESSIONS_PER_YEAR} "
        "sessions in the cell")
    return res


def render_output2(result: dict) -> str:
    L = []
    A = L.append
    A("# Typed read — per-leg catch and false calls by type "
      f"(guard: {result['guard']['mode']})")
    A("")
    A(f"Definition: {result['definition']}")
    A(f"Cells with fewer than {MIN_CLUSTERS} distinct clusters print counts only.")
    A("")
    A("| era | dimension | value | sessions | clusters | caught | catch share | "
      "false calls | false / session-yr | cell note |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for c in result["cells"]:
        note = "counts only" if c["suppressed"] else ""
        catch = "—" if c["suppressed"] or c["catch_share"] is None else f"{c['catch_share']:.3f}"
        rate = "—" if c["suppressed"] or c["false_per_session_year"] is None \
            else f"{c['false_per_session_year']:.2f}"
        A(f"| {c['era']} | {c['dimension']} | {c['value']} | {c['sessions']} | "
          f"{c['clusters']} | {c['caught']} | {catch} | {c['false_calls']} | {rate} | {note} |")
    return "\n".join(L)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _parse_era_arg(text: str) -> Era:
    try:
        name, bounds = text.split("=", 1)
        start, end = bounds.split(":", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "expected NAME=YYYY-MM-DD:YYYY-MM-DD") from exc
    return era(name, start, end)


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--types", required=True, help="types file (.csv/.parquet)")
    common.add_argument("--eras", action="append", type=_parse_era_arg, default=None,
                        metavar="NAME=START:END",
                        help="extra era in addition to the default PRE and D eras")
    common.add_argument("--rd-v1", action="store_true",
                        help="the types file is the RD's type_history_v1 (RD_V1_COLUMNS)")
    common.add_argument("--types-sha256", default=None,
                        help="refuse unless the types file has exactly this sha256")

    p = argparse.ArgumentParser(
        description="Typed read: descriptive tables by regime type. Defines no type; "
                    "applies no decision.")
    sub = p.add_subparsers(dest="cmd")
    d = sub.add_parser("describe", parents=[common],
                       help="OUTPUT 1 (default): description by type value and flag state")
    d.add_argument("--turns", required=True, help="turns file (.csv/.parquet)")
    d.add_argument("--json", action="store_true", help="emit JSON instead of tables")

    g = sub.add_parser("per-leg", parents=[common],
                       help="OUTPUT 2 (guarded): catch and false calls for one alert series")
    g.add_argument("--turns", required=True)
    g.add_argument("--alerts", required=True)
    g.add_argument("--synthetic", action="store_true",
                   help="assert the inputs are synthetic (the only unguarded path)")
    g.add_argument("--ledger", default=None, help="JSONL ledger path (with --row-id)")
    g.add_argument("--row-id", default=None)
    g.add_argument("--json", action="store_true")
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("-"):
        argv = ["describe", *argv]
    args = _build_parser().parse_args(argv)
    eras = tuple(DEFAULT_ERAS) + tuple(args.eras or ())
    types = load_types(args.types, RD_V1_COLUMNS if args.rd_v1 else None,
                       expect_sha256=args.types_sha256)
    if args.cmd == "describe":
        result = describe(types, load_turns(args.turns), eras=eras)
        print(json.dumps(result, indent=2) if args.json else render_output1(result))
        return 0
    try:
        result = per_leg_table(load_alerts(args.alerts), load_turns(args.turns), types,
                               synthetic=args.synthetic, ledger_path=args.ledger,
                               row_id=args.row_id, eras=eras)
    except GuardRefusal as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(json.dumps(result, indent=2) if args.json else render_output2(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
