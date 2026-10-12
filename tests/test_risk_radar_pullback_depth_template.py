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
    assert "FURTHER DOWNSIDE" in html and "进一步跌幅" in html
    assert "Estimate unavailable" in html and "估计暂不可用" in html
    for shaped in ("后续下跌空间", "预估", "Estimated total", "from today"):
        assert shaped not in html
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
    assert "Pullback repaired" not in html


@pytest.mark.parametrize("phase,title,title_zh", [
    ("underway", "Pullback underway", "回撤进行中"), ("stabilizing", "Stabilization watch", "止跌观察"),
    ("recovering", "Watching price repair", "价格修复观察"), ("repaired", "Pullback repaired", "本轮回撤已修复"),
    ("developing", "Pullback developing", "回撤形成中"), ("monitoring", "Pullback monitor", "回撤观察"),
])
def test_existing_phase_is_rendered_without_reclassification(phase, title, title_zh):
    v = native_view()
    v["phase"] = v["observation"]["phase"] = phase
    v["observation"]["active"] = phase in ("underway", "stabilizing", "recovering")
    html = render(v)
    assert title in html and title_zh in html and f'data-pb-phase="{phase}"' in html
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
    v['detail_path'] = {'dates':['2026-09-29','2026-09-30'], 'vals':[-7.4,-6.8]}
    soup = BeautifulSoup(render(v), 'html.parser')
    assert soup.select_one('.rrp-chart[aria-hidden="true"]')
    caption = soup.select_one('.rrp-chart-caption')
    assert caption.select_one('.l-en') and caption.select_one('.l-zh')
    rows = soup.select('.rrp-history tbody tr')
    assert len(rows) == 2 and '2026-09-30' in rows[1].get_text()


def test_price_history_table_reads_the_same_window_the_chart_drew():
    # The table is the chart's text alternative (the chart is aria-hidden).
    v = native_view()
    v['observation']['price_path'] = {'dates': ['2026-09-11', '2026-09-14', '2026-09-30'],
                                      'vals': [-2.0, 0.0, -6.8]}
    v['detail_path'] = {'dates': ['2026-09-14', '2026-09-30'], 'vals': [0.0, -6.8]}
    rows = BeautifulSoup(render(v), 'html.parser').select('.rrp-history tbody tr')
    assert [r.select_one('td').get_text() for r in rows] == ['2026-09-14', '2026-09-30']


def test_raw_owner_path_alone_is_not_tabulated():
    # Only the presenter's validated window is the chart's text alternative; the
    # owner's raw path can start before the peak or miss the retained low.
    v = native_view()
    v['observation']['price_path'] = {'dates': ['2026-09-11', '2026-09-14', '2026-09-30'],
                                      'vals': [-2.0, 0.0, -6.8]}
    assert BeautifulSoup(render(v), 'html.parser').select_one('.rrp-history') is None


def test_withheld_chart_without_a_reason_stays_neutral_not_that_prices_are_unusable():
    # The figures are current; a presenter that does not say why the chart was
    # withheld (the real reasons are covered by the US presenter's tests) gets
    # copy that is true for every reason.
    v = native_view()
    v['detail_chart_html'] = ''
    evidence = BeautifulSoup(render(v), 'html.parser').select_one('.rrp-evidence')
    assert 'No chart is shown for this assessment.' in evidence.get_text()
    for claim in ('needs current, usable price evidence', 'Chart withheld', 'Too few closes'):
        assert claim not in evidence.get_text()
    v['observation']['quality'] = 'delayed'
    evidence = BeautifulSoup(render(v), 'html.parser').select_one('.rrp-evidence')
    assert 'needs current, usable price evidence' in evidence.get_text()


def test_close_above_the_retained_high_is_rejected_not_shown_as_zero_damage():
    v = native_view()
    v['observation']['close'] = 101.0
    v['observation']['low_close'] = 92.6
    assert 'data-pb-phase="unavailable"' in render(v)


def test_figures_that_round_to_zero_print_without_a_sign():
    v = native_view()
    v['observation'].update(close=99.97, peak_close=100.0, low_close=99.97)
    v['detail_path'] = {'dates': ['2026-09-29', '2026-09-30'], 'vals': [-0.004, -1.234]}
    soup = BeautifulSoup(render(v), 'html.parser')
    assert soup.select_one('[data-metric="current"]').get_text(strip=True) == "0.0%"
    assert soup.select_one('[data-metric="worst"]').get_text(strip=True) == "0.0%"
    assert soup.select_one('[data-metric="rebound"]').get_text(strip=True) == "0.0%"
    cells = [r.select('td')[1].get_text() for r in soup.select('.rrp-history tbody tr')]
    assert cells == ["0.00%", "\u22121.23%"]


@pytest.mark.parametrize("change, lead", [
    ({}, "1"),
    ({"low_close": None}, ""),
    ({"close": 101.0}, ""),
    ({"quality": "delayed"}, ""),
])
def test_lead_gate_uses_the_fragments_own_qualification(change, lead):
    v = native_view("us")
    v["observation"].update(change)
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
    got = env.from_string('{% import "_risk_radar_pullback_depth.html.j2" as p %}{{ p.lead("us", v) }}').render(v=v)
    assert got.strip() == lead


EXPIRY_JS = r"""
const assert = require('node:assert/strict');
let now = Date.parse('2026-10-11T00:00:00Z');
Date.now = () => now;
const timers = [], listeners = {document: {}, window: {}};
function section(stamp) {
  const attrs = {'data-pb-valid-until': stamp, 'data-pb-phase': 'underway'}, classes = new Set(['rrp', 'pbx']);
  const en = {textContent: 'Pullback underway'}, zh = {textContent: '回调进行中'};
  const heading = {querySelector: s => ({'.l-en': en, '.l-zh': zh})[s] || null};
  return {en, zh, attrs, classes,
          getAttribute: k => (k in attrs ? attrs[k] : null), setAttribute: (k, v) => { attrs[k] = String(v); },
          classList: {add: c => classes.add(c)},
          querySelector: s => (s === '.pbx-heading h2' ? heading : null)};
}
const sections = {
  zoned: section('2026-10-12T09:00:00+00:00'), utc: section('2026-10-12T09:00:00Z'),
  naive: section('2026-10-12T09:00:00'), past: section('2026-10-10T09:00:00+00:00'), empty: section(''),
};
const document = {
  readyState: 'complete', hidden: false,
  querySelectorAll(sel) { assert.equal(sel, '.rrp.pbx[data-pb-valid-until]'); return Object.values(sections); },
  addEventListener(type, fn) { listeners.document[type] = fn; },
};
const window = {
  setTimeout(fn, ms) { timers.push({fn, ms}); return timers.length; }, clearTimeout() {},
  addEventListener(type, fn) { listeners.window[type] = fn; },
};
new Function('window', 'document', require('node:fs').readFileSync(0, 'utf8'))(window, document);
const expired = k => sections[k].classes.has('pb-expired');
// Only a stamp with an explicit offset is a deadline.
assert.equal(expired('zoned'), false); assert.equal(expired('utc'), false);
for (const k of ['naive', 'past', 'empty']) {
  assert.equal(expired(k), true, k);
  assert.equal(sections[k].attrs['data-pb-phase'], 'unavailable');
  assert.equal(sections[k].en.textContent, 'Price update needed');
  assert.equal(sections[k].zh.textContent, '价格数据待更新');
}
assert.equal(sections.zoned.en.textContent, 'Pullback underway');
// One timer: a deadline more than a minute away is re-checked within a minute.
assert.equal(timers.length, 1);
assert.equal(timers[0].ms, 60000);
// With no wake event at all, the clock passing the deadline expires the section
// within one re-check interval.
now = Date.parse('2026-10-12T08:59:59.950Z');
timers.at(-1).fn();
assert.equal(expired('zoned'), false);
assert.equal(timers.at(-1).ms, 60, 'a near deadline is aimed just past itself');
now = Date.parse('2026-10-12T09:00:00.010Z');
timers.at(-1).fn();
assert.equal(expired('zoned'), true); assert.equal(expired('utc'), true);
assert.equal(timers.length, 2, 'the passive path stops re-arming once every section has expired');
// Reset the sections so the wake paths are proven on their own.
for (const k of ['zoned', 'utc']) {
  sections[k].classes.delete('pb-expired');
  sections[k].attrs['data-pb-phase'] = 'underway';
  sections[k].en.textContent = 'Pullback underway';
}
now = Date.parse('2026-10-11T00:00:00Z');
timers.length = 0; window.mmPbExpire();
assert.equal(expired('zoned'), false); assert.equal(timers.length, 1);
// A slept timer never fires: every wake path re-checks against the clock.
assert.equal(typeof window.mmPbExpire, 'function');
for (const [owner, type] of [['document', 'visibilitychange'], ['window', 'pageshow'], ['window', 'focus']]) {
  assert.equal(typeof listeners[owner][type], 'function', type);
}
now = Date.parse('2026-10-12T09:00:01Z');
listeners.window.focus();
assert.equal(expired('zoned'), true); assert.equal(expired('utc'), true);
assert.equal(sections.zoned.attrs['data-pb-phase'], 'unavailable');
assert.equal(sections.zoned.en.textContent, 'Price update needed');
assert.equal(timers.length, 1, 'nothing left to schedule once every section has expired');
"""


def test_expiry_script_honours_only_zoned_deadlines_and_rechecks_on_wake():
    """Execute the shipped expiry owner against a fake clock, document and timers."""
    from tests.test_us_pullback_modal_integration import _node_raw

    _node_raw(EXPIRY_JS, (ROOT / "templates/_risk_radar_pullback_depth.js.j2").read_text())


def test_both_risk_dialogs_recheck_expiry_as_they_open():
    us = (ROOT / "templates/dashboard.html.j2").read_text()
    opener = us[us.index("window.mx5OpenDlg = function(id){"):]
    opener = opener[:opener.index("\n    };")]
    check = "if(id === 'dlg-risk' && window.mmPbExpire) window.mmPbExpire();"
    assert check in opener
    # Expiry settles before focus lands, as China's opener does.
    assert opener.index(check) < opener.index("_focusFirst(dlg);")
    cn = (ROOT / "templates/china.html.j2").read_text()
    cn_open = cn[cn.index("function cnxOpenDlg(id){"):cn.index("function cnxCloseDlg(){")]
    cn_check = "if(id==='cnx-dlg-risk'&&window.mmPbExpire)window.mmPbExpire();"
    assert cn_check in cn_open
    assert cn_open.index(cn_check) < cn_open.index("first.focus({preventScroll:true})")


FULL_EVIDENCE = {
    "onset_session": "2026-09-16",
    "low_session": "2026-09-21",
    "no_new_low_closes": 4,
    "loss_recovered_pct": 8.11,
    "below_20_close_average": True,
    "price_transitions": [
        {"date": "2026-09-16", "phase": "underway"},
        {"date": "2026-09-24", "phase": "stabilizing"},
        {"date": "2026-09-29", "phase": "recovering"},
    ],
    "history_gap_count": 2,
}
_MISSING = object()


def evidence_view(phase="underway", **fields):
    v = native_view()
    v["phase"] = phase
    v["observation"]["phase"] = phase
    v["observation"]["active"] = phase in ("underway", "stabilizing", "recovering")
    if phase in ("monitoring", "developing"):
        v["observation"]["low_close"] = None
    v["observation"].update(fields)
    return v


def _signal(soup, name):
    return soup.select_one(f'.rrp-signals [data-signal="{name}"]')


@pytest.mark.parametrize("phase,en,zh", [
    ("underway", "Deterioration: no repair evidence yet", "恶化：尚无修复证据"),
    ("stabilizing", "Early repair evidence: the low is holding", "初步修复证据：低点守住"),
    ("recovering", "Repair evidence building; not a confirmed recovery", "修复证据增加中，尚未确认修复"),
])
def test_evidence_rows_are_bilingual_and_the_verdict_matches_the_phase(phase, en, zh):
    soup = BeautifulSoup(render(evidence_view(phase, **FULL_EVIDENCE)), "html.parser")
    block = soup.select_one(".rrp-signals[data-evidence]")
    assert block is not None
    onset = _signal(soup, "onset")
    assert onset.select_one(".l-en").get_text() == "Pullback confirmed"
    assert onset.select_one(".l-zh").get_text() == "回撤确认"
    assert onset.find_next_sibling("dd").get_text(strip=True) == "2026-09-16"
    low = _signal(soup, "low")
    assert low.select_one(".l-en").get_text() == "Lowest close"
    assert low.select_one(".l-zh").get_text() == "最低收盘价"
    assert low.find_next_sibling("dd").get_text(strip=True) == "2026-09-21"
    streak = _signal(soup, "no-new-low")
    assert streak.select_one(".l-en").get_text() == "Closes without a new low"
    assert streak.select_one(".l-zh").get_text() == "未创新低的收盘数"
    assert streak.find_next_sibling("dd").get_text(strip=True) == "4"
    recovered = _signal(soup, "recovered")
    assert recovered.select_one(".l-en").get_text() == "Share of the loss retraced"
    assert recovered.select_one(".l-zh").get_text() == "已收复跌幅比例"
    assert recovered.find_next_sibling("dd").get_text(strip=True) == "8%"
    side = _signal(soup, "ma20")
    assert side.select_one(".l-en").get_text() == "Against the 20-close average"
    assert side.select_one(".l-zh").get_text() == "相对20日收盘均价"
    value = side.find_next_sibling("dd")
    assert value.select_one(".l-en").get_text() == "Below"
    assert value.select_one(".l-zh").get_text() == "低于"
    verdict = _signal(soup, "verdict")
    assert verdict.select_one(".l-en").get_text() == en
    assert verdict.select_one(".l-zh").get_text() == zh
    for other in (
        "Deterioration: no repair evidence yet",
        "Early repair evidence: the low is holding",
        "Repair evidence building; not a confirmed recovery",
    ):
        if other != en:
            assert other not in block.get_text()
    items = block.select("ol.rrp-phase-trail li")
    assert [li.select_one(".l-en").get_text() for li in items] == [
        "Pullback underway", "Stabilization watch", "Watching price repair",
    ]
    assert [li.select_one(".l-zh").get_text() for li in items] == [
        "回撤进行中", "止跌观察", "价格修复观察",
    ]
    assert [li.get_text(" ", strip=True).split("·")[0].strip() for li in items] == [
        "2026-09-16", "2026-09-24", "2026-09-29",
    ]
    gaps = _signal(soup, "gaps")
    assert gaps.select_one(".l-en").get_text() == "2 sessions missing from the price history"
    assert gaps.select_one(".l-zh").get_text() == "价格历史缺少2个交易日"



def test_one_missing_session_reads_in_the_singular():
    soup = BeautifulSoup(render(evidence_view(history_gap_count=1)), "html.parser")
    gaps = _signal(soup, "gaps")
    assert gaps.select_one(".l-en").get_text() == "1 session missing from the price history"
    assert gaps.select_one(".l-zh").get_text() == "价格历史缺少1个交易日"

def test_average_at_or_above_uses_the_other_label():
    soup = BeautifulSoup(render(evidence_view(below_20_close_average=False)), "html.parser")
    value = _signal(soup, "ma20").find_next_sibling("dd")
    assert value.select_one(".l-en").get_text() == "Above or at"
    assert value.select_one(".l-zh").get_text() == "不低于"


def test_zero_counts_print_only_when_the_owner_sent_zero():
    soup = BeautifulSoup(render(evidence_view(
        no_new_low_closes=0, loss_recovered_pct=0, history_gap_count=0,
    )), "html.parser")
    assert _signal(soup, "no-new-low").find_next_sibling("dd").get_text(strip=True) == "0"
    assert _signal(soup, "recovered").find_next_sibling("dd").get_text(strip=True) == "0%"
    assert _signal(soup, "gaps") is None


def test_recovered_share_prints_a_whole_percent_inside_the_closed_range():
    for value, shown in ((8, "8%"), (100, "100%"), (0.4, "0%"), (99.6, "100%")):
        soup = BeautifulSoup(render(evidence_view(loss_recovered_pct=value)), "html.parser")
        assert _signal(soup, "recovered").find_next_sibling("dd").get_text(strip=True) == shown


@pytest.mark.parametrize("field,value,signal", [
    ("onset_session", _MISSING, "onset"),
    ("onset_session", None, "onset"),
    ("onset_session", "3", "onset"),
    ("onset_session", 20260916, "onset"),
    ("low_session", _MISSING, "low"),
    ("low_session", None, "low"),
    ("low_session", "3", "low"),
    ("no_new_low_closes", _MISSING, "no-new-low"),
    ("no_new_low_closes", None, "no-new-low"),
    ("no_new_low_closes", "3", "no-new-low"),
    ("no_new_low_closes", -1, "no-new-low"),
    ("no_new_low_closes", 1.5, "no-new-low"),
    ("no_new_low_closes", True, "no-new-low"),
    ("loss_recovered_pct", _MISSING, "recovered"),
    ("loss_recovered_pct", None, "recovered"),
    ("loss_recovered_pct", "3", "recovered"),
    ("loss_recovered_pct", -1, "recovered"),
    ("loss_recovered_pct", 101.0, "recovered"),
    ("loss_recovered_pct", float("nan"), "recovered"),
    ("loss_recovered_pct", float("inf"), "recovered"),
    ("below_20_close_average", _MISSING, "ma20"),
    ("below_20_close_average", None, "ma20"),
    ("below_20_close_average", "3", "ma20"),
    ("below_20_close_average", 0, "ma20"),
    ("below_20_close_average", 1, "ma20"),
    ("history_gap_count", _MISSING, "gaps"),
    ("history_gap_count", None, "gaps"),
    ("history_gap_count", "3", "gaps"),
    ("history_gap_count", -1, "gaps"),
    ("history_gap_count", 0, "gaps"),
    ("history_gap_count", 1.0, "gaps"),
    ("price_transitions", _MISSING, "trail"),
    ("price_transitions", None, "trail"),
    ("price_transitions", "3", "trail"),
    ("price_transitions", [], "trail"),
    ("price_transitions", {"date": "2026-09-16", "phase": "underway"}, "trail"),
    ("price_transitions", [{"date": "3", "phase": "underway"}], "trail"),
    ("price_transitions", [{"date": None, "phase": "underway"}], "trail"),
    ("price_transitions", [{"date": "2026-09-16", "phase": "shock"}], "trail"),
    ("price_transitions", [
        {"date": "2026-09-16", "phase": "underway"},
        {"date": "2026-09-20", "phase": "not-a-phase"},
    ], "trail"),
])
def test_missing_or_mistyped_evidence_field_omits_that_row(field, value, signal):
    kept = {k: v for k, v in FULL_EVIDENCE.items() if k != field}
    v = evidence_view(**kept)
    v["observation"].pop(field, None)
    if value is not _MISSING:
        v["observation"][field] = value
    soup = BeautifulSoup(render(v), "html.parser")
    if signal == "trail":
        assert soup.select_one("ol.rrp-phase-trail") is None
    else:
        assert _signal(soup, signal) is None
    assert _signal(soup, "verdict") is not None


def test_phase_alone_still_states_deterioration_without_inventing_counts():
    v = native_view()
    v["observation"].pop("loss_recovered_pct")
    soup = BeautifulSoup(render(v), "html.parser")
    block = soup.select_one(".rrp-signals")
    assert block is not None and block.select("dt") == []
    assert _signal(soup, "verdict").select_one(".l-en").get_text() == "Deterioration: no repair evidence yet"
    assert "8%" not in block.get_text()


@pytest.mark.parametrize("phase", ["monitoring", "developing", "repaired"])
def test_phases_outside_the_repair_watch_do_not_invent_a_verdict(phase):
    soup = BeautifulSoup(render(evidence_view(phase, **FULL_EVIDENCE)), "html.parser")
    text = soup.select_one(".rrp-signals").get_text()
    assert _signal(soup, "verdict") is None
    for claim in (
        "Deterioration: no repair evidence yet",
        "Early repair evidence: the low is holding",
        "Repair evidence building; not a confirmed recovery",
    ):
        assert claim not in text


def test_unavailable_view_renders_no_evidence_block():
    assert 'class="rrp-signals"' not in render(None)
    assert "data-evidence" not in render({})
    v = native_view()
    v["observation"]["quality"] = "delayed"
    html = render(v)
    assert 'data-pb-phase="unavailable"' in html
    assert 'class="rrp-signals"' not in html


def test_view_lacking_new_fields_omits_the_signals_block():
    """No new owner fields and no repair-phase verdict: the block is absent."""
    v = native_view()
    v["phase"] = v["observation"]["phase"] = "monitoring"
    v["observation"]["active"] = False
    v["observation"]["low_close"] = None
    v["observation"].pop("loss_recovered_pct")
    v["observation"]["valid_until"] = "2026-10-01T09:00:00"
    html = render(v)
    assert 'class="rrp-signals"' not in html and "data-evidence" not in html
    assert "Current until" not in html and "有效至" not in html
    assert 'data-metric="current"' in html
    assert 'data-pb-phase="monitoring"' in html
    assert 'data-pb-valid-until="2026-10-01T09:00:00"' in html


@pytest.mark.parametrize("stamp", [
    "2026-10-01T09:00:00",
    "2026-10-01T09:00",
    "2026-10-01",
    "",
    None,
    "2026-10-01T09:00:00+0000",
    "2026-10-01 09:00:00Z",
    "2026-10-01T09:00:00z",
])
def test_valid_until_without_offset_renders_no_current_until(stamp):
    v = native_view()
    v["observation"]["valid_until"] = stamp
    html = render(v)
    assert "Current until" not in html and "有效至" not in html
    if stamp:
        assert f'data-pb-valid-until="{stamp}"' in html


@pytest.mark.parametrize("stamp,display", [
    ("2026-10-01T09:00:00+00:00", "2026-10-01 09:00 UTC+00:00"),
    ("2026-10-01T09:00:00Z", "2026-10-01 09:00 UTC"),
    ("2026-10-01T09:00Z", "2026-10-01 09:00 UTC"),
    ("2026-10-01T09:00-05:00", "2026-10-01 09:00 UTC-05:00"),
    ("2026-10-01T09:30:45+08:00", "2026-10-01 09:30 UTC+08:00"),
])
def test_zoned_valid_until_is_readable_without_js(stamp, display):
    v = native_view()
    v["observation"]["valid_until"] = stamp
    soup = BeautifulSoup(render(v), "html.parser")
    section = soup.select_one("section.rrp")
    assert section.get("data-pb-valid-until") == stamp
    assert section.get("data-pb-asof") == "2026-09-30"
    assert section.get("data-pb-digest") == "a" * 64
    times = soup.select(".rrp-stamp time")
    assert times[0].get("datetime") == "2026-09-30"
    assert times[1].get("datetime") == stamp
    assert times[1].get_text(strip=True) == display
    stamp_node = soup.select_one(".rrp-stamp")
    assert stamp_node.select_one(".l-en") and "Current until" in stamp_node.get_text()
    assert "有效至" in stamp_node.get_text()


def test_rules_are_not_copied_in_as_cutoffs():
    v = evidence_view(**FULL_EVIDENCE)
    v["observation"]["rules"] = {
        "stabilization_closes": 3,
        "recovery_above_ma_closes": 5,
        "recovery_no_low_closes": 10,
        "trend_repair_no_low_closes": 21,
    }
    html = render(v)
    assert "stabilization_closes" not in html
    assert "recovery_no_low_closes" not in html
    assert "trend_repair_no_low_closes" not in html
    soup = BeautifulSoup(html, "html.parser")
    block = soup.select_one(".rrp-signals")
    assert _signal(soup, "no-new-low").find_next_sibling("dd").get_text(strip=True) == "4"
    assert "of 10" not in block.get_text() and "of 21" not in block.get_text()


def test_forecast_stays_free_of_digits():
    v = evidence_view(**FULL_EVIDENCE)
    v["observation"]["loss_recovered_pct"] = 100
    v["observation"]["no_new_low_closes"] = 21
    v["observation"]["history_gap_count"] = 12
    forecast = BeautifulSoup(render(v), "html.parser").select_one(".rrp-forecast")
    assert forecast.get("data-forecast-status") == "unavailable"
    assert not any(ch.isdigit() for ch in forecast.get_text())
    assert "Estimate unavailable" in forecast.get_text()


def test_phase_trail_remains_markup_when_autoescape_is_on():
    v = evidence_view(price_transitions=[{"date": "2026-09-16", "phase": "underway"}])
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    html = env.from_string(
        '{% import "_risk_radar_pullback_depth.html.j2" as p %}{{ p.detail(market, v) }}'
    ).render(market="cn", v=v)
    assert '<ol class="rrp-phase-trail">' in html
    assert "&lt;ol" not in html
    assert "2026-09-16" in html and "Pullback underway" in html


def test_signals_css_reuses_the_existing_palette_and_collapses():
    css = (ROOT / "templates/_risk_radar_pullback_depth.css.j2").read_text()
    assert ".rrp .rrp-signals" in css and ".rrp-phase-trail" in css
    assert "max-width:420px" in css.replace(" ", "")
    rules = css.split("Owner deterioration", 1)[1]
    assert "animation" not in rules
    assert "#" not in rules


def test_copy_names_measurements_not_forecasts():
    """G8: labels describe what was observed; nothing reads as an estimate."""
    v = native_view()
    v['observation']['price_path'] = {'dates': ['2026-09-14', '2026-09-30'], 'vals': [0.0, -6.8]}
    v['detail_path'] = {'dates': ['2026-09-14', '2026-09-30'], 'vals': [0.0, -6.8]}
    html = render(v)
    for phrase in (
        "From the reference high", "距参考高点",
        "Measured at the lowest close so far", "按本轮最低收盘价计算",
        "observed closes since the pullback was confirmed", "个已观测收盘（自回撤确认起）",
        "View price history", "查看历史价格",
        "Further decline from the latest close", "自最新收盘价起的进一步跌幅",
        "Total pullback depth", "回撤总深度",
        "This is not a new-entry signal.", "这不是新开仓信号。",
    ):
        assert phrase in html, phrase
    for retired in (
        "retained reference high", "保留参考高点", "The previous low is retained",
        "Trend repaired", "趋势修复", "Price repair building",
        "已观察价格", "价格历程",
        # Z1 copy review: backtest jargon, English word order, a softer verdict.
        "低点回测", "Below the reference high", "次已观测收盘", "新的入场信号", "仍在恶化",
        "session(s)",
    ):
        assert retired not in html, retired
