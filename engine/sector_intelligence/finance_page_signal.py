"""Page signal: the review gate writes the falsifier list.

No I/O, network, clock, store, or read of research/finance. Admits the
caller-supplied case document, then places each falsifier on the slice
whose ``slice_id`` equals the row, via :func:`attach_falsifiers`.
``compose_finance_projection`` stays unedited and keeps emitting empty
falsifier lists. ``WATCHING`` is not emitted. A descriptive state that
contains ``MEASURED`` does not change the falsifier state.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from engine.sector_intelligence.finance_case_signal import (
    attach_falsifiers,
    project_falsifier,
)


class SynthesisAdmissionRefusal(ValueError):
    """The review gate refuses the document. ``str(exc)`` is the code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def __str__(self) -> str:
        return self.code


def admit_synthesis(document: Mapping[str, Any]) -> list[dict[str, str]]:
    """Admit a synthetic synthesis only when no causal outcome is measured.

    Calls :func:`project_falsifier` for every row. A descriptive state that
    contains ``MEASURED`` does not admit a cause, and an alias does not
    become the falsifier id.
    """
    if document.get("formal_causal_outcomes_measured") != 0:
        raise SynthesisAdmissionRefusal("formal_causal_outcomes_measured")
    if document.get("prospective_validation_started") is not False:
        raise SynthesisAdmissionRefusal("prospective_validation_started")
    rows = document.get("cases")
    if not isinstance(rows, list) or not rows:
        raise SynthesisAdmissionRefusal("no_rows")
    admitted: list[dict[str, str]] = []
    for row in rows:
        if row.get("formal_causal_outcome") != "UNMEASURED":
            raise SynthesisAdmissionRefusal("row_outcome_not_unmeasured")
        admitted.append(project_falsifier(row))
    return admitted


def apply_page_signal(
    case_document: Mapping[str, Any],
    page: MutableMapping[str, Any],
) -> None:
    """Admit ``case_document`` and attach each falsifier to its slice.

    Admission finishes before any slice is written. A slice with no admitted
    row is left as it was.
    """
    falsifiers = admit_synthesis(case_document)
    rows = case_document.get("cases")
    if not isinstance(rows, list):
        raise SynthesisAdmissionRefusal("no_rows")
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
    for row, falsifier in zip(rows, falsifiers):
        slice_id = row.get("slice_id") if isinstance(row, Mapping) else None
        if not isinstance(slice_id, str) or slice_id not in by_id:
            raise SynthesisAdmissionRefusal("slice_absent")
        if slice_id not in grouped:
            order.append(slice_id)
            grouped[slice_id] = []
        grouped[slice_id].append(falsifier)
    for slice_id in order:
        attach_falsifiers(by_id[slice_id], grouped[slice_id])
