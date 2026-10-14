"""No downside forecast across every rendered pullback state.

Rendering entry points, reused rather than reimplemented:

* Presenter: ``lib.pullback_depth.present`` via the US and CN adapters'
  ``present()`` (``lib.us_pullback_observation``, ``lib.cn_pullback_observation``).
* Fragment: ``templates/_risk_radar_pullback_depth.html.j2`` ``detail()``,
  through ``tests.test_pullback_depth_copy_states.render_read`` and
  ``tests.test_risk_radar_pullback_depth_template.render``.
* Dialogs: ``tests.test_us_pullback_modal_integration.dialog`` and
  ``tests.test_cn_pullback_dialog_integration.dialog``. The dialog includes
  the fragment only when ``lead()`` is active (underway, stabilizing, recovering).

The forecast block is ``div.rrp-forecast`` with ``data-forecast-status="unavailable"``
(``templates/_risk_radar_pullback_depth.html.j2`` line 204). Its value cells are
the two ``.rrp-forecast-row strong`` elements (lines 208-209).

States are the ones the replay and copy-state suites enumerate, plus the
unavailable qualities those adapters' presenters actually emit. ``expired`` is
the client DOM produced by ``templates/_risk_radar_pullback_depth.js.j2``
(``expire`` / ``announceExpiry``), not a presenter quality. US-only
``unknown_adjustment`` is ``corporate_action_guard_down``; the CN adapter does
not emit it.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from functools import lru_cache
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup, Comment

from lib import cn_pullback_observation as cn_adapter
from lib import us_pullback_observation as us_adapter
from lib.pullback_depth import PHASES
from lib.pullback_observation import observe
from tests.test_cn_pullback_dialog_integration import dialog as cn_dialog
from tests.test_cn_pullback_observation_adapter import (
    FIXED_NOW as CN_NOW,
    reader as cn_reader,
    store as cn_store,
)
from tests.test_pullback_depth_copy_states import (
    _with_gaps,
    observe_series,
    render_read,
    session,
    weekday_closes,
)
from tests.test_pullback_scenario_replay import weekday_closes as replay_closes
from tests.test_risk_radar_pullback_depth_template import render as render_fragment
from tests.test_us_pullback_modal_integration import dialog as us_dialog
from tests.test_us_pullback_observation_adapter import (
    FIXED_NOW as US_NOW,
    reader as us_reader,
    store as us_store,
)

# The forecast block. Cite: templates/_risk_radar_pullback_depth.html.j2:204.
FORECAST_SELECTOR = ".rrp-forecast"
FORECAST_STATUS = "unavailable"
EM_DASH = "\u2014"

# Exact normalized text nodes (whitespace-collapsed) copied from
# templates/_risk_radar_pullback_depth.html.j2. A visible text node is exempt
# only when its whole normalized text equals one of these strings.
# Line 155 denies recovery odds. Line 202 denies a forecast path. Line 211
# denies a remaining-drop forecast. No substring match and no regex exemption.
_METHOD_DISCLAIMER = {
    "en": (
        "Publishing a range takes historical tests for this market, benchmark, "
        "price measurement and time window. Risk level and existing pullback "
        "probabilities are not a forecast of the remaining drop."
    ),
    "zh": (
        "发布区间需要针对本市场、基准、价格衡量方式和时间范围的历史检验。"
        "风险水平与现有回撤概率并非对剩余跌幅的预测。"
    ),
}
DISCLAIMER_ALLOW = frozenset({
    "Not recovery odds",
    "并非修复概率",
    "The chart is price history, not a forecast path.",
    "图表呈现历史价格，并非预测路径。",
    *_METHOD_DISCLAIMER.values(),
})

# Template labels for N2 (line 206). They match the template verbatim.
ESTIMATE_LABEL = {"en": "Estimate unavailable", "zh": "估计暂不可用"}

# Forbidden forecast language. One pattern per entry.
FORBIDDEN = (
    # EN: the word probability
    ("en", r"\bprobability\b"),
    # EN: the word probable
    ("en", r"\bprobable\b"),
    # EN: the phrase "likely to"
    ("en", r"likely to"),
    # EN: the word odds
    ("en", r"\bodds\b"),
    # EN: the phrase "chance of"
    ("en", r"chance of"),
    # EN: "expected" followed by a downside noun
    ("en", r"expected\s+(?:drop|decline|downside|bottom)"),
    # EN: the word target
    ("en", r"\btarget\b"),
    # EN: "forecast(ed) downside of"
    ("en", r"forecast(?:ed)?\s+downside\s+of"),
    # EN: the word forecast or forecasted, outside an allow-listed text node
    ("en", r"\bforecast(?:ed)?\b"),
    # EN: "will" followed by a directional verb
    ("en", r"will\s+(?:fall|drop|rebound|bounce|recover)"),
    # EN: the phrase "buy the dip"
    ("en", r"buy the dip"),
    # EN: the phrase "bounce = buy"
    ("en", r"bounce\s*=\s*buy"),
    # EN: the phrase "oversold so"
    ("en", r"oversold so"),
    # EN: the phrase "bottom is in"
    ("en", r"bottom is in"),
    # ZH: 概率
    ("zh", r"概率"),
    # ZH: 可能性
    ("zh", r"可能性"),
    # ZH: 预计
    ("zh", r"预计"),
    # ZH: 预期
    ("zh", r"预期"),
    # ZH: 目标价
    ("zh", r"目标价"),
    # ZH: 目标位
    ("zh", r"目标位"),
    # ZH: 将会下跌 / 将会反弹 / 将会回升
    ("zh", r"将会(?:下跌|反弹|回升)"),
    # ZH: 抄底
    ("zh", r"抄底"),
    # ZH: 见底
    ("zh", r"见底"),
    # ZH: 预测, outside an allow-listed text node
    ("zh", r"预测"),
)

# Template eyebrow is "FURTHER DOWNSIDE" / "进一步跌幅" (line 205).
# "进一步下跌" is the packet phrase; the template does not use that word.
DOWNSIDE_PHRASE = re.compile(r"further\s+downside|进一步下跌|进一步跌幅", re.I)
PERCENT_FIGURE = re.compile(r"\d+(?:\.\d+)?\s*%")

# Rendered data-pb-phase for each state the sweep builds.
PHASE_OF = {
    "no_pullback": "monitoring",
    "developing": "developing",
    "worsening": "underway",
    "early_repair": "underway",
    "deep_pullback": "underway",
    "stabilizing": "stabilizing",
    "recovering_at_high": "recovering",
    "recovering_above": "recovering",
    "repaired": "repaired",
    "missing_sessions": "stabilizing",
    "insufficient_history": "unavailable",
    "stale": "unavailable",
    "asof_withheld": "unavailable",
    "expired": "unavailable",
    "missing_reader": "unavailable",
    "missing_observer": "unavailable",
    "refused_basis": "unavailable",
    "unknown_adjustment": "unavailable",
}

_SHARED = (
    "no_pullback", "developing", "worsening", "early_repair", "deep_pullback",
    "stabilizing", "recovering_at_high", "recovering_above", "repaired",
    "missing_sessions", "insufficient_history", "stale", "asof_withheld",
    "expired",
)
_BOTH_ADAPTERS = ("missing_reader", "missing_observer", "refused_basis")
_US_ONLY = ("unknown_adjustment",)

CASES = (
    [(state, market) for state in _SHARED + _BOTH_ADAPTERS for market in ("us", "cn")]
    + [(state, "us") for state in _US_ONLY]
)

DIALOG_STATES = tuple(
    state for state, phase in PHASE_OF.items()
    if phase in {"underway", "stabilizing", "recovering"}
)

_HTML = {}


SWEEP = [
    pytest.param(state, market, lang, id=f"{state}-{market}-{lang}")
    for state, market in CASES
    for lang in ("en", "zh")
]


@lru_cache(maxsize=None)
def _owner_read(state):
    """One synthetic observation per replay/copy-state shape."""
    if state == "no_pullback":
        # Steady tape. Replay: monitoring, drawdown never reaches onset.
        return observe_series([100.0] * 70)
    if state == "developing":
        # One close at onset_drawdown, short of onset_closes and shock.
        return observe_series([100.0] * 70 + [97.5])
    if state in {"worsening", "asof_withheld", "expired"}:
        # Copy suite: underway, no repair evidence, deterioration verdict.
        return observe_series([100.0] * 70 + [90.0])
    if state == "early_repair":
        return observe_series([100.0] * 70 + [90, 94, 96])
    if state == "deep_pullback":
        # Replay grind: -15% over sixty closes, still making new lows.
        grind = [100.0 - 0.25 * (i + 1) for i in range(60)]
        rows = replay_closes([100.0] * 63 + grind)
        return _observe_rows(rows)
    if state == "stabilizing":
        # Replay shock path, stopped on the stabilizing close.
        rows = replay_closes([100.0] * 63 + [94.0, 96.0, 97.5, 99.0])
        return _observe_rows(rows)
    if state == "recovering_at_high":
        return observe_series([100.0] * 70 + [90, 100])
    if state == "recovering_above":
        return observe_series([100.0] * 70 + [90, 101])
    if state == "repaired":
        rows = replay_closes([100.0] * 63 + [94.0, 96.0, 97.5, 99.0, 100.0, 100.0])
        return _observe_rows(rows)
    if state == "missing_sessions":
        full = weekday_closes([100.0] * 70 + [90, 94, 96, 97])
        return _with_gaps({full[10][0]})
    if state == "insufficient_history":
        rows = weekday_closes([100.0] * 40)
        read = observe(
            rows, expected_session=date.fromisoformat(rows[-1][0]), is_session=session,
        )
        assert read["quality"] == "insufficient_history", read["quality"]
        return read
    if state == "stale":
        rows = weekday_closes([100.0] * 70 + [90.0])
        end = date.fromisoformat(rows[-1][0]) + timedelta(days=1)
        while not session(end):
            end += timedelta(days=1)
        read = observe(rows, expected_session=end, is_session=session)
        assert read["quality"] == "delayed", read["quality"]
        return read
    raise KeyError(state)


def _observe_rows(rows):
    read = observe(
        rows, expected_session=date.fromisoformat(rows[-1][0]), is_session=session,
    )
    assert read["available"] is True and read["quality"] == "current", read.get("quality")
    return read


def _us_days(n, last=date(2026, 10, 9)):
    found = []
    day = last
    while len(found) < n:
        if day.weekday() < 5:
            found.append(day)
        day -= timedelta(days=1)
    return found[::-1]


def _adapter_observation(state, market):
    adapter = us_adapter if market == "us" else cn_adapter
    now = US_NOW if market == "us" else CN_NOW
    if state == "missing_reader":
        out = adapter.snapshot(now=now, read=None, observer=observe)
        assert out["quality"] == "source_unavailable"
        return out
    if state == "missing_observer":
        # observer is checked before read, so the source is not touched.
        out = adapter.snapshot(now=now, read=None, observer=None)
        assert out["quality"] == "observer_unavailable"
        return out
    if state == "refused_basis" and market == "cn":
        closes = [3200.0] * 69 + [320.0, 321.0]
        out = cn_adapter.snapshot(
            now=CN_NOW, read=cn_reader(cn_store(closes=closes)), observer=observe,
        )
        assert out["quality"] == "price_basis_discontinuity"
        return out
    if state == "refused_basis" and market == "us":
        days = _us_days(2)
        out = us_adapter.snapshot(
            now=US_NOW,
            read=us_reader(load=lambda ticker: us_store(
                stamps=[d.isoformat() for d in days], closes=(100.0, 40.0),
            )),
            observer=observe,
        )
        assert out["quality"] == "price_basis_discontinuity"
        return out
    if state == "unknown_adjustment":
        days = _us_days(3)

        def actions(session_label):
            return SimpleNamespace(session=session_label, complete=False)

        out = us_adapter.snapshot(
            now=US_NOW,
            read=us_reader(
                load=lambda ticker: us_store(
                    stamps=[d.isoformat() for d in days],
                    closes=(100.0, 100.0, 80.0),
                ),
                corp_actions=actions,
            ),
            observer=observe,
        )
        assert out["quality"] == "corporate_action_guard_down"
        return out
    raise KeyError((state, market))


def _view(state, market):
    key = ("view", state, market)
    if key not in _HTML:
        if state in _BOTH_ADAPTERS or state == "unknown_adjustment":
            obs = _adapter_observation(state, market)
            adapter = us_adapter if market == "us" else cn_adapter
            _HTML[key] = adapter.present(obs)
        else:
            read = _owner_read(state)
            if state == "asof_withheld":
                read = dict(read, asof="")
            valid = (
                "2020-01-02T21:00:00+00:00" if state == "expired"
                else "2026-12-31T21:00:00+00:00"
            )
            stamped = dict(
                read, market=market, clock="settled_close", valid_until=valid,
            )
            adapter = us_adapter if market == "us" else cn_adapter
            _HTML[key] = adapter.present(stamped)
    return _HTML[key]


def apply_client_expiry(html):
    """Mirror ``expire`` / ``announceExpiry`` in the pullback expiry script.

    ``templates/_risk_radar_pullback_depth.js.j2`` lines 44-60 and 28-42.
    """
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("section.rrp")
    classes = [c for c in (root.get("class") or []) if c != "pb-expired"]
    classes.append("pb-expired")
    root["class"] = classes
    root["data-pb-phase"] = "unavailable"
    heading = root.select_one(".pbx-heading h2")
    heading.select_one(".l-en").string = "Price update needed"
    heading.select_one(".l-zh").string = "价格数据待更新"
    region = root.select_one(".pbx-expiry")
    carrier = root.select_one("template.pbx-expiry-msg")
    live = BeautifulSoup(
        '<span class="pbx-expiry-live">' + carrier.decode_contents() + "</span>",
        "html.parser",
    ).span
    region.append(live)
    carrier.decompose()
    region["data-pb-announced"] = "1"
    return str(root)


def fragment_html(state, market):
    key = ("frag", state, market)
    if key not in _HTML:
        if state in _BOTH_ADAPTERS or state == "unknown_adjustment" or state == "expired":
            html = render_fragment(_view(state, market), market)
            if state == "expired":
                html = apply_client_expiry(html)
        elif state == "asof_withheld":
            html = render_read(dict(_owner_read(state), asof=""), market)
        else:
            html = render_read(_owner_read(state), market)
        _HTML[key] = html
    return _HTML[key]


def dialog_section_html(state, market):
    key = ("dlg", state, market)
    if key not in _HTML:
        root = cn_dialog(_view(state, market)) if market == "cn" else us_dialog(_view(state, market))
        section = root.select_one("section.rrp")
        assert section is not None, (state, market)
        _HTML[key] = str(section)
    return _HTML[key]


def _prepared(html, lang=None):
    """Visible text for one language.

    ``template`` / ``script`` / ``style`` are inert. Once the expiry owner has
    added ``pb-expired``, the shipped CSS hides ``.pbx-current`` and ``.rrp-sub``
    (``templates/_risk_radar_pullback_depth.css.j2`` line 41).
    """
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("section.rrp")
    assert section is not None
    for node in section.select("template, script, style"):
        node.decompose()
    if "pb-expired" in (section.get("class") or []):
        for node in section.select(".pbx-current, .rrp-sub"):
            node.decompose()
    if lang == "en":
        for node in section.select(".l-zh"):
            node.decompose()
    elif lang == "zh":
        for node in section.select(".l-en"):
            node.decompose()
    return section


def language_text(html, lang):
    return _prepared(html, lang).get_text(" ", strip=True)


def attribute_values(html, lang):
    parts = []
    for el in _prepared(html, lang).find_all(True):
        for key, value in el.attrs.items():
            if key in {"title", "alt"} or key.startswith("aria-") or key.startswith("data-"):
                if isinstance(value, list):
                    value = " ".join(value)
                parts.append(str(value))
    return "\n".join(parts)


def _normalized_text_nodes(html, lang):
    """Visible text nodes, whitespace-collapsed, for one language.

    A node is later exempt only when this whole string is in ``DISCLAIMER_ALLOW``.
    Comments are not text. ``template`` / ``script`` / ``style`` are already gone.
    """
    nodes = []
    for text in _prepared(html, lang).find_all(string=True):
        if isinstance(text, Comment):
            continue
        normalized = " ".join(str(text).split())
        if normalized:
            nodes.append(normalized)
    return nodes


def forbidden_hits(html, lang):
    """Return (pattern, sample) hits in visible text nodes and attribute values.

    A text node is skipped only when its whole normalized text equals an
    allow-listed sentence. Attribute values are not text nodes and are never
    exempt. The line-211 method sentence has to be present as its own node;
    the chart sentence is hidden once expiry removes ``.pbx-current``.
    """
    nodes = _normalized_text_nodes(html, lang)
    attrs = attribute_values(html, lang)
    found = []
    for pattern_lang, pattern in FORBIDDEN:
        if pattern_lang != lang:
            continue
        for node in nodes:
            if node in DISCLAIMER_ALLOW:
                continue
            match = re.search(pattern, node, re.I)
            if not match:
                continue
            sample = node[max(0, match.start() - 28):match.end() + 28]
            found.append((pattern, f"text: {sample}"))
        match = re.search(pattern, attrs, re.I)
        if not match:
            continue
        sample = attrs[max(0, match.start() - 28):match.end() + 28].replace("\n", " ")
        found.append((pattern, f"attribute: {sample}"))
    if _METHOD_DISCLAIMER[lang] not in nodes:
        found.append((
            "disclaimer",
            f"forecast disclaimer missing from {lang} text: {_METHOD_DISCLAIMER[lang]!r}",
        ))
    return found


def assert_forecast_blank(html):
    """N1. Value cells are only U+2014, and the forecast element has no digit."""
    soup = BeautifulSoup(html, "html.parser")
    forecast = soup.select_one(FORECAST_SELECTOR)
    assert forecast is not None, "forecast block missing"
    assert forecast.get("data-forecast-status") == FORECAST_STATUS
    cells = [node.get_text(strip=True) for node in forecast.select(".rrp-forecast-row strong")]
    assert cells == [EM_DASH, EM_DASH], cells
    visible = forecast.get_text("", strip=False)
    digits = sorted({ch for ch in visible if ch.isdigit()})
    assert not digits, f"digit in .rrp-forecast: {digits!r} in {visible!r}"
    for el in [forecast, *forecast.find_all(True)]:
        for key, value in el.attrs.items():
            if isinstance(value, list):
                value = " ".join(value)
            digit = next((ch for ch in str(value) if ch.isdigit()), None)
            assert digit is None, f"digit in forecast attribute {key}={value!r}"


def assert_estimate_label(html, lang):
    """N2. The template's own unavailable label, in that language."""
    text = language_text(html, lang)
    assert ESTIMATE_LABEL[lang] in text, text[:240]


def assert_no_downside_percent(html):
    """N4. No percent figure in the further-downside block.

    Ancestors of ``.rrp-forecast`` also contain the observed-path chart, whose
    percents are history. A percent inside the forecast block, or in any other
    element that itself mentions further downside, still fails.
    """
    soup = BeautifulSoup(html, "html.parser")
    forecast = soup.select_one(FORECAST_SELECTOR)
    assert forecast is not None
    for el in soup.find_all(True):
        text = el.get_text(" ", strip=True)
        if DOWNSIDE_PHRASE.search(text) is None:
            continue
        if el is not forecast and el.select_one(FORECAST_SELECTOR) is not None:
            continue
        figure = PERCENT_FIGURE.search(text)
        if figure:
            raise AssertionError(
                f"percent figure {figure.group()!r} beside further downside: {text[:200]!r}"
            )


def assert_no_forbidden(html, lang):
    hits = forbidden_hits(html, lang)
    if hits:
        raise AssertionError("; ".join(f"{pattern}: {sample}" for pattern, sample in hits))


def test_sweep_covers_every_presenter_phase():
    rendered = {PHASE_OF[state] for state, _market in CASES}
    assert set(PHASES) <= rendered
    assert "unavailable" in rendered


def test_whitelist_sentences_are_the_template_strings():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "templates" / "_risk_radar_pullback_depth.html.j2").read_text()
    assert DISCLAIMER_ALLOW
    for sentence in DISCLAIMER_ALLOW:
        assert sentence == " ".join(sentence.split())
        assert sentence in source
    assert _METHOD_DISCLAIMER["en"] in DISCLAIMER_ALLOW
    assert _METHOD_DISCLAIMER["zh"] in DISCLAIMER_ALLOW
    assert ESTIMATE_LABEL["en"] in source and ESTIMATE_LABEL["zh"] in source


@pytest.mark.parametrize("state,market", CASES, ids=[f"{s}-{m}" for s, m in CASES])
def test_rendered_phase(state, market):
    html = fragment_html(state, market)
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("section.rrp")
    assert section.get("data-pb-phase") == PHASE_OF[state]
    if state == "expired":
        assert "pb-expired" in section.get("class", [])
        assert "Price update needed" in language_text(html, "en")
        assert "Awaiting a newer close" in language_text(html, "en")
        assert "价格数据待更新" in language_text(html, "zh")
        assert "等待更新的收盘价" in language_text(html, "zh")


@pytest.mark.parametrize("state,market,lang", SWEEP)
def test_forecast_cells_are_blank(state, market, lang):
    assert_forecast_blank(fragment_html(state, market))


@pytest.mark.parametrize("state,market,lang", SWEEP)
def test_estimate_unavailable_label(state, market, lang):
    assert_estimate_label(fragment_html(state, market), lang)


@pytest.mark.parametrize("state,market,lang", SWEEP)
def test_no_percent_figure_on_further_downside(state, market, lang):
    assert_no_downside_percent(fragment_html(state, market))


@pytest.mark.parametrize("state,market,lang", SWEEP)
def test_no_forbidden_forecast_language(state, market, lang):
    assert_no_forbidden(fragment_html(state, market), lang)


@pytest.mark.parametrize("state", DIALOG_STATES)
@pytest.mark.parametrize("market", ["us", "cn"])
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_dialog_section_keeps_the_invariant(state, market, lang):
    html = dialog_section_html(state, market)
    assert_forecast_blank(html)
    assert_estimate_label(html, lang)
    assert_no_downside_percent(html)
    assert_no_forbidden(html, lang)


def test_detector_catches_a_digit_in_the_forecast_cell():
    html = fragment_html("stale", "us")
    assert_forecast_blank(html)
    poisoned = html.replace("<strong>—</strong>", "<strong>12%</strong>", 1)
    with pytest.raises(AssertionError, match="12"):
        assert_forecast_blank(poisoned)


def test_detector_catches_a_missing_estimate_label():
    html = fragment_html("stale", "us")
    assert_estimate_label(html, "en")
    poisoned = html.replace("Estimate unavailable", "Estimate pending", 1)
    with pytest.raises(AssertionError, match="Estimate unavailable"):
        assert_estimate_label(poisoned, "en")


def test_detector_catches_probability_word():
    html = fragment_html("stale", "us")
    assert_no_forbidden(html, "en")
    poisoned = html.replace(
        "Estimate unavailable",
        "Estimate unavailable — a 40% probability of a further drop",
        1,
    )
    with pytest.raises(AssertionError, match="probability"):
        assert_no_forbidden(poisoned, "en")


def test_detector_catches_a_percent_on_further_downside():
    html = fragment_html("stale", "us")
    assert_no_downside_percent(html)
    poisoned = html.replace("FURTHER DOWNSIDE", "FURTHER DOWNSIDE 12%", 1)
    with pytest.raises(AssertionError, match="%"):
        assert_no_downside_percent(poisoned)


def test_detector_catches_rewritten_recovery_odds():
    """'Not recovery odds' is exempt. A forecast phrasing of that node is not."""
    html = fragment_html("worsening", "us")
    assert_no_forbidden(html, "en")
    poisoned = html.replace("Not recovery odds", "Recovery odds 60%", 1)
    assert "Recovery odds 60%" in poisoned and "Not recovery odds" not in poisoned
    with pytest.raises(AssertionError, match="Recovery odds 60%"):
        assert_no_forbidden(poisoned, "en")


def test_detector_catches_rewritten_recovery_probability():
    """'并非修复概率' is exempt. '修复概率较高' is not."""
    html = fragment_html("worsening", "us")
    assert_no_forbidden(html, "zh")
    poisoned = html.replace("并非修复概率", "修复概率较高", 1)
    assert "修复概率较高" in poisoned and "并非修复概率" not in poisoned
    with pytest.raises(AssertionError, match="修复概率较高"):
        assert_no_forbidden(poisoned, "zh")


def test_detector_catches_method_sentence_without_negation():
    """The method sentence is exempt only as the exact denial, with 并非."""
    html = fragment_html("stale", "us")
    assert_no_forbidden(html, "zh")
    original = _METHOD_DISCLAIMER["zh"]
    mutated = original.replace("并非", "", 1)
    assert mutated not in DISCLAIMER_ALLOW and "并非" not in mutated
    poisoned = html.replace(original, mutated, 1)
    assert mutated in poisoned and original not in poisoned
    with pytest.raises(AssertionError, match="回撤概率对剩余"):
        assert_no_forbidden(poisoned, "zh")
