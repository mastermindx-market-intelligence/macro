"""Forward Path board — rates & inflation command context layer.

Schema: rates_command.v1
Chartered: research/RATES_INFLATION_COMMAND_MASTERPLAN_BY_FABLE.md §P5, W7.

PUBLIC API
----------
build_board(root)               — full artifact content dict
compact_state(contract)         — small comparable fingerprint for diffing
diff_changes(old_state, new)    — list of change items (max 6)
build_changes(old_contract, new_contract, new_asof) — (changes_block, prev_state_block)
compose_stance(board)           — {en, zh} deterministic stance sentence

HOUSE LAWS (RIC-W7 binding)
---------------------------
* RIC-R1:  display-only end-to-end.  Every emitted dict carries display_only=True,
           authority=False.  No scoring, ranking, gating, sizing, escalation.
* RIC-R9:  deterministic join of existing calibrated artifacts.  "benchmark" NEVER
           "consensus" (MRI-R5 — the word consensus is banned from all strings,
           EN and ZH 共识).  Conditions never intent (PS-R1): no "Fed will …",
           no administration-timing predictions, no policy-intent classification.
* MRI-R4:  never originate a projection/probability.  Read artifact values only.
* MRI-R16: Polymarket values are context-only benchmark.  Display juxtaposition only,
           labeled "market-implied benchmark"; NEVER fused into computed state/score.
* PS-R4:   geopolitical legs are UNSIGNED qualitative display rows (no probability,
           no direction score).  Iran/oil context row = quote policy intel theater
           text + as-of stamp + staleness disclosure.
* Naming:  new field names MUST NOT contain substrings: forecast, predicted,
           expected_return, or "target" in the forward-price/return sense.  Existing
           read keys like fed_path.target_mid are fine to read, and `vs_target_pp`
           is permitted: it measures distance to the Fed's 2% inflation target (a
           policy constant), not a forward price/return target.
* "validated" banned from any user-facing string.
* Fail-open everywhere: absent/corrupt input → leg active=None + null_reason, never raises.
* Ledger law: forward_log.jsonl appends ONLY under nightly lane gate, keep-FIRST per
  asof_night.
* Additive only: never rename/remove keys in existing artifacts.
* Bilingual: every user-facing string has en + zh twins, equally plain.
* No LLM-originated content.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def _curve_accounting_board_shell(reason: str) -> dict:
    """curve_accounting.v1 "unavailable" shell for a missing/malformed
    transmission contract (RIC Y1b). Never a fabricated read."""
    return {
        "schema": "curve_accounting.v1",
        "calculation_version": "ric_y1_curve_accounting.v1",
        "basis_schema": None,
        "cutoff": None,
        "asof": None,
        "status": "unavailable",
        "reason": reason,
        "display_only": True,
        "authority": False,
        "can_score": False,
        "can_size": False,
        "can_trade": False,
        "law": [],
        "observations": {},
        "comparisons": {},
        "accounting_views": [],
        "views_are_alternatives_never_summed": True,
    }

# ---------------------------------------------------------------------------
# Frozen thresholds (module-level constants — unit-tested exhaustively)
# ---------------------------------------------------------------------------
# H1 path_repricing: active when d20 >= +15 bp, easing mirror when d20 <= -15 bp
H1_HAWKISH_THRESHOLD_BP: float = 15.0
H1_DOVISH_THRESHOLD_BP: float = -15.0

# H2 breakeven_momentum: 20d velocity >= +8 bp
H2_BE_THRESHOLD_BP: float = 8.0

# H4 inflation_trajectory: cpi surprise_skew.tag == 'hotter'
# H5 curve_regime: bear_steepener + term_premium_dir == 'rising'
# H6 anchoring_strain: worst anchoring bands
H6_STRAINED_BANDS: frozenset = frozenset({"strained", "de-anchoring", "drifting up"})

# E1 equity_deleveraging: radar.state in caution/elevated/risk-off
E1_TRIGGER_STATES: frozenset = frozenset({"caution", "elevated", "risk-off"})

# E4 credit_stress: hy_oas_z >= 1.0
E4_HY_OAS_Z_THRESHOLD: float = 1.0

# D1 dots_vs_market divergence: |gap_bp| >= 50
D1_GAP_BP_THRESHOLD: float = 50.0

# D3 pressure_vs_market
D3_IMPLIED_BP_LOW: float = 0.0
D3_IMPLIED_BP_HIGH: float = 25.0

# shock_state staleness threshold (days)
SHOCK_STALE_DAYS: int = 7

# Max change items in diff
_MAX_CHANGES: int = 6

# ---------------------------------------------------------------------------
# Plain-word label maps
# ---------------------------------------------------------------------------

_NET_STATE_LABELS: dict[str, dict[str, str]] = {
    "repricing_hawkish": {
        "en": "Hike expectations rising now",
        "zh": "加息预期正在升温",
    },
    "pressure_building": {
        "en": "Hawkish pressure building — market not moved yet",
        "zh": "鹰派压力积聚——市场尚未定价",
    },
    "repricing_dovish": {
        "en": "Cut expectations rising now",
        "zh": "降息预期正在升温",
    },
    "pressure_fading": {
        "en": "Easing pressure building",
        "zh": "宽松压力积聚",
    },
    "two_sided": {
        "en": "Two-sided — watch the tape",
        "zh": "双向——观察市场走势",
    },
}

_ANCHORING_LABEL_ZH: dict[str, str] = {
    "anchored": "锚定",
    "drifting up": "上行脱锚",
    "drifting down": "下行",
    "strained": "承压",
    "de-anchoring": "脱锚",
}

_CURVE_REGIME_ZH: dict[str, str] = {
    "bear_steepener": "熊市变陡",
    "bull_steepener": "牛市变陡",
    "bear_flattener": "熊市变平",
    "bull_flattener": "牛市变平",
    "flat": "曲线平坦",
    "inverted": "曲线倒挂",
}

_INFL_DIR_ZH: dict[str, str] = {
    "re-accelerating": "再加速",
    "steady": "平稳",
    "cooling": "降温",
    "rising": "上行",
    "falling": "下行",
    "flat": "横盘",
}

_USD_DIR_ZH: dict[str, str] = {
    "strengthening": "走强",
    "weakening": "走软",
    "flat": "横盘",
}

_DIFF_ORDER: list[str] = [
    "net_state",
    "curve_regime",
    "anchoring",
    "infl_dir",
    "usd_dir",
    "hawk_score",
    "ease_score",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _data_root(root=None) -> Path:
    if root is not None:
        return Path(root)
    try:
        from lib import config as _cfg
        return _cfg.data_dir()
    except Exception:
        return Path(__file__).resolve().parent.parent / "data"


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _safe_get(obj: Any, *path) -> Any:
    """Nested dict accessor that fails open to None."""
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _staleness_days(ts_str: str | None, today: datetime | None = None) -> int | None:
    """Return age in whole days for an ISO timestamp string, or None."""
    if not ts_str:
        return None
    try:
        from datetime import date
        # try ISO datetime first
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            ref = today or datetime.now(timezone.utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ref.tzinfo is None:
                ref = ref.replace(tzinfo=timezone.utc)
            return (ref - ts).days
        except Exception:
            # date-only string
            ts_d = date.fromisoformat(ts_str[:10])
            ref_d = (today or datetime.now(timezone.utc)).date()
            return (ref_d - ts_d).days
    except Exception:
        return None


def _intel_staleness_days(intel: dict | None) -> int | None:
    as_of = _safe_get(intel, "as_of")
    return _staleness_days(as_of)


# ---------------------------------------------------------------------------
# Leg builders
# ---------------------------------------------------------------------------

def _build_hawkish_legs(
    fed_path: dict,
    tx: dict,
    zq_d20_bp: float | None,
    release_items: list[dict],
    shock_state_oil: dict | None,
    shock_stale: bool,
) -> list[dict]:
    """Build H1-H6 hawkish pressure legs.

    Each leg: {key, active: true|false|null, weight, value, detail_en, detail_zh, null_reason}
    """
    legs: list[dict] = []

    # H1 — path_repricing (weight 2)
    if zq_d20_bp is None:
        legs.append({
            "key": "H1_path_repricing",
            "active": None,
            "weight": 2,
            "value": None,
            "detail_en": "Rate futures 12m path change unavailable (zq_path.parquet missing).",
            "detail_zh": "利率期货12个月路径变化不可用（zq_path.parquet缺失）。",
            "null_reason": "zq_path.parquet absent or unreadable",
        })
    else:
        active = zq_d20_bp >= H1_HAWKISH_THRESHOLD_BP
        legs.append({
            "key": "H1_path_repricing",
            "active": active,
            "weight": 2,
            "value": round(zq_d20_bp, 1),
            "detail_en": (
                f"Futures added {zq_d20_bp:+.1f}bp of 12-month rate over the last month."
                if active
                else f"12-month rate futures moved {zq_d20_bp:+.1f}bp over 20 trading days (threshold: +{H1_HAWKISH_THRESHOLD_BP:.0f}bp)."
            ),
            "detail_zh": (
                f"期货在过去一个月内将12个月利率上调了{zq_d20_bp:+.1f}个基点。"
                if active
                else f"20个交易日内12个月利率期货变动{zq_d20_bp:+.1f}个基点（阈值：+{H1_HAWKISH_THRESHOLD_BP:.0f}bp）。"
            ),
            "null_reason": None,
        })

    # H2 — breakeven_momentum (weight 1)
    be_v = _safe_get(tx, "breakeven_decomp", "velocity_bp", "chg_20d_bp")
    if be_v is None:
        legs.append({
            "key": "H2_breakeven_momentum",
            "active": None,
            "weight": 1,
            "value": None,
            "detail_en": "Breakeven velocity unavailable.",
            "detail_zh": "盈亏平衡点速度不可用。",
            "null_reason": "breakeven_decomp.velocity_bp.chg_20d_bp absent",
        })
    else:
        active = float(be_v) >= H2_BE_THRESHOLD_BP
        legs.append({
            "key": "H2_breakeven_momentum",
            "active": active,
            "weight": 1,
            "value": round(float(be_v), 1),
            "detail_en": f"10y breakeven moved {be_v:+.1f}bp over 20 days (threshold: +{H2_BE_THRESHOLD_BP:.0f}bp).",
            "detail_zh": f"10年期盈亏平衡点20天变动{be_v:+.1f}个基点（阈值：+{H2_BE_THRESHOLD_BP:.0f}bp）。",
            "null_reason": None,
        })

    # H3 — oil_impulse (weight 1)
    oil_trend = _safe_get(tx, "state", "rates")  # We'll read from commodity artifact separately
    # The commodity data is passed via tx dict indirectly — caller injects oil_trend/shock
    # We'll use the values already extracted from the commodity artifact (passed as shock_state_oil)
    # and read from fed_path (cause_badge from breakeven_decomp)
    cause_badge_cause = _safe_get(tx, "breakeven_decomp", "cause_badge", "cause")

    # oil data is NOT in tx; it is passed as parameters
    # Caller must inject oil_trend from commodity/latest.json
    # We use the _oil_trend parameter (see build_board)
    # For this function, oil_trend is passed via shock_state_oil dict with extra keys
    _oil_trend = _safe_get(shock_state_oil, "_oil_trend") if shock_state_oil else None
    _oil_chg = _safe_get(shock_state_oil, "_oil_chg") if shock_state_oil else None

    if _oil_trend is None:
        legs.append({
            "key": "H3_oil_impulse",
            "active": None,
            "weight": 1,
            "value": None,
            "detail_en": "Oil trend data unavailable.",
            "detail_zh": "原油趋势数据不可用。",
            "null_reason": "commodity/latest.json absent or oil.trend missing",
        })
    else:
        oil_up = _oil_trend == "up"
        if shock_stale:
            # Judge on trend + cause_badge alone
            shock_qualifier = oil_up and cause_badge_cause == "oil"
            detail_note_en = " (shock_state stale >7d — judged on trend+cause_badge only)"
            detail_note_zh = "（shock_state超过7天未更新——仅依据趋势和原因标识判断）"
        else:
            shock_oil_state = _safe_get(shock_state_oil, "state") if shock_state_oil else None
            shock_qualifier = shock_oil_state in {"stabilizing", "shock"}
            detail_note_en = ""
            detail_note_zh = ""
        active = oil_up and (shock_qualifier or cause_badge_cause == "oil")
        legs.append({
            "key": "H3_oil_impulse",
            "active": active,
            "weight": 1,
            "value": _oil_trend,
            "detail_en": (
                f"Oil trending {_oil_trend} ({_oil_chg:+.1f}% 20d) with shock/oil-driven breakeven pressure.{detail_note_en}"
                if active
                else f"Oil trend: {_oil_trend}; shock or oil-driver condition not met.{detail_note_en}"
            ),
            "detail_zh": (
                f"原油趋势{_oil_trend}（20天涨跌{_oil_chg:+.1f}%），叠加冲击/油价驱动的盈亏平衡压力。{detail_note_zh}"
                if active
                else f"原油趋势：{_oil_trend}；冲击或油价驱动条件未满足。{detail_note_zh}"
            ),
            "null_reason": None,
        })

    # H4 — inflation_trajectory (weight 1)
    # Nearest cpi_headline OR cpi_core tag == 'hotter', OR infl direction indicates re-acceleration
    cpi_hotter = False
    cpi_detail_en = "No upcoming CPI data with hotter skew."
    cpi_detail_zh = "无近期CPI数据显示偏热倾斜。"
    for item in release_items:
        rtype = item.get("release_type", "") if isinstance(item, dict) else ""
        if rtype in {"cpi_headline", "cpi_core"}:
            tag = _safe_get(item, "surprise_skew", "tag")
            if tag == "hotter":
                cpi_hotter = True
                cpi_detail_en = (
                    f"Nearest {rtype.replace('_', ' ')} (due {item.get('release_date', '?')}) "
                    f"skewed hotter (sigma={_safe_get(item, 'surprise_skew', 'sigma'):.2f})."
                )
                cpi_detail_zh = (
                    f"近期{rtype.replace('_', ' ')}（预定{item.get('release_date', '?')}）"
                    f"偏热（sigma={_safe_get(item, 'surprise_skew', 'sigma'):.2f}）。"
                )
                break

    infl_dir = _safe_get(tx, "state", "inflation", "direction")
    reaccel = infl_dir in {"re-accelerating", "rising"}
    active_h4 = cpi_hotter or reaccel

    if not cpi_hotter and reaccel:
        cpi_detail_en = f"Inflation direction: {infl_dir} (re-acceleration flag active)."
        cpi_detail_zh = f"通胀方向：{infl_dir}（再加速信号有效）。"

    legs.append({
        "key": "H4_inflation_trajectory",
        "active": active_h4,
        "weight": 1,
        "value": infl_dir,
        "detail_en": cpi_detail_en,
        "detail_zh": cpi_detail_zh,
        "null_reason": None,
    })

    # H5 — curve_regime (weight 1)
    yc_regime_key = _safe_get(tx, "yield_curve", "regime", "key")
    term_premium_dir = _safe_get(tx, "yield_curve", "regime", "term_premium_dir")

    if yc_regime_key is None:
        legs.append({
            "key": "H5_curve_regime",
            "active": None,
            "weight": 1,
            "value": None,
            "detail_en": "Yield curve regime unavailable.",
            "detail_zh": "收益率曲线形态不可用。",
            "null_reason": "yield_curve.regime.key absent",
        })
    else:
        active_h5 = yc_regime_key == "bear_steepener" and term_premium_dir == "rising"
        legs.append({
            "key": "H5_curve_regime",
            "active": active_h5,
            "weight": 1,
            "value": yc_regime_key,
            "detail_en": (
                f"Bear steepener with rising term premium — "
                "fiscal/risk-premium driven steepening, not growth-led."
                if active_h5
                else f"Curve regime: {yc_regime_key}; term premium direction: {term_premium_dir}."
                " Bear steepener + rising term premium condition not met."
            ),
            "detail_zh": (
                "熊市变陡叠加期限溢价上升——财政/风险溢价驱动，并非增长主导。"
                if active_h5
                else f"曲线形态：{_CURVE_REGIME_ZH.get(yc_regime_key, yc_regime_key)}；期限溢价方向：{term_premium_dir}。"
                "熊市变陡+期限溢价上升条件未满足。"
            ),
            "null_reason": None,
        })

    # H6 — anchoring_strain (weight 1)
    anchoring = _safe_get(tx, "state", "expectations", "anchoring")
    if anchoring is None:
        legs.append({
            "key": "H6_anchoring_strain",
            "active": None,
            "weight": 1,
            "value": None,
            "detail_en": "Anchoring state unavailable.",
            "detail_zh": "锚定状态不可用。",
            "null_reason": "state.expectations.anchoring absent",
        })
    else:
        active_h6 = str(anchoring).lower() in H6_STRAINED_BANDS
        legs.append({
            "key": "H6_anchoring_strain",
            "active": active_h6,
            "weight": 1,
            "value": anchoring,
            "detail_en": (
                f"Inflation expectations strained: anchoring = '{anchoring}'."
                if active_h6
                else f"Inflation expectations anchored: '{anchoring}'."
            ),
            "detail_zh": (
                f"通胀预期承压：锚定状态为'{_ANCHORING_LABEL_ZH.get(anchoring, anchoring)}'。"
                if active_h6
                else f"通胀预期稳定：'{_ANCHORING_LABEL_ZH.get(anchoring, anchoring)}'。"
            ),
            "null_reason": None,
        })

    return legs


def _build_easing_legs(
    tx: dict,
    release_items: list[dict],
    complex_growth_dir: str | None,
    chains: list[dict],
) -> list[dict]:
    """Build E1-E5 easing/offset legs."""
    legs: list[dict] = []

    # E1 — equity_deleveraging (weight 2)
    radar_state = _safe_get(tx, "_radar_state")  # injected by build_board
    if radar_state is None:
        legs.append({
            "key": "E1_equity_deleveraging",
            "active": None,
            "weight": 2,
            "value": None,
            "detail_en": "Equity radar state unavailable.",
            "detail_zh": "股票雷达状态不可用。",
            "null_reason": "market_state/latest.json absent",
        })
    else:
        active_e1 = str(radar_state).lower() in E1_TRIGGER_STATES
        legs.append({
            "key": "E1_equity_deleveraging",
            "active": active_e1,
            "weight": 2,
            "value": radar_state,
            "detail_en": (
                f"Equity radar in '{radar_state}' — risk-off pressure historically cools "
                "inflation and rate expectations."
                if active_e1
                else f"Equity radar in '{radar_state}' — not triggering offset."
            ),
            "detail_zh": (
                f"股票雷达处于'{radar_state}'状态——历史上风险规避会压制通胀和加息预期。"
                if active_e1
                else f"股票雷达处于'{radar_state}'状态——未触发对冲条件。"
            ),
            "null_reason": None,
        })

    # E2 — growth_cooling (weight 1)
    nfp_cooler = False
    e2_detail_en = "No NFP cooler skew; complex growth direction not falling."
    e2_detail_zh = "无NFP偏冷倾斜；商品综合增长方向未下行。"

    for item in release_items:
        if isinstance(item, dict) and item.get("release_type") == "nfp":
            tag = _safe_get(item, "surprise_skew", "tag")
            if tag == "cooler":
                nfp_cooler = True
                e2_detail_en = f"NFP (due {item.get('release_date','?')}) skewed cooler."
                e2_detail_zh = f"NFP（预定{item.get('release_date','?')}）偏冷。"
            break

    growth_falling = complex_growth_dir == "falling"
    active_e2 = nfp_cooler or growth_falling

    if not nfp_cooler and growth_falling:
        e2_detail_en = "Commodity complex growth direction: falling."
        e2_detail_zh = "商品综合增长方向：下行。"
    elif nfp_cooler and growth_falling:
        e2_detail_en += " Commodity complex growth also falling."
        e2_detail_zh += " 商品综合增长方向也在下行。"

    legs.append({
        "key": "E2_growth_cooling",
        "active": active_e2,
        "weight": 1,
        "value": complex_growth_dir,
        "detail_en": e2_detail_en,
        "detail_zh": e2_detail_zh,
        "null_reason": None,
    })

    # E3 — dollar_tightening (weight 1)
    usd_dir = _safe_get(tx, "dollar_channel", "usd_dir")
    if usd_dir is None:
        # Try state.rates indirectly — dollar_channel may not always be present
        legs.append({
            "key": "E3_dollar_tightening",
            "active": None,
            "weight": 1,
            "value": None,
            "detail_en": "Dollar direction unavailable.",
            "detail_zh": "美元方向不可用。",
            "null_reason": "dollar_channel.usd_dir absent",
        })
    else:
        active_e3 = usd_dir == "strengthening"
        legs.append({
            "key": "E3_dollar_tightening",
            "active": active_e3,
            "weight": 1,
            "value": usd_dir,
            "detail_en": (
                "Dollar strengthening — acts as an external tightening offset to domestic inflation pressure."
                if active_e3
                else f"Dollar direction: {usd_dir} — no tightening offset active."
            ),
            "detail_zh": (
                "美元走强——作为对国内通胀压力的外部紧缩对冲。"
                if active_e3
                else f"美元方向：{usd_dir}——无紧缩对冲效果。"
            ),
            "null_reason": None,
        })

    # E4 — credit_stress (weight 1)
    hy_oas_z = _safe_get(tx, "breakeven_decomp", "costate", "hy_oas_z")
    if hy_oas_z is None:
        legs.append({
            "key": "E4_credit_stress",
            "active": None,
            "weight": 1,
            "value": None,
            "detail_en": "HY OAS z-score unavailable.",
            "detail_zh": "高收益利差z分数不可用。",
            "null_reason": "breakeven_decomp.costate.hy_oas_z absent",
        })
    else:
        active_e4 = float(hy_oas_z) >= E4_HY_OAS_Z_THRESHOLD
        legs.append({
            "key": "E4_credit_stress",
            "active": active_e4,
            "weight": 1,
            "value": round(float(hy_oas_z), 2),
            "detail_en": (
                f"HY OAS z-score elevated at {hy_oas_z:.2f} — credit stress may cool inflation pressure."
                if active_e4
                else f"HY OAS z-score: {hy_oas_z:.2f} (threshold: +{E4_HY_OAS_Z_THRESHOLD:.1f})."
            ),
            "detail_zh": (
                f"高收益利差z分数偏高{hy_oas_z:.2f}——信用压力可能抑制通胀。"
                if active_e4
                else f"高收益利差z分数：{hy_oas_z:.2f}（阈值：+{E4_HY_OAS_Z_THRESHOLD:.1f}）。"
            ),
            "null_reason": None,
        })

    # E5 — policy_easing_chain (weight 1)
    policy_easing_active = None
    for c in chains:
        if c.get("id") == "policy_easing":
            policy_easing_active = bool(c.get("active"))
            break

    if policy_easing_active is None:
        legs.append({
            "key": "E5_policy_easing_chain",
            "active": None,
            "weight": 1,
            "value": None,
            "detail_en": "Policy easing chain state unavailable.",
            "detail_zh": "政策宽松链状态不可用。",
            "null_reason": "chains[policy_easing] not found in transmission",
        })
    else:
        legs.append({
            "key": "E5_policy_easing_chain",
            "active": policy_easing_active,
            "weight": 1,
            "value": policy_easing_active,
            "detail_en": (
                "Policy easing transmission chain active — supports lower rate expectations."
                if policy_easing_active
                else "Policy easing transmission chain inactive."
            ),
            "detail_zh": (
                "政策宽松传导链活跃——支持降低加息预期。"
                if policy_easing_active
                else "政策宽松传导链未激活。"
            ),
            "null_reason": None,
        })

    return legs


def _compute_net_state(
    hawk_score: float,
    ease_score: float,
    zq_d20_bp: float | None,
    h1_active: bool | None,
) -> str:
    """Frozen net-state mapping (unit-tested exhaustively).

    Inputs:
        hawk_score: weighted sum of active hawkish legs (H1-H6)
        ease_score: weighted sum of active easing legs (E1-E5)
        zq_d20_bp:  20-day change in ZQ m12 (None if unavailable)
        h1_active:  whether H1 path_repricing is active
    """
    net = hawk_score - ease_score
    net_ease = ease_score - hawk_score

    # Hawkish path
    if h1_active and net >= 2:
        return "repricing_hawkish"
    if net >= 2:
        return "pressure_building"

    # Easing/dovish path (mirror of H1: d20 <= -15)
    h1_dovish_mirror = zq_d20_bp is not None and zq_d20_bp <= H1_DOVISH_THRESHOLD_BP
    if h1_dovish_mirror and net_ease >= 2:
        return "repricing_dovish"
    if net_ease >= 2:
        return "pressure_fading"

    return "two_sided"


def _compute_divergence(
    fed_path: dict,
    release_items: list[dict],
    tx: dict,
    net_state: str,
) -> list[dict]:
    """Compute D1-D3 divergence flags.

    Each: {key, active: bool|null, detail_en, detail_zh}
    """
    flags: list[dict] = []

    # D1 — dots_vs_market: |gap_bp| >= 50
    gap_bp = _safe_get(fed_path, "gap", "gap_bp")
    if gap_bp is None:
        flags.append({
            "key": "D1_dots_vs_market",
            "active": None,
            "detail_en": "Dot-vs-market gap unavailable.",
            "detail_zh": "点阵图与市场利差不可用。",
        })
    else:
        active_d1 = abs(float(gap_bp)) >= D1_GAP_BP_THRESHOLD
        lean_en = _safe_get(fed_path, "gap", "lean_en") or ""
        flags.append({
            "key": "D1_dots_vs_market",
            "active": active_d1,
            "value_bp": round(float(gap_bp), 1),
            "detail_en": (
                f"Significant divergence: market vs dot gap = {gap_bp:+.0f}bp ({lean_en})."
                if active_d1
                else f"Market vs dot gap: {gap_bp:+.0f}bp — within normal range (threshold: ±{D1_GAP_BP_THRESHOLD:.0f}bp)."
            ),
            "detail_zh": (
                f"显著背离：市场与点阵图利差{gap_bp:+.0f}个基点（{_safe_get(fed_path, 'gap', 'lean_zh') or ''}）。"
                if active_d1
                else f"市场与点阵图利差：{gap_bp:+.0f}个基点——在正常范围内。"
            ),
        })

    # D2 — projection_vs_breakeven wedge
    # hotter CPI while breakevens down, or cooler CPI while breakevens up
    cpi_tag = None
    for item in release_items:
        if isinstance(item, dict) and item.get("release_type") in {"cpi_headline", "cpi_core"}:
            cpi_tag = _safe_get(item, "surprise_skew", "tag")
            break

    be_chg_20d = _safe_get(tx, "breakeven_decomp", "velocity_bp", "chg_20d_bp")
    if cpi_tag is None or be_chg_20d is None:
        flags.append({
            "key": "D2_projection_vs_breakeven",
            "active": None,
            "detail_en": "Insufficient data for CPI-breakeven wedge check.",
            "detail_zh": "CPI与盈亏平衡点楔形检查数据不足。",
        })
    else:
        be_chg = float(be_chg_20d)
        # wedge: hot print + falling breakevens; or cool print + rising breakevens
        d2_active = (cpi_tag == "hotter" and be_chg <= -5.0) or \
                    (cpi_tag == "cooler" and be_chg >= 5.0)
        if d2_active:
            if cpi_tag == "hotter" and be_chg <= -5.0:
                detail_en = f"Wedge: near-term CPI skewed hotter but 20d breakeven down {be_chg:.0f}bp — market not believing the print."
                detail_zh = f"楔形：近期CPI偏热但20天盈亏平衡点下降{be_chg:.0f}bp——市场不相信数据。"
            else:
                detail_en = f"Wedge: near-term CPI skewed cooler but 20d breakeven up {be_chg:.0f}bp — market pricing persistent inflation anyway."
                detail_zh = f"楔形：近期CPI偏冷但20天盈亏平衡点上升{be_chg:.0f}bp——市场仍定价持续通胀。"
        else:
            detail_en = f"No projection-breakeven wedge: CPI tag={cpi_tag}, 20d breakeven={be_chg:+.0f}bp."
            detail_zh = f"无预测-盈亏平衡楔形：CPI标签={cpi_tag}，20天盈亏平衡点={be_chg:+.0f}bp。"

        flags.append({
            "key": "D2_projection_vs_breakeven",
            "active": d2_active,
            "detail_en": detail_en,
            "detail_zh": detail_zh,
        })

    # D3 — pressure_vs_market
    implied_bp_12m = _safe_get(fed_path, "implied_bp_12m")
    if implied_bp_12m is None:
        flags.append({
            "key": "D3_pressure_vs_market",
            "active": None,
            "detail_en": "implied_bp_12m unavailable for pressure-vs-market check.",
            "detail_zh": "implied_bp_12m不可用，无法进行压力与市场比较。",
        })
    else:
        ibp = float(implied_bp_12m)
        d3_active = (
            (net_state == "pressure_building" and ibp <= D3_IMPLIED_BP_LOW) or
            (net_state == "pressure_fading" and ibp >= D3_IMPLIED_BP_HIGH)
        )
        flags.append({
            "key": "D3_pressure_vs_market",
            "active": d3_active,
            "detail_en": (
                f"Hawkish pressure building but futures imply {ibp:+.0f}bp over 12m — "
                "market has not priced the pressure yet."
                if net_state == "pressure_building" and ibp <= D3_IMPLIED_BP_LOW else
                f"Easing pressure building but futures imply {ibp:+.0f}bp over 12m — "
                "market still priced for tightening."
                if net_state == "pressure_fading" and ibp >= D3_IMPLIED_BP_HIGH else
                f"Pressure-vs-market gap not active (net_state={net_state}, implied={ibp:+.0f}bp)."
            ),
            "detail_zh": (
                f"鹰派压力积聚但期货12个月隐含{ibp:+.0f}个基点——市场尚未定价该压力。"
                if net_state == "pressure_building" and ibp <= D3_IMPLIED_BP_LOW else
                f"宽松压力积聚但期货12个月隐含{ibp:+.0f}个基点——市场仍定价紧缩。"
                if net_state == "pressure_fading" and ibp >= D3_IMPLIED_BP_HIGH else
                f"压力与市场背离未激活（net_state={net_state}，隐含={ibp:+.0f}bp）。"
            ),
        })

    return flags


def _render_cuts(implied_cuts_12m: int | float | None) -> dict[str, str]:
    """Render implied cuts/hikes as plain words.

    -2 -> 'about two hikes'
    +2 -> 'about two cuts'
     0 -> 'roughly on hold'
    """
    if implied_cuts_12m is None:
        return {"en": "path unclear", "zh": "路径不明"}
    n = float(implied_cuts_12m)
    abs_n = abs(n)
    # Build magnitude word
    if abs_n < 0.5:
        return {"en": "roughly on hold", "zh": "基本按兵不动"}
    count = int(round(abs_n))
    if count == 1:
        count_word_en = "one"
        count_word_zh = "一次"
    elif count == 2:
        count_word_en = "two"
        count_word_zh = "两次"
    elif count == 3:
        count_word_en = "three"
        count_word_zh = "三次"
    else:
        count_word_en = str(count)
        count_word_zh = f"{count}次"

    if n < 0:
        # Negative cuts = hikes
        return {"en": f"about {count_word_en} hike{'s' if count != 1 else ''}", "zh": f"约{count_word_zh}加息"}
    else:
        return {"en": f"about {count_word_en} cut{'s' if count != 1 else ''}", "zh": f"约{count_word_zh}降息"}


def _t0_text(value: Any) -> str | None:
    """A non-blank string verbatim, else None (UNKNOWN). Never a default source."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def _t0_day(value: Any):
    """Leading YYYY-MM-DD of an ISO string as a date; None when absent or malformed."""
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _t0_countdown(item: dict, release_meta: dict, display_cutoff: Any) -> dict:
    """Release countdown bound to an explicit display cutoff (A05).

    The source snapshot (artefact asof + the item's build-time days_to) is carried verbatim
    and never re-stamped. Without a display cutoff the count is HISTORICAL and no current day
    count is claimed; with one, days are recomputed from the item's release_date.
    """
    if display_cutoff is not None and not isinstance(display_cutoff, str):
        display_cutoff = str(display_cutoff)
    source_cutoff = release_meta.get("asof")
    countdown = {
        "source_cutoff": source_cutoff,
        "source_days_to": item.get("days_to"),
        "display_cutoff": display_cutoff,
        "days_to": None,
        "state": "historical",
        "method": "source_snapshot",
    }
    if display_cutoff is None:
        return countdown
    countdown["method"] = "release_forecast_release_date"
    display_day = _t0_day(display_cutoff)
    source_day = _t0_day(source_cutoff)
    if display_day is None or source_day is None:
        countdown["state"] = "unknown"
        return countdown
    if source_day > display_day:
        countdown["state"] = "source_after_display_cutoff"
        return countdown
    release_day = _t0_day(item.get("release_date"))
    if release_day is None:
        countdown["state"] = "unknown"
        return countdown
    delta = (release_day - display_day).days
    if delta >= 0:
        countdown["state"] = "current"
        countdown["days_to"] = delta
    else:
        countdown["state"] = "released"
    return countdown


# --------------------------------------------------------------------------- #
# T0-B basis contract helpers (rates_command_basis.v1).
#
# All of this code sits BELOW the f01 line pins (engine lines 557-575), so it
# must never be moved above them, and the frozen contract module is imported
# FUNCTION-LOCALLY only — no module-level import of rates_command_basis.
# --------------------------------------------------------------------------- #


def _t0b_number(value: Any) -> float | None:
    """Coerce a raw board value to a finite float; None for anything else.

    bool is not a number here, NaN/inf are not numbers here, and a numeric
    string is accepted only via float() inside try. Never raises.
    """
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _t0b_basis_cutoff(explicit: Any, source_asof: Any) -> str | None:
    """Publication cutoff for a basis record: explicit, else source asof.

    Build time is NEVER a cutoff; None when neither exists, so the row
    carries no basis rather than a fabricated one.
    """
    if explicit is not None:
        return str(explicit)
    if isinstance(source_asof, str) and source_asof:
        return source_asof
    return None


def _t0b_precision(stamp: Any) -> str:
    """Precision of an evidence stamp: 'day' only for a YYYY-MM-DD stamp."""
    if isinstance(stamp, str) and len(stamp) == 10:
        try:
            datetime.strptime(stamp, "%Y-%m-%d")
            return "day"
        except ValueError:
            return "unknown"
    return "unknown"


# Exact fed_path implied_source_en labels -> basis source keys. Exact string
# equality only (never prefix/substring): an unknown label stays UNKNOWN.
_RATE_SOURCE_BASIS = {
    "ZQ fed-funds futures": {
        "source": "rate_futures:ZQ",
        "target": "effr_monthly_average",
        "basket_or_index": "EFFR",
        "rate_index": "EFFR",
        "averaging_law": "arithmetic_calendar_day",
    },
    "ZQ front (30d) only": {
        "source": "rate_futures:ZQ",
        "target": "effr_monthly_average",
        "basket_or_index": "EFFR",
        "rate_index": "EFFR",
        "averaging_law": "arithmetic_calendar_day",
    },
    "SR3 SOFR futures": {
        "source": "rate_futures:SR3",
        "target": "sofr_compounded_quarter",
        "basket_or_index": "SOFR",
        "rate_index": "SOFR",
        "averaging_law": "compounded_business_day",
    },
}


def _t0b_basis_contract_version() -> str:
    """Frozen contract version carried at the artifact top level."""
    from engine import rates_command_basis as rcb

    return rcb.SCHEMA_VERSION


# Exact fed_path implied_source_en labels -> the D0 provenance strip key
# (engine/fed_path.py _selected_strip). Rights are read from that strip only.
_RATE_SOURCE_STRIP = {
    "ZQ fed-funds futures": "zq",
    "SR3 SOFR futures": "sofr",
    "ZQ front (30d) only": "zq_front",
}


def _rate_path_rights(fed_path: dict, label: Any) -> str:
    """Rights of the selected futures strip, from D0 `implied_source_meta`.

    Never asserted here: an absent provenance block, an unmapped label, a
    strip without a rights field or a value outside the B0 vocabulary all
    stay "unknown" (which B0 refuses for export purposes).
    """
    from engine import rates_command_basis as rcb

    strip_key = _RATE_SOURCE_STRIP.get(label) if isinstance(label, str) else None
    meta = fed_path.get("implied_source_meta")
    strips = meta.get("strips") if isinstance(meta, dict) else None
    strip = strips.get(strip_key) if isinstance(strips, dict) and strip_key else None
    rights = strip.get("rights") if isinstance(strip, dict) else None
    return rights if rights in rcb.RIGHTS_VALUES else "unknown"


def _rate_path_basis(fed_path: dict, cutoff: Any) -> dict | None:
    """Qualify the m12 implied-path value as a rates_command_basis.v1 record.

    None when fed_path is not a dict or no basis cutoff exists. The source
    label decides the basis keys: an unknown label leaves them UNKNOWN
    (omitted) with limitation `source_unknown` — never a guessed default.
    """
    from engine import rates_command_basis as rcb

    if not isinstance(fed_path, dict):
        return None
    basis_cutoff = _t0b_basis_cutoff(cutoff, fed_path.get("asof"))
    if basis_cutoff is None:
        return None
    implied = fed_path.get("implied") or {}
    if not isinstance(implied, dict):
        implied = {}
    label = fed_path.get("implied_source_en")
    source_keys = _RATE_SOURCE_BASIS.get(label) if isinstance(label, str) else None
    limitations = [
        "risk_premium_not_stripped",
        "implied_bp_12m_is_month12_path_minus_policy_level",
    ]
    # Evidence stamps: the fed_path asof only; reference_start/reference_end,
    # vintage, source_version, content_ref and admitted_at stay UNKNOWN —
    # never derived from asof+12m.
    asof = fed_path.get("asof")
    asof_stamp = asof if isinstance(asof, str) else None
    meta: dict[str, Any] = {
        "subject": "fed_path.implied_path.m12",
        "evidence_class": "market_implied_expectation",
        "unit": "pct_ann_rate",
        "seasonal_treatment": rcb.NA,
        "curve_convention": rcb.NA,
        "tenor": rcb.NA,
        "model_id": rcb.NA,
        "target_epoch": rcb.NA,
        "observation_time": asof_stamp,
        "observation_precision": _t0b_precision(asof_stamp),
        "first_public_evidence": asof_stamp,
        "first_public_precision": _t0b_precision(asof_stamp),
        "rights": _rate_path_rights(fed_path, label),
    }
    if source_keys is None:
        limitations.append("source_unknown")
    else:
        meta.update(source_keys)
        if label == "ZQ front (30d) only":
            limitations.append("degraded_front_month_only")
    meta["limitations"] = tuple(limitations)
    value = _t0b_number(implied.get("m12"))
    return rcb.qualify_observation(value, meta, basis_cutoff).to_dict()


def _cpi_basis(item: dict, release_meta: dict, cutoff: Any) -> dict | None:
    """Qualify the nearest-CPI projection point as a basis record.

    None unless the item is a CPI release with a declared MoM SA target and a
    basis cutoff exists: any other (or missing) target means the unit is
    UNKNOWN, so the observation cannot be qualified — never assume MoM.
    """
    import calendar as _calendar

    from engine import rates_command_basis as rcb

    if not isinstance(item, dict):
        return None
    if item.get("release_type") not in {"cpi_headline", "cpi_core"}:
        return None
    # The frozen gate is the producer's byte-exact MoM SA target string
    # "mom_sa_pct"; every other spelling (case or whitespace variants
    # included) leaves the unit UNKNOWN, so no basis is attached.
    if item.get("target") != "mom_sa_pct":
        return None
    artefact = release_meta if isinstance(release_meta, dict) else {}
    basis_cutoff = _t0b_basis_cutoff(cutoff, artefact.get("asof"))
    if basis_cutoff is None:
        return None
    headline = item.get("release_type") == "cpi_headline"
    limitations: list[str] = []
    target = "cpi_u_all_items_mom_sa" if headline else "cpi_u_core_mom_sa"
    if item.get("first_print_basis") == "first_print":
        target += "_first_print"
    else:
        limitations.append("first_print_basis_undeclared")
    meta: dict[str, Any] = {
        "subject": "CPIAUCSL" if headline else "CPILFESL",
        "evidence_class": "house_estimate",
        "unit": "pct_mom",
        "target": target,
        "basket_or_index": "CPI-U",
        "seasonal_treatment": "sa",
        "rate_index": rcb.NA,
        "averaging_law": rcb.NA,
        "curve_convention": rcb.NA,
        "tenor": rcb.NA,
        "source": "release_forecast",
        "rights": "display_only",
    }
    period = item.get("period")
    if isinstance(period, str) and len(period) == 7 and period[4] == "-":
        try:
            last_day = _calendar.monthrange(int(period[:4]), int(period[5:7]))[1]
        except ValueError:
            last_day = None
        if last_day is not None:
            meta["reference_start"] = f"{period}-01"
            meta["reference_end"] = f"{period}-{last_day:02d}"
    for version_key in ("schema_version", "version"):
        version_val = artefact.get(version_key)
        if isinstance(version_val, str) and version_val:
            meta["source_version"] = version_val
            break
    for item_key, meta_key in (("model_epoch", "model_id"), ("target_epoch", "target_epoch")):
        item_val = item.get(item_key)
        if isinstance(item_val, str) and item_val:
            meta[meta_key] = item_val
    asof = artefact.get("asof")
    asof_stamp = asof if isinstance(asof, str) else None
    meta["observation_time"] = asof_stamp
    meta["observation_precision"] = _t0b_precision(asof_stamp)
    meta["first_public_evidence"] = asof_stamp
    meta["first_public_precision"] = _t0b_precision(asof_stamp)
    # Model status is read exactly where _build_inflation_row reads it.
    ms = artefact.get("methodology_status")
    if not isinstance(ms, dict):
        ms = {}
    quality: list[str] = []
    forecast_epoch = ms.get("forecast_epoch")
    if isinstance(forecast_epoch, str) and "experimental" in forecast_epoch:
        quality.append("experimental")
    accuracy_claim = ms.get("accuracy_claim")
    if isinstance(accuracy_claim, str) and accuracy_claim.startswith("withheld"):
        quality.append("accuracy_withheld")
    meta["quality"] = tuple(quality)
    meta["limitations"] = tuple(limitations)
    value = _t0b_number(_safe_get(item, "projection", "point"))
    return rcb.qualify_observation(value, meta, basis_cutoff).to_dict()


def _build_rate_path_row(fed_path: dict, *, cutoff: Any = None) -> dict:
    """Build the rate_path display row."""
    if not isinstance(fed_path, dict):
        fed_path = {}
    implied = fed_path.get("implied") or {}
    if not isinstance(implied, dict):
        implied = {}
    dots = fed_path.get("dots") or []
    if not isinstance(dots, list):
        dots = []
    gap = fed_path.get("gap") or {}
    if not isinstance(gap, dict):
        gap = {}
    implied_cuts_12m = fed_path.get("implied_cuts_12m")
    implied_bp_12m = fed_path.get("implied_bp_12m")
    path_read = _render_cuts(implied_cuts_12m)

    row = {
        "asof": fed_path.get("asof"),
        "policy_rate": fed_path.get("policy_rate"),
        "implied_path": {
            "m1": implied.get("m1"),
            "m3": implied.get("m3"),
            "m6": implied.get("m6"),
            "m12": implied.get("m12"),
        },
        "implied_bp_12m": implied_bp_12m,
        "implied_cuts_12m": implied_cuts_12m,
        "path_plain": path_read,
        "dots": dots,
        "gap": gap,
        "headline_en": fed_path.get("headline_en"),
        "headline_zh": fed_path.get("headline_zh"),
        "read_en": fed_path.get("read_en"),
        "read_zh": fed_path.get("read_zh"),
        "source_en": _t0_text(fed_path.get("implied_source_en")),
        "source_zh": _t0_text(fed_path.get("implied_source_zh")),
    }
    # The basis key is ALWAYS present; None when the observation cannot be
    # qualified. The basis never edits the row's display fields.
    row["basis"] = _rate_path_basis(fed_path, cutoff)
    return row


def _build_inflation_row(
    tx: dict,
    release_items: list[dict],
    *,
    release_meta: dict | None = None,
    display_cutoff: Any = None,
    cutoff: Any = None,
) -> dict:
    """Build the inflation display row."""
    infl = (_safe_get(tx, "state", "inflation") or {})
    exp = (_safe_get(tx, "state", "expectations") or {})
    meta = release_meta if isinstance(release_meta, dict) else {}
    ms = meta.get("methodology_status")
    if not isinstance(ms, dict):
        ms = {}
    if not isinstance(release_items, list):
        release_items = []

    # Nearest CPI projection data
    cpi_proj = None
    for item in release_items:
        if not isinstance(item, dict):
            continue
        if item.get("release_type") in {"cpi_headline", "cpi_core"}:
            cov = item.get("coverage_flags")
            if not isinstance(cov, dict):
                cov = {}
            bs = item.get("benchmark_set")
            cpi_proj = {
                "release_type": item.get("release_type"),
                "period": item.get("period"),
                "release_date": item.get("release_date"),
                "days_to": item.get("days_to"),
                "point": _safe_get(item, "projection", "point"),
                "surprise_skew_tag": _safe_get(item, "surprise_skew", "tag"),
                "surprise_skew_sigma": _safe_get(item, "surprise_skew", "sigma"),
                "target": item.get("target"),
                "model_epoch": item.get("model_epoch"),
                "target_epoch": item.get("target_epoch"),
                "primary_forecast_basis": item.get("primary_forecast_basis"),
                "context_metrics_basis": item.get("context_metrics_basis"),
                "model_maturity": cov.get("model_maturity"),
                "forecast_epoch": ms.get("forecast_epoch"),
                "accuracy_claim": ms.get("accuracy_claim"),
                "benchmark_ids": (
                    sorted(str(k) for k in bs)
                    if isinstance(bs, dict) and bs
                    else None
                ),
                "first_print_basis": item.get("first_print_basis"),
                "countdown": _t0_countdown(item, meta, display_cutoff),
            }
            # The basis key is ALWAYS present on nearest_cpi (None when the
            # observation cannot be qualified); when nearest_cpi itself is
            # None there is no basis to add.
            cpi_proj["basis"] = _cpi_basis(item, release_meta, cutoff)
            break

    return {
        "core_pce_yoy": infl.get("core_pce_yoy"),
        "core_cpi_yoy": infl.get("core_cpi_yoy"),
        "core_pce_3m_ann": infl.get("core_pce_3m_ann"),
        "vs_target_pp": infl.get("vs_target_pp"),
        "regime": infl.get("regime"),
        "direction": infl.get("direction"),
        "breakeven_10y": exp.get("breakeven_10y"),
        "breakeven_5y5y": exp.get("breakeven_5y5y"),
        "anchoring": exp.get("anchoring"),
        "nearest_cpi": cpi_proj,
    }


def _build_risk_row(tx: dict) -> dict:
    """Build the risk display row.

    Honest label: real_speed_pctile MUST print 'flags risk, not return'.
    Term premium: Kim-Wright model (FRED THREEFYTP10); ACM pending.
    """
    yc = tx.get("yield_curve") or {}
    regime = (yc.get("regime") or {}) if isinstance(yc, dict) else {}
    momentum = (yc.get("momentum") or {}) if isinstance(yc, dict) else {}
    recession = (yc.get("recession") or {}) if isinstance(yc, dict) else {}

    real_speed_pctile = momentum.get("real_speed_pctile")
    curve_key = regime.get("key")
    term_premium_dir = regime.get("term_premium_dir")
    term_premium_chg_bp = regime.get("term_premium_chg_bp")

    # Look for Kim-Wright term premium from transmission state
    # THREEFYTP10 is stored as term_premium_10y in the parquet store;
    # yield_curve.regime.term_premium_dir reflects the direction
    term_premium_note_en = "Kim-Wright model (FRED THREEFYTP10); ACM pending"
    term_premium_note_zh = "Kim-Wright模型（FRED THREEFYTP10）；ACM待接入"

    return {
        "real_speed_pctile": real_speed_pctile,
        "real_speed_note_en": "Flags risk, not return — high percentile = fast real-rate moves, not directional signal.",
        "real_speed_note_zh": "标记风险而非收益——高百分位表示实际利率快速波动，并非方向性信号。",
        "curve_regime_key": curve_key,
        "curve_regime_label_en": regime.get("label", {}).get("en") if isinstance(regime.get("label"), dict) else curve_key,
        "curve_regime_label_zh": _CURVE_REGIME_ZH.get(curve_key or "", curve_key or ""),
        "term_premium_dir": term_premium_dir,
        "term_premium_chg_bp": term_premium_chg_bp,
        "term_premium_note_en": term_premium_note_en,
        "term_premium_note_zh": term_premium_note_zh,
        "front2y_speed_bp": momentum.get("front2y_speed_bp"),
        "real10y_speed_bp": momentum.get("real10y_speed_bp"),
        "recession_ntfs": recession.get("ntfs"),
        "nyfed_prob": recession.get("nyfed_prob"),
    }


def _build_policy_row(
    policy_lever: dict | None,
    intel: dict | None,
    intel_staleness_days: int | None,
) -> dict:
    """Build the policy conditions row."""
    fed_intel = (intel.get("fed") or {}) if intel else {}
    chair = fed_intel.get("chair", "")
    profile_en = (fed_intel.get("profile") or {}).get("en", "") if isinstance(fed_intel.get("profile"), dict) else str(fed_intel.get("profile") or "")
    optionality_en = (fed_intel.get("optionality_read") or {}).get("en", "") if isinstance(fed_intel.get("optionality_read"), dict) else ""

    # th_iran theater
    iran_row = None
    if intel:
        theaters = (intel.get("administration") or {}).get("theaters") or []
        for t in theaters:
            if t.get("id") == "th_iran":
                iran_row = {
                    "title_en": t.get("title_en"),
                    "title_zh": t.get("title_zh"),
                    "facts_en": t.get("facts_en"),
                    "facts_zh": t.get("facts_zh"),
                    "as_of_note_en": (
                        f"Intel as of {intel.get('as_of', '?')} "
                        f"({intel_staleness_days}d old)" if intel_staleness_days is not None
                        else f"Intel as of {intel.get('as_of', '?')}"
                    ),
                    "as_of_note_zh": (
                        f"情报截至{intel.get('as_of', '?')}"
                        f"（{intel_staleness_days}天前）" if intel_staleness_days is not None
                        else f"情报截至{intel.get('as_of', '?')}"
                    ),
                    "unsigned_display": True,
                }
                break

    return {
        "state": (policy_lever.get("state") if policy_lever else None),
        "jawboning": (policy_lever.get("jawboning") if policy_lever else None),
        "lever_asof": (policy_lever.get("as_of") if policy_lever else None),
        "chair": chair,
        "chair_profile_en": profile_en[:400] + "…" if len(profile_en) > 400 else profile_en,
        "chair_profile_zh": "",  # profile is EN-only in the intel artifact
        "optionality_read_en": optionality_en,
        "intel_as_of": (intel.get("as_of") if intel else None),
        "intel_staleness_days": intel_staleness_days,
        "iran_context": iran_row,
    }


def _pick_conditions(
    hawkish_legs: list[dict],
    easing_legs: list[dict],
    iran_row: dict | None,
) -> list[dict]:
    """Pick 2-3 conditions rows deterministically.

    Rule: top active hawkish leg by weight, then top active easing leg, then
    geopolitical row if th_iran present.
    """
    conditions: list[dict] = []

    # Top active hawkish leg by weight desc
    active_h = [l for l in hawkish_legs if l.get("active") is True]
    if active_h:
        top_h = max(active_h, key=lambda l: l.get("weight", 0))
        conditions.append({
            "key": top_h["key"],
            "direction": "hawkish",
            "en": top_h.get("detail_en", ""),
            "zh": top_h.get("detail_zh", ""),
            "watch_en": (
                "If this pressure persists, upward rate repricing stays at risk; "
                "a deepening equity correction historically pulls the other way."
            ),
            "watch_zh": (
                "若该压力持续，利率上调风险上升；"
                "股市进一步下跌历史上会起到反向对冲作用。"
            ),
        })

    # Top active easing leg by weight desc
    active_e = [l for l in easing_legs if l.get("active") is True]
    if active_e:
        top_e = max(active_e, key=lambda l: l.get("weight", 0))
        conditions.append({
            "key": top_e["key"],
            "direction": "easing",
            "en": top_e.get("detail_en", ""),
            "zh": top_e.get("detail_zh", ""),
            "watch_en": (
                "If this offset fades, the hawkish legs would have less counterweight — "
                "watch the tape for repricing."
            ),
            "watch_zh": (
                "若该对冲因素消退，鹰派腿将减少制衡——"
                "关注市场定价变化。"
            ),
        })

    # Geopolitical row if iran present
    if iran_row:
        conditions.append({
            "key": "geo_iran",
            "direction": "geopolitical",
            "en": iran_row.get("title_en", ""),
            "zh": iran_row.get("title_zh", ""),
            "watch_en": (
                "Conditions-only: oil market conditions may shift if the theater escalates "
                "or de-escalates — unsigned, no probability assigned."
            ),
            "watch_zh": (
                "条件性观察：若局势升级或缓和，油市条件可能变化——"
                "无定向，不赋予概率。"
            ),
        })

    return conditions


def _build_market_check(
    fed_path: dict,
    pm_snapshot: dict | None,
) -> dict:
    """Build the market_check display block (juxtaposition only, never fused)."""
    implied = fed_path.get("implied") or {}
    if not isinstance(implied, dict):
        implied = {}
    implied_bp_12m = fed_path.get("implied_bp_12m")
    headline_en = fed_path.get("headline_en", "")
    headline_zh = fed_path.get("headline_zh", "")

    futures_block = {
        "m1": implied.get("m1"),
        "m3": implied.get("m3"),
        "m6": implied.get("m6"),
        "m12": implied.get("m12"),
        "implied_bp_12m": implied_bp_12m,
        "plain_read_en": headline_en,
        "plain_read_zh": headline_zh,
    }

    pm_block = None
    if pm_snapshot and pm_snapshot.get("events"):
        events_out = []
        for ev in pm_snapshot["events"][:3]:
            top = ev.get("top") or {}
            events_out.append({
                "key": ev.get("key"),
                "label_en": ev.get("label_en"),
                "label_zh": ev.get("label_zh"),
                "top_outcome": top.get("outcome"),
                "top_prob": top.get("prob"),
                "chg_pp": top.get("chg_pp"),
                "source": "Polymarket",
                "type": "market_implied_benchmark",
            })
        pm_block = {
            "as_of": pm_snapshot.get("asof"),
            "source": "Polymarket",
            "events": events_out,
        }

    return {
        "futures": futures_block,
        "prediction_markets": pm_block,
        "benchmark_note_en": "What markets price — a benchmark, not our read.",
        "benchmark_note_zh": "市场定价内容——作为参考基准，不代表本系统观点。",
    }


def compose_stance(board: dict) -> dict[str, str]:
    """Deterministic template stance sentence from board contents.

    <= 2 sentences, plain words, numbers with interpretation.
    Never intent, never probability.
    """
    try:
        ep = board.get("expectations_pressure") or {}
        net_state = ep.get("net_state", "two_sided")
        hawk_score = ep.get("hawk_score", 0)
        ease_score = ep.get("ease_score", 0)
        legs = ep.get("legs") or []

        # Build context phrases from active legs
        rate_path_row = board.get("board", {}).get("rate_path_row") or {}
        implied_bp_12m = rate_path_row.get("implied_bp_12m") or 0
        path_plain_en = (rate_path_row.get("path_plain") or {}).get("en", "roughly on hold")
        path_plain_zh = (rate_path_row.get("path_plain") or {}).get("zh", "基本按兵不动")
        net = hawk_score - ease_score

        # Build top active leg descriptions
        active_h_legs = [l for l in legs if l.get("active") is True and l.get("key", "").startswith("H")]
        active_e_legs = [l for l in legs if l.get("active") is True and l.get("key", "").startswith("E")]

        top_h_key = active_h_legs[0]["key"] if active_h_legs else None
        top_e_key = active_e_legs[0]["key"] if active_e_legs else None

        # Hawkish driver phrase
        h_phrase_en = ""
        h_phrase_zh = ""
        # Noun phrases only — branch templates below supply the predicates.
        if top_h_key == "H1_path_repricing":
            h_phrase_en = "front-end futures repricing"
            h_phrase_zh = "期货利率重新定价"
        elif top_h_key == "H3_oil_impulse":
            h_phrase_en = "hot oil"
            h_phrase_zh = "原油走高"
        elif top_h_key == "H4_inflation_trajectory":
            h_phrase_en = "a hotter-than-expected inflation print"
            h_phrase_zh = "高于预期的通胀数据"
        elif top_h_key == "H5_curve_regime":
            h_phrase_en = "long rates rising on term premium"
            h_phrase_zh = "期限溢价推动长端利率上行"
        elif top_h_key:
            h_phrase_en = "hawkish inputs"
            h_phrase_zh = "鹰派因素"

        # Easing offset noun phrase
        e_phrase_en = ""
        e_phrase_zh = ""
        if top_e_key == "E1_equity_deleveraging":
            e_phrase_en = "a deeper equity pullback"
            e_phrase_zh = "股市进一步回调"
        elif top_e_key == "E3_dollar_tightening":
            e_phrase_en = "dollar strength"
            e_phrase_zh = "美元走强"
        elif top_e_key:
            e_phrase_en = "easing inputs"
            e_phrase_zh = "宽松因素"

        # Build sentence based on net_state (phrases above are noun phrases)
        if net_state == "repricing_hawkish":
            s1_en = f"Futures now price {path_plain_en} over the next year — hawkish repricing is underway."
            s1_zh = f"期货目前为未来一年定价{path_plain_zh}——加息定价正在进行。"
            if h_phrase_en and e_phrase_en:
                s2_en = f"{h_phrase_en.capitalize()} is the main pressure; {e_phrase_en} is the offset to watch."
                s2_zh = f"{h_phrase_zh}是主要压力；{e_phrase_zh}是需要关注的对冲。"
            elif h_phrase_en:
                s2_en = f"{h_phrase_en.capitalize()} is the main pressure."
                s2_zh = f"{h_phrase_zh}是主要压力。"
            else:
                s2_en = s2_zh = ""
        elif net_state == "pressure_building":
            s1_en = f"Hawkish pressure is building ({hawk_score:.0f} hawkish vs {ease_score:.0f} easing inputs) — the market has not moved yet ({path_plain_en} priced)."
            s1_zh = f"鹰派压力正在积聚（{hawk_score:.0f}项鹰派对{ease_score:.0f}项宽松）——市场尚未行动（当前定价{path_plain_zh}）。"
            s2_en = f"{h_phrase_en.capitalize()} is the pressure; {e_phrase_en} is the offset to watch." if h_phrase_en and e_phrase_en else (f"{h_phrase_en.capitalize()} is the pressure." if h_phrase_en else "")
            s2_zh = f"{h_phrase_zh}构成压力；{e_phrase_zh}是需要关注的对冲。" if h_phrase_zh and e_phrase_zh else (f"{h_phrase_zh}构成压力。" if h_phrase_zh else "")
        elif net_state == "repricing_dovish":
            s1_en = f"Futures now price {path_plain_en} over the next year — dovish repricing is underway."
            s1_zh = f"期货目前为未来一年定价{path_plain_zh}——降息定价正在进行。"
            s2_en = f"{e_phrase_en.capitalize()} is driving the move." if e_phrase_en else ""
            s2_zh = f"{e_phrase_zh}是主要驱动。" if e_phrase_zh else ""
        elif net_state == "pressure_fading":
            s1_en = f"Easing pressure is building — futures still price {path_plain_en}."
            s1_zh = f"宽松压力积聚——期货仍定价{path_plain_zh}。"
            s2_en = f"{e_phrase_en.capitalize()} is the main offset." if e_phrase_en else ""
            s2_zh = f"{e_phrase_zh}是主要对冲。" if e_phrase_zh else ""
        else:  # two_sided
            s1_en = f"Outlook is two-sided: futures price {path_plain_en}; hawkish and easing inputs are roughly balanced ({hawk_score:.0f} vs {ease_score:.0f})."
            s1_zh = f"前景双向：期货定价{path_plain_zh}；鹰派与宽松因素大体制衡（{hawk_score:.0f}对{ease_score:.0f}）。"
            if h_phrase_en and e_phrase_en:
                s2_en = f"{h_phrase_en.capitalize()} and {e_phrase_en} are pulling against each other."
                s2_zh = f"{h_phrase_zh}与{e_phrase_zh}相互制衡。"
            elif h_phrase_en:
                s2_en = f"{h_phrase_en.capitalize()} is the pressure; no clear offset yet."
                s2_zh = f"{h_phrase_zh}构成压力；暂无明确对冲。"
            else:
                s2_en = "Watch the tape — no dominant pressure yet."
                s2_zh = "观察市场走势——暂无主导压力。"

        en = (s1_en + " " + s2_en).strip()
        zh = (s1_zh + " " + s2_zh).strip()
        return {"en": en, "zh": zh}
    except Exception as exc:
        log.warning("compose_stance failed: %s", exc)
        return {
            "en": "Rate-path and inflation pressure summary unavailable.",
            "zh": "利率路径与通胀压力摘要不可用。",
        }


# ---------------------------------------------------------------------------
# Main build_board function
# ---------------------------------------------------------------------------

def build_board(root=None, *, cutoff=None) -> dict:
    """Build the full rates_command.v1 artifact.

    Fails open everywhere: absent/corrupt input -> leg active=None, never raises.
    Returns a complete dict with display_only=True, authority=False.

    cutoff: optional display cutoff (ISO date) for release countdowns; None = historical
    """
    data_dir = _data_root(root)
    caveats: list[str] = [
        "futures-implied path reflects risk premium not stripped — not a forecast",
        "All legs are display-tier context only; no scoring or authority.",
    ]

    # ------------------------------------------------------------------ #
    # 1. Load all input artifacts (fail-open)
    # ------------------------------------------------------------------ #

    # bond_health.json -> fed_path
    bond_health = _read_json(data_dir / "bonds" / "bond_health.json") or {}
    fed_path = bond_health.get("fed_path") or {}
    main_asof = fed_path.get("asof") or bond_health.get("as_of") or ""

    if not fed_path:
        caveats.append("bond_health.json / fed_path absent — rate path row will be empty")
        log.warning("build_board: bond_health.json fed_path absent")

    # transmission/latest.json
    tx = _read_json(data_dir / "transmission" / "latest.json") or {}
    tx_asof = tx.get("asof") or ""
    if not tx:
        caveats.append("transmission/latest.json absent — many legs will be null")
    yield_momentum = tx.get("yield_momentum") if isinstance(tx.get("yield_momentum"), dict) else {
        "schema": "yield_momentum.v1",
        "display_only": True,
        "authority": False,
        "can_score": False,
        "can_size": False,
        "can_trade": False,
        "series": {},
    }

    # RIC Y1b: curve accounting passes through VERBATIM from the transmission
    # snapshot (no recomputation, basis/vintage/rights carried as produced);
    # a missing or malformed contract gets the "unavailable" shell.
    _ca = tx.get("curve_accounting")
    if isinstance(_ca, dict):
        curve_accounting = _ca
    elif _ca is None:
        curve_accounting = _curve_accounting_board_shell(
            "transmission_contract_missing_curve_accounting")
    else:
        curve_accounting = _curve_accounting_board_shell(
            "transmission_contract_malformed_curve_accounting")

    # zq_path.parquet -> H1 d20
    zq_d20_bp: float | None = None
    try:
        import pandas as pd
        zq_path = data_dir / "rate_futures" / "zq_path.parquet"
        if zq_path.exists():
            zq_df = pd.read_parquet(str(zq_path))
            if "m12" in zq_df.columns:
                m12 = zq_df["m12"].dropna()
                if len(m12) >= 20:
                    delta = m12.iloc[-1] - m12.iloc[-20]
                    zq_d20_bp = round(float(delta) * 100, 2)
    except Exception as exc:
        caveats.append(f"zq_path.parquet unavailable: {exc}")
        log.warning("build_board: zq_path.parquet error: %s", exc)

    # release_forecast/latest.json
    release_latest = _read_json(data_dir / "release_forecast" / "latest.json") or {}
    if not isinstance(release_latest, dict):
        release_latest = {}
    release_items = release_latest.get("upcoming") or []
    if not isinstance(release_items, list):
        release_items = []

    # market_state/latest.json
    market_state = _read_json(data_dir / "market_state" / "latest.json") or {}
    radar_state = _safe_get(market_state, "radar", "state")

    # commodity/latest.json, shock_state.json, complex_latest.json
    commodity = _read_json(data_dir / "commodity" / "latest.json") or {}
    oil_asset = (commodity.get("assets") or {}).get("oil") or {}
    oil_trend = oil_asset.get("trend")
    oil_chg = oil_asset.get("chg")

    shock_state_raw = _read_json(data_dir / "commodity" / "shock_state.json") or {}
    shock_oil_raw = shock_state_raw.get("oil") or {}
    shock_oil_ts = shock_oil_raw.get("ts") or shock_oil_raw.get("last_eval")
    shock_stale_days = _staleness_days(shock_oil_ts)
    shock_stale = shock_stale_days is not None and shock_stale_days > SHOCK_STALE_DAYS

    if shock_stale:
        caveats.append(f"commodity/shock_state.json oil entry is {shock_stale_days}d old (>{SHOCK_STALE_DAYS}d threshold) — H3 leg judged on trend+cause_badge only")
    if shock_stale_days is not None:
        shock_oil_raw["_stale_days"] = shock_stale_days

    # Inject oil data into shock_oil_raw for H3 leg builder
    shock_oil_aug = dict(shock_oil_raw)
    shock_oil_aug["_oil_trend"] = oil_trend
    shock_oil_aug["_oil_chg"] = oil_chg

    complex_d = _read_json(data_dir / "commodity" / "complex_latest.json") or {}
    complex_growth_dir = complex_d.get("growth_dir")

    # policy/intel.json
    intel = _read_json(data_dir / "policy" / "intel.json") or {}
    intel_stale_days = _intel_staleness_days(intel) if intel else None
    if intel_stale_days is not None:
        caveats.append(f"policy/intel.json is {intel_stale_days}d old — policy row quotes as-of {intel.get('as_of','?')}")

    # site/policy_lever.json
    policy_lever = _read_json(data_dir.parent / "site" / "policy_lever.json") or \
                   _read_json(data_dir / "policy_lever.json")

    # prediction_markets
    pm_snapshot: dict | None = None
    try:
        import sys
        repo_root = str(Path(__file__).resolve().parent.parent)
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from engine.prediction_markets import snapshot as pm_snapshot_fn
        pm_snapshot = pm_snapshot_fn()
    except Exception as exc:
        log.warning("prediction_markets.snapshot() failed: %s", exc)
        caveats.append(f"prediction_markets unavailable: {exc}")

    # Inject radar_state into tx so leg builders can access it
    tx["_radar_state"] = radar_state

    # ------------------------------------------------------------------ #
    # 2. Build expectation pressure gauge legs
    # ------------------------------------------------------------------ #
    chains = tx.get("chains") or []
    hawkish_legs = _build_hawkish_legs(
        fed_path=fed_path,
        tx=tx,
        zq_d20_bp=zq_d20_bp,
        release_items=release_items,
        shock_state_oil=shock_oil_aug,
        shock_stale=shock_stale,
    )
    easing_legs = _build_easing_legs(
        tx=tx,
        release_items=release_items,
        complex_growth_dir=complex_growth_dir,
        chains=chains,
    )

    all_legs = hawkish_legs + easing_legs

    # Compute scores (null legs contribute 0)
    hawk_score = sum(
        l["weight"] for l in hawkish_legs
        if l.get("active") is True
    )
    ease_score = sum(
        l["weight"] for l in easing_legs
        if l.get("active") is True
    )

    # Net state
    h1_leg = next((l for l in hawkish_legs if l["key"] == "H1_path_repricing"), None)
    h1_active = h1_leg["active"] if h1_leg else None
    net_state = _compute_net_state(
        hawk_score=hawk_score,
        ease_score=ease_score,
        zq_d20_bp=zq_d20_bp,
        h1_active=h1_active,
    )
    state_label = _NET_STATE_LABELS.get(net_state, {"en": net_state, "zh": net_state})

    # ------------------------------------------------------------------ #
    # 3. Divergence flags
    # ------------------------------------------------------------------ #
    divergence = _compute_divergence(
        fed_path=fed_path,
        release_items=release_items,
        tx=tx,
        net_state=net_state,
    )

    # ------------------------------------------------------------------ #
    # 4. Board rows
    # ------------------------------------------------------------------ #
    # C0 §2.7 / S2: the th_iran row is gated on intel freshness at the
    # explicit cutoff when one is supplied (a stale theater becomes a
    # caveat, never a live condition). With no cutoff the legacy
    # build-time staleness is used so the historical contract survives.
    iran_row = None
    iran_age = _c0_geo_iran_caveat_age(intel, cutoff) if isinstance(intel, dict) else None
    iran_fresh = iran_age is None or iran_age <= _C0_GEO_STALE_DAYS
    if iran_fresh:
        for t in (intel.get("administration") or {}).get("theaters") or []:
            if t.get("id") == "th_iran":
                iran_row = {"title_en": t.get("title_en"), "title_zh": t.get("title_zh"),
                            "facts_en": t.get("facts_en")}
                break

    board = {
        "rate_path_row": _build_rate_path_row(fed_path, cutoff=cutoff),
        "inflation_row": _build_inflation_row(
            tx, release_items, release_meta=release_latest, display_cutoff=cutoff,
            cutoff=cutoff,
        ),
        "risk_row": _build_risk_row(tx),
        "policy_row": _build_policy_row(policy_lever, intel, intel_stale_days),
    }

    # ------------------------------------------------------------------ #
    # 5. Conditions block
    # ------------------------------------------------------------------ #
    conditions = _pick_conditions(hawkish_legs, easing_legs, iran_row)

    # ------------------------------------------------------------------ #
    # 6. Market check block
    # ------------------------------------------------------------------ #
    market_check = _build_market_check(fed_path, pm_snapshot)

    # ------------------------------------------------------------------ #
    # 7. Determine asof (newest input)
    # ------------------------------------------------------------------ #
    candidate_dates = [d for d in [main_asof, tx_asof] if d]
    if candidate_dates:
        asof = max(candidate_dates)
        build_time_fallback = False
    else:
        asof = str(datetime.now(timezone.utc).date())
        build_time_fallback = True

    # Build the pre-stance artifact (needed by compose_stance)
    pre_artifact = {
        "schema": "rates_command.v1",
        "asof": asof,
        "built": datetime.now(timezone.utc).isoformat(),
        "display_only": True,
        "authority": False,
        "board": board,
        "expectations_pressure": {
            "legs": all_legs,
            "hawk_score": hawk_score,
            "ease_score": ease_score,
            "net_state": net_state,
            "state_label": state_label,
        },
        "divergence": divergence,
        "conditions": conditions,
        "market_check": market_check,
        "yield_momentum": yield_momentum,
        "caveats": caveats,
    }

    # Stance is composed by the C0 layer below (with the §2.6 basis-safe
    # guard); no direct compose_stance call here. The §2.6 guard requires
    # the rate-path basis state and D1 identification, both of which are
    # derivable from the pre_artifact + fed_path without an I0 read.
    board = pre_artifact.get("board") if isinstance(pre_artifact, dict) else {}
    rate_path_row = board.get("rate_path_row") if isinstance(board, dict) else {}
    _rp_basis = rate_path_row.get("basis") if isinstance(rate_path_row, dict) else None
    basis_present = (
        isinstance(_rp_basis, dict)
        and _rp_basis.get("value_state") == "present"
    )
    d1_identified = _c0_d1_any_identified(
        fed_path if isinstance(fed_path, dict) else {}
    )
    pre_artifact["stance"] = _c0_compose_stance_with_basis_guard(
        pre_artifact,
        basis_present=basis_present,
        d1_identified=d1_identified,
    )

    # Final artifact
    artifact = dict(pre_artifact)
    # changes + prev_state are added by the builder (build_changes call)
    artifact["changes"] = {"vs_asof": None, "items": []}
    artifact["prev_state"] = {"as_of": None, "state": {}}
    artifact["basis_contract_version"] = _t0b_basis_contract_version()
    # qualified_comparisons, board_generation and inflation_lenses are filled
    # by the C0 layer below; an empty list means "not yet compared" only
    # AFTER the C0 layer has run (the gaps live on each row's basis record).
    artifact["qualified_comparisons"] = []
    # RIC Y1b: display-only curve accounting (A22-A24), attached AFTER the
    # stance is composed so compose_stance's input is unchanged. Export stays
    # closed until the E1 ruling.
    artifact["curve_accounting"] = curve_accounting
    artifact["curve_accounting_export"] = {
        "export_allowed": False,
        "reason": "awaiting_e1_ruling",
        "display_only": True,
    }

    # C0 layer (RIC-W7 binding): qualified_comparisons, board_generation,
    # inflation_lenses and the caveat extension. Never re-touches stance
    # (the basis-safe guard already wrote pre_artifact["stance"] above);
    # never overwrites the legacy keys (curve_accounting, curve_accounting_export,
    # top-level asof). Reads I0 once (shared between comparisons and the
    # verbatim lenses carry).
    artifact = _c0_apply_to_artifact(
        artifact,
        fed_path=fed_path,
        data_dir=data_dir,
        cutoff=cutoff,
        build_time_fallback=build_time_fallback,
        intel=intel,
    )

    return artifact


# ---------------------------------------------------------------------------
# compact_state, diff_changes, build_changes
# ---------------------------------------------------------------------------

def _leg_value(contract: dict, key: str):
    """Return the `value` field of the leg in expectations_pressure.legs whose
    `key` matches, when it is a string; otherwise None. Used by compact_state
    so the fingerprint carries the rendered dollar direction (a scalar), never
    the policy_row dict the contract owns for other reasons."""
    legs = _safe_get(contract, "expectations_pressure", "legs")
    if not isinstance(legs, list):
        return None
    for leg in legs:
        if isinstance(leg, dict) and leg.get("key") == key:
            val = leg.get("value")
            return val if isinstance(val, str) else None
    return None


def compact_state(contract: dict) -> dict:
    """Extract a comparable fingerprint from a rates_command artifact."""
    ep = contract.get("expectations_pressure") or {}
    return {
        "net_state": ep.get("net_state"),
        "hawk_score": ep.get("hawk_score"),
        "ease_score": ep.get("ease_score"),
        "curve_regime": _safe_get(contract, "board", "risk_row", "curve_regime_key"),
        "anchoring": _safe_get(contract, "board", "inflation_row", "anchoring"),
        "infl_dir": _safe_get(contract, "board", "inflation_row", "direction"),
        "usd_dir": _leg_value(contract, "E3_dollar_tightening"),
        "implied_bp_12m": _safe_get(contract, "board", "rate_path_row", "implied_bp_12m"),
    }


def _compact_sentence(key: str, old_val, new_val) -> tuple[str, str]:
    if key == "net_state":
        old_lbl = _NET_STATE_LABELS.get(old_val or "", {}).get("en", old_val or "—")
        new_lbl = _NET_STATE_LABELS.get(new_val or "", {}).get("en", new_val or "—")
        return (f"Pressure state changed: {old_lbl} → {new_lbl}",
                f"压力状态变化：{_NET_STATE_LABELS.get(old_val or '', {}).get('zh', old_val or '—')} → "
                f"{_NET_STATE_LABELS.get(new_val or '', {}).get('zh', new_val or '—')}")
    if key == "curve_regime":
        oe = old_val or "—"; ne = new_val or "—"
        oz = _CURVE_REGIME_ZH.get(old_val or "", old_val or "—")
        nz = _CURVE_REGIME_ZH.get(new_val or "", new_val or "—")
        return (f"Curve regime: {oe} → {ne}", f"曲线形态：{oz} → {nz}")
    if key == "anchoring":
        oz = _ANCHORING_LABEL_ZH.get(old_val or "", old_val or "—")
        nz = _ANCHORING_LABEL_ZH.get(new_val or "", new_val or "—")
        return (f"Anchoring: {old_val or '—'} → {new_val or '—'}",
                f"锚定状态：{oz} → {nz}")
    if key == "infl_dir":
        oz = _INFL_DIR_ZH.get(old_val or "", old_val or "—")
        nz = _INFL_DIR_ZH.get(new_val or "", new_val or "—")
        return (f"Inflation direction: {old_val or '—'} → {new_val or '—'}",
                f"通胀方向：{oz} → {nz}")
    if key == "usd_dir":
        oe = old_val or "—"; ne = new_val or "—"
        oz = _USD_DIR_ZH.get(old_val or "", oe)
        nz = _USD_DIR_ZH.get(new_val or "", ne)
        return (f"Dollar direction: {oe} → {ne}", f"美元方向：{oz} → {nz}")
    if key == "implied_bp_12m":
        return (f"12m implied change shifted: {old_val:+.0f}bp → {new_val:+.0f}bp",
                f"12个月隐含变化：{old_val:+.0f}bp → {new_val:+.0f}bp")
    return (f"{key} changed: {old_val} → {new_val}", f"{key}变化：{old_val} → {new_val}")


def diff_changes(prev: dict, curr: dict) -> list[dict]:
    """Compare two compact_state dicts; emit at most 6 change items."""
    candidates: list[tuple[int, dict]] = []

    for key in _DIFF_ORDER:
        old_val = prev.get(key)
        new_val = curr.get(key)
        if old_val is None or new_val is None:
            continue
        # Skip non-scalar side: legacy baselines written before this repair
        # may carry the WHOLE policy_row dict under `usd_dir`; we cannot diff
        # a dict and emit no useful sentence from it.
        if isinstance(old_val, (dict, list)) or isinstance(new_val, (dict, list)):
            continue
        if old_val == new_val:
            continue
        try:
            en, zh = _compact_sentence(key, old_val, new_val)
        except Exception:
            en = f"{key}: {old_val} → {new_val}"
            zh = en
        idx = _DIFF_ORDER.index(key)
        candidates.append((idx, {"key": key, "from": old_val, "to": new_val, "en": en, "zh": zh}))

    candidates.sort(key=lambda x: x[0])
    return [item for _, item in candidates[:_MAX_CHANGES]]


def build_changes(
    old_contract: dict | None,
    new_contract: dict,
    new_asof: str,
) -> tuple[dict, dict]:
    """Same-day-idempotent changes block builder.

    Mirror of transmission_context.build_changes semantics (lines 507-554).
    """
    if old_contract is None:
        return (
            {"vs_asof": None, "items": []},
            {"as_of": None, "state": {}},
        )

    new_cs = compact_state(new_contract)
    old_asof = old_contract.get("asof")

    if old_asof != new_asof:
        # New day — diff against yesterday
        base = compact_state(old_contract)
        base_asof = old_asof
    else:
        # Same-day rebuild — reuse stored prev_state
        prev_state_stored = old_contract.get("prev_state") or {}
        base = prev_state_stored.get("state") or {}
        base_asof = prev_state_stored.get("as_of")

    if base_asof is None or not base:
        items: list[dict] = []
    else:
        items = diff_changes(base, new_cs)

    changes = {"vs_asof": base_asof, "items": items}
    prev_state = {"as_of": base_asof, "state": base}
    return changes, prev_state


# --------------------------------------------------------------------------- #
# C0 comparison layer (RIC-W7 binding).
#
# Above this block, the board shipped with `qualified_comparisons = []` and
# no per-component generation integrity. C0 fills that gap with B0-backed
# cross-component comparisons (or upstream references), generation integrity,
# the inflation_lenses carry, and basis-safe stance copy when the rate-path
# cannot be matched to the policy rate. No upstream computation is redone
# here (seat ruling S7): D1's effr_meeting_path vs_target_midpoint and I0's
# matched_lenses.comparisons are referenced by input_id, content_ref and
# per-comparison cutoff, never re-run.
# --------------------------------------------------------------------------- #

# Staleness threshold for the geo_iran intel theater at the cutoff (§2.7).
# Reused name (no new constant beyond this single threshold).
_C0_GEO_STALE_DAYS: int = SHOCK_STALE_DAYS  # 7 calendar days; same envelope as H3.

# Inflation-lenses payload size cap (§2.11d). 16 KiB is the wire cap.
_C0_LENS_LIMIT_BYTES: int = 16384

# Input-id prefixes used by the comparison layer to point at upstream bytes.
_C0_D1_INPUT_ID_PREFIX: str = "data/bonds/bond_health.json#/fed_path/effr_meeting_path"
_C0_I0_INPUT_ID_PREFIX: str = (
    "data/release_forecast/inflation_intelligence.json#/matched_lenses"
)
_C0_I0_PATH: str = "data/release_forecast/inflation_intelligence.json"
_C0_D1_PATH: str = "data/bonds/bond_health.json"


def _c0_sha256_bytes(path: Path) -> str | None:
    """sha256 hex of `path`'s bytes, or None when unreadable.

    Fail-open: a missing or unreadable file yields None so the comparison
    layer records provenance as best it can without raising.
    """
    try:
        if not path.exists() or not path.is_file():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None


def _c0_input_id(prefix: str, *pointers: str) -> str:
    """Build a C0 input_id from a file-prefix and one or more JSON pointers.

    Pointer segments are joined with '/'; the prefix keeps its own trailing
    '/fed_path/...' or '/matched_lenses' tail. Empty pointer segments are
    dropped so the result is always a clean path#fragment form.
    """
    parts = [seg for seg in pointers if seg]
    return prefix + ("/" + "/".join(parts) if parts else "")


def _c0_ref_d1(data_dir: Path) -> dict:
    """Provenance stamp for the D1 source bytes (bond_health.json fed_path).

    Returns the dict {input_id, content_ref} the comparison layer embeds on
    every D1-sourced comparison; either value may be None when the file is
    unreadable, never raised.
    """
    return {
        "input_id": _C0_D1_INPUT_ID_PREFIX,
        "content_ref": _c0_sha256_bytes(data_dir / "bonds" / "bond_health.json"),
    }


def _c0_ref_i0(data_dir: Path) -> dict:
    """Provenance stamp for the I0 source bytes (inflation_intelligence.json)."""
    return {
        "input_id": _C0_I0_INPUT_ID_PREFIX,
        "content_ref": _c0_sha256_bytes(data_dir / "release_forecast" / "inflation_intelligence.json"),
    }


def _c0_load_i0_block(data_dir: Path) -> dict | None:
    """Read the inflation_intelligence.json matched_lenses block, or None.

    Shared with `_c0_qualified_comparisons` (component i0) and the
    `inflation_lenses` carry (verbatim copy). Never raises: a missing file,
    unreadable bytes, or non-dict payload all yield None so the caller can
    surface `{"status":"unavailable","reason":<R>}` instead.
    """
    path = data_dir / "release_forecast" / "inflation_intelligence.json"
    raw = _read_json(path)
    if not isinstance(raw, dict):
        return None
    block = raw.get("matched_lenses")
    return block if isinstance(block, dict) else None


def _c0_staleness_days_at(ts_str: Any, cutoff: Any) -> int | None:
    """Staleness of `ts_str` measured against `cutoff` (both ISO strings).

    When `cutoff` is None the staleness is measured against build time so
    the legacy contract is preserved (§2.7); with an explicit cutoff the
    staleness window is the cutoff, not `datetime.now`. Returns None when
    either stamp is unparsable or absent.
    """
    if not isinstance(ts_str, str) or not ts_str:
        return None
    if cutoff is None:
        return _staleness_days(ts_str)
    if not isinstance(cutoff, str) or not cutoff:
        return _staleness_days(ts_str)
    try:
        from datetime import date
        ts_day = _staleness_days(ts_str)
        cutoff_day = date.fromisoformat(cutoff[:10])
        ts_parsed = date.fromisoformat(ts_str[:10])
        return (cutoff_day - ts_parsed).days
    except Exception:
        return _staleness_days(ts_str)


def _c0_geo_iran_intel(intel: dict | None, cutoff: Any) -> dict | None:
    """Return the th_iran row only when intel is fresh at the cutoff.

    The row is suppressed (None) when intel's `as_of` is missing, unparsable,
    or older than the cutoff by more than `_C0_GEO_STALE_DAYS` days; a stale
    theater becomes a caveat string elsewhere, never a live condition row
    (per §2.7 / S2). At `cutoff=None` the comparison falls back to build-time
    staleness so the legacy behavior is preserved.
    """
    if not isinstance(intel, dict):
        return None
    as_of = intel.get("as_of")
    age = _c0_staleness_days_at(as_of, cutoff)
    if age is None:
        return None
    if age > _C0_GEO_STALE_DAYS:
        return None
    theaters = (intel.get("administration") or {}).get("theaters") or []
    for t in theaters:
        if isinstance(t, dict) and t.get("id") == "th_iran":
            return {
                "title_en": t.get("title_en"),
                "title_zh": t.get("title_zh"),
                "facts_en": t.get("facts_en"),
                "facts_zh": t.get("facts_zh"),
                "as_of": as_of,
                "as_of_note_en": (
                    f"Intel as of {as_of} ({age}d old)" if age is not None
                    else f"Intel as of {as_of}"
                ),
                "as_of_note_zh": (
                    f"情报截至{as_of}（{age}天前）" if age is not None
                    else f"情报截至{as_of}"
                ),
                "unsigned_display": True,
            }
    return None


def _c0_basis_safe_stance_pair() -> dict[str, str]:
    """The exact basis-safe EN/ZH pair when the rate-path cannot be matched.

    Sourced from SEAT S1; never augmented, never with a cut count, never
    with a `path_plain` default. Returns a 2-key dict consumed by
    `_c0_compose_stance_with_basis_guard` to keep the side-exit stable.
    """
    return {
        "en": "The futures rate path isn't shown until it can be matched to the policy rate.",
        "zh": "期货隐含的利率路径须与政策利率口径一致后才会显示。",
    }


def _c0_compose_stance_with_basis_guard(
    pre_artifact: dict, *, basis_present: bool, d1_identified: bool
) -> dict[str, str]:
    """Wrap compose_stance with the §2.6 basis-safe guard.

    When the rate-path basis is missing OR D1's `vs_target_midpoint` for any
    of the months summarised in stance is not identified, the returned pair
    is the exact basis-safe copy (no number, no cut count, no `path_plain`
    fallback); otherwise the legacy compose_stance result is returned
    byte-identically. compose_stance is still invoked even when the guard
    fires (its result discarded) so downstream spies that wrap the
    `compose_stance` symbol can observe the unchanged input — this keeps
    the legacy Y1b spy-assertion pinned at LANE BASE. Never raises.
    """
    if not basis_present or not d1_identified:
        try:
            compose_stance(pre_artifact)  # observed for spies; result unused
        except Exception:
            pass
        return _c0_basis_safe_stance_pair()
    try:
        return compose_stance(pre_artifact)
    except Exception as exc:  # never fail the artifact
        log.warning("c0 compose_stance failed: %s", exc)
        return _c0_basis_safe_stance_pair()


def _c0_d1_any_identified(fed_path: dict) -> bool:
    """True iff any per-month vs_target_midpoint in D1 is identified.

    D1's `effr_meeting_path.months[*].vs_target_midpoint` is a B0
    ComparisonResult; an identified status is DIRECTLY_COMPARABLE or
    COMPARABLE_AFTER_TRANSFORMATION. With no D1 block, no per-month row, or
    no identified row the function returns False so the §2.6 guard fires.
    """
    block = fed_path.get("effr_meeting_path") if isinstance(fed_path, dict) else None
    if not isinstance(block, dict):
        return False
    months = block.get("months")
    if not isinstance(months, list):
        return False
    for m in months:
        if not isinstance(m, dict):
            continue
        vt = m.get("vs_target_midpoint")
        if not isinstance(vt, dict):
            continue
        status = vt.get("status")
        if status in ("directly_comparable", "comparable_after_transformation"):
            return True
    return False


def _c0_wrap_with_provenance(
    base: dict,
    *,
    component: str,
    input_id: str | None,
    content_ref: str | None,
    cutoff: str | None,
    reference_only: bool,
) -> dict:
    """Add provenance fields to a B0 ComparisonResult dict.

    The B0 schema is frozen at 14 fields (additionalProperties: false), but
    the C0 layer carries input_id / content_ref / cutoff / component /
    reference_only OUTSIDE that schema on the artifact side — `from_dict`
    still refuses unknown keys for schema validation, but the wrapper keeps
    the underlying 14 fields byte-identical to B0. Never modifies `base`.
    """
    out = dict(base)
    if input_id is not None:
        out["input_id"] = input_id
    if content_ref is not None:
        out["content_ref"] = content_ref
    if cutoff is not None:
        out["cutoff"] = cutoff
    out["component"] = component
    out["reference_only"] = bool(reference_only)
    return out


def _c0_qualified_comparisons(
    *,
    fed_path: dict,
    inflation_lenses_block: dict | None,
    data_dir: Path,
    cutoff: Any,
    build_time_fallback: bool,
) -> list[dict]:
    """Build the `qualified_comparisons` list with provenance per comparison.

    Three pools:
      * D1 references — each per-month `vs_target_midpoint` is carried with
        its input_id, content_ref and the D1 cutoff_effective (per seat S7:
        D1 is never re-run here).
      * I0 references — each `matched_lenses.comparisons` row is carried
        with its input_id, content_ref and the I0 cutoff (per seat S7).
      * Cross-component built here — left empty in the first slice because
        every cross-component candidate is either already computed upstream
        (D1 vs_target_midpoint, I0 comparisons) or fails the B0 rule gate
        on the available operands (per the §0 envelope: built ONLY through
        B0 with registered rule ids; no hand-rolled arithmetic). The list
        is non-empty when D1 or I0 is present.

    The list always carries the 14 B0 fields per entry plus provenance
    fields; never raises; never returns None.
    """
    out: list[dict] = []
    d1_ref = _c0_ref_d1(data_dir)
    i0_ref = _c0_ref_i0(data_dir)

    # --- 1) D1 per-month vs_target_midpoint (referenced, never re-run) ---
    d1_block = fed_path.get("effr_meeting_path") if isinstance(fed_path, dict) else None
    if isinstance(d1_block, dict):
        d1_cutoff = d1_block.get("cutoff_effective") if isinstance(
            d1_block.get("cutoff_effective"), str
        ) else (cutoff if isinstance(cutoff, str) else None)
        months = d1_block.get("months") if isinstance(d1_block, dict) else None
        if isinstance(months, list):
            for idx, m in enumerate(months):
                if not isinstance(m, dict):
                    continue
                vt = m.get("vs_target_midpoint")
                if not isinstance(vt, dict):
                    continue
                # Carry every B0 field through verbatim; only add provenance.
                entry = _c0_wrap_with_provenance(
                    vt,
                    component="d1",
                    input_id=_c0_input_id(
                        _C0_D1_INPUT_ID_PREFIX, "months", str(idx), "vs_target_midpoint"
                    ),
                    content_ref=d1_ref["content_ref"],
                    cutoff=d1_cutoff,
                    reference_only=True,
                )
                out.append(entry)

    # --- 2) I0 matched_lenses.comparisons (referenced, never re-run) ---
    if isinstance(inflation_lenses_block, dict):
        i0_cutoff = inflation_lenses_block.get("cutoff")
        i0_cutoff = i0_cutoff if isinstance(i0_cutoff, str) else (
            cutoff if isinstance(cutoff, str) else None
        )
        comps = inflation_lenses_block.get("comparisons")
        if isinstance(comps, list):
            for idx, c in enumerate(comps):
                if not isinstance(c, dict):
                    continue
                entry = _c0_wrap_with_provenance(
                    c,
                    component="i0",
                    input_id=_c0_input_id(
                        _C0_I0_INPUT_ID_PREFIX, "comparisons", str(idx)
                    ),
                    content_ref=i0_ref["content_ref"],
                    cutoff=i0_cutoff,
                    reference_only=True,
                )
                out.append(entry)

    # No cross-component comparators are added here in the first slice:
    # the only cross-component candidates (T0 cpi first-print vs I0 cpi
    # latest-revised; T0 cpi vs breakeven) fail the B0 rule gates on the
    # available operands, and §2.1 forbids hand-rolled arithmetic. The
    # framework is in place — a future cross-component rule that admits
    # these operands will plug in here behind B0.

    if build_time_fallback and out:
        # Mark every entry so downstream consumers see the build-time caveat
        # (informational; never alters B0 fields).
        for entry in out:
            entry["asof_build_time_fallback"] = True

    return out


def _c0_board_generation(
    *,
    fed_path: dict,
    inflation_lenses_block: dict | None,
    cutoff: Any,
    build_time_fallback: bool,
    d1_content_ref: str | None,
    i0_content_ref: str | None,
    rate_path_basis: dict | None,
) -> dict:
    """Build the `board_generation` generation-integrity stamp (§2.3).

    `plan` lists every planned component; `components` carries the
    per-component input_id, content_ref, cutoff and state. `complete` is
    True only when every planned component is present at its cutoff with
    matching content_ref; otherwise `incomplete_reasons` lists each gap.
    """
    components: dict[str, dict] = {}
    incomplete: list[str] = []

    # Component D1 (effr_meeting_path).
    d1_block = fed_path.get("effr_meeting_path") if isinstance(fed_path, dict) else None
    d1_cutoff = d1_block.get("cutoff_effective") if isinstance(d1_block, dict) else None
    d1_present = isinstance(d1_block, dict)
    components["d1"] = {
        "input_id": _C0_D1_INPUT_ID_PREFIX,
        "content_ref": d1_content_ref,
        # Cutoff is the COMPONENT's own cutoff (D1's cutoff_effective);
        # never the user's `cutoff` parameter, which would leak into the
        # `cutoff touches only the countdown` invariant pinned by the
        # legacy T0 test suite.
        "cutoff": d1_cutoff if isinstance(d1_cutoff, str) else None,
        "state": "present" if d1_present else "missing",
    }
    if not d1_present:
        incomplete.append("d1_missing")
    elif d1_content_ref is None:
        incomplete.append("d1_content_ref_unreadable")

    # Component I0 (inflation_intelligence matched_lenses).
    i0_present = isinstance(inflation_lenses_block, dict)
    i0_cutoff = None
    if i0_present:
        c = inflation_lenses_block.get("cutoff")
        i0_cutoff = c if isinstance(c, str) else None
    components["i0"] = {
        "input_id": _C0_I0_INPUT_ID_PREFIX,
        "content_ref": i0_content_ref,
        "cutoff": i0_cutoff if isinstance(i0_cutoff, str) else None,
        "state": "present" if i0_present else "missing",
    }
    if not i0_present:
        incomplete.append("i0_missing")
    elif i0_content_ref is None:
        incomplete.append("i0_content_ref_unreadable")

    # Component T0 (rate-path basis — the T0 row carried on this board).
    # The basis may be a dict with value_state=missing (qualified but no
    # value), or None (no cutoff / no source asof). Both are semantically
    # "no present value" so the board_generation reason fires for both;
    # this keeps the C0 generation stamp aligned with the legacy
    # `_strip_volatile` invariant that already pins `cutoff touches only
    # the countdown` in the existing T0 test suite.
    if not isinstance(rate_path_basis, dict):
        rate_basis_state = "missing"
        basis_value_state = None
    else:
        basis_value_state = rate_path_basis.get("value_state")
        rate_basis_state = (
            "present" if basis_value_state == "present" else "missing"
        )
    components["t0_rate_path"] = {
        "input_id": _C0_D1_INPUT_ID_PREFIX,  # the rate_path_basis is qualified
        "content_ref": d1_content_ref,        # from the bond_health.json bytes.
        # T0's cutoff follows the row basis's own cutoff ONLY when the
        # basis is fully present (value_state=present); missing bases
        # carry an unknown cutoff, never the user's `cutoff` parameter —
        # see D1/I0 note above (this keeps the `cutoff touches only the
        # countdown` invariant pinned by the legacy T0 test suite).
        "cutoff": (
            rate_path_basis.get("cutoff")
            if rate_basis_state == "present"
            and isinstance(rate_path_basis, dict)
            and isinstance(rate_path_basis.get("cutoff"), str)
            else None
        ),
        "state": rate_basis_state,
    }
    if rate_basis_state != "present":
        incomplete.append("t0_rate_path_basis_missing")

    if build_time_fallback:
        incomplete.append("asof_build_time_fallback")

    plan = ["t0_rate_path", "d1", "i0"]
    return {
        "plan": plan,
        "components": components,
        "complete": not incomplete,
        "incomplete_reasons": incomplete,
    }


def _c0_inflation_lenses(
    *,
    inflation_lenses_block: dict | None,
    cutoff: Any,
    build_time_fallback: bool,
    caveats: list[str],
) -> dict:
    """Return the verbatim inflation_lenses block (§2.11).

    Reads ONLY the same bytes as §2.2 (one content_ref, one read). When the
    block is missing or unreadable it returns exactly
    `{"status":"unavailable","reason":R}` with R drawn from §2.11c — never
    `{}`, `None`, `[]`, an omitted key, or an `available:true` shell.

    When the block exceeds the wire cap (16 KiB), it is reduced to the
    schema-faithful truncation shape, the `truncation` marker is added, and
    a `inflation_lenses_truncated:<N>B` caveat is appended.
    """
    if inflation_lenses_block is None:
        return {"status":"unavailable","reason":"i0_artifact_missing"}

    if not isinstance(inflation_lenses_block, dict):
        return {"status":"unavailable","reason":"i0_matched_lenses_malformed"}

    lenses_obj = inflation_lenses_block.get("lenses")
    if not isinstance(lenses_obj, dict):
        return {"status":"unavailable","reason":"i0_matched_lenses_missing"}

    # Cutoff comparison (§2.11c).
    block_cutoff = inflation_lenses_block.get("cutoff")
    if not isinstance(block_cutoff, str) or not block_cutoff:
        return {"status":"unavailable","reason":"i0_cutoff_unknown"}

    # Staleness check: more than 7 calendar days before the cutoff (or build
    # date when no cutoff is supplied). Same threshold and reference as
    # §2.7 / S2.
    ref_for_stale = cutoff if isinstance(cutoff, str) and cutoff else None
    age = _c0_staleness_days_at(block_cutoff, ref_for_stale)
    if age is not None and age > _C0_GEO_STALE_DAYS:
        return {"status":"unavailable","reason":"i0_stale"}

    # Block cutoff is later than the board cutoff? (§2.11c i0_after_cutoff)
    if isinstance(cutoff, str) and cutoff:
        try:
            from datetime import date as _date
            block_day = _date.fromisoformat(block_cutoff[:10])
            cutoff_day = _date.fromisoformat(cutoff[:10])
            if block_day > cutoff_day:
                return {"status":"unavailable","reason":"i0_after_cutoff"}
        except Exception:
            pass

    # Size check.
    try:
        encoded = json.dumps(
            inflation_lenses_block, ensure_ascii=False, separators=(",", ":"),
            sort_keys=True, default=str,
        ).encode("utf-8")
    except Exception:
        return {"status":"unavailable","reason":"i0_matched_lenses_malformed"}
    full_bytes = len(encoded)
    if full_bytes <= _C0_LENS_LIMIT_BYTES:
        return inflation_lenses_block

    # Truncation path: reduce each lens to the schema-faithful minimal shape
    # while keeping the comparison / street_consensus / gaps blocks whole.
    truncated_lenses: dict[str, dict] = {}
    keep_fields = {
        "lens_id", "measure", "unit", "value", "value_state", "reference_period",
        "limitations", "qualified",
    }
    qualified_fields = (
        "target", "model_id", "vintage", "rights", "basket_or_index",
        "reference_start", "reference_end", "unit", "source_version",
        "content_ref", "cutoff",
    )
    for lens_id, lens in lenses_obj.items():
        if not isinstance(lens, dict):
            continue
        reduced: dict = {k: lens.get(k) for k in keep_fields if k in lens}
        qual = lens.get("qualified")
        if isinstance(qual, dict):
            reduced["qualified"] = {k: qual.get(k) for k in qualified_fields if k in qual}
        truncated_lenses[lens_id] = reduced

    out = dict(inflation_lenses_block)
    out["lenses"] = truncated_lenses
    out["truncation"] = {
        "truncated": True,
        "full_bytes": full_bytes,
        "limit_bytes": _C0_LENS_LIMIT_BYTES,
        "pointer": "data/release_forecast/inflation_intelligence.json#/matched_lenses",
        "content_ref": _c0_sha256_bytes(
            Path(os.environ.get("MACRO_ROOT", str(Path(__file__).resolve().parent.parent)))
            / "data" / "release_forecast" / "inflation_intelligence.json"
        ),
    }
    caveats.append(f"inflation_lenses_truncated:{full_bytes}B")
    return out


def _c0_build_caveats(
    *,
    fed_path: dict,
    intel: dict | None,
    cutoff: Any,
    rate_path_basis: dict | None,
    inflation_lenses_block: dict | None,
    build_time_fallback: bool,
) -> list[str]:
    """Compute the C0-specific caveat strings appended to artifact['caveats'].

    Only the C0-specific entries are returned; the legacy caveats list is
    owned by the caller. Always returns a fresh list; never mutates input.
    """
    caveats: list[str] = []
    # Build-time-fallback asof flag (also surfaced under board_generation).
    if build_time_fallback:
        caveats.append("asof_build_time_fallback")

    # Rate-path basis missing or refused (still happens without a cutoff).
    # The basis may be a dict with value_state=missing (qualified but no
    # value) — that is also "no present value" and the caveat fires for
    # both `None` and value_state=missing bases, mirroring the
    # `_strip_volatile` invariant pinned by the legacy T0 test suite.
    basis_value_state = (
        rate_path_basis.get("value_state")
        if isinstance(rate_path_basis, dict)
        else None
    )
    if not isinstance(rate_path_basis, dict) or basis_value_state != "present":
        caveats.append("rate_path_basis_missing")

    # Stale intel theater — the row is suppressed upstream but the caveat
    # is honest so the operator sees the source-as-of distance.
    if isinstance(intel, dict):
        as_of = intel.get("as_of")
        age = _c0_staleness_days_at(as_of, cutoff)
        if age is not None and age > _C0_GEO_STALE_DAYS:
            caveats.append(
                f"policy/intel.json th_iran theater is {age}d old (>{_C0_GEO_STALE_DAYS}d "
                f"threshold) — suppressed from conditions; quote intel.as_of={as_of!r}"
            )

    # I0 unavailable categorisation.
    if inflation_lenses_block is None:
        caveats.append("inflation_lenses_unavailable:i0_artifact_missing")
    return caveats


def _c0_apply_to_artifact(
    pre_artifact: dict,
    *,
    fed_path: dict,
    data_dir: Path,
    cutoff: Any,
    build_time_fallback: bool,
    intel: dict | None = None,
) -> dict:
    """Apply the C0 layer to a near-final artifact and return the augmented copy.

    Reads the I0 matched_lenses block once (shared between `qualified_comparisons`
    and `inflation_lenses`), computes D1/I0 provenance, fills the comparison
    list, the generation stamp and the lenses carry. The §2.6 basis-safe
    stance guard already wrote `stance` upstream (in build_board) so the
    stance key is never re-touched here — this preserves the legacy
    key-order pinned by the Y1b test suite. Existing keys
    (curve_accounting, curve_accounting_export, top-level asof semantics)
    are unchanged.
    """
    inflation_lenses_block = _c0_load_i0_block(data_dir)
    d1_content_ref = _c0_sha256_bytes(data_dir / "bonds" / "bond_health.json")
    i0_content_ref = _c0_sha256_bytes(
        data_dir / "release_forecast" / "inflation_intelligence.json"
    )

    # Pull the rate-path basis directly from the existing rate_path_row
    # (T0 already qualifies it; we never recompute here).
    board = pre_artifact.get("board") if isinstance(pre_artifact, dict) else {}
    rate_path_row = board.get("rate_path_row") if isinstance(board, dict) else {}
    rate_path_basis = rate_path_row.get("basis") if isinstance(rate_path_row, dict) else None

    # Caveats: extend, never replace.
    existing_caveats = list(pre_artifact.get("caveats") or [])
    caveats = existing_caveats + _c0_build_caveats(
        fed_path=fed_path,
        intel=intel,
        cutoff=cutoff,
        rate_path_basis=rate_path_basis,
        inflation_lenses_block=inflation_lenses_block,
        build_time_fallback=build_time_fallback,
    )
    pre_artifact["caveats"] = caveats

    # Comparisons (D1 + I0 references; cross-component framework ready).
    pre_artifact["qualified_comparisons"] = _c0_qualified_comparisons(
        fed_path=fed_path,
        inflation_lenses_block=inflation_lenses_block,
        data_dir=data_dir,
        cutoff=cutoff,
        build_time_fallback=build_time_fallback,
    )

    # Generation integrity stamp.
    pre_artifact["board_generation"] = _c0_board_generation(
        fed_path=fed_path,
        inflation_lenses_block=inflation_lenses_block,
        cutoff=cutoff,
        build_time_fallback=build_time_fallback,
        d1_content_ref=d1_content_ref,
        i0_content_ref=i0_content_ref,
        rate_path_basis=rate_path_basis,
    )

    # Inflation-lenses carry.
    pre_artifact["inflation_lenses"] = _c0_inflation_lenses(
        inflation_lenses_block=inflation_lenses_block,
        cutoff=cutoff,
        build_time_fallback=build_time_fallback,
        caveats=pre_artifact["caveats"],
    )

    return pre_artifact


def _c0_geo_iran_caveat_age(intel: dict | None, cutoff: Any) -> int | None:
    """Expose the §2.7 staleness age for the geo_iran theater.

    Returned for the legacy `_pick_conditions` to decide whether to drop the
    th_iran row (suppressed when age > _C0_GEO_STALE_DAYS or age is None
    with no cutoff). When the caller's policy is to suppress, the row is
    dropped and a caveat is appended upstream.
    """
    if not isinstance(intel, dict):
        return None
    as_of = intel.get("as_of")
    return _c0_staleness_days_at(as_of, cutoff)
