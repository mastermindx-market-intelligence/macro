"""Synthetic consumer acceptance: complete claims failures never become empty success.

These tests exercise the real consumer functions through the inactive helper's
task-local fixture binding. No production selector, host data or publisher is used.
"""

from contextlib import contextmanager
from datetime import date
from hashlib import sha256
import importlib
import json
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

from engine import operator_grading as operator
from engine import qledger as q
from engine import qledger_falsifier as falsifier
from engine import qledger_store as store
from engine import qledger_store_protocol as protocol
from engine import qledger_store_sources as sources
from engine.metabolism import til_fitness as til
from engine.neuralweb import evidence_clock
from scripts import audit_claim_accountability as accountability
from scripts import audit_grading_closure as closure
from scripts import backfill_qledger_us as us_backfill
from scripts import build_intelligence_registry as registry
from scripts import check_qledger_metric_validity as metric
from scripts import grade_qledger as grader


query_module = importlib.import_module("engine.neuralweb.query")
TODAY = date(2026, 10, 9)
CLAIMS_REL = Path("data/qledger/claims.jsonl")
TAIL = b'{"claim_id":"tail","desk":"synthetic","status":"closed"}\n'
PREFIX = b'{"claim_id":"prefix","desk":"synthetic","status":"closed"}\n'


@pytest.fixture
def limits():
    return protocol.ProtocolLimits(
        base_bytes=16384, part_bytes=1024, page_bytes=8192, root_bytes=4096,
        descriptor_bytes=1024, leaf_entries=2, fanout=2, index_levels=3,
        history_operations=16, reference_visits=1024, snapshot_members=128,
        snapshot_bytes=262144, logical_bytes=32768, input_rows=128,
        publication_objects=256, git_blob_bytes=16384,
    )


class FixtureBinding:
    """Mutable fixture provider; every returned snapshot is separately verified."""

    def __init__(self, root, limits, raw=PREFIX, *, tail=TAIL):
        self.claims_path = root / CLAIMS_REL
        self.limits = limits
        self.reads = 0
        self.last_error = None
        ref = protocol.MemberRef(protocol.BASE_PATH, sha256(raw).hexdigest(), len(raw))
        record = protocol.RootRecord(
            ref, None, 0, len(raw), sha256(raw).hexdigest(), limits.fingerprint,
        )
        self.members = {
            protocol.BASE_PATH: raw,
            protocol.ROOT_PATH: protocol.encode_root(record, limits=limits),
        }
        snapshot = protocol.verify_snapshot(
            protocol.InMemorySource(self.members, snapshot_id="consumer-fixture:base"),
            record, limits=limits,
        )
        if tail is not None:
            plan = protocol.plan_append(
                snapshot, transaction_id="consumer-fixture:append",
                serialized_rows=[tail], limits=limits,
            )
            self.members.update(plan.members)
            self.members[protocol.ROOT_PATH] = plan.root_bytes
            snapshot = plan.snapshot
        self.record = snapshot.root

    def read_snapshot(self):
        self.reads += 1
        try:
            return protocol.verify_snapshot(
                protocol.InMemorySource(
                    self.members, snapshot_id=f"consumer-fixture:read-{self.reads}",
                ),
                self.record, limits=self.limits,
            )
        except protocol.SnapshotIntegrityError as exc:
            self.last_error = exc
            raise

    def install(self, other):
        self.members = dict(other.members)
        self.record = other.record

    def damage_tail(self, kind):
        name = sorted(p for p in self.members if p.startswith("data/qledger/claims.parts/"))[-1]
        original = self.members[name]
        if kind == "missing":
            del self.members[name]
        elif kind == "corrupt":
            self.members[name] = b"!" + original[1:]
        else:
            raise AssertionError(kind)
        return name, original


@contextmanager
def bound(binding):
    with store._synthetic_claims_binding(binding.claims_path, binding):
        yield binding


def put(root, relative, payload):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def write_spy(monkeypatch, root):
    """Observe real Path file writes in only the explicitly supplied temp root."""
    events = []
    original_open = Path.open
    original_text = Path.write_text
    original_bytes = Path.write_bytes

    def opened(path, mode="r", *args, **kwargs):
        if path.is_relative_to(root) and any(char in mode for char in "wa+"):
            events.append((str(path.relative_to(root)), mode))
        return original_open(path, mode, *args, **kwargs)

    def written_text(path, text, *args, **kwargs):
        if path.is_relative_to(root):
            events.append((str(path.relative_to(root)), "write_text"))
        return original_text(path, text, *args, **kwargs)

    def written_bytes(path, data, *args, **kwargs):
        if path.is_relative_to(root):
            events.append((str(path.relative_to(root)), "write_bytes"))
        return original_bytes(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "open", opened)
    monkeypatch.setattr(Path, "write_text", written_text)
    monkeypatch.setattr(Path, "write_bytes", written_bytes)
    return events


def deny_claims_stat(monkeypatch, claims_path):
    for name in ("exists", "is_file"):
        original = getattr(Path, name)

        def checked(path, *args, _original=original, **kwargs):
            if path == claims_path:
                pytest.fail("native claims were qualified by a physical legacy-file check")
            return _original(path, *args, **kwargs)

        monkeypatch.setattr(Path, name, checked)


def closure_spec():
    return next(dict(spec) for spec in closure.INVENTORY if spec["key"] == "qledger_claims")


def output_markers(root):
    relatives = (
        "data/qledger/grades.jsonl", "data/qledger/run_status.json",
        "data/qledger/falsifier_evaluations.jsonl", "site/qledger/track_record.json",
    )
    return {put(root, rel, b'{"previous_output":true}\n'): b'{"previous_output":true}\n'
            for rel in relatives}


@pytest.mark.parametrize("kind", ["missing", "corrupt"])
@pytest.mark.parametrize("physical_anchor", [False, True])
@pytest.mark.parametrize("caller", ["operator", "accountability", "falsifier", "placebo"])
def test_integrity_propagates_before_claim_derived_work(
    tmp_path, limits, monkeypatch, kind, physical_anchor, caller,
):
    binding = FixtureBinding(tmp_path, limits)
    binding.damage_tail(kind)
    if physical_anchor:
        put(tmp_path, CLAIMS_REL, PREFIX)
    markers = output_markers(tmp_path)
    writes = write_spy(monkeypatch, tmp_path)
    work = []
    if caller == "operator":
        # The existing FDR-registration prelude is not a claims-derived result.
        monkeypatch.setattr(operator, "_register_fdr_budget", Mock(return_value=False))
        work = [Mock(), Mock()]
        monkeypatch.setattr(operator, "_compute_contrasts", work[0])
        monkeypatch.setattr(operator, "_load_grades", work[1])
        call = lambda: operator.grade(tmp_path)
    elif caller == "accountability":
        work = [Mock(), Mock()]
        monkeypatch.setattr(accountability, "_write_json", work[0])
        monkeypatch.setattr(accountability, "_write_md", work[1])
        call = lambda: accountability.run(tmp_path, write=True)
    elif caller == "falsifier":
        work = [Mock(), Mock()]
        monkeypatch.setattr(falsifier, "evaluate_check", work[0])
        monkeypatch.setattr(falsifier, "_load_evaluated_ids", work[1])
        call = lambda: falsifier.evaluate_falsifiers(tmp_path, today=TODAY.isoformat())
    else:
        monkeypatch.setattr(us_backfill, "_load_jsonl", Mock(return_value=[{
            "id": "synthetic-thesis", "ticker": "SYNTH", "state_asof": "2026-10-01",
            "claim_family": "altdata_flow",
        }]))
        monkeypatch.setattr(us_backfill, "_load_placebo_universe", Mock(return_value=["CONTROL"]))
        work = [Mock(), Mock(), Mock()]
        monkeypatch.setattr(us_backfill, "register_batch", work[0])
        monkeypatch.setattr(us_backfill, "make_claim", work[1])
        monkeypatch.setattr(us_backfill, "_placebo_tickers", work[2])
        call = lambda: us_backfill.backfill_altdata(tmp_path, dry_run=False)
    deny_claims_stat(monkeypatch, binding.claims_path)
    with bound(binding), pytest.raises(protocol.SnapshotIntegrityError) as caught:
        call()
    assert caught.value is binding.last_error
    assert binding.reads == 1
    assert not writes
    assert all(not spy.called for spy in work)
    assert all(path.read_bytes() == payload for path, payload in markers.items())


@pytest.mark.parametrize("kind", ["missing", "corrupt"])
@pytest.mark.parametrize("sidecar_present", [False, True])
@pytest.mark.parametrize("caller", ["query", "evidence_clock", "til", "registry"])
def test_display_consumers_preserve_unavailable_instead_of_empty_success(
    tmp_path, limits, monkeypatch, kind, sidecar_present, caller,
):
    binding = FixtureBinding(tmp_path, limits)
    binding.damage_tail(kind)
    if sidecar_present:
        put(tmp_path, "data/qledger/grades.jsonl", b"")
        put(tmp_path, "data/qledger/falsifier_evaluations.jsonl", b"")
    fallback = Mock(side_effect=AssertionError("native read invoked generic tracked fallback"))
    monkeypatch.setattr(registry, "read_tracked", fallback)
    deny_claims_stat(monkeypatch, binding.claims_path)
    with bound(binding):
        if caller == "query":
            rows, gaps = query_module.adapt_qledger(tmp_path)
            assert rows.empty
            assert len(gaps) == 1 and "read failed" in gaps[0]
            diagnostic = gaps[0]
        elif caller == "evidence_clock":
            rows, gaps = evidence_clock._adapt_qledger(tmp_path, {}, TODAY)
            assert rows == []  # No new falsifier-floor row from unavailable history.
            assert len(gaps) == 1 and "could not load" in gaps[0]
            diagnostic = gaps[0]
        elif caller == "til":
            row = til._read_live_leg_quality(tmp_path)
            assert row["value"] is None
            assert row["n"] == 0 and row["maturity"] == "accruing"
            assert row["note"].startswith("read error:")
            diagnostic = row["note"]
        else:
            result = registry._load_qledger(tmp_path)
            assert result.rows is None and result.horizons is None
            assert result.considered == result.unparseable == 0
            assert result.source_label.startswith("qledger-native-unreadable:")
            diagnostic = result.source_label
    assert str(binding.last_error) in diagnostic
    assert binding.reads == 1
    fallback.assert_not_called()


@pytest.mark.parametrize("kind", ["missing", "corrupt"])
@pytest.mark.parametrize("grades_present", [False, True])
@pytest.mark.parametrize("json_mode", [False, True])
def test_metric_integrity_error_is_neither_absent_nor_clean(
    tmp_path, limits, monkeypatch, capsys, kind, grades_present, json_mode,
):
    binding = FixtureBinding(tmp_path, limits)
    binding.damage_tail(kind)
    if grades_present:
        put(tmp_path, "data/qledger/grades.jsonl", b"")
    audit = Mock(return_value=[])
    emit = Mock()
    monkeypatch.setattr(metric, "audit", audit)
    monkeypatch.setattr(metric, "_emit", emit)
    monkeypatch.setattr(sys, "argv", ["metric", "--root", str(tmp_path)] + (["--json"] if json_mode else []))
    deny_claims_stat(monkeypatch, binding.claims_path)
    with bound(binding):
        assert metric.main() == 2  # A failure also fails without --strict.
    out = capsys.readouterr().out
    if json_mode:
        payload = json.loads(out)
        assert payload["store_absent"] is False
        assert payload["claims"] is payload["grades"] is payload["findings"] is None
        assert payload["storage_error_code"] == binding.last_error.code
        assert payload["storage_error"] == str(binding.last_error)
    else:
        assert "storage integrity failure, not audited" in out
        assert str(binding.last_error) in out
    audit.assert_not_called()
    emit.assert_not_called()
    assert binding.reads == 1


@pytest.mark.parametrize("kind", ["missing", "corrupt"])
def test_closure_audit_emits_explicit_error_not_zero_or_closed(
    tmp_path, limits, monkeypatch, kind,
):
    binding = FixtureBinding(tmp_path, limits)
    binding.damage_tail(kind)
    put(tmp_path, "data/qledger/grades.jsonl", b'{"claim_id":"prefix","graded_at":"2026-10-01"}\n')
    monkeypatch.setattr(closure, "INVENTORY", [closure_spec()])
    json_write, markdown_write = Mock(), Mock()
    monkeypatch.setattr(closure, "_write_json", json_write)
    monkeypatch.setattr(closure, "_write_md", markdown_write)
    deny_claims_stat(monkeypatch, binding.claims_path)
    with bound(binding):
        report = closure.run(tmp_path, write=True)
    row = report["ledgers"][0]
    assert row["verdict"] == "STORAGE-ERROR"
    assert row["storage"] == "integrity-error"
    assert row["n_logged"] is row["n_graded"] is row["last_graded_at"] is None
    assert row["logical_snapshot_complete"] is False
    assert row["physical_local_inventory"] == "not-inspected"
    assert row["storage_error_code"] == binding.last_error.code
    assert report["n_closed"] == report["n_grader_starved"] == report["n_log_only"] == 0
    json_write.assert_called_once_with(report, tmp_path)
    markdown_write.assert_called_once_with(report, tmp_path)


def test_closure_success_reports_verified_logical_counts_without_local_file_claim(
    tmp_path, limits, monkeypatch,
):
    binding = FixtureBinding(tmp_path, limits)
    assert not binding.claims_path.exists()
    deny_claims_stat(monkeypatch, binding.claims_path)
    with bound(binding):
        row = closure.audit_entry(closure_spec(), tmp_path)
    assert row["storage"] == "verified-native-snapshot"
    assert row["n_logged"] == 2 and row["n_graded"] == 0
    assert row["logical_snapshot_complete"] is True
    assert row["physical_local_inventory"] == "not-inspected"


def test_metric_malformed_rows_and_missing_grades_are_distinct_from_storage_error(
    tmp_path, limits, monkeypatch, capsys,
):
    raw = b'# schema\n{"claim_id":"kept","desk":"synthetic"}\nmalformed\n'
    binding = FixtureBinding(tmp_path, limits, raw, tail=None)
    audit = Mock(return_value=[])
    monkeypatch.setattr(metric, "audit", audit)
    monkeypatch.setattr(sys, "argv", ["metric", "--root", str(tmp_path), "--json"])
    with bound(binding):
        assert metric.main() == 0
        absent = json.loads(capsys.readouterr().out)
        assert absent["store_absent"] is True
        assert absent["missing"] == [str(tmp_path / "data/qledger/grades.jsonl")]
        assert absent["findings"] is None and "storage_error" not in absent
        audit.assert_not_called()
        put(tmp_path, "data/qledger/grades.jsonl", b"")
        assert metric.main() == 0
        audited = json.loads(capsys.readouterr().out)
    assert audited["store_absent"] is False
    assert audited["claims"] == 1 and audited["findings"] == []
    assert "storage_error" not in audited
    audit.assert_called_once_with([{"claim_id": "kept", "desk": "synthetic"}], [])


@pytest.mark.parametrize("kind", ["missing", "corrupt"])
@pytest.mark.parametrize("entry", ["run", "collect", "backfill", "readiness"])
def test_grader_source_failure_stops_before_fresh_outputs(
    tmp_path, limits, monkeypatch, kind, entry,
):
    binding = FixtureBinding(tmp_path, limits)
    binding.damage_tail(kind)
    markers = output_markers(tmp_path)
    writes = write_spy(monkeypatch, tmp_path)
    track, ladder, grade_claim = Mock(), Mock(), Mock()
    monkeypatch.setattr(q, "emit_track_record", track)
    monkeypatch.setattr(q, "emit_ladder_states", ladder)
    monkeypatch.setattr(q, "grade_claim", grade_claim)
    alerts = [Mock(), Mock(), Mock(), Mock()]
    for name, spy in zip(("_fire_readiness_alert", "_fire_grader_quiet_alert",
                          "_save_fired", "_update_grader_quiet_log"), alerts):
        monkeypatch.setattr(grader, name, spy)
    families = Mock(return_value=[])
    monkeypatch.setattr(grader, "_load_qual_ladder_families", families)
    backfill = Mock(return_value={"n_claims": 0, "n_backfilled": 0, "n_unstamped": 0})
    if entry == "backfill":
        backfill = Mock(side_effect=lambda root: q.load_claims(root))
    monkeypatch.setattr(q, "backfill_regime_stamps", backfill)
    if entry == "collect":
        call = lambda: grader.run_as_collect_step(tmp_path)
    elif entry == "readiness":
        call = lambda: grader.run_readiness_post_step(tmp_path, 0, 1, today=TODAY)
    else:
        call = lambda: grader.run(tmp_path, today=TODAY)
    with bound(binding), pytest.raises(protocol.SnapshotIntegrityError) as caught:
        call()
    assert caught.value is binding.last_error
    assert binding.reads == 1
    assert not writes
    assert not track.called and not ladder.called and not grade_claim.called
    assert not families.called and all(not spy.called for spy in alerts)
    assert backfill.call_count == (0 if entry == "readiness" else 1)
    assert all(path.read_bytes() == payload for path, payload in markers.items())


def test_combined_grader_captures_after_backfill_and_reuses_snapshot_through_outputs(
    tmp_path, limits, monkeypatch,
):
    before = FixtureBinding(tmp_path, limits, PREFIX, tail=None)
    after = FixtureBinding(tmp_path, limits, PREFIX + TAIL, tail=None)
    changed = FixtureBinding(tmp_path, limits)
    changed.damage_tail("missing")
    other_root = tmp_path / "other-root"
    other = FixtureBinding(other_root, limits, b'{"claim_id":"other","status":"closed"}\n', tail=None)
    put(tmp_path, "site/qledger/track_record.json", b"{}")
    put(tmp_path, "data/qledger/grades.jsonl", b"")
    observed = []

    def ids(root):
        return [c["claim_id"] for c in q.load_claims(root)]

    def backfill(root):
        assert before.reads == 0
        before.install(after)
        observed.append(("backfill", None))
        return {"n_claims": 2, "n_backfilled": 1, "n_unstamped": 0}

    def track(root):
        observed.append(("track", ids(root)))
        before.install(changed)  # The provider changes after the run's capture.

    def ladder(root, **kwargs):
        with store.ClaimsReadScope(root):
            observed.append(("ladder", ids(root)))
        with store.ClaimsReadScope(other_root):
            observed.append(("other", ids(other_root)))
        observed.append(("ladder-again", ids(root)))

    def readiness(root, families, today=None):
        snapshot_ids = ids(root)
        observed.append(("readiness", snapshot_ids))
        return {"_snapshot_claim_ids": snapshot_ids}

    monkeypatch.setattr(q, "backfill_regime_stamps", backfill)
    monkeypatch.setattr(q, "emit_track_record", track)
    monkeypatch.setattr(q, "emit_ladder_states", ladder)
    monkeypatch.setattr(q, "count_unresolvable_clock_claims", lambda **kwargs: {"n": 0})
    monkeypatch.setattr(grader, "_load_qual_ladder_families", lambda root: [])
    monkeypatch.setattr(grader, "compute_promotion_readiness", readiness)
    monkeypatch.setattr(grader, "_load_fired", lambda root: {})
    monkeypatch.setattr(grader, "_update_grader_quiet_log", lambda *args: 0)
    alerts = Mock()
    monkeypatch.setattr(grader, "_fire_readiness_alert", alerts)
    monkeypatch.setattr(grader, "_fire_grader_quiet_alert", alerts)
    writes = write_spy(monkeypatch, tmp_path)
    with bound(before), bound(other):
        result = grader.run(tmp_path, today=TODAY)
        assert before.reads == 1 and other.reads == 1
        # The completed scope must not hide a newly corrupt source on the next read.
        with pytest.raises(protocol.SnapshotIntegrityError):
            q.load_claims(tmp_path)
    assert observed == [
        ("backfill", None), ("track", ["prefix", "tail"]),
        ("ladder", ["prefix", "tail"]), ("other", ["other"]),
        ("ladder-again", ["prefix", "tail"]), ("readiness", ["prefix", "tail"]),
    ]
    assert before.reads == 2
    assert result["regime_stamp_backfill"]["n_backfilled"] == 1
    assert result["n_open"] == 0 and "error" not in result["w6_readiness"]
    written = json.loads((tmp_path / "site/qledger/track_record.json").read_text())
    assert written["promotion_readiness"]["_snapshot_claim_ids"] == ["prefix", "tail"]
    status = json.loads((tmp_path / "data/qledger/run_status.json").read_text())
    assert status == result
    assert writes  # Positive control: the writer spies observe this successful run.
    alerts.assert_not_called()


@pytest.mark.parametrize("boundary", ["ladder", "readiness-wrapper", "readiness-compute", "collect"])
def test_integrity_is_not_swallowed_by_remaining_grader_catch_boundaries(
    tmp_path, limits, monkeypatch, boundary,
):
    binding = FixtureBinding(tmp_path, limits, b"", tail=None)
    error = protocol.SnapshotIntegrityError("SOURCE", "synthetic downstream integrity failure")
    monkeypatch.setattr(q, "backfill_regime_stamps", lambda root: {})
    monkeypatch.setattr(q, "emit_track_record", Mock())
    monkeypatch.setattr(q, "emit_ladder_states", Mock())
    monkeypatch.setattr(grader, "_load_qual_ladder_families", lambda root: [])
    if boundary == "ladder":
        monkeypatch.setattr(q, "emit_ladder_states", Mock(side_effect=error))
    elif boundary == "readiness-wrapper":
        monkeypatch.setattr(grader, "run_readiness_post_step", Mock(side_effect=error))
    elif boundary == "readiness-compute":
        monkeypatch.setattr(grader, "compute_promotion_readiness", Mock(side_effect=error))
    else:
        monkeypatch.setattr(grader, "run", Mock(side_effect=error))
    writes = write_spy(monkeypatch, tmp_path)
    with bound(binding), pytest.raises(protocol.SnapshotIntegrityError) as caught:
        if boundary == "collect":
            grader.run_as_collect_step(tmp_path)
        elif boundary == "readiness-compute":
            grader.run_readiness_post_step(tmp_path, 0, 0, today=TODAY)
        else:
            grader.run(tmp_path, today=TODAY)
    assert caught.value is error
    assert not writes


@pytest.mark.parametrize("boundary", ["backfill", "ladder", "readiness-wrapper", "readiness-compute", "collect"])
def test_ordinary_grader_failure_policy_stays_nonfatal(tmp_path, monkeypatch, boundary):
    error = RuntimeError("ordinary synthetic failure")
    if boundary == "readiness-compute":
        monkeypatch.setattr(grader, "_load_qual_ladder_families", lambda root: [])
        monkeypatch.setattr(grader, "compute_promotion_readiness", Mock(side_effect=error))
        assert grader.run_readiness_post_step(tmp_path, 0, 0, today=TODAY) == {"error": str(error)}
        return
    if boundary == "collect":
        monkeypatch.setattr(grader, "run", Mock(side_effect=error))
        assert grader.run_as_collect_step(tmp_path) is None
        return
    monkeypatch.setattr(q, "backfill_regime_stamps", lambda root: {})
    monkeypatch.setattr(q, "emit_track_record", Mock())
    monkeypatch.setattr(q, "emit_ladder_states", Mock())
    monkeypatch.setattr(q, "count_unresolvable_clock_claims", lambda **kwargs: {"n": 0})
    monkeypatch.setattr(grader, "run_readiness_post_step", Mock(return_value={}))
    if boundary == "backfill":
        monkeypatch.setattr(q, "backfill_regime_stamps", Mock(side_effect=error))
    elif boundary == "ladder":
        monkeypatch.setattr(q, "emit_ladder_states", Mock(side_effect=error))
    elif boundary == "readiness-wrapper":
        monkeypatch.setattr(grader, "run_readiness_post_step", Mock(side_effect=error))
    result = grader.run(tmp_path, today=TODAY)
    assert result["n_open"] == 0 and result["n_graded_today"] == 0
    if boundary == "readiness-wrapper":
        assert result["w6_readiness"] == {"error": str(error)}
    assert json.loads((tmp_path / "data/qledger/run_status.json").read_text()) == result


POLICY_ROW = {
    "claim_id": "valid", "desk": "synthetic", "status": "open", "horizon_d": 5,
    "falsifier": "synthetic check", "check_by": "2026-10-01",
    "is_placebo": True, "placebo_real_source_id": "synthetic-thesis",
}
POLICY_LINE = json.dumps(POLICY_ROW, ensure_ascii=False).encode() + b"\n"
POLICY_BYTES = [
    POLICY_LINE * 2,
    POLICY_LINE + b"# schema\nmalformed\nnull\n[]\n17\n" + POLICY_LINE,
    (json.dumps(dict(POLICY_ROW, note="one\u2028two\u2029three"), ensure_ascii=False) + "\r\n").encode(),
    b"\xff\n" + POLICY_LINE,
    b"",
]


def read_policy(name, root):
    claims = root / CLAIMS_REL
    if name == "falsifier":
        return falsifier._read_jsonl(claims)
    if name == "operator":
        return operator._load_jsonl(claims, qledger_claims=True)
    if name == "accountability":
        return accountability._read_jsonl(claims, qledger_claims=True)
    if name == "closure":
        return closure._read_jsonl(claims, qledger_claims=True)
    if name == "metric":
        return metric._read_jsonl(claims, qledger_claims=True)
    if name == "placebo":
        return us_backfill._thesis_ids_with_placebos(root)
    if name == "registry":
        result = registry._load_qledger(root)
        return result.rows, result.horizons, result.unparseable, result.considered
    if name == "til":
        return til._read_live_leg_quality(root)
    if name == "query":
        frame, gaps = query_module.adapt_qledger(root)
        return frame["signal_id"].tolist(), gaps
    rows, gaps = evidence_clock._adapt_qledger(root, {}, TODAY)
    return [(r["clock_id"], r["state"], r["readiness"]) for r in rows], gaps


def outcome(call):
    try:
        return "returned", call()
    except Exception as exc:
        return "raised", type(exc), str(exc)


@pytest.mark.parametrize("name", [
    "falsifier", "operator", "accountability", "closure", "metric", "placebo",
    "registry", "til", "query", "evidence_clock",
])
@pytest.mark.parametrize("raw", POLICY_BYTES, ids=["duplicates", "malformed-and-shapes", "unicode-splitlines", "decode-error", "empty"])
def test_existing_parser_and_encoding_policies_match_for_identical_complete_bytes(
    tmp_path, limits, monkeypatch, name, raw,
):
    put(tmp_path, CLAIMS_REL, raw)
    put(tmp_path, "data/qledger/grades.jsonl", b"")
    put(tmp_path, "data/qledger/falsifier_evaluations.jsonl", b'{"claim_id":"valid","outcome":"CONFIRMED"}\n')
    # Preserve the tracked reader's exact legacy text contract without Git fallback.
    def tracked(root, relative):
        return (root / relative).read_text(encoding="utf-8"), "fixture-legacy"
    monkeypatch.setattr(registry, "read_tracked", tracked)
    legacy = outcome(lambda: read_policy(name, tmp_path))
    binding = FixtureBinding(tmp_path, limits, raw, tail=None)
    with bound(binding):
        native = outcome(lambda: read_policy(name, tmp_path))
    assert native == legacy
    if raw in (POLICY_LINE * 2, b""):
        assert legacy[0] == "returned"
    assert binding.reads == 1


@pytest.mark.parametrize("loader", [operator._load_jsonl, accountability._read_jsonl, closure._read_jsonl])
def test_generic_non_claims_reader_keeps_its_existing_broad_failure_policy(
    tmp_path, monkeypatch, loader,
):
    grades = put(tmp_path, "data/qledger/grades.jsonl", b"{}\n")
    original = Path.read_text
    def failed(path, *args, **kwargs):
        if path == grades:
            raise protocol.SnapshotIntegrityError("SOURCE", "synthetic generic-read control")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", failed)
    assert loader(grades) == []


def test_legacy_missing_and_registry_null_contracts_are_unchanged(tmp_path, monkeypatch, capsys):
    assert operator._load_claims(tmp_path) == {}
    assert us_backfill._thesis_ids_with_placebos(tmp_path) == set()
    row = closure.audit_entry(closure_spec(), tmp_path)
    assert row["storage"] == "absent-locally"
    assert row["n_logged"] == row["n_graded"] == 0
    assert "logical_snapshot_complete" not in row
    marker = "fixture:legacy-unreadable"
    callback = Mock(return_value=(None, marker))
    monkeypatch.setattr(registry, "read_tracked", callback)
    result = registry._load_qledger(tmp_path)
    assert result.rows is result.horizons is None and result.source == marker
    callback.assert_called_once_with(tmp_path, registry.CLAIMS_REL)
    monkeypatch.setattr(sys, "argv", ["metric", "--root", str(tmp_path), "--json"])
    assert metric.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["store_absent"] is True and payload["findings"] is None
    assert "storage_error" not in payload


@pytest.mark.parametrize("kind", ["missing", "corrupt"])
def test_real_locked_local_source_failure_reaches_accountability_before_writes(
    tmp_path, limits, monkeypatch, kind,
):
    fixture = FixtureBinding(tmp_path, limits)
    for name, payload in fixture.members.items():
        put(tmp_path, name, payload)
    name, original = fixture.damage_tail(kind)
    affected = tmp_path / name
    if kind == "missing":
        affected.unlink()
    else:
        affected.write_bytes(fixture.members[name])

    class LocalBinding:
        claims_path = tmp_path / CLAIMS_REL

        def read_snapshot(self):
            with sources.claims_lock(
                tmp_path / sources.LOCK_RELATIVE_PATH, mode="shared", timeout=1,
            ) as lease:
                root_digest = sources.pin_local_root(tmp_path, lease=lease, limits=limits)
                source = sources.LockedLocalSource(
                    tmp_path, lease=lease, expected_root_digest=root_digest, limits=limits,
                )
                return sources.verify_source_snapshot(source, limits=limits)

    json_write, markdown_write = Mock(), Mock()
    monkeypatch.setattr(accountability, "_write_json", json_write)
    monkeypatch.setattr(accountability, "_write_md", markdown_write)
    binding = LocalBinding()
    with bound(binding), pytest.raises(protocol.SnapshotIntegrityError):
        accountability.run(tmp_path, write=True)
    json_write.assert_not_called()
    markdown_write.assert_not_called()
    # The failed read released the lease, and restoring the owned fixture yields
    # the two complete logical rows rather than silently discarding the tail.
    affected.write_bytes(original)
    with bound(binding):
        report = accountability.run(tmp_path, write=False)
    assert report["global"]["n_claims"] == 2
