import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';

const path = new URL('../templates/_bonds_duration.mjs.j2', import.meta.url);
assert.ok(existsSync(path), 'Actual Bonds controller must exist, not a detached prototype');
const source = readFileSync(path, 'utf8');
const api = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const positions = () => [
  {id: 'example-intermediate', positionValue: 10000, durationYears: 5},
  {id: 'example-long', positionValue: 10000, durationYears: 14.8},
];

class Node {
  constructor(extra = {}) {
    Object.assign(this, {value: '', textContent: '', hidden: false, disabled: true,
      dataset: {}, attributes: {}, listeners: new Map(), focused: false}, extra);
  }
  setAttribute(k, v) { this.attributes[k] = String(v); }
  removeAttribute(k) { delete this.attributes[k]; }
  addEventListener(k, fn) { const s = this.listeners.get(k) || new Set(); s.add(fn); this.listeners.set(k, s); }
  removeEventListener(k, fn) { this.listeners.get(k)?.delete(fn); }
  emit(k, props = {}) {
    const e = {target: this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...props};
    for (const fn of this.listeners.get(k) || []) fn(e);
    return e;
  }
  focus() { this.focused = true; }
  select() { this.selected = true; }
}

function fixture({supported = true} = {}) {
  const fields = Object.fromEntries(['input', 'slider', 'form', 'editor', 'edit', 'reset',
    'title-en', 'title-zh', 'state-en', 'state-zh', 'error', 'error-en', 'error-zh',
    'shock-en', 'shock-zh', 'edit-en', 'edit-zh'].map(k => [k, new Node()]));
  fields.input.value = '50'; fields.slider.value = '50'; fields.editor.hidden = true;
  const rows = positions().map((p) => {
    const row = new Node({dataset: {positionId: p.id, positionValue: String(p.positionValue), modifiedDuration: String(p.durationYears)}});
    row.valueNode = new Node({hidden: true}); row.emptyNode = new Node(); row.pctNode = new Node({hidden: true});
    row.querySelector = s => ({'[data-duration-value]': row.valueNode, '[data-duration-empty]': row.emptyNode, '[data-duration-percent]': row.pctNode}[s] || null);
    return row;
  });
  const trigger = new Node(); const notice = new Node(); const closeButtons = [new Node(), new Node()];
  const dialog = new Node({open: false, dataset: {durationOrigin: 'illustrative'}});
  dialog.querySelector = s => {
    const match = s.match(/^\[data-duration-(.+)\]$/);
    return match ? fields[match[1]] || null : null;
  };
  dialog.querySelectorAll = s => ({'[data-duration-row]': rows, '[data-duration-close]': closeButtons}[s] || []);
  dialog.close = () => { dialog.open = false; dialog.emit('close'); };
  if (supported) dialog.showModal = () => { dialog.open = true; };
  const doc = {
    querySelector: s => s === '#bonds-duration-dialog' ? dialog : s === '[data-duration-unavailable]' ? notice : null,
    querySelectorAll: s => s === '[data-duration-open]' ? [trigger] : [],
  };
  const dispose = api.mountDurationWorkflow(doc);
  return {fields, rows, dialog, trigger, notice, dispose, closeButtons, doc,
    change(value) { fields.input.value = value; fields.input.emit('input'); },
    open() { trigger.emit('click'); }};
}

function assertCleared(f) {
  for (const row of f.rows) {
    assert.equal(row.valueNode.textContent, '');
    assert.equal(row.valueNode.hidden, true);
    assert.equal(row.emptyNode.hidden, false);
    assert.equal(row.pctNode.textContent, '');
    assert.equal(row.pctNode.hidden, true);
  }
}

test('R11 model retains the 50 bp first-order examples without modifying input', () => {
  const input = positions(); const copy = structuredClone(input);
  const result = api.buildDurationPreview({shockInput: '50', positions: input});
  assert.equal(result.state, 'valid');
  assert.deepEqual(result.results.map(r => r.priceChangeAmount), [-250, -740]);
  assert.deepEqual(result.results.map(r => r.priceChangePct), [-2.5, -7.4]);
  assert.deepEqual(input, copy);
});

for (const value of ['', ' ', '350', '-301', '1e2', '0x10', '12junk', 'NaN', 'Infinity', null, true]) {
  test(`model rejects ${JSON.stringify(value)} with no partial results`, () => {
    const result = api.buildDurationPreview({shockInput: value, positions: positions()});
    assert.equal(result.state, 'invalid'); assert.deepEqual(result.results, []);
  });
}

test('currency uses unrounded sensitivity; zero never displays negative zero', () => {
  const result = api.calculateDurationScenario({positionValue: 1234567, durationYears: 14.8, yieldChangeBp: 0.0137});
  assert.equal(result.priceChangeAmount, -25.03);
  const zero = api.calculateDurationScenario({positionValue: 10000, durationYears: 5, yieldChangeBp: 0});
  assert.equal(Object.is(zero.priceChangeAmount, -0), false);
  assert.equal(Object.is(zero.priceChangePct, -0), false);
});

test('invalid second position, duplicate identity and overflow invalidate the whole preview', () => {
  for (const rows of [
    [positions()[0], {...positions()[1], durationYears: NaN}],
    [positions()[0], {...positions()[1], id: positions()[0].id}],
    [positions()[0], {...positions()[1], positionValue: Number.MAX_VALUE, durationYears: Number.MAX_VALUE}],
  ]) assert.deepEqual(api.buildDurationPreview({shockInput: '50', positions: rows}).results, []);
});

test('real controller opens the native review, with the corrected default results', () => {
  const f = fixture(); assert.equal(f.trigger.disabled, false); assert.equal(f.notice.hidden, true);
  f.open(); assert.equal(f.dialog.open, true); assert.equal(f.fields.editor.hidden, true);
  assert.deepEqual(f.rows.map(r => r.valueNode.textContent), ['−$250.00', '−$740.00']);
  assert.equal(f.dialog.dataset.durationState, 'valid');
});

test('350 bp clears both old estimates and exposes correction-first bilingual state', () => {
  const f = fixture(); f.open(); f.change('350'); assertCleared(f);
  assert.equal(f.dialog.dataset.durationState, 'invalid');
  assert.equal(f.fields.error.hidden, false);
  assert.match(f.fields['error-en'].textContent, /−300.*\+300/);
  assert.match(f.fields['error-zh'].textContent, /基点/);
  assert.equal(f.fields.input.attributes['aria-invalid'], 'true');
  assert.equal(f.fields.slider.disabled, true);
  assert.match(f.fields['title-en'].textContent, /unavailable/i);
  assert.match(f.fields['edit-en'].textContent, /Correct/);
});

for (const value of ['', '1e2', '0x10', 'NaN', '350']) {
  test(`DOM update clears stale figures for ${JSON.stringify(value)}`, () => {
    const f = fixture(); f.open(); f.change(value); assertCleared(f);
  });
}

test('correcting to negative and zero shocks restores only valid estimates', () => {
  const f = fixture(); f.open(); f.change('350'); f.change('-50');
  assert.deepEqual(f.rows.map(r => r.valueNode.textContent), ['+$250.00', '+$740.00']);
  assert.match(f.fields['title-en'].textContent, /−50/);
  assert.match(f.fields['title-zh'].textContent, /−50/);
  assert.equal(f.fields.input.attributes['aria-invalid'], 'false');
  f.change('0'); assert.deepEqual(f.rows.map(r => r.valueNode.textContent), ['$0.00', '$0.00']);
});

test('editing opens assumptions; invalid submit cannot dismiss the correction', () => {
  const f = fixture(); f.open(); f.fields.edit.emit('click');
  assert.equal(f.fields.editor.hidden, false); assert.equal(f.fields.input.focused, true);
  f.change('350'); const event = f.fields.form.emit('submit');
  assert.equal(event.defaultPrevented, true); assert.equal(f.fields.editor.hidden, false);
  f.change('25'); f.fields.form.emit('submit'); assert.equal(f.fields.editor.hidden, true);
});

test('slider and reset use the same validator rather than a second calculator', () => {
  const f = fixture(); f.open(); f.fields.slider.value = '-25'; f.fields.slider.emit('input');
  assert.equal(f.fields.input.value, '-25');
  assert.deepEqual(f.rows.map(r => r.valueNode.textContent), ['+$125.00', '+$370.00']);
  f.change('350'); f.fields.reset.emit('click');
  assert.equal(f.fields.input.value, '50');
  assert.deepEqual(f.rows.map(r => r.valueNode.textContent), ['−$250.00', '−$740.00']);
});

test('return/close preserve the draft and never restore an invalid result on reopening', () => {
  const f = fixture(); f.open(); f.change('350'); f.closeButtons[1].emit('click');
  assert.equal(f.dialog.open, false); assert.equal(f.trigger.focused, true);
  assert.equal(f.fields.input.value, '350'); f.open(); assertCleared(f);
  assert.equal(f.dialog.dataset.durationState, 'invalid');
});

test('a changed or missing example origin withholds results rather than inventing sourced holdings', () => {
  for (const origin of ['', 'sourced', 'stale', 'unknown']) {
    const f = fixture(); f.open(); f.dialog.dataset.durationOrigin = origin; f.change('50');
    assertCleared(f); assert.equal(f.dialog.dataset.durationState, 'unavailable');
    assert.match(f.fields['error-en'].textContent, /inputs.*unavailable/i);
    assert.equal(f.fields.input.attributes['aria-invalid'], 'false');
  }
});

test('invalid duration metadata cannot leave a valid first row beside a missing second row', () => {
  for (const value of ['', 'NaN', '1e2', '0x10', '14.8years', '-5', '0']) {
    const f = fixture(); f.open(); f.rows[1].dataset.modifiedDuration = value; f.change('50');
    assertCleared(f); assert.equal(f.dialog.dataset.durationState, 'unavailable');
  }
});

test('unsupported native dialog leaves the calculator unavailable, not a working-looking control', () => {
  const f = fixture({supported: false});
  assert.equal(f.trigger.disabled, true); assert.equal(f.notice.hidden, false);
  assertCleared(f);
});

test('missing second output slot fails closed before controls become available', () => {
  const f = fixture(); f.dispose();
  f.rows[1].querySelector = () => null;
  const doc = {querySelector: s => s === '#bonds-duration-dialog' ? f.dialog : f.notice,
    querySelectorAll: () => [f.trigger]};
  api.mountDurationWorkflow(doc);
  assert.equal(f.trigger.disabled, true); assert.equal(f.notice.hidden, false);
});

test('disposing closes the review, restores focus, clears figures and removes input handlers', () => {
  const f = fixture(); f.open(); f.dispose();
  assert.equal(f.dialog.open, false); assert.equal(f.trigger.focused, true);
  assert.equal(f.trigger.disabled, true); assertCleared(f);
  f.change('-50'); assertCleared(f);
});

test('served module cannot write a watch, holding, market state or persistent store', () => {
  for (const forbidden of [/\bfetch\s*\(/, /XMLHttpRequest/, /localStorage/, /sessionStorage/,
    /indexedDB/, /\.innerHTML\s*=/, /style\.textContent/, /setInterval\s*\(/]) assert.doesNotMatch(source, forbidden);
});


test('valid fractional text shock and the slider stay in the same units', () => {
  const f = fixture(); f.open(); f.change('0.0137');
  assert.equal(f.fields.slider.value, '0.0137');
  assert.match(f.fields['shock-en'].textContent, /0\.0137 bp/);
  assert.deepEqual(f.rows.map(r => r.valueNode.textContent), ['−$0.07', '−$0.20']);
});

test('inclusive entry bounds accept both directions without treating them as validated accuracy', () => {
  for (const value of ['-300', '+300', '.5', '1.', '-0']) {
    const result = api.buildDurationPreview({shockInput: value, positions: positions()});
    assert.equal(result.state, 'valid'); assert.equal(result.results.length, 2);
    assert.match(result.approximation, /Large shocks.*reduce accuracy/);
  }
});

test('repeated mount reuses the existing handler set and disposal identity', () => {
  const f = fixture(); const same = api.mountDurationWorkflow(f.doc);
  assert.equal(same, f.dispose); assert.equal(f.trigger.listeners.get('click').size, 1);
  assert.equal(f.fields.input.listeners.get('input').size, 1);
});

test('native dialog failure clears results and exposes unavailability at the entry point', () => {
  const f = fixture(); f.dialog.showModal = () => { throw new Error('dialog cannot be opened'); };
  f.open(); assertCleared(f); assert.equal(f.trigger.disabled, true);
  assert.equal(f.notice.hidden, false); assert.equal(f.dialog.dataset.durationState, 'unavailable');
});

test('the native close event restores focus without resetting the selected shock', () => {
  const f = fixture(); f.open(); f.change('-25'); f.dialog.close();
  assert.equal(f.trigger.focused, true); assert.equal(f.fields.input.value, '-25');
  f.open(); assert.deepEqual(f.rows.map(r => r.valueNode.textContent), ['+$125.00', '+$370.00']);
});
