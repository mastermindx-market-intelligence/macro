"""Industrials T06 — financial dossier obligations, enforced from recovered text.

This suite is the plan's own T06 home (section 6 assigns every T06 requirement to
``tests/test_industrials_financial_dossier.py``).  It opens with exactly ONE row,
``IND-R214``, because that is the only T06 obligation whose behaviour is reachable
today:

* Its authority is the RECOVERED ORIGINAL wording, not a paraphrase.  Sol's
  CONTINUE ruling on carrier #7789 (comment ``5894127980``) restored the r1/r2/W12
  corpus from the original branch history; ``IND-R214`` is r2 blob
  ``9c98e106b954d0a48610afad418de2a9eeb1e58b`` section 11, quoted verbatim below.
* Its subject is ``build_comparison_receipt``, which is MERGED in
  ``engine.fundamental_forensics.industrials_result_cash`` (T04).  So it needs no
  issuer binding (#7905), no entitlement or private transport (#7870) and none of
  T05's information-time editions, which stay PARKED.

The other eight T06 rows are deliberately absent, and their absence is the honest
signal rather than an oversight: ``IND-D03`` needs the private content-role owner,
``IND-D22``/``IND-R213`` need native correction lineage, and ``IND-D23``,
``IND-R201``, ``IND-R215``, ``IND-R218`` and ``IND-SF04`` were not discriminated in
this change.  An anchor row is a claim that a test separates the compliant case
from the violating one, so a row is added only when that claim is true.

Every fixture is synthetic: invented issuers, ``example.invalid`` sources, no real
Exponent or Pentair figure.
"""

from __future__ import annotations

import pytest

from engine.fundamental_forensics.industrials_result_cash import (
    FORMULA_VERSION,
    build_comparison_receipt,
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
