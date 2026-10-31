"""The crawl hub claims only what the catalog supports.

`site/research/index.html` described itself as "buy-side and sell-side reports from
111 institutions, indexed by desk" — but the builder groups by INSTITUTION
(`scripts/build_research_pages.py` `build()`, `by_inst.setdefault(n["inst"], …)`),
`items[].desk` is filled for 15 records, and `items[].side` has three values
(sell / independent / buy), not two. The same page had no date at all, so a reader
could not tell how recent a multi-thousand-report archive was; the catalog's own
`generated_at` was loaded and then discarded.

Fixtures are synthetic and inline; the committed catalog is never a fixture. The
`generated_at` value below is the shape of the committed one.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

GENERATED_AT = "2026-10-19T08:48:02.670798+00:00"   # shape of the committed stamp
AS_OF = "Oct 19, 2026"

_GROUPS = [
    {"inst": "J.P. Morgan", "reports": [
        {"title": "Afternoon Briefing Oct 14", "slug": "afternoon-briefing-a7588c",
         "date_disp": "Oct 15, 2026"}]},
    {"inst": "Institutional desk", "reports": [
        {"title": "Cross Border M&A Flow Update", "slug": "cross-border-fa3dbd",
         "date_disp": "Sep 22, 2026"}]},
]

_ITEMS = [
    {"id": "marketdesk-2vgkwavht24-a7588c",
     "title": "JPM US Market Intelligence | Afternoon Briefing Oct 14",
     "institution": "J.P. Morgan", "side": "sell",
     "published_at": "2026-10-15T08:52:07Z", "pages": 14, "language": "en",
     "summary_points": ["CPI Surprise & Inflation Pressure."]},
    {"id": "marketdesk-3bhwj6ebg0t-fa3dbd",
     "title": "GS Fishman Cross Border M&A Flow Update 22 Sep 2026",
     "institution": "S&T", "side": "sell",
     "published_at": "2026-09-22T06:14:00Z", "pages": None, "language": None,
     "summary_points": []},
]


def _render(as_of: str | None = None, groups: list[dict] | None = None) -> str:
    env = Environment(loader=FileSystemLoader("templates"),
                      autoescape=True, trim_blocks=True, lstrip_blocks=True)
    kw = {"groups": _GROUPS if groups is None else groups, "total": 2,
          "canonical": "https://www.mastermind-x.com/research/index.html",
          "site_base": "https://www.mastermind-x.com"}
    if as_of is not None:
        kw["as_of"] = as_of
    return env.get_template("research_index.html.j2").render(**kw)


def _build_index(monkeypatch, tmp_path: Path, catalog: dict) -> str:
    """Run the real builder with every write redirected into tmp_path/a recorder.

    `build()` mkdirs `RESEARCH_DIR` (= `site/research`) and rewrites `SITEMAP`
    (= `site/sitemap.xml`), and `lib.pages.write_page` copies a shim asset into
    `site/`. A lane must never write under `site/`, so all three are redirected;
    the render path itself is the shipped one.
    """
    from scripts import build_research_pages as rp

    written: dict[str, str] = {}

    def _record(path, html, *, encoding=None):
        written[Path(path).name] = html
        return Path(path)

    monkeypatch.setattr(rp, "RESEARCH_DIR", tmp_path / "research")
    monkeypatch.setattr(rp, "SITEMAP", tmp_path / "sitemap.xml")
    monkeypatch.setattr(rp, "EXCERPTS", tmp_path / "excerpts.json")
    monkeypatch.setattr("lib.pages.write_page", _record)
    assert rp.build(catalog=catalog) == len(_ITEMS)
    return written["index.html"]


def test_hub_meta_description_does_not_claim_a_desk_index():
    assert "indexed by desk" not in _render()


def test_hub_meta_description_does_not_overstate_the_institution_count():
    html = _render()
    assert re.search(r"from \d+ institutions", html) is None
    assert "111 institutions" not in html


def test_hub_prints_the_catalog_as_of_date(monkeypatch, tmp_path):
    catalog = {"generated_at": GENERATED_AT, "items": _ITEMS}
    html = _build_index(monkeypatch, tmp_path, catalog)
    assert AS_OF in html

    from scripts import build_research_pages as rp
    assert rp._fmt_date(GENERATED_AT) == AS_OF


def test_hub_renders_identically_without_a_generated_at(monkeypatch, tmp_path):
    absent = _build_index(monkeypatch, tmp_path / "a", {"items": _ITEMS})
    blank = _build_index(monkeypatch, tmp_path / "b",
                         {"generated_at": "", "items": _ITEMS})
    for html in (absent, blank):
        assert AS_OF not in html
        assert "Archive as of" not in html
        assert "存档截至" not in html
    assert absent == blank
    # a caller that passes "" gets exactly the page a caller that passes nothing
    # gets — an absent stamp changes no other byte
    assert _render(as_of="") == _render()


def test_hub_as_of_label_is_bilingual_and_never_both_visible():
    html = _render(as_of=AS_OF)
    assert f'<span class="l-en">Archive as of {AS_OF}</span>' in html
    assert f'<span class="l-zh">存档截至 {AS_OF}</span>' in html
    # the page's existing toggle contract is what keeps the two halves apart
    assert 'html:not([data-lang="zh"]) .l-zh{ display:none; }' in html
