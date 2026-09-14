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
  - ``engine/policy_calendar.py``              — reg_stage + entity-list themes
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

# ZH display names for each event class — plain-Word copy used by the
# valuation panel's bilingual line. Keys are EN source-of-truth labels
# (the keys of the three source maps); values are the ZH display name. The
# bridge looks them up when the class is one of the special-situations
# categories; for SEC and policy kinds, the bridge returns the EN key
# verbatim in both languages (no ZH translation exists in the repo).
_EVENT_CLASS_ZH: dict[str, str] = {
    "Acquisitions":        "收购",
    "Divestitures":        "剥离",
    "Activist Campaigns":  "维权行动",
    "Strategic Reviews":   "战略评估",
    "Tender Offers":       "要约收购",
    "Going-Private":       "私有化",
    "Capital Returns":     "资本回报",
    "Spin-Offs":           "分拆上市",
    "Rights Offerings":    "配股发行",
    "Restructuring":       "重组",
    "Liquidations":        "清算",
    "Delistings":          "退市",
    "Issuer Tenders":      "发行人要约",
    "Deal Terminations":   "交易终止",
    "SPACs":               "特殊目的收购公司",
    "Management Changes":  "管理层变更",
    "Other":               "其他",
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
# ---------------------------------------------------------------------------
SPECIAL_SITUATIONS_TO_ASSUMPTION: dict[str, tuple[str, str, str] | None] = {
    # growth — fresh top-line is the directional read
    "Acquisitions":       (GROWTH, *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    "Spin-Offs":          (GROWTH, *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    "SPACs":              (GROWTH, *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    "Activist Campaigns": (GROWTH, *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    "Strategic Reviews":  (GROWTH, *_direction_words(_EN_LIFTS,    _ZH_LIFTS,    GROWTH)),
    "Divestitures":       (GROWTH, *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  GROWTH)),
    # margin — operating drag is the directional read
    "Restructuring":      (MARGIN, *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  MARGIN)),
    "Capital Returns":    (MARGIN, *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  MARGIN)),
    "Liquidations":       (MARGIN, *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  MARGIN)),
    "Deal Terminations":  (MARGIN, *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  MARGIN)),
    "Management Changes": (MARGIN, *_direction_words(_EN_PRESSES,  _ZH_PRESSES,  MARGIN)),
    # multiple — premium / exit pricing is the directional read
    "Tender Offers":      (MULTIPLE, *_direction_words(_EN_LIFTS,   _ZH_LIFTS,    MULTIPLE)),
    "Going-Private":      (MULTIPLE, *_direction_words(_EN_LIFTS,   _ZH_LIFTS,    MULTIPLE)),
    "Delistings":         (MULTIPLE, *_direction_words(_EN_LIFTS,   _ZH_LIFTS,    MULTIPLE)),
    "Issuer Tenders":     (MULTIPLE, *_direction_words(_EN_LIFTS,   _ZH_LIFTS,    MULTIPLE)),
    "Rights Offerings":   (MULTIPLE, *_direction_words(_EN_LIFTS,   _ZH_LIFTS,    MULTIPLE)),
    # "Other" is the catch-all bucket — no clear directional read.
    "Other":              None,
}

# ---------------------------------------------------------------------------
# Source 2: engine.capital_structure.event_spine — SEC event-kind subtypes.
# Only the subtypes with a meaningful directional read are mapped; mechanical
# lifecycle kinds (effectiveness, periodic reports, proxies, prospectus
# filings) return None — no directional read for those event classes.
# ---------------------------------------------------------------------------
EVENT_SPINE_TO_ASSUMPTION: dict[str, tuple[str, str, str] | None] = {
    # New equity issuance under a registration typically funds growth.
    "registration_statement":        (GROWTH,  *_direction_words(_EN_LIFTS,   _ZH_LIFTS,   GROWTH)),
    "automatic_shelf_registration":  (GROWTH,  *_direction_words(_EN_LIFTS,   _ZH_LIFTS,   GROWTH)),
    "registration_amendment":        (GROWTH,  *_direction_words(_EN_LIFTS,   _ZH_LIFTS,   GROWTH)),
    # Post-effective / withdrawal events typically return capital — margin.
    "post_effective_amendment":      (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "automatic_shelf_withdrawal":    (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "withdrawal_request":            (MARGIN,  *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    # Mechanical / informational lifecycle kinds — no directional read.
    "effectiveness_notice":          None,
    "periodic_report":               None,
    "proxy_solicitation":            None,
    "prospectus_filing":             None,
    "insider_transaction":           None,
    "ownership_change":              None,
    "ownership_initial":             None,
}

# ---------------------------------------------------------------------------
# Source 3: engine.policy_calendar — Federal Register reg_stages + themes.
# Sector-level (not issuer-level); directional reads are domain standards
# the bridge owns as plain words. None = no directional read for that kind.
# ---------------------------------------------------------------------------
POLICY_CALENDAR_TO_ASSUMPTION: dict[str, tuple[str, str, str] | None] = {
    "entity_list_update":            (MARGIN, *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "export_control_rule":           (MARGIN, *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "final_rule":                    (MARGIN, *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "proposed_rule":                 (MARGIN, *_direction_words(_EN_PRESSES, _ZH_PRESSES, MARGIN)),
    "request_for_information":       None,
    "notice":                        None,
}

# ---------------------------------------------------------------------------
# Closed (exhaustive) union — every event class the repo already produces.
# Adding a new event class requires an entry in one of the three source maps;
# the union is the public surface.
# ---------------------------------------------------------------------------
EVENT_TO_ASSUMPTION: dict[str, tuple[str, str, str] | None] = {
    **SPECIAL_SITUATIONS_TO_ASSUMPTION,
    **EVENT_SPINE_TO_ASSUMPTION,
    **POLICY_CALENDAR_TO_ASSUMPTION,
}


def bridge(event_class: object) -> dict | None:
    """Map an event class to ``{target, direction_word, direction_word_zh,
    event_class}``, or ``None``.

    Returns ``None`` when the input is not a string, is empty after stripping,
    or is absent from the closed map. The closed map covers every event
    class the repo already produces; classes that fall through are typed
    as ``None`` rather than silently mapped to one of the three targets.
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
    # Hard invariant: every non-None pair targets one of the three F07-2 inputs.
    assert target in ALLOWED_TARGETS, (
        f"target {target!r} not in {sorted(ALLOWED_TARGETS)}"
    )
    return {
        "target": target,
        "direction_word": direction_word_en,
        "direction_word_zh": direction_word_zh,
        "event_class": key,
        "event_class_zh": _EVENT_CLASS_ZH.get(key, key),
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
    """Read-only view of the closed map.

    Used by tests (every entry must satisfy the closed-map invariant) and
    by the build script (so a new event class added to one of the three
    source modules shows up here without extra wiring).
    """
    return dict(EVENT_TO_ASSUMPTION)