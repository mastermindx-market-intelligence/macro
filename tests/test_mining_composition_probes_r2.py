"""Opus R2 probes for PR #7950 — frozen RED at ac2db290 (R-MIN-04). Seat amendment: probe C keys
withdrawal on the case's omissions (research-usability, R-MIN-30/31), not on limitation codes,
because the domain file itself declares `stream_threshold_unknown` for the rare-earth slice."""
from engine.market_ontology import mining_theme_research as C
from engine.market_ontology.mining_dependency_binding import OMISSION_TO_LIMITATION
from tests.mining_casebook import CASE_NAMES, synthetic_case

def _c(n):
    c = synthetic_case(n); return C.compose_mining_research(c.query, c.bundle)

def test_r2_a_leg_values_never_synthesised():
    r = _c("copper_complete")
    for row in r["expectations"]:
        for leg in ("earlier_point_estimate", "later_actual"):
            assert (row[leg] or {}).get("value") not in ("quarter", 0, "", None), (leg, row[leg])
        assert row["earlier_point_estimate"]["value"] != row["later_actual"]["value"]

def test_r2_b_withdrawn_cases_publish_no_expectation_row():
    for n in ("denied_source", "source_only", "changed_source", "missing_issuer"):
        assert _c(n)["expectations"] == [], (n, len(_c(n)["expectations"]))

def test_r2_c_suppression_invariant_holds_for_every_case():
    for n in CASE_NAMES:
        case = synthetic_case(n)
        r = C.compose_mining_research(case.query, case.bundle)
        withdrawn = bool(case.bundle.omissions)
        mapped = {OMISSION_TO_LIMITATION[o] for o in case.bundle.omissions}
        assert bool(r["economics"]["native_blocks"]) == (not withdrawn), (n, r["economics"]["native_blocks"])
        assert mapped <= set(r["limitations"]), (n, mapped, r["limitations"])
        if withdrawn:
            assert r["expectations"] == [], (n, len(r["expectations"]))
        else:
            assert "missing_derivation" not in r["limitations"], (n, r["limitations"])

def test_r2_d_qualified_case_mints_no_definition_unqualified():
    r = _c("copper_complete")
    assert [l for l in r["limitations"] if l.startswith("definition_unqualified:")] == []

def test_r2_e_industry_total_unknown_truthful_polarity():
    r = _c("rare_earth_complete")
    assert r["authorized_coverage"]["industry_total"] is None
    assert "industry_total_unknown" in r["limitations"]

def test_r2_f_expectation_rows_bind_a_real_subject_identity():
    r = _c("copper_complete")
    assert all(row["stable_subject_id"] != "subject:unknown" for row in r["expectations"]), \
        [row["stable_subject_id"] for row in r["expectations"]]
