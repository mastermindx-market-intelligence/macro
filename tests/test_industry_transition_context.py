from copy import deepcopy
from datetime import datetime, timezone
import io
import json
import zipfile

import pytest
from engine.prophet_lab.industry_transition_context import read_industry_context, validate_snapshot
from scripts.industry_transition_research import parse_archive


def snapshot():
    return {"schema": "prophet.industry_research_snapshot.v1", "as_of": "2002-12-31T00:00:00+00:00",
            "financial_influence": False, "authority": "research_only", "evidence_mode": "RECONSTRUCTED_DISCOVERY",
            "source_refs": ["source-hash"], "forecasts": [{
                "schema": "prophet.industry_transition.v1", "industry": "Meals", "decision_date": "2002-12-31",
                "state": "reversal_attempt", "authority": "research_only", "financial_influence": False,
                "evidence_mode": "RECONSTRUCTED_DISCOVERY", "probabilities": {"upside_first": .4, "downside_first": .2, "timeout": .4},
                "p_bad_loss": .25, "expected_excess_net": .01, "outside_support_share": .1,
                "model": {"calibration_label_end": "2002-12-30", "prediction_start": "2002-12-31",
                          "label_contract": {"horizon": 63, "entry_delay": 1, "target": .1, "loss": .1, "cost": .002}}}]}


def test_real_reader_historical_not_live(tmp_path):
    p = tmp_path / "latest.json"; p.write_text(json.dumps(snapshot()))
    out = read_industry_context(p, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert out["state"] == "HISTORICAL_RESEARCH"
    assert out["live_signal"] is False and out["financial_influence"] is False
    assert len(out["content_sha256"]) == 64


def test_absent_invalid_future_and_oversize(tmp_path):
    p = tmp_path / "missing.json"
    assert read_industry_context(p)["reason"] == "RESEARCH_ARTIFACT_NOT_PRESENT"
    p.write_text("not-json")
    assert read_industry_context(p)["reason"] == "RESEARCH_ARTIFACT_INVALID"
    p.write_text(json.dumps(snapshot()))
    assert read_industry_context(p, now=datetime(2000, 1, 1, tzinfo=timezone.utc))["state"] == "UNAVAILABLE"
    p.write_text(" " * 2_000_001)
    assert read_industry_context(p)["state"] == "UNAVAILABLE"


@pytest.mark.parametrize("change", [
    lambda s: s.update(financial_influence=True),
    lambda s: s["forecasts"][0]["probabilities"].update(timeout=.7),
    lambda s: s["forecasts"][0].update(p_bad_loss=float("nan")),
    lambda s: s["forecasts"].append(deepcopy(s["forecasts"][0])),
    lambda s: s["forecasts"][0]["model"].update(calibration_label_end="2003-01-01"),
    lambda s: s["forecasts"][0].update(context_changes_forecast=True),
    lambda s: s["forecasts"][0].update(k3e=None),
    lambda s: s["forecasts"][0].update(probabilities=None),
    lambda s: s["forecasts"][0]["model"].pop("label_contract"),
])
def test_snapshot_refuses_bad_claims(change):
    s = snapshot(); change(s)
    with pytest.raises((ValueError, KeyError)): validate_snapshot(s)


def test_archive_filters_date_before_numeric_parse():
    text = "vendor header\n,A,B\n20021230,1,-99.99\n20021231,2,3\n20030102,THIS_MUST_NOT_PARSE,garbage\n\n  Next section\n"
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as z: z.writestr("daily.csv", text)
    df, meta = parse_archive(raw.getvalue())
    assert len(df) == 2 and df.iloc[0, 0] == .01 and df.iloc[0, 1] != df.iloc[0, 1]
    assert meta["last"] == "2002-12-31"
    with pytest.raises(ValueError): parse_archive(raw.getvalue(), "2023-01-01")
