"""Connected per-decision prefix driver tests; invented fixtures, zero real effects.

Everything here is hermetic: the engine is always a scripted fake, the candidate
``feature`` source bytes are never imported, compiled or executed on this host, and
no provider, container runtime or subprocess is ever started.  The capture,
manifest, owner-reference and accounting fixtures are rebuilt structurally from the
accepted contract modules because the supplied snapshot does not carry the
incumbent ``lib.store`` capture helper or the ``TrialLedger`` bookkeeping used by
the historical bridge fixture; that dependency limitation is deliberate and no
provider call replaces it.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import ast
import base64
import hashlib
import inspect
import json
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from engine.research_codegen import bridge as b, evaluation, prefix_driver as pd_mod
from engine.research_codegen import transport as tp

CID = "ab" * 32
CID_STDOUT = (CID + "\n").encode("ascii")
ABSENT_STDERR = ("Error response from daemon: No such container: " + CID + "\n").encode("ascii")
ROOT_ID = "fixture-root-1"


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def bound(value):
    raw = value if type(value) is bytes else encoded(value)
    return b.BoundBytes(raw, hashlib.sha256(raw).hexdigest(), len(raw))


def hexid(number):
    return "%064x" % number


# ---------------------------------------------------------------------------
# Owner candidate source bytes.  Source text only: never executed on this host.
# ---------------------------------------------------------------------------

KNOWN_ANSWER_SOURCE = b"""
import json

COHORT = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")


def feature(input_envelope):
    node = input_envelope["entity_id"]
    return {"decision_id": input_envelope["decision_id"], "status": "available",
            "value": 9 - COHORT.index(node), "reason": None}
"""

TEMPORAL_BAD_SOURCE = b"""
import json

COHORT = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")


def feature(input_envelope):
    # Temporal leakage: reads an observation positioned after the decision cutoff.
    future = input_envelope["observations"][70]
    return {"decision_id": input_envelope["decision_id"], "status": "available",
            "value": future["value"], "reason": None}
"""


def source_binding(raw=KNOWN_ANSWER_SOURCE):
    return b.BoundBytes(raw, hashlib.sha256(raw).hexdigest(), len(raw))


# ---------------------------------------------------------------------------
# Structural fixtures rebuilt from the accepted contract modules.
# ---------------------------------------------------------------------------

def trusted_protocol():
    return dict(schema="research_codegen.protocol.v1", protocol_sha256=hexid(1),
                input_policy_sha256=hexid(2), runtime_sha256=hexid(3),
                evaluator_sha256=hexid(4), trial_family="rf.prefix_driver.fixture",
                original_root_id=ROOT_ID,
                required_evidence=["writer_receipt", "durable_readback"])


def valid_manifest(protocol, source_sha256):
    return dict(schema="research_codegen.manifest.v1", candidate_id="rf-codegen-prefix-fixture",
                source_sha256=source_sha256, config_sha256=hexid(6),
                protocol_sha256=protocol["protocol_sha256"],
                input_policy_sha256=protocol["input_policy_sha256"],
                runtime_sha256=protocol["runtime_sha256"],
                evaluator_sha256=protocol["evaluator_sha256"],
                trial_family=protocol["trial_family"],
                lineage=dict(original_root_id=ROOT_ID, parent_candidate_id=None,
                             refinement_generation=0),
                morphology="research_feature", authority="display_only")


def owner_receipts(manifest):
    return {name: dict(schema="research_codegen.owner_reference.v1", evidence_id=name,
                       source_sha256=manifest["source_sha256"],
                       protocol_sha256=manifest["protocol_sha256"])
            for name in ("writer_receipt", "durable_readback")}


def accounting_pair(manifest):
    """Two retained variants: the known answer and the controlled temporal refusal."""
    variants = [dict(variant_id="fixture-known-answer", source_sha256=manifest["source_sha256"],
                     config_sha256=manifest["config_sha256"], incumbent_config_hash="a" * 16),
                dict(variant_id="fixture-controlled-refusal", source_sha256=hexid(8),
                     config_sha256=hexid(9), incumbent_config_hash="b" * 16)]
    expected = dict(schema="research_codegen.expected_generation.v1",
                    original_root_id=ROOT_ID, family=manifest["trial_family"],
                    protocol_sha256=manifest["protocol_sha256"], history_anchor_sha256=hexid(10),
                    variants=variants, inherited_variants=[], trial_ceiling=4,
                    vault_required=False, vault_request=None)
    trial = dict(schema="research_codegen.trial_readback_reference.v1",
                 original_root_id=ROOT_ID, family=manifest["trial_family"],
                 protocol_sha256=manifest["protocol_sha256"], history_anchor_sha256=hexid(10),
                 snapshot_sha256=hexid(11), snapshot_bytes=128, writer_receipt_sha256=hexid(12),
                 durable_readback_receipt_sha256=hexid(13), history_state="complete",
                 load_error=None, corrupt_lines=0, recorded_variants=variants,
                 declared_floor=2, literal_n=2, effective_n=2)
    return expected, trial


def make_capture(node, retained_dates, trigger_date, last_value=10.0):
    known = trigger_date + "T21:05:00+00:00"
    captured = trigger_date + "T21:06:00+00:00"
    durable = trigger_date + "T21:07:00+00:00"
    received = trigger_date + "T21:11:00+00:00"
    rows = [[day, 10.0] for day in retained_dates]
    rows[-1][1] = last_value
    image = dict(encoding="dated_numeric_frame_json.v1", columns=["close"], rows=rows)
    image_binding = bound(image)
    reference = dict(sha256=image_binding.sha256, bytes=image_binding.size,
                     object_ref="objects/" + image_binding.sha256 + ".json")
    receipt = dict(schema="yahoo.availability_capture.v1", ticker=node,
                   provider_return_image=dict(
                       reference, adapter_return_known_by_utc=known, basis="total_return",
                       scope="validated_session_filtered_adapter_output_not_vendor_wire"),
                   merged_capture_image=dict(
                       reference, captured_known_by_utc=captured,
                       immutable_publication_durable_at_utc=durable, basis="total_return",
                       scope="separate_capture_of_returned_merged_values"),
                   provider_available_at=None, operation_identity="fixture-operation",
                   source_code_identity=hexid(14), rights_reference="fixture-rights",
                   clock_attestation="fixture-clock", source_actor_authentication="fixture-actor",
                   calendar_verification="fixture-calendar",
                   upstream_revision_history_complete=True,
                   historical_original_availability_proven=True,
                   canonical_cache_transaction_durability="fixture-durable")
    clocks = tuple((day, day + "T21:00:00Z") for day in retained_dates)
    return b.CaptureBinding(node, "fixture-yahoo", bound(receipt), image_binding, image_binding,
                            received, clocks)


def make_case(source_sha256=None, warm_node=None):
    source_sha256 = source_sha256 or hashlib.sha256(KNOWN_ANSWER_SOURCE).hexdigest()
    protocol = trusted_protocol()
    manifest = valid_manifest(protocol, source_sha256)
    expected, trial = accounting_pair(manifest)
    dates = tuple(day.strftime("%Y-%m-%d") for day in pd.bdate_range("2008-01-01", "2010-07-01"))
    anchor = dates.index(evaluation.FORMATION_ANCHOR)
    eligible = (evaluation.COHORT[:2], (), evaluation.COHORT[:4], ())
    positions = tuple(b.SchedulePosition(index, dates[anchor + 26 * index], eligible[index],
        tuple((node, "source_unavailable" if index == 1 and node == "XLY" else "qualified")
              for node in evaluation.COHORT)) for index in range(4))
    decisions = []
    for position in positions:
        for node in position.eligible_nodes:
            offset = anchor + 26 * position.calendar_index
            cutoff = datetime.fromisoformat(dates[offset + 1] + "T09:00:00")
            cutoff = cutoff.replace(tzinfo=ZoneInfo("America/New_York"))
            request = dict(schema="research_codegen.request.v1",
                           candidate_id=manifest["candidate_id"], fold_id="invented",
                           entity_id=node,
                           decision_id="d%d-%s" % (position.calendar_index, node),
                           cutoff=cutoff.isoformat(),
                           input_policy_sha256=manifest["input_policy_sha256"],
                           allowed_source_ids=["fixture-yahoo"])
            retained = dates[offset - 70:offset + 1]
            capture = make_capture(node, retained, position.trigger_date,
                                   last_value=None if node == warm_node else 10.0)
            decisions.append(b.DecisionBinding(position.calendar_index, node, bound(request), capture))
    schedules = tuple(bound(dict(schema="research_codegen.schedule.v1",
        candidate_id=manifest["candidate_id"], fold_id="invented", entity_id=node,
        input_policy_sha256=manifest["input_policy_sha256"],
        decision_ids=[json.loads(item.request.raw)["decision_id"]
                      for item in decisions if item.node == node]))
        for node in evaluation.COHORT[:4])
    losses = {0: {"XLB": .1, "XLE": .3}, 2: {"XLB": .1, "XLE": .2, "XLF": .5, "XLI": .8}}
    paths = []
    for node in evaluation.COHORT:
        returns = [0.0] * len(dates)
        for index, table in losses.items():
            returns[anchor + 26 * index + 2] = -table.get(node, 0.0)
        paths.append(evaluation.SourcePath(node, dates, tuple(returns)))
    identity = b.ArtifactBinding("/fixture/staging/diagnostic.json", hexid(20), 1,
        "fixture-diagnostic", ROOT_ID, manifest["candidate_id"],
        *(manifest[key] for key in ("source_sha256", "config_sha256", "protocol_sha256",
                                    "input_policy_sha256", "runtime_sha256", "evaluator_sha256")))
    commission = b.SyntheticTestCommission(ROOT_ID, "/fixture/staging")
    run = b.SyntheticRun(identity, "2010-07-01T22:00:00Z", bound(manifest), bound(protocol),
        bound(owner_receipts(manifest)), bound(expected), bound(trial), positions,
        tuple(decisions), schedules, (), tuple(paths), dates)
    return run, commission, manifest, expected, trial


def accepted_outputs(run):
    """Known-answer whole-run outputs, hand-designed exactly as the accepted fixture."""
    outputs = []
    for schedule in run.schedules:
        value = json.loads(schedule.raw)
        outputs.append(bound({**{key: item for key, item in value.items() if key != "decision_ids"},
            "schema": "research_codegen.output.v1",
            "rows": [dict(decision_id=identifier, status="available",
                          value=9 - evaluation.COHORT.index(value["entity_id"]), reason=None)
                     for identifier in value["decision_ids"]]}))
    return tuple(outputs)


def spec(**overrides):
    values = dict(image="registry.example/repo@sha256:" + "ef" * 32,
                  entrypoint="/usr/local/bin/python", docker_binary="/usr/bin/docker",
                  uid=4711, gid=4712, pids_limit=256, memory_bytes=268435456, cpus=1.5,
                  wall_clock_seconds=60.0, output_cap_bytes=65536, tmpfs_bytes=16777216,
                  stop_timeout_seconds=10.0, max_attempts=64, total_wall_seconds=600.0)
    values.update(overrides)
    return pd_mod.PrefixTransportSpec(**values)


def known_answer(decision_id):
    node = decision_id.split("-")[1]
    return dict(decision_id=decision_id, status="available",
                value=9 - evaluation.COHORT.index(node), reason=None)


class ScriptedFakeEngine:
    """Reads the carrier from the create command line exactly as the owner runner
    documents it, then returns a scripted row on the attached start.  The candidate
    source bytes are hashed for identity and never executed; every bounded call and
    every decoded envelope is recorded."""

    def __init__(self, behaviour=None):
        self.calls = []
        self.creates = 0
        self.envelopes = []
        self.behaviour = dict(behaviour or {})
        self._pending = None

    def run(self, argv, *, deadline_seconds, output_cap_bytes):
        assert type(argv) is tuple and all(isinstance(item, str) for item in argv)
        assert deadline_seconds > 0 and output_cap_bytes > 0
        self.calls.append({"argv": argv, "deadline": deadline_seconds, "cap": output_cap_bytes})
        subcommand = argv[1]
        if subcommand == "create":
            self.creates += 1
            self._pending = self._decode(argv)
            return tp.EngineCommandResult(0, CID_STDOUT, b"", deadline_seconds, output_cap_bytes,
                                          observed_container_id=CID)
        if subcommand == "start":
            return tp.EngineCommandResult(self.behaviour.get("start_rc", 0), self._workload(),
                                          b"", deadline_seconds, output_cap_bytes,
                                          observed_container_id=CID)
        if subcommand == "inspect" and "--format" in argv:
            state = self.behaviour.get("exit_state") or {"Running": False, "ExitCode": 0,
                                                         "OOMKilled": False}
            return tp.EngineCommandResult(0, json.dumps([CID, state]).encode("ascii"), b"",
                                          deadline_seconds, output_cap_bytes,
                                          observed_container_id=CID)
        if subcommand == "inspect":
            if self.behaviour.get("absence", "absent") == "absent":
                return tp.EngineCommandResult(1, b"[]\n", ABSENT_STDERR, deadline_seconds,
                                              output_cap_bytes)
            return tp.EngineCommandResult(0, b"", b"", deadline_seconds, output_cap_bytes)
        return tp.EngineCommandResult(0, b"", b"", deadline_seconds, output_cap_bytes)

    def _decode(self, argv):
        """The container command line is the only carrier channel: no stdin, mount
        or extra flag.  The item after ``-c`` is the fixed runner, then the header,
        then the base64 carrier chunks."""
        marker = argv.index("-c")
        header = json.loads(argv[marker + 2])
        body = "".join(argv[marker + 3:])
        assert len(argv) - (marker + 3) == header["chunks"]
        assert len(body) == header["carrier_b64_chars"]
        assert hashlib.sha256(body.encode("ascii")).hexdigest() == header["carrier_b64_sha256"]
        carrier = base64.b64decode(body.encode("ascii"), validate=True)
        assert len(carrier) == header["carrier_bytes"]
        assert hashlib.sha256(carrier).hexdigest() == header["carrier_sha256"]
        parts = json.loads(carrier.decode("utf-8"))
        source = base64.b64decode(parts["source_b64"], validate=True)
        payload = base64.b64decode(parts["input_b64"], validate=True)
        assert hashlib.sha256(source).hexdigest() == header["source_sha256"]
        assert hashlib.sha256(payload).hexdigest() == header["input_sha256"]
        return json.loads(payload.decode("utf-8"))

    def _workload(self):
        envelope = self._pending
        self.envelopes.append(envelope)
        override = self.behaviour.get("workload")
        if callable(override):
            body = override(envelope)
            if body is not None:
                return body
        elif override is not None:
            return override
        return encoded({"schema": "research_codegen.output.v1",
                        "candidate_id": envelope["candidate_id"],
                        "fold_id": envelope["fold_id"], "entity_id": envelope["entity_id"],
                        "input_policy_sha256": envelope["input_policy_sha256"],
                        "rows": [known_answer(envelope["decision_id"])]})


@pytest.fixture()
def case():
    return make_case()


def prepare(case):
    run, commission = case[0], case[1]
    return b.prepare_synthetic_inputs(run, commission=commission)


def drive(prepared, engine, *, source=None, spec_override=None, config_sha256=hexid(6)):
    return pd_mod.run_prefix_driver(prepared, source=source or source_binding(), engine=engine,
                                   spec=spec(**(spec_override or {})),
                                   config_sha256=config_sha256)


# ---------------------------------------------------------------------------
# Connected end-to-end: preparer -> fake transport -> outputs -> compute -> public
# ---------------------------------------------------------------------------

def test_connected_preparer_fake_transport_outputs_and_public_diagnostic(case):
    run, commission, manifest, expected, trial = case
    prepared = b.prepare_synthetic_inputs(run, commission=commission)
    assert len(prepared.decisions) == 6 and len(prepared.schedules) == 4
    assert prepared.identity.candidate_id == manifest["candidate_id"]
    assert prepared.identity.source_sha256 == manifest["source_sha256"]
    engine = ScriptedFakeEngine()
    outcome = drive(prepared, engine, config_sha256=manifest["config_sha256"])
    assert outcome.completed and outcome.refusal_reasons == ()
    assert len(outcome.attempts) == 6 and engine.creates == 6
    assert len({attempt.operation_id for attempt in outcome.attempts}) == 6
    assert all(attempt.state == "cleaned_success" for attempt in outcome.attempts)
    assert all(attempt.workload_returncode == 0 for attempt in outcome.attempts)
    assert all(attempt.cleanup_confirmed and not attempt.execution_uncertain
               for attempt in outcome.attempts)
    assert len(outcome.outputs) == 4
    for attempt, task, envelope in zip(outcome.attempts, prepared.decisions, engine.envelopes):
        assert attempt.decision_id == task.decision_id
        assert attempt.input_sha256 == task.input_bytes.sha256
        assert envelope["decision_id"] == task.decision_id
        assert envelope["schema"] == "research_codegen.input.v1"
        assert len(envelope["observations"]) == 63
    # Grouped outputs drive the existing whole-run diagnostic unchanged.
    raw = pd_mod.connect_prepared_outputs(run, outcome, commission=commission)
    binding = replace(run.identity, artifact_sha256=hashlib.sha256(raw).hexdigest(),
                      artifact_bytes=len(raw))
    read = b.decode_bound_artifact(raw, expected=binding, commission=commission)
    aggregate = dict(read.aggregates)
    assert read.status == "DIAGNOSTIC_ONLY"
    assert [aggregate[key] for key in ("scheduled_formation_count",
                                       "source_excluded_formation_count",
                                       "source_qualified_formation_count",
                                       "no_opportunity_formation_count",
                                       "opportunity_formation_count",
                                       "paired_formation_count")] == [4, 1, 3, 1, 2, 2]
    assert aggregate["paired_mean_baseline_adverse_loss"] == pytest.approx(.3)
    assert aggregate["paired_mean_selected_adverse_loss"] == pytest.approx(.125)
    assert aggregate["paired_mean_improvement"] == pytest.approx(.175)
    public = b.public_diagnostic(read)
    assert not any(public[key] for key in ("generation_enabled", "execution_enabled",
                                           "evaluation_enabled", "authority_granted"))
    assert public["scientific_acceptance"] == "UNQUALIFIED"
    assert all(token not in encoded(public).decode()
               for token in ("XLB", "observations", "decision_ids", "source_b64", "cutoff"))


def test_bridge_seam_is_pure_and_preserves_whole_run_semantics(case):
    run, commission, manifest, expected, trial = case
    complete = replace(run, outputs=accepted_outputs(run))
    assert b.compute_synthetic_diagnostic(complete, commission=commission) == \
           b.compute_synthetic_diagnostic(complete, commission=commission)
    prepared = b.prepare_synthetic_inputs(complete, commission=commission)
    assert len(prepared.decisions) == 6
    engine = ScriptedFakeEngine()
    outcome = drive(prepared, engine, config_sha256=manifest["config_sha256"])
    assert pd_mod.connect_prepared_outputs(complete, outcome, commission=commission) == \
           b.compute_synthetic_diagnostic(complete, commission=commission)
    empty = replace(run, positions=tuple(replace(p, eligible_nodes=()) for p in run.positions),
                    decisions=(), schedules=(), outputs=())
    empty_prepared = b.prepare_synthetic_inputs(empty, commission=commission)
    assert empty_prepared.decisions == () and empty_prepared.schedules == ()
    idle = ScriptedFakeEngine()
    outcome = drive(empty_prepared, idle, config_sha256=manifest["config_sha256"])
    assert outcome.completed and outcome.outputs == () and idle.calls == []


def test_per_decision_prefix_and_causal_suffix_independence(case):
    run, commission, manifest, expected, trial = case
    prepared = b.prepare_synthetic_inputs(run, commission=commission)
    early = prepared.decisions[0]
    late = [task for task in prepared.decisions if task.calendar_index == 2][0]
    early_envelope = json.loads(early.input_bytes.raw.decode("utf-8"))
    late_envelope = json.loads(late.input_bytes.raw.decode("utf-8"))
    assert early.cutoff < late.cutoff
    assert len(early_envelope["observations"]) == len(late_envelope["observations"]) == 63
    assert early_envelope["observations"][-1]["event_time"] \
        < late_envelope["observations"][-1]["event_time"]
    assert late_envelope["decision_id"] != early_envelope["decision_id"]
    # Suffix independence: retained labels and return paths never enter any carrier.
    labelled = replace(run, outputs=accepted_outputs(run),
                       paths=tuple(replace(p, returns=tuple(9.0 for _ in p.returns))
                                   for p in run.paths))
    relabelled = b.prepare_synthetic_inputs(labelled, commission=commission)
    assert [task.input_bytes.raw for task in relabelled.decisions] \
        == [task.input_bytes.raw for task in prepared.decisions]
    carrier = pd_mod.build_carrier(source_binding().raw, late.input_bytes.raw)[2]
    for token in (b"9.0", b"decision_ids", b"baseline_entries", b"/fixture/staging", b"ret_exit"):
        assert token not in carrier, token


def test_missing_and_warmup_rows_are_preserved_not_invented():
    warm_run, warm_commission, warm_manifest, expected, trial = make_case(warm_node="XLF")
    prepared = b.prepare_synthetic_inputs(warm_run, commission=warm_commission)
    assert [task.complete_trailing for task in prepared.decisions] == \
        [True, True, True, True, False, True]
    warm_task = [task for task in prepared.decisions if not task.complete_trailing][0]
    assert warm_task.decision_id == "d2-XLF"

    def warm_row(envelope):
        if envelope["decision_id"] != warm_task.decision_id:
            return None
        return encoded({"schema": "research_codegen.output.v1",
                        "candidate_id": warm_manifest["candidate_id"], "fold_id": "invented",
                        "entity_id": "XLF",
                        "input_policy_sha256": warm_manifest["input_policy_sha256"],
                        "rows": [dict(decision_id=warm_task.decision_id, status="warmup",
                                      value=None, reason="insufficient trailing coverage")]})

    engine = ScriptedFakeEngine(behaviour={"workload": warm_row})
    outcome = drive(prepared, engine, config_sha256=warm_manifest["config_sha256"])
    assert outcome.completed and len(outcome.outputs) == 4
    grouped = [json.loads(item.raw.decode("utf-8")) for item in outcome.outputs]
    warm_output = [item for item in grouped if item["entity_id"] == "XLF"][0]
    assert warm_output["rows"][0]["status"] == "warmup"
    assert warm_output["rows"][0]["value"] is None
    assert warm_output["rows"][0]["decision_id"] == "d2-XLF"
    # The whole-run diagnostic refuses; nothing is zero-filled, dropped or salvaged.
    raw = pd_mod.connect_prepared_outputs(warm_run, outcome, commission=warm_commission)
    value = json.loads(raw.decode("utf-8"))
    assert value["evaluation"]["status"] == "REFUSED"
    assert len(expected["variants"]) == 2 and len(trial["recorded_variants"]) == 2
    binding = replace(warm_run.identity, artifact_sha256=hashlib.sha256(raw).hexdigest(),
                      artifact_bytes=len(raw))
    read = b.decode_bound_artifact(raw, expected=binding, commission=warm_commission)
    aggregate = dict(read.aggregates)
    assert aggregate["refusal_count"] > 0
    assert aggregate["paired_mean_improvement"] is None
    assert aggregate["scheduled_formation_count"] == 4
    assert aggregate["source_excluded_formation_count"] == 1
    assert aggregate["source_qualified_formation_count"] == 3


def test_temporal_bad_variant_refuses_and_both_variants_remain_described(case):
    run, commission, manifest, expected, trial = case
    temporal_manifest_sha = hashlib.sha256(TEMPORAL_BAD_SOURCE).hexdigest()
    temporal_run, temporal_commission, temporal_manifest, _, _ = make_case(
        source_sha256=temporal_manifest_sha)
    temporal_prepared = b.prepare_synthetic_inputs(temporal_run, commission=temporal_commission)
    # The future-reading source bytes are carried, hashed and never executed; the
    # nonfinite value they would surface is injected as raw carrier text.
    nonfinite = json.dumps({"schema": "research_codegen.output.v1",
        "candidate_id": temporal_manifest["candidate_id"], "fold_id": "invented",
        "entity_id": "XLB", "input_policy_sha256": temporal_manifest["input_policy_sha256"],
        "rows": [dict(decision_id=temporal_prepared.decisions[0].decision_id,
                      status="available", value=float("inf"), reason=None)]},
        allow_nan=True).encode()
    assert b"Infinity" in nonfinite
    outcome = drive(temporal_prepared, ScriptedFakeEngine(behaviour={"workload": nonfinite}),
                    source=source_binding(TEMPORAL_BAD_SOURCE),
                    config_sha256=temporal_manifest["config_sha256"])
    assert not outcome.completed and len(outcome.attempts) == 1
    assert outcome.attempts[0].state == "cleaned_success"
    assert outcome.refusal_reasons[0] in ("OUTPUT_CONTRACT_REFUSED", "INVALID_OUTPUT_JSON",
                                          "NONFINITE_JSON")
    assert outcome.outputs == ()
    # The accounting descriptors of the control case still carry both variants.
    control = json.loads(run.expected_generation.raw.decode("utf-8"))
    assert [v["variant_id"] for v in control["variants"]] == \
           ["fixture-known-answer", "fixture-controlled-refusal"]
    readback = json.loads(run.trial_readback.raw.decode("utf-8"))
    assert len(readback["recorded_variants"]) == 2


# ---------------------------------------------------------------------------
# Pre-I/O refusals
# ---------------------------------------------------------------------------

def test_identity_mismatch_and_oversize_refuse_before_any_io(case):
    run, commission, manifest, expected, trial = case
    prepared = b.prepare_synthetic_inputs(run, commission=commission)
    engine = ScriptedFakeEngine()

    def refused(raw, why, target=None, config=manifest["config_sha256"]):
        with pytest.raises(pd_mod.PrefixDriverRefused, match=why):
            pd_mod.run_prefix_driver(target or prepared, source=raw, engine=engine, spec=spec(),
                                     config_sha256=config)
        assert engine.calls == [] and engine.creates == 0

    oversized = b"x" * (pd_mod.MAX_SOURCE_BYTES + 1)
    oversized_binding = b.BoundBytes(oversized, hashlib.sha256(oversized).hexdigest(), len(oversized))
    widened = replace(prepared, identity=replace(prepared.identity,
                                                 source_sha256=oversized_binding.sha256))
    refused(oversized_binding, "SOURCE", target=widened)
    refused(b.BoundBytes(KNOWN_ANSWER_SOURCE, hexid(99), len(KNOWN_ANSWER_SOURCE)), "SOURCE_IDENTITY")
    refused(source_binding(TEMPORAL_BAD_SOURCE), "SOURCE_IDENTITY")
    too_big_input = b.BoundBytes(b"y" * (pd_mod.MAX_INPUT_BYTES + 1), hexid(98),
                                 pd_mod.MAX_INPUT_BYTES + 1)
    widened_input = replace(prepared, decisions=(
        replace(prepared.decisions[0], input_bytes=too_big_input),) + prepared.decisions[1:])
    refused(source_binding(), "INPUT", target=widened_input)
    # An input within its own ceiling can still overflow the total carrier ceiling.
    wide_input = b"y" * pd_mod.MAX_INPUT_BYTES
    wide_binding = b.BoundBytes(wide_input, hashlib.sha256(wide_input).hexdigest(), len(wide_input))
    with pytest.raises(pd_mod.PrefixDriverRefused, match="CARRIER"):
        pd_mod.build_carrier(source_binding().raw, wide_binding.raw)
    with pytest.raises(pd_mod.PrefixDriverRefused, match="CONFIG"):
        pd_mod.run_prefix_driver(prepared, source=source_binding(), engine=engine, spec=spec(),
                                 config_sha256=hexid(77))
    # A binding that claims the retained source identity but carries other bytes.
    tampered = KNOWN_ANSWER_SOURCE + b" "
    with pytest.raises(pd_mod.PrefixDriverRefused, match="SOURCE_DIGEST"):
        pd_mod.run_prefix_driver(prepared, source=b.BoundBytes(tampered, prepared.identity.source_sha256,
                                                              len(tampered)),
                                 engine=engine, spec=spec(), config_sha256=hexid(6))


@pytest.mark.parametrize("override", [
    {"wall_clock_seconds": tp.MAX_WALL_SECONDS + 1},
    {"wall_clock_seconds": 0.0},
    {"cpus": tp.MAX_CPUS + 1},
    {"memory_bytes": tp.MAX_MEMORY_BYTES + 1},
    {"output_cap_bytes": 0},
    {"image": "registry.example/repo:latest"},
    {"entrypoint": "/bin/sh"},
])
def test_deadline_and_resource_caps_refuse_before_io(case, override):
    prepared = prepare(case)
    engine = ScriptedFakeEngine()
    with pytest.raises(pd_mod.PrefixDriverRefused, match="TRANSPORT_PLAN_REFUSED"):
        pd_mod.run_prefix_driver(prepared, source=source_binding(), engine=engine,
                                 spec=spec(**override), config_sha256=hexid(6))
    assert engine.calls == [] and engine.creates == 0


def test_carrier_count_ceiling_is_reachable_and_exact():
    assert -(-pd_mod.MAX_CARRIER_BYTES * 4 // 3 // pd_mod.MAX_CHUNK_CHARS) == pd_mod.MAX_CHUNKS
    assert pd_mod.MAX_CHUNKS + 3 <= 64
    argv, header, carrier = pd_mod.build_carrier(b"a" * 64, b"b" * 64)
    assert argv[0] == "-c" and argv[1] == pd_mod.RUNNER_SOURCE
    assert len(argv) == 4 and all(len(item) <= 4096 for item in argv)
    value = json.loads(header)
    assert set(value) == set(pd_mod._HEADER_KEYS) and value["chunks"] == 1
    assert value["source_sha256"] == hashlib.sha256(b"a" * 64).hexdigest()
    assert value["input_sha256"] == hashlib.sha256(b"b" * 64).hexdigest()
    assert value["carrier_sha256"] == hashlib.sha256(carrier).hexdigest()


def test_attempt_budget_bound_stops_and_retains(case):
    prepared = prepare(case)
    engine = ScriptedFakeEngine()
    outcome = drive(prepared, engine, spec_override={"max_attempts": 2})
    assert not outcome.completed
    assert len(outcome.attempts) == 2 and engine.creates == 2
    assert outcome.refusal_reasons == ("ATTEMPT_BUDGET_EXHAUSTED",)
    assert outcome.outputs == ()


# ---------------------------------------------------------------------------
# Output adoption refusals
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("behaviour, label, uncertain", [
    ({"start_rc": 7}, "attach-failure", True),
    ({"exit_state": {"Running": False, "ExitCode": 7, "OOMKilled": False}}, "nonzero-exit", False),
    ({"exit_state": {"Running": False, "ExitCode": 0, "OOMKilled": True}}, "oom-killed", False),
])
def test_nonzero_or_unconfirmed_exit_is_not_adopted_and_stops(case, behaviour, label, uncertain):
    prepared = prepare(case)
    engine = ScriptedFakeEngine(behaviour=behaviour)
    outcome = drive(prepared, engine)
    assert not outcome.completed and len(outcome.attempts) == 1, label
    attempt = outcome.attempts[0]
    assert attempt.state == "cleaned_failure" and attempt.cleanup_confirmed is True, label
    assert attempt.workload_confirmed is False, label
    # A CLI failure is not a proved container exit; a settled exit state is.
    assert attempt.execution_uncertain is uncertain, label
    assert outcome.refusal_reasons == ("TRANSPORT_ATTEMPT_NOT_CONFIRMED",), label
    assert outcome.outputs == ()


@pytest.mark.parametrize("label", ["nonfinite", "duplicate", "foreign", "trailing"])
def test_malformed_output_rejected_and_attempt_retained(case, label):
    prepared = prepare(case)
    decision = prepared.decisions[0]
    identity = {"schema": "research_codegen.output.v1", "candidate_id": "rf-codegen-prefix-fixture",
                "fold_id": "invented", "entity_id": "XLB", "input_policy_sha256": hexid(2)}
    row = known_answer(decision.decision_id)
    payload = encoded({**identity, "rows": [row]})
    if label == "nonfinite":
        payload = payload.replace(b'"value":9', b'"value":NaN', 1)
        assert b"NaN" in payload
    elif label == "duplicate":
        payload = payload.replace(b'"rows"', b'"rows":1,"rows"', 1)
    elif label == "foreign":
        payload = encoded({**identity, "rows": [dict(decision_id="d9-XLY", status="available",
                                                     value=1, reason=None)]})
    else:
        payload = payload + b" trailing text"
    engine = ScriptedFakeEngine(behaviour={"workload": payload})
    outcome = drive(prepared, engine)
    assert not outcome.completed and len(outcome.attempts) == 1, label
    assert outcome.attempts[0].output_sha256 is not None, label
    assert outcome.outputs == (), label


def test_cleanup_uncertainty_stops_next_attempt_and_retains_receipt(case):
    prepared = prepare(case)
    engine = ScriptedFakeEngine(behaviour={"absence": "exists"})
    outcome = drive(prepared, engine)
    assert not outcome.completed
    assert len(outcome.attempts) == 1 and engine.creates == 1
    assert outcome.attempts[0].state == "cleanup_uncertain"
    assert outcome.attempts[0].reconciliation_required is True
    assert outcome.attempts[0].output_sha256 is not None
    assert outcome.outputs == ()


# ---------------------------------------------------------------------------
# Dormancy, import safety and runner source audit
# ---------------------------------------------------------------------------

def test_default_disabled_never_constructs_engine_or_runs_callable(monkeypatch):
    monkeypatch.setattr(tp, "collect_process",
                        lambda *arguments, **keywords: pytest.fail("unexpected local I/O"))

    class Sentinel:
        def run(self, *arguments, **keywords):
            raise AssertionError("engine must never be reached")

    with pytest.raises(pd_mod.PrefixDriverRefused, match="EXACT_PREPARED_INPUTS_REQUIRED"):
        pd_mod.run_prefix_driver(object(), source=source_binding(), engine=Sentinel(), spec=spec(),
                                 config_sha256=hexid(6))
    prepared = prepare(make_case())
    with pytest.raises(pd_mod.PrefixDriverRefused, match="TRANSPORT_ENGINE_REQUIRED"):
        pd_mod.run_prefix_driver(prepared, source=source_binding(), engine=None, spec=spec(),
                                 config_sha256=hexid(6))
    with pytest.raises(pd_mod.PrefixDriverRefused, match="TRANSPORT_ENGINE_REQUIRED"):
        pd_mod.run_prefix_driver(prepared, source=source_binding(), engine=lambda *a, **k: None,
                                 spec=spec(), config_sha256=hexid(6))
    with pytest.raises(pd_mod.PrefixDriverRefused, match="TRANSPORT_PLAN_REFUSED"):
        pd_mod.run_prefix_driver(prepared, source=source_binding(), engine=Sentinel(),
                                 spec=spec(wall_clock_seconds=tp.MAX_WALL_SECONDS + 1),
                                 config_sha256=hexid(6))


def test_runner_source_is_bounded_ascii_with_no_host_surface():
    text = pd_mod.RUNNER_SOURCE
    assert text.isascii() and 0 < len(text) <= 4096
    for forbidden in ("pandas", "subprocess", "socket", "urllib", "config", "label",
                      "sys.path", "os.environ", "open(", "input_envelope_path"):
        assert forbidden not in text, forbidden
    runner = ast.parse(text)
    execs = [node for node in ast.walk(runner) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "exec"]
    assert len(execs) == 1
    # The driver module itself never imports, compiles, evaluates or opens anything.
    for node in ast.walk(ast.parse(inspect.getsource(pd_mod))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in ("__import__", "eval", "exec", "compile", "open")


def test_operation_identity_is_stable_and_input_sensitive(case):
    prepared = prepare(case)
    task = prepared.decisions[0]
    argv, header, carrier = pd_mod.build_carrier(source_binding().raw, task.input_bytes.raw)
    first = pd_mod.decision_operation_id(prepared, task, carrier)
    assert first == pd_mod.decision_operation_id(prepared, task, carrier)
    assert first.startswith("prefix-") and 0 < len(first) <= 128
    other = replace(task, input_bytes=bound(b'{"different": true}'))
    other_carrier = pd_mod.build_carrier(source_binding().raw, other.input_bytes.raw)[2]
    assert pd_mod.decision_operation_id(prepared, other, other_carrier) != first


# Parent verified regressions: fixed helpers/fake engines only; no primitive execution.
"""Parent discriminators: reviewed fixed parsers and fake engine/clock only."""
import ast
from dataclasses import replace
import json
import pytest
from engine.research_codegen import bridge as b, prefix_driver as p


def fixed_parser():
    tree = ast.parse(p.RUNNER_SOURCE)
    names = {'_reject', 'pairs', 'bounded', 'parse_header'}
    nodes = [n for n in tree.body if isinstance(n, ast.Import) or
             isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='HEADER_KEYS' for t in n.targets) or
             isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes if isinstance(n, ast.FunctionDef)} == names
    # Excludes main, source compile/exec and every primitive-dispatch statement.
    for node in ast.walk(ast.Module(body=nodes, type_ignores=[])):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {'compile','exec','feature','main'}
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<reviewed-fixed-json-only>', 'exec'), namespace)
    return namespace['bounded']


def test_fixed_json_parser_valid_header_and_nested_object():
    parse = fixed_parser()
    value = {'schema': p.HEADER_SCHEMA, 'nested': {'a': 1}}
    assert parse(json.dumps(value)) == value


@pytest.mark.parametrize('text', ['{"schema":"a","schema":"b"}', '{"nested":{"a":1,"a":2}}'])
def test_fixed_json_parser_duplicate_refuses(text):
    with pytest.raises(SystemExit): fixed_parser()(text)


@pytest.mark.parametrize('text', ['{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}'])
def test_fixed_json_parser_nonfinite_refuses(text):
    with pytest.raises(ValueError): fixed_parser()(text)


def test_public_preparer_rejects_foreign_schedule_iterator_before_hook():
    case = make_case(); touched=[]
    class Foreign:
        def __iter__(self): touched.append(True); return iter(case[0].schedules)
    with pytest.raises(b.BridgeRefused):
        b.prepare_synthetic_inputs(replace(case[0], schedules=Foreign()), commission=case[1])
    assert touched == []


@pytest.mark.parametrize('change', [{'schema':'foreign'}, {'extra': 'field'}])
def test_public_preparer_enforces_closed_schedule_schema(change):
    run, commission = make_case()[:2]
    schedule = json.loads(run.schedules[0].raw); schedule.update(change)
    with pytest.raises(b.BridgeRefused):
        b.prepare_synthetic_inputs(replace(run,schedules=(bound(schedule),*run.schedules[1:])), commission=commission)


@pytest.mark.parametrize('budget', [float('inf'), float('nan'), 601.0])
def test_total_budget_finite_bounded_before_io(budget):
    engine=ScriptedFakeEngine()
    with pytest.raises(p.PrefixDriverRefused):
        drive(prepare(make_case()), engine, spec_override={'total_wall_seconds':budget})
    assert engine.creates == 0


def test_tiny_total_budget_does_not_launch_sixty_second_plan():
    engine=ScriptedFakeEngine()
    outcome=drive(prepare(make_case()), engine, spec_override={'total_wall_seconds':.1})
    assert engine.creates == 0 and not outcome.completed and outcome.outputs == ()
    assert 'WALL_BUDGET_EXHAUSTED' in outcome.refusal_reasons


def test_final_attempt_overrun_cannot_report_completed(monkeypatch):
    run, commission=make_case()[:2]
    # One qualified decision; full schedule/source exclusion still comes from shared bridge.
    positions=tuple(replace(q,eligible_nodes=('XLB',) if q.calendar_index==0 else ()) for q in run.positions)
    decision=next(d for d in run.decisions if d.calendar_index==0 and d.node=='XLB')
    schedule=json.loads(run.schedules[0].raw);schedule['decision_ids']=[json.loads(decision.request.raw)['decision_id']]
    narrow=replace(run,positions=positions,decisions=(decision,),schedules=(bound(schedule),))
    prepared=b.prepare_synthetic_inputs(narrow,commission=commission)
    clock=iter([0.0,0.0,601.0]);monkeypatch.setattr(p.time,'monotonic',lambda:next(clock))
    engine=ScriptedFakeEngine();outcome=drive(prepared,engine)
    assert engine.creates == 1 and len(outcome.attempts)==1
    assert not outcome.completed and outcome.outputs == ()
    assert 'WALL_BUDGET_EXHAUSTED' in outcome.refusal_reasons


def test_sufficient_fixed_envelope_succeeds_fake_only(monkeypatch):
    monkeypatch.setattr(p.time,'monotonic',lambda:0.0)
    engine=ScriptedFakeEngine();outcome=drive(prepare(make_case()),engine)
    assert outcome.completed and engine.creates==6 and not outcome.refusal_reasons


def test_join_refuses_same_envelope_with_altered_source_config(monkeypatch):
    case=make_case(); run,commission=case[:2]
    outcome=drive(prepare(case),ScriptedFakeEngine())
    manifest=json.loads(run.manifest.raw);manifest['source_sha256']=hexid(8);manifest['config_sha256']=hexid(9)
    other=replace(run,identity=replace(run.identity,source_sha256=hexid(8),config_sha256=hexid(9)),
                  manifest=bound(manifest),owner_references=bound(owner_receipts(manifest)))
    assert b.prepare_synthetic_inputs(other,commission=commission).identity.source_sha256==hexid(8)
    with pytest.raises(p.PrefixDriverRefused):
        p.connect_prepared_outputs(other,outcome,commission=commission)


def test_receipt_retains_original_immutable_plan_and_attempt():
    outcome=drive(prepare(make_case()),ScriptedFakeEngine())
    record=outcome.attempts[0]
    assert record.transport_attempt.workload_output
    assert record.transport_attempt.engine_events
    assert record.transport_attempt.plan_sha256==record.plan_sha256
    assert record.transport_plan.operation_id==record.operation_id
    from engine.research_codegen import transport
    assert transport.plan_identity(record.transport_plan)==record.plan_sha256


def test_total_envelope_includes_actual_control_and_reap_bounds():
    from engine.research_codegen import transport as t
    prepared=prepare(make_case());engine=ScriptedFakeEngine();outcome=drive(prepared,engine)
    plan=outcome.attempts[0].transport_plan
    assert p.worst_case_attempt_seconds(plan)==plan.wall_clock_seconds+430.0
    assert plan.wall_clock_seconds==60.0
    assert 0<len(p.RUNNER_SOURCE.encode('ascii'))<=4096


def test_reviewed_header_schema_before_any_dispatch():
    tree=ast.parse(p.RUNNER_SOURCE)
    names={'_reject','pairs','bounded','parse_header'}
    nodes=[n for n in tree.body if isinstance(n,ast.Import) or
           isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='HEADER_KEYS' for t in n.targets) or
           isinstance(n,ast.FunctionDef) and n.name in names]
    subset=ast.Module(body=nodes,type_ignores=[])
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                   and n.func.id in {'exec','compile','feature','main'} for n in ast.walk(subset))
    ns={};exec(compile(subset,'<reviewed-header-only>','exec'),ns)
    _,header,_=p.build_carrier(b'opaque-data-not-executed',b'{}')
    assert ns['parse_header'](header)['schema']==p.HEADER_SCHEMA
    wrong=json.loads(header);wrong['schema']='foreign'
    with pytest.raises(SystemExit):ns['parse_header'](json.dumps(wrong))
    wrong=json.loads(header);wrong['extra']=1
    with pytest.raises(SystemExit):ns['parse_header'](json.dumps(wrong))
    with pytest.raises(SystemExit):ns['parse_header']('[]')


def test_shared_decision_names_do_not_hide_duplicate_entity_schedule():
    run,commission=make_case()[:2]
    decisions=[]
    for decision in run.decisions:
        request=json.loads(decision.request.raw);request['decision_id']='d'+str(decision.calendar_index)
        decisions.append(replace(decision,request=bound(request)))
    schedules=[]
    for binding in run.schedules:
        schedule=json.loads(binding.raw)
        schedule['decision_ids']=[name.split('-')[0] for name in schedule['decision_ids']]
        schedules.append(bound(schedule))
    shared=replace(run,decisions=tuple(decisions),schedules=tuple(schedules))
    assert len(b.prepare_synthetic_inputs(shared,commission=commission).decisions)==6
    # XLB and XLE have identical decision-name lists; compare complete group keys.
    assert json.loads(schedules[0].raw)['decision_ids']==json.loads(schedules[1].raw)['decision_ids']
    substituted=replace(shared,schedules=(schedules[0],schedules[0],*schedules[2:]))
    with pytest.raises(b.BridgeRefused,match='DUPLICATE_OWNER_SCHEDULE'):
        b.prepare_synthetic_inputs(substituted,commission=commission)
