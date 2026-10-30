"""Pure publication-origin tests; copied stored point, synthetic issuance context."""
import ast
import copy
import logging
from pathlib import Path

import pandas as pd
import pytest
from engine import intl_inputs


def functions():
    # Avoid importing the page builder's unrelated collectors or invoking a build.
    path = Path(__file__).resolve().parents[1] / "scripts" / "build_intl.py"
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name in {"_ecb_publication_result", "_ecb_publication_measure"}]
    namespace = {"log": logging.getLogger("publication-origin-test")}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def materialized():
    return {"status": "ready", "series": pd.Series([2.5, 2.5],
            index=pd.date_range("2026-10-05", periods=2), name="ez_depo_rate"),
            "materialized_identity": {"artifact_sha256": "d5ce385fa74960c5449f4d06ec807f889e6833053b02a2d90fda5cb5f8f0bce8",
                "provenance_sha256": "9b12934a0d5d6f9da843a01066b6701e5fc238ac2567fc5de22328636e52af2f", "column": "ez_depo_rate"},
            "provenance": {"last_observation": "2026-10-06", "provider": "ecb",
                "release_period_semantics": "Daily effective policy-rate observation",
                "requested_at": "2026-10-06T03:10:11.694643+00:00",
                "source_id": "D.U2.EUR.4F.KR.DFR.LEV", "source_updated": "2026-10-06",
                "source_url": "https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata&startPeriod=1999-01-01",
                "status": "official", "unit": "PCPA"}}


def evaluate(m=None, clock="2026-10-07T10:00:00Z", generation="fixture:publication"):
    return functions()["_ecb_publication_result"](materialized() if m is None else m,
            evaluated_at=clock, generation=generation)


def test_ready_retains_original_decision_not_content_or_clock():
    result = evaluate()
    assert result["measure"]["quality"] == "qualified"
    assert result["origin"] == {"qualification_identity": "fixture:publication:EZ.policy_rate"}
    assert result["origin"]["qualification_identity"] != result["measure"]["evidence_key"]
    assert result["clocks"] == {"published_at": None, "rights_at": None,
                                "source_observed_at": "2026-10-06"}
    second = evaluate(generation="fixture:second")
    assert second["measure"] == result["measure"]
    assert second["origin"] != result["origin"]


@pytest.mark.parametrize("status", ["missing", "failed"])
def test_missing_failed_no_origin(status):
    r = evaluate({"status": status})
    assert r["origin"] is None and r["measure"]["value"] is None
    assert all(v is None for v in r["clocks"].values())


@pytest.mark.parametrize("kind", ["empty", "bool", "nonfinite", "bad_provenance"])
def test_invalid_no_origin(kind):
    m = materialized()
    if kind == "empty": m["series"] = m["series"].iloc[:0]
    elif kind == "bool": m["series"] = m["series"].astype(object); m["series"].iloc[-1] = True
    elif kind == "nonfinite": m["series"].iloc[-1] = float("inf")
    else: m["provenance"]["provider"] = "fred"
    r = evaluate(m)
    assert r["origin"] is None and r["measure"]["value"] is None


def test_stale_is_not_positive_qualification_origin():
    r = evaluate(clock="2026-10-20T00:00:00Z")
    assert r["measure"]["quality"] == "stale" and r["measure"]["value"] == 2.5
    assert r["origin"] is None and r["clocks"]["source_observed_at"] == "2026-10-06"


@pytest.mark.parametrize("field,permission", [("metadata", "denied"), ("metadata", "unknown"),
                                             ("value_permission", "denied"), ("value_permission", "unknown")])
def test_real_owner_denied_suppressed_no_origin(monkeypatch, field, permission):
    original = intl_inputs.admit_ecb_deposit_field
    def with_permission(*args, **kwargs):
        kwargs["publication_decision"][field] = permission
        return original(*args, **kwargs)
    monkeypatch.setattr(intl_inputs, "admit_ecb_deposit_field", with_permission)
    r = evaluate()
    assert r["origin"] is None and r["measure"]["value"] is None
    if field == "metadata": assert r["clocks"]["source_observed_at"] is None


def test_detachment_and_unchanged_field_api():
    m = materialized(); before = copy.deepcopy(m)
    fn = functions()
    r = fn["_ecb_publication_result"](m, evaluated_at="2026-10-07T10:00:00Z", generation="fixture:publication")
    field = fn["_ecb_publication_measure"](m, evaluated_at="2026-10-07T10:00:00Z", generation="fixture:publication")
    assert field == r["measure"] and "origin" not in field
    r["measure"]["instrument"]["id"] = "mutated"; r["origin"]["qualification_identity"] = "mutated"
    assert evaluate()["origin"]["qualification_identity"] == "fixture:publication:EZ.policy_rate"
    pd.testing.assert_series_equal(m["series"], before["series"])
    assert m["provenance"] == before["provenance"] and m["materialized_identity"] == before["materialized_identity"]
