"""Descriptive risk-recovery context; never position-changing advice.

An older peak comparison is not a latest-session improvement. Missing or invalid
recovery eligibility, missing same-market confirmation, and an unknown/active
local veto cannot produce the shared card's green TURN presentation. International
market internals remain N/A; US internals never stand in for another market.

The existing trajectory and numerical estimates are retained, not recalibrated.
``phase`` carries the raw trajectory; ``receding``/``turn_confirmed`` are stricter
presentation flags requiring explicit eligibility, local confirmation, a clear
veto and a dated liquidity catalyst. ``turn_confirmed_full`` stays None off-US.
These observations are not a forward-validated re-entry or sizing signal.

Liquidity quantity, Fed policy, reserve/funding conditions and local repair are
separate. Undated expanding/dovish categories are context, not fresh policy events.
The existing recovery audit remains the research owner; no new ledger, score,
ceiling, portfolio policy or execution authority is created here.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime
from pathlib import Path

log = logging.getLogger(__name__)


def _load_liquidity_plumbing() -> dict:
    """Load data/neuralweb/liquidity_plumbing.json via lib.config — fail-open to empty dict.

    Uses the same loader pattern as _us_latest(): lib.config.data_dir() for the
    data root, silent exception swallow, never raises.
    """
    try:
        from lib import config  # noqa: PLC0415
        p = config.data_dir() / "neuralweb" / "liquidity_plumbing.json"
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception as e:  # noqa: BLE001
        log.debug("recovery: liquidity_plumbing unavailable (%s)", e)
        return {}


def _num(v):
    try:
        if v is None or isinstance(v, bool):
            return None
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _recent(date_str: str | None, days: int = 60) -> bool:
    """True if an ISO date string is within `days` of today (for the 'fresh' catalyst flag)."""
    if not date_str:
        return False
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
        return 0 <= (date.today() - d).days <= days
    except (TypeError, ValueError):
        return False


def _us_latest() -> dict:
    """The US regime latest.json — canonical source of the Fed net-liquidity overlay + reaction
    function. The intl (CN/HK/CA) latests don't carry these, but the Fed is a GLOBAL liquidity
    driver (US rate shocks are the #1 external lead in every intl radar profile), so the intl
    recovery reads them from here. Never raises."""
    try:
        import json
        from lib import config
        p = config.data_dir() / "regime" / "latest.json"
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception as e:  # noqa: BLE001
        log.debug("recovery: US latest unavailable (%s)", e)
        return {}


# --- liquidity-injection catalysts -------------------------------------------------------------
def _market_catalysts(latest: dict | None = None) -> dict | None:
    """Lazy import of engine/risk_radar_market_catalysts. Returns the compute() dict or None on
    any failure. latest is passed for future context-gating but currently unused by compute().
    NEVER raises.

    Hot-path note: this function is called on both the intraday fast-path
    (build_risk_state.py → market_state.market_state_snapshot → assess) and the nightly path
    (engine/run.py).  compute() itself is read-only (no ledger writes) and the result is
    stripped from risk_state.json by _verdict_block's key whitelist, so no ledger or banner
    mutation occurs intraday.  The per-tick I/O cost is ~4 store.read calls (breadth/SPY/_VIX
    /FRED) plus rolling/EMA/pct_rank_window; acceptable on the current 4-core box given the
    intraday tick rate (~1/min), but operator should revisit if tick frequency increases.
    """
    try:
        from engine import risk_radar_market_catalysts as _rmc
        return _rmc.compute()
    except Exception as e:  # noqa: BLE001
        log.debug("recovery: market catalysts unavailable (%s)", e)
        return None


def _fed_netliq_detail() -> tuple[str, str]:
    """Describe stored US quantity, policy and funding separately; never infer a cause.

    Component changes retain their producer-reported windows. The snapshot date
    is not substituted for a missing raw-source clock or a dated policy turn.
    """
    fallback = (
        "US net-liquidity proxy context; component detail unavailable. "
        "This is not a Fed-policy or bank-reserve measure.",
        "美国净流动性代理指标背景；成分明细暂缺。这不是美联储政策或银行准备金指标。",
    )
    try:
        payload = _load_liquidity_plumbing()
        if not isinstance(payload, dict) or not payload:
            return fallback
        qty = payload.get("quantity") or {}
        fed = payload.get("fed") or {}
        funding = payload.get("funding") or {}
        components = payload.get("components") or {}
        treasury = payload.get("treasury") or {}
        en = ["US net-liquidity proxy (WALCL − RRP − TGA); not Fed policy or bank reserves"]
        zh = ["美国净流动性代理指标（WALCL − RRP − TGA）；不代表美联储政策或银行准备金"]
        asof = payload.get("asof")
        if isinstance(asof, str) and asof:
            en.append(f"snapshot {asof[:10]} (component clocks may differ)")
            zh.append(f"快照日期{asof[:10]}（各成分日期可能不同）")
        for value, label_en, label_zh in [
            (qty.get("netliq_chg_20d_bn"), "proxy", "代理指标"),
            (fed.get("assets_chg_20d_bn"), "Fed assets", "美联储资产"),
            ((components.get("reserves") or {}).get("d20_bn"), "bank reserves", "银行准备金"),
        ]:
            number = _num(value)
            if number is not None:
                en.append(f"{label_en} {number:+.0f}B USD / reported 20d")
                zh.append(f"{label_zh}{number * 10:+.0f}亿美元／报告的20日期间")
        if _num(qty.get("netliq_chg_20d_bn")) is None:
            en.append("quantity change unavailable")
            zh.append("数量变化暂缺")
        stance = fed.get("policy_stance")
        if stance in ("hawkish", "dovish", "neutral"):
            en.append(f"Fed policy: {stance}")
            zh.append("美联储政策：" + {"hawkish": "鹰派", "dovish": "鸽派", "neutral": "中性"}[stance])
        scarcity = funding.get("reserve_scarcity_state")
        if scarcity in ("tightening", "scarce", "ample", "neutral", "unknown"):
            en.append(f"reserve conditions: {scarcity}")
            zh.append("准备金状况：" + {"tightening": "趋紧", "scarce": "紧缺", "ample": "充裕",
                                       "neutral": "中性", "unknown": "未知"}[scarcity])
        impulse = treasury.get("tga_impulse") or {}
        magnitude = _num(impulse.get("magnitude_bn"))
        direction = impulse.get("direction")
        if impulse.get("active") is True and magnitude is not None and magnitude >= 0:
            if direction in ("drawdown", "build"):
                verb = "drawdown" if direction == "drawdown" else "refill"
                en.append(f"Treasury account {verb}: ${magnitude:.0f}B in its reported window")
                zh.append(f"财政部现金账户{'动用' if direction == 'drawdown' else '补充'}"
                          f"{magnitude * 10:.0f}亿美元（其报告期间）")
        return "; ".join(en) + ".", "；".join(zh) + "。"
    except (AttributeError, TypeError, ValueError):
        return fallback


def _liquidity_catalysts(latest: dict, market: str = "us") -> list[dict]:
    """The supportive-liquidity legs that are firing right now, as display chips. All read the
    display-only context already on the page; each degrades to absent. `fresh` = a genuinely
    recent turn (drives the chip glow). For the intl radars (market != 'us') the Fed legs are read
    from the US regime latest (a global driver). NEVER raises."""
    latest = latest or {}
    # Fed net-liq + reaction function: the US latest has them; the intl latests don't, so fall back
    # to the US regime latest (the Fed is a global liquidity driver for CN/HK/CA too).
    fed_src = latest if (market == "us" or latest.get("fed_stance")) else _us_latest()
    cats: list[dict] = []

    # 1) Fed net liquidity (WALCL − RRP − TGA). 'expanding' = the 20d ROC is positive, i.e. the
    #    balance sheet is adding reserves and/or the Treasury is drawing its account down (TGA
    #    drop). engine/regime.py classifies this into latest['liquidity_overlay'].
    lo = fed_src.get("liquidity_overlay")
    if lo == "expanding":
        # RLT-R5: enrich detail with netliq Δ20d magnitude and TGA impulse when available.
        # Fail-open: falls back to the generic string when the artifact is absent.
        detail_en, detail_zh = _fed_netliq_detail()
        cats.append({
            "key": "fed_netliq", "icon": "💵", "region": "US", "fresh": False,
            "label_en": "US net-liquidity proxy rising", "label_zh": "美国净流动性代理指标上升",
            "detail_en": detail_en,
            "detail_zh": detail_zh,
            # A quantity category does not establish a dated liquidity turn, Fed
            # easing, or a transferable market-specific dip-buying advantage.
            "salience_en": "US context only; not Fed easing or local-market recovery.",
            "salience_zh": "仅为美国背景信息，不代表美联储宽松或本地市场修复。",
        })

    # 2) Fed policy easing / emergency cut — market pricing + reaction-function read (display-only;
    #    engine/fed_path.py + engine/fed_stance.py). A large cut count = the emergency-cut case.
    fs = fed_src.get("fed_stance") or {}
    fp = fed_src.get("fed_path") or {}
    cuts = _num(fs.get("implied_cuts_12m"))
    if cuts is None:
        cuts = _num(fp.get("implied_cuts_12m"))
    dovish = (fs.get("stance") == "dovish")
    easing_guide = ((fs.get("guidance") or "") == "easing")
    if dovish or easing_guide or (cuts is not None and cuts >= 1.5):
        if cuts is not None and cuts >= 1:
            det_en = f"Market prices ~{cuts:.0f} cut{'s' if cuts >= 2 else ''} over 12m — market expectations, not an announced cut."
            det_zh = f"市场为未来12个月定价约{cuts:.0f}次降息 — 市场预期，并非已宣布的降息。"
        else:
            det_en = "Dovish Fed-policy classification; no dated policy action established."
            det_zh = "美联储政策分类偏鸽；尚无有日期支持的政策行动。"
        cats.append({
            "key": "fed_policy", "icon": "🏛", "region": "US",
            "fresh": False,  # pricing/guidance categories do not date a policy event
            "label_en": "Fed cuts priced" if cuts is not None and cuts >= 1 else "Dovish Fed-policy context",
            "label_zh": "美联储降息预期定价" if cuts is not None and cuts >= 1 else "美联储偏鸽政策背景",
            "detail_en": det_en, "detail_zh": det_zh,
        })

    # 3) PBoC easing (RRR / LPR / money-market) — engine/china_pboc_stance.py. Relevant to the
    #    global liquidity tide, not just China. Lazy import: it is a China leaf the US latest may
    #    not carry.
    try:
        from engine import china_pboc_stance
        pb = china_pboc_stance.snapshot()
    except Exception as e:  # noqa: BLE001
        log.debug("recovery: pboc stance unavailable (%s)", e)
        pb = None
    if pb and pb.get("stance") == "easing":
        moves = pb.get("last_moves") or []
        fresh = any(m.get("easing") and _recent(m.get("date")) for m in moves)
        rat = pb.get("rationale") or {}
        cats.append({
            "key": "pboc", "icon": "🇨🇳", "region": "CN", "fresh": bool(fresh),
            "label_en": "PBoC easing", "label_zh": "中国央行宽松",
            "detail_en": rat.get("en") or "RRR / LPR cuts — PBoC adding liquidity.",
            "detail_zh": rat.get("zh") or "降准／降息 — 央行注入流动性。",
        })

    # 4) Global central-bank balance-sheet tide (Fed + ECB + BoJ, USD-summed) — engine/
    #    global_liquidity.py. This is the ONLY freely-available read of BoJ liquidity, so the BoJ
    #    leg lives here (the chip says so). Lazy import (not wired into the US latest).
    try:
        from engine import global_liquidity
        gl = global_liquidity.snapshot()
    except Exception as e:  # noqa: BLE001
        log.debug("recovery: global liquidity unavailable (%s)", e)
        gl = None
    if gl and gl.get("state") == "expanding":
        accel = gl.get("accel")
        imp = (gl.get("impulse_pct") or {}).get("13w")
        imp_txt = f"+{imp}%" if isinstance(imp, (int, float)) and imp > 0 else (f"{imp}%" if imp is not None else "")
        cats.append({
            "key": "global_cb", "icon": "🌊", "region": "GLOBAL",
            "fresh": False,  # acceleration alone is not a dated turn event
            "label_en": "Global CB liquidity expanding", "label_zh": "全球央行流动性扩张",
            "detail_en": f"Fed + ECB + BoJ balance-sheet tide {imp_txt} (13w), {accel}.".replace("  ", " "),
            "detail_zh": f"美欧日央行资产负债表 13周 {imp_txt}（{accel}）。",
        })

    return cats


# --- the assembled recovery read ---------------------------------------------------------------
def assess(latest: dict) -> dict | None:
    """The display-only recovery view-model attached to market_state.radar.recovery. Returns
    {'present': False} when there is nothing to show, the full dict when the risk-off looks to be
    peaking / receding, or None when there is no trajectory at all. NEVER raises."""
    try:
        rr = (latest or {}).get("risk_radar") or {}
        traj = rr.get("trajectory")
        if not traj:
            return None
        market = rr.get("market") or "us"   # 'us' | 'cn' | 'hk' | 'ca' (intl reads Fed legs globally)
        phase = traj.get("phase")
        reached = traj.get("reached_risk") is True
        cats = _liquidity_catalysts(latest, market)
        n_cat = len(cats)
        n_fresh = sum(1 for c in cats if c.get("fresh") is True)

        # Market-internal confirmation channel (W1, accruing — not yet forward-tested).
        # US-ONLY: the chips read US stores (S&P breadth, SPY, VIX term, HY OAS) — attaching
        # them to the CN/HK/CA radar latests would render US internals on intl cards
        # (assess() serves BOTH call sites in engine/market_state.py). Intl ports are a
        # W5 docket (masterplan §5); until then the intl market channel is N/A, not False.
        mkt = _market_catalysts(latest) if market == "us" else None

        # Show ONLY once there was genuine risk to recede FROM, and it is no longer rising — OR a
        # broad liquidity turn is underway while the radar sits at/just past its peak.
        present = (reached and phase in ("peaking", "receding")) or \
                  (reached and phase != "rising" and n_fresh >= 2)
        if not present:
            return {"present": False}

        # Missing/invalid permission is not recovery evidence. Raw trajectory and
        # numerical estimates remain available below, without a green all-clear.
        deesc = rr.get("deescalation")
        eligible = isinstance(deesc, dict) and deesc.get("eligible") is True
        mkt_confirmed = mkt_veto = None
        if market == "us" and isinstance(mkt, dict):
            raw_confirmed = mkt.get("market_confirmed")
            veto = mkt.get("veto")
            raw_veto = veto.get("active") if isinstance(veto, dict) else None
            mkt_confirmed = raw_confirmed if type(raw_confirmed) is bool else None
            mkt_veto = raw_veto if type(raw_veto) is bool else None
        local_confirmed = mkt_confirmed is True and mkt_veto is False
        suppressed = not (eligible and local_confirmed)
        # International internals remain N/A; US inputs are never borrowed as
        # local confirmation. The legacy liquidity-only TURN was unsafe.
        turn_confirmed = bool(phase == "receding" and eligible
                              and local_confirmed and n_fresh >= 1)
        receding = turn_confirmed  # the shared card uses this flag for green
        peaking = bool(phase == "peaking" and eligible and local_confirmed)
        turn_confirmed_full = turn_confirmed if market == "us" else None
        channels = {"liquidity": bool(n_fresh >= 1),
                    "market": mkt_confirmed, "veto": mkt_veto}

        off = traj.get("off_peak") or 0.0
        vel = traj.get("velocity") or 0.0
        # Modest, illustrative 0-100 strength: distance off the peak + how fast it is falling +
        # how broad the liquidity turn is. Capped; never implies precision it doesn't have.
        strength = int(max(0, min(100, round(
            off * 3.0 + max(0.0, -vel) * 3.5 + n_cat * 11 + n_fresh * 6 + (14 if receding else 0)))))

        odds_now = _num(traj.get("odds_now"))
        odds_peak = _num(traj.get("odds_peak"))
        odds_delta = _num(traj.get("odds_delta"))
        days = int(traj.get("peak_days_ago") or 0)

        # One descriptive voice. Neither a lower old-peak comparison nor a
        # supportive component grants position-changing authority.
        if turn_confirmed:
            head_en = "Risk measures easing — local internals agree"
            head_zh = "风险指标缓和 — 本地市场内部指标一致"
        elif isinstance(deesc, dict) and deesc.get("eligible") is False:
            head_en = "Recovery not confirmed — risk warning remains"
            head_zh = "修复尚未确认 — 风险警示仍在"
        elif phase == "receding":
            head_en = "Recovery not confirmed — some measures below their peak"
            head_zh = "修复尚未确认 — 部分指标低于此前峰值"
        else:
            head_en = "Recovery not confirmed — local evidence incomplete"
            head_zh = "修复尚未确认 — 本地证据不完整"

        if (odds_now is not None and odds_peak is not None
                and 0 <= odds_now <= odds_peak <= 1):
            sub_en = (f"Model estimate {round(odds_now * 100)}%; earlier window peak "
                      f"{round(odds_peak * 100)}% — not a latest-session change.")
            sub_zh = (f"模型估计{round(odds_now * 100)}%；此前窗口峰值"
                      f"{round(odds_peak * 100)}% — 并非最近交易日的变化。")
        else:
            sub_en = "Historical risk context; a comparable latest-session change is unavailable."
            sub_zh = "历史风险背景；可比的最近交易日变化暂缺。"
        do_en = ("Watch whether local breadth and price repair persists. Context only; "
                 "this panel does not authorize exposure changes.")
        do_zh = "观察本地广度与价格修复能否持续。仅供背景参考；此面板不授权调整敞口。"
        caveat_en = ("Descriptive context, not a re-entry signal. "
                     "Policy stance, liquidity quantity, funding quality and local repair "
                     "are separate. Missing confirmation is unknown, not an all-clear. "
                     "The existing risk scores, probabilities and restrictions are unchanged.")
        caveat_zh = ("描述性背景，并非再入场信号。政策立场、流动性数量、融资质量"
                     "与本地修复分别呈现。缺少确认代表未知，并非解除警报。既有风险评分、概率与限制不变。")

        # RRX2 WA-3: mirror the drivers block (which scares faded / warm) from trajectory.
        # Old artifacts without a drivers key → None → template renders nothing.
        drivers = traj.get("drivers")

        return {
            "present": True,
            "phase": phase, "receding": receding, "peaking": peaking,
            # radar-derived gate (one risk voice): green suppressed while the
            # dominant scare escalates; mirrored for the template/bot to read
            "suppressed": suppressed, "deescalation": deesc,
            "turn_confirmed": turn_confirmed, "strength": strength,
            # --- W1 market-channel additions (sibling keys, never wrappers — RRX-R7) ---
            # market_confirmed_raw and market_confirmed are the raw chip outputs
            "market": mkt,
            "turn_confirmed_full": turn_confirmed_full,
            "channels": channels,
            # the odds turn + velocity (mirrored from the trajectory so the template reads one dict)
            "odds_now": odds_now, "odds_peak": odds_peak, "odds_delta": odds_delta,
            "peak_days_ago": days, "velocity": vel, "off_peak": off,
            "intensity": _num(traj.get("intensity")), "peak": _num(traj.get("peak")),
            # sparkline (pre-scaled in engine/risk_radar.trajectory)
            "spark": traj.get("spark"), "spark_pts": traj.get("spark_pts"),
            "spark_peak": traj.get("spark_peak"), "spark_last": traj.get("spark_last"),
            "spark_w": traj.get("spark_w"), "spark_h": traj.get("spark_h"),
            # catalysts
            "catalysts": cats, "n_catalysts": n_cat, "n_fresh": n_fresh,
            # RRX2 WA-3: drivers line (which scares faded / still warm); None on old artifacts
            "drivers": drivers,
            # copy
            "headline_en": head_en, "headline_zh": head_zh,
            "sub_en": sub_en, "sub_zh": sub_zh,
            "do_en": do_en, "do_zh": do_zh,
            "caveat_en": caveat_en, "caveat_zh": caveat_zh,
        }
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("risk_radar_recovery assess failed: %s", e)
        return None
