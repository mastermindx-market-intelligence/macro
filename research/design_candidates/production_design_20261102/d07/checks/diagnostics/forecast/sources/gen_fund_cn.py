"""Emit <SYM>.fund.json (mastermind.fund/v1, BUILD-SPEC §1.1) for CN A-shares.

Joins the parquets collect_cn_hk_fund.py + collect_cn_deep.py write:
    stmt_income/balance/cashflow.parquet   full whole-market statements, keyed (ts_code, end_date)
    valuation.parquet                      daily_basic snapshot (pe/pb/ps/dv + mktcap)
    daily_basic.parquet                    shares_out / float_shares / mktcap
    financials.parquet                     fina-indicator margins/roe/growth + multiyear series
    dividends.parquet                      per-ticker cash-dividend history
    forecast.parquet                       forecast_vip guidance (预增/预减 …) — §1.1 guidance field
    holders.parquet                        top10 float holders → ownership
    cn_consensus.parquet                   EastMoney bulk consensus EPS/revenue by predict_year
    cn_reports.parquet                     per-ticker research reports (rating + EPS + target price)
    cn_company.parquet                     stock_company profile (website/employees/province/city)
    cn_holdernum.parquet                   stk_holdernumber snapshot (latest filed holder count)
    cn_disclosure.parquet                  disclosure_date → upcoming earnings pre_date/actual_date

CRITICAL judge rulings honoured:
  - gross_profit = total_revenue − oper_cost (营业成本), NOT total_cogs (营业总成本 bundles selling/
    admin/finance and differs by ~40B for Moutai). opex = total_cogs − oper_cost best-effort.
  - quote_currency = stmt_currency = "CNY".
  - Annual periods come from Dec-31 (mmdd == 1231) statement rows; quarterly from the four quarter-ends.
  - estimates.eps_q: null (A-share consensus is annual-only — no quarterly estimates available).
  - analyst rating mapping (FINAL ruling): 买入→strongBuy, 增持→buy, 中性/持有→hold,
    减持→sell, 卖出→strongSell; anything else/blank → uncounted.
  - earnings.q: Q1 EPS as reported; later discrete EPS withheld; compatible additive flows only
    (Q1 as-is, Qn = cum_n − cum_{n-1}); guard nulls.
  - next_date/next_period: from cn_disclosure pre_date or actual_date.
  - beta: computed from OHLC daily returns vs 000001.SS benchmark (250 trading days).
  - profile.founded/hq/website/employees: from cn_company.
  - No inst_pct / insider_pct (no clean source).

Terminal ↔ Tushare symbol mapping: terminal uses .SS (Shanghai); Tushare uses .SH. Handled both ways.

Usage:
    "<Macro Dashboard>/.venv/bin/python" ingest/gen_fund_cn.py [--only 600519.SS,000001.SZ] [--limit N] \
        [--out <dir>]        # default out = terminal/public/data
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import traceback
from pathlib import Path

import pandas as pd

CA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CA_ROOT))
from ingest.earnings_calendar import select_next_earnings_date  # noqa: E402
from ingest.statement_history import merge_statement_history, annual_earnings_from_statements  # noqa: E402
from ingest.cn_statement_rules import (  # noqa: E402
    contiguous_prior, discrete_value, is_quarter_end, normalize_period,
    compatible_cumulative_rows, is_consolidated, retainable_row,
    parse_quarter_label, prior_quarter, quarter_label, report_date,
)
MACRO = Path(os.environ.get("MACRO_REPO") or "/Users/chriswong/Documents/Cluade/Macro Dashboard")
CA = Path(__file__).resolve().parents[1]  # charting-app root (worktree-safe)
TU = MACRO / "data" / "tushare"
CN_SITE = MACRO / "site" / "chinastockdata"
DEFAULT_OUT = CA_ROOT / "terminal" / "public" / "data"

ASOF = pd.Timestamp.today().strftime("%Y-%m-%d")


# ─────────────────────────────── symbol mapping ───────────────────────────────
def term_to_ts(sym: str) -> str:
    """terminal 600519.SS → tushare 600519.SH; .SZ unchanged."""
    return sym[:-3] + ".SH" if sym.endswith(".SS") else sym


def ts_to_term(code: str) -> str:
    return code[:-3] + ".SS" if code.endswith(".SH") else code


def _f(v):
    if v is None:
        return None
    try:
        x = float(v)
        return None if x != x else x
    except (TypeError, ValueError):
        return None


def _num(row, key):
    return _f(row.get(key)) if isinstance(row, dict) else None


# ─────────────────────────────── parquet loaders ───────────────────────────────
def _read(name: str):
    p = TU / name
    if not p.exists():
        return None
    try:
        return pd.read_parquet(p)
    except Exception:
        return None


def load_statements() -> dict:
    """{ts_code: {end_date: row}} per statement kind."""
    out = {}
    for kind in ("income", "balance", "cashflow"):
        df = _read(f"stmt_{kind}.parquet")
        d: dict = {}
        if df is not None:
            for r in df.to_dict("records"):
                code = str(r.get("ts_code") or "")
                end = str(r.get("end_date") or "")
                end = normalize_period(end)
                if code and end and retainable_row(r):
                    d.setdefault(code, {})[end] = r
        out[kind] = d
    return out


def load_map(name: str, key_col: str) -> dict:
    df = _read(name)
    out: dict = {}
    if df is None:
        return out
    for r in df.to_dict("records"):
        k = str(r.get(key_col) or "")
        if k:
            out[k] = r
    return out


def load_dividends() -> dict:
    df = _read("dividends.parquet")
    out: dict = {}
    if df is None:
        return out
    for r in df.to_dict("records"):
        code = str(r.get("ts_code") or "")
        if not code:
            continue
        try:
            out[code] = json.loads(r.get("events_json") or "[]")
        except Exception:
            out[code] = []
    return out


def load_forecast() -> dict:
    """ts_code(terminal .SS) → latest guidance row from forecast.parquet."""
    df = _read("forecast.parquet")
    out: dict = {}
    if df is None:
        return out
    for r in df.to_dict("records"):
        tk = str(r.get("ticker") or "")
        if not tk:
            continue
        cur = out.get(tk)
        if cur is None or str(r.get("ann_date") or "") > str(cur.get("ann_date") or ""):
            out[tk] = r
    return out


def load_holders() -> dict:
    df = _read("holders.parquet")
    out: dict = {}
    if df is None or "holders_json" not in getattr(df, "columns", []):
        return out
    for r in df.to_dict("records"):
        code = str(r.get("ts_code") or "")
        if not code:
            continue
        try:
            out[code] = json.loads(r.get("holders_json") or "[]")
        except Exception:
            out[code] = []
    return out


def load_consensus() -> dict:
    """cn_consensus.parquet → {SECUCODE: {year: row}}.
    SECUCODE is in '000651.SZ' form (exchange-suffixed 6-digit code).
    """
    df = _read("cn_consensus.parquet")
    out: dict = {}
    if df is None:
        return out
    for r in df.to_dict("records"):
        code = str(r.get("SECUCODE") or "")
        yr = r.get("PREDICT_YEAR")
        if not code or yr is None:
            continue
        out.setdefault(code, {})[int(yr)] = r
    return out


def load_reports() -> dict:
    """cn_reports.parquet → {ts_code: [report_row, ...]}."""
    df = _read("cn_reports.parquet")
    out: dict = {}
    if df is None:
        return out
    for r in df.to_dict("records"):
        code = str(r.get("ts_code") or "")
        if not code:
            continue
        try:
            out[code] = json.loads(r.get("reports_json") or "[]")
        except Exception:
            out[code] = []
    return out


def load_company() -> dict:
    """cn_company.parquet → {ts_code: row}."""
    df = _read("cn_company.parquet")
    out: dict = {}
    if df is None:
        return out
    for r in df.to_dict("records"):
        code = str(r.get("ts_code") or "")
        if code:
            out[code] = r
    return out


def load_holdernum() -> dict:
    """cn_holdernum.parquet → {ts_code: holder_nums (int)}."""
    df = _read("cn_holdernum.parquet")
    out: dict = {}
    if df is None:
        return out
    for r in df.to_dict("records"):
        code = str(r.get("ts_code") or "")
        n = r.get("holder_nums")
        if code and n is not None:
            try:
                out[code] = int(float(n))
            except (TypeError, ValueError):
                pass
    return out


def load_disclosure() -> dict:
    """cn_disclosure.parquet → {ts_code: {end_date, pre_date, actual_date}}."""
    df = _read("cn_disclosure.parquet")
    out: dict = {}
    if df is None:
        return out
    for r in df.to_dict("records"):
        code = str(r.get("ts_code") or "")
        if not code:
            continue
        # Keep latest end_date per ticker (the parquet may have multiple periods)
        existing = out.get(code)
        this_end = str(r.get("end_date") or "")
        if existing is None or this_end > str(existing.get("end_date") or ""):
            out[code] = {
                "end_date": this_end,
                "pre_date": str(r.get("pre_date") or ""),
                "actual_date": str(r.get("actual_date") or ""),
            }
    return out


# ─────────────────────────────── statement assembly ───────────────────────────────
def _period_label_annual(end: str) -> str:
    return end[:4]


def _period_label_q(end: str) -> str:
    q = {"03": 1, "06": 2, "09": 3, "12": 4}.get(end[4:6])
    return f"Q{q} {end[:4]}" if q else end[:4]


def _income_block(rows: list[dict]) -> dict:
    """rows = list of income statement dicts oldest→newest. Judge cost-basis ruling applied."""
    def col(key):
        return [_num(r, key) for r in rows]

    total_rev = col("total_revenue")
    revenue = col("revenue")
    oper_cost = col("oper_cost")     # 营业成本 — the correct COGS for gross margin (judge ruling)
    total_cogs = col("total_cogs")   # 营业总成本 — bundles selling/admin/finance; NOT for gross margin

    gross_profit, opex = [], []
    for tr, oc, tc in zip(total_rev, oper_cost, total_cogs):
        gp = (tr - oc) if (tr is not None and oc is not None) else None
        gross_profit.append(gp)
        # opex best-effort: total operating cost minus pure cost of goods
        opex.append((tc - oc) if (tc is not None and oc is not None) else None)

    return {
        "revenue": [tr if tr is not None else rv for tr, rv in zip(total_rev, revenue)],
        "cogs": oper_cost,
        "gross_profit": gross_profit,
        "opex": opex,
        "op_income": col("operate_profit"),
        "nonop_income": [None] * len(rows),
        "pretax_income": col("total_profit"),
        "taxes": col("income_tax"),
        "net_income": col("n_income_attr_p"),
        "eps_basic": col("basic_eps"),
        "eps_diluted": col("diluted_eps"),
        "ebitda": col("ebitda"),
    }


def _balance_block(rows: list[dict]) -> dict:
    def col(key):
        return [_num(r, key) for r in rows]

    st_borr = col("st_borr")
    lt_borr = col("lt_borr")
    bond = col("bond_payable")
    cash = col("money_cap")
    debt = []
    for s, l, b in zip(st_borr, lt_borr, bond):
        parts = [x for x in (s, l, b) if x is not None]
        debt.append(sum(parts) if parts else None)
    net_debt = [(d - c) if (d is not None and c is not None) else None for d, c in zip(debt, cash)]
    return {
        "assets": col("total_assets"),
        "assets_st": col("total_cur_assets"),
        "assets_lt": col("total_nca"),
        "liabilities": col("total_liab"),
        "liab_st": col("total_cur_liab"),
        "liab_lt": col("total_ncl"),
        "equity": col("total_hldr_eqy_inc_min_int"),
        "debt": debt,
        "cash": cash,
        "net_debt": net_debt,
    }


def _cashflow_block(rows: list[dict]) -> dict:
    def col(key):
        return [_num(r, key) for r in rows]

    cfo = col("n_cashflow_act")
    capex = col("c_pay_acq_const_fiolta")
    fcf_col = col("free_cashflow")
    fcf = []
    for f, o, c in zip(fcf_col, cfo, capex):
        if f is not None:
            fcf.append(f)
        elif o is not None and c is not None:
            fcf.append(o - c)   # capex is a positive outflow figure
        else:
            fcf.append(None)
    return {
        "cfo": cfo,
        "cfi": col("n_cashflow_inv_act"),
        "cff": col("n_cash_flows_fnc_act"),
        "capex": [(-c if c is not None else None) for c in capex],   # sign as outflow
        "fcf": fcf,
    }


def _assemble_period(stmts: dict, code: str, ends: list[str], labeler) -> dict | None:
    """Build one {periods, period_end, income, balance, cashflow} block for the given end-dates."""
    inc = stmts["income"].get(code, {})
    bal = stmts["balance"].get(code, {})
    cf = stmts["cashflow"].get(code, {})
    ends = [e for e in ends if e in inc or e in bal or e in cf]
    if not ends:
        return None
    ends = sorted(ends)          # oldest→newest
    inc_rows = [inc.get(e, {}) for e in ends]
    bal_rows = [bal.get(e, {}) for e in ends]
    cf_rows = [cf.get(e, {}) for e in ends]
    return {
        "periods": [labeler(e) for e in ends],
        "period_end": [f"{e[:4]}-{e[4:6]}-{e[6:8]}" for e in ends],
        "income": _income_block(inc_rows),
        "balance": _balance_block(bal_rows),
        "cashflow": _cashflow_block(cf_rows),
        "period_provenance": {
            family: [{
                "origin": "source_cache",
                "scope": "consolidated_type1" if is_consolidated(row) else "legacy_unknown",
                "acquired_at": row.get("_acquired_at") if isinstance(row.get("_acquired_at"), str) else None,
                "filing_date": report_date(row.get("ann_date"), row.get("f_ann_date")),
                "revision_conflict": bool(row.get("_revision_conflict")) if row.get("_revision_conflict") is True else False,
            } for row in rows]
            for family, rows in (("income", inc_rows), ("balance", bal_rows), ("cashflow", cf_rows))
        },
    }


def build_statements(stmts: dict, code: str) -> dict:
    inc = stmts["income"].get(code, {})
    bal = stmts["balance"].get(code, {})
    cf = stmts["cashflow"].get(code, {})
    all_ends = sorted(set(inc) | set(bal) | set(cf))
    annual_ends = [e for e in all_ends if e[4:8] == "1231"][-6:]
    q_ends = all_ends[-12:]
    return {
        "annual": _assemble_period(stmts, code, annual_ends, _period_label_annual),
        "quarterly": _assemble_period(stmts, code, q_ends, _period_label_q),
    }


# ─────────────────────────────── other sections ───────────────────────────────
def build_ratios(vrow, frow, annual) -> dict:
    """current live ratios from daily_basic; annual pe/ps/pb series unavailable (single snapshot)."""
    cur = {"pe_ttm": None, "pe_fwd": None, "ps": None, "pb": None, "ev_ebitda": None,
           "div_yield": None, "payout": None, "gross_margin": None, "net_margin": None,
           "roe": None, "roa": None, "debt_to_equity": None, "current_ratio": None}
    if vrow:
        cur["pe_ttm"] = _num(vrow, "pe_ttm") if _num(vrow, "pe_ttm") is not None else _num(vrow, "pe")
        cur["ps"] = _num(vrow, "ps_ttm")
        cur["pb"] = _num(vrow, "pb")
        # UNIT RULING: Tushare daily_basic dv_ttm is percent-form (4.258 == 4.258%). The contract stores
        # div_yield as a 0..1 FRACTION → divide by 100 (→ 0.04258).
        dv = _num(vrow, "dv_ttm")
        cur["div_yield"] = dv / 100.0 if dv is not None else None
    if frow:
        gms = frow.get("gross_margin_series")
        cur["gross_margin"] = _f(frow.get("gross_margin")) if frow.get("gross_margin") is not None else (
            _f(gms[-1]) if isinstance(gms, (list, tuple)) and len(gms) else None)
        cur["net_margin"] = _f(frow.get("net_margin"))
        cur["roe"] = _f(frow.get("roe"))
    # derive current_ratio & debt/equity from latest annual balance
    if annual and annual.get("balance"):
        b = annual["balance"]

        def last(key):
            v = b.get(key)
            return v[-1] if isinstance(v, list) and v and v[-1] is not None else None
        ast, lst = last("assets_st"), last("liab_st")
        if ast and lst:
            cur["current_ratio"] = round(ast / lst, 2)
        debt, eq = last("debt"), last("equity")
        if debt is not None and eq:
            cur["debt_to_equity"] = round(debt / eq, 2)
    periods = (annual or {}).get("periods") or []
    empty = [None] * len(periods)   # null-pad per-period series to len(periods) (contract §1.1)
    return {"periods": periods,
            "pe": list(empty), "ps": list(empty), "pb": list(empty), "pcf": list(empty),
            "ev": list(empty), "ev_ebitda": list(empty), "current": cur}


def build_stats(vrow, dbrow, holdernum_map: dict | None = None,
                sym: str | None = None, data_dir: "Path | None" = None) -> dict:
    def yi_to_raw(v):   # valuation.parquet mktcap is in 亿元 (1e8)
        return round(v * 1e8) if v is not None else None
    mktcap = shares = flt = None
    if dbrow:   # daily_basic: total_mv/circ_mv in 万元 (1e4); total_share/float_share in 万股 (1e4)
        mktcap = round(_num(dbrow, "total_mv") * 1e4) if _num(dbrow, "total_mv") else None
        shares = round(_num(dbrow, "total_share") * 1e4) if _num(dbrow, "total_share") else None
        flt = round(_num(dbrow, "float_share") * 1e4) if _num(dbrow, "float_share") else None
    if mktcap is None and vrow:
        mktcap = yi_to_raw(_num(vrow, "total_mv_yi"))
    # num_holders from cn_holdernum (latest filed quarter-end)
    num_holders = None
    if holdernum_map and sym:
        ts = term_to_ts(sym)
        num_holders = holdernum_map.get(ts)
    # beta: computed from OHLC JSON vs 000001.SS benchmark (250 trading days).
    # Always read OHLC from DEFAULT_OUT (terminal/public/data) regardless of the
    # --out target dir, so that staging/temp-dir runs do not silently null beta.
    beta = None
    if sym:
        beta = _compute_beta(sym, DEFAULT_OUT)
    return {"mktcap": mktcap, "shares_out": shares, "float_shares": flt, "inst_pct": None,
            "insider_pct": None, "beta": beta, "num_holders": num_holders}


def build_dividends(events: list) -> dict:
    events = events or []
    yr = None
    if events:
        # trailing 12m sum of amounts
        last_ex = events[-1]["ex"]
        if last_ex:
            cutoff = f"{int(last_ex[:4]) - 1}{last_ex[4:]}"
            yr = round(sum(e["amount"] for e in events if e["ex"] and e["ex"] >= cutoff), 4)
    return {"never_paid": len(events) == 0, "yield_ttm": None, "payout_ratio": None,
            "events": [{"ex": e["ex"], "amount": e["amount"], "pay": e.get("pay"),
                        "type": e.get("type", "regular")} for e in events],
            "splits": [], "_ttm_amount": yr}


def build_guidance(frow) -> dict | None:
    if not frow:
        return None
    return {"type": frow.get("type"),
            "chg_min": _f(frow.get("p_change_min")), "chg_max": _f(frow.get("p_change_max")),
            "period": str(frow.get("end_date") or "")}


def build_ownership(holders: list) -> dict:
    top = []
    for h in (holders or [])[:10]:
        top.append({"name": h.get("name"), "pct": _f(h.get("ratio")), "value": None})
    return {"free_float_pct": None, "closely_held_pct": None, "top_inst": top}


# ─── EastMoney analyst rating mapping (FINAL ruling) ───────────────────────
_RATING_MAP: dict[str, str] = {
    "买入": "strongBuy",
    "强烈推荐": "strongBuy",
    "强推": "strongBuy",
    "增持": "buy",
    "推荐": "buy",
    "中性": "hold",
    "持有": "hold",
    "审慎推荐": "hold",
    "减持": "sell",
    "卖出": "strongSell",
    "回避": "strongSell",
}
_RATING_LABEL: dict[str, str] = {
    "strongBuy": "Strong buy",
    "buy": "Buy",
    "hold": "Hold",
    "sell": "Sell",
    "strongSell": "Strong sell",
}
_RATING_WEIGHT: dict[str, int] = {
    "strongBuy": 5, "buy": 4, "hold": 3, "sell": 2, "strongSell": 1,
}


def _secucode_to_ts(secucode: str) -> str:
    """'000651.SZ' → '000651.SZ'; '600519.SH' → '600519.SH' (Tushare form)."""
    return secucode  # already in Tushare form from EastMoney datacenter


def build_estimates(ts_code: str, consensus_map: dict, reports_map: dict,
                    stmts: dict, sym: str) -> dict | None:
    """Build estimates block from EastMoney consensus + per-report EPS aggregation.

    consensus_map: {SECUCODE → {year → row}}  (SECUCODE uses Tushare exchange suffix)
    reports_map:   {ts_code → [report_row, ...]}

    Revenue unit: CNY raw (TOTAL_OPERATE_INCOME from EastMoney is already in CNY units).
    Sanity: Moutai 2026 rev consensus ~1.8e11.

    Returns None when no consensus data is available for this ticker.
    """
    # EastMoney SECUCODE is ts_code form (e.g. '600519.SH') — map directly
    cdata = consensus_map.get(ts_code) or {}
    reports = reports_map.get(ts_code) or []

    years = sorted(yr for yr in (2026, 2027, 2028) if yr in cdata)
    if not years:
        return None

    eps_avg, rev_avg = [], []
    eps_high, eps_low, eps_n = [], [], []
    rev_high, rev_low, rev_n = [], [], []

    # Per-report EPS aggregation per fiscal year (reports carry this-year / next-year EPS)
    # Determine which year is "this year" from today
    today_year = dt.date.today().year

    def _report_eps_for_year(yr: int) -> list:
        """Extract per-report EPS estimates for a given fiscal year.

        EastMoney semantics: predictThisYearEps is the estimate for the fiscal
        year that was current AT TIME OF PUBLICATION; predictNextYearEps is for
        the following fiscal year.  Therefore, for target fiscal year `yr`:
          - take predictThisYearEps  when pub_year == yr   (report published in yr)
          - take predictNextYearEps  when pub_year == yr-1 (report published a year earlier)
          - skip all other reports
        Using today_year for the slot (the previous bug) contaminated the 2026
        pool with 2025-published nextYear values and gave wrong n/high/low.
        """
        result = []
        for r in reports:
            pub = str(r.get("publishDate") or "")[:4]
            if not pub.isdigit():
                continue
            pub_year = int(pub)
            if pub_year == yr:
                v = _f(r.get("predictThisYearEps"))
            elif pub_year == yr - 1:
                v = _f(r.get("predictNextYearEps"))
            else:
                v = None
            if v is not None:
                result.append(v)
        return result

    for yr in years:
        row = cdata[yr]
        avg = _f(row.get("EPS"))
        rev = _f(row.get("TOTAL_OPERATE_INCOME"))
        eps_avg.append(avg)
        rev_avg.append(rev)

        per_report = _report_eps_for_year(yr)
        if per_report:
            eps_high.append(max(per_report))
            eps_low.append(min(per_report))
            eps_n.append(len(per_report))
            rev_high.append(None)
            rev_low.append(None)
            rev_n.append(None)
        else:
            eps_high.append(None)
            eps_low.append(None)
            eps_n.append(None)
            rev_high.append(None)
            rev_low.append(None)
            rev_n.append(None)

    # Growth: FY1 consensus EPS vs latest annual actual EPS
    eps_yoy = rev_yoy = None
    inc = stmts["income"].get(ts_code, {})
    annual_eps = [(e, _f(r.get("basic_eps"))) for e, r in sorted(inc.items())
                  if e[4:8] == "1231" and _f(r.get("basic_eps")) is not None]
    if annual_eps and eps_avg:
        last_actual_eps = annual_eps[-1][1]
        fy1_eps = eps_avg[0]
        if last_actual_eps and last_actual_eps != 0 and fy1_eps is not None:
            eps_yoy = round((fy1_eps - last_actual_eps) / abs(last_actual_eps), 6)

    annual_rev = [(e, _f(r.get("total_revenue"))) for e, r in sorted(inc.items())
                  if e[4:8] == "1231" and _f(r.get("total_revenue")) is not None]
    if annual_rev and rev_avg:
        last_actual_rev = annual_rev[-1][1]
        fy1_rev = rev_avg[0]
        if last_actual_rev and last_actual_rev != 0 and fy1_rev is not None:
            rev_yoy = round((fy1_rev - last_actual_rev) / abs(last_actual_rev), 6)

    return {
        "eps_fy": {
            "periods": [str(yr) for yr in years],
            "avg": eps_avg,
            "high": eps_high,
            "low": eps_low,
            "n": eps_n,
        },
        "rev_fy": {
            "periods": [str(yr) for yr in years],
            "avg": rev_avg,
            "high": rev_high,
            "low": rev_low,
            "n": rev_n,
        },
        "eps_q": None,   # A-share consensus is annual-only — honest null
        "growth": {"eps_yoy": eps_yoy, "rev_yoy": rev_yoy},
    }


def build_analyst(ts_code: str, reports_map: dict) -> dict | None:
    """Build analyst block from per-ticker EastMoney reports.

    Rating mapping (FINAL ruling): 买入→strongBuy, 增持→buy, 中性/持有→hold,
    减持→sell, 卖出→strongSell; blank/other → uncounted.
    rating_label: plain-word label of the weighted-mode bucket.
    target: {mean, high, low, n} from indvAimPriceT when present; null if n=0.
    """
    reports = reports_map.get(ts_code) or []
    if not reports:
        return None

    dist: dict[str, int] = {"strongBuy": 0, "buy": 0, "hold": 0, "sell": 0, "strongSell": 0}
    total_weight = 0
    weighted_sum = 0
    targets = []

    for r in reports:
        name = str(r.get("emRatingName") or "").strip()
        bucket = _RATING_MAP.get(name)
        if bucket:
            dist[bucket] += 1
            w = _RATING_WEIGHT[bucket]
            total_weight += w
            weighted_sum += w
        aim = _f(r.get("indvAimPriceT"))
        if aim is not None and aim > 0:
            targets.append(aim)

    total = sum(dist.values())
    if total == 0:
        return None

    # Weighted mode: bucket with highest weight score
    mode_bucket = max(
        (b for b in dist if dist[b] > 0),
        key=lambda b: dist[b] * _RATING_WEIGHT[b],
        default="hold"
    )
    rating_label = _RATING_LABEL.get(mode_bucket, "Hold")

    target = None
    if targets:
        target = {
            "mean": round(sum(targets) / len(targets), 4),
            "high": max(targets),
            "low": min(targets),
            "n": len(targets),
        }

    return {
        "dist": dist,
        "rating_label": rating_label,
        "target": target,
    }


def build_earnings_q(ts_code: str, stmts: dict, disclosure_map: dict) -> list[dict]:
    """Build earnings.q from the last 8 fiscal quarters of cumulative income rows.

    Two quantities, two rules, because they are different things:

    * EPS is a WEIGHTED-AVERAGE per-share figure for the cumulative year-to-date window, and
      every filing uses a different share denominator - the H1 report divides six months of
      earnings by a six-month weighted share count, the Q1 report divides three months by a
      three-month one. Their difference is therefore NOT the second quarter. Only Q1, where the
      cumulative window IS the quarter, yields a discrete figure straight from the income
      statement. Q2..Q4 stay null and say why in `eps_basis`.

    * Revenue and net income ARE additive, so they may be differenced - but only against the
      IMMEDIATELY preceding quarter of the same fiscal year. A missing Q1 leaves Q2 without a
      base, and Q3 must not borrow Q2 in its place.

    This matches `discreteQuarters` in terminal/lib/finStatementMath.ts, which already withholds
    non-differenceable YTD EPS on the statements surface; the producer no longer contradicts it.

    THE DEFECT THIS REPLACES: the old loop treated `i == 0` - the first row *present* in the
    cache - as the first quarter. When Q1 was missing, Q2 took that slot and the six-month
    year-to-date total was published as "Q2", with no way for a reader to tell. Every row now
    carries `eps_basis` / `rev_basis`, so a filed figure and a withheld one are distinguishable
    on their face. Missing stays None; it is never coerced to 0.
    """
    inc = stmts["income"].get(ts_code, {})
    if not inc:
        return []

    q_ends = sorted(e for e in inc if is_quarter_end(e))
    present = [normalize_period(e) for e in q_ends]

    rows: list[dict] = []
    for e in q_ends:
        period = normalize_period(e)
        r = inc.get(e) or inc.get(period) or {}
        base_end = contiguous_prior(present, period)
        prev = (inc.get(base_end) or {}) if base_end else {}
        compatible = compatible_cumulative_rows(r, prev)
        if not compatible:
            prev = {}

        disc_eps, eps_basis = discrete_value("basic_eps", period, _f(r.get("basic_eps")), None)
        disc_rev, rev_basis = discrete_value(
            "total_revenue", period, _f(r.get("total_revenue")), _f(prev.get("total_revenue")))
        disc_ni, ni_basis = discrete_value(
            "n_income_attr_p", period, _f(r.get("n_income_attr_p")), _f(prev.get("n_income_attr_p")))

        rows.append({
            "period": quarter_label(period),
            "end": f"{period[:4]}-{period[4:6]}-{period[6:8]}",
            "report_date": None,  # a revised filing date is not the original earnings release
            "filing_date": report_date(r.get("ann_date"), r.get("f_ann_date")),
            "source_scope": "consolidated_type1" if is_consolidated(r) else "legacy_unknown",
            "eps_a": round(disc_eps, 4) if disc_eps is not None else None,
            "rev_a": round(disc_rev) if disc_rev is not None else None,
            "eps_e": None,
            "rev_e": None,
            "surp_pct": None,
            # Provenance per cell, so no consumer has to infer which rows are filings and which
            # are differences. Additive to the contract: existing readers ignore unknown keys.
            "eps_basis": eps_basis,
            "rev_basis": rev_basis,
            "net_income": round(disc_ni) if disc_ni is not None else None,
            "net_income_basis": ni_basis,
        })

    return rows[-8:]


def build_earnings_fy(ts_code: str, stmts: dict) -> list[dict]:
    """Last 5 annual EPS from Dec-31 rows."""
    inc = stmts["income"].get(ts_code, {})
    annual_ends = sorted(e for e in inc if e[4:8] == "1231")[-5:]
    rows = []
    for e in annual_ends:
        r = inc.get(e, {})
        eps = _f(r.get("basic_eps"))
        rev = _f(r.get("total_revenue"))
        rows.append({
            "period": e[:4],
            "eps_a": round(eps, 4) if eps is not None else None,
            "rev_a": round(rev) if rev is not None else None,
            "eps_e": None,
            "rev_e": None,
            "surp_pct": None,
        })
    return rows


def _next_earnings_info(ts_code: str, disclosure_map: dict) -> tuple[str | None, str | None]:
    """Return (next_date YYYY-MM-DD, next_period label) from disclosure_map."""
    rec = disclosure_map.get(ts_code)
    if not rec:
        return None, None
    end_date = rec.get("end_date") or ""
    pre = rec.get("pre_date") or ""
    actual = rec.get("actual_date") or ""
    # Prefer actual_date if available, else pre_date
    date_str = actual.strip() if actual.strip() else pre.strip()
    if not date_str:
        return None, None
    # Format date
    if len(date_str) == 8 and date_str.isdigit():
        date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    else:
        date_fmt = date_str[:10]
    # Build period label from end_date
    period = None
    if len(end_date) >= 8 and end_date[:8].isdigit():
        yr, mmdd = end_date[:4], end_date[4:8]
        q = {"0331": 1, "0630": 2, "0930": 3, "1231": 4}.get(mmdd)
        period = f"Q{q} {yr}" if q else yr
    # `actual_date` is the day a report was actually filed, i.e. necessarily in the past;
    # `pre_date` is a forecast. Neither is a "next" date until proven present-or-future.
    upcoming = select_next_earnings_date(date_fmt)
    return (upcoming, period) if upcoming else (None, None)


def _compute_beta(sym: str, ohlc_dir: "Path") -> float | None:
    """Compute beta from 250-day daily returns vs 000001.SS benchmark.

    Benchmark source priority:
      1. MACRO/data/tushare/benchmark_000001SS.json  (pre-built Tushare index_daily bars)
      2. ohlc_dir / '000001.SS.json'                (fallback: app OHLC file if present)

    ohlc_dir must be terminal/public/data so sym_path resolves correctly;
    the benchmark is loaded from the data dir regardless of --out target.

    Bars format: [date, open, high, low, close, volume]
    """
    # Benchmark: prefer the dedicated Tushare index file; fall back to app OHLC
    _bench_candidates = [
        MACRO / "data" / "tushare" / "benchmark_000001SS.json",
        ohlc_dir / "000001.SS.json",
    ]
    bench_path = next((p for p in _bench_candidates if p.exists()), None)
    sym_path = ohlc_dir / f"{sym}.json"
    if bench_path is None or not sym_path.exists():
        return None
    try:
        bench_bars = json.loads(bench_path.read_text()).get("bars") or []
        sym_bars = json.loads(sym_path.read_text()).get("bars") or []
    except Exception:
        return None
    if not bench_bars or not sym_bars:
        return None
    # Build date→close dicts; bars[4] is close
    def _close_map(bars):
        m = {}
        for b in bars:
            if len(b) >= 5:
                try:
                    m[b[0]] = float(b[4])
                except (TypeError, ValueError):
                    pass
        return m

    bmap = _close_map(bench_bars)
    smap = _close_map(sym_bars)
    dates = sorted(set(bmap) & set(smap))[-251:]   # last 251 common dates → 250 returns
    if len(dates) < 50:
        return None
    brets = [(bmap[dates[i]] / bmap[dates[i - 1]]) - 1 for i in range(1, len(dates))]
    srets = [(smap[dates[i]] / smap[dates[i - 1]]) - 1 for i in range(1, len(dates))]
    n = len(brets)
    if n < 20:
        return None
    mean_b = sum(brets) / n
    mean_s = sum(srets) / n
    cov = sum((srets[i] - mean_s) * (brets[i] - mean_b) for i in range(n)) / n
    var_b = sum((b - mean_b) ** 2 for b in brets) / n
    if var_b == 0:
        return None
    return round(cov / var_b, 3)


def build_profile(src: dict, company_row: dict | None = None) -> dict:
    fu = src.get("fundamentals") or {}
    d = fu.get("description")
    desc = d.get("main_business") if isinstance(d, dict) else d
    website = employees = founded = hq = None
    if company_row:
        website = company_row.get("website") or None
        emp = company_row.get("employees")
        employees = int(emp) if emp is not None and emp == emp else None  # NaN guard
        sd = str(company_row.get("setup_date") or "")
        if len(sd) == 8 and sd.isdigit():
            founded = f"{sd[:4]}-{sd[4:6]}-{sd[6:8]}"
        prov = str(company_row.get("province") or "").strip()
        city = str(company_row.get("city") or "").strip()
        hq = f"{prov} {city}".strip() if prov or city else None
        # Use introduction as fallback description if we have no main_business
        if not desc:
            intro = company_row.get("introduction")
            desc = intro if intro else None
    return {"website": website, "employees": employees, "sector": src.get("sector"),
            "industry": None, "description": desc, "founded": founded, "hq": hq}


# ─────────────────────────────── emitter ───────────────────────────────
def build_fund(sym: str, src: dict, stmts, vmap, dbmap, fmap, divmap, fcmap, hmap,
               consensus_map=None, reports_map=None, company_map=None,
               holdernum_map=None, disclosure_map=None, data_dir=None) -> dict:
    code = term_to_ts(sym)          # tushare code (.SH/.SZ)
    statements = build_statements(stmts, code)
    annual = statements.get("annual")
    vrow = vmap.get(code) or vmap.get(sym)
    dbrow = dbmap.get(code)
    frow = fmap.get(code) or fmap.get(sym)
    events = divmap.get(code, [])
    fcrow = fcmap.get(sym) or fcmap.get(ts_to_term(code))
    holders = hmap.get(code, [])
    company_row = (company_map or {}).get(code)

    dividends = build_dividends(events)
    ttm = dividends.pop("_ttm_amount", None)

    # Earnings block: discrete quarterly EPS + annual EPS + next date from disclosure
    earnings_q = build_earnings_q(code, stmts, disclosure_map or {})
    earnings_fy = build_earnings_fy(code, stmts)
    next_date, next_period = _next_earnings_info(code, disclosure_map or {})

    # Estimates from EastMoney consensus + reports
    estimates = None
    estimates_src = None
    if consensus_map is not None and reports_map is not None:
        estimates = build_estimates(code, consensus_map, reports_map, stmts, sym)
        if estimates is not None:
            estimates_src = "eastmoney"

    # Analyst from per-ticker reports
    analyst = None
    if reports_map is not None:
        analyst = build_analyst(code, reports_map)

    fund = {
        "schema": "mastermind.fund/v1",
        "ticker": sym, "asof": src.get("asof") or ASOF,
        "quote_currency": "CNY", "stmt_currency": "CNY",
        "src": {"statements": "tushare",
                "estimates": estimates_src,
                "dividends": "tushare" if events else None},
        "profile": build_profile(src, company_row),
        "stats": build_stats(vrow, dbrow, holdernum_map=holdernum_map, sym=sym, data_dir=data_dir),
        "statements": {"annual": annual, "quarterly": statements.get("quarterly")},
        "ratios": build_ratios(vrow, frow, annual),
        "earnings": {
            "next_date": next_date,
            "next_period": next_period,
            "next_eps_est": None,
            "next_rev_est": None,
            "q": earnings_q,
            "fy": earnings_fy,
        },
        "estimates": estimates,
        "analyst": analyst,
        "dividends": dividends,
        "ownership": build_ownership(holders),
        "guidance": build_guidance(fcrow),
        "segments": None,
    }
    if ttm is not None:
        fund["dividends"]["yield_ttm"] = None   # need spot price to annualize; left null (raw events carry amounts)
    return fund


def cn_universe() -> list[str]:
    # Universe = the terminal manifest's CN symbols (what the app actually serves).
    # The site/chinastockdata JSON is OPTIONAL enrichment — it must not gate the
    # universe (the R2 migration untracked those files; the dir can be empty).
    man = CA / "terminal" / "public" / "data" / "manifest.json"
    out: list[str] = []
    if man.exists():
        try:
            symbols = json.loads(man.read_text()).get("symbols", {})
            out = [s for s in symbols if s.endswith((".SS", ".SZ"))]
        except Exception:
            out = []
    if not out:  # fallback: site glob (legacy behavior)
        out = [p.name[:-5] for p in CN_SITE.glob("*.json") if p.name[:-5].endswith((".SS", ".SZ"))]
    return sorted(set(out))


def _arg(argv, flag, default=None):
    return argv[argv.index(flag) + 1] if flag in argv else default


def atomic_write(dest: Path, text: str) -> None:
    """Write via tmp+rename so a kill mid-write never leaves a truncated fund.json."""
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, dest)


# ─────────────────────────────── merge-mode helpers ───────────────────────────────

def _nonempty(v) -> bool:
    """True when a JSON value is meaningfully non-null/non-empty."""
    if v is None:
        return False
    if isinstance(v, list):
        return len(v) > 0
    if isinstance(v, dict):
        return bool(v)
    return True


def _load_existing(dest: Path) -> dict | None:
    """Load an existing fund.json if present; return None on any failure."""
    if not dest.exists():
        return None
    try:
        return json.loads(dest.read_text())
    except Exception:
        return None


def _earnings_from_existing_stmts(existing: dict, disclosure_map: dict, ts_code: str) -> tuple[list, list, str | None, str | None]:
    """Derive earnings.q and earnings.fy from the existing fund.json's statements block.

    Used when stmt parquets are absent on this machine (fresh parquet-derived values are empty).
    Returns (q_rows, fy_rows, next_date, next_period).

    earnings.q: the SAME quarter rules as build_earnings_q, re-derived from the published
    statements block (labels 'Q1 2023', 'Q2 2023', …) because only the label survives a round
    trip through fund.json. EPS is therefore a Q1-only figure here too — weighted-average
    per-share values are never differenced — while revenue and net income are differenced only
    against the immediately preceding quarter of the same fiscal year. Same 8-quarter cap.

    This function used to carry its own copy of the differencing loop, which is how the same
    defect existed twice; both sites now call the shared rules in ingest/cn_statement_rules.py.

    earnings.fy: last 5 annual EPS from statements.annual income.eps_basic.
    """
    stmts = (existing or {}).get("statements") or {}
    q_rows: list[dict] = []
    fy_rows: list[dict] = []

    # ── quarterly earnings ────────────────────────────────────────────────────
    qstmt = stmts.get("quarterly")
    if qstmt:
        periods = qstmt.get("periods") or []
        period_ends = qstmt.get("period_end") or []
        inc = qstmt.get("income") or {}
        eps_list = inc.get("eps_basic") or []
        rev_list = inc.get("revenue") or []
        # Pad to same length
        n = len(periods)
        eps_list = (eps_list + [None] * n)[:n]
        rev_list = (rev_list + [None] * n)[:n]

        # Parse period label → (fiscal_year, quarter_num). Only the label survives in a published
        # fund.json, so the same quarter rules are applied by (year, quarter) identity.
        # Group by fiscal year, preserving index order.
        from collections import defaultdict
        by_year: dict = defaultdict(list)
        by_identity: dict[tuple[str, int], int] = {}
        for i, p in enumerate(periods):
            yr, qn = parse_quarter_label(p)
            if yr and qn:
                by_year[yr].append((i, qn))
                by_identity[(yr, qn)] = i

        ni_list = (inc.get("net_income") or [])
        ni_list = (ni_list + [None] * n)[:n]

        for yr in sorted(by_year):
            for i, qn in sorted(by_year[yr], key=lambda x: x[1]):
                cum_eps = _f(eps_list[i]) if i < len(eps_list) else None
                cum_rev = _f(rev_list[i]) if i < len(rev_list) else None
                cum_ni = _f(ni_list[i]) if i < len(ni_list) else None
                end_str = period_ends[i] if i < len(period_ends) else None

                # The differencing base is the IMMEDIATELY preceding quarter, looked up by
                # identity rather than by position. The old `rank == 0` test meant "first row
                # present", so a missing Q1 published the H1 cumulative total as "Q2".
                prev_i = by_identity.get(prior_quarter(yr, qn))
                prev_eps = _f(eps_list[prev_i]) if prev_i is not None and prev_i < len(eps_list) else None
                prev_rev = None  # retained legacy revision/scope is unqualified
                prev_ni = None  # retained legacy revision/scope is unqualified

                # EPS is a weighted-average per-share figure and is never differenced;
                # revenue and net income are additive and are, but only across a contiguous
                # quarter boundary of the same fiscal year.
                disc_eps, eps_basis = discrete_value("basic_eps", qn, cum_eps, prev_eps)
                disc_rev, rev_basis = discrete_value("total_revenue", qn, cum_rev, prev_rev)
                disc_ni, ni_basis = discrete_value("n_income_attr_p", qn, cum_ni, prev_ni)

                q_rows.append({
                    "period": periods[i],
                    "end": end_str,
                    "report_date": None,
                    "eps_a": round(disc_eps, 4) if disc_eps is not None else None,
                    "rev_a": round(disc_rev) if disc_rev is not None else None,
                    "eps_e": None,
                    "rev_e": None,
                    "surp_pct": None,
                    "eps_basis": eps_basis,
                    "rev_basis": rev_basis,
                    "net_income": round(disc_ni) if disc_ni is not None else None,
                    "net_income_basis": ni_basis,
                    "actuals_provenance": ((qstmt.get("period_provenance") or {}).get("income") or
                                           [{}] * n)[i],
                })
        q_rows = q_rows[-8:]

    # ── annual earnings ───────────────────────────────────────────────────────
    astmt = stmts.get("annual")
    if astmt:
        a_periods = astmt.get("periods") or []
        a_inc = astmt.get("income") or {}
        a_eps = a_inc.get("eps_basic") or []
        a_rev = a_inc.get("revenue") or []
        n = len(a_periods)
        a_eps = (a_eps + [None] * n)[:n]
        a_rev = (a_rev + [None] * n)[:n]
        for i, yr_label in enumerate(a_periods[-5:]):
            real_i = i + max(0, n - 5)
            eps_v = _f(a_eps[real_i]) if real_i < len(a_eps) else None
            rev_v = _f(a_rev[real_i]) if real_i < len(a_rev) else None
            fy_rows.append({
                "period": yr_label,
                "eps_a": round(eps_v, 4) if eps_v is not None else None,
                "rev_a": round(rev_v) if rev_v is not None else None,
                "eps_e": None,
                "rev_e": None,
                "surp_pct": None,
            })

    # ── next earnings date from disclosure_map (live source; preserve from existing as fallback) ──
    next_date, next_period = _next_earnings_info(ts_code, disclosure_map)
    if not next_date:
        existing_earn = (existing or {}).get("earnings") or {}
        # Re-prove the preserved date against today; never inherit a stale "next".
        next_date = select_next_earnings_date(existing_earn.get("next_date"))
        next_period = existing_earn.get("next_period") if next_date else None

    return q_rows, fy_rows, next_date, next_period


def _statement_freshness(fund: dict) -> dict:
    """Coverage by statement family; build time and source acquisition stay separate."""
    sections = {}
    for family in ("income", "balance", "cashflow"):
        latest = qualified = acquired = None
        for basis in ("annual", "quarterly"):
            block = (fund.get("statements") or {}).get(basis) or {}
            ends = block.get("period_end") or []
            meta = (block.get("period_provenance") or {}).get(family) or []
            columns = block.get(family) or {}
            for index, end in enumerate(ends):
                if not any(index < len(values) and values[index] is not None for values in columns.values()):
                    continue
                latest = max(latest or end, end)
                provenance = meta[index] if index < len(meta) else {}
                if provenance.get("scope") == "consolidated_type1" and not provenance.get("revision_conflict"):
                    qualified = max(qualified or end, end)
                stamp = provenance.get("acquired_at")
                if stamp:
                    acquired = max(acquired or stamp, stamp)
        sections[family] = {"latest_report_period": latest, "latest_qualified_report_period": qualified,
                            "latest_acquired_at": acquired}
    reported = [value["latest_report_period"] for value in sections.values() if value["latest_report_period"]]
    qualified = [value["latest_qualified_report_period"] for value in sections.values()]
    return {
        "latest_report_period": max(reported) if reported else None,
        "latest_report_period_semantics": "newest_observation_in_any_statement",
        "oldest_latest_qualified_report_period": min(qualified) if all(qualified) else None,
        "sections": sections,
        "source": (fund.get("src") or {}).get("statements"),
    }


def _merge_fund(fresh: dict, existing: dict) -> dict:
    """Apply merge-mode rules: preserve canonical blocks from existing when fresh is null/empty.

    PRESERVE from existing (when fresh value is null/empty):
      statements, ratios series (pe/ps/pb/pcf/ev/ev_ebitda + periods),
      dividends (events + splits), ownership, guidance, segments,
      and per-field stats/profile values where fresh is null.

    REPLACE always:
      estimates, analyst, earnings (all sub-fields), asof=today,
      src.estimates, ratios.current (live snapshot), stats.num_holders, stats.beta,
      profile fields where fresh non-null (website/employees/founded/hq).
    """
    merged = dict(fresh)
    merged["asof"] = ASOF
    # `asof` is the BUILD date, not a claim that the observations are current. Say so in the
    # artifact so the two can never be conflated again; `data_freshness` carries the real
    # reporting period. Both are additive — existing consumers keep reading `asof` unchanged.
    merged["asof_semantics"] = "build_date"

    # ── statements ──────────────────────────────────────────────────────────
    merged["statements"] = merge_statement_history(fresh, existing)["statements"]

    # ── ratios: preserve period series AND current fields where fresh is null ──
    fresh_ratios = fresh.get("ratios") or {}
    exist_ratios = existing.get("ratios") or {}
    merged_ratios = dict(fresh_ratios)
    # Period series: preserve from existing when fresh has none
    if not _nonempty(fresh_ratios.get("periods")):
        for key in ("periods", "pe", "ps", "pb", "pcf", "ev", "ev_ebitda"):
            if _nonempty(exist_ratios.get(key)):
                merged_ratios[key] = exist_ratios[key]
    # Current snapshot: merge field-by-field — keep existing non-null for fields fresh nulled
    # (fresh pe_ttm/ps/pb/div_yield come from valuation.parquet; gross_margin/net_margin/roe
    # come from financials.parquet; current_ratio/debt_to_equity derived from balance stmts —
    # preserve existing values when the parquet source is absent on this machine)
    fresh_cur = fresh_ratios.get("current") or {}
    exist_cur = exist_ratios.get("current") or {}
    merged_cur = dict(exist_cur)    # start from existing
    for field, val in fresh_cur.items():
        if val is not None:
            merged_cur[field] = val  # fresh overrides
        # else: keep existing value
    merged_ratios["current"] = merged_cur
    merged["ratios"] = merged_ratios

    # ── dividends: preserve when fresh has no events ────────────────────────
    fresh_div = fresh.get("dividends") or {}
    if not _nonempty(fresh_div.get("events")):
        exist_div = existing.get("dividends")
        if _nonempty((exist_div or {}).get("events")):
            merged["dividends"] = exist_div

    # ── ownership: preserve when fresh top_inst is empty ────────────────────
    fresh_own = fresh.get("ownership") or {}
    if not _nonempty(fresh_own.get("top_inst")):
        exist_own = existing.get("ownership")
        if _nonempty((exist_own or {}).get("top_inst")):
            merged["ownership"] = exist_own

    # ── guidance / segments: preserve when fresh is null ────────────────────
    if fresh.get("guidance") is None and existing.get("guidance") is not None:
        merged["guidance"] = existing["guidance"]
    if fresh.get("segments") is None and existing.get("segments") is not None:
        merged["segments"] = existing["segments"]

    # ── stats: keep existing non-null fields where fresh is null ────────────
    fresh_stats = fresh.get("stats") or {}
    exist_stats = existing.get("stats") or {}
    merged_stats = dict(fresh_stats)
    for field in ("mktcap", "shares_out", "float_shares", "inst_pct", "insider_pct"):
        if merged_stats.get(field) is None and exist_stats.get(field) is not None:
            merged_stats[field] = exist_stats[field]
    # num_holders and beta are REPLACE (fresh overrides even if null — they come from live parquets)
    merged["stats"] = merged_stats

    # ── profile: fill-in non-null fresh fields; preserve existing for nulls ─
    fresh_prof = fresh.get("profile") or {}
    exist_prof = existing.get("profile") or {}
    merged_prof = dict(exist_prof)   # start from existing
    for field in ("website", "employees", "sector", "industry", "description", "founded", "hq"):
        if fresh_prof.get(field) is not None:
            merged_prof[field] = fresh_prof[field]
        # else: keep existing value (already present from exist_prof copy)
    merged["profile"] = merged_prof

    # ── src: update estimates source ─────────────────────────────────────────
    fresh_src = fresh.get("src") or {}
    merged_src = dict((existing.get("src") or {}))
    merged_src.update(fresh_src)
    merged["src"] = merged_src

    # Reconcile actuals on the retained statement-period observations, even if a
    # sparse fresh cache supplies one nonempty row. Fresh quarterly results win
    # as complete observations; legacy Q2–Q4 EPS is never copied or differenced.
    fresh_earnings = dict(fresh.get("earnings") or {})
    retained_q, _, _, _ = _earnings_from_existing_stmts(merged, {}, term_to_ts(merged["ticker"]))
    by_end = {row["end"]: row for row in retained_q if row.get("end")}
    for row in fresh_earnings.get("q") or []:
        if row.get("end"):
            by_end[row["end"]] = row
    fresh_earnings["q"] = [by_end[end] for end in sorted(by_end)][-8:]
    fresh_earnings["fy"] = annual_earnings_from_statements(merged, limit=5)
    merged["earnings"] = fresh_earnings
    # Estimates and analyst observations remain from the current source cache.
    # Freshness is computed LAST, from the merged block, so a statements block that survived
    # from the previous file reports the period it really carries. A failed collector therefore
    # still keeps the good historical block AND still says plainly how old it is.
    merged["data_freshness"] = _statement_freshness(merged)
    return merged


def main(argv: list[str]) -> None:
    only = _arg(argv, "--only")
    limit = int(_arg(argv, "--limit", 0) or 0)
    out_dir = Path(_arg(argv, "--out", str(DEFAULT_OUT)))
    no_merge = "--no-merge" in argv
    previous_dir = Path(_arg(argv, "--previous-dir", str(out_dir)))
    out_dir.mkdir(parents=True, exist_ok=True)

    syms = ([s.strip() for s in only.split(",")] if only else cn_universe())
    # normalize .SH → .SS for terminal file naming
    syms = [ts_to_term(s) for s in syms]
    if limit:
        syms = syms[:limit]

    stmts = load_statements()
    vmap = load_map("valuation.parquet", "ticker")
    dbmap = load_map("daily_basic.parquet", "ts_code")
    fmap = load_map("financials.parquet", "ts_code")
    divmap = load_dividends()
    fcmap = load_forecast()
    hmap = load_holders()
    consensus_map = load_consensus()
    reports_map = load_reports()
    company_map = load_company()
    holdernum_map = load_holdernum()
    disclosure_map = load_disclosure()
    print(f"joins — stmt_income {len(stmts['income'])}, valuation {len(vmap)}, daily_basic {len(dbmap)}, "
          f"financials {len(fmap)}, dividends {len(divmap)}, forecast {len(fcmap)}, holders {len(hmap)}, "
          f"consensus {len(consensus_map)}, reports {len(reports_map)}, "
          f"company {len(company_map)}, holdernum {len(holdernum_map)}, disclosure {len(disclosure_map)}",
          flush=True)
    merge_mode = not no_merge
    print(f"merge-mode: {'ON (default)' if merge_mode else 'OFF (--no-merge)'}", flush=True)

    ok = err = 0
    for sym in syms:
        sp = CN_SITE / f"{sym}.json"
        src = {}
        if sp.exists():
            try:
                src = json.loads(sp.read_text())
            except Exception:
                src = {}
        try:
            fund = build_fund(sym, src, stmts, vmap, dbmap, fmap, divmap, fcmap, hmap,
                              consensus_map=consensus_map,
                              reports_map=reports_map,
                              company_map=company_map,
                              holdernum_map=holdernum_map,
                              disclosure_map=disclosure_map,
                              data_dir=out_dir)

            if merge_mode:
                existing = _load_existing(previous_dir / f"{sym}.fund.json")
                if existing is not None:
                    ts_code = term_to_ts(sym)
                    # If fresh earnings.q/fy are empty (stmt parquets absent), derive from existing stmts
                    fresh_earn = fund.get("earnings") or {}
                    if not _nonempty(fresh_earn.get("q")) and not _nonempty(fresh_earn.get("fy")):
                        q_rows, fy_rows, nd, np_ = _earnings_from_existing_stmts(
                            existing, disclosure_map, ts_code)
                        fund["earnings"] = {
                            "next_date": fresh_earn.get("next_date") or nd,
                            "next_period": fresh_earn.get("next_period") or np_,
                            "next_eps_est": fresh_earn.get("next_eps_est"),
                            "next_rev_est": fresh_earn.get("next_rev_est"),
                            "q": q_rows,
                            "fy": fy_rows,
                        }
                    fund = _merge_fund(fund, existing)

            fund["asof"] = ASOF
            fund["asof_semantics"] = "build_date"
            fund["data_freshness"] = _statement_freshness(fund)
            atomic_write(out_dir / f"{sym}.fund.json",
                         json.dumps(fund, separators=(",", ":"), ensure_ascii=False, sort_keys=False))
            ok += 1
        except Exception as exc:   # noqa: BLE001
            err += 1
            if err <= 20:
                print(f"  ERR {sym}: {exc}", flush=True)
                if err <= 5:
                    traceback.print_exc()
    print(f"gen_fund_cn: {ok} written, {err} errors → {out_dir}", flush=True)
    if err:
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
