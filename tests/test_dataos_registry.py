"""Dataset contracts + the static lineage DAG (Data OS §D5/§D9) — ``lib/dataos/registry.py``.

Two halves, both load-bearing:

* the SYNTHETIC half proves each violation class is actually detected (a validator
  that returns ``[]`` for everything passes a "the real registry is clean" test
  perfectly);
* the REAL half proves the committed ``config/dataset_registry.yml`` is clean and
  says only true things — a registry that lists a dataset which does not exist is
  worse than no registry, because the next session builds against it.

No ``data/`` read: the registry is a config file, and the stores it DESCRIBES are
never opened here.

Run: .venv/bin/python -m pytest tests/test_dataos_registry.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.dataos.price import is_ambiguous
from lib.dataos.registry import (
    REGISTRY_PATH,
    ConflictPolicy,
    DatasetContract,
    DatasetStatus,
    Layer,
    Registry,
    RegistryError,
    load_registry,
    validate_registry,
)
from lib.dataos.temporal import TemporalProfile

ROOT = Path(__file__).resolve().parent.parent


def contract(dataset_id: str, **overrides) -> DatasetContract:
    """A minimal VALID contract, so a test can introduce exactly one defect."""
    base = {
        "dataset_id": dataset_id,
        "layer": "L1",
        "status": "PRODUCED",
        "owner": "macro-dashboard",
        "producer": "collectors/example.py",
        "storage": "data/example/{ticker}.parquet",
        "format": "parquet",
        "grain": ["ticker", "date"],
        "temporal_profile": "BARS",
        "version": "1.0.0",
    }
    base.update(overrides)
    return DatasetContract.from_mapping(base)


# ── the real, committed registry ─────────────────────────────────────────────
def test_the_registry_path_is_resolved_against_the_repo_not_the_cwd() -> None:
    """The nightly, the CI packs and a developer shell all run from different
    directories; a cwd-relative default is a config file that silently is not there."""
    assert REGISTRY_PATH == ROOT / "config" / "dataset_registry.yml"
    assert REGISTRY_PATH.is_file()


def test_the_committed_registry_loads_and_has_no_violations() -> None:
    violations = validate_registry(load_registry())
    assert violations == [], "\n".join(violations)


def test_the_committed_registry_retains_the_ten_seeded_datasets() -> None:
    """The original ten remain present as later programs add lawful contracts.

    V4-D2B1-R1 added ``reference.security_migrations`` beside the issuer-migration
    plane. B1's six additions have their own exact field assertions in
    ``test_us_candidate_episode_wiring.py``; this seed fence must not freeze the
    global registry cardinality forever.
    """
    registry = load_registry()
    assert {
        "equity.bars.daily.stocks",
        "equity.bars.daily.yahoo",
        "equity.bars.daily.massive",
        "macro.fred.observations",
        "macro.fred.vintages",
        "reference.security_master",
        "reference.vendor_aliases",
        "reference.issuer_master",
        "reference.issuer_migrations",
        "reference.security_migrations",
    } <= set(registry.ids())


def test_nothing_unproduced_is_marked_produced() -> None:
    """The honesty rule: a row claiming a store that does not exist is a trap.

    The two identity rows were PROPOSED for exactly one day (DOS-1.0) and were promoted
    by DOS-1.1, which shipped the producer and committed the artifacts.  A promotion is
    only honest if the row names a REAL producer and a REAL path, so this pins the
    strings; the on-disk half of gate G1 — the path exists, the producer file exists —
    is asserted by ``tests/test_dataos_security_master.py``, which runs in a lane that
    has ``data/``.  It deliberately does NOT live here: every suite in the
    ``dataos-foundation`` job is a pure unit test that never opens ``data/``, so it
    behaves identically on a full checkout and in that thin lane.
    """
    registry = load_registry()
    for dataset_id in ("reference.security_master", "reference.vendor_aliases"):
        contract = registry.get(dataset_id)
        assert contract.status is DatasetStatus.PRODUCED
        assert contract.producer == "scripts/build_security_master.py"
        assert contract.storage.startswith("data/reference/")
        assert contract.storage.endswith(".parquet")
    for dataset_id in ("equity.bars.daily.stocks", "macro.fred.vintages"):
        assert registry.get(dataset_id).status is DatasetStatus.PRODUCED


def test_every_enum_valued_field_in_the_real_registry_coerced_to_an_enum() -> None:
    for c in load_registry().all():
        assert isinstance(c.layer, Layer), c.dataset_id
        assert isinstance(c.status, DatasetStatus), c.dataset_id
        assert isinstance(c.temporal_profile, TemporalProfile), c.dataset_id
        assert isinstance(c.conflict_policy, ConflictPolicy), c.dataset_id


def test_the_measured_price_bases_reach_the_registry_schema() -> None:
    """§D4's measurement is only useful if a reader can find it without grepping."""
    registry = load_registry()
    assert registry.get("equity.bars.daily.stocks").schema["close"]["basis"] == "tradj"
    assert registry.get("equity.bars.daily.yahoo").schema["close"]["basis"] == "tradj"
    assert registry.get("equity.bars.daily.yahoo").schema["close_price"]["basis"] == "sadj"
    assert registry.get("equity.bars.daily.massive").schema["close"]["basis"] == "raw"


def test_every_ambiguous_price_column_declares_the_canonical_name_it_renames_to() -> None:
    """The V1 migration in one invariant: 132 files keep reading `close`, and the
    basis stops being a guess.

    Scoped to the PRICE stores on purpose — §D4's law is the price naming law.
    ``macro.fred.observations`` also stores a column called ``value``, which is
    ambiguous in the unit sense but has no adjustment basis to declare, and demanding
    a `basis:` there would be a fabricated fact.
    """
    registry = load_registry()
    price_datasets = [c for c in registry.all() if c.dataset_id.startswith("equity.bars.")]
    assert price_datasets, "the price stores are what this invariant is about"
    checked = 0
    for c in price_datasets:
        for column, spec in c.schema.items():
            if not is_ambiguous(column):
                continue
            assert spec.get("basis"), f"{c.dataset_id}:{column} has no measured basis"
            assert spec.get("renames_to"), f"{c.dataset_id}:{column} has no canonical name"
            assert spec["renames_to"] == f"{column.split('_')[0]}_{spec['basis']}"
            checked += 1
    assert checked == 4, "the four measured NVDA columns of §D4"


def test_the_real_dag_edges_and_reverse_edges_agree() -> None:
    """The one real edge in the seed: the alias table joins on the security master."""
    registry = load_registry()
    assert ("reference.security_master", "reference.vendor_aliases") in registry.dag()
    assert registry.inputs_of("reference.vendor_aliases") == ("reference.security_master",)
    # V4-D2B1 (2026-08-19) added two more consumers of the same producer's other
    # outputs — reference.issuer_master and reference.issuer_migrations both declare
    # inputs: [reference.security_master] alongside reference.vendor_aliases.
    # V4-D2B1-R1 (2026-08-20) added a THIRD — reference.security_migrations, the
    # security-axis mirror of reference.issuer_migrations.
    assert {
        "reference.vendor_aliases", "reference.issuer_master", "reference.issuer_migrations",
        "reference.security_migrations",
    } <= set(registry.consumers_of("reference.security_master"))
    assert registry.consumers_of("equity.bars.daily.stocks") == ()


def test_the_two_fred_stores_are_siblings_and_declare_no_edge_between_them() -> None:
    """A FALSE lineage edge is worse than a missing one, and this one shipped.

    ``macro.fred.vintages`` used to declare ``inputs: [macro.fred.observations]``. It
    does not read it: ``collectors/fred.py::_vintage_series`` takes its series list
    from ``config.yml`` / ``DEFAULT_VINTAGE_SERIES``, and ``_fetch_vintage_one``
    calls the ALFRED realtime endpoint directly. The two are L1 SIBLINGS off one
    vendor API with no producer/consumer relationship at all.

    What the false edge would have cost: a lineage query asks
    ``consumers_of('macro.fred.observations')``, gets the vintage store, and an
    operator chasing a bad row in ``data/fred/CPIAUCSL.parquet`` concludes the
    point-in-time store is contaminated — it never touched that file. The reverse is
    worse: a rebuild plan orders observations before vintages and reports the vintage
    refresh as "covered" by a backfill that did nothing for it.
    """
    registry = load_registry()
    assert registry.inputs_of("macro.fred.vintages") == ()
    assert registry.consumers_of("macro.fred.observations") == ()
    assert ("macro.fred.observations", "macro.fred.vintages") not in registry.dag()


def test_no_contract_declares_a_code_path_where_a_dataset_id_belongs() -> None:
    """``inputs`` is the DAG; a function path in it is not an edge, it is a lie.

    ``validate_registry`` already rejects an unknown ``inputs`` reference, so the
    only way a ``collectors/fred.py::as_of_series``-shaped value survives is in a
    field that is NOT the graph — which is why code-level readers are declared under
    ``code_consumers`` and never under ``inputs``/``consumers``.
    """
    for c in load_registry().all():
        for src in c.inputs:
            assert "::" not in src and "/" not in src, f"{c.dataset_id}: inputs {src!r}"


def test_code_consumers_and_the_graph_reverse_edge_are_two_different_notions() -> None:
    """One field, two meanings, is how a lineage answer becomes untrustworthy.

    ``consumers_of()`` returns DATASET_IDS derived from the ``inputs`` graph — a
    fact, not a hand-maintained list. The functions that READ a store are a different
    thing entirely and live in ``code_consumers``. They were both called "consumers"
    once, and a caller could not tell which answer it was holding.
    """
    registry = load_registry()
    vintages = registry.get("macro.fred.vintages")
    assert vintages.code_consumers == (
        "collectors/fred.py::as_of_series",
        "collectors/fred.py::initial_release",
    )
    assert registry.consumers_of("macro.fred.vintages") == ()


def test_get_returns_none_for_an_unknown_id_rather_than_raising() -> None:
    assert load_registry().get("no.such.dataset") is None


# ── loader failure modes ─────────────────────────────────────────────────────
def test_a_missing_registry_file_raises_with_the_path(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="not found"):
        load_registry(tmp_path / "nope.yml")


def test_a_registry_without_a_datasets_key_raises(tmp_path: Path) -> None:
    path = tmp_path / "registry.yml"
    path.write_text("schema: dataset_registry.v1\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="no `datasets:` key"):
        load_registry(path)


def test_a_datasets_key_that_is_not_a_list_raises(tmp_path: Path) -> None:
    path = tmp_path / "registry.yml"
    path.write_text("datasets:\n  a: 1\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="must be a list"):
        load_registry(path)


def test_a_round_trip_through_yaml_preserves_the_contract(tmp_path: Path) -> None:
    path = tmp_path / "registry.yml"
    path.write_text(
        "datasets:\n"
        "  - dataset_id: a.b.c\n"
        "    layer: L2\n"
        "    status: PROPOSED\n"
        "    owner: me\n"
        "    producer: none\n"
        "    storage: data/x\n"
        "    format: parquet\n"
        "    grain: [id]\n"
        "    temporal_profile: SNAPSHOT_SERIES\n"
        "    version: \"0.1.0\"\n"
        "    identity: {id_column: security_id, id_type: SEC}\n"
        "    freshness_sla_hours: 26\n"
        "    schema:\n"
        "      close_tradj: {dtype: float64}\n",
        encoding="utf-8",
    )
    c = load_registry(path).get("a.b.c")
    assert c.layer is Layer.L2_CANONICAL
    assert c.temporal_profile is TemporalProfile.SNAPSHOT_SERIES
    assert c.id_column == "security_id" and c.id_type == "SEC"
    assert c.freshness_sla_hours == 26.0
    assert c.grain == ("id",)
    assert validate_registry(load_registry(path)) == []


# ── each violation class, proved detectable ──────────────────────────────────
def test_a_cyclic_input_graph_is_reported_as_a_cycle() -> None:
    """The synthetic registry the spec asks for: A -> B -> C -> A."""
    cyclic = Registry([
        contract("a", inputs=["c"]),
        contract("b", inputs=["a"]),
        contract("c", inputs=["b"]),
    ])
    violations = validate_registry(cyclic)
    cycles = [v for v in violations if v.startswith("cycle in dependency DAG")]
    assert len(cycles) == 1, violations
    assert {"a", "b", "c"} <= set(cycles[0].replace("->", " ").split())


def test_a_self_edge_is_a_cycle_too() -> None:
    violations = validate_registry(Registry([contract("a", inputs=["a"])]))
    assert any(v.startswith("cycle in dependency DAG") for v in violations)


def test_an_acyclic_diamond_is_not_reported_as_a_cycle() -> None:
    """A shared upstream is normal lineage, not a loop — the guard must not cry wolf."""
    diamond = Registry([
        contract("src"),
        contract("left", inputs=["src"]),
        contract("right", inputs=["src"]),
        contract("sink", inputs=["left", "right"]),
    ])
    assert validate_registry(diamond) == []


def test_an_unknown_input_dataset_id_is_reported() -> None:
    violations = validate_registry(Registry([contract("a", inputs=["ghost.dataset"])]))
    assert any("ghost.dataset" in v and "not a dataset_id" in v for v in violations)


def test_a_duplicate_dataset_id_is_reported_even_though_the_index_hides_it() -> None:
    violations = validate_registry(Registry([contract("a"), contract("a")]))
    assert any(v.startswith("duplicate dataset_id") for v in violations)


@pytest.mark.parametrize("missing", ["owner", "producer", "storage", "format", "version"])
def test_a_missing_required_field_is_reported_by_name(missing: str) -> None:
    violations = validate_registry(Registry([contract("a", **{missing: ""})]))
    assert any(f"missing required field {missing!r}" in v for v in violations)


def test_an_empty_grain_is_a_missing_required_field() -> None:
    violations = validate_registry(Registry([contract("a", grain=[])]))
    assert any("missing required field 'grain'" in v for v in violations)


def test_a_temporal_profile_outside_the_enum_is_reported_not_raised() -> None:
    """Reported rather than exploding at load: one bad row must not take the whole
    catalog down with it."""
    c = contract("a", temporal_profile="WHENEVER")
    assert c.temporal_profile == "WHENEVER"
    violations = validate_registry(Registry([c]))
    assert any("temporal_profile" in v and "WHENEVER" in v for v in violations)


@pytest.mark.parametrize(
    "field, value, needle",
    [("layer", "L9", "layer"),
     ("status", "MAYBE", "status"),
     ("conflict_policy", "WHATEVER", "conflict_policy")],
)
def test_other_closed_vocabularies_are_reported_too(field, value, needle) -> None:
    violations = validate_registry(Registry([contract("a", **{field: value})]))
    assert any(needle in v and value in v for v in violations)


def test_an_ambiguous_price_column_on_an_l2_dataset_is_reported() -> None:
    """§D4's naming law binds at the CANONICAL layer."""
    violations = validate_registry(Registry([
        contract("a", layer="L2", schema={"close": {"dtype": "float64"}}),
    ]))
    assert any("ambiguous price name" in v for v in violations)


def test_the_same_ambiguous_column_is_tolerated_on_an_l1_vendor_shaped_store() -> None:
    """L1 is vendor-shaped by definition — ``data/yahoo`` really does store `close`.
    Flagging it there would make the guard unfixable and therefore ignored."""
    assert validate_registry(Registry([
        contract("a", layer="L1", schema={"close": {"dtype": "float64"}}),
    ])) == []


def test_a_canonical_column_on_an_l2_dataset_is_clean() -> None:
    assert validate_registry(Registry([
        contract("a", layer="L2", schema={"close_tradj": {"dtype": "float64"}}),
    ])) == []


def test_validate_registry_returns_and_never_exits() -> None:
    """Severity is the caller's decision; a validator that calls sys.exit is unusable
    to both a test and a catalog builder."""
    out = validate_registry(Registry([contract("a", owner="")]))
    assert isinstance(out, list) and all(isinstance(v, str) for v in out)


def test_china_gold_source_contracts_are_produced_after_live_acceptance() -> None:
    """The stable source-plane ids are PRODUCED only after real stores + live path proof.

    The 2026-09-20 protected-main backfill landed both parquet stores, and the
    exact-main source -> engine -> render/machine audit made the bounded Data OS
    promotion eligible before these statuses changed.
    """
    registry = load_registry()
    sge = registry.get("commodity.gold.sge_au9999.close")
    global_ref = registry.get("commodity.gold.xaucny.close_ref")

    assert sge is not None
    assert global_ref is not None
    for item in (sge, global_ref):
        assert item.status is DatasetStatus.PRODUCED
        assert item.owner == "macro-dashboard"
        assert item.producer == "collectors/china_gold_basis.py::ChinaGoldBasisAdapter"
        assert item.storage.startswith("data/gold_china_basis/")
        assert item.storage.endswith(".parquet")
        assert item.temporal_profile is TemporalProfile.SNAPSHOT_SERIES
        assert item.conflict_policy is ConflictPolicy.PRIMARY_ONLY
        assert item.code_consumers == ("engine/china_gold_premium.py",)
        assert "PRODUCED 2026-09-20" in item.notes

    assert sge.schema["rmb_per_g"]["unit"] == "CNY_per_gram"
    assert global_ref.schema["cny_per_oz"]["unit"] == "CNY_per_troy_ounce"


# BEA GVC byte staging is Data OS preparation, not source admission.
# Keep its synthetic tests in this incumbent code-gated Data OS suite so an
# unrun stand-alone test or a new CI control plane cannot hide a regression.
from dataclasses import replace as _bea_replace
import json as _bea_json
from lib.dataos import bea_gvc_staging as _bea_stage

_BEA_STAGE_GEN = "a" * 64


def _bea_staging_receipt(**changes):
    base = _bea_stage.BEAGVCStageReceipt(
        source_generation_id=_BEA_STAGE_GEN,
        candidate_manifest_sha256="b" * 64,
        candidate_index_sha256="c" * 64,
        relative_directory="candidate-" + _BEA_STAGE_GEN,
        source_response_count=72, source_file_count=72,
        capture_receipt_count=4, industry_count=138,
        total_industry_rows=138 * 139 * 8,
    )
    return _bea_replace(base, **changes)


def test_bea_stage_roundtrip_is_explicitly_unadmitted(tmp_path):
    root = tmp_path.resolve()
    payload = {
        "candidate_index.json": b'{"synthetic":true}',
        "original_responses/Use/" + "b" * 64 + ".json": b'{"fake":true}',
        "industry_inputs/industry_5241X.jsonl": b'{"row":"synthetic"}\n',
    }
    result = _bea_stage._stage_verified_bytes(
        root, generation=_BEA_STAGE_GEN, files=payload,
        receipt=_bea_staging_receipt())
    stage = root / result.relative_directory
    assert stage.is_dir()
    for path, value in payload.items():
        assert (stage / path).read_bytes() == value
    assert _bea_json.loads((stage / "stage_receipt.json").read_bytes()) == result.as_dict()
    assert result.state == "STAGED_NOT_INSTALLED"
    assert all(result.as_dict()[field] is False for field in (
        "dataos_native_admitted", "may_publish", "may_rank", "may_trade",
        "historical_pit_eligible"))
    with pytest.raises(_bea_stage.BEAGVCStageRefused, match="already staged"):
        _bea_stage._stage_verified_bytes(
            root, generation=_BEA_STAGE_GEN, files=payload,
            receipt=_bea_staging_receipt())


@pytest.mark.parametrize("path", (
    "../out", "/tmp/out", "a/../../out", "a//b", "./x",
    "a/./b", "a\\b", "a\x00b",
))
def test_bea_stage_rejects_path_escape_before_any_write(tmp_path, path):
    root = tmp_path.resolve()
    with pytest.raises(_bea_stage.BEAGVCStageRefused):
        _bea_stage._stage_verified_bytes(
            root, generation=_BEA_STAGE_GEN, files={path: b"fake"},
            receipt=_bea_staging_receipt())
    assert not tuple(root.iterdir())


@pytest.mark.parametrize("changes", (
    {"may_publish": True}, {"dataos_native_admitted": True},
    {"may_rank": True}, {"may_trade": True},
    {"historical_pit_eligible": True}, {"state": "PRODUCED"},
    {"source_generation_id": "d" * 64},
    {"relative_directory": "candidate-somewhere-else"},
))
def test_bea_stage_refuses_all_authority_and_identity_escalations(tmp_path, changes):
    root = tmp_path.resolve()
    with pytest.raises(_bea_stage.BEAGVCStageRefused):
        _bea_stage._stage_verified_bytes(
            root, generation=_BEA_STAGE_GEN,
            files={"synthetic.txt": b"fake"},
            receipt=_bea_staging_receipt(**changes))
    assert not tuple(root.iterdir())


def test_bea_stage_failed_write_rolls_back_partial_directory(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    original = _bea_stage._write_exact
    attempted = []

    def fail_second(base, name, data):
        attempted.append(name)
        if len(attempted) == 2:
            raise OSError("synthetic interrupted stage")
        return original(base, name, data)

    monkeypatch.setattr(_bea_stage, "_write_exact", fail_second)
    with pytest.raises(OSError, match="synthetic interrupted stage"):
        _bea_stage._stage_verified_bytes(
            root, generation=_BEA_STAGE_GEN,
            files={"a.txt": b"a", "b.txt": b"b"},
            receipt=_bea_staging_receipt())
    assert not tuple(root.iterdir())


def test_bea_stage_symlink_root_and_unbound_source_refuse(tmp_path):
    root = tmp_path.resolve()
    actual = root / "actual"
    actual.mkdir()
    alias = root / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(_bea_stage.BEAGVCStageRefused):
        _bea_stage._stage_verified_bytes(
            alias, generation=_BEA_STAGE_GEN,
            files={"a": b"fake"}, receipt=_bea_staging_receipt())
    with pytest.raises(_bea_stage.BEAGVCStageRefused):
        _bea_stage.stage_native_bea_gvc_candidate(
            {"not": "a native candidate"}, root=actual,
            expected_manifest_sha256="b" * 64,
            expected_index_sha256="c" * 64)
    assert not tuple(actual.iterdir())

def test_bea_stage_stays_owner_only_under_permissive_umask(tmp_path):
    import stat
    import os
    root = tmp_path.resolve()
    previous = os.umask(0)
    try:
        output = _bea_stage._stage_verified_bytes(
            root, generation=_BEA_STAGE_GEN,
            files={
                "nested/synthetic.json": b'{"synthetic":true}',
                "candidate_manifest.json": b"synthetic",
            }, receipt=_bea_staging_receipt())
    finally:
        os.umask(previous)
    stage = root / output.relative_directory
    assert stat.S_IMODE(stage.stat().st_mode) == 0o700
    for path in stage.rglob("*"):
        if path.is_file():
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
        elif path.is_dir():
            assert stat.S_IMODE(path.stat().st_mode) == 0o700


def test_bea_stage_syncs_all_directories_before_return(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    original_sync = _bea_stage._fsync_directory
    synced = []

    def record_sync(path):
        synced.append(path)
        return original_sync(path)

    monkeypatch.setattr(_bea_stage, "_fsync_directory", record_sync)
    result = _bea_stage._stage_verified_bytes(
        root, generation=_BEA_STAGE_GEN,
        files={"nested/a.json": b"a"}, receipt=_bea_staging_receipt())
    assert synced[-1] == root
    assert any("nested" in path.parts for path in synced[:-1])
    assert (root / result.relative_directory / "nested/a.json").read_bytes() == b"a"


def test_bea_stage_post_rename_sync_uncertain_effect_cannot_blind_retry(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    original_sync = _bea_stage._fsync_directory

    def fail_after_visible_rename(path):
        if path == root:
            raise OSError("synthetic directory durability interruption")
        return original_sync(path)

    monkeypatch.setattr(_bea_stage, "_fsync_directory", fail_after_visible_rename)
    with pytest.raises(OSError, match="synthetic directory durability interruption"):
        _bea_stage._stage_verified_bytes(
            root, generation=_BEA_STAGE_GEN,
            files={"candidate_manifest.json": b"synthetic"},
            receipt=_bea_staging_receipt())
    observed = root / ("candidate-" + _BEA_STAGE_GEN)
    assert (observed / "candidate_manifest.json").read_bytes() == b"synthetic"
    with pytest.raises(_bea_stage.BEAGVCStageRefused, match="already staged"):
        _bea_stage._stage_verified_bytes(
            root, generation=_BEA_STAGE_GEN,
            files={"candidate_manifest.json": b"synthetic"},
            receipt=_bea_staging_receipt())


def test_bea_stage_optional_source_import_only_at_invocation(tmp_path, monkeypatch):
    calls = []

    def missing_source(name):
        calls.append(name)
        raise ModuleNotFoundError("synthetic missing native source", name=name)

    monkeypatch.setattr(_bea_stage, "import_module", missing_source)
    with pytest.raises(_bea_stage.BEAGVCStageRefused, match="producer unavailable"):
        _bea_stage.stage_native_bea_gvc_candidate(
            object(), root=tmp_path.resolve(),
            expected_manifest_sha256="b" * 64,
            expected_index_sha256="c" * 64)
    assert calls == ["collectors.bea_gvc_native"]
    assert not tuple(tmp_path.iterdir())


def test_bea_stage_nested_source_import_failure_is_not_hidden(tmp_path, monkeypatch):
    def missing_transitive(name):
        raise ModuleNotFoundError("synthetic transitive failure", name="missing_dependency")

    monkeypatch.setattr(_bea_stage, "import_module", missing_transitive)
    with pytest.raises(ModuleNotFoundError, match="synthetic transitive failure"):
        _bea_stage.stage_native_bea_gvc_candidate(
            object(), root=tmp_path.resolve(),
            expected_manifest_sha256="b" * 64,
            expected_index_sha256="c" * 64)
    assert not tuple(tmp_path.iterdir())



# Unadmitted BEA byte-readback contract; never a new Data OS source reader.
def _synthetic_bea_full_stage(tmp_path, *, correction_revision=0):
    """Synthetic full 72x138 index. NO original BEA source is involved."""
    import hashlib
    import json
    from lib.dataos import bea_gvc_staging as bea

    def encoded(obj):
        return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")

    def digest(blob):
        return hashlib.sha256(blob).hexdigest()

    years = list(range(2017, 2025))
    tables = (
        "Use", "ImMatAll", "ImMatCan", "ImMatChi", "ImMatEur",
        "ImMatJap", "ImMatMex", "ImMatRoa", "ImMatRow",
    )
    lineage_bytes = encoded({"synthetic": True, "years": years})
    lineage_sha = digest(lineage_bytes)
    producer_sha = "4" * 64
    source = []
    files = {"source_lineage.json": lineage_bytes}
    capture = {}
    for year in years:
        for group in range(3):
            body = encoded({"synthetic": "capture", "year": year, "group": group})
            capture[year, group] = digest(body)
            files["capture_receipts/" + capture[year, group] + ".json"] = body
        for i, table in enumerate(tables):
            body = encoded({"synthetic": "original", "year": year, "table": table})
            sha = digest(body)
            source.append({
                "accounting_year": year, "source_table_id": table,
                "original_response_sha256": sha, "original_response_bytes": len(body),
                "capture_receipt_sha256": capture[year, i % 3],
                "research_source_capture_completed_at": "2026-10-19T00:00:00+00:00",
            })
            files[f"original_responses/{table}/{sha}.json"] = body
    manifest = {
        "schema": "mastermind.bea_gvc_source_candidate/v1",
        "l0_dataset_id": "bea.gvc.may2026.original_responses",
        "l1_dataset_id": "bea.gvc.may2026.industry_import_inputs",
        "candidate_state": "BYTE_VERIFIED_NOT_INSTALLED",
        "accounting_years": years, "source_response_count": 72,
        "expected_l1_rows": 138 * 139 * 8,
        "complete_2017_2024_panel": True,
        "publisher_edition_date": "2026-05-21",
        "publication_precision": "DAY",
        "source_lineage_sha256": lineage_sha,
        "producer_code_sha256": producer_sha,
        "candidate_revision_seq": correction_revision,
        "supersedes_candidate_generation":
            ("1" * 64 if correction_revision else None),
        "native_ingested_at": None, "native_revision_seq": None,
        "native_known_at": None, "published_at": None,
        "original_historical_available_at": None,
        "dataos_native_admitted": False, "may_publish": False,
        "may_rank": False, "may_trade": False, "may_train": False,
        "historical_pit_eligible": False, "named_company_relationship": False,
        "sources": source,
    }
    manifest_bytes = encoded(manifest)
    gen = digest(manifest_bytes)
    files["candidate_manifest.json"] = manifest_bytes
    views = []
    for i in range(138):
        code = f"I{i:03d}"
        body = (encoded({"synthetic": "industry", "code": code}) + b"\n") * (139 * 8)
        sha = digest(body)
        files[f"industry_inputs/industry_{code}.jsonl"] = body
        views.append({
            "industry_code_exact": code,
            "relative_storage_path_proposed_only":
                f"data/bea/gvc/may2026/industry_inputs/industry_{code}.jsonl",
            "jsonl_sha256": sha, "jsonl_bytes": len(body), "row_count": 139 * 8,
        })
    index = {
        "schema": "mastermind.bea_gvc_l1_candidate_index/v1",
        "dataset_id": "bea.gvc.may2026.industry_import_inputs",
        "source_generation_id": gen,
        "candidate_state": "BYTE_VERIFIED_NOT_INSTALLED",
        "source_lineage_sha256": lineage_sha, "producer_code_sha256": producer_sha,
        "accounting_years": years, "source_response_count": 72,
        "industry_count": 138, "row_count": 138 * 139 * 8,
        "publisher_edition_date": "2026-05-21",
        "publication_precision": "DAY",
        "native_ingested_at": None, "native_revision_seq": None,
        "dataos_native_admitted": False, "may_publish": False,
        "views": views,
    }
    index_bytes = encoded(index)
    files["candidate_index.json"] = index_bytes
    index_sha = digest(index_bytes)
    receipt = bea.BEAGVCStageReceipt(
        source_generation_id=gen,
        candidate_manifest_sha256=gen,
        candidate_index_sha256=index_sha,
        relative_directory="candidate-" + gen,
        source_response_count=72, source_file_count=72,
        capture_receipt_count=24, industry_count=138,
        total_industry_rows=138 * 139 * 8)
    bea._stage_verified_bytes(tmp_path.resolve(), generation=gen, files=files,
                              receipt=receipt)
    return {
        "kwargs": {
            "root": tmp_path.resolve(),
            "source_generation_id": gen,
            "expected_manifest_sha256": gen,
            "expected_index_sha256": index_sha,
        },
        "directory": tmp_path.resolve() / receipt.relative_directory,
        "files": files,
        "receipt": receipt,
    }


@pytest.mark.parametrize("revision", [0, 1])
def test_bea_stage_readback_full_synthetic_generation_and_correction(tmp_path, revision):
    from lib.dataos import bea_gvc_staging as bea
    staged = _synthetic_bea_full_stage(tmp_path, correction_revision=revision)
    actual = bea.verify_unadmitted_bea_gvc_stage(**staged["kwargs"])
    assert actual == staged["receipt"]
    assert actual.state == "STAGED_NOT_INSTALLED"
    assert actual.industry_count == 138 and actual.total_industry_rows == 153456
    assert not (actual.dataos_native_admitted or actual.may_publish or actual.may_trade)
    assert len([p for p in staged["directory"].rglob("*.jsonl")]) == 138


@pytest.mark.parametrize("kind", (
    "original", "industry", "capture", "lineage", "manifest", "index", "receipt",
    "missing", "extra", "link", "mode", "forged_authority",
))
def test_bea_stage_readback_rejects_modified_or_untrusted_bytes(tmp_path, kind):
    import json
    import os
    from lib.dataos import bea_gvc_staging as bea
    staged = _synthetic_bea_full_stage(tmp_path)
    directory = staged["directory"]
    files = staged["files"]
    name = (
        next(p for p in files if p.startswith("original_responses/"))
        if kind == "original" else
        next(p for p in files if p.startswith("industry_inputs/"))
        if kind == "industry" else
        next(p for p in files if p.startswith("capture_receipts/"))
        if kind == "capture" else
        {"lineage": "source_lineage.json", "manifest": "candidate_manifest.json",
         "index": "candidate_index.json", "receipt": "stage_receipt.json"}.get(kind))
    if name is not None:
        (directory / name).write_bytes((directory / name).read_bytes() + b" ")
    elif kind == "missing":
        (directory / "candidate_index.json").unlink()
    elif kind == "extra":
        (directory / "unexpected_extra_file").write_bytes(b"extra")
    elif kind == "link":
        target = tmp_path / "outside"
        target.write_bytes(b"outside")
        (directory / "extra_symlink").symlink_to(target)
    elif kind == "mode":
        os.chmod(directory / "candidate_index.json", 0o644)
    elif kind == "forged_authority":
        path = directory / "stage_receipt.json"
        doc = json.loads(path.read_bytes())
        doc["may_publish"] = True
        path.write_bytes(bea._canonical(doc))
    with pytest.raises(bea.BEAGVCStageRefused):
        bea.verify_unadmitted_bea_gvc_stage(**staged["kwargs"])


def test_bea_stage_readback_refuses_caller_pin_and_missing_generation(tmp_path):
    from lib.dataos import bea_gvc_staging as bea
    staged = _synthetic_bea_full_stage(tmp_path)
    wrong = dict(staged["kwargs"])
    wrong["expected_index_sha256"] = "f" * 64
    with pytest.raises(bea.BEAGVCStageRefused):
        bea.verify_unadmitted_bea_gvc_stage(**wrong)
    wrong = dict(staged["kwargs"])
    wrong["source_generation_id"] = "e" * 64
    with pytest.raises(bea.BEAGVCStageRefused):
        bea.verify_unadmitted_bea_gvc_stage(**wrong)
    assert bea.verify_unadmitted_bea_gvc_stage(**staged["kwargs"]) == staged["receipt"]


def test_bea_stage_readback_rejects_forged_row_count_with_matching_digests(tmp_path):
    """A consistent forged index digest must not make one row into 1,112."""
    import hashlib
    import json
    from lib.dataos import bea_gvc_staging as bea
    staged = _synthetic_bea_full_stage(tmp_path)
    root = staged["directory"]
    victim = root / "industry_inputs/industry_I000.jsonl"
    victim.write_bytes(b'{"synthetic":"one row"}\n')
    index_file = root / "candidate_index.json"
    index = json.loads(index_file.read_bytes())
    view = index["views"][0]
    assert view["industry_code_exact"] == "I000"
    view["jsonl_sha256"] = hashlib.sha256(victim.read_bytes()).hexdigest()
    view["jsonl_bytes"] = len(victim.read_bytes())
    index_raw = bea._canonical(index)
    index_file.write_bytes(index_raw)
    pin = hashlib.sha256(index_raw).hexdigest()
    receipt_file = root / "stage_receipt.json"
    receipt = json.loads(receipt_file.read_bytes())
    receipt["candidate_index_sha256"] = pin
    receipt_file.write_bytes(bea._canonical(receipt))
    kwargs = dict(staged["kwargs"])
    kwargs["expected_index_sha256"] = pin
    with pytest.raises(bea.BEAGVCStageRefused, match="row count"):
        bea.verify_unadmitted_bea_gvc_stage(**kwargs)


def test_bea_stage_intermediate_parents_remain_private_with_umask_022(tmp_path):
    """Linux mkdir(parents=True) must not create 0755 intermediate parents."""
    import os
    import stat
    from lib.dataos import bea_gvc_staging as bea
    root = tmp_path.resolve()
    old = os.umask(0o022)
    try:
        receipt = bea._stage_verified_bytes(
            root, generation=_BEA_STAGE_GEN,
            files={"original_responses/Use/synthetic.json": b'{"fake":true}'},
            receipt=_bea_staging_receipt())
    finally:
        os.umask(old)
    final = root / receipt.relative_directory
    for dirname in (final, final / "original_responses",
                    final / "original_responses/Use"):
        assert stat.S_IMODE(dirname.stat().st_mode) == 0o700
    assert bea._stage_stat.S_IMODE(
        (final / "original_responses/Use/synthetic.json").stat().st_mode
    ) == 0o600


def test_bea_stage_readback_fifo_metadata_fails_without_blocking(tmp_path, monkeypatch):
    """A FIFO at the first metadata read must refuse, never hang CI."""
    import os
    from lib.dataos import bea_gvc_staging as bea
    staged = _synthetic_bea_full_stage(tmp_path)
    fifo = staged["directory"] / "stage_receipt.json"
    fifo.unlink()
    os.mkfifo(fifo, 0o600)
    original_open = os.open
    observed_leaf_open = []

    def guarded_open(path, flags, *args, **kwargs):
        if path == "stage_receipt.json":
            # This assertion ensures the test itself cannot hang if a future
            # change accidentally drops O_NONBLOCK from the metadata open.
            assert flags & os.O_NONBLOCK, "metadata FIFO open must be nonblocking"
            observed_leaf_open.append(True)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(bea.os, "open", guarded_open)
    with pytest.raises(bea.BEAGVCStageRefused, match="unsafe shape"):
        bea.verify_unadmitted_bea_gvc_stage(**staged["kwargs"])
    assert observed_leaf_open
