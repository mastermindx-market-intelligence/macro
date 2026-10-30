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
    original_result = build_intl._ecb_publication_result
    rich_calls, field_calls = [], []

    def rich_once(*args, **kwargs):
        rich_calls.append((args, kwargs))
        return original_result(*args, **kwargs)

    def field_only(*args, **kwargs):
        field_calls.append((args, kwargs))
        return original_result(*args, **kwargs)["measure"]

    monkeypatch.setattr(build_intl, "_ecb_publication_result", rich_once)
    monkeypatch.setattr(build_intl, "_ecb_publication_measure", field_only)
    one, two = publish(tmp_path), publish(tmp_path)
    assert calls == [{"data_root": tmp_path}, {"data_root": tmp_path}]
    assert len(rich_calls) == 2 and field_calls == []
    assert all(len(args) == 1
               and kwargs.get("evaluated_at") == "2026-10-07T10:00:00Z"
               and set(kwargs) == {"evaluated_at", "generation"}
               for args, kwargs in rich_calls)
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
    for workspace in (one, two):
        nonce = workspace["config"]["source_reference"]
        record = workspace["macro_publication"]
        assert record["measure_id"] == "EZ.policy_rate"
        assert record["generation"] == nonce
        assert record["evaluated_at"] == "2026-10-07T10:00:00Z"
        assert record["origin"] == {"qualification_identity": nonce + ":EZ.policy_rate"}
        assert record["decision_origin"] == {
            "owner_ref": "scripts/build_intl.py",
            "policy_ref": "docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#official-ecb-deposit-level-admission",
            "decision_ref": nonce + ":EZ.policy_rate",
        }
        assert record["source_reference"] == policy(workspace)["source_reference"]
        assert record["evidence_key"] == policy(workspace)["evidence_key"]
        assert record["source_reference"] not in json.dumps(workspace["panels"])
        assert nonce not in record["source_reference"]
        assert record["clocks"] == {"published_at": None, "rights_at": None,
                                    "source_observed_at": "2026-10-06"}
        assert record["source_notice"] == {
            "market_id": "EZ", "field": "policy_rate",
            "instrument_id": "deposit_facility",
            "origin_url": "https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV",
        }
        assert set(record) == {"measure_id", "generation", "evaluated_at", "origin",
                               "decision_origin", "source_reference", "evidence_key",
                               "clocks", "source_notice"}
        blob = json.dumps(record)
        assert '"value"' not in blob and "artifact_sha256" not in blob
        assert "binding" not in blob and "requested_at" not in blob
        assert all("macro_publication" not in p for p in workspace["panels"])
        assert all(list(p) == ["context_id", "context", "macro_section", "source_notice",
                               "generation"] for p in workspace["macros"])
    # One detached record per publication: fresh generations, same source bytes.
    assert one["macro_publication"] is not two["macro_publication"]
    assert (one["macro_publication"]["generation"]
            != two["macro_publication"]["generation"])
    assert (one["macro_publication"]["source_reference"]
            == two["macro_publication"]["source_reference"])
    one["macro_publication"]["decision_origin"]["decision_ref"] = "edited"
    assert two["macro_publication"]["decision_origin"]["decision_ref"].endswith(":EZ.policy_rate")


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
        assert "macro_publication" not in workspace
    elif quality == "stale":
        assert result["value"] == 2.5
        assert all(p["source_notice"] is not None for p in workspace["macros"])
        # Stale evidence keeps its ordinary projection but never the record.
        assert "macro_publication" not in workspace
    else:
        assert result["value"] == 2.5
        assert all(p["source_notice"] is not None for p in workspace["macros"])
        assert workspace["macro_publication"]["clocks"] == {
            "published_at": None, "rights_at": None, "source_observed_at": "2026-10-06"}


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
    assert "macro_publication" not in workspace


def test_failed_mount_preserves_valid_workspace(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("test-only malformed mount")
    monkeypatch.setattr(build_intl, "attach_macros", fail)
    result = publish(tmp_path)
    assert result["binding_version"] == 2 and len(result["panels"]) == 10
    assert "macros" not in result
    assert "macro_publication" not in result


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


# --- Synthetic coexistence: shell publication block + W2F surveillance seam -
# Local publications only; these fixtures leave Surveillance sub-tabs disabled.
# No template or panel data is fabricated for them; the retained shell permits
# its absent _gs_snapshot.html.j2 include explicitly via `ignore missing`.

_eod = _fixture_module("publisher_eod_fixture", "test_intl_eod_publication.py")


def _render(workspace, catalogue=None):
    before = deepcopy(workspace)
    html, stocks = render_international_pages(
        _shell.ActualShell(), {"intl_workspace": workspace}, catalogue=catalogue)
    assert stocks == "Incumbent stocks" and workspace == before
    return html


def _json_script(html, marker):
    needle = '<script type="application/json" data-im-' + marker + '>'
    start = html.index(needle) + len(needle)
    return html[start:html.index("</script>", start)]


def _spy(owner, name, monkeypatch):
    calls = []
    original = getattr(owner, name)

    def watching(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        calls[-1]["result"] = original(*args, **kwargs)
        return calls[-1]["result"]

    monkeypatch.setattr(owner, name, watching)
    return calls


def test_one_inert_publication_block_leaves_controller_config_untouched(tmp_path):
    materialize(tmp_path)
    workspace = publish(tmp_path)
    bare = deepcopy(workspace)
    bare.pop("macro_publication")
    with_record = _render(workspace)
    without_record = _render(bare)
    # Exactly one inert application/json publication block ...
    assert with_record.count("data-im-macro-publication") == 1
    assert "data-im-macro-publication" not in without_record
    assert '<script type="application/json" data-im-macro-publication>' in with_record
    assert with_record.index("data-im-macro-publication") < with_record.index("data-im-config")
    # ... separate from the exact unchanged controller config ...
    config_with = _json_script(with_record, "config")
    config_without = _json_script(without_record, "config")
    assert config_with == config_without
    assert json.loads(config_with) == bare["config"]
    assert json.loads(_json_script(with_record, "macro-publication")) == workspace["macro_publication"]
    assert "macro_publication" not in config_with
    # ... one block despite ten Macro panels.
    assert with_record.count('data-view="macro"') == 10


def test_script_closing_record_stays_inert_json_without_injected_element(tmp_path):
    materialize(tmp_path)
    workspace = publish(tmp_path)
    injected = deepcopy(workspace["macro_publication"])
    injected["decision_origin"]["decision_ref"] = (
        '</script><script>im-injected()</script>'
        '<img src=x onerror=im-owns-no-element>')
    workspace["macro_publication"] = injected
    bare = deepcopy(workspace)
    bare.pop("macro_publication")
    html = _render(workspace)
    baseline = _render(bare)
    assert html.count("data-im-macro-publication") == 1
    raw = _json_script(html, "macro-publication")
    assert json.loads(raw) == injected
    assert "\\u003c/script\\u003e\\u003cscript\\u003e" in raw
    assert "</script><script>" not in html and "<img " not in html
    assert html.count("im-injected()") == 1
    assert html.count("<script") == baseline.count("<script") + 1
    assert html.count("</script>") == baseline.count("</script>") + 1


@pytest.mark.parametrize("materialized,clock", [
    (True, "2026-10-19T00:00:00Z"),
    (True, "2026-10-05T23:59:59Z"),
    (False, "2026-10-07T10:00:00Z"),
])
def test_absent_publication_record_adds_no_shell_block(tmp_path, materialized, clock):
    if materialized:
        materialize(tmp_path)
    workspace = publish(tmp_path, clock)
    assert "macro_publication" not in workspace
    html = _render(workspace)
    assert "data-im-macro-publication" not in html
    assert '<script type="application/json" data-im-config>' in html
    assert html.count('data-view="macro"') == 10


@pytest.mark.parametrize("ready", [True, False])
def test_surveillance_chain_shares_admitted_frame_and_rights_objects(tmp_path, monkeypatch, ready):
    import lib.intl_eod_publication as eod_publication

    frame, _ = _eod._setup(tmp_path)
    if ready:
        materialize(tmp_path)
    eod_calls = _spy(eod_publication, "build_eod_inputs", monkeypatch)
    obs_calls = _spy(build_intl, "build_observation_set", monkeypatch)
    surf_calls = _spy(build_intl, "attach_surveillance", monkeypatch)
    workspace = build_intl._publication_workspace(
        frame, data_root=tmp_path, evaluated_at=_eod.EVALUATED)
    assert len(eod_calls) == len(obs_calls) == len(surf_calls) == 1
    admitted = eod_calls[0]["result"]
    assert admitted is not None
    assert obs_calls[0]["args"][0] is admitted[0]
    assert obs_calls[0]["kwargs"]["publication_inputs"] is admitted[1]
    assert obs_calls[0]["kwargs"]["rights"] is eod_calls[0]["kwargs"]["rights"]
    assert surf_calls[0]["kwargs"]["observations"] is obs_calls[0]["result"]
    assert len(workspace["panels"]) == len(workspace["macros"]) == 10
    assert workspace["eod_snapshot"]["as_of"] == "2026-10-07"
    assert workspace["surveillance_panels"] == []
    assert set(workspace["surveillance"]["views"]) == {
        "scanner", "dislocations", "transmission", "dossier",
        "scenario", "replay", "coverage"}
    assert all(view["status"] != "available"
               for view in workspace["surveillance"]["views"].values())
    if ready:
        assert policy(workspace)["quality"] == "qualified"
        assert workspace["macro_publication"]["generation"] == workspace["config"]["source_reference"]
    else:
        assert policy(workspace)["quality"] == "missing"
        assert "macro_publication" not in workspace


def test_unavailable_eod_keeps_native_none_inputs_and_disabled_views(tmp_path, monkeypatch):
    import lib.intl_eod_publication as eod_publication

    materialize(tmp_path)
    eod_calls = _spy(eod_publication, "build_eod_inputs", monkeypatch)
    obs_calls = _spy(build_intl, "build_observation_set", monkeypatch)
    surf_calls = _spy(build_intl, "attach_surveillance", monkeypatch)
    workspace = publish(tmp_path)
    assert len(eod_calls) == len(obs_calls) == len(surf_calls) == 1
    assert eod_calls[0]["result"] is None
    assert obs_calls[0]["args"][0] is None
    assert obs_calls[0]["kwargs"]["publication_inputs"] is None
    assert obs_calls[0]["kwargs"]["rights"] is eod_calls[0]["kwargs"]["rights"]
    assert "result" not in obs_calls[0]
    assert surf_calls[0]["kwargs"]["observations"] is None
    assert workspace["surveillance"]["observations"]["status"] is None
    assert all(entry == {"total": 0, "qualified": 0, "abstain": 0}
               for entry in workspace["surveillance"]["observations"]["counts"].values())
    assert "eod_snapshot" not in workspace
    assert len(workspace["panels"]) == len(workspace["macros"]) == 10
    assert policy(workspace)["quality"] == "qualified"
    assert "macro_publication" in workspace
    html = _render(workspace)
    for view in ("scanner", "dislocations", "transmission", "dossier",
                 "scenario", "replay", "coverage"):
        assert 'data-im-view="' + view + '" disabled' in html
    assert 'data-im-view="overview" disabled' not in html
    assert html.count('data-view="macro"') == 10
    assert "intl-gs" not in html
