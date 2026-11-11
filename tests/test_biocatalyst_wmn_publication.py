from __future__ import annotations

import json

import pytest
from datetime import date
from hashlib import sha256

from engine.biocatalyst.company_event_adapter import resolve_current_event_identity
from engine.biocatalyst.publication import PublicGenerationPublisher
from engine.biocatalyst.what_matters_next import validate_wmn_inputs
from engine.company_intelligence.contracts import canonical_json_sha256
from engine.company_intelligence.events import project_catalyst_event
from engine.company_intelligence.identity import company_id_for_cik
from lib.dataos.identity import IssuerMaster, VendorAliasTable
import scripts.biocatalyst_worker as worker
from tests.test_biocatalyst_worker import FakeCollectorFactory, MemoryStore, NOW, config


CIK = "0001365916"
COMPANY = company_id_for_cik(CIK)
CUTOFF = "2026-08-01T15:00:04Z"


def _wmn_inputs() -> dict:
    event = project_catalyst_event(
        company_id=COMPANY,
        issuer_cik=CIK,
        source_namespace="issuer_disclosure",
        native_event_key="doc_2026_08_01#claim/readout",
        event_family="issuer_readout_guidance",
        revision_ref="doc_2026_08_01:r1",
        revision_is_current=True,
        occurrence="uncorroborated",
        timing={
            "state": "consistent",
            "source_class": "issuer_guided",
            "lower_date": "2026-09-01",
            "upper_date": "2026-09-01",
            "precision": "day",
            "source_timezone": None,
            "source_wording": "expects topline data in September 2026",
            "evidence_refs": ["ev_public_fixture"],
        },
        source_available_at="2026-08-01T14:00:00Z",
        observed_at="2026-08-01T14:00:01Z",
        document_refs=["doc_2026_08_01:r1"],
        public_evidence=[],
        asset_mentions=[],
        relationship_claims=[],
        generation_cutoff=CUTOFF,
    )
    master = IssuerMaster.from_records([
        {
            "security_id": "SEC:US-XNAS-AMLX",
            "issuer_id": "ISS:US-XNAS-AMLX",
            "issuer_state": "RESOLVED",
            "issuer_cik": CIK,
            "listing_key": "US-XNAS-AMLX",
            "security_state": None,
            "superseded_by": None,
        }
    ])
    aliases = VendorAliasTable.from_records([
        {
            "vendor": "store",
            "vendor_symbol": "AMLX",
            "security_id": "SEC:US-XNAS-AMLX",
            "valid_from": None,
            "valid_to": None,
        }
    ])
    identity = resolve_current_event_identity(
        event,
        issuer_master=master,
        alias_table=aliases,
        identity_cut_date=date(2026, 8, 1),
        identity_observed_at="2026-08-01T15:00:00Z",
        generation_cutoff=CUTOFF,
    )
    return {
        "contract_id": "biocatalyst_wmn_inputs.v2",
        "schema_version": "2.0.0",
        "input_cut": {
            "cutoff": CUTOFF,
            "members": [
                {
                    "contract_id": "company_catalyst_event.v1",
                    "ref": event["event_id"],
                    "sha256": canonical_json_sha256(event),
                    "observed_at": event["observed_at"],
                    "accepted_at": event["observed_at"],
                    "availability": "available",
                },
                {
                    "contract_id": "dataos_issuer_master.current",
                    "ref": "issuer-master-cut-2026-08-01",
                    "sha256": "2" * 64,
                    "observed_at": "2026-08-01T15:00:00Z",
                    "accepted_at": "2026-08-01T15:00:00Z",
                    "availability": "available",
                },
                {
                    "contract_id": "dataos_vendor_aliases.current",
                    "ref": "vendor-alias-cut-2026-08-01",
                    "sha256": "3" * 64,
                    "observed_at": "2026-08-01T15:00:00Z",
                    "accepted_at": "2026-08-01T15:00:00Z",
                    "availability": "available",
                },
            ],
        },
        "events": [event],
        "relationships": [],
        "identity_projection": {event["event_id"]: identity},
        "coverage": {
            "declared_universe_ref": "bio:first-company-event-slice",
            "source_health": "current",
            "family_states": {
                "issuer_readout_guidance": {
                    "declared_scope": "issuer_disclosure:first_slice",
                    "observed_count": 1,
                    "state": "partial",
                }
            },
            "missing_owner_ports": [
                "asset_relationships",
                "economic_exposure",
                "probability",
                "materiality",
                "historical_response",
                "incorporation",
            ],
        },
        "authority": event["authority"],
    }


def test_worker_can_publish_pointer_bound_wmn_owner_cut(tmp_path) -> None:
    cfg = config(tmp_path)
    store = MemoryStore()
    inputs = _wmn_inputs()

    result = worker.run_once(
        cfg,
        collector_factory=FakeCollectorFactory(),
        store_factory=lambda _: store,
        now_fn=lambda: NOW,
        activation_verifier=lambda _config, _now: None,
        wmn_inputs=inputs,
    )

    assert result.exit_code == worker.EXIT_SUCCESS
    publisher = PublicGenerationPublisher(cfg.public_root)
    committed = publisher.read_committed()
    assert committed is not None
    assert committed.schema_version == "1.9.0"
    generation = cfg.public_root / "generations" / committed.generation_id
    artifact_path = generation / "what_matters_next_inputs.json"
    assert artifact_path.is_file()
    artifact = json.loads(artifact_path.read_text())
    assert artifact == validate_wmn_inputs(inputs)

    manifest = json.loads((generation / "manifest.json").read_text())
    entry = next(a for a in manifest["artifacts"] if a["name"] == "what_matters_next_inputs.json")
    raw = artifact_path.read_bytes()
    assert entry == {
        "name": "what_matters_next_inputs.json",
        "sha256": sha256(raw).hexdigest(),
        "byte_count": len(raw),
    }

    projection = publisher.read_trial_projection()
    assert projection is not None
    assert projection.what_matters_next_inputs == validate_wmn_inputs(inputs)


def test_worker_without_owner_cut_remains_old_generation_shape(tmp_path) -> None:
    cfg = config(tmp_path)
    result = worker.run_once(
        cfg,
        collector_factory=FakeCollectorFactory(),
        store_factory=lambda _: MemoryStore(),
        now_fn=lambda: NOW,
        activation_verifier=lambda _config, _now: None,
    )
    assert result.exit_code == worker.EXIT_SUCCESS
    publisher = PublicGenerationPublisher(cfg.public_root)
    committed = publisher.read_committed()
    assert committed is not None
    assert committed.schema_version == "1.7.0"
    projection = publisher.read_trial_projection()
    assert projection is not None
    assert projection.what_matters_next_inputs is None
    generation = cfg.public_root / "generations" / committed.generation_id
    assert not (generation / "what_matters_next_inputs.json").exists()


def _environment_for_wmn(tmp_path):
    state_root = tmp_path / "macro-biocatalyst" / "state"
    public_root = tmp_path / "macro-biocatalyst" / "public"
    return state_root, public_root, {
        "BIOCATALYST_ENABLED": "1",
        "BIOCATALYST_STATE_ROOT": str(state_root),
        "BIOCATALYST_PUBLIC_ROOT": str(public_root),
        "BIOCATALYST_CANARY_NCTS": "NCT00000001",
        "BIOCATALYST_USER_AGENT": "MastermindX test contact@example.com",
        "BIOCATALYST_R2_ENDPOINT": "https://r2.example.test",
        "BIOCATALYST_R2_BUCKET": "biocatalyst-private",
        "BIOCATALYST_R2_ACCESS_KEY_ID": "test-access",
        "BIOCATALYST_R2_SECRET_ACCESS_KEY": "test-secret",
        "BIOCATALYST_WMN_ENABLED": "1",
    }


def test_environment_worker_acquires_and_publishes_configured_owner_cut(tmp_path, monkeypatch):
    state_root, public_root, environ = _environment_for_wmn(tmp_path)
    owner_path = tmp_path / "owner-inputs" / "what_matters_next_inputs.json"
    owner_path.parent.mkdir(parents=True)
    owner_path.write_text(json.dumps(_wmn_inputs()), encoding="utf-8")
    monkeypatch.setattr(worker, "_SERVICE_STATE_ROOT", state_root)
    monkeypatch.setattr(worker, "_SERVICE_PUBLIC_ROOT", public_root)
    monkeypatch.setattr(worker, "_SERVICE_WMN_INPUTS_PATH", owner_path)

    result = worker.run_from_environment(
        environ,
        collector_factory=FakeCollectorFactory(),
        store_factory=lambda _: MemoryStore(),
        now_fn=lambda: NOW,
        activation_verifier=lambda _config, _now: None,
    )

    assert result.exit_code == worker.EXIT_SUCCESS
    publisher = PublicGenerationPublisher(public_root)
    committed = publisher.read_committed()
    assert committed is not None
    assert committed.schema_version == "1.8.0"
    projection = publisher.read_trial_projection()
    assert projection is not None
    assert projection.what_matters_next_inputs == validate_wmn_inputs(_wmn_inputs())


def test_environment_worker_missing_required_owner_cut_preserves_prior_pointer(tmp_path, monkeypatch):
    state_root, public_root, environ = _environment_for_wmn(tmp_path)
    owner_path = tmp_path / "owner-inputs" / "what_matters_next_inputs.json"
    monkeypatch.setattr(worker, "_SERVICE_STATE_ROOT", state_root)
    monkeypatch.setattr(worker, "_SERVICE_PUBLIC_ROOT", public_root)
    monkeypatch.setattr(worker, "_SERVICE_WMN_INPUTS_PATH", owner_path)

    legacy = worker.run_from_environment(
        {k: v for k, v in environ.items() if k != "BIOCATALYST_WMN_ENABLED"},
        collector_factory=FakeCollectorFactory(),
        store_factory=lambda _: MemoryStore(),
        now_fn=lambda: NOW,
        activation_verifier=lambda _config, _now: None,
    )
    assert legacy.exit_code == worker.EXIT_SUCCESS
    before = (public_root / "current.json").read_bytes()

    calls = {"collector": 0}
    failed = worker.run_from_environment(
        environ,
        collector_factory=lambda **_: calls.__setitem__("collector", calls["collector"] + 1),
        store_factory=lambda _: MemoryStore(),
        now_fn=lambda: NOW,
        activation_verifier=lambda _config, _now: None,
    )

    assert failed.exit_code == worker.EXIT_FAILED
    assert failed.status == "failed"
    assert failed.error_code == "BIOCATALYST_WMN_OWNER_INPUT_UNAVAILABLE"
    assert calls["collector"] == 0
    assert (public_root / "current.json").read_bytes() == before
    health = json.loads((public_root / "health.json").read_text(encoding="utf-8"))
    assert health["state"] == "partial"
    assert health["last_error_code"] == "BIOCATALYST_WMN_OWNER_INPUT_UNAVAILABLE"


def test_environment_worker_rejects_malformed_owner_cut_before_collection(tmp_path, monkeypatch):
    state_root, public_root, environ = _environment_for_wmn(tmp_path)
    owner_path = tmp_path / "owner-inputs" / "what_matters_next_inputs.json"
    owner_path.parent.mkdir(parents=True)
    owner_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(worker, "_SERVICE_STATE_ROOT", state_root)
    monkeypatch.setattr(worker, "_SERVICE_PUBLIC_ROOT", public_root)
    monkeypatch.setattr(worker, "_SERVICE_WMN_INPUTS_PATH", owner_path)

    calls = {"collector": 0}
    result = worker.run_from_environment(
        environ,
        collector_factory=lambda **_: calls.__setitem__("collector", calls["collector"] + 1),
        store_factory=lambda _: MemoryStore(),
        now_fn=lambda: NOW,
        activation_verifier=lambda _config, _now: None,
    )

    assert result.exit_code == worker.EXIT_FAILED
    assert result.error_code == "BIOCATALYST_WMN_OWNER_INPUT_INVALID"
    assert calls["collector"] == 0
    assert not (public_root / "current.json").exists()


def test_environment_rejects_nonbinary_wmn_enable_flag(tmp_path, monkeypatch):
    state_root, public_root, environ = _environment_for_wmn(tmp_path)
    monkeypatch.setattr(worker, "_SERVICE_STATE_ROOT", state_root)
    monkeypatch.setattr(worker, "_SERVICE_PUBLIC_ROOT", public_root)
    plan = worker.load_environment({**environ, "BIOCATALYST_WMN_ENABLED": "true"})
    assert plan.state == "invalid"
    assert plan.error_code == "BIOCATALYST_WMN_ENABLED_INVALID"


@pytest.mark.parametrize(
    "owner_bytes",
    [
        b"{]",
        b"\xff\xfe",
        b'{"x":1,"x":2}',
        b'{"x":0.10000000000000001}',
    ],
    ids=["syntax", "utf8", "duplicate-key", "lossy-number"],
)
def test_environment_worker_invalid_json_is_typed_and_precollection(
    tmp_path, monkeypatch, owner_bytes
):
    state_root, public_root, environ = _environment_for_wmn(tmp_path)
    owner_path = tmp_path / "owner-inputs" / "what_matters_next_inputs.json"
    owner_path.parent.mkdir(parents=True)
    owner_path.write_bytes(owner_bytes)
    monkeypatch.setattr(worker, "_SERVICE_STATE_ROOT", state_root)
    monkeypatch.setattr(worker, "_SERVICE_PUBLIC_ROOT", public_root)
    monkeypatch.setattr(worker, "_SERVICE_WMN_INPUTS_PATH", owner_path)

    calls = {"collector": 0}
    result = worker.run_from_environment(
        environ,
        collector_factory=lambda **_: calls.__setitem__("collector", calls["collector"] + 1),
        store_factory=lambda _: MemoryStore(),
        now_fn=lambda: NOW,
        activation_verifier=lambda _config, _now: None,
    )

    assert result.exit_code == worker.EXIT_FAILED
    assert result.status == "failed"
    assert result.error_code == "BIOCATALYST_WMN_OWNER_INPUT_INVALID"
    assert calls["collector"] == 0
    assert not (public_root / "current.json").exists()


def test_wmn_owner_cut_rejects_atomic_replacement_during_descriptor_read(tmp_path, monkeypatch):
    owner_path = tmp_path / "owner-inputs" / "what_matters_next_inputs.json"
    owner_path.parent.mkdir(parents=True)
    owner_path.write_text(json.dumps(_wmn_inputs()), encoding="utf-8")
    replacement = tmp_path / "owner-inputs" / "replacement.json"
    replacement.write_text("{", encoding="utf-8")

    real_read = worker.os.read
    swapped = {"done": False}

    def swapping_read(fd, size):
        if not swapped["done"]:
            replacement.replace(owner_path)
            swapped["done"] = True
        return real_read(fd, size)

    monkeypatch.setattr(worker.os, "read", swapping_read)

    with pytest.raises(
        worker.WorkerConfigError,
        match="BIOCATALYST_WMN_OWNER_INPUT_INVALID",
    ):
        worker._load_service_wmn_inputs(owner_path)

    assert swapped["done"] is True
    assert owner_path.read_text(encoding="utf-8") == "{"



# Captured by the original ec5 publisher with the existing offline collector.
# These bytes are not regenerated by the implementation under test.
def _legacy_v1_capture() -> dict:
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/biocatalyst_wmn/legacy_v1_generation_ec5.json"
    raw = fixture.read_bytes()
    assert sha256(raw).hexdigest() == "eb1dd51c9be94103feb0b7eea39e306c385fd03d70f1ecdc57a6a9c653865ed8"
    return json.loads(raw)


def _install_legacy_v1_generation(public_root) -> dict:
    capture = _legacy_v1_capture()
    for name, text in capture["public_files"].items():
        raw = text.encode("utf-8")
        assert sha256(raw).hexdigest() == capture["sha256_by_path"][name]
        path = public_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return capture


def test_legacy_v1_generation_retains_identity_bytes_and_trial_facts(tmp_path):
    public_root = tmp_path / "public"
    capture = _install_legacy_v1_generation(public_root)
    publisher = PublicGenerationPublisher(public_root)
    committed = publisher.read_committed()
    bundle = publisher.read_product_bundle()
    assert committed is not None and bundle is not None
    assert committed.generation_id == capture["generation_id"]
    assert committed.manifest_sha256 == capture["manifest_sha256"]
    prefix = f"generations/{committed.generation_id}/"
    original_inputs = json.loads(capture["public_files"][prefix + "what_matters_next_inputs.json"])
    assert bundle.projection.what_matters_next_inputs == original_inputs
    assert validate_wmn_inputs(original_inputs) == original_inputs
    assert original_inputs["contract_id"] == "biocatalyst_wmn_inputs.v1"
    assert original_inputs["schema_version"] == "1.0.0"
    assert all(member["contract_id"] != "dataos_vendor_aliases.current" for member in original_inputs["input_cut"]["members"])
    original_trial = json.loads(capture["public_files"][prefix + "trial_snapshots/NCT00000001.json"])
    assert bundle.projection.trials == (original_trial,)
    # Reading may neither rewrite the old input nor replace any selected bytes.
    for name, digest in capture["sha256_by_path"].items():
        assert sha256((public_root / name).read_bytes()).hexdigest() == digest


def test_legacy_v1_generation_still_rejects_artifact_tampering(tmp_path):
    from engine.biocatalyst.publication import PublicationError

    public_root = tmp_path / "public"
    capture = _install_legacy_v1_generation(public_root)
    path = public_root / "generations" / capture["generation_id"] / "what_matters_next_inputs.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(PublicationError):
        PublicGenerationPublisher(public_root).read_product_bundle()


def test_new_worker_publication_refuses_legacy_v1_owner_input(tmp_path, monkeypatch):
    from engine.biocatalyst.publication import PublicationError

    original_prepare = PublicGenerationPublisher.prepare_generation
    publication_errors = []

    def observe_prepare(self, *args, **kwargs):
        try:
            return original_prepare(self, *args, **kwargs)
        except PublicationError as exc:
            publication_errors.append(exc.code)
            raise

    monkeypatch.setattr(PublicGenerationPublisher, "prepare_generation", observe_prepare)
    capture = _legacy_v1_capture()
    name = f"generations/{capture['generation_id']}/what_matters_next_inputs.json"
    cfg = config(tmp_path)
    store = MemoryStore()
    result = worker.run_once(
        cfg,
        collector_factory=FakeCollectorFactory(),
        store_factory=lambda _: store,
        now_fn=lambda: NOW,
        activation_verifier=lambda _config, _now: None,
        wmn_inputs=json.loads(capture["public_files"][name]),
    )
    assert result.exit_code == worker.EXIT_FAILED
    assert publication_errors == ["WMN_OWNER_INPUT_INVALID"]
    # The worker's existing public-code allowlist projects this publisher error
    # to COLLECTION_FAILED; the actual preparation refusal is asserted above.
    assert result.error_code == "COLLECTION_FAILED"
    assert not (cfg.public_root / "current.json").exists()
    assert store.put_attempts == []


def test_service_handoff_refuses_legacy_v1_before_collection(tmp_path, monkeypatch):
    capture = _legacy_v1_capture()
    name = f"generations/{capture['generation_id']}/what_matters_next_inputs.json"
    state_root, public_root, environ = _environment_for_wmn(tmp_path)
    owner_path = tmp_path / "owner-inputs.json"
    owner_path.write_text(capture["public_files"][name], encoding="utf-8")
    monkeypatch.setattr(worker, "_SERVICE_STATE_ROOT", state_root)
    monkeypatch.setattr(worker, "_SERVICE_PUBLIC_ROOT", public_root)
    monkeypatch.setattr(worker, "_SERVICE_WMN_INPUTS_PATH", owner_path)

    def forbidden_collector(**_):
        raise AssertionError("legacy owner input must fail before collection")

    result = worker.run_from_environment(
        environ,
        collector_factory=forbidden_collector,
        store_factory=lambda _: MemoryStore(),
        now_fn=lambda: NOW,
        activation_verifier=lambda _config, _now: None,
    )
    assert result.exit_code == worker.EXIT_FAILED
    assert result.error_code == "BIOCATALYST_WMN_OWNER_INPUT_INVALID"
    assert not (public_root / "current.json").exists()
