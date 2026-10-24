"""Deterministic, source-labelled Options Pulse PROJECTOR (display tier only).

A PURE projection of ALREADY-PUBLISHED options artifacts into one reviewable
card for the Macro lens of the AI Daily Brief. It is NOT a source, NOT a scorer
and NOT a new model: every number it shows is copied, re-bounded or
cross-checked from bytes some incumbent owner already published.

INPUT OWNERS (this module reads none of them itself — the caller materialises
them and passes them in):
  * ``site/gex/<KEY>.json``          — ``scripts/build_gex_board.py`` via ``engine/gex_model``
  * ``site/options_intel_brief.json``— the options intel-brief owner
  * ``data/options_flow/signing_gate.json`` — the options-flow signing gate

DETERMINISM LAW. This module performs NO network IO, NO file IO, NO LLM call, NO
randomness and NO wall-clock read. ``now`` and ``reference_session`` are supplied
by the caller; the calendar arithmetic they feed (``lib.nyse_calendar``) is a pure
function of those arguments. Same inputs -> byte-identical output.

HONEST FRAMING (carried from ``engine/gex_engine`` / ``engine/gex_model``, whose
LIMITATIONS this card inherits verbatim):
  * The dealer long-call / short-put SIGN is an UNOBSERVABLE ASSUMPTION. Every
    gamma sign here is assumption-basis, not observed.
  * The published feed is delayed / end-of-day, so this card is a DATED, DELAYED
    context surface — never "live".
  * Magnet / wall / flip strikes are LEVELS where hedging CONCENTRATES. They are
    never a floor, cap, or target.
  * The GEX curve is an ESTIMATED dealer-gamma EXPOSURE profile re-priced as a
    function of spot. It is NOT a closing-price density.

WHAT IS DELIBERATELY UNAVAILABLE (never synthesised, never proxied):
  * Real-world up/down CLOSING PROBABILITIES. ``engine/options_rn_tail_density``,
    ``engine/options_arbfree_surface`` and ``engine/options_american_exercise``
    stand at RESEARCH_ONLY / INSUFFICIENT_DATA; their verdicts are imported here
    neither as numbers nor as prose.
  * Signed flow and "bullish expiry" percentages while
    ``signing_gate.direction_reliable`` is false.
NO trade, rank, size, score or alert authority is granted by this card.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any

from lib import nyse_calendar

# ── identity ────────────────────────────────────────────────────────────────
PULSE_SCHEMA = "options.pulse/v1"
PROJECTOR_VERSION = "options-pulse-projector/1.0.0"

# ── input bounds (a card is not a data lake) ────────────────────────────────
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_PROFILE_POINTS = 401
MAX_WALL_ROWS = 200
# Chart geometry. The viewBox aspect must stay in a sane band (see CHART_ASPECT):
# the card is a wide strip, so an extreme ratio renders thousands of pixels tall.
MAX_PROFILE_XL = 800.0
MAX_PROFILE_XH = 200.0
CHART_ASPECT = (2.0, 8.0)
MAX_TABLE_ROWS = 12

# ── authority: this card is display-only, permanently ───────────────────────
AUTHORITY_FLAGS: dict[str, bool] = {
    "display_only": True,
    "may_recommend_trade": False,
    "may_rank": False,
    "may_size": False,
    "may_alert": False,
    "may_score": False,
}

# The incantation shown wherever a probability would have gone.
PROBABILITY_WITHHELD = (
    "Real-world closing probability is unavailable here: the admitted probability "
    "engines stand at RESEARCH_ONLY / INSUFFICIENT_DATA. What is shown instead is "
    "gamma context — the estimated dealer-gamma profile and the levels where "
    "hedging concentrates."
)

FLOW_WITHHELD = (
    "Signed flow and bullish-expiry percentages are unavailable while the flow "
    "signing gate reports direction_reliable = false. No numeric bullish proxy is "
    "substituted, and a missing or stale brief is never read as zero activity."
)


class PulseInputError(ValueError):
    """Programmer error: the projector was called with an unusable contract.

    Distinct from a DATA problem, which degrades to an ``available: False`` card.
    """


# ── small numeric guards ────────────────────────────────────────────────────
def _num(value: Any) -> float | None:
    """Return a finite float, or None.

    Rejects bool (a bool is never a measurement), non-numeric types, and
    non-finite values. Missing is NOT zero: None stays None all the way to the
    card, which then renders an explicit unavailable state.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return f if f == f and f not in (float("inf"), float("-inf")) else None
    return None


def _pos(value: Any) -> float | None:
    f = _num(value)
    return f if (f is not None and f > 0) else None


def _fmt(value: float | None, places: int = 2) -> str:
    return "—" if value is None else f"{value:.{places}f}"


def _declared_spot(block: dict, key: str, name: str, reasons: list[str]) -> float | None:
    """Read a DECLARED spot, or reject the payload.

    A key that is present but unusable (bool, NaN, inf, <= 0, wrong type) is a
    malformed input, not an absent one: silently ignoring it would let a bad
    summary sit behind a good profile and read as agreement.
    """
    if not isinstance(block, dict) or key not in block:
        return None
    value = _pos(block.get(key))
    if value is None:
        reasons.append(
            f"spot_invalid: {name}.{key} is not a finite positive number"
            f" (got {type(block.get(key)).__name__})"
        )
    return value


def _iso_date(value: Any) -> str | None:
    """Accept only a strict YYYY-MM-DD calendar date; anything else is None."""
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


# ── input contract ──────────────────────────────────────────────────────────
def build_pulse(
    *,
    symbol: str,
    gex: Any,
    gex_file: str,
    gex_digest: str | None,
    intel: Any = None,
    intel_file: str = "site/options_intel_brief.json",
    intel_digest: str | None = None,
    gate: Any = None,
    gate_file: str = "data/options_flow/signing_gate.json",
    gate_digest: str | None = None,
    now: datetime,
    reference_session: date | None = None,
    detail_href: str = "gex.html",
    detail_anchor: str = "",
) -> dict:
    """Project already-published options artifacts into one deterministic card.

    Args:
        symbol: the REQUESTED symbol (``"QQQ"``). Never read out of the payload —
            a payload for a different ticker is a mismatch, not a substitution.
        gex: materialised ``site/gex/<SYMBOL>.json`` payload, or None.
        gex_file / gex_digest: the INPUT FILE IDENTITY, kept separate from the
            payload and from the source session so a corrected file cannot
            masquerade as the same one.
        intel / intel_file / intel_digest: the options intel-brief, or None.
        gate / gate_file / gate_digest: the flow signing gate, or None.
        now: tz-aware EVALUATION CLOCK, supplied by the caller.
        reference_session: the caller's reference session; defaults to the most
            recent COMPLETED session before ``now`` per the exchange calendar.
        detail_href / detail_anchor: a LOCAL link to the existing Options detail
            page (no new page, no third-party host).

    Returns a dict that always renders. A data problem degrades this to
    ``available: False`` with explicit ``unavailable_reasons``; it never raises
    and never fabricates.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise PulseInputError("symbol must be a non-empty string")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise PulseInputError("now must be a tz-aware datetime (the caller owns the clock)")
    symbol = symbol.strip().upper()

    if reference_session is None:
        reference_session = nyse_calendar.expected_last_session(now)
    if not isinstance(reference_session, date):
        raise PulseInputError("reference_session must be a date or None")

    pulse: dict[str, Any] = {
        "schema": PULSE_SCHEMA,
        "projector_version": PROJECTOR_VERSION,
        "symbol": symbol,
        "available": False,
        "unavailable_reasons": [],
        "authority": dict(AUTHORITY_FLAGS),
        "source": {
            "key": None,
            "asof": None,
            "detail_href": detail_href,
            "detail_anchor": detail_anchor,
            "files": {
                "gex": {"path": gex_file, "digest": gex_digest, "present": gex is not None},
                "intel": {"path": intel_file, "digest": intel_digest,
                          "present": intel is not None},
                "signing_gate": {"path": gate_file, "digest": gate_digest,
                                 "present": gate is not None},
            },
        },
        # Assessment is environment, not content: it is deliberately EXCLUDED
        # from the content hash so a rebuild at a different clock on identical
        # inputs still reproduces identical content.
        "assessment": {
            "evaluated_utc": now.astimezone(timezone.utc).isoformat(),
            "reference_session": reference_session.isoformat(),
            "sessions_behind": None,
            "freshness": "unknown",
            "reference_session_injected": False,
        },
        "identity": {"name_en": None, "name_zh": None, "group": None},
        "gamma": _gamma_unavailable(),
        "hedge": _hedge_unavailable(),
        "concentrations": _concentrations_unavailable(),
        "chart": None,
        "probability": {
            "available": False,
            "withheld_note_en": PROBABILITY_WITHHELD,
            "withheld_note_zh": (
                "此处不提供真实收盘概率：已准入的概率引擎仍为 RESEARCH_ONLY / "
                "INSUFFICIENT_DATA。此处改为呈现 gamma 背景 — 估计的做市商 gamma 曲线"
                "以及对冲集中的位置。"
            ),
            "alternatives_offered": [
                "Estimated dealer-gamma profile across spot (display-only)",
                "Levels where hedging concentrates (walls / magnet)",
                "Linear assumption-based local gamma sensitivity per 1% move",
            ],
            "alternatives_offered_zh": [
                "跨现价的估计做市商 gamma 曲线（仅供展示）",
                "对冲集中的位置（墙位／磁吸位）",
                "每 1% 变动的线性假设局部敏感度",
            ],
        },
        "flow": _flow_block(intel, gate, reference_session, now),
    }

    reasons = pulse["unavailable_reasons"]

    # ── 1. presence ──────────────────────────────────────────────────────────
    if gex is None:
        reasons.append("source_missing: gex payload not available")
        return _finish(pulse, now, reference_session)
    if not isinstance(gex, dict):
        reasons.append("source_malformed: gex payload is not an object")
        return _finish(pulse, now, reference_session)

    # ── 2. ticker identity (requested symbol, never the payload's own claim) ──
    meta = gex.get("meta")
    meta = meta if isinstance(meta, dict) else {}
    key = meta.get("key")
    if not isinstance(key, str) or key.strip().upper() != symbol:
        reasons.append(f"symbol_mismatch: requested {symbol}, payload declares {key!r}")
        return _finish(pulse, now, reference_session)

    pulse["source"]["key"] = key
    pulse["identity"] = {
        "name_en": meta.get("en") if isinstance(meta.get("en"), str) else None,
        "name_zh": meta.get("zh") if isinstance(meta.get("zh"), str) else None,
        "group": meta.get("grp") if isinstance(meta.get("grp"), str) else None,
    }

    # ── 3. source session (date-only ⇒ delayed / EOD context, never live) ─────
    asof = _iso_date(meta.get("asof"))
    pulse["source"]["asof"] = asof
    if asof is None:
        reasons.append("session_missing: source carries no parseable session date")
        return _finish(pulse, now, reference_session)

    assessment = pulse["assessment"]
    assessment["reference_session_injected"] = True

    # A source dated beyond the caller's reference session is rejected outright.
    # (sessions_behind cannot detect this: past a reference session it measures an
    # EMPTY range and returns 0, which would read as "current" — a silent lie.)
    if asof > assessment["reference_session"]:
        reasons.append(
            f"source_future: source session {asof} is ahead of the reference session "
            f"{assessment['reference_session']}"
        )
        return _finish(pulse, now, reference_session)

    try:
        behind = nyse_calendar.sessions_behind(date.fromisoformat(asof), now)
    except Exception:  # noqa: BLE001 — a calendar fault is a degrade, never a raise
        behind = None
    assessment["sessions_behind"] = behind

    if behind is None:
        assessment["freshness"] = "unknown"
    elif behind == 0:
        assessment["freshness"] = "current_session"
    else:
        assessment["freshness"] = "delayed"
    pulse["source"]["context_label_en"] = (
        f"Delayed end-of-day context, session {asof}"
        + (f" — {behind} session(s) behind the reference session."
           if behind else " — matches the reference session.")
    )
    pulse["source"]["context_label_zh"] = (
        f"延迟的收盘（EOD）背景，交易日 {asof}"
        + (f" — 落后参考交易日 {behind} 个交易日。" if behind else " — 与参考交易日一致。")
    )

    summary = gex.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    profile = gex.get("profile")
    profile = profile if isinstance(profile, dict) else {}
    walls = gex.get("walls")
    walls = walls if isinstance(walls, dict) else {}

    # ── 4. spot identity: summary and profile must be the same instrument ────
    _reasons_before = len(reasons)
    summary_spot = _declared_spot(summary, "spot", "summary", reasons)
    profile_spot = _declared_spot(profile, "spot", "profile", reasons)
    if len(reasons) > _reasons_before:
        # a DECLARED but unusable spot is a malformed payload, not an absent field
        return _finish(pulse, now, reference_session)
    if summary_spot is None and profile_spot is None:
        reasons.append("spot_missing: neither summary nor profile carries a usable spot")
        return _finish(pulse, now, reference_session)
    if summary_spot is not None and profile_spot is not None:
        if abs(summary_spot - profile_spot) > max(1e-6, 1e-6 * profile_spot):
            reasons.append(
                f"spot_identity_mismatch: summary.spot={summary_spot} vs profile.spot={profile_spot}"
            )
            return _finish(pulse, now, reference_session)
    spot = profile_spot if profile_spot is not None else summary_spot
    assert spot is not None  # guarded above

    # ── 5. profile: same owner as the displayed curve AND the displayed crossing
    curve = _read_profile(profile, spot, reasons)
    if curve is None:
        return _finish(pulse, now, reference_session)

    profile_flip = _num(profile.get("flip"))
    summary_flip = _num(summary.get("gamma_flip"))
    crossing = _crossing(curve, profile_flip, spot, summary_flip)

    pulse["chart"] = _chart(curve, spot, crossing.get("spot"))

    # regime sign read off the SAME profile at the SAME spot the curve uses.
    at_spot_bn = curve["at_spot_bn"]
    gamma: dict[str, Any] = {
        "available": at_spot_bn is not None,
        "spot": spot,
        "profile_spot": profile_spot,
        "summary_spot": summary_spot,
        "unit": "$bn net dealer gamma per 1% move",
        "unit_zh": "每 1% 变动的净做市商 gamma（十亿美元）",
        "net_gamma_bn_per_1pct": at_spot_bn,
        "net_gamma_summary_bn": _num(summary.get("net_gex_bn")),
        "regime": None if at_spot_bn is None else ("positive" if at_spot_bn > 0 else
                                                   ("negative" if at_spot_bn < 0 else "zero")),
        "regime_owner": "gex.profile",
        "regime_basis": "assumption",
        "regime_passport": summary.get("regime_passport") if isinstance(
            summary.get("regime_passport"), dict) else None,
        "source_tier": summary.get("tier") if isinstance(summary.get("tier"), str) else None,
        "n_strikes": summary.get("n_strikes") if isinstance(
            summary.get("n_strikes"), int) and not isinstance(
            summary.get("n_strikes"), bool) else None,
        "profile_points": len(curve["points"]),
        "crossing": crossing,
        "framing_en": (
            "Estimated dealer-gamma exposure as a function of spot. Not a closing-price "
            "density. The long-call / short-put sign is an unobservable assumption."
        ),
        "framing_zh": (
            "以现价为变量的估计做市商 gamma 敞口曲线，并非收盘价密度。多头看涨／空头看跌的"
            "符号方向是不可观测的假设。"
        ),
    }
    pulse["gamma"] = gamma
    if not gamma["available"]:
        reasons.append("gamma_unavailable: profile carries no value at the reference spot")

    # ── 6. ±1% local sensitivity — LINEAR, ASSUMPTION-BASED, REFERENCE NOTIONAL ─
    pulse["hedge"] = _hedge(at_spot_bn, summary, spot)

    # ── 7. concentrations (walls) — never a floor, cap or target ─────────────
    pulse["concentrations"] = _concentrations(walls, spot)

    pulse["available"] = bool(gamma["available"] or pulse["concentrations"]["available"])
    if not pulse["available"]:
        reasons.append("no_usable_projection: neither gamma nor concentrations qualified")
    return _finish(pulse, now, reference_session)


# ── profile reader ──────────────────────────────────────────────────────────
def _read_profile(profile: dict, spot: float, reasons: list[str]) -> dict | None:
    spots = profile.get("spots")
    values = profile.get("gamma_bn")
    if not isinstance(spots, list) or not isinstance(values, list):
        reasons.append("profile_malformed: profile.spots / profile.gamma_bn missing or not lists")
        return None
    if not spots or len(spots) != len(values):
        reasons.append(
            f"profile_malformed: {len(spots)} spot(s) vs {len(values)} value(s)"
        )
        return None
    if len(spots) > MAX_PROFILE_POINTS:
        reasons.append(f"profile_oversize: {len(spots)} points exceeds cap {MAX_PROFILE_POINTS}")
        return None

    xs: list[float] = []
    ys: list[float] = []
    for i, (x, y) in enumerate(zip(spots, values)):
        fx, fy = _num(x), _num(y)
        if fx is None or fy is None:
            reasons.append(f"profile_malformed: non-finite coordinate at index {i}")
            return None
        if i and fx <= xs[-1]:
            reasons.append(
                f"profile_malformed: spots not strictly increasing at index {i} "
                f"({fx} after {xs[-1]})"
            )
            return None
        xs.append(fx)
        ys.append(fy)

    # The profile grid is symmetric about spot, so the midpoint IS the spot. Bind
    # the reading to the profile's OWN coordinate rather than to the summary.
    mid = len(xs) // 2
    at_spot = ys[mid] if abs(xs[mid] - spot) <= max(1e-6, 1e-6 * spot) else None
    return {
        "x": xs,
        "y": ys,
        "points": [{"spot": round(x, 2), "gamma_bn": y} for x, y in zip(xs, ys)],
        "at_spot_bn": at_spot,
    }


def _crossing(curve: dict, profile_flip: float | None, spot: float,
              summary_flip: float | None) -> dict:
    """The displayed crossing comes from the SAME owner as the displayed curve.

    When the two published owners disagree, the disagreement is surfaced, never
    silently resolved by averaging the two numbers.
    """
    out: dict[str, Any] = {
        "available": profile_flip is not None,
        "spot": profile_flip,
        "owner": "gex.profile",
        "dist_pct": None if profile_flip is None else round(100.0 * (profile_flip - spot) / spot, 2),
        "disagreement": {
            "present": False,
            "profile_flip": profile_flip,
            "summary_flip": summary_flip,
            "delta": None,
            "note_en": "",
            "note_zh": "",
        },
    }
    if profile_flip is not None and summary_flip is not None:
        delta = round(profile_flip - summary_flip, 4)
        if abs(delta) > 1e-9:
            out["disagreement"] = {
                "present": True,
                "profile_flip": profile_flip,
                "summary_flip": summary_flip,
                "delta": delta,
                "note_en": (
                    f"The curve owner and the summary owner disagree on the crossing by "
                    f"{delta:+.4f}. This card shows the profile's own crossing ({profile_flip}), "
                    f"because it is the same object the curve above is drawn from."
                ),
                "note_zh": (
                    f"曲线来源与摘要来源的交叉点相差 {delta:+.4f}。本卡片显示曲线自身的交叉点"
                    f"（{profile_flip}），因为上方曲线正由该对象绘制。"
                ),
            }
    elif profile_flip is None:
        out["disagreement"]["note_en"] = (
            "No crossing on this profile; the curve does not change sign over the plotted range."
        )
        out["disagreement"]["note_zh"] = "该曲线在所绘区间内无交叉点，符号未发生变化。"
    return out


# ── ±1% sensitivity ─────────────────────────────────────────────────────────
def _hedge(at_spot_bn: float | None, summary: dict, spot: float) -> dict:
    """LINEAR assumption-based local gamma sensitivity — never a hedge TRADE.

    ``net_gex_bn`` is the incumbent engine's OWN unit (dollars per ``pct_move``,
    i.e. per 1% move), so no repricer is introduced here. What is published is a
    REFERENCE-DOLLAR sensitivity under held assumptions, with opposite shocks
    obeying consistent signs.
    """
    out: dict[str, Any] = {
        "available": at_spot_bn is not None,
        "basis": "LINEAR_ASSUMPTION_BASED_SENSITIVITY",
        "basis_zh": "线性假设敏感度",
        "unit": "$bn per 1% move, reference notional",
        "unit_zh": "每 1% 变动的十亿美元参考名义",
        "reference_notional_usd_per_1pct": None,
        "up_1pct_bn": None,
        "down_1pct_bn": None,
        "interpretation_en": (
            "Local sensitivity only. A 1% move corresponds to roughly this much "
            "assumption-signed dealer gamma, expressed as a reference-dollar amount."
        ),
        "interpretation_zh": (
            "仅为局部敏感度。1% 的变动对应约此规模的、带假设符号的做市商 gamma，以参考美元金额表示。"
        ),
        "assumptions_en": [
            "Linear local approximation — not an exact nonlinear hedge trade",
            "Implied volatility, time and open interest held constant across the shock",
            "Assumed dealer book: long calls, short puts (an unobservable sign assumption)",
            "Reference-dollar notional — not an executable order size",
        ],
        "assumptions_zh": [
            "局部线性近似 — 并非精确的非线性对冲交易",
            "冲击前后隐含波动率、时间与未平仓量保持不变",
            "假设做市商持仓：多头看涨期权、空头看跌期权（不可观测的符号假设）",
            "参考美元名义 — 并非可执行订单规模",
        ],
        "withheld_reasons_en": [],
        "withheld_reasons_zh": [],
    }
    if at_spot_bn is None:
        out["withheld_reasons_en"].append(
            "No qualified local gamma value at the reference spot; amounts are withheld "
            "rather than estimated."
        )
        out["withheld_reasons_zh"].append(
            "参考现价处没有合格的局部 gamma 值；此处不展示金额，而非进行估算。"
        )
        return out

    # Reference notional is the shock DEFINITION, read off the published spot:
    # one percent of the reference spot, in dollars per unit. It is not a size.
    out["reference_notional_usd_per_1pct"] = round(spot * 0.01, 2)
    out["up_1pct_bn"] = round(at_spot_bn, 4)
    out["down_1pct_bn"] = round(-at_spot_bn, 4)
    return out


# ── concentrations ──────────────────────────────────────────────────────────
def _concentrations(walls: dict, spot: float) -> dict:
    out = _concentrations_unavailable()
    rows = walls.get("by_strike")
    if not isinstance(rows, list) or not rows:
        out["withheld_reasons_en"].append("No per-strike wall rows published.")
        out["withheld_reasons_zh"].append("未发布按行权价划分的墙位数据。")
        return out
    if len(rows) > MAX_WALL_ROWS:
        out["withheld_reasons_en"].append(
            f"Per-strike ladder of {len(rows)} rows exceeds the {MAX_WALL_ROWS}-row card cap."
        )
        out["withheld_reasons_zh"].append(f"按行权价的阶梯数据超过卡片上限 {MAX_WALL_ROWS} 行。")
        return out

    cleaned: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        k, net = _num(r.get("K")), _num(r.get("net_mn"))
        if k is None or net is None or k <= 0:
            continue
        pct = _num(r.get("pct"))
        cleaned.append({
            "strike": k,
            "net_mn": net,
            "share_pct": pct,
            "side": "above" if k > spot else ("below" if k < spot else "at"),
        })
    if not cleaned:
        out["withheld_reasons_en"].append("Per-strike rows carried no usable strike/value pair.")
        out["withheld_reasons_zh"].append("按行权价的数据中没有可用的行权价／数值组合。")
        return out

    cleaned.sort(key=lambda r: (-abs(r["net_mn"]), r["strike"]))
    top = cleaned[:MAX_TABLE_ROWS]
    top.sort(key=lambda r: r["strike"])
    out.update({
        "available": True,
        "rows": top,
        "row_count": len(cleaned),
        "call_wall": _num(walls.get("call_wall")),
        "put_wall": _num(walls.get("put_wall")),
        "largest_oi": _num(walls.get("largest_oi")),
        "max_abs_mn": _num(walls.get("max_abs_mn")),
        "withheld_reasons_en": [],
        "withheld_reasons_zh": [],
    })
    return out


# ── flow (signed direction is withheld) ─────────────────────────────────────
def _flow_block(intel: Any, gate: Any, reference_session: date, now_utc: datetime) -> dict:
    out: dict[str, Any] = {
        "available": False,
        "withheld_note_en": FLOW_WITHHELD,
        "withheld_note_zh": (
            "在资金流签名门报告 direction_reliable = false 期间，带符号的资金流与看涨"
            "到期百分比不可用。不会以任何数字看涨代理替代，缺失或过期的简报也绝不会被读作零活动。"
        ),
        "reasons": [],
        "gate_present": isinstance(gate, dict),
        "gate_direction_reliable": None,
        "gate_asof": None,
        "intel_schema": None,
        "intel_model": None,
        "intel_as_of_session": None,
        "intel_sessions_behind": None,
        "intel_board_state": None,
        "intel_pending_reason": None,
        "unsigned_activity_note_en": (
            "Any call/put activity retained from these artifacts is UNSIGNED open interest or "
            "volume — never a bullish or bearish read."
        ),
        "unsigned_activity_note_zh": (
            "从这些产物中保留的任何看涨／看跌活动均为「未签名」持仓或成交量，绝不构成看涨或看跌解读。"
        ),
    }
    if not isinstance(gate, dict):
        out["reasons"].append("signing_gate_missing: flow signing gate not available")
    else:
        reliable = gate.get("direction_reliable")
        out["gate_direction_reliable"] = reliable if isinstance(reliable, bool) else None
        out["gate_asof"] = _iso_date(gate.get("asof"))
        if reliable is not True:
            out["reasons"].append(
                "direction_unreliable: signing_gate.direction_reliable is "
                f"{reliable!r}, so no signed flow direction is published"
            )
    if not isinstance(intel, dict):
        out["reasons"].append("intel_brief_missing: options intel brief not available")
    else:
        out["intel_schema"] = intel.get("schema") if isinstance(
            intel.get("schema"), str) else None
        mv = intel.get("model_version")
        out["intel_model"] = mv if isinstance(mv, str) else None
        out["intel_as_of_session"] = _iso_date(intel.get("as_of_session"))
        bs = intel.get("board_state")
        out["intel_board_state"] = bs if isinstance(bs, str) else None
        pr = intel.get("pending_reason")
        out["intel_pending_reason"] = pr if isinstance(pr, str) else None
        if out["intel_as_of_session"] is None:
            out["reasons"].append("intel_brief_stale: brief carries no parseable as-of session")
        else:
            try:
                behind = nyse_calendar.sessions_behind(
                    date.fromisoformat(out["intel_as_of_session"]), now_utc)
            except Exception:  # noqa: BLE001
                behind = None
            out["intel_sessions_behind"] = behind
            if behind is not None and behind > 0:
                # Historical provenance is preserved verbatim; only the DIRECTIONAL
                # read is suppressed. A stale brief is never reinterpreted as zero.
                out["reasons"].append(
                    f"intel_brief_stale: brief as-of session {out['intel_as_of_session']} is "
                    f"{behind} session(s) behind the reference session "
                    f"{reference_session.isoformat()}"
                )
    if not out["reasons"]:  # pragma: no cover — defensive
        out["reasons"].append("direction_unreliable: signed flow is not admitted for this card")
    return out


# ── deterministic chart geometry (numbers only; no third-party renderer) ────
def _chart(curve: dict, spot: float, flip: float | None) -> dict | None:
    xs, ys = curve["x"], curve["y"]
    if len(xs) < 2:
        return None
    lo, hi = min(ys), max(ys)
    span = (hi - lo) or 1.0
    # pad so the zero line and the extremes never touch the frame
    pad = span * 0.12
    ymin, ymax = lo - pad, hi + pad
    x0, x1 = xs[0], xs[-1]
    w, h = MAX_PROFILE_XL, MAX_PROFILE_XH

    def px(x: float) -> float:
        return round(w * (x - x0) / (x1 - x0 or 1.0), 2)

    def py(y: float) -> float:
        return round(h * (ymax - y) / (ymax - ymin), 2)

    lo_aspect, hi_aspect = CHART_ASPECT
    if not (lo_aspect <= (w / h) <= hi_aspect):  # pragma: no cover - invariant guard
        raise PulseInputError(f"chart aspect {w / h:.2f} outside {CHART_ASPECT}")
    path = "M " + " L ".join(f"{px(x)},{py(y)}" for x, y in zip(xs, ys))
    return {
        "width": w,
        "height": h,
        "x_min": round(x0, 2),
        "x_max": round(x1, 2),
        "y_min": round(ymin, 4),
        "y_max": round(ymax, 4),
        "y_zero": py(0.0) if ymin <= 0.0 <= ymax else None,
        "spot_x": px(spot),
        "spot": round(spot, 2),
        "flip_x": px(flip) if flip is not None and x0 <= flip <= x1 else None,
        "flip": None if flip is None else round(flip, 2),
        "path": path,
        "points": len(xs),
        "unit": "$bn net dealer gamma per 1% move",
    }



# ── narrative (fully deterministic EN/ZH; states what is known) ──────────────
def _narrative(pulse: dict) -> dict:
    en: list[str] = []
    zh: list[str] = []
    if not pulse["available"]:
        en.append("Options data is unavailable for this symbol right now.")
        zh.append("该标的的期权数据当前不可用。")
        for r in pulse["unavailable_reasons"]:
            en.append(f"Reason: {r}.")
            zh.append(f"原因：{r}。")
        return {"en": en, "zh": zh}

    g = pulse["gamma"]
    src = pulse["source"]
    assess = pulse["assessment"]
    sym = pulse["symbol"]

    en.append(f"{sym} estimated dealer gamma, delayed end-of-day session {src['asof']}.")
    zh.append(f"{sym} 估计做市商 gamma，延迟收盘数据，交易日 {src['asof']}。")

    if g["available"] and g["net_gamma_bn_per_1pct"] is not None:
        v = g["net_gamma_bn_per_1pct"]
        direction = "positive" if v > 0 else ("negative" if v < 0 else "flat")
        en.append(
            f"The profile reads {v:+.2f} $bn per 1% move at spot {g['spot']:.2f} — an "
            f"assumption-signed {direction} gamma regime."
        )
        zh.append(
            f"曲线在现价 {g['spot']:.2f} 处读数为每 1% 变动 {v:+.2f} 十亿美元 — "
            f"一个带假设符号的{direction} gamma 状态。"
        )
    else:
        en.append("No qualified gamma value at the reference spot.")
        zh.append("参考现价处没有合格的 gamma 值。")

    crossing = g.get("crossing") or {}
    if crossing.get("available"):
        en.append(
            f"The curve crosses zero at {crossing['spot']:.2f}, "
            f"{crossing['dist_pct']:+.2f}% from spot."
        )
        zh.append(
            f"曲线在 {crossing['spot']:.2f} 处穿越零轴，距现价 {crossing['dist_pct']:+.2f}%。"
        )
    dis = crossing.get("disagreement") or {}
    if dis.get("present"):
        en.append(dis["note_en"])
        zh.append(dis["note_zh"])

    c = pulse["concentrations"]
    if c["available"]:
        en.append(
            "Concentration is shown where dealer hedging is largest — these are levels of "
            "positioning concentration, not a floor, a cap or a target."
        )
        zh.append(
            "集中度展示做市商对冲规模最大的位置 — 这些是持仓集中度水平，不是支撑、下跌上限或目标价。"
        )
        if c.get("call_wall") is not None:
            en.append(f"Heaviest positive-gamma concentration above spot: {c['call_wall']:.2f}.")
            zh.append(f"现价之上最重的正 gamma 集中位：{c['call_wall']:.2f}。")
        if c.get("put_wall") is not None:
            en.append(f"Heaviest negative-gamma concentration below spot: {c['put_wall']:.2f}.")
            zh.append(f"现价之下最重的负 gamma 集中位：{c['put_wall']:.2f}。")
    else:
        en.append("Strike-level concentrations are unavailable.")
        zh.append("行权价级别的集中度不可用。")

    h = pulse["hedge"]
    if h["available"]:
        en.append(
            f"At ±1% the local sensitivity is {h['up_1pct_bn']:+.2f} / "
            f"{h['down_1pct_bn']:+.2f} $bn — a linear, assumption-based reference sensitivity, "
            "not an exact hedge trade."
        )
        zh.append(
            f"在 ±1% 处，局部敏感度为 {h['up_1pct_bn']:+.2f} / {h['down_1pct_bn']:+.2f} 十亿美元 — "
            "这是基于线性假设的参考敏感度，而非精确的对冲交易。"
        )

    en.append(PROBABILITY_WITHHELD)
    zh.append(
        "此处不提供真实收盘概率：已准入的概率引擎仍为 RESEARCH_ONLY / INSUFFICIENT_DATA。"
        "此处改为呈现 gamma 背景 — 估计的做市商 gamma 曲线以及对冲集中的位置。"
    )
    en.append(FLOW_WITHHELD)
    zh.append(pulse["flow"]["withheld_note_zh"])

    behind = assess.get("sessions_behind")
    if isinstance(behind, int) and behind > 0:
        en.append(f"This context is {behind} session(s) behind the reference session.")
        zh.append(f"该背景落后参考交易日 {behind} 个交易日。")
    return {"en": en, "zh": zh}


# ── compact AI context (facts only, display_only; the model may not restate) ──
def _context(pulse: dict, *, max_chars: int = 2400) -> dict:
    g, c, h = pulse["gamma"], pulse["concentrations"], pulse["hedge"]
    facts: dict[str, Any] = {
        "display_only": True,
        "symbol": pulse["symbol"],
        "source_asof": pulse["source"]["asof"],
        "source_files": {k: v["path"] for k, v in pulse["source"]["files"].items()},
        "reference_session": pulse["assessment"]["reference_session"],
        "sessions_behind": pulse["assessment"]["sessions_behind"],
        "spot": g["spot"],
        "net_gamma_bn_per_1pct": g["net_gamma_bn_per_1pct"],
        "gamma_regime": g["regime"],
        "gamma_basis": g["regime_basis"],
        "crossing_spot": (g.get("crossing") or {}).get("spot"),
        "crossing_owner": (g.get("crossing") or {}).get("owner"),
        "call_wall": c.get("call_wall"),
        "put_wall": c.get("put_wall"),
        "hedge_up_1pct_bn": h["up_1pct_bn"],
        "hedge_down_1pct_bn": h["down_1pct_bn"],
        "hedge_basis": h["basis"],
        "probability_available": False,
        "signed_flow_available": False,
        "authority": dict(AUTHORITY_FLAGS),
    }
    blob = json.dumps(facts, sort_keys=True, separators=(",", ":"), default=str)
    if len(blob) > max_chars:  # bounded budget; never silently over budget
        facts["_truncated"] = True
        facts.pop("hedge_up_1pct_bn", None)
        facts.pop("hedge_down_1pct_bn", None)
        facts.pop("spot", None)
        blob = json.dumps(facts, sort_keys=True, separators=(",", ":"), default=str)
    facts["_facts"] = blob
    return facts


# ── content hash: binds SEMANTIC inputs, excludes the build clock ───────────
def _semantic_fingerprint(pulse: dict) -> str:
    g, c, h = pulse["gamma"], pulse["concentrations"], pulse["hedge"]
    return json.dumps({
        "schema": PULSE_SCHEMA,
        "projector_version": PROJECTOR_VERSION,
        "symbol": pulse["symbol"],
        "source_asof": pulse["source"]["asof"],
        "digests": {k: v["digest"] for k, v in sorted(pulse["source"]["files"].items())},
        "spot": g["spot"],
        "net_gamma": g["net_gamma_bn_per_1pct"],
        "regime": g["regime"],
        "crossing": (g.get("crossing") or {}).get("spot"),
        "crossing_disagreement": ((g.get("crossing") or {}).get("disagreement") or {}).get("delta"),
        "hedge_up": h["up_1pct_bn"],
        "hedge_down": h["down_1pct_bn"],
        "rows": [[r["strike"], r["net_mn"]] for r in c.get("rows", [])],
        "call_wall": c.get("call_wall"),
        "put_wall": c.get("put_wall"),
        "gate_direction_reliable": pulse["flow"].get("gate_direction_reliable"),
        "intel_as_of_session": pulse["flow"].get("intel_as_of_session"),
        "intel_board_state": pulse["flow"].get("intel_board_state"),
        "available": pulse["available"],
    }, sort_keys=True, separators=(",", ":"), default=str)


def _finish(pulse: dict, now: datetime, reference_session: date) -> dict:
    pulse["narrative"] = _narrative(pulse)
    pulse["context"] = _context(pulse)
    pulse["content_hash"] = "sha256:" + hashlib.sha256(
        _semantic_fingerprint(pulse).encode("utf-8")
    ).hexdigest()
    pulse["assessment"]["evaluated_utc"] = now.astimezone(timezone.utc).isoformat()
    return pulse


def _gamma_unavailable() -> dict:
    """Same SHAPE as the qualified block, so every consumer is total."""
    return {
        "available": False,
        "spot": None,
        "profile_spot": None,
        "summary_spot": None,
        "unit": "$bn net dealer gamma per 1% move",
        "unit_zh": "每 1% 变动的净做市商 gamma（十亿美元）",
        "net_gamma_bn_per_1pct": None,
        "net_gamma_summary_bn": None,
        "regime": None,
        "regime_owner": None,
        "regime_basis": None,
        "regime_passport": None,
        "source_tier": None,
        "n_strikes": None,
        "profile_points": 0,
        "crossing": {"available": False, "spot": None, "owner": None, "dist_pct": None,
                     "disagreement": {"present": False, "profile_flip": None,
                                      "summary_flip": None, "delta": None,
                                      "note_en": "", "note_zh": ""}},
        "framing_en": "",
        "framing_zh": "",
    }


def _hedge_unavailable() -> dict:
    return _hedge(None, {}, 0.0)


def _concentrations_unavailable() -> dict:
    return {
        "available": False,
        "rows": [],
        "row_count": 0,
        "call_wall": None,
        "put_wall": None,
        "largest_oi": None,
        "max_abs_mn": None,
        "withheld_reasons_en": [],
        "withheld_reasons_zh": [],
        "framing_en": "Concentration levels — never a floor, cap or target.",
        "framing_zh": "集中度水平 — 绝不是支撑、下跌上限或目标价。",
    }


def digest_bytes(raw: bytes) -> str:
    """Stable content digest for an input FILE, kept separate from its payload."""
    return "sha256:" + hashlib.sha256(raw).hexdigest()