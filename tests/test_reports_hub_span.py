"""The Reports hub masthead dates its own archive.

`scripts/build_reports.py:284` computes `stats["oldest"]` and `:300-303` passes the
whole `stats` dict to `reports.html.j2`, but the masthead strip rendered only
`n_reports` / `n_topics` / `total_min` — so the page said "Latest briefing · AUG 24,
2026" with no frame, and a reader had to scroll to the last archive card to learn
when the desk's oldest published read is.

`scripts/build_reports.py` is read-only here: the template consumes only what the
builder already passes. The vm below is built inline from the badge parts
`_enrich` produces (`mon` / `day` / `year`, `scripts/build_reports.py:255-258`,
`_MON` uppercase at `:42`) and carries the committed registry's two endpoint
records by value.
"""
from __future__ import annotations

import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_PRODUCER = Path(__file__).resolve().parents[1] / "scripts" / "build_reports.py"
_TAGS = [{"key": "macro", "en": "Macro", "zh": "宏观", "count": 2}]


def _report(slug: str, date: str, mon: str, day: str, year: str,
            full: str, read_min: int) -> dict:
    """One record shaped like `_enrich`'s output (badge parts + long date)."""
    return {
        "slug": slug, "date": date, "mon": mon, "day": day, "year": year,
        "date_display": full, "read_min": read_min,
        "title_en": slug.replace("report_", " ").title(), "title_zh": "报告 " + slug,
        "dek_en": "Dek.", "dek_zh": "摘要。",
        "tags": [{"key": "macro", "en": "Macro", "zh": "宏观"}],
    }


# The committed registry's two endpoints: newest `report_price_of_duration`
# 2026-08-24, oldest `report_warsh_fomc` 2026-06-17 (reports sorted desc by date).
_LATEST = _report("report_price_of_duration", "2026-08-24", "AUG", "24", "2026",
                  "August 24, 2026", 34)
_OLDEST = _report("report_warsh_fomc", "2026-06-17", "JUN", "17", "2026",
                  "June 17, 2026", 18)


def _vm(reports: list[dict]) -> dict:
    return {
        "reports": reports,
        "all_tags": _TAGS if reports else [],
        "stats": {
            "n_reports": len(reports),
            "n_topics": len(_TAGS if reports else []),
            "total_min": sum(r["read_min"] for r in reports),
            "latest": reports[0] if reports else None,
            "oldest": reports[-1] if reports else None,
        },
    }


def _render(vm: dict) -> str:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    return env.get_template("reports.html.j2").render(
        reports=vm["reports"], all_tags=vm["all_tags"], stats=vm["stats"],
        active_section="research", active_page="reports")


def _strip(html: str) -> str:
    """The masthead stat strip, `<div class="rc-deskstat">` … its own `</div>`."""
    start = html.index('<div class="rc-deskstat">')
    return html[start:html.index("</div>", start)]


def test_masthead_strip_states_the_archive_span():
    strip = _strip(_render(_vm([_LATEST, _OLDEST])))
    assert "JUN 17" in strip
    assert "AUG 24, 2026" in strip
    # the span sits next to the totals it frames, inside the same strip
    assert strip.index("JUN 17") > strip.index("min of reading")


def test_committed_registry_span_reaches_the_masthead():
    vm = _vm([_LATEST, _OLDEST])
    assert vm["stats"]["oldest"]["slug"] == "report_warsh_fomc"
    strip = _strip(_render(vm))
    assert "JUN 17" in strip
    assert "AUG 24, 2026" in strip

    # read-only pin on the producer this template consumes: `oldest` is still
    # computed, still passed, and the registry still carries both endpoints.
    src = _PRODUCER.read_text(encoding="utf-8")
    assert '"oldest": reports[-1] if reports else None' in src
    assert 'env.get_template("reports.html.j2").render(' in src
    assert "stats=stats" in src
    assert '"report_warsh_fomc"' in src and '"2026-06-17"' in src
    assert '"report_price_of_duration"' in src and '"2026-08-24"' in src


def test_strip_is_unchanged_for_an_empty_registry():
    html = _render(_vm([]))
    assert '<div class="rc-deskstat">' not in html
    assert "JUN 17" not in html

    # a partial stats payload — a count but no usable `oldest` — must neither
    # raise nor render a half-empty span
    for absent in (True, False):
        vm = _vm([_LATEST, _OLDEST])
        if absent:
            vm["stats"].pop("oldest")
        else:
            vm["stats"]["oldest"] = None
        strip = _strip(_render(vm))
        assert "JUN" not in strip
        assert "AUG" not in strip


def test_strip_span_is_bilingual():
    strip = _strip(_render(_vm([_LATEST, _OLDEST])))
    span = strip[strip.index("JUN 17"):]
    head = strip[:strip.index("JUN 17")]
    assert '<span class="l-en">span</span>' in head
    assert '<span class="l-zh">跨度</span>' in head
    assert "JUN 17" in span
