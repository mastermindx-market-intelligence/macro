"""Publication-path regression tests for the macro workspace builder (F01 / R1A).

Adversarial review round 1, finding F5: exercise ``engine.market_os.macro_workspaces.build``
end-to-end into a tmp dir, and the CLI's exit-code contract (finding F4). Also
carries F2's determinism-under-code_version-churn test (F2's own fix lives in
``contract.py``; this is the publish-path proof of it).

    python3 -m pytest tests/test_macro_workspace_build.py -x -q
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.market_os.macro_workspaces import build, contract, liquidity_regime  # noqa: E402
from engine.market_os.macro_workspaces.history import (  # noqa: E402
    MAX_POINTS, SOURCES, attach_workspace_history, load_economic_histories, project_source,
)
from lib.macro_suite_view import build_view  # noqa: E402
from scripts.build_macro_suite_pages import SUITE_PAGES, SnapshotRefused, read_workspace  # noqa: E402

BUILT_AT = "2026-09-04T00:00:00Z"


def _base_regime() -> dict:
    return {
        "asof": "2026-09-03", "date": "2026-09-03",
        "liquidity_overlay": "contracting",
        "liquidity_quality": {
            "asof": "2026-09-03", "label": "contracting", "quantity_roc_bn": -165.3,
            "rrp_buffer_bn": 6.7, "rrp_exhausted": True,
            "composition": {"mechanical": True},
            "stress_overlay": {"confirming_stress": False, "hy_oas_z": -0.2, "hy_oas_pct": 2.66},
            "walcl_stale_days": 1, "degraded": False,
        },
        "conditions": {
            "stale_inputs": [],
            "vintages": {
                "nfci": {"asof": "2026-08-28", "stale": False},
                "ofr_fsi": {"asof": "2026-08-30", "stale": False},
                "hy_oas": {"asof": "2026-09-02", "stale": False},
            },
            "financial_conditions": {"nfci": -0.558, "nfci_pctile": 0.046},
            "systemic_stress": {"ofr_fsi": -2.749, "ofr_fsi_pctile": 0.0278},
        },
        "regime_vector": {"rate_pressure_rates_scare_score": 43.2,
                          "rate_pressure_real10y_chg63_bp": 24.0},
    }


def _write_regime(tmp_path: Path) -> Path:
    p = tmp_path / "regime_latest.json"
    p.write_text(json.dumps(_base_regime()), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# F5(a): atomic publish leaves exactly the two files, valid, hash-matched
# --------------------------------------------------------------------------- #
def test_atomic_publish_leaves_exactly_two_valid_hash_matched_files(tmp_path) -> None:
    regime_path = _write_regime(tmp_path)
    out_root = tmp_path / "out"
    receipt = build.build_liquidity_regime(
        regime_latest_path=regime_path, out_root=out_root, built_at=BUILT_AT, write=True,
    )
    files = sorted(p.relative_to(out_root).as_posix() for p in out_root.rglob("*") if p.is_file())
    assert files == ["workspaces/liquidity_regime/US/latest.json", "workspaces/manifest.json"]

    body = json.loads((out_root / "workspaces" / "liquidity_regime" / "US" / "latest.json")
                       .read_text(encoding="utf-8"))
    contract.validate(body)  # must not raise: real schema + hash validity
    assert body["generation"]["content_sha256"] == receipt["digest"]

    manifest = json.loads((out_root / "workspaces" / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest["workspaces"]["liquidity_regime/US"]
    assert entry["content_sha256"] == receipt["digest"]
    assert entry["generation_id"] == body["generation"]["generation_id"]


# --------------------------------------------------------------------------- #
# F5(b): body written before manifest
# --------------------------------------------------------------------------- #
def test_body_written_before_manifest(tmp_path, monkeypatch) -> None:
    regime_path = _write_regime(tmp_path)
    out_root = tmp_path / "out"
    calls: list[str] = []
    original = build._atomic_write_bytes

    def _spy(path, data):
        calls.append(str(path))
        return original(path, data)

    monkeypatch.setattr(build, "_atomic_write_bytes", _spy)
    build.build_liquidity_regime(
        regime_latest_path=regime_path, out_root=out_root, built_at=BUILT_AT, write=True,
    )
    assert len(calls) == 2
    assert calls[0].endswith(str(Path("workspaces") / "liquidity_regime" / "US" / "latest.json"))
    assert calls[1].endswith(str(Path("workspaces") / "manifest.json"))


# --------------------------------------------------------------------------- #
# F5(c): manifest per-workspace hash equals the recomputed body digest
# --------------------------------------------------------------------------- #
def test_manifest_hash_matches_recomputed_body_digest(tmp_path) -> None:
    regime_path = _write_regime(tmp_path)
    out_root = tmp_path / "out"
    receipt = build.build_liquidity_regime(
        regime_latest_path=regime_path, out_root=out_root, built_at=BUILT_AT, write=True,
    )
    body = json.loads(Path(receipt["paths"]["workspace"]).read_text(encoding="utf-8"))
    manifest = json.loads(Path(receipt["paths"]["manifest"]).read_text(encoding="utf-8"))
    recomputed = contract.content_digest(body)
    assert body["generation"]["content_sha256"] == recomputed
    assert manifest["workspaces"]["liquidity_regime/US"]["content_sha256"] == recomputed


# --------------------------------------------------------------------------- #
# F5(d) / F2: identical owner input + built_at, different code_version ->
# identical digest and generation_id (code_version stays published as
# provenance, it is simply excluded from the hash).
# --------------------------------------------------------------------------- #
def test_code_version_does_not_affect_digest_or_generation_id(tmp_path) -> None:
    regime_path = _write_regime(tmp_path)
    receipt_a = build.build_liquidity_regime(
        regime_latest_path=regime_path, out_root=tmp_path / "out_a",
        built_at=BUILT_AT, code_version="commit-aaaaaaa", write=True,
    )
    receipt_b = build.build_liquidity_regime(
        regime_latest_path=regime_path, out_root=tmp_path / "out_b",
        built_at=BUILT_AT, code_version="commit-bbbbbbb", write=True,
    )
    assert receipt_a["digest"] == receipt_b["digest"]
    assert (receipt_a["snapshot"]["generation"]["generation_id"]
            == receipt_b["snapshot"]["generation"]["generation_id"])
    # code_version itself still differs in the published body (kept as provenance)
    assert receipt_a["snapshot"]["generation"]["code_version"] == "commit-aaaaaaa"
    assert receipt_b["snapshot"]["generation"]["code_version"] == "commit-bbbbbbb"


# --------------------------------------------------------------------------- #
# F4: CLI exit-code contract
# --------------------------------------------------------------------------- #
_CLI_PATH = ROOT / "scripts" / "build_macro_workspaces.py"
_CLI_SPEC = importlib.util.spec_from_file_location("build_macro_workspaces_cli", _CLI_PATH)
cli = importlib.util.module_from_spec(_CLI_SPEC)
_CLI_SPEC.loader.exec_module(cli)  # type: ignore[union-attr]


def _fake_receipt(availability_state: str) -> dict:
    snap = {
        "generation": {"generation_id": "liquidity_regime-US-deadbeefdeadbeef",
                        "code_version": "deadbeef"},
        "headline": {
            "state_id": "C",
            "state_label": {"en": "Easy funding / Weak support"},
            "quadrant": {"x": 10.0, "y": 20.0},
            "one_month_vector": {"dx": None, "dy": None, "status": "ABSENT", "null_reason": "WARMUP", "x_axis_id": None, "y_axis_id": None},
        },
        "availability": {"state": availability_state, "contradiction": {"present": False}},
    }
    return {"snapshot": snap, "digest": "a" * 64, "bytes": 123, "manifest": {},
            "paths": {"workspace": None, "manifest": None}}


def _fake_receipts(availability_state: str) -> dict:
    # The CLI consumes build_all()'s receipts shape: one entry per built
    # workspace plus the "_manifest" bookkeeping entry.
    return {
        "liquidity_regime/US": _fake_receipt(availability_state),
        "_manifest": {"manifest": {}, "path": None},
    }


def test_cli_main_returns_0_when_current(monkeypatch) -> None:
    monkeypatch.setattr(cli._build, "build_all", lambda **kw: _fake_receipts("CURRENT"))
    assert cli.main(["--no-write"]) == 0


def test_cli_main_returns_0_when_late_within_tolerance(monkeypatch) -> None:
    monkeypatch.setattr(cli._build, "build_all",
                        lambda **kw: _fake_receipts("LATE_WITHIN_TOLERANCE"))
    assert cli.main(["--no-write"]) == 0


def test_cli_main_returns_2_when_typed_degraded(monkeypatch) -> None:
    monkeypatch.setattr(cli._build, "build_all",
                        lambda **kw: _fake_receipts("STALE_SOURCE"))
    assert cli.main(["--no-write"]) == 2


def test_cli_main_returns_2_when_any_one_workspace_is_degraded(monkeypatch) -> None:
    # Suite-wide worst-state law: one degraded workspace among healthy ones
    # still exits 2 -- a green exit must mean every published workspace is usable.
    receipts = _fake_receipts("CURRENT")
    receipts["growth_real_economy/US"] = _fake_receipt("SOURCE_FAILED")
    monkeypatch.setattr(cli._build, "build_all", lambda **kw: receipts)
    assert cli.main(["--no-write"]) == 2


def test_cli_main_returns_1_on_hard_failure(monkeypatch, capsys) -> None:
    def _boom(**kw):
        raise RuntimeError("owner artifact missing")

    monkeypatch.setattr(cli._build, "build_all", _boom)
    rc = cli.main(["--no-write"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err
    assert "owner artifact missing" in err


def test_cli_help_documents_exit_codes(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Exit codes" in out
    assert "typed-degraded" in out


# Existing publication-path CI also owns collector history -> native view proof.
HISTORY_BUILT_AT = "2026-11-14T12:00:00Z"


def test_component_rows_preserve_gaps_units_and_source_clocks():
    projection = project_source(SOURCES["WALCL"], [
        ("2026-11-12", 6000000), ("2026-10-29", 6100000), ("2026-11-05", None),
    ], built_at=HISTORY_BUILT_AT)
    assert projection["entry"]["points"] == [
        {"t": "2026-10-29", "v": 6100.0}, {"t": "2026-11-05", "v": None},
        {"t": "2026-11-12", "v": 6000.0},
    ]
    assert projection["entry"]["source_ref"] == projection["source"]["source_id"]
    assert projection["entry"]["basis"] == "latest_revised_observation_history"
    assert projection["source"]["released_at"] is None
    assert projection["source"]["first_known_at"] is None
    assert projection["source"]["collected_at"] is None


@pytest.mark.parametrize("rows", [
    [("2026-11-12", float("inf"))], [("2026-11-12", float("nan"))],
    [("2026-11-12", True)], [("2026-11-12", "3.5")],
    [("2026-02-30", 2)], [("2026-11-15", 2)],
    [("2026-11-12", 2), ("2026-11-12", 3)],
])
def test_invalid_observations_fail_closed(rows):
    with pytest.raises(ValueError):
        project_source(SOURCES["CPIAUCSL"], rows, built_at=HISTORY_BUILT_AT)


def test_tail_bound_is_real_observations_not_downsampling():
    first = dt.date(2020, 1, 1)
    rows = [((first + dt.timedelta(days=i)).isoformat(), i) for i in range(1000)]
    result = project_source(SOURCES["EFFR"], rows, built_at=HISTORY_BUILT_AT)["entry"]
    assert len(result["points"]) == MAX_POINTS
    assert result["points"][0]["v"] == 1000 - MAX_POINTS
    assert result["points"][-1]["v"] == 999
    assert result["freshness"] == "STALE_SOURCE"


def test_batch_reads_once_and_preserves_missing_siblings():
    seen = []
    def reader(path, column):
        seen.append(path)
        return [("2026-11-12", 10)] if path.stem == "INDPRO" else None
    batch = load_economic_histories(fred_dir="fixtures/fred", treasury_dir="fixtures/treasury", built_at=HISTORY_BUILT_AT, reader=reader)
    assert len(seen) == len(set(seen)) == len(SOURCES)
    assert batch["business_activity"]["series"]["status"] == "PARTIAL"
    assert batch["growth_real_economy"]["series"]["status"] == "PARTIAL"
    assert batch["labor_markets"]["series"]["status"] == "ABSENT"
    assert batch["business_activity"]["series"]["items"][0]["points"][0]["v"] == 10


def test_attachment_preserves_current_state_and_deterministic_digest():
    body = liquidity_regime.compose({}, built_at=HISTORY_BUILT_AT)
    original = copy.deepcopy(body)
    batch = load_economic_histories(fred_dir="unused", treasury_dir="unused", built_at=HISTORY_BUILT_AT,
                                    reader=lambda p, c: [("2026-11-12", 20)])
    attached = attach_workspace_history(body, batch["liquidity_regime"])
    assert body == original
    for key in ["headline", "axes", "metrics", "availability", "authority", "changes"]:
        assert attached[key] == original[key]
    sealed = contract.finalize(attached)
    contract.validate(sealed)
    shifted = copy.deepcopy(attached)
    shifted["generation"]["built_at"] = "2026-11-14T13:00:00Z"
    assert contract.content_digest(shifted) == sealed["generation"]["content_sha256"]
    with pytest.raises(ValueError, match="existing series owner"):
        attach_workspace_history(attached, batch["liquidity_regime"])


def test_real_parquet_publication_manifest_and_view_keep_null_points(tmp_path):
    fred = tmp_path / "fred"
    fred.mkdir()
    pd.DataFrame({"headline_cpi": [300.0, float("nan"), 301.5]},
                 index=pd.to_datetime(["2026-08-01", "2026-09-01", "2026-10-01"])).to_parquet(fred / "CPIAUCSL.parquet")
    regime = tmp_path / "regime.json"
    regime.write_text("{}", encoding="utf-8")
    out = tmp_path / "macrodata"
    build.build_all(regime_latest_path=regime, fred_dir=fred, treasury_dir=tmp_path / "treasury",
                    out_root=out, built_at=HISTORY_BUILT_AT)
    page = next(page for page in SUITE_PAGES if page.workspace_id == "inflation_system")
    snapshot, artifact = read_workspace(out, page)
    contract.validate(snapshot)
    view = build_view(snapshot, page_built_at=HISTORY_BUILT_AT, artifact=artifact)
    entry = view["series"]["entries"][0]
    assert entry["points"] == [
        {"t": "2026-08-01", "v": 300.0}, {"t": "2026-09-01", "v": None},
        {"t": "2026-10-01", "v": 301.5},
    ]
    assert entry["count"] == 2 and view["series"]["absent"] is False
    assert entry["unit_token"] == "cpi_index"
    assert "reference dates" in entry["basis"]["en"]
    assert entry["source_ref"] in {row["source_id"] for row in view["evidence"]["sources"]}
    assert artifact["sha256"] == snapshot["generation"]["content_sha256"]
    # The reader, not the client chart, detects tampering with the published body.
    body_path = out / "workspaces" / "inflation_system" / "US" / "latest.json"
    tampered = json.loads(body_path.read_text())
    tampered["series"]["items"][0]["points"][0]["v"] = 0
    body_path.write_text(json.dumps(tampered))
    with pytest.raises(SnapshotRefused):
        read_workspace(out, page)


def test_unreadable_existing_history_aborts_before_publication(tmp_path):
    fred = tmp_path / "fred"
    fred.mkdir()
    (fred / "CPIAUCSL.parquet").write_text("corrupted collector file")
    regime = tmp_path / "regime.json"
    regime.write_text("{}")
    out = tmp_path / "macrodata"
    from pyarrow import ArrowInvalid
    with pytest.raises(ArrowInvalid):
        build.build_all(regime_latest_path=regime, fred_dir=fred, treasury_dir=tmp_path / "treasury",
                        out_root=out, built_at=HISTORY_BUILT_AT)
    assert not (out / "workspaces" / "manifest.json").exists()


def test_gdpnow_quarter_reference_does_not_claim_update_freshness():
    result = project_source(SOURCES["GDPNOW"], [("2026-10-01", 3.481)], built_at=HISTORY_BUILT_AT)
    assert result["entry"]["freshness"] == "CURRENT"
    assert result["source"]["collected_at"] is None
    assert result["source"]["released_at"] is None
    assert "source-update freshness" in result["source"]["transform"]
    assert "Federal Reserve Bank of Atlanta" in result["source"]["provider"]
    assert result["source"]["owner_ref"] == "https://fred.stlouisfed.org/series/GDPNOW"
    assert result["entry"]["unit"] == "percent_saar"


def test_history_age_and_attribution_are_visible_in_series_and_evidence():
    body = liquidity_regime.compose({}, built_at=HISTORY_BUILT_AT)
    batch = load_economic_histories(fred_dir="unused", treasury_dir="unused", built_at=HISTORY_BUILT_AT,
                                    reader=lambda p, c: [("2026-11-12", 20)])
    sealed = contract.finalize(attach_workspace_history(body, batch["liquidity_regime"]))
    view = build_view(sealed, page_built_at=HISTORY_BUILT_AT, artifact={})
    row = view["series"]["entries"][0]
    source = next(row for row in view["evidence"]["sources"] if row["source_id"] == "history:fred:WALCL")
    assert "Reference period" in row["freshness"]["en"]
    assert "Reference period" in source["freshness"]["en"]
    assert "attribution" in source["rights"]["en"]


def test_curve_comparison_dates_belong_to_the_exact_values_and_skip_nulls():
    from lib.macro_suite_view import _curve_hero

    snapshot = {"availability": {"state": "CURRENT"}, "series": {"items": [
        {"series_id": "us10y", "points": [
            {"t": "2026-07-01", "v": 4.0},
            {"t": "2026-08-20", "v": 4.1},
            {"t": "2026-09-07", "v": 4.2},
            {"t": "2026-09-08", "v": None},
            {"t": "2026-09-09", "v": 4.3},
        ]},
        {"series_id": "us2y", "points": [{"t": "2026-09-09", "v": 4.4}]},
    ]}}
    rows = {row["tenor"]: row for row in _curve_hero(snapshot)["tenors"]}
    assert (rows["10y"]["prior_close"], rows["10y"]["prior_close_as_of"]) == (4.2, "2026-09-07")
    assert (rows["10y"]["prior_month"], rows["10y"]["prior_month_as_of"]) == (4.0, "2026-07-01")
    for tenor in ("2y", "30y"):
        for window in ("prior_close", "prior_month"):
            assert rows[tenor][window] is None and rows[tenor][f"{window}_as_of"] is None


# Payroll: source cohort -> canonical same-vintage truth -> publication -> view.
_PAYROLL_ROWS = [
    ("2024-11-01", "2024-12-06", "9999-12-31", 158800.0),
    ("2024-12-01", "2025-01-10", "2025-02-06", 158900.0),
    ("2024-12-01", "2025-02-07", "2025-03-06", 159000.0),
    ("2025-01-01", "2025-02-07", "2025-03-06", 159057.0),
    ("2024-12-01", "2025-03-07", "9999-12-31", 159010.0),
    ("2025-01-01", "2025-03-07", "9999-12-31", 159040.0),
    ("2025-02-01", "2025-03-07", "9999-12-31", 159151.0),
]


def _write_payroll_cohort(tmp_path, rows=None, *, frame=None):
    folder = tmp_path / "release_targets"
    folder.mkdir(parents=True, exist_ok=True)
    if frame is None:
        frame = pd.DataFrame(_PAYROLL_ROWS if rows is None else rows,
                             columns=["period", "realtime_start", "realtime_end", "value"])
        frame["series"], frame["source_output_type"] = "PAYEMS", 2
    path = folder / "PAYEMS_all_vintages.parquet"
    frame.to_parquet(path, index=False)
    data = path.read_bytes()
    manifest = {
        "schema": "release_target_vintage_collection.v1", "integrity_profile": "release_target_artifact_sha256_bytes.v1",
        "status": "ok", "source_output_type": 2,
        "collected_at": "2025-04-01T09:00:00+00:00", "completed_at": "2025-04-01T09:00:01+00:00",
        "series": {"PAYEMS": {"status": "written", "path": "data/fred_vintage/release_targets/PAYEMS_all_vintages.parquet",
                              "artifact_sha256": hashlib.sha256(data).hexdigest(), "artifact_bytes": len(data),
                              "rows": len(frame), "periods": int(frame["period"].nunique()),
                              "release_dates": int(frame["realtime_start"].nunique()),
                              "period_min": frame["period"].min(), "period_max": frame["period"].max()}},
    }
    (folder / "manifest.json").write_text(json.dumps(manifest))
    return folder


def _read_payroll(folder, cutoff="2025-03-15"):
    from engine.market_os.macro_workspaces.payroll_revision_sources import load_payroll_revisions
    return load_payroll_revisions(folder, built_at="2025-04-15T12:00:00Z", as_of=cutoff)


def test_payroll_same_vintage_changes_and_net_revision_preserve_cutoff(tmp_path):
    folder = _write_payroll_cohort(tmp_path)
    result = _read_payroll(folder)
    january = next(row for row in result["rows"] if row["period"] == "2025-01-01")
    assert january == {"period": "2025-01-01", "earliest_change": 57.0, "selected_change": 30.0,
                       "net_revision": -27.0, "earliest_vintage": "2025-02-07", "selected_vintage": "2025-03-07"}
    assert result["collected_at"] == "2025-04-01T09:00:00+00:00"
    before = _read_payroll(folder, "2025-02-06")
    assert all(row["period"] < "2025-01-01" for row in before["rows"])
    on = _read_payroll(folder, "2025-02-07")
    january = next(row for row in on["rows"] if row["period"] == "2025-01-01")
    assert january["selected_change"] == 57.0 and january["net_revision"] == 0
    assert "realtime_end" not in json.dumps(result)


def test_future_vintage_addition_changes_no_cutoff_economic_projection(tmp_path):
    original = _read_payroll(_write_payroll_cohort(tmp_path / "before"))
    rows = [(p, start, "2025-04-03" if start == "2025-03-07" else end, value)
            for p, start, end, value in _PAYROLL_ROWS]
    rows += [("2025-01-01", "2025-04-04", "9999-12-31", 180000.0),
             ("2024-12-01", "2025-04-04", "9999-12-31", 170000.0),
             ("2025-03-01", "2025-04-04", "9999-12-31", 190000.0)]
    later = _read_payroll(_write_payroll_cohort(tmp_path / "after", rows))
    assert later["rows"] == original["rows"]
    assert later["source_digest"] != original["source_digest"]  # audit cohort may change
    assert "2025-04-03" not in json.dumps(later["rows"])


def test_payroll_missing_prior_keeps_missing_arithmetic_and_bulk_vintage_label(tmp_path):
    rows = [row for row in _PAYROLL_ROWS if row[:2] != ("2024-12-01", "2025-02-07")]
    january = next(row for row in _read_payroll(_write_payroll_cohort(tmp_path, rows))["rows"] if row["period"] == "2025-01-01")
    assert january["earliest_change"] is None and january["net_revision"] is None
    assert january["selected_change"] == 30
    old = _read_payroll(_write_payroll_cohort(tmp_path / "bulk", [
        ("1939-01-01", "1997-01-01", "9999-12-31", 100),
        ("1939-02-01", "1997-01-01", "9999-12-31", 120),
    ]), "1997-01-01")
    assert old["rows"][-1]["earliest_vintage"] == "1997-01-01"
    assert old["rows"][-1]["earliest_change"] == 20
    assert "official" not in old["rows"][-1]
    missing = _read_payroll(tmp_path / "bulk" / "release_targets", "1996-12-31")
    assert missing["rows"] == [] and missing["unavailable_reason"] == "INSUFFICIENT_HISTORY"


def test_repeated_unchanged_vintage_is_not_a_revision_event(tmp_path):
    rows = [(p, start, "2025-03-31" if start == "2025-03-07" else end, value)
            for p, start, end, value in _PAYROLL_ROWS]
    rows += [(p, "2025-04-01", "9999-12-31", value) for p, start, end, value in _PAYROLL_ROWS if start == "2025-03-07"]
    from engine.market_os.macro_workspaces import labor, payroll_revisions as payroll
    projection = _read_payroll(_write_payroll_cohort(tmp_path, rows), "2025-04-01")
    body = payroll.attach_payroll_revisions(labor.compose({}, built_at=HISTORY_BUILT_AT), projection)
    metrics = [row for row in body["metrics"]["items"] if row["metric_id"].startswith(payroll.PREFIX)]
    assert all(row["revised_at"] is None and row["available_at"] is None and row["released_at"] is None for row in metrics)
    assert next(row for row in projection["rows"] if row["period"] == "2025-01-01")["net_revision"] == -27


def test_exact_byte_reader_decodes_verified_memory_after_path_replacement(tmp_path, monkeypatch):
    import pyarrow.parquet as parquet
    from engine.release_target_cohort import read_release_target_cohort
    folder = _write_payroll_cohort(tmp_path)
    path = folder / "PAYEMS_all_vintages.parquet"
    original_bytes = path.read_bytes()
    factory = parquet.ParquetFile
    def replace_path_then_decode(data):
        path.write_bytes(b"not the verified parquet")
        return factory(data)
    monkeypatch.setattr(parquet, "ParquetFile", replace_path_then_decode)
    frames, _, _, receipts = read_release_target_cohort(folder / "manifest.json", {"PAYEMS": path})
    assert 159057 in frames["PAYEMS"]["value"].tolist()
    assert receipts["PAYEMS"]["artifact_sha256"] == hashlib.sha256(original_bytes).hexdigest()


def test_cohort_manifest_change_during_decode_refuses_the_result(tmp_path, monkeypatch):
    import pyarrow.parquet as parquet
    from engine.release_target_cohort import ReleaseTargetCohortError
    folder = _write_payroll_cohort(tmp_path)
    factory = parquet.ParquetFile
    def change_manifest(data):
        manifest = folder / "manifest.json"
        manifest.write_bytes(manifest.read_bytes() + b"\n")
        return factory(data)
    monkeypatch.setattr(parquet, "ParquetFile", change_manifest)
    with pytest.raises(ReleaseTargetCohortError, match="changed while reading"):
        _read_payroll(folder)


@pytest.mark.parametrize("defect", ["wrong_series", "wrong_type", "invalid_date", "infinity", "duplicate", "inverted_interval"])
def test_bound_payroll_cohort_rejects_invalid_observations(tmp_path, defect):
    from engine.release_target_cohort import ReleaseTargetCohortError
    frame = pd.DataFrame(_PAYROLL_ROWS, columns=["period", "realtime_start", "realtime_end", "value"])
    frame["series"], frame["source_output_type"] = "PAYEMS", 2
    if defect == "wrong_series": frame.loc[0, "series"] = "CPIAUCSL"
    if defect == "wrong_type": frame.loc[0, "source_output_type"] = 4
    if defect == "invalid_date": frame.loc[1, "realtime_start"] = "2025-02-30"
    if defect == "infinity": frame.loc[1, "value"] = float("inf")
    if defect == "duplicate": frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    if defect == "inverted_interval": frame.loc[0, "realtime_end"] = "1939-01-01"
    with pytest.raises(ReleaseTargetCohortError):
        _read_payroll(_write_payroll_cohort(tmp_path, frame=frame))


def test_missing_partial_or_corrupt_cohort_are_distinct_and_never_fall_back(tmp_path):
    from engine.release_target_cohort import ReleaseTargetCohortError
    assert _read_payroll(tmp_path / "absent")["unavailable_reason"] == "NOT_COVERED"
    folder = _write_payroll_cohort(tmp_path)
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "partial"
    manifest_path.write_text(json.dumps(manifest))
    assert _read_payroll(folder)["rows"] == []
    manifest["status"] = "ok"
    manifest["series"]["PAYEMS"]["artifact_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ReleaseTargetCohortError, match="SHA-256"):
        _read_payroll(folder)


def test_payroll_publication_view_and_original_obligation_remain_distinct(tmp_path):
    from engine.market_os.macro_workspaces import payroll_revisions as payroll
    folder = _write_payroll_cohort(tmp_path)
    regime = tmp_path / "regime.json"
    regime.write_text("{}")
    out = tmp_path / "published"
    build.build_all(regime_latest_path=regime, fred_dir=tmp_path / "fred", treasury_dir=tmp_path / "treasury",
                    release_target_dir=folder, out_root=out, built_at="2025-04-15T12:00:00Z")
    page = next(page for page in SUITE_PAGES if page.workspace_id == "labor_markets")
    body, artifact = read_workspace(out, page)
    view = build_view(body, page_built_at="2025-04-15T12:00:00Z", artifact=artifact)
    revision = view["payroll_revisions"]
    assert revision["rows"][-2]["net_revision"] == -27
    assert revision["unit"] == "thousands" and revision["status"] == "partial"
    assert "合计修订" in revision["limitation"]["zh"]
    original = next(row for row in body["metrics"]["items"] if row["metric_id"] == "payrolls_nfp_change_and_revision")
    assert original["value"] is None and original["null_reason"] == "NOT_COVERED"
    from engine.market_os.macro_workspaces import labor
    baseline = labor.compose({}, built_at="2025-04-15T12:00:00Z")
    for field in ("authority", "axes", "headline", "availability", "changes"):
        assert body[field] == baseline[field]
    for row in view["metrics"]:
        if row["metric_id"].startswith(payroll.PREFIX) and row["value_raw"] is not None:
            assert row["freshness"]["en"] == "Retrospective vintage history"
    assert not any("as known then" in row["freshness"]["en"] for row in view["evidence"]["sources"] if row["source_id"].startswith("revision:"))


@pytest.mark.parametrize("defect", ["missing_role", "duplicate_role", "digest", "cutoff", "released_clock", "revision_value", "missing_source", "duplicate_source", "source_digest", "future_collection"])
def test_payroll_view_refuses_inconsistent_scalar_groups(tmp_path, defect):
    from engine.market_os.macro_workspaces import labor, payroll_revisions as payroll
    body = payroll.attach_payroll_revisions(labor.compose({}, built_at=HISTORY_BUILT_AT), _read_payroll(_write_payroll_cohort(tmp_path)))
    rows = body["metrics"]["items"]
    chosen = next(row for row in rows if row["metric_id"] == "payroll_revision:2025-01-01:net_revision")
    if defect == "missing_role": rows.remove(chosen)
    if defect == "duplicate_role": rows.append(copy.deepcopy(chosen))
    if defect == "digest": chosen["source_digest"] = "1" * 64
    if defect == "cutoff": chosen["calculation_as_of"] = "2025-02-01"
    if defect == "released_clock": chosen["released_at"] = "2025-02-07T00:00:00Z"
    if defect == "revision_value": chosen["value"] = -26
    if defect == "missing_source": body["sources"]["items"] = []
    if defect == "duplicate_source": body["sources"]["items"].append(copy.deepcopy(body["sources"]["items"][-1]))
    if defect == "source_digest": body["sources"]["items"][-2]["artifact_ref"] = payroll.ARTIFACT + "#sha256=" + "9" * 64
    if defect == "future_collection":
        for row in rows:
            if row["metric_id"].startswith(payroll.PREFIX): row["collected_at"] = "2030-01-01T00:00:00Z"
        for source in body["sources"]["items"]:
            if source["source_id"].startswith("revision:"): source["collected_at"] = "2030-01-01T00:00:00Z"
    with pytest.raises(ValueError):
        payroll.read_payroll_revision_metrics(body)


def test_payroll_collection_completion_and_decode_budgets_are_real_bounds(tmp_path, monkeypatch):
    from engine import release_target_cohort as cohort
    from engine.market_os.macro_workspaces.payroll_revision_sources import load_payroll_revisions
    folder = _write_payroll_cohort(tmp_path)
    with pytest.raises(cohort.ReleaseTargetCohortError, match="completed after"):
        load_payroll_revisions(folder, built_at="2025-04-01T09:00:00Z")
    monkeypatch.setattr(cohort, "MAX_DECODED_BYTES", 1)
    with pytest.raises(cohort.ReleaseTargetCohortError, match="decoded-byte bound"):
        _read_payroll(folder)


def test_vintage_dates_without_any_change_are_not_a_ready_revision_panel(tmp_path):
    from engine.market_os.macro_workspaces import labor, payroll_revisions as payroll
    projection = _read_payroll(_write_payroll_cohort(tmp_path, [
        ("2025-01-01", "2025-02-07", "9999-12-31", 159057),
    ]))
    body = contract.finalize(payroll.attach_payroll_revisions(labor.compose({}, built_at=HISTORY_BUILT_AT), projection))
    view = build_view(body, page_built_at=HISTORY_BUILT_AT, artifact={})
    assert view["payroll_revisions"]["status"] == "unavailable"
    assert view["payroll_revisions"]["absence"] is not None
    assert view["payroll_revisions"]["rows"][0]["earliest_change"] is None


@pytest.fixture(scope="module")
def driver_publications(tmp_path_factory):
    """Exercise the real fourteen producers and verified publication reader."""
    root = tmp_path_factory.mktemp("driver_sources")
    regime = _write_regime(root)
    out = root / "published"
    build.build_all(regime_latest_path=regime, fred_dir=root / "fred", treasury_dir=root / "treasury",
                    out_root=out, built_at=BUILT_AT)
    result = {}
    for page in SUITE_PAGES:
        body, artifact = read_workspace(out, page)
        result[page.workspace_id] = (body, build_view(body, page_built_at=BUILT_AT, artifact=artifact))
    return result


def _driver(body, identifier):
    return next(row for group in ("rate_side", "balance_sheet")
                for row in body["drivers"][group] if row["driver_id"] == identifier)


def test_driver_sources_join_real_published_inputs_without_upgrading_absence(driver_publications):
    unlinked = set()
    bound = 0
    for workspace, (body, view) in driver_publications.items():
        source_ids = {row["source_id"] for row in body["sources"]["items"]}
        for group in view["drivers"]:
            for row in group["rows"]:
                original = _driver(body, row["driver_id"])
                binding = row["source_binding"]
                assert binding["method_version"] == body["headline"]["method_version"]
                if original["value"] is None:
                    assert row["value"] is None and row["absence"] is not None
                if binding["state"] == "bound":
                    bound += 1
                    assert binding["source_refs"] and set(binding["source_refs"]) <= source_ids
                else:
                    unlinked.add((workspace, row["driver_id"]))
                    assert binding["source_refs"] == []
                if row["calculation"]:
                    assert binding["input_kind"] == "component"
                    assert row["calculation"]["axis_id"] in {axis["axis_id"] for axis in view["axes"]}
    assert bound == 85
    assert unlinked == {
        ("liquidity_regime", "rates_scare_score"),
        ("inflation_system", "current_month_core_nowcast_annualized"),
        ("financial_conditions", "ig_oas_credit_leg"),
        ("financial_conditions", "dollar_index_leg"),
    }


@pytest.mark.parametrize("defect", ["owner", "value", "boolean", "unit", "duplicate", "method"])
def test_driver_component_identity_is_required_before_sources_or_calculation(driver_publications, defect):
    from engine.market_os.macro_workspaces.source_bindings import driver_binding
    body = copy.deepcopy(driver_publications["liquidity_regime"][0])
    driver = _driver(body, "nfci_pctile")
    axis = next(axis for axis in body["axes"]["items"] if any(c["component_id"] == "nfci_pctile" for c in axis["components"]))
    component = next(c for c in axis["components"] if c["component_id"] == "nfci_pctile")
    if defect == "owner": driver["owner_field"] = "different.input"
    if defect == "value": driver["value"] = 999
    if defect == "boolean": component["raw_value"], driver["value"] = 1, True
    if defect == "unit": driver["unit"] = "USD_bn"
    if defect == "duplicate": axis["components"].append(copy.deepcopy(component))
    if defect == "method": body["headline"]["method_version"] = "liquidity_regime.compose.v2"
    binding = driver_binding(body, driver)
    assert binding["state"] == "unlinked" and binding["input_kind"] is None
    if defect == "method":
        with pytest.raises(KeyError, match="method_version"):
            build_view(body, page_built_at=BUILT_AT, artifact={})
        return
    view = build_view(body, page_built_at=BUILT_AT, artifact={})
    shown = next(row for group in view["drivers"] for row in group["rows"] if row["driver_id"] == "nfci_pctile")
    assert shown["calculation"] is None


def test_driver_multi_source_join_is_complete_and_unambiguous(driver_publications):
    from engine.market_os.macro_workspaces.source_bindings import driver_binding
    body = copy.deepcopy(driver_publications["monetary_policy"][0])
    driver = _driver(body, "dots_vs_market_gap_bp")
    assert driver_binding(body, driver)["source_refs"] == ["fed_funds_futures", "fomc_sep_dots"]
    source = next(row for row in body["sources"]["items"] if row["source_id"] == "fomc_sep_dots")
    body["sources"]["items"].remove(source)
    missing = driver_binding(body, driver)
    assert missing["source_refs"] == [] and missing["reason"] == "source_disclosure_missing"
    body["sources"]["items"].extend([source, copy.deepcopy(source)])
    duplicate = driver_binding(body, driver)
    assert duplicate["source_refs"] == [] and duplicate["reason"] == "source_disclosure_ambiguous"


def test_driver_metric_identity_units_and_explicit_credit_alias(driver_publications):
    from engine.market_os.macro_workspaces.source_bindings import driver_binding
    body = copy.deepcopy(driver_publications["financial_conditions"][0])
    driver = _driver(body, "hy_oas_z_credit_leg")
    metric = next(row for row in body["metrics"]["items"] if row["metric_id"] == "hy_oas_z")
    assert driver_binding(body, driver)["input_id"] == "hy_oas_z"
    assert driver_binding(body, driver)["source_refs"] == ["hy_oas"]
    metric["definition_id"] = "different.input"
    assert driver_binding(body, driver)["reason"] == "input_identity_mismatch"
    body = copy.deepcopy(driver_publications["trade_flows"][0])
    driver = _driver(body, "export_import_coverage_ratio")
    metric = next(row for row in body["metrics"]["items"] if row["metric_id"] == driver["driver_id"])
    assert metric["unit"] is None and driver_binding(body, driver)["state"] == "bound"
    metric["value_type"] = "number"
    assert driver_binding(body, driver)["state"] == "unlinked"
    metric["value_type"], metric["unit"] = "ratio", "percent"
    assert driver_binding(body, driver)["state"] == "unlinked"
    metric["unit"] = None
    body["metrics"]["items"].append(copy.deepcopy(metric))
    assert driver_binding(body, driver)["state"] == "unlinked"


@pytest.mark.parametrize("defect", ["owner", "model"])
def test_driver_ordinary_metric_rejects_contradictory_definition_or_model(driver_publications, defect):
    from engine.market_os.macro_workspaces.source_bindings import driver_binding
    body = copy.deepcopy(driver_publications["financial_conditions"][0])
    driver = _driver(body, "real_10y_pctile")
    metric = next(row for row in body["metrics"]["items"] if row["metric_id"] == "real_10y_pctile")
    assert driver_binding(body, driver)["state"] == "bound"
    if defect == "owner": driver["owner_field"] = "different.owner.field"
    if defect == "model": metric["model_version"] = "different.compose.v1"
    assert driver_binding(body, driver)["reason"] == "input_identity_mismatch"


def test_driver_fred_join_uses_exact_unique_artifact_not_provider_or_owner_prefix(driver_publications):
    from engine.market_os.macro_workspaces.source_bindings import driver_binding
    body = copy.deepcopy(driver_publications["trade_flows"][0])
    driver = _driver(body, "trade_balance_level")
    assert driver_binding(body, driver)["source_refs"] == ["bopgstb"]
    source = next(row for row in body["sources"]["items"] if row["source_id"] == "bopgstb")
    source["artifact_ref"] = "data/fred/BOPGSTB_OTHER.parquet"
    assert driver_binding(body, driver)["reason"] == "source_disclosure_missing"
    source["artifact_ref"] = "data/fred/BOPGSTB.parquet"
    body["sources"]["items"].append({**source, "source_id": "second-disclosure"})
    assert driver_binding(body, driver)["reason"] == "source_disclosure_ambiguous"
