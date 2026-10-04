"""F07 event -> AssumptionChange proposal contract.

Spec: research/F07_EVENT_ASSUMPTION_PROPOSAL_CONTRACT_V1.md

These tests pin the invariants that keep an event from laundering a number it is
not entitled to. Fixture-based on purpose: they run in a sparse checkout.
"""
from __future__ import annotations

import pytest

from engine import valuation_event_proposal as vep
from engine.valuation_scenario import SCENARIOS

# Real AAPL FY2025 base (SEC companyfacts), so the fixture cannot drift into a
# shape the product never produces.
BASE_PERIOD_END = "2025-09-27"


def controls(period_end=BASE_PERIOD_END, ticker="AAPL"):
    return {
        "schema": "valuation_scenario_controls.v1",
        "ticker": ticker,
        "period_end": period_end,
        "inputs": {
            "net_income": 112010000000.0,
            "revenue": 416161000000.0,
            "shares": 14773260000.0,
            "net_margin_base": 0.2691506412181824,
        },
        "server_default": {
            "sales_growth_pct": 3,
            "margin_delta_pp": 0,
            "earnings_multiple": 18,
            "per_share": 140.57,
        },
    }


def guidance_hit(direction="raise", file_date="2026-07-30", phrase="raising our full-year guidance"):
    return {
        "id": "0001755672-26-000022:a2q_2026xearningsxnewsxr.htm",
        "ticker": "CTVA",
        "cik": "0001755672",
        "form": "8-K",
        "file_date": file_date,
        "phrase": phrase,
        "direction": direction,
    }


def earnings_event(ts="2026-07-30T00:00:00Z", facts=("Jun 2026 · EPS 1.57 · est 1.42 · surprise +10.6%",)):
    return {
        "id": "cev-earnings-22f8605d10db",
        "kind": "earnings",
        "tickers": ["AAPL"],
        "ts": ts,
        "title": "Earnings: AAPL actual vs est",
        "facts": list(facts),
        "links": {"receipt": None, "site": None, "source": None},
        "source_ref": "AAPL#2026-07-30",
    }


PRESET_VALUES = {
    "sales_growth_pct": {row[1] for row in SCENARIOS},
    "margin_delta_pp": {row[2] for row in SCENARIOS},
    "earnings_multiple": {row[3] for row in SCENARIOS},
}


# --- Invariant 1: no number that the model has not already published --------

def test_proposed_value_is_always_a_published_preset_value():
    p = vep.propose_from_guidance_hit(guidance_hit(), controls())
    assert p["status"] == vep.STATUS_PROPOSED
    assert p["magnitude_source"] == vep.MAGNITUDE_SOURCE_MODEL_PRESET
    assert p["proposed_value"] in PRESET_VALUES[p["assumption_name"]]


def test_magnitude_never_comes_from_the_event_even_when_the_phrase_has_a_number():
    """A filing that states a figure still does not get to set the input."""
    hit = guidance_hit(phrase="raising our full-year guidance to $8.40 per share, up 22%")
    p = vep.propose_from_guidance_hit(hit, controls())
    assert p["magnitude_source"] == vep.MAGNITUDE_SOURCE_MODEL_PRESET
    assert p["proposed_value"] in PRESET_VALUES["sales_growth_pct"]
    # the event's own numbers appear nowhere as an input value
    assert p["proposed_value"] not in (8.40, 22)


@pytest.mark.parametrize("direction,expected_preset", [("raise", "upbeat"), ("cut", "cautious")])
def test_direction_selects_the_models_own_adjacent_scenario(direction, expected_preset):
    p = vep.propose_from_guidance_hit(guidance_hit(direction=direction), controls())
    want = vep._preset_value(expected_preset, "sales_growth_pct")
    assert p["proposed_value"] == want


# --- Invariant 2: an abstention never carries a number ----------------------

def test_insufficient_never_carries_a_number_or_a_method():
    p = vep.propose_from_chronicle_event(earnings_event(), controls())
    assert p["status"] == vep.STATUS_INSUFFICIENT
    assert p["proposed_value"] is None
    assert p["magnitude_source"] is None
    assert p["mapping_method"] == vep.MAP_NONE
    assert p["abstain_reason"] is not None


def test_no_event_is_a_typed_abstention_not_a_blank():
    p = vep.propose_from_chronicle_event(None, controls())
    assert p["status"] == vep.STATUS_INSUFFICIENT
    assert p["abstain_reason"] == vep.R_NO_EVENT
    assert p["rationale_en"]


# --- Invariant 3: a reported result is a fact, never an assumption ----------

def test_reported_result_always_abstains_even_with_a_clean_payload_and_source():
    ev = earnings_event(facts=("Jun 2026 · revenue 94.0B",))
    ev["links"] = {"source": "https://www.sec.gov/Archives/edgar/data/320193/x.htm"}
    p = vep.propose_from_chronicle_event(ev, controls())
    assert p["status"] == vep.STATUS_INSUFFICIENT
    assert vep.R_REPORTED_RESULT_NOT_AN_ASSUMPTION in p["abstain_reasons"]


# --- Invariant 4: never applied --------------------------------------------

def test_evaluate_is_shadow_only_and_never_applies():
    cb = controls()
    p = vep.propose_from_guidance_hit(guidance_hit(), cb)
    out = vep.evaluate_proposal(cb, p)
    assert out["applied"] is False
    assert out["baseline"]["per_share"] == cb["server_default"]["per_share"]
    # the controls blob itself is untouched
    assert cb["server_default"]["sales_growth_pct"] == 3


def test_evaluate_changes_exactly_one_assumption_and_names_the_rest():
    cb = controls()
    p = vep.propose_from_guidance_hit(guidance_hit(), cb)
    out = vep.evaluate_proposal(cb, p)
    assert out["changed_assumptions"] == ["sales_growth_pct"]
    assert out["unchanged_assumptions"] == ["earnings_multiple", "margin_delta_pp"]
    assert out["proposed"]["per_share"] > out["baseline"]["per_share"]


def test_evaluate_carries_a_refusal_through_instead_of_a_zero():
    cb = controls()
    p = vep.propose_from_chronicle_event(earnings_event(), cb)
    out = vep.evaluate_proposal(cb, p)
    assert out["refused"] is True
    assert out["proposed"] is None
    assert out["per_share_delta"] is None
    assert out["abstain_reason"] == p["abstain_reason"]


# --- Invariant 5: consensus cannot enter, whatever the event is labelled ----

@pytest.mark.parametrize("payload", [
    "Jun 2026 · EPS 1.57 · est 1.42 · surprise +10.6%",
    "analyst consensus raised to 2.10",
    "price target lifted to 320",
    "whisper number 1.90",
])
def test_consensus_payload_is_refused_on_rights(payload):
    assert vep.carries_unlicensed_payload({"facts": [payload]}) is True


def test_a_guidance_hit_carrying_a_consensus_phrase_abstains_on_rights():
    hit = guidance_hit(phrase="raising guidance above consensus")
    p = vep.propose_from_guidance_hit(hit, controls())
    assert p["status"] == vep.STATUS_INSUFFICIENT
    assert vep.R_PAYLOAD_NOT_LICENSED in p["abstain_reasons"]


# --- Invariant 6: a proposal the user cannot verify is not a proposal -------

def test_proposed_requires_a_resolvable_source_ref():
    p = vep.propose_from_guidance_hit(guidance_hit(), controls())
    assert p["status"] == vep.STATUS_PROPOSED
    assert p["event"]["source_refs"]
    assert p["event"]["source_refs"][0]["url"].startswith("https://www.sec.gov/Archives/")


def test_missing_accession_shape_yields_no_link_and_abstains():
    hit = guidance_hit()
    hit["id"] = "no-colon-id"
    p = vep.propose_from_guidance_hit(hit, controls())
    assert p["event"]["source_refs"] == []
    assert p["status"] == vep.STATUS_INSUFFICIENT
    assert vep.R_NO_SOURCE_REF in p["abstain_reasons"]


def test_edgar_url_is_never_guessed_from_a_bad_shape():
    assert vep._edgar_document_url("0001755672", "nocolon") is None
    assert vep._edgar_document_url("0001755672", "abc-de-fgh:x.htm") is None
    assert vep._edgar_document_url(None, "0001-26-1:x.htm") is None


# --- Double-count / point-in-time law --------------------------------------

def test_event_inside_the_reported_base_abstains_on_double_count():
    """The negative control: the base already absorbed this event."""
    ev = earnings_event(ts="2025-07-31T00:00:00Z")
    p = vep.propose_from_chronicle_event(ev, controls())
    assert p["abstain_reason"] == vep.R_ALREADY_IN_REPORTED_BASE


def test_guidance_inside_the_reported_base_also_abstains():
    hit = guidance_hit(file_date="2025-06-30")
    p = vep.propose_from_guidance_hit(hit, controls())
    assert p["status"] == vep.STATUS_INSUFFICIENT
    assert vep.R_ALREADY_IN_REPORTED_BASE in p["abstain_reasons"]


def test_an_undated_event_cannot_be_point_in_time_checked_and_abstains():
    ev = earnings_event(ts=None)
    ev.pop("ts", None)
    ev.pop("date", None)
    p = vep.propose_from_chronicle_event(ev, controls())
    assert p["status"] == vep.STATUS_INSUFFICIENT


# --- Model/version binding --------------------------------------------------

def test_proposal_and_scenario_both_name_the_model_version():
    cb = controls()
    p = vep.propose_from_guidance_hit(guidance_hit(), cb)
    out = vep.evaluate_proposal(cb, p)
    assert p["model_version"] == vep.MODEL_VERSION
    assert out["model_version"] == vep.MODEL_VERSION
    assert p["base_period_end"] == cb["period_end"]
    assert out["base_period_end"] == cb["period_end"]


def test_tier_is_research_display_only():
    p = vep.propose_from_guidance_hit(guidance_hit(), controls())
    assert p["tier"] == "research_display_only"


# --- Forbidden vocabulary ---------------------------------------------------

FORBIDDEN = ("probability", "confidence", "consensus", "price target", "fair value", "% chance")


def test_no_forbidden_vocabulary_in_user_facing_copy():
    for p in (
        vep.propose_from_guidance_hit(guidance_hit(), controls()),
        vep.propose_from_chronicle_event(earnings_event(), controls()),
        vep.propose_from_chronicle_event(None, controls()),
    ):
        blob = " ".join(
            str(p.get(k) or "") for k in ("rationale_en", "uncertainty", "what_would_change_this", "horizon")
        ).lower()
        for word in FORBIDDEN:
            if word == "consensus":
                continue  # the rights refusal may name what it is refusing
            assert word not in blob, f"{word!r} leaked into user copy"


# --- Selection --------------------------------------------------------------

def test_a_rights_clean_forecast_change_outranks_a_reported_result():
    cb = controls()
    p = vep.best_proposal(cb, chronicle_events=[earnings_event()], guidance_hits=[guidance_hit()])
    assert p["status"] == vep.STATUS_PROPOSED
    assert p["evidence_class"] == vep.EV_MANAGEMENT_FORECAST_CHANGE


def test_with_nothing_lawful_the_panel_still_gets_a_reason():
    cb = controls()
    p = vep.best_proposal(cb, chronicle_events=[earnings_event()], guidance_hits=[])
    assert p["status"] == vep.STATUS_INSUFFICIENT
    assert p["abstain_reason"]


def test_every_abstain_reason_is_a_declared_constant():
    cb = controls()
    for p in (
        vep.propose_from_chronicle_event(earnings_event(), cb),
        vep.propose_from_chronicle_event(None, cb),
        vep.propose_from_guidance_hit(guidance_hit(file_date="2025-01-01"), cb),
    ):
        for reason in p["abstain_reasons"]:
            assert reason in vep._REASON_ORDER


# --- the rights gate must not over-refuse either ----------------------------

@pytest.mark.parametrize("clean", [
    "we plan to invest more in capacity",     # 'invest' contains 'est'
    "our latest results were strong",         # 'latest' contains 'est'
    "the highest margin in our history",      # 'highest' contains 'est'
    "raising our full-year guidance",
    "above the high end",
    "increasing our guidance",
])
def test_lawful_management_language_is_not_refused(clean):
    """A false refusal is as dishonest as a false number."""
    assert vep.carries_unlicensed_payload({"phrase": clean}) is False


@pytest.mark.parametrize("dirty", [
    "ahead of the Street",
    "analyst price target lifted",
    "guidance above consensus",
    "EPS 1.57 · est 1.42",
])
def test_consensus_language_is_still_refused(dirty):
    assert vep.carries_unlicensed_payload({"phrase": dirty}) is True


# --- forward point-in-time: a scheduled event is not yet evidence -----------

def test_event_after_as_of_cannot_propose():
    """A calendar entry for a future date is not evidence of anything yet."""
    p = vep.propose_from_guidance_hit(
        guidance_hit(file_date="2026-12-01"), controls(), as_of="2026-09-22"
    )
    assert p["status"] == vep.STATUS_INSUFFICIENT
    assert vep.R_EVENT_NOT_YET_OBSERVABLE in p["abstain_reasons"]


def test_event_on_the_as_of_day_is_observable():
    p = vep.propose_from_guidance_hit(
        guidance_hit(file_date="2026-09-22"), controls(), as_of="2026-09-22"
    )
    assert p["status"] == vep.STATUS_PROPOSED


def test_without_as_of_behaviour_is_unchanged():
    p = vep.propose_from_guidance_hit(guidance_hit(file_date="2026-12-01"), controls())
    assert p["status"] == vep.STATUS_PROPOSED


# --- stored-proposal binding ------------------------------------------------

def test_a_proposal_from_another_model_version_is_refused():
    cb = controls()
    p = vep.propose_from_guidance_hit(guidance_hit(), cb)
    p["model_version"] = "valuation_scenario.v2"
    out = vep.evaluate_proposal(cb, p)
    assert out["refused"] is True
    assert out["abstain_reason"] == vep.R_MODEL_VERSION_MISMATCH
    assert out["proposed"] is None


def test_a_proposal_against_an_older_base_is_refused_not_silently_replayed():
    """The base advanced; re-applying the old delta would double-count it."""
    old_base = controls(period_end="2025-09-27")
    p = vep.propose_from_guidance_hit(guidance_hit(), old_base)
    assert p["status"] == vep.STATUS_PROPOSED
    newer_base = controls(period_end="2026-09-26")
    out = vep.evaluate_proposal(newer_base, p)
    assert out["refused"] is True
    assert out["abstain_reason"] == vep.R_SUPERSEDED_BY_BASE
    # the historical proposal itself is untouched
    assert p["base_period_end"] == "2025-09-27"
    assert p["status"] == vep.STATUS_PROPOSED


# --- the panel itself -------------------------------------------------------

import pathlib as _pathlib  # noqa: E402
import re  # noqa: E402

import jinja2  # noqa: E402

from engine import i18n  # noqa: E402

ROOT = _pathlib.Path(__file__).resolve().parents[1]


def _render(blob):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = i18n.t
    tmpl = env.from_string("{% include '_valuation_assumptions.html.j2' %}")
    return tmpl.render(valuation_assumptions=blob, deep_ids=[])


def _proposed_blob():
    cb = controls()
    p = vep.propose_from_guidance_hit(guidance_hit(), cb)
    assert p["status"] == vep.STATUS_PROPOSED
    cb["event_assumption_proposal"] = p
    cb["event_assumption_scenario"] = vep.evaluate_proposal(cb, p)
    return cb


def test_panel_never_shows_a_number_without_saying_whose_number_it_is():
    """Vector 8: the figure shown is the MODEL's scenario, not the company's.

    The disclaimer is the whole defence against a reader taking the preset for
    a figure management gave, so it is pinned, not left to copy drift.
    """
    html = _render(_proposed_blob())
    assert 'id="va-event-proposal"' in html
    assert "not a number the company gave" in html
    assert "并非公司给出的数字" in html


def test_panel_shows_the_before_and_after_and_the_untouched_inputs():
    html = _render(_proposed_blob())
    assert "$140.57" in html            # baseline per share, unchanged
    assert "The other two are untouched." in html


def test_panel_links_the_filing_it_quotes():
    html = _render(_proposed_blob())
    assert "https://www.sec.gov/Archives/edgar/data/1755672/" in html
    assert "raising our full-year guidance" in html


def test_panel_copy_carries_no_machine_slugs_or_status_codes():
    """DESIGN_DOCTRINE Law 2: no raw slugs or internal state names on Tier 1."""
    html = _render(_proposed_blob())
    # Scope to the proposal block itself: the panel's pre-existing slider JS
    # legitimately uses the control keys as element ids, and those are code.
    body = re.search(
        r'id="va-event-proposal".*?</div>', html, re.DOTALL
    )
    assert body, "proposal block missing"
    body = body.group(0)
    for slug in (
        "MANAGEMENT_FORECAST_CHANGE", "DIRECTION_TO_MODEL_PRESET", "INSUFFICIENT",
        "PROPOSED", "sales_growth_pct", "model_preset", "assumption_change_proposal",
        "reported_result_not_an_assumption", "payload_not_licensed",
    ):
        assert slug not in body, f"machine slug {slug!r} leaked into panel copy"


def test_panel_carries_no_refutation_language():
    """Falsifier/refutation wording is never front-facing (operator 2026-07-27)."""
    html = _render(_proposed_blob()).lower()
    for word in ("falsifier", "refute", "refuted", "证伪", "thesis", "disproven"):
        assert word not in html, f"refutation language {word!r} is front-facing"


def test_abstaining_panel_renders_no_number_block_at_all():
    cb = controls()
    p = vep.propose_from_chronicle_event(earnings_event(), cb)
    cb["event_assumption_proposal"] = p
    cb["event_assumption_scenario"] = vep.evaluate_proposal(cb, p)
    html = _render(cb)
    assert 'id="va-event-proposal"' not in html
    assert "A reported quarterly result is a fact" in html
