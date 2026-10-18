"""Invented connected fixtures, never candidate code or historical labels."""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json

import pandas as pd
import pytest

from engine.research_codegen import bridge as b, evaluation
from engine.trial_ledger import TrialLedger, _hash, _canon
from lib import store
from tests.test_research_codegen_contracts import valid_manifest, trusted_protocol, owner_receipts


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def bound(value):
    raw = value if type(value) is bytes else encoded(value)
    return b.BoundBytes(raw, hashlib.sha256(raw).hexdigest(), len(raw))


def make_case(tmp_path, monkeypatch):
    """Real capture and TrialLedger APIs, solely within this exclusive tmp root."""
    data = tmp_path / "data"
    (data / "yahoo").mkdir(parents=True)
    monkeypatch.setattr(store.config, "data_dir", lambda: data)
    manifest, protocol = valid_manifest(), trusted_protocol()
    # Existing bookkeeping, explicitly staged. Both good and refused configurations count.
    ledger_path = tmp_path / "trial.jsonl"
    ledger_path.touch(exist_ok=False)
    configs = [{"case": "known-answer"}, {"case": "controlled-refusal"}]
    ledger = TrialLedger(path=ledger_path, family=manifest["trial_family"])
    assert ledger.log_grid(configs, source="synthetic_engineering_fixture") == 2
    assert ledger.log_declared_budget(2, reason="Two invented configurations") is True
    before = ledger_path.read_bytes()
    assert ledger.log_grid(configs) == 0 and ledger_path.read_bytes() == before
    cold = TrialLedger(path=ledger_path, family=manifest["trial_family"])
    variants = [{"variant_id": "fixture-" + str(i), "source_sha256": manifest["source_sha256"] if i == 0 else "1" * 64,
                 "config_sha256": hashlib.sha256(_canon(c).encode()).hexdigest(),
                 "incumbent_config_hash": _hash(manifest["trial_family"], c)} for i, c in enumerate(configs)]
    manifest["config_sha256"] = variants[0]["config_sha256"]
    history = hashlib.sha256(b"").hexdigest()
    expected = dict(schema="research_codegen.expected_generation.v1", original_root_id=protocol["original_root_id"],
        family=manifest["trial_family"], protocol_sha256=manifest["protocol_sha256"], history_anchor_sha256=history,
        variants=variants, inherited_variants=[], trial_ceiling=4, vault_required=False, vault_request=None)
    trial = dict(schema="research_codegen.trial_readback_reference.v1", original_root_id=protocol["original_root_id"],
        family=manifest["trial_family"], protocol_sha256=manifest["protocol_sha256"], history_anchor_sha256=history,
        snapshot_sha256=hashlib.sha256(before).hexdigest(), snapshot_bytes=len(before), writer_receipt_sha256="2" * 64,
        durable_readback_receipt_sha256="3" * 64, history_state="complete", load_error=cold.load_error,
        corrupt_lines=cold.corrupt_lines, recorded_variants=variants, declared_floor=cold.declared_budget(),
        literal_n=cold.literal_n(), effective_n=cold.effective_n())
    dates = tuple(d.strftime("%Y-%m-%d") for d in pd.bdate_range("2008-01-01", "2010-07-01"))
    anchor = dates.index("2010-01-04")
    eligible = (evaluation.COHORT[:2], (), evaluation.COHORT[:4], ())
    positions = tuple(b.SchedulePosition(i, dates[anchor + 26 * i], eligible[i],
        tuple((n, "source_unavailable" if i == 1 and n == "XLY" else "qualified") for n in evaluation.COHORT)) for i in range(4))
    decisions, schedules, outputs = [], [], []
    for p in positions:
        for node in p.eligible_nodes:
            from zoneinfo import ZoneInfo
            cutoff = datetime.fromisoformat(dates[anchor + 26*p.calendar_index + 1] + "T09:00:00").replace(tzinfo=ZoneInfo("America/New_York"))
            req = dict(schema="research_codegen.request.v1", candidate_id=manifest["candidate_id"], fold_id="invented",
                entity_id=node, decision_id=f"d{p.calendar_index}-{node}", cutoff=cutoff.isoformat(),
                input_policy_sha256=manifest["input_policy_sha256"], allowed_source_ids=["fixture-yahoo"])
            trailing = dates[anchor + 26*p.calendar_index - 62:anchor + 26*p.calendar_index + 1]
            # Real helper retains a longer image; only the last63 verified sessions reach inputs.
            retained_dates = dates[anchor + 26*p.calendar_index - 70:anchor + 26*p.calendar_index + 1]
            frame = pd.DataFrame({"close": [10.0] * len(retained_dates)}, index=pd.to_datetime(retained_dates))
            now = datetime.fromisoformat(p.trigger_date + "T21:10:00+00:00")
            monkeypatch.setattr(store, "_availability_now", lambda now=now: now)
            captured = store.capture_yahoo_observation(node, frame, frame,
                lineage={"provider": "yahoo", "field": "Adj Close", "basis": "total_return", "ticker": node},
                adapter_return_known_by=datetime.fromisoformat(p.trigger_date + "T21:05:00+00:00"))
            root = data / "yahoo/.availability_capture"
            receipt_raw = (root / captured["receipt_ref"]).read_bytes()
            assert hashlib.sha256(receipt_raw).hexdigest() == captured["receipt_sha256"]
            image_raw = (root / captured["receipt"]["provider_return_image"]["object_ref"]).read_bytes()
            merged_raw = (root / captured["receipt"]["merged_capture_image"]["object_ref"]).read_bytes()
            capture = b.CaptureBinding(node, "fixture-yahoo", bound(receipt_raw), bound(image_raw), bound(merged_raw),
                p.trigger_date + "T21:11:00+00:00", tuple((day, day + "T21:00:00Z") for day in retained_dates))
            decision = b.DecisionBinding(p.calendar_index, node, bound(req), capture)
            assert len(b._capture_input(decision, req, trailing)["observations"]) == 63
            decisions.append(decision)
    for node in evaluation.COHORT[:4]:
        ids = [json.loads(d.request.raw)["decision_id"] for d in decisions if d.node == node]
        schedule = dict(schema="research_codegen.schedule.v1", candidate_id=manifest["candidate_id"], fold_id="invented",
                        entity_id=node, input_policy_sha256=manifest["input_policy_sha256"], decision_ids=ids)
        output = {k: v for k, v in schedule.items() if k != "decision_ids"}
        output.update(schema="research_codegen.output.v1", rows=[dict(decision_id=d, status="available",
                      value=9-evaluation.COHORT.index(node), reason=None) for d in ids])
        schedules.append(bound(schedule)); outputs.append(bound(output))
    # Hand-designed return paths: one negative day then flat, so native MAE is known.
    losses = {0: {"XLB": .1, "XLE": .3}, 2: {"XLB": .1, "XLE": .2, "XLF": .5, "XLI": .8}}
    paths = []
    for node in evaluation.COHORT:
        returns = [0.0] * len(dates)
        for i, table in losses.items():
            # _per_entry_rows starts accumulating AFTER the next-session entry close.
            returns[anchor + 26*i + 2] = -table.get(node, 0.0)
        paths.append(evaluation.SourcePath(node, dates, tuple(returns)))
    identity = b.ArtifactBinding(str(tmp_path / "diagnostic.json"), "0" * 64, 1,
        "fixture-diagnostic", protocol["original_root_id"], manifest["candidate_id"],
        *(manifest[k] for k in ("source_sha256", "config_sha256", "protocol_sha256", "input_policy_sha256", "runtime_sha256", "evaluator_sha256")))
    commission = b.SyntheticTestCommission(protocol["original_root_id"], str(tmp_path))
    run = b.SyntheticRun(identity, "2010-07-01T22:00:00Z", bound(manifest), bound(protocol), bound(owner_receipts()),
        bound(expected), bound(trial), positions, tuple(decisions), tuple(schedules), tuple(outputs), tuple(paths), dates)
    return run, commission


def persist(run, commission):
    raw = b.compute_synthetic_diagnostic(run, commission=commission)
    binding = replace(run.identity, artifact_sha256=hashlib.sha256(raw).hexdigest(), artifact_bytes=len(raw))
    from pathlib import Path
    Path(binding.artifact_path).write_bytes(raw)
    return binding, b.load_diagnostic_artifact(binding, commission=commission)


def test_actual_capture_accounting_native_evaluator_and_readback(tmp_path, monkeypatch):
    run, commission = make_case(tmp_path, monkeypatch)
    binding, read = persist(run, commission)
    agg = dict(read.aggregates)
    assert read.status == "DIAGNOSTIC_ONLY"
    assert [agg[k] for k in ("scheduled_formation_count", "source_excluded_formation_count", "source_qualified_formation_count",
        "no_opportunity_formation_count", "opportunity_formation_count", "paired_formation_count")] == [4, 1, 3, 1, 2, 2]
    assert agg["provided_baseline_entry_count"] == 6
    assert agg["provided_selected_entry_count"] == agg["provided_foregone_entry_count"] == 3
    assert agg["paired_mean_baseline_adverse_loss"] == pytest.approx(.3)
    assert agg["paired_mean_selected_adverse_loss"] == pytest.approx(.125)
    assert agg["paired_mean_improvement"] == pytest.approx(.175)
    assert agg["paired_mean_improvement"] != pytest.approx(.2)
    public = b.public_diagnostic(read)
    assert not any(public[k] for k in ("generation_enabled", "execution_enabled", "evaluation_enabled", "authority_granted"))
    assert public["scientific_acceptance"] == "UNQUALIFIED"
    assert public["procedure_state"] == "NO_QUALIFIED_PROCEDURE"
    assert all(token not in encoded(public).decode() for token in ("XLB", "MFE", "ret_exit", "baseline_entries", "decision_ids", "observations"))
    assert b.load_diagnostics((binding,), commission=commission) == (read,)


@pytest.mark.parametrize("damage", ["missing-output", "failed", "empty-input", "late-receipt", "reordered", "missing-accounting", "missing-owner"])
def test_whole_candidate_refused_without_pair_salvage(tmp_path, monkeypatch, damage):
    run, commission = make_case(tmp_path, monkeypatch)
    if damage == "missing-output":
        run = replace(run, outputs=run.outputs[:-1], schedules=run.schedules[:-1])
    elif damage in ("failed", "reordered"):
        out = json.loads(run.outputs[0].raw)
        if damage == "failed":
            out["rows"][1].update(status="failed", value=None, reason="synthetic failure")
        else:
            out["rows"].reverse()
        run = replace(run, outputs=(bound(out), *run.outputs[1:]))
    elif damage in ("empty-input", "late-receipt"):
        d = run.decisions[0]
        capture = replace(d.capture, receipt_read_completed_at="2010-01-05T22:01:00Z")
        run = replace(run, decisions=(replace(d, capture=capture), *run.decisions[1:]))
    elif damage == "missing-accounting":
        trial = json.loads(run.trial_readback.raw)
        trial["recorded_variants"] = trial["recorded_variants"][:1]
        run = replace(run, trial_readback=bound(trial))
    else:
        run = replace(run, owner_references=bound({}))
    _, read = persist(run, commission)
    agg = dict(read.aggregates)
    assert read.status == "REFUSED" and agg["refusal_count"] > 0
    assert agg["scheduled_formation_count"] == 4 and agg["source_excluded_formation_count"] == 1
    for key in ("paired_mean_improvement", "paired_mean_baseline_adverse_loss", "paired_mean_selected_adverse_loss",
                "paired_formation_count", "provided_selected_entry_count", "provided_baseline_entry_count", "provided_foregone_entry_count"):
        assert agg[key] is None


def test_default_disabled_and_hostile_object_do_not_read_or_invoke(tmp_path, monkeypatch):
    class Hostile:
        def __getattribute__(self, name):
            pytest.fail("hostile object invoked")
    with monkeypatch.context() as scoped:
        scoped.setattr(b.os, "open", lambda *a, **k: pytest.fail("unexpected I/O"))
        assert b.load_diagnostics() == ()
        with pytest.raises(b.BridgeRefused):
            b.load_diagnostics((Hostile(),))
        with pytest.raises(b.BridgeRefused):
            b.compute_synthetic_diagnostic(Hostile())


@pytest.mark.parametrize("damage", ["hash", "size", "identity", "duplicate-key", "pair-salvage", "effect", "authority", "extra-field", "bool-index", "entry-date"])
def test_persisted_artifact_tampering(tmp_path, monkeypatch, damage):
    run, commission = make_case(tmp_path, monkeypatch)
    binding, _ = persist(run, commission)
    from pathlib import Path
    raw = Path(binding.artifact_path).read_bytes()
    if damage == "hash":
        binding = replace(binding, artifact_sha256="9" * 64)
    elif damage == "size":
        binding = replace(binding, artifact_bytes=len(raw)+1)
    elif damage == "identity":
        binding = replace(binding, source_sha256="9" * 64)
    else:
        value = json.loads(raw)
        if damage == "pair-salvage":
            value["evaluation"]["status"] = "REFUSED"
            value["evaluation"]["refusal_reasons"] = ["failure"]
        elif damage == "effect":
            value["evaluation"]["pairs"][0]["difference"] = 99
        elif damage == "authority":
            value["flags"]["execution_enabled"] = True
        elif damage == "extra-field":
            value["p_value"] = .001
        elif damage == "bool-index":
            value["evaluation"]["pairs"][0]["calendar_index"] = False
        elif damage == "entry-date":
            value["evaluation"]["pairs"][0]["baseline_entries"][0]["exec_date"] = "not-a-date"
        raw = encoded(value)
        if damage == "duplicate-key":
            raw = raw.replace(b'"schema":', b'"schema":"forged","schema":', 1)
        binding = replace(binding, artifact_sha256=hashlib.sha256(raw).hexdigest(), artifact_bytes=len(raw))
    with pytest.raises(b.BridgeRefused):
        b.decode_bound_artifact(raw, expected=binding, commission=commission)


def test_no_opportunity_has_no_effect_sample(tmp_path, monkeypatch):
    run, commission = make_case(tmp_path, monkeypatch)
    run = replace(run, positions=tuple(replace(p, eligible_nodes=()) for p in run.positions), decisions=(), schedules=(), outputs=())
    _, read = persist(run, commission)
    assert read.status == "DIAGNOSTIC_ONLY"
    assert dict(read.aggregates)["paired_formation_count"] == 0
    assert dict(read.aggregates)["paired_mean_improvement"] is None


def test_full_schedule_cannot_compress_or_hide_exclusion(tmp_path, monkeypatch):
    run, commission = make_case(tmp_path, monkeypatch)
    with pytest.raises(b.BridgeRefused, match="FULL_SCHEDULE"):
        b.compute_synthetic_diagnostic(replace(run, positions=run.positions[1:]), commission=commission)
    p = replace(run.positions[1], trigger_date="2010-01-01")
    with pytest.raises(b.BridgeRefused, match="ANCHOR"):
        b.compute_synthetic_diagnostic(replace(run, positions=(run.positions[0], p, *run.positions[2:])), commission=commission)


def test_trailing_63_is_required_and_null_is_not_invented(tmp_path, monkeypatch):
    run, commission = make_case(tmp_path, monkeypatch)
    decision = run.decisions[0]
    image = json.loads(decision.capture.provider_image.raw)
    image["rows"][-1][1] = None
    changed_image = bound(image)
    receipt = json.loads(decision.capture.receipt.raw)
    receipt["provider_return_image"].update(sha256=changed_image.sha256, bytes=changed_image.size,
                                         object_ref="objects/" + changed_image.sha256 + ".json")
    capture = replace(decision.capture, provider_image=changed_image, receipt=bound(receipt))
    changed = replace(decision, capture=capture)
    trigger = run.session_dates.index(run.positions[0].trigger_date)
    envelope = b._capture_input(changed, json.loads(changed.request.raw), run.session_dates[trigger-62:trigger+1])
    assert len(envelope["observations"]) == 63 and envelope["observations"][-1]["value"] is None
    _, read = persist(replace(run, decisions=(changed, *run.decisions[1:])), commission)
    assert read.status == "REFUSED"
    image["rows"] = image["rows"][-1:]
    image["rows"][0][1] = 10.0
    changed_image = bound(image)
    receipt["provider_return_image"].update(sha256=changed_image.sha256, bytes=changed_image.size,
                                         object_ref="objects/" + changed_image.sha256 + ".json")
    changed = replace(decision, capture=replace(capture, provider_image=changed_image, receipt=bound(receipt)))
    _, read = persist(replace(run, decisions=(changed, *run.decisions[1:])), commission)
    assert read.status == "REFUSED"


def test_nested_foreign_hooks_are_rejected_before_use(tmp_path, monkeypatch):
    run, commission = make_case(tmp_path, monkeypatch)
    _, read = persist(run, commission)
    class IterBomb:
        def __iter__(self):
            pytest.fail("foreign iteration")
    class EqBomb:
        def __eq__(self, other):
            pytest.fail("foreign equality")
    with pytest.raises(b.BridgeRefused):
        b.public_diagnostic(replace(read, aggregates=(IterBomb(),)))
    with pytest.raises(b.BridgeRefused):
        b.compute_synthetic_diagnostic(run, commission=replace(commission, original_root_id=EqBomb()))


def test_prepare_synthetic_inputs_is_a_pure_narrow_seam(tmp_path, monkeypatch):
    """The public preparer reuses the accepted checks exactly and carries no label."""
    run, commission = make_case(tmp_path, monkeypatch)
    before = b.compute_synthetic_diagnostic(run, commission=commission)
    prepared = b.prepare_synthetic_inputs(run, commission=commission)
    assert b.compute_synthetic_diagnostic(run, commission=commission) == before
    assert [len(task.trailing_session_dates) for task in prepared.decisions] == [63] * 6
    assert all(task.complete_trailing for task in prepared.decisions)
    assert [list(group.decision_ids) for group in prepared.schedules] == [
        json.loads(item.raw)["decision_ids"] for item in run.schedules]
    # Narrow: no SourcePath, retained output, capture image or staging path is carried.
    for name in ("paths", "outputs", "positions", "manifest", "trial_readback"):
        assert not hasattr(prepared, name), name
    assert not hasattr(prepared.identity, "artifact_path")
    assert not any(hasattr(task, "capture") for task in prepared.decisions)
    # Exact: every task reproduces the accepted per-decision causal input bytes.
    for task, decision in zip(prepared.decisions, run.decisions):
        request = json.loads(decision.request.raw)
        trigger = run.session_dates.index(run.positions[decision.calendar_index].trigger_date)
        trailing = run.session_dates[max(0, trigger - 62):trigger + 1]
        assert task.input_bytes.raw == encoded(b._capture_input(decision, request, trailing))
        assert task.cutoff == request["cutoff"]
        assert task.request is decision.request
    # Structural admission still refuses; it is never authority.
    with pytest.raises(b.BridgeRefused, match="PREREQUISITES_INVALID"):
        b.prepare_synthetic_inputs(replace(run, owner_references=bound({})), commission=commission)
