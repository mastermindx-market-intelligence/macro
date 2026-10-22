"""A qualified producer stance must not be contradicted by the macro glance."""
from pathlib import Path

import pytest
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]


def render_fed(artifact):
    source = (ROOT / "templates/dashboard.html.j2").read_text()
    start = source.index('  <div class="sx-v5-static" id="sx-v5-fed">')
    end = source.index("{# /sx-v5-fed #}", start) + len("{# /sx-v5-fed #}")
    return Environment().from_string(source[start:end]).render(
        rates_command=artifact, policy_lever=None, prediction_markets=None
    )


@pytest.fixture
def rates():
    return {
        "expectations_pressure": {
            "state_label": {"en": "Easing pressure building", "zh": "宽松压力上升"},
            "net_state": "repricing_dovish",
        },
        "stance": {
            "en": "The futures rate path isn't shown until it can be matched to the policy rate.",
            "zh": "期货隐含的利率路径须与政策利率口径一致后才会显示。",
        },
        "board": {
            "rate_path_row": {
                "policy_rate": 3.88,
                "basis": {"value_state": "present"},
            }
        },
        "market_check": {
            "futures": {
                "m1": 3.9, "m3": 4.11, "m6": 4.38, "m12": 4.67,
                "plain_read_en": "Market prices ~3 hikes over the next 12m",
                "plain_read_zh": "市场为未来12个月定价约加息3次",
            }
        },
        "qualified_comparisons": [],
    }


@pytest.mark.parametrize("comparisons", [
    [],
    [{"component": "d1", "status": "not_comparable"}],
    [{"component": "d1", "status": "not_identified"}],
    [{"component": "i0", "status": "directly_comparable"}],
])
def test_unqualified_comparison_keeps_pressure_and_caveat_but_no_path(rates, comparisons):
    rates["qualified_comparisons"] = comparisons
    rendered = render_fed(rates)
    assert "Easing pressure building" in rendered
    assert "matched to the policy rate" in rendered
    assert "口径一致后才会显示" in rendered
    assert "Market prices ~3 hikes" not in rendered
    assert "市场为未来12个月定价约加息3次" not in rendered
    assert 'class="plf-spark-svg"' not in rendered


@pytest.mark.parametrize("status", ["directly_comparable", "comparable_after_transformation"])
def test_identified_rate_comparison_preserves_producer_read_and_chart(rates, status):
    rates["qualified_comparisons"] = [{"component": "d1", "status": status}]
    rates["stance"] = {"en": "The matched path implies tightening.", "zh": "同口径路径显示收紧。"}
    rendered = render_fed(rates)
    assert "Market prices ~3 hikes" in rendered
    assert "市场为未来12个月定价约加息3次" in rendered
    assert 'class="plf-spark-svg"' in rendered


@pytest.mark.parametrize("basis", [None, {"value_state": "missing"}])
def test_missing_basis_with_identified_row_still_withholds_comparison(rates, basis):
    rates["qualified_comparisons"] = [{"component": "d1", "status": "directly_comparable"}]
    rates["board"]["rate_path_row"]["basis"] = basis
    rendered = render_fed(rates)
    assert "Market prices ~3 hikes" not in rendered
    assert 'class="plf-spark-svg"' not in rendered


def test_absent_rates_artifact_keeps_honest_pending_state():
    rendered = render_fed(None)
    assert "Forward path data" in rendered
    assert "Market prices" not in rendered


@pytest.mark.parametrize("identified", [False, True])
def test_policy_glance_uses_the_same_qualified_rate_comparison(rates, identified):
    source = (ROOT / "templates/dashboard.html.j2").read_text()
    start = source.index('  <div class="sx-v5-static" id="sx-v5-fed">')
    end = source.index("{# /sx-v5-fed #}", start) + len("{# /sx-v5-fed #}")
    fed = source[start:end]
    start = source.index('  <div class="sx" id="sx-policy-v2"')
    end = source.index("{# /sx-policy-v2 #}", start) + len("{# /sx-policy-v2 #}")
    policy = source[start:end]
    if identified:
        rates["qualified_comparisons"] = [{"component": "d1", "status": "directly_comparable"}]
    latest = {
        "fed_stance": None,
        "fed_path": {
            "implied": {"now": 3.88, "m1": 3.9, "m3": 4.11, "m6": 4.38, "m12": 4.67},
            "headline_en": "Market prices ~3 hikes",
            "headline_zh": "市场定价约加息3次",
        },
    }
    rendered = Environment().from_string(fed + policy).render(
        rates_command=rates,
        policy_lever={"state": "ELEVATED"},
        _pl_state="ELEVATED",
        latest=latest,
        prediction_markets=None,
    )
    policy_result = rendered[rendered.index('id="sx-policy-v2"'):]
    assert ("Market prices ~3 hikes" in policy_result) is identified
    assert ('class="plf-spark-svg"' in policy_result) is identified
    assert ("Rate-path comparison unavailable." in policy_result) is not identified
    assert ("利率路径比较暂不可用。" in policy_result) is not identified
