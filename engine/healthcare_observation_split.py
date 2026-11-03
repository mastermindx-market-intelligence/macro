"""Regulator status, manufacturer availability and capacity as three separate clauses.

The foresight desk row for an FDA-fed theme publishes one chip. One chip cannot say
"the regulator records are current" without also implying whether manufacturers can
supply the molecule, or what capacity is doing. This module splits the three so the
public page never implies a capacity observation it does not have:

  regulator    -> only what the regulator-status tally says
  manufacturer -> only what the manufacturer-availability tally says
  capacity     -> the closed refusal "not observed"; there is no input path to it

Display-only sibling of the chip. Synthetic inputs only: this module does not read
the shortage store, does not call the network, and does not import the scarcity
engine or the theme graph. English halves are ASCII, name only the non-zero words
of their own slot, and never carry a demand, price, rank, size or entry claim.
Chinese halves are separate strings; the two are never on screen at once.
"""
from __future__ import annotations

_REGULATOR_KEYS = ("current", "resolved", "discontinued")
_REGULATOR_EN = {
    "current": "current",
    "resolved": "resolved",
    "discontinued": "discontinued",
}
_REGULATOR_ZH = {
    "current": "当前",
    "resolved": "已解决",
    "discontinued": "停产",
}

_MANUFACTURER_KEYS = ("available", "limited", "unavailable", "not_stated")
_MANUFACTURER_EN = {
    "available": "available",
    "limited": "limited",
    "unavailable": "unavailable",
    "not_stated": "not stated",
}
_MANUFACTURER_ZH = {
    "available": "可供",
    "limited": "供应受限",
    "unavailable": "无供应",
    "not_stated": "未说明",
}

# An unfinished capture publishes no count, in either language.
_REGULATOR_WITHHELD_EN = "regulator: capture incomplete - no counts published"
_REGULATOR_WITHHELD_ZH = "监管状态：采集未完成，不发布计数"
_MANUFACTURER_WITHHELD_EN = "manufacturer: capture incomplete - no counts published"
_MANUFACTURER_WITHHELD_ZH = "厂商供应情况：采集未完成，不发布计数"

# A finished capture that found nothing for this slot says so without naming a word
# of the tally, so a zero is never rendered as if it had been observed.
_REGULATOR_NONE_EN = "regulator: nothing recorded in this observation"
_REGULATOR_NONE_ZH = "监管状态：本次观察无记录"
_MANUFACTURER_NONE_EN = "manufacturer: nothing recorded in this observation"
_MANUFACTURER_NONE_ZH = "厂商供应情况：本次观察无记录"

# The closed refusal. Constant, digit-free, and unreachable by any argument.
CAPACITY_EN = "The capacity thesis is not observed from this source."
CAPACITY_ZH = "产能论断未获观察：该来源不发布产能数据。"


def _counts(value, keys) -> dict:
    """Positive ints for `keys` only; a missing or unreadable entry counts as zero."""
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for key in keys:
        raw = value.get(key)
        if raw is None or isinstance(raw, bool):
            continue
        try:
            number = int(raw)
        except (TypeError, ValueError):
            continue
        if number > 0:
            counts[key] = number
    return counts


def _clause(counts, keys, words_en, words_zh, label_en, label_zh,
            withheld_en, withheld_zh, none_en, none_zh, incomplete) -> dict:
    """One bilingual clause: the slot's own label plus only its non-zero words."""
    if incomplete:
        return {"en": withheld_en, "zh": withheld_zh}
    named = [key for key in keys if key in counts]
    if not named:
        return {"en": none_en, "zh": none_zh}
    return {
        "en": label_en + ": " + ", ".join(
            f"{words_en[key]} {counts[key]}" for key in named
        ),
        "zh": label_zh + "：" + "、".join(
            f"{words_zh[key]}{counts[key]}条" for key in named
        ),
    }


def observation_split_clause(regulator_counts, manufacturer_counts,
                             capture_incomplete=False) -> dict:
    """Split one FDA observation into regulator, manufacturer and capacity clauses.

    `regulator_counts` names the non-zero of current / resolved / discontinued;
    `manufacturer_counts` the non-zero of available / limited / unavailable /
    not_stated. Neither dict crosses into the other slot's sentence. When
    `capture_incomplete` is true both halves fall back to the unpublished form
    and publish no digit at all. Capacity is the same closed refusal either way,
    because no caller can pass a capacity thesis into this function.
    """
    incomplete = bool(capture_incomplete)
    regulator = _clause(
        _counts(regulator_counts, _REGULATOR_KEYS), _REGULATOR_KEYS,
        _REGULATOR_EN, _REGULATOR_ZH, "regulator", "监管状态",
        _REGULATOR_WITHHELD_EN, _REGULATOR_WITHHELD_ZH,
        _REGULATOR_NONE_EN, _REGULATOR_NONE_ZH, incomplete,
    )
    manufacturer = _clause(
        _counts(manufacturer_counts, _MANUFACTURER_KEYS), _MANUFACTURER_KEYS,
        _MANUFACTURER_EN, _MANUFACTURER_ZH, "manufacturer", "厂商供应情况",
        _MANUFACTURER_WITHHELD_EN, _MANUFACTURER_WITHHELD_ZH,
        _MANUFACTURER_NONE_EN, _MANUFACTURER_NONE_ZH, incomplete,
    )
    return {
        "regulator": regulator,
        "manufacturer": manufacturer,
        "capacity": {"en": CAPACITY_EN, "zh": CAPACITY_ZH},
    }
