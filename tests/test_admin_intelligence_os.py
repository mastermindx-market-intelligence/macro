"""tests/test_admin_intelligence_os.py — the Intelligence OS admin surface.

FIXTURE ROOTS ONLY, same law as the T4 suite this joins: nothing here reads the live
``config/synapse.yml`` or asserts anything about the live estate's health. The registry
took 69 commits in a trailing fortnight and "an artifact is stale tonight" is operational
data, not a PR defect — either would turn this lane into a nightly alarm about work the
operator has not done yet.

THE LOAD-BEARING TEST IS :func:`test_reflectivity_a_new_engine_appears_with_no_code_edit`.
The panel is only worth having if the estate is its source: an engine added to the
registry must show up with no edit here, and one removed must disappear. A page that has
to be taught about each engine is a second registry wearing a dashboard's clothes, and it
goes wrong exactly when it matters — quietly, at the moment the estate changes.
"""
from __future__ import annotations

import ast
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from admin import intelligence_os as IOS  # noqa: E402

# Wall-clock relative: panel() uses datetime.now(), so a frozen 2026-08-14
# asof ages out of the 24h SLA the next calendar day and this suite becomes a
# nightly alarm. Keep FRESH 6h behind now, matching the T4 suite contract.
FRESH = (datetime.now(timezone.utc) - timedelta(hours=6)).strftime(
    "%Y-%m-%dT%H:%M:%S+00:00"
)


# ---------------------------------------------------------------------------
# Fixture builders — adapted from tests/test_output_health.py
# ---------------------------------------------------------------------------

def artifact(
    path: str,
    *,
    producer: str,
    owner: str,
    consumers: tuple[str, ...] = (),
    asof_field: str | None = "asof",
    sla: int | None = 24,
    storage: str = "git",
    fmt: str = "json",
    **extra: object,
) -> dict:
    entry: dict = {
        "path": path,
        "format": fmt,
        "producer": producer,
        "owner_program": owner,
        "cadence": "daily-engine",
        "storage": storage,
        "asof_field": asof_field,
        "freshness_sla_hours": sla,
        "schema": "none",
        "tier": "display",
        "horizon_role": "context",
        "weights": "none",
        "consumers": list(consumers),
    }
    entry.update(extra)
    return entry


def _write_root(tmp_path: Path, artifacts: dict, overlay: dict | None = None) -> Path:
    """A checkout-shaped fixture: config/, the producer modules, the artifacts themselves.

    Deliberately NOT a git repo. Every artifact is materialized on disk, so the presence
    ladder answers from the worktree and the git half is never consulted — which keeps
    this suite off subprocess spawn entirely (the live estate walk costs minutes).
    """
    root = tmp_path / "estate"
    (root / "config").mkdir(parents=True, exist_ok=True)
    doc = {
        "meta": {
            "schema_version": 1,
            "description": "fixture",
            "tier_vocabulary": {},
            "article2_surfaces": [],
        },
        "artifacts": artifacts,
    }
    (root / "config" / "synapse.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    (root / "config" / "intelligence_registry_overlay.yml").write_text(
        yaml.safe_dump(overlay or {"engines": {}}), encoding="utf-8"
    )
    for entry in artifacts.values():
        producer = root / str(entry["producer"])
        producer.parent.mkdir(parents=True, exist_ok=True)
        producer.write_text("", encoding="utf-8")
        target = root / str(entry["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"asof": FRESH}), encoding="utf-8")
    return root


def one_engine(tmp_path: Path, **kw) -> Path:
    return _write_root(
        tmp_path,
        {"a": artifact("data/a.json", producer="engine/a.py", owner="prog-one")},
        **kw,
    )


@pytest.fixture(autouse=True)
def _clean_cache():
    """Every test starts cold. The panel cache is module-level and keyed on mtimes, and
    two tmp_path roots minted in the same nanosecond would otherwise share an entry."""
    IOS._CACHE.clear()
    yield
    IOS._CACHE.clear()


def _tree(root: Path) -> dict[str, tuple[int, int]]:
    """path -> (size, mtime_ns) for every file under *root*."""
    return {
        p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


# ---------------------------------------------------------------------------
# The reflectivity gate
# ---------------------------------------------------------------------------

def test_reflectivity_a_new_engine_appears_with_no_code_edit(tmp_path):
    """Add an engine to the registry -> it is on the page. Remove it -> it is gone.

    BOTH directions, because only one of them is the failure mode people notice. A page
    that never learns about a new engine looks empty and gets investigated; a page that
    keeps rendering a DELETED one looks healthy and does not.
    """
    root = _write_root(
        tmp_path,
        {"a": artifact("data/a.json", producer="engine/a.py", owner="prog-one")},
    )
    before = IOS.panel(root=root)
    assert before["ok"] is True
    ids_before = {r["engine_id"] for r in before["engines"]}
    assert ids_before == {"engine/a.py::prog-one"}
    assert before["census"]["engines"] == 1
    assert before["census"]["artifacts"] == 1

    # --- the estate grows, the module does not ---------------------------
    root = _write_root(
        tmp_path,
        {
            "a": artifact("data/a.json", producer="engine/a.py", owner="prog-one"),
            "z": artifact("data/z.json", producer="engine/z.py", owner="prog-two"),
        },
    )
    after = IOS.panel(root=root, force=True)
    ids_after = {r["engine_id"] for r in after["engines"]}
    assert ids_after == {"engine/a.py::prog-one", "engine/z.py::prog-two"}
    assert after["census"]["engines"] == 2
    assert after["census"]["artifacts"] == 2
    grown = next(r for r in after["engines"] if r["engine_id"] == "engine/z.py::prog-two")
    assert grown["owner_program"] == "prog-two"
    assert grown["producer"] == "engine/z.py"
    assert grown["n_artifacts"] == 1

    # --- and it shrinks again --------------------------------------------
    root = _write_root(
        tmp_path,
        {"a": artifact("data/a.json", producer="engine/a.py", owner="prog-one")},
    )
    shrunk = IOS.panel(root=root, force=True)
    assert {r["engine_id"] for r in shrunk["engines"]} == {"engine/a.py::prog-one"}
    assert shrunk["census"]["engines"] == 1


def test_output_class_is_null_for_an_uncurated_engine(tmp_path):
    """No adjudication in the overlay -> ``None``, never a guess.

    The panel joins T1's overlay and nothing else. Inferring a class from tier, authority
    or the producer's name would turn a census row into an authority claim, which is the
    one thing this surface is not allowed to mint.
    """
    root = one_engine(tmp_path)
    panel = IOS.panel(root=root)
    row = panel["engines"][0]
    assert row["output_class"] is None
    assert panel["census"]["by_output_class"] == {"null": 1}

    detail = IOS.engine_detail("engine/a.py::prog-one", root=root)
    assert detail["ok"] is True
    assert detail["engine"]["output_class"] is None
    assert detail["outputs"][0]["output_class"] is None


def test_a_curated_output_class_is_passed_through_verbatim(tmp_path):
    """The other half of the null test: when the overlay HAS adjudicated a class, the
    panel must show that class and its rationale — otherwise "always None" would pass the
    test above while the join was simply broken."""
    root = _write_root(
        tmp_path,
        {"a": artifact("data/a.json", producer="engine/a.py", owner="prog-one")},
        overlay={
            "engines": {
                "engine/a.py::prog-one": {
                    "output_class": {
                        "value": "state_estimate",
                        "rationale": "fixture adjudication",
                    }
                }
            }
        },
    )
    panel = IOS.panel(root=root)
    assert panel["engines"][0]["output_class"] == "state_estimate"
    detail = IOS.engine_detail("engine/a.py::prog-one", root=root)
    assert detail["engine"]["output_class"] == "state_estimate"
    assert "fixture adjudication" in (detail["engine"]["output_class_rationale"] or "")


# ---------------------------------------------------------------------------
# A1 evidence disposition — pure, deterministic, and owner-bounded
# ---------------------------------------------------------------------------

def evidence_cell(**overrides: object) -> dict:
    """A complete T1-shaped cell for the A1 pure-derivation tests."""
    cell: dict = {
        "engine_id": "engine/a.py::prog-one",
        "producer": "engine/a.py",
        "owner_program": "prog-one",
        "output_class": "predictive",
        "output_class_reason": "curated: fixture",
        "authority": "engine_input",
        "ledger": "data/a/theses.jsonl",
        "ledger_evidence": {
            "rule": 3,
            "desk": None,
            "shape": "store",
            "corpus_checked": False,
            "corpus_rows": None,
        },
        "graded_by_design": "yes",
        "graded_by_design_evidence": "strong",
        "graded_by_design_source": "derived: fixture owner ledger",
        "declared_horizon": {
            "horizon_role": ["context"],
            "horizon_role_homogeneous": True,
            "horizon_d": [21],
        },
        "validation_state": "phase0",
        "validation_state_evidence": {
            "bound_species": [],
            "reason": "no_species_bound",
        },
        "evidence_ref": ["fixture.prereg"],
    }
    cell.update(overrides)
    return cell


def healthy_output(**overrides: object) -> dict:
    output: dict = {
        "artifact_id": "a",
        "state": "healthy",
        "assessment_status": "complete",
        "reason_codes": [],
    }
    output.update(overrides)
    return output


def qledger_provider(**row_overrides: object) -> dict:
    row: dict = {
        "n_dates": 7,
        "needed": 25,
        "ready": False,
        "approaching": False,
        "projected_ready_date": "2026-09-30",
        "reason": "7 independent dates; evidence still accruing",
        "clock_basis": "explicit_unit_v1:trading_days:US",
        "clock_migration": False,
        "clock_prior_n_dates": {},
        "evidence_basis": "benchmark",
        "control_coverage": None,
        "n_cohort_dates": None,
        "n_controlled_dates": None,
        "cohort_rowless": {},
        "control_clock_start": None,
        "unclassified": False,
    }
    row.update(row_overrides)
    return {
        "kind": "qledger",
        "binding": "direct:qledger:fixture",
        "family": "fixture",
        "read_status": "ok",
        "clock_start": {
            "claim_family": "fixture",
            "first_prospective_registration_utc": "2026-08-20T01:02:03+00:00",
            "declared_horizon_d": 21,
            "horizon_unit": "trading_days",
            "git_sha": "abc123",
        },
        "readiness": {"21": row},
    }


def test_ceo_view_keeps_an_empty_validated_band_visible():
    """Removing empty bands would turn zero validated engines into an invisible omission."""
    view = IOS.build_ceo_view(
        [
            {"engine_id": "engine/z.py::p", "evidence_status": "Accruing"},
            {"engine_id": "engine/a.py::p", "evidence_status": "Accruing"},
        ]
    )

    assert [band["evidence_status"] for band in view] == [
        "Validated",
        "Accruing",
        "Ungraded by design",
        "Degraded",
        "Disproven",
    ]
    assert view[0] == {
        "evidence_status": "Validated",
        "n_engines": 0,
        "engine_ids": [],
    }
    assert view[1]["engine_ids"] == ["engine/a.py::p", "engine/z.py::p"]


def test_null_output_class_stays_null_and_cannot_be_validated():
    """A validated lifecycle may not fill an unknown metric contract with a guessed class."""
    cell = evidence_cell(output_class=None, validation_state="validated")
    result = IOS.derive_evidence_status(cell, [healthy_output()])

    assert cell["output_class"] is None
    assert result["evidence_status"] == "Accruing"
    assert "output_class_null" in result["evidence_reason_codes"]


def test_t1_null_output_class_cannot_be_backfilled_from_a_t4_record():
    """Even contradictory downstream bytes cannot overwrite T1's explicit null contract."""
    cell = evidence_cell(output_class=None, validation_state="validated")
    output = healthy_output(
        engine_id=cell["engine_id"], output_class="predictive", authority="engine_input"
    )

    rows = IOS._engine_rows(
        {"outputs": [output]}, {"engines": [cell], "excluded": []}, {}
    )

    assert rows[0]["output_class"] is None
    assert rows[0]["evidence_status"] == "Accruing"
    assert "output_class_null" in rows[0]["evidence_reason_codes"]


def test_panel_and_detail_keep_a_canonical_t1_cell_with_no_t4_outputs(
    monkeypatch, tmp_path
):
    """Every canonical T1 cell gets a disposition, including an explicit no-output failure."""
    cell = evidence_cell()
    view = {"outputs": [], "summary": {}, "generated": {}}
    registry = {"engines": [cell], "excluded": []}
    monkeypatch.setattr(
        IOS,
        "_derive",
        lambda root, force: (view, registry, {}, 0.0, "miss"),
    )

    panel = IOS.panel(root=tmp_path)
    assert panel["census"]["canonical_engines"] == 1
    assert panel["engines"][0]["engine_id"] == cell["engine_id"]
    assert panel["engines"][0]["evidence_status"] == "Degraded"
    assert "health_no_outputs" in panel["engines"][0]["evidence_reason_codes"]
    assert sum(band["n_engines"] for band in panel["ceo_view"]) == 1

    detail = IOS.engine_detail(cell["engine_id"], root=tmp_path)
    assert detail["ok"] is True
    assert detail["engine"]["evidence_status"] == "Degraded"
    assert detail["outputs"] == []


def test_mixed_explicit_bases_refuse_a_validated_disposition():
    """Two incompatible explicit clocks must not pool into one apparently mature verdict."""
    provider = qledger_provider(
        n_dates=0,
        ready=False,
        clock_basis=None,
        clock_prior_n_dates={
            "explicit_unit_v1:calendar_days:US": 11,
            "explicit_unit_v1:trading_days:US": 14,
        },
        by_clock_basis={
            "explicit_unit_v1:calendar_days:US": {"n_dates": 11, "ready": False},
            "explicit_unit_v1:trading_days:US": {"n_dates": 14, "ready": False},
        },
        reason="two explicit clock bases; refusing to pool",
    )
    result = IOS.derive_evidence_status(
        evidence_cell(validation_state="validated"),
        [healthy_output()],
        provider,
    )

    assert result["evidence_status"] == "Accruing"
    assert "mixed_clock_basis_refused" in result["evidence_reason_codes"]
    assert result["evidence_basis"]["pooling_refused"] is True
    assert sorted(result["evidence_basis"]["available_clock_bases"]) == [
        "explicit_unit_v1:calendar_days:US",
        "explicit_unit_v1:trading_days:US",
    ]


def test_immature_qledger_record_is_accruing_with_its_ruler_and_honest_n():
    """Seven independent dates are not silently rounded up to the 25-date owner floor."""
    result = IOS.derive_evidence_status(
        evidence_cell(),
        [healthy_output()],
        qledger_provider(),
    )

    assert result["evidence_status"] == "Accruing"
    assert "insufficient_maturity" in result["evidence_reason_codes"]
    assert result["evidence_ruler"]["qledger_clock"] == {
        "horizon_d": 21,
        "horizon_unit": "trading_days",
        "clock_market": "US",
    }
    assert result["evidence_maturity"]["rungs"]["21"] == {
        "n_dates": 7,
        "needed": 25,
        "ready": False,
        "approaching": False,
        "projected_ready_date": "2026-09-30",
    }


def test_degraded_health_overrides_an_otherwise_validated_engine():
    """A lifecycle receipt must not paint over an output the current observer cannot trust."""
    result = IOS.derive_evidence_status(
        evidence_cell(validation_state="validated"),
        [healthy_output(state="degraded", assessment_status="partial")],
    )

    assert result["evidence_status"] == "Degraded"
    assert "health_degraded" in result["evidence_reason_codes"]


def test_blind_output_is_degraded_but_remains_distinct_from_a_health_verdict():
    """Could-not-look is reduced trust, not an invented unavailable or stale verdict."""
    result = IOS.derive_evidence_status(
        evidence_cell(validation_state="validated"),
        [healthy_output(state=None, assessment_status="could_not_look")],
    )

    assert result["evidence_status"] == "Degraded"
    assert "health_blind" in result["evidence_reason_codes"]
    assert "health_unavailable" not in result["evidence_reason_codes"]


def test_ungraded_by_design_requires_t1_semantic_evidence():
    """Missing data must not be mislabeled as an intentional descriptive contract."""
    semantic = IOS.derive_evidence_status(
        evidence_cell(
            output_class=None,
            graded_by_design="no — descriptive",
            graded_by_design_evidence="none",
            graded_by_design_source="derived: every artifact is infrastructure",
        ),
        [healthy_output()],
    )
    unsupported = IOS.derive_evidence_status(
        evidence_cell(
            output_class="descriptive",
            graded_by_design="no — not yet",
            graded_by_design_evidence="none",
            graded_by_design_source="derived: no ledger",
        ),
        [healthy_output()],
    )

    assert semantic["evidence_status"] == "Ungraded by design"
    assert "t1_semantic_ungraded" in semantic["evidence_reason_codes"]
    assert unsupported["evidence_status"] == "Accruing"
    assert "t1_semantic_ungraded" not in unsupported["evidence_reason_codes"]


def test_terminal_owner_state_is_disproven_and_keeps_its_evidence():
    """A1 displays the owner's terminal decision; it does not recreate or soften it."""
    result = IOS.derive_evidence_status(
        evidence_cell(
            validation_state="falsified",
            validation_state_evidence={
                "bound_species": [
                    {"species_id": "S-DEAD", "validation_status": "falsified"}
                ],
                "reason": "single_species",
            },
        ),
        [healthy_output(state="degraded", assessment_status="partial")],
    )

    assert result["evidence_status"] == "Disproven"
    assert "owner_terminal_falsified" in result["evidence_reason_codes"]
    assert "species:S-DEAD" in result["evidence_refs"]


def test_validated_requires_the_existing_owner_lifecycle_not_qledger_readiness():
    """Qledger readiness is measurement evidence and cannot mint validation authority."""
    ready_provider = qledger_provider(n_dates=30, needed=25, ready=True)
    still_phase0 = IOS.derive_evidence_status(
        evidence_cell(validation_state="phase0"), [healthy_output()], ready_provider
    )
    owner_validated = IOS.derive_evidence_status(
        evidence_cell(validation_state="validated", output_class="ranking"),
        [healthy_output()],
    )

    assert still_phase0["evidence_status"] == "Accruing"
    assert owner_validated["evidence_status"] == "Accruing"
    assert "owner_validation_scope_unqualified" in owner_validated["evidence_reason_codes"]
    assert owner_validated["evidence_owner_scope"]["owner_lifecycle"] == "validated"
    assert owner_validated["evidence_owner_scope"]["qualified_task_scope"] is None
    assert "evidence_score" not in owner_validated


@pytest.mark.parametrize(
    ("cell", "adapter_families", "expected"),
    [
        (
            evidence_cell(
                ledger="qledger:whitehouse",
                ledger_evidence={"desk": "whitehouse", "rule": 2},
            ),
            ("stock_desk", "thematic_desk", "demand_chain"),
            "whitehouse",
        ),
        (
            evidence_cell(ledger="data/stock_desk/theses.jsonl"),
            ("stock_desk", "thematic_desk", "demand_chain"),
            "stock_desk",
        ),
        (
            evidence_cell(ledger="data/not_stock_desk/theses.jsonl"),
            ("stock_desk", "thematic_desk", "demand_chain"),
            None,
        ),
    ],
)
def test_qledger_family_binding_is_exact_and_derived(cell, adapter_families, expected):
    """A1 may join canonical owner names exactly; fuzzy producer/name routing is illegal."""
    assert IOS.qledger_family_for_cell(cell, adapter_families) == expected


def test_panel_and_detail_expose_one_status_and_all_five_ceo_bands(tmp_path):
    """Dropping the pure result at the API seam would leave A1 built but invisible."""
    root = one_engine(tmp_path)

    panel = IOS.panel(root=root)
    assert panel["census"]["by_evidence_status"] == {"Accruing": 1}
    assert [band["evidence_status"] for band in panel["ceo_view"]] == list(
        IOS.EVIDENCE_STATUS_ORDER
    )
    assert panel["ceo_view"][0]["n_engines"] == 0
    row = panel["engines"][0]
    assert row["output_class"] is None
    assert row["evidence_status"] == "Accruing"
    assert "output_class_null" in row["evidence_reason_codes"]

    detail = IOS.engine_detail("engine/a.py::prog-one", root=root)
    assert detail["engine"]["evidence_status"] == "Accruing"
    assert detail["engine"]["evidence_provider"]["kind"] == "t1_owner_native"
    assert detail["engine"]["declared_horizon"]["horizon_role"] == ["context"]
    assert detail["engine"]["validation_state"] is None
    assert detail["engine"]["validation_state_evidence"] == {
        "bound_species": None,
        "reason": "species_store_absent",
    }


def test_panel_orders_by_evidence_band_then_engine_id(tmp_path):
    """The CEO view orders status strength, never class or headline performance."""
    root = _write_root(
        tmp_path,
        {
            "z": artifact("data/z.json", producer="engine/z.py", owner="prog-z"),
            "a": artifact(
                "data/a.json",
                producer="engine/a.py",
                owner="prog-a",
                tier="infrastructure",
            ),
        },
    )
    rows = IOS.panel(root=root)["engines"]

    assert [(row["evidence_status"], row["engine_id"]) for row in rows] == [
        ("Accruing", "engine/z.py::prog-z"),
        ("Ungraded by design", "engine/a.py::prog-a"),
    ]


def _record_owner_fixture(root: Path, families: list[str]) -> dict:
    from scripts import grade_qledger
    readiness = grade_qledger.compute_promotion_readiness(root, families=families)
    path = root / "site/qledger/track_record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"promotion_readiness": readiness,
                               "promotion_readiness_at": "2026-10-12T20:00:00+00:00"}))
    return readiness


def qledger_adapter_root(tmp_path: Path, *, with_store: bool = True) -> Path:
    root = _write_root(
        tmp_path,
        {
            "stock-ledger": artifact(
                "data/stock_desk/theses.jsonl",
                producer="engine/stock_desk.py",
                owner="qualitative-intelligence",
                tier="shadow",
                fmt="jsonl",
            )
        },
        overlay={
            "engines": {
                "engine/stock_desk.py::qualitative-intelligence": {
                    "output_class": {
                        "value": "predictive",
                        "rationale": "forward stock calls in the fixture",
                    }
                }
            }
        },
    )
    if with_store:
        qdir = root / "data" / "qledger"
        qdir.mkdir(parents=True, exist_ok=True)
        (qdir / "claims.jsonl").write_text("", encoding="utf-8")
        (qdir / "grades.jsonl").write_text("", encoding="utf-8")
        _record_owner_fixture(root, ["stock_desk"])
    return root


def test_incomplete_e1_adapter_evidence_is_accruing_not_absent(tmp_path):
    """An empty-but-readable stock desk clock is the commissioned incomplete E1 case."""
    root = qledger_adapter_root(tmp_path)
    before = _tree(root)

    panel = IOS.panel(root=root)
    row = panel["engines"][0]
    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["binding"] == "adapter:stock_desk"
    assert row["evidence_provider"]["read_status"] == "partial"
    assert row["evidence_provider"]["recorded_snapshot"]["current_source_qualification"] == "unavailable"
    assert "owner_recorded_snapshot_current_unqualified" in row["evidence_reason_codes"]
    assert row["evidence_maturity"]["rungs"]["63"]["n_dates"] == 0

    detail = IOS.engine_detail(
        "engine/stock_desk.py::qualitative-intelligence", root=root
    )
    assert detail["engine"]["evidence_provider"]["family"] == "stock_desk"
    assert detail["engine"]["evidence_ruler"]["qledger_clock"] is None
    assert _tree(root) == before


def test_a_bound_but_unreadable_qledger_store_degrades_instead_of_faking_empty(tmp_path):
    """Missing owner bytes are could-not-look, not a zero-row accruing receipt."""
    root = qledger_adapter_root(tmp_path, with_store=False)
    row = IOS.panel(root=root)["engines"][0]

    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] in {"partial", "unreadable"}
    assert any(code in row["evidence_reason_codes"] for code in ["owner_snapshot_unavailable", "owner_recorded_snapshot_current_unqualified"])


def test_malformed_qledger_claims_degrade_instead_of_faking_an_empty_store(tmp_path):
    """A compatibility reader skipping corrupt JSONL must not become zero evidence."""
    root = qledger_adapter_root(tmp_path)
    (root / "data" / "qledger" / "claims.jsonl").write_text(
        "{not-json}\n", encoding="utf-8"
    )

    row = IOS.panel(root=root)["engines"][0]

    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] == "partial"
    assert row["evidence_provider"]["recorded_snapshot"]["current_source_qualification"] == "unavailable"
    assert any(code in row["evidence_reason_codes"] for code in ["owner_snapshot_unavailable", "owner_recorded_snapshot_current_unqualified"])


@pytest.mark.parametrize("store_name", ["claims.jsonl", "grades.jsonl"])
def test_semantically_invalid_qledger_rows_degrade_even_when_json_parses(
    tmp_path, store_name
):
    """Owner readers accepting ``{}`` must not turn corruption into Accruing."""
    root = qledger_adapter_root(tmp_path)
    (root / "data" / "qledger" / store_name).write_text("{}\n", encoding="utf-8")

    row = IOS.panel(root=root)["engines"][0]

    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] == "partial"
    assert row["evidence_provider"]["recorded_snapshot"]["current_source_qualification"] == "unavailable"
    assert any(code in row["evidence_reason_codes"] for code in ["owner_snapshot_unavailable", "owner_recorded_snapshot_current_unqualified"])


@pytest.mark.parametrize("store_name", ["claims.jsonl", "grades.jsonl"])
def test_invalid_utf8_qledger_store_is_provider_blindness_not_page_failure(
    tmp_path, store_name
):
    """Undecodable owner bytes degrade bound evidence while preserving the census."""
    root = qledger_adapter_root(tmp_path)
    (root / "data" / "qledger" / store_name).write_bytes(b"\xff\xfe\x00")

    result = IOS.panel(root=root)

    assert result["ok"] is True
    row = result["engines"][0]
    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] in {"partial", "unreadable"}
    assert row["evidence_provider"]["recorded_snapshot"]["current_source_qualification"] == "unavailable"
    assert any(code in row["evidence_reason_codes"] for code in ["owner_snapshot_unavailable", "owner_recorded_snapshot_current_unqualified"])


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("direction", True),
        ("scope", {"type": [], "key": "AAPL"}),
    ],
)
def test_claim_semantic_validation_is_type_total(tmp_path, field, bad_value):
    """Every JSON type becomes a provider verdict, never a page-level exception."""
    root = qledger_adapter_root(tmp_path)
    claim = {
        "claim_id": "c1",
        "desk": "stock_desk",
        "claim_family": "stock_desk",
        "asof": "2026-08-29",
        "scope": {"type": "entity", "key": "AAPL"},
        "direction": 1,
        "horizon_d": 20,
        "timestamp_quality": "CRAWL_BOUNDED",
    }
    claim[field] = bad_value
    (root / "data" / "qledger" / "claims.jsonl").write_text(
        json.dumps(claim) + "\n", encoding="utf-8"
    )

    from engine import qledger
    assert IOS._valid_claim_row(claim, qledger) is False
    result = IOS.panel(root=root)
    assert result["ok"] is True
    row = result["engines"][0]
    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] == "partial"
    assert row["evidence_provider"]["recorded_snapshot"]["current_source_qualification"] == "unavailable"


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("subject_ret", "0.1"),
        ("excess", {"value": 0.1}),
    ],
)
def test_grade_semantic_validation_rejects_nonnumeric_metrics(
    tmp_path, field, bad_value
):
    """Parseable prose/objects are not numeric owner evidence."""
    root = qledger_adapter_root(tmp_path)
    grade = {
        "claim_id": "c1",
        "horizon_d": 20,
        "graded_at": "2026-08-29T01:02:03+00:00",
        "subject_ret": 0.1,
        "bench_ret": 0.0,
        "control_ret": None,
        "excess": 0.1,
        "hit": True,
    }
    grade[field] = bad_value
    (root / "data" / "qledger" / "grades.jsonl").write_text(
        json.dumps(grade) + "\n", encoding="utf-8"
    )

    from engine import qledger
    assert IOS._valid_grade_row(grade, qledger) is False
    row = IOS.panel(root=root)["engines"][0]
    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] == "partial"
    assert row["evidence_provider"]["recorded_snapshot"]["current_source_qualification"] == "unavailable"


def test_grade_semantic_validation_contains_unrepresentable_numeric_metrics(tmp_path):
    """An enormous JSON integer degrades its provider; it never sinks the panel."""
    root = qledger_adapter_root(tmp_path)
    grade = {
        "claim_id": "c1",
        "horizon_d": 20,
        "graded_at": "2026-08-29T01:02:03+00:00",
        "subject_ret": 10**1000,
        "bench_ret": 0.0,
        "control_ret": None,
        "excess": 0.1,
        "hit": True,
    }
    (root / "data" / "qledger" / "grades.jsonl").write_text(
        json.dumps(grade) + "\n", encoding="utf-8"
    )

    from engine import qledger
    assert IOS._valid_grade_row(grade, qledger) is False
    result = IOS.panel(root=root)
    assert result["ok"] is True
    row = result["engines"][0]
    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] == "partial"
    assert row["evidence_provider"]["recorded_snapshot"]["current_source_qualification"] == "unavailable"


@pytest.mark.parametrize(
    "basis_patch",
    [
        {"clock_version": "explicit_unit_v1"},
        {"horizon_unit": "trading_days"},
        {"clock_market": "US"},
    ],
)
def test_grade_semantic_validation_rejects_partial_clock_basis(
    tmp_path, basis_patch
):
    """Partial explicit stamps cannot be silently reclassified as legacy evidence."""
    root = qledger_adapter_root(tmp_path)
    grade = {
        "claim_id": "c1",
        "horizon_d": 20,
        "graded_at": "2026-08-29T01:02:03+00:00",
        "subject_ret": 0.1,
        "bench_ret": 0.0,
        "control_ret": None,
        "excess": 0.1,
        "hit": True,
        **basis_patch,
    }
    (root / "data" / "qledger" / "grades.jsonl").write_text(
        json.dumps(grade) + "\n", encoding="utf-8"
    )

    from engine import qledger
    assert IOS._valid_grade_row(grade, qledger) is False
    row = IOS.panel(root=root)["engines"][0]
    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] == "partial"
    assert row["evidence_provider"]["recorded_snapshot"]["current_source_qualification"] == "unavailable"


def test_market_unstamped_explicit_basis_remains_lawful(tmp_path):
    """The owner contract permits version+unit without a market during migration."""
    root = qledger_adapter_root(tmp_path)
    grade = {
        "claim_id": "c1",
        "horizon_d": 20,
        "graded_at": "2026-08-29T01:02:03+00:00",
        "subject_ret": 0.1,
        "bench_ret": 0.0,
        "control_ret": None,
        "excess": 0.1,
        "hit": True,
        "clock_version": "explicit_unit_v1",
        "horizon_unit": "trading_days",
    }
    (root / "data" / "qledger" / "grades.jsonl").write_text(
        json.dumps(grade) + "\n", encoding="utf-8"
    )

    row = IOS.panel(root=root)["engines"][0]
    assert row["evidence_provider"]["read_status"] == "partial"
    assert "evidence_provider_unreadable" not in row["evidence_reason_codes"]


def test_qledger_semantic_validators_are_total_over_json_types():
    """Adversarial JSON values always yield a boolean, never an exception."""
    from engine import qledger

    values = [None, False, True, 0, 1, 1.5, "", "value", [], {}]
    claim = {
        "claim_id": "c1",
        "desk": "stock_desk",
        "claim_family": "stock_desk",
        "asof": "2026-08-29",
        "scope": {"type": "entity", "key": "AAPL"},
        "direction": 1,
        "horizon_d": 20,
        "timestamp_quality": "CRAWL_BOUNDED",
    }
    for field in claim:
        for value in values:
            assert isinstance(
                IOS._valid_claim_row({**claim, field: value}, qledger), bool
            )
    for nested in ("type", "key"):
        for value in values:
            assert isinstance(
                IOS._valid_claim_row(
                    {**claim, "scope": {**claim["scope"], nested: value}}, qledger
                ),
                bool,
            )

    grade = {
        "claim_id": "c1",
        "horizon_d": 20,
        "graded_at": "2026-08-29T01:02:03+00:00",
        "subject_ret": 0.1,
        "bench_ret": 0.0,
        "control_ret": None,
        "excess": 0.1,
        "hit": True,
        "clock_version": "explicit_unit_v1",
        "horizon_unit": "trading_days",
        "clock_market": "US",
    }
    for field in grade:
        for value in [*values, float("nan"), float("inf"), float("-inf"), 10**1000]:
            assert isinstance(
                IOS._valid_grade_row({**grade, field: value}, qledger), bool
            )


def test_corrupt_existing_evidence_clock_degrades_instead_of_looking_unstarted(tmp_path):
    """An existing unreadable write-once receipt is blindness, not an absent clock."""
    root = qledger_adapter_root(tmp_path)
    clock_dir = root / "data" / "qledger" / "evidence_clock_start"
    clock_dir.mkdir(parents=True)
    (clock_dir / "stock_desk.json").write_text("{not-json}", encoding="utf-8")

    row = IOS.panel(root=root)["engines"][0]

    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] in {"partial", "unreadable"}
    assert row["evidence_provider"]["recorded_snapshot"]["current_source_qualification"] == "unavailable"
    assert "evidence_clock_not_started" not in row["evidence_reason_codes"]


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("first_prospective_registration_utc", "definitely-not-a-timestamp"),
        ("declared_horizon_d", True),
    ],
)
def test_semantically_invalid_evidence_clock_degrades(tmp_path, field, bad_value):
    """A parseable receipt still fails closed when its ruler fields are dishonest."""
    root = qledger_adapter_root(tmp_path)
    clock_dir = root / "data" / "qledger" / "evidence_clock_start"
    clock_dir.mkdir(parents=True)
    receipt = {
        "claim_family": "stock_desk",
        "first_prospective_registration_utc": "2026-08-29T01:02:03+00:00",
        "declared_horizon_d": 20,
        "horizon_unit": "trading_days",
        "git_sha": "abc123",
    }
    receipt[field] = bad_value
    (clock_dir / "stock_desk.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )

    row = IOS.panel(root=root)["engines"][0]

    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] in {"partial", "unreadable"}
    assert row["evidence_provider"]["recorded_snapshot"]["current_source_qualification"] == "unavailable"
    assert "evidence_clock_not_started" not in row["evidence_reason_codes"]


def test_missing_grades_is_a_lawful_empty_accrual_not_provider_blindness(tmp_path):
    """Before the first grade, absence of the optional grade ledger is an honest zero."""
    root = qledger_adapter_root(tmp_path)
    (root / "data" / "qledger" / "grades.jsonl").unlink()

    row = IOS.panel(root=root)["engines"][0]

    assert row["evidence_status"] == "Degraded"
    assert row["evidence_provider"]["read_status"] == "partial"
    assert "evidence_provider_unreadable" not in row["evidence_reason_codes"]


def test_new_evidence_clock_invalidates_the_in_process_view(tmp_path):
    """The five-minute cache must not hide the first prospective clock receipt."""
    root = qledger_adapter_root(tmp_path)
    first = IOS.panel(root=root)
    assert first["generated"]["cache"] == "miss"
    assert IOS.panel(root=root)["generated"]["cache"] == "hit"

    clock_dir = root / "data" / "qledger" / "evidence_clock_start"
    clock_dir.mkdir(parents=True)
    (clock_dir / "stock_desk.json").write_text(
        json.dumps(
            {
                "claim_family": "stock_desk",
                "first_prospective_registration_utc": "2026-08-29T01:02:03+00:00",
                "declared_horizon_d": 20,
                "horizon_unit": "trading_days",
                "git_sha": "abc123",
            }
        ),
        encoding="utf-8",
    )

    fresh = IOS.panel(root=root)
    assert fresh["generated"]["cache"] == "miss"
    row = fresh["engines"][0]
    assert row["evidence_ruler"]["qledger_clock"]["horizon_d"] == 20
    assert "qledger-clock:stock_desk:2026-08-29T01:02:03+00:00" in row[
        "evidence_refs"
    ]


@pytest.mark.parametrize("changed_rel", ["data/species/registry.json", "engine/a.py"])
def test_t1_evidence_input_movement_invalidates_the_in_process_view(
    tmp_path, changed_rel
):
    """Owner lifecycle and producer semantics must not remain stale for the cache TTL."""
    root = one_engine(tmp_path)
    assert IOS.panel(root=root)["generated"]["cache"] == "miss"
    assert IOS.panel(root=root)["generated"]["cache"] == "hit"

    changed = root / changed_rel
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text(
        '{"species": []}\n' if changed.suffix == ".json" else "# producer changed\n",
        encoding="utf-8",
    )

    assert IOS.panel(root=root)["generated"]["cache"] == "miss"


def test_new_repo_path_prereg_invalidates_the_in_process_view(tmp_path):
    """A newly materialized Synapse evidence pointer must not hide for the TTL."""
    prereg_rel = "research/new_prereg.md"
    root = _write_root(
        tmp_path,
        {
            "a": artifact(
                "data/a.json",
                producer="engine/a.py",
                owner="prog-one",
                tier="scored",
                qual_ladder_ref=prereg_rel,
            )
        },
    )
    (root / "config" / "qual_ladder.yml").write_text("{}\n", encoding="utf-8")
    first = IOS.panel(root=root)
    assert prereg_rel not in first["engines"][0]["evidence_refs"]
    assert IOS.panel(root=root)["generated"]["cache"] == "hit"

    prereg = root / prereg_rel
    prereg.parent.mkdir(parents=True)
    prereg.write_text("# prospective protocol\n", encoding="utf-8")

    fresh = IOS.panel(root=root)
    assert fresh["generated"]["cache"] == "miss"
    assert prereg_rel in fresh["engines"][0]["evidence_refs"]


def test_revised_existing_evidence_clock_invalidates_the_in_process_view(tmp_path):
    """Changing clock bytes in place must invalidate even when the directory does not."""
    root = qledger_adapter_root(tmp_path)
    clock_dir = root / "data" / "qledger" / "evidence_clock_start"
    clock_dir.mkdir(parents=True)
    clock = clock_dir / "stock_desk.json"
    receipt = {
        "claim_family": "stock_desk",
        "first_prospective_registration_utc": "2026-08-29T01:02:03+00:00",
        "declared_horizon_d": 20,
        "horizon_unit": "trading_days",
        "git_sha": "abc123",
    }
    clock.write_text(json.dumps(receipt), encoding="utf-8")
    first = IOS.panel(root=root)
    assert first["engines"][0]["evidence_ruler"]["qledger_clock"]["horizon_d"] == 20
    assert IOS.panel(root=root)["generated"]["cache"] == "hit"

    before = clock.stat().st_mtime_ns
    receipt["declared_horizon_d"] = 63
    receipt["git_sha"] = "def456"
    clock.write_text(json.dumps(receipt), encoding="utf-8")
    os.utime(clock, ns=(before + 1_000_000_000, before + 1_000_000_000))

    fresh = IOS.panel(root=root)
    assert fresh["generated"]["cache"] == "miss"
    assert fresh["engines"][0]["evidence_ruler"]["qledger_clock"]["horizon_d"] == 63
    assert "git:def456" in fresh["engines"][0]["evidence_refs"]


# ---------------------------------------------------------------------------
# No persisted state
# ---------------------------------------------------------------------------

def test_neither_entry_point_writes_anything_to_disk(tmp_path):
    """CEO law: this surface holds NO state. Not a cache file, not a snapshot.

    Compared by (size, mtime_ns) over every file, so a rewrite with identical bytes is
    caught as well as an addition or a deletion — 'the file did not change' has to mean
    nobody touched it, not that they put it back the way they found it.
    """
    root = one_engine(tmp_path)
    before = _tree(root)
    assert IOS.panel(root=root)["ok"] is True
    assert IOS.engine_detail("engine/a.py::prog-one", root=root)["ok"] is True
    assert IOS.panel(root=root, force=True)["ok"] is True
    assert _tree(root) == before

    # Nothing outside the fixture root either — the repo itself must be untouched.
    assert not list(tmp_path.glob("*.json"))
    assert not list(tmp_path.glob("*.cache"))


# ---------------------------------------------------------------------------
# engine_detail
# ---------------------------------------------------------------------------

def test_engine_detail_for_an_unknown_id_refuses_with_a_sample(tmp_path):
    root = one_engine(tmp_path)
    result = IOS.engine_detail("engine/nope.py::nowhere", root=root)
    assert result["ok"] is False
    assert "nope" in result["error"]
    # The sample is the affordance that turns a typo into a fix instead of a shrug.
    assert result["known_ids_sample"] == ["engine/a.py::prog-one"]


def test_engine_detail_returns_the_full_t4_record(tmp_path):
    """The drill-down renders the record verbatim, so the keys it draws must be present.

    Pinned by NAME: a resolver change that renamed one of these would otherwise show up
    as a silently blank row on the page rather than as a red test.
    """
    root = one_engine(tmp_path)
    detail = IOS.engine_detail("engine/a.py::prog-one", root=root)
    assert detail["ok"] is True
    record = detail["outputs"][0]
    for key in (
        "artifact_id", "path", "storage", "state", "assessment_status", "decided_by",
        "age_hours", "freshness_sla_hours", "dependency_bound", "reason_codes",
        "required_inputs", "optional_inputs", "reader_observation", "self_health",
        "source_asof", "display_confidence_state",
    ):
        assert key in record, f"the engine drill-down renders {key!r} and it is missing"


def test_artifacts_outside_every_engine_cell_are_surfaced_not_dropped(tmp_path):
    """A synapse artifact with a placeholder producer is in NO T1 engine cell. It still
    has to appear: an artifact nobody owns is precisely what an operator census exists to
    find, and dropping it would make the page's own artifact count a lie."""
    root = _write_root(
        tmp_path,
        {
            "a": artifact("data/a.json", producer="engine/a.py", owner="prog-one"),
            "orphan": artifact("data/orphan.json", producer="<MANUAL>", owner="prog-one"),
        },
    )
    panel = IOS.panel(root=root)
    assert panel["census"]["artifacts"] == 2
    ids = {r["engine_id"] for r in panel["engines"]}
    assert IOS.UNREGISTERED_ENGINE_ID in ids
    orphan = next(
        row for row in panel["engines"] if row["engine_id"] == IOS.UNREGISTERED_ENGINE_ID
    )
    assert orphan["canonical_t1"] is False
    assert orphan["evidence_status"] is None
    assert orphan["evidence_reason_codes"] == ["not_canonical_t1"]
    # The legacy table keeps the orphan visible, but the commissioned CEO ordering is
    # explicitly over canonical T1 cells. A registry gap is not a 2nd engine.
    assert panel["census"]["canonical_engines"] == 1
    assert panel["census"]["noncanonical_output_groups"] == 1
    assert sum(band["n_engines"] for band in panel["ceo_view"]) == 1
    assert IOS.UNREGISTERED_ENGINE_ID not in {
        engine_id
        for band in panel["ceo_view"]
        for engine_id in band["engine_ids"]
    }

    detail = IOS.engine_detail(IOS.UNREGISTERED_ENGINE_ID, root=root)
    assert detail["ok"] is True
    assert detail["engine"]["canonical_t1"] is False
    assert detail["engine"]["evidence_status"] is None
    assert detail["engine"]["evidence_reason_codes"] == ["not_canonical_t1"]
    assert [o["artifact_id"] for o in detail["outputs"]] == ["orphan"]


# ---------------------------------------------------------------------------
# worst_state ordering
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def blind_estate(tmp_path_factory):
    """A two-engine estate the roll-up cannot honestly summarize with a state alone.

    ``blind`` has ONE output and it is unreadable (a csv carries no readable watermark, so
    the freshness axis is blind). ``mixed`` has one readable-and-current output and one
    unreadable one — the shape that used to render a plain green row.

    Module-scoped because the panel is a real derivation and the assertions below hang off
    a parametrized test; deriving it once is the difference between a pin and a tax.
    """
    root = _write_root(
        tmp_path_factory.mktemp("blind"),
        {
            "b1": artifact("data/b1.csv", producer="engine/blind.py", owner="prog-blind",
                           fmt="csv"),
            "m1": artifact("data/m1.json", producer="engine/mixed.py", owner="prog-mixed"),
            "m2": artifact("data/m2.csv", producer="engine/mixed.py", owner="prog-mixed",
                           fmt="csv"),
        },
    )
    return IOS.panel(root=root, force=True)


@pytest.mark.parametrize(
    "states, expected",
    [
        (["healthy", "degraded"], "degraded"),
        (["healthy", "stale", "degraded"], "stale"),
        (["stale", "unavailable", "degraded"], "unavailable"),
        (["healthy", None], "healthy"),          # a null NEVER outranks a real verdict
        ([None, None], None),
        (["healthy", "healthy"], "healthy"),
        ([], None),
    ],
)
def test_worst_state_follows_the_t4_precedence_ladder(states, expected, blind_estate):
    assert IOS.worst_state(states) == expected

    # THE OTHER HALF OF THE SAME LADDER. `worst_state` folding only real verdicts is
    # correct — "could not determine" is not a health verdict and must never outrank one —
    # but it means the fold ALONE cannot describe an engine some of whose outputs were
    # unreadable. So every row carries the blind count, asserted on the payload (the DOM
    # is not the contract; the payload is).
    rows = {r["engine_id"]: r for r in blind_estate["engines"]}
    assert all("n_blind" in r for r in rows.values()), sorted(rows)

    all_blind = rows["engine/blind.py::prog-blind"]
    assert all_blind["worst_state"] is None
    assert all_blind["n_blind"] == all_blind["n_artifacts"] == 1

    mixed = rows["engine/mixed.py::prog-mixed"]
    assert mixed["worst_state"] == "healthy"          # the worst thing that could be SEEN
    assert (mixed["n_blind"], mixed["n_artifacts"]) == (1, 2)
    assert mixed["state_counts"]["null"] == 1         # and it agrees with its own tally


def test_worst_state_treats_an_unknown_word_as_the_worst_thing_it_has_seen():
    """A state this page has not learned must announce itself, not hide behind healthy.

    If the T4 vocabulary ever grows a fifth verdict, the roll-up surfacing it is a bug
    report; the roll-up quietly reporting `healthy` is an outage nobody sees.
    """
    assert IOS.worst_state(["healthy", "on_fire"]) == "on_fire"


def test_state_severity_matches_the_resolver_ladder():
    """The one hand-written list in the module, pinned against the contract it mirrors."""
    assert IOS.STATE_SEVERITY == ("unavailable", "stale", "degraded", "healthy", None)


def test_engine_worst_state_folds_its_own_outputs(tmp_path):
    """Fold direction, end to end: one stale output makes the whole engine row stale."""
    root = _write_root(
        tmp_path,
        {
            "fresh": artifact("data/fresh.json", producer="engine/a.py", owner="prog-one"),
            "old": artifact("data/old.json", producer="engine/a.py", owner="prog-one"),
        },
    )
    (root / "data" / "old.json").write_text(
        json.dumps({"asof": "2026-01-01T00:00:00+00:00"}), encoding="utf-8"
    )
    row = IOS.panel(root=root)["engines"][0]
    assert row["n_artifacts"] == 2
    assert row["worst_state"] == "stale"
    assert row["state_counts"]["stale"] == 1


# ---------------------------------------------------------------------------
# Cache protocol
# ---------------------------------------------------------------------------

def test_second_call_is_a_cache_hit_and_force_recomputes(tmp_path):
    root = one_engine(tmp_path)
    first = IOS.panel(root=root)
    assert first["generated"]["cache"] == "miss"

    second = IOS.panel(root=root)
    assert second["generated"]["cache"] == "hit"
    assert second["generated"]["compute_seconds"] == 0.0
    assert second["engines"] == first["engines"]

    forced = IOS.panel(root=root, force=True)
    assert forced["generated"]["cache"] == "miss"


def test_editing_the_registry_evicts_the_cache_without_force(tmp_path):
    """The TTL is a floor, not the invalidation rule. Keying on the two declared inputs'
    mtimes is what stops an operator editing synapse.yml and reading a five-minute-old
    census that still says the old thing."""
    root = one_engine(tmp_path)
    assert IOS.panel(root=root)["generated"]["cache"] == "miss"
    assert IOS.panel(root=root)["generated"]["cache"] == "hit"

    doc = yaml.safe_load((root / "config" / "synapse.yml").read_text())
    doc["artifacts"]["z"] = artifact("data/z.json", producer="engine/z.py", owner="prog-two")
    (root / "config" / "synapse.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    (root / "engine").mkdir(exist_ok=True)
    (root / "engine" / "z.py").write_text("", encoding="utf-8")
    (root / "data" / "z.json").write_text(json.dumps({"asof": FRESH}), encoding="utf-8")

    fresh = IOS.panel(root=root)
    assert fresh["generated"]["cache"] == "miss"
    assert fresh["census"]["engines"] == 2


def test_the_cache_does_not_grow_one_entry_per_registry_edit(tmp_path):
    """The key changes on every edit, and the process is long-lived. Without eviction the
    admin server would accumulate a full 642-record view per nightly commit."""
    root = one_engine(tmp_path)
    for i in range(3):
        doc = yaml.safe_load((root / "config" / "synapse.yml").read_text())
        doc["meta"]["description"] = f"fixture {i}"
        (root / "config" / "synapse.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")
        assert IOS.panel(root=root)["ok"] is True
    assert len(IOS._CACHE) == 1


# ---------------------------------------------------------------------------
# Trust-mtime plane + fail-open
# ---------------------------------------------------------------------------

def test_write_time_evidence_is_refused_on_every_plane_including_the_deployed_one(
    monkeypatch,
):
    """A DEPLOYED file's mtime is a git-transport clock, not a write time.

    ``app/deploy/update.sh`` updates the VPS with ``git fetch && git reset --hard``, so
    every file git rewrites is stamped with the PULL time. The panel used to admit
    write-time evidence whenever ``ADMIN_DEPLOYED=1``, which means a deploy or a rollback
    would have restamped the tree and turned the 63 artifacts that declare an SLA but no
    watermark green — an entire class of frozen stores reading "fresh" because somebody
    deployed. The environment cannot turn it back on because the environment is no longer
    consulted: pinned structurally, since an env read is the thing being removed.
    """
    monkeypatch.setenv("ADMIN_DEPLOYED", "1")
    assert IOS._trust_mtime() is False
    monkeypatch.delenv("ADMIN_DEPLOYED", raising=False)
    assert IOS._trust_mtime() is False

    tree = ast.parse((REPO / "admin" / "intelligence_os.py").read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    # os is allowed for nonblocking regular-file reads, never freshness policy.
    trust = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_trust_mtime")
    assert not any(isinstance(node, ast.Attribute) and node.attr in ("environ", "getenv") for node in ast.walk(trust))
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in ("environ", "getenv")
    ]
    assert "ADMIN_DEPLOYED" not in {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_a_no_watermark_artifact_stays_unassessed_rather_than_trusting_its_mtime(tmp_path):
    """The consequence of the rule above, made visible: an artifact that declares an SLA
    but no watermark field is NOT healthy and NOT stale — it is unassessed, and the record
    says which axis and why. That reason code is the standing argument for declaring a
    watermark; a silent green would have removed the argument."""
    root = _write_root(
        tmp_path,
        {
            "nowm": artifact("data/nowm.json", producer="engine/a.py", owner="prog-one",
                             asof_field=None, sla=24),
        },
    )
    detail = IOS.engine_detail("engine/a.py::prog-one", root=root)
    record = detail["outputs"][0]
    assert record["state"] is None
    assert record["assessment_status"] == "partial"
    assert "write_time_untrusted" in record["reason_codes"]
    assert IOS.panel(root=root)["generated"]["trust_mtime"] is False


def test_both_entry_points_fail_open_on_an_unreadable_root(tmp_path):
    """Every sibling admin panel degrades rather than 500s, and so does this one."""
    empty = tmp_path / "not-a-checkout"
    empty.mkdir()
    panel = IOS.panel(root=empty)
    assert panel["ok"] is False
    assert panel["error"]
    detail = IOS.engine_detail("anything", root=empty)
    assert detail["ok"] is False


def test_census_counts_agree_with_the_rows_they_summarize(tmp_path):
    """A census whose headline disagrees with its own table is worse than no census."""
    root = _write_root(
        tmp_path,
        {
            "a": artifact("data/a.json", producer="engine/a.py", owner="prog-one"),
            "b": artifact("data/b.json", producer="engine/b.py", owner="prog-two"),
            "c": artifact("data/c.json", producer="engine/b.py", owner="prog-two"),
        },
    )
    panel = IOS.panel(root=root)
    census, engines = panel["census"], panel["engines"]
    assert census["engines"] == len(engines)
    assert census["artifacts"] == sum(r["n_artifacts"] for r in engines)
    assert sum(census["by_state"].values()) == census["artifacts"]
    assert sum(census["by_authority"].values()) == census["artifacts"]
    assert sum(census["by_storage"].values()) == census["artifacts"]
    assert census["outputs_assessed"] <= census["artifacts"]
    assert census["by_assessment_status"].get("could_not_look", 0) == (
        census["artifacts"] - census["outputs_assessed"]
    )


# ---------------------------------------------------------------------------
# The reader plane rides along
# ---------------------------------------------------------------------------

def _capture_builder_kwargs(monkeypatch) -> dict:
    """Route _derive's lazy import through a capturing wrapper around the real builder."""
    import scripts.build_output_health as boh

    seen: dict = {}
    real = boh.build_with_registry

    def capture(root_arg, **kw):
        seen.update(kw)
        return real(root_arg, **kw)

    monkeypatch.setattr(boh, "build_with_registry", capture)
    return seen


def test_the_panel_hands_the_sentinel_file_to_the_builder_when_it_exists(
    tmp_path, monkeypatch
):
    """Reader evidence is sovereign (resolver §8), and the sentinel's staleness.json IS
    the reader plane's live source on the deployed estate. The T4 CLI already defaults
    to it; a panel that dropped it was reader-blind on exactly the plane it runs on."""
    root = one_engine(tmp_path)
    staleness = root / "site" / "live" / "staleness.json"
    staleness.parent.mkdir(parents=True, exist_ok=True)
    staleness.write_text(json.dumps({"surfaces": {}}), encoding="utf-8")

    seen = _capture_builder_kwargs(monkeypatch)
    assert IOS.panel(root=root, force=True)["ok"] is True
    assert seen.get("staleness_json") == staleness


def test_an_absent_sentinel_file_is_passed_as_none_never_a_dangling_path(
    tmp_path, monkeypatch
):
    """No sentinel file is a legitimate state (a checkout, a fresh estate) — the builder
    must see None, not a path to nothing, so absence stays disclosed as absence."""
    root = one_engine(tmp_path)
    seen = _capture_builder_kwargs(monkeypatch)
    assert IOS.panel(root=root, force=True)["ok"] is True
    assert seen.get("staleness_json") is None

# Evaluation OS consumer boundary regressions: synthetic owners, no market outcomes.
@pytest.mark.parametrize("output_class", ["predictive", "ranking", "classification_state",
    "detection_event", "descriptive", "salience", "generative"])
def test_lifecycle_only_validation_preserves_owner_scope_without_empirical_pass(output_class):
    cell = evidence_cell(validation_state="validated", output_class=output_class,
        validation_state_evidence={"bound_species": [{"species_id": "fixture-v1",
          "validation_status": "validated", "owner_scope": {"version": "1.0", "market_scope": ["US"]}}]})
    result = IOS.derive_evidence_status(cell, [healthy_output()])
    assert result["evidence_status"] == "Accruing"
    assert "owner_validation_scope_unqualified" in result["evidence_reason_codes"]
    assert result["evidence_owner_scope"]["owner_lifecycle"] == "validated"
    assert result["evidence_owner_scope"]["bound_species"][0]["owner_scope"]["version"] == "1.0"
    assert result["evidence_owner_scope"]["qualified_task_scope"] is None
    assert "species:fixture-v1" in result["evidence_refs"]


@pytest.mark.parametrize("output", [{}, {"state": None, "assessment_status": "partial"},
    {"state": "healthy", "assessment_status": "partial"}, {"state": "healthy"}])
def test_unqualified_health_cannot_support_owner_validation(output):
    result = IOS.derive_evidence_status(evidence_cell(validation_state="validated"), [output])
    assert result["evidence_status"] == "Degraded"


def test_retirement_is_preserved_without_claiming_empirical_falsification():
    retired = IOS.derive_evidence_status(evidence_cell(validation_state="retired"), [healthy_output()])
    falsified = IOS.derive_evidence_status(evidence_cell(validation_state="falsified"), [healthy_output()])
    assert retired["evidence_status"] == "Degraded"
    assert "owner_terminal_retired" in retired["evidence_reason_codes"]
    assert retired["evidence_maturity"]["validation_state"] == "retired"
    assert falsified["evidence_status"] == "Disproven"


def test_current_declared_horizon_union_outranks_immutable_first_clock():
    provider = qledger_provider()
    provider["clock_start"]["declared_horizon_d"] = 20
    provider["readiness"] = {str(n): {"n_dates": 0, "ready": False} for n in (5,21,63)}
    result = IOS.derive_evidence_status(evidence_cell(declared_horizon={"horizon_d": [20,126]}), [healthy_output()], provider)
    assert result["evidence_ruler"]["selected_qledger_rung"] == "63"
    assert result["evidence_ruler"]["qledger_clock"]["horizon_d"] == 20
    assert result["evidence_ruler"]["declared_horizon"]["horizon_d"] == [20,126]
    assert provider["clock_start"]["declared_horizon_d"] == 20


def test_same_size_preserved_mtime_corrections_invalidate_generation(tmp_path):
    path = tmp_path / "claims.jsonl"
    path.write_text("A\n")
    stamp = path.stat().st_mtime_ns
    a = IOS._mtime_ns(path)
    path.write_text("B\n")
    os.utime(path, ns=(stamp,stamp))
    b = IOS._mtime_ns(path)
    path.write_text("A\n")
    os.utime(path, ns=(stamp,stamp))
    a2 = IOS._mtime_ns(path)
    assert path.stat().st_mtime_ns == stamp
    assert a != b and b != a2


def test_changed_legacy_source_during_build_refuses_mixed_generation(monkeypatch, tmp_path):
    root = one_engine(tmp_path)
    claims = root / "data/qledger/claims.jsonl"
    claims.parent.mkdir(parents=True,exist_ok=True)
    claims.write_text("A\n")
    from scripts import build_output_health as builder
    original = builder.build_with_registry
    def moving(*args, **kwargs):
        result = original(*args, **kwargs)
        stamp = claims.stat().st_mtime_ns
        claims.write_text("B\n")
        os.utime(claims,ns=(stamp,stamp))
        return result
    monkeypatch.setattr(builder,"build_with_registry",moving)
    result = IOS.panel(root=root,force=True)
    assert result["ok"] is False and result["error_code"] == "changed_during_read"
    assert not IOS._CACHE


def _native_fixture(raw):
    from hashlib import sha256
    from engine import qledger_store_protocol as p
    limits = p.ProtocolLimits()
    digest = sha256(raw).hexdigest()
    ref = p.MemberRef(p.BASE_PATH,digest,len(raw))
    record = p.RootRecord(ref,None,0,len(raw),digest,limits.fingerprint)
    return p.verify_snapshot(p.InMemorySource({p.BASE_PATH:raw},snapshot_id="fixture:"+digest),record,limits=limits)


class _RetainedClaimsFixture:
    def __init__(self,path,*snapshots):
        self.claims_path=path;self.snapshots=snapshots;self.reads=0
    def read_snapshot(self):
        value=self.snapshots[min(self.reads,len(self.snapshots)-1)];self.reads+=1;return value


def test_selected_native_counts_and_values_use_one_snapshot_without_legacy_file(tmp_path):
    from engine import qledger_store as store,qledger
    path=tmp_path/"data/qledger/claims.jsonl"
    raw=b'{"claim_id":"first"}\n{"claim_id":"first"}\nnull\nbad\n#comment\n'
    binding=_RetainedClaimsFixture(path,_native_fixture(raw),_native_fixture(b'{}\n'))
    with store._synthetic_claims_binding(path,binding),store.ClaimsReadScope(tmp_path):
        before=IOS._claims_source_key(tmp_path)
        assert IOS._claims_candidate_count(path)==(4,None)
        assert qledger.load_claims(tmp_path)==[{"claim_id":"first"},{"claim_id":"first"},None]
        assert IOS._claims_source_key(tmp_path)==before
        assert binding.reads==1
    assert not path.exists() and not store.uses_native_claims(path)


def test_native_cache_identity_tracks_selected_owner_a_b_a_not_physical_file(tmp_path):
    from engine import qledger_store as store
    path=tmp_path/"data/qledger/claims.jsonl"
    binding=_RetainedClaimsFixture(path,_native_fixture(b'A\n'),_native_fixture(b'B\n'),_native_fixture(b'A\n'))
    with store._synthetic_claims_binding(path,binding):
        keys=[IOS._claims_source_key(tmp_path) for _ in range(3)]
    assert keys[0]!=keys[1] and keys[0]==keys[2]
    assert keys[0][0]=="native" and binding.reads==3


def test_private_derivation_error_has_fixed_unknown_failure(monkeypatch,tmp_path):
    def fail(*a,**k):raise RuntimeError("/private/synthetic SECRET_CANARY")
    monkeypatch.setattr(IOS,"_derive",fail)
    for result in (IOS.panel(root=tmp_path),IOS.engine_detail("fixture",root=tmp_path)):
        assert result["ok"] is False and result["error_code"]=="evidence_estate_unavailable"
        assert "SECRET_CANARY" not in json.dumps(result) and "/private" not in json.dumps(result)


@pytest.mark.parametrize("output_class", ["predictive","ranking","classification_state","detection_event","descriptive","salience","generative"])
def test_real_t1_t4_panel_detail_keep_unqualified_owner_support_separate(monkeypatch,tmp_path,output_class):
    from engine import intelligence_registry as ir, output_health as oh
    eid="engine/a.py::fixture"
    doc={"meta":{},"artifacts":{"a":artifact("data/fixture/theses.jsonl",producer="engine/a.py",owner="fixture",tier="shadow",asof_field=None,sla=None)}}
    registry=ir.build_registry(synapse=doc,overlay={"schema_version":1,"engines":{eid:{"output_class":{"value":output_class,"rationale":"synthetic"}}}},species=[{"species_id":"fixture-v1","validation_status":"validated","version":"1.0","ledger_binding":{"ledger":"data/fixture/theses.jsonl"}}],file_exists=lambda _:True,qual_ladder_keys=set())
    observation={"exists":True,"presence_source":"filesystem","content_asof_raw":None,"asof_field_present":None,"watermark_field_used":None,"mtime_utc":None,"mtime_trusted":False,"parse_error":None,"sparse_unmaterialized":False}
    for partial,expected in [(False,"Accruing"),(True,"Degraded")]:
        extra={"reader_observations":{"a":{"source":"fixture","verdict":"indeterminate","clock_kind":"transport"}},"self_health":{"a":{"source":"fixture","status":"unknown"}}} if partial else {}
        view=oh.resolve_output_health(synapse=doc,registry=registry,observations={"a":observation},now=datetime.now(timezone.utc),**extra)
        if partial:assert view["outputs"][0]["state"] is None and view["outputs"][0]["assessment_status"]=="partial"
        provider=IOS._load_evidence_providers(tmp_path,registry)
        assert provider=={}
        monkeypatch.setattr(IOS,"_derive",lambda *_a,**_k:(view,registry,provider,0.,"miss"))
        row=IOS.panel(root=tmp_path)["engines"][0]
        detail=IOS.engine_detail(eid,root=tmp_path)["engine"]
        assert row["evidence_status"]==detail["evidence_status"]==expected
        assert detail["validation_state"]=="validated"
        assert detail["evidence_owner_scope"]["bound_species"][0]["owner_scope"]["version"]=="1.0"


def test_real_claims_reader_t1_provider_current_horizon_correction(monkeypatch,tmp_path):
    from engine import intelligence_registry as ir,qledger as q
    from scripts import build_intelligence_registry as builder
    root=tmp_path;family="fixture-ruler";eid="engine/fixture.py::ruler-fixture"
    clock={"claim_family":family,"first_prospective_registration_utc":"2026-08-19T08:00:00+00:00","declared_horizon_d":20,"horizon_unit":"trading_days","git_sha":"fixture-only"}
    base=root/"data/qledger";(base/"evidence_clock_start").mkdir(parents=True)
    (base/f"evidence_clock_start/{family}.json").write_text(json.dumps(clock));(base/"grades.jsonl").write_text("")
    (root/"config").mkdir();(root/"config/qual_ladder.yml").write_text("families: {}\n")
    entry=artifact("data/fixture/view.json",producer="engine/fixture.py",owner="ruler-fixture",tier="shadow",asof_field=None,sla=None)
    for horizons,expected in [([20],"5"),([20,126],"63")]:
        claims=[{"claim_id":f"fixture-{h}","desk":family,"claim_family":family,"asof":"2026-08-19","scope":{"type":"entity","key":"AAPL"},"direction":1,"horizon_d":h,"horizon_unit":"trading_days","timestamp_quality":next(iter(q.TIMESTAMP_QUALITY)),"bench":"SPY"} for h in horizons]
        assert all(IOS._valid_claim_row(c,q) for c in claims)
        (base/"claims.jsonl").write_text("".join(json.dumps(c)+"\n" for c in claims))
        builder._READ_CACHE.clear()
        loaded=builder._load_qledger(root)
        registry=ir.build_registry(synapse={"meta":{},"artifacts":{"fixture":entry}},overlay={"schema_version":1,"engines":{eid:{"output_class":{"value":"predictive","rationale":"synthetic"}}}},desk_scans={"engine/fixture.py":ir.DeskScan(True,(family,),False)},qledger_desk_rows=loaded.rows,qledger_desk_horizons=loaded.horizons,species=[],file_exists=lambda _:True,qual_ladder_keys=set())
        _record_owner_fixture(root,[family])
        provider=IOS._load_evidence_providers(root,registry)
        assert provider[eid]["read_status"]=="partial"
        view={"outputs":[healthy_output(engine_id=eid)],"summary":{}}
        monkeypatch.setattr(IOS,"_derive",lambda *_a,**_k:(view,registry,provider,0.,"miss"))
        panel=IOS.panel(root=root)["engines"][0]["evidence_ruler"]
        detail=IOS.engine_detail(eid,root=root)["engine"]["evidence_ruler"]
        assert panel==detail and panel["selected_qledger_rung"]==expected
        assert panel["declared_horizon"]["horizon_d"]==horizons
        assert json.loads((base/f"evidence_clock_start/{family}.json").read_text())==clock

@pytest.mark.parametrize('ledger', ['data/decoy/stock_desk/theses.jsonl','data/stock_desk/other.jsonl','backup/stock_desk/theses.jsonl'])
def test_actual_provider_refuses_noncanonical_native_ledger(tmp_path,ledger):
    base=tmp_path/'data/qledger';base.mkdir(parents=True)
    (base/'claims.jsonl').write_text('');(base/'grades.jsonl').write_text('')
    cell=evidence_cell(ledger=ledger)
    # Actual adapter lookup and readiness provider, no mocked family resolver.
    assert IOS._load_evidence_providers(tmp_path,{'engines':[cell]}) == {}

@pytest.mark.parametrize('family',['stock_desk','thematic_desk','demand_chain'])
def test_actual_provider_keeps_canonical_native_ledger(tmp_path,family):
    from engine.qledger_desk_adapter import native_ledger_for_family
    base=tmp_path/'data/qledger';base.mkdir(parents=True)
    (base/'claims.jsonl').write_text('');(base/'grades.jsonl').write_text('')
    cell=evidence_cell(ledger=native_ledger_for_family(family))
    assert IOS._load_evidence_providers(tmp_path,{'engines':[cell]})[cell['engine_id']]['family']==family

@pytest.mark.parametrize('scenario',['matched','zero','empty','mixed_clock','mixed_direction'])
def test_actual_owner_provider_detail_preserves_measurement_populations(monkeypatch,tmp_path,scenario):
    import importlib.util
    spec=importlib.util.spec_from_file_location('control_fixture',REPO/'tests/test_qledger_control_policy.py')
    owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    family='radar' if scenario=='mixed_direction' else 'stock_desk'
    claims=[];grades=[]
    if scenario=='matched':
        for asof in owner._dates(40):
            c=owner._claim(family=family,asof=asof,control=None,claim_id='pre|'+asof)
            claims.append(c);grades.append(owner._grade_row(c,subject_ret=-.05,control_ret=None,bench_ret=0.,hit=False))
        c,g=owner._cohort(family,30,controlled=30,start='2025-07-01');claims+=c;grades+=g
    elif scenario=='zero':
        claims,grades=owner._cohort(family,30,controlled=30,correct=False,start='2025-07-01')
    elif scenario=='mixed_clock':
        for unit,subject,bench in [('trading_days','AAPL','SPY'),('calendar_days','BTC-USD','BTC-USD')]:
            for asof in owner._dates(30,'2025-07-01'):
                c=owner._claim(family=family,asof=asof,unit=unit,subject=subject,bench=bench,claim_id=unit+'|'+asof)
                claims.append(c);grades.append(owner._grade_row(c))
    elif scenario=='mixed_direction':
        for direction,start in [(1,'2025-07-01'),(-1,'2025-08-01')]:
            c,g=owner._cohort(family,30,controlled=0,direction=direction,start=start);claims+=c;grades+=g
    owner._write_store(tmp_path,claims,grades)
    if family=='stock_desk':owner._start_clock(tmp_path,family,when='2025-06-01T00:00:00+00:00')
    cell=evidence_cell(ledger='qledger:'+family,ledger_evidence={'desk':family},validation_state='validated')
    registry={'engines':[cell],'excluded':[]}
    _record_owner_fixture(tmp_path,[family])
    provider=IOS._load_evidence_providers(tmp_path,registry)
    assert provider[cell['engine_id']]['read_status']=='partial'
    expected=owner.grader.compute_promotion_readiness(tmp_path,families=[family])[family]
    view={'outputs':[healthy_output(engine_id=cell['engine_id'])],'summary':{}}
    monkeypatch.setattr(IOS,'_derive',lambda *_a,**_k:(view,registry,provider,0.,'miss'))
    detail=IOS.engine_detail(cell['engine_id'],root=tmp_path)['engine']
    rows=detail['evidence_measurement']['by_horizon']
    for h,row in expected.items():
        if h.startswith('_'):continue
        for k,v in row.items():
            if k in rows[h] and k!='by_clock_basis':assert rows[h][k]==v
        assert rows[h]['benchmark_baseline_denominator'] is None
        for basis,sub in row.get('by_clock_basis',{}).items():
            for k,v in sub.items():
                if k in rows[h]['by_clock_basis'][basis]:assert rows[h]['by_clock_basis'][basis][k]==v
    row=rows['21']
    if scenario=='matched':
        assert row['n_dates']==30 and row['hit_rate'] is None
        assert row['benchmark_baseline_hit_rate']==pytest.approx(30/70,abs=1e-4)
        assert row['wilson_ci_low']>0
    elif scenario=='zero':assert row['wilson_ci_low']==0
    elif scenario=='empty':assert row['wilson_ci_low'] is None
    elif scenario=='mixed_clock':assert len(row['by_clock_basis'])==2 and row['wilson_ci_low'] is None
    elif scenario=='mixed_direction':assert row['excess_mean'] is None and len(row['excess_mean_by_direction'])==2
    assert detail['evidence_owner_scope']['qualified_task_scope'] is None


def _source_link_repo(tmp_path):
    import subprocess
    def git(*args):
        return subprocess.run(['git',*args],cwd=tmp_path,capture_output=True,text=True,check=True).stdout.strip()
    (tmp_path/'config').mkdir();(tmp_path/'config/qual_ladder.yml').write_text('fixture.key: {}\n')
    (tmp_path/'research').mkdir();(tmp_path/'research/FIXTURE_PREREG #1.md').write_text('Synthetic source declaration only\n')
    git('init');git('remote','add','origin','https://github.com/mastermindx-market-intelligence/macro.git');git('add','config','research')
    git('-c','user.name=Fixture','-c','user.email=fixture@invalid','commit','-m','synthetic source declaration')
    return git('rev-parse','HEAD')


def test_source_links_verify_immutable_declarations_and_reject_dirty_data(tmp_path):
    oid=_source_link_repo(tmp_path)
    links=IOS._source_document_links(tmp_path,['fixture.key','research/FIXTURE_PREREG #1.md','data/qledger/grades.jsonl','research/RESULTS.md'])
    assert len(links)==2 and all(x['revision']==oid for x in links)
    assert 'FIXTURE_PREREG%20%231.md' in links[1]['url']
    before=IOS._mtime_ns(tmp_path/'config/qual_ladder.yml')
    (tmp_path/'config/qual_ladder.yml').write_text('fixture.key: {changed: true}\n')
    assert IOS._source_document_links(tmp_path,['fixture.key'])==[]
    assert IOS._source_document_links(tmp_path,['research/FIXTURE_PREREG #1.md'],qualification_identity=before)==[]


def test_source_links_no_lazy_fetch_and_bounded_work(monkeypatch,tmp_path):
    import subprocess
    _source_link_repo(tmp_path)
    run=subprocess.run;calls=[]
    def inspect(args,**kw):
        calls.append((args,kw))
        assert kw['env']['GIT_NO_LAZY_FETCH']=='1' and kw['env']['GIT_OPTIONAL_LOCKS']=='0'
        assert 0<kw['timeout']<=3
        if args[1]=='show':return subprocess.CompletedProcess(args,128,b'',b'missing local blob')
        return run(args,**kw)
    monkeypatch.setattr(IOS.subprocess,'run',inspect)
    assert IOS._source_document_links(tmp_path,['research/FIXTURE_PREREG #1.md']*100)==[]
    assert len(calls)<=19


def test_source_links_reject_head_change_and_malformed_ladder(monkeypatch,tmp_path):
    import subprocess
    oid=_source_link_repo(tmp_path);run=subprocess.run;revisions=0
    def changed(args,**kw):
        nonlocal revisions
        if args[1:]==['rev-parse','HEAD']:
            revisions+=1
            if revisions>1:return subprocess.CompletedProcess(args,0,'0'*40+'\n','')
        return run(args,**kw)
    monkeypatch.setattr(IOS.subprocess,'run',changed)
    assert IOS._source_document_links(tmp_path,['fixture.key'])==[]
    (tmp_path/'config/qual_ladder.yml').write_text('broken: [')
    assert IOS._source_document_links(tmp_path,['fixture.key'])==[]


def test_actual_t1_version_change_invalidates_cache_without_inheriting_qualification(monkeypatch,tmp_path):
    from engine import intelligence_registry as ir
    from scripts import build_output_health as builder
    root=one_engine(tmp_path)
    base=root/'data/qledger';base.mkdir(parents=True,exist_ok=True)
    (base/'claims.jsonl').write_text('');(base/'grades.jsonl').write_text('')
    species_path=root/'data/species/registry.json';species_path.parent.mkdir(parents=True,exist_ok=True)
    doc={'meta':{},'artifacts':{'a':artifact('data/stock_desk/theses.jsonl',producer='engine/a.py',owner='prog-one',tier='shadow',asof_field=None,sla=None)}}
    eid='engine/a.py::prog-one'; builds=[]
    def actual_t1(root,**kwargs):
        species=json.loads(species_path.read_text())
        registry=ir.build_registry(synapse=doc,overlay={'schema_version':1,'engines':{eid:{'output_class':{'value':'predictive','rationale':'synthetic'}}}},species=species,file_exists=lambda _:True,qual_ladder_keys=set())
        builds.append(species[0]['version'])
        return {'outputs':[healthy_output(engine_id=eid)],'summary':{},'generated':{}},registry
    monkeypatch.setattr(builder,'build_with_registry',actual_t1)
    import importlib.util
    spec=importlib.util.spec_from_file_location('version_control_fixture',REPO/'tests/test_qledger_control_policy.py')
    owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    claims,grades=owner._cohort('stock_desk',30,controlled=30,start='2025-07-01')
    owner._write_store(root,claims,grades)
    owner._start_clock(root,'stock_desk',when='2025-06-01T00:00:00+00:00')
    from engine import qledger_evidence_clock
    qledger_evidence_clock.record_start('stock_desk',horizon_d=21,horizon_unit='trading_days',root=root,now='2025-06-01T00:00:00+00:00')
    _record_owner_fixture(root,['stock_desk'])
    before_clock={p:p.read_bytes() for p in (root/'data/qledger').rglob('*.json')}
    scopes=[];keys=[]
    for version,horizon in [('fixture-v1',20),('fixture-v2',126)]:
        species_path.write_text(json.dumps([{'species_id':'fixture-species','validation_status':'validated','version':version,'horizon_class':str(horizon),'regime_scope':['synthetic-'+version],'ledger_binding':{'ledger':'data/stock_desk/theses.jsonl'}}]))
        keys.append(IOS._dependency_key(root))
        panel=IOS.panel(root=root);detail=IOS.engine_detail(eid,root=root)['engine']
        row=next(x for x in panel['engines'] if x['engine_id']==eid)
        assert row['evidence_status']==detail['evidence_status']=='Degraded'
        assert detail['evidence_owner_scope']['reason']=='owner_validation_scope_unqualified'
        assert detail['evidence_owner_scope']['qualified_task_scope'] is None
        assert detail['evidence_provider']['binding']=='adapter:stock_desk'
        assert detail['evidence_measurement']['by_horizon']['21']['n_dates']==30
        assert detail['evidence_measurement']['by_horizon']['21']['wilson_ci_low']>0
        scopes.append(detail['evidence_owner_scope']['bound_species'][0]['owner_scope'])
    assert keys[0]!=keys[1] and builds==['fixture-v1','fixture-v2']
    assert scopes[0]['version']=='fixture-v1' and scopes[1]['version']=='fixture-v2'
    assert scopes[0]['regime_scope']!=scopes[1]['regime_scope']
    assert {p:p.read_bytes() for p in (root/'data/qledger').rglob('*.json')}==before_clock


def test_source_link_overall_deadline_and_document_byte_limit(monkeypatch,tmp_path):
    _source_link_repo(tmp_path)
    real_clock=IOS.time.monotonic
    # The deadline must cover all git calls collectively, not restart per ref.
    ticks=iter([0.,0.,4.])
    monkeypatch.setattr(IOS.time,'monotonic',lambda:next(ticks))
    assert IOS._source_document_links(tmp_path,['fixture.key'])==[]
    monkeypatch.setattr(IOS.time,'monotonic',real_clock)
    (tmp_path/'config/qual_ladder.yml').write_text('x' * 262145)
    assert IOS._source_document_links(tmp_path,['research/FIXTURE_PREREG #1.md'])==[]


def test_source_link_rejects_large_local_head_blob_before_reading_body(monkeypatch,tmp_path):
    import subprocess
    _source_link_repo(tmp_path)
    path=tmp_path/'research/FIXTURE_PREREG #1.md'
    path.write_text('x'*262145)
    for args in [['git','add','research'],['git','-c','user.name=Fixture','-c','user.email=fixture@invalid','commit','-m','synthetic large declaration']]:
        subprocess.run(args,cwd=tmp_path,capture_output=True,check=True)
    path.write_text('small dirty working source\n')
    run=subprocess.run;calls=[]
    def inspected(args,**kwargs):
        calls.append(args)
        assert args[1]!='show','large HEAD body must not be captured'
        return run(args,**kwargs)
    monkeypatch.setattr(IOS.subprocess,'run',inspected)
    assert IOS._source_document_links(tmp_path,['research/FIXTURE_PREREG #1.md'])==[]
    assert any(a[1:3]==['cat-file','-s'] for a in calls)


def _recorded_snapshot(root, payload=None, receipt=None):
    if payload is None:
        payload={'stock_desk':{'21':{'n_dates':30,'needed':25,'ready':True,'wilson_ci_low':0,'hit_rate':None,'evidence_basis':'matched_control','clock_basis':'explicit_unit_v1:trading_days:US','n_controlled_dates':30,'n_cohort_rows':70,'n_controlled_rows':30,'control_coverage':30/70,'benchmark_baseline_hit_rate':0,'benchmark_baseline_excess_mean':None,'benchmark_baseline_excess_basis':'magnitude_only','benchmark_baseline_excess_mean_by_direction':{'1':0,'-1':-.1}}}}
    path=root/'site/qledger/track_record.json';path.parent.mkdir(parents=True,exist_ok=True)
    doc={'promotion_readiness':payload,'promotion_readiness_at':'2026-10-12T20:00:00+00:00'}
    if receipt is not None:doc['promotion_readiness_receipt']=receipt
    path.write_text(json.dumps(doc));return path,payload


def test_recorded_owner_snapshot_never_computes_or_reads_corpus(monkeypatch,tmp_path):
    from engine import qledger as q
    from scripts import grade_qledger as grader
    path,payload=_recorded_snapshot(tmp_path)
    def forbidden(*a,**k):raise AssertionError('request-time corpus/grade work')
    monkeypatch.setattr(grader,'compute_promotion_readiness',forbidden)
    monkeypatch.setattr(q,'load_claims',forbidden);monkeypatch.setattr(q,'load_grades',forbidden)
    cell=evidence_cell(ledger='data/stock_desk/theses.jsonl',validation_state='validated')
    provider=IOS._load_evidence_providers(tmp_path,{'engines':[cell]})[cell['engine_id']]
    assert provider['readiness']==payload['stock_desk']
    assert provider['read_status']=='partial'
    assert provider['recorded_snapshot']['recorded_at']=='2026-10-12T20:00:00+00:00'
    assert provider['recorded_snapshot']['evaluation_date'] is None
    assert provider['recorded_snapshot']['current_source_qualification']=='unavailable'
    result=IOS.derive_evidence_status(cell,[healthy_output()],provider)
    assert result['evidence_status']=='Degraded'
    assert result['evidence_owner_scope']['owner_lifecycle']=='validated'
    assert result['evidence_measurement']['by_horizon']['21']['wilson_ci_low']==0
    assert result['evidence_measurement']['by_horizon']['21']['hit_rate'] is None
    assert result['evidence_measurement']['by_horizon']['21']['benchmark_baseline_hit_rate']==0
    assert result['evidence_owner_scope']['qualified_task_scope'] is None


@pytest.mark.parametrize('bad',[None,[],{'stock_desk':{'21':{'n_dates':True}}},{'stock_desk':{'21':{'n_dates':2,'ready':'yes'}}},{'stock_desk':{'21':{'n_dates':2,'hit_rate':float('inf')}}},{'stock_desk':{'21':{'n_dates':2,'by_clock_basis':[]}}}])
def test_malformed_recorded_snapshot_is_wholly_unavailable_without_compute(monkeypatch,tmp_path,bad):
    from scripts import grade_qledger
    monkeypatch.setattr(grade_qledger,'compute_promotion_readiness',lambda *_a,**_k:pytest.fail('must not grade'))
    path,_=_recorded_snapshot(tmp_path)
    path.write_text(json.dumps({'promotion_readiness':bad}))
    assert IOS._read_owner_readiness_snapshot(tmp_path)['readiness']=={}


def test_snapshot_missing_and_corrupt_bytes_do_not_grade(monkeypatch,tmp_path):
    from scripts import grade_qledger
    monkeypatch.setattr(grade_qledger,'compute_promotion_readiness',lambda *_a,**_k:pytest.fail('must not grade'))
    assert IOS._read_owner_readiness_snapshot(tmp_path)['context']['available'] is False
    path,_=_recorded_snapshot(tmp_path);path.write_bytes(b'\xff\xfe')
    assert IOS._read_owner_readiness_snapshot(tmp_path)['context']['available'] is False


def test_snapshot_limit_applies_to_actual_read_and_generation_race(monkeypatch,tmp_path):
    path,_=_recorded_snapshot(tmp_path)
    monkeypatch.setattr(IOS,'_OWNER_READINESS_MAX_BYTES',32)
    assert IOS._read_owner_readiness_snapshot(tmp_path)['context']['available'] is False
    monkeypatch.setattr(IOS,'_OWNER_READINESS_MAX_BYTES',16*1024*1024)
    real=IOS._mtime_ns;calls=0
    def changed(p):
        nonlocal calls
        value=real(p);calls+=1
        return (*value[:-1],value[-1]+calls) if value is not None and calls>1 else value
    monkeypatch.setattr(IOS,'_mtime_ns',changed)
    assert IOS._read_owner_readiness_snapshot(tmp_path)['context']['available'] is False


@pytest.mark.parametrize('kind',['fifo','directory','symlink','replace_fifo'])
def test_snapshot_reader_refuses_nonregular_and_preopen_replacement(monkeypatch,tmp_path,kind):
    import os
    path,_=_recorded_snapshot(tmp_path)
    if kind=='directory':path.unlink();path.mkdir()
    elif kind=='fifo':path.unlink();os.mkfifo(path)
    elif kind=='symlink':other=tmp_path/'regular.json';other.write_bytes(path.read_bytes());path.unlink();path.symlink_to(other)
    else:
        original=IOS.os.open
        def replace(p,*args,**kwargs):
            if Path(p)==path:path.unlink();os.mkfifo(path)
            return original(p,*args,**kwargs)
        monkeypatch.setattr(IOS.os,'open',replace)
    assert IOS._read_owner_readiness_snapshot(tmp_path)['context']['available'] is False


def test_normal_owner_receipt_named_generation_is_not_current_qualification(tmp_path):
    from scripts import grade_qledger as grader
    base=tmp_path/'data/qledger';base.mkdir(parents=True)
    (base/'claims.jsonl').write_text('');(base/'grades.jsonl').write_text('')
    (tmp_path/'site/qledger').mkdir(parents=True)
    result=grader.run_readiness_post_step(tmp_path,0,0,today='2026-10-12')
    assert 'error' not in result
    read=IOS._read_owner_readiness_snapshot(tmp_path)
    assert read['context']['receipt_status']=='recorded_provenance'
    assert read['context']['named_generation_match'] is True
    assert read['context']['current_source_qualification']=='unavailable'
    assert read['context']['all_inputs_qualification']=='unavailable'
    assert read['context']['evaluation_date']=='2026-10-12'
    assert 'quote_prices' in read['context']['excluded_scope']
    assert str(tmp_path) not in json.dumps(read['context'])


@pytest.mark.parametrize('mutation',['schema','producer','payload','families','cross_host','grades','clock','config','code'])
def test_recorded_receipt_mismatch_retains_values_and_never_qualifies(tmp_path,mutation):
    from scripts import grade_qledger as grader
    base=tmp_path/'data/qledger';base.mkdir(parents=True)
    (base/'claims.jsonl').write_text('');(base/'grades.jsonl').write_text('')
    (tmp_path/'site/qledger').mkdir(parents=True)
    assert 'error' not in grader.run_readiness_post_step(tmp_path,0,0,today='2026-10-12')
    path=tmp_path/'site/qledger/track_record.json';doc=json.loads(path.read_text());before=doc['promotion_readiness'];receipt=doc['promotion_readiness_receipt']
    if mutation=='schema':receipt['schema']='unknown'
    elif mutation=='producer':receipt['producer']='other'
    elif mutation=='payload':receipt['payload_digest']='0'*64
    elif mutation=='families':receipt['source_generation']['families']=[]
    elif mutation=='cross_host':receipt['source_generation']['host_scope_digest']='0'*64
    elif mutation=='code':receipt['source_generation']['owner_code']['engine/qledger.py']['sha256']='0'*64
    elif mutation=='grades':(base/'grades.jsonl').write_text('\n')
    elif mutation=='clock':
        from engine import qledger_evidence_clock
        qledger_evidence_clock.record_start('stock_desk',horizon_d=21,horizon_unit='trading_days',root=tmp_path,now='2026-10-12T20:00:00+00:00')
    elif mutation=='config':
        (tmp_path/'config').mkdir(exist_ok=True);(tmp_path/'config/qual_ladder.yml').write_text('changed: true\n')
    if mutation in ['schema','producer','payload','families','cross_host','code']:path.write_text(json.dumps(doc))
    read=IOS._read_owner_readiness_snapshot(tmp_path)
    assert read['readiness']==before and read['context']['named_generation_match'] is False
    assert read['context']['current_source_qualification']=='unavailable'


def test_published_snapshot_update_invalidates_existing_derive_identity(tmp_path):
    first=IOS._dependency_key(tmp_path)
    path,_=_recorded_snapshot(tmp_path)
    second=IOS._dependency_key(tmp_path)
    assert first!=second
    doc=json.loads(path.read_text());doc['promotion_readiness']['stock_desk']['21']['n_dates']=31;path.write_text(json.dumps(doc))
    assert IOS._dependency_key(tmp_path)!=second


def test_native_current_generation_comparison_is_deferred_without_snapshot_materialization(monkeypatch,tmp_path):
    from scripts import grade_qledger as grader
    from engine import qledger_store
    base=tmp_path/'data/qledger';base.mkdir(parents=True)
    (base/'claims.jsonl').write_text('');(base/'grades.jsonl').write_text('')
    (tmp_path/'site/qledger').mkdir(parents=True)
    assert 'error' not in grader.run_readiness_post_step(tmp_path,0,0,today='2026-10-12')
    monkeypatch.setattr(qledger_store,'uses_native_claims',lambda *_a,**_k:True)
    monkeypatch.setattr(grader,'readiness_source_generation',lambda *_a,**_k:pytest.fail('native corpus must not be materialized for comparison'))
    read=IOS._read_owner_readiness_snapshot(tmp_path)
    assert read['context']['available'] is True
    assert read['context']['named_generation_match'] is False
    assert read['context']['named_generation_check']=='native_comparison_deferred'
    assert read['context']['current_source_qualification']=='unavailable'


@pytest.mark.parametrize(('field','value'),[('hit_rate',1.5),('wilson_ci_low',-.1),('control_coverage',2.),('benchmark_baseline_hit_rate',-.01)])
def test_recorded_owner_fraction_bounds_reject_whole_snapshot(tmp_path,field,value):
    path,payload=_recorded_snapshot(tmp_path)
    payload['stock_desk']['21'][field]=value
    path.write_text(json.dumps({'promotion_readiness':payload}))
    assert IOS._read_owner_readiness_snapshot(tmp_path)['context']['available'] is False


def test_recorded_fraction_endpoints_and_signed_negative_excess_remain_exact():
    payload={'stock_desk':{'21':{'n_dates':2,'needed':25,'ready':False,'hit_rate':0,'wilson_ci_low':1,'control_coverage':0,'benchmark_baseline_hit_rate':1,'excess_mean':-.15,'excess_mean_by_direction':{'-1':-.15}}}}
    assert IOS._valid_recorded_readiness(payload) is True


@pytest.mark.parametrize('row',[{'unknown':1},{'n_dates':2},{'n_dates':2,'needed':25},{}])
def test_recorded_owner_row_requires_actual_minimal_contract(row):
    assert IOS._valid_recorded_readiness({'stock_desk':{'21':row}}) is False


def test_recorded_explicit_null_support_is_unknown_not_fabricated_immaturity():
    row={'n_dates':None,'needed':None,'ready':None}
    assert IOS._valid_recorded_readiness({'stock_desk':{'21':row}}) is True
    provider={'kind':'qledger','read_status':'partial','readiness':{'21':row},'recorded_snapshot':{'available':True,'current_source_qualification':'unavailable'}}
    result=IOS.derive_evidence_status(evidence_cell(),[healthy_output()],provider)
    assert result['evidence_status']=='Degraded'
    assert 'insufficient_maturity' not in result['evidence_reason_codes']
    assert result['evidence_maturity']['rungs']['21']['n_dates'] is None
    assert result['evidence_maturity']['rungs']['21']['ready'] is None
