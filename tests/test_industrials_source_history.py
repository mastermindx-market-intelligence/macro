"""Industrials T05 — source editions and dossier comparisons.

One test per recovered requirement. The obligation text is quoted from the
original corpus (r1 blob ``40fd1e3783102c28fe748fe35b927484d4f3dddb``,
r2 blob ``9c98e106b954d0a48610afad418de2a9eeb1e58b``,
W12 blob ``b343cbd7bc1f52cfc6fbb5e18ab8d9e9f9392f6c``).

``select_editions`` and ``assess_dossier_comparison`` are not defined on
``engine.company_intelligence.financial_dossier`` (the module ends at
``assemble_evidence_view``). An id that surface cannot express is
``xfail(strict=True)`` with the gap named in the reason. The marker is not
a pass: ``pytest --runxfail`` runs the body and the body fails.

``IND-SF02`` is the exception. Both operands lacking an accounting basis is
already refused by ``qualify_operands`` / ``derive_result_cash``, which is
the native comparison those dossier functions would have to call. That test
is a guard on the merged qualifier, not a stand-in for the missing function.

Every figure is synthetic. No issuer profile and no guidance projector.
"""

from __future__ import annotations

import pytest

from engine.company_intelligence import financial_dossier
from engine.fundamental_forensics.industrials_result_cash import (
    build_comparison_receipt,
    derive_result_cash,
    qualify_operands,
)
from tests.industrials_result_cash_helpers import cell


_CHECKED_ALL = {
    name: True
    for name in (
        "basis",
        "currency",
        "scale",
        "duration",
        "perimeter",
        "definition",
        "source_mode",
    )
}


def _require_edition_selector():
    select_editions = getattr(financial_dossier, "select_editions", None)
    assert callable(select_editions), (
        "financial_dossier.select_editions is absent; "
        "edition selection is not expressible on this module"
    )
    return select_editions


def _require_comparison():
    assess = getattr(financial_dossier, "assess_dossier_comparison", None)
    assert callable(assess), (
        "financial_dossier.assess_dossier_comparison is absent; "
        "dossier comparison is not expressible on this module"
    )
    return assess


@pytest.mark.xfail(
    strict=True,
    reason=(
        "gap: financial_dossier.select_editions is absent, so preliminary and "
        "final statement modes cannot both be retained without overwriting"
    ),
)
def test_ind_d17() -> None:
    """IND-D17, recovered original wording (r1 section 11), verbatim:

        | IND-D17 | Preliminary and final reports |
        | Preserve both information events and statement modes; no retrospective overwriting. |
    """
    select_editions = _require_edition_selector()
    selected = select_editions(
        editions=[
            {
                "event_id": "e-prelim",
                "statement_mode": "preliminary_result",
                "value": "100",
            },
            {
                "event_id": "e-final",
                "statement_mode": "reported_final",
                "value": "110",
            },
        ]
    )
    by_id = {row["event_id"]: row for row in selected["editions"]}
    assert set(by_id) == {"e-prelim", "e-final"}
    assert by_id["e-prelim"]["statement_mode"] == "preliminary_result"
    assert by_id["e-final"]["statement_mode"] == "reported_final"
    assert by_id["e-prelim"]["value"] == "100"
    assert by_id["e-final"]["value"] == "110"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "gap: financial_dossier.assess_dossier_comparison is absent, so prior "
        "guidance, a management preview and an external estimate are not "
        "separately labeled"
    ),
)
def test_ind_d18() -> None:
    """IND-D18, recovered original wording (r1 section 11), verbatim:

        | IND-D18 | Prior guidance versus preview versus external estimate |
        | Label each comparison; none silently becomes another's consensus. |
    """
    assess = _require_comparison()
    guidance = assess("prior_guidance", {"value": "90"})
    preview = assess("management_preview", {"value": "95"})
    estimate = assess("external_estimate", {"value": "97"})
    assert guidance["label"] == "prior_guidance"
    assert preview["label"] == "management_preview"
    assert estimate["label"] == "external_estimate"
    assert len({guidance["label"], preview["label"], estimate["label"]}) == 3
    for row in (guidance, preview, estimate):
        assert row["label"] != "consensus"
        assert row.get("as_consensus") is not True


@pytest.mark.xfail(
    strict=True,
    reason=(
        "gap: financial_dossier.select_editions is absent, so a later filing "
        "cannot be excluded from an earlier source cutoff"
    ),
)
def test_ind_d19() -> None:
    """IND-D19, recovered original wording (r1 section 11), verbatim:

        | IND-D19 | Later filing at earlier cutoff |
        | Exclude filing-only detail until native availability supports inclusion. |
    """
    select_editions = _require_edition_selector()
    selected = select_editions(
        editions=[
            {
                "event_id": "release",
                "available_at": "2026-07-30T20:00:00Z",
                "detail": "release-only",
            },
            {
                "event_id": "filing",
                "available_at": "2026-08-07T20:00:00Z",
                "detail": "filing-only",
            },
        ],
        source_cutoff="2026-07-30T21:00:00Z",
    )
    included = {row["event_id"]: row for row in selected["included"]}
    excluded = {row["event_id"] for row in selected["excluded"]}
    assert "release" in included
    assert "filing" in excluded
    assert included["release"]["detail"] == "release-only"
    assert "filing-only" not in included["release"].get("detail", "")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "gap: financial_dossier.select_editions is absent, so a signature, "
        "call or cache date cannot be refused as a publication instant"
    ),
)
def test_ind_d20() -> None:
    """IND-D20, recovered original wording (r1 section 11), verbatim:

        | IND-D20 | Signature/call/cache date offered as publication time |
        | Preserve unknown publication instant and refuse false precision. |
    """
    select_editions = _require_edition_selector()
    selected = select_editions(
        editions=[
            {
                "event_id": "filing",
                "signature_date": "2026-08-07",
                "call_time": "2026-07-30T21:00:00Z",
                "cache_refreshed_at": "2026-08-08T01:00:00Z",
                "published_at": None,
            }
        ]
    )
    row = selected["editions"][0]
    assert row["published_at"] is None
    assert row.get("publication_instant") in (None, "unknown")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "gap: financial_dossier.select_editions is absent and does not consume "
        "the same-day date-versus-instant refusal (theme_state.py KNOWLEDGE_TIME_UNPROVEN)"
    ),
)
def test_ind_d21() -> None:
    """IND-D21, recovered original wording (r1 section 11), verbatim:

        | IND-D21 | Same-day source date and intraday cutoff |
        | Preserve the existing ambiguous-order refusal. |

    The existing refusal is ``KNOWLEDGE_TIME_UNPROVEN`` when a date-only source
    falls on the cutoff's calendar day (``engine/theme_graph/theme_state.py``
    ``_clock_reasons``). This dossier module does not call it. Ordering the
    release as eligible, or as simply after the cutoff, would replace that
    refusal.
    """
    select_editions = _require_edition_selector()
    selected = select_editions(
        editions=[{"event_id": "release", "published_at": "2026-07-30"}],
        source_cutoff="2026-07-30T15:00:00Z",
    )
    assert selected["status"] == "refused"
    reasons = set(selected.get("reasons") or selected.get("limitations") or [])
    assert reasons & {"KNOWLEDGE_TIME_UNPROVEN", "same_day_boundary_unresolved"}
    included = selected.get("included") or []
    assert all(row.get("event_id") != "release" for row in included)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "gap: financial_dossier.select_editions is absent, so an announced "
        "acquisition is not retained as incomplete and confounding"
    ),
)
def test_ind_d24() -> None:
    """IND-D24, recovered original wording (r1 section 11), verbatim:

        | IND-D24 | Announced acquisition in event window |
        | Preserve non-completed status and potential confound; no unearned ownership or return attribution. |
    """
    select_editions = _require_edition_selector()
    selected = select_editions(
        editions=[],
        events=[
            {
                "event_id": "deal",
                "kind": "acquisition",
                "status": "announced",
                "completed": False,
            }
        ],
    )
    deal = next(row for row in selected["events"] if row["event_id"] == "deal")
    assert deal["status"] == "announced"
    assert deal["completed"] is False
    assert deal["potential_confound"] is True
    assert deal.get("ownership_attributed") is not True
    assert deal.get("return_attributed") is not True


@pytest.mark.xfail(
    strict=True,
    reason=(
        "gap: financial_dossier.assess_dossier_comparison is absent, so a recast "
        "amount before its source availability is not kept off current analysis"
    ),
)
def test_ind_r209() -> None:
    """IND-R209, recovered original wording (r2 section 11), verbatim:

        | IND-R209 | Recast comparative amount before its source availability |
        | Current analysis and historical eligibility remain separate. |
    """
    assess = _require_comparison()
    result = assess(
        "recast_before_availability",
        {
            "as_of": "2026-08-07T00:00:00Z",
            "current": {"value": "10", "available_at": "2026-08-01T00:00:00Z"},
            "recast_comparative": {
                "value": "8",
                "available_at": "2026-09-01T00:00:00Z",
            },
        },
    )
    assert result["current_analysis"]["eligible"] is True
    assert result["historical_eligibility"]["eligible"] is False
    assert result["current_analysis"] is not result["historical_eligibility"]


def test_ind_sf02() -> None:
    """IND-SF02, recovered original wording (W12), verbatim:

        | IND-SF02 | Prior/actual both lack required accounting basis |
        | Unknown is not sufficient for a certified comparison; native input qualification or visible refusal. |

    Both operands lack ``basis.accounting`` (missing key, ``None``, and empty
    string). The receipt declares every gate checked, including basis. The
    comparison still refuses, names ``required_basis_unknown``, and publishes
    no number. The control is the same pair with GAAP on both sides, which
    certifies growth ``10``: the refusal is the missing basis.

    The literal token ``accounting="unknown"`` is the same refusal, pinned by
    ``test_ind_sf02_unknown_accounting_token_refuses``. ``assess_dossier_comparison``
    is absent, so this guard pins the qualifier the dossier comparison would
    have to pass through.
    """
    lack_shapes = (
        {"recast": "as_reported"},
        {"accounting": None, "recast": "as_reported"},
        {"accounting": "", "recast": "as_reported"},
    )
    for basis in lack_shapes:
        cells = [
            cell(
                "110",
                metric="revenue_current",
                owner_ref="synthetic:cell:sf02-current",
                basis=basis,
            ),
            cell(
                "100",
                metric="revenue_prior",
                owner_ref="synthetic:cell:sf02-prior",
                basis=basis,
            ),
        ]
        receipt = build_comparison_receipt(
            "year_over_year", cells, checked=_CHECKED_ALL
        )
        qualified = qualify_operands(
            "year_over_year",
            cells,
            comparison_receipt=receipt,
            formula="growth_pct",
        )
        derived = derive_result_cash(
            "growth_pct", cells, comparison_receipt=receipt
        )
        assert qualified["status"] == "refused", (basis, qualified)
        assert "required_basis_unknown" in qualified["limitations"], (basis, qualified)
        assert derived["status"] == "refused", (basis, derived)
        assert derived["value"] is None, (basis, derived)
        assert "required_basis_unknown" in derived["limitations"], (basis, derived)

    present = {"accounting": "GAAP", "recast": "as_reported"}
    ok_cells = [
        cell(
            "110",
            metric="revenue_current",
            owner_ref="synthetic:cell:sf02-current",
            basis=present,
        ),
        cell(
            "100",
            metric="revenue_prior",
            owner_ref="synthetic:cell:sf02-prior",
            basis=present,
        ),
    ]
    ok_receipt = build_comparison_receipt(
        "year_over_year", ok_cells, checked=_CHECKED_ALL
    )
    ok = derive_result_cash("growth_pct", ok_cells, comparison_receipt=ok_receipt)
    assert ok["status"] == "ready", ok
    assert ok["value"] == "10", ok


@pytest.mark.parametrize(
    "accounting",
    ("unknown", "Unknown", "UNKNOWN", "Unknown "),
    ids=("unknown", "Unknown", "UNKNOWN", "Unknown_trailing_space"),
)
def test_ind_sf02_unknown_accounting_token_refuses(accounting: str) -> None:
    """IND-SF02: a stripped casefold of ``unknown`` is not an accounting basis.

    Both operands carry the token, recast is present, and every receipt gate
    is checked. ``unknown``, ``Unknown``, ``UNKNOWN``, and ``Unknown ``
    (trailing space) must refuse with ``required_basis_unknown`` and publish
    no number. A truthy token must not certify growth ``10``.
    """
    basis = {"accounting": accounting, "recast": "as_reported"}
    cells = [
        cell(
            "110",
            metric="revenue_current",
            owner_ref="synthetic:cell:sf02-current",
            basis=basis,
        ),
        cell(
            "100",
            metric="revenue_prior",
            owner_ref="synthetic:cell:sf02-prior",
            basis=basis,
        ),
    ]
    receipt = build_comparison_receipt(
        "year_over_year", cells, checked=_CHECKED_ALL
    )
    qualified = qualify_operands(
        "year_over_year",
        cells,
        comparison_receipt=receipt,
        formula="growth_pct",
    )
    derived = derive_result_cash(
        "growth_pct", cells, comparison_receipt=receipt
    )
    assert qualified["status"] == "refused", qualified
    assert "required_basis_unknown" in qualified["limitations"], qualified
    assert derived["status"] == "refused", derived
    assert derived["value"] is None, derived
    assert "required_basis_unknown" in derived["limitations"], derived


@pytest.mark.xfail(
    strict=True,
    reason=(
        "gap: financial_dossier.assess_dossier_comparison is absent, so a missing "
        "next-period outlook is not kept from dropping the operating section or "
        "from inventing a guidance role; preliminary/final chronology is not selected"
    ),
)
def test_ind_sf03() -> None:
    """IND-SF03, recovered original wording (W12), verbatim:

        | IND-SF03 | Same-period preliminary/final results with no next-period outlook |
        | Correct event/document chronology; no fabricated guidance role or lost operating dossier. |

    ``assemble_evidence_view`` keeps a ready section when ``consensus`` or
    ``theme_graph`` is absent. That is not this obligation: it has no
    preliminary/final chronology and no outlook, so a missing outlook cannot
    be shown to spare the operating section.
    """
    assess = _require_comparison()
    result = assess(
        "management_sequence",
        {
            "editions": [
                {
                    "event_id": "prelim",
                    "statement_mode": "preliminary_result",
                    "published_at": "2026-07-21",
                },
                {
                    "event_id": "final",
                    "statement_mode": "reported_final",
                    "published_at": "2026-07-30",
                },
            ],
            "outlook": None,
            "operating": {"section": "operating", "status": "ready", "value": "42"},
        },
    )
    chronology = [row["event_id"] for row in result["chronology"]]
    assert chronology == ["prelim", "final"]
    assert result["operating"]["status"] == "ready"
    assert result["operating"]["value"] == "42"
    assert result.get("guidance_role") in (None, "absent")
    roles = result.get("roles") or {}
    assert "guidance" not in roles
