'use strict';
// OWNER-REVIEW V3 COMPOSITION DRAFT. Not executed by its author. Separate from the v13 derivative.
// Genuine anonymous beta/www UI + finite read-only GETs; no routes, cookies,
// init scripts, postMessages, fixture content, chat submission or account edits.
// Overall served acceptance still needs the owner's post-journey host bracket.

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');

const PARENT = 'https://beta.mastermind-x.com';
const CHILD = 'https://www.mastermind-x.com';
const PARENT_SOURCE = '6d14ec45238ba51328a90485d727595aa9592027';
const COUNTRIES = ['JP', 'KR', 'TW', 'IN', 'AU', 'GB', 'EZ'];
const PRIVATE_ASSETS = ['/hkstockdata/0700_HK.json', '/canadastockdata/ATRL_TO.json'];
const QUERY = '?view=history&market=TW&pins=&horizon=3m&basis=local&return_basis=price&group=';
const REQUIRED_ARTIFACTS = [
  'intl.html', 'shared_shell_bridge.js', 'shared_shell.css', 'intl_workspace.js',
  'intl_workspace_state.js', 'intl_workspace_scenario.js', 'intl_workspace.css',
  'theme.js', 'theme.css', 'mm_brain.js',
];
const SELECTOR_SOURCES = {
  parent: {
    commit: PARENT_SOURCE,
    files: {
      'terminal/components/chrome/shared-shell/SharedShellPresentationControls.tsx': '7fb99136805197eae72cf0d7bd8c0dd68d0eb481',
      'terminal/components/chrome/shared-shell/SharedShellPresentation.tsx': 'b7cf52ee808ba4426fab15a1240de2507e8f0382',
      'terminal/lib/sharedShellCopy.ts': '585a9bbc33f0bdb507ec3cac39bede09c76a70c0',
      'terminal/components/chrome/AppShell.tsx': 'fad76e11e24f02510854768878ef7ce7e0a063bf',
      'terminal/app/api/me/route.ts': '67dddc5a829a9f8d4d52354a6ce15f987f5ea964',
    },
  },
  macro: {
    reviewed_commit: 'PENDING_ACTUAL_INTEGRATED_SOURCE_COMMIT',
    baseline_reviewed_commit: 'bdeb609bf11a170c39713461eace85b47d2ca18c',
    composition_reference_main: '24559ffa06bcf06fa8e9f36bb7e078412bd769fe',
    files: {
      'templates/intl_country_cockpit.html.j2': '7027a488638bca8966a0bcfa66aa06d593afb2a7',
      'templates/intl_country_cockpit.js': 'db14efb15eb4a1b3e35e2f8fbd5e69dcdb7530db',
      'templates/intl_country_cockpit.css': '72b6440d5e8ea0d1bcc8bed1c6e35db5b43d1016',
      'site/intl_workspace_scenario.js': '11a1456c9c1e172dd9ff97ac758cc08648f086cc',
      'site/mm_brain.js': '1b79f047a4385cd8254a647350a1d2d9e65c1329',
      'app/regwall.py': 'f5d28050873019d1b4c20fa92ae85a796ef88a55',
      'app/deploy/Caddyfile': '63404b593f50848cac09ad7d155dda6555d86aae',
      'config/site_access.yml': 'd08668ca975bdc363ba61635fa1ecbd70876e01d',
    },
    sha256_files: {
      'templates/intl_workspace.js': 'bf3b3d81c4a51d1771400d801450620e1e5b538333c5604bcac486080d5bd5ae',
    },
  },
};
const sha40 = x => typeof x === 'string' && /^[a-f0-9]{40}$/.test(x);
const sha64 = x => typeof x === 'string' && /^[a-f0-9]{64}$/.test(x);
const hash = x => crypto.createHash('sha256').update(x).digest('hex');
const gitBlob = x => crypto.createHash('sha1').update(Buffer.from('blob ' + x.length + '\0')).update(x).digest('hex');
const now = () => new Date().toISOString();
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const bounded = async (promise, ms, label) => {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(label + ' exceeded its finite time limit')), ms);
  })]); } finally { clearTimeout(timer); }
};

function argumentsFor(argv) {
  const allowed = new Set(['artifact', 'output', 'release-manifest', 'repository', 'playwright']);
  const values = {};
  assert(argv.length % 2 === 0, 'Arguments must be explicit option/value pairs');
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i].replace(/^--/, '');
    assert(argv[i] === '--' + key && allowed.has(key) && !Object.hasOwn(values, key), 'Unknown or repeated option');
    assert(typeof argv[i + 1] === 'string' && path.isAbsolute(argv[i + 1]), 'All paths must be absolute');
    values[key] = path.resolve(argv[i + 1]);
  }
  for (const key of ['artifact', 'output', 'release-manifest']) assert(values[key], 'Missing --' + key);
  values.repository ||= '/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018';
  values.playwright ||= '/Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/intl-parent-proof-20261022/terminal/node_modules/playwright';
  return values;
}

function readFile(file, limit = 64 * 1024 * 1024) {
  const before = fs.lstatSync(file);
  assert(before.isFile() && !before.isSymbolicLink() && before.size <= limit, 'Expected bounded regular evidence file');
  const bytes = fs.readFileSync(file);
  const after = fs.lstatSync(file);
  assert.equal(bytes.length, before.size, 'Evidence file size changed');
  for (const field of ['dev', 'ino', 'size', 'mtimeMs', 'ctimeMs']) assert.equal(before[field], after[field], 'Evidence file identity changed');
  return bytes;
}

function safePath(name) {
  assert(typeof name === 'string' && name && !name.startsWith('/') && !name.includes('\\') &&
    !name.split('/').some(x => !x || x === '.' || x === '..'), 'Unsafe artifact/source path');
  return name;
}

function publicTuple(body) {
  const keys = ['enabled', 'protocol', 'buildId', 'bridgeVersion', 'documentVersion', 'registrySha256'];
  if (!body || typeof body !== 'object' || Array.isArray(body) ||
      !same(Object.keys(body).sort(), [...keys].sort())) return null;
  return Object.fromEntries(keys.map(key => [key, body[key]]));
}

function sameTuple(a, b) {
  const x = publicTuple(a), y = publicTuple(b);
  return x !== null && y !== null && Object.keys(x).every(key => x[key] === y[key]);
}

function safeJsonProjection(bytes) {
  try {
    const value = JSON.parse(bytes.toString('utf8'));
    return {
      public_status: publicTuple(value),
      authenticated: typeof value.authenticated === 'boolean' ? value.authenticated : null,
      guest_tier: value.tier === 'guest',
      terminal_guest_default: value.tier === 'free' && value.status === 'none' &&
        Array.isArray(value.features) && value.features.length === 0 && Object.keys(value).length === 3,
      locked: value.locked === true,
      authentication_required: value.reason === 'authentication_required',
      signin_url_is_canonical: value.signin_url === '/?signin=1',
      json_object: value !== null && typeof value === 'object' && !Array.isArray(value),
    };
  } catch (_) { return {json_object: false}; }
}

function countryOracles(html, currencies) {
  // Parse the already publication-bound HTML as inert data with the standard
  // library. No browser document, template, script or resource is executed.
  // Python's format operators deliberately match the pinned Jinja template.
  const program = String.raw`import sys,json,math,re
from html.parser import HTMLParser
payload=json.load(sys.stdin)
class Document(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.root={'tag':'root','attrs':{},'children':[]};self.stack=[self.root];self.count=0
 def handle_starttag(self,tag,attrs):
  self.count+=1
  if self.count>1000000:raise ValueError('HTML oracle node limit')
  node={'tag':tag,'attrs':dict(attrs),'children':[]};self.stack[-1]['children'].append(node)
  if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append(node)
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i]['tag']==tag:self.stack=self.stack[:i];break
 def handle_startendtag(self,tag,attrs):
  self.handle_starttag(tag,attrs);self.handle_endtag(tag)
 def handle_data(self,data):self.stack[-1]['children'].append(data)
def walk(node):
 yield node
 for child in node['children']:
  if isinstance(child,dict):yield from walk(child)
def has(node,cls):return cls in (node['attrs'].get('class') or '').split()
def one(node,predicate):
 found=[x for x in walk(node) if predicate(x)]
 if len(found)!=1:raise ValueError('Expected exactly one country oracle element, got '+str(len(found)))
 return found[0]
def text(node,lang='en'):
 if has(node,'l-zh' if lang=='en' else 'l-en'):return ''
 return ''.join(x if isinstance(x,str) else text(x,lang) for x in node['children'])
def norm(value):return ' '.join(value.split())
def rendered(node,lang='en'):return norm(text(node,lang))
doc=Document();doc.feed(payload['html']);doc.close()
rows=payload['currencies'];countries=['JP','KR','TW','IN','AU','GB','EZ']
assert len(rows)==7 and sorted(x['cc'] for x in rows)==sorted(countries)
result={}
for row in rows:
 cc=row['cc'];assert row['verdict']=='PASS' and row['consumer_quality']=='current'
 panel=one(doc.root,lambda x:x['attrs'].get('id')=='imc-country-'+cc)
 outlook=one(panel,lambda x:has(x,'imc-outlook-panel'))
 chart_count=sum(1 for figure in walk(panel) if has(figure,'imc-growth-chart') for node in walk(figure) if node['tag']=='svg')
 missing=[x for x in walk(outlook) if has(x,'imc-missing')]
 unavailable=bool(missing) and all(rendered(x) for x in missing)
 assert chart_count>0 or unavailable,cc+' has neither a chart nor an explicit published unavailability statement'
 fx=one(panel,lambda x:has(x,'imc-fx-read'))
 value=one(fx,lambda x:x['tag']=='strong');date=one(fx,lambda x:has(x,'imc-fx-date'))
 quotes=one(panel,lambda x:has(x,'imc-currency-quotes'))
 ledger=one(panel,lambda x:has(x,'imc-currency-ledger'))
 cells=[x for x in ledger['children'] if isinstance(x,dict) and x['tag']=='td'];assert len(cells)==4
 a=row['endpoints']['start'];b=row['endpoints']['end']
 start=float(a['quote']);end=float(b['quote']);observed=float(row['local_currency_vs_usd_return_percent'])
 assert all(math.isfinite(x) for x in [start,end,observed]) and start>0 and end>0
 assert start.hex()==a['quote_hex'] and end.hex()==b['quote_hex'],cc+' exact qualified endpoint values'
 convention=row['quote_convention'];assert convention in ['local_per_USD','USD_per_local']
 recomputed=((start/end if convention=='local_per_USD' else end/start)-1.0)*100.0
 assert recomputed==observed,cc+' probe return recomputes from the two actual qualified quotes'
 percent=('%+.2f'%(observed if abs(observed)>=0.005 else 0))+'%'
 expected_dates=a['provider_date']+' → '+b['provider_date']
 expected_pair=('%.6g'%start)+' → '+('%.6g'%end)
 expected_units=row['currency']+' per USD' if convention=='local_per_USD' else 'USD per '+row['currency']
 source=one(cells[3],lambda x:x['tag']=='a')
 assert fx['attrs'].get('data-fx-quality')=='current'
 assert rendered(value)==percent and rendered(cells[1])==percent,cc+' published percent matches actual probe'
 assert rendered(cells[2])==expected_dates,cc+' published endpoint dates match actual probe'
 assert re.findall(r'\d{4}-\d{2}-\d{2}',rendered(date))==[b['provider_date']],cc+' through-date is exact'
 assert expected_pair in rendered(quotes) and expected_units in rendered(quotes),cc+' exact quoted rates and convention'
 assert row['reference_target'] in rendered(quotes),cc+' actual reference target'
 if row['reference_gap_days']:assert a['provider_date'] in rendered(quotes),cc+' actual earlier observed reference date'
 assert source['attrs'].get('href')==row['source_url'],cc+' actual admitted source URL'
 result[cc]={'chart_count':chart_count,'explicit_chart_unavailability':unavailable,'fx_quality':'current','fx_value':percent,
  'fx_date':{lang:rendered(date,lang) for lang in ['en','zh']},'quoted_rates':{lang:rendered(quotes,lang) for lang in ['en','zh']},
  'ledger_value':percent,'ledger_dates':expected_dates,'source_url':row['source_url'],
  'probe_value':observed,'recomputed_value':recomputed,'quote_convention':convention,'start_quote':start,'end_quote':end,
  'start_quote_display':'%.6g'%start,'end_quote_display':'%.6g'%end,'evidence_sha256':row['evidence_sha256']}
print(json.dumps(result,ensure_ascii=False,allow_nan=False))`;
  const result = JSON.parse(execFileSync('/tmp/intl-country-cockpit-ci-20261021/bin/python', ['-c',program], {
    input: JSON.stringify({html:html.toString('utf8'),currencies}), maxBuffer:1024*1024, timeout:30000,
  }));
  assert(same(Object.keys(result).sort(),[...COUNTRIES].sort()),'Complete finite country oracle');
  return {countries:result,parser_sha256:hash(Buffer.from(program)),html_sha256:hash(html),
    qualification:'Exact published chart counts and text; percentages, dates, source and formatted endpoint quotes independently cross-checked against the hash-qualified actual acquisition probe.'};
}

let report = null, output = null, browser = null, browserOwner = null;
let release, childExpected, parentExpected, countryOracle;
const tasks = [], contexts = [], apiClients = [], apiResponses = [], browserRequests = [];
let sequence = 0, requestSequence = 0, pageSequence = 0;
const requestRows = new WeakMap(), pageIds = new WeakMap();
const pageId = page => {
  assert(page && (typeof page === 'object' || typeof page === 'function'), 'Actual browser page required');
  if (!pageIds.has(page)) pageIds.set(page, ++pageSequence);
  return pageIds.get(page);
};
const firstParty = url => [PARENT, CHILD].includes(new URL(url).origin);
const check = (scope, id, pass, detail = {}) => {
  report.cases.push({scope, id, pass: !!pass, ...detail});
};
const save = () => fs.writeFileSync(path.join(output, 'observation.json'), JSON.stringify(report, null, 2) + '\n', {mode: 0o600});

function expectedAsset(url) {
  const u = new URL(url);
  if (u.origin === CHILD && Object.hasOwn(childExpected, u.pathname)) return childExpected[u.pathname];
  if (u.origin === PARENT && u.pathname.startsWith('/_next/static/')) return parentExpected[u.pathname] || null;
  return null;
}

function parentDocumentIdentity(bytes, row) {
  const html = bytes.toString('utf8');
  const ids = [...html.matchAll(/data-dpl-id=["']([^"']+)["']/g)].map(x => x[1]);
  const urls = [...html.matchAll(/(?:src|href)=["']([^"']*\/_next\/static\/[^"']+)["']/g)]
    .map(x => new URL(x[1].replace(/&amp;/g, '&'), PARENT).href);
  const queryIds = urls.map(x => new URL(x).searchParams.get('dpl')).filter(Boolean);
  const values = [...ids, ...queryIds, ...(row.deployment_header ? [row.deployment_header] : [])];
  return {
    html_ids: ids, static_urls: urls, query_ids: queryIds, header: row.deployment_header,
    verified: values.length > 0 && values.every(x => x === release.parent.source_commit) &&
      urls.length > 0 && urls.every(x => {
        const u = new URL(x);
        return u.origin === PARENT && Object.hasOwn(parentExpected, u.pathname) &&
          (!u.searchParams.has('dpl') || u.searchParams.get('dpl') === release.parent.source_commit);
      }),
  };
}

function cacheEvidence(row, rows) {
  const pin = expectedAsset(row.url);
  if (!pin || row.method !== 'GET' || row.status !== 304 || row.body_error ||
      row.body_state !== 'bodyless304' || !Number.isSafeInteger(row.sequence) || row.sequence <= 0 ||
      !row.owner_kind || !row.owner_id) return null;
  const prior = rows.find(x => x.scope === row.scope && x.url === row.url && x.sequence < row.sequence &&
    x.sequence > 0 && x.owner_kind === row.owner_kind && x.owner_id === row.owner_id &&
    x.method === 'GET' && x.status === 200 && !x.body_error && x.body_state === 'complete' &&
    x.sha256 === pin.sha256 && x.bytes === pin.bytes &&
    (row.if_none_match !== null ? !!x.etag && row.if_none_match === x.etag :
      !!row.if_modified_since && !!x.last_modified && row.if_modified_since === x.last_modified));
  return prior ? {prior_sequence: prior.sequence, sha256: prior.sha256, bytes: prior.bytes,
    validator: row.if_none_match !== null ? 'If-None-Match' : 'If-Modified-Since'} : null;
}

function legitimateAnonymousResponse(row) {
  const u = new URL(row.url), body = row.safe_json;
  if (!firstParty(row.url) || row.method !== 'GET' || row.body_error || !body?.json_object ||
      !/application\/json/i.test(row.content_type || '')) return false;
  if (u.origin === CHILD && u.pathname === '/api/brain/me' && !u.search) {
    return row.status === 401 || row.status === 200 && body.guest_tier === true;
  }
  if (u.origin === CHILD && u.pathname === '/api/me' && !u.search) return row.status === 401;
  if (u.origin === CHILD && u.pathname === '/api/account' && !u.search) {
    return row.status === 401 || row.status === 200 && body.authenticated === false;
  }
  if (u.origin === PARENT && u.pathname === '/api/me' && !u.search) {
    return row.status === 200 && body.terminal_guest_default === true;
  }
  // Graded data is probed only in the isolated direct-GET access context below.
  return row.scope === 'anonymous-access' && u.origin === CHILD && PRIVATE_ASSETS.includes(u.pathname) &&
    !u.search && row.status === 401 && body.locked && body.authentication_required && body.signin_url_is_canonical &&
    /\bno-store\b/i.test(row.cache_control || '') && /\bcookie\b/i.test(row.vary || '') &&
    row.regwall === 'deny' && /\bnoindex\b/i.test(row.robots || '') && /\bnoarchive\b/i.test(row.robots || '');
}

function responseFields(headers) {
  return {
    content_type: headers['content-type'] || null, cache_control: headers['cache-control'] || null,
    etag: headers.etag || null, last_modified: headers['last-modified'] || null,
    vary: headers.vary || null, regwall: headers['x-regwall'] || null,
    robots: headers['x-robots-tag'] || null, deployment_header: headers['x-nextjs-deployment-id'] || null,
  };
}

function observe(context, scope) {
  const onPage = page => {
    const id = pageId(page);
    page.on('pageerror', error => report.page_errors.push({scope, page_id: id, message: String(error.message).slice(0,1500)}));
    page.on('console', message => {
      if (message.type() === 'error') report.console_errors.push({scope, page_id: id,
        message: message.text().slice(0,1500), url: message.location().url || null});
    });
  };
  context.on('page', onPage);
  const requestRecord = request => {
    let row = requestRows.get(request);
    if (!row) {
      row = {scope, request_id: ++requestSequence, page_id: null, owner_kind: 'browser-unattributed',
      owner_id: scope, url: request.url(), started_at: now(),
      method: request.method(), resource_type: request.resourceType(), first_party: firstParty(request.url()),
      authorization_present: !!request.headers().authorization, terminal: 'pending'};
      requestRows.set(request, row); report.requests.push(row);
      browserRequests.push({scope, request, refresh: () => requestRecord(request)});
    }
    // Initial navigation can precede Playwright's page attachment. Retry on
    // response/finish/failure and before cleanup, and update linked responses.
    if (row.page_id === null) {
      try {
        row.page_id = pageId(request.frame().page());
        row.owner_kind = 'browser-page'; row.owner_id = scope + '/page/' + row.page_id;
        for (const responseRow of report.responses) if (responseRow.request_id === row.request_id) {
          responseRow.page_id = row.page_id;
          responseRow.owner_kind = row.owner_kind; responseRow.owner_id = row.owner_id;
        }
      } catch (_) { /* Unattributed requests remain explicit; document/static ownership cannot pass with null. */ }
    }
    return row;
  };
  context.on('request', requestRecord);
  context.on('requestfinished', request => {
    const row = requestRecord(request); row.terminal = 'finished'; row.finished_at = now();
  });
  context.on('requestfailed', request => {
    const row = requestRecord(request);
    row.terminal = 'failed'; row.finished_at = now(); row.failure = request.failure()?.errorText || 'unknown';
  });
  context.on('response', response => {
    const request = response.request(), requestRow = requestRecord(request);
    const row = {scope, sequence: ++sequence, request_id: requestRow.request_id,
      page_id: requestRow.page_id, owner_kind: requestRow.owner_kind, owner_id: requestRow.owner_id,
      url: response.url(), method: request.method(), body_state: 'pending',
      resource_type: request.resourceType(), status: response.status(),
      from_service_worker: response.fromServiceWorker(), ...responseFields(response.headers()),
      if_none_match: null, if_modified_since: null};
    requestRow.response_sequence = row.sequence; report.responses.push(row);
    const task = (async () => {
      try {
        if (row.status === 304) {
          const headers = await bounded(request.allHeaders(), 20000, 'Conditional request headers');
          row.if_none_match = headers['if-none-match'] || null;
          row.if_modified_since = headers['if-modified-since'] || null;
          row.body_state = 'bodyless304';
          return;
        }
        assert(!/text\/event-stream/i.test(row.content_type || ''), 'Streaming body has no finite acceptance contract');
        const body = await bounded(response.body(), 20000, 'Response body');
        assert(body.length <= 64 * 1024 * 1024, 'Response exceeds 64 MiB');
        row.sha256 = hash(body); row.bytes = body.length; row.body_state = 'complete';
        const u = new URL(row.url);
        if (u.origin === PARENT && row.resource_type === 'document') row.document_identity = parentDocumentIdentity(body, row);
        if (firstParty(row.url) && (u.pathname.startsWith('/api/') || PRIVATE_ASSETS.includes(u.pathname))) row.safe_json = safeJsonProjection(body);
      } catch (error) { row.body_state = 'failed'; row.body_error = String(error.message).slice(0,500); }
      finally { requestRecord(request); }
    })();
    tasks.push(task);
  });
}

async function closeOwned(owner) {
  if (owner.closed) return;
  const row = {scope: owner.scope, kind: owner.kind, started_at: now(), pass: false};
  report.cleanup.push(row);
  try {
    await bounded(owner.resource[owner.method](), 15000, owner.kind + ' cleanup');
    owner.closed = true; row.pass = true;
  } catch (error) { row.error = String(error.message).slice(0,1000); }
  row.finished_at = now();
  check(owner.scope, owner.kind + '_cleanup', row.pass, {cleanup: row});
}

async function settleResponseTasks(scope) {
  const until = Date.now() + 30000;
  let previous = -1;
  while (Date.now() < until) {
    const count = tasks.length;
    await bounded(Promise.allSettled(tasks.slice()), 22000, 'Final response tasks');
    if (count === tasks.length && previous === count) return;
    previous = count; await sleep(100);
  }
  throw new Error('Response population did not settle after cleanup: ' + scope);
}

async function finishContext(owner) {
  if (owner.closed) return;
  for (const row of browserRequests) if (row.scope === owner.scope) row.refresh();
  try { await drain(owner.scope); check(owner.scope, 'network_settled_before_context_close', true); }
  catch (error) { check(owner.scope, 'network_settled_before_context_close', false, {error: String(error.message)}); }
  await closeOwned(owner);
  try { await settleResponseTasks(owner.scope); }
  catch (error) { check(owner.scope, 'response_tasks_settled_after_context_close', false, {error: String(error.message)}); }
  save();
}

async function drain(scope) {
  const until = Date.now() + 25000;
  let previous = -1;
  while (Date.now() < until) {
    const count = tasks.length;
    await bounded(Promise.allSettled(tasks.slice()), 22000, 'Response drain');
    const active = report.requests.filter(x => x.scope === scope && x.first_party && x.terminal === 'pending');
    if (count === tasks.length && previous === count && active.length === 0) return;
    previous = count; await sleep(200);
  }
  throw new Error('First-party responses did not settle within the finite drain window');
}

async function screenshot(page, scope, suffix) {
  const name = scope + '-' + suffix + '.png', file = path.join(output, name);
  await page.screenshot({path: file, fullPage: false, timeout: 15000});
  const bytes = readFile(file);
  report.screenshots.push({scope, path: name, sha256: hash(bytes), bytes: bytes.length});
}

async function frameFor(page) {
  const locator = page.locator('iframe[data-shared-shell-frame][data-response-kind="content"]');
  await locator.waitFor({state: 'visible', timeout: 45000});
  const frame = await (await locator.elementHandle()).contentFrame();
  assert(frame, 'Actual public child frame required');
  assert.equal(new URL(frame.url()).origin, CHILD, 'Supported public child origin');
  await frame.waitForFunction(() => window.MMXSharedShell?.active === true &&
    document.querySelector('[data-im-country-analysis]')?.dataset.imcEnhanced === 'true' &&
    document.querySelector('[data-im-workspace][data-im-mode="macro"]')?.dataset.imEnhanced === 'true', null, {timeout: 20000});
  return frame;
}

async function clickable(page, locator, isFrame = false) {
  await locator.scrollIntoViewIfNeeded({timeout: 10000});
  const box = await locator.boundingBox(), viewport = page.viewportSize();
  if (!box || box.width <= 0 || box.height <= 0) return false;
  const left = Math.max(0, box.x), right = Math.min(viewport.width, box.x + box.width);
  const top = Math.max(0, box.y), bottom = Math.min(viewport.height, box.y + box.height);
  if (!(right > left && bottom > top)) return false;
  const hit = await locator.evaluate(element => {
    const r = element.getBoundingClientRect();
    const x = (Math.max(0,r.left)+Math.min(innerWidth,r.right))/2;
    const y = (Math.max(0,r.top)+Math.min(innerHeight,r.bottom))/2;
    const top = document.elementFromPoint(x,y);
    return !!top && (top === element || element.contains(top));
  });
  if (!hit) return false;
  return !isFrame || await page.evaluate(({x,y}) => !!document.elementFromPoint(x,y)?.closest('iframe[data-shared-shell-frame]'),
    {x: (left+right)/2, y: (top+bottom)/2});
}

async function snap(page, frame) {
  const parent = await page.evaluate(() => ({url: location.href, history: history.length,
    entry: history.state?.mmxSharedShellEntry || null, theme: document.documentElement.dataset.theme,
    lang: document.documentElement.dataset.lang}));
  const child = await frame.evaluate(() => {
    const root = document.querySelector('[data-im-workspace][data-im-mode="macro"]');
    const q = selector => root?.querySelector(selector);
    const control = action => q('[data-im-controls] select[data-im-action="'+action+'"]')?.value ?? null;
    const active = document.activeElement;
    const blocked = [];
    for (let node = active; node?.nodeType === 1; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (node.hidden || node.inert || style.display === 'none' || style.visibility === 'hidden' ||
          node.tagName === 'DETAILS' && !node.open && !node.querySelector(':scope > summary')?.contains(active))
        blocked.push({tag:node.tagName,id:node.id,hidden:node.hidden,inert:node.inert,display:style.display,visibility:style.visibility});
    }
    return {url: location.href, history: history.length, generation: new URL(location.href).searchParams.get('mmx_generation'),
      theme: document.documentElement.dataset.theme, lang: document.documentElement.dataset.lang,
      view: control('set_view'), horizon: control('set_horizon'), basis: control('set_basis'),
      market: q('[data-im-history-panel] select[data-im-action="select_market"]')?.value ?? null,
      history_tab: q('[data-im-history-panel]')?.getAttribute('data-im-history-tab') || null,
      scenario_tab: q('[data-im-scenario-tab="scenario"]')?.getAttribute('aria-pressed') || null,
      context: q('[data-im-scenario-context]')?.textContent || '', candidate: q('[data-im-scenario-candidate-context]')?.textContent || '',
      local: q('[data-im-scenario-field="local"]')?.value ?? null, fx: q('[data-im-scenario-field="fx"]')?.value ?? null,
      usd: q('[data-im-scenario-usd]')?.textContent || '', result_hidden: q('[data-im-scenario-result]')?.hidden ?? null,
      pending_hidden: q('[data-im-scenario-confirm-context]')?.hidden ?? null,
      reset_hidden: q('[data-im-scenario-confirm-reset]')?.hidden ?? null,
      result_rows: q('[data-im-scenario-rows]')?.children.length ?? null,
      calculate_disabled: q('[data-im-scenario-action="calculate"]')?.disabled ?? null,
      request_reset_disabled: q('[data-im-scenario-action="request_reset"]')?.disabled ?? null,
      fields_disabled: ['local','fx'].map(field => q('[data-im-scenario-field="'+field+'"]')?.matches(':disabled') ?? null),
      tools_open: document.getElementById('intl-analysis-tools')?.open === true,
      active_id: active?.id || '', active_tag: active?.tagName || '',
      active_action: active?.getAttribute('data-im-action') || null,
      active_field: active?.getAttribute('data-im-scenario-field') || null,
      active_connected: active?.isConnected === true, active_blocked: blocked,
    };
  });
  return {parent, child};
}

function businessQuery(input) {
  const search = new URL(input).search;
  if (!search) return '';
  const parts = search.slice(1).split('&').filter(part => {
    try { return !['mmx_shell','mmx_generation'].includes(decodeURIComponent(part.split('=')[0].replace(/\+/g,' '))); }
    catch (_) { return true; }
  });
  return parts.length ? '?' + parts.join('&') : '';
}

async function preferences(page, frame, scope, width) {
  const bar = page.locator(width === 390 ? '.mobilebar' : '.topbar');
  const before = await snap(page, frame);
  const choices = [['theme', /^(Light theme|浅色主题)$/, ['dark','light']],
    ['lang', /^(Chinese language|中文界面)$/, ['en','zh']]];
  for (const [key, name, options] of choices) {
    const original = before.parent[key];
    assert(options.includes(original), 'Known initial public presentation value');
    for (const expected of [options.find(x => x !== original), original]) {
      const button = bar.getByRole('button', {name});
      assert.equal(await button.count(), 1, 'One visible-chrome presentation control');
      check(scope, key+'_control_clickable_'+expected, await clickable(page, button));
      await button.click();
      await page.waitForFunction(({key,expected}) => document.documentElement.dataset[key] === expected,
        {key,expected}, {timeout: 10000});
      await frame.waitForFunction(({key,expected}) => document.documentElement.dataset[key] === expected,
        {key,expected}, {timeout: 10000});
      const after = await snap(page, frame);
      check(scope, key+'_visible_choice_'+expected,
        await button.getAttribute('aria-pressed') === String(expected === options[1]) &&
        await button.evaluate(el => document.activeElement === el) &&
        after.parent.url === before.parent.url && after.parent.history === before.parent.history &&
        same(after.parent.entry,before.parent.entry) && after.child.url === before.child.url &&
        after.child.generation === before.child.generation && await frameFor(page) === frame,
        {before,after});
      await screenshot(page,scope,key+'-'+expected);
    }
  }
}

async function scenario(page, frame, scope) {
  await frame.locator('[data-im-scenario-tab="scenario"]').click();
  const local = frame.locator('[data-im-scenario-field="local"]');
  const fx = frame.locator('[data-im-scenario-field="fx"]');
  await local.fill('5.25'); await fx.fill('-1.5');
  await frame.locator('[data-im-scenario-action="calculate"]').click();
  const baseline = await snap(page,frame);
  check(scope,'scenario_initial_real_calculation',baseline.child.view==='history' && baseline.child.horizon==='3m' &&
    baseline.child.basis==='local' && baseline.child.usd==='3.67%' && baseline.child.result_hidden===false &&
    baseline.child.pending_hidden===true,{baseline});
  assert(baseline.child.usd==='3.67%' && baseline.child.pending_hidden===true,'Nonvacuous real Scenario starting point');
  const horizon = frame.locator('[data-im-controls] select[data-im-action="set_horizon"]');
  await horizon.selectOption('1m');
  await frame.locator('[data-im-scenario-confirm-context]').waitFor({state:'visible'});
  await local.fill('12'); await fx.fill('4');
  const pending = await snap(page,frame);
  check(scope,'scenario_horizon_proposal_is_uncommitted',pending.child.pending_hidden===false &&
    pending.child.result_hidden===true && pending.child.local==='12' && pending.child.fx==='4' &&
    pending.child.candidate.includes('1m') && pending.child.horizon==='3m' &&
    pending.parent.url===baseline.parent.url && pending.parent.history===baseline.parent.history &&
    pending.child.generation===baseline.child.generation,{pending});
  check(scope,'scenario_pending_horizon_disables_calculate_and_reset',
    pending.child.calculate_disabled===true && pending.child.request_reset_disabled===true &&
    same(pending.child.fields_disabled,[false,false]),{pending});
  await frame.locator('[data-im-scenario-action="cancel_context"]').click();
  await frame.locator('[data-im-scenario-confirm-context]').waitFor({state:'hidden'});
  const cancelled = await snap(page,frame);
  check(scope,'scenario_cancel_restores_raw_draft_result_and_focus',cancelled.child.local==='5.25' &&
    cancelled.child.fx==='-1.5' && cancelled.child.usd==='3.67%' && cancelled.child.result_hidden===false &&
    cancelled.child.horizon==='3m' && cancelled.child.basis==='local' &&
    cancelled.child.active_action==='set_horizon' && cancelled.child.active_tag==='SELECT' &&
    cancelled.parent.url===baseline.parent.url && cancelled.parent.history===baseline.parent.history &&
    cancelled.child.generation===baseline.child.generation,{baseline,cancelled});
  const basis = frame.locator('[data-im-controls] select[data-im-action="set_basis"]');
  await basis.selectOption('usd_unhedged');
  await frame.locator('[data-im-scenario-confirm-context]').waitFor({state:'visible'});
  await local.fill('6'); await fx.fill('-2');
  const pendingBasis = await snap(page,frame);
  check(scope,'scenario_basis_proposal_keeps_original_url',pendingBasis.child.pending_hidden===false &&
    pendingBasis.child.basis==='local' && pendingBasis.child.local==='6' && pendingBasis.child.fx==='-2' &&
    pendingBasis.parent.url===baseline.parent.url && pendingBasis.parent.history===baseline.parent.history,
    {pending:pendingBasis});
  check(scope,'scenario_pending_basis_disables_calculate_and_reset',
    pendingBasis.child.calculate_disabled===true && pendingBasis.child.request_reset_disabled===true &&
    same(pendingBasis.child.fields_disabled,[false,false]),{pending:pendingBasis});
  await frame.locator('[data-im-scenario-action="confirm_context"]').click();
  await page.waitForURL(url => url.origin===PARENT && url.pathname==='/intl.html' &&
    url.searchParams.get('basis')==='usd_unhedged',{timeout:15000});
  await frame.locator('[data-im-scenario-confirm-context]').waitFor({state:'hidden'});
  const confirmed = await snap(page,frame);
  const parentUrl = new URL(confirmed.parent.url), childUrl = new URL(confirmed.child.url);
  const confirmedExpectedUrl = baseline.parent.url.replace('basis=local','basis=usd_unhedged');
  check(scope,'scenario_confirm_commits_once_and_calculates',confirmed.child.local==='6' &&
    confirmed.child.fx==='-2' && confirmed.child.usd==='3.88%' && confirmed.child.result_hidden===false &&
    confirmed.child.basis==='usd_unhedged' && confirmed.child.horizon==='3m' && confirmed.child.active_field==='local' &&
    parentUrl.searchParams.get('market')==='TW' && parentUrl.searchParams.get('horizon')==='3m' &&
    parentUrl.searchParams.get('view')==='history' && childUrl.searchParams.get('basis')==='usd_unhedged' &&
    confirmed.parent.url===confirmedExpectedUrl && businessQuery(confirmed.child.url)===parentUrl.search &&
    confirmed.parent.history===baseline.parent.history+1 && confirmed.child.generation===baseline.child.generation &&
    await frameFor(page)===frame,{confirmed});
  await screenshot(page,scope,'scenario-confirmed');
  // Parent history creates a fresh child document. createDraft initializes empty
  // assumptions and the History tab; the research query, not a manual draft,
  // belongs to the restored history entry. Never require stale result retention.
  let currentFrame = frame;
  for (const [action,expected] of [['goBack',baseline],['goForward',confirmed]]) {
    const before = await snap(page,currentFrame), priorFrame = currentFrame;
    await page[action]({waitUntil:'domcontentloaded',timeout:20000});
    await page.waitForURL(expected.parent.url,{timeout:15000});
    const until = Date.now()+20000;
    let after;
    do {
      currentFrame = await frameFor(page);
      after = await snap(page,currentFrame);
      if (currentFrame!==priorFrame && after.child.generation!==before.child.generation &&
          after.parent.url===expected.parent.url && businessQuery(after.child.url)===new URL(expected.parent.url).search) break;
      await sleep(100);
    } while (Date.now()<until);
    const expectedUrl = new URL(expected.parent.url), actualChild = new URL(after.child.url);
    check(scope,'scenario_'+action+'_restores_exact_entry_and_fresh_document',
      after.parent.url===expected.parent.url && same(after.parent.entry,expected.parent.entry) &&
      !!after.parent.entry && after.parent.history===confirmed.parent.history &&
      currentFrame!==priorFrame && !!after.child.generation && after.child.generation!==before.child.generation &&
      actualChild.origin===CHILD && actualChild.pathname===expectedUrl.pathname && actualChild.hash===expectedUrl.hash &&
      businessQuery(after.child.url)===expectedUrl.search,{before,after,expected_parent:expected.parent});
    check(scope,'scenario_'+action+'_restores_research_context',after.child.view==='history' &&
      after.child.market==='TW' && after.child.horizon==='3m' && after.child.basis===expected.child.basis &&
      after.child.context===expected.child.context && after.child.tools_open,{after,expected_context:expected.child.context});
    check(scope,'scenario_'+action+'_starts_a_fresh_empty_draft',after.child.local==='' && after.child.fx==='' &&
      after.child.usd==='' && after.child.result_hidden===true && after.child.result_rows===0 &&
      after.child.pending_hidden===true && after.child.reset_hidden===true && after.child.candidate==='' &&
      after.child.history_tab==='history' && after.child.scenario_tab==='false' &&
      after.child.calculate_disabled===false && after.child.request_reset_disabled===false &&
      same(after.child.fields_disabled,[false,false]),{after,
        contract:'Reviewed createDraft initializes empty raw inputs, null result/pending/reset and History tab in each new document.'});
    check(scope,'scenario_'+action+'_focus_belongs_to_visible_current_document',
      after.child.active_connected && after.child.active_blocked.length===0,{after,
        qualification:'Records focus usability only. No specific history focusId was captured here; exact saved-focus restoration remains in the v13 journey. Cancel and Confirm have their own exact target assertions above.'});
    await screenshot(page,scope,'scenario-'+action);
  }
  return currentFrame;
}

async function assistant(page, owner, scope, inFrame) {
  const initial = owner.locator('#mmb-launch:visible, #mmb-boot:visible');
  await owner.waitForFunction(() => [...document.querySelectorAll('#mmb-launch,#mmb-boot')]
    .filter(el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden').length === 1,
    null, {timeout:30000});
  await initial.waitFor({state:'visible',timeout:30000});
  assert.equal(await initial.count(),1,'Exactly one incumbent visible assistant launcher');
  check(scope,'assistant_initial_launcher_clickable',await clickable(page,initial,inFrame));
  await initial.click();
  const panel = owner.locator('#mmb-panel');
  await panel.waitFor({state:'visible',timeout:30000});
  await owner.waitForFunction(() => document.querySelector('#mmb-panel')?.contains(document.activeElement),null,{timeout:10000});
  check(scope,'assistant_visible_open_and_focus',await panel.evaluate(el => el.classList.contains('open') && el.contains(document.activeElement)));
  await screenshot(page,scope,'assistant-open');
  const close = owner.locator('#mmb-panel button[data-act="close"]');
  check(scope,'assistant_close_is_visible_control',await clickable(page,close,inFrame));
  await close.click();
  await panel.waitFor({state:'hidden',timeout:10000});
  const launcher = owner.locator('#mmb-launch');
  check(scope,'assistant_close_returns_keyboard_focus',await launcher.getAttribute('aria-expanded')==='false' &&
    await launcher.evaluate(el => document.activeElement===el) && await clickable(page,launcher,inFrame));
  await launcher.press('Enter');
  await panel.waitFor({state:'visible',timeout:10000});
  await owner.waitForFunction(() => document.querySelector('#mmb-panel')?.contains(document.activeElement),null,{timeout:10000});
  check(scope,'assistant_real_keyboard_reopen',await launcher.getAttribute('aria-expanded')==='true' &&
    await panel.evaluate(el => el.classList.contains('open') && el.contains(document.activeElement)));
  await close.click();
  await panel.waitFor({state:'hidden',timeout:10000});
}

async function parentContext(playwright, width, height) {
  const scope='parent-'+width+'x'+height;
  const context=await browser.newContext({viewport:{width,height},locale:'en-US',colorScheme:'dark'});
  const owner={scope,kind:'browser_context',resource:context,method:'close',closed:false};
  contexts.push(owner); observe(context,scope);
  assert.equal((await context.cookies()).length,0,'Fresh anonymous context without fixture cookies');
  const page=await context.newPage(); page.setDefaultTimeout(15000);
  report.contexts.push({scope,viewport:{width,height},started_at:now(),storage_seeded:false});
  try {
    await page.goto(PARENT+'/intl.html'+QUERY+'#intl-analysis-tools',{waitUntil:'domcontentloaded',timeout:60000});
    let frame=await frameFor(page);
    await preferences(page,frame,scope,width);
    frame=await scenario(page,frame,scope);
    await assistant(page,frame,scope,true);
    await drain(scope);
  } catch(error) {check(scope,'journey_completed',false,{error:String(error.message).slice(0,1500)});}
  finally {await finishContext(owner);}
}

async function countriesContext(width,height) {
  const scope='standalone-'+width+'x'+height;
  const context=await browser.newContext({viewport:{width,height},locale:'en-US',colorScheme:'dark'});
  const owner={scope,kind:'browser_context',resource:context,method:'close',closed:false};
  contexts.push(owner);observe(context,scope);
  assert.equal((await context.cookies()).length,0,'Fresh standalone anonymous context');
  const page=await context.newPage();page.setDefaultTimeout(15000);
  report.contexts.push({scope,viewport:{width,height},started_at:now(),storage_seeded:false});
  try {
    await page.goto(CHILD+'/intl.html#imc-country-JP',{waitUntil:'domcontentloaded',timeout:60000});
    await page.waitForFunction(() => document.querySelector('[data-im-country-analysis]')?.dataset.imcEnhanced==='true');
    const rail=page.locator('.imc-country-rail');
    check(scope,'all_seven_countries_in_real_rail',same((await rail.locator('a[data-imc-country]').evaluateAll(links=>links.map(x=>x.dataset.imcCountry))).sort(),[...COUNTRIES].sort()));
    for(const cc of COUNTRIES) {
      const link=rail.locator('a[data-imc-country="'+cc+'"]');
      await link.scrollIntoViewIfNeeded();await link.click();
      await page.waitForURL(url=>url.origin===CHILD && url.pathname==='/intl.html' && url.hash==='#imc-country-'+cc);
      const panel=page.locator('#imc-country-'+cc);
      const selection=await panel.evaluate(element=>({
        open:element.open,opened:[...document.querySelectorAll('details.imc-country[open]')].map(x=>x.id),
        focus_is_summary:document.activeElement===element.querySelector(':scope > summary'),
        current:[...document.querySelectorAll('.imc-country-rail a[aria-current="location"]')].map(x=>x.dataset.imcCountry),
      }));
      check(scope,cc+'_country_selection_focus_and_rail',selection.open && same(selection.opened,['imc-country-'+cc]) &&
        selection.focus_is_summary && same(selection.current,[cc]),{selection});
      const evidence=panel.locator('details.imc-evidence');
      if(!await evidence.evaluate(x=>x.open))await evidence.locator(':scope > summary').click();
      const reading=await panel.evaluate(element=>{
        const forecast=element.querySelector('.imc-forecast-path');
        const outlook=element.querySelector('.imc-outlook-panel');
        const evidence=element.querySelector('details.imc-evidence');
        const fx=element.querySelector('.imc-fx-read');
        const rect=element.getBoundingClientRect();
        const charts=[...element.querySelectorAll('.imc-growth-chart svg')].map(svg=>({
          role:svg.getAttribute('role'),label:svg.getAttribute('aria-labelledby'),
          description:document.getElementById(svg.getAttribute('aria-labelledby'))?.textContent || '',
          width:svg.getBoundingClientRect().width,
          labels:[...svg.querySelectorAll('.imc-chart-value,.imc-chart-year,.imc-chart-scale')].map(text=>{
            const m=text.getScreenCTM();const size=parseFloat(getComputedStyle(text).fontSize);
            return {text:text.textContent,rendered_font_px:m?size*Math.hypot(m.a,m.b):0};
          }),
        }));
        return {
          lang:document.documentElement.dataset.lang==='zh'?'zh':'en',
          viewport:{width:innerWidth,height:innerHeight},document_width:document.documentElement.scrollWidth,
          body_width:document.body.scrollWidth,panel:{left:rect.left,right:rect.right,width:rect.width},
          forecast_present:!!forecast,forecast_text:forecast?.innerText||'',
          honest_unavailable:!!outlook?.querySelector('.imc-missing') && !!outlook.querySelector('.imc-missing').innerText.trim(),
          forecast_sources:[...(outlook?.querySelectorAll('.imc-source-line a')||[])].map(a=>({href:a.href,text:a.innerText})),
          forecast_source_text:[...(outlook?.querySelectorAll('.imc-source-line')||[])].map(x=>x.innerText).join(' '),
          evidence_open:evidence?.open===true,captions:[...(evidence?.querySelectorAll('table caption')||[])].map(x=>x.innerText),
          source_links:[...(evidence?.querySelectorAll('a[href]')||[])].map(a=>({href:a.href,text:a.innerText})),
          evidence_text:evidence?.innerText.slice(0,1400)||'',fx_quality:fx?.dataset.fxQuality||null,
          fx_value:fx?.querySelector('strong')?.innerText||'',fx_date:fx?.querySelector('.imc-fx-date')?.innerText||'',
          currency_ledger:element.querySelector('.imc-currency-ledger')?.innerText||'',
          currency_ledger_cells:[...(element.querySelectorAll('.imc-currency-ledger > td')||[])].map(x=>x.innerText),
          currency_source:element.querySelector('.imc-currency-ledger a')?.getAttribute('href')||null,
          quoted_rates:element.querySelector('.imc-currency-quotes')?.innerText||'',charts,
        };
      });
      const oracle=countryOracle.countries[cc],normalized=value=>String(value).replace(/\s+/g,' ').trim();
      check(scope,cc+'_dated_forecast_or_honest_absence',reading.forecast_present ?
        /\d/.test(reading.forecast_text) && reading.forecast_sources.length>0 &&
        /\d{4}-\d{2}-\d{2}/.test(reading.forecast_source_text) &&
        reading.forecast_sources.every(x=>/^https?:\/\//.test(x.href)) : reading.honest_unavailable,{reading});
      check(scope,cc+'_evidence_is_open_and_attributed',reading.evidence_open &&
        reading.captions.some(x=>/Observation ledger|观测记录/.test(x)) &&
        reading.captions.some(x=>/Projection sources|预测来源/.test(x)) &&
        reading.source_links.length>0 && reading.source_links.every(x=>/^https?:\/\//.test(x.href)),{captions:reading.captions});
      check(scope,cc+'_actual_acquired_fx_is_rendered',reading.fx_quality===oracle.fx_quality &&
        normalized(reading.fx_value)===oracle.fx_value && normalized(reading.fx_date)===oracle.fx_date[reading.lang] &&
        normalized(reading.quoted_rates)===oracle.quoted_rates[reading.lang] && reading.currency_ledger_cells.length===4 &&
        normalized(reading.currency_ledger_cells[1])===oracle.ledger_value &&
        normalized(reading.currency_ledger_cells[2])===oracle.ledger_dates && reading.currency_source===oracle.source_url,
        {quality:reading.fx_quality,value:reading.fx_value,date:reading.fx_date,ledger:reading.currency_ledger,
          quoted_rates:reading.quoted_rates,oracle});
      check(scope,cc+'_viewport_geometry',reading.viewport.width===width && reading.viewport.height===height &&
        reading.document_width<=width+1 && reading.body_width<=width+1 && reading.panel.left>=-1 && reading.panel.right<=width+1,
        {viewport:reading.viewport,document_width:reading.document_width,body_width:reading.body_width,panel:reading.panel});
      check(scope,cc+'_chart_labels_and_accessible_description',reading.charts.length===oracle.chart_count &&
        (oracle.chart_count>0 || oracle.explicit_chart_unavailability && reading.honest_unavailable) &&
        reading.charts.every(chart=>chart.role==='img' &&
        chart.description.trim().length>0 && chart.width>0 && chart.labels.length>0 &&
        chart.labels.every(label=>label.rendered_font_px>=9.9)),{charts:reading.charts,
        expected_chart_count:oracle.chart_count,explicit_published_unavailability:oracle.explicit_chart_unavailability,
        qualification:reading.charts.length?'All publication-declared charts measured':'Zero charts permitted only with the publication-bound explicit unavailable state'});
      await panel.locator(':scope > summary').scrollIntoViewIfNeeded();
      await screenshot(page,scope,cc);
    }
    await assistant(page,page,scope,false);
    await drain(scope);
  } catch(error) {check(scope,'journey_completed',false,{error:String(error.message).slice(0,1500)});}
  finally {await finishContext(owner);}
}

async function anonymousAccess(playwright) {
  const scope='anonymous-access';
  const client=await playwright.request.newContext({ignoreHTTPSErrors:false,extraHTTPHeaders:{'Accept-Encoding':'identity'}});
  const clientOwner={scope,kind:'api_client',resource:client,method:'dispose',closed:false};apiClients.push(clientOwner);
  const ownerId=scope+'/client/'+apiClients.length;
  try {
    const urls=[PARENT+'/api/shared-shell/status',...Object.keys(childExpected).map(x=>CHILD+x),...PRIVATE_ASSETS.map(x=>CHILD+x)];
    assert(urls.length<=256,'Finite public-resource access inventory');
    for(const url of urls) {
      const u=new URL(url),isPrivate=PRIVATE_ASSETS.includes(u.pathname);
      const requestRow={scope,request_id:++requestSequence,page_id:null,owner_kind:'direct-get',owner_id:ownerId,
        url,method:'GET',resource_type:'direct-read-only-access-probe',first_party:true,
        authorization_present:false,terminal:'pending',started_at:now()};report.requests.push(requestRow);
      let row=null,responseOwner=null;
      try {
        const response=await client.get(url,{timeout:20000,maxRedirects:0,failOnStatusCode:false,
          headers:{Accept:u.pathname.startsWith('/api/')||isPrivate?'application/json':'*/*'}});
        responseOwner={scope,kind:'api_response',resource:response,method:'dispose',closed:false};apiResponses.push(responseOwner);
        row={scope,sequence:++sequence,request_id:requestRow.request_id,page_id:null,owner_kind:'direct-get',owner_id:ownerId,
          url:response.url(),requested_url:url,method:'GET',resource_type:'direct-read-only-access-probe',body_state:'pending',
          status:response.status(),...responseFields(response.headers()),if_none_match:null,if_modified_since:null};
        requestRow.response_sequence=row.sequence;requestRow.terminal='finished';requestRow.finished_at=now();report.responses.push(row);
        assert.equal(row.url,url,'Direct GET did not redirect');
        if(isPrivate && row.status!==401) {
          row.body_state='intentionally_unread_protected_response';row.body_not_collected=true;
          check(scope,'protected_refusal_'+u.pathname,false,{status:row.status,body_not_collected:true});
          continue;
        }
        if(row.status===304) {
          row.body_state='bodyless304';
          throw new Error('Unconditional direct GET has no prior validator for a 304');
        }
        assert(!/text\/event-stream/i.test(row.content_type||''),'Streaming access response has no finite contract');
        const body=await bounded(response.body(),20000,'Anonymous access response');
        assert(body.length<=64*1024*1024,'Bounded public response');
        row.sha256=hash(body);row.bytes=body.length;row.body_state='complete';
        if(isPrivate || u.pathname==='/api/shared-shell/status')row.safe_json=safeJsonProjection(body);
        if(isPrivate)check(scope,'protected_refusal_'+u.pathname,legitimateAnonymousResponse(row),{response_sequence:row.sequence});
        else if(u.origin===PARENT)check(scope,'public_parent_full_status',row.status===200 &&
          sameTuple(row.safe_json.public_status,release.parent.status) && /\bprivate\b/.test(row.cache_control||'') &&
          /\bno-store\b/.test(row.cache_control||''),{response_sequence:row.sequence});
        else {const pin=childExpected[u.pathname];check(scope,
          (pin.binding_kind==='normal-updater-runtime-overlay'?'public_exact_runtime_overlay_':'public_exact_artifact_')+u.pathname,
          row.status===200 && row.sha256===pin.sha256 && row.bytes===pin.bytes,
          {response_sequence:row.sequence,binding_kind:pin.binding_kind});}
      } catch(error) {
        if(row){row.body_state='failed';row.body_error=String(error.message).slice(0,1000);}
        else {requestRow.terminal='failed';requestRow.finished_at=now();requestRow.failure=String(error.message).slice(0,1000);}
        check(scope,'direct_get_completed_'+u.pathname,false,{request_id:requestRow.request_id,error:String(error.message).slice(0,1000)});
      } finally {if(responseOwner)await closeOwned(responseOwner);}
    }
  } finally {await closeOwned(clientOwner);save();}
}

function finalNetworkChecks() {
  for(const row of report.responses)if(row.status===304)row.revalidation=cacheEvidence(row,report.responses);
  const bound=report.responses.filter(row=>expectedAsset(row.url));
  for(const row of bound)row.asset_binding_kind=expectedAsset(row.url).binding_kind||'parent-live-host-static';
  const bad=bound.filter(row=>{const pin=expectedAsset(row.url);return row.method!=='GET' || row.body_error ||
    !(row.status===200 && row.body_state==='complete' && row.sha256===pin.sha256 && row.bytes===pin.bytes || row.status===304 && row.revalidation);});
  check('custody','all_observed_bound_assets_match',bound.length>0 && bad.length===0,{responses:bound.length,bad});
  const unknown=report.responses.filter(row=>{
    const u=new URL(row.url);
    return (u.origin===PARENT && u.pathname.startsWith('/_next/static/') ||
      u.origin===CHILD && ['script','stylesheet','font'].includes(row.resource_type)) && !expectedAsset(row.url);
  });
  check('custody','no_unbound_first_party_code_style_or_font',unknown.length===0,{unknown});
  const documents=report.responses.filter(row=>new URL(row.url).origin===PARENT && row.resource_type==='document');
  check('custody','parent_html_names_the_host_bound_artifact',documents.length>=2 && documents.every(row=>
    row.method==='GET' && row.status===200 && !row.body_error && row.body_state==='complete' &&
    row.owner_kind==='browser-page' && Number.isSafeInteger(row.page_id) && row.page_id>0 && row.document_identity?.verified &&
    report.responses.some(asset=>asset.scope===row.scope && asset.page_id===row.page_id &&
      asset.owner_kind==='browser-page' && asset.owner_id===row.owner_id && asset.body_state==='complete' && !asset.body_error &&
      new URL(asset.url).origin===PARENT && new URL(asset.url).pathname.startsWith('/_next/static/') &&
      asset.method==='GET' && asset.status===200 && expectedAsset(asset.url)?.sha256===asset.sha256 &&
      expectedAsset(asset.url)?.bytes===asset.bytes)),{documents});
  const unownedStatic=report.responses.filter(row=>new URL(row.url).origin===PARENT &&
    new URL(row.url).pathname.startsWith('/_next/static/') &&
    !(row.owner_kind==='browser-page' && Number.isSafeInteger(row.page_id) && row.page_id>0));
  check('custody','parent_static_resources_have_actual_page_owners',unownedStatic.length===0,{responses:unownedStatic});
  const statuses=report.responses.filter(row=>new URL(row.url).origin===PARENT &&
    new URL(row.url).pathname==='/api/shared-shell/status');
  check('custody','every_observed_parent_status_matches',statuses.length>0 && statuses.every(row=>
    row.method==='GET' && row.status===200 && !row.body_error &&
    sameTuple(row.safe_json?.public_status,release.parent.status) && /\bprivate\b/.test(row.cache_control||'') &&
    /\bno-store\b/.test(row.cache_control||'')),{responses:statuses.length});
  const firstPartyResponses=report.responses.filter(row=>firstParty(row.url));
  const failedRequests=report.requests.filter(row=>row.first_party && (row.terminal!=='finished' ||
    !row.response_sequence || !firstPartyResponses.some(response=>response.sequence===row.response_sequence &&
      response.request_id===row.request_id && response.scope===row.scope && response.owner_kind===row.owner_kind && response.owner_id===row.owner_id)));
  const unlinked=firstPartyResponses.filter(row=>!report.requests.some(request=>request.request_id===row.request_id &&
    request.response_sequence===row.sequence && request.scope===row.scope && request.owner_kind===row.owner_kind && request.owner_id===row.owner_id));
  check('network','complete_first_party_request_response_census',failedRequests.length===0 && unlinked.length===0,
    {requests:failedRequests,unlinked_responses:unlinked});
  const incompleteBodies=firstPartyResponses.filter(row=>row.body_error ||
    !(row.status===304 ? row.body_state==='bodyless304' && !!row.revalidation :
      row.body_state==='complete' && sha64(row.sha256) && Number.isSafeInteger(row.bytes) && row.bytes>=0));
  check('network','every_first_party_body_has_a_complete_outcome',incompleteBodies.length===0,{responses:incompleteBodies});
  const unsupported=firstPartyResponses.filter(row=>!(row.status>=200 && row.status<300 ||
    row.status===304 && row.revalidation || legitimateAnonymousResponse(row)));
  check('network','explicit_first_party_status_contract',unsupported.length===0,{responses:unsupported,
    policy:'2xx with separately complete bodies; 304 only against an earlier exact URL/owner/expected-body/validator match; only listed anonymous endpoint refusals. No generic 3xx, 304, auth, or body-error waiver.'});
  const identityReads=report.responses.filter(row=>{
    const u=new URL(row.url);
    return row.method==='GET' && !u.search && (u.origin===CHILD &&
      ['/api/brain/me','/api/me','/api/account'].includes(u.pathname) || u.origin===PARENT && u.pathname==='/api/me');
  });
  check('anonymous','documented_guest_identity_status_and_safe_fields',identityReads.every(legitimateAnonymousResponse),
    {responses:identityReads.map(row=>({sequence:row.sequence,url:row.url,status:row.status,safe_json:row.safe_json})),
      qualification:'The listed 401 identity responses require an exact endpoint, GET, JSON object and complete body; no stronger error-envelope schema is claimed. Guest 200 responses and protected-data refusal fields have their explicit predicates.'});
  const mutations=report.requests.filter(row=>firstParty(row.url) && !['GET','HEAD','OPTIONS'].includes(row.method) &&
    /^\/api\/(?:brain(?:\/|$)|account(?:\/|$)|auth(?:\/|$)|preferences(?:\/|$))/.test(new URL(row.url).pathname));
  const credentials=report.requests.filter(row=>row.authorization_present);
  check('anonymous','no_chat_or_account_mutations_or_bearer_credentials',mutations.length===0 && credentials.length===0,
    {mutations,credential_request_ids:credentials.map(x=>x.request_id)});
  report.observed_non_read_requests=report.requests.filter(row=>!['GET','HEAD','OPTIONS'].includes(row.method));
  const consoleFailures=[];
  for(const error of report.console_errors) {
    const matching=report.responses.filter(row=>Number.isInteger(error.page_id) && error.page_id>0 &&
      row.owner_kind==='browser-page' && row.page_id===error.page_id &&
      row.owner_id===error.scope+'/page/'+error.page_id && row.scope===error.scope &&
      row.url===error.url && row.status===401 && legitimateAnonymousResponse(row));
    error.documented_anonymous_resource_notice=matching.length>0 && /^Failed to load resource: the server responded with a status of 401\b/.test(error.message);
    if(!error.documented_anonymous_resource_notice)consoleFailures.push(error);
  }
  check('runtime','no_unexpected_console_or_page_errors',report.page_errors.length===0 && consoleFailures.length===0,
    {page_errors:report.page_errors,console_errors:consoleFailures});
  report.external_responses=report.responses.filter(row=>!firstParty(row.url)).map(row=>({
    scope:row.scope,url:row.url,status:row.status,method:row.method,resource_type:row.resource_type,
    sha256:row.sha256,bytes:row.bytes,body_error:row.body_error||null,
  }));
}

(async()=>{
  try {
    const args=argumentsFor(process.argv.slice(2));output=args.output;
    assert(!fs.existsSync(output),'Output must be a new directory; reconcile earlier observations instead of overwriting');
    fs.mkdirSync(output,{recursive:true,mode:0o700});
    report={schema:'intl.production_additions.v1',environment:'production',started_at:now(),
      pass:false,overall_served_acceptance:false,selector_sources:SELECTOR_SOURCES,
      driver_sha256:hash(readFile(__filename)),contexts:[],cases:[],requests:[],responses:[],screenshots:[],page_errors:[],console_errors:[],
      cleanup:[],result:'PENDING_EXECUTION',
      network_interception:false,fixture_cookies:false,injected_messages:false,storage_seeded:false,
      qualification:{scope:'Finite genuine public presentation, Scenario, assistant, country and access journeys',
        parent_build_reproduced:false,external_asset_hashes_are_observations_not_a_reproduced_build:true,
        required_external_completion:'Owner must reconcile the same accepted runtime and complete static map in a fresh post-journey host receipt; combine with accepted v13 production proof before overall served acceptance'}};
    const manifestBytes=readFile(args['release-manifest']);release=JSON.parse(manifestBytes);
    assert.equal(release.schema,'intl.production_release_inputs.v1');
    assert.equal(release.parent.origin,PARENT);assert.equal(release.child_origin,CHILD);
    assert.equal(release.parent.source_commit,PARENT_SOURCE,'Selectors are reviewed for this exact served parent source');
    assert.equal(path.resolve(release.artifact.directory),args.artifact);
    assert(sameTuple(release.parent.status,{enabled:true,protocol:'mmx.shared-shell.v1',buildId:PARENT_SOURCE,
      bridgeVersion:'20261018.1',documentVersion:'20261018.1',registrySha256:'868b5ff4ab2dd974228ec53a857dbba24c07ce164e2996e8721524a47e1edd8f'}));
    const files=release.artifact.files;assert(files && typeof files==='object' && Object.keys(files).length<=240);
    for(const name of REQUIRED_ARTIFACTS)assert(files[name],'Missing artifact '+name);
    const repository=args.repository;
    const at=(sha,name)=>{
      assert(sha40(sha),'Exact source commit required');safePath(name);
      const size=Number(execFileSync('git',['-C',repository,'cat-file','-s',sha+':'+name],{timeout:30000,maxBuffer:1024}).toString().trim());
      assert(Number.isSafeInteger(size) && size>=0 && size<=64*1024*1024,'Bounded Git blob');
      const bytes=execFileSync('git',['-C',repository,'show',sha+':'+name],{timeout:60000,maxBuffer:Math.max(4096,size+1024)});
      assert.equal(bytes.length,size);return bytes;
    };
    const ancestor=(a,b)=>{assert(sha40(a)&&sha40(b));try{execFileSync('git',['-C',repository,'merge-base','--is-ancestor',a,b],{timeout:30000,stdio:'ignore'});return true;}catch(_){return false;}};
    const helperPath=path.join(__dirname,'validate_production_release_v3.cjs'),helperHash=hash(readFile(helperPath));
    const custody=require(helperPath)({release,at,ancestor,hash,repository,artifact:args.artifact});
    assert.equal(hash(readFile(helperPath)),helperHash,'Custody helper changed during validation');
    assert.equal(custody.pass,true);
    assert(sha40(SELECTOR_SOURCES.macro.reviewed_commit),'Unresolved actual composition source for selector review');
    assert.equal(custody.inventory_qualification.reviewed_source,SELECTOR_SOURCES.macro.reviewed_commit,'Selector review belongs to this exact composed source');
    assert.equal(custody.inventory_qualification.composition_reference_main,SELECTOR_SOURCES.macro.composition_reference_main);
    parentExpected=custody.parent_static_files;
    childExpected={};const artifactBindings=[];
    for(const [name,pin] of Object.entries(files)){
      safePath(name);assert(sha64(pin.sha256)&&Number.isSafeInteger(pin.bytes)&&pin.bytes>=0);
      const local=readFile(path.join(args.artifact,name)),published=at(release.render.publication_commit,'site/'+name);
      assert.equal(hash(local),pin.sha256);assert.equal(local.length,pin.bytes);assert(local.equals(published),'Generated publication does not match artifact '+name);
      childExpected['/'+name]={sha256:pin.sha256,bytes:pin.bytes,binding_kind:'generated-publication'};
      artifactBindings.push({name,...childExpected['/'+name]});
    }
    assert(same(Object.keys(custody.child_runtime_overlays||{}),['logo_config.js']), 'Exactly the separately reviewed normal-updater logo overlay');
    const runtimeOverlayBindings=[];
    for(const [name,pin] of Object.entries(custody.child_runtime_overlays)){
      assert(!Object.hasOwn(files,name) && name==='logo_config.js' && sha64(pin.sha256) &&
        Number.isSafeInteger(pin.bytes) && pin.bytes>0,'Bounded runtime-only overlay identity');
      childExpected['/'+name]={sha256:pin.sha256,bytes:pin.bytes,binding_kind:'normal-updater-runtime-overlay'};
      runtimeOverlayBindings.push({name,...pin});
    }
    countryOracle=countryOracles(readFile(path.join(args.artifact,'intl.html')),custody.acquisition.currency_observations);
    assert.equal(countryOracle.html_sha256,files['intl.html'].sha256,'Oracle uses exact publication-bound HTML');
    report.country_oracle=countryOracle;report.runtime_overlay_bindings=runtimeOverlayBindings;
    const sourceBindings=custody.source_paths.map(name=>{
      const candidate=at(release.accepted_candidate,name),adopted=at(release.accepted_main,name),rendered=at(release.render.source_commit,name);
      assert(candidate.equals(adopted)&&candidate.equals(rendered),'Source applicability changed: '+name);
      return {name,sha256:hash(candidate),bytes:candidate.length};
    });
    const selectorBindings=Object.entries(SELECTOR_SOURCES.macro.files).map(([name,blob])=>{
      const candidate=at(release.accepted_candidate,name),rendered=at(release.render.source_commit,name);
      assert.equal(gitBlob(candidate),blob,'Reviewed selector/access source changed: '+name);
      assert(candidate.equals(rendered),'Selector/access source changed before rendering');
      return {name,git_blob:blob,sha256:hash(candidate),bytes:candidate.length};
    });
    for(const [name,pin] of Object.entries(SELECTOR_SOURCES.macro.sha256_files)){
      const candidate=at(release.accepted_candidate,name),rendered=at(release.render.source_commit,name);
      assert.equal(hash(candidate),pin,'Reviewed interaction source changed: '+name);
      assert(candidate.equals(rendered),'Interaction source changed before rendering');
      selectorBindings.push({name,sha256:pin,git_blob:gitBlob(candidate),bytes:candidate.length});
    }
    const updaterBytes=readFile(release.updater.receipt_path),updater=JSON.parse(updaterBytes);
    assert.equal(hash(updaterBytes),release.updater.receipt_sha256);assert.equal(updater.pass,true);
    assert.equal(updater.checkout_commit,release.updater.checkout_commit);
    assert.equal(updater.render_publication_commit,release.render.publication_commit);
    assert(ancestor(release.accepted_main,release.render.source_commit));
    assert(ancestor(release.acquisition.publication_commit,release.render.source_commit));
    assert(ancestor(release.render.source_commit,release.render.publication_commit));
    assert(ancestor(release.render.publication_commit,release.updater.checkout_commit));
    for(const [name,pin] of Object.entries(files))assert(updater.served_files?.[name]?.sha256===pin.sha256 && updater.served_files?.[name]?.bytes===pin.bytes,'Updater asset binding '+name);
    report.release_manifest={path:args['release-manifest'],sha256:hash(manifestBytes)};
    report.release_custody=custody;report.custody_helper_sha256=helperHash;
    report.parent_host_receipt=custody.parent_host_receipt;
    report.subject=release.accepted_candidate;report.accepted_main=release.accepted_main;report.render=release.render;
    report.source_bindings=sourceBindings;report.selector_bindings=selectorBindings;report.artifact_bindings=artifactBindings;
    report.updater_receipt_sha256=hash(updaterBytes);save();
    const playwright=require(args.playwright);
    browser=await playwright.chromium.launch({headless:true});
    browserOwner={scope:'runtime',kind:'browser',resource:browser,method:'close',closed:false};
    for(const [width,height] of [[1440,900],[390,844]])await parentContext(playwright,width,height);
    for(const [width,height] of [[1440,900],[390,844]])await countriesContext(width,height);
    await anonymousAccess(playwright);
    report.result='PENDING_CLEANUP';save();
  } catch(error) {
    if(report){report.pass=false;report.error=String(error.message).slice(0,2000);
      check('runtime','setup_and_execution_completed',false,{error:report.error});}
    else {process.stdout.write(JSON.stringify({schema:'intl.production_additions.v1',pass:false,result:'SETUP_FAILURE',error:String(error.message).slice(0,1000)})+'\n');process.exitCode=2;return;}
  } finally {
    if(report){
      // Failed journeys can leave resources outside their normal local finally.
      // Cleanup failures are retained as failed cases even if a later retry works.
      for(const owner of contexts)if(!owner.closed)await finishContext(owner);
      for(const owner of apiResponses)if(!owner.closed)await closeOwned(owner);
      for(const owner of apiClients)if(!owner.closed)await closeOwned(owner);
      if(browserOwner)await closeOwned(browserOwner);
      try {await settleResponseTasks('all-owned-resources-closed');}
      catch(error){check('runtime','final_response_population_settled',false,{error:String(error.message)});}
      // Reconcile after browser closure so late body failures, request failures,
      // responses and diagnostics participate in the only final verdict.
      if(childExpected&&parentExpected){
        try {finalNetworkChecks();}
        catch(error){check('runtime','final_network_checks_completed',false,{error:String(error.message)});}
      }
      check('runtime','every_owned_resource_closed',!!browserOwner?.closed &&
        [...contexts,...apiResponses,...apiClients].every(owner=>owner.closed));
      report.passed=report.cases.filter(x=>x.pass).length;report.failed=report.cases.filter(x=>!x.pass).length;
      report.pass=!report.error && report.failed===0;
      report.result=report.error?'SETUP_OR_EXECUTION_FAILURE':report.pass?'PASS_WITH_EXTERNAL_HOST_BRACKET_REQUIRED':'FAIL';
      report.finished_at=now();save();process.stdout.write(JSON.stringify({schema:report.schema,pass:report.pass,result:report.result,
        passed:report.passed,failed:report.failed,report:path.join(output,'observation.json'),
        overall_served_acceptance:false,post_journey_host_bracket_required:true})+'\n');process.exitCode=report.pass?0:2;
    }
  }
})();
