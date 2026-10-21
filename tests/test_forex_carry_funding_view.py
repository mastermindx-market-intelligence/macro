"""R19: carry/funding evidence is a read-only projection of existing Forex owners."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def _mod():
    return importlib.import_module("lib.forex_carry_funding_view")


def _pairs():
    return [
        {
            "key": "USDJPY", "label": "USD / JPY", "base": "JPY",
            "carry_diff": -2.88, "carry_to_vol": -0.31, "rate_diff_10y": -2.42,
            "pos_pctile": 87.0, "pos_state": "crowded_long", "carry_context": False,
        },
        {
            "key": "AUDUSD", "label": "AUD / USD", "base": "AUD",
            "carry_diff": 0.37, "carry_to_vol": 0.04, "rate_diff_10y": 0.61,
            "pos_pctile": 52.0, "pos_state": "neutral", "carry_context": False,
        },
        {
            "key": "USDMXN", "label": "USD / MXN", "base": "MXN",
            "carry_diff": None, "carry_to_vol": None, "rate_diff_10y": None,
            "pos_pctile": 91.0, "pos_state": "crowded_long", "carry_context": True,
        },
    ]


def _carry_scenario(*, status="ok", active=False, intensity=14.8, n_fired=1, min_legs=3):
    return {
        "key": "carry_unwind",
        "name_en": "Carry Unwind / Yen-Funded Deleveraging",
        "name_zh": "套息平仓 / 日元融资去杠杆",
        "intensity_today": intensity,
        "n_fired": n_fired,
        "min_legs": min_legs,
        "active": active,
        "illustrative": False,
        "fired_legs": [
            {"id": "funder_5d_z", "kind": "velocity", "en": "Funders surging",
             "zh": "融资货币飙升", "fired": True, "value": 1.22, "absent": False},
            {"id": "carry_5d_z", "kind": "velocity", "en": "Carry basket falling",
             "zh": "套息篮子下跌", "fired": False, "value": 0.24, "absent": False},
            {"id": "carry_resid_corr", "kind": "level", "en": "Carry residuals moving together",
             "zh": "套息残差同步", "fired": False, "value": None, "absent": True},
        ],
        "prob": {
            "status": status,
            "p_cond": 0.157, "base_rate": 0.105,
            "wilson_lo": 0.092, "wilson_hi": 0.255,
            "n_raw": 226, "n_eff": 75.3, "N": 10,
        },
        "disc_en": "Funders surge while carry/EM crash together.",
        "disc_zh": "融资货币走强且套息/新兴市场同步下跌。",
    }


def _regime(**kwargs):
    return {"as_of": "2026-09-28", "scenarios": [_carry_scenario(**kwargs)]}


def _funding():
    return {
        "ofr_fsi": {"status": "available", "value": -2.663, "calculated_through": "2026-09-23",
                    "source_family": "ofr_fsi"},
        "ofr_funding": {"status": "available", "value": -0.166, "calculated_through": "2026-09-23",
                        "source_family": "ofr_fsi"},
        "sofr_iorb": {"status": "available", "value_bp": -2.0, "hot": False,
                      "last5_all_positive": False, "calculated_through": None,
                      "artifact_built": "2026-09-27T08:06:33+00:00",
                      "source_family": "intl_risk_two_tier"},
        "a2p2_spread": {"status": "available", "value_bp": 16.0, "artifact_as_of": "2026-09-29",
                        "source_family": "regime_systemic_stress"},
        "cp_bill_spread": {"status": "available", "value_bp": 0.0, "artifact_as_of": "2026-09-29",
                           "stress_state": "normal", "source_family": "regime_systemic_stress"},
        "direct_usd_xccy_basis": {"status": "unavailable", "reason": "not_collected",
                                  "source_family": "direct_usd_xccy_basis"},
    }


def test_projection_preserves_distinct_units_and_never_emits_composite_score():
    got = _mod().project_carry_funding(_pairs(), _regime(), _funding())
    assert got["version"] == 1 and got["display_only"] is True
    assert "score" not in got and "confidence" not in got and "probability" not in got
    row = next(r for r in got["rate_edges"] if r["pair"] == "USDJPY")
    assert row["carry_diff"]["value"] == -2.88
    assert row["carry_diff"]["unit"] == "percentage_points_annualized"
    assert row["carry_to_vol"]["value"] == -0.31
    assert row["carry_to_vol"]["unit"] == "ratio"
    assert row["rate_diff_10y"]["unit"] == "percentage_points"
    assert row["positioning"]["unit"] == "percentile_rank_0_100"
    assert row["source_freshness"] == "unknown"


def test_context_only_em_pair_does_not_acquire_fake_carry():
    got = _mod().project_carry_funding(_pairs(), _regime(), _funding())
    row = next(r for r in got["rate_edges"] if r["pair"] == "USDMXN")
    assert row["carry_context_only"] is True
    assert row["carry_diff"]["status"] == "unavailable"
    assert row["carry_to_vol"]["status"] == "unavailable"
    assert row["positioning"]["value"] == 91.0


@pytest.mark.parametrize("active", ["false", 1, 0, None])
def test_nonboolean_scenario_state_is_unknown_not_active_or_inactive(active):
    got = _mod().project_carry_funding(_pairs(), _regime(active=active), _funding())
    assert got["carry_unwind"]["state"] == "unknown"
    assert got["carry_unwind"]["active"] is None


def test_canonical_scenario_owns_confirmation_and_fired_legs():
    got = _mod().project_carry_funding(_pairs(), _regime(active=False, n_fired=1, min_legs=3), _funding())
    s = got["carry_unwind"]
    assert s["state"] == "inactive" and s["active"] is False
    assert s["intensity"] == 14.8
    assert s["n_fired"] == 1 and s["min_legs"] == 3
    assert [x["id"] for x in s["legs"]] == ["funder_5d_z", "carry_5d_z", "carry_resid_corr"]
    assert s["legs"][2]["status"] == "unavailable"
    assert s["legs"][0]["fired"] is True
    assert "derived_confirmation" not in s


def test_historical_receipt_is_past_tense_and_sample_gated():
    ok = _mod().project_carry_funding(_pairs(), _regime(status="ok"), _funding())["carry_unwind"]["historical_receipt"]
    assert ok["status"] == "ok"
    assert ok["conditional_frequency"] == 0.157
    assert ok["base_rate"] == 0.105
    assert ok["n_raw"] == 226 and ok["horizon_sessions"] == 10
    assert "wilson" not in ok and "n_eff" not in ok
    assert ok["uncertainty"] == {
        "status": "withheld_unqualified",
        "method": "legacy_n_raw_over_horizon_wilson",
        "reason": "dependence_adjustment_not_qualified",
    }
    assert ok["semantics"] == "past_conditional_frequency_not_forecast"

    insufficient = _mod().project_carry_funding(_pairs(), _regime(status="insufficient"), _funding())["carry_unwind"]["historical_receipt"]
    assert insufficient["status"] == "insufficient"
    assert insufficient["headline_frequency"] is None
    assert insufficient["semantics"] == "insufficient_sample_not_forecast"


def test_funding_proxies_are_not_independent_votes_and_direct_basis_stays_missing():
    got = _mod().project_carry_funding(_pairs(), _regime(), _funding())["funding"]
    assert got["ofr_fsi"]["value"] == -2.663
    assert got["ofr_funding"]["value"] == -0.166
    assert got["ofr_fsi"]["family"] == got["ofr_funding"]["family"] == "ofr_fsi"
    assert got["ofr_family_independent_votes"] is False
    assert got["sofr_iorb"]["value_bp"] == -2.0
    assert got["direct_usd_xccy_basis"]["status"] == "unavailable"
    assert got["direct_usd_xccy_basis"]["reason"] == "not_collected"
    assert got["funding_interpretation"] == "proxy_context_only"


def test_owner_stamped_direct_basis_receipt_is_consumed_without_local_date_admission():
    receipt = {
        "value_bps": 0.0,
        "asof": "2026-10-02",
        "source": "qualified-direct-owner",
        "date_status": "known",
    }
    got = _mod().collect_funding_context(
        lambda *_: None, {}, {}, direct_basis_receipt=receipt
    )
    direct = got["direct_usd_xccy_basis"]
    assert direct == {
        "status": "available",
        "value_bp": 0.0,
        "unit": "basis_points",
        "asof": "2026-10-02",
        "source": "qualified-direct-owner",
        "date_status": "known",
        "source_family": "direct_usd_xccy_basis",
    }

    view = _mod().project_carry_funding(_pairs(), _regime(), got)
    assert view["funding"]["direct_usd_xccy_basis"]["status"] == "available"
    assert view["funding"]["direct_usd_xccy_basis"]["value_bp"] == 0.0
    assert view["funding"]["state"] == "partial"
    assert "direct_usd_cross_currency_basis_unavailable" not in view["limitations"]


def test_direct_basis_without_owner_admission_stamp_stays_unavailable():
    receipt = {
        "value_bps": -12.5,
        "asof": "2026-10-02",
        "source": "looks-valid-but-not-owner-admitted",
    }
    got = _mod().collect_funding_context(
        lambda *_: None, {}, {}, direct_basis_receipt=receipt
    )
    direct = got["direct_usd_xccy_basis"]
    assert direct["status"] == "unavailable"
    assert direct["reason"] == "owner_receipt_not_admitted"

    # The consumer trusts the owner's admission stamp instead of duplicating
    # calendar-date parsing here. A malformed date with no stamp must still fail closed.
    malformed = _mod().collect_funding_context(
        lambda *_: None, {}, {},
        direct_basis_receipt={
            "value_bps": -9.0,
            "asof": "not-a-date",
            "source": "unadmitted",
        },
    )["direct_usd_xccy_basis"]
    assert malformed["status"] == "unavailable"
    assert malformed["reason"] == "owner_receipt_not_admitted"


def test_missing_funding_never_changes_carry_scenario_state():
    regime = _regime(active=True, n_fired=3, min_legs=3)
    for i, leg in enumerate(regime["scenarios"][0]["fired_legs"], start=1):
        leg.update(fired=True, absent=False, value=float(i))
    got = _mod().project_carry_funding(
        _pairs(), regime,
        {"direct_usd_xccy_basis": {"status": "unavailable", "reason": "not_collected"}},
    )
    assert got["carry_unwind"]["state"] == "active"
    assert got["funding"]["state"] == "partial"
    assert got["funding"]["direct_usd_xccy_basis"]["status"] == "unavailable"


def test_missing_or_malformed_pair_values_are_withheld_not_zero():
    pairs = _pairs()
    pairs[0]["carry_diff"] = True
    pairs[0]["carry_to_vol"] = float("inf")
    pairs[0]["pos_pctile"] = 101
    got = _mod().project_carry_funding(pairs, _regime(), _funding())
    row = got["rate_edges"][0]
    assert row["carry_diff"] == {"status": "invalid", "value": None, "unit": "percentage_points_annualized"}
    assert row["carry_to_vol"] == {"status": "invalid", "value": None, "unit": "ratio"}
    assert row["positioning"]["status"] == "invalid" and row["positioning"]["value"] is None


def test_duplicate_pair_identity_quarantines_both_rows():
    pairs = _pairs() + [{**_pairs()[0], "carry_diff": 99}]
    got = _mod().project_carry_funding(pairs, _regime(), _funding())
    rows = [r for r in got["rate_edges"] if r["pair"] == "USDJPY"]
    assert len(rows) == 1
    assert rows[0]["identity_status"] == "conflict"
    assert rows[0]["carry_diff"]["value"] is None


def test_collect_funding_context_consumes_published_artifacts_without_recomputing_contagion():
    idx = pd.to_datetime(["2026-09-22", "2026-09-23"])
    frames = {
        ("ofr_fsi", "fsi"): pd.DataFrame({"value": [-2.5, -2.663]}, index=idx),
        ("ofr_fsi", "fsi_funding"): pd.DataFrame({"value": [-0.12, -0.166]}, index=idx),
    }
    def read(group, name):
        return frames.get((group, name))

    # Canonical intl_risk artifact stores the rate spread in percentage points.
    intl_risk = {
        "built": "2026-09-27T08:06:33+00:00",
        "two_tier": {"tier2": {"legs": {"sofr_iorb_corridor": {
            "value": -0.02, "last5_all_positive": False, "hot": False,
            "threshold": "SOFR-IORB > 0 for 5 consecutive days",
            "caveat": "Quarter-end spikes can be technical.",
        }}}},
    }
    regime = {
        "asof": "2026-09-29",
        "conditions": {"systemic_stress": {
            "a2p2_spread_bps": 16,
            "cp_bill_spread_bps": 0,
            "cp_stress": "normal",
        }},
    }
    got = _mod().collect_funding_context(read, intl_risk, regime)
    assert got["ofr_fsi"]["calculated_through"] == "2026-09-23"
    assert got["ofr_funding"]["calculated_through"] == "2026-09-23"
    assert got["sofr_iorb"]["value_bp"] == -2.0
    assert got["sofr_iorb"]["calculated_through"] is None
    assert got["sofr_iorb"]["artifact_built"] == "2026-09-27T08:06:33+00:00"
    assert got["a2p2_spread"]["value_bp"] == 16
    assert got["a2p2_spread"]["artifact_as_of"] == "2026-09-29"
    assert got["cp_bill_spread"]["value_bp"] == 0
    assert got["cp_bill_spread"]["stress_state"] == "normal"
    assert got["direct_usd_xccy_basis"]["status"] == "unavailable"


def test_bool_and_missing_funding_values_fail_closed_without_zero_substitution():
    idx = pd.to_datetime(["2026-09-23"])
    def read(group, name):
        value = True if name == "fsi" else float("nan")
        return pd.DataFrame({"value": [value]}, index=idx)
    got = _mod().collect_funding_context(read, {}, {})
    assert got["ofr_fsi"]["status"] == "invalid"
    assert got["ofr_funding"]["status"] == "unavailable"
    assert got["ofr_funding"]["value"] is None
    assert got["sofr_iorb"]["status"] == "unavailable"
    assert got["a2p2_spread"]["status"] == "unavailable"
    assert got["cp_bill_spread"]["status"] == "unavailable"


def _render(view):
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    return env.get_template("_forex_carry_funding.html.j2").render(carry_funding_view=view)


def test_template_is_read_only_bilingual_and_never_says_funding_is_normal():
    from bs4 import BeautifulSoup
    view = _mod().project_carry_funding(_pairs(), _regime(), _funding())
    html = _render(view)
    visible = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    assert "Carry & funding evidence" in visible and "套息与融资证据" in visible
    assert "14.8" in visible and "Inactive" in visible
    assert "A2/P2" in visible and "16.0 bp" in visible
    assert "CP − bill" in visible and "0.0 bp" in visible
    assert "Direct USD cross-currency basis" in visible
    assert "Unavailable" in visible
    assert "proxy" in visible.lower()
    assert "funding is normal" not in visible.lower()
    assert "funding normal" not in visible.lower()
    assert "<script" not in html
    assert "<input" not in html and "<button" not in html


def test_template_renders_owner_qualified_direct_basis_without_proxy_substitution():
    from bs4 import BeautifulSoup

    funding = _funding()
    funding["direct_usd_xccy_basis"] = {
        "status": "available",
        "value_bp": 0.0,
        "unit": "basis_points",
        "asof": "2026-10-02",
        "source": "qualified-direct-owner",
        "date_status": "known",
        "source_family": "direct_usd_xccy_basis",
    }
    view = _mod().project_carry_funding(_pairs(), _regime(), funding)
    html = _render(view)
    visible = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)

    assert "Direct USD cross-currency basis" in visible
    assert "0.0 bp" in visible
    assert "qualified-direct-owner" in visible
    assert "2026-10-02" in visible
    assert "owner-qualified direct receipt" in visible
    assert "Direct USD cross-currency basis · Unavailable" not in visible
    assert "funding is normal" not in visible.lower()
    assert "direct_usd_cross_currency_basis_unavailable" not in view["limitations"]


def test_template_withholds_frequency_when_sample_is_insufficient():
    view = _mod().project_carry_funding(_pairs(), _regime(status="insufficient"), _funding())
    html = _render(view)
    assert "Insufficient sample" in html
    assert "15.7%" not in html


def test_template_withholds_unqualified_uncertainty_and_uses_rule_state_copy():
    from bs4 import BeautifulSoup
    view = _mod().project_carry_funding(_pairs(), _regime(status="ok"), _funding())
    html = _render(view)
    visible = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    assert "Existing carry-unwind scenario rule is inactive." in visible
    assert "confirmed" not in visible.lower()
    assert "95% Wilson" not in visible
    assert "75.3" not in visible
    assert "Dependence-adjusted interval withheld" in visible
    assert "n_eff/Wilson shortcut" in visible
    assert "Raw sample" in visible and "226" in visible
    assert "Horizon" in visible and "10 sessions" in visible


def test_parent_forex_route_includes_exactly_one_carry_funding_component():
    source = (TEMPLATES / "forex.html.j2").read_text()
    assert source.count('{% include "_forex_carry_funding.html.j2" %}') == 1
    assert source.index('{% include "_forex_movement_evidence.html.j2" %}') < source.index('{% include "_forex_carry_funding.html.j2" %}')
    assert source.index('{% include "_forex_carry_funding.html.j2" %}') < source.index("§4 — The pairs")


def test_forex_builder_does_not_import_macro_context_as_a_second_basis_admission_owner():
    source = (ROOT / "scripts" / "build_forex.py").read_text()
    assert "build_macro_context" not in source
    assert "_direct_usd_xccy_basis" not in source
    # No receipt is supplied today because no admitted direct-basis producer exists.
    # The default remains honestly unavailable until an owner-native caller provides one.
    assert "direct_basis_receipt=" not in source


def test_builder_exposes_same_projection_to_page_and_machine_snapshot_without_recomputing_contagion():
    source = (ROOT / "scripts" / "build_forex.py").read_text()
    assert source.count("project_carry_funding(") == 1
    assert source.count("collect_funding_context(") == 1
    assert "carry_funding_view=carry_funding_view" in source
    assert '"carry_funding": carry_funding_view' in source
    assert "contagion.two_tier_read" not in source
    assert "from engine import forex_regime, contagion" not in source
    assert 'config.data_dir() / "intl_risk" / "latest.json"' in source
    assert 'config.data_dir() / "regime" / "latest.json"' in source


def test_component_uses_existing_tokens_and_has_no_hardcoded_colors():
    html = (TEMPLATES / "_forex_carry_funding.html.j2").read_text()
    assert ":root" not in html
    assert "color-mix(" not in html
    import re
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", html)
    assert "var(--" in html
    assert "prefers-reduced-motion" in html
    assert "max-width:900px" in html and "max-width:640px" in html


def test_full_forex_route_uses_the_same_carry_funding_projection_in_html_and_json(tmp_path, monkeypatch):
    import importlib.util
    from bs4 import BeautifulSoup
    from engine.i18n import tr, td

    fixture_path = ROOT / "tests" / "test_forex_context_bus.py"
    spec = importlib.util.spec_from_file_location("r19_forex_context_fixture", fixture_path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    snapshot, contexts = fixture._r12_build_fixture(tmp_path, monkeypatch, fixture._r13_clock_table())
    context = contexts[0]
    assert context["carry_funding_view"] == snapshot["carry_funding"]
    # Complete only the older bounded fixture fields required by the real template.
    for section in context["sections"]:
        for pair in section["pairs"]:
            for factor in pair["conviction"]["factors"]:
                factor["value"] = 0.4
    from scripts import build_forex as BF
    context["dollar"] = BF.dollar_vm(fixture._dol_frame())
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    env.globals.update(tr=tr, td=td)
    html = env.get_template("forex.html.j2").render(**context)
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.select("#fx-carry-funding-evidence")) == 1
    evidence = soup.select_one("#fx-carry-funding-evidence")
    assert "Carry & funding evidence" in evidence.get_text(" ", strip=True)
    assert "Direct USD cross-currency basis" in evidence.get_text(" ", strip=True)
    assert evidence.select_one("script") is None
    assert snapshot["regime_radar"]["active"] == []


def test_carry_funding_component_survives_real_page_writer_and_css_extraction(tmp_path, monkeypatch):
    import hashlib
    from bs4 import BeautifulSoup
    from lib import pages
    from scripts.externalize_css import externalize

    partial = _render(_mod().project_carry_funding(_pairs(), _regime(), _funding()))
    html = '<!doctype html><html><head><meta charset="utf-8"><title>FX carry funding</title></head><body>' + partial + '</body></html>'
    site = tmp_path / "site"
    site.mkdir()
    monkeypatch.setattr(pages, "_site_root", lambda: site)
    monkeypatch.setattr(pages, "_shim_checked", False)
    output = site / "forex.html"
    pages.write_page(output, html, encoding="utf-8")
    externalize(site)
    first = output.read_bytes()
    soup = BeautifulSoup(output.read_text(), "html.parser")
    component = soup.select_one("#fx-carry-funding-evidence")
    assert component is not None
    assert component.select_one("script") is None
    css_matches = []
    for link in soup.select('link[rel="stylesheet"][href^="assets/css/"]'):
        rel = link["href"].split("?")[0]
        raw = (site / rel).read_bytes()
        if b".fx-cf" in raw:
            css_matches.append(raw)
            assert hashlib.sha256(raw).hexdigest()[:8] == Path(rel).stem
    assert len(css_matches) == 1
    externalize(site)
    assert output.read_bytes() == first


def test_actual_builder_reads_published_funding_artifacts_without_engine_recompute(tmp_path, monkeypatch):
    import importlib.util

    fixture_path = ROOT / "tests" / "test_forex_context_bus.py"
    spec = importlib.util.spec_from_file_location("r19_funding_builder_fixture", fixture_path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)

    data = tmp_path / "data"
    (data / "intl_risk").mkdir(parents=True)
    (data / "regime").mkdir(parents=True)
    (data / "intl_risk" / "latest.json").write_text(json.dumps({
        "built": "2026-09-27T08:06:33+00:00",
        "two_tier": {"tier2": {"legs": {"sofr_iorb_corridor": {
            "value": -0.02,
            "last5_all_positive": False,
            "hot": False,
            "threshold": "SOFR-IORB > 0 for 5 consecutive days",
            "caveat": "Quarter-end spikes can be technical.",
        }}}},
    }))
    (data / "regime" / "latest.json").write_text(json.dumps({
        "asof": "2026-09-29",
        "conditions": {"systemic_stress": {
            "a2p2_spread_bps": 16,
            "cp_bill_spread_bps": 0,
            "cp_stress": "normal",
        }},
    }))

    snapshot, contexts = fixture._r12_build_fixture(
        tmp_path, monkeypatch, fixture._r13_clock_table()
    )
    funding = snapshot["carry_funding"]["funding"]
    assert funding["sofr_iorb"]["value_bp"] == -2.0
    assert funding["sofr_iorb"]["artifact_built"] == "2026-09-27T08:06:33+00:00"
    assert funding["a2p2_spread"]["value_bp"] == 16.0
    assert funding["a2p2_spread"]["artifact_as_of"] == "2026-09-29"
    assert funding["cp_bill_spread"]["value_bp"] == 0.0
    assert funding["cp_bill_spread"]["stress_state"] == "normal"
    assert funding["direct_usd_xccy_basis"]["status"] == "unavailable"
    assert contexts[0]["carry_funding_view"] == snapshot["carry_funding"]


def test_inconsistent_canonical_fired_leg_count_withholds_scenario_state():
    regime = _regime(active=False, n_fired=2, min_legs=3)
    # Fixture emits exactly one fired leg; a claimed count of two is internally inconsistent.
    got = _mod().project_carry_funding(_pairs(), regime, _funding())["carry_unwind"]
    assert got["state"] == "unknown"
    assert got["active"] is None


def test_invalid_legacy_uncertainty_geometry_does_not_invalidate_descriptive_frequency():
    regime = _regime()
    prob = regime["scenarios"][0]["prob"]
    prob["p_cond"] = 0.90
    prob["wilson_lo"] = 0.10
    prob["wilson_hi"] = 0.20
    prob["n_raw"] = 10
    prob["n_eff"] = 12.0
    got = _mod().project_carry_funding(_pairs(), regime, _funding())["carry_unwind"]["historical_receipt"]
    assert got["status"] == "ok"
    assert got["headline_frequency"] == 0.90
    assert "wilson" not in got and "n_eff" not in got
    assert got["uncertainty"]["status"] == "withheld_unqualified"


def test_existing_code_job_owns_carry_suite_and_published_artifact_producers():
    import yaml

    manifest = yaml.safe_load((ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text())
    job = manifest["jobs"]["data-base-shim"]
    commands = "\n".join(
        step.get("run", "") for step in job.get("steps", []) if isinstance(step, dict)
    )
    assert job.get("gate") == "code"
    assert "tests/test_forex_carry_funding_view.py" in commands
    paths = set(job.get("paths") or [])
    assert {
        "tests/test_forex_carry_funding_view.py",
        "lib/forex_carry_funding_view.py",
        "scripts/build_forex.py",
        "templates/forex.html.j2",
        "templates/_forex_carry_funding.html.j2",
        "scripts/build_intl.py",
        "engine/contagion.py",
        "engine/conditions.py",
    } <= paths


@pytest.mark.parametrize("bad", [0, 1, -1, 123456789, 0.0, 1.5])
def test_date_helper_rejects_numeric_epoch_coercion(bad):
    assert _mod()._date(bad) is None


def test_latest_point_numeric_index_is_invalid_not_epoch_date():
    frame = pd.DataFrame({"value": [1.5]}, index=[123456789])
    got = _mod()._latest_point(frame, "fixture")
    assert got["status"] == "invalid"
    assert got["value"] is None
    assert got["calculated_through"] is None


@pytest.mark.parametrize("good, expected", [
    ("2026-09-29", "2026-09-29"),
    (pd.Timestamp("2026-09-29"), "2026-09-29"),
])
def test_date_helper_preserves_actual_date_like_inputs(good, expected):
    assert _mod()._date(good) == expected


def test_numeric_regime_asof_never_becomes_1970_artifact_date():
    regime = {
        "asof": 123456789,
        "conditions": {"systemic_stress": {
            "a2p2_spread_bps": 16,
            "cp_bill_spread_bps": 0,
            "cp_stress": "normal",
        }},
    }
    got = _mod().collect_funding_context(lambda *_: None, {}, regime)
    assert got["a2p2_spread"]["artifact_as_of"] is None
    assert got["cp_bill_spread"]["artifact_as_of"] is None
