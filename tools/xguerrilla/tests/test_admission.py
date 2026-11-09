"""Admission-chain regression laws: cost order, measured ceiling, no allocation.

Everything here is records and synthetic slots — no domain, no mailbox, no proxy,
no box and no browser is touched. These assertions therefore qualify the *chain*,
not any real deployment: a passing suite says the refusals fire in the right order
with the right numbers, not that a box has room or an account exists.
"""

from __future__ import annotations

import json

import pytest

from xguerrilla import admission, net

NOW = 1_000_000.0
GB = 1024 * 1024 * 1024


# ---------------------------------------------------------------------------
# Fixtures: one box, one cohort, everything synthetic
# ---------------------------------------------------------------------------

def headroom(**over) -> admission.Headroom:
    """A synthetic box with headroom to spare: memory seats 9, processes seat 100.

    Not a reading of any real box — the numbers are chosen so the declared
    ceiling of 6 is the binding term, which is what makes an override visible.
    """
    base: dict = dict(
        measured_at=NOW - 5,
        memory_total_bytes=16 * GB,
        memory_available_bytes=9 * GB,
        browser_resident_bytes=1 * GB,
        process_limit=4000,
        process_in_use=1000,
        browser_processes=30,
        memory_basis="free_inactive_speculative",
        reserve_bytes=0,
    )
    base.update(over)
    return admission.Headroom(**base)


def enumeration(**over) -> admission.Enumeration:
    """A synthetic census of the synthetic box: nothing observed, schema pinned.

    A clean default so every pre-existing law keeps firing on the ceilings it
    was written for; the enumeration laws below build their own. Nothing here
    is a reading of any real box.
    """
    base: dict = dict(
        schema_version=1,
        host="synthetic-box",
        taken_at=NOW - 5,
        collection_status="complete",
        observed_ports=frozenset(),
        tool_sha256="ab" * 32,
    )
    base.update(over)
    return admission.Enumeration(**base)


def box_with(head: admission.Headroom | None, *, declared: int = 6,
             max_age: float = 900.0,
             census: admission.Enumeration | None = None,
             declared_ports: frozenset[int] = frozenset(),
             baseline_ports: frozenset[int] = frozenset()) -> admission.Box:
    """A box descriptor around an explicit measurement — ``None`` means nobody read it.

    ``census=None`` substitutes the clean synthetic census above. A box nobody
    enumerated is described by building the ``Box`` directly, which is what the
    ``enumeration_not_collected`` law does.
    """
    if census is None:
        census = enumeration()
    return admission.Box("synthetic-box", declared, head, max_age, census,
                         declared_ports, baseline_ports)


def one_box(*, declared: int = 6) -> admission.Box:
    """The synthetic box above, declared at the spec's six."""
    return box_with(headroom(), declared=declared)


class Rig:
    """A complete, admitting cohort for one box. Override any stage per test."""

    def __init__(self, n: int = 6, slots: int = 16,
                 descriptor: admission.Box | None = None) -> None:
        self.handles = [f"kid.{i:02d}" for i in range(n)]
        self.domains = [
            admission.DomainRecord(
                domain=f"{h.replace('.', '-')}.example",
                handle=h,
                verified=True,
                expires_at=NOW + 10 ** 7,
            )
            for h in self.handles
        ]
        self.identities = [
            admission.Identity(
                handle=d.handle,
                address=f"ops@{d.domain}",
                domain=d.domain,
                recovery_owner="chairman",
                verified=True,
            )
            for d in self.domains
        ]
        self.custody = [
            admission.Custody(
                handle=h,
                totp_enrolled=True,
                recovery_custodian="chairman",
                recovery_codes_held=True,
            )
            for h in self.handles
        ]
        self.accounts = [
            admission.Account(handle=h, account_id=f"acct-{i:02d}", admitted=True)
            for i, h in enumerate(self.handles)
        ]
        self.slots = [
            net.Slot(
                host=f"proxy-{i:02d}.invalid",
                port=10000 + i,
                user="fake-user",
                password=f"fake-password-{i:02d}",
                name=f"synthetic-pool-{i:02d}",
            )
            for i in range(slots)
        ]
        self.box = descriptor or one_box()

    def preflight(self, **over) -> admission.Admission:
        kwargs: dict = dict(
            handles=self.handles,
            domains=self.domains,
            identities=self.identities,
            custody=self.custody,
            slots=self.slots,
            accounts=self.accounts,
            box=self.box,
            now=NOW,
        )
        kwargs.update(over)
        return admission.preflight(**kwargs)


def refuse(rig: Rig, **over) -> admission.AdmissionRefused:
    with pytest.raises(admission.AdmissionRefused) as caught:
        rig.preflight(**over)
    return caught.value


# ---------------------------------------------------------------------------
# 1. the happy path, and what success actually contains
# ---------------------------------------------------------------------------

def test_clean_cohort_admits_all_six_stages():
    admitted = Rig().preflight()
    assert tuple(a.stage for a in admitted.artifacts) == admission.STAGES
    assert admitted.grant.handles == tuple(f"kid.{i:02d}" for i in range(6))
    assert admitted.grant.effective_ceiling == 6
    assert admitted.grant.chain_digest == admitted.artifacts[-1].digest


@pytest.mark.parametrize("fields,code", [
    ({"schema_version": 2}, "schema_unsupported"),
    ({"schema_version": 1.0}, "schema_unsupported"),
    ({"schema_version": True}, "schema_unsupported"),
    ({"collection_status": "incomplete"}, "enumeration_incomplete"),
    ({"observed_ports": frozenset({0})}, "schema_unsupported"),
    ({"observed_ports": frozenset({65536})}, "schema_unsupported"),
    ({"observed_ports": frozenset({True})}, "schema_unsupported"),
    ({"observed_ports": frozenset({9223.0})}, "schema_unsupported"),
])
def test_direct_enumeration_objects_obey_the_snapshot_contract(fields, code):
    census = enumeration(**fields)
    # Even a declared invalid port must fail schema validation, not be waived.
    descriptor = box_with(headroom(), census=census, declared_ports=census.observed_ports)
    assert refuse(Rig(descriptor=descriptor)).code == code


@pytest.mark.parametrize("stamp", [float("nan"), float("inf"), float("-inf"), True, "now"])
def test_invalid_clock_cannot_admit_stale_records(stamp):
    rig = Rig(descriptor=box_with(headroom(measured_at=NOW - 3600),
                                  census=enumeration(taken_at=NOW - 3600)))
    assert refuse(rig, now=stamp).code == "clock_invalid"
    with pytest.raises(admission.AdmissionRefused) as caught:
        rig.box.effective_ceiling(stamp)
    assert caught.value.code == "clock_invalid"


@pytest.mark.parametrize("expiry", [float("nan"), float("inf"), float("-inf"), True, "later"])
def test_domain_expiry_must_be_a_finite_positive_moment(expiry):
    from dataclasses import replace
    rig = Rig()
    rig.domains[0] = replace(rig.domains[0], expires_at=expiry)
    assert refuse(rig).code == "domain_expiry_unstated"


@pytest.mark.parametrize("max_age", [float("nan"), float("inf"), float("-inf"), 0, -1, True])
def test_age_limit_must_be_finite_and_positive(max_age):
    descriptor = box_with(headroom(), max_age=max_age)
    assert refuse(Rig(descriptor=descriptor)).code == "measurement_incoherent"
    with pytest.raises(admission.AdmissionRefused) as caught:
        descriptor.effective_ceiling(NOW)
    assert caught.value.code == "measurement_incoherent"


@pytest.mark.parametrize("fields", [
    {"memory_available_bytes": 0, "reserve_bytes": -6 * GB},
    {"memory_available_bytes": float("nan")},
    {"memory_available_bytes": -1},
    {"memory_total_bytes": float("inf")},
    {"browser_resident_bytes": True},
    {"reserve_bytes": float("nan")},
    {"process_in_use": float("nan")},
    {"process_limit": float("inf")},
    {"browser_processes": 1.5},
    {"compressor_bytes": -1},
    {"pageouts": float("nan")},
])
def test_invalid_resource_counters_cannot_create_capacity(fields):
    descriptor = box_with(headroom(**fields))
    assert refuse(Rig(descriptor=descriptor)).code == "measurement_incoherent"


@pytest.mark.parametrize("declared", [float("nan"), float("inf"), 6.0, True])
def test_declared_ceiling_is_an_integer_count(declared):
    assert refuse(Rig(descriptor=box_with(headroom(), declared=declared))).code == "measurement_incoherent"


def test_valid_reserve_larger_than_available_memory_leaves_zero_capacity():
    descriptor = box_with(headroom(memory_available_bytes=GB, reserve_bytes=2 * GB))
    assert descriptor.effective_ceiling(NOW).memory == 0
    assert refuse(Rig(descriptor=descriptor)).code == "ceiling_exhausted"


def test_the_chain_verifies_and_every_link_names_its_parent():
    admitted = Rig().preflight()
    admission.verify_chain(admitted.artifacts)
    parent = ""
    for art in admitted.artifacts:
        assert art.parent == parent
        parent = art.digest
    assert set(admitted.stage_digests) == set(admission.STAGES)


def test_slot_grant_carries_names_not_endpoints():
    """A grant is pasted into logs; it must not carry the paid pool with it."""
    grant = Rig().preflight().grant
    blob = json.dumps(grant.public())
    for secret in ("fake-password", "proxy-00.invalid", "http://", "user"):
        assert secret not in blob
    assert grant.slots["kid.00"].startswith("synthetic-pool-")


# ---------------------------------------------------------------------------
# 2. stage one: domain, the cheapest refusal there is
# ---------------------------------------------------------------------------

def test_empty_cohort_refuses_at_the_domain_stage():
    refused = refuse(Rig(), handles=[])
    assert (refused.stage, refused.stage_index) == ("domain", 1)
    assert refused.code == "cohort_empty"


def test_duplicate_handle_refuses_at_the_domain_stage():
    rig = Rig()
    refused = refuse(rig, handles=rig.handles + ["kid.00"])
    assert refused.code == "duplicate_handle"
    assert "kid.00" in refused.detail


def test_missing_domain_record_refuses_at_stage_one():
    rig = Rig()
    refused = refuse(rig, domains=rig.domains[1:])
    assert (refused.stage, refused.code) == ("domain", "no_domain_record")
    assert "kid.00" in refused.detail


def test_unverified_domain_refuses():
    rig = Rig(1)
    refused = refuse(rig, domains=[admission.DomainRecord(
        domain=rig.domains[0].domain, handle="kid.00", verified=False,
        expires_at=NOW + 10 ** 7)])
    assert refused.code == "domain_unverified"


def test_expired_domain_refuses():
    rig = Rig(1)
    refused = refuse(rig, domains=[admission.DomainRecord(
        domain=rig.domains[0].domain, handle="kid.00", verified=True,
        expires_at=NOW - 1)])
    assert refused.code == "domain_expired"


def test_a_domain_record_with_an_unstated_expiry_refuses():
    """The default `expires_at` of 0.0 is 'never stated', not 'never expires'."""
    rig = Rig(1)
    refused = refuse(rig, domains=[admission.DomainRecord(
        domain=rig.domains[0].domain, handle="kid.00", verified=True)])
    assert (refused.stage, refused.code) == ("domain", "domain_expiry_unstated")


# ---------------------------------------------------------------------------
# 3. stage two: identity — and the ordering rule the card exists for
# ---------------------------------------------------------------------------

def test_cohort_larger_than_admitted_identities_refuses_before_any_browser():
    """The whole point of the ordering: 7 children, 5 identities, no browser.

    Stage 6 is the expensive link; an identity shortfall is a line of text. If
    this ever reports ``slot``, the chain has been reordered and the cheap
    refusal has been traded for the expensive one.
    """
    rig = Rig(7)
    allocated = []

    def allocate(grant):
        allocated.append(grant)

    refused = refuse(rig, identities=rig.identities[:5])
    assert (refused.stage, refused.stage_index) == ("identity", 2)
    assert refused.code == "identity_shortfall"
    assert "7 children" in refused.detail and "5 admitted identities" in refused.detail
    assert allocated == []


def test_unverified_identities_shrink_the_admitted_pool():
    rig = Rig()
    rig.identities[0] = admission.Identity(
        handle="kid.00", address="ops@kid-00.example",
        domain="kid-00.example", recovery_owner="chairman", verified=False)
    rig.identities[1] = admission.Identity(
        handle="kid.01", address="ops@kid-01.example",
        domain="kid-01.example", recovery_owner="chairman", verified=False)
    refused = refuse(rig)
    assert refused.code == "identity_shortfall"
    assert "6 children" in refused.detail and "4 admitted identities" in refused.detail


def test_identity_needs_a_named_recovery_owner():
    rig = Rig(1)
    refused = refuse(rig, identities=[admission.Identity(
        handle="kid.00", address="ops@kid-00.example",
        domain="kid-00.example", verified=True, recovery_owner="")])
    assert refused.code == "no_recovery_owner"


def test_identity_off_its_domain_refuses():
    rig = Rig(1)
    refused = refuse(rig, identities=[admission.Identity(
        handle="kid.00", address="ops@elsewhere.example",
        domain="elsewhere.example", verified=True, recovery_owner="chairman")])
    assert refused.code == "identity_off_domain"


def test_persona_in_another_cell_refuses_before_a_proxy_is_spent():
    rig = Rig(1)
    from xguerrilla.persona import Persona
    refused = refuse(rig, personas={"kid.00": Persona(handle="kid.00", cell="ATX-04")})
    assert (refused.stage, refused.code) == ("identity", "cohort_off_box")


# ---------------------------------------------------------------------------
# 4. stage three: custody
# ---------------------------------------------------------------------------

def test_custody_without_totp_refuses():
    rig = Rig(1)
    refused = refuse(rig, custody=[admission.Custody(
        handle="kid.00", totp_enrolled=False,
        recovery_custodian="chairman", recovery_codes_held=True)])
    assert (refused.stage, refused.code) == ("custody", "totp_not_enrolled")


def test_custody_without_held_recovery_codes_refuses():
    rig = Rig(1)
    refused = refuse(rig, custody=[admission.Custody(
        handle="kid.00", totp_enrolled=True,
        recovery_custodian="chairman", recovery_codes_held=False)])
    assert refused.code == "recovery_codes_missing"


def test_custody_without_a_named_custodian_refuses():
    rig = Rig(1)
    refused = refuse(rig, custody=[admission.Custody(
        handle="kid.00", totp_enrolled=True,
        recovery_custodian="", recovery_codes_held=True)])
    assert refused.code == "no_recovery_custodian"


# ---------------------------------------------------------------------------
# 5. stages four and five
# ---------------------------------------------------------------------------

def test_proxy_shortfall_refuses_at_stage_four():
    refused = refuse(Rig(6, slots=5))
    assert (refused.stage, refused.stage_index) == ("proxy", 4)
    assert refused.code == "proxy_shortfall"
    assert "6 children on 5 proxy slots" in refused.detail


def test_unadmitted_account_refuses_at_stage_five():
    rig = Rig(1)
    refused = refuse(rig, accounts=[admission.Account(
        handle="kid.00", account_id="acct-00", admitted=False)])
    assert (refused.stage, refused.stage_index) == ("account", 5)
    assert refused.code == "account_not_admitted"


def test_missing_account_record_refuses_rather_than_passing_vacuously():
    refused = refuse(Rig(2), accounts=[])
    assert refused.code == "no_account"


# ---------------------------------------------------------------------------
# 6. stage six: the measured ceiling, not the nominal one
# ---------------------------------------------------------------------------

def test_declared_six_does_not_survive_a_measurement_of_four():
    """The operator's rule: a box that measures four has four, whatever §26.3 says."""
    tight = box_with(headroom(memory_available_bytes=4 * GB))
    assert tight.effective_ceiling(NOW).effective == 4
    refused = refuse(Rig(5, descriptor=tight))
    assert (refused.stage, refused.code) == ("slot", "ceiling_exhausted")
    assert "measured ceiling is 4" in refused.detail
    assert "declared 6" in refused.detail


def test_process_headroom_binds_when_memory_is_plentiful():
    """The helper count is per profile class: the process table can bind first."""
    crowded = box_with(headroom(process_limit=1000, process_in_use=910))
    ceiling = crowded.effective_ceiling(NOW)
    assert (ceiling.memory, ceiling.process) == (9, 3)
    assert (ceiling.effective, ceiling.binding) == (3, "process")
    refused = refuse(Rig(4, descriptor=crowded))
    assert refused.code == "ceiling_exhausted"
    assert "processes support 3" in refused.detail


def test_unmeasured_box_refuses_instead_of_trusting_the_spec():
    refused = refuse(Rig(descriptor=box_with(None)))
    assert (refused.stage, refused.code) == ("slot", "ceiling_unmeasured")
    assert "declared ceiling of 6" in refused.detail


def test_stale_measurement_refuses():
    old = box_with(headroom(measured_at=NOW - 3600))
    refused = refuse(Rig(descriptor=old))
    assert refused.code == "ceiling_stale"


def test_incoherent_measurement_refuses():
    broken = box_with(headroom(browser_processes=0))
    refused = refuse(Rig(descriptor=broken))
    assert refused.code == "measurement_incoherent"


def test_a_measurement_timestamp_that_is_not_finite_is_not_a_measurement():
    """NaN and the infinities cannot be aged against: the stale comparison
    would wave them through (`nan > limit` is False), so they refuse first."""
    for stamp in (float("nan"), float("inf"), float("-inf")):
        refused = refuse(Rig(1, descriptor=box_with(headroom(measured_at=stamp))))
        assert (refused.stage, refused.code) == ("slot", "measurement_unstated")


def test_a_measurement_stamped_in_the_future_refuses():
    """A reading dated after the moment it is used measured nothing."""
    ahead = box_with(headroom(measured_at=NOW + admission.FUTURE_TOLERANCE * 2))
    refused = refuse(Rig(1, descriptor=ahead))
    assert (refused.stage, refused.code) == ("slot", "measurement_from_future")


def test_a_measurement_within_clock_tolerance_still_admits():
    """Skew up to FUTURE_TOLERANCE is absorbed, not refused."""
    skewed = box_with(headroom(measured_at=NOW + 30))
    assert Rig(1, descriptor=skewed).preflight().grant.effective_ceiling == 6


def test_a_measurement_at_exactly_max_age_refuses():
    """`age >= max_age`: a reading exactly at the limit has reached it."""
    edge = box_with(headroom(measured_at=NOW - 900))
    refused = refuse(Rig(1, descriptor=edge))
    assert refused.code == "ceiling_stale"


@pytest.mark.parametrize(
    "field, value",
    [
        ("memory_total_bytes", 0),
        ("memory_available_bytes", 17 * GB),  # one past the fixture's 16 GB total
        ("process_in_use", -1),
        ("process_limit", 0),
        ("process_in_use", 4001),  # one past the fixture's 4000 limit
    ],
)
def test_headroom_that_contradicts_itself_refuses(field, value):
    """A reading that contradicts itself is not a reading of any box: the gate
    refuses `measurement_incoherent` instead of computing a ceiling from it."""
    broken = box_with(headroom(**{field: value}))
    refused = refuse(Rig(1, descriptor=broken))
    assert (refused.stage, refused.code) == ("slot", "measurement_incoherent")


def test_grant_records_which_constraint_bound_and_whether_the_box_was_over_claimed():
    crowded = box_with(headroom(process_limit=1000, process_in_use=910))
    admitted = Rig(3, descriptor=crowded).preflight()
    assert admitted.grant.effective_ceiling == 3
    assert admitted.grant.declared_ceiling == 6
    assert admitted.grant.binding == "process"
    slot_facts = admitted.artifacts[-1].facts["ceiling"]
    assert slot_facts["over_claim"] is True


# ---------------------------------------------------------------------------
# 7. a memory figure must name the counter it came from
# ---------------------------------------------------------------------------

def test_memory_headroom_without_a_named_basis_refuses():
    """A number with no provenance is not a measurement."""
    refused = refuse(Rig(descriptor=box_with(headroom(memory_basis=""))))
    assert (refused.stage, refused.code) == ("slot", "measurement_basis_unstated")


def test_a_pressure_gauge_percentage_cannot_stand_in_for_free_pages():
    """58% 'free' over 299 MiB of unused pages is how a gate reports health in swap."""
    gauge = headroom(
        memory_basis="memory_pressure_percent",
        memory_available_bytes=int(0.58 * 16 * GB),
    )
    refused = refuse(Rig(1, descriptor=box_with(gauge)))
    assert refused.code == "measurement_basis_unstated"
    assert "memory_pressure_percent" in refused.detail


def test_a_box_down_to_pages_cannot_seat_another_browser():
    """299 MiB unused against a 1.6 GiB instance seats nothing, and says so."""
    squeezed = headroom(
        memory_available_bytes=299 * 1024 * 1024,
        browser_resident_bytes=int(1.6 * GB),
        compressor_bytes=4 * GB,
        pageouts=5116,
    )
    refused = refuse(Rig(1, descriptor=box_with(squeezed)))
    assert (refused.stage, refused.code) == ("slot", "ceiling_exhausted")
    assert "measured ceiling is 0" in refused.detail
    assert "bound by memory" in refused.detail


def test_the_receipt_carries_the_page_evidence_behind_the_ceiling():
    squeezed = headroom(compressor_bytes=4 * GB, pageouts=5116,
                        memory_available_bytes=4 * GB)
    admitted = Rig(3, descriptor=box_with(squeezed)).preflight()
    facts = admitted.artifacts[-1].facts["ceiling"]
    assert facts["memory_basis"] == "free_inactive_speculative"
    assert facts["compressor_bytes"] == 4 * GB
    assert facts["pageouts"] == 5116


def test_proxy_receipt_says_ownership_is_asserted_not_discovered():
    """Detached browsers are reparented to pid 1, so parentage proves nothing."""
    admitted = Rig().preflight()
    facts = admitted.artifacts[3].facts
    assert facts["ownership"] == "pool_record"
    assert set(facts["slots"]) == set(admitted.grant.handles)


# ---------------------------------------------------------------------------
# 8. no allocation, ever, before stage six
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "overrides, expected_stage",
    [
        ({}, "domain"),
        ({"identity_shortfall": True}, "identity"),
    ],
)
def test_a_refused_chain_yields_no_grant(overrides, expected_stage):
    rig = Rig(7)
    if overrides.get("identity_shortfall"):
        kwargs = {"identities": rig.identities[:5]}
    else:
        kwargs = {"domains": rig.domains[1:]}
    refused = refuse(rig, **kwargs)
    assert refused.stage == expected_stage
    assert refused.stage_index < 6
    assert refused.public()["ok"] is False


# ---------------------------------------------------------------------------
# 9. a stored chain cannot be edited into a passing one
# ---------------------------------------------------------------------------

def test_verify_chain_rejects_a_removed_stage():
    admitted = Rig().preflight()
    without_custody = tuple(a for a in admitted.artifacts if a.stage != "custody")
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.verify_chain(without_custody)
    assert caught.value.code == "chain_incomplete"


def test_verify_chain_rejects_a_patched_artifact():
    from dataclasses import replace
    admitted = Rig().preflight()
    patched = list(admitted.artifacts)
    patched[3] = replace(patched[3], facts={**patched[3].facts, "pool": 99})
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.verify_chain(patched)
    assert caught.value.code == "chain_tampered"


def test_verify_chain_rejects_a_reordered_chain():
    """A swapped pair is out of order, and it refuses as one."""
    admitted = Rig().preflight()
    swapped = [admitted.artifacts[1], admitted.artifacts[0], *admitted.artifacts[2:]]
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.verify_chain(swapped)
    assert caught.value.code == "chain_out_of_order"


def test_an_unknown_stage_refuses_outside_the_six():
    """A ghost link must come back as a refusal, not a KeyError.

    ``[ghost, domain, identity, ...]`` reaches the out-of-order branch with a
    stage the gate does not know; before the chain-level refusal existed that
    escaped as a KeyError instead of a verdict.
    """
    from dataclasses import replace
    admitted = Rig().preflight()
    ghosted = [replace(admitted.artifacts[0], stage="ghost"),
               *admitted.artifacts[1:-1]]
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.verify_chain(ghosted)
    refused = caught.value
    assert (refused.stage, refused.stage_index, refused.code) == \
        ("chain", 0, "chain_unknown_stage")
    assert "ghost" in refused.detail


# ---------------------------------------------------------------------------
# 10. the box is enumerated, never assumed
# ---------------------------------------------------------------------------

def snapshot(**over) -> dict:
    """A minimal observer snapshot in the shipped payload's shape, all synthetic.

    Mirrors the real v1 payload's top-level keys: ``schema_version``, ``host``,
    ``taken_at``, ``provenance`` (with ``script_sha256``), ``collected``,
    ``listeners``, ``chrome`` and the top-level ``collection_status``.
    """
    base: dict = {
        "schema_version": 1,
        "host": "synthetic-box",
        "taken_at": "2026-11-08T10:41:26.180591+00:00",
        "observer": "synthetic",
        "provenance": {"script_sha256": "ab" * 32, "tool_identity": "synthetic"},
        "collected": {"hosts_attempted": 1, "hosts_returned": ["synthetic-box"],
                      "command_failures": []},
        "listeners": [],
        "chrome": [],
        "collection_status": "complete",
    }
    base.update(over)
    return base


def test_a_snapshot_from_a_newer_schema_refuses():
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snapshot(schema_version=2))
    refused = caught.value
    assert (refused.stage, refused.stage_index) == ("slot", 6)
    assert refused.code == "schema_unsupported"


def test_a_snapshot_with_a_missing_schema_version_refuses():
    snap = snapshot()
    del snap["schema_version"]
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snap)
    assert caught.value.code == "schema_unsupported"


def test_a_string_port_is_a_shape_the_contract_forbids():
    snap = snapshot(listeners=[{"port": "9333", "bind_addr": "127.0.0.1", "pid": 1}])
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snap)
    refused = caught.value
    assert refused.code == "schema_unsupported"
    assert "9333" in refused.detail


def test_an_incomplete_collection_refuses():
    snap = snapshot(collection_status="incomplete",
                    listeners=[{"port": 9333, "bind_addr": "127.0.0.1", "pid": 1}])
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snap)
    refused = caught.value
    assert (refused.stage, refused.code) == ("slot", "enumeration_incomplete")


def test_collection_status_is_read_from_the_top_level_of_the_payload():
    """The shipped payload states it at top level; the older position also parses."""
    snap = snapshot()
    del snap["collection_status"]
    snap["collected"]["collection_status"] = "complete"
    assert admission.Enumeration.from_snapshot(snap).collection_status == "complete"


def test_taken_at_must_be_present_and_parseable():
    snap = snapshot()
    del snap["taken_at"]
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snap)
    assert caught.value.code == "schema_unsupported"
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snapshot(taken_at="day before yesterday"))
    assert caught.value.code == "schema_unsupported"


def test_taken_at_parses_as_an_epoch_number_or_an_iso_stamp():
    assert admission.Enumeration.from_snapshot(snapshot(taken_at=NOW - 5)).taken_at == NOW - 5
    # An ISO stamp parses to the same moment an epoch would name:
    iso = admission.Enumeration.from_snapshot(snapshot(taken_at="1970-01-12T13:46:40+00:00"))
    assert iso.taken_at == NOW  # 1970-01-12T13:46:40Z is epoch 1,000,000


def test_a_naive_iso_stamp_refuses():
    """A stamp with no offset dates the sweep to no moment in particular."""
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snapshot(taken_at="2026-11-08T10:41:26"))
    refused = caught.value
    assert refused.code == "schema_unsupported"
    assert "taken_at must carry a UTC offset" in refused.detail


def test_a_non_finite_epoch_stamp_refuses():
    for stamp in (float("nan"), float("inf")):
        with pytest.raises(admission.AdmissionRefused) as caught:
            admission.Enumeration.from_snapshot(snapshot(taken_at=stamp))
        assert caught.value.code == "schema_unsupported"


def test_a_snapshot_that_is_not_a_mapping_refuses():
    """None, a list, a string — any non-mapping payload is not a census."""
    for bad in (None, [], "synthetic-box", 42):
        with pytest.raises(admission.AdmissionRefused) as caught:
            admission.Enumeration.from_snapshot(bad)  # pyright: ignore[reportArgumentType]
        refused = caught.value
        assert (refused.stage, refused.code) == ("slot", "schema_unsupported")


def test_a_non_mapping_chrome_row_refuses():
    """Chrome rows parse under the listener law: a row the census did not take
    as an object refuses instead of shrinking the observed set silently."""
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snapshot(chrome=["9222", None]))
    assert caught.value.code == "schema_unsupported"


def test_a_float_schema_version_refuses():
    """`1.0` is not `1`: the schema pin is an exact int, not a value comparison."""
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snapshot(schema_version=1.0))
    assert caught.value.code == "schema_unsupported"


@pytest.mark.parametrize("port", [0, -1, 65536, 70000])
def test_a_listener_port_out_of_range_refuses(port):
    snap = snapshot(listeners=[{"port": port, "bind_addr": "127.0.0.1", "pid": 1}])
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snap)
    assert caught.value.code == "schema_unsupported"


def test_a_chrome_port_out_of_range_refuses():
    snap = snapshot(chrome=[{"pid": 1, "cdp_port": 70000}])
    with pytest.raises(admission.AdmissionRefused) as caught:
        admission.Enumeration.from_snapshot(snap)
    assert caught.value.code == "schema_unsupported"


def test_the_extreme_valid_ports_still_parse():
    low = admission.Enumeration.from_snapshot(snapshot(listeners=[{"port": 1}]))
    high = admission.Enumeration.from_snapshot(snapshot(listeners=[{"port": 65535}]))
    assert low.observed_ports == frozenset({1})
    assert high.observed_ports == frozenset({65535})


def test_an_unenumerated_box_refuses_before_any_ceiling_is_computed():
    """No census, no ceiling — the census fires even when the headroom is gone too."""
    bare = admission.Box("synthetic-box", 6, None, 900.0)  # no census AND no headroom
    refused = refuse(Rig(descriptor=bare))
    assert (refused.stage, refused.code) == ("slot", "enumeration_not_collected")
    assert refused.code != "ceiling_unmeasured"


def test_an_observed_port_neither_declared_nor_baseline_refuses():
    """9223 is the resource plane's bridge, not a persona: until it is declared, refuse."""
    census = enumeration(observed_ports=frozenset({9333, 9223, 3283}))
    undeclared = box_with(headroom(), census=census,
                          declared_ports=frozenset({9333}),
                          baseline_ports=frozenset({3283}))
    refused = refuse(Rig(1, descriptor=undeclared))
    assert (refused.stage, refused.code) == ("slot", "undeclared_port")
    assert "9223" in refused.detail

    # The same box with the bridge declared in the resource plane admits, and
    # the receipt gives every observed port exactly one word.
    declared = box_with(headroom(), census=census,
                        declared_ports=frozenset({9333, 9223}),
                        baseline_ports=frozenset({3283}))
    admitted = Rig(1, descriptor=declared).preflight()
    fact = admitted.artifacts[-1].facts["enumeration"]
    assert fact["verdicts"] == {"9333": "declared", "9223": "declared", "3283": "baseline"}
    assert admitted.grant.enumeration_digest != ""


def test_a_baseline_port_is_admitted_and_labelled_baseline():
    census = enumeration(observed_ports=frozenset({3283}))
    admitted = Rig(1, descriptor=box_with(headroom(), census=census,
                                          baseline_ports=frozenset({3283}))).preflight()
    fact = admitted.artifacts[-1].facts["enumeration"]
    assert fact["verdicts"] == {"3283": "baseline"}


def test_an_undeclared_port_never_beats_a_cheaper_refusal():
    """Ordering: 7 children against 5 identities refuses at stage 2, not at the census."""
    box = box_with(headroom(), census=enumeration(observed_ports=frozenset({7777})))
    rig = Rig(7, descriptor=box)
    refused = refuse(rig, identities=rig.identities[:5])
    assert (refused.stage, refused.stage_index) == ("identity", 2)
    assert refused.code == "identity_shortfall"


def test_a_stale_enumeration_refuses():
    old = enumeration(taken_at=NOW - 3600)  # beyond the 900s default
    refused = refuse(Rig(descriptor=box_with(headroom(), census=old)))
    assert refused.code == "enumeration_stale"


def test_an_enumeration_at_exactly_max_age_refuses():
    """`age >= max_age`: a census exactly at the limit has reached it."""
    census = enumeration(taken_at=NOW - 900)
    refused = refuse(Rig(1, descriptor=box_with(headroom(), census=census)))
    assert refused.code == "enumeration_stale"


def test_an_enumeration_timestamp_that_is_not_finite_refuses():
    census = enumeration(taken_at=float("nan"))
    refused = refuse(Rig(1, descriptor=box_with(headroom(), census=census)))
    assert (refused.stage, refused.code) == ("slot", "measurement_unstated")


def test_an_enumeration_stamped_in_the_future_refuses():
    census = enumeration(taken_at=NOW + admission.FUTURE_TOLERANCE * 2)
    refused = refuse(Rig(1, descriptor=box_with(headroom(), census=census)))
    assert (refused.stage, refused.code) == ("slot", "measurement_from_future")


def test_another_boxs_census_refuses():
    refused = refuse(Rig(descriptor=box_with(headroom(),
                                             census=enumeration(host="other-box"))))
    assert (refused.stage, refused.code) == ("slot", "enumeration_wrong_box")
    assert "other-box" in refused.detail


def test_the_grant_is_pinned_to_what_was_observed():
    """A different observed set is a different census, so the digest moves."""
    def admit(observed: frozenset) -> admission.Admission:
        box = box_with(headroom(), declared_ports=frozenset({9333, 9223}),
                       baseline_ports=frozenset({3283}),
                       census=enumeration(observed_ports=observed))
        return Rig(1, descriptor=box).preflight()

    one = admit(frozenset({9333, 9223, 3283}))
    two = admit(frozenset({9333, 9223}))
    assert one.grant.enumeration_digest != two.grant.enumeration_digest
    admission.verify_chain(one.artifacts)
    admission.verify_chain(two.artifacts)


def test_a_realistic_snapshot_parses_to_the_right_observed_set():
    """Mirrors the shipped payload: chrome rows carry a possibly-null cdp_port."""
    snap = snapshot(
        listeners=[
            {"port": 9333, "bind_addr": "127.0.0.1", "pid": 10248, "proc": "Chrome"},
            {"port": 3283, "bind_addr": "*", "pid": 34487, "proc": "ARDAgent"},
            {"port": 4141, "bind_addr": "127.0.0.1", "pid": 87248, "proc": "sshd-session"},
        ],
        chrome=[
            {"pid": 34493, "cdp_port": 9222},
            {"pid": 11186, "cdp_port": None},
        ],
    )
    enum = admission.Enumeration.from_snapshot(snap)
    assert enum.schema_version == 1
    assert enum.host == "synthetic-box"
    assert enum.collection_status == "complete"
    assert enum.tool_sha256 == "ab" * 32
    assert enum.observed_ports == frozenset({9333, 3283, 4141, 9222})


# ---------------------------------------------------------------------------
# 11. a refusal names the handle, never the mailbox
# ---------------------------------------------------------------------------

def test_no_refusal_names_a_mailbox_address():
    """Walk every refusal the fixture set can reach; none may carry the address.

    The fixture mailboxes are ``ops@kid-NN.example``. Handles, domains and
    account ids are identifiers and may appear; the mailbox itself must not —
    not in the message, not in the public verdict, not in an admitted receipt.
    """
    from dataclasses import replace
    from xguerrilla.persona import Persona

    address = "ops@kid-00.example"
    rig7 = Rig(7)

    def chain_refusal(mutate):
        admitted = Rig().preflight()
        with pytest.raises(admission.AdmissionRefused) as caught:
            admission.verify_chain(mutate(list(admitted.artifacts)))
        return caught.value

    cases = [
        ("cohort_empty", lambda: refuse(Rig(), handles=[])),
        ("duplicate_handle", lambda: refuse(Rig(), handles=["kid.00", "kid.00"])),
        ("no_domain_record", lambda: refuse(Rig(), domains=[])),
        ("domain_unverified", lambda: refuse(Rig(), domains=[admission.DomainRecord(
            domain="kid-00.example", handle="kid.00", verified=False,
            expires_at=NOW + 10 ** 7)])),
        ("domain_expiry_unstated", lambda: refuse(Rig(), domains=[admission.DomainRecord(
            domain="kid-00.example", handle="kid.00", verified=True)])),
        ("domain_expired", lambda: refuse(Rig(), domains=[admission.DomainRecord(
            domain="kid-00.example", handle="kid.00", verified=True,
            expires_at=NOW - 1)])),
        ("identity_shortfall", lambda: refuse(rig7, identities=rig7.identities[:5])),
        ("no_identity", lambda: refuse(Rig(1), identities=[admission.Identity(
            handle="someone-else", address="ops@kid-00.example",
            domain="kid-00.example", recovery_owner="chairman", verified=True)])),
        ("identity_unverified", lambda: refuse(Rig(1), identities=[
            admission.Identity(handle="kid.01", address="ops@kid-01.example",
                               domain="kid-01.example", recovery_owner="chairman",
                               verified=True),
            admission.Identity(handle="kid.00", address=address,
                               domain="kid-00.example", recovery_owner="chairman",
                               verified=False)])),
        ("no_recovery_owner", lambda: refuse(Rig(1), identities=[admission.Identity(
            handle="kid.00", address=address, domain="kid-00.example",
            verified=True, recovery_owner="")])),
        ("identity_off_domain", lambda: refuse(Rig(1), identities=[admission.Identity(
            handle="kid.00", address=address, domain="elsewhere.example",
            verified=True, recovery_owner="chairman")])),
        ("no_persona", lambda: refuse(Rig(1), personas={})),
        ("cohort_off_box", lambda: refuse(Rig(1), personas={
            "kid.00": Persona(handle="kid.00", cell="ATX-04")})),
        ("no_custody", lambda: refuse(Rig(), custody=[])),
        ("totp_not_enrolled", lambda: refuse(Rig(), custody=[admission.Custody(
            handle="kid.00", totp_enrolled=False, recovery_custodian="chairman",
            recovery_codes_held=True)])),
        ("recovery_codes_missing", lambda: refuse(Rig(), custody=[admission.Custody(
            handle="kid.00", totp_enrolled=True, recovery_custodian="chairman",
            recovery_codes_held=False)])),
        ("no_recovery_custodian", lambda: refuse(Rig(), custody=[admission.Custody(
            handle="kid.00", totp_enrolled=True, recovery_custodian="",
            recovery_codes_held=True)])),
        ("proxy_shortfall", lambda: refuse(Rig(), slots=[])),
        ("no_account", lambda: refuse(Rig(), accounts=[])),
        ("account_not_admitted", lambda: refuse(Rig(), accounts=[admission.Account(
            handle="kid.00", account_id="acct-00", admitted=False)])),
        ("ceiling_unmeasured", lambda: refuse(Rig(), box=box_with(None))),
        ("ceiling_stale", lambda: refuse(
            Rig(), box=box_with(headroom(measured_at=NOW - 3600)))),
        ("measurement_unstated", lambda: refuse(
            Rig(), box=box_with(headroom(measured_at=float("nan"))))),
        ("measurement_from_future", lambda: refuse(
            Rig(), box=box_with(headroom(measured_at=NOW + admission.FUTURE_TOLERANCE * 2)))),
        ("measurement_basis_unstated", lambda: refuse(
            Rig(), box=box_with(headroom(memory_basis="")))),
        ("measurement_incoherent", lambda: refuse(
            Rig(), box=box_with(headroom(memory_total_bytes=0)))),
        ("enumeration_not_collected", lambda: refuse(
            Rig(), box=admission.Box("synthetic-box", 6, None, 900.0))),
        ("enumeration_wrong_box", lambda: refuse(
            Rig(), box=box_with(headroom(), census=enumeration(host="other-box")))),
        ("enumeration_stale", lambda: refuse(
            Rig(), box=box_with(headroom(), census=enumeration(taken_at=NOW - 3600)))),
        ("undeclared_port", lambda: refuse(
            Rig(), box=box_with(headroom(),
                                census=enumeration(observed_ports=frozenset({7777}))))),
        ("ceiling_exhausted", lambda: refuse(Rig(7))),
        ("chain_incomplete", lambda: chain_refusal(lambda arts: arts[1:])),
        ("chain_out_of_order", lambda: chain_refusal(
            lambda arts: [arts[1], arts[0], *arts[2:]])),
        ("chain_tampered", lambda: chain_refusal(
            lambda arts: [arts[0],
                          replace(arts[1], facts={**arts[1].facts,
                                                  "admitted_pool": 99}),
                          *arts[2:]])),
        ("chain_unknown_stage", lambda: chain_refusal(
            lambda arts: [replace(arts[0], stage="ghost"), *arts[1:]])),
    ]

    for code, make in cases:
        refused = make()
        assert isinstance(refused, admission.AdmissionRefused), code
        assert refused.code == code, f"expected {code}, got {refused.code}"
        text = str(refused) + json.dumps(refused.public())
        assert "ops@" not in text, f"{code} leaks a mailbox address: {text}"
        assert address not in text, f"{code} leaks the fixture mailbox: {text}"

    # The success path is logged too: an admitted receipt carries handles,
    # domains and account ids, and still no mailbox.
    receipt = json.dumps(Rig().preflight().public())
    assert "ops@" not in receipt and address not in receipt
