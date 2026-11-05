"""FIF Z0 row A18: V0 publish-path failure-injection drill.

The store-level reconciliation drill
(tests/test_fundamental_forensics_recovery_drill.py:605-663) proves the A18
write law at the ENGINE boundary. This module drives the same fault classes
through the path production actually runs — the publisher CLI's own plan,
commit, read-back, report and re-run sequence
(scripts/publish_fif_production_datasets.py:2036-2126) — against ONE
fault-injected production store object, and asserts exactly-once publication
under each fault:

S1 lost write response (``raise_on_conditional_after_commit``): the engine
   reconciles the lost response by byte-exact read-back
   (production_datasets.py:660-670), so run 1 publishes once and SUCCEEDS;
   run 2 reports every issuer ``unchanged`` at the same generation id with a
   zero-object key-set delta. Run 1 failing (rc != 0) for a write whose
   commit LANDED is not reachable at BASE — that premise gap is recorded in
   the lane return, and the absorption itself is the exactly-once proof.
S2 immediate absence (``raise_on_conditional_after_commit`` +
   ``drop_after_commit``): run 1 exits rc != 0 with the typed partial report
   (failed row ``publish_failed`` / ProductionDatasetEffectUnknownError,
   not-attempted issuers listed) and NOTHING landed — no pointer, no
   manifest, no objects; run 2 publishes cleanly with no dangling run-1
   object. ``drop_after_commit`` alone is inert at BASE
   (production_datasets.py:1501-1505 consults it only inside the raise
   branch) — pinned by its own test below.
S3 delayed commit (``_DelayedPointerStore``): the first pointer CAS is
   denied while its commit becomes visible one read later; run 1 exits rc != 0
   with a typed failed row and the manifest landed-but-pointer-absent store;
   run 2's plan phase reads the landed pointer and reports the issuer
   ``unchanged`` at the run-1 generation id — no second generation, no
   publisher write for the issuer.

Clocks are the publisher bench's fixed constants; no wall clock, no network.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

from engine.fundamental_forensics import production_datasets as PDS
import scripts.publish_fif_production_datasets as producer
from tests.test_fundamental_forensics_production_publisher import (
    NEXT_NIGHT_RUN,
    _capture_cli,
    _fixture_identity,
    _materialize_lane,
    _publish_cli,
    _stage_three_issuers,
    _stderr_error_lines,
    _write_contract,
    offline_collector,  # noqa: F401  (fixture re-export)
)


# ---------------------------------------------------------------------------
# Store doubles (fault injection rides the engine's own in-memory double)
# ---------------------------------------------------------------------------


class _FaultRecordingStore(PDS.InMemoryStrictConditionalStore):
    """The engine's in-memory strict-conditional double plus drill telemetry.

    Records every write-path method name (so the drill can prove the
    publisher never touches the refused unconditional ``put_bytes`` path)
    and every transport fault the store raised after a commit, which is the
    positive evidence that a lost-write-response fault actually fired.
    """

    def __init__(self) -> None:
        super().__init__()
        self.write_method_calls: list[str] = []
        self.transport_faults: list[str] = []

    def put_bytes_strict_conditional(
        self,
        key: str,
        data: bytes,
        *,
        expected_version: str | None,
        content_type: str = "application/octet-stream",
    ) -> bool:
        self.write_method_calls.append("put_bytes_strict_conditional")
        try:
            return super().put_bytes_strict_conditional(
                key, data, expected_version=expected_version, content_type=content_type
            )
        except RuntimeError as exc:
            self.transport_faults.append(f"{key}: {exc}")
            raise

    def put_bytes(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> bool:
        self.write_method_calls.append("put_bytes")
        return super().put_bytes(key, data, content_type=content_type)

    def raw_put(self, key: str, data: bytes) -> None:
        self.write_method_calls.append("raw_put")
        super().raw_put(key, data)

    def drop(self, key: str) -> None:
        self.write_method_calls.append("drop")
        super().drop(key)


class _DelayedPointerStore(_FaultRecordingStore):
    """A18 double (S3): the first pointer CAS is denied, its commit lands late.

    The denial mirrors ``false_on_conditional`` (the backing authority
    rejected the predecessor). The commit becomes visible one read later:
    the engine reconciles a denied CAS by reading the pointer immediately
    (production_datasets.py:715 inside ``_pointer_after_failed_cas``), so a
    commit flushed on that very read is absorbed in-run and the failure
    path never happens. Landing on the NEXT read keeps the write genuinely
    "late": run 1's reconciliation sees absence (typed failed row, rc != 0)
    and the following publisher run's plan read observes the landed
    generation. Every other write and read behaves normally.
    """

    def __init__(self, issuer_id: str) -> None:
        super().__init__()
        self._issuer_id = issuer_id
        self._pending: tuple[str, bytes] | None = None
        self._denied = False
        self._reads_since_denial = 0

    def put_bytes_strict_conditional(
        self,
        key: str,
        data: bytes,
        *,
        expected_version: str | None,
        content_type: str = "application/octet-stream",
    ) -> bool:
        if (
            not self._denied
            and expected_version is None
            and key == PDS.production_latest_key(self._issuer_id)
        ):
            self.conditional_writes.append((key, expected_version))
            self._denied = True
            self._pending = (key, bytes(data))
            return False
        return super().put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type
        )

    def get_bytes_strict_bounded_versioned(self, key: str, maximum_bytes: int):
        observed = super().get_bytes_strict_bounded_versioned(key, maximum_bytes)
        if (
            self._denied
            and self._pending is not None
            and key == PDS.production_latest_key(self._issuer_id)
        ):
            self._reads_since_denial += 1
            if self._reads_since_denial >= 2:
                pending_key, payload = self._pending
                self._pending = None
                self.raw_put(pending_key, payload)
                return super().get_bytes_strict_bounded_versioned(key, maximum_bytes)
        return observed


# ---------------------------------------------------------------------------
# Drill harness: the publisher's own CLI against the injected real store
# ---------------------------------------------------------------------------


def _inject_real_store(monkeypatch, store: Any, store_dir: Path) -> list[str]:
    """The store seam (publisher test module :1978-1986): the factory returns
    the fault-injected store ONLY for the real ``--store-dir`` path; every
    other build — the plan-phase scratch stores — gets the honest builder.
    Returns the type names of the honest builds so S4 can prove the fault
    never reached a scratch store."""
    real_builder = producer.build_production_dataset_store
    built: list[str] = []

    def _factory(local_dir=None):
        product = real_builder(local_dir)
        if local_dir is not None and Path(local_dir) == store_dir:
            return store
        built.append(type(product).__name__)
        return product

    monkeypatch.setattr(producer, "build_production_dataset_store", _factory)
    return built


def _run_publish_fault_drill(
    tmp_path: Path,
    monkeypatch,
    store: Any,
    arm: Callable[[], None],
) -> dict[str, Any]:
    """Stage three issuers, run the publisher CLI twice against the SAME
    injected store object (run 1 armed with the fault, run 2 with the fault
    cleared), and return both reports plus the store's key sets and write
    logs after each run."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store_dir = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    _stage_three_issuers(monkeypatch)
    scratch_builds = _inject_real_store(monkeypatch, store, store_dir)
    arm()
    rc1 = _publish_cli(lane, contract, store_dir, report_path)
    report1 = json.loads(report_path.read_text(encoding="utf-8"))
    keys1 = store.list_prefix("")
    writes1 = list(store.conditional_writes)
    store.raise_on_conditional_after_commit = False
    store.drop_after_commit = False
    rc2 = _publish_cli(lane, contract, store_dir, report_path, clock=NEXT_NIGHT_RUN)
    report2 = json.loads(report_path.read_text(encoding="utf-8"))
    keys2 = store.list_prefix("")
    return {
        "identity": identity,
        "entity_ids": [
            identity["entity_id"],
            identity["entity_id"] + "2",
            identity["entity_id"] + "3",
        ],
        "rc1": rc1,
        "report1": report1,
        "keys1": keys1,
        "writes1": writes1,
        "rc2": rc2,
        "report2": report2,
        "keys2": keys2,
        "scratch_builds": scratch_builds,
        "store": store,
    }


def _scenario(name: str) -> tuple[Any, Callable[[], None]]:
    if name == "s1_lost_write_response":
        store = _FaultRecordingStore()

        def arm() -> None:
            store.raise_on_conditional_after_commit = True

        return store, arm
    if name == "s2_immediate_absence":
        store = _FaultRecordingStore()

        def arm() -> None:
            store.raise_on_conditional_after_commit = True
            store.drop_after_commit = True

        return store, arm
    store = _DelayedPointerStore(_fixture_identity()["entity_id"])
    return store, lambda: None


SCENARIOS = (
    "s1_lost_write_response",
    "s2_immediate_absence",
    "s3_delayed_commit",
)


# ---------------------------------------------------------------------------
# Small assertion helpers
# ---------------------------------------------------------------------------


def _issuer_prefix(entity_id: str) -> str:
    return f"{PDS.PRODUCTION_DATASET_PREFIX}/issuers/{entity_id}"


def _issuer_key_prefix(entity_id: str) -> str:
    """Path-segment-scoped issuer prefix (trailing slash), so the derived
    second/third issuer ids (``<id>2``/``<id>3``) never superstring-match."""
    return f"{_issuer_prefix(entity_id)}/"


def _generation_manifests(store: Any, entity_id: str) -> list[str]:
    return store.list_prefix(f"{_issuer_key_prefix(entity_id)}generations/")


def _published_row(report: dict[str, Any], entity_id: str) -> dict[str, Any]:
    for row in report["published"]:
        if row["entity_id"] == entity_id:
            return row
    raise AssertionError(f"no published row for {entity_id}")


def _generation_id_from_manifest_key(key: str) -> str:
    return key.rsplit("/", 1)[-1][: -len(".json")]


# ---------------------------------------------------------------------------
# S1 — lost write response (commit landed, response lost)
# ---------------------------------------------------------------------------


def test_s1_lost_write_response_is_reconciled_in_run_exactly_once(
    tmp_path, monkeypatch, offline_collector
) -> None:
    store, arm = _scenario("s1_lost_write_response")
    drill = _run_publish_fault_drill(tmp_path, monkeypatch, store, arm)
    entity_ids = drill["entity_ids"]

    # Run 1: the fault FIRED (one transport fault after a commit) and the
    # engine reconciled it by byte-exact read-back — idempotent completion,
    # so the publisher publishes once and succeeds. A lost response whose
    # commit landed cannot fail the run at BASE.
    assert drill["rc1"] == 0
    assert len(store.transport_faults) == 1
    assert store.raise_on_conditional_after_commit is False
    assert drill["report1"].get("failed") is None
    assert drill["report1"].get("not_attempted") is None
    rows1 = {row["entity_id"]: row for row in drill["report1"]["published"]}
    assert set(rows1) == set(entity_ids)
    assert all(row["outcome"] == "published" for row in rows1.values())
    generation_ids = {eid: rows1[eid]["generation_id"] for eid in entity_ids}

    # Run 2 (fault cleared): every issuer is the already-published path —
    # outcome unchanged at latest_unchanged, SAME generation ids, and the
    # store's key set is byte-for-byte identical (zero new objects).
    assert drill["rc2"] == 0
    rows2 = {row["entity_id"]: row for row in drill["report2"]["published"]}
    assert set(rows2) == set(entity_ids)
    for eid in entity_ids:
        assert rows2[eid]["outcome"] == "unchanged"
        assert rows2[eid]["clock_basis"] == "latest_unchanged"
        assert rows2[eid]["generation_id"] == generation_ids[eid]
    assert drill["keys2"] == drill["keys1"]

    # Exactly one generation manifest for the issuer; the pointer names it
    # and the generation loads.
    primary = entity_ids[0]
    manifests = _generation_manifests(store, primary)
    assert manifests == [
        PDS.production_manifest_key(primary, generation_ids[primary])
    ]
    latest = PDS.load_latest_generation(store, primary)
    assert latest is not None and latest.generation_id == generation_ids[primary]
    loaded = PDS.load_generation(store, primary, generation_ids[primary])
    assert loaded.generation_id == generation_ids[primary]


# ---------------------------------------------------------------------------
# S2 — immediate absence (committed object dropped, response lost)
# ---------------------------------------------------------------------------


def test_s2_immediate_absence_writes_typed_partial_report_then_clean_rerun(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    store, arm = _scenario("s2_immediate_absence")
    drill = _run_publish_fault_drill(tmp_path, monkeypatch, store, arm)
    entity_ids = drill["entity_ids"]
    primary = entity_ids[0]

    # Run 1: rc != 0 with the typed partial report — the failed row names the
    # issuer with the typed code and a non-empty error, the not-attempted
    # issuers are listed, and the typed code rides stderr.
    assert drill["rc1"] == 1
    failed = drill["report1"]["failed"]
    assert failed["entity_id"] == primary
    assert failed["code"] == "publish_failed"
    assert failed["error"]
    assert "ProductionDatasetEffectUnknownError" in failed["error"]
    assert [row["entity_id"] for row in drill["report1"]["not_attempted"]] == [
        entity_ids[1],
        entity_ids[2],
    ]
    assert drill["report1"]["published"] == []
    assert any(
        "publish_failed" in line for line in _stderr_error_lines(capsys)
    )
    assert len(store.transport_faults) == 1

    # Observed store facts after run 1: NOTHING landed for any issuer — no
    # pointer, no manifest, no objects (the fault fired on the very first
    # conditional write and the store dropped it).
    assert drill["keys1"] == []

    # Run 2 (fault cleared): the publisher publishes all three issuers
    # cleanly; each has exactly one loadable generation and the pointer
    # names it.
    assert drill["rc2"] == 0
    rows2 = {row["entity_id"]: row for row in drill["report2"]["published"]}
    assert set(rows2) == set(entity_ids)
    assert all(row["outcome"] == "published" for row in rows2.values())
    latest = PDS.load_latest_generation(store, primary)
    assert latest is not None
    loaded = PDS.load_generation(store, primary, latest.generation_id)
    assert loaded.generation_id == latest.generation_id
    # No run-1 object is dangling unreferenced: the store was empty after
    # run 1, and the issuer prefix holds exactly the pointer, the one
    # generation manifest the pointer names and (A21, R-A21-STORE-TRACE)
    # the observation record THIS clean run wrote for its own publication —
    # never a run-1 object, which the withheld commit-phase record proves.
    assert set(drill["keys2"]) >= {
        PDS.production_latest_key(primary),
        PDS.production_manifest_key(primary, latest.generation_id),
    }
    observation_key = producer.observation_key(primary)
    issuer_keys = set(store.list_prefix(_issuer_key_prefix(primary)))
    assert issuer_keys - {observation_key} == {
        PDS.production_latest_key(primary),
        PDS.production_manifest_key(primary, latest.generation_id),
    }
    if observation_key in issuer_keys:
        observation = json.loads(store.get_bytes(observation_key) or b"{}")
        assert observation["state"] == "new_filing"
        assert observation["publication"]["generation_id"] == latest.generation_id


def test_s2_drop_after_commit_alone_is_inert_at_base(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """``drop_after_commit = True`` on its own produces no fault at BASE: the
    flag is consulted only inside the raise branch
    (engine/fundamental_forensics/production_datasets.py:1501-1505), so the
    packet's S2 premise "drop_after_commit = True" alone cannot produce
    immediate absence. This run is therefore a clean publication — the
    premise-gap evidence recorded for the A18 row."""
    store = _FaultRecordingStore()

    def arm() -> None:
        store.drop_after_commit = True

    drill = _run_publish_fault_drill(tmp_path, monkeypatch, store, arm)
    assert drill["rc1"] == 0
    assert store.transport_faults == []
    assert store.raise_on_conditional_after_commit is False
    assert all(
        row["outcome"] == "published" for row in drill["report1"]["published"]
    )
    assert drill["rc2"] == 0
    assert all(
        row["outcome"] == "unchanged" for row in drill["report2"]["published"]
    )
    assert drill["keys2"] == drill["keys1"]


# ---------------------------------------------------------------------------
# S3 — delayed commit (pointer CAS denied, commit lands one read later)
# ---------------------------------------------------------------------------


def test_s3_delayed_pointer_commit_lands_before_rerun_reports_unchanged(
    tmp_path, monkeypatch, offline_collector
) -> None:
    store, arm = _scenario("s3_delayed_commit")
    drill = _run_publish_fault_drill(tmp_path, monkeypatch, store, arm)
    entity_ids = drill["entity_ids"]
    primary = entity_ids[0]
    pointer_key = PDS.production_latest_key(primary)

    # Run 1: rc != 0 with a typed failed row; the manifest landed but the
    # pointer is absent (read-back cannot name the generation).
    assert drill["rc1"] == 1
    failed = drill["report1"]["failed"]
    assert failed["entity_id"] == primary
    assert failed["code"] == "publish_failed"
    assert "compare-and-swap conflict" in failed["error"]
    assert [row["entity_id"] for row in drill["report1"]["not_attempted"]] == [
        entity_ids[1],
        entity_ids[2],
    ]
    manifests1 = _generation_manifests(store, primary)
    assert len(manifests1) == 1
    generation_id = _generation_id_from_manifest_key(manifests1[0])
    assert manifests1 == [PDS.production_manifest_key(primary, generation_id)]
    assert pointer_key not in drill["keys1"]

    # Run 2 (plain behaviour — the denial is one-shot): the plan phase's
    # pointer read is where the delayed run-1 commit lands, so the issuer is
    # reported unchanged at the run-1 generation id.
    assert drill["rc2"] == 0
    row2 = _published_row(drill["report2"], primary)
    assert row2["outcome"] == "unchanged"
    assert row2["clock_basis"] == "latest_unchanged"
    assert row2["generation_id"] == generation_id
    others = {row["entity_id"]: row for row in drill["report2"]["published"]}
    assert others[entity_ids[1]]["outcome"] == "published"
    assert others[entity_ids[2]]["outcome"] == "published"

    # Zero new objects for the faulted material — never a second generation
    # id: still exactly the run-1 manifest, and the publisher performed no
    # conditional write for the issuer in run 2. The only issuer-prefix
    # addition is the pointer itself, arriving via the store's delayed
    # landing of the run-1 write, not via a publisher write.
    assert _generation_manifests(store, primary) == manifests1
    writes_after_run1 = store.conditional_writes[len(drill["writes1"]) :]
    assert pointer_key not in [key for key, _ in writes_after_run1]
    assert not [
        key
        for key, _ in writes_after_run1
        if key.startswith(_issuer_key_prefix(primary))
    ]
    assert set(store.list_prefix(_issuer_key_prefix(primary))) == {
        pointer_key,
        PDS.production_manifest_key(primary, generation_id),
    }

    # The pointer names the landed generation and it loads.
    latest = PDS.load_latest_generation(store, primary)
    assert latest is not None and latest.generation_id == generation_id
    loaded = PDS.load_generation(store, primary, generation_id)
    assert loaded.generation_id == generation_id


# ---------------------------------------------------------------------------
# S4 — cross-drill invariants, parametrised over S1-S3
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_s4_cross_drill_invariants(
    tmp_path, monkeypatch, offline_collector, scenario: str
) -> None:
    store, arm = _scenario(scenario)
    drill = _run_publish_fault_drill(tmp_path, monkeypatch, store, arm)

    # The plan-phase scratch stores never receive the fault: every non-real
    # store the factory built is an honest builder product (a LocalStore on
    # the scratch tempdir), never the injected fault store — one per run.
    assert len(drill["scratch_builds"]) >= 2
    assert set(drill["scratch_builds"]) == {"LocalStore"}

    # The report is valid JSON on every run (the runner parsed both, partial
    # and full) and carries the report schema.
    schema = "fundamental_forensics.fif_production_publish_report/v1"
    assert drill["report1"]["schema"] == schema
    assert drill["report2"]["schema"] == schema

    # The real store never holds two generation manifests for one issuer.
    for eid in drill["entity_ids"]:
        assert len(_generation_manifests(store, eid)) == 1

    # The publisher never calls the refused unconditional put_bytes path.
    assert "put_bytes" not in store.write_method_calls
    assert store.unconditional_writes == []
