"""Phase-0 badge -> actual IPO view model -> bilingual receipt fragment.

These are consumer checks with inline native-shaped badges. They do not rerun
the event study, call a provider, build/publish the site, or import test_ipo's
fixtures. The original 25-name counterexample is recorded in #11131,
issuecomment-6830426679; the separate union count is not a focus denominator.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
from jinja2 import Environment, StrictUndefined

from scripts import build_ipo as bi


VERDICTS = [
    ("DISPLAY-ONLY · no measurable edge on our sample", "仅供展示 · 在我们的样本上无可测量的优势"),
    ("DISPLAY-ONLY · insufficient usable event windows", "仅供展示 · 可用事件窗口不足"),
    ("DISPLAY-ONLY · event-window statistics unavailable", "仅供展示 · 事件窗口统计不可用"),
    ("DISPLAY-ONLY · drift confirmed (avoid, not shortable)", "仅供展示 · 漂移已确认（应规避，不代表可做空）"),
    ("DISPLAY-ONLY · soft negative drift, not significant", "仅供展示 · 轻微负向漂移，未达显著性"),
]


def _badge(n=24, status="available", verdict=None):
    stat = {"n": n, "n_unavailable": 25 - n, "status": status}
    if status == "available":
        stat.update(mean_pct=0.88, pct_negative=44.2)
    return {
        "verdict": verdict or VERDICTS[2 if status == "unavailable_statistics" else 1][0],
        "tier": "none", "focus": "event[-1,+3]", "n_names": 25,
        "as_of": "2026-11-12", "stat": stat,
    }


def _legacy():
    return {
        "verdict": VERDICTS[0][0], "tier": "none", "focus": "event[-1,+3]",
        "n_names": 77, "as_of": "2026-06-16",
        "stat": {"n": 77, "mean_pct": 0.88, "pct_negative": 44.2},
    }


@pytest.fixture(scope="module")
def receipt_template():
    source = (Path(bi.__file__).resolve().parents[1] / "templates/ipo.html.j2").read_text()
    start = source.index('    <div class="note warn">', source.index("dot size = deal size"))
    end = source.index("  </div>\n  {% endif %}\n\n  <!-- ============ AFTERMARKET", start)
    # Keep the real t/qtip macros, escaping and warning/receipt markup together.
    fragment = source[:source.index("<!DOCTYPE html>")] + source[start:end]
    return Environment(autoescape=True, undefined=StrictUndefined).from_string(fragment)


def _render(template, badge, **overrides):
    view = bi._phase0_receipt_vm(badge)
    return view, template.render(
        lockup_p0=view, lockup_receipt_en=overrides.get("en"),
        lockup_receipt_zh=overrides.get("zh"),
    )


def _assert_current_disclosure(html):
    assert "finds no measurable, tradeable edge" not in html
    assert "未发现可测量、可交易的优势" not in html
    assert "modeled lock-up calendar" in html
    assert "估算禁售到期日历" in html
    assert "not a verified release record or a forecast" in html
    assert "并非实际解禁记录或预测" in html


@pytest.mark.parametrize("n", [25, 24, 8])
def test_current_numerical_receipt_uses_focus_sample(receipt_template, n):
    badge = _badge(n=n)
    original = copy.deepcopy(badge)
    view, html = _render(receipt_template, badge)
    assert view["n_names"] == n
    assert view["n_any_window"] == 25
    assert f"Our event study of {n} recent un-locks" in html
    assert f"的{n}次近期解禁的事件研究" in html
    assert f"{n} usable focus-window observations" in html
    assert f"{25 - n} unavailable" in html
    assert "+0.88%" in html and "44.2% of names fell behind" in html
    assert "可用事件窗口不足" in html  # Available statistics do not imply a sufficient study.
    _assert_current_disclosure(html)
    assert badge == original


@pytest.mark.parametrize("n,status,verdict_zh", [
    (7, "insufficient", "可用事件窗口不足"),
    (0, "insufficient", "可用事件窗口不足"),
    (25, "unavailable_statistics", "事件窗口统计不可用"),
])
def test_unavailable_statistics_stay_visible(receipt_template, n, status, verdict_zh):
    badge = _badge(n=n, status=status)
    view, html = _render(receipt_template, badge)
    assert view is not None and view["n_names"] == n
    assert view["has_statistics"] is False
    assert view["mean_disp"] == "" and view["pct_negative"] == ""
    assert f"{n} usable focus-window observations" in html
    assert f"{n}个可用重点窗口观测" in html
    assert f"{25 - n} unavailable" in html
    assert badge["verdict"] in html and verdict_zh in html
    assert "average return vs the S&amp;P 500" not in html
    assert "相对标普500的平均回报为" not in html
    _assert_current_disclosure(html)


@pytest.mark.parametrize("mean,pct,mean_text,pct_text", [
    (0.0, 0.0, "+0.00%", "0.0"),
    (-0.5, 44.2, "−0.50%", "44.2"),
    (0.88, 100.0, "+0.88%", "100.0"),
])
def test_measured_values_are_not_treated_as_absence(receipt_template, mean, pct, mean_text, pct_text):
    badge = _badge()
    badge["stat"].update(mean_pct=mean, pct_negative=pct)
    view, html = _render(receipt_template, badge)
    assert view["has_statistics"] is True
    assert view["mean_disp"] == mean_text and view["pct_negative"] == pct_text
    assert mean_text in html and f"{pct_text}% of names fell behind" in html
    assert "average return vs the S&amp;P 500" in html


@pytest.mark.parametrize("verdict_en,verdict_zh", VERDICTS)
def test_all_producer_verdicts_have_chinese_disclosure(receipt_template, verdict_en, verdict_zh):
    view, html = _render(receipt_template, _badge(verdict=verdict_en))
    assert view["verdict_en"] == verdict_en
    assert view["verdict_zh"] == verdict_zh
    assert verdict_zh in html and "DISPLAY-ONLY" not in view["evidence_note_zh"]


@pytest.mark.parametrize("status", ["available", "insufficient", "unavailable_statistics"])
def test_current_evidence_takes_precedence_over_old_custom_receipt(receipt_template, status):
    view, html = _render(
        receipt_template, _badge(status=status),
        en="OLD CUSTOM STUDY: no edge", zh="旧自定义研究：没有优势",
    )
    assert view is not None
    assert "OLD CUSTOM STUDY" not in html and "旧自定义研究" not in html
    assert "24 usable focus-window observations" in html
    _assert_current_disclosure(html)


@pytest.mark.parametrize("status", ["available", "insufficient", "unavailable_statistics"])
@pytest.mark.parametrize("missing", ["absent", "null"])
def test_missing_current_focus_count_never_borrows_union(receipt_template, status, missing):
    badge = _badge(status=status)
    if missing == "absent":
        badge["stat"].pop("n")
    else:
        badge["stat"]["n"] = None
    view, html = _render(receipt_template, badge)
    assert view is not None and view["n_names"] is None
    assert view["n_any_window"] == 25 and view["has_statistics"] is False
    assert "focus-window observation count unavailable" in html
    assert "重点窗口观测数量不可用" in html
    assert "25 usable focus-window observations" not in html
    assert "Our event study of 25 recent un-locks" not in html
    assert "average return vs the S&amp;P 500" not in html
    _assert_current_disclosure(html)


@pytest.mark.parametrize("missing", ["absent", "null"])
def test_legacy_missing_focus_count_keeps_legacy_fallback(receipt_template, missing):
    badge = _legacy()
    if missing == "absent":
        badge["stat"].pop("n")
    else:
        badge["stat"]["n"] = None
    view, html = _render(receipt_template, badge)
    assert view["n_names"] == 77 and view["mean_disp"] == "+0.88%"
    assert "Our event study of 77 recent un-locks (to 2026-06-16)" in html


def test_legacy_explicit_focus_count_is_an_intentional_correction(receipt_template):
    badge = _legacy()
    badge["stat"]["n"] = 76
    view, html = _render(receipt_template, badge)
    assert view["n_names"] == 76 and view["n_any_window"] == 77
    assert "Our event study of 76 recent un-locks" in html


def test_legacy_custom_receipt_keeps_its_precedence(receipt_template):
    _, html = _render(receipt_template, _legacy(), en="LEGACY CUSTOM RECEIPT", zh="原有自定义说明")
    assert "LEGACY CUSTOM RECEIPT" in html and "原有自定义说明" in html
    assert "Field &amp; Hanka document" not in html


@pytest.mark.parametrize("badge", [None, {}, {"stat": None}, {"stat": {}, "n_names": 25, "as_of": "2026-11-12"}])
def test_absent_or_malformed_legacy_receipt_stays_absent(receipt_template, badge):
    view, html = _render(receipt_template, badge)
    assert view is None
    assert "average return vs the S&amp;P 500" not in html


@pytest.mark.parametrize("mean", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_legacy_statistics_are_not_printed(receipt_template, mean):
    badge = _legacy()
    badge["stat"]["mean_pct"] = mean
    view, html = _render(receipt_template, badge)
    assert view is None
    assert "average return vs the S&amp;P 500" not in html
