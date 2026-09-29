"""Render and capture real-template PRI-C1 evidence cells."""
from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.us_candidate_lanes import project_candidate_visibility
from scripts.build_site import _plan_relations_for
from tests.test_dashboard_template_render import _base_vm, _board_row, _env, _prophet_book

VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
PLV_EXPECTATIONS = {
    "fixture_plv_today.html": (
        "today", {"en": "quotes as of 10:12 am ET", "zh": "报价截至 美东 10:12"}),
    "fixture_plv_prior.html": (
        "prior_day", {"en": "last read Jul 29, 4:12 pm ET", "zh": "上次判读 07-29 美东 16:12"}),
    "fixture_plv_unavailable.html": (
        "unavailable", {"en": "quote time unavailable", "zh": "报价时间不可用"}),
}
PAINT_JS = """([theme, locale]) => {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.dataset.lang = locale;
  root.lang = locale;
}"""
MEASURE_JS = """() => {
  const parse = (value) => {
    const match = String(value || '').match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
    return match ? [Number(match[1]), Number(match[2]), Number(match[3])] : [255, 255, 255];
  };
  const luminance = ([r, g, b]) => {
    const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const style = getComputedStyle(document.body);
  const english = document.querySelector('.l-en');
  const chinese = document.querySelector('.l-zh');
  const visible = (node) => !!node && getComputedStyle(node).display !== 'none';
  return {
    paintedTheme: luminance(parse(style.backgroundColor)) < 0.5 ? 'dark' : 'light',
    paintedLocale: visible(chinese) && !visible(english) ? 'zh' : (visible(english) ? 'en' : null),
    bg: style.backgroundColor,
  };
}"""
PLV_ASSERT_JS = """([expectedState, expectedText]) => {
  const asOf = document.querySelector('#plv-asof');
  const target = document.querySelector('#prophet-live');
  if (!asOf || !target) throw new Error('PLV as-of or target is missing');
  if (asOf.dataset.plvAsofState !== expectedState) {
    throw new Error(`PLV state is ${asOf.dataset.plvAsofState}, expected ${expectedState}`);
  }
  const text = asOf.textContent || '';
  if (!text.trim()) throw new Error('PLV as-of text is empty');
  if (!text.includes(expectedText)) {
    throw new Error(`PLV as-of text ${JSON.stringify(text)} lacks ${JSON.stringify(expectedText)}`);
  }
  const asBox = asOf.getBoundingClientRect();
  const targetBox = target.getBoundingClientRect();
  if (asBox.left < targetBox.left || asBox.right > targetBox.right ||
      asBox.top < targetBox.top || asBox.bottom > targetBox.bottom) {
    throw new Error('PLV as-of bounding box is outside #plv-panel');
  }
  return true;
}"""


def png_dimensions(data: bytes) -> tuple[int, int]:
    return struct.unpack(">II", data[16:24])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def base_vm():
    vm = _base_vm()
    related = _board_row(
        ticker="LFUS", name="LFUS", lane=None, dossier=None, featured=True,
        stage="setting_up", entry_signal={"status": "watch", "headline": "Wait for the base"},
        signal={}, hold={},
    )
    unrelated = _board_row(
        ticker="AAA", name="AAA", lane=None, dossier=None, featured=True,
        stage="setting_up", entry_signal={"status": "watch", "headline": "Wait for the base"},
        signal={}, hold={},
    )
    related["signal_asof"] = "2026-09-25"
    unrelated["signal_asof"] = "2026-09-25"
    vm["us_standouts"] = {"buy": [related, unrelated], "eligible": 2}
    vm["us_prophet_book"] = _prophet_book(
        [{
            "id": "LFUS-BULL-20260810", "asset": " lfus ", "lifecycle_state": "entered",
            "entry_status": "buy_now", "board_read": None, "_priority_score": 72.0,
            "entry_zone": None, "entry_zone_state": None, "closed": False,
            "plan_asof": "2026-08-16", "recorded_at": "2026-08-16",
            "entry_date": "2026-08-10", "signal_date": "2026-08-15",
            "formation_date": "2026-08-10",
        }],
        asof="2026-09-24", source_board_asof="2026-09-23",
    )
    vm["us_prophet_book"]["source_asof"] = "2026-09-25"
    state, by_ticker = _plan_relations_for(vm["us_prophet_book"], False)
    vm["plan_rel"] = {"state": state, "plans": []}
    vm["plan_rel_by_ticker"] = by_ticker

    def pool_row(ticker, rank):
        return {
            "ticker": ticker, "name": ticker, "sector": "Industrials", "pool_rank": rank,
            "in_buy_lane": True, "lane": "bottoming", "headline_reason": "already_open",
            "lane_reasons": ["cleared_admission", "already_open"], "tier_cascade": None,
            "admission_class": None, "prophet_score_basis": None, "prophet": None,
        }

    vm["us_candidate_visibility"] = project_candidate_visibility({
        "as_of": "2026-09-24",
        "candidate_pool": {"as_of": "2026-09-24", "pool_definition": "us_candidate_pool_v1",
                           "eligible": 2, "rows": [pool_row("LFUS", 1), pool_row("AAA", 2)]},
    })
    return vm


def render_base() -> str:
    html = _env().get_template("dashboard.html.j2").render(**base_vm(), mode="stocks")
    soup = BeautifulSoup(html, "html.parser")
    assert soup.select_one('.pvs-plan-relation[data-plan-relation="related_security"]')
    assert soup.select_one('.pvs-plan-relation[data-plan-relation="none"]')
    assert soup.select_one("#us-plan-book-asof")
    assert soup.select_one("#plv-asof")
    for selector in ("details.pvs-audit", "#us-candidate-pool details", "details.ucp-receipt",
                     "details.pv-setup-inline"):
        for node in soup.select(selector):
            node["open"] = ""
    for script in list(soup.find_all("script")):
        text = script.string or script.get_text()
        if not any(key in text for key in ("USProphetSource", "_plvRender", "setLang", "setTheme", "pv-setup-dialog")):
            script.decompose()
    for external in soup.find_all(["link", "script"]):
        href = external.get("href") or external.get("src") or ""
        if href.startswith("/") and not href.startswith("//"):
            external["href" if external.name == "link" else "src"] = href[1:]
    style = soup.new_tag("style")
    style.string = "body{margin:0;background:var(--bg);color:var(--text)} #content{display:block !important;margin:16px auto;max-width:1180px;padding:0 16px} #plv-panel{display:block !important;margin:12px 0} #us-today{display:block !important;visibility:visible !important;opacity:1 !important}"
    soup.head.append(style)
    theme = soup.new_tag("script", src="theme.js")
    soup.body.append(theme)
    return str(soup)


def with_script(base: str, script: str) -> str:
    soup = BeautifulSoup(base, "html.parser")
    node = soup.new_tag("script")
    node.string = script
    live = next(item for item in soup.find_all("script")
                if item.string and "_plvFetch" in item.string)
    live.insert_before(node)
    return str(soup)


def plv_page(base: str, quote_asof: str | None) -> str:
    payload = {
        "schema": "prophet_live.states/v1", "status": "live", "states": {},
        "meta": {"session_et": "2026-09-29"},
    }
    if quote_asof is not None:
        payload["meta"]["quote_asof"] = quote_asof
    script = (
        "(function(){var payload=" + json.dumps(payload, separators=(",", ":")) +
        ";var nativeFetch=window.fetch.bind(window);window.fetch=function(url,options){"
        "if(String(url).indexOf('live/prophet_live.json')!==-1){"
        "return Promise.resolve(new Response(JSON.stringify(payload),{status:200,headers:{'Content-Type':'application/json'}}));}"
        "return nativeFetch(url,options);};})();"
    )
    return with_script(base, script)


def prepare_site(site: Path) -> dict[str, str]:
    base = render_base()
    pages = {
        "fixture.html": base,
        "fixture_dialog.html": base,
        "fixture_plans.html": with_script(base, "window.addEventListener('load', function(){window.USProphetSource.set('plans');});"),
        "fixture_plv_today.html": plv_page(base, "2026-09-29T14:12:00Z"),
        "fixture_plv_prior.html": plv_page(base, "2026-07-29T20:12:00Z"),
        "fixture_plv_unavailable.html": plv_page(base, None),
    }
    for asset in ("theme.css", "theme.js"):
        source = ROOT / "templates" / asset
        (site / asset).write_bytes(source.read_bytes())
    for name, html in pages.items():
        (site / name).write_text(html, encoding="utf-8")
    return pages


def capture() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=ROOT).strip()
    with tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"]) as temporary:
        site = Path(temporary) / "site"
        site.mkdir()
        pages = prepare_site(site)
        from playwright.sync_api import sync_playwright
        pages_out = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            for page_id in pages:
                states = []
                for viewport, (width, height) in VIEWPORTS.items():
                    page.set_viewport_size({"width": width, "height": height})
                    for locale in ("en", "zh"):
                        for theme in ("dark", "light"):
                            page.goto((site / page_id).as_uri(), wait_until="domcontentloaded")
                            page.evaluate(PAINT_JS, [theme, locale])
                            page.wait_for_timeout(250)
                            measured = page.evaluate(MEASURE_JS)
                            if measured["paintedTheme"] != theme:
                                raise RuntimeError(f"{page_id}: painted {measured['paintedTheme']} not {theme}")
                            if measured["paintedLocale"] != locale:
                                raise RuntimeError(f"{page_id}: painted {measured['paintedLocale']} not {locale}")
                            if page_id in PLV_EXPECTATIONS:
                                expected_state, expected_by_locale = PLV_EXPECTATIONS[page_id]
                                page.evaluate(PLV_ASSERT_JS, [expected_state, expected_by_locale[locale]])
                            target = page.locator("#us-today").first
                            if page_id in PLV_EXPECTATIONS:
                                target = page.locator("#prophet-live").first
                            if page_id == "fixture_dialog.html":
                                page.evaluate("document.getElementById('us-standouts').setAttribute('data-prophet-src','candidates'); window.USProphetSource.set('candidates')")
                                page.evaluate("document.getElementById('us-candidate-pool').open = true")
                                page.evaluate("document.querySelector('#us-candidate-pool .pv-setup-inline [data-native-id=\"LFUS\"]').closest('details').querySelector('summary').click()")
                                page.wait_for_selector("#pv-setup-dialog[open]", timeout=5000)
                                page.wait_for_timeout(150)
                                target = page.locator("#pv-setup-dialog").first
                            target.scroll_into_view_if_needed(timeout=8000)
                            filename = f"{page_id[:-5]}_{theme}_{locale}_{viewport}.png"
                            output = EVIDENCE / filename
                            target.screenshot(path=str(output))
                            data = output.read_bytes()
                            png_width, png_height = png_dimensions(data)
                            states.append({
                                "viewport": viewport, "locale": locale, "theme": theme,
                                "access": "anonymous", "viewport_width": width, "viewport_height": height,
                                "force_state": None, "captured": True, "file": filename,
                                "sha256": sha256(data), "bytes": len(data),
                                "width": png_width, "height": png_height,
                                "applied_theme": measured["paintedTheme"],
                                "applied_locale": measured["paintedLocale"],
                                "computed_bg": measured["bg"],
                            })
                pages_out.append({
                    "page_id": page_id,
                    "route": f"/{page_id}",
                    "states": states,
                    "page_tree_sha": subprocess.check_output(
                        ["git", "hash-object", "--stdin"], input=pages[page_id], text=True,
                        cwd=ROOT).strip(),
                    "gaps": [],
                })
            browser.close()
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_affordances": [
            "details.pvs-audit, the #us-candidate-pool details element, details.ucp-receipt, and details.pv-setup-inline are forced open by render_fixture.py::render_base only so folded content is visible in the crops.",
            "Those details elements are collapsed by default in production.",
            "The view model is synthetic fixture data from render_fixture.py::base_vm; it is not a production board.",
        ],
        "provenance": {
            "superseded_capture": "4a1e829ef70879d58e317c65065596bee15fc3d0",
            "superseded_at": "2026-09-29T15:57Z",
            "superseded_reasons": [
                "R4-1 changed the none-state plan-relation copy.",
                "R4-3 used the wrong screenshot target for the PLV states.",
            ],
        },
        "capture_head": head,
        "target": {"resolved_sha_or_none": head},
        "pages": pages_out,
    }
    (EVIDENCE / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"captured {sum(len(page['states']) for page in pages_out)} cells at {head}")


if __name__ == "__main__":
    capture()
