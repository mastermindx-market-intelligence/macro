"""Canada regime-history page: the regime in force and the flip counting up.

W33 SPEC 3 (finding F3 of the W32D design packet): ``site/canada_history.html``
shades Q3 (#d04545, 2026-10-06..2026-10-19) while the page's own dials end at
growth -0.20 / inflation -0.571 — both negative, which the legend at
``templates/canada_history.html.j2:76`` defines as Growth scare (Q4). The keys
that resolve the disagreement (``latest.quad``, ``latest.pending_quad``,
``latest.pending_days``) are already inside the vm passed at
``scripts/build_canada.py:610`` and no template rendered them.

``data/canada_regime/latest.json`` carries no ``pending_need`` and no
``raw_quad``, so the page prints the day count only and never invents a
denominator or names a confirmation threshold. ``pending_quad`` is a float NaN
in the HK/CN artifacts and NaN is truthy, hence the tight
``in ['Q1','Q2','Q3','Q4']`` guard (``templates/china.html.j2:1811``).

``pending_days`` adds one per row of a frame built on ``pd.bdate_range``
(``engine/canada_inputs.py:63``, ``engine/regime.py:84``), and
``data/canada_regime/regime_history.parquet`` holds every Monday to Friday in
its span, 12-25 and 1-1 included. The count and the medians are weekdays, not
trading days, so both labels say weekdays.

Synthetic fixtures only: no ``data/`` or ``site/`` read, no builder call.

Run: MM_DATA_GUARD=off PYTHONPATH=. python3 -m pytest \
    tests/test_regime_history_canada_today.py -q
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from engine import i18n  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "canada_history.html.j2"
STAMP = "2026-10-20 17:33 UTC"

# the four rows site/canada_history.html prints; the two "next" strings quoted
# by the packet (F5 for Q3, SPEC 3's reader decision for Q4) are verbatim, the
# other two are synthetic and are never asserted on.
LIFESPAN_ROWS = [
    {"name": "Goldilocks", "n": 67, "median": 20,
     "next": "Reflation 41%, Stagflation 28%",
     "next_zh": "再通胀 41%、滞胀 28%"},
    {"name": "Reflation", "n": 83, "median": 21,
     "next": "Goldilocks 45%, Stagflation 31%",
     "next_zh": "理想增长 45%、滞胀 31%"},
    {"name": "Stagflation", "n": 72, "median": 17,
     "next": "Reflation 69%, Growth scare 21%",
     "next_zh": "再通胀 69%、增长恐慌 21%"},
    {"name": "Growth scare", "n": 65, "median": 24,
     "next": "Goldilocks 54%, Stagflation 32%",
     "next_zh": "理想增长 54%、滞胀 32%"},
]

# the exact values F3 quotes from data/canada_regime/latest.json
LATEST = {"date": "2026-10-14", "quad": "Q3", "quad_name": "Stagflation",
          "pending_quad": "Q4", "pending_days": 1, "growth_score": -0.2,
          "inflation_score": -0.571}

MARKERS = ("_qn", "_force", "_pend", "in force", "pending_quad", "pending_days",
           "generated_utc", "td(row.name)", "row.next", "row.n }}")
NEW_EN = ("in force", "A different regime is pending confirmation", "for", "weekday",
          "median length (weekdays)")
NEW_ZH = ("现行", "另一周期待确认", "已持续", "天（周一至周五计）",
          "存续中位数（周一至周五计，天）")
BANNED = ("实时", "申报", "证伪", "validated", "已验证", "live", "forecast",
          "falsifier", "refuted", "z-score", "percentile rank", "probability",
          "概率", "当前", "最新", "独立")


def _render(latest: dict, rows: list | None = None) -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr)
    html = env.get_template("canada_history.html.j2").render(
        latest=latest, generated_utc=STAMP, chart_regime="", chart_axes="",
        lifespan_rows=LIFESPAN_ROWS if rows is None else rows)
    return re.sub(r"\s+", " ", html)


def _view(html: str, drop: str) -> str:
    """The reader's text in one language: the other language's spans and every
    tag go away WITHOUT leaving a space, so the spacing is the template's own."""
    out = re.sub(r'<span class="l-%s">.*?</span>' % drop, "", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", out))


def _row(html: str, en_name: str) -> str:
    needle = '<span class="l-en">%s</span>' % en_name
    for chunk in html.split("<tr>")[1:]:
        if needle in chunk:
            return chunk
    raise AssertionError("no lifespan row for %s" % en_name)


def _disclosure(html: str) -> str:
    for chunk in html.split('<p class="muted">')[1:]:
        body = chunk.split("</p>")[0]
        if "pending confirmation" in body:
            return body
    return ""


def test_marks_the_row_in_force_and_the_pending_flip() -> None:
    html = _render(dict(LATEST))
    stag = _row(html, "Stagflation")
    assert '<span class="l-en">in force</span>' in stag, stag[:220]
    assert '<span class="l-zh">现行</span>' in stag
    for other in ("Goldilocks", "Reflation", "Growth scare"):
        assert "in force" not in _row(html, other), "%s row is marked too" % other
    chunk = _disclosure(html)
    assert chunk, "no pending disclosure rendered"
    en, zh = _view(chunk, "zh"), _view(chunk, "en")
    assert "A different regime is pending confirmation" in en
    assert "Growth scare" in en and "for 1 weekday" in en, en
    assert "另一周期待确认" in zh and "增长恐慌" in zh
    assert "已持续 1 天（周一至周五计）" in zh, zh


def test_pending_count_is_labelled_weekdays_on_both_arms() -> None:
    """The frame has a row for every Monday to Friday, market holidays included."""
    chunk = _disclosure(_render(dict(LATEST)))
    en, zh = _view(chunk, "zh"), _view(chunk, "en")
    assert "1 weekdays" not in en and "1d" not in en and "trading" not in en
    assert "交易日" not in zh
    chunk = _disclosure(_render(dict(LATEST, pending_days=3)))
    en, zh = _view(chunk, "zh"), _view(chunk, "en")
    assert "for 3 weekdays" in en, en
    assert "已持续 3 天（周一至周五计）" in zh, zh


def test_median_column_states_its_unit() -> None:
    html = _render(dict(LATEST))
    en, zh = _view(html, "zh"), _view(html, "en")
    assert "median length (weekdays)" in en
    assert "存续中位数（周一至周五计，天）" in zh
    assert "median length (days)" not in en
    assert "存续中位数（天）" not in zh


def test_nan_pending_quad_never_reaches_the_page() -> None:
    # canada_run coerces pending_days independently of pending_quad, so a
    # non-quad pending_quad can arrive with a nonzero day count: the guard must
    # key on the quad itself, not on the day count happening to be zero.
    for pq, pdays in ((float("nan"), 0), (float("nan"), 5), (None, 5), ("", 5)):
        latest = dict(LATEST, pending_quad=pq, pending_days=pdays)
        html = _render(latest)
        panel = html.split("Regime lifespans")[1].split("Generated")[0]
        assert not re.search(r"\bnan\b", panel), panel[:300]
        assert "pending confirmation" not in _view(panel, "zh"), (pq, pdays)
        assert not _disclosure(html), (pq, pdays)
        assert '<span class="l-en">in force</span>' in _row(html, "Stagflation")


def test_no_denominator_is_invented() -> None:
    """data/canada_regime/latest.json has no pending_need: print the day count
    only, never a confirmation threshold."""
    html = _render(dict(LATEST))
    chunk = _disclosure(html)
    assert chunk
    en, zh = _view(chunk, "zh"), _view(chunk, "en")
    assert not re.search(r"\bof\s+\d", en), en
    assert not re.search(r"需要\s*\d", zh), zh
    assert "pending_need" not in html
    assert "/" not in en.split("pending confirmation")[1]


def test_degrades_without_latest_quad() -> None:
    html = _render({"date": "2026-10-14"})
    panel = html.split("Regime lifespans")[1]
    en = _view(html, "zh")
    assert panel.count("<tr>") == 5, "the lifespan table must still print 4 rows"
    assert "in force" not in en
    assert not _disclosure(html)
    assert "None" not in panel.split("</table>")[0]
    for row in LIFESPAN_ROWS:
        assert row["name"] in html


def test_generation_stamp_prints_utc_once() -> None:
    html = _render(dict(LATEST))
    stamp = re.search(
        r'<p class="muted"><span class="l-en">Generated</span>.*?</p>', html)
    assert stamp, "no generation stamp"
    assert stamp.group(0).count("UTC") == 1, stamp.group(0)
    assert STAMP in stamp.group(0)


def test_bilingual_and_copy_laws() -> None:
    html = _render(dict(LATEST))
    for phrase in NEW_EN:
        assert re.search(r'<span class="l-en">[^<]*%s' % re.escape(phrase), html), phrase
    for phrase in NEW_ZH:
        assert re.search(r'<span class="l-zh">[^<]*%s' % re.escape(phrase), html), phrase
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    touched = [ln for ln in lines if any(mark in ln for mark in MARKERS)]
    assert len(touched) >= 8, "the new Canada lines are missing: %d" % len(touched)
    for line in touched:
        assert len(line) <= 100, "added line over 100 chars: %r" % line[:40]
        low = line.lower()
        for bad in BANNED:
            assert bad not in low, "banned token %r in an added line" % bad
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", line), "new colour literal"
        assert "color-mix" not in line
