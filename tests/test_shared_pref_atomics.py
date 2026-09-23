"""tests/test_shared_pref_atomics.py — the cross-product shared-preference contract (E6).

`user_metadata.prefs` is a NESTED object, and supabase `auth.updateUser` REPLACES a nested
object wholesale. TWO browsers write it — this dashboard (templates/theme.js) and the
Mastermind Terminal (terminal/lib/accountPrefs.ts) — so each one's write silently discarded
whatever the other had changed since it last read:

    1. Terminal reads  {theme: dark, lang: en}
    2. here: the user picks Light  -> we write the WHOLE object
    3. Terminal, still holding its snapshot, changes language to Chinese
    4. Terminal sends {theme: dark, lang: zh}
    5. the Light choice from step 2 is gone.

Serializing either product's own writes cannot fix that — the race is BETWEEN the products —
and a fresh-read-before-write only shrinks the window, because read and write are not atomic.

The repair removes the shared container: each field is its own TOP-LEVEL key, and top-level
keys MERGE. This module pins the JS side of that as a source contract, the same way
tests/test_canada_build.py asserts on templates/theme.js text: there is no browser harness in
this repo, and a silent regression here is invisible until two live products disagree.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

THEME_JS = Path(__file__).resolve().parent.parent / "templates" / "theme.js"
#: The DEPLOYED artifact. `site/theme.js` is a committed build product — lib/site_assets.py
#: `copy_asset` bakes the Supabase config and the Terminal overlay into it at copy time — and it
#: is what mastermind-x.com actually serves. It is committed ALONGSIDE the template in every
#: commit that touches templates/theme.js (verified: the five commits before #6170 all did).
#: PR #6170 shipped the template alone, so the fix merged and changed nothing live. That is the
#: gap `test_the_deployed_artifact_is_not_stale` exists to close.
SITE_THEME_JS = Path(__file__).resolve().parent.parent / "site" / "theme.js"


@pytest.fixture(scope="module")
def src() -> str:
    return THEME_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def deployed() -> str:
    return SITE_THEME_JS.read_text(encoding="utf-8")


def _save_pref_fn(src: str) -> str:
    """The body of `_savePrefToServer`, up to the next top-level comment block."""
    start = src.index("function _savePrefToServer(")
    end = src.index("/* Hook into theme/lang events", start)
    return src[start:end]


def test_the_writer_never_sends_the_nested_prefs_blob(src: str) -> None:
    """The whole point. A writer that sends `prefs` clobbers the other product's field."""
    body = _save_pref_fn(src)
    assert "data: { prefs" not in body
    assert "prefs: prefs" not in body
    assert re.search(r"\bpatch\.prefs\b", body) is None


def test_the_writer_sends_top_level_atomics(src: str) -> None:
    body = _save_pref_fn(src)
    assert "patch.theme =" in body
    assert "patch.theme_auto =" in body
    assert "patch.lang =" in body
    assert "updateUser({ data: data })" in body


def test_a_language_change_carries_only_the_language(src: str) -> None:
    """The restraint IS the fix: a lang write that also carried a stale theme would still
    lose the other product's newer theme, atomics or not."""
    body = _save_pref_fn(src)
    lang_branch = body[body.index("else if (which === 'lang')"):]
    assert "patch.lang" in lang_branch
    assert "patch.theme" not in lang_branch


def test_each_event_names_the_field_it_changed(src: str) -> None:
    assert "'themechange', function () { _savePrefToServer('theme'); }" in src
    assert "'langchange', function () { _savePrefToServer('lang'); }" in src


def test_the_reader_falls_back_per_field_not_per_blob(src: str) -> None:
    """A half-migrated account is the NORMAL state during the rollout: an account may have a
    v2 `lang` and only a legacy `prefs.theme`. A per-blob fallback reads one of them wrong."""
    fn = src[src.index("function _sharedPref("):src.index("function _isTheme(")]
    assert "meta[atomicKey]" in fn
    assert "legacy[legacyKey]" in fn
    # the atomic is preferred, and the legacy value is only consulted after it fails validation
    assert fn.index("meta[atomicKey]") < fn.index("legacy[legacyKey]")


def test_the_reader_resolves_all_three_shared_fields(src: str) -> None:
    apply_fn = src[src.index("function _applyServerPrefs("):src.index("/* Save ONLY the atomics")]
    assert "_sharedPref(meta, 'theme', 'theme', _isTheme)" in apply_fn
    assert "_sharedPref(meta, 'theme_auto', 'themeAuto', _isFlag)" in apply_fn
    assert "_sharedPref(meta, 'lang', 'lang', _isLang)" in apply_fn


def test_the_atomic_names_match_the_servers_own_vocabulary(src: str) -> None:
    """`theme` and `lang` are not new names — lib/user_prefs.py already calls them canonical
    and app/account_prefs.py already writes them. A parallel `ui_*` namespace would have made
    a THIRD representation of one preference."""
    from lib import user_prefs

    assert "lang" in user_prefs.PREF_VALUES
    assert "theme" in user_prefs.PREF_VALUES
    assert set(user_prefs.PREF_VALUES["theme"]) == {"light", "dark"}
    assert set(user_prefs.PREF_VALUES["lang"]) == {"en", "zh"}
    assert "ui_theme" not in src and "ui_lang" not in src


def test_theme_auto_is_browser_only_and_stays_out_of_the_route_vocabulary(src: str) -> None:
    """It is a presentation flag (the dashboard computes the theme from local time when it is
    set), not a server-stored preference — adding it to PREF_VALUES would widen the chat tool's
    write surface for nothing."""
    from lib import user_prefs

    assert "theme_auto" in src
    assert "theme_auto" not in user_prefs.PREF_VALUES


def test_the_deployed_artifact_is_not_stale(deployed: str) -> None:
    """site/theme.js is what the live site serves. A template-only change is invisible.

    This is not a hypothetical: PR #6170 edited templates/theme.js and NOT site/theme.js, so the
    lost-update fix merged to main while mastermind-x.com kept serving the whole-blob writer. The
    template is the source of truth, but the artifact is the thing that runs.
    """
    body = _save_pref_fn(deployed)
    assert "patch.theme =" in body
    assert "patch.theme_auto =" in body
    assert "patch.lang =" in body
    assert "data: { prefs" not in body
    assert "prefs: prefs" not in body


def test_the_deployed_artifact_reads_per_field_too(deployed: str) -> None:
    apply_fn = deployed[deployed.index("function _applyServerPrefs("):deployed.index("/* Save ONLY the atomics")]
    assert "_sharedPref(meta, 'theme', 'theme', _isTheme)" in apply_fn
    assert "_sharedPref(meta, 'theme_auto', 'themeAuto', _isFlag)" in apply_fn
    assert "_sharedPref(meta, 'lang', 'lang', _isLang)" in apply_fn


def test_the_deployed_artifact_matches_the_template_for_this_block(src: str, deployed: str) -> None:
    """copy_asset() bakes config into site/theme.js, so the files are not byte-identical — but the
    preference-sync block is copied verbatim, and any drift between them means one of the two was
    hand-edited instead of regenerated."""
    assert _save_pref_fn(src) == _save_pref_fn(deployed)


# ---------------------------------------------------------------------------
# Shared Settings host contract
#
# The theme/lang atomics above are only useful if the shared Settings host can
# present them without collision and dismiss predictably. This suite is the
# existing CI owner that actually runs whenever templates/site theme.js changes,
# so the two Batch A host regressions live here rather than in an untriggered
# navigation suite.
# ---------------------------------------------------------------------------

def _run_settings_focus_runtime(source: str, *, old_focus_restore: bool = False) -> dict:
    """Execute the shipped Settings dismissal/focus fragment in a tiny DOM stub."""
    start = source.index("    function isOpen() {")
    end = source.index("    // account section", start)
    fragment = source[start:end]

    if old_focus_restore:
        guard = """    var _gearPointerDown = false, _gearFocusRestore = false;
    function restoreGearFocus() {
      // Focus restoration is part of closing, not a fresh request to open.
      // Some browsers report relatedTarget=null on programmatic focus; without
      // this one-shot guard the focusin handler can immediately reopen the pane.
      _gearFocusRestore = true;
      try { gear.focus(); } catch (e) {}
      setTimeout(function () { _gearFocusRestore = false; }, 0);
    }
"""
        assert guard in fragment
        fragment = fragment.replace(guard, "    var _gearPointerDown = false;\n", 1)
        fragment = fragment.replace("restoreGearFocus();", "gear.focus();")
        fragment = fragment.replace(
            "      if (e.target === gear && _gearFocusRestore) "
            "{ _gearFocusRestore = false; return; }\n",
            "",
            1,
        )

    driver = r"""
const timers = [];
function events(name) {
  const own = {};
  return {
    name,
    addEventListener(type, fn) { (own[type] ||= []).push(fn); },
    emit(type, event = {}) { for (const fn of own[type] || []) fn(event); }
  };
}
function classes(initial = []) {
  const set = new Set(initial);
  return {
    contains(x) { return set.has(x); },
    add(x) { set.add(x); },
    remove(x) { set.delete(x); }
  };
}
const wrap = events('wrap');
wrap.classList = classes();
wrap.contains = node => node === wrap || node === gear || node === pop || node === closeButton;
const closeButton = events('close');
const pop = events('pop');
pop.classList = classes();
pop.focus = () => {
  const prev = document.activeElement;
  document.activeElement = pop;
  wrap.emit('focusin', { target: pop, relatedTarget: prev });
};
pop.querySelector = selector => selector === '.settings-close' ? closeButton : null;
const gear = events('gear');
gear.attrs = {};
gear.setAttribute = (k, v) => { gear.attrs[k] = v; };
gear.focus = () => {
  const prev = document.activeElement;
  document.activeElement = gear;
  wrap.emit('focusin', { target: gear, relatedTarget: null, previous: prev });
};
const document = events('document');
document.activeElement = null;
const window = { matchMedia: () => ({ matches: false }), MMSettings: null };
const setTimeout = fn => { timers.push(fn); return timers.length; };
const _curUser = null;
""" + fragment + r"""
function snapshot() {
  return {
    open: isOpen(),
    expanded: gear.attrs['aria-expanded'] || null,
    active: document.activeElement && document.activeElement.name
  };
}
open();
document.emit('keydown', { key: 'Escape' });
const afterEscape = snapshot();

open();
closeButton.emit('click', {});
const afterCloseButton = snapshot();

wrap.emit('focusin', { target: gear, relatedTarget: null });
const afterFreshFocus = snapshot();

console.log(JSON.stringify({ afterEscape, afterCloseButton, afterFreshFocus }));
"""
    result = subprocess.run(
        ["node", "-e", driver],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (
        f"node Settings focus harness failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    return json.loads(result.stdout)


def test_settings_focus_restore_executes_without_reopening(src: str, deployed: str) -> None:
    """Escape/x restore focus without reopening; fresh external focus still opens."""
    for source in (src, deployed):
        fixed = _run_settings_focus_runtime(source)
        for key in ("afterEscape", "afterCloseButton"):
            assert fixed[key] == {"open": False, "expanded": "false", "active": "gear"}
        assert fixed["afterFreshFocus"] == {
            "open": True,
            "expanded": "true",
            "active": "pop",
        }

        # Discrimination: reinstating the historical implementation must fail
        # the close contract by reopening immediately on restored focus.
        old = _run_settings_focus_runtime(source, old_focus_restore=True)
        assert old["afterEscape"]["open"] is True
        assert old["afterCloseButton"]["open"] is True



def _run_settings_hover_escape_runtime(source: str) -> dict:
    """Exercise the CSS-hover-only Settings presentation against shipped JS."""
    start = source.index("    function isOpen() {")
    end = source.index("    // account section", start)
    fragment = source[start:end]

    driver = r"""
const timers = [];
function events(name) {
  const own = {};
  return {
    name,
    addEventListener(type, fn) { (own[type] ||= []).push(fn); },
    emit(type, event = {}) { for (const fn of own[type] || []) fn(event); }
  };
}
function classes(initial = []) {
  const set = new Set(initial);
  return {
    contains(x) { return set.has(x); },
    add(x) { set.add(x); },
    remove(x) { set.delete(x); }
  };
}
let hovering = true;
const wrap = events('wrap');
wrap.classList = classes();
wrap.matches = selector => selector === ':hover' && hovering;
wrap.contains = node => node === wrap || node === gear || node === pop || node === closeButton;
const closeButton = events('close');
const pop = events('pop');
pop.classList = classes();
pop.focus = () => {
  const prev = document.activeElement;
  document.activeElement = pop;
  wrap.emit('focusin', { target: pop, relatedTarget: prev });
};
pop.querySelector = selector => selector === '.settings-close' ? closeButton : null;
const gear = events('gear');
gear.attrs = {'aria-expanded': 'false'};
gear.focusCount = 0;
gear.setAttribute = (k, v) => { gear.attrs[k] = v; };
gear.focus = () => {
  gear.focusCount += 1;
  const prev = document.activeElement;
  document.activeElement = gear;
  wrap.emit('focusin', { target: gear, relatedTarget: null, previous: prev });
};
const outside = { name: 'outside' };
const document = events('document');
document.activeElement = outside;
const window = {
  matchMedia: q => ({ matches: q.indexOf('(hover:hover)') !== -1 }),
  MMSettings: null
};
const setTimeout = fn => { timers.push(fn); return timers.length; };
const _curUser = null;
""" + fragment + r"""
function snapshot() {
  return {
    open: isOpen(),
    expanded: gear.attrs['aria-expanded'] || null,
    dismissed: wrap.classList.contains('settings-dismissed'),
    active: document.activeElement && document.activeElement.name,
    focusCount: gear.focusCount
  };
}
wrap.emit('mouseenter', {});
const beforeEscape = snapshot();
document.emit('keydown', { key: 'Escape' });
const afterEscape = snapshot();
document.emit('keydown', { key: 'Escape' });
const afterRepeatedEscape = snapshot();
while (timers.length) timers.shift()();
hovering = false;
wrap.emit('mouseleave', {});
hovering = true;
wrap.emit('mouseenter', {});
const afterReenter = snapshot();
console.log(JSON.stringify({ beforeEscape, afterEscape, afterRepeatedEscape, afterReenter }));
"""
    result = subprocess.run(
        ["node", "-e", driver],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (
        f"node Settings hover/Escape harness failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    return json.loads(result.stdout)


def test_settings_hover_only_escape_dismisses_without_reopen(src: str, deployed: str) -> None:
    """Escape must dismiss CSS-only desktop hover without stealing focus on hover."""
    for source in (src, deployed):
        state = _run_settings_hover_escape_runtime(source)
        assert state["beforeEscape"] == {
            "open": False,
            "expanded": "false",
            "dismissed": False,
            "active": "outside",
            "focusCount": 0,
        }
        assert state["afterEscape"] == {
            "open": False,
            "expanded": "false",
            "dismissed": True,
            "active": "gear",
            "focusCount": 1,
        }
        assert state["afterRepeatedEscape"]["focusCount"] == 1
        assert state["afterRepeatedEscape"]["dismissed"] is True
        assert state["afterReenter"]["open"] is False
        assert state["afterReenter"]["dismissed"] is False


def test_settings_narrow_phone_reflow_hosts_shared_preferences(src: str, deployed: str) -> None:
    """At <=360px theme/lang controls move below labels instead of obscuring them."""
    for source in (src, deployed):
        settings_css = source.split("  var SETTINGS_CSS = [", 1)[1].split(
            "  ].join('');", 1
        )[0]
        assert "@media (max-width:360px){" in settings_css
        assert (
            ".settings-row:not(.settings-acct){display:grid;"
            "grid-template-columns:18px minmax(0,1fr);column-gap:11px;"
            "row-gap:8px;align-items:center}"
        ) in settings_css
        assert (
            ".settings-row:not(.settings-acct)>.sr-ctrl{grid-column:1 / -1;"
            "width:100%;min-width:0}"
        ) in settings_css
        assert (
            ".settings-row:not(.settings-acct) .set-theme-seg{width:100%;"
            "box-sizing:border-box;min-width:0}"
        ) in settings_css
        assert (
            ".settings-row:not(.settings-acct) .set-seg-btn{flex:1 1 0;"
            "min-width:40px;padding-left:6px;padding-right:6px}"
        ) in settings_css
        assert (
            ".settings-row:not(.settings-acct) .lang-toggle{width:100%;"
            "box-sizing:border-box}"
        ) in settings_css
        assert (
            ".settings-row:not(.settings-acct) .lang-toggle .opt{flex:1 1 50%;"
            "min-width:0}"
        ) in settings_css
        narrow = settings_css.split("@media (max-width:360px){", 1)[1].split(
            "'}',", 1
        )[0]
        assert ".settings-acct .sa-btns" not in narrow
        assert ".settings-acct-in" not in narrow
