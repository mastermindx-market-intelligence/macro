"""Release Radar clocks and refresh regressions: real dashboard JavaScript, controlled I/O."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "templates/dashboard.html.j2").read_text()


def _extract(start: str, end: str) -> str:
    left = SOURCE.index(start)
    return SOURCE[left:SOURCE.index(end, left)]


def _node(script: str) -> None:
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_release_radar_countdowns_use_live_new_york_calendar_day():
    """An Oct 16 snapshot's baked 'in 13d' must read six days on Oct 23."""
    source = _extract("    function _rrEasternDay(){", "    function _rrMetaChip")
    driver = r"""
const assert = require('assert');
const NativeDate = Date;
let now = NativeDate.parse('2026-10-23T07:15:00Z');
class Clock extends NativeDate {
  constructor(...args) { super(...(args.length ? args : [now])); }
  static now() { return now; }
}
global.Date = Clock;
""" + source + r"""
assert.strictEqual(_rrDaysUntil('2026-10-29'), 6);
assert.strictEqual(_rrCountdownLabels(_rrDaysUntil('2026-10-29')).en, '6 days away');
assert.strictEqual(_rrDaysUntil('2026-10-22'), -1);
assert.strictEqual(_rrCountdownLabels(-1).en, '1 days since release');
now = NativeDate.parse('2026-10-24T03:59:00Z'); // Still Oct 23 Eastern
assert.strictEqual(_rrDaysUntil('2026-10-29'), 6);
now = NativeDate.parse('2026-10-24T04:00:00Z'); // Eastern midnight
assert.strictEqual(_rrDaysUntil('2026-10-29'), 5);
now = NativeDate.parse('2026-11-01T05:30:00Z'); // DST fallback
assert.strictEqual(_rrDaysUntil('2026-11-02'), 1);
now = NativeDate.parse('2026-11-01T06:30:00Z');
assert.strictEqual(_rrDaysUntil('2026-11-02'), 1);
assert.strictEqual(_rrDaysUntil('2026-02-30'), null);
assert.strictEqual(_rrDaysUntil(null), null);
"""
    _node(driver)
    assert "var daysTo = _rrDaysUntil(item.release_date)" in SOURCE
    assert "var currentDays = _rrDaysUntil(item.release_date)" in SOURCE
    assert "_rrCountdownLabels(item.days_to)" not in SOURCE
    assert "var daysTo = item.days_to" not in SOURCE


def test_stale_forecast_snapshot_disclosed_without_claiming_live_models():
    source = _extract("    function _rrSnapshotNotice(){", "    function _rrUpdateSnapshotNotice(){")
    driver = (
        "const assert = require('assert');\n"
        "var _rrForecastAsOf = '2026-10-16T18:18:59Z';\n"
        "var _rrForecastFailed = false;\n"
        + source
        + """
const oldNow = Date.now;
Date.now = () => Date.parse('2026-10-23T07:15:00Z');
assert(_rrSnapshotNotice().en.includes('last-known'));
assert(_rrSnapshotNotice().en.includes('Oct 16'));
_rrForecastAsOf = '2026-10-23T07:14:00Z';
assert.strictEqual(_rrSnapshotNotice(), null);
_rrForecastFailed = true;
assert(_rrSnapshotNotice().en.includes('refresh unavailable'));
_rrForecastAsOf = '';
assert(_rrSnapshotNotice().en.includes('no live model estimate'));
Date.now = oldNow;
"""
    )
    _node(driver)


def test_forecast_refresh_coalesces_requests_retains_last_good_and_revalidates():
    source = _extract("    var _rrForecastSignature = null;", "    /* Deep-link hook:")
    driver = r"""
const assert = require('assert');
let requests = [];
let listeners = {};
let tick;
let renders = [];
let clocks = 0, notices = 0;
let _rrForecastAsOf = null, _rrForecastFailed = false;
global.document = {
  hidden:false,
  addEventListener:(name,cb)=>{listeners[name]=cb;}
};
global.window = { addEventListener:(name,cb)=>{listeners[name]=cb;} };
global.fetch = (url,opts) => new Promise((resolve,reject) => {
  assert.strictEqual(url,'macrodata/release_forecast.json');
  assert.strictEqual(opts.cache,'no-store');
  requests.push({resolve,reject});
});
global.setInterval = (cb,ms) => { assert.strictEqual(ms,60000); tick=cb; };
function renderRadar(value){ renders.push(value); }
function _rrUpdateCountdowns(){ clocks += 1; }
function _rrUpdateSnapshotNotice(){ notices += 1; }
""" + source + r"""
async function drain(){ await new Promise(setImmediate); }
(async function(){
  assert.strictEqual(requests.length,1);
  tick(); listeners.focus(); listeners.visibilitychange();
  assert.strictEqual(requests.length,1,'pending request must coalesce');
  let payload = {asof:'2026-10-23T07:00:00Z',upcoming:[{release:'PCE'}]};
  requests[0].resolve({ok:true,json:async()=>payload});
  await drain();
  assert.strictEqual(renders.length,1);
  assert.strictEqual(_rrForecastFailed,false);
  tick();
  assert.strictEqual(requests.length,2);
  requests[1].resolve({ok:true,json:async()=>payload});
  await drain();
  assert.strictEqual(renders.length,1,'identical snapshot must retain DOM');
  tick();
  requests[2].reject(new Error('offline'));
  await drain();
  assert.strictEqual(_rrForecastFailed,true);
  assert.strictEqual(renders.length,1,'failure must preserve last-good snapshot');
  document.hidden=true;
  tick(); assert.strictEqual(requests.length,3,'hidden page must not fetch');
  document.hidden=false;
  listeners.visibilitychange();
  assert.strictEqual(requests.length,4,'visibility should revalidate');
  payload = {asof:'2026-10-23T07:30:00Z',upcoming:[{release:'GDP'}]};
  requests[3].resolve({ok:true,json:async()=>payload});
  await drain();
  assert.strictEqual(renders.length,2);
  assert.strictEqual(_rrForecastFailed,false);
  assert(clocks>=3 && notices>=4);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    _node(driver)
