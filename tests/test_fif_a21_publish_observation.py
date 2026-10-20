"""FIF A21: observation state wired into the C0 publish path.

Drives ``scripts.publish_fif_production_datasets`` through its real
``main()`` — reusing the incumbent publisher suite's lane helpers by import,
never by copy — and proves the per-issuer observation contract of Z0 row
A21: one immutable record per issuer at
``<prefix>/issuers/<issuer_id>/observation.json``, the versioned prior read
before planning, states decided from facts the publisher already has, CAS
persistence after the real-write loop, report projections, and same-clock
idempotence. Ruling R-A21-T8B: an unchanged check persists nothing — the
record writes only on a material transition, and a later-clock rerun with
nothing new leaves the whole store byte-identical while the report row
carries the fresh clocks. Checked-no-change, newly published, commit
failure and source outage become distinguishable per issuer after every
publish; the pointer clock alone can no longer be mistaken for evidence of
a check.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.publish_fif_production_datasets as producer
from collectors.sec_document_spine import ArchiveStoreError
from engine.fundamental_forensics.filing_observation_state import (
    FILING_OBSERVATION_SCHEMA,
)
from engine.fundamental_forensics.production_datasets import (
    InMemoryStrictConditionalStore,
    load_latest_generation,
)
from tests.test_fundamental_forensics_production_publisher import (
    NEXT_NIGHT_RUN,
    RUN_CLOCK,
    THIRD_NIGHT_RUN,
    USER_AGENT,
    _capture_cli,
    _empty_mint,
    _FakeCollector,
    _materialize_lane,
    _no_sleep_pacer,
    _publish_cli,
    _served_members,
    _stage_three_issuers,
    _stderr_error_lines,
    _store_files,
    _write_contract,
    offline_collector,
)

OBSERVATION_SCHEMA = FILING_OBSERVATION_SCHEMA


def _observation_path(store: Path, entity_id: str) -> Path:
    return store / producer.observation_key(entity_id)


def _memory_record(store: InMemoryStrictConditionalStore, entity_id: str) -> dict:
    payload = store.get_bytes(producer.observation_key(entity_id))
    assert payload is not None
    return json.loads(payload.decode("utf-8"))


def _memory_store_seam(monkeypatch, store_dir: Path, real: InMemoryStrictConditionalStore):
    """Route the REAL store (--store-dir) to an in-memory double; plan-phase
    scratch stores keep the honest builder (the incumbent seam shape)."""
    real_builder = producer.build_production_dataset_store

    def _factory(local_dir=None):
        if local_dir is not None and Path(local_dir) == store_dir:
            return real
        return real_builder(local_dir)

    monkeypatch.setattr(producer, "build_production_dataset_store", _factory)
    return real


class _CommitFaultStore(InMemoryStrictConditionalStore):
    """The first real conditional write commits, is DROPPED, then raises —
    the A18 shape no read-back can reconcile, so the commit phase fails."""

    def __init__(self) -> None:
        super().__init__()
        self.raise_on_conditional_after_commit = True
        self.drop_after_commit = True


class _ObservationFaultStore(InMemoryStrictConditionalStore):
    """Faults ONLY the first conditional write of an observation key.

    ``never_lands`` picks the failure shape: a CAS rejection that never
    commits (the write is lost outright), or a commit followed by a transport
    raise (the write landed but the run cannot know from the return value).
    """

    def __init__(self, *, never_lands: bool) -> None:
        super().__init__()
        self.never_lands = never_lands
        self.observation_writes = 0

    def put_bytes_strict_conditional(self, key, data, **kwargs):
        if key.endswith("/observation.json"):
            self.observation_writes += 1
            if self.observation_writes == 1:
                if self.never_lands:
                    return False
                self._commit(key, bytes(data))
                raise RuntimeError("observation transport failed after commit")
        return super().put_bytes_strict_conditional(key, data, **kwargs)


def _lane(tmp_path: Path) -> tuple[dict, Path, Path, Path]:
    """Materialize one captured single-issuer lane plus store/report paths."""
    lane = _materialize_lane(tmp_path)
    contract = _write_contract(tmp_path, lane["identity"], None)
    assert _capture_cli(lane, contract) == 0
    return lane, contract, tmp_path / "store", tmp_path / "publish_report.json"


# ---------------------------------------------------------------------------
# T1: first publish — new_filing, one key per issuer, current freshness
# ---------------------------------------------------------------------------


def test_t1_first_publish_writes_one_new_filing_observation_per_issuer(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    assert _capture_cli(lane, contract) == 0
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    _stage_three_issuers(monkeypatch)

    assert _publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["outcome"] for row in report["published"]] == ["published"] * 3
    assert report["observation_sla_seconds"] == 4 * 24 * 60 * 60

    entity_ids = [
        identity["entity_id"],
        identity["entity_id"] + "2",
        identity["entity_id"] + "3",
    ]
    # Exactly one observation key per issuer, and nothing else named observation.
    assert sorted(
        path.relative_to(store).as_posix()
        for path in store.rglob("observation.json")
    ) == sorted(producer.observation_key(entity_id) for entity_id in entity_ids)
    for row, entity_id in zip(report["published"], entity_ids):
        record = json.loads(
            _observation_path(store, entity_id).read_text(encoding="utf-8")
        )
        assert record["schema"] == OBSERVATION_SCHEMA
        assert record["state"] == "new_filing"
        assert record["accession"] is None  # issuer-level record
        assert record["issuer_cik"] == row["cik"]
        assert record["last_checked_at"] == "2026-10-13T02:35:00Z"
        assert record["publication"]["generation_kind"] == "issuer_manifest"
        assert record["publication"]["generation_id"] == row["generation_id"]
        assert row["observation"] == {
            "state": "new_filing",
            "last_checked_at": "2026-10-13T02:35:00Z",
            "last_successful_check_at": "2026-10-13T02:35:00Z",
            "freshness": "current",
            "persisted": True,
        }


# ---------------------------------------------------------------------------
# T2: second run, same inputs, later clock — checked_no_change
# ---------------------------------------------------------------------------


def test_t2_second_run_same_inputs_later_clock_is_checked_no_change(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane, contract, store, report_path = _lane(tmp_path)
    identity = lane["identity"]
    mem = _memory_store_seam(monkeypatch, store, InMemoryStrictConditionalStore())
    entity_id = identity["entity_id"]
    observation_key = producer.observation_key(entity_id)

    # Run 1, first publish: first creation — exactly ONE conditional write
    # per issuer at the absent prior's version; the row reports it.
    assert _publish_cli(lane, contract, store, report_path) == 0
    first_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert first_report["published"][0]["observation"]["persisted"] is True
    first = _memory_record(mem, entity_id)
    assert first["state"] == "new_filing"
    after_first = mem.get_bytes(observation_key)
    assert [
        entry for entry in mem.conditional_writes if entry[0] == observation_key
    ] == [(observation_key, None)]

    # Run 2 at a LATER clock, same inputs: the observed state moves to
    # checked_no_change, but per R-A21-T8B that relabel plus the two clock
    # fields is not a material transition — ZERO conditional writes, the
    # stored record stays byte-identical, and the report row carries the
    # fresh run-2 clocks with persisted: false.
    assert _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    row = report["published"][0]
    assert row["outcome"] == "unchanged"
    assert row["observation"] == {
        "state": "checked_no_change",
        "last_checked_at": "2026-10-14T02:35:00Z",
        "last_successful_check_at": "2026-10-14T02:35:00Z",
        "freshness": "current",
        "persisted": False,
    }
    assert [
        entry for entry in mem.conditional_writes if entry[0] == observation_key
    ] == [(observation_key, None)]
    assert mem.get_bytes(observation_key) == after_first

    # Run 3 at a YET later clock: nothing in the record but the clocks —
    # still ZERO conditional writes, store bytes identical, and the row
    # shows the run-3 clocks with persisted: false.
    assert _publish_cli(lane, contract, store, report_path, clock=THIRD_NIGHT_RUN) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    row = report["published"][0]
    assert row["observation"]["state"] == "checked_no_change"
    assert row["observation"]["last_checked_at"] == "2026-10-15T02:35:00Z"
    assert row["observation"]["last_successful_check_at"] == "2026-10-15T02:35:00Z"
    assert row["observation"]["persisted"] is False
    assert [
        entry for entry in mem.conditional_writes if entry[0] == observation_key
    ] == [(observation_key, None)]
    assert mem.get_bytes(observation_key) == after_first


# ---------------------------------------------------------------------------
# T3: changed material — new_content, old record is the CAS prior
# ---------------------------------------------------------------------------


def test_t3_changed_material_is_new_content_with_old_record_as_cas_prior(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane, contract, store, report_path = _lane(tmp_path)
    identity = lane["identity"]
    mem = _memory_store_seam(monkeypatch, store, InMemoryStrictConditionalStore())
    entity_id = identity["entity_id"]
    observation_key = producer.observation_key(entity_id)

    assert _publish_cli(lane, contract, store, report_path) == 0
    first = _memory_record(mem, entity_id)
    assert first["state"] == "new_filing"
    prior = mem.get_bytes_strict_bounded_versioned(
        observation_key, producer.OBSERVATION_KEY_MAXIMUM_BYTES
    )
    assert prior.version is not None

    monkeypatch.setattr(producer, "mint_production_lineage_evidence", _empty_mint)
    assert _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    row = report["published"][0]
    assert row["outcome"] == "published"
    second = _memory_record(mem, entity_id)
    assert second["state"] == "new_content"
    assert second["publication"]["generation_id"] != first["publication"]["generation_id"]
    assert second["publication"]["generation_id"] == row["generation_id"]
    assert row["observation"]["state"] == "new_content"
    # The old record was the CAS prior: create (no predecessor), then the
    # swap at exactly the prior read's version.
    assert [
        entry
        for entry in mem.conditional_writes
        if entry[0] == observation_key
    ] == [(observation_key, None), (observation_key, prior.version)]


# ---------------------------------------------------------------------------
# T4: commit failure — check_failed; not-attempted issuers get no record
# ---------------------------------------------------------------------------


def test_t4_commit_failure_withholds_the_observation_not_attempted_get_none(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane, contract, store, report_path = _lane(tmp_path)
    identity = lane["identity"]
    _stage_three_issuers(monkeypatch)
    fault = _memory_store_seam(monkeypatch, store, _CommitFaultStore())

    rc = _publish_cli(lane, contract, store, report_path)
    assert rc == 1
    partial = json.loads(report_path.read_text(encoding="utf-8"))
    entity_ids = [
        identity["entity_id"],
        identity["entity_id"] + "2",
        identity["entity_id"] + "3",
    ]
    assert partial["published"] == []
    assert partial["failed"]["entity_id"] == entity_ids[0]
    assert partial["failed"]["code"]
    assert [row["entity_id"] for row in partial["not_attempted"]] == entity_ids[1:]
    # R-A21-STORE-TRACE: the store faulted in the commit phase, so the
    # observation is WITHHELD (a write now would be the blind retry A18
    # forbids); the row says why and no record lands for any issuer.
    assert (
        partial["failed"]["observation_write"]
        == producer.OBSERVATION_WITHHELD_COMMIT_PHASE_FAULT
    )
    assert "observation" not in partial["failed"]
    observation_keys = sorted(
        key
        for key in fault.list_prefix("fundamental_forensics/production-datasets/v1/")
        if key.endswith("/observation.json")
    )
    assert observation_keys == []
    # No second generation: nothing landed in any issuer's generations dir.
    assert [
        key
        for key in fault.list_prefix("fundamental_forensics/production-datasets/v1/")
        if "/generations/" in key
    ] == []
    assert any(
        partial["failed"]["code"] in line for line in _stderr_error_lines(capsys)
    )


# ---------------------------------------------------------------------------
# T5: observation write lost after commit / never lands
# ---------------------------------------------------------------------------


def test_t5a_observation_write_lost_after_commit_lands_via_read_back(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane, contract, store, report_path = _lane(tmp_path)
    identity = lane["identity"]
    fault = _memory_store_seam(
        monkeypatch, store, _ObservationFaultStore(never_lands=False)
    )

    assert _publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    row = report["published"][0]
    assert fault.observation_writes == 1
    # Bounded read-back proved the committed bytes: no marker on the row.
    assert "observation_write" not in row
    record = _memory_record(fault, identity["entity_id"])
    assert record["state"] == "new_filing"
    assert row["observation"]["state"] == "new_filing"


def test_t5b_observation_write_never_lands_is_not_landed_rc_unchanged(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane, contract, store, report_path = _lane(tmp_path)
    identity = lane["identity"]
    fault = _memory_store_seam(
        monkeypatch, store, _ObservationFaultStore(never_lands=True)
    )

    assert _publish_cli(lane, contract, store, report_path) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    row = report["published"][0]
    assert fault.observation_writes == 1
    assert row["observation_write"] == "not_landed"
    assert "observation" not in row
    # The generation commit is intact and the exit code never moved.
    latest = load_latest_generation(fault, identity["entity_id"])
    assert latest is not None and latest.generation_id == row["generation_id"]
    assert fault.get_bytes(producer.observation_key(identity["entity_id"])) is None


# ---------------------------------------------------------------------------
# T6: unreadable prior — typed refusal before any write
# ---------------------------------------------------------------------------


def test_t6_unreadable_prior_record_refuses_before_any_write(
    tmp_path, monkeypatch, offline_collector, capsys
) -> None:
    lane, contract, store, report_path = _lane(tmp_path)
    identity = lane["identity"]
    assert _publish_cli(lane, contract, store, report_path) == 0
    observation = _observation_path(store, identity["entity_id"])
    assert observation.is_file()

    for junk in (b"\x00\x01 not a record", b'{"schema": "wrong.schema/v9"}'):
        observation.write_bytes(junk)
        files_junk = _store_files(store)
        capsys.readouterr()  # drop the lawful night's output
        rc = _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN)
        assert rc == 1
        assert any(
            "observation_prior_unreadable" in line
            for line in _stderr_error_lines(capsys)
        )
        # Refused before any write: same key set, junk never overwritten.
        assert _store_files(store) == files_junk
        assert observation.read_bytes() == junk


# ---------------------------------------------------------------------------
# T7: exclusion mapping — source_outage vs refusal-class check_failed
# ---------------------------------------------------------------------------


def test_t7_exclusion_observation_state_covers_every_reason_constant() -> None:
    """The mapping covers every exclusion reason string the publisher can
    emit, collected from the module's own constants (never by hand)."""
    exact_reasons = {
        producer.EXCLUSION_IDENTITY_NOT_FROZEN,
        producer.EXCLUSION_NO_RETAINED_PACKAGE,
        producer.EXCLUSION_ONLY_EVENT_PACKAGES,
    }
    prefix_reasons = {
        producer.EXCLUSION_MEMBER_CAPTURE_FAILED_PREFIX,
        producer.EXCLUSION_ADMISSION_REFUSED_PREFIX,
        producer.EXCLUSION_STATEMENT_REFUSED_PREFIX,
    }
    for reason in exact_reasons | prefix_reasons:
        assert reason in producer.EXCLUSION_OBSERVATION_STATE, reason
        assert producer.EXCLUSION_OBSERVATION_STATE[reason] in ("source_outage", "check_failed")
    # Behavioural spot map: source-side capture codes are the outage class;
    # every other code family is our side (refused / cannot attest).
    assert (
        producer.exclusion_observation_state("member_capture_failed:member_fetch_failed")
        == "source_outage"
    )
    assert (
        producer.exclusion_observation_state("member_capture_failed:submissions_unavailable")
        == "source_outage"
    )
    for reason in (
        "member_capture_failed:malformed_member",
        "admission_refused:witness_mismatch",
        f"{producer.EXCLUSION_STATEMENT_RECONSTRUCTION_REFUSED}:displayed_layout_unsupported",
        producer.EXCLUSION_NO_RETAINED_PACKAGE,
    ):
        assert producer.exclusion_observation_state(reason) == "check_failed"


def test_t7a_source_outage_exclusion_observes_source_outage(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """A capture whose member fetches all failed at the source (transport
    failure on every policy member) files
    member_capture_failed:member_fetch_failed — the source did not answer —
    so the issuer's record is source_outage."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    served = _served_members()

    class _NoAnswerCollector(_FakeCollector):
        """Every member fetch fails at the archive: the source did not answer."""

        def fetch_document(self, document, **kwargs):
            raise ArchiveStoreError(
                f"forced source outage: {document['archive_url']}"
            )

    def _collector_factory(cache_root, **kwargs):
        return _NoAnswerCollector(cache_root, served, kwargs["pacer"])

    monkeypatch.setattr(producer, "SecFilingArchiveCollector", _collector_factory)
    capture_report = tmp_path / "capture_report.json"
    rc = producer.main(
        [
            "capture-members",
            "--coverage-file", str(contract),
            "--raw-root", str(lane["raw_root"]),
            "--archive-root", str(lane["archive_root"]),
            "--recorded-at", RUN_CLOCK,
            "--user-agent", USER_AGENT,
            "--report-path", str(capture_report),
        ]
    )
    assert rc == 0
    capture = json.loads(capture_report.read_text(encoding="utf-8"))
    assert {row["outcome"] for row in capture["issuers"][0]["accessions"]} == {
        "member_capture_failed:member_fetch_failed"
    }

    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert (
        producer.main(
            [
                "publish",
                "--coverage-file", str(contract),
                "--raw-root", str(lane["raw_root"]),
                "--archive-root", str(lane["archive_root"]),
                "--recorded-at", RUN_CLOCK,
                "--store-dir", str(store),
                "--repo-root", str(Path(__file__).resolve().parents[1]),
                "--report-path", str(report_path),
                "--capture-report", str(capture_report),
            ]
        )
        == 0
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["published"] == []
    assert [row["reason"] for row in report["excluded"]] == [
        "member_capture_failed:member_fetch_failed"
    ]
    record = json.loads(
        _observation_path(store, identity["entity_id"]).read_text(encoding="utf-8")
    )
    assert record["state"] == "source_outage"
    assert record["last_successful_check_at"] is None
    assert report["excluded"][0]["observation"] == {
        "state": "source_outage",
        "last_checked_at": "2026-10-13T02:35:00Z",
        "last_successful_check_at": None,
        "freshness": "never_checked",
        "persisted": True,
    }


def test_t7b_refusal_class_exclusion_observes_check_failed(
    tmp_path, monkeypatch, offline_collector
) -> None:
    """A capture that read the bytes but failed member parsing
    (malformed_member) is our side — the source answered — so the record is
    check_failed, never absent_at_source."""
    lane = _materialize_lane(tmp_path)
    identity = lane["identity"]
    contract = _write_contract(tmp_path, identity, None)
    for accession in identity["accessions"]:
        served = offline_collector["served"][accession.replace("-", "")]
        schema_name = next(name for name in sorted(served) if name.endswith(".xsd"))
        served[schema_name] = b""
    capture_report = tmp_path / "capture_report.json"
    assert (
        producer.main(
            [
                "capture-members",
                "--coverage-file", str(contract),
                "--raw-root", str(lane["raw_root"]),
                "--archive-root", str(lane["archive_root"]),
                "--recorded-at", RUN_CLOCK,
                "--user-agent", USER_AGENT,
                "--report-path", str(capture_report),
            ]
        )
        == 0
    )
    store = tmp_path / "store"
    report_path = tmp_path / "publish_report.json"
    assert (
        producer.main(
            [
                "publish",
                "--coverage-file", str(contract),
                "--raw-root", str(lane["raw_root"]),
                "--archive-root", str(lane["archive_root"]),
                "--recorded-at", RUN_CLOCK,
                "--store-dir", str(store),
                "--repo-root", str(Path(__file__).resolve().parents[1]),
                "--report-path", str(report_path),
                "--capture-report", str(capture_report),
            ]
        )
        == 0
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["reason"] for row in report["excluded"]] == [
        "member_capture_failed:malformed_member"
    ]
    record = json.loads(
        _observation_path(store, identity["entity_id"]).read_text(encoding="utf-8")
    )
    assert record["state"] == "check_failed"
    assert report["excluded"][0]["observation"]["state"] == "check_failed"


# ---------------------------------------------------------------------------
# T8: same-clock rerun — byte-identical records, zero extra writes
# ---------------------------------------------------------------------------


def test_t8_same_clock_rerun_is_byte_identical_zero_extra_writes(
    tmp_path, monkeypatch, offline_collector
) -> None:
    lane, contract, store, report_path = _lane(tmp_path)
    identity = lane["identity"]
    mem = _memory_store_seam(monkeypatch, store, InMemoryStrictConditionalStore())
    entity_id = identity["entity_id"]
    observation_key = producer.observation_key(entity_id)

    assert _publish_cli(lane, contract, store, report_path) == 0
    assert _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN) == 0
    second_bytes = mem.get_bytes(observation_key)
    writes_before = len(mem.conditional_writes)

    # Third run at the SAME --recorded-at as the second, same inputs.
    assert _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN) == 0
    assert mem.get_bytes(observation_key) == second_bytes
    # Zero extra conditional writes beyond what BASE's unchanged rerun makes
    # (which is none): the byte-identical record is already landed.
    assert len(mem.conditional_writes) == writes_before
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["published"][0]["observation"]["state"] == "checked_no_change"


# ---------------------------------------------------------------------------
# T9: unchanged check at a later clock — zero writes, the t8b shape
# ---------------------------------------------------------------------------


def _store_tree(store: Path) -> dict[str, bytes]:
    """The t8b helper's byte-level store read, reimplemented locally."""
    return {
        path.relative_to(store).as_posix(): path.read_bytes()
        for path in sorted(store.rglob("*"))
        if path.is_file()
    }


def test_t9_unchanged_check_at_later_clock_is_zero_write_like_t8b(
    tmp_path, offline_collector
) -> None:
    lane, contract, store, report_path = _lane(tmp_path)
    identity = lane["identity"]
    assert _publish_cli(lane, contract, store, report_path) == 0
    assert _observation_path(store, identity["entity_id"]).is_file()
    before = _store_tree(store)

    # Rerun with nothing new at a later clock: the WHOLE store — generation,
    # pointer and observation record alike — stays byte-identical (t8b's
    # exactly-once zero-write invariant, R-A21-T8B), while the report row
    # still shows the fresh check clocks with persisted: false.
    assert _publish_cli(lane, contract, store, report_path, clock=NEXT_NIGHT_RUN) == 0
    assert _store_tree(store) == before
    report = json.loads(report_path.read_text(encoding="utf-8"))
    row = report["published"][0]
    assert row["outcome"] == "unchanged"
    assert row["observation"]["state"] == "checked_no_change"
    assert row["observation"]["last_checked_at"] == "2026-10-14T02:35:00Z"
    assert row["observation"]["persisted"] is False
    assert "observation_write" not in row
