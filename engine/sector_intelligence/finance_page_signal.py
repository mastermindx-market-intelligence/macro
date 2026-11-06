"""Page signal: the review gate writes the falsifier list.

No I/O, network, clock, store, or read of research/finance. Admits the
caller-supplied case document, then places each falsifier on the slice
whose ``slice_id`` equals the row. :func:`apply_page_signal` is the only
public placement path; placement itself goes through the module-private
:func:`_attach_falsifiers`.
``compose_finance_projection`` stays unedited and keeps emitting empty
falsifier lists. ``WATCHING`` is not emitted. A descriptive state that
contains ``MEASURED`` does not change the falsifier state.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from engine.sector_intelligence.finance_case_signal import (
    _attach_falsifiers,
    project_falsifier,
)


class SynthesisAdmissionRefusal(ValueError):
    """The review gate refuses the document. ``str(exc)`` is the code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def __str__(self) -> str:
        return self.code


def _admit_pairs(
    document: Mapping[str, Any],
) -> list[tuple[Mapping[str, Any], dict[str, str]]]:
    """Admit the document and pair every row with its projected falsifier.

    Calls :func:`project_falsifier` for every row. A descriptive state that
    contains ``MEASURED`` does not admit a cause, and an alias does not
    become the falsifier id. ``"cases"`` is read from the document once.
    """
    if document.get("formal_causal_outcomes_measured") != 0:
        raise SynthesisAdmissionRefusal("formal_causal_outcomes_measured")
    if document.get("prospective_validation_started") is not False:
        raise SynthesisAdmissionRefusal("prospective_validation_started")
    rows = document.get("cases")
    if not isinstance(rows, list) or not rows:
        raise SynthesisAdmissionRefusal("no_rows")
    pairs: list[tuple[Mapping[str, Any], dict[str, str]]] = []
    for row in rows:
        if row.get("formal_causal_outcome") != "UNMEASURED":
            raise SynthesisAdmissionRefusal("row_outcome_not_unmeasured")
        pairs.append((row, project_falsifier(row)))
    return pairs


def admit_synthesis(document: Mapping[str, Any]) -> list[dict[str, str]]:
    """Admit a synthetic synthesis only when no causal outcome is measured.

    Returns the falsifier :func:`_admit_pairs` projected for each row, in
    row order.
    """
    return [falsifier for _, falsifier in _admit_pairs(document)]


def apply_page_signal(
    case_document: Mapping[str, Any],
    page: MutableMapping[str, Any],
) -> None:
    """Admit ``case_document`` and attach each falsifier to its slice.

    Admission finishes before any slice is written, and each falsifier is
    routed by the row admission read, not by a second read of the
    document. Every slice's falsifier list is checked and every target
    slice's ``rerating`` value is read before the first slice is written.
    A :func:`_attach_falsifiers` refusal leaves the page as it was, and
    so does any exception raised by a lookup on a caller-supplied slice
    mapping or on the ``rerating`` mapping nested inside it. A slice with
    no admitted row is left as it was. A ``__setitem__`` that raises on a
    caller-supplied mapping is outside the guarantee: undoing such a
    write would itself call ``__setitem__``.
    """
    pairs = _admit_pairs(case_document)
    slices = page.get("slices")
    if not isinstance(slices, list):
        raise SynthesisAdmissionRefusal("no_slices")
    by_id: dict[str, MutableMapping[str, Any]] = {}
    for sl in slices:
        if isinstance(sl, MutableMapping):
            slice_id = sl.get("slice_id")
            if isinstance(slice_id, str):
                by_id[slice_id] = sl
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    order: list[str] = []
    for row, falsifier in pairs:
        slice_id = row.get("slice_id") if isinstance(row, Mapping) else None
        if not isinstance(slice_id, str) or slice_id not in by_id:
            raise SynthesisAdmissionRefusal("slice_absent")
        if slice_id not in grouped:
            order.append(slice_id)
            grouped[slice_id] = []
        grouped[slice_id].append(falsifier)
    # _attach_falsifiers refuses only on the list itself, so a dry run on a
    # bare slice finds every refusal before a real slice changes.
    for slice_id in order:
        _attach_falsifiers({"slice_id": slice_id}, grouped[slice_id])
    # Every lookup on a caller-supplied slice happens before the first
    # caller-visible write, so a raising lookup leaves the page as it was.
    pre_read: dict[str, Any] = {}
    for slice_id in order:
        pre_read[slice_id] = by_id[slice_id].get("rerating")
    for slice_id in order:
        _attach_falsifiers(
            by_id[slice_id], grouped[slice_id], rerating=pre_read[slice_id]
        )
