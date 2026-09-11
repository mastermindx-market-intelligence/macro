"""HK dashboard Tier-1 glance copy — display names, tone-sign, lanes, flip line.

DISPLAY-ONLY helpers consumed by scripts/build_hk.py and engine/hk_signal_stack.py.
No I/O. Every function is a pure rewrite of a value the producers already computed.
"""
from __future__ import annotations

from engine.i18n import _ordinal_suffix, tr

# Doctrine §3 / #2206 lanes. Named glance leaks remap to the ratified words;
# every unknown/unmapped cycle label routes to the cautious lane (never a raw slug).
CAUTIOUS_LANE: tuple[str, str] = ("Stand aside", "观望")
CYCLE_LANE: dict[str, tuple[str, str]] = {
    "BUY ZONE": ("Buy now", "立即买入"),
    "UNCONFIRMED TURN": CAUTIOUS_LANE,
}
_FACE_LANE_BY_EN = {en: (en, zh) for en, zh in CYCLE_LANE.values()}

# Peg-state jargon on the What To Do face → one plain pair. Full machine state
# stays on the card dialog.
PEG_FACE: dict[str, tuple[str, str]] = {
    "weak-side (outflow)": ("money leaving", "资金流出"),
    "strong-side (inflow)": ("money arriving", "资金流入"),
    "mid-band": ("in the middle of the band", "处于区间中部"),
    "weak-side": ("money leaving", "资金流出"),
    "strong-side": ("money arriving", "资金流入"),
}

# Cross-asset strip: slug → (display_en, display_zh, meaning_en, meaning_zh).
# `kind` is the stable machine key (peg matching, tests); it is never shown.
TILE_COPY: dict[str, dict[str, str]] = {
    "growth": {
        "tag_en": "Hang Seng Tech", "tag_zh": "恒生科技",
        "meaning_en": "Hong Kong tech stocks today",
        "meaning_zh": "今日港股科技",
    },
    "peg": {
        "tag_en": "HK dollar peg", "tag_zh": "港元联汇",
        "meaning_en": "higher = a weaker HK dollar",
        "meaning_zh": "数值升高 = 港元走弱",
    },
    "USDCNH": {
        "tag_en": "Offshore yuan", "tag_zh": "离岸人民币",
        "meaning_en": "quoted as yuan per US dollar — higher = a weaker yuan",
        "meaning_zh": "以美元兑人民币报价 — 数值升高 = 人民币走弱",
    },
    "DXY": {
        "tag_en": "US dollar", "tag_zh": "美元指数",
        "meaning_en": "against a basket of currencies — higher = a stronger dollar",
        "meaning_zh": "相对一篮子货币 — 数值升高 = 美元走强",
    },
    "yield": {
        "tag_en": "HK overnight rate", "tag_zh": "港元隔夜利率",
        "meaning_en": "what HK banks charge each other overnight",
        "meaning_zh": "香港银行间隔夜拆借成本",
    },
    "USD/oz": {
        "tag_en": "Gold", "tag_zh": "黄金",
        "meaning_en": "gold priced in US dollars",
        "meaning_zh": "以美元计价的黄金",
    },
}

_CHG_WORD = {
    "up": ("Up", "涨"),
    "down": ("Down", "跌"),
    "flat": ("Flat", "平"),
}


def chg_sign(chg: float, *, decimals: int | None = None) -> str:
    """Sign of the displayed change. Never inverted for risk-tone.

    When `decimals` is set, the sign follows the rounded print (a raw +0.04
    that formats as +0.0 is Flat, not Up).
    """
    shown = float(f"{chg:.{decimals}f}") if decimals is not None else chg
    if shown > 0:
        return "up"
    if shown < 0:
        return "down"
    return "flat"


def chg_word(sign: str) -> tuple[str, str]:
    """Up / Down / Flat for the strip chip. Follows chg_sign, never risk-tone."""
    return _CHG_WORD.get(sign, _CHG_WORD["flat"])


def cycle_lane(label: str | None, label_zh: str | None = None) -> tuple[str, str]:
    """Glance-tier cycle label → doctrine §3 lane. Unknown states → cautious lane."""
    lab = str(label) if label else ""
    zh = str(label_zh) if label_zh else ""
    if not lab:
        return ("", zh)
    hit = CYCLE_LANE.get(lab)
    if hit:
        return hit
    already = _FACE_LANE_BY_EN.get(lab)
    if already:
        return already
    return CAUTIOUS_LANE


def apply_cycle_lane(row: dict) -> dict:
    """Copy a standout/setup row and put a doctrine §3 lane on the face."""
    out = dict(row)
    en, zh = cycle_lane(row.get("label"), row.get("label_zh"))
    out["label"], out["label_zh"] = en, zh
    return out


def range_reading(pctile: int | float | None) -> tuple[str, str]:
    """VHSI-style 'where in its range' — 32 lands in mid-range (packet example)."""
    if pctile is None:
        return ("", "")
    p = int(round(float(pctile)))
    if p <= 24:
        return ("near the low of its range", "接近区间低位")
    if p <= 74:
        return ("mid-range", "区间中部")
    return ("near the high of its range", "接近区间高位")


def history_reading(pctile: int | float | None) -> tuple[str, str]:
    """A/H-style 'vs history' — 51 lands in about average (packet example)."""
    if pctile is None:
        return ("", "")
    p = int(round(float(pctile)))
    if p <= 24:
        return ("low vs history", "低于历史")
    if p <= 74:
        return ("about average", "大致平均")
    return ("high vs history", "高于历史")


def pctile_label(pctile: int | float | None) -> tuple[str, str]:
    """Tier-2 ordinal: 32nd percentile / 第32百分位. Never the '32th' typo."""
    if pctile is None:
        return ("", "")
    n = int(round(float(pctile)))
    return (f"{n}{_ordinal_suffix(n)} percentile", f"第{n}百分位")


def peg_face(state: str | None) -> tuple[str, str]:
    if not state:
        return ("", "")
    hit = PEG_FACE.get(state)
    if hit:
        return hit
    for key, pair in PEG_FACE.items():
        if key in state:
            return pair
    return (state, tr(state))


def plain_flip_line(snap: dict | None) -> tuple[str, str]:
    """ONE Tier-1 sentence of what would flip the read. Numeric thresholds stay
    on the existing 'The checks' popover (the producer flip_en / flip_zh)."""
    if not isinstance(snap, dict):
        return ("", "")
    comps = [c for c in (snap.get("components") or []) if isinstance(c, dict)]
    verdict = snap.get("verdict")
    weakest = min(comps, key=lambda c: c.get("score") if c.get("score") is not None else 50) if comps else None
    strongest = max(comps, key=lambda c: c.get("score") if c.get("score") is not None else 50) if comps else None
    if verdict == "RISK_ON" and weakest:
        return (f"The read flips if {weakest['label_en']} loses its lead.",
                f"若{weakest['label_zh']}失去领先，读数会翻转。")
    if verdict == "RISK_OFF" and strongest:
        return (f"The read flips if {strongest['label_en']} recovers.",
                f"若{strongest['label_zh']}回稳，读数会翻转。")
    if weakest:
        return (f"The read flips if {weakest['label_en']} turns clearly for or against.",
                f"若{weakest['label_zh']}明确转多或转空，读数会翻转。")
    return ("The read flips if the checks turn.",
            "若各项检查转向，读数会翻转。")
