"""Section 11 report draws: the frontier-only audit subset and the gold-agreed seat audit.

DEC:NEWS-IMPACT-SECTION11-REPORT reserves two seeds. Seed 20261021 draws the
frontier_only_audit subset, about 10% of each template-polarity cell of MATCH cases, frozen
before any score exists and never widened. Seed 20261022 draws the fresh seat audit of
gold-agreed slots, stratified by template and agreement kind, drawn before any system score
is read. Both draws are pure functions of their inputs and seed: the selection ranks by
sha256 and never calls a random generator, so the same inputs always give the same ids.

Reports hold ids and counts only, never labeled values.
"""
from __future__ import annotations

import math
from collections import defaultdict
from hashlib import sha256
from typing import Iterable, Mapping, Sequence

SECTION11_DRAWS_VERSION = "ni-section11-draws-1"

FRONTIER_AUDIT_SEED = 20261021
FRONTIER_AUDIT_RATE = 0.10
GOLD_AUDIT_SEED = 20261022
GOLD_AUDIT_SIZE = 40

AGREEMENT_KINDS = ("present", "absent")


def _rank(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def frontier_only_audit_draw(
    cases: Iterable[Mapping[str, str]],
    *,
    seed: int = FRONTIER_AUDIT_SEED,
    rate: float = FRONTIER_AUDIT_RATE,
) -> dict:
    """Draw ceil(rate * n) cases from every (template, proxy_cell) cell.

    ``cases`` rows carry ``case_id``, ``template`` and ``proxy_cell``. Inside a cell the
    smallest sha256(f"{seed}|{template}-{cell}|{case_id}") ranks first. ceil gives every
    non-empty cell at least one case, so a population of small cells draws above ``rate``;
    the report prints the realised share.
    """
    if not 0.0 < rate <= 1.0:
        raise ValueError("rate must be in (0, 1]")
    cells: dict[str, list[str]] = defaultdict(list)
    seen: set[str] = set()
    for row in cases:
        case_id, template, cell = str(row["case_id"]), str(row["template"]), str(row["proxy_cell"])
        if not case_id or not template or not cell:
            raise ValueError("case_id, template and proxy_cell must be non-empty")
        if case_id in seen:
            raise ValueError(f"duplicate case_id {case_id}")
        seen.add(case_id)
        cells[f"{template}-{cell}"].append(case_id)
    selected: list[str] = []
    per_cell: dict[str, dict[str, int]] = {}
    for key in sorted(cells):
        ids = cells[key]
        k = math.ceil(rate * len(ids))
        ranked = sorted(ids, key=lambda cid: _rank(f"{seed}|{key}|{cid}"))
        selected.extend(ranked[:k])
        per_cell[key] = {"n": len(ids), "drawn": k}
    return {
        "draws_version": SECTION11_DRAWS_VERSION,
        "seed": seed,
        "rate": rate,
        "n_population": len(seen),
        "n_drawn": len(selected),
        "per_cell": per_cell,
        "case_ids": sorted(selected),
    }


def gold_agreed_audit_draw(
    slots: Sequence[tuple[str, str, str, str]],
    *,
    seed: int = GOLD_AUDIT_SEED,
    size: int = GOLD_AUDIT_SIZE,
) -> dict:
    """Draw about ``size`` gold-agreed slots, stratified by (template, agreement_kind).

    ``slots`` are (case_id, template, field, agreement_kind) with agreement_kind in
    AGREEMENT_KINDS: both gold families give the same value (present) or both find none
    (absent). With n_total <= size every slot is drawn. Otherwise each non-empty cell draws
    ceil(size * n_cell / n_total), so the total can exceed ``size`` by fewer than the number
    of cells. Inside a cell the smallest sha256(f"{seed}|{case_id}|{field}") ranks first.
    """
    if size < 1:
        raise ValueError("size must be at least 1")
    cells: dict[str, list[tuple[str, str]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for case_id, template, field, kind in slots:
        if not case_id or not template or not field:
            raise ValueError("case_id, template and field must be non-empty")
        if kind not in AGREEMENT_KINDS:
            raise ValueError(f"agreement_kind must be one of {AGREEMENT_KINDS}")
        if (case_id, field) in seen:
            raise ValueError(f"duplicate slot {case_id}/{field}")
        seen.add((case_id, field))
        cells[f"{template}-{kind}"].append((case_id, field))
    n_total = len(seen)
    selected: list[tuple[str, str]] = []
    per_cell: dict[str, dict[str, int]] = {}
    for key in sorted(cells):
        members = cells[key]
        k = len(members) if n_total <= size else math.ceil(size * len(members) / n_total)
        ranked = sorted(members, key=lambda s: _rank(f"{seed}|{s[0]}|{s[1]}"))
        selected.extend(ranked[:k])
        per_cell[key] = {"n": len(members), "drawn": k}
    return {
        "draws_version": SECTION11_DRAWS_VERSION,
        "seed": seed,
        "size": size,
        "n_population": n_total,
        "n_drawn": len(selected),
        "per_cell": per_cell,
        "slots": [list(s) for s in sorted(selected)],
    }
