"""Pure case-row falsifier for the Finance Intelligence page.

No I/O, network, clock, or store. Does not read research/finance.
``compose_finance_projection`` keeps emitting empty falsifier lists; the only
public placement path is :func:`finance_page_signal.apply_page_signal`, which
routes admitted rows through the module-private :func:`_attach_falsifiers`.

A row is admitted only when ``formal_causal_outcome`` is ``UNMEASURED`` and
``slice_id`` is a member of ``finance_projection._FINANCE_SLICE_IDS``. Every
admitted row is ``NOT_YET_EVALUABLE``. ``WATCHING`` is not emitted.
``descriptive_evidence_state`` is not a cause, and an alias does not replace
``canonical_case_id``. Authority caps stay on the projection.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Sequence

from engine.sector_intelligence.finance_projection import _FINANCE_SLICE_IDS


_ADMITTED_OUTCOME = "UNMEASURED"
_FALSIFIER_STATE = "NOT_YET_EVALUABLE"
_SLICE_IDS = frozenset(_FINANCE_SLICE_IDS)
_FALSIFIER_KEYS = ("falsifier_id", "statement", "window", "state")
# Private sentinel: the caller did not pre-read ``rerating``, so read
# the slice's own ``get("rerating")`` at write time.
_RERATING_READ_FROM_SLICE = object()


class FinanceCaseSignalRefusal(ValueError):
    """Typed refusal. ``str(exc)`` is the code and never a falsifier state."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def __str__(self) -> str:
        return self.code


def project_falsifier(row: Mapping[str, Any]) -> dict[str, str]:
    """Project one caller-scoped case row into a schema falsifier.

    ``descriptive_evidence_state`` is not read. A value that contains
    ``MEASURED`` does not change the state.
    """
    if row.get("formal_causal_outcome") != _ADMITTED_OUTCOME:
        raise FinanceCaseSignalRefusal("formal_causal_outcome_not_unmeasured")
    slice_id = row.get("slice_id")
    if not isinstance(slice_id, str) or slice_id not in _SLICE_IDS:
        raise FinanceCaseSignalRefusal("unknown_slice")
    canonical = row.get("canonical_case_id")
    statement = row.get("primary_limit")
    window = row.get("anchor_date")
    if not isinstance(canonical, str) or canonical == "":
        raise FinanceCaseSignalRefusal("missing_canonical_case_id")
    if not isinstance(statement, str) or statement == "":
        raise FinanceCaseSignalRefusal("missing_primary_limit")
    if not isinstance(window, str) or window == "":
        raise FinanceCaseSignalRefusal("missing_anchor_date")
    return {
        "falsifier_id": canonical,
        "statement": statement,
        "window": window,
        "state": _FALSIFIER_STATE,
    }


def _attach_falsifiers(
    slice_doc: MutableMapping[str, Any],
    falsifiers: Sequence[Mapping[str, Any]],
    *,
    rerating: Any = _RERATING_READ_FROM_SLICE,
) -> None:
    """Place already-projected falsifiers onto one slice.

    Does not call ``compose_finance_projection``. A state other than
    ``NOT_YET_EVALUABLE`` is refused, so ``WATCHING`` is not attached.
    The ``rerating`` keyword defaults to a private sentinel meaning
    "read it yourself": with no value passed, the slice's own
    ``get("rerating")`` is consulted after the falsifier write, exactly
    as before. A caller that already read the value passes it here so
    this helper never looks at the slice again.
    """
    placed: list[dict[str, str]] = []
    for item in falsifiers:
        if item.get("state") != _FALSIFIER_STATE:
            raise FinanceCaseSignalRefusal("watching_not_emitted")
        try:
            placed.append({key: item[key] for key in _FALSIFIER_KEYS})
        except KeyError as exc:
            raise FinanceCaseSignalRefusal("invalid_falsifier") from exc
    slice_doc["falsifiers"] = placed
    if rerating is _RERATING_READ_FROM_SLICE:
        rerating = slice_doc.get("rerating")
    if isinstance(rerating, MutableMapping):
        rerating["falsifier_ids"] = [item["falsifier_id"] for item in placed]
