"""Seeded China-dialog fuzz: snapshot → present → shared risk dialog.

Each seed builds a synthetic close series on the China session calendar
that ``lib.cn_pullback_observation.snapshot`` uses. ``snapshot(read=...)``
receives a ``LicensedCloses`` reader and the shared observer, ``present()``
shapes the read model, and ``templates/_risk_radar_dlg.html.j2`` is rendered
with the consumers' plain ``Environment(autoescape=False)``.

Price shapes come from ``tests.test_pullback_episode_fuzz`` (shock, slow
bleed, a close above the reference high, recovery, holes in sessions, and
the rest of that generator). ``random.Random(k)`` only. Levels are
synthetic and are not index quotes.

The dialog includes the pullback fragment only for an active China episode.
Those renders must satisfy the shared forecast, sign, receipt, phase, and
byte-identity checks. Hong Kong and Canada receive the same ``pullback_view``
and must render the same bytes as a dialog with no ``pullback_view``.

The shared generator's recovering seed closes 0.04% over the reference high
on at least one seed; the dialog must print that tenth unsigned. And the
fragment's own ``assess`` rule decides qualification: a view it rejects must
leave the dialog byte-identical to its no-pullback shell, and the fragment
itself must fall back to the unavailable copy.
"""
from __future__ import annotations

import random
import time
from datetime import date, datetime, time as clock, timedelta
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from lib import cn_calendar
from lib.cn_pullback_observation import present, snapshot
from lib.pullback_depth import LicensedCloses
from lib.pullback_observation import PATH_MAX_CLOSES, RULES, observe
from tests.test_pullback_episode_fuzz import (
    _EM,
    _MINUS,
    _PHASE_LABELS,
    _SCENARIOS,
    _fail,
    _values,
    _walk_checks,
    assert_i1,
    assert_i2,
    assert_i3,
    assert_i5_receipt,
    assert_i6,
)

ROOT = Path(__file__).resolve().parents[1]
_ENV = Environment(
    loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False,
)
_DIALOG = (
    '{% import "_risk_radar_dlg.html.j2" as rrd %}'
    "{{ rrd.risk_radar_dlg(mkt, rd, none, ctx) }}"
)
_TPL = _ENV.from_string(_DIALOG)
# The fragment's own qualification rule, asked the way the dialog asks it.
_QUALIFIED = (
    '{% import "_risk_radar_pullback_depth.html.j2" as p %}'
    "{% set ns = namespace(current=false, low_ok=false) %}"
    '{{ p.assess("cn", v, ns) }}'
    '{{ "1" if ns.current else "0" }}'
)
_QUALIFIED_TPL = _ENV.from_string(_QUALIFIED)
# The fragment without the dialog's lead gate: what a view the rule rejects
# still renders there.
_DETAIL = (
    '{% import "_risk_radar_pullback_depth.html.j2" as p %}'
    "{{ p.detail('cn', v) }}"
)
_DETAIL_TPL = _ENV.from_string(_DETAIL)

# A calm stub: no odds card (that card reads dd21) and no live radar copy.
_STUB_RD = {"state": "calm"}
_TITLE = {"title_en": "Synthetic risk radar", "title_zh": "合成风险雷达"}

# The fragment's lead() gate. Monitoring, developing, repaired, and an
# unavailable reading stay on the dialog's own shell.
_LEAD_PHASES = {"underway", "stabilizing", "recovering"}
_LEAK = ("rrp", "pbx", "data-pb-", "mmPbExpire")

# One fixed session so every series' last close is the snapshot's expected
# session. 18:00 CST is past the calendar's settle buffer.
_END = date(2026, 6, 12)
_NOW = datetime.combine(_END, clock(18, 0), tzinfo=cn_calendar.CST)

# Three passes of the shared scenario set. The dialog budget is 60s.
_REPEATS = 3
N = len(_SCENARIOS) * _REPEATS


def _days(count, end=_END):
    found = []
    cursor = end
    while len(found) < count:
        if cn_calendar.is_session(cursor):
            found.append(cursor)
        cursor -= timedelta(days=1)
        if (end - cursor).days > count * 4 + 40:
            raise RuntimeError(f"no {count} China sessions on or before {end}")
    found.reverse()
    return found


def series_for(k):
    """Synthetic China closes for seed ``k``. Deterministic given ``k`` alone."""
    rng = random.Random(k)
    kind = _SCENARIOS[k % len(_SCENARIOS)]
    values = _values(kind, rng)
    if kind == "gaps":
        days = _days(len(values))
        drop = set(range(20, 55, 5))
        keep = [i for i in range(len(values)) if i not in drop]
        rows = [(days[i].isoformat(), float(values[i])) for i in keep]
    else:
        rows = [
            (day.isoformat(), float(value))
            for day, value in zip(_days(len(values)), values)
        ]
    if any(price <= 0 for _, price in rows):
        raise RuntimeError(f"seed {k} produced a non-positive close")
    return kind, rows


def _render(mkt, view):
    """The country dialog. ``view`` is attached only when it is a real mapping."""
    ctx = dict(_TITLE)
    if view is not None:
        ctx["pullback_view"] = view
    return _TPL.render(mkt=mkt, rd=_STUB_RD, ctx=ctx)


def _drive(rows):
    """snapshot(read=<synthetic>) → present(), with the shared observer admitted."""
    def read(_expected):
        return LicensedCloses(rows=list(rows))

    observation = snapshot(now=_NOW, read=read, observer=observe)
    view = present(observation)
    return observation, view


def _leads(obs, view):
    """True when this reading is an active episode the China gate may show."""
    return (
        obs.get("available") is True
        and obs.get("quality") == "current"
        and obs.get("phase") in _LEAD_PHASES
        and view.get("phase") == obs.get("phase")
    )


def _qualified(view):
    """The fragment's own assess() verdict for this China view."""
    return _QUALIFIED_TPL.render(v=view).strip()[-1] == "1"


def assert_rejected_fallback(html, soup, bare_html, k, kind, rows):
    """I6 rejected branch, dialog side: a view the fragment's assess() rejects
    must leave the dialog byte-identical to its no-pullback shell."""
    if soup.select_one("section.rrp") is not None:
        _fail(k, kind, rows, "rejected view still rendered the pullback section")
    for copy in ("Pullback underway", "回撤进行中", "Estimate unavailable", "估计暂不可用"):
        if copy in html:
            _fail(k, kind, rows, f"rejected view still shows {copy!r} from the fragment")
    for token in _LEAK:
        if token in html:
            _fail(k, kind, rows, f"pullback markup {token!r} leaked into a rejected view")
    assert_same_bytes(html, bare_html, k, kind, rows)


def assert_same_bytes(first, second, k, kind, rows):
    """I7: a second render of the same dialog is the same bytes."""
    if first != second or first.encode() != second.encode():
        _fail(k, kind, rows, "I7: second render differs")


def assert_market_unchanged(with_view, without_view, mkt, k, kind, rows):
    """HK/CA: attaching a China pullback_view must not change the dialog."""
    if with_view != without_view or with_view.encode() != without_view.encode():
        _fail(
            k, kind, rows,
            f"{mkt}: dialog with pullback_view differs from the dialog without it",
        )
    for token in _LEAK:
        if token in with_view:
            _fail(k, kind, rows, f"{mkt}: pullback markup {token!r} leaked")


def test_i1_rejects_probability_language_that_is_not_a_disclaimer():
    """A bare probability label in the forecast block fails I1."""
    html = (
        '<div class="rrp-forecast" data-forecast-status="unavailable">'
        '<p><span class="l-en">Probability of a further decline: —</span>'
        '<span class="l-zh">进一步下跌概率：—</span></p>'
        f"<strong>{_EM}</strong></div>"
    )
    with pytest.raises(AssertionError, match="I1"):
        assert_i1(
            BeautifulSoup(html, "html.parser"),
            k=0, kind="planted", rows=[("2026-06-12", 100.0)],
        )


def test_sign_rules_reject_a_wrong_mark_and_a_signed_zero():
    """I2 rejects a '+' end tag on a drawdown. I3 rejects a signed zero of
    either sign."""
    rows = [("2026-06-12", 90.0)]
    soup = BeautifulSoup('<div class="ilx-tag">+1.0%</div>', "html.parser")
    obs = {"close": 90.0, "peak_close": 100.0}
    view = {
        "detail_chart_html": "<svg></svg>",
        "detail_path": {"vals": [-10.0]},
    }
    with pytest.raises(AssertionError, match="I2"):
        assert_i2(soup, obs, view, k=0, kind="planted", rows=rows)
    with pytest.raises(AssertionError, match="I3"):
        assert_i3(
            BeautifulSoup("", "html.parser"),
            f"{_MINUS}0.0%", {}, k=0, kind="planted", rows=rows,
        )
    with pytest.raises(AssertionError, match="I3"):
        assert_i3(
            BeautifulSoup("", "html.parser"),
            "+0.0%", {}, k=0, kind="planted", rows=rows,
        )


def test_i5_rejects_a_receipt_that_is_not_the_last_session():
    """I5: the dated close stamp has to be the series' last session."""
    html = (
        '<section class="rrp" data-pb-asof="2026-01-01">'
        '<div class="rrp-stamp"><time datetime="2026-01-01">2026-01-01</time></div>'
        "</section>"
    )
    with pytest.raises(AssertionError, match="I5"):
        assert_i5_receipt(
            BeautifulSoup(html, "html.parser"),
            rows=[("2026-06-12", 100.0)], k=0, kind="planted",
        )


def test_i6_rejects_underway_shown_above_the_reference_high():
    """I6: the underway label must not be shown once the close is back at the high."""
    en, zh = _PHASE_LABELS["underway"]
    html = (
        '<section class="rrp" data-pb-phase="underway">'
        '<div class="pbx-heading"><h2>'
        f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>'
        "</h2></div></section>"
    )
    obs = {"close": 101.0, "peak_close": 100.0}
    with pytest.raises(AssertionError, match="I6: UNDERWAY"):
        assert_i6(
            BeautifulSoup(html, "html.parser"),
            obs, {"phase": "underway"}, True,
            k=0, kind="planted", rows=[("2026-06-12", 101.0)],
        )


def test_i7_rejects_a_second_render_that_differs():
    """I7 fires when the second render is not the same bytes."""
    with pytest.raises(AssertionError, match="I7"):
        assert_same_bytes(
            "<section></section>", "<section> </section>",
            k=0, kind="planted", rows=[("2026-06-12", 100.0)],
        )


def test_hk_ca_identity_rejects_a_leaked_fragment():
    """The identity check fires when pullback markup changes the dialog."""
    plain = '<div id="hkx-dlg-risk">shell</div>'
    leaked = plain + '<section class="rrp">'
    with pytest.raises(AssertionError, match="hk"):
        assert_market_unchanged(
            leaked, plain, "hk",
            k=0, kind="planted", rows=[("2026-06-12", 100.0)],
        )


def test_rejected_fallback_rejects_a_leaked_fragment():
    """The fallback check fires when a view assess() rejects still changes
    the dialog: a rendered section, or the fragment's copy."""
    plain = '<div id="cnx-dlg-risk">shell</div>'
    section = plain + '<section class="rrp" data-pb-phase="underway"></section>'
    with pytest.raises(AssertionError, match="rejected view still rendered"):
        assert_rejected_fallback(
            section, BeautifulSoup(section, "html.parser"), plain,
            k=0, kind="planted", rows=[("2026-06-12", 100.0)],
        )
    copy = plain + "<p>Pullback underway</p>"
    with pytest.raises(AssertionError, match="rejected view still shows"):
        assert_rejected_fallback(
            copy, BeautifulSoup(copy, "html.parser"), plain,
            k=0, kind="planted", rows=[("2026-06-12", 100.0)],
        )


def test_seeded_china_episode_fuzz_through_the_shared_dialog():
    started = time.perf_counter()
    bare = {mkt: _render(mkt, None) for mkt in ("cn", "hk", "ca")}
    for mkt, html in bare.items():
        for token in _LEAK:
            if token in html:
                raise AssertionError(f"bare {mkt} dialog already contains {token!r}")
    phases = set()
    shown_phases = set()
    saw_gap = False
    saw_tie = False
    saw_above = False
    saw_zero_above = False
    saw_rejected = False
    shortest = PATH_MAX_CLOSES
    longest = 0
    shown_n = 0
    for k in range(N):
        kind, rows = series_for(k)
        obs, view = _drive(rows)
        _walk_checks(kind, obs, view, rows, k)
        html = _render("cn", view)
        assert_same_bytes(html, _render("cn", view), k, kind, rows)
        for mkt in ("hk", "ca"):
            assert_market_unchanged(
                _render(mkt, view), bare[mkt], mkt, k, kind, rows,
            )
        soup = BeautifulSoup(html, "html.parser")
        section = soup.select_one("section.rrp")
        qualified = _qualified(view)
        if not qualified:
            # A view the fragment's own rule rejects must leave the dialog on
            # its shell, and the fragment itself must fall back to the
            # unavailable copy (I6's rejected branch).
            saw_rejected = True
            assert_rejected_fallback(html, soup, bare["cn"], k, kind, rows)
            assert_i6(
                BeautifulSoup(_DETAIL_TPL.render(mkt="cn", v=view), "html.parser"),
                obs, view, False, k, kind, rows,
            )
        if _leads(obs, view) != (section is not None):
            _fail(
                k, kind, rows,
                "dialog lead gate disagreed with the active-episode reading: "
                f"phase={obs.get('phase')} shown={section is not None}",
            )
        phases.add(obs.get("phase"))
        if section is None:
            assert_same_bytes(html, bare["cn"], k, kind, rows)
        else:
            shown_n += 1
            shown_phases.add(section.get("data-pb-phase"))
            if assert_i1(soup, k, kind, rows) != 2:
                _fail(k, kind, rows, "I1: forecast block did not disclaim in both languages")
            assert_i2(soup, obs, view, k, kind, rows)
            assert_i3(soup, html, view, k, kind, rows)
            assert_i5_receipt(soup, rows, k, kind)
            # lead() is 1 only when assess() is current, so the fragment's
            # phase is the presenter's phase.
            assert_i6(soup, obs, view, qualified, k, kind, rows)
            text = section.get_text(" ", strip=True)
            if "Shanghai Composite" not in text or "上证综指" not in text:
                _fail(k, kind, rows, "shown fragment is not the China benchmark")
        saw_gap = saw_gap or (obs.get("history_gap_count") or 0) > 0
        low = obs.get("low_close")
        saw_tie = saw_tie or (
            isinstance(low, float) and sum(1 for _, price in rows if price == low) >= 2
        )
        close, peak = obs.get("close"), obs.get("peak_close")
        saw_above = saw_above or (
            isinstance(close, float) and isinstance(peak, float) and close > peak
            and obs.get("phase") != "underway"
            and section is not None
            and section.get("data-pb-phase") != "underway"
        )
        # 0.04% over the high: above it, but the tenth rounds to 0.0, so the
        # dialog's metric, end tag and history must all print it unsigned.
        saw_zero_above = saw_zero_above or (
            isinstance(close, float) and isinstance(peak, float) and close > peak
            and round(100.0 * (close / peak - 1.0), 1) == 0
            and section is not None
        )
        shortest = min(shortest, len(rows))
        longest = max(longest, len(rows))
    missing = {
        "monitoring", "developing", "underway", "stabilizing",
        "recovering", "repaired", "unavailable",
    } - phases
    if missing:
        raise AssertionError(
            f"generator missed owner phases {sorted(missing)}; saw {sorted(phases)}"
        )
    if shown_phases != _LEAD_PHASES or shown_n < 1:
        raise AssertionError(
            f"dialog showed phases {sorted(shown_phases)} on {shown_n} seeds"
        )
    if not saw_gap or not saw_tie or not saw_above or not saw_zero_above or not saw_rejected:
        raise AssertionError(
            f"generator missed a situation gap={saw_gap} tie={saw_tie} above={saw_above} "
            f"zero_above={saw_zero_above} rejected={saw_rejected}"
        )
    if shortest >= RULES.reference_closes or longest <= PATH_MAX_CLOSES:
        raise AssertionError(f"generator length range {shortest}..{longest}")
    elapsed = time.perf_counter() - started
    print(f"china episode fuzz: N={N} shown={shown_n} elapsed={elapsed:.2f}s")
    assert elapsed < 60.0, f"N={N} took {elapsed:.2f}s"
