"""Review-only proof: pinned Python producer -> pinned existing JS consumer.

Run from this checkout with Python and Node installed. Uses explicitly synthetic
adversarial rows, never the network. Not a browser, full application, live source
or production acceptance test. Future source changes require a fresh review of
these blob pins, not deletion of the checks.
"""
from datetime import date
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine import event_calendar as ec  # noqa: E402

EXPECTED = {
    'engine/event_calendar.py': 'ff60c892a41138e07a8e77b318ae50137993c1ef',
    'engine/calendar_event_context.py': 'db1d08adb36e81418b8f9137114e89af488eafa1',
    'templates/calendar_event_context.js': '9e144245006f24679f50b37fb2ea98c6540f97a8',
}


def git_blob(path):
    raw = (ROOT / path).read_bytes()
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def main():
    assert {path: git_blob(path) for path in EXPECTED} == EXPECTED, 'Review source changed'
    base = dict(securityType='Note', securityTerm='2-Year', cusip='91282CRP8',
                auctionDate='2026-09-22', announcementDate='2026-09-17',
                issueDate='2026-09-30', maturityDate='2028-09-30',
                offeringAmount='69000000000', closingTimeCompetitive='01:00 PM', reopening='No')
    neighbor = dict(base, cusip='91282CRN3', securityTerm='5-Year', offeringAmount='70000000000')
    cases = []
    original_fetch = ec._fetch_upcoming_auctions
    try:
        for mutation in ({'reopening': 'Yes'}, {'floatingRate': 'Yes', 'type': 'FRN'},
                         {'tips': 'Yes', 'type': 'TIPS'}, {'securityTerm': '5-Year'}):
            for order in itertools.permutations([base, dict(base, **mutation), dict(base)]):
                ec._fetch_upcoming_auctions = lambda _, rows=list(order) + [neighbor]: rows
                got = ec._auction_events(date(2026, 9, 17), date(2026, 9, 30))
                assert len(got) == 2
                assert got[0]['intelligence']['coverage'] == 'conflicting_terms'
                assert got[1]['intelligence']['coverage'] == 'official_terms'
                cases.append({'kind': 'conflict', 'rows': [x['intelligence'] for x in got]})
        for invalid in (None, '', 'not a time', '25:99', {}, []):
            for floating in ('Yes', 'No'):
                row = dict(base, closingTimeCompetitive=invalid, floatingRate=floating)
                ec._fetch_upcoming_auctions = lambda _, r=row: [r]
                got = ec._auction_events(date(2026, 9, 17), date(2026, 9, 30))
                assert got[0]['time_et'] == ''
                cases.append({'kind': 'missing_time', 'rows': [got[0]['intelligence']]})
    finally:
        ec._fetch_upcoming_auctions = original_fetch
    source = (ROOT / 'templates/calendar_event_context.js').read_text(encoding='utf-8')
    program = """const assert=require('node:assert/strict'); let payload=[];
global.window={};global.document={getElementById:()=>({textContent:JSON.stringify(payload)})};
""" + source + '\nconst cases=' + json.dumps(cases) + ';\n' + """
for(const c of cases){
  payload=c.rows;
  const html=window.MMXCalendarEventContext.renderDate('2026-09-22');
  if(c.kind==='conflict'){
    assert(html.includes('Conflicting source terms'));
    assert(html.includes('来源条款冲突'));
    assert(!html.includes('69,000,000,000'));
    assert(html.includes('70,000,000,000'));
    assert(html.includes('terms disputed'));
    assert(!html.includes('Read the floating-rate terms'));
    assert(!html.includes('Read real yield'));
    assert.equal((html.match(/<article /g)||[]).length,2);
  } else {
    assert(html.includes('Partial official terms'));
    assert(html.includes('Not supplied'));
    assert(!html.includes('13:00'));
  }
  assert.equal(window.MMXCalendarEventContext.renderDate('2026-09-23'),'');
}
console.log(JSON.stringify({status:'PASS',producer_consumer_cases:cases.length}));
"""
    result = subprocess.run(['node'], input=program, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    report = dict(json.loads(result.stdout),
                  semantic_head='1caee1d8edf70c210f55720568eb282277d320d3',
                  source_blobs=EXPECTED, data='synthetic adversarial rows',
                  boundary='isolated producer and existing renderer; not browser or production proof')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
