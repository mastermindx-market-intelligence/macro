"""HK regime-history page: the segment in force and the sample behind "next".

W33 SPEC 2 (findings F4/F5/F11 of the W32D design packet):

* ``engine/playbook.transition_stats`` returns ``current`` (quad / age_days /
  median_days) and ``n_segments``, and ``quad_segments`` returns each segment's
  ``start`` — at the seed ``scripts/build_hk._build_history`` read only
  ``matrix`` / ``n_by_quad`` / ``median_days`` and ``n_segments`` survived only
  into ``log.info`` (``scripts/build_hk.py:313``), so the page said
  "Reflation -> Stagflation 70%" with no hint the label was 3 sessions old.
* ``engine/playbook.py:231`` excludes the unfinished segment from ``matrix[q]``
  while ``:234-237`` counts it in ``n_by_quad[q]``: the sample behind the
  "most common next" percentages is ``n_by_quad[q] - 1`` for the regime in
  force (HK: 45 shown / 44 behind).
* ``scripts/build_hk.py:1334`` already stamps ``... UTC``, so the template's
  own literal made the committed page read ``2026-10-20 17:09 UTC UTC``.

Synthetic frames only: no ``data/`` or ``site/`` read, and ``write_page`` plus
both chart helpers are patched out so nothing is written.

Run: MM_DATA_GUARD=off PYTHONPATH=. python3 -m pytest \
    tests/test_regime_history_hk_current.py -q
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from engine import i18n  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "hk_history.html.j2"
STAMP = "2026-10-20 17:09 UTC"

BANNED = ("实时", "申报", "证伪", "validated", "已验证", "live", "forecast",
          "falsifier", "refuted", "z-score", "percentile rank", "probability",
          "概率", "当前", "最新", "独立")
NEW_EN = ("(sample)", "sample", "Regime in force", "since", "sessions old",
          "median", "periods in the sample")
NEW_ZH = ("（样本）", "样本", "现行周期", "始于", "个交易日", "中位数",
          "个样本时段")


class _Store:
    """Stands in for lib.store: only the regime_history frame is served."""

    def __init__(self, frame):
        self.frame = frame

    def read(self, category, name, *args, **kwargs):
        if (category, name) == ("hk_regime", "regime_history"):
            return self.frame
        return None


class _Config:
    @staticmethod
    def load():
        return {"hk": {"yahoo": {"market_index": "^HSI"}},
                "storage": {"site_dir": "."}}


def _frame(segments, end="2026-10-16"):
    """Expand [(quad, n_sessions), ...] onto a business-day index ending `end`."""
    from scripts import build_hk
    pd = build_hk.pd
    quads = [quad for quad, n in segments for _ in range(n)]
    index = pd.bdate_range(end=end, periods=len(quads))
    return pd.DataFrame({"quad": quads}, index=index)


def _committed_shape_frame():
    """The shape of data/hk_regime/regime_history.parquet: 162 segments, the
    one in force is Q2, 3 sessions old, started 2026-10-14, Q2 median 26."""
    cycle = ["Q1", "Q3", "Q2", "Q4"] * 40
    return _frame([(quad, 26) for quad in cycle] + [("Q1", 26), ("Q2", 3)])


def _denominator_frame():
    """n_by_quad Q1=40 / Q2=45 with Q2 in force: 45 shown, 44 behind it."""
    pairs = ["Q1", "Q2"] * 40 + ["Q3", "Q2"] * 5
    return _frame([(quad, 26) for quad in pairs])


def _render(monkeypatch, tmp_path, frame):
    """Run scripts/build_hk.py's own _build_history with every write patched."""
    from scripts import build_hk
    captured = {}
    monkeypatch.setattr(build_hk, "store", _Store(frame))
    monkeypatch.setattr(build_hk, "config", _Config)
    monkeypatch.setattr(build_hk, "_chart_regime", lambda *a, **k: "")
    monkeypatch.setattr(build_hk, "_chart_axes", lambda *a, **k: "")
    monkeypatch.setattr(
        build_hk, "write_page",
        lambda path, html: captured.__setitem__("html", html))
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr)
    build_hk._build_history(env, {"date": "2026-10-16"}, STAMP)
    assert captured.get("html"), "_build_history wrote no page"
    return re.sub(r"\s+", " ", captured["html"])


def _view(html, drop):
    out = re.sub(r'<span class="l-%s">.*?</span>' % drop, " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", out))


def _row(html, en_name):
    needle = '<span class="l-en">%s</span>' % en_name
    for chunk in html.split("<tr>")[1:]:
        if needle in chunk:
            return chunk
    raise AssertionError("no lifespan row for %s" % en_name)


def _sample_of(row_html):
    hit = re.search(r'l-zh">样本</span>\s*(\d+)', row_html)
    assert hit, "no sample marker beside the next-quad line: %s" % row_html[:160]
    return int(hit.group(1))


def test_current_segment_start_and_age_reach_the_template(monkeypatch, tmp_path) -> None:
    html = _render(monkeypatch, tmp_path, _committed_shape_frame())
    en, zh = _view(html, "zh"), _view(html, "en")
    assert "Regime in force" in en and "现行周期" in zh
    assert "since 2026-10-14" in en, en[-400:]
    assert "始于 2026-10-14" in zh
    assert "3 sessions old" in en
    assert "3 个交易日" in zh
    assert "median 26" in en and "中位数 26" in zh


def test_denominator_is_one_less_for_the_regime_in_force(monkeypatch, tmp_path) -> None:
    html = _render(monkeypatch, tmp_path, _denominator_frame())
    q2, q1 = _row(html, "Reflation"), _row(html, "Goldilocks")
    assert ">45</td>" in q2, q2[:200]
    assert _sample_of(q2) == 44, "the regime in force must drop its own open segment"
    assert ">40</td>" in q1, q1[:200]
    assert _sample_of(q1) == 40, "a closed regime's sample equals its period count"


def test_n_segments_total_renders(monkeypatch, tmp_path) -> None:
    html = _render(monkeypatch, tmp_path, _committed_shape_frame())
    en, zh = _view(html, "zh"), _view(html, "en")
    assert "162 periods in the sample" in en
    assert "162 个样本时段" in zh


def test_degrades_to_todays_output_on_a_two_session_frame(monkeypatch, tmp_path) -> None:
    """One segment: no median to compare an age against, so no age row."""
    html = _render(monkeypatch, tmp_path, _frame([("Q2", 2)]))
    en = _view(html, "zh")
    assert "Regime in force" not in en
    assert "periods in the sample" not in en
    assert "None" not in html.split("Regime lifespans")[1].split("</table>")[0]
    panel = html.split("Regime lifespans")[1]
    assert panel.count("<tr>") == 5, "the lifespan table must still print 4 rows"


def test_generation_stamp_prints_utc_once(monkeypatch, tmp_path) -> None:
    html = _render(monkeypatch, tmp_path, _committed_shape_frame())
    stamp = re.search(r'<p class="muted"><span class="l-en">Generated</span>.*?</p>', html)
    assert stamp, "no generation stamp"
    assert stamp.group(0).count("UTC") == 1, stamp.group(0)
    assert STAMP in stamp.group(0)


def test_bilingual_and_copy_laws(monkeypatch, tmp_path) -> None:
    html = _render(monkeypatch, tmp_path, _committed_shape_frame())
    for phrase in NEW_EN:
        assert re.search(r'<span class="l-en">[^<]*%s' % re.escape(phrase), html), phrase
    for phrase in NEW_ZH:
        assert re.search(r'<span class="l-zh">[^<]*%s' % re.escape(phrase), html), phrase
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    head = next(i for i, ln in enumerate(lines) if ln.strip() == "<table>")
    tail = next(i for i, ln in enumerate(lines) if ln.strip() == "</table>" and i > head)
    touched = lines[head:tail + 1] + [ln for ln in lines if "generated_utc" in ln]
    for line in touched:
        assert len(line) <= 100, "added line over 100 chars: %r" % line[:40]
        low = line.lower()
        for bad in BANNED:
            assert bad not in low, "banned token %r in an added line" % bad
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", line), "new colour literal"
        assert "color-mix" not in line
