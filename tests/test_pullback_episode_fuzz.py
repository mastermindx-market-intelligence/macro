"""Seeded episode fuzz: observe → present → render, one synthetic series per seed.

The US builder (scripts/build_site.py ``_us_pullback_risk_popup``) binds
``lib.pullback_observation.observe`` into ``us_pullback_observation.snapshot``
and then calls ``present``. This file does the same with a synthetic reader
(no market-data feed): ``observe``, ``episode_window``, ``present``, and the
fragment's ``assess`` macro, then renders ``detail`` through the real Jinja
loader the way ``tests/test_risk_radar_pullback_depth_template.py`` does.

Series are synthetic. ``random.Random(k)`` only — no Hypothesis. Prices are
not quotes. The session clock is the NYSE rule calendar the US snapshot uses.

I1: the forecast block prints no figure (em dashes only, no digit-percent
token), and it may name probabilities or odds only in a sentence that says
they are not a forecast. The "Why no estimate?" disclaimer does exactly that
for the Risk Radar's existing pullback probabilities, so the rule is checked
per sentence, never as a bare word ban.
"""
from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from lib import nyse_calendar
from lib.pullback_depth import MIN_CHART_POINTS, LicensedCloses, episode_window
from lib.pullback_observation import PATH_MAX_CLOSES, RULES, observe
from lib.us_pullback_observation import present as present_popup
from lib.us_pullback_observation import snapshot

ROOT = Path(__file__).resolve().parents[1]
_ENV = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
_DETAIL = (
    '{% import "_risk_radar_pullback_depth.html.j2" as p %}'
    "{{ p.detail(market, v) }}"
)
_ASSESS = (
    '{% import "_risk_radar_pullback_depth.html.j2" as p %}'
    "{% set ns = namespace(current=false, low_ok=false) %}"
    '{{ p.assess("us", v, ns) }}'
    '{{ "1" if ns.current else "0" }}'
)

# Display copy the fragment shows for the presenter's phases, plus the
# unqualified state the same fragment substitutes. Trail rows use the six
# phases; the heading may also be the unqualified pair.
_PHASE_LABELS = {
    "monitoring": ("Pullback monitor", "回撤观察"),
    "developing": ("Pullback developing", "回撤形成中"),
    "underway": ("Pullback underway", "回撤进行中"),
    "stabilizing": ("Stabilization watch", "止跌观察"),
    "recovering": ("Watching price repair", "价格修复观察"),
    "repaired": ("Pullback repaired", "本轮回撤已修复"),
    "unavailable": ("Price update needed", "价格数据待更新"),
}
_TRAIL_LABELS = {
    pair for phase, pair in _PHASE_LABELS.items() if phase != "unavailable"
}
_WITHHELD_EN = {
    "short": "Too few closes since the reference high to draw a chart yet.",
    "uncovered": (
        "Chart not shown: the closing history on record does not fully "
        "support these figures."
    ),
}
_MINUS = "\u2212"
_EM = "\u2014"
_DIGIT_PCT = re.compile(r"\d+(?:\.\d+)?%")
_EXPIRED_EN = "Price update needed"
_EXPIRED_ZH = "价格数据待更新"

# One fixed session so every series' last close is the snapshot's expected
# session and every valid_until stamp is that session's successor settle.
_END = date(2026, 6, 12)
_NOW = datetime.combine(_END, time(18, 0), tzinfo=nyse_calendar.ET)

# 15 shapes × repeats. Sized so the module stays under 20s on this host.
_SCENARIOS = (
    "calm",
    "shock",
    "slow_confirm",
    "developing",
    "deepening",
    "stabilizing",
    "recovering_above",
    "repaired",
    "rebreak",
    "gaps",
    "flat",
    "tie_low",
    "short",
    "long_cap",
    "young",
)
_REPEATS = 3
N = len(_SCENARIOS) * _REPEATS

# Probability language, and the two ways a sentence may disclaim it.
_PROB = re.compile(r"probabilit|odds|概率", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.。])\s*")


def _disclaims(sentence):
    return bool(re.search(r"\bnot a forecast\b", sentence, re.IGNORECASE)) or (
        "并非" in sentence and "预测" in sentence)


def _fail(k, kind, rows, detail):
    raise AssertionError(f"seed {k} ({kind}): {detail}; tail={rows[-8:]}")


def _days(count, end=_END):
    found = []
    cursor = end
    while len(found) < count:
        if nyse_calendar.is_session(cursor):
            found.append(cursor)
        cursor -= timedelta(days=1)
        if (end - cursor).days > count * 4 + 40:
            raise RuntimeError(f"no {count} sessions on or before {end}")
    found.reverse()
    return found


def _zip(values, days=None):
    days = _days(len(values)) if days is None else days
    if len(days) != len(values):
        raise RuntimeError(f"days {len(days)} != values {len(values)}")
    return [(day.isoformat(), float(value)) for day, value in zip(days, values)]


def _cents(value):
    return round(float(value), 2)


def _baseline(rng):
    # Flat 100s: the reference high stays 100 until the tail moves it, and a
    # flat run is part of every long enough series.
    return [100.0] * rng.randint(72, 88)


def _off(pct):
    """A close ``pct`` percent under 100, kept off the 2% and 5% boundaries."""
    return _cents(100.0 * (1.0 - pct))


def _shock_tail(rng):
    # One close at least 5.5% under the flat high, then enough follow-through
    # that the window from that high has MIN_CHART_POINTS sessions.
    shock = _off(rng.uniform(0.055, 0.09))
    follow = []
    for _ in range(MIN_CHART_POINTS - 2):
        follow.append(_cents(shock * (1.0 + rng.uniform(-0.01, 0.008))))
    return [shock, *follow]


def _values(kind, rng):
    if kind == "calm":
        # Under 1.2%: still monitoring, and the peak is not the last bar, so
        # the window is long enough to draw.
        dips = [_off(rng.uniform(0.002, 0.012)) for _ in range(MIN_CHART_POINTS - 1)]
        return _baseline(rng) + dips
    if kind == "shock":
        return _baseline(rng) + _shock_tail(rng)
    if kind == "slow_confirm":
        # Two closes between 2.5% and 4.8%: confirmation without a 5% shock.
        depths = [rng.uniform(0.025, 0.048) for _ in range(MIN_CHART_POINTS - 1)]
        return _baseline(rng) + [_off(depth) for depth in depths]
    if kind == "developing":
        mild = [_off(rng.uniform(0.002, 0.012)) for _ in range(MIN_CHART_POINTS - 2)]
        return _baseline(rng) + mild + [_off(rng.uniform(0.025, 0.045))]
    if kind == "deepening":
        price = _off(rng.uniform(0.055, 0.07))
        tail = [price]
        for _ in range(MIN_CHART_POINTS - 2):
            price = _cents(price * (1.0 - rng.uniform(0.02, 0.05)))
            tail.append(price)
        return _baseline(rng) + tail
    if kind == "stabilizing":
        # Bounce stays under the frozen high. The last close clears the 5-close
        # average and three closes hold above the low, which is this owner's
        # stabilization rule.
        low = rng.uniform(88.0, 91.0)
        shock = rng.uniform(max(low + 0.5, 93.0), 95.0)
        rises = [low + 0.5, low + 1.5, low + 3.0]
        return _baseline(rng) + [_cents(shock), _cents(low), *[_cents(v) for v in rises]]
    if kind == "recovering_above":
        shock = _off(rng.uniform(0.055, 0.08))
        low = _cents(shock * (1.0 - rng.uniform(0.03, 0.08)))
        above = _cents(100.0 + rng.uniform(0.5, 2.0))
        return _baseline(rng) + [shock, low, above]
    if kind == "repaired":
        shock = _off(rng.uniform(0.055, 0.08))
        low = _cents(shock * (1.0 - rng.uniform(0.03, 0.08)))
        if rng.random() < 0.5:
            second = 100.0  # back on the frozen high: the end tag rounds to 0.0
        else:
            second = _cents(100.0 + rng.uniform(0.5, 2.0))
        return _baseline(rng) + [shock, low, 100.0, second]
    if kind == "rebreak":
        shock = _off(rng.uniform(0.055, 0.08))
        low = _cents(shock * (1.0 - rng.uniform(0.03, 0.08)))
        repaired_at = _cents(100.0 + rng.uniform(0.5, 2.0))
        mild = _cents(repaired_at * (1.0 - rng.uniform(0.003, 0.01)))
        pending = _cents(repaired_at * (1.0 - rng.uniform(0.025, 0.04)))
        broke = _cents(repaired_at * (1.0 - rng.uniform(0.06, 0.10)))
        return _baseline(rng) + [shock, low, 100.0, repaired_at, mild, pending, broke]
    if kind == "gaps":
        return _baseline(rng) + _shock_tail(rng)
    if kind == "flat":
        return [100.0] * rng.randint(70, 100)
    if kind == "tie_low":
        shock = _off(rng.uniform(0.055, 0.07))
        low = _cents(shock * (1.0 - rng.uniform(0.04, 0.10)))
        return _baseline(rng) + [shock] + [low] * rng.randint(3, 5)
    if kind == "short":
        count = rng.randint(1, RULES.reference_closes - 1)
        return [_cents(100.0 + rng.uniform(-1.0, 1.0)) for _ in range(count)]
    if kind == "long_cap":
        # Peak on the first close, then a strict new low every session, past
        # the 252-close path cap so the retained high ages out of the window.
        extra = rng.randint(8, 24)
        price = 110.0
        values = [120.0, price]
        for _ in range(PATH_MAX_CLOSES + extra - 1):
            stepped = price * (1.0 - rng.uniform(0.001, 0.003))
            price = min(stepped, price - 0.02)
            values.append(round(price, 4))
        return values
    if kind == "young":
        # The last close is a new high, so the window is that single session.
        base = [100.0] * rng.randint(70, 90)
        return base + [_cents(100.0 + rng.uniform(0.3, 2.0))]
    raise RuntimeError(kind)


def series_for(k):
    """Synthetic closes for seed ``k``. Deterministic given ``k`` alone."""
    rng = random.Random(k)
    kind = _SCENARIOS[k % len(_SCENARIOS)]
    values = _values(kind, rng)
    if kind == "gaps":
        days = _days(len(values))
        drop = set(range(20, 55, 5))
        keep = [i for i in range(len(values)) if i not in drop]
        rows = _zip([values[i] for i in keep], [days[i] for i in keep])
    else:
        rows = _zip(values)
    if any(price <= 0 for _, price in rows):
        raise RuntimeError(f"seed {k} produced a non-positive close")
    return kind, rows


def _feed(rows):
    """The US builder's public path, with the synthetic series as the reader."""
    def read(_expected):
        return LicensedCloses(rows=list(rows))

    observation = snapshot(now=_NOW, read=read, observer=observe)
    window = episode_window(observation)
    view = present_popup(observation)
    qualified = _ENV.from_string(_ASSESS).render(v=view).strip()[-1] == "1"
    html = _ENV.from_string(_DETAIL).render(market="us", v=view)
    return observation, window, view, qualified, html


def _forecast(soup):
    block = soup.select_one(".rrp-forecast")
    return block


def assert_i1_values(soup, k, kind, rows):
    """I1 value clause: the forecast block's figures are em dashes only."""
    block = _forecast(soup)
    if block is None:
        _fail(k, kind, rows, "I1: .rrp-forecast block is missing")
    strongs = [node.get_text(strip=True) for node in block.select("strong")]
    blob = block.get_text(" ", strip=True)
    if not strongs or set(strongs) != {_EM}:
        _fail(k, kind, rows, f"I1: forecast values {strongs!r}, expected only {_EM!r}")
    if _DIGIT_PCT.search(blob):
        _fail(k, kind, rows, f"I1: digit-% token in forecast: {blob!r}")
    if block.get("data-forecast-status") != "unavailable":
        _fail(k, kind, rows, "I1: forecast status is not unavailable")


def assert_i1(soup, k, kind, rows):
    """Full I1: the value clause, then every sentence that names a probability
    or odds must disclaim it as a forecast and carry no digit. Returns the
    number of disclaiming sentences seen."""
    assert_i1_values(soup, k, kind, rows)
    seen = 0
    for node in _forecast(soup).select(".l-en, .l-zh"):
        for sentence in _SENTENCE.split(node.get_text()):
            if not _PROB.search(sentence):
                continue
            if re.search(r"\d", sentence):
                _fail(k, kind, rows, f"I1: a number next to probability language: {sentence!r}")
            if not _disclaims(sentence):
                _fail(k, kind, rows, f"I1: probability language not disclaimed: {sentence!r}")
            seen += 1
    return seen


def _split_pct(text):
    body = text.strip()
    if not body.endswith("%"):
        return None
    body = body[:-1]
    if body.startswith("+"):
        return "+", body[1:]
    if body.startswith(_MINUS):
        return _MINUS, body[1:]
    if body.startswith("-"):
        return "-", body[1:]
    return "", body


def _expected_signed(value):
    rounded = round(float(value), 1)
    if rounded == 0:
        rounded = 0.0
    if rounded > 0:
        return "+", f"{rounded:.1f}"
    if rounded < 0:
        return _MINUS, f"{abs(rounded):.1f}"
    return "", "0.0"


def assert_i2(soup, obs, view, k, kind, rows):
    """I2: drawn end tag matches the signed tenth from the frozen high."""
    drawn = bool(view.get("detail_chart_html")) and view.get("detail_path")
    tag = soup.select_one(".ilx-tag")
    if not drawn:
        if tag is not None:
            _fail(k, kind, rows, f"I2: end tag present while chart withheld: {tag.get_text()!r}")
        return
    if tag is None:
        _fail(k, kind, rows, "I2: drawn chart has no end tag")
    close, peak = obs.get("close"), obs.get("peak_close")
    if not isinstance(close, float) or not isinstance(peak, float) or peak <= 0:
        _fail(k, kind, rows, f"I2: cannot measure drawdown from close={close!r} peak={peak!r}")
    ratio = 100.0 * (close / peak - 1.0)
    got = _split_pct(tag.get_text(strip=True))
    want_sign, want_num = _expected_signed(ratio)
    if got is None or got[0] != want_sign or got[1] != want_num:
        _fail(
            k, kind, rows,
            f"I2: end tag {tag.get_text(strip=True)!r}, expected sign {want_sign!r} "
            f"number {want_num} from round({ratio}, 1)",
        )
    if want_sign == "+" and got[0] != "+":
        _fail(k, kind, rows, "I2: positive tenth missing '+'")
    if want_sign == _MINUS and ("-" in tag.get_text() or got[0] != _MINUS):
        _fail(k, kind, rows, "I2: negative tenth must use U+2212 and not ASCII '-'")
    if want_sign == "" and (got[0] != "" or got[1] != "0.0"):
        _fail(k, kind, rows, f"I2: zero tenth must be unsigned 0.0%, got {got!r}")


def assert_i3(soup, html, view, k, kind, rows):
    """I3: each history percent uses the same sign rule; no signed zero."""
    if "-0.0%" in html or f"{_MINUS}0.0%" in html:
        _fail(k, kind, rows, "I3: signed zero percent in the fragment")
    path = view.get("detail_path")
    cells = soup.select(".rrp-history tbody tr")
    if not path:
        if cells:
            _fail(k, kind, rows, "I3: history rows rendered without a presenter window")
        return
    if len(cells) != len(path["vals"]):
        _fail(k, kind, rows, f"I3: {len(cells)} history rows for {len(path['vals'])} window points")
    for cell, value in zip(cells, path["vals"]):
        text = cell.select("td")[1].get_text(strip=True)
        got = _split_pct(text)
        want_sign, want_num = _expected_signed(value)
        if got is None or got != (want_sign, want_num):
            _fail(
                k, kind, rows,
                f"I3: history cell {text!r} for value {value}, expected {want_sign}{want_num}%",
            )


def assert_i4(soup, obs, window, view, k, kind, rows):
    """I4: a drawn window holds the peak and the low; a withheld chart says why."""
    slot = soup.select(".rrp-chart svg")
    reason = view.get("detail_withheld")
    drawn = bool(view.get("detail_chart_html")) and view.get("detail_path")
    if drawn:
        if not slot:
            _fail(k, kind, rows, "I4: presenter drew a chart but the slot has no svg")
        dates = list(view["detail_path"]["dates"])
        if window is None or list(window["dates"]) != dates:
            _fail(k, kind, rows, "I4: drawn path is not the episode window")
        peak = obs.get("peak_session")
        if peak not in dates:
            _fail(k, kind, rows, f"I4: peak session {peak} missing from drawn window")
        low = obs.get("low_session")
        if low is not None and low not in dates:
            _fail(k, kind, rows, f"I4: low session {low} missing from drawn window")
        return
    if slot:
        _fail(k, kind, rows, "I4: svg inside the pullback chart slot while chart is withheld")
    if reason is None:
        return
    saying = _WITHHELD_EN.get(reason)
    if saying is None:
        _fail(k, kind, rows, f"I4: unknown detail_withheld {reason!r}")
    text = soup.select_one(".rrp-evidence").get_text(" ", strip=True)
    if saying not in text:
        _fail(k, kind, rows, f"I4: withheld {reason!r} but fragment does not say {saying!r}")
    for other, sentence in _WITHHELD_EN.items():
        if other != reason and sentence in text:
            _fail(k, kind, rows, f"I4: withheld {reason!r} but also says the {other} reason")


def assert_i5_receipt(soup, rows, k, kind):
    """I5 receipt: the dated close stamp is the series' last session."""
    last = date.fromisoformat(rows[-1][0])
    section = soup.select_one("section.rrp")
    if section is None:
        _fail(k, kind, rows, "I5: fragment has no pullback section")
    raw = section.get("data-pb-asof") or ""
    try:
        stamped = date.fromisoformat(raw)
    except ValueError:
        _fail(k, kind, rows, f"I5: data-pb-asof {raw!r} is not an ISO date")
    if stamped != last:
        _fail(k, kind, rows, f"I5: receipt {stamped.isoformat()} != last session {last.isoformat()}")
    times = [node.get("datetime") for node in soup.select(".rrp-stamp time")]
    if raw not in times:
        _fail(k, kind, rows, f"I5: dated receipt time is missing; times={times!r}")
    return section.get("data-pb-valid-until") or ""


def assert_i6(soup, obs, view, qualified, k, kind, rows):
    """I6: shown phase copy is the presenter's vocabulary; no underway above the high."""
    section = soup.select_one("section.rrp")
    phase = section.get("data-pb-phase")
    if phase not in _PHASE_LABELS:
        _fail(k, kind, rows, f"I6: shown phase {phase!r} is outside the presenter vocabulary")
    if view.get("phase") not in _PHASE_LABELS:
        _fail(k, kind, rows, f"I6: presenter phase {view.get('phase')!r} is outside its vocabulary")
    heading = soup.select_one(".pbx-heading h2")
    shown = (
        heading.select_one(".l-en").get_text(),
        heading.select_one(".l-zh").get_text(),
    )
    if shown != _PHASE_LABELS[phase]:
        _fail(k, kind, rows, f"I6: heading {shown!r} does not match phase {phase}")
    for item in soup.select("ol.rrp-phase-trail li"):
        pair = (
            item.select_one(".l-en").get_text(),
            item.select_one(".l-zh").get_text(),
        )
        if pair not in _TRAIL_LABELS:
            _fail(k, kind, rows, f"I6: trail label {pair!r} is outside the presenter vocabulary")
    if qualified and phase != view.get("phase"):
        _fail(k, kind, rows, f"I6: assess qualified the view but fragment shows {phase}")
    if not qualified and phase != "unavailable":
        _fail(k, kind, rows, f"I6: assess rejected the view but fragment shows {phase}")
    close, peak = obs.get("close"), obs.get("peak_close")
    if isinstance(close, float) and isinstance(peak, float) and close >= peak:
        if phase == "underway" or shown[0] == "Pullback underway":
            _fail(
                k, kind, rows,
                f"I6: UNDERWAY view shown with close {close} >= frozen peak {peak}",
            )


def assert_i7(view, html, k, kind, rows):
    """I7: a second render of the same view is the same bytes."""
    again = _ENV.from_string(_DETAIL).render(market="us", v=view)
    if again != html or again.encode() != html.encode():
        _fail(k, kind, rows, "I7: second render differs")


def _expiry_owner(sections, now_ms):
    """Run the shipped expiry script the existing expiry test executes."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node is required to apply the shipped expiry owner")
    script = r"""
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
let now = payload.now;
Date.now = () => now;
function section(s) {
  const attrs = {'data-pb-valid-until': s.vu, 'data-pb-phase': s.phase};
  const classes = new Set(['rrp', 'pbx']);
  const en = {textContent: s.en}, zh = {textContent: s.zh};
  const heading = {querySelector: sel => ({'.l-en': en, '.l-zh': zh})[sel] || null};
  return {attrs, classes, en, zh,
    getAttribute: k => (k in attrs ? attrs[k] : null),
    setAttribute: (k, v) => { attrs[k] = String(v); },
    classList: {add: c => classes.add(c)},
    querySelector: sel => (sel === '.pbx-heading h2' ? heading : null)};
}
const sections = payload.sections.map(section);
const document = {
  readyState: 'complete', hidden: false,
  querySelectorAll() { return sections; },
  addEventListener() {},
  createElement() { return {className: '', innerHTML: ''}; },
  activeElement: null,
};
const window = {setTimeout() { return 1; }, clearTimeout() {}, addEventListener() {}};
new Function('window', 'document', payload.src)(window, document);
process.stdout.write(JSON.stringify(sections.map(s => ({
  expired: s.classes.has('pb-expired'),
  phase: s.attrs['data-pb-phase'],
  en: s.en.textContent,
  zh: s.zh.textContent,
}))));
"""
    payload = json.dumps({
        "src": (ROOT / "templates" / "_risk_radar_pullback_depth.js.j2").read_text(),
        "now": now_ms,
        "sections": sections,
    })
    result = subprocess.run(
        [node, "-e", script], input=payload, text=True, capture_output=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def _epoch_ms(stamp):
    return int(datetime.fromisoformat(stamp).timestamp() * 1000)


def assert_i5_expired(pending):
    """I5: a now past valid_until applies the shipped expired state."""
    if not pending:
        raise AssertionError("I5: no rendered sections to expire")
    sections = [
        {
            "vu": item["vu"],
            "phase": item["phase"],
            "en": item["en"],
            "zh": item["zh"],
        }
        for item in pending
    ]
    latest = max(datetime.fromisoformat(item["vu"]) for item in pending)
    past = _expiry_owner(sections, _epoch_ms((latest + timedelta(seconds=1)).isoformat()))
    for item, got in zip(pending, past):
        if not (
            got["expired"] is True
            and got["phase"] == "unavailable"
            and got["en"] == _EXPIRED_EN
            and got["zh"] == _EXPIRED_ZH
        ):
            _fail(
                item["k"], item["kind"], item["rows"],
                f"I5: injected now past {item['vu']} produced {got!r}, "
                f"expected pb-expired / unavailable / {_EXPIRED_EN!r} / {_EXPIRED_ZH!r}",
            )
    earliest = min(datetime.fromisoformat(item["vu"]) for item in pending)
    before = _expiry_owner(
        sections, _epoch_ms((earliest - timedelta(hours=1)).isoformat()),
    )
    for item, got in zip(pending, before):
        if got["expired"] or got["phase"] != item["phase"] or got["en"] != item["en"]:
            _fail(
                item["k"], item["kind"], item["rows"],
                f"I5: injected now before {item['vu']} expired the section: {got!r}",
            )


def _walk_checks(kind, obs, view, rows, k):
    """The generator really walked the situation this seed claims to build."""
    phase = obs.get("phase")
    withheld = view.get("detail_withheld")
    if kind == "calm" and phase != "monitoring":
        _fail(k, kind, rows, f"generator: calm landed on {phase}")
    if kind == "shock" and phase != "underway":
        _fail(k, kind, rows, f"generator: shock landed on {phase}")
    if kind == "slow_confirm" and phase != "underway":
        _fail(k, kind, rows, f"generator: slow confirmation landed on {phase}")
    if kind == "developing" and phase != "developing":
        _fail(k, kind, rows, f"generator: developing landed on {phase}")
    if kind == "deepening" and phase != "underway":
        _fail(k, kind, rows, f"generator: deepening landed on {phase}")
    if kind == "stabilizing" and phase != "stabilizing":
        _fail(k, kind, rows, f"generator: stabilizing landed on {phase}")
    if kind == "recovering_above":
        if phase != "recovering" or not (obs["close"] > obs["peak_close"]):
            _fail(k, kind, rows, f"generator: recovering-above landed on {phase} close={obs.get('close')}")
    if kind == "repaired" and phase != "repaired":
        _fail(k, kind, rows, f"generator: repaired landed on {phase}")
    if kind == "rebreak":
        if phase != "underway" or obs["close"] >= obs["peak_close"] or not obs.get("reference_reset_session"):
            _fail(k, kind, rows, f"generator: rebreak landed on {phase}")
    if kind == "gaps" and not (obs.get("history_gap_count") or 0) > 0:
        _fail(k, kind, rows, "generator: gap series has no missing session")
    if kind == "flat" and phase != "monitoring":
        _fail(k, kind, rows, f"generator: flat run landed on {phase}")
    if kind == "tie_low":
        low = obs.get("low_close")
        ties = sum(1 for _, price in rows if price == low)
        if phase != "underway" or ties < 2:
            _fail(k, kind, rows, f"generator: tie at the low landed on {phase} ties={ties}")
    if kind == "short" and (len(rows) >= RULES.reference_closes or obs.get("available") is not False):
        _fail(k, kind, rows, "generator: short series was treated as current")
    if kind == "long_cap":
        dates = (obs.get("price_path") or {}).get("dates") or []
        if len(rows) <= PATH_MAX_CLOSES or obs.get("peak_session") in dates or withheld != "uncovered":
            _fail(k, kind, rows, f"generator: long series did not age the peak out ({withheld})")
    if kind == "young" and (phase != "monitoring" or withheld != "short"):
        _fail(k, kind, rows, f"generator: young window landed on {phase} withheld={withheld}")


def test_i1_probability_language_appears_only_as_a_disclaimer():
    """One close still renders the forecast block. Its only probability
    language is the English and Chinese disclaimer sentence."""
    rows = [("2026-06-12", 100.0)]
    _obs, _window, _view, _qualified, html = _feed(rows)
    assert assert_i1(BeautifulSoup(html, "html.parser"), k=0, kind="minimal", rows=rows) == 2


@pytest.mark.parametrize("en, zh", [
    ("Probability of a further decline: —", "进一步下跌概率：—"),
    ("Existing pullback probabilities (35) are not a forecast.", "现有回撤概率（35）并非预测。"),
    ("Odds of a new low are elevated.", "创新低的可能性较高。"),
])
def test_i1_rejects_probability_language_that_is_not_a_disclaimer(en, zh):
    """The sentence rule bites: a bare probability label, a disclaimer that
    carries a number, and an odds claim each fail I1."""
    html = (
        '<div class="rrp-forecast" data-forecast-status="unavailable">'
        f'<p><span class="l-en">{en}</span><span class="l-zh">{zh}</span></p>'
        f"<strong>{_EM}</strong></div>"
    )
    with pytest.raises(AssertionError, match="I1"):
        assert_i1(BeautifulSoup(html, "html.parser"), k=0, kind="planted", rows=[("2026-06-12", 100.0)])


def test_seeded_episode_fuzz_across_owner_presenter_and_fragment():
    import time

    started = time.perf_counter()
    phases = set()
    withheld = set()
    drew = 0
    saw_gap = False
    saw_tie = False
    saw_above = False
    shortest = PATH_MAX_CLOSES
    longest = 0
    pending = []
    for k in range(N):
        kind, rows = series_for(k)
        obs, window, view, qualified, html = _feed(rows)
        soup = BeautifulSoup(html, "html.parser")
        _walk_checks(kind, obs, view, rows, k)
        assert_i1(soup, k, kind, rows)
        assert_i2(soup, obs, view, k, kind, rows)
        assert_i3(soup, html, view, k, kind, rows)
        assert_i4(soup, obs, window, view, k, kind, rows)
        vu = assert_i5_receipt(soup, rows, k, kind)
        assert_i6(soup, obs, view, qualified, k, kind, rows)
        assert_i7(view, html, k, kind, rows)
        phases.add(obs.get("phase"))
        if view.get("detail_withheld"):
            withheld.add(view["detail_withheld"])
        elif view.get("detail_chart_html"):
            drew += 1
        saw_gap = saw_gap or (obs.get("history_gap_count") or 0) > 0
        low = obs.get("low_close")
        saw_tie = saw_tie or (
            isinstance(low, float) and sum(1 for _, price in rows if price == low) >= 2
        )
        close, peak = obs.get("close"), obs.get("peak_close")
        saw_above = saw_above or (
            isinstance(close, float) and isinstance(peak, float) and close > peak
            and obs.get("phase") != "underway"
        )
        shortest = min(shortest, len(rows))
        longest = max(longest, len(rows))
        heading = soup.select_one(".pbx-heading h2")
        pending.append({
            "k": k,
            "kind": kind,
            "rows": rows,
            "vu": vu,
            "phase": soup.select_one("section.rrp").get("data-pb-phase"),
            "en": heading.select_one(".l-en").get_text(),
            "zh": heading.select_one(".l-zh").get_text(),
        })
    assert_i5_expired(pending)
    missing = {
        "monitoring", "developing", "underway", "stabilizing",
        "recovering", "repaired", "unavailable",
    } - phases
    if missing:
        raise AssertionError(f"generator missed owner phases {sorted(missing)}; saw {sorted(phases)}")
    if withheld != {"short", "uncovered"} or drew < 1:
        raise AssertionError(f"generator chart states withheld={withheld} drew={drew}")
    if not saw_gap or not saw_tie or not saw_above:
        raise AssertionError(
            f"generator missed a situation gap={saw_gap} tie={saw_tie} above={saw_above}"
        )
    if shortest >= RULES.reference_closes or longest <= PATH_MAX_CLOSES:
        raise AssertionError(f"generator length range {shortest}..{longest}")
    elapsed = time.perf_counter() - started
    print(f"episode fuzz: N={N} elapsed={elapsed:.2f}s")
    assert elapsed < 20.0, f"N={N} took {elapsed:.2f}s"
