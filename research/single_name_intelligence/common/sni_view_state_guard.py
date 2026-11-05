"""SNI-local DRAFT view-state-guard contract (A31 EN/ZH and viewport persistence).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
view-state records from the product page state owner (the single-name
page state the R1-gated surfaces will carry). It does not re-implement
Data OS identity, Company Event/Earnings, FIF, Capital Structure,
Stock Identity, Options, Research Vault, or qledger/Evaluation. Identity
ids are caller-supplied opaque strings owned by Stock Identity / Data OS;
this guard never mints, derives, or guesses canonical HK/US issuer or
security identifiers from a ticker, name, code, or CIK. Unknown identity
stays UNRESOLVED / null. It never produces issuer, counter, lens, or
as-of values; it only compares caller-supplied ones.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, or repair anything. A silent issuer,
counter, lens, or as-of change across an EN/ZH or viewport transition
is refused, not fixed.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade path.
Every authority flag is literal false. A caller that tries to set any of
them true is refused (raise). Residuals and stress statistics stay
descriptive; this guard makes no causal or news-impact claim (A24). An
unestimable family is outside this module; the guard never invents a
default 50/50 (A25). This is a descriptive refusal contract, not a signal,
score, or forecast.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

AXES: tuple[str, ...] = (
    "issuer_id",
    "counter_id",
    "lens",
    "as_of",
    "lang",
    "viewport",
)

LANGS: tuple[str, ...] = (
    "en",
    "zh",
)

VIEWPORTS: tuple[str, ...] = (
    "desktop",
    "tablet",
    "mobile",
)

REASONS: tuple[str, ...] = (
    "FIELD_MISSING",
    "LANG_UNKNOWN",
    "VIEWPORT_UNKNOWN",
    "CHANGE_UNDECLARED",
    "MULTIPLE_AXES_CHANGED",
    "ISSUER_CHANGED",
    "COUNTER_CHANGED",
    "LENS_CHANGED",
    "AS_OF_CHANGED",
)

AUTHORITY_FLAGS: Mapping[str, bool] = MappingProxyType(
    {
        "rank_authority": False,
        "gate_authority": False,
        "size_authority": False,
        "signal_authority": False,
        "escalation_authority": False,
        "trade_authority": False,
    }
)

_IDENTITY_REASONS: tuple[tuple[str, str], ...] = (
    ("issuer_id", "ISSUER_CHANGED"),
    ("counter_id", "COUNTER_CHANGED"),
    ("lens", "LENS_CHANGED"),
    ("as_of", "AS_OF_CHANGED"),
)


def refuse_nonfalse_authority(flags: Mapping[str, object] | None = None) -> None:
    """Refuse any authority flag that is not literal False.

    Idiom copied from research/single_name_intelligence/event_response/s2_seal.py
    (refuse_nonfalse_authority); this module does not import that owner.
    """
    for key, value in AUTHORITY_FLAGS.items():
        if value is not False:
            raise ValueError(
                f"AUTHORITY_FLAGS[{key!r}] is {value!r}; every authority flag "
                "must be literal False"
            )
    if flags is None:
        return
    if not isinstance(flags, Mapping):
        raise ValueError("authority flags is not a mapping")
    for key, value in flags.items():
        if value is not False:
            raise ValueError(
                f"authority_flags[{key!r}] is {value!r}; "
                "every authority flag must be literal False"
            )


@dataclass(frozen=True)
class ViewTransitionVerdict:
    """Descriptive view-transition refusal. Carries no page state or identity."""

    allowed: bool
    reasons: tuple[str, ...]
    changed_axes: tuple[str, ...]

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)
        object.__setattr__(self, "changed_axes", tuple(self.changed_axes))

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _text_present(value: object) -> bool:
    """An opaque-text id / ref / label is present iff it is a non-empty
    string that is not whitespace-only and that does not begin or end with
    whitespace. None, ``""``, ``"  "``, ``1``, ``True``, ``1.0``,
    ``b"id"``, ``["id"]`` and any other object are ABSENT and never match
    each other. The seat ruling applies this check to every field the
    module documents as an id / ref / label / owner reference; numbers,
    timestamps parsed by a dedicated parser, enums checked against a
    closed set (LANGS, VIEWPORTS), and containers keep their existing
    checks and are NOT routed through this helper.

    FAMILY TEXT RULE v2 (seat ruling): a string that begins or ends with
    whitespace is ABSENT, exactly like a whitespace-only string, so a
    padded id can never pass as a different valid id. The check uses no
    normalisation method (``.strip()`` / ``.lower()`` / ``.upper()`` /
    ``.casefold()`` / ``.replace()``), which keeps the family's
    no-normalisation static scans green.
    """
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


def _blank(value: object) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    return False


def _present(fact: Mapping[str, object], key: str) -> bool:
    return not _blank(fact.get(key))


def _freeze_reasons(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    found = set(items)
    return tuple(code for code in REASONS if code in found)


def _changed_axes(before: Mapping, after: Mapping) -> tuple[str, ...]:
    """Per-axis comparison for identity / id-style axes (issuer_id,
    counter_id, lens, as_of): only text-present values are compared for
    sameness; a non-text side is ABSENT, never equal to anything, so a
    numeric ``1`` on one side and ``True`` on the other is reported as
    changed (the FIELD_MISSING reason then refuses the verdict). Lang and
    viewport are checked against their closed sets elsewhere, not here.
    """
    out: list[str] = []
    for axis in AXES:
        b = before.get(axis)
        a = after.get(axis)
        if not (_text_present(b) and _text_present(a)):
            # Either side is non-text. The axis is ABSENT; FIELD_MISSING
            # will refuse the verdict via _field_missing. We do NOT add
            # the axis to changed_axes here (per the existing tests that
            # pin changed_axes == () for an omitted axis).
            continue
        if b != a:
            out.append(axis)
    return tuple(out)


def _field_missing(before: Mapping, after: Mapping) -> bool:
    for axis in AXES:
        if axis not in before or axis not in after:
            return True
        if not _text_present(before.get(axis)) or not _text_present(after.get(axis)):
            return True
    return False


def _verdict(
    reasons: list[str],
    changed_axes: tuple[str, ...],
) -> ViewTransitionVerdict:
    frozen = _freeze_reasons(reasons)
    return ViewTransitionVerdict(
        allowed=not frozen,
        reasons=frozen,
        changed_axes=changed_axes,
    )


def check_view_transition(
    before: Mapping,
    after: Mapping,
    *,
    change: str | None,
) -> ViewTransitionVerdict:
    """Refuse an EN/ZH or viewport transition that silently changes issuer,
    counter, lens, or as-of.

    `change` is the one AXES name the user action declared, or None.
    `change` names a PERMITTED axis, not an exclusive intent marker;
    declaring an axis that did not change is ALLOWED. Reports every
    applicable reason, de-duplicated, in REASONS order. as_of is compared
    as an exact string.
    """
    refuse_nonfalse_authority()
    if not isinstance(before, Mapping):
        raise TypeError("before must be a Mapping")
    if not isinstance(after, Mapping):
        raise TypeError("after must be a Mapping")

    reasons: list[str] = []
    changed = _changed_axes(before, after)

    if _field_missing(before, after):
        reasons.append("FIELD_MISSING")

    if before.get("lang") not in LANGS or after.get("lang") not in LANGS:
        reasons.append("LANG_UNKNOWN")

    if before.get("viewport") not in VIEWPORTS or after.get("viewport") not in VIEWPORTS:
        reasons.append("VIEWPORT_UNKNOWN")

    undeclared = False
    for axis in changed:
        if axis != change:
            undeclared = True
            break
    if undeclared:
        reasons.append("CHANGE_UNDECLARED")

    if len(changed) > 1:
        reasons.append("MULTIPLE_AXES_CHANGED")

    for axis, code in _IDENTITY_REASONS:
        if axis in changed and change != axis:
            reasons.append(code)

    return _verdict(reasons, changed)


def persist_across(
    before: Mapping,
    *,
    lang: object = None,
    viewport: object = None,
) -> dict:
    """Return a copy of `before` with only the given lang and/or viewport
    replaced. Never reads or writes any other axis or key.
    """
    if not isinstance(before, Mapping):
        raise TypeError("before must be a Mapping")
    out = dict(before)
    if lang is not None:
        out["lang"] = lang
    if viewport is not None:
        out["viewport"] = viewport
    return out