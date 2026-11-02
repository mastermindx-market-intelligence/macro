"""Accessible task sections inside the existing candidate setup dialog (Paper LKU-0/8OM-0).

The candidate setup template already groups its ALREADY SUPPLIED content into
structure / evidence / research / sources bodies marked ``data-pvs-section``. These
regressions run the ACTUAL shipped Packet2 owner (sliced verbatim by the existing
harness module, with explicit mock section markers and the template's own nested
source disclosure on the fixture bodies) and hold the generated navigation to its
contract:

  * the tablist, tabs and panel state exist only while the native dialog holds the body;
    in the no-JS inline fallback every group stays visible and untouched;
  * one labelled tablist, connected tabs/panels with unique per-dialog ids,
    ``aria-selected``/``aria-controls``/``aria-labelledby`` and one roving tabindex stop;
  * click, Left/Right/Home/End on the tablist activate and focus the right tab; no other
    key and no arrow outside the tablist is captured;
  * a panel carrying the collapsed ``details.pvs-audit`` source disclosure (the Sources
    body) shows it immediately on that panel's first selection of a mount — mouse or
    keyboard, focus left on the tab, and again on a same-candidate Plan return — exactly
    once per mount, so an explicit close is respected; on release it goes home in exactly
    its published state (including a body published with it open);
  * identity and the independent source clock stay outside every panel and stay available;
  * a body without markers — Plan records, legacy and other callers — gains nothing, and
    the existing Previous/Next browsing, Plan hop/return and access invalidation keep
    working with no duplicated or leaked state; the Plan hop/return reopens the SAME
    candidate on the section the reader left from (recorded as a semantic name before
    dismiss), while every fresh open and every Previous/Next step — and any return whose
    recorded group is no longer a visible panel — still lands on Structure;
  * a valid same-candidate return also hands the reader back the exact initiating
    Plan-link focus and the prior dialog scrollTop, and only while that link is still
    this journey's own live, enabled, same-plan, in-body, visible button: a missing,
    hidden, replaced or retargeted link, a lost section or lost access degrade to the
    fresh-open behaviour (Close focused, the dialog at the top);
  * close/release removes the generated bar, ids, roles and hidden state so the exact
    original nodes return home intact.

Honest limits of this harness: it is a Node DOM double — real browser focus, top-layer
modality, :focus-visible and every visual/layout property remain parent gates (no
screenshot or visual acceptance is claimed here). The Terminal-handoff owner slice is
not exercised because ``openTerminal``/``closeTerminal`` live in the production theme.js
prefix that is omitted from this packet; those unchanged tests run where the full owner
ships. The Jinja tests below cover the rendered markup and the no-JS fallback.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_prophet_candidate_plan_return import _PRE, _run

ROOT = Path(__file__).resolve().parents[1]

# ── mock section markers on the fixture bodies ─────────────────────────────────
# The shipped template emits the same four groups over the same content; the fixture
# marks the harness candidate body explicitly so the owner code under test is the real one.
# The sources body carries its content the way the template publishes it: ONE collapsed
# native <details class="pvs-audit"> disclosure (sourced facts and the real Plan-relation
# control nested inside it, once). ``auditOpen`` lets a fixture publish it already open.
_SECTIONS_PRE = """
const sectioned = (c, names, auditOpen) => {
  if (c.groups) return c;                        // marking twice must not duplicate groups
  const order = names || ['structure', 'evidence', 'research', 'sources'];
  const identity = mk('header', 'pvs-opportunity-identity');
  identity.textContent = 'Snapshot identity';
  const clock = mk('p', 'pvs-note pvs-summary-clock');
  clock.textContent = 'Source as-of clock';
  c.body.children[0].before(identity);          // header stays outside every panel
  c.body.children[1].before(clock);             // the independent source clock stays outside too
  const chart = c.body.querySelector('[data-pvs-chart]');
  order.forEach(name => {
    const group = mk('div', 'pvs-group', {'data-pvs-section': name});
    const section = mk('section', 'pvs-section');
    const h3 = mk('h3'); h3.textContent = name;
    section.append(h3);
    if (name === 'structure' && chart) section.append(chart);
    if (name === 'sources') {
      const audit = mk('details', 'pvs-audit', auditOpen ? {open: ''} : null);
      const summary = mk('summary'); summary.textContent = 'Evidence & source details';
      audit.append(summary, section, c.link);   // nested once — no duplicate control or content
      c.audit = audit;
      group.append(audit);
    } else {
      group.append(section);
    }
    c.body.append(group);
  });
  c.groups = Array.from(c.body.querySelectorAll('[data-pvs-section]'));
  return c;
};
/* Platform double: a browser toggles a details through its summary and hides the closed
   content itself; the DOM double has no native details semantics, so the fixture supplies
   exactly that one behaviour for the pvs-audit disclosure and nothing else. */
document.addEventListener('click', (e) => {
  const s = e.target && e.target.closest ? e.target.closest('summary') : null;
  const d = s && s.parentNode;
  if (d && d.classList.contains('pvs-audit')) d[d.hasAttribute('open') ? 'removeAttribute' : 'setAttribute']('open', '');
});
"""
_HOOKS = """
const tabsBar = () => dialogEl() && dialogEl().querySelector('.pvs-section-tabs');
const tabs = () => Array.from(dialogEl() ? dialogEl().querySelectorAll('[role="tab"]') : []);
const panels = () => Array.from(dialogEl() ? dialogEl().querySelectorAll('[role="tabpanel"]') : []);
const visiblePanels = () => panels().filter(p => !p.hasAttribute('hidden') && p.getClientRects().length);
const tabKeys = ev => (tabsBar().listeners.keydown || []).forEach(fn => fn(Object.assign(
  {type: 'keydown', preventDefault() { this.prevented = true; }}, ev)));
const sectionOf = () => (visiblePanels()[0] || {getAttribute: () => null}).getAttribute('data-pvs-section');
"""
_PREP = _SECTIONS_PRE + _HOOKS + """
await flush();
const origin = sectioned(origins.board);
"""
_OPEN = """
fire(origin.trigger); await flush();
"""


def test_tabs_exist_only_after_the_native_dialog_opens_with_correct_aria():
    """No-JS the groups stay visible and unmarked-up; after the dialog opens there is one
    labelled bilingual tablist whose tabs and panels are correctly linked, Structure first."""
    _run(
        _PREP
        + """
assert.equal(tabsBar(), null, 'no generated navigation outside the open dialog');
assert.equal(origin.body.querySelectorAll('[data-pvs-section][hidden]').length, 0,
             'no-JS: every group is visible');
assert.equal(origin.body.querySelectorAll('[role]').length, 0, 'no-JS: no generated roles');
assert.equal(origin.body.querySelectorAll('[aria-selected],[aria-labelledby],[aria-controls]').length, 0);
assert.equal(origin.body.querySelectorAll('[data-pvs-section][id]').length, 0, 'no-JS: no temporary ids');
assert.equal(origin.body.querySelectorAll('[data-pvs-section]').length, 4, 'fixture control: four groups');

fire(origin.trigger); await flush();
assert.equal(dialogEl().open, true);
const bar = tabsBar();
assert.ok(bar, 'one tablist is built only after the native dialog opens');
assert.equal(bar.getAttribute('role'), 'tablist');
const label = bar.getAttribute('aria-label');
assert.ok(label.includes('Setup sections') && label.includes('形态分区'), label);
assert.equal(bar.closest('[data-pvs-section]'), null, 'the tablist is not inside any panel');
assert.equal(bar.parentNode, origins.board.body, 'the bar sits under the identity/clock, above the groups');

const t = tabs(), ps = panels();
assert.equal(t.length, 4);
assert.equal(ps.length, 4);
assert.deepEqual(ps.map(p => p.getAttribute('data-pvs-section')),
                 ['structure', 'evidence', 'research', 'sources'], 'published group order');
t.forEach((tab, i) => {
  assert.equal(tab.getAttribute('role'), 'tab');
  const panel = document.getElementById(tab.getAttribute('aria-controls'));
  assert.ok(panel, 'each tab controls an existing id');
  assert.equal(panel, ps[i], 'tab order matches panel order');
  assert.equal(panel.getAttribute('role'), 'tabpanel');
  assert.equal(panel.getAttribute('aria-labelledby'), tab.id, 'panels are labelled by their tab');
  assert.equal(tab.textContent.includes(['Structure & timing', 'Evidence', 'Context', 'Sources'][i]) &&
               tab.textContent.includes(['结构与时机', '证据', '背景', '来源'][i]), true,
              'EN/ZH copy ships together on every tab');
});
assert.equal(new Set(t.map(x => x.id)).size, 4, 'tab ids are unique per dialog');
assert.equal(new Set(ps.map(x => x.id)).size, 4, 'panel ids are unique per dialog');
assert.equal(t[0].getAttribute('aria-selected'), 'true', 'Structure is the default section');
assert.deepEqual(t.slice(1).map(x => x.getAttribute('aria-selected')), ['false', 'false', 'false']);
assert.deepEqual(t.map(x => x.getAttribute('tabindex')), ['0', '-1', '-1', '-1'], 'one roving stop');
assert.equal(visiblePanels().length, 1, 'exactly one panel is visible');
assert.equal(sectionOf(), 'structure');
assert.equal(panels()[0].contains(bar), false);
""",
    )


def test_click_and_keyboard_activation_with_roving_tabindex_and_no_global_capture():
    """Click, Left/Right/Home/End activate and focus the right tab, arrows clamp at the
    ends, and nothing outside the four keys on this one tablist is captured."""
    _run(
        _PREP + _OPEN
        + """
const t = tabs();
fire(t[2]); await flush();                       // click straight to Context
assert.equal(sectionOf(), 'research');
assert.equal(visiblePanels().length, 1);
assert.equal(t[2].getAttribute('aria-selected'), 'true');
assert.deepEqual(t.map(x => x.getAttribute('tabindex')), ['-1', '-1', '0', '-1']);
assert.equal(document.activeElement, t[2]);

tabKeys({key: 'ArrowRight', target: t[2]});      // → Sources
assert.equal(sectionOf(), 'sources');
assert.equal(document.activeElement, t[3]);
tabKeys({key: 'ArrowRight', target: t[3]});      // the end does not wrap
assert.equal(sectionOf(), 'sources');
assert.equal(document.activeElement, t[3]);
tabKeys({key: 'Home', target: t[3]});            // Home → Structure
assert.equal(sectionOf(), 'structure');
assert.equal(document.activeElement, t[0]);
tabKeys({key: 'End', target: t[0]});             // End → Sources
assert.equal(sectionOf(), 'sources');
assert.equal(document.activeElement, t[3]);
tabKeys({key: 'ArrowLeft', target: t[3]});       // ← Context
assert.equal(sectionOf(), 'research');
assert.equal(visiblePanels().length, 1);

const elsewhere = {key: 'ArrowRight', target: origins.board.body,
                   preventDefault() { this.prevented = true; }};
(dialogEl().listeners.keydown || []).forEach(fn => fn(Object.assign({type: 'keydown'}, elsewhere)));
assert.equal(elsewhere.prevented, undefined, 'arrows outside the tablist are never captured');
const other = {key: 'ArrowDown', target: t[1], preventDefault() { this.prevented = true; }};
tabKeys(other);
assert.equal(other.prevented, undefined, 'only Left/Right/Home/End are handled');
assert.equal(tabs().map(x => x.getAttribute('aria-selected')).join(','), 'false,false,true,false',
             'the tour leaves one selected tab');
assert.equal(visiblePanels().length, 1);
""",
    )


def test_first_sources_selection_shows_the_source_disclosure_without_moving_focus():
    """The reported defect: the Sources body is published as one collapsed native
    disclosure, so selecting Sources used to show only its summary. Now the first
    selection — mouse or keyboard — shows the panel's own details.pvs-audit open, with
    focus left on the tab; panels without a disclosure of their own are never touched."""
    _run(
        _PREP + _OPEN
        + """
const sourcePanel = panels()[3];
const audit = sourcePanel.querySelector('details.pvs-audit');
assert.ok(audit, 'fixture control: the faithful nested disclosure exists');
assert.equal(sourcePanel.querySelectorAll('details').length, 1, 'no duplicate disclosure');
assert.equal(sourcePanel.querySelectorAll('.pvs-plan-link').length, 1, 'no duplicate plan control');
assert.equal(audit.contains(origins.board.link), true, 'the Plan relation lives inside the disclosure');
assert.equal(audit.hasAttribute('open'), false, 'published collapsed, exactly like the template');
assert.equal(sectionOf(), 'structure', 'Structure first, the disclosure untouched');

fire(tabs()[3]); await flush();                    // mouse selection of Sources
assert.equal(sectionOf(), 'sources');
assert.equal(audit.hasAttribute('open'), true, 'Sources shows the source details immediately');
assert.equal(document.activeElement, tabs()[3], 'focus stays on the selected tab');
assert.equal(visiblePanels().length, 1);

tabKeys({key: 'Home', target: tabs()[3]});         // away to Structure, by keyboard
assert.equal(sectionOf(), 'structure');
assert.equal(document.activeElement, tabs()[0]);
assert.equal(audit.hasAttribute('open'), true, 'the open disclosure is not forced back');
tabKeys({key: 'End', target: tabs()[0]});          // keyboard selection of Sources
assert.equal(sectionOf(), 'sources');
assert.equal(audit.hasAttribute('open'), true, 'a keyboard selection shows the details too');
assert.equal(document.activeElement, tabs()[3], 'focus stays on the tab after the key');

for (const name of ['structure', 'evidence', 'research']) {
  const panel = panels().find(p => p.getAttribute('data-pvs-section') === name);
  assert.equal(panel.querySelector('details'), null, name + ' carries no disclosure of its own');
}
""",
    )


def test_an_explicit_close_is_respected_for_the_rest_of_this_mount():
    """Once the first selection has opened the disclosure, the reader's own close stays
    closed for every repeated Sources selection in this same mount; only a fresh mount
    offers it open again."""
    _run(
        _PREP + _OPEN
        + """
fire(tabs()[3]); await flush();                    // first Sources selection: opened for the reader
const audit = panels()[3].querySelector('details.pvs-audit');
assert.equal(audit.hasAttribute('open'), true);
fire(audit.querySelector('summary')); await flush();   // the reader closes it themselves
assert.equal(audit.hasAttribute('open'), false, 'the native toggle still works in the dialog');

tabKeys({key: 'Home', target: tabs()[3]});         // away to Structure
assert.equal(sectionOf(), 'structure');
tabKeys({key: 'End', target: tabs()[3]});          // back to Sources, same mount
assert.equal(sectionOf(), 'sources');
assert.equal(audit.hasAttribute('open'), false, 'the explicit close is respected');
fire(tabs()[0]); await flush();
fire(tabs()[3]); await flush();                    // repeated selections still respect it
assert.equal(audit.hasAttribute('open'), false);
fire(closeBtn()); await flush();

fire(origin.trigger); await flush();               // a fresh mount opens it again, once
assert.equal(sectionOf(), 'structure');
const fresh = panels()[3].querySelector('details.pvs-audit');
assert.equal(fresh, audit, 'the same body came home and went back in');
assert.equal(fresh.hasAttribute('open'), false, 'released collapsed, as published');
fire(tabs()[3]); await flush();
assert.equal(fresh.hasAttribute('open'), true, 'a fresh mount offers the source details again');
""",
    )


def test_absent_sections_are_omitted_and_unmarked_bodies_gain_nothing():
    """A body with no research group ships three tabs; a body without markers — the legacy
    and Plan-record shape — must not gain generated navigation at all."""
    _run(
        _SECTIONS_PRE + _HOOKS + """
await flush();
const origin = sectioned(origins.board, ['structure', 'evidence', 'sources']);
const unmarked = candidate('board', 'UNMARKED', 'OTHER-BULL-20260811');
candGrid.append(unmarked.row);
await flush();
fire(origin.trigger); await flush();
assert.equal(dialogEl().open, true);
const t = tabs();
assert.equal(t.length, 3, 'an absent section is omitted, never stubbed');
assert.equal(panels().length, 3);
assert.equal(t.some(x => x.textContent.includes('Context') || x.textContent.includes('背景')), false);
assert.equal(visiblePanels().length, 1);
tabKeys({key: 'End', target: t[0]});
assert.equal(sectionOf(), 'sources', 'the remaining sections still work');
fire(closeBtn()); await flush();
assert.equal(dialogEl().open, false);

fire(unmarked.trigger); await flush();
assert.equal(dialogEl().open, true);
assert.equal(tabsBar(), null, 'a body without markers gains no tablist');
assert.equal(tabs().length, 0);
const held = dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body');
assert.equal(held.querySelectorAll('[data-pvs-section]').length, 0);
assert.equal(held.querySelectorAll('[hidden],[role="tabpanel"]').length, 0,
             'an unmarked body stays whole and visible');
fire(closeBtn()); await flush();

fire(srcBtn('plan'));
panel.setAttribute('data-lifef', 'entered');
fire(plans.LFUS.trigger); await flush();
assert.equal(dialogEl().open, true);
assert.equal(tabsBar(), null, 'Plan record detail keeps its own body without tabs');
assert.equal(dialogEl().querySelector('.pvs-dialog-content').textContent.includes('model record LFUS-BULL-20260810'),
             true, 'the Plan body is untouched');
""",
        pre=_PRE["grid"] + """
const second = candidate('board', 'SECOND', 'OTHER-BULL-20260811');
candGrid.append(second.row);
""",
    )


def test_identity_and_source_clock_stay_outside_every_panel():
    """The header identity and the independent source clock never enter a panel and stay
    available whichever section the reader selects."""
    _run(
        _PREP + _OPEN
        + """
const identity = origin.body.querySelector('.pvs-opportunity-identity');
const clock = origins.board.body.querySelector('.pvs-summary-clock');
assert.ok(identity && clock, 'fixture control: both nodes exist');
assert.equal(identity.closest('[data-pvs-section]'), null);
assert.equal(clock.closest('[data-pvs-section]'), null);
for (const tab of tabs()) {
  fire(tab); await flush();
  assert.equal(visiblePanels().length, 1);
  assert.equal(identity.closest('[data-pvs-section]'), null, tab.textContent + ': identity outside');
  assert.equal(clock.closest('[data-pvs-section]'), null, tab.textContent + ': clock outside');
  assert.equal(identity.getClientRects().length, 1, tab.textContent + ': identity still available');
  assert.equal(clock.getClientRects().length, 1, tab.textContent + ': clock still available');
  assert.ok(clock.textContent.includes('Source as-of'));
}
""",
    )


def test_evidence_label_counts_supplied_cautions_and_retired_tabs_cannot_hide_source():
    _run(_PREP + """
const evidence = origin.groups.find(p => p.getAttribute('data-pvs-section') === 'evidence');
const risks = mk('section', 'pvs-opportunity-cautions');
const list = mk('ul');
for (const label of ['First supplied caution', 'Second supplied caution']) {
  const item = mk('li'); item.textContent = label; list.append(item);
}
risks.append(list); evidence.append(risks);
fire(origin.trigger); await flush();
const evidenceTab = tabs()[1];
assert.ok(evidenceTab.textContent.includes('Evidence · 2 cautions'));
assert.ok(evidenceTab.textContent.includes('证据 · 2 项注意'));
const retired = tabs().slice();
fire(closeBtn()); await flush();
for (const tab of retired) fire(tab);
assert.equal(origin.body.querySelectorAll('[data-pvs-section][hidden]').length, 0,
             'retired controls cannot mutate the restored inline detail');
fire(origin.trigger); await flush();
for (const tab of retired) fire(tab);
assert.equal(sectionOf(), 'structure', 'retired controls cannot change a new mount');
fire(tabs()[1]); await flush();
assert.equal(sectionOf(), 'evidence', 'the current control still works');
""")


def test_close_reopen_navigation_and_escape_leave_no_generated_state_behind():
    """Close/Escape/reopen and Previous/Next remove or rebuild the generated layer cleanly:
    the bar, ids, roles and hidden state are gone, every group is visible again for the
    inline fallback, each candidate defaults to Structure, and nothing duplicates."""
    _run(
        _SECTIONS_PRE + _HOOKS + """
await flush();
const origin = sectioned(origins.board);
const second = sectioned(candidate('board', 'SECOND', 'OTHER-BULL-20260811'));
candGrid.append(second.row);
await flush();
const groups = origin.groups;
fire(origin.trigger); await flush();
const oldIds = panels().map(p => p.id);
fire(tabs()[3]); await flush();                  // leave a non-default section open
assert.equal(sectionOf(), 'sources');

fire(closeBtn()); await flush();
assert.equal(dialogEl().open, false);
assert.equal(origin.body.querySelector('.pvs-section-tabs'), null, 'the bar is removed');
assert.equal(origin.body.querySelectorAll('[data-pvs-section][hidden]').length, 0,
             'no hidden state leaks into the inline fallback');
assert.equal(origin.body.querySelectorAll('[data-pvs-section][role]').length, 0);
assert.equal(origin.body.querySelectorAll('[data-pvs-section][aria-labelledby]').length, 0);
assert.equal(origin.body.querySelectorAll('[data-pvs-section][id]').length, 0, 'temporary ids are gone');
assert.equal(oldIds.every(id => !document.getElementById(id)), true, 'old ids resolve to nothing');
assert.deepEqual(origin.groups, groups, 'the exact original group nodes returned home');
assert.equal(origin.body.contains(origin.link), true, 'the Plan-relation control is still in the body');

fire(origin.trigger); await flush();             // reopen: fresh layer, Structure first
assert.equal(dialogEl().open, true);
assert.equal(dialogEl().querySelectorAll('.pvs-section-tabs').length, 1, 'no duplicated bar');
assert.equal(sectionOf(), 'structure');
assert.equal(panels().every(p => oldIds.indexOf(p.id) < 0), true, 'ids are minted fresh per dialog');

fire(document.querySelector('[data-pvs-browse="next"]')); await flush();
assert.equal(dialogEl().querySelector('#pvs-dialog-title').textContent, 'SECOND');
assert.equal(dialogEl().querySelectorAll('.pvs-section-tabs').length, 1,
             'stepping candidates never duplicates the controls');
assert.equal(sectionOf(), 'structure', 'the next candidate opens on its own Structure');
fire(document.querySelector('[data-pvs-browse="previous"]')); await flush();
assert.equal(sectionOf(), 'structure', 'revisiting a candidate resets to Structure');
assert.equal(second.body.querySelectorAll('[data-pvs-section][hidden]').length, 0,
             'the body that left keeps no hidden state');

(dialogEl().listeners.cancel || []).forEach(fn => fn({type: 'cancel', preventDefault() {}}));
await flush();
assert.equal(dialogEl().open, false, 'Escape still dismisses through the native owner');
assert.equal(second.body.querySelector('.pvs-section-tabs'), null);
assert.equal(second.body.querySelectorAll('[data-pvs-section][hidden]').length, 0);
""",
        pre=_PRE["grid"],
    )


def test_release_returns_the_disclosure_to_its_published_state():
    """Whatever happened inside the dialog — the automatic first-reveal open, or the
    reader's own toggling — the disclosure returns home exactly as the source published
    it: a collapsed body goes home collapsed, and a body published with the disclosure
    open goes home open even if the reader closed it while the dialog held the body."""
    _run(
        _SECTIONS_PRE + _HOOKS + """
await flush();
const origin = sectioned(origins.board);                       // published collapsed
const second = sectioned(candidate('board', 'OSHIP', 'OTHER-BULL-20260811'), null, true);
candGrid.append(second.row); await flush();

fire(origin.trigger); await flush();
fire(tabs()[3]); await flush();
const audit = origin.body.querySelector('details.pvs-audit');
assert.equal(audit.hasAttribute('open'), true, 'first selection opened it');
fire(audit.querySelector('summary')); await flush();           // reader closes it …
fire(audit.querySelector('summary')); await flush();           // … and opens it again
assert.equal(audit.hasAttribute('open'), true, 'the reader can browse the disclosure');
fire(closeBtn()); await flush();
assert.equal(audit.hasAttribute('open'), false,
             'a reader-opened disclosure still goes home collapsed, as published');

fire(second.trigger); await flush();                           // published open
const audit2 = second.body.querySelector('details.pvs-audit');
assert.equal(sectionOf(), 'structure');
assert.equal(audit2.hasAttribute('open'), true, 'fixture control: published open');
fire(tabs()[3]); await flush();
assert.equal(audit2.hasAttribute('open'), true, 'already open: the first selection leaves it open');
fire(audit2.querySelector('summary')); await flush();          // the reader closes it in the dialog
assert.equal(audit2.hasAttribute('open'), false);
fire(closeBtn()); await flush();
assert.equal(audit2.hasAttribute('open'), true, 'an initially open disclosure goes home open');
""",
        pre=_PRE["grid"],
    )


def test_plan_relation_stays_operable_from_sources_and_return_restores_section():
    """From the Sources panel the exact Plan hop still works through the shipped owner, and
    returning to the SAME candidate reopens that body with Sources selected again — with
    its source disclosure shown immediately, exactly as the first selection did: one
    connected tablist, the tab/panel aria intact, nothing leaked. The restore is bound to
    this one return only — a fresh open of the same row and a Previous/Next step still
    default to Structure. The same return also restores the exact initiating Plan-link
    focus and the dialog scrollTop the reader left from (177 here); fresh opens and
    Previous/Next keep the normal Close/browse focus and start at the top."""
    _run(
        _PREP + """
const second = sectioned(candidate('board', 'SECOND', 'OTHER-BULL-20260811'));
candGrid.append(second.row); await flush();
""" + _OPEN
        + """
const sourcePanel = panels().find(p => p.getAttribute('data-pvs-section') === 'sources');
fire(tabs()[3]); await flush();
assert.equal(visiblePanels()[0], sourcePanel, 'the Plan relation lives in the Sources panel');
assert.equal(sourcePanel.contains(origins.board.link), true);
assert.equal(sourcePanel.querySelector('details.pvs-audit').hasAttribute('open'), true,
             'the hop starts from a Sources panel whose details are already shown');
origins.board.link.focus();                      // the reader is on the exact Plan-link control
dialogEl().scrollTop = 177;                      // ... at their own dialog reading position
fire(origins.board.link);                        // View in Plans, from inside the panel
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(window.USProphetSource.get(), 'plans');
assert.equal(window.PVSetupReturn.available(), true);
assert.equal(returnBtns().length, 1);
assert.equal(origins.board.body.querySelector('.pvs-section-tabs'), null,
             'the released candidate body carries no generated layer');
assert.equal(origins.board.body.querySelectorAll('[data-pvs-section][hidden]').length, 0);

assert.equal(window.PVSetupReturn.run(), true);
await flush();
assert.equal(window.USProphetSource.get(), 'candidates');
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             origins.board.body, 'the same body reopened');
assert.equal(document.querySelectorAll('.pvs-section-tabs').length, 1, 'exactly one tablist');
assert.equal(sectionOf(), 'sources', 'the return restores the section the reader left from');
const t = tabs(), ps = panels();
assert.equal(t.length, 4, 'the rebuilt layer is whole');
assert.equal(t[3].getAttribute('aria-selected'), 'true', 'Sources is the selected tab');
assert.deepEqual(t.slice(0, 3).map(x => x.getAttribute('aria-selected')), ['false', 'false', 'false']);
assert.deepEqual(t.map(x => x.getAttribute('tabindex')), ['-1', '-1', '-1', '0'], 'one roving stop, on Sources');
assert.equal(visiblePanels().length, 1);
assert.equal(ps[3].querySelector('details.pvs-audit').hasAttribute('open'), true,
             'the restored Sources panel shows its source details again');
assert.equal(document.activeElement, origins.board.link,
             'the exact initiating Plan-link control is focused again');
assert.equal(dialogEl().scrollTop, 177, 'the prior dialog scrollTop is restored');
const controls = document.getElementById(t[3].getAttribute('aria-controls'));
assert.equal(controls, ps[3], 'the selected tab is connected to its own panel');
assert.equal(controls.getAttribute('data-pvs-section'), 'sources');
assert.equal(controls.getAttribute('aria-labelledby'), t[3].id, 'the panel is labelled by its tab');
assert.equal(new Set(t.map(x => x.id)).size, 4, 'tab ids stay unique in the rebuilt layer');
assert.equal(returnBtns().length, 0, 'the journey is spent');
fire(closeBtn()); await flush();
assert.equal(document.activeElement, origins.board.trigger);

fire(origins.board.trigger); await flush();      // an explicit fresh open of the same row
assert.equal(sectionOf(), 'structure', 'a fresh open still defaults to Structure');
assert.equal(document.activeElement, closeBtn(), 'a fresh open keeps the normal focus');
assert.equal(dialogEl().scrollTop, 0, 'a fresh open still starts at the top');
fire(document.querySelector('[data-pvs-browse="next"]')); await flush();   // while the dialog is open
assert.equal(dialogEl().querySelector('#pvs-dialog-title').textContent, 'SECOND');
assert.equal(sectionOf(), 'structure', 'the next candidate still opens on Structure');
assert.equal(dialogEl().scrollTop, 0, 'stepping candidates still starts at the top');
fire(document.querySelector('[data-pvs-browse="previous"]')); await flush();
assert.equal(dialogEl().querySelector('#pvs-dialog-title').textContent, 'BOAR');
assert.equal(sectionOf(), 'structure', 'stepping back carries no restore either');
assert.equal(dialogEl().scrollTop, 0, 'stepping back still starts at the top');
fire(closeBtn()); await flush();
""",
    )


def test_return_falls_back_to_structure_when_the_section_is_gone():
    """The recorded name is a hint, never an authority: if the recorded group is no longer
    a visible panel of this same body when the reader comes back, the detail opens on
    Structure instead of a dangling or failed selection — and with it the position
    restore degrades too: Close focus, the dialog at the top."""
    _run(
        _PREP + _OPEN
        + """
fire(tabs()[3]); await flush();                  // leave from Sources, as the panel invites
origins.board.link.focus();
dialogEl().scrollTop = 177;
fire(origins.board.link); await flush();
assert.equal(window.PVSetupReturn.available(), true);
origins.board.groups.find(p => p.getAttribute('data-pvs-section') === 'sources').remove();
await flush();                                   // the same row/generation lost that group
assert.equal(window.PVSetupReturn.available(), true, 'row custody is unchanged: the journey stands');

assert.equal(window.PVSetupReturn.run(), true);
await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             origins.board.body, 'the same body reopened');
assert.equal(document.querySelectorAll('.pvs-section-tabs').length, 1, 'exactly one tablist');
const t = tabs();
assert.equal(t.length, 3, 'the remaining groups ship three tabs, never a stub');
assert.equal(sectionOf(), 'structure', 'a missing section falls back to Structure');
assert.equal(t[0].getAttribute('aria-selected'), 'true');
assert.equal(visiblePanels().length, 1);
assert.equal(t.every(x => document.getElementById(x.getAttribute('aria-controls'))), true,
             'every surviving tab is still connected');
assert.equal(document.activeElement, closeBtn(),
             'a return whose section is gone keeps the fresh-open focus');
assert.equal(dialogEl().scrollTop, 0, 'a return whose section is gone opens at the top');
""",
    )


def test_return_position_degrades_when_the_link_is_hidden_retargeted_or_replaced():
    """The focus/scroll restore is bound to the exact same-plan, visible, in-body link the
    reader left from. Hidden or retargeted while in Plans, the return still reopens the
    SAME candidate on its restored section, but keeps the fresh-open behaviour: Close
    focused, the dialog at the top — never a stale, moved-out or moved-into control."""
    _run(
        _PREP + """
const second = sectioned(candidate('board', 'SECOND', 'OTHER-BULL-20260811'));
candGrid.append(second.row); await flush();
""" + _OPEN
        + """
fire(tabs()[3]); await flush();
origins.board.link.focus();
dialogEl().scrollTop = 177;
fire(origins.board.link); await flush();
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(window.PVSetupReturn.available(), true);

origins.board.link.setAttribute('hidden', '');   // hidden while in Plans
assert.equal(window.PVSetupReturn.available(), true, 'the link is not row custody');
assert.equal(window.PVSetupReturn.run(), true);
await flush();
assert.equal(sectionOf(), 'sources', 'the section restore keeps its own contract');
assert.equal(document.activeElement, closeBtn(), 'a hidden link is never focused');
assert.equal(dialogEl().scrollTop, 0, 'a hidden link leaves the dialog at the top');
origins.board.link.removeAttribute('hidden');
fire(closeBtn()); await flush();
assert.equal(document.activeElement, origins.board.trigger);

fire(origins.board.trigger); await flush();      // again, from a live, visible, same-plan link
fire(tabs()[3]); await flush();
origins.board.link.focus();
dialogEl().scrollTop = 88;
fire(origins.board.link); await flush();
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(window.PVSetupReturn.available(), true);
origins.board.link.setAttribute('data-pvs-plan-target', 'pv-OTHER-PLAN');   // retargeted
assert.equal(window.PVSetupReturn.run(), true);
await flush();
assert.equal(sectionOf(), 'sources');
assert.equal(document.activeElement, closeBtn(), 'a retargeted link is never focused');
assert.equal(dialogEl().scrollTop, 0, 'a retargeted link leaves the dialog at the top');
fire(closeBtn()); await flush();
""",
    )


def test_access_loss_while_in_plans_ends_the_journey_and_restores_nothing():
    """A tier/access turn while the reader is in Plans ends the journey outright: the run
    reports failure, no dialog is reopened and no focus or scroll is restored anywhere."""
    _run(
        _PREP + _OPEN
        + """
fire(tabs()[3]); await flush();
origins.board.link.focus();
dialogEl().scrollTop = 177;
fire(origins.board.link); await flush();
assert.equal(window.PVSetupReturn.available(), true);
origins.board.row.classList.add('mx-tier-hidden');
await flush();
assert.equal(window.PVSetupReturn.available(), false, 'access loss clears the journey');
assert.equal(window.PVSetupReturn.run(), false);
await flush();
assert.equal(dialogEl().open, false, 'no dialog is reopened');
assert.equal(sectionOf(), null, 'no panel is shown');
assert.equal(document.querySelectorAll('.pvs-section-tabs').length, 0, 'no generated layer at all');
""",
    )


def test_access_invalidation_with_a_tab_open_dismisses_and_cleans_up():
    """The existing access/source invalidation stays authoritative while a non-default tab
    is selected: the dialog dismisses, and the withheld body returns whole so the withheld
    row can never be reopened into a stale tab state."""
    _run(
        _PREP + _OPEN
        + """
fire(tabs()[1]); await flush();
assert.equal(sectionOf(), 'evidence');
origins.board.row.classList.add('mx-tier-hidden');
await flush();
assert.equal(dialogEl().open, false, 'the existing owner still dismisses on access loss');
assert.equal(origins.board.body.querySelector('.pvs-section-tabs'), null);
assert.equal(origins.board.body.querySelectorAll('[data-pvs-section][hidden]').length, 0,
             'the body is whole for whoever may legitimately see it again');
fire(origins.board.trigger); await flush();
assert.equal(dialogEl().open, false, 'a withheld row cannot reopen into stale tabs');
""",
    )


# ── rendered-markup and no-JS fallback (Jinja) ─────────────────────────────────
jinja2 = pytest.importorskip("jinja2")


def _module():
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    return env.get_template("_prophet_setup_detail.html.j2").module


def _row(**over):
    row = {
        "ticker": "LFUS", "name": "Lfus Inc", "name_zh": "Lfus 公司",
        "sector": "Financials", "sector_zh": "金融", "industry": "Banks", "industry_zh": "银行",
        "price": 33.5, "price_as_of": "2026-10-14T20:00:00-04:00", "signal_asof": "2026-10-13",
        "stage": "basing", "lane": "bottoming", "headline_reason": "Base depth and RS",
        "entry_signal": {"status": "buy_soon", "headline": "Near entry", "headline_zh": "接近入场",
                          "buy_zone": {"low": 32.0, "high": 34.0}, "stop": 30.5, "chase_above": 36.0},
        "signal": {"reason": "Base depth and RS", "above200": True, "weekly_bull": False,
                    "provisional": False, "tier_observed_date": "2026-10-12"},
        "hold": {"invalidation": 29.75},
    }
    row.update(over)
    return row


def _display(links=True):
    d = {
        "cautions": [{"en": "Do not chase the breakout", "zh": "请勿追高"}],
        "assessment_detail": {"en": "Assessment detail copy", "zh": "评估说明文案"},
        "evidence_profile": {
            "scores": [{"key": "trend", "label": {"en": "Trend", "zh": "趋势"}, "value": 61.0}],
            "abstaining": [{"en": "Quality", "zh": "质量"}]},
        "chart": {"asof": "2026-10-14"},
    }
    if links:
        d["context"] = {"href": "https://example.test/context", "label": {"en": "Context", "zh": "背景"}}
        d["memory_href"] = "https://example.test/mm"
    return d


def _body_html(kind="board", display="full", plan_rel=None, row=None, as_of="2026-10-09"):
    row = row if row is not None else _row()
    if display == "full":
        display = _display(links=True)
    elif display == "bare":
        display = _display(links=False)
    elif display == "none":
        display = {}                                    # the legacy no-rich-display caller
    return _module().body(row, kind, as_of, plan_rel or {"state": "none", "plans": []}, display=display)


def test_rendered_groups_are_in_order_and_every_supplied_field_survives():
    html = _body_html()
    assert re.findall(r'data-pvs-section="(\w+)"', html) == ["structure", "evidence", "research", "sources"]
    # identity and the independent source clock stay above/outside every group
    assert 0 < html.index("pvs-opportunity-identity") < html.index('data-pvs-section=')
    assert html.index("pvs-summary-clock") < html.index('data-pvs-section=')
    # no-JS: nothing pre-hidden, no generated widget state ships in the markup
    assert "hidden" not in html
    assert 'role="' not in html
    assert "aria-selected" not in html and "tabindex" not in html
    # structure: entry conditions, clocks, chart slot, every level field and the caution copy
    for needle in ["Entry conditions", "入场条件", "Near entry", "接近入场", "data-assessment-asof",
                   "Entry read date not supplied", "data-signal-asof", "Signal session",
                   "not the date of the entry assessment", "data-pvs-chart", "Price levels",
                   "entry_signal.buy_zone.low", "entry_signal.buy_zone.high", "entry_signal.stop",
                   "hold.invalidation", "entry_signal.chase_above", "Chase boundary", "追高边界",
                   "$33.50", "not a target"]:
        assert needle in html, needle
    # evidence: cautions, why, family scores, abstentions, technical context, unavailable terms
    for needle in ["Risks to review", "Do not chase the breakout", "请勿追高", "Why it is here",
                   "Evidence profile", "not probabilities or entry permission",
                   "data-evidence-family=\"trend\"", "61.0", "Not scored", "质量",
                   "Technical context", "暂定观察", "Target and holding period unavailable"]:
        assert needle in html, needle
    # research: the existing context and Market Memory links only
    for needle in ['class="pvs-context-link" href="https://example.test/context"',
                   'class="pvs-memory-link l-en" href="https://example.test/mm&amp;mm_lang=en"',
                   "Market Memory", "separate research, not evidence matched"]:
        assert needle in html, needle
    # sources: the full disclosure, exact plan relation copy and dates, native link target
    for needle in ["Evidence &amp; source details", "Setup information", "策略分组",
                   "Selection is not entry permission", "data-plan-relation=\"none\"",
                   "Exact plan relation: not available from the source", "Source dates",
                   "envelope.as_of", "signal.tier_observed_date", "Missing clocks remain missing"]:
        assert needle in html, needle


def test_entry_read_falls_back_to_explicit_unsupplied_copy_only_when_absent():
    html = _body_html(row=_row(entry_signal=None))
    assert "Entry read not supplied" in html and "未提供入场读数" in html
    assert "Near entry" not in html


def test_legacy_display_keeps_the_original_source_path_and_all_groups():
    html = _body_html(display="none")
    assert re.findall(r'data-pvs-section="(\w+)"', html) == ["structure", "evidence", "sources"]
    assert "Original source" in html and "来源原文" in html and "Base depth and RS" in html
    assert "hidden" not in html and 'role="' not in html


def test_research_group_is_omitted_when_no_links_and_kept_when_present():
    bare = _body_html(display="bare")
    assert re.findall(r'data-pvs-section="(\w+)"', bare) == ["structure", "evidence", "sources"]
    assert "Market Memory" not in bare and "pvs-context-link" not in bare
    full = _body_html()
    assert 'data-pvs-section="research"' in full


def test_research_candidate_kind_groups_without_board_only_content():
    html = _body_html(kind="research", display="none")
    assert re.findall(r'data-pvs-section="(\w+)"', html) == ["structure", "evidence", "sources"]
    assert "Research only" in html and "仅供研究" in html
    assert "Entry read not supplied" not in html and "Price levels" not in html
    assert "Technical context" not in html
    assert "headline_reason" not in html and "Base depth and RS" in html
    assert "Risks to review" not in html and "Evidence profile" not in html


def test_plan_relation_and_table_serialisation_keep_their_published_shape():
    rel = {"state": "related_security",
           "plans": [{"id": "BOAR-BULL-20260810", "lifecycle_state": "entered",
                      "formation_date": "2026-08-10", "signal_date": "2026-08-11",
                      "plan_asof": "2026-10-09"}]}
    html = _body_html(plan_rel=rel)
    assert 'data-plan-relation="related_security"' in html
    assert 'data-pvs-plan-target="pv-BOAR-BULL-20260810"' in html
    assert "View in Plans" in html and "在计划中查看" in html
    assert "not this candidate&#39;s plan" in html      # the escape the source ships with
    # the serialised table action still embeds the same grouped body as inert content
    tpl = _module()
    action = tpl.table_action(_row(), "2026-10-09", rel, display=_display())
    assert '<template class="pvs-body-source">' in action
    assert 'data-pvs-section="structure"' in action and 'data-pvs-section="sources"' in action
    assert 'class="pvs-fallback-note"' in action
    legacy = tpl.action("legacy body without markers")
    assert "legacy body without markers" in legacy and 'data-pvs-section' not in legacy
