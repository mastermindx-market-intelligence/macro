"""Render the real basket-detail template with source-bound persisted inputs.

Local browser proof only: no live account, no production write, no external
network. The stored DETAIL carries the real holdings/history; only the matched
producer explanation changes. Existing static assets and UI are unmodified.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import mimetypes
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from prove import read_blob, replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report, payload = replay(args.source_ref)
    themes = {row["id"]: row for row in payload["theme_intel"]["themes"]}
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    template = env.get_template("basket_detail.html.j2")
    baseline_source = read_blob(args.source_ref, "templates/basket_detail.html.j2")
    baseline_env = Environment(loader=ChoiceLoader([
        DictLoader({"basket_detail.html.j2": baseline_source.decode()}),
        FileSystemLoader(str(ROOT / "templates")),
    ]), autoescape=True)
    baseline_template = baseline_env.get_template("basket_detail.html.j2")
    pages, expected, page_sources = {}, {}, {}
    for name in ("ai_semiconductors", "cybersecurity", "mag7"):
        path = f"site/basket/{name}.html"
        raw = read_blob(args.source_ref, path)
        html = raw.decode()
        marker = "const DETAIL = "
        detail, _ = json.JSONDecoder().raw_decode(html.split(marker, 1)[1])
        assert detail["as_of"] == payload["theme_intel"]["as_of"]
        for key in ("id", "rank", "score", "reco", "components", "textures"):
            assert detail["theme"].get(key) == themes[name].get(key), (name, key)
        for version in ("baseline", "candidate"):
            source = deepcopy(detail)
            if version == "candidate":
                for key in ("reco_why_en", "reco_why_zh", "reco_reason_code", "reco_base_reason_code"):
                    source["theme"][key] = themes[name][key]
            chosen_template = template if version == "candidate" else baseline_template
            generated = chosen_template.render(
                detail_json=json.dumps(source, separators=(",", ":"), ensure_ascii=False),
                basket_name=source["basket"]["name"], generated_utc="Frozen source proof",
                back_href=source["back"], back_label_en="Sector Intelligence", back_label_zh="行业智慧")
            url = f"/basket/{name}-{version}.html"
            pages[url] = generated.encode()
            expected[url] = {"en": source["theme"].get("reco_why_en"),
                             "zh": source["theme"].get("reco_why_zh")}
            page_sources[url] = {"input": path, "input_sha256": hashlib.sha256(raw).hexdigest(),
                                 "rendered_sha256": hashlib.sha256(pages[url]).hexdigest(),
                                 "source_as_of": source.get("as_of")}
    observations = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for theme in ("dark", "light"):
            for language in ("en", "zh"):
                for width in (1440, 390):
                    context = browser.new_context(viewport={"width": width, "height": 1000},
                                                  device_scale_factor=1, locale="en-US")
                    context.add_init_script("localStorage.setItem('theme'," + json.dumps(theme) +
                                            ");localStorage.setItem('lang'," + json.dumps(language) + ");")
                    requests = []
                    def route(request):
                        parsed = urlsplit(request.request.url)
                        path = unquote(parsed.path)
                        requests.append(path)
                        if parsed.hostname != "proof.local":
                            request.fulfill(status=204, body="")
                        elif path in pages:
                            request.fulfill(status=200, content_type="text/html", body=pages[path])
                        elif path.startswith(("/live/", "/api/")):
                            # A Git snapshot is not the live quote owner. Exercise
                            # the existing unavailable-feed path rather than mix
                            # an old tracked pulse into this dated reason proof.
                            request.fulfill(status=404, body="Live feed outside frozen evidence")
                        else:
                            target = (ROOT / "site" / path.lstrip("/")).resolve()
                            if target.is_relative_to((ROOT / "site").resolve()) and target.is_file():
                                request.fulfill(status=200, content_type=mimetypes.guess_type(str(target))[0] or "application/octet-stream",
                                                body=target.read_bytes())
                            else:
                                request.fulfill(status=404, body="Not part of frozen local evidence")
                    context.route("**/*", route)
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    for name in ("ai_semiconductors", "cybersecurity", "mag7"):
                        for version in ("baseline", "candidate"):
                            path = f"/basket/{name}-{version}.html"
                            page.goto("http://proof.local" + path, wait_until="networkidle")
                            page.wait_for_selector("#app .hero", timeout=15000)
                            actual = page.locator("#app .hero").inner_text()
                            wanted = expected[path][language]
                            # Old positive/no-entry payloads intentionally use the
                            # cautious legacy fallback instead of their old add text.
                            if version == "candidate":
                                assert wanted in actual, (path, theme, language, wanted, actual)
                                assert "no member has a clean entry" not in actual
                                assert "very extended (RS" not in actual
                            attrs = page.evaluate("({theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang,width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+2})")
                            assert attrs["theme"] == theme and attrs["lang"] == language
                            filename = f"{name}-{version}-{width}-{theme}-{language}.png"
                            page.screenshot(path=str(args.out / filename), full_page=False)
                            observations.append({"name": name, "version": version, "width": width,
                                                 "theme": theme, "language": language, "applied": attrs,
                                                 "file": filename, "visible_reason": wanted if version == "candidate" else None,
                                                 "hero_text": actual, "page_errors": list(errors),
                                                 **page_sources[path]})
                            errors.clear()
                    context.close()
        browser.close()
    result = {"source_ref": args.source_ref, "producer_proof": report,
              "baseline_template_sha256": hashlib.sha256(baseline_source).hexdigest(),
              "live_feeds": "unavailable_by_fixture; never substituted with old tracked quotes",
              "template_sha256": hashlib.sha256((ROOT / "templates/basket_detail.html.j2").read_bytes()).hexdigest(),
              "cells": observations,
              "limitations": ["Local browser only; no production or authentication proof.",
                              "Real stored holdings/history with matched explanatory-field replay, not a full nightly.",
                              "Baseline uses the pinned original template and original stored explanation; shared assets are unchanged."]}
    (args.out / "browser-proof.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps({"cells": len(observations), "candidate_reasons_visible": True,
                      "cells_with_page_errors": sum(bool(x["page_errors"]) for x in observations),
                      "cells_with_page_overflow": sum(x["applied"]["overflow"] for x in observations)}))


if __name__ == "__main__":
    main()
