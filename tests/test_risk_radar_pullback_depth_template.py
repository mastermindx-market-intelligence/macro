"""Paper-derived fragment: consume native observed prices, never mint a forecast."""
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/_risk_radar_pullback_depth.html.j2"


def native_view(market="cn"):
    """Minimal shape of the existing China pullback present()/observe() contract."""
    observation = {
        "schema": "pullback_observation.v1", "market": market,
        "benchmark": "000001.SS" if market == "cn" else "SPY",
        "benchmark_en": "Shanghai Composite" if market == "cn" else "SPY",
        "benchmark_zh": "上证综指" if market == "cn" else "SPY",
        "available": True, "quality": "current", "clock": "settled_close",
        "phase": "underway", "active": True, "asof": "2026-09-30",
        "peak_session": "2026-09-14", "source_digest": "a" * 64,
        "valid_until": "2026-10-01T09:00:00+00:00",
        "close": 93.2, "peak_close": 100.0, "low_close": 92.6,
        "drawdown_pct": -6.8, "loss_recovered_pct": 8.11,
        "observed_closes_since_onset": 12,
    }
    return {"observation": observation, "phase": "underway", "value": "-6.8%",
            "detail_chart_html": '<figure class="ilx" role="img" aria-label="Observed drawdown"><svg></svg></figure>'}


def render(v=None, market="cn"):
    assert TEMPLATE.exists(), "Paper pullback fragment is not implemented"
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
    return env.from_string('{% import "_risk_radar_pullback_depth.html.j2" as p %}{{ p.detail(market, v) }}').render(market=market, v=v)


@pytest.mark.parametrize("market", ["cn", "us"])
def test_native_view_shows_three_distinct_observed_metrics(market):
    html = render(native_view(market), market)
    soup = BeautifulSoup(html, "html.parser")
    assert soup.select_one('[data-metric="current"]').get_text(strip=True) == "−6.8%"
    assert soup.select_one('[data-metric="worst"]').get_text(strip=True) == "−7.4%"
    assert soup.select_one('[data-metric="rebound"]').get_text(strip=True) == "+0.6%"
    assert 'data-pb-phase="underway"' in html
    assert "Pullback underway" in html and "回撤进行中" in html
    assert "12" in soup.select_one('[data-metric="age"]').get_text()


@pytest.mark.parametrize("market", ["cn", "us"])
def test_no_forecast_or_reentry_authority_is_inferred(market):
    v = native_view(market)
    v.update(probability=0.97, score=99, forecast={"q25": 0.024, "q75": 0.056})
    html = render(v, market)
    assert 'data-forecast-status="unavailable"' in html
    assert "Further downside" in html and "后续下跌空间" in html
    assert "97%" not in html and "2.4" not in html and "5.6" not in html
    assert "not a new-entry signal" in html
    assert "Confidence: 100" not in html


@pytest.mark.parametrize("value", [None, {}, [], "bad"])
def test_missing_view_is_not_a_calm_or_current_vote(value):
    html = render(value)
    assert 'data-pb-phase="unavailable"' in html
    assert "Price update needed" in html and "价格数据待更新" in html
    assert 'data-metric="current"' not in html


@pytest.mark.parametrize("key,value", [
    ("available", False), ("available", "true"), ("quality", "delayed"),
    ("clock", "intraday"), ("market", "us"), ("schema", "other.v1"),
    ("close", None), ("close", float("nan")), ("close", True),
    ("peak_close", 0), ("peak_close", float("inf")),
    ("low_close", 0), ("low_close", 96), ("valid_until", None),
])
def test_invalid_observation_does_not_leak_current_metrics(key, value):
    v = native_view()
    v["observation"][key] = value
    html = render(v)
    assert 'data-pb-phase="unavailable"' in html
    assert 'data-metric="current"' not in html
    assert "−6.8%" not in html


def test_presenter_phase_must_match_the_observation():
    v = native_view()
    v["phase"] = "repaired"
    html = render(v)
    assert 'data-pb-phase="unavailable"' in html
    assert "Trend repaired" not in html


@pytest.mark.parametrize("phase,title", [
    ("underway", "Pullback underway"), ("stabilizing", "Stabilization watch"),
    ("recovering", "Price repair building"), ("repaired", "Trend repaired"),
    ("developing", "Pullback developing"), ("monitoring", "Pullback monitor"),
])
def test_existing_phase_is_rendered_without_reclassification(phase, title):
    v = native_view()
    v["phase"] = v["observation"]["phase"] = phase
    v["observation"]["active"] = phase in ("underway", "stabilizing", "recovering")
    html = render(v)
    assert title in html and f'data-pb-phase="{phase}"' in html
    assert 'data-forecast-status="unavailable"' in html


def test_expiry_uses_existing_owner_selectors_without_another_timer():
    v = native_view()
    html = render(v)
    assert 'data-pb-valid-until="2026-10-01T09:00:00+00:00"' in html
    soup = BeautifulSoup(html, "html.parser")
    assert soup.select_one(".pbx-heading h2 .l-en")
    assert soup.select_one(".pbx-expiry") and soup.select_one(".pbx-current")
    assert "setTimeout" not in html and "<script" not in html
    assert 'role="dialog"' not in html  # the existing popup retains the shell


def test_dynamic_text_is_escaped_even_without_jinja_autoescape():
    v = native_view()
    v["observation"]["benchmark_en"] = '<img src=x onerror="alert(1)">'
    v["observation"]["source_digest"] = '" onclick="bad'
    soup = BeautifulSoup(render(v), "html.parser")
    assert not soup.find("img")
    assert not soup.select("[onclick]")


def test_prior_peak_reclaim_does_not_delete_worst_damage():
    v = native_view()
    v["phase"] = v["observation"]["phase"] = "recovering"
    v["observation"]["close"] = 101
    v["observation"]["drawdown_pct"] = 0
    soup = BeautifulSoup(render(v), "html.parser")
    assert soup.select_one('[data-metric="current"]').get_text(strip=True) == "0.0%"
    assert soup.select_one('[data-metric="worst"]').get_text(strip=True) == "−7.4%"


def test_render_does_not_mutate_native_view():
    v = native_view()
    prior = deepcopy(v)
    render(v)
    assert v == prior


def test_no_guessed_age_when_native_count_is_missing():
    v = native_view()
    del v["observation"]["observed_closes_since_onset"]
    html = render(v)
    assert 'data-metric="age"' not in html


def test_source_has_both_art_directions_and_no_local_palette():
    path = ROOT / "templates/_risk_radar_pullback_depth.css.j2"
    assert path.exists(), "Paper pullback styles are not implemented"
    css = path.read_text()
    assert 'html[data-theme="light"] .rrp' in css
    assert "var(--card-shadow)" in css and "var(--panel)" in css
    assert ".rrp.pb-expired .pbx-current" in css
    assert "@media" in css and "#" not in css and ":root" not in css


def test_monitoring_without_an_episode_low_is_still_a_current_observation():
    v = native_view()
    v['phase'] = v['observation']['phase'] = 'monitoring'
    v['observation']['active'] = False
    v['observation']['low_close'] = None
    html = render(v)
    assert 'data-pb-phase="monitoring"' in html
    assert 'data-metric="current"' in html


@pytest.mark.parametrize('active', [False, None, 'true'])
def test_active_phase_cannot_survive_contradictory_native_activity(active):
    v = native_view()
    v['observation']['active'] = active
    assert 'data-pb-phase="unavailable"' in render(v)


def test_chart_has_bilingual_text_alternative_and_price_history():
    v = native_view()
    v['observation']['price_path'] = {'dates':['2026-09-29','2026-09-30'], 'vals':[-7.4,-6.8]}
    soup = BeautifulSoup(render(v), 'html.parser')
    assert soup.select_one('.rrp-chart[aria-hidden="true"]')
    caption = soup.select_one('.rrp-chart-caption')
    assert caption.select_one('.l-en') and caption.select_one('.l-zh')
    rows = soup.select('.rrp-history tbody tr')
    assert len(rows) == 2 and '2026-09-30' in rows[1].get_text()
