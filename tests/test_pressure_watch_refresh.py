"""Same-run Pressure Watch section refresh, through the canonical template."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from scripts import build_ticker_pages as pages

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 16, 6, tzinfo=timezone.utc)


def setup_site(tmp_path):
    site = tmp_path / "site"
    (site / "stocks").mkdir(parents=True)
    data = tmp_path / "data"
    (data / "price_pressure").mkdir(parents=True)
    (data / "massive_stock_day").mkdir()
    payload = json.loads((ROOT / "tests/fixtures/price_pressure_latest.json").read_text())
    payload.update(asof="2026-09-11", evaluated_through="2026-09-14")
    payload["day"] = {"asof": "2026-09-14", "broad_selloff": False,
                      "banner": "Today's pressure is name-by-name, not market-wide."}
    (data / "price_pressure/latest.json").write_text(json.dumps(payload))
    (data / "massive_stock_day/_manifest.json").write_text('{"latest_date":"2026-09-14"}')
    (site / "stocks/index.html").write_text('<!doctype html><html><head></head><body>'
        '<div id="preserve-before">keep before</div>'
        '<section id="pressure" class="section-anchor"><p>old pressure</p></section>'
        '<div id="preserve-after">keep after</div></body></html>')
    return site


def test_refresh_consumes_evaluation_without_rebuilding_dossiers(tmp_path, monkeypatch):
    site = setup_site(tmp_path)
    monkeypatch.setattr(pages, "load_all_aggregates", lambda *_: pytest.fail("full dossier rebuild"))
    monkeypatch.setattr(pages, "load_per_ticker", lambda *_: pytest.fail("per-ticker rebuild"))
    assert pages.refresh_pressure_watch(site, now=NOW) == 0
    html = (site / "stocks/index.html").read_text()
    assert "as of 2026-09-14" in html
    assert "old pressure" not in html
    assert 'id="preserve-before">keep before' in html
    assert 'id="preserve-after">keep after' in html
    assert "next data file" in html
    assert "new today" not in html
    assert len(list((site / "stocks").glob("*.html"))) == 1


@pytest.mark.parametrize("replacement", ["", '<section id="pressure"></section>' * 2])
def test_ambiguous_or_missing_target_is_not_written(tmp_path, replacement):
    site = setup_site(tmp_path)
    target = site / "stocks/index.html"
    target.write_text('<html><head></head><body>' + replacement + '</body></html>')
    before = target.read_bytes()
    assert pages.refresh_pressure_watch(site, now=NOW) != 0
    assert target.read_bytes() == before


def test_page_carries_an_expiry_from_the_source_calendar(tmp_path):
    site = setup_site(tmp_path)
    assert pages.refresh_pressure_watch(site, now=NOW) == 0
    html = (site / "stocks/index.html").read_text()
    assert 'data-pw-expires="2026-09-16T15:00:00+00:00"' in html
    assert 'data-pw-status="awaiting_source"' in html
    assert "Update due" in html


def test_shared_partial_is_used_by_both_full_and_pressure_only_render():
    source = (ROOT / "templates/ticker_index.html.j2").read_text()
    assert "include '_pressure_watch.html.j2'" in source
    assert '<section id="pressure"' not in source, "no duplicated widget markup"


def test_pressure_only_cli_does_not_accept_dossier_modes():
    with pytest.raises(SystemExit) as raised:
        pages.main(["--pressure-only", "--only", "AAPL"])
    assert raised.value.code == 2


def test_browser_expiry_updates_a_page_that_did_not_rebuild():
    import re
    import subprocess
    text = (ROOT / "templates/_pressure_watch.html.j2").read_text()
    script = re.search(r'<script data-pw-expiry>(.*?)</script>', text, re.S).group(1)
    harness = r'''
const vm = require('vm');
const fs = require('fs');
let now = Date.parse('2026-09-16T14:59:00Z');
class Clock extends Date { static now() { return now; } }
const current={hidden:false}, warning={hidden:true}, en={}, zh={};
const nodes={'[data-pw-current-banner]':current,'[data-pw-expiry-warning]':warning,
             '.pw-stance .l-en':en,'.pw-stance .l-zh':zh};
const section={dataset:{pwExpires:'2026-09-16T15:00:00Z',pwStatus:'awaiting_source'},
               querySelector:key=>nodes[key]};
let wake;
const document={getElementById:()=>section,addEventListener:(event,callback)=>{wake=callback;}};
vm.runInNewContext(fs.readFileSync(0,'utf8'),{document,Date:Clock,Number,setTimeout:()=>{}});
if (warning.hidden!==true || current.hidden!==false) throw Error('expired early');
now=Date.parse('2026-09-16T15:01:00Z'); wake();
if (warning.hidden!==false || current.hidden!==true) throw Error('silent frozen page');
if (section.dataset.pwStatus!=='update_due') throw Error('status remained current');
if (!en.textContent || !zh.textContent) throw Error('missing bilingual stance');
'''
    result = subprocess.run(["node", "-e", harness], input=script, text=True,
                            capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
