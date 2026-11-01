from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


ROOT = Path(__file__).resolve().parents[1]
MACRO = """{% macro t(en, zh) -%}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{%- endmacro %}"""


def render(**kwargs):
    env = Environment(loader=FileSystemLoader(ROOT / "templates"),
                      autoescape=True, undefined=StrictUndefined)
    return env.from_string(MACRO + '{% include "_petroleum_flow_context.html.j2" %}').render(**kwargs)


def context(state="stale"):
    return {
        "state": state, "common_period": "2026-10-02", "evaluated_on": "2026-10-20",
        "age_days": 18,
        "values": {"crude_production": 13979, "refinery_inputs": 16480,
                   "gasoline_supplied": 8769, "distillate_supplied": 3650},
    }


def test_stale_values_are_historical_with_separate_period_and_evaluation():
    html = render(petroleum_flow=context())
    assert 'datetime="2026-10-02"' in html and 'datetime="2026-10-20"' in html
    assert "Stale · historical context" in html and "已过时 · 历史背景" in html
    assert "18" in html and "after 9 days" in html
    assert all(v in html for v in ["13,979", "16,480", "8,769", "3,650"])
    assert "Thousand barrels per day" in html and "千桶/日" in html


def test_three_stages_do_not_imply_barrel_tracking_or_balanced_conversion():
    html = render(petroleum_flow=context())
    assert html.count('class="cm-row"') == 3
    assert "not traced movements of the same barrels" in html
    assert "Includes imported crude" in html
    assert "not the entire output" in html
    assert "not a reconciled mass balance" in html
    assert "approximate" in html and "近似消费量" in html


def test_missing_or_legacy_context_is_unknown_without_fake_value_or_period():
    for html in [render(), render(petroleum_flow={"state": "unavailable"})]:
        assert "unknown, not zero" in html and "缺失覆盖意味着未知" in html
        assert 'class="cm-row"' not in html and "<time " not in html
        assert "13,979" not in html and "0.0" not in html


def test_available_zero_is_kept_without_stale_claim():
    data = context("available")
    data.update(common_period="2026-10-16", age_days=4)
    data["values"]["gasoline_supplied"] = 0
    html = render(petroleum_flow=data)
    assert "<strong>0</strong>" in html
    assert "Stale · historical context" not in html
    assert "US crude field production" in html


def test_each_quantity_links_native_source_and_discloses_unknown_clocks():
    html = render(petroleum_flow=context())
    for code in ["WCRFPUS2", "WCRRIUS2", "WGFUPUS2", "WDIUPUS2"]:
        assert f"s={code}&amp;f=W" in html
    assert "<details" in html and "<summary>" in html
    assert "publication, retrieval and first-known times are not retained" in html
    assert "past values may be revised" in html
    assert "Weeks are not mixed or forward-filled" in html
