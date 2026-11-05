"""Real-artifact component/payload proof; NOT a production deployment or auth test."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine.us_candidate_lanes import project_candidate_visibility
from scripts import build_site as bs
from tests.test_dashboard_template_render import _env


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    source = subprocess.check_output(["git", "-C", str(ROOT), "show", args.source_ref + ":site/factordata/us_standouts.json"])
    board = json.loads(source)
    original = json.dumps(board, sort_keys=True)
    # Exact historical bytes in an isolated input fixture, never a canonical backfill.
    from engine.us_candidate_lanes import load_candidate_archive_status
    archive_path = f"data/us_prophet_rank/candidates/{board['as_of'][:7]}.parquet"
    archive_bytes = subprocess.check_output([
        "git", "-C", str(ROOT), "show", args.source_ref + ":" + archive_path])
    with tempfile.TemporaryDirectory(prefix="prophet-archive-proof-") as scratch:
        archive_file = Path(scratch) / archive_path
        archive_file.parent.mkdir(parents=True)
        archive_file.write_bytes(archive_bytes)
        archive_status = load_candidate_archive_status(board, root=Path(scratch))
    view = project_candidate_visibility(board, archive=archive_status)
    assert view["status"] == "ready", view
    assert archive_status["exact_generation_verified"] is False
    vm = {"us_candidate_visibility": view}
    override, gate, locked = bs._split_us_panels(vm, 3, gated=True)
    env = _env()
    shell = env.get_template("_us_candidate_pool.html.j2").render(us_candidate_visibility=override.get("us_candidate_visibility", view), pgate=gate)
    blocks = bs._render_us_panel_payload(env, gate, locked, vm)
    bs._write_us_payload(env, args.out, None, locked_rows=[], us_standouts=board, top_setups=None, built=board["as_of"], pgate=gate, panel_blocks=blocks)
    payload = json.loads((args.out / bs.US_PAYLOAD_DIR / bs.US_PAYLOAD_NAME).read_text())
    assert json.dumps(board, sort_keys=True) == original
    amd = next(row for row in view["rows"] if row["ticker"] == "AMD")
    assert amd["in_buy_lane"] is False and amd["prophet"] is None
    assert amd["headline_reason"] == "sector_cap_overflow"
    assert 'data-ticker="AMD"' not in shell
    assert 'data-ticker="AMD"' in payload["candidate_pool_html"]
    dashboard = (ROOT / "templates/dashboard.html.j2").read_text()
    hydrate = "function hydrateCandidatePool(html, source){" + dashboard.split("  function hydrateCandidatePool(html, source){", 1)[1].split("\n  function hydratePanels", 1)[0]
    css = (ROOT / "templates/theme.css").read_text()
    doc = '<!doctype html><html lang="en" data-lang="en" data-theme="light"><head><meta charset="utf-8"><style>' + css + '</style></head><body><main style="margin:20px;max-width:1150px">' + shell + '</main></body></html>'
    (args.out / "preview.html").write_text(doc)
    # theme.css imports this existing asset; keep the local capture network-complete.
    (args.out / "product-nav-icons.css").write_bytes(
        (ROOT / "templates/product-nav-icons.css").read_bytes())
    receipt = {"source_ref": args.source_ref, "source_sha256": hashlib.sha256(source).hexdigest(),
        "source_path": "site/factordata/us_standouts.json", "board_as_of": board["as_of"],
        "proof_scope": "real artifact -> production projection/split/payload -> browser component; auth response simulated; NOT deployed",
        "counts": view["counts"], "preview": len(override["us_candidate_visibility"]["rows"]),
        "protected_tail": len(locked["candidate_pool"]), "amd": amd, "board_bytes_unchanged": True, "browser": []}
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_content(doc)
        page.add_script_tag(content=hydrate)
        root = page.locator('#us-candidate-pool')
        root.locator(':scope > summary').focus()
        page.keyboard.press('Enter')
        assert root.get_attribute('open') is not None
        assert root.locator('.ucp-row').count() == 3
        page.evaluate('hydrateCandidatePool("")')
        assert root.locator('.ucp-more').count() == 1
        # Mixed generation or partial tails must not mutate the preview.
        wrong = json.loads(json.dumps(payload))
        wrong['candidate_pool_source']['digest'] = 'wrong-generation'
        page.evaluate('p => hydrateCandidatePool(p.candidate_pool_html, p.candidate_pool_source)', wrong)
        assert root.locator('.ucp-row').count() == 3
        assert root.locator('.ucp-more').count() == 1
        partial = json.loads(json.dumps(payload))
        partial['candidate_pool_html'] = '<div class="ucp-row" data-ticker="AMD"></div>'
        page.evaluate('p => hydrateCandidatePool(p.candidate_pool_html, p.candidate_pool_source)', partial)
        assert root.locator('.ucp-row').count() == 3
        # Simulates the existing authorized payload callback, not authentication.
        page.evaluate('p => hydrateCandidatePool(p.candidate_pool_html, p.candidate_pool_source)', payload)
        page.evaluate('p => hydrateCandidatePool(p.candidate_pool_html, p.candidate_pool_source)', payload)
        assert root.locator('.ucp-row').count() == view['counts']['eligible']
        assert root.locator('.ucp-more').count() == 0
        actual = root.locator('.ucp-row').evaluate_all('(rows) => rows.map(r => r.dataset.ticker)')
        assert actual == [r['ticker'] for r in view['rows']]
        root.locator('#ucp-outside').check()
        assert root.locator('.ucp-row:visible').count() == view['counts']['off_buy_lane']
        root.locator('#ucp-search').fill('this-company-does-not-exist')
        assert root.locator('.ucp-row:visible').count() == 0
        assert root.locator('.ucp-no-match').is_visible()
        root.locator('#ucp-search').fill('Advanced Micro')
        assert root.locator('.ucp-row:visible').count() == 1
        assert root.locator('.ucp-row:visible').get_attribute('data-ticker') == 'AMD'
        assert 'Not scored' in root.locator('.ucp-row:visible').text_content()
        for width in (1440, 390):
            for theme in ('light', 'dark'):
                for language in ('en', 'zh'):
                    page.set_viewport_size({'width': width, 'height': 1000})
                    page.evaluate('x => {document.documentElement.dataset.theme=x[0]; document.documentElement.dataset.lang=x[1];}', [theme, language])
                    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), (width, theme, language)
                    name=f'candidate-{width}-{theme}-{language}.png'
                    root.screenshot(path=str(args.out/name))
                    receipt['browser'].append({'width': width, 'theme': theme, 'language': language, 'horizontal_overflow': False, 'screenshot': name})
        receipt.update(keyboard_open=True, hydration_idempotent=True, search_amd=True,
                       outside_filter=True, no_match=True, order_preserved=True, mixed_generation_refused=True, partial_tail_refused=True)
        browser.close()
    (args.out/'receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False))
    print(json.dumps({key: value for key, value in receipt.items() if key != 'browser'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
