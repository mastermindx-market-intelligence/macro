"""Live not-connected Finance shell: two NOT_YET_EVALUABLE watching items.

The Finance Intelligence public shell renders with ``data-fi-read-url=""``
(no foundation route, no fetch, no WATCHING). A visitor who opens the
shell should still see *something* in ``ul.fi-falsifiers``: the two
synthetic watching items this module returns.

No network, no I/O, no clock, no store, no read of ``research/finance``.
The frozen constants are byte-equal to the shared fixture at
``tests/fixtures/finance_case_signal/synthesis_v0.json``; the engine
module itself never opens that file. ``compose_finance_projection``
stays unedited and still emits ``[]``.

The only public placement path is :func:`finance_page_signal.apply_page_signal`;
this module never calls ``_attach_falsifiers`` directly and never imports
the helper by name. ``WATCHING`` is not emitted — a descriptive state
that contains ``MEASURED`` does not change the falsifier state.
``shell_watching_items`` is the integration-bridge contract (the page
template iterates its return value). It fails closed: an admission
refusal propagates and the page is left as it was.

The ZH strings live in this module, not in the page template, so the
bilingual deck stays review-gated display copy. Dates stay ISO.

W10-FIN-2 adds ``shell_hint_rows()``: the eleven R12 preflight witness
symbols as ``RESEARCH_HINT_UNVALIDATED`` hint-roster rows for
``#company-exposure``. Record ids come only from
:func:`engine.sector_intelligence.finance_witness_hints.hint_binding`;
a row carries symbol, record id and state and nothing else — no
identity key, no stock route, no source_record. BNY keeps
``fin-research-bk-2025``; ``BK`` is not a symbol. Same no-I/O law
applies: the preflight JSON is never opened here.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from engine.sector_intelligence.finance_page_signal import apply_page_signal
from engine.sector_intelligence.finance_witness_hints import hint_binding


# Frozen synthetic constants — byte-equal to the shared fixture at
# tests/fixtures/finance_case_signal/synthesis_v0.json. Tests open the
# fixture file; this module never does.
_SHELL_DOCUMENT: Mapping[str, Any] = {
    "formal_causal_outcomes_measured": 0,
    "prospective_validation_started": False,
    "case_count": 2,
    "cases": [
        {
            "case_id": "syn-case-alpha",
            "canonical_case_id": "syn-fin-case-alpha",
            "aliases": ["syn-alias-alpha-not-canonical"],
            "anchor_date": "2024-06-30",
            "archetype": "synthetic_descriptive",
            "witness": "SYN_WITNESS_A",
            "descriptive_evidence_state": "MARKET_AND_VALUATION_MEASURED",
            "formal_causal_outcome": "UNMEASURED",
            "primary_limit": (
                "Synthetic limit: a measured description is not a measured cause."
            ),
            "slice_id": "card_networks",
        },
        {
            "case_id": "syn-case-beta",
            "canonical_case_id": "syn-fin-case-beta",
            "aliases": ["syn-alias-beta-not-canonical"],
            "anchor_date": "2023-11-02",
            "archetype": "synthetic_alias",
            "witness": "SYN_WITNESS_B",
            "descriptive_evidence_state": "DESCRIPTIVE_ONLY",
            "formal_causal_outcome": "UNMEASURED",
            "primary_limit": (
                "Synthetic limit: an alias does not replace the canonical case id."
            ),
            "slice_id": "exchanges_trading_venues",
        },
    ],
}

# The synthetic rows cover both finance slices the shell template ships
# watching items for. The include is rendered in the order the rows are
# admitted (alphabetical-by-insertion-order on the slice_id, per the
# review gate).
_SHELL_SLICES: list[dict[str, Any]] = [
    {
        "slice_id": "card_networks",
        "falsifiers": [],
        "rerating": {"falsifier_ids": []},
    },
    {
        "slice_id": "exchanges_trading_venues",
        "falsifiers": [],
        "rerating": {"falsifier_ids": []},
    },
]


# In-module ZH translations for the synthetic fixture sentences (review-
# gated display copy, the same class as the bilingual deck in the page
# template). The fixture itself does not carry ZH — it is a test fixture
# only — so this map is the canonical bilingual mirror. Keys are the
# canonical case ids (``falsifier_id``).
SHELL_STATEMENT_ZH: Mapping[str, str] = {
    "syn-fin-case-alpha": "综合上限：已被度量的描述不等于已被度量的因果。",
    "syn-fin-case-beta": "综合上限：别名不能替代规范的案例标识。",
}

# Window ZH mirrors: dates stay ISO. The ZH copy of a date window is the
# same ISO string in both locales; this map exists so the include can
# iterate one source of truth instead of branching in Jinja.
SHELL_WINDOW_ZH: Mapping[str, str] = {
    "syn-fin-case-alpha": "2024-06-30",
    "syn-fin-case-beta": "2023-11-02",
}

_FALSIFIER_STATE = "NOT_YET_EVALUABLE"
_WATCHING_ITEMS: list[dict[str, str]] | None = None


def _build_shell_page() -> MutableMapping[str, Any]:
    """Return a fresh shell page each call.

    A new dict means each caller observes its own writes; the include
    and the renderer do not share a mutable.
    """
    return {"slices": [dict(sl) for sl in _SHELL_SLICES]}


def watching_items(
    document: Mapping[str, Any],
    page: MutableMapping[str, Any],
) -> None:
    """Run ``apply_page_signal`` against a caller-supplied document + page.

    Test-side helper: admits ``document``, then writes the falsifiers
    onto ``page`` exactly the way the review gate does. Admission
    refuses (``SynthesisAdmissionRefusal``) on any of the four guarded
    shapes; the refusal propagates and the page is left as it was.
    """
    apply_page_signal(document, page)


def shell_watching_items() -> list[dict[str, str]]:
    """Return the two NOT_YET_EVALUABLE falsifiers the shell ships with.

    Each call runs :func:`apply_page_signal` against the frozen
    synthetic document and a fresh shell page. The result is memoized
    only inside this module; every caller receives defensive copies
    (the list and each item dict), so mutating a returned item cannot
    leak into the memo or a later call. The falsifier shape is the
    page-gate's own projection (four keys, ``NOT_YET_EVALUABLE``).
    Admission refusal propagates — the caller sees
    :class:`SynthesisAdmissionRefusal` and the page is left as it was;
    a placed falsifier in any other state raises ``ValueError`` naming
    that state instead of vanishing from the page.
    """
    global _WATCHING_ITEMS
    if _WATCHING_ITEMS is not None:
        return [dict(item) for item in _WATCHING_ITEMS]
    page = _build_shell_page()
    apply_page_signal(_SHELL_DOCUMENT, page)
    placed: list[dict[str, str]] = []
    for sl in page["slices"]:
        for item in sl["falsifiers"]:
            if item["state"] != _FALSIFIER_STATE:
                # Review gate contract: never WRITE not-emitted — and
                # never silently DROP a placement in a foreign state
                # either. Fail loudly, naming the state.
                raise ValueError(
                    f"unexpected watching falsifier state: {item['state']}"
                )
            placed.append(dict(item))
    _WATCHING_ITEMS = placed
    return [dict(item) for item in _WATCHING_ITEMS]


# The hint roster is the R12 preflight witness symbol order, enumerated
# in-module so this file never reaches into ``finance_witness_hints``
# privates. ``hint_binding`` fails closed on an unknown symbol, and
# ``tests/test_finance_watching.py`` pins the eleven-row roster, so a
# drift between this tuple and the binding map is a loud test failure,
# not a silent row loss.
_HINT_ROSTER: tuple[str, ...] = (
    "V",
    "MA",
    "FI",
    "FIS",
    "CME",
    "ICE",
    "NDAQ",
    "BNY",
    "STT",
    "SPGI",
    "MCO",
)


def shell_hint_rows() -> list[dict[str, str]]:
    """Return the eleven RESEARCH_HINT_UNVALIDATED hint-roster rows.

    Each row is ``{"symbol", "record_id", "state"}`` — the closed
    research-hint citation the shell shows inside ``#company-exposure``
    while the read-model route stays unwired. ``record_id`` is copied
    verbatim from ``hint_binding(symbol)["record_id"]`` (BNY keeps
    ``fin-research-bk-2025``); it is the binding's citation id, never an
    identity key, and no other binding field is carried. ``BK`` and
    ``GHOST`` are not roster symbols. No stock route, no
    ``IDENTITY_VALIDATED``, no fetch, no research/finance read.
    """
    rows: list[dict[str, str]] = []
    for symbol in _HINT_ROSTER:
        binding = hint_binding(symbol)
        rows.append(
            {
                "symbol": symbol,
                "record_id": binding["record_id"],
                "state": binding["state"],
            }
        )
    return rows
