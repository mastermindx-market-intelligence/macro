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
        "effr_meeting_path": _effr_meeting_path(asof_ts, md, cutoff, strips["zq"], out),
    }


def _read_path_row(store_key: str, *, asof=None) -> tuple[dict | None, str | None]:
    """One read, finite daily source row, no per-column date mixing or filling.

    An all-null latest row falls back only as an explicitly older entire row.
    Future rows cannot replace an available row on/before the supplied daily cut.
    This observation-date filter is not a historical knowledge-time reconstruction.
    """
    df = store.read('rate_futures', store_key)
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return None, None
    if not isinstance(df, pd.DataFrame):
        raise ValueError('path table is not a DataFrame')
    idx = df.index
    if (not isinstance(idx, pd.DatetimeIndex) or idx.hasnans or not idx.is_unique
            or idx.tz is not None or not idx.equals(idx.normalize()) or not df.columns.is_unique):
        raise ValueError('path table requires unique timezone-naive daily labels')
    columns = [c for c in df.columns if isinstance(c, str) and c.startswith('m') and c[1:].isdigit()]
    if not columns:
        return None, None
    clean = df[columns].apply(lambda s: s.map(lambda v: _pricing_r(v, 8))).sort_index()
    clean = clean.dropna(how='all')
    if clean.empty:
        return None, None
    cut = _pricing_date_label(asof)
    eligible = clean.loc[:cut] if cut else clean
    selected = eligible if not eligible.empty else clean
    row = selected.iloc[-1]
    return {c: _pricing_r(row[c], 8) for c in selected.columns}, _pricing_date_label(selected.index[-1])


def snapshot(f: pd.DataFrame, cfg: dict | None = None) -> dict | None:
    """Capture inputs once; retain legacy/D0/D1 and attach the dated pricing view."""
    from engine.bonds import near_term_forward_spread
    cfg = cfg if cfg is not None else _cfg()
    asof = f.index.max() if len(f) else None

    def frame_value(column):
        if (column not in f or not f.columns.is_unique
                or not isinstance(f.index, pd.DatetimeIndex)
                or not f.index.is_unique or f.index.hasnans or f.index.tz is not None
                or not f.index.is_monotonic_increasing or not f.index.equals(f.index.normalize())):
            return None, None
        series = f[column].map(lambda v: _pricing_r(v, 8)).dropna()
        if series.empty:
            return None, None
        return float(series.iloc[-1]), _pricing_date_label(series.index[-1])

    policy_rate, policy_asof = frame_value('fed_funds')
    target_low, low_asof = frame_value('fed_target_lower')
    target_high, high_asof = frame_value('fed_target_upper')
    zq_front_implied, front_asof = frame_value('zq_implied_rate')
    rate_exp_proxy, _ = frame_value('rate_expectations_proxy')
    curve_tp_adj, _ = frame_value('curve_tp_adj')
    try:
        ntfs = _pricing_last(near_term_forward_spread(f))
    except Exception:
        ntfs = None
    try:
        dot_df = store.read('fred', 'FEDTARMD')
        dot_series = (dot_df.iloc[:, 0] if isinstance(dot_df, pd.DataFrame) and not dot_df.empty else None)
        if dot_series is not None:
            dot_series = dot_series.map(lambda v: _pricing_r(v, 8)).dropna()
            if not isinstance(dot_series.index, pd.DatetimeIndex) or dot_series.index.hasnans:
                dot_series = None
    except Exception:
        dot_series = None
    # No frame fallback: a filled single dot cannot recover projection-year identity.
    rows, dates, statuses = {}, {}, {}
    for short, key in (('zq', 'zq_path'), ('sofr', 'sofr_path')):
        try:
            rows[short], dates[short] = _read_path_row(key, asof=asof)
        except ValueError:
            rows[short], dates[short], statuses[short] = None, None, 'invalid_source'
        except Exception:
            rows[short], dates[short], statuses[short] = None, None, 'read_unavailable'
    metadata = _live_source_metadata(dates['zq'], dates['sofr'])
    legacy_dots = dot_series
    if legacy_dots is None and "fed_dot_median" in f:
        # Preserve the frozen compatibility envelope's existing fallback only.
        legacy_dots = f["fed_dot_median"].dropna()
    legacy = compute(asof=asof, policy_rate=policy_rate, target_low=target_low,
                     target_high=target_high, dot_series=legacy_dots,
                     zq_path_row=rows['zq'], sofr_path_row=rows['sofr'],
                     zq_front_implied=zq_front_implied, ntfs=ntfs,
                     curve_tp_adj=curve_tp_adj, rate_exp_proxy=rate_exp_proxy, cfg=cfg,
                     metadata=metadata, cutoff=None)
    projection = compute_qualified_pricing(asof=asof, policy_rate=policy_rate, policy_asof=policy_asof,
                   target_low=target_low, target_high=target_high, dot_series=dot_series,
                   target_low_asof=low_asof, target_high_asof=high_asof,
                   zq_path_row=rows['zq'], sofr_path_row=rows['sofr'],
                   zq_path_asof=dates['zq'], sofr_path_asof=dates['sofr'], path_status=statuses,
                   zq_front_implied=zq_front_implied, front_asof=front_asof, ntfs=ntfs,
                   curve_tp_adj=curve_tp_adj, rate_exp_proxy=rate_exp_proxy, cfg=cfg)
    if legacy is None:
        return projection
    legacy["qualified_pricing"] = projection
    return legacy


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
                     "contract_closes": _contract_closes_at(asof, f"{key}_contracts"),
                     "price_type": rf.PRICE_TYPE, "vendor": rf.VENDOR,
                     "rights": rf.RIGHTS}
    effr = _fred_last("DFF")
    if effr is not None:
        meta["effr"] = {"value": effr[0], "observation_date": effr[1],
                        "source": "fred:DFF"}
    lo = _fred_last("DFEDTARL")
    hi = _fred_last("DFEDTARU")
    if lo is not None and hi is not None:
        meta["target_range"] = {
            "low": lo[0], "high": hi[0],
            "observation_date": min(lo[1], hi[1]),
        }
    elif lo is not None:
        meta["target_range"] = {"low": lo[0], "high": None,
                                "observation_date": lo[1]}
    elif hi is not None:
        meta["target_range"] = {"low": None, "high": hi[0],
                                "observation_date": hi[1]}
    return meta
def _contract_closes_at(asof: str | None, store_key: str) -> dict | None:
    """Per-symbol daily close at the path's OWN asof (nulls dropped).

    Mirrors `_contracts_at` (symbol names only); used by the D1 EFFR meeting
    path block to construct per-contract monthly averages. Returns None on
    absence, missing-asof or any exception."""
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
        out_d = {str(c): float(row[c]) for c in cf.columns
                 if not pd.isna(row[c])}
        return out_d or None
    except Exception:  # noqa: BLE001 — additive, never fatal
        return None


def _fred_last(series_id: str) -> tuple[float, str] | None:
    """Last non-null of a FRED series at column 0 — (value, ISO date) or None."""
    try:
        df = store.read("fred", series_id)
        if df is None or df.empty:
            return None
        s = df.iloc[:, 0].dropna()
        if s.empty:
            return None
        return float(s.iloc[-1]), pd.Timestamp(s.index[-1]).date().isoformat()
    except Exception:  # noqa: BLE001 — additive, never fatal
        return None


# --------------------------------------------------------------------------- #
# D1 — FED-PATH EFFR MEETING PATH (RIC-INCLUDED-CORE, R-1)
#
# Additive block: a single new key in `implied_source_meta`. No existing output
# byte changes. The function fails CLOSED inside its body (returns an
# `unavailable` block on any exception) so compute() never raises because of D1.
# --------------------------------------------------------------------------- #
_SCHEMAv1_EFFR_MEETING = "fed_path_effr_meeting_path.v1"
_ASSUMPTIONS_EFFR = (
    "effective_date_convention=decision_plus_1d",
    "no_intermeeting_change",
    "effr_level_constant_between_effective_dates",
)


def _effr_unavailable_block(reason: str, cutoff_effective: str,
                             cutoff_basis: str) -> dict:
    return {
        "schema": _SCHEMAv1_EFFR_MEETING,
        "authority": "display_only",
        "status": "unavailable",
        "reason": reason,
        "cutoff_effective": cutoff_effective,
        "cutoff_basis": cutoff_basis,
        "effective_date_law": "decision_plus_1d",
        "calendar_years_covered": [],
        "assumptions": list(_ASSUMPTIONS_EFFR),
        "gap": None,
        "months": [],
        "refused_contracts": [],
        "limitations": [],
    }


def _isfinite_real(v) -> bool:
    """True iff v is a finite real number (no booleans, no NaN, no strings)."""
    if isinstance(v, bool) or v is None:
        return False
    if isinstance(v, float) and v != v:  # NaN
        return False
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return np.isfinite(f)


def _no_eff_open_open(lo: "date", hi: "date", eff_dates: list) -> bool:
    for ed in eff_dates:
        if lo < ed < hi:
            return False
    return True


def _no_eff_open_closed(lo: "date", hi: "date", eff_dates: list) -> bool:
    for ed in eff_dates:
        if lo < ed <= hi:
            return False
    return True


def _compare_zq_vs_mid(rcb, month_obs, mid_obs, gap_info: dict):
    if month_obs is None or mid_obs is None:
        return None
    ctx = ({"effr_minus_midpoint_bp": gap_info["value_bp"]}
           if gap_info.get("usable") and gap_info.get("value_bp") is not None
           else None)
    try:
        return rcb.compare_qualified(
            month_obs, mid_obs,
            rcb.RULES["zq_month_vs_policy_midpoint.v1"],
            context=ctx).to_dict()
    except Exception:  # noqa: BLE001 — never fail the block
        return None


def _effr_meeting_path(asof_ts, md, cutoff, zq_strip_meta: dict, out: dict) -> dict:
    """D1 EFFR monthly-identity reading of the ZQ strip (the EFFR-meeting path).

    Reads only `md["zq"]["contract_closes"]` (per-vendor-symbol daily close) +
    `md["effr"]` (FRED DFF daily) + `md["target_range"]` (FRED DFEDTAR{L,U})
    + `md["effr_basis"]` (explicit EFFR-minus-midpoint bp). The B0 solver is
    `engine.rates_command_basis.solve_reference_average`. Returns the schema'd
    block; degrades to an `unavailable` block on strip absence or any
    exception so the legacy compute never raises."""
    from datetime import timedelta as _td
    from engine import rates_command_basis as rcb
    from engine import event_calendar as ec
    from collectors import rate_futures as rf

    try:
        # --- 1) cutoff_effective + cutoff_basis ---
        if cutoff is not None and str(cutoff).strip():
            cutoff_effective = str(cutoff)
            cutoff_basis = "supplied"
        else:
            cutoff_effective = (asof_ts.date() + _td(days=1)).isoformat()
            cutoff_basis = "live_asof_plus_1d"

        # --- 2) block availability on the ZQ strip's value_state ---
        zq_state = (zq_strip_meta or {}).get("value_state") if isinstance(zq_strip_meta, dict) else None
        if zq_state != "present":
            return _effr_unavailable_block(
                reason=f"zq_strip_{zq_state or 'missing'}",
                cutoff_effective=cutoff_effective,
                cutoff_basis=cutoff_basis)

        md_zq = md.get("zq") if isinstance(md, dict) else None
        closes = (md_zq or {}).get("contract_closes") if isinstance(md_zq, dict) else None
        zq_obs_date = (md_zq or {}).get("observation_date") if isinstance(md_zq, dict) else None
        if not isinstance(closes, dict) or not closes:
            return _effr_unavailable_block(
                reason="contract_closes_missing",
                cutoff_effective=cutoff_effective,
                cutoff_basis=cutoff_basis)

        # --- 3) FOMC effective dates + calendar_years_covered ---
        decisions = ec.fomc_decision_dates(date(1900, 1, 1), date(2999, 12, 31))
        all_eff = sorted((d + _td(days=1)).isoformat() for d in decisions)
        calendar_years_covered = sorted({d.year for d in decisions})
        eff_date_objs = [date.fromisoformat(s) for s in all_eff]

        # --- 4) R1 basis gate + duplicate handling ---
        refused: list = []
        admitted: dict = {}  # (year, month) -> (sym, close, parsed)
        for sym in sorted(str(s) for s in closes.keys()):
            p = rf.parse_contract_symbol(sym)
            if p is None:
                refused.append({"contract": sym, "reason": "unknown_basis:rate_index"})
                continue
            b = rf.strip_basis(p["symbol_root"])
            if not b or b.get("rate_index") is None:
                refused.append({"contract": sym, "reason": "unknown_basis:rate_index"})
                continue
            if b["rate_index"] != "EFFR":
                refused.append({"contract": sym, "reason": "basis_mismatch:rate_index"})
                continue
            if b.get("averaging_law") != "arithmetic_calendar_day":
                refused.append({"contract": sym, "reason": "basis_mismatch:averaging_law"})
                continue
            ym = (p["year"], p["month"])
            if ym in admitted:
                refused.append({"contract": sym, "reason": "duplicate_contract_month"})
                continue
            admitted[ym] = (sym, closes[sym], p)

        # --- 5) optional EFFR daily + target midpoint ---
        effr_md = md.get("effr") if isinstance(md, dict) else None
        effr_value = (effr_md or {}).get("value") if isinstance(effr_md, dict) else None
        effr_obs_date = (effr_md or {}).get("observation_date") if isinstance(effr_md, dict) else None

        dff_obs = None
        if isinstance(effr_md, dict) and effr_obs_date:
            try:
                dff_obs = rcb.qualify_observation(
                    effr_value,
                    {
                        "subject": "effr_daily",
                        "evidence_class": "official_measurement",
                        "unit": "pct_ann_rate",
                        "target": "effr_daily",
                        "basket_or_index": "EFFR",
                        "rate_index": "EFFR",
                        "averaging_law": "point",
                        "observation_time": effr_obs_date,
                        "observation_precision": "day",
                        "first_public_evidence": (
                            date.fromisoformat(effr_obs_date) + _td(days=1)
                        ).isoformat(),
                        "first_public_precision": "day",
                        "limitations": ("publication_lag_assumed_1d",),
                        "rights": "public_official",
                        "source": "fred:DFF",
                    },
                    cutoff_effective)
            except Exception:
                dff_obs = None

        target_md = md.get("target_range") if isinstance(md, dict) else None
        target_obs_date = None
        mid_value = None
        mid_source = "fed_path:out.target"
        if isinstance(target_md, dict) and target_md:
            lo = target_md.get("low")
            hi = target_md.get("high")
            target_obs_date = target_md.get("observation_date")
            if _isfinite_real(lo) and _isfinite_real(hi):
                mid_value = (float(lo) + float(hi)) / 2.0
                mid_source = "fred:DFEDTARL+DFEDTARU"
        # fallback to out.target_low/target_high
        if mid_value is None:
            lo_out = (out or {}).get("target_low")
            hi_out = (out or {}).get("target_high")
            if _isfinite_real(lo_out) and _isfinite_real(hi_out):
                mid_value = (float(lo_out) + float(hi_out)) / 2.0
                target_obs_date = None
                mid_source = "fed_path:out.target"

        mid_obs = None
        if mid_value is not None:
            try:
                mid_obs = rcb.qualify_observation(
                    mid_value,
                    {
                        "subject": "fed_funds_target_midpoint",
                        "evidence_class": "official_measurement",
                        "unit": "pct_ann_rate",
                        "target": "fed_funds_target_midpoint",
                        "averaging_law": "point",
                        "observation_time": target_obs_date,
                        "observation_precision": "day",
                        "first_public_evidence": target_obs_date,
                        "first_public_precision": "day",
                        "rights": "public_official",
                        "source": mid_source,
                    },
                    cutoff_effective)
            except Exception:
                mid_obs = None

        # --- 6) R6 GAP (block level, computed once) ---
        gap_info: dict = {"value_bp": None, "usable": False,
                          "source": None, "reason": None}
        block_limitations: list = []

        effr_basis_md = md.get("effr_basis") if isinstance(md, dict) else None
        eb_value = (effr_basis_md or {}).get("effr_minus_midpoint_bp") if isinstance(effr_basis_md, dict) else None
        eb_obs = (effr_basis_md or {}).get("observation_date") if isinstance(effr_basis_md, dict) else None
        eb_source = (effr_basis_md or {}).get("source") if isinstance(effr_basis_md, dict) else None

        if _isfinite_real(eb_value):
            if eb_obs is None or str(eb_obs).strip() == "":
                gap_info["reason"] = "effr_basis_time_unknown"
            elif _evidence_later(str(eb_obs), "day", cutoff_effective) is True:
                gap_info["reason"] = "effr_basis_after_cutoff"
            else:
                gap_info["value_bp"] = float(eb_value)
                gap_info["usable"] = True
                gap_info["source"] = "explicit:" + (eb_source or "unspecified")
        else:
            d_dff_date = _as_date(effr_obs_date) if dff_obs is not None and dff_obs.value_state.value == "present" else None
            d_mid_date = _as_date(target_obs_date) if mid_obs is not None and mid_obs.value_state.value == "present" else None
            if d_dff_date is None or d_mid_date is None:
                gap_info["reason"] = "gap_inputs_missing"
            elif (d_dff_date.year not in calendar_years_covered
                  or d_mid_date.year not in calendar_years_covered):
                gap_info["reason"] = "meeting_calendar_unknown"
            else:
                lo_d, hi_d = min(d_dff_date, d_mid_date), max(d_dff_date, d_mid_date)
                if not _no_eff_open_closed(lo_d, hi_d, eff_date_objs):
                    gap_info["reason"] = "target_changed_between_gap_dates"
                else:
                    gap_info["value_bp"] = round((float(effr_value) - float(mid_value)) * 100.0, 6)
                    gap_info["usable"] = True
                    gap_info["source"] = (
                        f"measured:fred:DFF@{effr_obs_date}-midpoint@{target_obs_date}"
                    )
                    block_limitations.append("single_day_gap")

        # --- 7) per-month processing (sorted by ref_start) ---
        months_out: list = []
        # chain table: (year, month) -> end_rate, only for IDENTIFIED_CONDITIONAL records
        # — used by R7.2 to chain the IMMEDIATELY PRECEDING calendar month only.
        chain_identified: dict = {}

        for (year, month), (sym, close_raw, _p) in sorted(admitted.items(),
                                                         key=lambda kv: kv[0]):
            ref_start_iso, ref_end_iso = rf.contract_reference_period(year, month, "monthly")
            ref_start = date.fromisoformat(ref_start_iso)
            ref_end = date.fromisoformat(ref_end_iso)
            month_days = (ref_end - ref_start).days + 1
            realised = max(0, min(month_days, (asof_ts.date() - ref_start).days))
            remaining = month_days - realised

            # R2 monthly-average qualification
            month_obs = None
            if _isfinite_real(close_raw):
                try:
                    month_obs = rcb.qualify_observation(
                        100.0 - float(close_raw),
                        {
                            "subject": f"zq_month_average:{sym}",
                            "evidence_class": "market_implied_expectation",
                            "unit": "pct_ann_rate",
                            "target": "effr_monthly_average",
                            "basket_or_index": "EFFR",
                            "rate_index": "EFFR",
                            "averaging_law": "arithmetic_calendar_day",
                            "reference_start": ref_start_iso,
                            "reference_end": ref_end_iso,
                            "observation_time": zq_obs_date,
                            "observation_precision": "day",
                            "first_public_evidence": zq_obs_date,
                            "first_public_precision": "day",
                            "rights": rf.RIGHTS,
                            "source": f"yfinance:{sym}",
                        },
                        cutoff_effective)
                except Exception:
                    month_obs = None

            inside = [e for e in all_eff if ref_start_iso <= e <= ref_end_iso]

            # R8.a month_obs not present
            if month_obs is None or month_obs.value_state.value != "present":
                state_val = month_obs.value_state.value if month_obs else "missing"
                months_out.append({
                    "contract": sym,
                    "reference_start": ref_start_iso,
                    "reference_end": ref_end_iso,
                    "month_days": month_days,
                    "monthly_average": (month_obs.to_dict() if month_obs else None),
                    "effective_dates_inside": inside,
                    "status": "unavailable",
                    "reason": f"monthly_average_{state_val}",
                    "pre_change_rate": None,
                    "pre_change_rate_source": None,
                    "identification": None,
                    "vs_target_midpoint": _compare_zq_vs_mid(rcb, month_obs, mid_obs, gap_info),
                    "weights": {"days_pre": None, "days_post": None,
                                "realised_days": realised,
                                "remaining_days": remaining},
                    "post_rate_sensitivity": None,
                    "limitations": [],
                })
                continue

            # R8.b ref year not in calendar
            if ref_start.year not in calendar_years_covered:
                months_out.append({
                    "contract": sym,
                    "reference_start": ref_start_iso,
                    "reference_end": ref_end_iso,
                    "month_days": month_days,
                    "monthly_average": month_obs.to_dict(),
                    "effective_dates_inside": inside,
                    "status": "missing_inputs",
                    "reason": "meeting_calendar_unknown",
                    "pre_change_rate": None,
                    "pre_change_rate_source": None,
                    "identification": None,
                    "vs_target_midpoint": _compare_zq_vs_mid(rcb, month_obs, mid_obs, gap_info),
                    "weights": {"days_pre": None, "days_post": None,
                                "realised_days": realised,
                                "remaining_days": remaining},
                    "post_rate_sensitivity": None,
                    "limitations": [],
                })
                continue

            pre = None
            pre_source = None

            if len(inside) == 1:
                eff_iso = inside[0]
                eff_d = date.fromisoformat(eff_iso)
                route_used = False

                # R7 Route 1: DFF
                if (dff_obs is not None and dff_obs.value_state.value == "present"
                        and effr_obs_date):
                    d_dff = _as_date(effr_obs_date)
                    if d_dff is not None and d_dff < eff_d:
                        if _no_eff_open_open(d_dff, eff_d, eff_date_objs):
                            pre = float(dff_obs.value)
                            pre_source = f"observed_effr:fred:DFF@{effr_obs_date}"
                            route_used = True

                # R7 Route 2: chained from the IMMEDIATELY PRECEDING calendar month
                if not route_used:
                    if month == 1:
                        prev_ym = (year - 1, 12)
                    else:
                        prev_ym = (year, month - 1)
                    prior_end_rate = chain_identified.get(prev_ym)
                    if prior_end_rate is not None:
                        py, pm = prev_ym
                        pre = float(prior_end_rate)
                        pre_source = f"chained:{py}-{pm:02d}"
                        route_used = True

                # R7 Route 3: midpoint + gap
                if (not route_used and mid_obs is not None
                        and mid_obs.value_state.value == "present"
                        and target_obs_date):
                    d_mid = _as_date(target_obs_date)
                    if d_mid is not None and d_mid < eff_d:
                        if _no_eff_open_open(d_mid, eff_d, eff_date_objs):
                            if gap_info["usable"] and gap_info["value_bp"] is not None:
                                pre = float(mid_value) + gap_info["value_bp"] / 100.0
                                pre_source = f"target_midpoint_plus_gap:{gap_info['source']}"
                                route_used = True
                            else:
                                # not_identified, skip the solver
                                months_out.append({
                                    "contract": sym,
                                    "reference_start": ref_start_iso,
                                    "reference_end": ref_end_iso,
                                    "month_days": month_days,
                                    "monthly_average": month_obs.to_dict(),
                                    "effective_dates_inside": inside,
                                    "status": "not_identified",
                                    "reason": "underidentified:effr_target_basis",
                                    "pre_change_rate": None,
                                    "pre_change_rate_source": None,
                                    "identification": None,
                                    "vs_target_midpoint": _compare_zq_vs_mid(rcb, month_obs, mid_obs, gap_info),
                                    "weights": {"days_pre": (eff_d - ref_start).days,
                                                "days_post": month_days - (eff_d - ref_start).days,
                                                "realised_days": realised,
                                                "remaining_days": remaining},
                                    "post_rate_sensitivity": None,
                                    "limitations": [],
                                })
                                continue

            # solver call — exceptions bubble to the outer block-level try/except
            assumptions = rcb.PathAssumptions(
                month_start=ref_start_iso,
                month_end=ref_end_iso,
                effective_dates=tuple(all_eff),
                pre_change_rate=pre,
            )
            identification = rcb.solve_reference_average([month_obs], assumptions)

            ident_dict = identification.to_dict()
            status_val = identification.status.value
            missing_set = set(identification.missing)
            month_limitations: list = []
            days_pre = days_post = None
            post_rate_sensitivity = None

            if (status_val == "identified_conditional"
                    and len(inside) == 1 and pre is not None):
                reason = f"pre_change_rate:{pre_source}"
                eff_d = date.fromisoformat(inside[0])
                days_pre = (eff_d - ref_start).days
                days_post = month_days - days_pre
                post_rate_sensitivity = round(month_days / days_post, 4) if days_post else None
            elif status_val == "identified_conditional" and not inside:
                reason = "no_intra_month_change"
                post_rate_sensitivity = 1.0
            elif len(inside) >= 2:
                reason = "multiple_effective_dates"
            elif "pre_change_rate" in missing_set:
                reason = "pre_change_rate_unavailable"
            else:
                reason = (identification.assumptions_used[-1]
                          if identification.assumptions_used else None)

            if pre_source and pre_source.startswith("chained:"):
                month_limitations.append("chained_identification")

            months_out.append({
                "contract": sym,
                "reference_start": ref_start_iso,
                "reference_end": ref_end_iso,
                "month_days": month_days,
                "monthly_average": month_obs.to_dict(),
                "effective_dates_inside": inside,
                "status": status_val,
                "reason": reason,
                "pre_change_rate": pre,
                "pre_change_rate_source": pre_source,
                "identification": ident_dict,
                "vs_target_midpoint": _compare_zq_vs_mid(rcb, month_obs, mid_obs, gap_info),
                "weights": {"days_pre": days_pre, "days_post": days_post,
                            "realised_days": realised,
                            "remaining_days": remaining},
                "post_rate_sensitivity": post_rate_sensitivity,
                "limitations": month_limitations,
            })

            if status_val == "identified_conditional":
                end_rate = None
                if identification.identified and isinstance(identification.identified, dict):
                    end_rate = identification.identified.get("end_rate")
                if end_rate is not None:
                    chain_identified[(year, month)] = float(end_rate)
            # non-identified months break any chain into the following month

        gap_out = gap_info if (gap_info["usable"] or gap_info["reason"]) else None
        return {
            "schema": _SCHEMAv1_EFFR_MEETING,
            "authority": "display_only",
            "status": "computed",
            "reason": None,
            "cutoff_effective": cutoff_effective,
            "cutoff_basis": cutoff_basis,
            "effective_date_law": "decision_plus_1d",
            "calendar_years_covered": calendar_years_covered,
            "assumptions": list(_ASSUMPTIONS_EFFR),
            "gap": gap_out,
            "months": months_out,
            "refused_contracts": refused,
            "limitations": block_limitations,
        }

    except Exception as exc:
        # hard backstop — D1 must NEVER raise compute()
        ce = str(cutoff) if cutoff else ""
        return _effr_unavailable_block(
            reason="internal_error:" + type(exc).__name__,
            cutoff_effective=ce,
            cutoff_basis=("supplied" if cutoff else "live_asof_plus_1d"))


# Explicit dated pricing view; the legacy compute definition above is frozen.
def _pricing_r(v, nd: int = 2):
    """Finite scalar only; malformed optional values are explicit missingness."""
    if isinstance(v, (bool, np.bool_)) or v is None:
        return None
    try:
        value = float(v)
        return round(value, nd) if np.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _pricing_date_label(value) -> str | None:
    """Daily labels only: never infer a release instant from a date."""
    if value is None or isinstance(value, (bool, int, float, np.number)):
        return None
    try:
        stamp = pd.Timestamp(value)
        if pd.isna(stamp) or stamp.tz is not None or stamp != stamp.normalize():
            return None
        return stamp.date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def _pricing_path_evidence(row, source_asof, analysis_day, horizons, family, status=None):
    clean = {f"m{h}": _pricing_r(row.get(f"m{h}"), 8) for h in horizons} if isinstance(row, dict) else {}
    present = any(v is not None for v in clean.values())
    day = _pricing_date_label(source_asof)
    age = ((pd.Timestamp(analysis_day) - pd.Timestamp(day)).days
           if day is not None and analysis_day is not None else None)
    if status not in ('read_unavailable', 'invalid_source'):
        status = ('missing' if not present else
                  'observation_date_unknown' if day is None else
                  'analysis_date_unknown' if analysis_day is None else
                  'after_analysis_date' if age < 0 else
                  'same_date_context' if age == 0 else 'stale_dated_context')
    return {
        "contract_family": family, "underlying": "EFFR" if family == "ZQ" else "SOFR",
        "aggregation": "calendar_month_average" if family == "ZQ" else "quarterly_compounded",
        "representation": "interpolated_relative_horizons_not_individual_contracts",
        "source_asof": day, "analysis_asof": analysis_day, "age_calendar_days": age,
        "status": status, "last_observed_path": clean if present else None,
        "usable_as_same_date_context": present and status == 'same_date_context',
        "actual_contract_ids": None, "target_period_identity_qualified": False,
        "available_at": None, "historical_availability_qualified": False,
    }


def _pricing_last(s: pd.Series | None) -> float | None:
    if s is None:
        return None
    for value in reversed(s.tolist()):
        number = _pricing_r(value, 8)
        if number is not None:
            return number
    return None


def _pricing_dots_by_year(dot_series: pd.Series | None, this_year: int) -> list[dict]:
    """Retain finite projection-year values; publication time remains unqualified."""
    if (not isinstance(dot_series, pd.Series) or
            not isinstance(dot_series.index, pd.DatetimeIndex) or dot_series.index.hasnans
            or not dot_series.index.is_unique or dot_series.index.tz is not None):
        return []
    by_year: dict[int, float] = {}
    for ts, value in dot_series.sort_index().items():
        value = _pricing_r(value, 8)
        if value is not None:
            by_year[pd.Timestamp(ts).year] = value
    return [{"year": y, "median": round(by_year[y], 3)}
            for y in sorted(by_year) if y >= this_year]


def compute_qualified_pricing(*, asof, policy_rate, target_low, target_high, dot_series,
            zq_path_row, sofr_path_row, zq_front_implied,
            ntfs, curve_tp_adj, rate_exp_proxy, cfg=None,
            zq_path_asof=None, sofr_path_asof=None, policy_asof=None,
            path_status=None, front_asof=None,
            target_low_asof=None, target_high_asof=None) -> dict | None:
    """Assemble explicitly dated context; preserve old keys without false basis joins.

    Undated inputs remain descriptive evidence, never same-date comparisons.
    SOFR is separate from EFFR. Relative mN points are not individually identified
    contracts and do not identify meeting probabilities or a causal policy shock.
    """
    cfg = cfg if cfg is not None else _cfg()
    horizons = list(cfg.get("horizons_m", [1, 3, 6, 12]))
    if (not horizons or len(horizons) > 24 or any(isinstance(h, bool) or
            not isinstance(h, int) or h <= 0 or h > 120 for h in horizons)
            or len(set(horizons)) != len(horizons)):
        raise ValueError("horizons_m must contain unique positive integer months")
    analysis_day = _pricing_date_label(asof)
    status = path_status if isinstance(path_status, dict) else {}
    zq = _pricing_path_evidence(zq_path_row, zq_path_asof, analysis_day, horizons, 'ZQ', status.get('zq'))
    sofr = _pricing_path_evidence(sofr_path_row, sofr_path_asof, analysis_day, horizons, 'SR3', status.get('sofr'))
    policy_rate = _pricing_r(policy_rate, 8)
    target_low, target_high = _pricing_r(target_low, 8), _pricing_r(target_high, 8)
    low_day, high_day = _pricing_date_label(target_low_asof), _pricing_date_label(target_high_asof)
    range_status = ('missing_bounds' if target_low is None or target_high is None else
                    'invalid_bounds' if target_low > target_high else
                    'dates_unknown' if low_day is None or high_day is None else
                    'mixed_dates' if low_day != high_day else
                    'analysis_date_unknown' if analysis_day is None else
                    'after_analysis_date' if low_day > analysis_day else
                    'same_date_frame_bounds' if low_day == analysis_day else
                    'older_matched_frame_bounds')
    tmid = ((target_low + target_high) / 2 if range_status in
            ('same_date_frame_bounds', 'older_matched_frame_bounds') else None)
    range_evidence = {'lower_value': target_low, 'upper_value': target_high,
                      'lower_asof': low_day, 'upper_asof': high_day,
                      'status': range_status, 'observation_origin': 'frame_aligned_unverified',
                      'historical_availability_qualified': False}
    pol = policy_rate if policy_rate is not None else tmid
    policy_day = _pricing_date_label(policy_asof)
    reference_current = policy_rate is not None and policy_day == analysis_day and analysis_day is not None
    path = zq['last_observed_path'] if zq['usable_as_same_date_context'] else None
    implied = {'now': _pricing_r(pol)}
    if path:
        implied.update({key: _pricing_r(value) for key, value in path.items()})
    path_src = 'ZQ fed-funds futures' if path else None
    path_src_zh = 'ZQ 联邦基金期货' if path else None
    comparable = path is not None and reference_current
    m12, m6 = (path or {}).get('m12'), (path or {}).get('m6')
    bp12 = round((m12 - policy_rate) * 100, 4) if comparable and m12 is not None else None
    eq12 = round((policy_rate - m12) / _QUARTER, 6) if bp12 is not None else None
    eq6 = round((policy_rate - m6) / _QUARTER, 6) if comparable and m6 is not None else None
    comparison_status = ('effective_rate_reference_unavailable' if policy_rate is None else
                         'reference_date_unqualified' if not reference_current else
                         'path_date_unqualified' if path is None else
                         'horizon_unavailable' if m12 is None else 'same_date_frame_reference')
    dots = _pricing_dots_by_year(dot_series, pd.Timestamp(analysis_day).year) if analysis_day else []
    # A dot is a year-end target midpoint; the available interpolated EFFR path
    # lacks both an accepted midpoint basis mapping and exact target-period identity.
    gap_reasons = (['target_basis_unqualified', 'dot_publication_clock_unqualified',
                    'target_period_identity_unqualified'] if dots else ['dot_path_unavailable'])
    front_value = _pricing_r(zq_front_implied, 8)
    front = ({'implied_average_rate': front_value, 'frame_asof': _pricing_date_label(front_asof),
              'contract_family': 'ZQ', 'contract_identity_qualified': False,
              'target_period_identity_qualified': False, 'observation_origin': 'frame_unverified',
              'historical_availability_qualified': False} if front_value is not None else None)
    head_en = head_zh = None
    if bp12 is not None:
        head_en = (f"Dated ZQ 12m pricing: {bp12:+.1f}bp vs EFFR frame reference "
                   f"({policy_rate:.2f}% → {m12:.2f}%); {abs(eq12):.2f} ×25bp "
                   f"{'cut' if eq12 >= 0 else 'hike'} equivalents, not a meeting count")
        head_zh = (f"有日期的 ZQ 12个月定价较 EFFR 框架参考值 {bp12:+.1f}基点"
                   f"（{policy_rate:.2f}% → {m12:.2f}%）；相当于 {abs(eq12):.2f} 个25基点"
                   f"{'降息' if eq12 >= 0 else '加息'}幅度，并非会议次数")
    elif pol is not None:
        basis = 'EFFR frame reference' if policy_rate is not None else 'target-range midpoint reference'
        head_en = f"Policy reference {pol:.2f}% ({basis}); no qualified 12m comparison"
        head_zh = f"政策参考值 {pol:.2f}%（{'EFFR 框架参考值' if policy_rate is not None else '目标区间中点'}）；12个月比较未合格"
    elif path:
        head_en, head_zh = 'Dated ZQ path; effective-rate reference unavailable', '有日期的 ZQ 路径；有效利率参考值缺失'
    elif target_low is not None or target_high is not None:
        head_en, head_zh = ('Dated target-bound observations; no qualified midpoint',
                            '有日期的目标边界观测；中点未合格')
    elif sofr['last_observed_path']:
        head_en, head_zh = 'SOFR context only; no fed-funds path', '仅有 SOFR 上下文；没有联邦基金利率路径'
    read_en, read_zh = [], []
    if policy_rate is not None:
        read_en.append(f'EFFR reference frame row {policy_day or "unknown"}; source origin unverified. ')
        read_zh.append(f'EFFR 参考框架行日期 {policy_day or "不明"}；源观测来源未核实。')
    if target_low is not None or target_high is not None:
        read_en.append(f'Target-bound frame dates: lower {low_day or "unknown"}, '
                       f'upper {high_day or "unknown"}; '
                       f'{"matched dated bounds" if tmid is not None else "no qualified midpoint"}. ')
        read_zh.append(f'目标边界框架日期：下限 {low_day or "不明"}，上限 {high_day or "不明"}；'
                       f'{"有日期的匹配边界" if tmid is not None else "中点未合格"}。')
    date_status_labels = {
        'missing': ('no usable path', '没有可用路径'),
        'observation_date_unknown': ('observation date unknown', '观测日期不明'),
        'analysis_date_unknown': ('analysis date unknown', '分析日期不明'),
        'after_analysis_date': ('later than the analysis date; not used', '晚于分析日期；不使用'),
        'same_date_context': ('same-date descriptive context only', '仅为同日期描述性上下文'),
        'stale_dated_context': ('older observations retained, not current pricing', '保留较早观测，不视为当前定价'),
        'invalid_source': ('invalid source structure; not used', '源结构无效；不使用'),
        'read_unavailable': ('source read unavailable', '源读取不可用'),
    }
    for key, label, zh in ((zq, 'ZQ/EFFR', 'ZQ/EFFR'), (sofr, 'SR3/SOFR', 'SR3/SOFR')):
        date_text = key['source_asof'] or 'unknown'
        status_en, status_zh = date_status_labels[key['status']]
        read_en.append(f"{label} observation date {date_text}: {status_en}. ")
        read_zh.append(f"{zh} 观测日期 {key['source_asof'] or '不明'}：{status_zh}。")
    if sofr['last_observed_path']:
        read_en.append('SOFR is a separate quarterly-compounded rate, not a fed-funds target proxy. ')
        read_zh.append('SOFR 是单独的季度复利利率，不是联邦基金目标利率替代值。')
    if front:
        read_en.append('Continuous ZQ front quote has no qualified fixed contract period; not an m1 point. ')
        read_zh.append('连续 ZQ 近月报价缺少合格的固定合约期间；不作 m1 点使用。')
    if dots:
        read_en.append('Dots retained; market-versus-dot gap withheld without matched basis and target period. ')
        read_zh.append('保留点阵图；没有匹配的利率基础及目标期间，市场与点阵图差值暂不提供。')
    ntfs = _pricing_r(ntfs, 8)
    if ntfs is not None:
        read_en.append(f'Near-term forward spread {ntfs:+.2f}pp; not a meeting-specific probability. ')
        read_zh.append(f'近端远期利差 {ntfs:+.2f}个百分点；并非单次会议概率。')
    note_en = ('Display context only. ZQ/EFFR monthly averages and SR3/SOFR quarterly compounding '
               'are different bases. Dates are observations, not receipt timestamps. Relative horizons '
               'do not identify fixed contracts, meeting probabilities or a causal policy surprise. '
               'An EFFR frame reference may be carried or revised; same date is not live/replay proof. '
               'A build timestamp never refreshes its sources.')
    note_zh = ('仅供展示上下文。ZQ/EFFR 月均值与 SR3/SOFR 季度复利基础不同。观测日期不是接收时间。'
               '相对期限不能识别固定合约、会议概率或因果政策意外。EFFR 框架参考值可能经过填充或修订；'
               '日期相同不代表实时或历史回放证明。构建时间不会更新源观测。')
    out = {
        'asof': analysis_day, 'built': datetime.now(timezone.utc).isoformat(),
        'calculation_version': 'fed_path.date_basis.v2', 'horizons_m': list(horizons),
        'display_only': True, 'authority': False, 'can_score': False,
        'can_rank': False, 'can_size': False, 'can_gate': False, 'can_trade': False,
        'historical_availability_qualified': False, 'current_session_freshness': 'not_certified',
        'policy_rate': _pricing_r(policy_rate), 'target_low': _pricing_r(target_low),
        'target_high': _pricing_r(target_high), 'target_mid': _pricing_r(tmid),
        'target_range_evidence': range_evidence,
        'policy_reference_evidence': {'underlying': 'EFFR', 'source_column': 'fed_funds',
            'source_asof': policy_day, 'value': policy_rate,
            'observation_origin': 'frame_aligned_unverified',
            'historical_availability_qualified': False},
        'policy_reference_asof': policy_day, 'policy_observation_origin': 'frame_aligned_unverified',
        'implied': implied, 'implied_source_en': path_src, 'implied_source_zh': path_src_zh,
        'implied_bp_12m': bp12, 'implied_cuts_12m': round(eq12) if eq12 is not None else None,
        'implied_cuts_6m': round(eq6) if eq6 is not None else None,
        'implied_cut_equivalents_12m': eq12, 'implied_cut_equivalents_6m': eq6,
        'cut_count_interpretation': 'rounded_25bp_equivalents_not_meeting_counts_or_probabilities',
        'pricing_comparison_status': comparison_status,
        'sofr_path': ({k:_pricing_r(v) for k,v in sofr['last_observed_path'].items()}
                      if sofr['usable_as_same_date_context'] else None),
        'path_evidence': {'zq':zq, 'sofr':sofr}, 'front_quote_context': front,
        'dots': dots, 'gap': None, 'gap_unavailable_reasons': gap_reasons,
        'ntfs': _pricing_r(ntfs), 'curve_tp_adj': _pricing_r(curve_tp_adj), 'rate_exp_proxy': _pricing_r(rate_exp_proxy),
        'headline_en': head_en, 'headline_zh': head_zh,
        'read_en': ''.join(read_en).strip(), 'read_zh': ''.join(read_zh),
        'note_en': note_en, 'note_zh': note_zh,
    }
    if (pol is None and not dots and not zq['last_observed_path'] and
            not sofr['last_observed_path'] and front is None
            and target_low is None and target_high is None):
        return None
    return out


def _validated_date_basis(payload: dict) -> dict:
    """Reconcile the versioned display object with its own dated economic inputs.

    Reuses compute_qualified_pricing() rather than defining another pricing formula. This checks
    internal consistency only, NOT source authenticity or historical availability.
    Old copied headlines cannot override the verified numeric interpretation.
    """
    from copy import deepcopy
    import json

    def unavailable(reason):
        original = payload if isinstance(payload, dict) else {}
        return {'calculation_version': original.get('calculation_version'),
                'asof': _pricing_date_label(original.get('asof')), 'implied': {},
                'policy_rate': None, 'implied_bp_12m': None, 'implied_cuts_12m': None,
                'implied_cuts_6m': None, 'implied_cut_equivalents_12m': None,
                'implied_cut_equivalents_6m': None, 'dots': [], 'gap': None,
                'path_evidence': {}, 'pricing_comparison_status': 'inconsistent_source_object',
                'consumer_validation': {'status': 'unavailable', 'reason': reason},
                'historical_availability_qualified': False,
                'current_session_freshness': 'not_certified',
                'implied_source_en': None, 'implied_source_zh': None,
                'headline_en': 'Dated pricing comparison unavailable',
                'headline_zh': '有日期的定价比较不可用',
                'read_en': 'Source dates, rate basis or values are inconsistent; no pricing assertion.',
                'read_zh': '源日期、利率基础或数值不一致；不作定价断言。',
                'note_en': 'Internal consistency only; no source authentication or live/decision-time proof.',
                'note_zh': '仅检查内部一致性；不是源认证、实时或决策时点证明。',
                'display_only': True, 'authority': False, 'can_score': False,
                'can_rank': False, 'can_size': False, 'can_gate': False, 'can_trade': False}

    try:
        if not isinstance(payload, dict):
            return unavailable('not_an_object')
        if payload.get('calculation_version') != 'fed_path.date_basis.v2':
            return unavailable('unsupported_calculation_version')
        ref=payload['policy_reference_evidence']; bounds=payload['target_range_evidence']
        evidence=payload['path_evidence']; zq=evidence['zq']; sofr=evidence['sofr']
        if not all(isinstance(v,dict) for v in (ref,bounds,evidence,zq,sofr)):
            return unavailable('invalid_evidence_structure')
        # Dates/bases and redundant outputs are checked below against compute_qualified_pricing's
        # canonical reconstruction. A source may be consistently stale/missing.
        dots=payload.get('dots') or []
        ds=(pd.Series({pd.Timestamp(year=int(d['year']),month=12,day=31):d['median']
                       for d in dots}) if dots else None)
        front=payload.get('front_quote_context') or {}
        rebuilt=compute_qualified_pricing(asof=payload.get('asof'),
            policy_rate=ref.get('value'), policy_asof=ref.get('source_asof'),
            target_low=bounds.get('lower_value'), target_high=bounds.get('upper_value'),
            target_low_asof=bounds.get('lower_asof'), target_high_asof=bounds.get('upper_asof'),
            dot_series=ds, zq_path_row=zq.get('last_observed_path'),
            sofr_path_row=sofr.get('last_observed_path'), zq_path_asof=zq.get('source_asof'),
            sofr_path_asof=sofr.get('source_asof'),
            path_status={'zq':zq.get('status'), 'sofr':sofr.get('status')},
            zq_front_implied=front.get('implied_average_rate'), front_asof=front.get('frame_asof'),
            ntfs=payload.get('ntfs'), curve_tp_adj=payload.get('curve_tp_adj'),
            rate_exp_proxy=payload.get('rate_exp_proxy'),
            cfg={'horizons_m':payload['horizons_m']})
        if rebuilt is None:
            return unavailable('no_reconstructible_evidence')
        protected=('asof','calculation_version','horizons_m','policy_reference_evidence',
                   'target_range_evidence','policy_reference_asof','policy_observation_origin',
                   'policy_rate','target_low','target_high','target_mid','implied','sofr_path',
                   'implied_bp_12m','implied_cuts_12m','implied_cuts_6m',
                   'implied_cut_equivalents_12m','implied_cut_equivalents_6m',
                   'pricing_comparison_status','path_evidence','front_quote_context','dots','gap',
                   'implied_source_en','implied_source_zh','cut_count_interpretation',
                   'gap_unavailable_reasons',
                   'historical_availability_qualified','current_session_freshness',
                   'display_only','authority','can_rank','can_score','can_gate','can_size','can_trade')
        def canonical(obj):
            return json.dumps(obj,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))
        for key in protected:
            if key not in payload or canonical(payload[key]) != canonical(rebuilt[key]):
                return unavailable('inconsistent_'+key)
        rebuilt['built']=payload.get('built')
        rebuilt['consumer_validation']={'status':'internally_consistent',
            'source_authentication':False,'historical_availability_qualified':False}
        return deepcopy(rebuilt)
    except (KeyError,TypeError,ValueError,OverflowError,AttributeError):
        return unavailable('malformed_evidence')



def is_versioned_pricing(payload) -> bool:
    """Typed pricing evidence may never downgrade to the bare legacy contract."""
    if not isinstance(payload, dict):
        return False
    if any(key in payload for key in (
        "qualified_pricing", "calculation_version", "path_evidence",
        "policy_reference_evidence", "target_range_evidence",
        "pricing_comparison_status", "implied_cut_equivalents_12m",
        "implied_cut_equivalents_6m",
    )):
        return True
    if "implied_source_meta" not in payload:
        return False
    meta = payload["implied_source_meta"]
    if not isinstance(meta, dict):
        return True
    if any(key in meta for key in (
        "schema", "selected_strip", "selected_basis", "selected_is_effr",
        "cutoff", "effr_meeting_path",
    )):
        return True
    strips = meta.get("strips")
    if isinstance(strips, dict):
        return any(isinstance(strip, dict) and any(key in strip for key in (
            "observation_time", "rate_index", "averaging_law", "value_state",
        )) for strip in strips.values())
    # Existing untyped rights-only annotations are part of bare legacy input.
    return False


def _pricing_unavailable(payload, reason: str) -> dict:
    out = _validated_date_basis({})
    if isinstance(payload, dict):
        out["asof"] = _pricing_date_label(payload.get("asof"))
        out["calculation_version"] = payload.get("calculation_version")
    out["consumer_validation"]["reason"] = reason
    return out


def validated_pricing_view(payload: dict, *, cutoff=None) -> dict:
    """Validate v2 inputs and retain every applicable existing D0 cutoff refusal.

    The frozen legacy envelope is provenance, not a fallback for missing pricing.
    This checks internal consistency and daily observation boundaries only; it
    never authenticates a source or establishes its historical availability.
    D1 identification and target-basis comparisons remain in their existing owner.
    """
    from copy import deepcopy

    if not isinstance(payload, dict):
        return _pricing_unavailable({}, "not_an_object")
    nested = "qualified_pricing" in payload
    projection = payload.get("qualified_pricing") if nested else payload
    if not isinstance(projection, dict):
        return _pricing_unavailable(payload, "malformed_pricing_projection")
    view = _validated_date_basis(projection)
    if view["consumer_validation"]["status"] != "internally_consistent":
        return view

    meta = payload.get("implied_source_meta")
    if nested or "implied_source_meta" in payload:
        if not isinstance(meta, dict) or meta.get("schema") != _SOURCE_META_SCHEMA:
            return _pricing_unavailable(projection, "source_metadata_unavailable")
        if _pricing_date_label(payload.get("asof")) != view.get("asof"):
            return _pricing_unavailable(projection, "envelope_analysis_date_mismatch")
        if view.get("implied_source_en") is not None:
            strips = meta.get("strips")
            zq = strips.get("zq") if isinstance(strips, dict) else None
            evidence = view["path_evidence"]["zq"]
            if not isinstance(zq, dict):
                return _pricing_unavailable(projection, "zq_source_metadata_unavailable")
            if (meta.get("selected_strip") != "zq"
                    or meta.get("selected_is_effr") is not True
                    or meta.get("selected_basis") != "zq_effr_monthly_average"
                    or zq.get("source") != "rate_futures:ZQ"
                    or zq.get("rate_index") != "EFFR"
                    or zq.get("averaging_law") != "arithmetic_calendar_day"):
                return _pricing_unavailable(projection, "source_basis_mismatch")
            if zq.get("value_state") != "present":
                return _pricing_unavailable(projection, "source_admission_" + str(zq.get("value_state")))
            if (_pricing_date_label(zq.get("observation_time"))
                    != evidence.get("source_asof")):
                return _pricing_unavailable(projection, "source_observation_date_mismatch")
        strips = meta.get("strips") if isinstance(meta.get("strips"), dict) else {}
        evidence = view.get("path_evidence") or {}
        operands = [
            ("zq", (evidence.get("zq") or {}).get("last_observed_path"), strips.get("zq")),
            ("sofr", (evidence.get("sofr") or {}).get("last_observed_path"), strips.get("sofr")),
            ("zq_front", view.get("front_quote_context"), strips.get("zq_front")),
            ("dots", view.get("dots"), meta.get("dots")),
        ]
        for name, value, source in operands:
            if value and isinstance(source, dict) and source.get("value_state") in ("refused", "withheld"):
                return _pricing_unavailable(projection, name + "_source_admission_" + source["value_state"])
        # Preserve the existing provenance, including all D1 fields and unknown
        # clocks. Neither validation nor build time rewrites any of those fields.
        view["implied_source_meta"] = deepcopy(meta)

    limits = [cutoff]
    if isinstance(meta, dict):
        limits.append(meta.get("cutoff"))
    for limit in limits:
        if limit is None:
            continue
        day = _pricing_date_label(limit)
        if day is None:
            return _pricing_unavailable(projection, "invalid_consumer_cutoff")
        if view.get("asof") is None or view["asof"] > day:
            return _pricing_unavailable(projection, "analysis_after_consumer_cutoff")
        for evidence in view["path_evidence"].values():
            if evidence.get("last_observed_path"):
                source_day = _pricing_date_label(evidence.get("source_asof"))
                if source_day is None or source_day > day:
                    return _pricing_unavailable(projection, "path_evidence_after_or_unknown_at_cutoff")
        if view.get("dots"):
            dots_meta = meta.get("dots") if isinstance(meta, dict) else None
            release = dots_meta.get("first_public_evidence") if isinstance(dots_meta, dict) else None
            precision = dots_meta.get("first_public_precision") if isinstance(dots_meta, dict) else None
            if _evidence_later(release, precision, day) is not False:
                return _pricing_unavailable(projection, "dot_evidence_after_or_unknown_at_cutoff")
        front = view.get("front_quote_context")
        if isinstance(front, dict):
            front_day = _pricing_date_label(front.get("frame_asof"))
            if front_day is None or front_day > day:
                return _pricing_unavailable(projection, "front_evidence_after_or_unknown_at_cutoff")
        if view.get("implied_bp_12m") is not None:
            required_dates = (
                view["path_evidence"]["zq"].get("source_asof"),
                view["policy_reference_evidence"].get("source_asof"),
            )
            if any(_pricing_date_label(value) is None or value > day
                   for value in required_dates):
                return _pricing_unavailable(projection, "pricing_evidence_after_or_unknown_at_cutoff")
    return view


def consumer_pricing_view(payload: dict, *, cutoff=None) -> dict:
    """One version boundary for RIC, stance and their pricing-only readers."""
    from copy import deepcopy

    if not isinstance(payload, dict):
        return {}
    if not is_versioned_pricing(payload):
        return deepcopy(payload)
    return validated_pricing_view(payload, cutoff=cutoff)
