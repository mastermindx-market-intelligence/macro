"""D03 T48 public Featured access card: template source and real-browser contract.

This fixture renders the *actual* template branch and scoped CSS with shared
theme tokens. It never uses private snapshots or a live authenticated account.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment
from markupsafe import Markup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/dashboard.html.j2"
THEME = ROOT / "templates/theme.css"


def _card_fixture() -> str:
    source = TEMPLATE.read_text()
    assert "{%- elif _today_total > 0 %}" in source
    fragment = source.split("{%- elif _today_total > 0 %}", 1)[1].split(
        "{%- else %}", 1
    )[0]
    scoped = source.split("/* D03 T48:", 1)[1].split(
        "/* count chips row", 1
    )[0]

    def tr(en: str, zh: str) -> Markup:
        from html import escape
        return Markup(
            '<span class="l-en">' + escape(en) + '</span>'
            + '<span class="l-zh">' + escape(zh) + '</span>'
        )

    card = Environment(autoescape=True).from_string(fragment).render(t=tr)
    assert 'class="mx-empty mx-today-access-empty"' in card
    assert 'role="region" aria-labelledby="us-featured-empty-title"' in card
    assert "mx-empty-line" in card and "mx-empty-why" in card
    assert "USProphetSource.set('candidates')" in card
    assert "setup" in card.lower() and "access" in card.lower()
    assert "Save" in card
    # Existing access-denied / genuine-no-source distinction must remain.
    later = source.split("{%- elif _today_total > 0 %}", 1)[1]
    assert "{%- else %}" in later and "No Featured setups on this board." in later

    # Live shared theme tokens + exactly the scoped source CSS; no replica palette.
    css = THEME.read_text() + "\n/* D03 T48:" + scoped
    return (
        '<!doctype html><html data-theme="{theme}" data-lang="{lang}"><head>'
        '<meta charset="utf-8"><style>' + css + '</style></head>'
        '<body class="page-stocks" style="background:var(--bg);color:var(--text)">'
        '<section id="us-today" style="max-width:100%">' + card
        + '</section><script>'
        'window.USProphetSource={set:function(key){window.__selected=key}};'
        '</script></body></html>'
    )


def _lum(c: list[float]) -> float:
    ch = [x / 255 for x in c[:3]]
    ch = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in ch]
    return .2126 * ch[0] + .7152 * ch[1] + .0722 * ch[2]


def _rgb(css: str) -> list[float]:
    import re
    values = re.findall(r"[0-9.]+", css)
    assert len(values) >= 3, css
    return [float(x) for x in values[:3]]


def _contrast(a: str, b: str) -> float:
    x, y = _lum(_rgb(a)), _lum(_rgb(b))
    return (max(x, y) + .05) / (min(x, y) + .05)


@pytest.mark.parametrize("width", [320, 390])
@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_featured_access_empty_card_browser(width: int, theme: str, lang: str):
    document = _card_fixture().replace('{theme}', theme).replace('{lang}', lang)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content(document, wait_until="domcontentloaded")
        card = page.locator(".mx-today-access-empty")
        assert card.is_visible()
        expected_name = ("Featured setups are outside this preview." if lang == "en"
                         else "精选形态不在当前预览范围内。")
        assert page.get_by_role("region", name=expected_name).count() == 1
        assert page.locator(".mx-today-access-cta").is_visible()
        assert page.locator(".mx-today-access-cta").evaluate(
            "(e) => e.getBoundingClientRect().height"
        ) >= 44
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator(".mx-today-access-mark .l-" + lang).is_visible()
        assert not page.locator(
            ".mx-today-access-mark .l-" + ("zh" if lang == "en" else "en")
        ).is_visible()
        colors = page.evaluate("""() => {
          const card=document.querySelector('.mx-today-access-empty');
          const names=['.mx-today-access-mark','.mx-empty-line','.mx-empty-why',
            '.mx-today-access-cta','.mx-today-access-caption'];
          return names.map(n=>{
            const e=card.querySelector(n), s=getComputedStyle(e);
            let b=getComputedStyle(card).backgroundColor;
            if(s.backgroundColor!=='rgba(0, 0, 0, 0)'
               && s.backgroundColor!=='transparent') b=s.backgroundColor;
            return [n,s.color,b];
          });
        }""")
        for name, fg, bg in colors:
            assert _contrast(fg, bg) >= 4.5, (width, theme, lang, name, fg, bg)
        page.locator(".mx-today-access-cta").focus()
        assert page.locator(".mx-today-access-cta").evaluate(
            "(e)=>document.activeElement===e"
        )
        page.locator(".mx-today-access-cta").click()
        assert page.evaluate("window.__selected") == "candidates"
        assert not errors, errors
        browser.close()
