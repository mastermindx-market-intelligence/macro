"""Dependency-binding tests for the synthetic Industrials T01 corpus."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from engine.company_intelligence.financial_dossier import DELIVERY_INPUT_VALIDATOR_VERSION
from tests.industrials_result_cash_helpers import (
    FIXTURE_NAMES,
    PLAN_REQUIREMENT_ANCHORS,
    case,
    cell,
    comparison,
    issuer_registry,
    publication_harness,
)


REQUIRED_FIXTURES = {
    "service_net_gross",
    "paired_expense_income",
    "cash_quarter_vs_half",
    "segment_recast",
    "same_number_two_headers",
    "preliminary_final",
    "filing_later",
    "both_basis_unknown",
    "source_only",
    "negative_cash",
    "mixed_sector_generation",
    "warm_rights_revoked",
    "logout_late_response",
    "ordinary_refresh_outage",
    "shared_query",
    "shared_owner_bundle",
    "foundation_only_proof",
}


def _validate(payload, *, registry=None, research_hosts=None):
    """Helper that always passes the test-only research-host policy.

    T05/T06 will replace this with the real host policy supplied by the
    ranking/gating programs.
    """
    from engine.company_intelligence.financial_dossier import validate_delivery_inputs

    if research_hosts is None:
        research_hosts = frozenset({"example.invalid"})
    return validate_delivery_inputs(
        payload,
        registry=registry,
        research_hosts=research_hosts,
    )


def test_ind_sf07():
    from tests.industrials_result_cash_helpers import case
    result = _validate(case('source_only'))
    assert result['live_admission'] == 'refused'
    assert result['research_usable'] is True
    assert 'accepted_binding_missing' in result['reasons']


def test_every_required_fixture_is_synthetic() -> None:
    assert REQUIRED_FIXTURES == FIXTURE_NAMES
    for name in sorted(REQUIRED_FIXTURES):
        assert case(name)["synthetic"] is True


def test_cell_requires_decimal_text() -> None:
    assert cell("12.3")["value"] == "12.3"
    with pytest.raises(TypeError):
        cell(12.3)
    with pytest.raises(TypeError):
        cell(True)


def test_comparison_contract_and_purpose_guard() -> None:
    first = cell("1", owner_ref="synthetic:cell:first")
    second = cell("2", owner_ref="synthetic:cell:second")
    receipt = comparison("same_period", [first, second])
    assert receipt["operand_refs"] == ["synthetic:cell:first", "synthetic:cell:second"]
    assert set(receipt["checked"]) == {
        "basis",
        "currency",
        "scale",
        "duration",
        "perimeter",
        "definition",
        "source_mode",
    }
    with pytest.raises(ValueError):
        comparison("unknown_purpose", [first])


def test_foundation_only_proof_negative_state() -> None:
    proof = case("foundation_only_proof")
    assert proof["semiconductor_accepted"] is True
    assert proof["industrials_witnesses"] == []
    assert proof["industrials_accepted"] is False


def test_route_unbound_client_causes_no_read() -> None:
    harness = publication_harness()
    assert harness.read_count == 0
    response = harness.client(entitled=False).get("anything")
    assert response == {"status": "unavailable", "reason": "route_unbound", "status_code": None}
    assert harness.read_count == 0


def test_publish_binds_owner_entry_points(tmp_path) -> None:
    from tests.industrials_result_cash_helpers import publication_harness

    harness = publication_harness()
    before = harness.read_count
    result = harness.publish({}, stage_dir=tmp_path)
    assert result["status"] == "ok"
    assert result["generation_id"].startswith("earnpriv_")
    assert result["pointer"]["generation_id"] == result["generation_id"]
    assert result["read_count"] > before


def test_run_refresh_binds_acquire_results_filing_with_ordinary_refresh_outage() -> None:
    from tests.industrials_result_cash_helpers import publication_harness

    harness = publication_harness()
    result = harness.run_refresh({}, fail_sources=["ordinary_refresh_outage"])
    assert result["status"] == "unavailable"
    assert result["reason"] == "refresh_source_failed"
    assert result["source"] == "ordinary_refresh_outage"


def test_run_refresh_empty_fail_sources_returns_owner_ok_shape() -> None:
    """N3 (T01 round-5): the seam's own shape, not the seam-unbound refusal.

    With ``fail_sources=()`` the harness must serve the SEC submissions +
    archive + exhibit URLs that ``acquire_results_filing`` reaches for the
    synthetic CIK, and the seam must return every field the owner publishes
    on a real run — ``cik``, ``accession``, ``form``, ``filing_date``,
    ``acceptance_datetime``, ``report_date``, ``exhibit_url``, ``items``.
    """
    harness = publication_harness()
    result = harness.run_refresh({})
    assert result["status"] == "ok"
    for field in (
        "cik",
        "accession",
        "form",
        "filing_date",
        "acceptance_datetime",
        "report_date",
        "exhibit_url",
        "items",
    ):
        assert field in result, (field, sorted(result))
    assert result["cik"] == "0000987654"
    assert result["accession"] == "0000987654-26-000001"
    assert result["form"] == "8-K"
    # The seam constructs the exhibit URL as
    #   f"{archive_base}/{filename}" = https://www.sec.gov/Archives/edgar/data/987654/<acc_nodash>/synthetic-exhibit.htm
    # from the SEC submissions primaryDocument field; the harness serves any
    # URL ending with that filename, so the returned URL is the live archive
    # URL, not a re-derivation of the input document URL.
    assert result["exhibit_url"].endswith("/synthetic-exhibit.htm")


def test_run_refresh_fail_sources_is_causal_not_coincidental() -> None:
    """N3 (T01 round-5): a fail_source name causes the typed refusal; deleting
    the entry flips the result to the owner's ok shape on the very next call.

    The OLD harness returned ``refresh_source_failed`` because the seam's
    archive SGML map was empty — not because the named source failed. This
    test pins the new contract: the same harness instance, same fixtures,
    only the ``fail_sources`` argument changes between the two assertions.
    """
    harness = publication_harness()

    refused = harness.run_refresh({}, fail_sources=["ordinary_refresh_outage"])
    assert refused["status"] == "unavailable"
    assert refused["reason"] == "refresh_source_failed"
    assert refused["source"] == "ordinary_refresh_outage"
    assert "503" in refused["detail"], refused

    ok = harness.run_refresh({}, fail_sources=[])
    assert ok["status"] == "ok", ok
    assert ok["cik"] == "0000987654"
    assert ok["accession"] == "0000987654-26-000001"
    assert ok["exhibit_url"].endswith("/synthetic-exhibit.htm")


def test_members_is_not_an_empty_stub_after_enrollment() -> None:
    """Anti-vacuity guard for T02's mandated preservation assertion.

    `members()` shipped as `return set()`, so `before <= h.members()` could never
    fail. This pins the property that makes that assertion able to grade anything:
    after a successful refresh the harness reports the cases it actually holds.
    """
    harness = publication_harness()
    assert harness.members() == set()
    harness.run_refresh({"case_a": "edition_1", "case_b": "edition_1"})
    assert harness.members() == {"case_a", "case_b"}


def test_ordinary_refresh_preserves_unrelated_and_carried_case() -> None:
    """The frozen plan's T02 two-run test (plan blob a5462dc7, section T02).

    The plan's own snippet snapshots `before = h.members()` BEFORE the first
    refresh, where it is necessarily empty and `before <= h.members()` holds for
    free. The snapshot is taken here after enrollment instead, which is the only
    form in which the assertion can fail.
    """
    harness = publication_harness()
    harness.run_refresh({"case_a": "edition_1", "case_b": "edition_1"})
    before = harness.members()
    assert before == {"case_a", "case_b"}

    harness.run_refresh({"case_b": "edition_2"}, fail_sources=("case_a",))

    assert before <= harness.members()
    assert harness.get("case_a")["edition"] == "edition_1"
    assert harness.get("case_b")["edition"] == "edition_2"


def test_carried_case_is_marked_stale_and_never_restamped() -> None:
    """A source failure may mark a carried object stale, never restamp it as newly
    observed (plan T02). The observation stamp comes from the owner's result, so a
    silent re-observation would move it."""
    harness = publication_harness()
    harness.run_refresh({"case_a": "edition_1"})
    observed = harness.get("case_a")["observed_acceptance"]
    assert observed, harness.get("case_a")

    harness.run_refresh({"case_a": "edition_2"}, fail_sources=("case_a",))

    carried = harness.get("case_a")
    assert carried["edition"] == "edition_1", carried
    assert carried["stale"] is True, carried
    assert carried["observed_acceptance"] == observed, carried


def test_refused_case_with_no_predecessor_is_never_invented() -> None:
    """A failing source must not conjure an enrollment. The refused case stays
    absent and `get` raises rather than answering with a blank record."""
    harness = publication_harness()
    result = harness.run_refresh({"case_a": "edition_1"}, fail_sources=("case_a",))
    assert result["status"] == "unavailable"
    assert result["source"] == "case_a"
    assert harness.members() == set()
    with pytest.raises(KeyError):
        harness.get("case_a")


def test_per_case_fail_source_is_causal_not_global() -> None:
    """`fail_sources` names CASES, not the whole refresh: an unnamed case in the
    same call still advances, and dropping the name flips the named case to
    advancing on the very next call."""
    harness = publication_harness()
    harness.run_refresh({"case_a": "edition_1", "case_b": "edition_1"})

    harness.run_refresh(
        {"case_a": "edition_2", "case_b": "edition_2"}, fail_sources=("case_a",)
    )
    assert harness.get("case_a")["edition"] == "edition_1"
    assert harness.get("case_b")["edition"] == "edition_2"
    assert harness.get("case_b")["stale"] is False

    harness.run_refresh({"case_a": "edition_2"}, fail_sources=())
    advanced = harness.get("case_a")
    assert advanced["edition"] == "edition_2", advanced
    assert advanced["stale"] is False, advanced


def test_get_returns_a_copy_that_cannot_rewrite_harness_state() -> None:
    """An assertion must not be able to pass by editing the evidence it reads."""
    harness = publication_harness()
    harness.run_refresh({"case_a": "edition_1"})
    record = harness.get("case_a")
    record["edition"] = "edition_99"
    record["stale"] = True
    assert harness.get("case_a")["edition"] == "edition_1"
    assert harness.get("case_a")["stale"] is False


def test_top_level_refusal_reasons_are_closed_set_or_unknown_field() -> None:
    from engine.company_intelligence.financial_dossier import (
        DELIVERY_REFUSAL_REASONS,
        validate_delivery_inputs,
    )
    from tests.industrials_result_cash_helpers import issuer_registry

    registry = issuer_registry()
    # Walk every fixture plus a few hand-rolled payloads to exercise every code path.
    fixtures = [
        case(name) for name in sorted(__import__("tests.industrials_result_cash_helpers", fromlist=["FIXTURE_NAMES"]).FIXTURE_NAMES)
    ]
    payloads: list[dict] = list(fixtures)
    # malformed identity (missing fields)
    payloads.append({"synthetic": True, "identity": {}, "release_binding": None, "private_binding": None})
    # identity_not_registered (well-formed but pair not in registry)
    not_registered = case("source_only")
    not_registered["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000320193"},
    }
    payloads.append(not_registered)
    for payload in payloads:
        result = _validate(payload, registry=registry)
        for reason in result["reasons"]:
            assert reason in DELIVERY_REFUSAL_REASONS or reason.startswith("unknown_field:"), (
                f"unrecognized top-level reason: {reason!r}"
            )


def test_registered_pair_with_accepted_bindings_is_admissible() -> None:
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000987654"},
    }
    payload["release_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:release:candidate",
        "revision": "r1",
        "digest": "0" * 64,
    }
    payload["private_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:private:candidate",
        "revision": "r1",
        "digest": "0" * 64,
        "rights_state": "public_primary",
    }
    payload["cross_subject_join"] = None
    result = _validate(payload, registry=issuer_registry())
    assert result["live_admission"] == "admissible"
    assert result["reasons"] == []


def test_wellformed_cik_outside_synthetic_namespace_is_unresolved() -> None:
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "acme:northgate",
        "external_ids": {"cik": "0000987654"},
    }
    result = _validate(payload, registry=issuer_registry())
    assert "identity_unresolved" in result["reasons"]
    identity = result["bindings"]["identity"]
    assert identity["status"] == "unresolved"
    assert identity["reason"] == "identity_not_registered"


def test_eleven_digit_cik_fails_length_check() -> None:
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "00009876541"},
    }
    result = _validate(payload, registry=issuer_registry())
    assert "identity_unresolved" in result["reasons"]
    identity = result["bindings"]["identity"]
    assert identity["reason"] == "identity_unresolved"


def test_unknown_delivery_input_key_refused() -> None:
    payload = case("source_only")
    payload["unexpected"] = True
    result = _validate(payload)
    assert DELIVERY_INPUT_VALIDATOR_VERSION == "v1"
    assert result["live_admission"] == "refused"
    assert "unknown_field:unexpected" in result["reasons"]


def test_caller_authored_k1_join_refused() -> None:
    payload = case("source_only")
    payload["cross_subject_join"] = {"claimed_binding": "caller-authored"}
    result = _validate(payload)
    assert result["live_admission"] == "refused"
    assert "unsupported_cross_subject_join" in result["reasons"]


def test_unregistered_realistic_cik_is_not_identity() -> None:
    # Renamed in step 5: this exercises the CIK length boundary (11 digits fail).
    # The dedicated length check lives in test_eleven_digit_cik_fails_length_check.
    payload = case("source_only")
    payload["identity"] = {"company_id": "synthetic:northgate", "external_ids": {"cik": "00009876541"}}
    result = _validate(payload)
    assert result["live_admission"] == "refused"
    assert "identity_unresolved" in result["reasons"]


def test_realistic_cik_with_unknown_pair_is_identity_not_registered() -> None:
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000320193"},
    }
    result = _validate(payload, registry=issuer_registry())
    assert result["live_admission"] == "refused"
    identity = result["bindings"]["identity"]
    assert identity["status"] == "unresolved"
    assert identity["reason"] == "identity_not_registered"


def test_registry_generator_is_materialized_once_no_contradiction() -> None:
    """N4 (T01 round-5): a generator registry must not contradict itself.

    The OLD harness materialized ``frozenset(registry)`` inside
    ``_check_identity`` — every call after the first exhausted the generator
    and the second ``bindings.identity`` read answered
    ``identity_not_registered`` even though the FIRST identity read had
    answered ``resolved``. Pin the new contract: the registry is materialized
    ONCE at entry, so a generator caller observes the SAME answer in both
    ``live_admission`` and ``bindings.identity``.
    """
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000987654"},
    }
    payload["release_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:release:candidate",
        "revision": "r1",
        "digest": "0" * 64,
    }
    payload["private_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:private:candidate",
        "revision": "r1",
        "digest": "0" * 64,
        "rights_state": "public_primary",
    }

    registry = iter(list(issuer_registry()))  # iterator, single-pass
    result = _validate(payload, registry=registry)

    assert result["live_admission"] == "admissible", result
    assert result["bindings"]["identity"]["status"] == "resolved", result["bindings"]
    # No contradiction: identity is resolved AND live_admission is admissible.
    assert "identity_unresolved" not in result["reasons"]


def test_missing_registry_resolves_no_identity() -> None:
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000987654"},
    }
    result = _validate(payload)
    assert result["bindings"]["identity"]["status"] == "unresolved"
    assert result["bindings"]["identity"]["reason"] == "identity_not_registered"


def test_owner_ref_with_foreign_namespace_is_refused() -> None:
    payload = case("source_only")
    payload["release_binding"] = {
        "status": "accepted",
        "owner_ref": "foreign:thing:registered",
        "revision": "r1",
        "digest": "0" * 64,
    }
    payload["private_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:private:candidate",
        "revision": "r1",
        "digest": "0" * 64,
    }
    result = _validate(payload)
    assert result["live_admission"] == "refused"
    release = result["bindings"]["release_binding"]
    assert release["status"] == "unavailable"
    assert release["reason"] == "owner_namespace_unregistered"


def test_uppercase_digest_is_digest_malformed() -> None:
    payload = case("source_only")
    payload["release_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:release:candidate",
        "revision": "r1",
        "digest": "A" * 64,
    }
    payload["private_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:private:candidate",
        "revision": "r1",
        "digest": "0" * 64,
    }
    result = _validate(payload)
    assert result["live_admission"] == "refused"
    release = result["bindings"]["release_binding"]
    assert release["status"] == "unavailable"
    assert release["reason"] == "digest_malformed"


# ---------------------------------------------------------------------------
# Plan-named requirement anchors (IND-D02, IND-D06) and the test that makes the
# frozen plan's traceability table gradeable.
#
# `test_ind_sf07` above is one of only two anchors the plan's table named that
# actually existed before 2026-09-27 -- and it existed because the plan also
# froze its BODY, not because the table named it.  See
# `DSC:A-PLANS-TRACEABILITY-TABLE-IS-NOT-COVERAGE` and the map's own commentary
# in `tests/industrials_result_cash_helpers.py`.
# ---------------------------------------------------------------------------


def _admissible_payload() -> dict:
    """The payload `test_registered_pair_with_accepted_bindings_is_admissible`
    proves clean: a registered pair with both bindings accepted and no join."""
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000987654"},
    }
    payload["release_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:release:candidate",
        "revision": "r1",
        "digest": "0" * 64,
    }
    payload["private_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:private:candidate",
        "revision": "r1",
        "digest": "0" * 64,
        "rights_state": "public_primary",
    }
    return payload


def test_ind_d02(tmp_path) -> None:
    """IND-D02 — a new curation payload on the current GMI schema and store is
    refused until the shared native schema, persistence AND the reader
    round-trip are all admitted.

    The requirement is a CONJUNCTION, which is exactly how it can be
    half-satisfied and read as done.  Persistence is admitted here: ``publish``
    validates a locally built staging tree, freezes one generation, and the
    store records the read.  A delivery claim resting on that alone would look
    satisfied.  The reader round-trip is NOT admitted -- the route is unbound for
    an entitled client as much as an unentitled one, and no store read happens
    behind that refusal -- and the curation payload itself is still refused by
    the delivery-input validator with a reason from the closed set.

    Research continues throughout: ``research_usable`` stays True, which is the
    half of the requirement that must NOT be over-enforced.
    """
    harness = publication_harness()

    published = harness.publish({}, stage_dir=tmp_path)
    assert published["status"] == "ok", published
    assert published["generation_id"].startswith("earnpriv_"), published
    assert published["read_count"] > 0, published        # persistence admitted

    before = harness.read_count
    for entitled in (False, True):
        response = harness.client(entitled=entitled).get("anything")
        assert response["status"] == "unavailable", (entitled, response)
        assert response["reason"] == "route_unbound", (entitled, response)
    # A refusal that read the store anyway would be a partial round-trip
    # masquerading as none.
    assert harness.read_count == before, harness.read_count

    admission = _validate(case("source_only"), registry=issuer_registry())
    assert admission["live_admission"] == "refused", admission
    assert "accepted_binding_missing" in admission["reasons"], admission
    assert admission["research_usable"] is True, admission


def test_ind_d06() -> None:
    """IND-D06 — a caller-declared cross-type K1 join: the required composition
    refuses, while the optional exclusions and the denominator stay VISIBLE.

    The refusal must be surgical.  Built on the payload that is otherwise fully
    admissible, adding the join produces exactly ONE reason, and it withdraws
    nothing the caller could still legitimately read: each binding keeps
    reporting its own accepted / resolved state, and ``research_usable`` is
    unchanged from the identical payload without the join.  A validator that
    answered a refused composition by blanking its bindings, by adding
    collateral reasons, or by dropping research usability would satisfy the
    refusal assertion and fail these -- which is the failure mode the
    requirement's second clause exists to prevent.
    """
    base = _admissible_payload()
    without_join = _validate(base, registry=issuer_registry())
    assert without_join["live_admission"] == "admissible", without_join
    assert without_join["reasons"] == [], without_join

    joined = dict(base)
    joined["cross_subject_join"] = {"claimed_binding": "caller-authored"}
    result = _validate(joined, registry=issuer_registry())

    assert result["live_admission"] == "refused", result
    assert result["reasons"] == ["unsupported_cross_subject_join"], result
    # Exclusions and denominator remain visible.
    assert result["bindings"]["release_binding"] == (
        without_join["bindings"]["release_binding"]
    ), result
    assert result["bindings"]["private_binding"] == (
        without_join["bindings"]["private_binding"]
    ), result
    assert result["bindings"]["identity"] == without_join["bindings"]["identity"], result
    assert result["research_usable"] == without_join["research_usable"], result


def test_every_plan_named_requirement_anchor_exists() -> None:
    """The frozen plan's traceability table, made gradeable.

    This is the enforcing half of ``PLAN_REQUIREMENT_ANCHORS``.  Before it
    existed, the table was prose on a research branch: 13 of the 15 anchors it
    named for T01 and T04 did not exist, both tasks were merged and CI-green, and
    nothing in the repository could resolve a single row -- a suite run names
    FILES, so a missing test is not a failing test.

    Resolution is by AST rather than by import or ``getattr`` so a row cannot be
    satisfied by a name that merely happens to be reachable, and so a syntax
    error in a suite surfaces here as a failure rather than a collection skip.
    """
    import ast

    repo_root = Path(__file__).resolve().parent.parent
    seen: dict[str, set[str]] = {}
    for requirement, (relative_path, test_name) in sorted(
        PLAN_REQUIREMENT_ANCHORS.items()
    ):
        suite_path = repo_root / relative_path
        assert suite_path.is_file(), f"{requirement}: no such suite {relative_path}"
        if relative_path not in seen:
            tree = ast.parse(suite_path.read_text(encoding="utf-8"), filename=str(suite_path))
            seen[relative_path] = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
        assert test_name in seen[relative_path], (
            f"{requirement}: the plan assigns {relative_path}::{test_name}, "
            f"which does not exist. A missing anchor is invisible to a suite run "
            f"-- `pytest {relative_path}::{test_name}` reports `no tests ran`, "
            f"not a failure -- so it is asserted here instead."
        )

    # The map is a claim about coverage, so its own shape is asserted too: an
    # empty or silently-truncated map would pass every loop above.
    assert len(PLAN_REQUIREMENT_ANCHORS) == 18, sorted(PLAN_REQUIREMENT_ANCHORS)
    assert all(
        requirement.startswith("IND-") for requirement in PLAN_REQUIREMENT_ANCHORS
    ), sorted(PLAN_REQUIREMENT_ANCHORS)


_REQUIREMENT_INDEX = "research/industrials/first_vertical_program/requirement_index.md"
_INDEX_ROW = re.compile(
    r"^\|\s*(IND-[A-Z]+\d+)\s*\|\s*(T\d\d)\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*"
    r"\|\s*([A-Z_]+)\s*\|$"
)


def _read_requirement_index() -> dict[str, tuple[str, str, str, str]]:
    """Return ``{requirement: (task, test_file, test_name, anchor_basis)}``."""
    repo_root = Path(__file__).resolve().parent.parent
    path = repo_root / _REQUIREMENT_INDEX
    assert path.is_file(), (
        f"{_REQUIREMENT_INDEX} is missing. The anchor map's only external "
        f"authority is that file; without it a row asserts nothing but itself."
    )
    rows: dict[str, tuple[str, str, str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _INDEX_ROW.match(line.strip())
        if match is None:
            continue
        requirement, task, test_file, test_name, basis = match.groups()
        assert requirement not in rows, f"{requirement}: duplicated index row"
        rows[requirement] = (task, test_file, test_name, basis)
    return rows


def test_anchor_map_agrees_with_the_recovered_requirement_index() -> None:
    """An anchor row may not invent the requirement it claims to enforce.

    ``test_every_plan_named_requirement_anchor_exists`` above proves each row
    points at a test that EXISTS.  It cannot prove the row is honest, because
    the frozen plan's traceability table is not in this repository: a row naming
    an id the plan never assigned, or pointing at the suite of a different task,
    resolves exactly as cleanly as a correct one.

    The missing authority is the obligation's text.  Measured 2026-09-29, of the
    56 ids the plan names, 41 appear NOWHERE in this tree -- no spec, no doc, no
    fixture, no test -- because the requirement texts are inherited "unchanged
    from r1/r2/W12" and those specifications are not vendored here.  The 15 that
    did appear were exactly T01's and T04's, and only because landed code cites
    them.  So an anchor for any of the other 41 could not be enforcing a
    requirement; it would be inventing one, and nothing in CI would notice.

    UPDATED 2026-09-29: "absent from this tree" turned out NOT to mean lost.  Sol's
    CONTINUE ruling (#7789 comment 5894127980) recovered r1/r2/W12 from the original
    branch history, so the obligation texts are readable at named blobs even though
    they are still vendored at no path on ``main``.  That adds a fourth and stronger
    basis, ``RECOVERED_ORIGINAL``, which quotes the obligation itself rather than
    reconstructing it from a ruling or from landed code.  The barrier below is
    UNCHANGED and still fail-closed: a row migrates off ``NO_SOURCE`` only in a
    change that actually enforces it, one row at a time, never in a bulk edit.

    This binds the map to ``research/industrials/first_vertical_program/
    requirement_index.md``, which carries the plan's rows verbatim plus a declared
    ``anchor_basis`` per requirement.  A ``NO_SOURCE`` requirement may not be
    anchored, so extending coverage requires naming a real source in the same
    change instead of adding one line to a dict.
    """
    index = _read_requirement_index()
    assert len(index) == 56, f"expected the plan's 56 rows, parsed {len(index)}"

    assert {
        "RULING",
        "LANDED_BEHAVIOUR",
        "RECOVERED_ORIGINAL",
        "NO_SOURCE",
    } >= {row[3] for row in index.values()}, sorted(
        {row[3] for row in index.values()}
    )
    sourced = {r for r, row in index.items() if row[3] != "NO_SOURCE"}
    unsourced = {r for r, row in index.items() if row[3] == "NO_SOURCE"}
    # Derived, not a second hard-coded constant: clause 4 below binds `sourced`
    # to the anchor map, whose own size the sibling test asserts, so the count of
    # unsourced requirements follows from the plan's 56 rows.
    assert len(sourced) + len(unsourced) == 56, (sorted(sourced), sorted(unsourced))

    # 1. Every anchored requirement is one the plan actually named.
    for requirement in sorted(PLAN_REQUIREMENT_ANCHORS):
        assert requirement in index, (
            f"{requirement} is anchored but the plan's table never names it; "
            f"an anchor for an id outside the frozen scope is not coverage."
        )

    # 2. The anchor's suite and test name are the plan's own, not a paraphrase.
    for requirement, (relative_path, test_name) in sorted(
        PLAN_REQUIREMENT_ANCHORS.items()
    ):
        _task, planned_file, planned_test, _basis = index[requirement]
        assert relative_path == planned_file, (
            f"{requirement}: anchored to {relative_path}, plan assigns {planned_file}"
        )
        assert test_name == planned_test, (
            f"{requirement}: anchored to {test_name}, plan assigns {planned_test}"
        )

    # 3. The barrier this test exists for: no requirement whose obligation text
    #    nobody holds may be claimed as covered.
    invented = sorted(set(PLAN_REQUIREMENT_ANCHORS) & unsourced)
    assert not invented, (
        f"anchored with anchor_basis=NO_SOURCE: {invented}. The obligation's text "
        f"is not reachable from this repository, so the row would assert a "
        f"requirement rather than enforce one. Supply a source in "
        f"{_REQUIREMENT_INDEX} in the same change, or leave it unanchored."
    )

    # 4. The converse, so the index cannot claim a source that nothing enforces.
    assert sourced == set(PLAN_REQUIREMENT_ANCHORS), (
        f"index/anchor disagreement: sourced-but-unanchored="
        f"{sorted(sourced - set(PLAN_REQUIREMENT_ANCHORS))}, "
        f"anchored-but-unsourced={sorted(set(PLAN_REQUIREMENT_ANCHORS) - sourced)}"
    )

    # 5. A RULING basis names a ruling that has to exist.
    repo_root = Path(__file__).resolve().parent.parent
    ruling = repo_root / (
        "research/industrials/first_vertical_program/rulings/"
        "R-IND-2026-09-27-requirement-anchors.md"
    )
    by_ruling = sorted(r for r, row in index.items() if row[3] == "RULING")
    assert by_ruling == ["IND-D08", "IND-D09", "IND-D10", "IND-R208"], by_ruling
    assert ruling.is_file(), f"anchor_basis=RULING for {by_ruling} but {ruling} is absent"
