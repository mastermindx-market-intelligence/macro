"""Synthetic-state browser proof of #8026, not production or trading proof."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from engine.i18n import tr as source_tr

SEMANTIC = "c0105788547986e4937e3ae187098d979b85a7c7"
HOST = "88a3f1cfd18f391d2802e9086dc00f6fe5545607"
OUT = Path(__file__).resolve().parent / "browser"
OUT.mkdir(exist_ok=True)
def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])
def digest(data):
    return hashlib.sha256(data).hexdigest()
paths = ("engine/china_act_now.py", "templates/_china_act_now_board.html.j2",
         "templates/_decision_card.html.j2", "templates/theme.js",
         "tests/test_china_act_now.py")
source_hashes = {}
for path in paths:
    data = (ROOT / path).read_bytes()
    assert data == git("show", f"{SEMANTIC}:{path}"), path
    source_hashes[path] = digest(data)
fixtures = runpy.run_path(str(ROOT / "tests/test_china_act_now.py"))
fixture = fixtures["_emerging_enter_fixture"]
assemble = fixtures["_emerging_enter_board"]
current = fixture()
missing = fixture()
missing["themes"][0]["observation"] = None
states = {"continuing-enter": current, "initial-entry": fixture(clean=True),
          "final-hold": fixture(final="hold"), "unavailable": missing}
expected_lanes = {"continuing-enter": "buy_now", "initial-entry": "buy_now",
                  "final-hold": "wait_pullback", "unavailable": "wait_pullback"}
host_raw = git("show", f"{HOST}:site/china.html")
host = BeautifulSoup(host_raw, "html.parser")
css_paths = [x["href"].split("?")[0] for x in host.select('link[rel="stylesheet"]')]
assert all("://" not in p and ".." not in p for p in css_paths)
css_parts = {p: git("show", f"{HOST}:site/{p}") for p in css_paths}
css = "\n".join(v.decode() for v in css_parts.values())
body_class = " ".join(host.body.get("class", []))
env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
js = (ROOT / "templates/theme.js").read_text()
report = {"proof_kind": "synthetic-state component browser; NOT production",
          "semantic_head": SEMANTIC, "host_css_commit": HOST,
          "qualification_clock": "2026-09-21T10:00:00+00:00 (synthetic)",
          "source_sha256": source_hashes, "host_sha256": digest(host_raw),
          "css_sha256": {p: digest(v) for p, v in css_parts.items()},
          "limitations": ["No historical or current stock recommendation",
                          "No authenticated/full-page production proof",
                          "External requests blocked; existing host CSS reused"],
          "captures": [], "popovers": []}
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    try:
        for state, intel in states.items():
            original = deepcopy(intel)
            view = assemble(intel)
            assert intel == original
            lane = expected_lanes[state]
            row, = view["display_lanes"][lane]
            assert row["theme_decision"]["stock_entry_permission"] is False
            if state == "continuing-enter":
                assert row["entry_route"] == "theme_enter"
                assert view["lanes"]["buy_now"] == []
                assert len(view["lanes"]["wait_pullback"]) == 1
            for theme in ("dark", "light"):
                for lang in ("en", "zh"):
                    env.globals.update(t=lambda en, zh, lng=lang: zh if lng == "zh" else en,
                                       tr=source_tr, help=lambda *a, **kw: "")
                    component = env.get_template("_china_act_now_board.html.j2").render(
                        act_now_v2=view, sectors_by_ticker={})
                    for width in (1440, 390):
                        page = browser.new_page(viewport={"width": width, "height": 960})
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.route("**/*", lambda route: route.abort())
                        html = (f'<!doctype html><html lang="{lang}" data-lang="{lang}" '
                                f'data-theme="{theme}"><head><meta charset="utf-8">'
                                f'<style>{css}</style></head><body class="{body_class}">'
                                f'<main>{component}</main><script>{js}</script></body></html>')
                        page.set_content(html, wait_until="domcontentloaded")
                        page.evaluate('(x) => { document.documentElement.dataset.theme=x[0]; '
                                      'document.documentElement.dataset.lang=x[1]; }', [theme, lang])
                        board = page.locator("#act-now")
                        board.wait_for(state="visible")
                        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                        assert not overflow and not errors, (state, theme, lang, width, errors)
                        file = f"{state}-{theme}-{lang}-{width}.png"
                        board.screenshot(path=str(OUT / file))
                        report["captures"].append({"state": state, "theme": theme,
                            "language": lang, "width": width, "file": file,
                            "sha256": digest((OUT / file).read_bytes()),
                            "overflow": overflow, "page_errors": list(errors)})
                        target = "#anv2-buy" if lane == "buy_now" else "#anv2-pull"
                        page.locator(target + " .anv2-row a").first.focus()
                        pop = page.locator('.row-pop[role="tooltip"]')
                        pop.wait_for(state="visible")
                        text = pop.inner_text()
                        if state == "continuing-enter":
                            expected = "主题建仓判断仍然有效" if lang == "zh" else "Theme entry remains open"
                            caveat = "个股择时独立判断" if lang == "zh" else "Individual stock timing is separate"
                            assert expected in text and caveat in text, text
                            assert not page.locator('#anv2-pull [data-entry-route="theme_enter"]').count()
                        if state == "unavailable":
                            expected = "当前输入暂缺" if lang == "zh" else "Current inputs unavailable"
                            assert expected in text and pop.locator(".row-pop-score").count() == 0
                        bounds = pop.bounding_box()
                        assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width
                        assert not errors, errors
                        popfile = "hover-" + file
                        pop.screenshot(path=str(OUT / popfile))
                        report["popovers"].append({"state": state, "theme": theme,
                            "language": lang, "width": width, "file": popfile,
                            "sha256": digest((OUT / popfile).read_bytes()), "text": text,
                            "bounds": bounds, "page_errors": list(errors)})
                        page.close()
    finally:
        browser.close()
for path, expected in source_hashes.items():
    assert digest((ROOT / path).read_bytes()) == expected, "source moved during proof: " + path
report["harness_sha256"] = digest(Path(__file__).read_bytes())
(OUT / "proof.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"semantic_head": SEMANTIC, "board_captures": len(report["captures"]),
                  "keyboard_popovers": len(report["popovers"]),
                  "page_errors": sum(len(x["page_errors"]) for x in report["captures"]),
                  "overflows": sum(x["overflow"] for x in report["captures"]),
                  "receipt_sha256": digest((OUT / "proof.json").read_bytes())}))
