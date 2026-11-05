"""Industrials T06 — financial dossier obligations, enforced from recovered text.

This suite is the plan's own T06 home (section 6 assigns every T06 requirement to
``tests/test_industrials_financial_dossier.py``).  It opened with exactly ONE row,
``IND-R214``, and now covers six of the nine T06 obligations; each is here on the
same two grounds:

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

``IND-R201``, ``IND-R218`` and ``IND-SF04`` joined next, and how they got here is
worth stating because an earlier reading of it was wrong.  Measured against
``industrials_result_cash`` alone, none of the three separates a compliant case from a
violating one: ``IND-R201``'s "optional graph extension" is the theme graph, which
another owner holds; ``IND-R218``'s mispricing/probability/trade vocabulary occurs
nowhere in that package; ``IND-SF04``'s BOM/wafer/stage vocabulary likewise.  Those
measurements stand.  The inference drawn from them -- that the three obligations were
therefore not testable -- did not: Sol's CONTINUE ruling on carrier #7789 (comment
``5894912727``) scopes all five required-versus-optional rows, ``IND-D23`` and
``IND-R215`` included, to ONE user-facing capability at the ``financial_dossier.py``
surface.  A withheld conclusion is withheld where conclusions are PUBLISHED, and that
is not the cash derivation.  So the rows below the result-to-cash ones exercise
``assemble_evidence_view``, one composition over already-derived values, and the five
obligations are asserted there as one capability rather than five surfaces.

An anchor row is a claim that a test separates the compliant case from the violating
one, so a row is added only when that claim is true -- and, as those three show,
"true of this module" is not the same claim as "true of the capability".

Three T06 rows remain deliberately absent, and their absence is the honest signal
rather than an oversight: ``IND-D03`` needs the private content-role owner, and
``IND-D22``/``IND-R213`` need native correction lineage.  Neither seam is merged, and
neither is built here.

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

from engine.company_intelligence.financial_dossier import (
    WITHHELD_CONCLUSIONS,
    assemble_evidence_view,
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

# --------------------------------------------------------------------------------------
# The required-versus-optional evidence view.  Sol's CONTINUE ruling on carrier #7789
# (comment `5894912727`) commissions IND-D23, IND-R201, IND-R215, IND-R218 and IND-SF04 as
# ONE user-facing capability - "not five isolated anchors" - so the rows below exercise one
# composition (`assemble_evidence_view`) rather than five unrelated surfaces.
#
# Three of them (`IND-R201`, `IND-R218`, `IND-SF04`) are new anchors.  `IND-D23` and
# `IND-R215` already anchor on the result-to-cash rows above; the two dossier rows here are
# ADDITIONAL coverage under their own names, because the anchor those rows carry points at a
# test that exists and discriminates, and re-pointing it would trade unit coverage for page
# coverage rather than adding it.
# --------------------------------------------------------------------------------------


def _ready(name: str, value: str = "115") -> dict[str, object]:
    """A `derive_result_cash`-shaped result whose evidence is complete."""
    return {
        "status": "ready",
        "value": value,
        "limitations": [],
        "formula": "cash_rollforward",
        "formula_version": FORMULA_VERSION,
        "operand_refs": [f"synthetic:cell:{name}"],
        "receipt_ref": "synthetic:comparison:0000000000000000",
    }


def _refused(operand: str) -> dict[str, object]:
    """A result whose MANDATORY operand was unavailable: no value, typed reason."""
    return {
        "status": "refused",
        "value": None,
        "limitations": [f"operand_missing:{operand}"],
        "formula": "cash_rollforward",
        "formula_version": FORMULA_VERSION,
        "operand_refs": [],
        "receipt_ref": "synthetic:comparison:0000000000000000",
    }


def _limited(name: str) -> dict[str, object]:
    """A result whose OPTIONAL component was absent: supported total still stands.

    This is the shape ``derive_result_cash`` actually returns when ``closing_cash`` is
    omitted -- measured in ``test_ind_r215`` above, which is why the two rows can be
    asserted as one behaviour rather than two guesses.
    """
    return {
        "status": "limited",
        "value": "115",
        "limitations": ["rollforward_residual"],
        "formula": "cash_rollforward",
        "formula_version": FORMULA_VERSION,
        "operand_refs": [f"synthetic:cell:{name}"],
        "receipt_ref": "synthetic:comparison:0000000000000000",
    }


_PROSE = {"cash_story": ["cash_bridge"], "margin_story": ["margin"]}
_BOTH_EXTENSIONS = {"theme_graph": {"nodes": 3}, "consensus": {"eps_next_fy": "1.20"}}


def test_evidence_view_control_all_present() -> None:
    """The positive control, asserted in the same run as the five rows below.

    Twelve probe rows once read ``refused`` uniformly -- including the control -- because
    the metric names were wrong, and uniformity was the only tell.  A view that refused
    everything would satisfy every "is not ready" assertion in this file, so the case where
    nothing is missing is pinned FIRST: complete evidence must produce a complete page.
    """
    view = assemble_evidence_view(
        derivations={"cash_bridge": _ready("cash_bridge"), "margin": _ready("margin", "18.4")},
        prose=_PROSE,
        extensions=_BOTH_EXTENSIONS,
        business_model="manufacturing",
    )

    assert view["status"] == "ready", view
    assert [row["status"] for row in view["sections"].values()] == ["ready", "ready"]
    assert [row["status"] for row in view["prose"].values()] == ["ready", "ready"]
    assert view["withheld_conclusions"] == [], view
    assert view["limitations"] == [], view
    # The values are QUOTED, not recomputed: a view that re-derived them could agree here
    # by accident and disagree with the derivation anywhere else.
    assert view["sections"]["cash_bridge"]["value"] == "115"
    assert view["sections"]["margin"]["value"] == "18.4"


def test_ind_d23_page_verdict() -> None:
    """IND-D23, recovered original wording (r1 section 11), verbatim:

        | IND-D23 | Required cash/estimate operand unavailable |
        | Local typed absence; no zero or invented number, no all-page false success. |

    Three clauses.  ``test_ind_d23`` above proves the DERIVATION refuses; this row proves
    the PAGE built from it does not report success anyway -- the clause a unit-level test
    structurally cannot reach, since "all-page" is not a property of one derivation.
    """
    view = assemble_evidence_view(
        derivations={
            "cash_bridge": _refused("opening_cash"),
            "margin": _ready("margin", "18.4"),
        },
        prose=_PROSE,
        extensions=_BOTH_EXTENSIONS,
        business_model="manufacturing",
    )

    # Clause 1 - LOCAL.  The absence is scoped to what depends on it.  Asserted first,
    # because a view that simply refused the whole page would satisfy clauses 2 and 3 and
    # be useless: an operand this company never reported would erase its margin analysis.
    assert view["sections"]["margin"]["status"] == "ready", view
    assert view["sections"]["margin"]["value"] == "18.4"
    assert view["prose"]["margin_story"]["status"] == "ready", view

    # Clause 2 - TYPED ABSENCE, NO ZERO OR INVENTED NUMBER.  `value is None` and the reason
    # names the missing operand; `== 0` is asserted separately because a zero is the
    # specific wrong answer this obligation exists to forbid, and `not value` accepts it.
    section = view["sections"]["cash_bridge"]
    assert section["status"] == "refused", view
    assert section["value"] is None, view
    assert section["value"] != 0 and section["value"] != "0", view
    assert section["limitations"] == ["operand_missing:opening_cash"], view

    # Clause 3 - NO ALL-PAGE FALSE SUCCESS.  The page's own verdict, and the dependent
    # prose, both carry the absence.  A renderer reading `status` cannot present this as a
    # complete dossier.
    assert view["status"] == "incomplete", view
    assert view["prose"]["cash_story"]["status"] == "withheld", view
    assert view["prose"]["cash_story"]["blocked_by"] == ["cash_bridge"], view
    assert "section_not_ready:cash_bridge" in view["limitations"], view

    # Clause 3 again, with the prose support REMOVED.  Measured: a mutant that ignored
    # refused sections entirely when computing the page verdict still failed the assertion
    # above, because the withheld prose happened to reach the same answer by another route.
    # A refused section with nothing declared over it is the case where no other signal can
    # rescue the verdict - and it is the realistic one, since a caller declares prose only
    # for the sentences it actually writes.
    unsupported = assemble_evidence_view(
        derivations={
            "cash_bridge": _refused("opening_cash"),
            "margin": _ready("margin", "18.4"),
        },
        prose={"margin_story": ["margin"]},
        extensions=_BOTH_EXTENSIONS,
        business_model="manufacturing",
    )
    assert unsupported["prose"]["margin_story"]["status"] == "ready", unsupported
    assert unsupported["status"] == "incomplete", (
        "IND-D23: a refused section with no prose declared over it left the page reading as "
        "a complete dossier -- an all-page false success."
    )


def test_ind_r201() -> None:
    """IND-R201, recovered original wording (r2 section 11), verbatim:

        | IND-R201 | Qualified event facts; optional graph extension unavailable |
        | Core analysis can be qualified; no fake graph composition or full-vertical
        acceptance |

    The theme graph belongs to the shared-kernel owner (#7870) and is legitimately unbuilt
    here, which is exactly the state the obligation describes: the analysis must survive
    its absence WITHOUT the page claiming the full vertical.
    """
    view = assemble_evidence_view(
        derivations={"cash_bridge": _ready("cash_bridge"), "margin": _ready("margin", "18.4")},
        prose=_PROSE,
        extensions={"consensus": {"eps_next_fy": "1.20"}},
        business_model="manufacturing",
    )

    # Clause 1 - CORE ANALYSIS CAN BE QUALIFIED.  Every supported section and its prose
    # stay readable; the graph's absence does not propagate into the financial work.
    assert [row["status"] for row in view["sections"].values()] == ["ready", "ready"]
    assert [block["status"] for block in view["prose"].values()] == ["ready", "ready"]
    assert view["sections"]["cash_bridge"]["value"] == "115"

    # Clause 2 - NO FAKE GRAPH COMPOSITION.  The extension is reported ABSENT with a
    # reason, not synthesized, and not silently omitted from the view either: a key that
    # simply is not there is indistinguishable from one nobody asked for.
    assert view["extensions"]["theme_graph"] == {
        "state": "absent",
        "reason": "not_supplied",
    }, view
    assert "extension_absent:theme_graph" in view["limitations"], view

    # Clause 3 - NO FULL-VERTICAL ACCEPTANCE.  The page is usable and explicitly NOT a
    # complete one.  This is the clause that fails if `ready` is computed from refusals
    # alone: nothing here is refused, and the page still must not read as accepted.
    assert view["status"] == "qualified", view
    assert view["status"] != "ready", view


def test_ind_r215_dossier_view_distinctness() -> None:
    """IND-R215, recovered original wording (r2 section 11), verbatim:

        | IND-R215 | Mandatory source unavailable; optional source absent |
        | Distinct required refusal versus optional limitation; no invented data |

    ``test_ind_r215`` above proves the two cases stay distinct in the DERIVATION's status.
    This row proves they stay distinct in what the reader gets, which is the load-bearing
    half: an implementation can return two different status strings and still withhold the
    same prose for both, and then the distinction exists only in a field nobody renders.
    Measured on the first draft of this view, that was exactly the behaviour.
    """
    optional = assemble_evidence_view(
        derivations={"cash_bridge": _limited("cash_bridge"), "margin": _ready("margin", "18.4")},
        prose=_PROSE,
        extensions=_BOTH_EXTENSIONS,
        business_model="manufacturing",
    )
    mandatory = assemble_evidence_view(
        derivations={
            "cash_bridge": _refused("opening_cash"),
            "margin": _ready("margin", "18.4"),
        },
        prose=_PROSE,
        extensions=_BOTH_EXTENSIONS,
        business_model="manufacturing",
    )

    # Clause 1 - DISTINCT.  Three independent facts differ, so the two cases cannot be
    # collapsed by any one of them being wrong.
    assert optional["sections"]["cash_bridge"]["status"] == "limited"
    assert mandatory["sections"]["cash_bridge"]["status"] == "refused"
    assert optional["prose"]["cash_story"]["status"] == "qualified"
    assert mandatory["prose"]["cash_story"]["status"] == "withheld"
    assert optional["status"] == "qualified"
    assert mandatory["status"] == "incomplete"

    # Clause 2 - NO INVENTED DATA, on both sides of the distinction.  The optional case
    # publishes the supported total it actually derived; the mandatory case publishes
    # nothing.  A view that filled either one in would read as the other.
    assert optional["sections"]["cash_bridge"]["value"] == "115"
    assert optional["sections"]["cash_bridge"]["limitations"] == ["rollforward_residual"]
    assert mandatory["sections"]["cash_bridge"]["value"] is None
    assert mandatory["sections"]["cash_bridge"]["limitations"] == [
        "operand_missing:opening_cash"
    ]


def test_ind_r218() -> None:
    """IND-R218, recovered original wording (r2 section 11), verbatim:

        | IND-R218 | Operating improvement with absent market expectations |
        | Explain economics but withhold mispricing/probability/trade conclusion |

    The obligation is a pair of opposed duties: the economics must still be EXPLAINED, and
    the conclusion must be WITHHELD.  Either one alone is trivially satisfiable -- refuse
    everything, or publish everything -- so both halves are asserted on the same view.
    """
    view = assemble_evidence_view(
        derivations={"cash_bridge": _ready("cash_bridge"), "margin": _ready("margin", "18.4")},
        prose=_PROSE,
        extensions={"theme_graph": {"nodes": 3}},
        business_model="manufacturing",
    )

    # Clause 1 - EXPLAIN ECONOMICS.  The operating improvement is fully readable: absent
    # consensus is not a reason to stop reporting what the company did.
    assert [row["status"] for row in view["sections"].values()] == ["ready", "ready"]
    assert [block["status"] for block in view["prose"].values()] == ["ready", "ready"]
    assert view["sections"]["margin"]["value"] == "18.4"

    # Clause 2 - WITHHOLD THE CONCLUSION.  The obligation's own three words are asserted by
    # name, not just the count: `mispricing`, `probability` and `trade`.  Sol's ruling names
    # `valuation-gap`, `rank`, `entry` and `size` as well, so the withheld set is a superset
    # of the recovered wording - stricter than either, looser than neither.
    withheld = view["withheld_conclusions"]
    for conclusion in ("mispricing", "probability", "trade"):
        assert conclusion in withheld, (
            f"IND-R218: {conclusion!r} is not withheld with market expectations absent, so "
            f"the page could carry a conclusion it has no expectation to measure against."
        )
    assert set(withheld) == set(WITHHELD_CONCLUSIONS), withheld
    assert "conclusions_withheld:no_consensus" in view["limitations"], view

    # And the reason is the ABSENCE, not a blanket policy: with consensus present, nothing
    # is withheld.  Without this the row would pass against a module that always withholds
    # everything, which explains nothing about the obligation.
    with_consensus = assemble_evidence_view(
        derivations={"cash_bridge": _ready("cash_bridge"), "margin": _ready("margin", "18.4")},
        prose=_PROSE,
        extensions=_BOTH_EXTENSIONS,
        business_model="manufacturing",
    )
    assert with_consensus["withheld_conclusions"] == [], with_consensus


def test_ind_sf04() -> None:
    """IND-SF04, recovered original wording (W12 section 11), verbatim:

        | IND-SF04 | Service business with no physical manufacturing model |
        | Coherent financial/service view; no forced BOM, wafer measure or fake stage. |

    Every Industrials name is not a factory.  The violating behaviour is a template that
    attaches a production model to a services company because the sector schema has a slot
    for one.
    """
    service = assemble_evidence_view(
        derivations={"cash_bridge": _ready("cash_bridge")},
        prose={"cash_story": ["cash_bridge"]},
        extensions=_BOTH_EXTENSIONS,
        business_model="service",
        operating_model={
            "bom": ["synthetic-part-a"],
            "wafer_measure": "synthetic-starts",
            "stage": "synthetic-stage",
            "billable_headcount": 240,
        },
    )

    # Clause 1 - COHERENT FINANCIAL/SERVICE VIEW.  The financial sections assemble and the
    # SERVICE metric survives.  A view that answered SF04 by dropping the operating model
    # wholesale would pass clause 2 and leave the company undescribed.
    # `ready` here is deliberate and is the second half of a distinction the first draft
    # got wrong: a refused physical field came back `qualified`, i.e. every correctly-scoped
    # services page reported itself as partially evidenced.  A model mismatch is not an
    # evidence gap.  The refusal must therefore be DISCLOSED without degrading the verdict,
    # so both halves are asserted - disclosure below, verdict here.
    assert service["status"] == "ready", service
    assert "physical_model_refused:bom" in service["limitations"], service
    assert service["sections"]["cash_bridge"]["status"] == "ready"
    assert service["operating_model"]["billable_headcount"] == 240, service
    assert service["operating_model"]["business_model"] == "service"

    # Clause 2 - NO FORCED BOM, WAFER MEASURE OR FAKE STAGE.  All three named by the
    # obligation are refused BY NAME rather than dropped: a silently dropped key makes a
    # fabricated dependency indistinguishable from one nobody supplied.
    assert service["operating_model"]["refused_fields"] == ["bom", "stage", "wafer_measure"]
    for field in ("bom", "wafer_measure", "stage"):
        assert field not in service["operating_model"], service

    # The refusal is a property of the BUSINESS MODEL, not of the field names.  Without
    # this half the row would pass against a module that refuses those keys for every
    # company, which would be a different defect rather than this obligation.
    manufacturer = assemble_evidence_view(
        derivations={"cash_bridge": _ready("cash_bridge")},
        prose={"cash_story": ["cash_bridge"]},
        extensions=_BOTH_EXTENSIONS,
        business_model="manufacturing",
        operating_model={
            "bom": ["synthetic-part-a"],
            "wafer_measure": "synthetic-starts",
            "stage": "synthetic-stage",
            "billable_headcount": 240,
        },
    )
    assert manufacturer["operating_model"]["refused_fields"] == [], manufacturer
    assert manufacturer["operating_model"]["bom"] == ["synthetic-part-a"]
