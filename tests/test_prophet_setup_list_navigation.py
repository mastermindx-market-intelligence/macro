"""Previous/Next setup browsing inside the one native setup dialog (Paper LKU-0).

The reader who opens a candidate detail from a list — the Today shelf card, the board
card, the dense table row or the Screener pool row — can step to the exact previous or
next currently visible row of THAT list without closing the dialog. These regressions
run the ACTUAL shipped Packet2 owner (sliced verbatim by the existing harness module)
and hold the browsing context to its contract:

  * exact live source nodes only, in existing DOM order, of the one originating list;
  * hidden/withheld/blurred/folded rows and rows without a serviceable native
    detail/identity are never admitted; Plan records never browse;
  * a changed list population, order, access or published generation hides the
    controls instead of admitting new rows or keeping a stale index;
  * same-source quote text ticks do not invalidate;
  * forward/back reuses the existing open/release owners, so each visited body lands
    back in its own details element, the original scroll survives every step and Close
    returns focus to the currently viewed trigger;
  * the ends do not wrap; the native focus trap works with disabled endpoint controls;
  * the existing candidate→Plan→candidate return, Terminal handoff, comparison picks
    and the stock table's own state are untouched.

Honest limits of this harness: it is a Node DOM double. Real browser focus-trap
semantics, :focus-visible, top-layer modality and visual layout still need
separate native browser proof; there is no network layer to observe, so "no new
fetch" is asserted as "no board re-render and no view persistence write".
"""

from __future__ import annotations

import pytest

from tests.test_prophet_candidate_plan_return import _PRE, _run

# Each of the four originating lists: the origins fixture name, the build prelude, the
# candidate factory kind, the two appended rows, and the list element expression.
_LISTS = {
    "grid": ("board", _PRE["grid"], "board", "candGrid.append(second.row, third.row);",
             "candGrid"),
    "today": ("today", _PRE["today"], "today",
              "document.getElementById('us-today-grid').append(second.row, third.row);",
              "document.getElementById('us-today-grid')"),
    "table": ("table", _PRE["table"], "table",
              "document.querySelector('#us-stocktable-wrap tbody').append(second.row, third.row);",
              "document.querySelector('#us-stocktable-wrap tbody')"),
    "pool": ("pool", _PRE["grid"], "pool",
             "document.querySelector('#us-candidate-pool .ucp-list').append(second.row, third.row);",
             "document.querySelector('#us-candidate-pool .ucp-list')"),
}


def _three(kind: str, extra: str = "") -> str:
    """Prelude with three serviceable rows in the originating list."""
    _, pre, factory, append, _list = _LISTS[kind]
    return (pre +
            "\nconst second = candidate('%s', 'SECOND', 'OTHER-BULL-20260811');\n"
            "const third = candidate('%s', 'THIRD', 'OTHER-BULL-20260811');\n%s\n%s"
            % (factory, factory, append, extra))


_HOOKS = """
const prev = document.querySelector('[data-pvs-browse="previous"]');
const next = document.querySelector('[data-pvs-browse="next"]');
const bar = dialogEl().querySelector('.pvs-browse-bar');
const pos = dialogEl().querySelector('.pvs-browse-position');
"""


_AT_HOME = """
const atHome = ref => {                            // table bodies live in their own template
  const tpl = ref.details.querySelector(':scope > template.pvs-body-source');
  return tpl ? tpl.content.contains(ref.body) : ref.details.contains(ref.body);
};
"""


@pytest.mark.parametrize("kind", ["grid", "today", "table", "pool"])
def test_three_rows_step_forward_and_back_with_disabled_ends_per_list(kind):
    """Every originating list: N of M in your view, bilingual controls, no wrap at the
    ends, the exact body node moved in and back home, one stable scroll, and Close
    returning focus to the trigger the reader was actually on."""
    origin_name, _, _, _, list_expr = _LISTS[kind]
    _run(
        "const origin = origins['" + origin_name + "'];\n"
        "const listEl = " + list_expr + ";\n" + _AT_HOME
        + """
await flush();
const order = Array.from(listEl.children);
const initsAtOpen = stockTableInitCalls;
const persistsAtOpen = effects.filter(e => e[0] === 'persistView').length;
fire(origin.trigger); await flush();
"""
        + _HOOKS + """
assert.equal(dialogEl().open, true, 'the candidate detail did not open');
assert.equal(bar.hidden, false, 'navigation must show for a three-row view');
assert.equal(prev.disabled, true, 'previous must be disabled at the first row');
assert.equal(next.disabled, false);
assert.ok(prev.textContent.includes('Previous') && prev.textContent.includes('上一张'),
          'EN/ZH copy must ship together on both controls');
assert.ok(next.textContent.includes('Next') && next.textContent.includes('下一张'));
assert.ok(pos.textContent.includes('1 of 3 in your view'), pos.textContent);
assert.ok(pos.textContent.includes('视图中第 1 / 3 张'), pos.textContent);
const scrollAtOpen = scrollState.y;

fire(prev); await flush();                            // disabled end must not wrap
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             origin.body, 'the first row must not wrap backwards');

fire(next); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body, 'Next must move the exact next body node into the dialog');
assert.equal(dialogEl().querySelector('#pvs-dialog-title').textContent, 'SECOND');
assert.equal(second.body.parentNode, dialogEl().querySelector('.pvs-dialog-content'));
assert.equal(second.row.contains(second.body), false, 'the body really moved');
assert.equal(atHome(origin), true, 'the previous body returned home exactly');
assert.ok(pos.textContent.includes('2 of 3 in your view'), pos.textContent);
assert.ok(pos.textContent.includes('视图中第 2 / 3 张'), pos.textContent);
assert.equal(prev.disabled, false);
assert.equal(next.disabled, false);
assert.equal(document.activeElement, next, 'click navigation retains sensible focus');
assert.equal(scrollState.y, scrollAtOpen, 'the original page scroll survives the step');

fire(next); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             third.body);
assert.ok(pos.textContent.includes('3 of 3 in your view'), pos.textContent);
assert.equal(next.disabled, true, 'next must be disabled at the last row — no wrap');
assert.equal(document.activeElement, closeBtn(), 'a disabled endpoint cannot keep focus');

fire(prev); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body);
assert.equal(document.activeElement, prev, 'focus returns to the enabled control clicked');
assert.equal(scrollState.y, scrollAtOpen);

fire(closeBtn());
assert.equal(dialogEl().open, false);
assert.equal(document.activeElement, second.trigger,
             'Close must return focus to the currently viewed trigger');
assert.equal(scrollState.y, scrollAtOpen, 'Close must restore the original scroll');
assert.equal(atHome(second), true, 'each visited body returned home');
assert.equal(atHome(third), true);
assert.equal(atHome(origin), true);
assert.deepEqual(Array.from(listEl.children), order, 'the originating list is unchanged');
assert.equal(stockTableInitCalls, initsAtOpen, 'the board must not be re-rendered');
assert.equal(effects.filter(e => e[0] === 'persistView').length, persistsAtOpen,
             'no new view write, no fetch-sized effect');
""",
        pre=_three(kind),
    )


def test_hidden_withheld_folded_and_nonserviceable_rows_are_never_browsable():
    """Only exact currently visible, entitled, serviceable rows enter the snapshot: a
    hidden row, a tier-blurred row, an aria-withheld row, a show-more-folded row, a
    card with no setup detail and a row with a non-native link are all invisible to
    Previous/Next, which then counts exactly the two real rows."""
    _run(
        """
await flush();
fire(origins.board.trigger); await flush();
"""
        + _HOOKS + """
assert.ok(pos.textContent.includes('1 of 2 in your view'), pos.textContent);
fire(next); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body, 'only the serviceable visible row is browsable');
assert.ok(pos.textContent.includes('2 of 2 in your view'), pos.textContent);
fire(next); await flush();                            // disabled endpoint, no wrap
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body, 'nothing exists past the last serviceable row');
assert.equal(gone.row.isConnected, true, 'excluded rows stay in the list, untouched');
""",
        pre=_PRE["grid"] + """
const second = candidate('board', 'SECOND', 'OTHER-BULL-20260811');
const gone = candidate('board', 'GONE', 'OTHER-BULL-20260811'); gone.row.setAttribute('hidden', '');
const blurred = candidate('board', 'BLUR', 'OTHER-BULL-20260811'); blurred.row.classList.add('mx-tier-blurred');
const withheld = candidate('board', 'WTHLD', 'OTHER-BULL-20260811'); withheld.row.setAttribute('aria-hidden', 'true');
const folded = candidate('board', 'FOLDED', 'OTHER-BULL-20260811'); folded.row.classList.add('sm-hidden');
const bare = mk('article', 'pvcard', {'data-ticker': 'BARE'});
const unbound = candidate('board', 'UNBOUND', 'OTHER-BULL-20260811');
unbound.row.querySelector('.pv-setup-stock-link').setAttribute('href', 'other.html#UNBOUND');
candGrid.append(second.row, gone.row, blurred.row, withheld.row, folded.row, bare, unbound.row);
""",
    )


@pytest.mark.parametrize("label,mutation", [
    ("published generation changed", "panel.setAttribute('data-as-of', '2026-10-11T20:00:00-04:00');"),
    ("native identity moved", "second.row.querySelector('.pv-setup-stock-link').setAttribute('href', 'stock.html#SWAPPED');"),
    ("row recycled for another ticker", "second.row.setAttribute('data-ticker', 'RECYCLED');"),
    ("row removed", "third.row.remove();"),
    ("row hidden", "second.row.setAttribute('hidden', '');"),
    ("tier withheld", "second.row.classList.add('mx-tier-hidden');"),
    ("aria withheld", "second.row.setAttribute('aria-hidden', 'true');"),
    ("list reordered", "candGrid.children[0].before(second.row);"),
])
def test_a_changed_view_hides_the_controls_and_never_navigates_stale(label, mutation):
    """Whatever takes the snapshot's population, order, identity, access or generation
    away must hide the controls on the next mutation turn and leave no stale index for
    a click to act on."""
    _run(
        (
        """
const why = ]]WHY[;
await flush();
fire(second.trigger); await flush();
"""
        + _HOOKS + """
assert.equal(bar.hidden, false, 'fixture control: the middle row browses');
const bodyBefore = dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body');
""" + mutation + """
await flush();
assert.equal(bar.hidden, true, why + ': must hide the browsing controls');
if (dialogEl().open) {
  next.click(); prev.click(); await flush();
  assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
               bodyBefore, why + ': a dead context must not navigate');
  assert.equal(bar.hidden, true, why + ': the controls stay hidden');
}
""").replace("]]WHY[", repr(label)),
        pre=_three("grid"),
    )


def test_a_new_row_is_admitted_only_by_a_fresh_snapshot_not_a_stale_one():
    """A row added mid-episode must not join the open browsing context; reopening the
    detail may create a fresh visible-list snapshot that legitimately counts it."""
    _run(
        """
await flush();
fire(second.trigger); await flush();
"""
        + _HOOKS + """
assert.ok(pos.textContent.includes('2 of 3 in your view'), pos.textContent);
candGrid.append(candidate('board', 'FOURTH', 'OTHER-BULL-20260811').row);
await flush();
assert.equal(bar.hidden, true, 'a changed list must not admit the new row in place');
next.click(); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body, 'no stale index');
fire(closeBtn()); await flush();
fire(second.trigger); await flush();
assert.ok(pos.textContent.includes('2 of 4 in your view'),
          'a fresh snapshot may count the row that is now in the view: ' + pos.textContent);
fire(next); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             third.body, 'the fresh snapshot browses the current population');
""",
        pre=_three("grid"),
    )


def test_table_view_turn_ends_the_table_browsing_episode():
    """A filter/view owner turn that takes the dense rows out of the view ends both the
    open detail and the browsing episode through the existing owners."""
    _run(
        """
await flush();
fire(origins.table.trigger); await flush();
"""
        + _HOOKS + """
assert.ok(pos.textContent.includes('1 of 3 in your view'), pos.textContent);
window.USStockTable._setView('grid');                 // the existing view owner
await flush();
assert.equal(dialogEl().open, false, 'the rows left the view, so the detail closes');
assert.equal(bar.hidden, true, 'the browsing episode ended with the view');
fire(origins.table.trigger); await flush();
assert.equal(dialogEl().open, false, 'an unreachable row cannot reopen');
""",
        pre=_three("table"),
    )


def test_same_source_quote_text_ticks_do_not_invalidate():
    """Live quote ticks mutate row text constantly; the snapshot is node-identity and
    generation based, so a same-source text tick keeps the controls and index stable."""
    _run(
        """
const origin = origins.board;
await flush();
fire(second.trigger); await flush();
"""
        + _HOOKS + """
assert.equal(bar.hidden, false);
origin.trigger.textContent = 'Setup detail · quote tick';
origin.row.setAttribute('data-tick', '1');
await flush();
assert.equal(bar.hidden, false, 'a same-source text tick must not invalidate');
assert.ok(pos.textContent.includes('2 of 3 in your view'), 'the index stays stable');
fire(next); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             third.body, 'navigation still works after quote ticks');
""",
        pre=_three("grid"),
    )


def test_plan_records_and_single_candidate_views_hide_navigation():
    """Plan detail never browses; a one-candidate view has nothing to browse."""
    _run(
        """
await flush();
fire(srcBtn('plan'));                                 // Plans, reached the existing way
assert.equal(window.USProphetSource.get(), 'plans');
panel.setAttribute('data-lifef', 'entered');          // the lifecycle cell LFUS sits in
fire(plans.LFUS.trigger); await flush();
assert.equal(dialogEl().open, true, 'the Plan record detail opened');
assert.equal(dialogEl().querySelector('.pvs-browse-bar').hidden, true,
             'Plan records never browse');
fire(closeBtn()); await flush();
fire(srcBtn('cand'));
fire(origins.board.trigger); await flush();
assert.equal(dialogEl().querySelector('.pvs-browse-bar').hidden, true,
             'a single-candidate list hides navigation');
fire(closeBtn()); await flush();
fire(srcBtn('plan'));
panel.setAttribute('data-lifef', 'ready');            // the lifecycle cell TDAY sits in
fire(plans.TDAY.trigger); await flush();
assert.equal(dialogEl().querySelector('.pvs-browse-bar').hidden, true,
             'no other Plan record browses either');
""",
    )


def test_plan_hop_from_a_navigated_candidate_returns_to_that_candidate():
    """Step board → SECOND, hop to Plans from SECOND's own link: the one transient
    return belongs to the candidate the reader is viewing, never the first one, and
    the reopened detail keeps a fresh snapshot of the same view."""
    _run(
        """
await flush();
fire(origins.board.trigger); await flush();
fire(document.querySelector('[data-pvs-browse="next"]')); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body);
fire(second.link);                                    // View in Plans, from SECOND
assert.equal(document.body.dataset.pvsPlanLinkResult, 'ok');
assert.equal(window.USProphetSource.get(), 'plans');
assert.equal(returnBtns().length, 1, 'exactly one return control');
assert.equal(window.PVSetupReturn.available(), true);
assert.equal(window.PVSetupReturn.run(), true, 'return refused');
await flush();
assert.equal(window.USProphetSource.get(), 'candidates', 'the view mode is restored');
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body, 'the return must land on the viewed candidate, never the first one');
assert.equal(dialogEl().querySelector('#pvs-dialog-title').textContent, 'SECOND');
assert.equal(document.activeElement, closeBtn());
fire(closeBtn());
assert.equal(document.activeElement, second.trigger, 'focus returns to the viewed trigger');
""",
        pre=_three("grid"),
    )


@pytest.mark.parametrize("dispatch,kind", [
    ("(window.listeners['mmx-access-tier'] || []).forEach(fn => fn({}))", "grid"),
    ("(window.listeners['mdx-auth'] || []).forEach(fn => fn({}))", "today"),
    ("(document.listeners['candidate-pool-hydrated'] || []).forEach(fn => fn({}))", "pool"),
])
def test_auth_tier_and_hydration_end_the_episode_and_reopen_is_fresh(dispatch, kind):
    """The existing auth/tier/hydration invalidation must also end the browsing episode
    (dialog dismissed, controls gone); a later reopen creates a fresh snapshot."""
    opener = "fire(origins.%s.trigger); await flush();\n" % _LISTS[kind][0]
    _run(
        opener
        + """
fire(document.querySelector('[data-pvs-browse="next"]')); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body);
""" + dispatch + """;
await flush();
assert.equal(dialogEl().open, false, 'the existing owner still dismisses the detail');
assert.equal(dialogEl().querySelector('.pvs-browse-bar').hidden, true, 'the episode is over');
""" + opener
        + """
assert.equal(dialogEl().open, true);
assert.ok(dialogEl().querySelector('.pvs-browse-position').textContent.includes('1 of 3 in your view'),
          'a fresh visible-list snapshot: ' +
          dialogEl().querySelector('.pvs-browse-position').textContent);
fire(document.querySelector('[data-pvs-browse="next"]')); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body, 'the fresh snapshot browses again');
""",
        pre=_three(kind),
    )


def test_pool_generation_turn_ends_the_episode_and_the_new_generation_browses_fresh():
    """The pool publishes its own digest: a new generation is a new source, so the open
    episode ends through the existing owner and no stale click can act; only a fresh
    episode may browse the new generation."""
    _run(
        """
await flush();
fire(origins.pool.trigger); await flush();
"""
        + _HOOKS + """
assert.ok(pos.textContent.includes('1 of 3 in your view'), pos.textContent);
document.getElementById('us-candidate-pool').setAttribute('data-source-digest', 'dig-2');
await flush();
assert.equal(dialogEl().open, false, 'the existing owner dismisses a changed generation');
assert.equal(bar.hidden, true, 'a new published generation is a new source');
fire(origins.pool.trigger); await flush();
assert.ok(pos.textContent.includes('1 of 3 in your view'),
          'a fresh episode may browse the new generation: ' + pos.textContent);
fire(next); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body, 'the fresh snapshot browses normally');
""",
        pre=_three("pool"),
    )


def test_today_native_envelope_turn_ends_the_episode():
    """A Today envelope turn republishes the shelf: the browsing snapshot must go (the
    open detail itself stays, exactly as the existing owners keep it), and no stale
    click may act on the dead context."""
    _run(
        """
await flush();
fire(origins.today.trigger); await flush();
"""
        + _HOOKS + """
assert.ok(pos.textContent.includes('1 of 3 in your view'), pos.textContent);
const bodyBefore = dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body');
document.getElementById('us-today').setAttribute('data-today-roster-size', '9');
await flush();
assert.equal(bar.hidden, true, 'a new Today envelope is a new view');
next.click(); prev.click(); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             bodyBefore, 'no stale index for a click to act on');
fire(closeBtn()); await flush();
fire(origins.today.trigger); await flush();
assert.ok(pos.textContent.includes('1 of 3 in your view'),
          'a fresh episode may browse the new envelope: ' + pos.textContent);
fire(next); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body, 'the fresh snapshot browses normally');
""",
        pre=_three("today"),
    )


def test_language_turn_dismisses_but_labels_ship_both_languages():
    """The existing language owner still dismisses the detail; the controls carry their
    own EN/ZH pair, so a reopened episode labels itself bilingually at once."""
    _run(
        """
await flush();
fire(origins.board.trigger); await flush();
"""
        + _HOOKS + """
assert.ok(pos.textContent.includes('1 of 3 in your view'));
assert.ok(pos.textContent.includes('视图中第 1 / 3 张'));
(document.listeners.langchange || []).forEach(fn => fn({}));
await flush();
assert.equal(dialogEl().open, false, 'the existing language owner still dismisses');
assert.equal(bar.hidden, true, 'the episode is over');
fire(origins.board.trigger); await flush();
assert.ok(dialogEl().querySelector('.pvs-browse-position').textContent.includes('1 of 3 in your view'));
assert.ok(dialogEl().querySelector('.pvs-browse-position').textContent.includes('视图中第 1 / 3 张'),
          'the reopened controls are bilingual again');
""",
        pre=_three("grid"),
    )


def test_comparison_picks_and_compare_view_survive_navigation():
    """Stepping between two chosen cards must not touch the study selection, the compare
    view state, the source mode or the table view."""
    _run(
        """
await flush();
const origin = origins.board;
const pick = row => row.querySelector('.pvs-study-pick');
const studyBar = document.querySelector('[data-pvs-study-for="us-cand-grid"]');
fire(pick(origin.row)); fire(pick(second.row)); await flush();
fire(studyBar.querySelector('.pvs-study-start')); await flush();
assert.equal(candGrid.classList.contains('pvs-study-active'), true);
fire(origin.trigger); await flush();
"""
        + _HOOKS + """
assert.equal(bar.hidden, false, 'both chosen cards are visible and browsable');
assert.ok(pos.textContent.includes('1 of 2 in your view'), pos.textContent);
fire(next); await flush();
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'),
             second.body);
assert.equal(pick(origin.row).getAttribute('aria-pressed'), 'true',
             'navigation must not touch comparison picks');
assert.equal(pick(second.row).getAttribute('aria-pressed'), 'true');
assert.equal(candGrid.classList.contains('pvs-study-active'), true, 'compare view preserved');
assert.equal(window.USProphetSource.get(), 'candidates', 'source mode untouched');
assert.equal(window.USStockTable._getView(), 'grid', 'table view untouched');
fire(closeBtn()); await flush();
assert.equal(pick(origin.row).getAttribute('aria-pressed'), 'true');
assert.equal(pick(second.row).getAttribute('aria-pressed'), 'true');
assert.equal(candGrid.classList.contains('pvs-study-active'), true);
""",
        pre=_PRE["grid"] + """
const second = candidate('board', 'SECOND', 'OTHER-BULL-20260811');
candGrid.append(second.row);
""",
    )


def test_focus_trap_skips_disabled_endpoint_controls():
    """At the first row Previous is disabled: the native Tab trap must cycle between the
    enabled controls only, in both directions."""
    _run(
        """
await flush();
fire(origins.board.trigger); await flush();
"""
        + _HOOKS + """
assert.equal(prev.disabled, true, 'fixture control: first row');
const link = dialogEl().querySelector('.pvs-native-link');
link.focus();
assert.equal(document.activeElement, link);
const fwd = {type: 'keydown', key: 'Tab', shiftKey: false, target: link,
             preventDefault() { this.prevented = true; }};
(dialogEl().listeners.keydown || []).forEach(fn => fn(fwd));
assert.equal(fwd.prevented, true, 'the trap must cycle from the last control');
assert.equal(document.activeElement, closeBtn(),
             'forward wrap lands on the first non-disabled control');
const back = {type: 'keydown', key: 'Tab', shiftKey: true, target: closeBtn(),
              preventDefault() { this.prevented = true; }};
(dialogEl().listeners.keydown || []).forEach(fn => fn(back));
assert.equal(back.prevented, true);
assert.equal(document.activeElement, link,
             'backward wrap skips the disabled endpoint control');
""",
        pre=_three("grid"),
    )


@pytest.mark.parametrize("replacement", ["details", "trigger", "body"])
def test_same_turn_replacement_of_target_source_nodes_invalidates_snapshot(replacement):
    mutation = {
        "details": "second.details.remove(); second.row.append(fresh.details);",
        "trigger": "second.trigger.remove(); second.details.append(fresh.trigger);",
        "body": "second.body.remove(); second.details.append(fresh.body);",
    }[replacement]
    _run("""
await flush(); fire(origins.board.trigger); await flush();
const next = dialogEl().querySelector('[data-pvs-browse="next"]');
const fresh = candidate('board', 'SECOND', 'OTHER-BULL-20260811');
""" + mutation + """
// The same row, symbol and generation still exist. No observer has delivered yet.
fire(next); await flush();
assert.equal(dialogEl().querySelector('.pvs-browse-bar').hidden, true);
assert.equal(dialogEl().querySelector('.pvs-dialog-content').querySelector('.pv-setup-body'), origins.board.body);
assert.equal(dialogEl().contains(fresh.body), false);
""", pre=_three("grid"))
