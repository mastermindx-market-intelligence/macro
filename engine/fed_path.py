"""Fed policy path — the market-implied rate path vs the FOMC dot-plot.

ADDITIVE / leaf module — imports nothing from the scoring core, and nothing in the
scoring path imports it. It assembles a DISPLAY block (bonds.html + the latest.json
LLM-context vector) from three free, keyless feeds:

  • the FOMC dot-plot median (FRED FEDTARMD) — the Fed's own projected path,
  • the live target range (FRED DFEDTARU/DFEDTARL) — where policy is set today,
  • the ZQ/SR3 futures-implied path (collectors/rate_futures.py) — where the market
    prices the funds rate at 1/3/6/12 months out,

plus the curve primitives already in the frame (near-term forward spread, the
legacy TP10 curve heuristic, the us2y−funds rate-expectations proxy). The TP10
heuristic is context only and is not a matched-maturity expectations decomposition.

DISCIPLINE — display / context ONLY. The implied path LEVEL is a market PRICE, not a
forecast edge, and repricing is REACTIVE (the curve moves *after* data and the Fed,
it does not lead it). There is therefore NO scored leg and NO MRS entry — this only
enlarges the facts the read can cite. See research/DATA_SIGNAL_EXPANSION_2026.md #2.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

from lib import config, store

log = logging.getLogger(__name__)

_QUARTER = 0.25  # one 25bp move

# A strip older than this (calendar days before `asof`) is labelled stale in the
# source metadata — pinned by test to collectors.rate_futures.RateFuturesAdapter.
STRIP_STALE_AFTER_DAYS = 5

# --- implied_source_meta vocabulary (RIC D0, B0 freeze rates_command_basis.v1) -- #
_SOURCE_META_SCHEMA = "fed_path_source_meta.v1"
_KNOWN_PRICE_TYPES = {"settlement", "last_trade", "vendor_daily_close"}
_KNOWN_RIGHTS = {"public_official", "redistribution_limited", "display_only", "unknown"}
_PARTICIPANT_NOTE = ("participant appropriate-policy projection, not a committee "
                     "promise or probability")
_LEGACY_SOFR_NOTE = ("legacy implied_* values are a compounded-SOFR substitute, "
                     "not an EFFR/fed-funds path")
_SELECTED_BASIS = {"zq": "zq_effr_monthly_average", "sofr": "sr3_compounded_sofr",
                   "zq_front": "zq_front_effr_30d", None: None}
_SELECTED_IS_EFFR = {"zq": True, "zq_front": True, "sofr": False, None: None}


def _cfg() -> dict:
    return config.load().get("rate_futures", {}) or {}


def _r(v, nd: int = 2):
    return None if v is None or not np.isfinite(v) else round(float(v), nd)


def _last(s: pd.Series | None) -> float | None:
    if s is None:
        return None
    s = s.dropna()
    return float(s.iloc[-1]) if len(s) else None


def _interp_horizon(path_row: dict, horizons: list[int], h: float) -> float | None:
    """Linear-interpolate the implied rate at horizon `h` months from a path row
    keyed ``m{H}`` over the available horizons (e.g. {m1, m3, m6, m12})."""
    pts = [(hm, path_row.get(f"m{hm}")) for hm in horizons]
    pts = [(x, y) for x, y in pts if y is not None and np.isfinite(y)]
    if not pts:
        return None
    pts.sort()
    if h <= pts[0][0]:
        return pts[0][1]
    if h >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        if h <= pts[i][0]:
            x0, x1, y0, y1 = pts[i - 1][0], pts[i][0], pts[i - 1][1], pts[i][1]
            return y0 + (y1 - y0) * (h - x0) / (x1 - x0) if x1 != x0 else y1
    return pts[-1][1]


def _dots_by_year(dot_series: pd.Series | None, this_year: int) -> list[dict]:
    """Forward dot-plot medians keyed by projection year. FRED stamps each SEP
    projection at the year-end it projects, overwriting on each release, so the
    latest value per year IS the current dot path. Keeps years >= this year."""
    if dot_series is None:
        return []
    s = dot_series.dropna()
    if s.empty:
        return []
    by_year: dict[int, float] = {}
    for ts, v in s.items():
        by_year[pd.Timestamp(ts).year] = float(v)  # last write per year wins
    return [{"year": y, "median": round(by_year[y], 3)}
            for y in sorted(by_year) if y >= this_year]


def _lean(gap_bp: float | None) -> tuple[str, str]:
    if gap_bp is None:
        return ("—", "—")
    if abs(gap_bp) < 13:  # < ~half a 25bp move = essentially aligned
        return ("market ≈ the Fed", "市场与美联储基本一致")
    if gap_bp < 0:        # market prices a LOWER rate than the Fed projects
        return ("market more dovish than the Fed", "市场比美联储更鸽派")
    return ("market more hawkish than the Fed", "市场比美联储更鹰派")


def compute(*, asof, policy_rate, target_low, target_high, dot_series,
            zq_path_row, sofr_path_row, zq_front_implied,
            ntfs, curve_tp_adj, rate_exp_proxy, cfg=None,
            metadata=None, cutoff=None) -> dict | None:
    """PURE — assemble the policy-path display block from already-extracted inputs.

    `zq_path_row` / `sofr_path_row` are the latest implied-path rows (dicts keyed
    ``m{H}``) from collectors/rate_futures.py; `dot_series` is the raw FEDTARMD
    series. Returns None only when there is genuinely nothing to show.

    D0 provenance (additive): `metadata` (strip/dot provenance per §2.2 schema)
    adds ONE key `implied_source_meta`; `cutoff` (ISO date, day precision) treats
    any input whose evidence time is later than — or unknown at — the cutoff as
    ABSENT before the legacy logic runs, so no refused number can leak. With
    neither keyword the legacy dict comes back byte-identical, new key included
    never. The legacy output is untouched in every mode."""
    cfg = cfg if cfg is not None else _cfg()
    horizons = list(cfg.get("horizons_m", [1, 3, 6, 12]))
    asof_ts = pd.Timestamp(asof)

    want_meta = metadata is not None or cutoff is not None
    if cutoff is not None:
        # withhold pre-evidence inputs BEFORE the legacy logic: a refused strip
        # falls through selection exactly as if missing; refused dots vanish.
        zq_row_in, sofr_row_in, front_in, dots_in = (
            zq_path_row, sofr_path_row, zq_front_implied, dot_series)
        zq_path_row, sofr_path_row, zq_front_implied, dot_series = _apply_cutoff(
            metadata, cutoff, zq_path_row, sofr_path_row, zq_front_implied, dot_series)
    else:
        zq_row_in, sofr_row_in, front_in, dots_in = (
            zq_path_row, sofr_path_row, zq_front_implied, dot_series)

    tmid = None
    if target_low is not None and target_high is not None:
        tmid = round((target_low + target_high) / 2, 3)
    pol = policy_rate if policy_rate is not None else tmid

    # --- the market-implied path: prefer ZQ (fed funds), else SOFR; the ZQ front
    # implied rate (100 − ZQ=F) is the always-available near anchor.
    path_row, path_src, path_src_zh = None, None, None
    if zq_path_row and any(v is not None for v in zq_path_row.values()):
        path_row, path_src, path_src_zh = zq_path_row, "ZQ fed-funds futures", "ZQ 联邦基金期货"
    elif sofr_path_row and any(v is not None for v in sofr_path_row.values()):
        path_row, path_src, path_src_zh = sofr_path_row, "SR3 SOFR futures", "SR3 SOFR 期货"

    implied = {"now": _r(pol)}
    if path_row:
        for h in horizons:
            implied[f"m{h}"] = _r(path_row.get(f"m{h}"))
    elif zq_front_implied is not None:
        # degraded: only the ~1-month ZQ front is available (no dated strip)
        implied["m1"] = _r(zq_front_implied)
        path_src, path_src_zh = "ZQ front (30d) only", "仅 ZQ 近月 (30天)"

    m12 = implied.get("m12")
    m6 = implied.get("m6")
    implied_bp_12m = round((m12 - pol) * 100) if (m12 is not None and pol is not None) else None
    implied_cuts_12m = round((pol - m12) / _QUARTER) if (m12 is not None and pol is not None) else None
    implied_cuts_6m = round((pol - m6) / _QUARTER) if (m6 is not None and pol is not None) else None

    # --- the dot-plot path + the Fed-vs-market gap at the nearest projection horizon
    dots = _dots_by_year(dot_series, asof_ts.year)
    gap = None
    if dots and path_row:
        dot = dots[0]                                       # nearest forward year
        months = (dot["year"] - asof_ts.year) * 12 + (12 - asof_ts.month)
        months = max(1, months)
        if months <= max(horizons):                         # only compare within the strip
            mkt = _interp_horizon(path_row, horizons, months)
            if mkt is not None:
                gap_bp = round((mkt - dot["median"]) * 100)
                lean_en, lean_zh = _lean(gap_bp)
                gap = {
                    "horizon_label": f"end-{dot['year']}", "horizon_months": months,
                    "fed_dot": dot["median"], "market": _r(mkt), "gap_bp": gap_bp,
                    "lean_en": lean_en, "lean_zh": lean_zh,
                }

    # --- honest narrative -----------------------------------------------------
    cut_word = None
    if implied_cuts_12m is not None:
        n = implied_cuts_12m
        cut_word = (f"{n} cut{'s' if n != 1 else ''}" if n > 0
                    else f"{-n} hike{'s' if n != -1 else ''}" if n < 0 else "no change")
    head_en = head_zh = None
    if cut_word and pol is not None:
        head_en = f"Market prices ~{cut_word} over the next 12m (funds {pol:.2f}% → {m12:.2f}%)"
        head_zh = f"市场为未来12个月定价约{('降息' if implied_cuts_12m>0 else '加息' if implied_cuts_12m<0 else '不变')}{abs(implied_cuts_12m) if implied_cuts_12m else ''}次（基金利率 {pol:.2f}% → {m12:.2f}%）"
    elif pol is not None:
        head_en = f"Policy set at {pol:.2f}%"
        head_zh = f"政策利率设定于 {pol:.2f}%"

    read_en, read_zh = [], []
    if gap:
        read_en.append(f"At {gap['horizon_label']} the market implies {gap['market']:.2f}% vs the Fed's {gap['fed_dot']:.2f}% median dot ({gap['gap_bp']:+d}bp — {gap['lean_en']}).")
        read_zh.append(f"在{gap['horizon_label']}，市场隐含 {gap['market']:.2f}% 对比美联储 {gap['fed_dot']:.2f}% 的中位点（{gap['gap_bp']:+d}基点 — {gap['lean_zh']}）。")
    if ntfs is not None:
        ntfs_msg_en = ("The near-term forward spread is negative — the market prices cuts ~18m out"
                       if ntfs < 0 else "The near-term forward spread is positive — no cuts priced near-term")
        ntfs_msg_zh = ("近端远期利差为负——市场为约18个月后的降息定价" if ntfs < 0
                       else "近端远期利差为正——近端未为降息定价")
        read_en.append(f"{ntfs_msg_en} ({ntfs:+.2f}pp).")
        read_zh.append(f"{ntfs_msg_zh}（{ntfs:+.2f}个百分点）。")

    out = {
        "asof": str(asof_ts.date()),
        "built": datetime.now(timezone.utc).isoformat(),
        "policy_rate": _r(policy_rate), "target_low": _r(target_low),
        "target_high": _r(target_high), "target_mid": _r(tmid),
        "implied": implied, "implied_source_en": path_src, "implied_source_zh": path_src_zh,
        "implied_bp_12m": implied_bp_12m, "implied_cuts_12m": implied_cuts_12m,
        "implied_cuts_6m": implied_cuts_6m,
        "sofr_path": ({f"m{h}": _r(sofr_path_row.get(f"m{h}")) for h in horizons}
                      if sofr_path_row else None),
        "dots": dots, "gap": gap,
        "ntfs": _r(ntfs), "curve_tp_adj": _r(curve_tp_adj),
        "rate_exp_proxy": _r(rate_exp_proxy),
        "headline_en": head_en, "headline_zh": head_zh,
        "read_en": " ".join(read_en) or None, "read_zh": "".join(read_zh) or None,
        "note_en": ("Display / LLM-context only. The implied path is a market PRICE (the "
                    "futures-implied funds rate), not a forecast edge, and repricing is "
                    "REACTIVE — it moves after data and the Fed, it does not lead. Never "
                    "scored, never an MRS leg. ZQ/SR3 = keyless CME futures; dots = FRED "
                    "FEDTARMD (FOMC SEP median). Cite the CME/FRED."),
        "note_zh": ("仅供展示 / LLM 上下文。隐含路径是市场价格（期货隐含的基金利率），"
                    "并非预测优势，且重新定价是被动的——它在数据和美联储之后变动，并不领先。"
                    "从不评分，从不作为 MRS 项。ZQ/SR3=无需密钥的 CME 期货；点阵图=FRED FEDTARMD"
                    "（FOMC SEP 中位数）。请注明 CME/FRED。"),
    }
    # nothing worth showing?
    if (out["policy_rate"] is None and not dots and not path_row
            and zq_front_implied is None):
        return None
    if want_meta:
        out["implied_source_meta"] = _implied_source_meta(
            asof_ts, metadata, cutoff, zq_row_in, sofr_row_in, front_in, dots_in, out)
    return out


# --------------------------------------------------------------------------- #
# D0 provenance — cutoff admission + the implied_source_meta assembly. These are
# display-side only: they never alter a legacy value, and the rate_futures
# helpers are imported LAZILY so fed_path stays importable without yfinance.
# --------------------------------------------------------------------------- #
def _as_date(v):
    """Best-effort day-precision date, or None when unknown."""
    if isinstance(v, (datetime, date, pd.Timestamp)):
        return pd.Timestamp(v).date()
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _evidence_later(evidence, precision: str | None, cutoff) -> bool | None:
    """Is `evidence` STRICTLY later than `cutoff`?

    Compared at the coarser of the evidence precision and day: month precision
    compares year-month only, and an equal month is NOT later. None (unknown
    evidence time) means the caller must withhold, not refuse."""
    if evidence is None or str(evidence).strip() == "":
        return None
    if precision not in ("day", "month"):
        precision = "month" if len(str(evidence)) == 7 else "day"
    try:
        cparts = [int(x) for x in str(cutoff).split("-")]
        eparts = [int(x) for x in str(evidence).split("-")]
    except (TypeError, ValueError):
        return None
    if len(cparts) < 2 or len(eparts) < 2:
        return None
    if precision == "month" or len(eparts) == 2:
        return (eparts[0], eparts[1]) > (cparts[0], cparts[1])
    return (eparts[0], eparts[1], eparts[2]) > (cparts[0], cparts[1], cparts[2])


def _apply_cutoff(metadata, cutoff, zq_row, sofr_row, front, dot_series):
    """Null every input whose evidence time is later than, or unknown at, the
    cutoff, so the legacy logic treats it exactly as missing."""
    md = metadata if isinstance(metadata, dict) else {}

    def admissible(entry) -> bool:
        obs = entry.get("observation_date") if isinstance(entry, dict) else None
        return _evidence_later(obs, "day", cutoff) is False

    if not admissible(md.get("zq")):
        zq_row = None
    if not admissible(md.get("sofr")):
        sofr_row = None
    if not admissible(md.get("zq_front")):
        front = None
    dmd = md.get("dots")
    dev = dmd.get("release_date") if isinstance(dmd, dict) else None
    dprec = dmd.get("release_precision") if isinstance(dmd, dict) else None
    if _evidence_later(dev, dprec, cutoff) is not False:
        dot_series = None
    return zq_row, sofr_row, front, dot_series


def _selected_strip(out: dict) -> str | None:
    """The strip the legacy selection ACTUALLY used (post-cutoff)."""
    src = out.get("implied_source_en")
    return {"ZQ fed-funds futures": "zq", "SR3 SOFR futures": "sofr",
            "ZQ front (30d) only": "zq_front"}.get(src)


def _strip_value_state(row, obs_raw, cutoff, asof_ts):
    """(value_state, limitation-or-None, quality-flag-or-None) per §2.3 order:
    missing → refused/withheld (mode 3) → stale → present."""
    present_row = bool(row) and any(v is not None for v in row.values())
    if not present_row:
        return "missing", None, None
    if cutoff is not None:
        later = _evidence_later(obs_raw, "day", cutoff)
        if later is True:
            return "refused", "after_cutoff", None
        if later is None:
            return "withheld", "evidence_time_unknown", None
    obs = _as_date(obs_raw)
    if obs is not None and (asof_ts - pd.Timestamp(obs)).days > STRIP_STALE_AFTER_DAYS:
        return "stale", None, "stale"
    if obs is None:
        return "present", "observation_time_unknown", None
    return "present", None, None


def _strip_meta(basis_key: str, row, md_entry, asof_ts, cutoff, selected):
    """Per-strip provenance <S> — basis is ALWAYS this strip's own, its dates are
    ALWAYS its own, and an unknown contract identity is never filled."""
    from collectors import rate_futures as rf  # lazy — no yfinance needed to import
    root = "ZQ" if basis_key == "zq" else "SR3"
    basis = rf.STRIP_BASIS[root]
    md = md_entry if isinstance(md_entry, dict) else {}
    obs_raw = md.get("observation_date")
    obs = _as_date(obs_raw)

    state, lim, qflag = _strip_value_state(row, obs_raw, cutoff, asof_ts)
    limitations = [lim] if lim else []
    quality = [qflag] if qflag else []
    if basis_key == "sofr" and selected == "sofr":
        quality.append("fallback_strip")
    # a missing strip has nothing observed — never dress it in a metadata date
    obs_known = obs is not None and state != "missing"

    price_type = md.get("price_type")
    vintage = None
    if price_type == "settlement":
        vintage = obs_raw if obs_known else None
    elif price_type == "last_trade":
        limitations.append("last_trade_not_settlement")
    elif price_type == "vendor_daily_close":
        limitations.append("vendor_close_not_exchange_settlement")
    else:
        price_type = None
        limitations.append("price_type_unknown")

    rights = md.get("rights")
    if rights not in _KNOWN_RIGHTS:
        rights = "unknown"

    contracts = None
    raw_contracts = md.get("contracts")
    if raw_contracts is None:
        limitations.append("contract_reference_unknown")
    else:
        contracts = []
        for sym in raw_contracts:
            p = rf.parse_contract_symbol(str(sym))
            if p is None:
                contracts.append({"vendor_symbol": sym, "contract_code": None,
                                  "exchange_suffix": None, "listing_exchange": None,
                                  "reference_start": None, "reference_end": None,
                                  "centre_months": None})
                limitations.append("contract_reference_unknown")
                continue
            start, end = rf.contract_reference_period(
                p["year"], p["month"], basis["cadence"])
            centre = (None if not obs_known else
                      rf._months_diff(p["year"], p["month"], obs.year, obs.month)
                      + rf._CENTRE_OFFSET[basis["cadence"]])
            contracts.append({"vendor_symbol": p["vendor_symbol"],
                              "contract_code": p["contract_code"],
                              "exchange_suffix": p["exchange_suffix"],
                              "listing_exchange": p["listing_exchange"],
                              "reference_start": start, "reference_end": end,
                              "centre_months": centre})

    return {
        "source": f"rate_futures:{root}",
        "evidence_class": "market_implied_expectation",
        "rate_index": basis["rate_index"],
        "averaging_law": basis["averaging_law"],
        "target": basis["target"],
        "basket_or_index": basis["basket_or_index"],
        "vendor": md.get("vendor"),
        "price_type": price_type,
        "observation_time": obs_raw if obs_known else None,
        "observation_precision": "day" if obs_known else "unknown",
        "vintage": vintage,
        "rights": rights,
        "source_version": md.get("source_version"),
        "value_state": state,
        "quality": quality,
        "limitations": limitations,
        "contracts": contracts,
    }


def _front_meta(front, md_entry, asof_ts, cutoff):
    md = md_entry if isinstance(md_entry, dict) else {}
    obs_raw = md.get("observation_date")
    state, lim, _ = _strip_value_state(
        {"v": front} if front is not None else None, obs_raw, cutoff, asof_ts)
    limitations = [lim] if lim else []
    limitations.append("contract_reference_unknown")
    obs = _as_date(obs_raw)
    obs_known = obs is not None and state != "missing"
    return {
        "source": "zq_front_30d",
        "evidence_class": "market_implied_expectation",
        "rate_index": "EFFR",
        "averaging_law": "arithmetic_calendar_day",
        "reference_start": None,
        "reference_end": None,
        "observation_time": obs_raw if obs_known else None,
        "observation_precision": "day" if obs_known else "unknown",
        "value_state": state,
        "limitations": limitations,
    }


def _dots_meta(md_entry, cutoff, out):
    md = md_entry if isinstance(md_entry, dict) else {}
    release = md.get("release_date")
    precision = md.get("release_precision")
    limitations = []
    dots = out.get("dots") or []
    if dots:
        state = "present"
    else:
        later = _evidence_later(release, precision, cutoff) if cutoff is not None else None
        if later is True:
            state = "refused"
            limitations.append("after_cutoff")
        elif cutoff is not None and later is None:
            state = "withheld"
            limitations.append("evidence_time_unknown")
        else:
            state = "missing"
    if release is None:
        limitations.append("sep_release_date_unknown")
    limitations.append(_PARTICIPANT_NOTE)
    year = dots[0]["year"] if dots else None
    y = f"{year:04d}" if year else None
    return {
        "source": "fred:FEDTARMD",
        "evidence_class": "survey_participant_projection",
        "target": "sep_fed_funds_year_end_median",
        "subject": f"sep_median_{y}" if y else None,
        "target_epoch": f"{y}-12-31" if y else None,
        "reference_start": f"{y}-12-01" if y else None,
        "reference_end": f"{y}-12-31" if y else None,
        "vintage": release,
        "first_public_evidence": release,
        "first_public_precision": precision if precision in ("day", "month") else "unknown",
        "rights": "public_official",
        "source_version": md.get("source_version"),
        "value_state": state,
        "limitations": limitations,
    }


def _gap_meta(out, strips, dots_meta, selected):
    """SEP-vs-market comparability verdict <G> — the legacy `gap` is never altered."""
    legacy_gap = out.get("gap")
    if legacy_gap is None or selected is None or selected not in strips:
        return None
    strip = strips[selected]
    status = reason = transform = None
    limitations: list[str] = []
    start = end = None
    horizon = legacy_gap["horizon_months"]
    dot_year = (out.get("dots") or [{}])[0].get("year")

    if dots_meta["value_state"] != "present":
        status, reason = "unavailable", f"operand_{dots_meta['value_state']}:left"
    elif strip["value_state"] != "present":
        status, reason = "unavailable", f"operand_{strip['value_state']}:right"
    elif strip["rate_index"] != "EFFR":
        status, reason = "not_comparable", "basis_mismatch:rate_index"
    else:
        parsed = [c for c in (strip["contracts"] or [])
                  if c.get("reference_start") and c.get("centre_months") is not None]
        if strip["observation_time"] is None or not parsed:
            status, reason = "not_comparable", "unknown_basis:reference_end"
        else:
            lower = upper = None
            for c in parsed:
                cm = c["centre_months"]
                if cm <= horizon and (lower is None or cm > lower["centre_months"]):
                    lower = c
                if cm >= horizon and (upper is None or cm < upper["centre_months"]):
                    upper = c
            if lower is None or upper is None:
                status, reason = "not_comparable", "unknown_basis:reference_end"
            else:
                start, end = lower["reference_start"], upper["reference_end"]
                if not (start <= f"{dot_year}-12-01" and end >= f"{dot_year}-12-31"):
                    status, reason = "not_comparable", "basis_mismatch:reference_end"
                else:
                    status = "comparable_after_transformation"
                    transform = "year_end_interval_match"
                    limitations.append(_PARTICIPANT_NOTE)
    return {
        "rule_id": "sep_vs_market_year_end.v1",
        "left": "dots",
        "right": selected,
        "status": status,
        "reason": reason,
        "transform": transform,
        "limitations": limitations,
        "market_horizon_months": horizon,
        "market_reference_start": start,
        "market_reference_end": end,
    }


def _implied_source_meta(asof_ts, metadata, cutoff, zq_row, sofr_row, front,
                         dot_series, out):
    """The D0 provenance block — mirrors the legacy selection, classifies every
    operand, and answers the SEP-vs-market comparability question under §2.3a."""
    md = metadata if isinstance(metadata, dict) else {}
    selected = _selected_strip(out)
    strips = {
        "zq": _strip_meta("zq", zq_row, md.get("zq"), asof_ts, cutoff, selected),
        "sofr": _strip_meta("sofr", sofr_row, md.get("sofr"), asof_ts, cutoff, selected),
        "zq_front": _front_meta(front, md.get("zq_front"), asof_ts, cutoff),
    }
    dots_meta = _dots_meta(md.get("dots"), cutoff, out)
    is_effr = _SELECTED_IS_EFFR.get(selected)
    return {
        "schema": _SOURCE_META_SCHEMA,
        "authority": "display_only",
        "cutoff": cutoff,
        "selected_strip": selected,
        "strips": strips,
        "dots": dots_meta,
        "gap": _gap_meta(out, strips, dots_meta, selected),
        "selected_basis": _SELECTED_BASIS.get(selected),
        "selected_is_effr": is_effr,
        "missing_source": [k for k in ("zq", "sofr", "zq_front")
                           if strips[k]["value_state"] in ("missing", "refused", "withheld")],
        "legacy_value_basis_note": _LEGACY_SOFR_NOTE if is_effr is False else None,
    }


def _read_path_row(store_key: str) -> tuple[dict | None, str | None]:
    """Latest implied-path row (dict keyed m{H}) from data/rate_futures/."""
    df = store.read("rate_futures", store_key)
    if df is None or df.empty:
        return None, None
    row = df.dropna(how="all").iloc[-1]
    asof = str(df.dropna(how="all").index[-1].date())
    return {c: (None if pd.isna(row[c]) else float(row[c])) for c in df.columns}, asof


def snapshot(f: pd.DataFrame, cfg: dict | None = None) -> dict | None:
    """Live wiring: pull every input from the feature frame + the store, then
    delegate to the pure compute(). Degrade-never-raise."""
    from engine.bonds import near_term_forward_spread
    cfg = cfg if cfg is not None else _cfg()

    asof = f.dropna(how="all").index.max() if len(f) else pd.Timestamp.utcnow()
    policy_rate = _last(f["fed_funds"]) if "fed_funds" in f else None
    target_low = _last(f["fed_target_lower"]) if "fed_target_lower" in f else None
    target_high = _last(f["fed_target_upper"]) if "fed_target_upper" in f else None
    zq_front_implied = _last(f["zq_implied_rate"]) if "zq_implied_rate" in f else None
    rate_exp_proxy = _last(f["rate_expectations_proxy"]) if "rate_expectations_proxy" in f else None
    curve_tp_adj = _last(f["curve_tp_adj"]) if "curve_tp_adj" in f else None
    try:
        ntfs = _last(near_term_forward_spread(f))
    except Exception:  # noqa: BLE001 — additive, never fatal
        ntfs = None

    # dot-plot path: read the RAW FRED series (the frame ffill collapses its horizons)
    dot_df = store.read("fred", "FEDTARMD")
    dot_series = dot_df.iloc[:, 0] if dot_df is not None and not dot_df.empty else None
    if dot_series is None and "fed_dot_median" in f:  # frame fallback (single dot)
        dot_series = f["fed_dot_median"].dropna()

    zq_row, zq_asof = _read_path_row("zq_path")
    sofr_row, sofr_asof = _read_path_row("sofr_path")

    return compute(asof=asof, policy_rate=policy_rate, target_low=target_low,
                   target_high=target_high, dot_series=dot_series,
                   zq_path_row=zq_row, sofr_path_row=sofr_row,
                   zq_front_implied=zq_front_implied, ntfs=ntfs,
                   curve_tp_adj=curve_tp_adj, rate_exp_proxy=rate_exp_proxy, cfg=cfg,
                   metadata=_live_source_metadata(zq_asof, sofr_asof), cutoff=None)


def _contracts_at(asof: str | None, store_key: str) -> list[str] | None:
    """Vendor symbols non-null on the contracts frame at the path's OWN asof —
    the contracts that were actually live when the path row printed."""
    if asof is None:
        return None
    try:
        cf = store.read("rate_futures", store_key)
        if cf is None or cf.empty:
            return None
        ts = pd.Timestamp(asof)
        if ts not in cf.index:
            return None
        row = cf.loc[ts]
        kept = [c for c in cf.columns if not pd.isna(row[c])]
        return kept or None
    except Exception:  # noqa: BLE001 — provenance must never fail the snapshot
        return None


def _live_source_metadata(zq_asof: str | None, sofr_asof: str | None) -> dict:
    """Strip provenance from the live store: each strip's own path asof + the
    exact vendor symbols live at that date. No dots release date is known."""
    from collectors import rate_futures as rf  # lazy

    meta = {}
    for key, asof in (("zq", zq_asof), ("sofr", sofr_asof)):
        meta[key] = {"observation_date": asof,
                     "contracts": _contracts_at(asof, f"{key}_contracts"),
                     "price_type": rf.PRICE_TYPE, "vendor": rf.VENDOR,
                     "rights": rf.RIGHTS}
    return meta
