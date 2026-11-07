"""Candidate read contract structural regressions; no uncommitted model imports."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import jsonschema
import pytest

ROOT=Path(__file__).resolve().parents[1]
SCHEMA=ROOT/"contracts/capital_pressure_read_v1_candidate.schema.json"
EXAMPLE=ROOT/"evidence/capital_pressure_read_synthetic.json"


def schema():
    value=json.loads(SCHEMA.read_text())
    jsonschema.Draft202012Validator.check_schema(value)
    return value


def sample():
    return json.loads(EXAMPLE.read_text())


def test_candidate_read_contract_validates_complete_controlled_fixture():
    s=schema(); v=sample()
    jsonschema.validate(v,s)
    assert v["schema"]=="factor_atlas.capital_pressure.read.v1"
    assert v["market_pilot_admitted"] is False
    assert v["customer_publishable"] is False
    assert v["source_quality"]=="NOT_ADMITTED"
    assert len(v["factors"])>=1
    assert all(x["confidence"] is None and x["predicted_return"] is None
               for x in v["factors"])


def change(v,kind):
    f=v["factors"][0]
    if kind=="admitted":v["market_pilot_admitted"]=True
    elif kind=="published":v["customer_publishable"]=True
    elif kind=="trading":v["authority"][3][1]=True
    elif kind=="rank":v["authority"][0][1]=True
    elif kind=="source_proven":v["source_quality"]="PROVEN_LIVE"
    elif kind=="owner":v["beneficial_owner"]="FUND"
    elif kind=="confidence":f["confidence"]=.95
    elif kind=="predicted_return":f["predicted_return"]=.02
    elif kind=="pressure_outlier":f["pressure_ratio_full"]=12
    elif kind=="negative_gross":f["gross_observed_usd"]=-3
    elif kind=="unqualified_state":f["status"]="INSTITUTIONAL_BUYING"
    elif kind=="partial_full":f["status"]="PARTIAL_COVERAGE";f["missing_cells"]=1
    elif kind=="schema_version":v["schema"]="factor_atlas.capital_pressure.read.v2"
    elif kind=="missing_field":v.pop("source_quality")
    elif kind=="short_authority":v["authority"].pop()
    elif kind=="bad_digest":v["source_window_digest"]="bad"
    elif kind=="extra_member_field":f["contributions"][0]["beneficial_owner"]="unknown"
    elif kind=="negative_effective_n":f["effective_n_gross"]=-1
    elif kind=="bad_percentile":f["gross_baseline"]["percentile"]=2.0
    elif kind=="bad_clock":v["evaluated_cutoff_utc_s"]="later"
    elif kind=="corrected_known_clock":v["mode"]="corrected_history"
    else:raise AssertionError(kind)
    return v


@pytest.mark.parametrize("kind",[
    "admitted","published","trading","rank","source_proven",
    "owner","confidence","predicted_return","pressure_outlier",
    "negative_gross","unqualified_state","partial_full",
    "schema_version","missing_field","short_authority","bad_digest",
    "extra_member_field","negative_effective_n","bad_percentile",
    "bad_clock","corrected_known_clock"])
def test_invalid_authority_shape_or_unavailable_measure_rejected(kind):
    altered=change(copy.deepcopy(sample()),kind)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(altered,schema())


def test_json_encoding_rejects_nonfinite_market_numbers():
    altered=copy.deepcopy(sample())
    altered["factors"][0]["gross_observed_usd"]=float("nan")
    with pytest.raises(ValueError):
        json.dumps(altered,allow_nan=False)


def test_schema_structure_does_not_claim_mathematical_source_admission():
    s=schema()
    assert "source_quality" in s["required"]
    assert s["properties"]["market_pilot_admitted"]["const"] is False
    assert s["properties"]["additive_market_flow_allowed"]["const"] is False
    assert s["additionalProperties"] is False
    assert "certifies" in s["$comment"]
