/** Validate the actual local Macro calendar with the exact Terminal reader.
 * Run with native Node TypeScript stripping; no network, server or provider job.
 */
import assert from 'node:assert/strict';
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { parseArgs } from 'node:util';

const { values } = parseArgs({ options: {
  'macro-root': { type: 'string' }, 'terminal-root': { type: 'string' },
  'source-commit': { type: 'string' }, output: { type: 'string' }, now: { type: 'string' },
}, strict: true, allowPositionals: false });
for (const key of ['macro-root', 'terminal-root', 'output']) assert.ok(values[key], `--${key} is required`);
const macro = resolve(values['macro-root']);
const readerPath = resolve(values['terminal-root'], 'terminal/lib/sovereignAuctionContext.ts');
const raw = readFileSync(resolve(macro, 'site/feeds/event_calendar.json'));
const hash = value => createHash('sha256').update(value).digest('hex');
const wrapper = JSON.parse(raw.toString('utf8'));
const nowText = values.now ?? new Date().toISOString();
const nowMs = Date.parse(nowText);
assert.ok(Number.isFinite(nowMs), '--now must be an ISO clock');
if (values['source-commit']) {
  assert.match(values['source-commit'], /^[a-f0-9]{40}$/);
  const committed = execFileSync('git', ['show', `${values['source-commit']}:site/feeds/event_calendar.json`], { cwd: macro, maxBuffer: 4 * 1024 * 1024 });
  assert.deepEqual(committed, raw);
}
const { validateSovereignAuctionContext, auctionDisplayRows } = await import(pathToFileURL(readerPath).href);
const parsed = validateSovereignAuctionContext(wrapper.sovereign_auction_context, nowMs);
assert.equal(parsed.ok, true, 'Exact Terminal validator must accept the real artifact');
assert.equal(parsed.context.status, 'available');
assert.equal(parsed.context.events.length, wrapper.sovereign_auction_context.events.length);
assert.equal(parsed.context.forecast_authority, 'RESEARCH_ONLY');
assert.equal(parsed.context.probabilities, null);
const selected = auctionDisplayRows(parsed.context);
assert.equal(selected.total, parsed.context.events.length);
assert.ok(selected.rows.every(row => typeof row.episode_id === 'string'));
const receipt = {
  schema: 'terminal_actual_macro_artifact_validation_v1',
  verified_at: new Date().toISOString(), evaluation_clock: nowText,
  artifact: 'site/feeds/event_calendar.json', artifact_sha256: hash(raw),
  source_commit_checked: values['source-commit'] ?? null,
  reader_sha256: hash(readFileSync(readerPath)), verifier_sha256: hash(readFileSync(new URL(import.meta.url))),
  status: parsed.context.status, event_count: parsed.context.events.length,
  source_observed_at: parsed.context.source_observed_at,
  decision_cutoff_utc: parsed.context.decision_cutoff_utc,
  initial_display_rows: selected.rows.map(row => row.episode_id),
  real_http_entitlement_exercised: false, production_deployed: false,
  scope: 'Actual committed Macro artifact parsed by exact native Terminal pure validator and display selector; upstream route and browser verified separately.',
};
const output = resolve(values.output);
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify(receipt, null, 2));
