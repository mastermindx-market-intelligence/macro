"""Incumbent native Risk publication, clocks and existing summary boundary."""
from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from engine import contagion
from lib.intl_workspace_risk import qualify_us_transmission

KEYS = ("us_hy_oas_vel", "kre_spy_rs", "move_pctile", "sofr_iorb_corridor")
POLICY = {
    "status": "confirmed", "scope": "intl-us-transmission-derived-summary-v1",
    "policy_ref": "docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#incumbent-us-transmission-derived-summary",
    "metadata": "allowed", "value_permission": "allowed",
    "audience": "anonymous-and-registered-intl-html",
    "fields": ["state", "evidence_refs", "diagnostic.reported_state",
               "calculation_at", "observation_dates", "origin_coverage"],
}


@pytest.fixture
def native(monkeypatch):
    def series(end, level, trend=0):
        x = np.arange(600)
        return pd.Series(level + trend * x + .1 * np.sin(x / 11),
                         index=pd.bdate_range(end=end, periods=600))
    frames = {
        ("fred", "BAMLEMRACRPIASIAOAS"): series("2026-10-27", 3).to_frame(),
        ("fred", "BAMLEMRLCRPILAOAS"): series("2026-10-27", 4).to_frame(),
        ("fred", "BAMLEMRECRPIEMEAOAS"): series("2026-10-27", 5).to_frame(),
        ("fred", "BAMLH0A0HYM2"): series("2026-10-27", 3).to_frame(),
        ("yahoo", "SPY"): series("2026-10-26", 400, .15).to_frame("close"),
        ("yahoo", "KRE"): series("2026-10-27", 50, .01).to_frame("close"),
        ("yahoo", "_MOVE"): series("2026-10-23", 100).to_frame("close"),
        ("fred", "SOFR"): series("2026-10-22", 4.5).to_frame(),
        ("fred", "IORB"): series("2026-10-21", 4.6).to_frame(),
        ("yahoo", "DX-Y.NYB"): series("2026-10-27", 100, .01).to_frame("close"),
        ("fred", "DGS2"): series("2026-10-27", 4).to_frame(),
    }
    def read(group, key):
        frame = frames.get((group, key))
        return frame.copy() if frame is not None else None
    monkeypatch.setattr(contagion.store, "read", read)
    raw = contagion.two_tier_read(em_stress_state="stressed")
    origin = {
        "state": "stressed", "as_of": "2026-10-20", "built": raw["built"],
        "n_legs_available": 3, "n_legs_total": 6,
        "legs": {key: {"asof": "2026-10-20"} for key in ("em_hy_oas", "vxeem", "em_fx_basket")},
        "k_of_n_params": {"min_legs_for_state": 3},
    }
    return {"built": raw["built"], "two_tier": raw, "em_stress": origin}, frames


def test_native_observation_clocks_survive_the_actual_calculation(native):
    payload, _ = native
    raw = payload["two_tier"]
    observations = raw["publication_inputs"]
    assert set(observations) == set(KEYS)
    assert raw["state"] == "contained"
    assert raw["tier2"]["hot_count"] == 0
    assert all(raw["tier2"]["legs"][key]["hot"] is False for key in KEYS)
    assert observations["us_hy_oas_vel"]["observation_at"] == "2026-10-27"
    assert observations["move_pctile"]["observation_at"] == "2026-10-23"
    corridor = observations["sofr_iorb_corridor"]
    assert corridor["observation_at"] == "2026-10-22"
    assert [item["observation_at"] for item in corridor["inputs"]] == ["2026-10-22", "2026-10-21"]
    for key, observation in observations.items():
        assert observation["calculation_available"] is True
        assert observation["observation_at"] != raw["built"]
        assert all(len(item["calculation_input_sha256"]) == 64 for item in observation["inputs"])


def publication(tmp_path, payload):
    from lib.intl_risk_publication import publish_risk_snapshot
    directory = tmp_path / "intl_risk"
    directory.mkdir(exist_ok=True)
    return publish_risk_snapshot(directory / "latest.json", payload)


def eligibility(payload, receipt):
    from lib.intl_risk_publication import risk_summary_eligibility
    return risk_summary_eligibility(risk_desk=payload, publication=receipt, policy=POLICY)


@pytest.mark.parametrize("change", [None, "proposed", "refused", "raw", "audience", "value", "scope"])
def test_public_summary_needs_its_exact_existing_publisher_declaration(tmp_path, native, change):
    from lib.intl_risk_publication import risk_summary_eligibility
    payload, _ = native
    receipt = publication(tmp_path, payload)
    policy = deepcopy(POLICY)
    if change is None: policy = None
    elif change in {"proposed", "refused"}: policy["status"] = change
    elif change == "raw": policy["fields"].append("raw_values")
    elif change == "audience": policy["audience"] = "registered-only"
    elif change == "value": policy["value_permission"] = "unknown"
    elif change == "scope": policy["scope"] = "intl-index-fx-eod-user-facing-v1"
    assert risk_summary_eligibility(risk_desk=payload, publication=receipt, policy=policy) == {}


def test_successful_native_write_read_reaches_existing_consumer(tmp_path, native):
    payload, _ = native
    receipt = publication(tmp_path, payload)
    support = eligibility(payload, receipt)
    summary = qualify_us_transmission(two_tier=payload["two_tier"], eligibility=support)
    assert summary["quality"] == "qualified" and summary["state"] == "contained"
    assert support["asof"] == payload["two_tier"]["built"]
    assert support["origin"]["observation_at"] == "2026-10-20"
    assert support["legs"]["move_pctile"]["observation_at"] == "2026-10-23"
    assert all(receipt.artifact_sha256 in ref for ref in summary["evidence_refs"] if ref.startswith("sha256:"))
    assert json.loads(receipt.path.read_text()) == payload


def test_no_receipt_after_failed_write_even_with_same_old_payload(tmp_path, native, monkeypatch):
    from lib.intl_risk_publication import publish_risk_snapshot
    payload, _ = native
    old = publication(tmp_path, payload)
    def failed_write(*args, **kwargs):
        raise OSError("controlled write failure")
    monkeypatch.setattr(Path, "write_text", failed_write)
    receipt = None
    with pytest.raises(OSError, match="controlled write failure"):
        receipt = publish_risk_snapshot(old.path, payload)
    assert receipt is None
    assert eligibility(payload, receipt) == {}


def test_changed_readback_or_payload_cannot_reuse_success(tmp_path, native):
    payload, _ = native
    receipt = publication(tmp_path, payload)
    changed = deepcopy(payload)
    changed["two_tier"]["tier2"]["legs"]["us_hy_oas_vel"]["hot"] = True
    assert eligibility(changed, receipt) == {}
    receipt.path.write_text("{}")
    assert eligibility(payload, receipt) == {}


@pytest.mark.parametrize("mutation", [
    "missing_origin", "unknown_origin", "partial_origin", "origin_mismatch",
    "missing_clock", "missing_input_clock", "bad_input_identity", "wrong_source",
    "missing_leg", "nonboolean_hot", "inconsistent_count", "state_mismatch",
    "calculation_unavailable", "missing_observations", "future_source_clock",
])
def test_partial_malformed_or_unavailable_native_input_is_withheld(tmp_path, native, mutation):
    payload, _ = native
    raw = payload["two_tier"]
    observations = raw["publication_inputs"]
    if mutation == "missing_origin": payload["em_stress"] = None
    elif mutation == "unknown_origin": payload["em_stress"]["state"] = "insufficient_data"
    elif mutation == "partial_origin": payload["em_stress"]["n_legs_available"] = 2
    elif mutation == "origin_mismatch": payload["em_stress"]["state"] = "calm"
    elif mutation == "missing_clock": del observations[KEYS[0]]["observation_at"]
    elif mutation == "missing_input_clock": del observations[KEYS[0]]["inputs"][0]["observation_at"]
    elif mutation == "bad_input_identity": observations[KEYS[0]]["inputs"][0]["calculation_input_sha256"] = "bad"
    elif mutation == "wrong_source": observations[KEYS[0]]["inputs"][0]["source_reference"] = "data/fred/SOFR.parquet"
    elif mutation == "missing_leg": del raw["tier2"]["legs"][KEYS[0]]
    elif mutation == "nonboolean_hot": raw["tier2"]["legs"][KEYS[0]]["hot"] = 0
    elif mutation == "inconsistent_count": raw["tier2"]["hot_count"] = 1
    elif mutation == "state_mismatch": raw["state"] = "quiet"
    elif mutation == "calculation_unavailable": observations[KEYS[0]]["calculation_available"] = False
    elif mutation == "missing_observations": del raw["publication_inputs"]
    elif mutation == "future_source_clock": observations[KEYS[0]]["inputs"][0]["observation_at"] = "9999-01-01"
    assert eligibility(payload, publication(tmp_path, payload)) == {}


def test_native_missing_source_and_short_calculation_stay_unavailable(tmp_path, native):
    payload, frames = native
    frames[("fred", "BAMLH0A0HYM2")] = frames[("fred", "BAMLH0A0HYM2")].tail(2)
    del frames[("yahoo", "_MOVE")]
    payload["two_tier"] = contagion.two_tier_read(em_stress_state="stressed")
    assert payload["two_tier"]["publication_inputs"]["us_hy_oas_vel"]["calculation_available"] is False
    assert "move_pctile" not in payload["two_tier"]["publication_inputs"]
    assert eligibility(payload, publication(tmp_path, payload)) == {}


def test_observation_metadata_failure_does_not_break_legacy_calculation(tmp_path, native):
    payload, frames = native
    frame = frames[("fred", "BAMLH0A0HYM2")]
    frame.index = pd.RangeIndex(len(frame))
    payload["two_tier"] = contagion.two_tier_read(em_stress_state="stressed")
    assert payload["two_tier"]["state"] in {"contained", "watching", "transmitting"}
    assert payload["two_tier"]["publication_inputs"]["us_hy_oas_vel"]["observation_at"] is None
    assert eligibility(payload, publication(tmp_path, payload)) == {}


def test_optional_missing_safety_bid_does_not_replace_or_block_four_legs(tmp_path, native):
    payload, frames = native
    del frames[("yahoo", "DX-Y.NYB")]
    del frames[("fred", "DGS2")]
    payload["two_tier"] = contagion.two_tier_read(em_stress_state="stressed")
    payload["built"] = payload["two_tier"]["built"]
    assert payload["two_tier"]["safety_bid"] is None
    support = eligibility(payload, publication(tmp_path, payload))
    assert qualify_us_transmission(two_tier=payload["two_tier"], eligibility=support)["quality"] == "qualified"


@pytest.mark.parametrize("origin,hot_count,state", [
    ("stressed", 1, "watching"), ("strained", 2, "transmitting"), ("calm", 2, "quiet"),
])
def test_existing_native_state_rules_are_preserved_through_publication(tmp_path, native, origin, hot_count, state):
    payload, frames = native
    frames[("yahoo", "_MOVE")].iloc[-1, 0] += 1000
    if hot_count == 2:
        frames[("fred", "BAMLH0A0HYM2")].iloc[-1, 0] += 20
    payload["two_tier"] = contagion.two_tier_read(em_stress_state=origin)
    payload["built"] = payload["two_tier"]["built"]
    payload["em_stress"]["state"] = origin
    assert payload["two_tier"]["tier2"]["hot_count"] == hot_count
    support = eligibility(payload, publication(tmp_path, payload))
    assert qualify_us_transmission(two_tier=payload["two_tier"], eligibility=support)["state"] == state


def test_immutable_receipt_is_not_a_supplied_dictionary_grant(tmp_path, native):
    payload, _ = native
    receipt = publication(tmp_path, payload)
    assert eligibility(payload, {"path": receipt.path, "artifact_sha256": receipt.artifact_sha256}) == {}


def test_readback_failure_does_not_return_publication(tmp_path, native, monkeypatch):
    from lib.intl_risk_publication import publish_risk_snapshot
    payload, _ = native
    directory = tmp_path / "intl_risk"
    directory.mkdir()
    monkeypatch.setattr(Path, "read_bytes", lambda self: b"changed during publication")
    with pytest.raises(OSError, match="readback mismatch"):
        publish_risk_snapshot(directory / "latest.json", payload)


def test_existing_risk_mount_consumes_positive_native_summary_only(tmp_path, native):
    from scripts import build_intl
    from lib.intl_risk_mount import attach_risks
    payload, _ = native
    support = eligibility(payload, publication(tmp_path, payload))
    base = build_intl._publication_workspace(None, data_root=tmp_path,
                                           evaluated_at=payload["built"])
    registry = base["risk_registry"]
    # Re-enter the actual pre-Risk seam, before History/Surveillance attach
    # presentation-only tuple copy that intentionally is not a raw input tree.
    base = {key: base[key] for key in
            ("config", "panels", "binding_version", "macros", "macro_registry")}
    joined = attach_risks(base, registry=registry, risk_desk=payload, cgl=None,
                         measures={}, field_support={}, destinations={},
                         summary_eligibility={"us_transmission": support})
    assert len(joined["risks"]) == len(joined["panels"])
    for panel in joined["risks"]:
        section = panel["risk_section"]
        summary = section["domain_panels"]["us_transmission"]["summary"]
        assert summary["quality"] == "qualified" and summary["state"] == "contained"
        clocks = section["domain_panels"]["us_transmission"]["observations"]
        assert clocks["calculation_at"] == payload["two_tier"]["built"]
        assert clocks["origin_coverage"] == {"available": 3, "total": 6}
        assert [item["observation_at"] for item in clocks["legs"][-1]["inputs"]] == ["2026-10-22", "2026-10-21"]
        assert all(row["country_credit_change"]["quality"] == "unknown"
                   for row in section["pressure_rows"])
    panel = joined["risks"][0]
    section = panel["risk_section"]
    template = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1]),
                           undefined=StrictUndefined).get_template("templates/intl_workspace/risk.html.j2")
    def render():
        return template.render(risk_section=section, registry=registry,
                               context_id=panel["context_id"], panel_context=panel["context"],
                               generation=panel.get("generation", base["config"]["source_reference"]))
    html = render()
    assert "Current statement" not in html and "当前陈述" not in html
    assert "Transmission assessment" in html and "传导评估" in html
    assert "Calculated at" in html and "计算时间" in html
    assert payload["two_tier"]["built"] in html
    assert "Input observation dates" in html and "输入观测日期" in html
    assert "2026-10-22" in html and "2026-10-21" in html
    assert "SOFR" in html and "IORB" in html and "3/6" in html
    assert "Partial origin coverage" in html and "源头覆盖不完整" in html
    assert "Observation date unavailable" in html and "观测日期不可用" in html
    assert "does not establish market freshness" in html and "不能证明市场数据的时效性" in html
    # Unbound legacy support cannot borrow a nearby raw packet's clocks.
    del section["domain_panels"]["us_transmission"]["observations"]
    html = render()
    assert "Input observation dates unavailable" in html and "输入观测日期不可用" in html


@pytest.mark.parametrize("group,key,position", [
    ("yahoo", "_MOVE", -1), ("yahoo", "_MOVE", 0),
    ("fred", "BAMLH0A0HYM2", -1),
    ("yahoo", "KRE", -1), ("yahoo", "SPY", -1),
    ("fred", "SOFR", -1), ("fred", "IORB", -1),
])
def test_nonfinite_native_calculation_frame_never_receives_eligibility(tmp_path, native, group, key, position):
    payload, frames = native
    frames[(group, key)].iloc[position, 0] = np.inf
    payload["two_tier"] = contagion.two_tier_read(em_stress_state="stressed")
    payload["built"] = payload["two_tier"]["built"]
    # Keep the legacy native result. Only the publication observer withholds.
    assert eligibility(payload, publication(tmp_path, payload)) == {}


@pytest.mark.parametrize("group,key,position", [
    ("fred", "BAMLH0A0HYM2", 0), ("yahoo", "KRE", -10),
    ("yahoo", "SPY", -10), ("fred", "SOFR", 0), ("fred", "IORB", 0),
])
def test_nonfinite_history_not_consumed_by_the_metric_does_not_block_it(tmp_path, native, group, key, position):
    payload, frames = native
    frames[(group, key)].iloc[position, 0] = np.inf
    payload["two_tier"] = contagion.two_tier_read(em_stress_state="stressed")
    payload["built"] = payload["two_tier"]["built"]
    support = eligibility(payload, publication(tmp_path, payload))
    assert qualify_us_transmission(two_tier=payload["two_tier"], eligibility=support)["quality"] == "qualified"


@pytest.mark.parametrize("group,key", [
    ("fred", "BAMLH0A0HYM2"), ("yahoo", "KRE"), ("yahoo", "SPY"),
    ("yahoo", "_MOVE"), ("fred", "SOFR"), ("fred", "IORB"),
])
def test_missing_observations_excluded_by_native_reads_remain_eligible(tmp_path, native, group, key):
    payload, frames = native
    frames[(group, key)].iloc[-10, 0] = np.nan
    payload["two_tier"] = contagion.two_tier_read(em_stress_state="stressed")
    payload["built"] = payload["two_tier"]["built"]
    support = eligibility(payload, publication(tmp_path, payload))
    assert qualify_us_transmission(two_tier=payload["two_tier"], eligibility=support)["quality"] == "qualified"


def test_excluded_missing_terminal_observation_keeps_the_real_last_valid_date(tmp_path, native):
    payload, frames = native
    frame = frames[("yahoo", "_MOVE")]
    last_valid = frame.index[-2].date().isoformat()
    frame.iloc[-1, 0] = np.nan
    payload["two_tier"] = contagion.two_tier_read(em_stress_state="stressed")
    payload["built"] = payload["two_tier"]["built"]
    support = eligibility(payload, publication(tmp_path, payload))
    assert support["legs"]["move_pctile"]["observation_at"] == last_valid
    assert payload["two_tier"]["publication_inputs"]["move_pctile"]["inputs"][0]["observation_at"] == last_valid
