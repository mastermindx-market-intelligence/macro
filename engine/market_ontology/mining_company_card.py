"""Mining company card — the two typed absences printed on the issuer card (W10-3).

Pure, closed opt-in projection: when an identity row carries ``typed_absences``
entries from the admitted vocabulary, the company card gains an ``absences``
array ``[{field, reason}]`` in the identity row's order. A row without the key,
or whose entries carry none of the admitted pairs, keeps today's four-key
company object byte-for-byte — the card mints no limitation and never moves the
T07 ``copper_complete`` ``limitations`` bytes.

The admitted vocabulary is exactly the typed absence already minted at
``engine/company_intelligence/mining_issuer_profiles.py:238-246``
(``_unsourced``): the fields ``fiscal_year_end_month`` and ``listing_mic``,
reason ``missing_source`` (that file's :241). No new reason code is invented
here, and this module imports nothing: the identity row is the input, exactly
as the composition contract already passes it. Printing the absence is not an
``IssuerIdentity`` — ``fcx_issuer`` / ``mp_issuer`` stay ``None``
(mining_issuer_profiles.py:257-267) until an admitted receipt exists, and this
lane fetches none.
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = ["MINING_ABSENCE_FIELDS", "MINING_ABSENCE_REASON", "company_card_absences"]

# The closed absence vocabulary (W10-3): the two identity fields whose absence
# is typed on main, and the one existing typed-absence reason. Anything else is
# not this card's word and is not printed.
MINING_ABSENCE_FIELDS = ("fiscal_year_end_month", "listing_mic")
MINING_ABSENCE_REASON = "missing_source"


def company_card_absences(identity_row: Mapping[str, Any]) -> list[dict[str, str]]:
    """Project an identity row's ``typed_absences`` onto the company card.

    Returns ``absences`` entries ``{"field", "reason"}`` in the row's own
    order, admitting only ``(field in MINING_ABSENCE_FIELDS and
    reason == MINING_ABSENCE_REASON)`` pairs. Non-mapping or non-admitted
    entries are not the card's two typed absences and are dropped; an absent,
    empty or non-sequence ``typed_absences`` key yields ``[]`` (the card then
    keeps today's four keys). Pure: no I/O, no clock, no mutation of the row.
    """
    raw = identity_row.get("typed_absences")
    if not isinstance(raw, (list, tuple)):
        return []
    absences: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            continue
        field = entry.get("field")
        reason = entry.get("reason")
        if field in MINING_ABSENCE_FIELDS and reason == MINING_ABSENCE_REASON:
            absences.append({"field": str(field), "reason": str(reason)})
    return absences
