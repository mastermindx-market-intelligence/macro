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
