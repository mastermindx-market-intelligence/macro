"""Pin the AM Edition evidence-capture tool's two R2 repairs.

R1 of PR #8289 was BLOCKED by an independent Opus review on two capture
defects (F01 O26b REQUEST_REPAIR round 2): no ZH ``.mx-rw-zh-note`` rendered
because the fixture row's ``condition_zh_disclosed_why`` was ``None``; and
the theme-toggle ``.sky-fx`` orb baked into every cell because the capture
ran without ``prefers-reduced-motion: reduce``. This file pins the repair
at the tool's source so neither defect can silently return.

Tests are pure-Python — no Playwright — because the helper is pure and the
orb-suppression check is a literal pin on the source string.
"""
from __future__ import annotations

from pathlib import Path

from scripts.build_am_edition import (
    _RESEARCH_WATCH_ZH_DISCLOSURE,
    _RESEARCH_WATCH_ZH_DISCLOSURE_WHY,
)
from scripts.capture_am_edition_evidence import _extend_research_watch


def test_extend_research_watch_yields_two_rows_with_one_disclosed_why() -> None:
    """The helper appends a disclosed-English row and keeps the seed row.

    Templates emit the ``.mx-rw-zh-note`` only from non-empty distinct
    ``condition_zh_disclosed_why`` values (`templates/am_edition.html.j2`
    l.381), so a single translated row (whose disclosed-why is ``None``)
    renders zero notes. R2 requires ≥2 rows AND exactly one distinct
    non-empty disclosed-why equal to the canonical disclosure WHY.
    """
    seed_rows = [
        {
            "condition_en": "Watch when the dollar breaks its 20-day range.",
            "condition_zh": "观察美元是否突破20日区间。",
            "condition_zh_disclosed_why": None,
            "since": "2026-09-08",
            "as_of": "2026-09-08T10:00:00+00:00",
            "source_ref": "data/master_brain/theses.jsonl",
        }
    ]
    out = _extend_research_watch(seed_rows)
    assert len(out) >= 2, f"expected ≥2 rows, got {len(out)}"
    assert out[0] == seed_rows[0], "row 1 must be preserved verbatim"
    non_empty_why = {
        r.get("condition_zh_disclosed_why")
        for r in out
        if r.get("condition_zh_disclosed_why")
    }
    assert len(non_empty_why) == 1, (
        f"expected exactly one distinct non-empty disclosed-why, got {non_empty_why!r}"
    )
    assert non_empty_why == {_RESEARCH_WATCH_ZH_DISCLOSURE_WHY}, (
        "disclosed-why must equal the canonical RESEARCH_WATCH_ZH_DISCLOSURE_WHY"
    )
    disclosed_row = out[-1]
    assert disclosed_row["condition_zh"] == _RESEARCH_WATCH_ZH_DISCLOSURE
    assert disclosed_row["condition_en"] == "Watch when the 2s10s curve re-steepens past +25 bp."


def test_capture_tool_emulates_reduced_motion() -> None:
    """Cheap source-level pin: the tool must call ``emulate_media(reduced_motion="reduce")``.

    theme.js:543 suppresses the ``.sky-fx`` orb under prefers-reduced-motion;
    the capture tool only inherits that suppression if it emulates the media
    feature BEFORE ``page.goto``. This test fails closed if the call is
    silently dropped — a much cheaper guarantee than a Playwright regression.
    """
    tool_path = Path(__file__).resolve().parent.parent / "scripts" / "capture_am_edition_evidence.py"
    src = tool_path.read_text(encoding="utf-8")
    assert 'emulate_media(reduced_motion="reduce")' in src, (
        "capture tool must emulate prefers-reduced-motion before goto; "
        "without it, theme.js skyToggleFx mounts a .sky-fx orb over every cell"
    )