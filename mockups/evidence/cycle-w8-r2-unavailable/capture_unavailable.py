#!/usr/bin/env python3
"""S1-rig capture of the new cycle unavailable-why surface.

4 crops: dark/light × EN/ZH at 1440. Full 8-cell matrix stays r3.
Fixture feeds the real hazardLine markup; html.cyc-page.cyc-main + bare <body>
match site/cycle.html; window.__skyDeck is seeded; decorative layers are not
mounted (theme.js/sky.js not loaded) and are CSS-hidden with a disclosed receipt.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SITE = ROOT / "site"

CDF_EN = (
    "Unavailable today — the model's short- and long-window reads disagreed, "
    "so no clean probability can be shown. The projection below still stands."
)
CDF_ZH = (
    "今日暂不可用——模型的短窗与长窗读数不一致，无法给出可靠概率。下方的推算仍然有效。"
)

OVERLAY_SELECTORS = (
    ".sky-fx",
    ".mx5-aurora",
    ".theme-fab",
    "span.disc",
    ".aurora",
)


def fixture_html(theme: str, lang: str) -> str:
    theme_href = (SITE / "theme.css").as_uri()
    cycle_href = (SITE / "cycle.css").as_uri()
    return f"""<!DOCTYPE html>
<html lang="{lang}" class="cyc-page cyc-main" data-theme="{theme}" data-lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="{theme_href}">
<link rel="stylesheet" href="{cycle_href}">
<script>window.__skyDeck = true;</script>
<style>
  /* disclosed hides — decorative layers are not mounted in this fixture;
     keep them display:none if a later include pulls them in */
  .mx5-aurora, .sky-fx, .theme-fab, .theme-switch, span.disc {{ display: none !important; }}
  html.cyc-page, html.cyc-page * {{ animation: none !important; transition: none !important; }}
</style>
</head>
<body>
<div class="cyc-wrap" id="crop-root" style="padding-top:28px;max-width:760px">
  <article class="cyc-card lit" style="--c:var(--link);margin-bottom:16px">
    <div class="cc-top">
      <div class="cc-id"><span class="cc-dot"></span>
        <div>
          <div class="cc-nm"><span class="l-en">Volatility</span><span class="l-zh">波动率</span></div>
          <div class="cc-px"><span class="l-en">MEASURED · daily tape</span><span class="l-zh">已测量 · 日频</span></div>
        </div>
      </div>
      <div class="cc-badges">
        <div class="cc-phase" style="--ph:var(--muted)"><span class="l-en">Downturn</span><span class="l-zh">回落</span></div>
      </div>
    </div>
    <div class="cc-meta">
      <div class="cc-next">
        <span class="cc-arrow">▲</span>
        <span><span class="l-en">Peak ≈ Sep ’26</span><span class="l-zh">见顶 ≈ 26年9月</span></span>
      </div>
    </div>
  </article>
  <div class="cyc-detail" style="position:relative;transform:none;height:auto;max-height:none;box-shadow:none">
    <div class="cyc-panels" style="padding:0">
      <div class="cyc-panel show" style="position:relative;inset:auto;opacity:1;visibility:visible;transform:none;display:block">
        <div class="cyc-grp cyc-grp-3" style="grid-column:auto">
          <div class="cyc-hz-headline-row">
            <div class="cc-hz-headline">
              <span class="cc-arrow">▲</span>
              <span class="l-en">Peak ≈ Sep ’26</span><span class="l-zh">见顶 ≈ 26年9月</span>
            </div>
          </div>
          <div class="cyc-hazard">
            <span class="hz-label"><span class="l-en">Turn hazard</span><span class="l-zh">转折风险</span></span>
            <span class="l-en">{CDF_EN}</span>
            <span class="l-zh">{CDF_ZH}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""


def overlay_probe(page) -> list[dict]:
    return page.evaluate(
        """(sels) => sels.map(s => {
          const el = document.querySelector(s);
          if (!el) return {selector: s, present: false, over_content: false};
          const st = getComputedStyle(el);
          const hidden = st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0';
          const r = el.getBoundingClientRect();
          return {
            selector: s,
            present: true,
            display: st.display,
            visibility: st.visibility,
            over_content: !hidden && r.width > 0 && r.height > 0
          };
        })""",
        list(OVERLAY_SELECTORS),
    )


def main() -> None:
    cases = (
        ("dark", "en"),
        ("dark", "zh"),
        ("light", "en"),
        ("light", "zh"),
    )
    rows = []
    HERE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.emulate_media(reduced_motion="reduce")
        for theme, lang in cases:
            tmp = Path(tempfile.mkdtemp()) / f"unavailable_1440_{theme}_{lang}.html"
            tmp.write_text(fixture_html(theme, lang), encoding="utf-8")
            page.goto(tmp.as_uri(), wait_until="load")
            page.wait_for_timeout(200)
            html_theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
            html_lang = page.evaluate("document.documentElement.getAttribute('data-lang')")
            body_class = page.evaluate("document.body.className")
            html_class = page.evaluate("document.documentElement.className")
            sky = page.evaluate("window.__skyDeck === true")
            overlays = overlay_probe(page)
            over_content = [o for o in overlays if o.get("over_content")]
            why = page.locator(".cyc-hazard").inner_text()
            png = HERE / f"unavailable_1440_{theme}_{lang}.png"
            page.locator("#crop-root").screenshot(path=str(png))
            rows.append(
                {
                    "file": png.name,
                    "theme": theme,
                    "lang": lang,
                    "applied_theme": html_theme,
                    "applied_lang": html_lang,
                    "html_class": html_class,
                    "body_class": body_class,
                    "skyDeck": sky,
                    "overlay_over_content": over_content,
                    "overlay_probe": overlays,
                    "why_text": why.strip(),
                }
            )
            print(f"WROTE {png.name} theme={html_theme} lang={html_lang} overlays={over_content}")
        browser.close()
    (HERE / "overlay_probe.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("DONE", len(rows), "crops")


if __name__ == "__main__":
    main()
