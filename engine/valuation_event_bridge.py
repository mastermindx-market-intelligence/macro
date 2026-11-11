"""B-F07-3 — plain-word bridge from a classified event to one of the three
B-F07-2 valuation inputs (growth, margin, multiple), with a single direction
word only.

Pure: no IO, no network, no clock. The map is closed (every event class the
repo already produces maps to either a ``(target, direction_word)`` pair or
a typed null), exhaustive (no event class falls through), and read-only
(the inputs to ``bridge()`` never mutate the map).

Forbidden by construction (F07 do_not_redo):
  - no magnitude
  - no probability
  - no confidence
  - nothing is applied to a valuation input automatically
  - no consensus, no estimates, no price targets

The output only NAMES which of the three F07-2 inputs a freshly-arrived
filing would touch. The user moves the slider; the bridge never moves it.

Event-class sources (closed set, exhaustive):
  - ``engine/special_situations.py``           — MATURE_CATEGORIES (issuer-level)
  - ``engine/capital_structure/event_spine.py`` — SEC form-route subtypes
  - ``engine/policy_calendar.py`` / ``collectors/federal_register.py`` — reg_stages
  (Federal Register policy records are not issuer filings and never populate
  the issuer panel)
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Allowed targets — the three B-F07-2 inputs. Hard-coded; any new target is a
# spec change, not a code change.
# ---------------------------------------------------------------------------
GROWTH = "growth"
MARGIN = "margin"
MULTIPLE = "multiple"
ALLOWED_TARGETS = frozenset({GROWTH, MARGIN, MULTIPLE})

# EN and ZH display names for each event class — plain-word copy used by the
# valuation panel's bilingual line. Keys are EN source-of-truth labels
# (the keys of the three source maps); values are (EN, ZH) display tuples.
_EVENT_CLASS_NAMES: dict[str, tuple[str, str]] = {
    # Special situations (MATURE_CATEGORIES) — ZH is the official display name.
    "Acquisitions":              ("Acquisitions",        "收购"),
    "Divestitures":             ("Divestitures",       "剥离"),
    "Activist Campaigns":        ("Activist Campaigns",  "维权行动"),
    "Strategic Reviews":         ("Strategic Reviews",   "战略评估"),
    "Tender Offers":             ("Tender Offers",       "要约收购"),
    "Going-Private":             ("Going-Private",       "私有化"),
    "Capital Returns":            ("Capital Returns",      "资本回报"),
    "Spin-Offs":                 ("Spin-Offs",           "分拆上市"),
    "Rights Offerings":          ("Rights Offerings",    "配股发行"),
    "Restructuring":             ("Restructuring",       "重组"),
    "Liquidations":              ("Liquidations",        "清算"),
    "Delistings":                ("Delistings",          "退市"),
    "Issuer Tenders":            ("Issuer Tenders",       "发行人要约"),
    "Deal Terminations":         ("Deal Terminations",   "交易终止"),
    "SPACs":                    ("SPACs",               "特殊目的收购公司"),
    "Management Changes":         ("Management Changes",   "管理层变更"),
    "Other":                     ("Other",               "其他"),
    # SEC event-spine subtypes — ZH is the official display name; EN verbatim
    # only where no ZH translation has been established by the desk.
    "registration_statement":           ("Registration Statement",               "登记说明书"),
    "automatic_shelf_registration":    ("Automatic Shelf Registration",         "自动架上登记"),
    "registration_s1":                 ("S-1 Registration Statement",          "S-1 登记说明书"),
    "registration_f1":                 ("F-1 Registration Statement",          "F-1 登记说明书"),
    "registration_s3":                 ("S-3 Shelf Registration",              "S-3 架上登记"),
    "registration_f3":                 ("F-3 Shelf Registration",              "F-3 架上登记"),
    "registration_f10":                ("F-10 Shelf Registration",             "F-10 架上登记"),
    "registration_amendment":          ("Registration Amendment",              "登记修正案"),
    "post_effective_amendment":       ("Post-Effective Amendment",            "生效后修正"),
    "automatic_shelf_withdrawal":      ("Automatic Shelf Withdrawal",          "自动撤回登记"),
    "withdrawal_request":             ("Withdrawal Request",                  "撤回申请"),
    "effectiveness_notice":           ("Effectiveness Notice",                "生效通知"),
    "prospectus_event":               ("Prospectus Event",                    "招股说明书事件"),
    "charter_amendment_candidate":     ("Charter Amendment Candidate",         "章程修正候选"),
    "shareholder_vote_candidate":      ("Shareholder Vote Candidate",          "股东表决候选"),
    "unregistered_equity_sale_candidate": ("Unregistered Equity Sale Candidate","未登记股票发行候选"),
    "financing_agreement_candidate":  ("Financing Agreement Candidate",        "融资协议候选"),
    "current_report_candidate":        ("Current Report Candidate",            "当前报告候选"),
    "authorization_or_vote_candidate": ("Authorization or Vote Candidate",    "授权或表决候选"),
    "offering_statement":             ("Offering Statement",                  "发行说明书"),
    "offering_statement_amendment":   ("Offering Statement Amendment",         "发行说明书修正"),
    "reg_a_event_candidate":          ("Reg A Event Candidate",              "Reg A 事件候选"),
    "periodic_reconciliation_source": ("Periodic Reconciliation Source",       "定期对账来源"),
    "ownership_context_source":        ("Ownership Context Source",            "所有权上下文来源"),
    "unsupported_form":               ("Unsupported Form",                   "不支持的表格"),
    # Federal Register reg_stages — ZH is the official display name.
    "executive_order":      ("Executive Order",    "行政命令"),
    "interim_final_rule":   ("Interim Final Rule","临时最终规则"),
    "final_rule":           ("Final Rule",         "最终规则"),
    "proposed_rule":        ("Proposed Rule",      "拟议规则"),
    "rfi":                  ("Request for Information","信息征集"),
    "funding_notice":       ("Funding Notice",     "资助公告"),
    "notice":               ("Notice",             "公告"),
    # Federal Register entity-list themes (engine/policy_calendar._ENTITY_LIST_THEMES).
    "ai_semiconductors":         ("AI Semiconductors",          "AI芯片"),
    "semicap_equipment":        ("Semiconductor Equipment",     "半导体设备"),
    "rare_earth_critical_min":   ("Rare Earth & Critical Minerals","稀土关键矿产"),
    "memory_storage":            ("Memory & Storage",           "存储"),
}

# Direction-word verbs in EN and ZH. Plain language, no magnitude /
# probability / confidence. "ZH through the ZH formatter" is satisfied by
# the static pair below — no LLM, no runtime translation.
_EN_LIFTS = "usually lifts"
_EN_PRESSES = "usually presses"
_ZH_LIFTS = "通常推升"
_ZH_PRESSES = "通常压缩"

# Suffix variants — growth/margin read as "X growth" / "X margin"; multiple
# reads as "the multiple people pay" so the panel can name the valuation
# axis without committing to a specific earnings multiple.
_EN_GROWTH_SUFFIX = "growth"
_EN_MARGIN_SUFFIX = "margin"
_EN_MULTIPLE_SUFFIX = "the multiple people pay"
_ZH_GROWTH_SUFFIX = "增长"
_ZH_MARGIN_SUFFIX = "利润率"
_ZH_MULTIPLE_SUFFIX = "市盈率倍数"


def _direction_words(verb_en: str, verb_zh: str, target: str) -> tuple[str, str]:
    """Build an (EN, ZH) direction-word pair from a verb + the F07-2 input.

    Growth and margin use the short suffix; multiple uses the descriptive
    suffix ("the multiple people pay" / "市盈率倍数") so the panel can name
    the valuation axis without naming a specific earnings multiple. Raises
    on an unknown target so a typo in any source map cannot silently pass
    the closed-map invariant.
    """
    if target == GROWTH:
        return (f"{verb_en} {_EN_GROWTH_SUFFIX}", f"{verb_zh}{_ZH_GROWTH_SUFFIX}")
    if target == MARGIN:
        return (f"{verb_en} {_EN_MARGIN_SUFFIX}", f"{verb_zh}{_ZH_MARGIN_SUFFIX}")
    if target == MULTIPLE:
        return (
            f"{verb_en} {_EN_MULTIPLE_SUFFIX}",
            f"{verb_zh}{_ZH_MULTIPLE_SUFFIX}",
        )
    raise ValueError(
        f"unknown target {target!r}; allowed={sorted(ALLOWED_TARGETS)}"
    )


# ---------------------------------------------------------------------------
# Source 1: engine.special_situations — MATURE_CATEGORIES.
# Canonical issuer-level event classes the desk promotes.
#
# Semantic basis:
#   - Acquisitions / Spin-Offs / SPACs / Activist / Strategic Review → growth
#     (fresh top-line or re-rating catalyst)
#   - Divestitures → growth (spin-off or partial sale lifts per-share economics)
#   - Restructuring / Liquidations / Deal Terminations / Management Changes → margin
#     (operating drag reduction or cost action)
#   - Capital Returns (buybacks) → per-share lift via lower share count, NOT margin
#     → maps to GROWTH (per-share re-rating)
#   - Tender Offers / Going-Private / Issuer Tenders → multiple
#     (takeout premium / exit pricing)
#   - Rights Offerings → multiple (dilutive; new shares at discount presses per-share)
#   - Delistings → typed null (Form 25 regulatory exit, no clear directional read)
#   - Other → typed null
# ---------------------------------------------------------------------------
SPECIAL_SITUATIONS_TO_ASSUMPTION: dict[str, tuple[str, str, str] | None] = {
    # growth — fresh top-line or per-share re-rating
    "Acquisitions":       (GROWTH,  *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    "Spin-Offs":          (GROWTH,  *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    "SPACs":              (GROWTH,  *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    "Activist Campaigns": (GROWTH, *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    "Strategic Reviews":  (GROWTH,  *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    "Divestitures":       (GROWTH,  *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    # margin — operating drag reduction
    "Restructuring":      (MARGIN,  *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  MARGIN)),
    "Liquidations":       (MARGIN,  *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  MARGIN)),
    "Deal Terminations":  (MARGIN,  *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  MARGIN)),
    "Management Changes":  (MARGIN,  *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  MARGIN)),
    # multiple — takeout premium / exit / dilutive
    "Tender Offers":      (MULTIPLE, *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    MULTIPLE)),
    "Going-Private":      (MULTIPLE, *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    MULTIPLE)),
    # Delistings: Form 25 delistings are regulatory exits, not takeout premia.
    # Honest read = no clear directional read → typed null.
    "Delistings":        None,
    "Issuer Tenders":    (MULTIPLE, *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    MULTIPLE)),
    # Rights Offerings: dilutive — new shares at a discount press per-share value.
    "Rights Offerings":  (MULTIPLE, *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  MULTIPLE)),
    # Capital Returns (buybacks): per-share lift via lower share count → GROWTH.
    # The lift is a per-share re-rating, not a margin press.
    "Capital Returns":   (GROWTH,   *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    # "Other" is the catch-all bucket — no clear directional read.
    "Other":              None,
}

# ---------------------------------------------------------------------------
# Source 2: engine.capital_structure.event_spine — SEC form-route subtypes.
# Keys are exactly the subtype strings returned by route_form() (lines 167-249).
# Only subtypes with a meaningful directional read are mapped; mechanical
# lifecycle kinds (effectiveness_notice, periodic_reconciliation_source, etc.)
# return None — no directional read for informational filings.
# ---------------------------------------------------------------------------
EVENT_SPINE_TO_ASSUMPTION: dict[str, tuple[str, str, str] | None] = {
    # New equity issuance under a registration typically funds growth.
    "registration_statement":          (GROWTH,  *_direction_words(_EN_LIFTS,   _ZH_LIFTS,   GROWTH)),
    "automatic_shelf_registration":   (GROWTH,  *_direction_words(_EN_LIFTS,   _ZH_LIFTS,   GROWTH)),
    "registration_amendment":         (GROWTH,  *_direction_words(_EN_LIFTS,   _ZH_LIFTS,   GROWTH)),
    # Post-effective amendments and withdrawals return capital — no growth press.
    "post_effective_amendment":       (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "automatic_shelf_withdrawal":     (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "withdrawal_request":             (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    # Mechanical / lifecycle kinds — no directional read.
    "effectiveness_notice":            None,
    "prospectus_event":                None,
    "charter_amendment_candidate":     None,
    "shareholder_vote_candidate":      None,
    "unregistered_equity_sale_candidate": None,
    "financing_agreement_candidate":  None,
    "current_report_candidate":        None,
    "authorization_or_vote_candidate": None,
    "offering_statement":              None,
    "offering_statement_amendment":   None,
    "reg_a_event_candidate":           None,
    "periodic_reconciliation_source":  None,
    "ownership_context_source":        None,
    "unsupported_form":                None,
}

# ---------------------------------------------------------------------------
# Source 3a: collectors.federal_register — Federal Register reg_stages.
# Keys are the canonical reg_stage strings from _STAGE_WEIGHTS (lines 60-70).
# Domain standards — directional reads are owned here as plain words.
# None = no actionable directional read for valuation.
# ---------------------------------------------------------------------------
POLICY_CALENDAR_TO_ASSUMPTION: dict[str, tuple[str, str, str] | None] = {
    # Executive orders are sector-wide macro events — press margin (cost/mandate).
    "executive_order":     (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    # Interim final rules have immediate force — press margin.
    "interim_final_rule": (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    # Final rules are enacted regulation — press margin.
    "final_rule":         (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    # Proposed rules signal future compliance cost — press margin.
    "proposed_rule":      (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    # RFIs are information-gathering; no directional read.
    "rfi":                None,
    # Funding notices signal grant/contract opportunity — press margin.
    "funding_notice":     (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    # General notices carry no specific directional read.
    "notice":             None,
}

# ---------------------------------------------------------------------------
# Source 3b: engine/policy_calendar — Federal Register entity-list themes.
# Keys are the canonical theme strings from _ENTITY_LIST_THEMES.
# All four themes are macro-sector reg events — press margin.
# ---------------------------------------------------------------------------
_ENTITY_LIST_THEMES_TO_ASSUMPTION: dict[str, tuple[str, str, str] | None] = {
    # ai_semiconductors, semicap_equipment, rare_earth_critical_min, memory_storage
    # — macro-sector compliance/permitting events → press margin.
    "ai_semiconductors":        (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "semicap_equipment":        (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "rare_earth_critical_min":  (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "memory_storage":           (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
}

# ---------------------------------------------------------------------------
# Closed (exhaustive) union — every event class the repo already produces.
# ---------------------------------------------------------------------------
EVENT_TO_ASSUMPTION: dict[str, tuple[str, str, str] | None] = {
    **SPECIAL_SITUATIONS_TO_ASSUMPTION,
    **EVENT_SPINE_TO_ASSUMPTION,
}

POLICY_EVENT_TO_ASSUMPTION: dict[str, tuple[str, str, str] | None] = {
    **POLICY_CALENDAR_TO_ASSUMPTION,
    **_ENTITY_LIST_THEMES_TO_ASSUMPTION,
}


def bridge(event_class: object) -> dict | None:
    """Map an event class to ``{target, direction_word, direction_word_zh,
    event_class}``, or ``None``.

    Returns ``None`` when the input is not a string, is empty after stripping,
    or is absent from the closed map.
    """
    if not isinstance(event_class, str):
        return None
    key = event_class.strip()
    if not key:
        return None
    pair = EVENT_TO_ASSUMPTION.get(key)
    if pair is None:
        return None
    target, direction_word_en, direction_word_zh = pair
    assert target in ALLOWED_TARGETS, (
        f"target {target!r} not in {sorted(ALLOWED_TARGETS)}"
    )
    names = _EVENT_CLASS_NAMES.get(key, (key, key))
    return {
        "target": target,
        "direction_word": direction_word_en,
        "direction_word_zh": direction_word_zh,
        "event_class": key,
        "event_class_en": names[0],
        "event_class_zh": names[1],
    }


def bridge_for_issuer(latest_event_class: object) -> dict | None:
    """Same as ``bridge()``, but explicitly typed for the panel's "issuer has
    no classified event on file" path. The valuation panel calls this with
    ``None`` (or an empty string) for issuers without a classified event;
    the function returns ``None`` in both cases.
    """
    if latest_event_class is None:
        return None
    return bridge(latest_event_class)


def classified_event_domain() -> dict[str, tuple[str, str, str] | None]:
    """Read-only view of the closed map."""
    return dict(EVENT_TO_ASSUMPTION)
