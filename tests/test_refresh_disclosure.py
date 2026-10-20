"""MO-PAID-057: source-clock and visit-time Help disclosure regressions."""
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import subprocess
import pytest
from lib.help_directory import refresh_disclosure
from scripts import build_public_pages

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)

@pytest.mark.parametrize("stamp,age,state", [
    (None, None, "unknown"), ("", None, "unknown"), ("bad", None, "unknown"),
    ("2026-10-20T12:00:00", None, "unknown"),
    ("2026-02-30T12:00:00Z", None, "unknown"),
    ("2026-10-20T12:00:01Z", None, "unknown"),
    ("2026-10-20 11:30", 0, "fresh"),
    ("2026-10-20T12:00:00Z", 0, "fresh"),
    ("2026-10-20T13:00:00+02:00", 1, "fresh"),
    ("2026-10-19T00:00:01Z", 35, "fresh"),
    ("2026-10-19T00:00:00Z", 36, "stale"),
    ("2026-10-18T23:00:00Z", 37, "stale"),
])
def test_source_clock_contract(stamp, age, state):
    result = refresh_disclosure(ROOT, stamp, now=NOW)
    assert result["state"] == state
    assert result["age_hours"] == age
    assert len(result) == 7
    assert result["line_zh"] and result["line_zh"] != result["line_en"]
    assert "overnight" not in result["line_en"]
    assert "Help" in result["line_en"]
    assert result["stamp_utc"] == (stamp if age is not None else None)
    if age is None:
        assert "0 hours" not in result["line_en"]
    if age == 0:
        assert "less than an hour" in result["line_en"]
    if age == 1:
        assert "1 hour ago." in result["line_en"]
        assert "1 hours" not in result["line_en"]


def test_root_is_unread():
    assert refresh_disclosure(Path("/path/that/does/not/exist"), "2026-10-20 11:30", now=NOW) == refresh_disclosure(ROOT, "2026-10-20 11:30", now=NOW)


def test_ambiguous_now_cannot_produce_freshness():
    assert refresh_disclosure(ROOT, "2026-10-20 11:30", now=NOW.replace(tzinfo=None))["age_hours"] is None


def test_real_builder_and_noscript_fallback(tmp_path):
    build_public_pages.build(tmp_path)
    html = (tmp_path / "help.html").read_text()
    assert 'id="help-refresh" data-refresh-state="unknown" data-build-stamp="20' in html
    assert "The age of this Help page is unavailable in this browser." in html
    assert '<script src="help_refresh.js" defer></script>' in html
    hero = html.split('<header class="help-hero">')[1].split('</header>')[0]
    assert "overnight" not in hero
    assert "data-build-stamp" in hero


@pytest.mark.skipif(not shutil.which("node"), reason="Node required for real browser-script execution")
def test_browser_recomputes_old_static_stamp_and_bfcache():
    script = (ROOT / "templates/help_refresh.js").read_text()
    # Run the actual shipped script, preserving listeners and textContent writes.
    harness = r"""
const vm = require('node:vm');
const events = {}; const parts = {'.l-en':{}, '.l-zh':{}};
const attrs = {'data-build-stamp':'2026-10-20 11:30'};
let now = Date.parse('2026-10-20T12:00:00Z');
const element = {getAttribute:k=>attrs[k], setAttribute:(k,v)=>attrs[k]=v, querySelector:k=>parts[k]};
const context = {document:{hidden:false,getElementById:()=>element, addEventListener:(k,f)=>events[k]=f},
window:{addEventListener:(k,f)=>events[k]=f,setInterval:f=>events.timer=f},Date:{parse:Date.parse,now:()=>now},Number,Math};
vm.runInNewContext(SOURCE,context);
function read(){return {state:attrs['data-refresh-state'],en:parts['.l-en'].textContent,zh:parts['.l-zh'].textContent};}
const values=[read()];
now = Date.parse('2026-10-20T12:30:00Z'); events.timer(); const singular = read();
if (!singular.en.includes('1 hour ago.') || singular.en.includes('1 hours')) throw new Error('singular hour copy');
now = Date.parse('2026-10-22T12:00:00Z'); events.pageshow(); values.push(read());
now = Date.parse('2026-10-20T11:00:00Z'); events.visibilitychange(); values.push(read());
attrs['data-build-stamp']=''; events.timer(); values.push(read());
console.log(JSON.stringify(values));
""".replace("SOURCE", json.dumps(script))
    values = json.loads(subprocess.check_output(["node", "-e", harness], text=True))
    assert [v["state"] for v in values] == ["fresh", "stale", "unknown", "unknown"]
    assert "less than an hour" in values[0]["en"]
    assert "48 hours" in values[1]["en"]
    assert "Check the product page" in values[1]["en"]
    assert all(v["zh"] and "overnight" not in v["en"] for v in values)
