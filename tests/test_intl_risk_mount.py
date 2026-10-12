"""Real Risk projection joins must retain the existing publication binding."""
from copy import deepcopy

import pytest

from lib.intl_risk_mount import attach_risks
from tests.test_intl_workspace_risk_section import inputs

GENERATION = "im-workspace-generation:12345678-1234-4123-8123-123456789012"


def fixture():
    source = inputs()
    source.pop("context")
    overview = source.pop("overview")
    source["registry"]["horizons"] = ["1m"]
    source["registry"]["bases"] = ["usd_unhedged"]
    workspace = {
        "binding_version": 2,
        "config": {
            "markets": ["KR", "GB"], "horizons": ["1m"], "bases": ["usd_unhedged"],
            "default_horizon": "1m", "default_basis": "usd_unhedged",
            "source_reference": GENERATION, "anchor_ids": ["intl-legacy-research"],
            "library_group_ids": [],
        },
        "panels": [{"context_id": "im-overview-0", "generation": GENERATION, "overview": overview}],
        "existing_material": {"owner": "untouched"},
    }
    return workspace, source


def test_real_projection_keeps_generation_arithmetic_pressure_and_supported_summary():
    workspace, source = fixture()
    before = deepcopy((workspace, source))
    mounted = attach_risks(workspace, **source)
    panel = mounted["risks"][0]
    section = panel["risk_section"]
    assert panel["context_id"] == "im-overview-0"
    assert panel["generation"] == GENERATION
    assert section["selected_market"] is None
    assert section["currency_channels"][0]["usd_return"]["value"] == pytest.approx(-2.5856)
    assert section["pressure_rows"][0]["country_credit_change"]["value"] == 0
    assert section["domain_panels"]["us_transmission"]["summary"]["quality"] == "qualified"
    assert mounted["risk_registry"] == source["registry"]
    assert mounted["existing_material"] == workspace["existing_material"]
    assert (workspace, source) == before
    panel["risk_section"]["pressure_rows"][0]["country_credit_change"]["value"] = 999
    mounted["risk_registry"]["markets"][0]["name_en"] = "changed"
    assert (workspace, source) == before


def test_missing_sources_do_not_remove_currency_or_configured_roster():
    workspace, source = fixture()
    source.update(risk_desk=None, cgl=None, measures={}, field_support={}, summary_eligibility={}, destinations={})
    section = attach_risks(workspace, **source)["risks"][0]["risk_section"]
    assert len(section["pressure_rows"]) == 2
    assert section["currency_channels"][0]["local_return"]["value"] == -1.8
    assert section["domain_panels"]["us_transmission"]["summary"]["state"] is None


@pytest.mark.parametrize("mutate", [
    lambda w, s: w["panels"][0].update(generation="im-workspace-generation:99999999-9999-4999-8999-999999999999"),
    lambda w, s: w["panels"].append(deepcopy(w["panels"][0])),
    lambda w, s: s["registry"]["markets"].reverse(),
    lambda w, s: s["registry"].update(horizons=["3m"]),
    lambda w, s: w["panels"][0]["overview"]["context"].update(return_basis="total_return"),
    lambda w, s: w.update(risks=[]),
    lambda w, s: w.update(risk_registry={}),
    lambda w, s: w.update(binding_version=True),
    lambda w, s: w["panels"].clear(),
])
def test_invalid_join_is_fixed_error_and_never_mutates_owner(mutate):
    workspace, source = fixture()
    mutate(workspace, source)
    before = deepcopy((workspace, source))
    with pytest.raises(ValueError, match="^invalid_risk_workspace$"):
        attach_risks(workspace, **source)
    assert (workspace, source) == before


def test_v1_remains_readable_without_admitting_new_pressure_or_summary():
    workspace, source = fixture()
    workspace.pop("binding_version")
    workspace["panels"][0].pop("generation")
    workspace["config"]["source_reference"] = workspace["panels"][0]["overview"]["context"]["source_reference"]
    panel = attach_risks(workspace, **source)["risks"][0]
    assert "generation" not in panel
    section = panel["risk_section"]
    assert section["currency_channels"][0]["local_return"]["value"] == -1.8
    assert section["pressure_rows"][0]["country_credit_change"]["quality"] == "unknown"
    assert section["domain_panels"]["us_transmission"]["summary"]["quality"] == "unknown"


def test_no_workspace_stays_none():
    _, source = fixture()
    assert attach_risks(None, **source) is None


def test_deep_cycles_and_nonfinite_owned_material_fail_without_raw_error():
    workspace, source = fixture()
    workspace["existing_material"]["self"] = workspace
    with pytest.raises(ValueError, match="^invalid_risk_workspace$"):
        attach_risks(workspace, **source)
    workspace, source = fixture()
    source["cgl"]["unknown_metric"] = float("nan")
    with pytest.raises(ValueError, match="^invalid_risk_workspace$"):
        attach_risks(workspace, **source)


@pytest.mark.parametrize("value", [10 ** 400, -(10 ** 400), 0])
def test_real_v1_retains_currency_when_unadmitted_measure_is_extreme(value):
    workspace, source = fixture()
    workspace.pop("binding_version")
    workspace["panels"][0].pop("generation")
    workspace["config"]["source_reference"] = workspace["panels"][0]["overview"]["context"]["source_reference"]
    source["measures"]["KR.country_credit_change"]["value"] = value
    section = attach_risks(workspace, **source)["risks"][0]["risk_section"]
    assert section["currency_channels"][0]["local_return"]["value"] == -1.8
    assert section["pressure_rows"][0]["country_credit_change"]["quality"] == "unknown"
    assert section["domain_panels"]["us_transmission"]["summary"]["quality"] == "unknown"
