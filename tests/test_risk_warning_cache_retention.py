"""Adversarial cached-warning receipts must stay bounded and display-only."""
import json

import pytest

from scripts import risk_warning_projection as projection


def api():
    return projection


def radar(state, score=99):
    return {"schema": "risk_radar.v2", "asof": "2026-09-25",
            "state": state, "top_score": score}


def project(source):
    return projection.project_radar_warning(source, market="us", expected_session="2026-09-25")


def test_last_known_projection_is_bounded_and_cannot_carry_capital_authority():
    previous = project(radar("risk-off", 99))
    previous.update(extension="x" * 100000, score=float("nan"), reason_codes=[float("nan")])
    previous["authority"]["may_execute"] = True
    previous["recovery"] = {"assessed": True, "reentry_authorized": True}
    previous["driver_en"] = {"not": "a label"}
    previous["underlying_input_details"] = {"worst_input_age_days": float("inf")}
    value = api().retain_unresolved_warning(project(None), previous)
    retained = value["last_known"]
    assert retained["authority"]["may_execute"] is False
    assert retained["recovery"]["reentry_authorized"] is False
    assert "extension" not in retained and retained["score"] is None
    assert retained["driver_en"] is None
    assert len(json.dumps(value, allow_nan=False)) < 5000


@pytest.mark.parametrize("field,bad", [
    ("expected_session", "2026-09-24"), ("source_schema", "unrelated.v1")
])
def test_last_known_requires_a_coherent_prior_source_receipt(field, bad):
    previous = project(radar("risk-off"))
    previous[field] = bad
    value = api().retain_unresolved_warning(project(None), previous)
    assert value["status"] == "unavailable"
