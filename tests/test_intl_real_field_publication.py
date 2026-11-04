"""Discriminating source/store/permission boundaries for the new real fields."""
from copy import deepcopy
from datetime import datetime
from io import BytesIO
import json

import pandas as pd
import pytest
from openpyxl import Workbook

from lib import intl_annual_publication as annual
from lib import intl_yield_publication as yields
from lib.intl_workspace_risk_pressure import build_pressure_rows

RECEIVED = "2026-11-04T04:29:21+00:00"
COMMITTED = "2026-11-04T04:30:00+00:00"
EVALUATED = "2026-11-04T05:00:00+00:00"


def workbook(**changes):
    row = {"DATASET": "IMF.RES:WEO(9.0.0)", "SERIES_CODE": "JPN.BCA_NGDPD.A",
           "COUNTRY.ID": "JPN", "INDICATOR.ID": "BCA_NGDPD", "FREQUENCY": "Annual",
           "UNIT": "Percent", "SCALE": "Units", "PUBLICATION_DATE": "2026-10-13T02:00:00Z",
           "UPDATE_DATE": "2026-10-13T02:00:00Z", "COUNTRY_UPDATE_DATE": datetime(2026, 9, 24),
           "LATEST_ACTUAL_ANNUAL_DATA": 2025, "START_END_MONTHS_OF_REPORTING_YEAR": None,
           "METHODOLOGY.ID": "BPM6", "METHODOLOGY_NOTES": "source fixture",
           "2025": 4.125, "2026": 3.75}
    row.update(changes)
    book = Workbook(); sheet = book.active; sheet.title = "Countries"
    sheet.append(list(row)); sheet.append(list(row.values()))
    out = BytesIO(); book.save(out); book.close()
    return out.getvalue()


def decision(field, materialized, **changes):
    result = {"owner_ref": "scripts/build_intl.py", "policy_ref": "test-only-trusted-disclosure",
              "decision_ref": "test-decision", "metadata": "allowed", "value_permission": "allowed",
              "binding": {"field": field, "receipt_sha256": materialized["receipt_sha256"]}}
    result.update(changes)
    return result


def annual_materialized(root):
    raw = workbook()
    source = annual.parse_native_current_account(raw)
    returned = pd.DataFrame({annual.COLUMN: [source["values"][y]["value"] for y in (2025, 2026)]},
                            index=pd.to_datetime(["2025-12-31", "2026-12-31"]))
    (root / "imf_weo").mkdir()
    returned.to_parquet(root / annual.CACHE)
    receipt = {"status": 200, "sha256": annual._sha(raw), "url": "https://data.imf.org/test-fixture.xlsx", "received_at": RECEIVED}
    annual.capture_current_account_commit(data_root=root, workbook_bytes=raw, source_receipt=receipt,
                                          returned=returned, committed_at=COMMITTED)
    return annual.read_current_account_materialization(data_root=root)


def yield_materialized(root):
    raw = b"observation_date,IRLTLT01JPM156N\n2026-09-01,1.5\n2026-10-01,1.7\n"
    frame = pd.DataFrame({yields.COLUMN: [1.5, 1.7]}, index=pd.to_datetime(["2026-09-01", "2026-10-01"]))
    (root / "intl_macro").mkdir()
    frame.to_parquet(root / "intl_macro" / (yields.COLUMN + ".parquet"))
    source = {"provider": "fred_fallback", "source_id": yields.SOURCE_ID,
              "source_url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + yields.SOURCE_ID,
              "unit": "percent", "frequency": "monthly", "adjustment": "NSA",
              "instrument_id": yields.SOURCE_ID, "instrument_kind": "sovereign_10y"}
    yields.capture_jp_yield_commit(data_root=root, returned=frame, response_bytes=raw, source=source,
                                  received_at=RECEIVED, committed_at=COMMITTED)
    return yields.read_jp_yield_materialization(data_root=root)


def test_native_annual_actual_and_estimate_and_missing_reporting_period_are_distinct():
    row = annual.parse_native_current_account(workbook())
    assert row["values"][2025] == {"value": 4.125, "observation_type": "actual"}
    assert row["values"][2026] == {"value": 3.75, "observation_type": "estimate"}
    assert row["reporting_year_months"] is None
    assert row["country_updated_on"] == "2026-09-24"
    assert row["publication_at"] == "2026-10-13T02:00:00Z"


@pytest.mark.parametrize("change", [{"COUNTRY.ID": "USA"}, {"UNIT": "Dollars"}, {"SCALE": "Billions"},
                                         {"INDICATOR.ID": "GGXWDG_NGDP"}, {"LATEST_ACTUAL_ANNUAL_DATA": None},
                                         {"PUBLICATION_DATE": None}, {"2025": float("inf")}])
def test_native_annual_refuses_wrong_or_missing_original_semantics(change):
    # openpyxl omits an infinite numeric as an empty cell; either way the exact
    # actual endpoint must remain unavailable.
    with pytest.raises(ValueError):
        annual.parse_native_current_account(workbook(**change))


def test_actual_annual_committed_field_passes_existing_risk_contract(tmp_path):
    materialized = annual_materialized(tmp_path)
    assert materialized["status"] == "ready"
    projected = annual.admit_current_account_field(materialized, evaluated_at=EVALUATED,
                          publication_decision=decision("JP.annual_current_account", materialized))
    rows = build_pressure_rows(registry={"markets": [{"market_id": "JP", "name_en": "Japan", "name_zh": "日本"}],
                                         "horizons": ["1m"], "bases": ["local"]},
                               measures={"JP.annual_current_account": projected["measure"]},
                               field_support={"JP.annual_current_account": projected["support"]})
    assert rows[0]["annual_current_account"]["value"] == 4.125
    assert projected["support"]["field_year"] == 2025
    assert projected["measure"]["observation_at"] == "2026-09-24"
    assert projected["measure"]["calculation_at"] is None
    assert projected["support"]["vintage"] == "2026-10-13T02:00:00Z"
    assert projected["support"]["method_ref"] == annual.ANNUAL_METHOD
    assert projected["measure"]["period"]["end"] == "2026-01-01"


@pytest.mark.parametrize("owner,field", [(annual, "JP.annual_current_account"), (yields, "JP.yield_10y")])
def test_response_receipt_is_not_publication_permission(tmp_path, owner, field):
    materialized = annual_materialized(tmp_path) if owner is annual else yield_materialized(tmp_path)
    admit = owner.admit_current_account_field if owner is annual else owner.admit_jp_yield_field
    result = admit(materialized, evaluated_at=EVALUATED, publication_decision=None)
    measure = result["measure"] if owner is annual else result
    assert measure["value"] is None and measure["quality"] == "unknown"
    for metadata, permission in (("denied", "allowed"), ("allowed", "denied")):
        result = admit(materialized, evaluated_at=EVALUATED,
                       publication_decision=decision(field, materialized, metadata=metadata, value_permission=permission))
        measure = result["measure"] if owner is annual else result
        assert measure["value"] is None and measure["quality"] == "denied"
        if metadata == "denied": assert measure["source_reference"] is None


def test_japan_yield_exact_month_and_unknown_provider_dates(tmp_path):
    materialized = yield_materialized(tmp_path)
    assert materialized["status"] == "ready"
    row = yields.admit_jp_yield_field(materialized, evaluated_at=EVALUATED,
                                      publication_decision=decision("JP.yield_10y", materialized))
    assert row["value"] == 1.7 and row["quality"] == "qualified"
    assert row["period"] == {"start": "2026-10-01", "end": "2026-11-01", "count": 1, "count_basis": "release_periods"}
    assert materialized["receipt"]["provider_published_at"] is None
    assert materialized["receipt"]["revision_vintage"] is None
    assert row["calculation_at"] is None


@pytest.mark.parametrize("owner", [annual, yields])
def test_changed_committed_bytes_invalidate_previous_receipt(tmp_path, owner):
    annual_materialized(tmp_path) if owner is annual else yield_materialized(tmp_path)
    artifact = tmp_path / (annual.CACHE if owner is annual else "intl_macro/JP_yield_10y.parquet")
    frame = pd.read_parquet(artifact); frame.iloc[-1, 0] += 1; frame.to_parquet(artifact)
    reader = owner.read_current_account_materialization if owner is annual else owner.read_jp_yield_materialization
    assert reader(data_root=tmp_path)["status"] == "failed"


def test_yield_old_only_latest_row_cannot_become_response_coverage(tmp_path):
    materialized = yield_materialized(tmp_path)
    frame = pd.read_parquet(tmp_path / "intl_macro/JP_yield_10y.parquet")
    frame.loc[pd.Timestamp("2026-11-01")] = 1.8
    frame.to_parquet(tmp_path / "intl_macro/JP_yield_10y.parquet")
    with pytest.raises(ValueError, match="latest stored date"):
        yields.capture_jp_yield_commit(data_root=tmp_path, returned=frame.iloc[:-1],
            response_bytes=(tmp_path / yields.DIRECTORY / (materialized["receipt"]["source_sha256"] + ".csv")).read_bytes(),
            source=materialized["receipt"]["source"], received_at=RECEIVED, committed_at=COMMITTED)


def test_actual_year_after_publication_is_refused(tmp_path):
    materialized = annual_materialized(tmp_path)
    materialized["receipt"]["source"]["latest_actual_year"] = 2026
    materialized["receipt"]["source"]["values"]["2026"]["observation_type"] = "actual"
    projected = annual.admit_current_account_field(materialized, evaluated_at=EVALUATED,
                          publication_decision=decision("JP.annual_current_account", materialized))
    assert projected["measure"]["quality"] == "failed"


def test_full_builder_composes_both_fields_without_changing_existing_views(tmp_path, monkeypatch):
    from lib import config
    from scripts import build_intl
    from tests.test_intl_eod_publication import _setup

    annual_materialized(tmp_path); yield_materialized(tmp_path)
    closes, _ = _setup(tmp_path)
    original_load = config.load
    cfg = deepcopy(original_load())
    cfg["intl"]["field_publication"] = {field: {"status": "confirmed", "policy_ref": "test-only-source-policy",
        "metadata": "allowed", "value_permission": "allowed"} for field in ("JP.yield_10y", "JP.annual_current_account")}
    monkeypatch.setattr(config, "load", lambda: cfg)
    result = build_intl._publication_workspace(closes, data_root=tmp_path, evaluated_at=EVALUATED)
    assert result["macros"] and result["risks"] and result["histories"]
    # Inspect the actual mounted section rather than a stand-in helper call.
    macro_rows = result["macros"][0]["macro_section"]["market_rows"]
    assert next(r for r in macro_rows if r["market_id"] == "JP")["yield_10y"]["value"] == 1.7
    risk_rows = result["risks"][0]["risk_section"]["pressure_rows"]
    assert next(r for r in risk_rows if r["market_id"] == "JP")["annual_current_account"]["value"] == 4.125
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    risk = result["risks"][0]
    rendered = env.get_template("intl_workspace/risk.html.j2").render(
        risk_section=risk["risk_section"], registry=result["risk_registry"],
        panel_context=risk["context"], context_id=risk["context_id"], generation=risk["generation"])
    assert "Source updated" in rendered and "来源更新" in rendered
    assert "2026-09-24" in rendered and "2026-10-13T02:00:00Z" in rendered


@pytest.mark.parametrize("source_date,expected", [(None, "unknown"), ("2026-10-14", "failed"),
                                                   ("2026-02-01", "stale")])
def test_annual_freshness_and_chronology_use_country_update_not_edition(tmp_path, source_date, expected):
    materialized = annual_materialized(tmp_path)
    materialized["receipt"]["source"]["country_updated_on"] = source_date
    projected = annual.admit_current_account_field(materialized, evaluated_at=EVALUATED,
                         publication_decision=decision("JP.annual_current_account", materialized))
    assert projected["measure"]["quality"] == expected
    if expected != "stale": assert projected["measure"]["value"] is None


def test_normal_native_collector_input_is_reachable_and_does_not_refetch_japan(tmp_path, monkeypatch):
    from collectors import imf_weo
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    raw = workbook(); native = tmp_path / "imf_weo/native"; native.mkdir(parents=True)
    (native / "source.xlsx").write_bytes(raw)
    receipt = {"status": 200, "sha256": annual._sha(raw), "url": "https://data.imf.org/source.xlsx", "received_at": RECEIVED}
    (native / "receipt.json").write_text(json.dumps(receipt))
    adapter = imf_weo.ImfWeoAdapter()
    adapter.cfg = {"countries": ["JPN"], "indicators": {"BCA_NGDPD": annual.COLUMN},
                   "native_current_account": {"workbook": "imf_weo/native/source.xlsx", "receipt": "imf_weo/native/receipt.json"}}
    monkeypatch.setattr(imf_weo, "fetch_indicator", lambda *a, **kw: pytest.fail("native series must not refetch through DataMapper"))
    prior = pd.DataFrame({annual.COLUMN: [99.0, 88.0]}, index=pd.to_datetime(["2024-12-31", "2025-12-31"]))
    prior.to_parquet(tmp_path / annual.CACHE)
    result = adapter.fetch()
    assert result["imf_weo_runs"]["series_ok"].iloc[0] == 1
    stored = pd.read_parquet(tmp_path / annual.CACHE)
    assert stored.columns.tolist() == [annual.COLUMN]
    assert stored.loc[pd.Timestamp("2024-12-31"), annual.COLUMN] == 99
    assert stored.loc[pd.Timestamp("2025-12-31"), annual.COLUMN] == 4.125
    assert annual.read_current_account_materialization(data_root=tmp_path)["status"] == "ready"


def test_native_input_receipt_failure_and_store_failure_cannot_issue_evidence(tmp_path, monkeypatch):
    from collectors import imf_weo
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    adapter = imf_weo.ImfWeoAdapter(); raw = workbook()
    receipt = {"status": 200, "sha256": annual._sha(raw), "url": "https://data.imf.org/source.xlsx", "received_at": RECEIVED}
    calls = []
    monkeypatch.setattr(imf_weo.store, "upsert", lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError, match="unbound original"):
        adapter.materialize_native_current_account(raw, {**receipt, "sha256": "0" * 64})
    assert calls == []
    def failing(*a, **k): raise OSError("store write failed")
    monkeypatch.setattr(imf_weo.store, "upsert", failing)
    with pytest.raises(OSError, match="store write failed"):
        adapter.materialize_native_current_account(raw, receipt)
    assert annual.read_current_account_materialization(data_root=tmp_path)["status"] == "missing"


@pytest.mark.parametrize("failure", ["none", "evidence", "store"])
def test_normal_runner_calls_evidence_only_after_successful_store(tmp_path, monkeypatch, failure):
    from collectors import base
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(base, "_breaker_state", lambda: {})
    events = []
    class Producer(base.Adapter):
        name = "evidence_order_fixture"; group = "evidence_order_fixture"
        def fetch(self, full_history=False):
            return {"one": pd.DataFrame({"value": [1.0]}, index=pd.to_datetime(["2026-11-04"]))}
        def after_store_commit(self, name, returned, merged, *, committed_at):
            events.append("evidence")
            assert events[0] == "store"
            if failure == "evidence": raise OSError("capture interrupted")
    actual_upsert = base.store.upsert
    def commit(*args, **kwargs):
        events.append("store")
        if failure == "store": raise OSError("canonical write failed")
        return actual_upsert(*args, **kwargs)
    monkeypatch.setattr(base.store, "upsert", commit)
    result = base.run_adapter(Producer())
    assert events == (["store"] if failure == "store" else ["store", "evidence"])
    if failure == "store": assert result.status == "failed"
    elif failure == "evidence":
        assert result.status != "failed"
        assert any("publication unqualified" in n for n in result.notes)
