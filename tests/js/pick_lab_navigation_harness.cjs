'use strict';
// Executes the actual rendered inline script; this is a DOM state model, not a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
let focused = null;
let reduced = false;
let scrolls = [];
const elements = input.nodes.map((raw, index) => ({
  index, tagName: raw.tag.toUpperCase(), attrs: {...raw.attrs}, raw,
  style: {display: /display\s*:\s*([^;]+)/.exec(raw.attrs.style || '')?.[1] || ''},
  hidden: Object.hasOwn(raw.attrs, 'hidden'), open: Object.hasOwn(raw.attrs, 'open'),
  listeners: {}, removed: false,
  getAttribute(name) { return Object.hasOwn(this.attrs, name) ? this.attrs[name] ?? '' : null; },
  setAttribute(name, value) { this.attrs[name] = String(value); },
  removeAttribute(name) { delete this.attrs[name]; },
  get id() { return this.getAttribute('id') || ''; },
  get tabIndex() { return Number(this.getAttribute('tabindex') ?? 0); },
  set tabIndex(value) { this.setAttribute('tabindex', value); },
  addEventListener(type, callback) { (this.listeners[type] ||= []).push(callback); },
  focus(options) { focused = this; this.focusOptions = options; },
  click() { this.dispatch('click'); },
  dispatch(type, additions = {}) {
    const event = {target: this, currentTarget: this, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, ...additions};
    for (const fn of this.listeners[type] || []) fn(event);
    return event;
  },
  contains(other) { for (let p = other; p; p = parent(p)) if (p === this) return true; return false; },
  querySelector(selector) { return queryAll(selector, this)[0] || null; },
  querySelectorAll(selector) { return queryAll(selector, this); },
  scrollIntoView(options) { scrolls.push({target: this.id, ...options}); },
}));
function parent(el) { return el.raw.parent === null ? null : elements[el.raw.parent]; }
for (const el of elements) el.classList = {
  contains(name) { return (el.attrs.class || '').split(/\s+/).includes(name); },
  add(name) { el.attrs.class = [...new Set((el.attrs.class || '').split(/\s+/).filter(Boolean).concat(name))].join(' '); },
  remove(name) { el.attrs.class = (el.attrs.class || '').split(/\s+/).filter(x => x !== name).join(' '); },
};
function simpleMatch(el, selector) {
  if (selector.startsWith('.')) return el.classList.contains(selector.slice(1));
  if (selector.startsWith('#')) return el.id === selector.slice(1);
  const attribute = /^\[([^=\]]+)(?:="([^"]*)")?\]$/.exec(selector);
  if (attribute) return attribute[2] === undefined ? el.getAttribute(attribute[1]) !== null : el.getAttribute(attribute[1]) === attribute[2];
  return el.tagName.toLowerCase() === selector;
}
function matches(el, selector) {
  const parts = selector.trim().split(/\s+/);
  if (!simpleMatch(el, parts.pop())) return false;
  let ancestor = parent(el);
  while (parts.length) {
    const part = parts.pop();
    while (ancestor && !simpleMatch(ancestor, part)) ancestor = parent(ancestor);
    if (!ancestor) return false;
    ancestor = parent(ancestor);
  }
  return true;
}
function queryAll(selector, scope) {
  return elements.filter(el => !el.removed && (!scope || (el !== scope && scope.contains(el))) && matches(el, selector));
}
const document = {
  querySelectorAll: selector => queryAll(selector),
  querySelector: selector => queryAll(selector)[0] || null,
  getElementById: id => elements.find(el => !el.removed && el.id === id) || null,
  get activeElement() { return focused; },
};
const window = {matchMedia: query => ({matches: query.includes('prefers-reduced-motion') && reduced})};
vm.runInNewContext(input.script, {document, window, console}, {timeout: 2000});
const tabs = queryAll('.pl-tabs .tabbtn');
const chips = queryAll('#ab-chips .book-chip');
const tab = name => tabs.find(el => el.getAttribute('data-tab') === name);
const chip = id => chips.find(el => el.getAttribute('data-ab') === id);
const drill = id => queryAll('.book-drill').find(el => el.getAttribute('data-ab') === id);
function selected(list, target) {
  assert.equal(list.filter(el => el.getAttribute('aria-selected') === 'true').length, 1);
  for (const el of list) {
    assert.equal(el.getAttribute('aria-selected'), el === target ? 'true' : 'false');
    assert.equal(el.tabIndex, el === target ? 0 : -1);
    const panel = document.getElementById(el.getAttribute('aria-controls'));
    assert.ok(panel);
    assert.equal(panel.hidden, el !== target);
    assert.equal(panel.style.display, el === target ? 'block' : 'none');
  }
}
function press(el, key, extras = {}) { return el.dispatch('keydown', {key, ...extras}); }
function performDrill(id) {
  const trigger = drill(id); assert.ok(trigger); trigger.focus(); trigger.click();
  const target = document.getElementById('ab-' + id) || document.getElementById('lh-' + id);
  assert.ok(target.contains(focused), 'focus must move into the revealed destination');
  assert.equal(focused.getAttribute('data-book-focus'), '');
  assert.equal(focused.focusOptions?.preventScroll, true);
  const disclosure = target.querySelector('.all-fires-details');
  if (disclosure) assert.equal(disclosure.open, true);
  return target;
}
switch (input.scenario) {
  case 'initial': selected(tabs, tab('scoreboard')); selected(chips, chips[0]); break;
  case 'arrow_wrap':
    tab('scoreboard').focus(); assert.equal(press(tab('scoreboard'), 'ArrowLeft').defaultPrevented, true);
    selected(tabs, tab('method')); assert.equal(focused, tab('method'));
    press(focused, 'ArrowRight'); selected(tabs, tab('scoreboard')); assert.equal(focused, tab('scoreboard')); break;
  case 'home_end':
    tab('allbooks').click(); press(tab('allbooks'), 'End'); selected(tabs, tab('method'));
    press(focused, 'Home'); selected(tabs, tab('scoreboard')); break;
  case 'arrow_cycle':
    tab('scoreboard').focus();
    for (const [key, delta] of [['ArrowRight', 1], ['ArrowLeft', -1]]) {
      for (let step = 1; step <= tabs.length; step++) {
        press(focused, key);
        const target = tabs[(step * delta + tabs.length) % tabs.length];
        selected(tabs, target); assert.equal(focused, target);
      }
    } break;
  case 'native_activation':
    // Native Enter/Space-to-click translation is a browser obligation, verified in Chromium.
    for (const target of tabs) { target.focus(); target.click(); selected(tabs, target); assert.equal(focused, target); }
    break;
  case 'panel_tabstop':
    for (const target of tabs) { target.click(); assert.equal(document.getElementById(target.getAttribute('aria-controls')).tabIndex, 0); }
    break;
  case 'nested_books':
    tab('allbooks').click(); chip(input.entry).focus(); press(focused, 'ArrowRight');
    selected(chips, chip(input.second)); assert.equal(focused, chip(input.second));
    press(focused, 'Home'); selected(chips, chip(input.entry)); break;
  case 'entry_drill': performDrill(input.entry); selected(tabs, tab('allbooks')); selected(chips, chip(input.entry)); break;
  case 'longhold_drill': performDrill(input.longhold); selected(tabs, tab('longhold')); break;
  case 'missing_destination': {
    const trigger = drill(input.entry); trigger.setAttribute('data-ab', 'missing-book'); trigger.focus(); trigger.click();
    selected(tabs, tab('scoreboard')); assert.equal(focused, trigger); assert.equal(scrolls.length, 0); break;
  }
  case 'missing_chip': {
    chip(input.entry).setAttribute('aria-controls', 'missing-panel');
    const trigger = drill(input.entry); trigger.focus(); trigger.click();
    selected(tabs, tab('scoreboard')); assert.equal(focused, trigger); assert.equal(scrolls.length, 0); break;
  }
  case 'removed_chip': {
    chip(input.entry).removed = true;
    const trigger = drill(input.entry); trigger.focus(); trigger.click();
    selected(tabs, tab('scoreboard')); assert.equal(focused, trigger); assert.equal(scrolls.length, 0); break;
  }
  case 'wrong_label': {
    document.getElementById(tab('method').getAttribute('aria-controls')).setAttribute('aria-labelledby', tab('scoreboard').id);
    tab('method').click(); selected(tabs, tab('scoreboard')); break;
  }
  case 'malformed_control': {
    tab('method').setAttribute('aria-controls', 'absent-panel'); tab('method').click();
    assert.equal(tab('scoreboard').getAttribute('aria-selected'), 'true');
    assert.equal(document.getElementById(tab('scoreboard').getAttribute('aria-controls')).hidden, false); break;
  }
  case 'motion_preference_changes':
    for (const pref of [false, true, false]) {
      reduced = pref; tab('scoreboard').click(); performDrill(input.entry);
      assert.equal(scrolls.at(-1).behavior, pref ? 'instant' : 'smooth');
    } break;
  case 'modified_keys':
    for (const modifier of ['ctrlKey', 'altKey', 'metaKey']) {
      assert.equal(press(tab('scoreboard'), 'ArrowRight', {[modifier]: true}).defaultPrevented, false);
      selected(tabs, tab('scoreboard'));
    } break;
  case 'empty_page':
    assert.equal(chips.length, 0); press(tab('scoreboard'), 'End'); selected(tabs, tab('method')); break;
  case 'singleton_book':
    assert.equal(chips.length, 1); tab('allbooks').click(); chips[0].focus();
    for (const key of ['ArrowRight', 'ArrowLeft', 'Home', 'End']) {
      press(focused, key); selected(chips, chips[0]); assert.equal(focused, chips[0]);
    } break;
  default: throw new Error('Unknown scenario');
}
process.stdout.write(JSON.stringify({scenario: input.scenario, passed: true}));
