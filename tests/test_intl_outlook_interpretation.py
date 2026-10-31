"""Falsifiers for economic claims, source attribution and dependent conditions."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from collectors.intl_policy_sources import RELEASES, parse_registered_policy_release
from lib.intl_country_assessment import build_country_assessments, _world_brief
from lib.intl_country_outlook import build_country_outlook
from lib.intl_forecast_vintages import merge_publications
from lib.intl_policy_evidence import select_policy_decision

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 19)
NOW = "2026-10-19T00:00:00+00:00"


def baseline():
    return json.loads((ROOT / "config/intl_country_baseline.json").read_text())


def research():
    return json.loads((ROOT / "config/intl_country_commentary.json").read_text())["countries"]


def assessment(*, commentary=None, decisions=None):
    data = baseline()
    return build_country_assessments(
        {"date": TODAY.isoformat(), "records": [{"cc": cc} for cc in ("GB", "TW", "IN")]},
        today=TODAY, forecast_archive=data["forecast_archive"],
        policy_decisions=data["policy_decisions"] if decisions is None else decisions,
        commentary=research() if commentary is None else commentary,
    )


def test_original_world_mechanism_is_bound_to_the_reviewed_record():
    world = _world_brief([], baseline()["forecast_archive"], TODAY)
    assert "strengthen" in world["title_en"] and world["next"] == 3.4
    assert "AI investment" in world["mechanism_en"]


@pytest.mark.parametrize("values,word", [
    ({"2026": 3.1, "2027": 2.2}, "slow"),
    ({"2026": 3.1, "2027": -0.4}, "contract"),
    ({"2026": 3.1}, "published"),
])
def test_corrected_world_path_cannot_inherit_a_recovery_headline_or_narrative(values, word):
    original = next(r for r in baseline()["forecast_archive"] if r["cc"] == "WORLD")
    correction = {**deepcopy(original), "values": values, "correction_sequence": 1,
                  "supersedes_record_id": original["record_id"],
                  "correction_source_url": "https://www.imf.org/en/correction"}
    archive, diagnostics = merge_publications([original], [correction], observed_at=NOW)
    world = _world_brief([], archive, TODAY)
    assert word in world["title_en"]
    assert world["mechanism_en"] is None
    assert world["record_id"] != original["record_id"]


def test_national_thesis_leads_and_conditions_follow_its_evidence_identity():
    countries = {c["cc"]: c for c in assessment()["countries"]}
    gb = countries["GB"]
    assert gb["title_en"] == research()["GB"]["title"][0]
    assert gb["forecast"]["current"] == 1.3
    assert gb["thesis"]["classification"] == "source_attributed_assessment"
    assert all(c["proposition_id"] == gb["thesis"]["id"] and
               c["dependencies"] == gb["thesis"]["dependencies"] for c in gb["conditions"])
    assert gb["policy_decision"]["record_id"] in gb["thesis"]["dependencies"]
    assert gb["outlook"]["policy_en"] is None
    assert any(p["id"] == "GB:national_policy" for p in gb["outlook"]["propositions"])
    assert not any(p["id"] == "GB:policy_tradeoff" for p in gb["outlook"]["propositions"])


def test_revised_reviewed_mechanism_requalifies_its_conditions():
    old = next(c for c in assessment()["countries"] if c["cc"] == "GB")
    changed = research()
    changed["GB"]["upside"][0] = "A revised, separately reviewed condition."
    new = next(c for c in assessment(commentary=changed)["countries"] if c["cc"] == "GB")
    assert new["conditions"][0]["dependencies"] != old["conditions"][0]["dependencies"]
    assert new["conditions"][0]["text_en"] == changed["GB"]["upside"][0]


def test_conflicting_national_rationale_withholds_its_dependent_thesis():
    decisions = baseline()["policy_decisions"]
    prior = next(r for r in decisions if r["cc"] == "GB")
    decisions.append({**deepcopy(prior), "rationale_en": "A materially different rationale."})
    assert select_policy_decision(decisions, "GB", today=TODAY)["state"] == "conflict"
    gb = next(c for c in assessment(decisions=decisions)["countries"] if c["cc"] == "GB")
    assert gb["research"] is None and gb["thesis"]["id"] != "GB:national_thesis"
    assert all(prior["record_id"] not in c["dependencies"] for c in gb["conditions"])


def test_stale_national_thesis_is_not_kept_by_a_new_page_build():
    stale = research()
    stale["GB"]["published"] = "2026-01-01"
    gb = next(c for c in assessment(commentary=stale)["countries"] if c["cc"] == "GB")
    assert gb["research"] is None
    assert gb["title_en"] != stale["GB"]["title"][0]
    assert gb["thesis"]["classification"] == "published_projection"


def test_fiscal_ratio_does_not_infer_a_nominal_borrowing_amount():
    jp = build_country_outlook("JP", baseline()["forecast_archive"], today=TODAY)
    balance = next(b for b in jp["balances"] if b["series_id"] == "fiscal_balance")
    assert balance["reading_en"] == "The projected deficit widens as a share of GDP."


def test_cbc_parser_separates_annual_growth_and_headline_inflation():
    # Minimal contract fixture. This does not claim a successful CBC HTML download.
    html = b"""<h1>Monetary Policy Decision of the Board Meeting (2026 Q3)</h1>
    <p>Release Date: September 17, 2026</p>
    <p>The discount rate, the rate on refinancing of secured loans, and the rate on temporary accommodations unchanged at 2%, 2.375%, and 4.25%.</p>
    <p>First-half growth was 14.15% and second-half growth 9.09%; 11.48% for the year as a whole.</p>
    <p>A higher base effect would lead the economic growth rate to register 5.82% next year.</p>
    <p>The forecasts for Taiwan's CPI and core CPI inflation rates to 2.03% and 2.16%.</p>
    <p>Next year the CPI and core CPI inflation rates will slow to 1.83% and 1.89%.</p>"""
    parsed = parse_registered_policy_release(html, RELEASES[1], retrieved_at=NOW)
    views = {r["series_id"]: r["values"] for r in parsed["forecast_archive"]}
    assert views["real_gdp_growth"] == {"2026": 11.48, "2027": 5.82}
    assert views["inflation_average"] == {"2026": 2.03, "2027": 1.83}
    assert parsed["policy_decisions"][0]["instrument"] == "discount_rate"
    with pytest.raises(ValueError, match="missing_or_ambiguous"):
        parse_registered_policy_release(html + b"<p>12.5% for the year as a whole</p>", RELEASES[1], retrieved_at=NOW)


@pytest.mark.parametrize("cc", ["GB", "TW"])
def test_conflict_at_another_official_url_invalidates_the_same_country_bank_thesis(cc):
    decisions = baseline()["policy_decisions"]
    prior = next(r for r in decisions if r["cc"] == cc)
    alternate = {**deepcopy(prior),
                 "source_url": prior["source_url"] + "?version=alternative",
                 "rationale_en": "A materially conflicting rationale at another official URL."}
    decisions.append(alternate)
    selected = select_policy_decision(decisions, cc, today=TODAY)
    assert selected["state"] == "conflict"
    commentary = research()
    # Either version may be the representative. Bind commentary to the other
    # official URL so the test cannot pass through an incidental URL match.
    commentary[cc]["source_url"] = next(
        r["source_url"] for r in (prior, alternate)
        if r["source_url"] != selected["source_url"]
    )
    country = next(c for c in assessment(commentary=commentary, decisions=decisions)["countries"]
                   if c["cc"] == cc)
    assert country["research"] is None
    assert country["thesis"]["id"] != cc + ":national_thesis"
    assert all(not any(d.startswith("research:") for d in condition["dependencies"])
               for condition in country["conditions"])


def test_rising_inflation_does_not_presuppose_a_restrictive_policy_stance():
    jp = build_country_outlook("JP", baseline()["forecast_archive"], today=TODAY)
    assert jp["policy_en"] == (
        "Persistent domestic inflation could constrain scope for easing, even if growth slows."
    )
    assert "保持限制性" not in jp["policy_zh"]
