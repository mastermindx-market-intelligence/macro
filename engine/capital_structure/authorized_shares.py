"""Capital-structure V2 lane C2c-P: authorized-unreserved common-share headroom.

``select_authorized_headroom`` answers exactly one question — how many authorized
common shares are neither issued nor reserved, as of one instant — and nothing
else.  It produces no score, rank, sizing, probability or recommendation, and it
grants no authority: every input must already be context-only.

The law it enforces (masterplan L84/L98/L102, acceptance A19):

* Authorized, issued and reserved share counts are *state quantities* that
  events change.  They are separate observed facts and are never derived from
  outstanding shares; outstanding is never substituted for issued, because
  treasury shares would overstate the pool.
* A split ratio is NEVER applied to authorized, issued or reserved shares.  A
  split that took effect after the chosen instant makes the answer ``unknown``
  rather than scaling it, because a charter's authorized capital need not move
  in proportion to the outstanding count.
* Values from different instants are never combined.  The answer is taken at the
  latest instant where BOTH authorized and issued are clean; if the reserve is
  unreported at that instant the answer is a ceiling, not a number.
* Everything is exact ``Decimal`` arithmetic under a context that traps any
  inexact result.  There is no float anywhere, and every number is published as
  canonical plain decimal text (``1E+9`` is ``1000000000``; ``100.0`` is ``100``).
* Point in time: a record is visible only once it is available and filed on or
  before ``as_of``.  A visible correction supersedes its predecessor even when
  the correction itself reports a later instant.
* Corporate actions arrive as either the ``corporate_actions`` family (dated
  stage records) or the ``events`` family (filed 8-K event candidates).  An
  effective split after the instant, or an unconfirmed charter-amendment event
  filed after it, makes the answer ``unknown``; a vote or authorization event is
  only a note.  Event candidates never confirm that no split took effect, so
  without corporate-action stages the answer stays stated with the condition
  ``corporate_actions_unobserved_since:<instant>``.

Statuses: ``known`` (exact signed headroom), ``shortfall`` (negative headroom —
the reservation exceeds the unissued authorized pool), ``ceiling_only``
(reserved unobserved at the instant), ``unknown`` (a side missing, stale, or an
unscaled split after the instant) and ``contradicted`` (the facts disagree).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, Inexact, InvalidOperation, localcontext
from typing import Any, Mapping, Sequence

from engine.capital_structure.issuer_state_contracts import (
    CorporateActionInputs,
    ShareInputs,
)
from engine.capital_structure.share_basis import (
    AUTHORIZED_CAPITAL_KINDS,
    MAX_BASIS_AGE_DAYS,
    ShareBasisInputError,
    _assert_context_only,
    _available_instant,
    _event_notes,
    _get,
    _nonneg_decimal,
    _parse_date,
    _parse_ts,
    _superseded_ids,
    evaluate_split_actions,
    security_class_id_for,
)

IMPLEMENTATION = "engine.capital_structure.authorized_shares.select_authorized_headroom/1"
COMPILER_VERSION = "capital_structure.authorized_shares/1"
HEADROOM_STATUSES = ("known", "shortfall", "ceiling_only", "unknown", "contradicted")

AUTHORIZED_KIND = "common_shares_authorized"
ISSUED_KIND = "common_shares_issued"
RESERVED_KIND = "common_shares_reserved_for_future_issuance"


class AuthorizedSharesInputError(ValueError):
    """The inputs cannot be judged at all (wrong types, mixed issuers, bad ``as_of``)."""


@dataclass(frozen=True)
class AuthorizedHeadroom:
    """One exact answer about the authorized-unreserved common-share pool."""

    issuer_id: str
    security_class_id: str
    as_of: str
    status: str
    instant: str | None
    authorized: str | None
    issued: str | None
    reserved: str | None
    headroom: str | None
    ceiling: str | None
    observation_ids: tuple[str, ...]
    conditions: tuple[str, ...]
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in HEADROOM_STATUSES:
            raise AuthorizedSharesInputError(f"status {self.status!r} is not a headroom status")
        for label in ("authorized", "issued", "reserved", "headroom", "ceiling"):
            _exact_decimal(getattr(self, label), f"authorized_headroom.{label}")
        if self.status in ("known", "shortfall"):
            if self.authorized is None or self.issued is None or self.reserved is None:
                raise AuthorizedSharesInputError(f"{self.status} headroom requires authorized, issued and reserved")
            if self.headroom is None:
                raise AuthorizedSharesInputError(f"{self.status} headroom requires a signed headroom")
            if self.ceiling is not None:
                raise AuthorizedSharesInputError(f"{self.status} headroom carries no ceiling")
            signed = Decimal(self.headroom)
            if (signed >= 0) is not (self.status == "known"):
                raise AuthorizedSharesInputError("headroom sign disagrees with the status")
        elif self.status == "ceiling_only":
            if self.authorized is None or self.issued is None or self.ceiling is None:
                raise AuthorizedSharesInputError("ceiling_only requires authorized, issued and ceiling")
            if self.reserved is not None or self.headroom is not None:
                raise AuthorizedSharesInputError("ceiling_only carries neither reserved nor headroom")
        elif self.headroom is not None or self.ceiling is not None:
            raise AuthorizedSharesInputError(f"{self.status} headroom carries neither headroom nor ceiling")

    def as_record(self) -> dict[str, Any]:
        """Plain JSON-safe data: strings, lists and ``None``."""

        return {
            "issuer_id": self.issuer_id,
            "security_class_id": self.security_class_id,
            "as_of": self.as_of,
            "status": self.status,
            "instant": self.instant,
            "authorized": self.authorized,
            "issued": self.issued,
            "reserved": self.reserved,
            "headroom": self.headroom,
            "ceiling": self.ceiling,
            "observation_ids": list(self.observation_ids),
            "conditions": list(self.conditions),
            "notes": list(self.notes),
        }


def _exact_decimal(text: Any, label: str) -> None:
    if text is None:
        return
    if not isinstance(text, str):
        raise AuthorizedSharesInputError(f"{label}: exact decimal text required")
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise AuthorizedSharesInputError(f"{label}: not exact decimal text: {text!r}") from exc
    if not parsed.is_finite():
        raise AuthorizedSharesInputError(f"{label}: not a finite decimal: {text!r}")


def _decimal_text(value: Decimal) -> str:
    """Canonical plain decimal text: no exponent, no trailing zeros, never ``-0``."""

    if value == 0:
        return "0"
    # ``normalize()`` would round to the context precision; plain formatting never does.
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _exact(operation: Any) -> Decimal:
    """Run one subtraction in a context where any rounding raises."""

    with localcontext() as ctx:
        ctx.prec = 60
        ctx.traps[Inexact] = True
        return operation()


def _issuer_of_record(record: Mapping[str, Any]) -> str | None:
    issuer = record.get("issuer_id")
    if isinstance(issuer, str) and issuer:
        return issuer
    nested = _get(record, "issuer", "issuer_id")
    return nested if isinstance(nested, str) and nested else None


def _observation_id_of(record: Mapping[str, Any]) -> str:
    return str(record.get("observation_id") or "")


def _clean_value(record: Mapping[str, Any]) -> tuple[Decimal | None, str | None]:
    """One exactly usable value, or the named reason it can never be used."""

    disposition = _get(record, "state", "disposition")
    if disposition != "observed":
        return None, f"{disposition}:{_get(record, 'state', 'reason')}"
    normalized = record.get("normalized") if isinstance(record.get("normalized"), Mapping) else {}
    if normalized.get("unit") != "shares":
        return None, f"unit_mismatch:{normalized.get('unit')}"
    if str(_get(record, "fact", "unit")) != "shares":
        return None, f"unit_mismatch:{_get(record, 'fact', 'unit')}"
    if normalized.get("scale") not in ("1", None):
        return None, f"scale_mismatch:{normalized.get('scale')}"
    value = _nonneg_decimal(normalized.get("value"))
    if value is None:
        return None, "value_not_a_nonnegative_decimal"
    return value, None


def headroom_from_records(
    records: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]] | None,
    *,
    issuer_id: str,
    as_of: str,
    events: Sequence[Mapping[str, Any]] | None = None,
) -> AuthorizedHeadroom:
    """Judge authorized-capital records against one instant.  Pure; never reads a clock.

    ``actions`` are ``corporate_actions``-family stage records and ``events`` are
    ``events``-family filing candidates.  Without corporate-action stages the
    answer carries the condition ``corporate_actions_unobserved_since:<instant>``
    rather than a clean "no split" finding; events can only refuse or annotate.  Every authorized-capital record must name
    its issuer and be context-only; one that claims any authority is refused.
    """

    as_of_at = _parse_ts(as_of)
    if as_of_at is None:
        raise AuthorizedSharesInputError("as_of: timezone-aware ISO timestamp required")
    as_of_text = as_of_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    security_class_id = security_class_id_for(issuer_id)
    notes: list[str] = []
    conditions: list[str] = []

    def _result(
        status: str, *, instant: date | None = None, values: Mapping[str, Decimal | None] | None = None,
        headroom: Decimal | None = None, ceiling: Decimal | None = None,
        observation_ids: Sequence[str] = (),
    ) -> AuthorizedHeadroom:
        resolved = values or {}

        def _text(kind: str) -> str | None:
            value = resolved.get(kind)
            return None if value is None else _decimal_text(value)

        return AuthorizedHeadroom(
            issuer_id=issuer_id,
            security_class_id=security_class_id,
            as_of=as_of_text,
            status=status,
            instant=None if instant is None else instant.isoformat(),
            authorized=_text(AUTHORIZED_KIND),
            issued=_text(ISSUED_KIND),
            reserved=_text(RESERVED_KIND),
            headroom=None if headroom is None else _decimal_text(headroom),
            ceiling=None if ceiling is None else _decimal_text(ceiling),
            observation_ids=tuple(sorted(observation_ids)),
            conditions=tuple(sorted(conditions)),
            notes=tuple(sorted(set(notes))),
        )

    scoped: list[Mapping[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise AuthorizedSharesInputError(f"records[{index}]: mapping required")
        named = _issuer_of_record(record)
        if named is not None and named != issuer_id:
            raise AuthorizedSharesInputError(f"records[{index}]: issuer {named!r} differs from {issuer_id!r}")
        if _get(record, "metric", "kind") in AUTHORIZED_CAPITAL_KINDS:
            if named is None:
                raise AuthorizedSharesInputError(f"records[{index}]: an authorized-capital record must name its issuer")
            try:
                _assert_context_only(record, f"records[{index}]")
            except ShareBasisInputError as exc:
                raise AuthorizedSharesInputError(str(exc)) from exc
            scoped.append(record)

    visible: list[Mapping[str, Any]] = []
    for record in scoped:
        kind = str(_get(record, "metric", "kind"))
        available = _available_instant(record)
        filed = _parse_date(_get(record, "filing", "filed"))
        if available is None or available > as_of_at or (filed is not None and filed > as_of_at.date()):
            notes.append(f"not_yet_available:{kind}")
            continue
        visible.append(record)

    # A visible correction supersedes its predecessor even when the correction
    # itself is later excluded for its instant, so supersession is computed over
    # every visible record before the instant filter.
    superseded = _superseded_ids(visible)
    eligible: list[Mapping[str, Any]] = []
    for record in visible:
        kind = str(_get(record, "metric", "kind"))
        instant = _parse_date(_get(record, "period", "period_end"))
        if instant is None:
            notes.append(f"unclean:{kind}:no_instant")
            continue
        if instant > as_of_at.date():
            notes.append(f"instant_after_as_of:{kind}")
            continue
        eligible.append(record)

    clean: dict[str, dict[date, list[tuple[str, Decimal]]]] = {kind: {} for kind in AUTHORIZED_CAPITAL_KINDS}
    for record in eligible:
        observation_id = _observation_id_of(record)
        if observation_id in superseded:
            continue
        kind = str(_get(record, "metric", "kind"))
        instant = _parse_date(_get(record, "period", "period_end"))
        assert instant is not None
        value, reason = _clean_value(record)
        if value is None:
            notes.append(f"unclean:{kind}:{reason}")
            continue
        clean[kind].setdefault(instant, []).append((observation_id, value))

    authorized_instants = set(clean[AUTHORIZED_KIND])
    issued_instants = set(clean[ISSUED_KIND])
    shared = authorized_instants & issued_instants
    if not shared:
        # Values from different instants are never combined, so a side that
        # exists only at some other instant is unobserved for this answer.
        both_elsewhere = bool(authorized_instants) and bool(issued_instants)
        if both_elsewhere or not authorized_instants:
            notes.append("authorized_unobserved")
        if both_elsewhere or not issued_instants:
            notes.append("issued_unobserved")
        return _result("unknown")

    instant = max(shared)
    if instant < as_of_at.date():
        conditions.append(f"issuance_since_instant_not_reconciled:{instant.isoformat()}")
    values: dict[str, Decimal | None] = {}
    used_ids: list[str] = []
    conflicted = False
    for kind in AUTHORIZED_CAPITAL_KINDS:
        entries = clean[kind].get(instant, ())
        ids = sorted(observation_id for observation_id, _ in entries)
        used_ids.extend(ids)
        distinct = sorted({value for _, value in entries})
        if len(distinct) > 1:
            conflicted = True
            values[kind] = None
            notes.append(f"conflict:{kind}:{'+'.join(ids)}")
        else:
            values[kind] = distinct[0] if distinct else None
    if conflicted:
        return _result("contradicted", instant=instant, values=values, observation_ids=used_ids)

    if (as_of_at.date() - instant).days > MAX_BASIS_AGE_DAYS:
        notes.append(f"stale_instant:{instant.isoformat()}")
        return _result("unknown", instant=instant, values=values, observation_ids=used_ids)

    if actions is None:
        # Event candidates can refuse an answer but never confirm that no split
        # took effect, so only the dated corporate-action stages clear this.
        conditions.append(f"corporate_actions_unobserved_since:{instant.isoformat()}")
    labels: list[str] = []
    try:
        if actions is not None:
            decision = evaluate_split_actions(
                actions, issuer_id=issuer_id, security_class_id=security_class_id,
                count_instant=instant, as_of=as_of_at,
            )
            # A19: a split is never applied to authorized, issued or reserved shares.
            labels.extend(([decision.action_id] if decision.action_id is not None else []) + list(decision.refusals))
        if events is not None:
            event_refusals, event_notes = _event_notes(events, issuer_id=issuer_id, count_instant=instant, as_of=as_of_at)
            labels.extend(event_refusals)
            notes.extend(event_notes)
    except ShareBasisInputError as exc:
        raise AuthorizedSharesInputError(str(exc)) from exc
    for label in labels:
        notes.append(f"split_since_instant_unscaled:{label}")
    if labels:
        return _result("unknown", instant=instant, values=values, observation_ids=used_ids)

    authorized = values[AUTHORIZED_KIND]
    issued = values[ISSUED_KIND]
    reserved = values[RESERVED_KIND]
    assert authorized is not None and issued is not None
    unissued = _exact(lambda: authorized - issued)
    if unissued < 0:
        # Issued shares can never exceed authorized shares, so the facts disagree.
        notes.append(f"issued_exceeds_authorized:{instant.isoformat()}")
        return _result("contradicted", instant=instant, values=values, observation_ids=used_ids)
    if reserved is None:
        conditions.append(f"reserved_unobserved_at_instant:{instant.isoformat()}")
        return _result(
            "ceiling_only", instant=instant, values=values,
            ceiling=unissued, observation_ids=used_ids,
        )
    headroom = _exact(lambda: unissued - reserved)
    if headroom < 0:
        conditions.append(f"reservation_exceeds_unissued_authorized:{instant.isoformat()}")
    return _result(
        "shortfall" if headroom < 0 else "known", instant=instant, values=values,
        headroom=headroom, observation_ids=used_ids,
    )


def _resolve_issuer_id(observations: Sequence[Mapping[str, Any]]) -> str:
    issuers = {_issuer_of_record(record) for record in observations}
    issuers.discard(None)
    if not issuers:
        raise AuthorizedSharesInputError("no issuer identity: ShareInputs carries none and no record names one")
    if len(issuers) > 1:
        raise AuthorizedSharesInputError(
            f"mixed issuers in one authorized-headroom call: {sorted(str(item) for item in issuers)}",
        )
    return str(next(iter(issuers)))


def select_authorized_headroom(
    observations: ShareInputs, actions: CorporateActionInputs, as_of: str,
) -> AuthorizedHeadroom:
    """Typed wrapper: the authorized-unreserved common-share pool as of ``as_of``."""

    if not isinstance(observations, ShareInputs):
        raise AuthorizedSharesInputError("observations: ShareInputs required")
    if not isinstance(actions, CorporateActionInputs):
        raise AuthorizedSharesInputError("actions: CorporateActionInputs required")
    if _parse_ts(as_of) is None:
        raise AuthorizedSharesInputError("as_of: timezone-aware ISO timestamp required")
    action_family = actions.binding.input_family
    if actions.actions and action_family not in ("events", "corporate_actions"):
        raise AuthorizedSharesInputError(
            f"actions: corporate actions come from events or corporate_actions, not {action_family!r}",
        )
    issuer_id = _resolve_issuer_id(observations.observations)
    records = tuple(actions.actions)
    return headroom_from_records(
        observations.observations,
        records if action_family == "corporate_actions" and records else None,
        issuer_id=issuer_id, as_of=as_of,
        events=records if action_family == "events" and records else None,
    )


__all__ = [
    "AUTHORIZED_KIND",
    "COMPILER_VERSION",
    "AuthorizedHeadroom",
    "AuthorizedSharesInputError",
    "HEADROOM_STATUSES",
    "IMPLEMENTATION",
    "ISSUED_KIND",
    "RESERVED_KIND",
    "headroom_from_records",
    "select_authorized_headroom",
]
