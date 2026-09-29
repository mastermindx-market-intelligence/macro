"""Industrials T06 — financial dossier obligations, enforced from recovered text.

This suite is the plan's own T06 home (section 6 assigns every T06 requirement to
``tests/test_industrials_financial_dossier.py``).  It opened with exactly ONE row,
``IND-R214``, and holds three; each is here on the same two grounds:

* Its authority is the RECOVERED ORIGINAL wording, not a paraphrase.  Sol's
  CONTINUE ruling on carrier #7789 (comment ``5894127980``) restored the r1/r2/W12
  corpus from the original branch history; ``IND-R214`` is r2 blob
  ``9c98e106b954d0a48610afad418de2a9eeb1e58b`` section 11, quoted verbatim below.
* Its subject is MERGED T04 code in
  ``engine.fundamental_forensics.industrials_result_cash``.  So it needs no issuer
  binding (#7905), no entitlement or private transport (#7870) and none of T05's
  information-time editions, which stay PARKED.

``IND-D23`` and ``IND-R215`` joined it once their compliant/violating pairs were
measured rather than inferred from the module's vocabulary.  Unlike ``IND-R214``
they are GUARDS, not fixes: merged code already satisfies both, and these rows stop
a future change from collapsing the distinctions.

The remaining six T06 rows are deliberately absent, and their absence is the honest
signal rather than an oversight.  ``IND-D03`` needs the private content-role owner
and ``IND-D22``/``IND-R213`` need native correction lineage.  The other three were
each measured and ruled out for a stated reason: ``IND-R201``'s "optional graph
extension" is the theme graph, which another owner holds; ``IND-R218`` forbids a
mispricing/probability/trade conclusion, and no such vocabulary exists anywhere in
this package, so a test would guard nothing; ``IND-SF04``'s prohibition half (no
forced BOM, wafer measure or fake stage) is assertable but its positive half -- a
coherent financial/service view -- needs a service-business fixture path this
module does not own, and half an obligation is not an anchor.  An anchor row is a
claim that a test separates the compliant case from the violating one, so a row is
added only when that claim is true.

Every fixture is synthetic: invented issuers, ``example.invalid`` sources, no real
Exponent or Pentair figure.
"""

from __future__ import annotations

import pytest

from engine.fundamental_forensics.industrials_result_cash import (
    FORMULA_VERSION,
    build_comparison_receipt,
    derive_result_cash,
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


def test_ind_r214(monkeypatch: pytest.MonkeyPatch) -> None:
    """IND-R214, recovered original wording (r2 section 11), verbatim:

        | IND-R214 | Same operands with changed normalization/formula version |
        | New derived identity and visible method; no stale cached summary |

    Three clauses, each asserted against its violating case.

    ``receipt_id`` is the derived identity a consumer keys on.  Normalization was
    already covered before this change, because a normalization step is a
    ``transformations`` entry and the digest hashes those.  The formula VERSION was
    not in the digest at all -- and it is the one input that changes the method
    while every operand stays put, so nothing else in the digest moves with it.
    Measured on the merged module, the two receipts below were byte-identical.
    """
    cells = [
        cell("100", owner_ref="synthetic:cell:r214-a"),
        cell("90", owner_ref="synthetic:cell:r214-b"),
    ]

    first = build_comparison_receipt("year_over_year", cells, checked=_CHECKED_ALL)

    # Patch the module global through the function's own globals mapping rather
    # than by importing the module object.  `from engine.fundamental_forensics
    # import industrials_result_cash` would reference the PACKAGE, whose
    # `__init__` pulls in detectors, filing_attestation and four collectors --
    # measured, that widened this job's import closure by 8 files and failed
    # `test_curated_exclusive_scopes_cover_their_own_import_closure`, which would
    # have forced unrelated collector edits to schedule the Industrials gate.
    monkeypatch.setitem(
        build_comparison_receipt.__globals__, "FORMULA_VERSION", "v2-recovered-test"
    )
    second = build_comparison_receipt("year_over_year", cells, checked=_CHECKED_ALL)

    # The operands did NOT move -- this is the "same operands" precondition, and
    # asserting it is what stops the test from passing for the wrong reason.
    assert first["operand_refs"] == second["operand_refs"]
    assert first["checked"] == second["checked"]
    assert first["purpose"] == second["purpose"]

    # Clause 1 - NEW DERIVED IDENTITY.  Asserted FIRST and read with .get() so the
    # pre-fix module fails HERE, on the defect itself, rather than on a missing
    # key: a control that dies before reaching the identity comparison would not
    # show that this test discriminates the behaviour it claims to.
    assert first["receipt_id"] != second["receipt_id"], (
        "IND-R214: receipt_id is invariant across a formula-version change, so one "
        "derived identity addresses two different computations."
    )

    # Clause 2 - VISIBLE METHOD, on the object a consumer caches. formula_version
    # already reached the derivation payload; a derived identity whose method
    # cannot be read off the same object is not a visible method.
    assert first.get("formula_version") == FORMULA_VERSION
    assert second.get("formula_version") == "v2-recovered-test"

    # Clause 3 - NO STALE CACHED SUMMARY. This is the consequence the obligation
    # actually protects against, so it is asserted rather than left implied: a
    # cache keyed on the derived identity must MISS after a method change instead
    # of answering a v2 request with the body computed under v1.
    cache = {first["receipt_id"]: "summary computed under v1"}
    assert second["receipt_id"] not in cache, (
        "IND-R214: a consumer cache keyed on receipt_id would serve the stale v1 "
        "summary for a v2 request."
    )


# ---------------------------------------------------------------------------
# cash_rollforward is the one formula in this module carrying a genuinely
# OPTIONAL operand, which is what makes IND-D23 and IND-R215 discriminable here.
# ---------------------------------------------------------------------------

_REQUIRED_ROLLFORWARD = (
    "opening_cash",
    "operating_movement",
    "investing_movement",
    "financing_movement",
    "exchange_movement",
)


def _rollforward_cells() -> list[dict[str, object]]:
    """Six synthetic operands that reconcile exactly: 100 + 50 - 20 - 10 - 5 == 115."""
    return [
        cell("100", metric="opening_cash", owner_ref="synthetic:cell:open"),
        cell("50", metric="operating_movement", owner_ref="synthetic:cell:op"),
        cell("-20", metric="investing_movement", owner_ref="synthetic:cell:inv"),
        cell("-10", metric="financing_movement", owner_ref="synthetic:cell:fin"),
        cell("-5", metric="exchange_movement", owner_ref="synthetic:cell:fx"),
        cell("115", metric="closing_cash", owner_ref="synthetic:cell:close"),
    ]


def _typed_absence(operand, reason: str) -> dict[str, object]:
    """The operand's typed-absence shape: the value key is gone, a reason replaces it."""
    stripped = {k: v for k, v in operand.items() if k != "value"}
    stripped["absence"] = reason
    return stripped


def _rollforward(cells) -> dict[str, object]:
    return derive_result_cash(
        "cash_rollforward",
        cells,
        comparison_receipt=build_comparison_receipt("rollforward", cells),
    )


def test_ind_d23() -> None:
    """IND-D23, recovered original wording (r1 section 11), verbatim:

        | IND-D23 | Required cash/estimate operand unavailable |
        | Local typed absence; no zero or invented number, no all-page false success. |

    The absence must be TYPED, so the three unavailability shapes stay
    distinguishable, and it must be LOCAL, so it refuses its own derivation only.
    ``value`` and ``computed_total`` are both asserted absent: publishing the
    partial arithmetic of an unavailable operand set is the "invented number" the
    obligation forbids, in the form this module could actually produce it.

    The reconciling control runs FIRST and is asserted.  A dead control makes every
    shape below report ``refused`` and proves nothing -- measured, that is exactly
    what wrong metric names produced while writing this.
    """
    control = _rollforward(_rollforward_cells())
    assert control["status"] == "ready", control
    assert control["value"] == "115", control

    for index, metric in enumerate(_REQUIRED_ROLLFORWARD):
        cells = _rollforward_cells()

        typed = (
            cells[:index]
            + [_typed_absence(cells[index], "no_source_document")]
            + cells[index + 1 :]
        )
        refused = _rollforward(typed)
        assert refused["status"] == "refused", (metric, refused)
        assert refused["value"] is None, (metric, refused)
        assert refused.get("computed_total") is None, (metric, refused)

        omitted = cells[:index] + cells[index + 1 :]
        missing = _rollforward(omitted)
        assert missing["status"] == "refused", (metric, missing)
        assert missing["value"] is None, (metric, missing)
        assert missing.get("computed_total") is None, (metric, missing)
        # A refusal that does not NAME the operand it lacks is not a typed absence.
        assert "operand_missing:%s" % metric in missing["limitations"], (metric, missing)

    # "no all-page false success" -- one unavailable operand refuses ITS derivation
    # and leaves a second derivation over intact operands untouched.
    intact = _rollforward(_rollforward_cells())
    assert intact["status"] == "ready", intact
    assert intact["value"] == "115", intact


def test_ind_r215() -> None:
    """IND-R215, recovered original wording (r2 section 11), verbatim:

        | IND-R215 | Mandatory source unavailable; optional source absent |
        | Distinct required refusal versus optional limitation; no invented data |

    Asserted as ONE property, because the failure the obligation forbids is the
    COLLAPSE of the two outcomes into one -- refusing when only an optional input
    is missing, or publishing a computed total when a mandatory one is.  Two tests
    that each check one half would both still pass after that collapse.

    The module never uses the word "optional"; the distinction is structural, which
    is why it had to be measured rather than grepped for.
    """
    control = _rollforward(_rollforward_cells())
    assert control["status"] == "ready", control
    assert control["limitations"] == [], control

    # Optional source absent: the analysis stands, disclosed as a limitation, with
    # no figure invented to stand in for the operand that is gone.
    cells = _rollforward_cells()
    for label, supplied in (
        ("omitted", cells[:5]),
        ("typed-absent", cells[:5] + [_typed_absence(cells[5], "no_primary_release")]),
    ):
        optional = _rollforward(supplied)
        assert optional["status"] == "limited", (label, optional)
        assert optional["value"] == "115", (label, optional)
        assert optional["computed_total"] == "115", (label, optional)
        assert "rollforward_residual" in optional["limitations"], (label, optional)
        assert "residual" not in optional, (label, optional)

    # Mandatory source unavailable: refusal, and never a published total.
    mandatory = _rollforward([_typed_absence(cells[0], "no_source_document")] + cells[1:])
    assert mandatory["status"] == "refused", mandatory
    assert mandatory["value"] is None, mandatory
    assert mandatory.get("computed_total") is None, mandatory

    # The distinction itself, in the obligation's own terms.
    assert mandatory["status"] != optional["status"]
    assert mandatory["value"] is None and optional["value"] is not None
