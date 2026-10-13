"""Normal publisher composition with real Parquet and explicit test clocks.

These local publications exercise trusted build code, not a deployed purchase
surface or a live ECB query.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from uuid import UUID

import pandas as pd
import pytest

from engine import intl_inputs
from lib.intl_library_mount import render_international_pages
from scripts import build_intl


def _fixture_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ecb = _fixture_module("publisher_ecb_fixture", "test_intl_ecb_deposit_admission.py")
_shell = _fixture_module("publisher_shell_fixture", "test_intl_inspector_mount.py")


def materialize(root, *, values=None, provenance=None):
    series = pd.Series([2.5, 2.5, 2.5] if values is None else values,
                       index=pd.date_range("2026-10-04", periods=3), name="ez_depo_rate")
    directory = root / "intl_macro"
    directory.mkdir()
    series.to_frame().to_parquet(directory / "ez_depo_rate.parquet")
    (directory / "provenance.json").write_text(json.dumps({
        "series": {"ez_depo_rate": deepcopy(_ecb.PROVENANCE) if provenance is None else provenance}
    }))


def publish(root, clock="2026-10-07T10:00:00Z"):
    return build_intl._publication_workspace(None, data_root=root, evaluated_at=clock)


def policy(workspace):
    return next(row["policy_rate"] for row in workspace["macros"][0]["macro_section"]["market_rows"]
                if row["market_id"] == "EZ")


def test_real_bytes_bind_value_notice_and_fresh_publication_identity(tmp_path, monkeypatch):
    materialize(tmp_path)
    calls = []
    original = build_intl.read_ecb_deposit_materialization

    def read_once(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("No equity source or qualification supplied")

    monkeypatch.setattr(build_intl, "read_ecb_deposit_materialization", read_once)
    monkeypatch.setattr(intl_inputs, "source_snapshot", forbidden)
    monkeypatch.setattr(intl_inputs, "qualify_return_records", forbidden)
    one, two = publish(tmp_path), publish(tmp_path)
    assert calls == [{"data_root": tmp_path}, {"data_root": tmp_path}]
    assert one["config"]["source_reference"] != two["config"]["source_reference"]
    for workspace in (one, two):
        nonce = workspace["config"]["source_reference"]
        assert nonce.startswith("im-workspace-generation:")
        assert UUID(nonce.split(":", 1)[1]).version == 4
        assert workspace["binding_version"] == 2
        assert len(workspace["macros"]) == len(workspace["panels"]) == 10
        assert len(workspace["macro_registry"]["markets"]) == 7
        assert policy(workspace)["quality"] == "qualified"
        assert policy(workspace)["value"] == 2.5
        assert policy(workspace)["observation_at"] == "2026-10-06"
        assert policy(workspace)["calculation_at"] is None
        assert policy(workspace)["period"] is None
        assert all(p["generation"] == nonce and p["source_notice"]["market_id"] == "EZ"
                   for p in workspace["macros"])
        assert all(p["overview"]["context"]["source_reference"] is None for p in workspace["panels"])
        assert all(r["metric"]["value"] is None for p in workspace["panels"] for r in p["overview"]["rows"])
        assert all(not p["macro_section"]["coverage"]["classified_ids"] for p in workspace["macros"])
    assert policy(one)["source_reference"] == policy(two)["source_reference"]
    assert one["config"]["source_reference"] not in json.dumps(policy(one))


@pytest.mark.parametrize("values", [[0.0, 0.0, -0.0], [3, 3, 3], [2.5, 2.5, -2.5]])
def test_actual_typed_endpoint_is_not_scaled_or_rounded(tmp_path, values):
    materialize(tmp_path, values=values)
    result = policy(publish(tmp_path))
    assert result["quality"] == "qualified"
    assert result["value"] == values[-1] and type(result["value"]) is type(values[-1])
    assert result["unit"] == "percent"


@pytest.mark.parametrize("clock,quality", [
    ("2026-10-18T23:59:59Z", "qualified"),
    ("2026-10-19T00:00:00Z", "stale"),
    ("2026-10-05T23:59:59Z", "failed"),
])
def test_existing_helper_owns_observation_age(tmp_path, clock, quality):
    materialize(tmp_path)
    workspace = publish(tmp_path, clock)
    result = policy(workspace)
    assert result["quality"] == quality
    if quality == "failed":
        assert "value" not in result
        assert all(p["source_notice"] is None for p in workspace["macros"])
    else:
        assert result["value"] == 2.5
        assert all(p["source_notice"] is not None for p in workspace["macros"])


@pytest.mark.parametrize("failure", ["missing", "broken_parquet", "wrong_provenance", "missing_endpoint"])
def test_unavailable_sources_keep_macro_rows_without_fabricating_values(tmp_path, failure):
    if failure != "missing":
        materialize(tmp_path, values=[2.5, 2.5, float("nan")] if failure == "missing_endpoint" else None)
        if failure == "broken_parquet":
            (tmp_path / "intl_macro/ez_depo_rate.parquet").write_bytes(b"not parquet")
        elif failure == "wrong_provenance":
            (tmp_path / "intl_macro/provenance.json").write_text('{"series":null}')
    workspace = publish(tmp_path)
    assert len(workspace["macros"]) == 10
    assert policy(workspace)["quality"] == ("missing" if failure == "missing" else "failed")
    assert "value" not in policy(workspace) and "source_reference" not in policy(workspace)
    assert all(p["source_notice"] is None for p in workspace["macros"])


def test_failed_mount_preserves_valid_workspace(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("test-only malformed mount")
    monkeypatch.setattr(build_intl, "attach_macros", fail)
    result = publish(tmp_path)
    assert result["binding_version"] == 2 and len(result["panels"]) == 10
    assert "macros" not in result


def test_actual_existing_shell_and_other_owners_accept_publication(tmp_path):
    materialize(tmp_path)
    workspace = publish(tmp_path)
    before = deepcopy(workspace)
    catalogue = json.loads((Path(__file__).parents[1] / "config/intl_library_catalogue.json").read_text())
    html, stocks = render_international_pages(_shell.ActualShell(), {"intl_workspace": workspace}, catalogue=catalogue)
    assert stocks == "Incumbent stocks" and workspace == before
    assert html.count('data-view="macro"') == 10
    assert html.count('class="intl-macro__source-notice"') == 10
    assert "2.5" in html and "2026-10-06" in html and "available free" in html
    assert "data-im-library-static" in html and "data-im-inspector-shell" in html
    assert "data-im-compare-panel" in html
