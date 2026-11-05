"""Discriminate native economic clocks, committed bytes and disclosure."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
from urllib.parse import urlencode

import pandas as pd
import pytest

from collectors.base import run_adapter
from collectors.intl_macro import IntlMacroAdapter
from lib import config
from lib import intl_eurostat_publication as pub


NOW = "2026-11-04T06:20:00+00:00"


def payload(field):
    spec = pub.FIELDS[field]
    selectors = spec["selectors"]
    dims = list(selectors) + ["time"]
    quarter = field == "EZ.gdp_yoy"
    labels = ["2026-Q2", "2026-Q3"] if quarter else ["2026-08", "2026-09"]
    categories = {key: {"category": {"index": {value: 0}}} for key, value in selectors.items()}
    categories["time"] = {"category": {"index": dict(zip(labels, range(2)))}}
    return {"source": "ESTAT", "extension": {"id": spec["dataset"]}, "id": dims,
            "size": [1] * len(selectors) + [2], "dimension": categories,
            "updated": "2026-10-30T23:00:00+0100" if quarter else "2026-10-16T23:00:00+0200",
            "value": {"0": 1.2 if quarter else 3.2, "1": 1.3 if quarter else 3.8},
            "status": {"0": "p"}}


def source_url(field):
    spec = pub.FIELDS[field]
    return "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/" + spec["dataset"].lower() + "?" + urlencode(spec["selectors"])


def decision(field, materialized, metadata="allowed", permission="allowed"):
    return {"owner_ref": "scripts/build_intl.py", "policy_ref": pub.POLICY, "decision_ref": "test-owner-decision",
            "metadata": metadata, "value_permission": permission,
            "binding": {"field": field, "receipt_sha256": materialized.get("receipt_sha256")}}


def committed(tmp_path, field):
    raw = json.dumps(payload(field)).encode()
    _, frame = pub.parse_native_field(field, raw)
    p = tmp_path / "intl_macro" / (pub.FIELDS[field]["column"] + ".parquet")
    p.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(p)
    pub.capture_eurostat_commit(field=field, data_root=tmp_path, returned=frame, response_bytes=raw,
                                source_url=source_url(field), requested_at="2026-11-04T06:13:00+00:00",
                                input_verified_at="2026-11-04T06:14:00+00:00", committed_at="2026-11-04T06:15:00+00:00")
    return pub.read_eurostat_materialization(field=field, data_root=tmp_path)


@pytest.mark.parametrize("field,value,label", [("EZ.gdp_yoy", 1.3, "2026-Q3"), ("EZ.cpi_yoy", 3.8, "2026-09")])
def test_actual_period_end_and_separate_dataset_update(tmp_path, field, value, label):
    materialized = committed(tmp_path, field)
    admitted = pub.admit_eurostat_field(materialized, field=field, evaluated_at=NOW, publication_decision=decision(field, materialized))
    m, e = admitted["measure"], admitted["evidence"]
    assert m["quality"] == "qualified" and m["value"] == value
    assert m["observation_at"] == "2026-09-30" and m["calculation_at"] is None
    assert m["period"]["end"] == "2026-10-01"
    assert e["period_label"] == label
    assert e["dataset_updated_at"] == payload(field)["updated"]
    assert e["dataset_updated_at"] != m["observation_at"]
    assert e["response_received_at"] is None and e["observation_status"] is None
    assert pub.project_field_evidence({field: e}, {field: m}) == {field: e}


@pytest.mark.parametrize("field", list(pub.FIELDS))
def test_missing_canonical_write_cannot_be_captured(tmp_path, field):
    raw = json.dumps(payload(field)).encode()
    _, frame = pub.parse_native_field(field, raw)
    with pytest.raises(FileNotFoundError):
        pub.capture_eurostat_commit(field=field, data_root=tmp_path, returned=frame, response_bytes=raw,
                                    source_url=source_url(field), requested_at="2026-11-04T06:13:00+00:00",
                                    input_verified_at="2026-11-04T06:14:00+00:00", committed_at="2026-11-04T06:15:00+00:00")
    assert pub.read_eurostat_materialization(field=field, data_root=tmp_path) == {"status": "missing"}


@pytest.mark.parametrize("field", list(pub.FIELDS))
@pytest.mark.parametrize("metadata", ["unknown", "denied"])
def test_metadata_withheld_has_no_dynamic_disclosure(tmp_path, field, metadata):
    materialized = committed(tmp_path, field)
    admitted = pub.admit_eurostat_field(materialized, field=field, evaluated_at=NOW,
                                      publication_decision=decision(field, materialized, metadata))
    m = admitted["measure"]
    assert admitted["evidence"] is None
    assert all(m[k] is None for k in ["value", "instrument", "period", "observation_at", "source_reference", "evidence_key"])
    good = pub.admit_eurostat_field(materialized, field=field, evaluated_at=NOW, publication_decision=decision(field, materialized))
    assert pub.project_field_evidence({field: good["evidence"]}, {field: m}) == {}


@pytest.mark.parametrize("field", list(pub.FIELDS))
def test_current_selector_cannot_change_clocks_or_source(tmp_path, field):
    committed(tmp_path, field)
    p = tmp_path / "intl_macro/publication" / pub.FIELDS[field]["column"] / "current.json"
    r = json.loads(p.read_text()); r["committed_at"] = "2026-11-04T06:16:00+00:00"
    p.write_text(json.dumps(r))
    assert pub.read_eurostat_materialization(field=field, data_root=tmp_path)["status"] == "failed"


@pytest.mark.parametrize("field", list(pub.FIELDS))
def test_missing_blob_after_original_capture_is_source_failure(tmp_path, field):
    original = committed(tmp_path, field)
    directory = tmp_path / "intl_macro/publication" / pub.FIELDS[field]["column"]
    (directory / (original["receipt"]["source_sha256"] + ".source.json")).unlink()
    materialized = pub.read_eurostat_materialization(field=field, data_root=tmp_path)
    assert materialized["status"] == "failed" and materialized["receipt_sha256"] == original["receipt_sha256"]
    out = pub.admit_eurostat_field(materialized, field=field, evaluated_at=NOW, publication_decision=decision(field, materialized))
    assert out["measure"]["quality"] == "failed" and out["measure"]["reason"] == "source_failed"
    assert out["measure"]["metadata"] == "allowed" and out["evidence"] is None
    assert all(out["measure"][k] is None for k in ["value", "observation_at", "source_reference", "evidence_key"])


@pytest.mark.parametrize("field,days", [("EZ.gdp_yoy", 120), ("EZ.cpi_yoy", 75)])
def test_application_recency_measured_from_economic_end(tmp_path, field, days):
    m = committed(tmp_path, field)
    for extra, quality in [(0, "qualified"), (1, "stale")]:
        evaluated = (pd.Timestamp("2026-09-30", tz="UTC") + pd.Timedelta(days=days + extra)).isoformat()
        out = pub.admit_eurostat_field(m, field=field, evaluated_at=evaluated, publication_decision=decision(field, m))
        assert out["measure"]["quality"] == quality


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = datetime.fromisoformat(NOW)
        return value if tz is not None else value.replace(tzinfo=None)


def collector(tmp_path, monkeypatch):
    cfg = deepcopy(config.load())
    cfg["storage"]["data_dir"] = str(tmp_path)
    cfg["storage"]["run_status_file"] = str(tmp_path / "run_status.json")
    cfg["intl"]["countries"] = {}
    cfg["intl"]["macro"]["extra_series"] = {}
    cfg["intl"]["macro"]["official_series"] = {
        spec["column"]: cfg["intl"]["macro"]["official_series"][spec["column"]] for spec in pub.FIELDS.values()}
    monkeypatch.setattr(config, "load", lambda: cfg)
    monkeypatch.setattr("collectors.intl_macro.datetime", FixedDateTime)
    monkeypatch.setattr("collectors.base.datetime", FixedDateTime)
    return IntlMacroAdapter(), cfg


def test_configured_normal_http_collector_store_then_evidence(tmp_path, monkeypatch):
    adapter, _ = collector(tmp_path, monkeypatch)
    calls = []
    def http(url, **kwargs):
        field = next(f for f, s in pub.FIELDS.items() if url.endswith(s["dataset"].lower()))
        calls.append((field, kwargs["params"]))
        return type("Response", (), {"content": json.dumps(payload(field)).encode(), "url": source_url(field), "status_code": 200})()
    monkeypatch.setattr(adapter, "http_get", http)
    res = run_adapter(adapter)
    assert res.status == "ok" and len(calls) == 2
    for field, params in calls:
        assert all(params[k] == v for k, v in pub.FIELDS[field]["selectors"].items())
        materialized = pub.read_eurostat_materialization(field=field, data_root=tmp_path)
        assert materialized["status"] == "ready"
        assert materialized["receipt"]["response_received_at"] == NOW
    assert not (tmp_path / "intl_macro/EZ_gdp.parquet").exists()
    assert adapter._eurostat_responses == {}


def test_configured_retained_input_uses_same_normal_store_path_without_fetch(tmp_path, monkeypatch):
    adapter, cfg = collector(tmp_path, monkeypatch)
    for field, spec in pub.FIELDS.items():
        raw = json.dumps(payload(field)).encode()
        name = spec["column"]
        (tmp_path / (name + ".source.json")).write_bytes(raw)
        (tmp_path / (name + ".receipt.json")).write_text(json.dumps({"status": 200, "sha256": pub._sha(raw), "response_url": source_url(field), "requested_at": "2026-11-04T06:13:00+00:00"}))
        cfg["intl"]["macro"]["official_series"][name]["native_input"] = {"response": name + ".source.json", "receipt": name + ".receipt.json"}
    monkeypatch.setattr(adapter, "http_get", lambda *a, **k: pytest.fail("retained input must not acquire again"))
    assert run_adapter(adapter).status == "ok"
    for field in pub.FIELDS:
        m = pub.read_eurostat_materialization(field=field, data_root=tmp_path)
        assert m["status"] == "ready" and m["receipt"]["response_received_at"] is None


def test_capture_failure_does_not_retry_or_erase_successful_store(tmp_path, monkeypatch):
    adapter, _ = collector(tmp_path, monkeypatch)
    calls = []
    def http(url, **kwargs):
        field = next(f for f, s in pub.FIELDS.items() if url.endswith(s["dataset"].lower()))
        calls.append(field)
        return type("Response", (), {"content": json.dumps(payload(field)).encode(), "url": source_url(field), "status_code": 200})()
    monkeypatch.setattr(adapter, "http_get", http)
    monkeypatch.setattr(pub, "capture_eurostat_commit", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("capture failed after store")))
    res = run_adapter(adapter)
    assert res.status == "ok" and len(calls) == 2 and len(res.notes) == 2
    assert adapter._eurostat_responses == {}
    for field, spec in pub.FIELDS.items():
        assert pd.read_parquet(tmp_path / "intl_macro" / (spec["column"] + ".parquet")).iloc[-1, 0] in (1.3, 3.8)
        assert pub.read_eurostat_materialization(field=field, data_root=tmp_path)["status"] == "missing"


def test_separate_clock_projection_rejects_another_field_or_period(tmp_path):
    field = "EZ.gdp_yoy"
    m = committed(tmp_path, field)
    out = pub.admit_eurostat_field(m, field=field, evaluated_at=NOW, publication_decision=decision(field, m))
    for key, value in [("period_label", "2026-Q2"), ("evidence_key", "0" * 64), ("source_reference", source_url("EZ.cpi_yoy"))]:
        altered = {**out["evidence"], key: value}
        with pytest.raises(ValueError):
            pub.project_field_evidence({field: altered}, {field: out["measure"]})


def test_normal_builder_and_cell_keep_period_update_and_attribution_separate(tmp_path):
    from scripts.build_intl import _publication_workspace
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    for field in pub.FIELDS:
        committed(tmp_path, field)
    workspace = _publication_workspace(None, data_root=tmp_path, evaluated_at=NOW)
    panel = workspace["macros"][0]
    row = next(r for r in panel["macro_section"]["market_rows"] if r["market_id"] == "EZ")
    assert row["gdp_yoy"]["value"] == 1.3 and row["cpi_yoy"]["value"] == 3.8
    assert set(panel["field_evidence"]) == set(pub.FIELDS)
    env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1]), undefined=StrictUndefined)
    html = env.get_template("templates/intl_workspace/macro.html.j2").render(
        macro_section=panel["macro_section"], registry=workspace["macro_registry"],
        context_id=panel["context_id"], panel_context=panel["context"], generation=panel["generation"],
        source_notice=panel["source_notice"], field_evidence=panel["field_evidence"])
    assert "2026-Q3" in html and "2026-09" in html and "Period ended" in html
    assert "2026-09-30" in html and "Dataset updated" in html
    assert "2026-10-30T23:00:00+0100" in html and "2026-10-16T23:00:00+0200" in html
    assert "HICP YoY" in html and "Source: Eurostat" in html
    assert "Eurostat is not responsible" in html
    assert 'href="' + source_url("EZ.gdp_yoy").replace("&", "&amp;") + '"' in html
    assert row["gdp_yoy"]["calculation_at"] is None


@pytest.mark.parametrize("permission", ["unknown", "denied"])
def test_normal_builder_denied_metadata_has_no_eurostat_source_disclosure(tmp_path, monkeypatch, permission):
    from scripts.build_intl import _publication_workspace
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    for field in pub.FIELDS:
        committed(tmp_path, field)
    cfg = deepcopy(config.load())
    for field in pub.FIELDS:
        cfg["intl"]["field_publication"][field]["metadata"] = permission
    monkeypatch.setattr(config, "load", lambda: cfg)
    workspace = _publication_workspace(None, data_root=tmp_path, evaluated_at=NOW)
    panel = workspace["macros"][0]
    env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1]), undefined=StrictUndefined)
    html = env.get_template("templates/intl_workspace/macro.html.j2").render(
        macro_section=panel["macro_section"], registry=workspace["macro_registry"],
        context_id=panel["context_id"], panel_context=panel["context"], generation=panel["generation"],
        source_notice=panel["source_notice"], field_evidence=panel.get("field_evidence", {}))
    assert "Source: Eurostat" not in html and "Eurostat source data" not in html
    assert "Dataset updated" not in html and "2026-Q3" not in html
    assert all(source_url(field).replace("&", "&amp;") not in html for field in pub.FIELDS)


def test_numeric_native_field_requires_separate_clock_attribution_projection(tmp_path):
    from scripts.build_intl import _publication_workspace
    from lib.intl_macro_mount import attach_macros
    materialized = committed(tmp_path, "EZ.gdp_yoy")
    admitted = pub.admit_eurostat_field(materialized, field="EZ.gdp_yoy", evaluated_at=NOW,
                                      publication_decision=decision("EZ.gdp_yoy", materialized))
    w = _publication_workspace(None, data_root=tmp_path, evaluated_at=NOW)
    parent = {key: w[key] for key in ("config", "panels", "binding_version")}
    result = attach_macros(parent, registry=w["macro_registry"], measures={"EZ.gdp_yoy": admitted["measure"]},
                           cycle_evidence={}, destinations={})
    row = next(r for r in result["macros"][0]["macro_section"]["market_rows"] if r["market_id"] == "EZ")
    assert row["gdp_yoy"].get("value") is None


@pytest.mark.parametrize("field", list(pub.FIELDS))
@pytest.mark.parametrize("permission,quality,reason", [("allowed", "failed", "source_failed"),
                                                       ("denied", "denied", "value_denied"),
                                                       ("unknown", "unknown", "disclosure_unknown")])
def test_source_chronology_failure_retains_only_validated_static_permission(tmp_path, field, permission, quality, reason):
    materialized = committed(tmp_path, field)
    broken = deepcopy(materialized)
    broken["receipt"]["source_updated"] = "2026-11-05T00:00:00+0000"
    out = pub.admit_eurostat_field(broken, field=field, evaluated_at=NOW, publication_decision=decision(field, broken, permission=permission))
    m = out["measure"]
    assert m["quality"] == quality and m["reason"] == reason
    assert m["metadata"] == "allowed" and out["evidence"] is None
    assert all(m[k] is None for k in ["value", "period", "observation_at", "source_reference", "evidence_key"])


def test_boolean_canonical_column_is_not_numeric_source_coverage(tmp_path):
    field = "EZ.gdp_yoy"
    wire = payload(field); wire["value"] = {"0": 1, "1": 1}
    raw = json.dumps(wire).encode(); _, original = pub.parse_native_field(field, raw)
    target = tmp_path / "intl_macro/EZ_gdp_yoy_official.parquet"; target.parent.mkdir()
    pd.DataFrame({"EZ_gdp_yoy_official": [True, True]}, index=original.index).to_parquet(target)
    with pytest.raises(ValueError, match="canonical Eurostat observations"):
        pub.capture_eurostat_commit(field=field, data_root=tmp_path, returned=original, response_bytes=raw,
                                    source_url=source_url(field), requested_at="2026-11-04T06:13:00+00:00",
                                    input_verified_at="2026-11-04T06:14:00+00:00", committed_at="2026-11-04T06:15:00+00:00")
