"""Build the Expectation Surface page — the descriptive consensus layer of the
Information→Price programme (wave 1).

Reads the collected expectation ledger (data/revisions/expectation_observations.parquet
+ expectation_attempts.parquet, identity from data/reference/vendor_aliases.parquet)
and emits, under site/:

    site/expectation_surface/summary.json          schema expectation_surface.page.v1
    site/expectation_surface/tickers/index.json    [{ticker, sessions, latest_at, identity_status}]
    site/expectation_surface/tickers/<T>.json      per-ticker series
    site/expectation_surface.html                  rendered via templates/expectation_surface.html.j2

DESCRIPTIVE ONLY: financial_influence=false and k3e_admissible=false on every
emitted document. No rank, no gate, no position size, no trade, no capital
authority; no invented values — every number is computed from the parquet at
runtime. The builder never writes under data/, never touches the network, and
degrades to an honest OFFLINE page when the observations ledger is unreadable.

Contract: research/alpha_intelligence/expectation_market_dynamics/
EXPECTATION_SURFACE_PAGE_CONTRACT_2026-10-21.md

Run:  python -m scripts.build_expectation_surface
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config  # noqa: E402
from lib.pages import write_page, rendered_ticker_pages  # noqa: E402

log = logging.getLogger(__name__)

SCHEMA = "expectation_surface.page.v1"
OBSERVATIONS_PATH = "data/revisions/expectation_observations.parquet"
ATTEMPTS_PATH = "data/revisions/expectation_attempts.parquet"
ALIASES_PATH = "data/reference/vendor_aliases.parquet"

_TICKER_SAFE_RE = re.compile(r"[A-Z0-9.\-]{1,15}\Z")
_TOP_N_MOVERS = 25
# The movers shape is frozen at these two metrics even when the page is offline.
_OFFLINE_MOVERS_METRICS = ("EPS", "revenue")
# observation_type -> series field on a ticker-file point.
_POINT_FIELDS = {
    "average": "average",
    "median": "median",
    "high": "high",
    "low": "low",
    "covering_analyst_count": "analysts",
}
_KEY_COLS = ["ticker_compat", "metric", "horizon_label_raw"]
_OBS_REQUIRED = ["collection_session_id", "ticker_compat", "metric",
                 "horizon_label_raw", "period_end", "observation_type", "value",
                 "missingness_reason", "system_observed_at"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _round6(v) -> float | None:
    """Round to 6 dp; NaN/None -> null (json allow_nan=False stays honest)."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(v), 6)


def _try_read_parquet(path: Path, required: list[str]) -> tuple[pd.DataFrame | None, str | None]:
    """Read a parquet, degrading to (None, reason) instead of raising."""
    try:
        if not path.exists():
            return None, f"{path.as_posix()} missing"
        df = pd.read_parquet(path)
        missing = [c for c in required if c not in df.columns]
        if missing:
            return None, f"{path.as_posix()} missing columns: {', '.join(missing)}"
        return df, None
    except Exception as e:  # noqa: BLE001 — degrade, never break the build
        return None, f"{path.as_posix()} unreadable ({type(e).__name__}: {e})"


def _git_head(root: Path, reasons: list[str]) -> str | None:
    """`git rev-parse HEAD` with a 5 s timeout; null plus a reason on failure."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(root), capture_output=True,
            text=True, timeout=5, check=True,
        )
        head = (out.stdout or "").strip()
        return head or None
    except Exception as e:  # noqa: BLE001 — a missing repo must not break the page
        reasons.append(f"source_revision_unavailable: {type(e).__name__}")
        return None


def _blob_sha1(path: Path) -> str:
    """Git blob object id of the observations file, computed in-process."""
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


# ---------------------------------------------------------------------------
# Sessions and clocks (rule a)
# ---------------------------------------------------------------------------

def _session_clocks(obs: pd.DataFrame, attempts: pd.DataFrame | None,
                    reasons: list[str]) -> pd.DataFrame:
    """One row per OBSERVED collection session with its wall clock.

    Session universe = collection_session_ids present in the observations
    (attempt-only sessions produced no observations and must not move the
    latest/prior window). The clock is min(attempted_at) per session from the
    attempts ledger; when attempts is unusable it falls back to
    min(system_observed_at) and says so in reasons[].
    """
    obs_sids = set(obs["collection_session_id"].dropna().unique())
    if attempts is not None and len(attempts) and attempts["collection_session_id"].notna().any():
        clk_src = attempts.groupby("collection_session_id")["attempted_at"].min()
    else:
        clk_src = obs.groupby("collection_session_id")["system_observed_at"].min()
        reasons.append("attempts_unavailable: session clock from system_observed_at")
    clk = pd.DataFrame({"session_id": clk_src.index, "at_raw": clk_src.to_numpy()})
    clk = clk[clk["session_id"].isin(obs_sids)].copy()
    clk["at_dt"] = pd.to_datetime(clk["at_raw"], utc=True, format="ISO8601", errors="coerce")
    n_bad = int(clk["at_dt"].isna().sum())
    if n_bad:
        reasons.append(f"session_clock_unparseable: {n_bad} sessions dropped")
        clk = clk.dropna(subset=["at_dt"])
    clk = clk.sort_values(["at_dt", "session_id"], kind="mergesort").reset_index(drop=True)
    clk["at"] = clk["at_dt"].map(lambda ts: ts.isoformat().replace("+00:00", "Z"))
    return clk


# ---------------------------------------------------------------------------
# Valid average points and comparable pairs (rules b, c)
# ---------------------------------------------------------------------------

def _comparable_pairs(obs: pd.DataFrame, clk: pd.DataFrame,
                      exclusions: dict) -> pd.DataFrame:
    """Valid average points paired with the SAME key's previous valid point.

    A pair is comparable only when period_end is equal and non-null on both
    sides; anything else is a rollover — excluded and counted.
    """
    avg = obs[(obs["observation_type"] == "average")
              & obs["value"].notna()
              & obs["missingness_reason"].isna()]
    avg = avg.merge(clk[["session_id", "at_dt", "at"]],
                    left_on="collection_session_id", right_on="session_id", how="inner")
    avg = avg.sort_values(
        ["ticker_compat", "metric", "horizon_label_raw", "at_dt", "collection_session_id"],
        kind="mergesort").reset_index(drop=True)

    g = avg.groupby(_KEY_COLS, sort=False)
    pairs = avg.assign(
        prior_value=g["value"].shift(1),
        prior_period_end=g["period_end"].shift(1),
        prior_session_id=g["collection_session_id"].shift(1),
        prior_at=g["at"].shift(1),
    )
    pairs = pairs[pairs["prior_value"].notna()].copy()
    pe, ppe = pairs["period_end"], pairs["prior_period_end"]
    rollover = ~(pe.notna() & ppe.notna() & pe.eq(ppe))
    exclusions["rollover"] = int(rollover.sum())
    return pairs[~rollover].copy()


# ---------------------------------------------------------------------------
# Breadth (rule d) and movers (rule e)
# ---------------------------------------------------------------------------

def _breadth(comp: pd.DataFrame, clk: pd.DataFrame) -> list[dict]:
    """Per (session, metric) counts of comparable pairs by direction.

    up/down/flat compare each pair against tol = 1e-9 * max(1, |prior|).
    Sessions with no comparable pair are omitted; rows order by session clock
    then metric.
    """
    if comp.empty:
        return []
    delta = comp["value"] - comp["prior_value"]
    tol = 1e-9 * comp["prior_value"].abs().clip(lower=1.0)
    direction = pd.Series("flat", index=comp.index)
    direction[delta > tol] = "up"
    direction[delta < -tol] = "down"
    counts = (comp.assign(_dir=direction)
              .groupby(["session_id", "metric", "_dir"], sort=False).size()
              .unstack(fill_value=0))
    at_by_sid = dict(zip(clk["session_id"], clk["at"]))
    dt_by_sid = dict(zip(clk["session_id"], clk["at_dt"]))
    rows: list[dict] = []
    for (sid, metric), row in counts.iterrows():
        rows.append({
            "session_id": sid,
            "at": at_by_sid.get(sid),
            "metric": metric,
            "up": int(row.get("up", 0)),
            "down": int(row.get("down", 0)),
            "flat": int(row.get("flat", 0)),
        })
    rows.sort(key=lambda r: (dt_by_sid[r["session_id"]], r["metric"]))
    return rows


def _mover_items(cands: pd.DataFrame, cac_lookup: dict) -> list[dict]:
    items: list[dict] = []
    for row in cands.itertuples(index=False):
        pe = row.period_end
        items.append({
            "ticker": row.ticker_compat,
            "horizon": row.horizon_label_raw,
            "period_end": None if pd.isna(pe) else str(pe),
            "prior": _round6(row.prior_value),
            "latest": _round6(row.value),
            "pct_change": _round6(row.pct),
            "analysts": cac_lookup.get(
                (row.ticker_compat, row.metric, row.horizon_label_raw,
                 row.collection_session_id)),
            "prior_at": row.prior_at,
            "latest_at": row.at,
        })
    return items


def _movers(comp: pd.DataFrame, latest_sid: str, metrics: list[str],
            exclusions: dict, cac_lookup: dict) -> dict:
    """Latest-session movers per metric.

    Candidates are keys whose latest valid point sits in the latest session and
    which carry a comparable prior point (rule c). Rows with a zero prior are
    excluded and counted; rows with missingness never became valid points (rule
    b) and are counted once globally in exclusions.missingness by the caller.
    pct_change = (latest - prior) / |prior|; top 25 up descending, top 25 down
    ascending, ties broken by ticker then horizon.
    """
    movers: dict = {m: {"up": [], "down": []} for m in metrics}
    if comp.empty or latest_sid is None:
        return movers
    cands = comp[comp["collection_session_id"] == latest_sid]
    if cands.empty:
        return movers
    zero = cands["prior_value"] == 0
    exclusions["zero_prior"] = int(zero.sum())
    cands = cands[~zero].copy()
    cands["pct"] = (cands["value"] - cands["prior_value"]) / cands["prior_value"].abs()
    for metric in metrics:
        cm = cands[cands["metric"] == metric]
        up = cm[cm["pct"] > 0].sort_values(
            ["pct", "ticker_compat", "horizon_label_raw"],
            ascending=[False, True, True], kind="mergesort").head(_TOP_N_MOVERS)
        down = cm[cm["pct"] < 0].sort_values(
            ["pct", "ticker_compat", "horizon_label_raw"],
            ascending=[True, True, True], kind="mergesort").head(_TOP_N_MOVERS)
        movers[metric] = {"up": _mover_items(up, cac_lookup),
                          "down": _mover_items(down, cac_lookup)}
    return movers


# ---------------------------------------------------------------------------
# Identity (rule f), census (rule g), per-ticker series (rule i)
# ---------------------------------------------------------------------------

def _identity(obs: pd.DataFrame, aliases: pd.DataFrame | None,
              reasons: list[str]) -> tuple[dict, dict[str, str]]:
    """Identity counts + per-ticker status, computed at runtime from the
    vendor_aliases ledger (the probe's issuer-master join is NOT repeated).

    resolved  = tickers with a vendor=='store' row (vendor_symbol == ticker)
                carrying a non-null security_id
    undated   = resolved tickers with NO aliases row (any vendor, same
                vendor_symbol) carrying a non-null valid_from
    """
    universe = sorted(str(t) for t in obs["ticker_compat"].dropna().unique())
    if aliases is None:
        reasons.append("vendor_aliases_unavailable: identity_status set to unknown")
        status = {t: "unknown" for t in universe}
        return {"state": "COMPLETE_DEGRADED", "resolved": None, "unresolved": None,
                "undated_aliases": None}, status
    store_ok = set(aliases.loc[(aliases["vendor"] == "store")
                               & aliases["security_id"].notna(), "vendor_symbol"])
    dated = set(aliases.loc[aliases["valid_from"].notna(), "vendor_symbol"])
    resolved_t = {t for t in universe if t in store_ok}
    undated_t = {t for t in resolved_t if t not in dated}
    status = {}
    for t in universe:
        if t in resolved_t:
            status[t] = "resolved" if t in dated else "undated"
        else:
            status[t] = "unresolved"
    return ({"state": "COMPLETE_DEGRADED", "resolved": len(resolved_t),
             "unresolved": len(universe) - len(resolved_t),
             "undated_aliases": len(undated_t)}, status)


def _analyst_lookup(obs: pd.DataFrame) -> dict:
    """covering_analyst_count value per (ticker, metric, horizon, session)."""
    cac = obs[(obs["observation_type"] == "covering_analyst_count")
              & obs["value"].notna()]
    if cac.empty:
        return {}
    return {(str(t), str(m), str(h), str(s)): _round6(v)
            for t, m, h, s, v in zip(cac["ticker_compat"], cac["metric"],
                                     cac["horizon_label_raw"],
                                     cac["collection_session_id"], cac["value"])}


def _analysts_median(obs: pd.DataFrame, clk: pd.DataFrame) -> float | None:
    """Median covering_analyst_count at each key's latest session carrying one."""
    cac = obs[(obs["observation_type"] == "covering_analyst_count")
              & obs["value"].notna()]
    if cac.empty or clk.empty:
        return None
    cac = cac.merge(clk[["session_id", "at_dt"]], left_on="collection_session_id",
                    right_on="session_id", how="inner")
    if cac.empty:
        return None
    cac = cac.sort_values(_KEY_COLS + ["at_dt"], kind="mergesort")
    latest = cac.groupby(_KEY_COLS, sort=False).tail(1)
    if latest.empty:
        return None
    return _round6(latest["value"].median())


def _ticker_points(obs: pd.DataFrame, clk: pd.DataFrame) -> dict[str, dict[str, dict[str, list[dict]]]]:
    """Per ticker -> metric -> horizon -> points ordered by session clock.

    One point per (ticker, metric, horizon, session); average/median/high/low/
    analysts come from that session's observation_type rows, null when absent.
    """
    t = obs.merge(clk[["session_id", "at_dt", "at"]],
                  left_on="collection_session_id", right_on="session_id", how="inner")
    p = t[t["observation_type"].isin(_POINT_FIELDS)].copy()
    p["field"] = p["observation_type"].map(_POINT_FIELDS)
    p = p.drop_duplicates(subset=_KEY_COLS + ["collection_session_id", "field"], keep="last")
    wide = p.pivot(index=_KEY_COLS + ["collection_session_id"], columns="field",
                   values="value").reset_index()
    for field in ("average", "median", "high", "low", "analysts"):
        if field not in wide.columns:
            wide[field] = pd.NA
    # period_end for the point: first non-null within the key/session.
    pe = (t[t["period_end"].notna()]
          .sort_values("at_dt", kind="mergesort")
          .drop_duplicates(subset=_KEY_COLS + ["collection_session_id"], keep="first")
          [_KEY_COLS + ["collection_session_id", "period_end"]])
    base = t[_KEY_COLS + ["collection_session_id", "at_dt"]].drop_duplicates(
        subset=_KEY_COLS + ["collection_session_id"])
    pts = (wide.merge(base, on=_KEY_COLS + ["collection_session_id"])
           .merge(pe, on=_KEY_COLS + ["collection_session_id"], how="left")
           .merge(clk[["session_id", "at"]], left_on="collection_session_id",
                  right_on="session_id", how="left")
           .sort_values(["ticker_compat", "metric", "horizon_label_raw", "at_dt"],
                        kind="mergesort"))
    series: dict[str, dict[str, dict[str, list[dict]]]] = {}
    for row in pts.itertuples(index=False):
        point = {
            "at": row.at,
            "period_end": None if pd.isna(row.period_end) else str(row.period_end),
            "average": _round6(row.average),
            "median": _round6(row.median),
            "high": _round6(row.high),
            "low": _round6(row.low),
            "analysts": _round6(row.analysts),
        }
        (series.setdefault(row.ticker_compat, {})
         .setdefault(row.metric, {})
         .setdefault(row.horizon_label_raw, [])).append(point)
    return series


def _ticker_index(obs: pd.DataFrame, clk: pd.DataFrame,
                  status: dict[str, str]) -> list[dict]:
    """index.json rows: {ticker, sessions, latest_at, identity_status}, by ticker."""
    tk = (obs[["ticker_compat", "collection_session_id"]].drop_duplicates()
          .merge(clk[["session_id", "at_dt", "at"]],
                 left_on="collection_session_id", right_on="session_id", how="inner"))
    at_by_dt = dict(zip(clk["at_dt"], clk["at"]))
    entries: list[dict] = []
    for ticker, grp in tk.groupby("ticker_compat", sort=True):
        t = str(ticker)
        entries.append({
            "ticker": t,
            "sessions": int(grp["collection_session_id"].nunique()),
            "latest_at": at_by_dt.get(grp["at_dt"].max()),
            "identity_status": status.get(t, "unresolved"),
        })
    return entries


# ---------------------------------------------------------------------------
# Summary assembly (rules h–k)
# ---------------------------------------------------------------------------

def _offline_summary(root: Path, reasons: list[str]) -> dict:
    return {
        "schema": SCHEMA,
        "rendered_at": _now_iso(),
        "financial_influence": False,
        "k3e_admissible": False,
        "state": "OFFLINE",
        "reasons": reasons,
        "source": {
            "observations_path": OBSERVATIONS_PATH,
            "observations_blob_sha1": None,
            "source_revision": _git_head(root, reasons),
            "latest_session": None,
            "prior_session": None,
        },
        "identity": {"state": "COMPLETE_DEGRADED", "resolved": 0,
                     "unresolved": 0, "undated_aliases": 0},
        "census": {"observations": 0, "securities": 0, "metrics": [], "horizons": [],
                   "sessions": 0, "span": {"first": None, "last": None},
                   "analysts_median": None},
        "breadth": [],
        "movers": {m: {"up": [], "down": []} for m in _OFFLINE_MOVERS_METRICS},
        "exclusions": {"rollover": 0, "missingness": 0, "zero_prior": 0},
    }


def _census(obs: pd.DataFrame, clk: pd.DataFrame) -> dict:
    span_first = clk.iloc[0]["at"] if len(clk) else None
    span_last = clk.iloc[-1]["at"] if len(clk) else None
    return {
        "observations": int(len(obs)),
        "securities": int(obs["ticker_compat"].dropna().nunique()),
        "metrics": sorted(str(m) for m in obs["metric"].dropna().unique()),
        "horizons": sorted(str(h) for h in obs["horizon_label_raw"].dropna().unique()),
        "sessions": int(clk["session_id"].nunique()) if len(clk) else 0,
        "span": {"first": span_first, "last": span_last},
        "analysts_median": _analysts_median(obs, clk),
    }


def build(write: bool = True, root=None) -> dict:
    """Build the Expectation Surface summary (+ page and JSON when write=True).

    Returns the summary dict. Never writes under data/; all outputs land under
    <root>/site/. Degrades to an OFFLINE page when the observations ledger is
    missing or unreadable; only main()'s guard lets an unexpected error surface.
    """
    root = Path(root) if root is not None else config.ROOT
    reasons: list[str] = []

    obs, obs_err = _try_read_parquet(root / OBSERVATIONS_PATH, _OBS_REQUIRED)
    if obs is None:
        summary = _offline_summary(root, reasons + [f"observations_unavailable: {obs_err}"])
        index: list[dict] = []
        ticker_docs: list[tuple[str, dict]] = []
    else:
        attempts, _att_err = _try_read_parquet(
            root / ATTEMPTS_PATH, ["collection_session_id", "attempted_at"])
        aliases, _al_err = _try_read_parquet(
            root / ALIASES_PATH, ["vendor", "vendor_symbol", "security_id", "valid_from"])

        clk = _session_clocks(obs, attempts, reasons)
        exclusions = {"rollover": 0, "missingness": 0, "zero_prior": 0}
        # rows with missingness never enter anywhere (rule b); count the
        # average-typed ones that rule b filtered out.
        avg_rows = obs[obs["observation_type"] == "average"]
        exclusions["missingness"] = int(
            (avg_rows["missingness_reason"].notna() | avg_rows["value"].isna()).sum())

        metrics = sorted(str(m) for m in obs["metric"].dropna().unique())
        comp = _comparable_pairs(obs, clk, exclusions)
        breadth = _breadth(comp, clk)
        latest_sid = clk.iloc[-1]["session_id"] if len(clk) else None
        cac_lookup = _analyst_lookup(obs)
        movers = _movers(comp, latest_sid, metrics, exclusions, cac_lookup)
        identity, status = _identity(obs, aliases, reasons)

        sessions = [{"id": r.session_id, "at": r.at} for r in clk.itertuples(index=False)]
        summary = {
            "schema": SCHEMA,
            "rendered_at": _now_iso(),
            "financial_influence": False,
            "k3e_admissible": False,
            "state": "LIVE",
            "reasons": reasons,
            "source": {
                "observations_path": OBSERVATIONS_PATH,
                "observations_blob_sha1": _blob_sha1(root / OBSERVATIONS_PATH),
                "source_revision": _git_head(root, reasons),
                "latest_session": sessions[-1] if sessions else None,
                "prior_session": sessions[-2] if len(sessions) >= 2 else None,
            },
            "identity": identity,
            "census": _census(obs, clk),
            "breadth": breadth,
            "movers": movers,
            "exclusions": exclusions,
        }

        # Per-ticker JSON (rule i). Unsafe filenames are skipped with a count.
        series = _ticker_points(obs, clk)
        metrics_out = sorted(set(metrics) | set(_OFFLINE_MOVERS_METRICS))
        unsafe = [t for t in status if not _TICKER_SAFE_RE.match(t)]
        if unsafe:
            reasons.append(f"ticker_skipped_unsafe_filename: {len(unsafe)} tickers")
        index = _ticker_index(obs, clk, status)
        # company_page (wave 3a): set once per index entry from the tickers that
        # actually ship a stocks/<T>.html page, so the page link can never 404.
        pages = rendered_ticker_pages(root / "site")
        for entry in index:
            t = entry["ticker"]
            entry["company_page"] = f"stocks/{t}.html" if t in pages else None
        ticker_docs = []
        for entry in index:
            t = entry["ticker"]
            if not _TICKER_SAFE_RE.match(t):
                continue
            per_metric = series.get(t, {})
            ticker_docs.append((t, {
                "ticker": t,
                "identity_status": entry["identity_status"],
                "company_page": entry["company_page"],
                "financial_influence": False,
                "k3e_admissible": False,
                "series": {m: {h: per_metric.get(m, {}).get(h, [])
                               for h in sorted(per_metric.get(m, {}))}
                           for m in metrics_out},
            }))

    if write:
        _write_outputs(root, summary, index, ticker_docs)
    return summary


def _write_outputs(root: Path, summary: dict, index: list[dict],
                   ticker_docs: list[tuple[str, dict]]) -> None:
    """Write summary.json, tickers/index.json, tickers/<T>.json and the page.

    JSON: ensure_ascii=False, sort_keys=False, allow_nan=False (rule j). The
    page goes through lib.pages.write_page like every other builder.
    """
    site = root / "site"
    es_dir = site / "expectation_surface"
    tickers_dir = es_dir / "tickers"

    def _dump(obj) -> str:
        return json.dumps(obj, ensure_ascii=False, sort_keys=False, allow_nan=False)

    tickers_dir.mkdir(parents=True, exist_ok=True)
    (es_dir / "summary.json").write_text(_dump(summary), encoding="utf-8")
    (tickers_dir / "index.json").write_text(_dump(index), encoding="utf-8")
    for name, doc in ticker_docs:
        (tickers_dir / f"{name}.json").write_text(_dump(doc), encoding="utf-8")

    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(loader=FileSystemLoader(str(root / "templates")),
                      autoescape=select_autoescape(["html", "xml"]))
    html = env.get_template("expectation_surface.html.j2").render(
        summary=summary, mode="expectation_surface")
    write_page(site / "expectation_surface.html", html)
    log.info("built site/expectation_surface.html — state=%s securities=%s sessions=%s",
             summary.get("state"), summary.get("census", {}).get("securities"),
             summary.get("census", {}).get("sessions"))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        build(write=True)
        return 0
    except Exception as e:  # noqa: BLE001 — the standalone run reports, never raises
        log.error("build_expectation_surface failed: %s", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
