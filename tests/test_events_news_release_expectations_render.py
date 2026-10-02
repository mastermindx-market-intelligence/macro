"""Render contract for release model/benchmark context; no parent integration."""
from pathlib import Path

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from engine import events_news_release_evidence as view
from test_events_news_release_expectations import (
    ASOF,
    cpi_event,
    forecast_payload,
    official_pce,
    pce_event,
    scored_pce,
)

ROOT = Path(__file__).resolve().parents[1]


def render_event(event):
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    return env.get_template("_macro_events_news.html.j2").render(
        alerts=[],
        macro_news={"headlines": []},
        macro_catalysts=[event],
        latest=None,
        generated_utc=ASOF,
    )


def soup_for(event):
    return BeautifulSoup(render_event(event), "html.parser")


def test_future_model_context_is_secondary_and_street_survey_gap_is_explicit():
    event = cpi_event()
    event["expectation_context"] = view.event_expectation_context(
        event, forecast_payload(), as_of=ASOF)
    s = soup_for(event)
    panel = s.select_one(".nd-expectation-context")
    assert panel
    text = panel.get_text(" ", strip=True)
    assert "Expectations & benchmarks" in text
    assert "Street survey" in text and "Not connected" in text
    assert "Mastermind blended benchmark" in text
    assert text.count("Mastermind model benchmark") == 1
    assert "0.48%" in text and "0.27%" in text
    assert "Cleveland benchmark" in text
    assert "Market-implied median" in text
    assert "consensus" not in text.lower()
    assert len(panel.select("[data-nd-deep]")) == 2



def test_release_anatomy_renders_quirk_source_and_policy_without_directional_copy():
    payload = forecast_payload()
    policy = {
        "fed_stance": "hawkish",
        "gap_bp": 7,
        "implied_cuts_12m": -4.0,
        "next_fomc": "2026-10-28",
        "guidance_direction": "on_hold",
    }
    flag = {
        "code": "cpi_health_insurance_reset",
        "en": "CPI health-insurance retained-earnings update",
        "zh": "CPI医疗保险留存收益更新",
        "cite": "https://www.bls.gov/opub/mlr/2023/article/incorporating-new-estimates-into-the-cpi.htm",
    }
    for row in payload["upcoming"]:
        row["policy_backdrop"] = dict(policy)
        row["regime_axis"] = "inflation"
        row["quirk_flags"] = [dict(flag)]
    event = cpi_event()
    event["expectation_context"] = view.event_expectation_context(
        event, payload, as_of=ASOF)
    s = soup_for(event)
    anatomy = s.select_one(".nd-release-anatomy")
    assert anatomy
    text = anatomy.get_text(" ", strip=True)
    assert "What could complicate this print?" in text
    assert flag["en"] in text
    assert "Fed stance" in text and "Hawkish" in text
    assert "Market vs dots" in text and "+7 bp" in text
    assert "Implied cuts" in text and "-4.0" in text
    assert "Next FOMC" in text and "2026-10-28" in text
    assert "Guidance" in text and "On hold" in text
    assert "Primary axis" in text and "Inflation" in text
    assert "do not predict the direction" in text
    link = anatomy.select_one(".nd-quirk-card a")
    assert link and link["href"].startswith("https://www.bls.gov/")
    assert link["target"] == "_blank"
    assert set(link["rel"]) == {"noopener", "noreferrer"}


def test_release_anatomy_conflicting_policy_is_withheld_in_render():
    payload = forecast_payload()
    payload["upcoming"][0]["policy_backdrop"] = {"fed_stance": "hawkish"}
    payload["upcoming"][1]["policy_backdrop"] = {"fed_stance": "dovish"}
    event = cpi_event()
    event["expectation_context"] = view.event_expectation_context(
        event, payload, as_of=ASOF)
    s = soup_for(event)
    text = s.select_one(".nd-release-anatomy").get_text(" ", strip=True)
    assert "Policy backdrop is withheld because the matched release measures disagree." in text
    assert "Hawkish" not in text and "Dovish" not in text


def test_cold_start_and_accuracy_limits_are_visible_but_not_first_read_noise():
    event = cpi_event()
    event["expectation_context"] = view.event_expectation_context(
        event, forecast_payload(), as_of=ASOF)
    s = soup_for(event)
    panel = s.select_one(".nd-expectation-context")
    assert panel and not panel.has_attr("open")
    assert "Cold-start blend" in panel.get_text(" ", strip=True)
    method = panel.select_one(".nd-expectation-method")
    assert method and not method.has_attr("open")
    assert "Accuracy claim" in method.get_text(" ", strip=True)
    assert "Withheld pending clean aligned forward evidence" in method.get_text(" ", strip=True)


def test_historical_model_comparison_uses_bound_official_result_without_beat_miss_copy():
    payload = forecast_payload()
    payload["upcoming"] = []
    payload["last_scored_all_forward"] = scored_pce(True)
    event = pce_event()
    event["official_evidence"] = official_pce()
    event["expectation_context"] = view.event_expectation_context(
        event, payload, as_of=ASOF, official_evidence=event["official_evidence"])
    s = soup_for(event)
    panel = s.select_one(".nd-expectation-context")
    text = panel.get_text(" ", strip=True)
    assert "Frozen model benchmark" in text
    assert "Difference vs model benchmark" in text
    assert "-0.01 pp" in text
    assert "beat" not in text.lower()
    assert "miss" not in text.lower()
    assert "surprise" not in text.lower()


def test_ineligible_scored_row_explains_withholding_and_hides_model_number():
    payload = forecast_payload()
    payload["upcoming"] = []
    payload["last_scored_all_forward"] = scored_pce(False)
    event = pce_event()
    event["official_evidence"] = official_pce()
    event["expectation_context"] = view.event_expectation_context(
        event, payload, as_of=ASOF, official_evidence=event["official_evidence"])
    s = soup_for(event)
    panel = s.select_one(".nd-expectation-context")
    text = panel.get_text(" ", strip=True)
    assert "excluded from evaluation" in text
    assert "DN-004" in text
    assert not panel.select(".nd-model-value")


def test_reference_change_after_projection_withholds_stale_expectation_context():
    event = cpi_event()
    event["expectation_context"] = view.event_expectation_context(
        event, forecast_payload(), as_of=ASOF)
    event["reference_period"] = "2026-08"
    s = soup_for(event)
    panel = s.select_one(".nd-expectation-context")
    assert panel
    assert not panel.select(".nd-model-value")
    assert "does not match this event or snapshot" in panel.get_text(" ", strip=True)


def test_expectation_context_autoescapes_owner_fields():
    payload = forecast_payload()
    payload["upcoming"][0]["basis_warning"] = '<img src=x onerror="window.injected=1">'
    event = cpi_event()
    event["expectation_context"] = view.event_expectation_context(
        event, payload, as_of=ASOF)
    s = soup_for(event)
    panel = s.select_one(".nd-expectation-context")
    assert not panel.select("img")
    assert "onerror" not in panel.get_text()
    assert "use different inputs" in panel.get_text(" ", strip=True)


def test_expectation_styles_and_behavior_are_mirrored_to_site_assets():
    template_css = (ROOT / "templates" / "macro-events-news.css").read_text()
    site_css = (ROOT / "site" / "macro-events-news.css").read_text()
    template_js = (ROOT / "templates" / "macro-events-news.js").read_text()
    site_js = (ROOT / "site" / "macro-events-news.js").read_text()
    assert template_css == site_css
    assert template_js == site_js
    assert "data-nd-deep" in template_js
    assert ".nd-expectation-context" in template_css


def test_stale_forecast_context_explains_withholding_and_hides_numbers():
    payload = forecast_payload()
    payload["asof"] = "2026-09-28T20:21:25Z"
    event = cpi_event()
    event["expectation_context"] = view.event_expectation_context(
        event, payload, as_of=ASOF)
    s = soup_for(event)
    panel = s.select_one(".nd-expectation-context")
    text = panel.get_text(" ", strip=True)
    assert "Release Radar context is stale" in text
    assert not panel.select(".nd-model-value")
    assert "0.48%" not in text


def test_payroll_benchmark_units_are_readable_and_unqualified_market_count_is_hidden():
    payload = forecast_payload()
    payload["upcoming"] = [{
        "release": "nfp",
        "release_type": "nfp",
        "period": "2026-09",
        "release_date": "2026-10-02",
        "projection": {"point": 100.0, "p10": 50.0, "p90": 150.0},
        "benchmark_set": {
            "naive_prior": 217.0,
            "trailing_3m": 122.0,
            "market_implied": {"source": "kalshi", "implied_median": 97000.0, "asof": "2026-10-01"},
        },
        "model_epoch": "champion_legacy_target_v1",
        "target_epoch": "legacy_cross_vintage_initial_levels_v0",
        "cutoff_label": "T-1",
    }]
    event = {"type": "NFP", "date": "2026-10-02", "reference_period": "2026-09"}
    event["expectation_context"] = view.event_expectation_context(event, payload, as_of=ASOF)
    s = soup_for(event)
    panel = s.select_one(".nd-expectation-context")
    text = panel.get_text(" ", strip=True)
    assert "100k" in text
    assert "217k" in text
    assert "122k" in text
    assert "97000" not in text
    assert "unit basis" in text


def test_benchmark_only_context_remains_useful_when_model_point_is_absent():
    payload = forecast_payload()
    payload["upcoming"] = [{
        "release": "nfp",
        "release_type": "nfp",
        "period": "2026-09",
        "release_date": "2026-10-02",
        "projection": {"point": None},
        "benchmark_set": {"naive_prior": 217.0, "trailing_3m": 122.0},
        "model_epoch": "champion_legacy_target_v1",
        "target_epoch": "legacy_cross_vintage_initial_levels_v0",
        "cutoff_label": "T-1",
    }]
    event = {"type": "NFP", "date": "2026-10-02", "reference_period": "2026-09"}
    event["expectation_context"] = view.event_expectation_context(event, payload, as_of=ASOF)
    s = soup_for(event)
    panel = s.select_one(".nd-expectation-context")
    text = panel.get_text(" ", strip=True)
    assert "Benchmarks only" in text
    assert "No model point is presented" in text
    assert "217k" in text and "122k" in text
    assert not panel.select(".nd-model-value")
