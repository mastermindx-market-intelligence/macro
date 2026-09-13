"""China dashboard Tier-1 glance copy — posture lanes, reason faces, clause.

DISPLAY-ONLY helpers consumed by scripts/build_china.py and the china.html.j2
macro wrap. No I/O. Every function is a pure rewrite of a value the producers
already computed (engine.china_playbook dial + engine.market_state labels).

Stance vocabulary (Act · Get ready · Watch — don't chase · Stand aside) is
the house TLDR law in engine.master_brain._STANCE_LAW; "Stand aside" is also
a cycles.py / sector_bottom.py face label. A genuinely unknown/unmapped
state routes to the cautious lane — never a bullish word, never a raw slug.
"""
from __future__ import annotations

import re

from engine.china_playbook import MARGIN_CROWDED_PCTILE

# Keys are engine.china_playbook._POSTURES. Lane words are the
# engine.master_brain._STANCE_LAW set (Act · Get ready · Watch — don't chase ·
# Stand aside), plus the Neutral snapshot (spec §1.4 / §3.1a). Genuinely
# unknown strings → cautious lane.
CAUTIOUS_LANE: tuple[str, str] = ("Watch — don't chase", "观察，勿追高")
_LANE_STAND_ASIDE: tuple[str, str] = ("Stand aside", "观望")
_LANE_GET_READY: tuple[str, str] = ("Get ready", "做好准备")
_LANE_ACT: tuple[str, str] = ("Act", "行动")
_LANE_NEUTRAL: tuple[str, str] = (
    "Neutral — add slowly, don't chase",
    "中性——慢慢加仓，勿追高",
)

POSTURE_LANE: dict[str, tuple[str, str]] = {
    "DEFENSIVE": _LANE_STAND_ASIDE,          # engine: DEFENSIVE
    "CAREFUL": CAUTIOUS_LANE,                # engine: CAREFUL
    "NEUTRAL": _LANE_NEUTRAL,                # engine: NEUTRAL
    "CONSTRUCTIVE": _LANE_GET_READY,         # engine: CONSTRUCTIVE
    "AGGRESSIVE": _LANE_ACT,                 # engine: AGGRESSIVE
}
_FACE_LANE_BY_EN = {en: (en, zh) for en, zh in POSTURE_LANE.values()}
_FACE_LANE_BY_EN[CAUTIOUS_LANE[0]] = CAUTIOUS_LANE
_FACE_LANE_BY_EN[_LANE_STAND_ASIDE[0]] = _LANE_STAND_ASIDE

_POSTURE_TONE = {
    "DEFENSIVE": "down",
    "CAREFUL": "warn",
    "NEUTRAL": "warn",
    "CONSTRUCTIVE": "up",
    "AGGRESSIVE": "up",
}

# Producer constant (engine.china_playbook.MARGIN_CROWDED_PCTILE). Do not restate.
_MARGIN_TOP_PCT = 100 - MARGIN_CROWDED_PCTILE  # 15

_BULLISH_POSTURES = frozenset({"AGGRESSIVE", "CONSTRUCTIVE"})
_BEARISH_POSTURES = frozenset({"DEFENSIVE", "CAREFUL"})

# Round-2 word-budget faces. Used ONLY when the matching producer reason fired.
# Banned G3 tokens stay in the LENS tip, never at rest.
_FACE_GROWTH = {
    "sign": "+",
    "en": "Fear like this has usually been a buying window, not a top — add quality slowly, don't chase.",
    "zh": "这种恐慌通常是买入窗口，而不是顶部——慢慢吸纳优质资产，不要追高。",
    "tip_en": (
        "About seven in ten past growth-scare episodes on this page's own history "
        "resolved higher. Windows, not certainties — re-drawn nightly."
    ),
    "tip_zh": "本页历史记录中，过往增长恐慌阶段约有七成最终走高。是窗口，不是定论——每晚重新校准。",
}
_FACE_MONEY_MIXED = {
    "sign": "ℹ",
    "en": "Money at the central bank is mixed — no single vote yet.",
    "zh": "央行货币条件方向不一——尚无单一投票。",
    "tip_en": (
        "The available monetary-conditions inputs do not agree. Counted once, "
        "as a single monetary-conditions read; no net vote."
    ),
    "tip_zh": "可用的货币条件输入方向不一，合并为一次货币条件读数；无净投票。",
}
_FACE_MARGIN_CROWDED = {
    "sign": "−",
    "en": "Borrowed money in A-shares is crowded — a fall would run further from here. Tighten risk.",
    "zh": "A股杠杆资金拥挤，一旦下跌会走得更远。收紧风险。",
    "tip_en": (
        "Borrowed money invested in A-shares, as a share of tradable market value. "
        "Crowded borrowing makes a fall run further. It is currently in the top "
        f"{_MARGIN_TOP_PCT}% of its own range."
    ),
    "tip_zh": (
        "两融余额占流通市值的比重。杠杆越拥挤，下跌时的连锁反应越大。"
        f"目前处于自身区间的最高 {_MARGIN_TOP_PCT}%。"
    ),
}
_FACE_MARGIN_WASHED = {
    "sign": "+",
    "en": "Borrowed money in A-shares has washed out — positioning is light.",
    "zh": "A股杠杆资金已经出清——仓位偏轻。",
    "tip_en": _FACE_MARGIN_CROWDED["tip_en"],
    "tip_zh": _FACE_MARGIN_CROWDED["tip_zh"],
}

# Spec §9.12 worded empty — loading ≠ a frozen sentence.
EMPTY_REASON = {
    "sign": "ℹ",
    "en": "This stance line has not arrived",
    "zh": "该操作读数尚未到达",
    "tip_en": "The playbook has not emitted this reason for this session.",
    "tip_zh": "本会话策略尚未给出这条理由。",
    "empty": True,
}
EMPTY_CLAUSE: tuple[str, str] = (
    "This regime clause has not arrived for this session",
    "本会话尚未收到状态说明",
)

_MID_SCARE_CLAUSE: tuple[str, str] = (
    "Mid-scare: the market is falling broadly while policy stays easy — the fear is the setup, not yet the signal.",
    "恐慌中段：市场普跌，政策仍宽松——恐慌是机会的前置条件，还不是入场信号。",
)

_BANNED_G3 = (
    "90th percentile",
    "3/3",
    "ONE monetary-conditions vote",
    "~70% hit",
    "Breadth breakdown (all-boats)",
    "Intensity 87/100",
    "×0.78",
)

_EN_WORD_BUDGET = 22
_ZH_CHAR_BUDGET = 34

_LEGS_EN = re.compile(r"(\d+)\s*/\s*(\d+)\s*legs", re.I)
_LEGS_EN_OF = re.compile(r"(\d+)\s+of\s+(\d+)\s+legs", re.I)
_LEGS_ZH = re.compile(r"(\d+)\s*/\s*(\d+)\s*项")
_LEGS_ZH_OF = re.compile(r"(\d+)项中(\d+)项")
_MIXED_COUNTS_EN = re.compile(
    r"(\d+)\s+easing\s*/\s*(\d+)\s+tightening\s*/\s*(\d+)\s+neutral",
    re.I,
)
_MIXED_EN = re.compile(r"\bmixed\b|no net vote", re.I)
_TIGHT_EN = re.compile(r"conditions\s+tightening|\btilting\s+tightening\b", re.I)
_EASY_EN = re.compile(r"conditions\s+(?:tilting\s+)?easing", re.I)
_CONTRAST_EN = re.compile(
    r"^(?:but|yet|though|although|however|unless|while|not)\b",
    re.I,
)
# ZH mirrors EN: unless→除非; however→不过/但是/可是; though/although→虽然/尽管;
# yet/but→但/然而/却/反而; not/cannot/has not→没有/不/并非/无法/未能/并未/尚未;
# 只是 is the ZH twin of a contrastive "just/only" remainder.
_CONTRAST_ZH = re.compile(
    r"^(?:不过|但是|可是|虽然|尽管|然而|除非|并非|没有|无法|未能|并未|尚未|只是|反而|但|却|不)"
)
_LEAD_PUNCT = re.compile(r"^[,;:，。、；：—–\s]+")


def posture_lane(posture: str | None) -> tuple[str, str]:
    """Playbook dial posture → doctrine §3 lane.

    Each china_playbook posture has its own ratified lane. A genuinely
    unknown/unmapped string routes to the cautious lane (never a raw slug,
    never a bullish word).
    """
    lab = str(posture).strip() if posture else ""
    if not lab:
        return CAUTIOUS_LANE
    hit = POSTURE_LANE.get(lab)
    if hit:
        return hit
    already = _FACE_LANE_BY_EN.get(lab)
    if already:
        return already
    return CAUTIOUS_LANE


def posture_tone(posture: str | None) -> str:
    """Semantic ink class for the stance chip: up / warn / down."""
    lab = str(posture).strip() if posture else ""
    return _POSTURE_TONE.get(lab, "warn")


def _zh_chars(s: str) -> int:
    return len([c for c in s if not c.isspace() and c not in "—–-,，。、；;：:·"])


def _en_words(s: str) -> list[str]:
    return s.replace("—", " — ").replace("–", " – ").split()


def _remainder_inverts(dropped: list[str], *, zh: bool = False) -> bool:
    """True if a dropped segment opens with a contrastive/negating connective.

    Keeping the leading clause would invert the meaning (the negation lives
    in the dropped tail). Caller then returns worded-empty.
    """
    cue = _CONTRAST_ZH if zh else _CONTRAST_EN
    for part in dropped:
        s = _LEAD_PUNCT.sub("", (part or "").strip())
        if s and cue.match(s):
            return True
    return False


def _clamp_en(s: str, budget: int = _EN_WORD_BUDGET) -> str:
    """Keep whole clauses that fit the word budget; never amputate mid-clause.

    If even the first comma/em-dash/semicolon segment exceeds the budget,
    return "" so the caller can fall back to the worded-empty face. If a
    dropped remainder opens with a contrastive connective, also return "" —
    the surviving clause would invert the sentence.
    """
    text = (s or "").strip()
    if not text:
        return ""
    if len(_en_words(text)) <= budget:
        return text
    parts = re.split(r"(?<=[,;:—–])\s+", text)
    acc: list[str] = []
    for part in parts:
        trial = " ".join(acc + [part]) if acc else part
        if len(_en_words(trial)) <= budget:
            acc.append(part)
        else:
            break
    if not acc:
        return ""
    dropped = parts[len(acc):]
    if _remainder_inverts(dropped, zh=False):
        return ""
    out = " ".join(acc).rstrip(" .,;:—–")
    if not out:
        return ""
    if out[-1] not in ".!?":
        out += "."
    return out


def _clamp_zh(s: str, budget: int = _ZH_CHAR_BUDGET) -> str:
    """Keep whole ZH clauses that fit; never amputate mid-clause.

    A dropped remainder that opens with a contrastive/negating connective
    (the ZH mirror of `_CONTRAST_EN`) inverts the surviving clause —
    return "" (worded-empty) instead. A connective inside the kept
    portion does not void.
    """
    compact = (s or "").strip()
    if not compact:
        return ""
    if _zh_chars(compact) <= budget:
        return compact
    parts = re.split(r"(?<=[，。；：、—–])", compact)
    acc: list[str] = []
    for part in parts:
        trial = "".join(acc + [part])
        if _zh_chars(trial) <= budget:
            acc.append(part)
        else:
            break
    if not acc:
        return ""
    dropped = parts[len(acc):]
    if _remainder_inverts(dropped, zh=True):
        return ""
    out = "".join(acc).rstrip("，。、；：—–")
    if not out:
        return ""
    if out[-1] not in "。！？":
        out += "。"
    return out


def _strip_banned(s: str) -> str:
    out = s
    for tok in _BANNED_G3:
        out = out.replace(tok, "")
    return " ".join(out.split())


def _leg_counts(r_en: str, r_zh: str) -> tuple[int | None, int | None]:
    """Parse n, m from a producer parenthetical. Slash form or count-only form."""
    hit = _LEGS_EN.search(r_en or "")
    if hit:
        return int(hit.group(1)), int(hit.group(2))
    hit = _LEGS_EN_OF.search(r_en or "")
    if hit:
        return int(hit.group(1)), int(hit.group(2))
    hit = _LEGS_ZH.search(r_zh or "")
    if hit:
        return int(hit.group(1)), int(hit.group(2))
    hit = _LEGS_ZH_OF.search(r_zh or "")
    if hit:
        # 「（m项中n项）」 — first number is the denominator.
        return int(hit.group(2)), int(hit.group(1))
    return None, None


def _available_m(r_en: str, r_zh: str) -> int | None:
    """Parsed input count: n/m legs, else mixed easing/tightening/neutral sum."""
    _n, m = _leg_counts(r_en, r_zh)
    if m is not None:
        return m
    hit = _MIXED_COUNTS_EN.search(r_en or "")
    if hit:
        return int(hit.group(1)) + int(hit.group(2)) + int(hit.group(3))
    return None


def _agree_level(n: int | None, m: int | None) -> str:
    """Parsed-count agreement contract.

    n==m with m>=2 → unanimous; n*2 > m and n < m (m>=2) → majority;
    plurality that is not a majority, 1/1, n>m, and parse-fail → none.
    """
    if n is None or m is None or m < 2:
        return "none"
    if n == m:
        return "unanimous"
    if n * 2 > m and n < m:
        return "majority"
    return "none"


def _leg_count_paren(n: int, m: int) -> tuple[str, str]:
    """User-facing n/m parenthetical. 'agree'/同意 only at majority/unanimity."""
    if _agree_level(n, m) in ("majority", "unanimous"):
        return (f"({n}/{m} legs agree)", f"（{n}/{m}项指标同意）")
    return (f"({n} of {m} legs)", f"（{m}项中{n}项）")


def _money_tips(m: int | None, level: str) -> tuple[str, str]:
    """Parameterize the LENS tip by parsed m. Never hardcode 'Three inputs'."""
    if m is None or m < 1:
        if level == "mixed":
            return (
                "The available monetary-conditions inputs do not agree. "
                "Counted once, as a single monetary-conditions read; no net vote.",
                "可用的货币条件输入方向不一，合并为一次货币条件读数；无净投票。",
            )
        return (
            "Counted once, as a single monetary-conditions read.",
            "合并为一次货币条件读数。",
        )
    unit_en = "input" if m == 1 else "inputs"
    head_en = f"{m} {unit_en}"
    head_zh = f"{m}项输入"
    if level == "unanimous":
        return (
            f"{head_en} — all point the same way. Counted once, as a "
            "single monetary-conditions read.",
            f"{head_zh}——方向一致，合并为一次货币条件读数。",
        )
    if level == "majority":
        return (
            f"{head_en} — most point the same way. Counted once, as a "
            "single monetary-conditions read.",
            f"{head_zh}——多数方向一致，合并为一次货币条件读数。",
        )
    if level == "mixed":
        return (
            f"{head_en} — they do not agree. Counted once, as a single "
            "monetary-conditions read; no net vote.",
            f"{head_zh}——方向不一，合并为一次货币条件读数；无净投票。",
        )
    return (
        f"{head_en} — counted once, as a single monetary-conditions read.",
        f"{head_zh}——合并为一次货币条件读数。",
    )


def _agree_bits(n: int | None, m: int | None) -> tuple[str, str, str, str]:
    """Bind the agreement clause to parsed n/m. Missing or non-majority → none."""
    level = _agree_level(n, m)
    tip_en, tip_zh = _money_tips(m, level)
    if level == "unanimous":
        return (
            "and every part of that read agrees.",
            "该判读的各个部分方向一致。",
            tip_en,
            tip_zh,
        )
    if level == "majority":
        return (
            "and most of that read agrees.",
            "该判读的多数方向一致。",
            tip_en,
            tip_zh,
        )
    return ("", "", tip_en, tip_zh)


def _money_kind(sign: str, r_en: str, r_zh: str) -> str:
    """Honour an explicit +/-/i sign before free-text mixed/tight/easy regexes."""
    sig = (sign or "").strip()
    if sig in ("+", "-", "−"):
        return "easy" if sig == "+" else "tight"
    if sig in ("i", "ℹ") or _MIXED_EN.search(r_en) or "分歧" in r_zh or "无净投票" in r_zh:
        return "mixed"
    if _TIGHT_EN.search(r_en) or "趋紧" in r_zh:
        return "tight"
    if _EASY_EN.search(r_en) or "趋宽" in r_zh:
        return "easy"
    return "mixed"


def _money_face(sign: str, r_en: str, r_zh: str) -> dict:
    kind = _money_kind(sign, r_en, r_zh)
    n, m_legs = _leg_counts(r_en, r_zh)
    m = _available_m(r_en, r_zh)
    if kind == "mixed":
        face = dict(_FACE_MONEY_MIXED)
        tip_en, tip_zh = _money_tips(m, "mixed")
        face["tip_en"] = tip_en
        face["tip_zh"] = tip_zh
        return face
    agree_en, agree_zh, tip_en, tip_zh = _agree_bits(n, m_legs)
    if kind == "easy":
        if agree_en:
            en = f"Money is getting easier at the central bank, {agree_en}"
            zh = f"央行层面的货币条件正在放松，{agree_zh}"
        else:
            en = "Money is tilting easier at the central bank."
            zh = "央行层面的货币条件正在趋宽。"
        return {"sign": "+", "en": en, "zh": zh, "tip_en": tip_en, "tip_zh": tip_zh}
    if agree_en:
        en = f"Money is getting tighter at the central bank, {agree_en}"
        zh = f"央行层面的货币条件正在收紧，{agree_zh}"
    else:
        en = "Money is tilting tighter at the central bank."
        zh = "央行层面的货币条件正在趋紧。"
    return {"sign": "−", "en": en, "zh": zh, "tip_en": tip_en, "tip_zh": tip_zh}


def _empty_face(tip_en: str = "", tip_zh: str = "") -> dict:
    face = dict(EMPTY_REASON)
    if tip_en:
        face["tip_en"] = tip_en
    if tip_zh:
        face["tip_zh"] = tip_zh
    return face


def _axes_disagree(posture: str, ms: dict) -> bool:
    color = str((ms or {}).get("color") or "").strip().lower()
    if posture in _BULLISH_POSTURES and color == "red":
        return True
    if posture in _BEARISH_POSTURES and color == "green":
        return True
    return False


def _reconcile_clause(posture: str) -> tuple[str, str]:
    lane_en, lane_zh = posture_lane(posture)
    return (
        f"The tape and the playbook disagree — stance is {lane_en}. "
        "Honour both reads; the tape line is context — act on the posture, not the wording.",
        f"盘面与策略姿态不一致——姿态是{lane_zh}。两边都要看，行情线是背景——按姿态操作，而非按措辞。",
    )


def _unpack_reason(item) -> tuple[str, str, str]:
    sign, r_en, r_zh = "", "", ""
    if isinstance(item, (list, tuple)) and len(item) >= 3:
        sign, r_en, r_zh = item[0], item[1] or "", item[2] or ""
    elif isinstance(item, dict):
        sign = item.get("sign") or ""
        r_en = item.get("en") or item.get("r_en") or ""
        r_zh = item.get("zh") or item.get("r_zh") or ""
    return str(sign), r_en, r_zh


def _face_one(item) -> dict:
    sign, r_en, r_zh = _unpack_reason(item)
    if "Growth-scare" in r_en or "contrarian bottom" in r_en or "增长恐慌是实测" in r_zh:
        face = dict(_FACE_GROWTH)
    elif "PBoC monetary" in r_en or "央行货币" in r_zh:
        face = _money_face(sign, r_en, r_zh)
    elif "Margin leverage crowded" in r_en or "融资杠杆拥挤" in r_zh:
        face = dict(_FACE_MARGIN_CROWDED)
    elif "Margin leverage capitulated" in r_en or "融资杠杆已出清" in r_zh:
        face = dict(_FACE_MARGIN_WASHED)
    else:
        en = _clamp_en(_strip_banned(r_en))
        zh = _clamp_zh(_strip_banned(r_zh))
        if not en and not zh:
            return _empty_face(r_en, r_zh)
        ic = "+" if sign == "+" else ("−" if sign in ("-", "−") else "ℹ")
        face = {
            "sign": ic,
            "en": en or EMPTY_REASON["en"],
            "zh": zh or EMPTY_REASON["zh"],
            "tip_en": r_en or EMPTY_REASON["tip_en"],
            "tip_zh": r_zh or EMPTY_REASON["tip_zh"],
            "empty": not bool(en and zh),
        }
        return face
    face["empty"] = False
    return face


def reason_faces(reasons=None, n: int = 3) -> list[dict]:
    """First n playbook reasons → glance faces; missing slots get §9.12 empty.

    Dedupe on producer identity (sign, en, zh), not the rendered face, so two
    distinct reasons that both clamp to worded-empty still occupy two slots
    and a later reason is not promoted into the visible top-n.
    """
    out: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for item in list(reasons or []):
        key = _unpack_reason(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(_face_one(item))
        if len(out) >= n:
            break
    while len(out) < n:
        out.append(dict(EMPTY_REASON))
    return out


def _hero_fallback(pb: dict) -> tuple[str, str]:
    """C2 path: the clause a lane uses when it has no headline of its own."""
    progress = pb.get("progress") or {}
    qm = pb.get("quad_meaning") or {}
    meaning_en = qm.get("en") or ""
    meaning_zh = qm.get("zh") or ""
    phase = progress.get("phase")
    if phase == "mid" and (
        "Growth-scare" in meaning_en or "增长恐慌" in meaning_zh
    ):
        return _MID_SCARE_CLAUSE
    note_en = (progress.get("phase_note") or "").strip()
    if note_en:
        zh = (progress.get("phase_note_zh") or "").strip()
        return (note_en, zh or EMPTY_CLAUSE[1])
    if meaning_en:
        en = _clamp_en(meaning_en, 28)
        zh = _clamp_zh(meaning_zh, 40) if meaning_zh else ""
        if en:
            return (en, zh or EMPTY_CLAUSE[1])
        return EMPTY_CLAUSE
    return EMPTY_CLAUSE


def hero_clause(pb: dict | None, ms: dict | None = None) -> tuple[str, str]:
    """Plain clause under the h1. Producer headline, else playbook phase+quad.

    When the tape and the playbook disagree, render the headline AND the
    reconciliation together so the clause refers to a headline the user can
    see. Gated per lane: EN reconciliation only with a non-empty head_en;
    ZH reconciliation only with a non-empty head_zh. A lane without a
    headline falls through to that lane's mid-scare/empty clause.
    """
    ms = ms or {}
    pb = pb or {}
    posture = ""
    dial = pb.get("dial") or {}
    if isinstance(dial, dict):
        posture = str(dial.get("posture") or "").strip()
    head_en = (ms.get("headline_en") or "").strip()
    head_zh = (ms.get("headline_zh") or "").strip()
    disagree = _axes_disagree(posture, ms)
    rec_en, rec_zh = _reconcile_clause(posture) if disagree else ("", "")
    fb_en, fb_zh = _hero_fallback(pb)
    if head_en:
        en = f"{head_en} {rec_en}" if rec_en else head_en
    else:
        en = fb_en
    if head_zh:
        zh = f"{head_zh}{rec_zh}" if rec_zh else head_zh
    else:
        zh = fb_zh
    return (en, zh)


def plain_gross_band(gross: float | None) -> tuple[str, str]:
    """Suggested-size face from rd.gross. ¾ is the 0.70–0.85 snapshot band only."""
    if gross is None:
        return ("", "")
    g = float(gross)
    if 0.70 <= g <= 0.85:
        return ("¾ of normal", "约常规四分之三")
    if 0.45 <= g < 0.70:
        return ("half of normal", "约常规一半")
    return (f"×{g:.2f} of normal", f"常规的 {g:.2f} 倍")
