"""Reproduce component screenshots from pinned stores, without publishing data.

This is component evidence, not real-route or deployment acceptance.
Run from the Macro repo root with PYTHONPATH=. and an operation-owned output dir.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess

from jinja2 import Environment, FileSystemLoader, StrictUndefined
import pandas as pd
from playwright.sync_api import sync_playwright

from lib.china_pullback_view import present, snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--asof-clock", default="2026-09-29T10:00:00+00:00")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ref = subprocess.check_output(["git", "rev-parse", args.source_ref], text=True).strip()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.fromisoformat(args.asof_clock)
    def read(group, ticker):
        raw = subprocess.check_output(["git", "show", f"{ref}:data/{group}/{ticker}.parquet"])
        return pd.read_parquet(io.BytesIO(raw))
    observed = snapshot(now=now, read=read)
    stored_ms = json.loads(subprocess.check_output(["git", "show", f"{ref}:data/china_market_state/latest.json"]))
    radar = stored_ms.get("radar") or {}
    view = present(observed, radar)
    env = Environment(loader=FileSystemLoader("templates"), undefined=StrictUndefined, autoescape=True)
    component = env.get_template("_pullback_observation.html.j2").module
    style = "\n".join(Path(p).read_text() for p in (
        "templates/theme.css", "templates/illus.css", "templates/_pullback_observation.css.j2"))
    wrapper_css = """
    body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font-ui)}
    .review{max-width:1440px;margin:auto;padding:40px 32px}
    .review>header{margin-bottom:28px}.review-kicker{font-size:11px;letter-spacing:.14em;font-weight:700;color:var(--muted)}
    .review h1{font-size:32px;letter-spacing:-.035em;margin:10px 0 12px;line-height:1.15}
    .review-source{font-size:12px;color:var(--muted);line-height:1.6}
    .review-grid{display:grid;grid-template-columns:minmax(320px,.8fr) minmax(0,1.6fr);align-items:start;gap:24px}
    .review-caption{font-size:11px;color:var(--muted);letter-spacing:.09em;margin-bottom:12px;font-weight:650}
    .review .pbx-card{height:auto;min-height:0}
    @media(max-width:800px){.review{padding:24px 16px}.review h1{font-size:28px}.review-grid{grid-template-columns:1fr;gap:32px}}
    """
    t = env.from_string("""<!doctype html><html data-theme="dark" data-lang="en" lang="en"><head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>China pullback observation · component evidence</title><style>{{ css|safe }}</style></head><body>
    <main class="review"><header><div class="review-kicker">MASTERMIND X / CHINA / RISK OBSERVATION</div>
    <h1><span class="l-en">Beyond the warning.</span><span class="l-zh">不止于风险预警。</span></h1>
    <div class="review-source"><span class="l-en">Stored snapshot · {{ asof }} · source {{ ref }} · Component preview, not a live deployment.</span><span class="l-zh">存储快照 · {{ asof }} · 来源 {{ ref }} · 组件预览，非线上部署。</span></div></header>
    <div class="review-grid"><div><div class="review-caption"><span class="l-en">01 / THE GLANCE</span><span class="l-zh">01 / 一眼读懂</span></div>{{ card|safe }}</div>
    <div id="detail"><div class="review-caption"><span class="l-en">02 / THE EVIDENCE</span><span class="l-zh">02 / 证据详情</span></div>{{ detail|safe }}</div></div></main></body></html>""")
    html = t.render(css=style + wrapper_css, asof=observed["asof"], ref=ref[:12],
                    card=component.card(view), detail=component.detail(view))
    (out / "component-preview.html").write_text(html)
    (out / "observation.json").write_text(json.dumps(observed, indent=2, ensure_ascii=False, allow_nan=False))
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for width in (1440, 390):
                for theme in ("dark", "light"):
                    for lang in ("en", "zh"):
                        page = browser.new_page(viewport={"width": width, "height": 1000}, device_scale_factor=1,
                                                reduced_motion="reduce")
                        errors = []
                        page.on("pageerror", lambda e: errors.append(str(e)))
                        page.set_content(html, wait_until="load")
                        page.evaluate("([t,l])=>{document.documentElement.dataset.theme=t;document.documentElement.dataset.lang=l;document.documentElement.lang=l}", [theme, lang])
                        page.add_script_tag(content=Path("templates/_pullback_observation.js.j2").read_text())
                        page.wait_for_timeout(80)
                        metrics = page.evaluate("""() => ({
                          overflow: document.documentElement.scrollWidth > innerWidth,
                          ids: [...document.querySelectorAll('[id]')].map(e=>e.id),
                          pathCount: document.querySelectorAll('.pbx .ilx-path').length,
                          cardHeight: document.querySelector('.pbx-card').getBoundingClientRect().height,
                          cardPadding: parseFloat(getComputedStyle(document.querySelector('.pbx-card')).paddingLeft),
                          cardRadius: parseFloat(getComputedStyle(document.querySelector('.pbx-card')).borderTopLeftRadius),
                          buttonHeight: document.querySelector('.pbx-open').getBoundingClientRect().height,
                          chartLabel: document.querySelector('.pbx .ilx').getAttribute('aria-label'),
                          nonfinitePaths: [...document.querySelectorAll('.pbx svg path')].some(e=>/NaN|Infinity/.test(e.getAttribute('d')||''))
                        })""")
                        assert not metrics["overflow"], (width, theme, lang, "overflow")
                        assert len(metrics["ids"]) == len(set(metrics["ids"])), "duplicate DOM IDs"
                        assert metrics["pathCount"] >= 2 and not metrics["nonfinitePaths"]
                        assert metrics["buttonHeight"] >= 44
                        assert metrics["cardPadding"] >= 16 and metrics["cardRadius"] >= 14
                        assert not errors, errors
                        page.locator('.pbx-method summary').focus()
                        page.keyboard.press('Enter')
                        assert page.locator('.pbx-method').get_attribute('open') is not None
                        page.keyboard.press('Enter')
                        page.locator('.pbx-method summary').evaluate('e=>e.blur()')
                        image = out / f"component-{theme}-{lang}-{width}.png"
                        page.screenshot(path=str(image), full_page=True)
                        checks.append({"width": width, "theme": theme, "language": lang,
                                       **metrics, "errors": errors, "image": image.name,
                                       "image_sha256": sha256(image.read_bytes()).hexdigest()})
                        # Deterministic expiry exercise: no new producer or polling.
                        page.locator('[data-pb-valid-until]').evaluate_all("els=>els.forEach(e=>e.setAttribute('data-pb-valid-until','2000-01-01T00:00:00Z'))")
                        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
                        assert page.locator('.pbx-card').evaluate("e=>e.classList.contains('pb-expired')")
                        assert not page.locator('.pbx-card .pbx-current').is_visible()
                        page.close()
        finally:
            browser.close()
    report = {"kind": "component_browser_evidence", "not_live_deployment_proof": True,
              "source_ref": ref, "observed_clock": now.isoformat(),
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "phase": observed["phase"], "primary_drawdown_pct": observed["drawdown_pct"],
              "radar_source_asof": stored_ms.get("asof"), "checks": checks}
    (out / "component-browser-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({"output": str(out), "variants_passed": len(checks),
                      "source_ref": ref, "phase": observed["phase"],
                      "drawdown_pct": observed["drawdown_pct"], "not_live_deployment_proof": True}))


if __name__ == "__main__":
    main()
