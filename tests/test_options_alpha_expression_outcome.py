"""Discriminating tests for the pure expression-specific outcome codec.

Fixtures only: every receipt, quote row, ledger campaign and publisher pair
below is a synthetic source-schema test fixture built by reusing (read-only)
the incumbent publisher tests and OA-3 evaluator tests with
``PYTHONPATH=tests:scripts``.  Nothing here is natural evidence, provider
proof, or admission of anything: the positive FakeS3 receipt clock is simply
moved into real RTH on a valid NYSE session (2026-08-14, a Friday) by
overriding the test provider clock only; no product clock rule is changed.
"""
from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timedelta, timezone

import pytest

import test_publish_options_alpha_candidate_r2 as publisher_tests
import test_options_alpha_exact_option_outcome as oa3_tests
from engine.options_alpha_expression_outcome import (
    EXPRESSION_OUTCOME_SCHEMA,
    ExpressionOutcomeError,
    ExpressionOutcomeEvidence,
    expression_outcome_key,
    make_expression_outcome,
    validate_expression_outcome,
)
from engine import options_alpha_exact_option_outcome as oa3
from engine import options_alpha_expression_publication as intent_readback
from engine import options_nbbo_cohort as cohort
from engine import options_signal_campaign as campaigns

UTC = timezone.utc
# Actual regular NYSE RTH minute (10:35 ET Friday) for the positive fixture.
RTH_BASE = datetime(2026, 8, 14, 14, 35, 0, tzinfo=UTC)


class RthMetadataS3(publisher_tests.MetadataS3):
    """Test provider-clock override only: receipts land inside real RTH."""

    def _time(self):
        return RTH_BASE + timedelta(seconds=self.n)


def _z(stamp: datetime) -> str:
    return stamp.isoformat().replace("+00:00", "Z")


def _scenario(tmp_path, monkeypatch, store=None):
    rows = publisher_tests._feeds(tmp_path / "source", monkeypatch)
    intent = publisher_tests._expression_intent(rows, tmp_path / "source")
    store = store if store is not None else RthMetadataS3()
    assert publisher_tests._publish_expression(store, tmp_path, rows[0], [intent]) \
        == "published"
    pair = publisher_tests._read_expression(store, tmp_path)
    availability = intent_readback.resolve_intent_availability(
        pair, intent["expression_id"])
    assert availability["status"] == "available"
    candidate = next(item for item in pair.feed["formed_candidates"]
                     if item["candidate_id"] == intent["candidate_id"])
    snapshot = campaigns.load_ledger(
        tmp_path / "source" / campaigns.CAMPAIGNS_PATH,
        campaigns.CAMPAIGNS_PATH)
    revisions = [row.value for row in snapshot.rows if row.value["campaign_revision_id"]
                 == candidate["frozen_formation"]["campaign_revision_id"]]
    assert len(revisions) == 1
    return {"rows": rows, "intent": intent, "pair": pair,
            "availability": availability, "candidate": candidate,
            "campaign": copy.deepcopy(revisions[0])}


def _commitment(scenario):
    return datetime.strptime(scenario["availability"]["commitment_published_at"],
                             "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _receipt(scenario, **overrides):
    intent = scenario["intent"]
    contract = intent["contract"]
    fields = dict(
        expression_id=intent["expression_id"],
        policy_version=intent["oa3_ruler"]["policy_version"],
        source_candidate_id=intent["candidate_id"],
        decision_receipt_sha256=scenario["availability"]["intent_bytes_sha256"],
        source_rule_digest_sha256=intent["selection_policy_sha256"],
        selection_fence_at="2026-08-13T14:32:00Z",
        decision_at=intent["decision_at"],
        available_at=scenario["availability"]["commitment_published_at"],
        root=contract["root"], expiration=contract["expiration"],
        right=contract["right"], strike=contract["strike"],
        strike_millis=contract["strike_millis"], occ_symbol=contract["occ_symbol"])
    fields.update(overrides)
    return oa3_tests._expression_receipt(**fields)


def _evidence(scenario, entry_rows=None, early=False):
    contract = dict(scenario["intent"]["contract"])
    boundary = _commitment(scenario)
    entry_event = boundary + timedelta(seconds=5)
    exit_event = entry_event + timedelta(minutes=60, seconds=5)

    def rows_at(event, **quote_overrides):
        return [oa3_tests._row_at(event, symbol=contract["root"],
                                  expiration=contract["expiration"],
                                  strike=contract["strike_millis"] / 1000,
                                  **quote_overrides)]

    mature = (boundary + timedelta(seconds=61), boundary + timedelta(seconds=62),
              boundary + timedelta(minutes=85), boundary + timedelta(minutes=85, seconds=1))
    if early:  # retrieval before the entry window closes: not yet terminal
        mature = (boundary + timedelta(seconds=10), boundary + timedelta(seconds=11),
                  boundary + timedelta(seconds=20), boundary + timedelta(seconds=21))
    entry = oa3_tests._evidence(
        role="entry", contract=contract, boundary_at=boundary,
        request_started_at=mature[0], response_observed_at=mature[1],
        retrieval_observed_at=mature[2], computed_at=mature[3],
        rows=rows_at(entry_event) if entry_rows is None else entry_rows)
    exit_ev = oa3_tests._evidence(
        role="exit", contract=contract,
        boundary_at=entry_event + timedelta(minutes=60),
        request_started_at=mature[0], response_observed_at=mature[1],
        retrieval_observed_at=mature[2], computed_at=mature[3],
        rows=rows_at(exit_event, bid="2.40", ask="2.50"))
    return entry, exit_ev


def _inputs(scenario, *, receipt_overrides=None, entry_rows=None,
            early=False, observed_at=None):
    entry, exit_ev = _evidence(scenario, entry_rows=entry_rows, early=early)
    if observed_at is None:
        observed_at = _z(_commitment(scenario) + timedelta(hours=2))
    return ExpressionOutcomeEvidence(
        publication_pair=scenario["pair"],
        expression=_receipt(scenario, **(receipt_overrides or {})),
        entry=entry, exit=exit_ev, observed_at=observed_at)


def _make(scenario, **kwargs):
    return make_expression_outcome(campaign=scenario["campaign"],
                                   evidence=_inputs(scenario, **kwargs))


def _reseal(row):
    row["evaluation_sha256"] = hashlib.sha256(
        campaigns.canonical_bytes(row["evaluation"])).hexdigest()


def test_positive_complete_row_binds_the_resolved_publication(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    row = _make(scenario)
    assert set(row) == {
        "schema", "expression_outcome_id", "campaign_id", "campaign_revision_id",
        "expression_id", "source_candidate_id", "horizon", "policy_id",
        "policy_sha256", "observed_at", "intent", "publication", "evaluation",
        "evaluation_sha256", "label_authority", "evidence_admission",
        "training_eligible", "authority"}
    assert (row["schema"], row["horizon"], row["label_authority"],
            row["evidence_admission"]) == (
        EXPRESSION_OUTCOME_SCHEMA, "h60", "research_only",
        "local_retained_evidence_not_source_admission")
    intent, availability, pair = (scenario["intent"], scenario["availability"],
                                 scenario["pair"])
    assert (row["expression_id"], row["source_candidate_id"]) == (
        intent["expression_id"], intent["candidate_id"])
    assert (row["campaign_id"], row["campaign_revision_id"]) == (
        scenario["campaign"]["campaign_id"],
        scenario["candidate"]["frozen_formation"]["campaign_revision_id"])
    assert (row["policy_id"], row["policy_sha256"]) == (
        oa3.FROZEN_POLICY_ID, oa3.FROZEN_POLICY_SHA256)
    assert row["training_eligible"] is False
    assert row["authority"] == campaigns.FALSE_AUTHORITY
    assert all(value is False for value in row["authority"].values())
    expected_id = "ocexout_" + hashlib.sha256(campaigns.canonical_bytes({
        "expression_id": intent["expression_id"], "policy_id": oa3.FROZEN_POLICY_ID,
        "policy_sha256": oa3.FROZEN_POLICY_SHA256, "horizon": "h60"})).hexdigest()[:24]
    assert row["expression_outcome_id"] == expected_id
    assert row["intent"] == intent
    assert row["publication"] == {
        "manifest_sha256": pair.expression_manifest_sha256,
        "receipt_id": pair.receipt["receipt_id"],
        "feed_payload_sha256": hashlib.sha256(pair.payload).hexdigest(),
        "first_receipt_id": availability["first_receipt_id"],
        "commitment_published_at": availability["commitment_published_at"],
        "intent_bytes_sha256": availability["intent_bytes_sha256"],
        "consumer": "incumbent_private_publisher_owner",
        "public_consumer_available": False}
    assert row["publication"]["public_consumer_available"] is False
    assert row["publication"]["intent_bytes_sha256"] == intent_readback.digest(intent)
    evaluation = row["evaluation"]
    assert evaluation["status"] == "complete" and evaluation["reason"] is None
    assert evaluation["net_return_pct"] == "3.771949"  # exact Decimal string view
    assert evaluation["entry"]["selected"]["price"] == "2.30"
    assert evaluation["authority"] == dict(oa3.ALL_FALSE_AUTHORITY)
    assert all(value is False for value in evaluation["authority"].values())
    entry, _ = _evidence(scenario)
    assert evaluation["entry"]["raw_response_sha256"] == entry.raw_sha256
    assert evaluation["entry"]["clocks"]["request_started_at"] \
        == entry.request_started_at.isoformat()
    assert row["evaluation_sha256"] == hashlib.sha256(
        campaigns.canonical_bytes(evaluation)).hexdigest()
    assert expression_outcome_key(row) == (
        "exact_option_expression", intent["expression_id"],
        oa3.FROZEN_POLICY_SHA256, "h60")
    again = validate_expression_outcome(row)
    again["intent"]["authority"]["may_rank"] = True
    assert row["intent"]["authority"]["may_rank"] is False


def test_positive_explicit_source_unavailable_terminal_row(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    row = _make(scenario, entry_rows=[])  # mature window, empty source array
    evaluation = row["evaluation"]
    assert evaluation["status"] == "unavailable"
    assert evaluation["reason"] == "ENTRY_QUOTE_UNAVAILABLE"
    assert evaluation["entry"]["clocks"]["retrieval_observed_at"] is not None
    assert evaluation["exit"]["clocks"]["request_started_at"] is None
    assert row["evaluation_sha256"] == hashlib.sha256(
        campaigns.canonical_bytes(evaluation)).hexdigest()
    validate_expression_outcome(row)


def test_default_midnight_fixture_is_excluded_not_an_entry(tmp_path, monkeypatch):
    # The base publisher fixture's midnight provider clock is 20:00 ET: it is
    # not an OA-3 entry at all.  The unchanged native ruler retains the
    # ENTRY_BOUNDARY_OUTSIDE_RTH exclusion as a terminal record, and the codec
    # persists that verdict with its bindings intact -- never as a complete.
    scenario = _scenario(tmp_path, monkeypatch, store=publisher_tests.MetadataS3())
    contract = dict(scenario["intent"]["contract"])
    midnight = _commitment(scenario)
    query = cohort.source_query(contract=contract, boundary_at=RTH_BASE,
                                available_at=RTH_BASE + timedelta(seconds=61))
    raw = cohort.canonical_json_bytes([])

    def at(role):
        return oa3.QuoteEvidence(
            role=role, contract=contract, boundary_at=midnight,
            query_end_at=midnight + timedelta(seconds=60), query=query,
            raw_bytes=raw, parsed_payload=[], parse_error=None,
            endpoint=cohort.SOURCE_ENDPOINT,
            request_started_at=midnight + timedelta(seconds=61),
            response_observed_at=midnight + timedelta(seconds=62),
            retrieval_observed_at=midnight + timedelta(minutes=85),
            computed_at=midnight + timedelta(minutes=85, seconds=1))

    evidence = ExpressionOutcomeEvidence(
        publication_pair=scenario["pair"], expression=_receipt(scenario),
        entry=at("entry"), exit=at("exit"),
        observed_at=_z(midnight + timedelta(hours=2)))
    row = make_expression_outcome(campaign=scenario["campaign"], evidence=evidence)
    assert row["evaluation"]["status"] == "excluded"
    assert row["evaluation"]["reason"] == "ENTRY_BOUNDARY_OUTSIDE_RTH"
    assert row["expression_id"] == scenario["intent"]["expression_id"]
    validate_expression_outcome(row)


def test_pending_is_refused_as_not_terminal(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    with pytest.raises(ExpressionOutcomeError):
        _make(scenario, early=True)


def test_codec_never_sets_the_selection_frozen_flag(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    row = _make(scenario, receipt_overrides={"selection_frozen_before_outcomes": False})
    assert row["evaluation"]["status"] == "invalid"
    assert row["evaluation"]["reason"] == "EXPRESSION_SELECTION_FENCE_NOT_FROZEN"
    assert row["evaluation"]["selection_frozen_before_outcomes"] is False
    # Native identity-defective reject shape stays representable: no canonical
    # contract ever existed on this path, so the record legitimately keeps it
    # null and the persisted validator must still accept the record as-is.
    assert row["evaluation"]["contract"] is None
    validate_expression_outcome(row)


@pytest.mark.parametrize("label,override", [
    ("wrong candidate", {"source_candidate_id": "ocam_" + "0" * 24}),
    ("wrong ruler version", {"policy_version": "v2"}),
    ("wrong selection rule digest", {"source_rule_digest_sha256": "e" * 64}),
    ("wrong intent digest", {"decision_receipt_sha256": "f" * 64}),
    ("wrong first commitment clock", {
        "available_at": _z(datetime(2026, 8, 14, 14, 36, 2, tzinfo=UTC))}),
    ("wrong decision clock", {"decision_at": "2026-08-13T14:32:02Z"}),
    ("wrong terms multiplier", {"multiplier": 500}),
    ("wrong terms deliverable", {"standard_deliverable": False}),
    ("wrong contract", {
        "right": "put",
        "occ_symbol": cohort.canonical_occ_symbol(
            root="NVDA", expiration="2026-08-21", right="put", strike_millis=225000)}),
])
def test_refuses_unbound_receipt_or_intent_values(tmp_path, monkeypatch, label, override):
    scenario = _scenario(tmp_path, monkeypatch)
    with pytest.raises(ExpressionOutcomeError):
        _make(scenario, receipt_overrides=override)


def test_refuses_campaign_revision_and_bytes_binding(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    wrong_revision = copy.deepcopy(scenario["campaign"])
    wrong_revision["campaign_revision_id"] = "ocrev_" + "a" * 24
    with pytest.raises(ExpressionOutcomeError):
        make_expression_outcome(campaign=wrong_revision, evidence=_inputs(scenario))
    unbound_bytes = copy.deepcopy(scenario["campaign"])
    unbound_bytes["descriptive"]["member_count"] += 1
    with pytest.raises(ExpressionOutcomeError):
        make_expression_outcome(campaign=unbound_bytes, evidence=_inputs(scenario))


def test_refuses_candidate_campaign_mismatch_in_feed(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    tampered_pair = copy.deepcopy(scenario["pair"])
    tampered_pair.feed["formed_candidates"][0]["campaign_id"] = "ocam_" + "1" * 24
    evidence = _inputs(scenario)
    with pytest.raises(ExpressionOutcomeError):
        make_expression_outcome(
            campaign=scenario["campaign"],
            evidence=ExpressionOutcomeEvidence(
                publication_pair=tampered_pair, expression=evidence.expression,
                entry=evidence.entry, exit=evidence.exit,
                observed_at=evidence.observed_at))


def test_refuses_bare_claimed_expression_without_native_wrapper(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    evidence = _inputs(scenario)
    claim = ExpressionOutcomeEvidence(
        publication_pair=scenario["pair"],
        expression=dict(evidence.expression.parsed_payload),
        entry=evidence.entry, exit=evidence.exit,
        observed_at=evidence.observed_at)
    with pytest.raises(ExpressionOutcomeError):
        make_expression_outcome(campaign=scenario["campaign"], evidence=claim)


def test_refuses_future_factual_clock_relative_to_observed(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    boundary = _commitment(scenario)
    with pytest.raises(ExpressionOutcomeError):
        _make(scenario, observed_at=_z(boundary + timedelta(seconds=30)))


def test_validator_rejects_tampered_persisted_rows(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    base = _make(scenario)

    def flip_evaluation(field, value):
        def mutate(row):
            row["evaluation"][field] = value
            _reseal(row)
        return mutate

    def future_factual_clock(row):
        late = datetime.fromisoformat(
            base["observed_at"].replace("Z", "+00:00")) + timedelta(hours=1)
        late = datetime.fromisoformat(
            base["observed_at"].replace("Z", "+00:00")) + timedelta(hours=1)
        row["evaluation"]["entry"]["clocks"]["request_started_at"] = _z(late)
        _reseal(row)

    for mutate in (
        lambda row: row.__setitem__("memo", "caller claim"),
        lambda row: row.pop("evaluation_sha256"),
        lambda row: row.__setitem__("expression_outcome_id", "ocexout_" + "0" * 24),
        lambda row: row["authority"].__setitem__("may_trade", 0),
        lambda row: row.__setitem__("training_eligible", 0),
        lambda row: row["publication"].__setitem__("public_consumer_available", 0),
        lambda row: row["publication"].__setitem__("memo", "x"),
        lambda row: row["publication"].__setitem__("intent_bytes_sha256", "1" * 64),
        lambda row: row["evaluation"].__setitem__("x", 1),
        flip_evaluation("status", "pending"),
        flip_evaluation("expression_id", "oaexprintent_" + "9" * 64),
        flip_evaluation("standard_deliverable", False),
        future_factual_clock,
    ):
        row = copy.deepcopy(base)
        mutate(row)
        with pytest.raises(ExpressionOutcomeError):
            validate_expression_outcome(row)


def test_validator_rejects_observed_before_commitment(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    row = _make(scenario)
    row["observed_at"] = scenario["availability"]["commitment_published_at"]
    # exactly the commitment clock is still >= decision, but precedes every
    # factual evidence clock retained in the evaluation:
    with pytest.raises(ExpressionOutcomeError):
        validate_expression_outcome(row)


def test_caller_mutation_never_reaches_the_built_row(tmp_path, monkeypatch):
    scenario = _scenario(tmp_path, monkeypatch)
    row = _make(scenario)
    snapshot = copy.deepcopy(row)
    scenario["campaign"]["authority"]["may_trade"] = True
    scenario["campaign"]["descriptive"]["member_count"] = 424242
    scenario["intent"]["decision_at"] = "2020-01-01T00:00:00Z"
    scenario["pair"].feed["formed_candidates"][0]["campaign_id"] = "ocam_" + "2" * 24
    assert row == snapshot
    assert validate_expression_outcome(row) == snapshot
    mutated_output = validate_expression_outcome(row)
    mutated_output["publication"]["receipt_id"] = "oacfr_" + "0" * 25
    assert row == snapshot


# ── Persisted terminal-shape repair: discriminating rehashed mutations ──────
# The baseline validator accepted each evaluation mutation below once
# ``evaluation_sha256`` was recomputed over the tampered record (and a
# malformed clock block crashed it with KeyError instead of a typed refusal).
# The genuine native evaluator fixture itself is unchanged: these cases only
# bind validate_expression_outcome to the exact terminal record the unchanged
# OA-3 builders emit for each status.


def _shape_mutations():
    def contract_null(row):
        row["evaluation"]["contract"] = None

    def contract_deleted(row):
        row["evaluation"].pop("contract")

    def entry_block_emptied(row):
        row["evaluation"]["entry"] = {}

    def entry_clocks_deleted(row):
        row["evaluation"]["entry"].pop("clocks")

    def entry_clocks_null(row):
        row["evaluation"]["entry"]["clocks"] = None

    def entry_clocks_emptied(row):
        row["evaluation"]["entry"]["clocks"] = {}

    def entry_clock_extra_field(row):
        row["evaluation"]["entry"]["clocks"]["ingested_at"] = \
            row["evaluation"]["entry"]["clocks"]["computed_at"]

    def exit_clock_fields_missing(row):
        row["evaluation"]["exit"]["clocks"] = {"request_started_at": None}

    def complete_digest_blank(row):
        row["evaluation"]["expression_digest_sha256"] = ""

    def complete_raw_receipt_identity_blank(row):
        row["evaluation"]["expression_raw_response_sha256"] = ""
        row["evaluation"]["expression_raw_response_bytes"] = 0

    def complete_return_null(row):
        row["evaluation"]["net_return_pct"] = None

    def complete_not_selection_frozen(row):
        row["evaluation"]["selection_frozen_before_outcomes"] = False

    def complete_session_missing(row):
        row["evaluation"]["session_date"] = None

    def complete_terms_missing(row):
        row["evaluation"]["multiplier"] = None
        row["evaluation"]["standard_deliverable"] = None

    def complete_decision_clock_deleted(row):
        row["evaluation"].pop("expression_decision_at")

    def complete_selected_quotes_removed(row):
        row["evaluation"]["entry"]["selected"] = None
        row["evaluation"]["exit"]["selected"] = None

    def complete_exit_query_bounds_removed(row):
        row["evaluation"]["exit"]["query_bounds"] = None

    def complete_entry_window_rebound(row):
        row["evaluation"]["entry"]["query_bounds"]["start_at"] = \
            row["evaluation"]["exit"]["query_bounds"]["start_at"]

    def entry_block_role_flipped(row):
        row["evaluation"]["entry"]["role"] = "exit"
        row["evaluation"]["entry"]["side"] = "bid"

    def cost_block_grown(row):
        row["evaluation"]["cost"]["memo"] = "caller note"

    def quote_source_endpoint_tampered(row):
        row["evaluation"]["quote_source"]["endpoint"] = "/v3/attacker/quote"

    def evaluation_key_grown(row):
        row["evaluation"]["memo"] = "caller claim"

    return [
        ("complete contract=None", contract_null),
        ("complete contract key deleted", contract_deleted),
        ("entry block emptied to {}", entry_block_emptied),
        ("entry factual clocks deleted", entry_clocks_deleted),
        ("entry factual clocks null", entry_clocks_null),
        ("entry factual clocks emptied", entry_clocks_emptied),
        ("entry factual clock set grown", entry_clock_extra_field),
        ("exit factual clock set truncated", exit_clock_fields_missing),
        ("complete native digest blanked", complete_digest_blank),
        ("complete raw receipt identity blanked", complete_raw_receipt_identity_blank),
        ("complete return nulled", complete_return_null),
        ("complete record not selection-frozen", complete_not_selection_frozen),
        ("complete session date removed", complete_session_missing),
        ("complete explicit terms removed", complete_terms_missing),
        ("complete decision clock removed", complete_decision_clock_deleted),
        ("complete observed quotes removed", complete_selected_quotes_removed),
        ("complete exit query bounds removed", complete_exit_query_bounds_removed),
        ("complete entry window rebound to exit", complete_entry_window_rebound),
        ("entry block role/side flipped", entry_block_role_flipped),
        ("cost block grown", cost_block_grown),
        ("quote source endpoint tampered", quote_source_endpoint_tampered),
        ("evaluation record key grown", evaluation_key_grown),
    ]


_SHAPE_MUTATIONS = _shape_mutations()


@pytest.mark.parametrize("label,mutate", _SHAPE_MUTATIONS,
                         ids=[label for label, _ in _SHAPE_MUTATIONS])
def test_validator_rejects_rehashed_terminal_shape_mutations(
        tmp_path, monkeypatch, label, mutate):
    base = _make(_scenario(tmp_path, monkeypatch))
    validate_expression_outcome(copy.deepcopy(base))  # genuine row still validates
    row = copy.deepcopy(base)
    mutate(row)
    _reseal(row)  # the reproduced attack: rehash after mutating the record
    with pytest.raises(ExpressionOutcomeError):
        validate_expression_outcome(row)


def test_validator_keeps_native_reject_shapes_representable(tmp_path, monkeypatch):
    # unavailable/excluded keep their native empty/None-valued blocks and the
    # invalid identity-defective record keeps contract null; none of the new
    # terminal-shape checks may normalize or refuse those genuine records.
    scenario = _scenario(tmp_path / "unavailable", monkeypatch)
    validate_expression_outcome(_make(scenario, entry_rows=[]))  # unavailable
    excluded = _scenario(tmp_path / "excluded", monkeypatch,
                         store=publisher_tests.MetadataS3())
    contract = dict(excluded["intent"]["contract"])
    boundary = _commitment(excluded)
    query = cohort.source_query(contract=contract, boundary_at=RTH_BASE,
                                available_at=RTH_BASE + timedelta(seconds=61))
    raw = cohort.canonical_json_bytes([])

    def at(role):
        return oa3.QuoteEvidence(
            role=role, contract=contract, boundary_at=boundary,
            query_end_at=boundary + timedelta(seconds=60), query=query,
            raw_bytes=raw, parsed_payload=[], parse_error=None,
            endpoint=cohort.SOURCE_ENDPOINT,
            request_started_at=boundary + timedelta(seconds=61),
            response_observed_at=boundary + timedelta(seconds=62),
            retrieval_observed_at=boundary + timedelta(minutes=85),
            computed_at=boundary + timedelta(minutes=85, seconds=1))

    row = make_expression_outcome(
        campaign=excluded["campaign"],
        evidence=ExpressionOutcomeEvidence(
            publication_pair=excluded["pair"], expression=_receipt(excluded),
            entry=at("entry"), exit=at("exit"),
            observed_at=_z(boundary + timedelta(hours=2))))
    assert row["evaluation"]["status"] == "excluded"
    assert row["evaluation"]["entry"]["clocks"]["request_started_at"] is None
    validate_expression_outcome(row)


@pytest.mark.parametrize("path,value", [
    (("net_return_pct",), "not-a-decimal"),
    (("net_return_pct",), "NaN"),
    (("net_return_pct",), "Infinity"),
    (("session_date",), "not-a-date"),
    (("session_rth_open",), "not-a-clock"),
    (("selection_fence_at",), "not-a-clock"),
    (("position",), "short"),
    (("quantity_contracts",), 0),
    (("quantity_contracts",), 2),
    (("entry", "selected", "price"), "NaN"),
    (("entry", "selected", "price"), "not-a-decimal"),
])
def test_validator_refuses_rehashed_scalar_shape_corruption(
        tmp_path, monkeypatch, path, value):
    row = _make(_scenario(tmp_path, monkeypatch))
    target = row["evaluation"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    _reseal(row)
    with pytest.raises(ExpressionOutcomeError):
        validate_expression_outcome(row)
