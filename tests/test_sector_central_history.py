"""Sector Central / Sector Cycles Back/Forward invariants (J-restore).

Charter: research/sector_completion_20261021/INTEGRATION_CONTRACT.md §Gaps 1, 2
and 4, closed by SIC-I09A (P18 part A) — a Back/Forward in the Sector Central
shell must restore the previous view AND its scroll origin, and a Back/Forward
on /sector_cycles.html must re-apply its focus deep link.

What this file is defending, and why each pin exists rather than being obvious:

* **Event bindings are the whole contract.** The J-restore paths are event-driven.
  Drop the shell's popstate listener or the router's hashchange binding and the
  page still works when clicked forward — only Back/Forward silently degrades,
  which is exactly the no-symptom failure gap 1 recorded (0 test hits for
  popstate anywhere in tests/ at contract time).
* **Scroll memory ordering.** The per-view scroll position is only correct if it
  is captured BEFORE the .on section swap (the section being hidden still owns
  the viewport at that instant) and replayed only when no explicit target was
  passed — a LEGACY_ANCHORS deep link must keep winning over remembered scroll.
  `history.scrollRestoration` must stay untouched: the memory is additive, not a
  hostile takeover of the browser's own restoration.
* **One reader, no history spam.** The cycles listeners must re-run the same
  deep-link reader boot() uses, and must stay off the shell host (inside Sector
  Central the hash belongs to si_workspace.js's view router — a setFocus-driven
  replaceState there would clobber the shell's #view entry). Focus changes stay
  replaceState: a pushState would turn every chip tap into a Back-button stop.
* **The 21-key literal.** Byte-stability of `var LEGACY_ANCHORS={…};` is what
  keeps test_xpv2_sector_r3_fixture.py::TestLegacyAnchors (a real parser) and
  every redirect stub in agreement; this file re-parses the same literal with
  the same regex so the two suites cannot drift apart silently.

Static on purpose: these are shipped template assets copied verbatim by the
nightly render, so a text pin on the source is the same pin on the artifact —
no browser, no site/ build, nothing the 4-core render host has to own.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"
SHELL = TPL / "sector_central.html.j2"
ROUTER = TPL / "si_workspace.js"
CYCLES = TPL / "sector_cycles.js"


def _code(js: str) -> str:
    """The asset with comments stripped.

    Every code-SHAPE assertion below must run against this, not the raw file
    (same rationale as tests/test_si_workspace_shell.py::_code): the assets
    document their own traps in prose, so a raw-text scan matches the warning
    against a construct and reports — or hides — a defect that is not there.
    """
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", js)


def _shell() -> str:
    return SHELL.read_text(encoding="utf-8")


def _router() -> str:
    return ROUTER.read_text(encoding="utf-8")


def _cycles() -> str:
    return CYCLES.read_text(encoding="utf-8")


# ────────────────────────────────────────────────────── gap 1: the bindings exist

def test_shell_popstate_handler_present() -> None:
    """The mr-panel ?g= restore is the shell's only popstate listener; losing it
    silently reverts every measured-read Back/Forward to the default group."""
    assert "window.addEventListener('popstate'" in _shell(), (
        "sector_central.html.j2 lost its popstate listener"
    )


def test_router_binds_hashchange_to_route() -> None:
    """Back/Forward between #view entries reaches activate() only through this
    binding; the view itself is restored nowhere else."""
    assert "window.addEventListener('hashchange',route);" in _code(_router()), (
        "si_workspace.js no longer binds hashchange to route"
    )


# ─────────────────────────────────────────── gap 2: per-view scroll origin memory

def test_router_declares_scroll_memory_map() -> None:
    assert "var SCROLL_MEM={}" in _code(_router()), (
        "si_workspace.js lost its module-level SCROLL_MEM declaration"
    )


def test_scroll_memory_captured_before_the_view_swap() -> None:
    """The write must sit inside activate(), before the first .on toggle: the
    section about to be hidden still owns window.scrollY at that instant, and
    after the swap the viewport no longer describes the view being left."""
    code = _code(_router())
    write = "if(current) SCROLL_MEM[current]=window.scrollY;"
    assert write in code, "per-view scroll capture line is gone or reworded"
    activate_at = code.index("function activate(view,target){")
    write_at = code.index(write)
    toggle_at = code.index("classList.toggle('on'")
    assert activate_at < write_at < toggle_at, (
        "scroll capture must run inside activate(), before the .on section swap "
        f"(activate@{activate_at}, capture@{write_at}, first .on toggle@{toggle_at})"
    )


def test_scroll_memory_restored_only_when_no_explicit_target() -> None:
    """The replay lives in the else of `if(target){`, guarded by a typeof check,
    so a LEGACY_ANCHORS deep link (explicit target) always wins and a first
    visit (no entry — `typeof SCROLL_MEM[view]` is not 'number') keeps native
    browser behaviour."""
    code = _code(_router())
    assert "else if(typeof SCROLL_MEM[view]==='number'){" in code, (
        "restore lost its no-entry guard or moved out of the no-target branch"
    )
    m = re.search(r"requestAnimationFrame\(function\(\)\{\s*"
                  r"window\.scrollTo\(0,\s*SCROLL_MEM\[view\]\|\|0\);?\s*\}\)", code)
    assert m, "restore must replay the remembered offset on the next frame"
    assert code.index("if(target){") < m.start(), (
        "restore must sit after the explicit-target branch, i.e. run only when "
        "activate() was called without a scroll target"
    )


def test_scroll_restoration_setting_is_never_touched() -> None:
    """The memory is additive; the router must never hijack the browser's own
    restoration by assigning history.scrollRestoration."""
    assert "scrollRestoration" not in _code(_router()), (
        "si_workspace.js must not assign history.scrollRestoration"
    )
    assert "scrollRestoration" not in _code(_cycles()), (
        "sector_cycles.js must not assign history.scrollRestoration"
    )


# ───────────────────────────────────── gap 4: cycles focus deep link on Back/Forward

def test_cycles_binds_popstate_and_hashchange_to_one_shared_reader() -> None:
    """Both listeners must route through the single extracted reader
    (applyFocusHash) that boot()'s delayed first paint also uses — a second
    copy of the parse rules is how the two paths drift apart."""
    code = _code(_cycles())
    assert code.count("function applyFocusHash()") == 1, (
        "the focus deep-link reader must exist exactly once"
    )
    assert "setTimeout(applyFocusHash, 350)" in code, (
        "boot() must keep applying the landing deep link after first paint"
    )
    pat = re.compile(
        r"if \(!window\.SC_LAZY_EXTRAS\) \{\s*"
        r"var syncFocusHash = function \(\) \{ if \(!applyFocusHash\(\)\) setFocus\(null\); \};\s*"
        r'window\.addEventListener\("popstate", syncFocusHash\);\s*'
        r'window\.addEventListener\("hashchange", syncFocusHash\);'
    )
    assert pat.search(code), (
        "cycles must register exactly one popstate and one hashchange listener, "
        "behind the standalone-page guard, both calling the shared reader"
    )


def test_cycles_focus_changes_never_push_history() -> None:
    """Focus selection stays replaceState (:1018 at contract time) — pushing an
    entry per chip tap would make Back leave the page instead of clearing the
    focus."""
    assert "pushState" not in _code(_cycles()), (
        "sector_cycles.js must keep focus changes replaceState-only"
    )


# ─────────────────────────────────────────── the frozen 21-key LEGACY_ANCHORS literal

def _parse_legacy_anchors(text: str) -> dict:
    """Same real-parser approach as test_xpv2_sector_r3_fixture.py: lift the
    `var LEGACY_ANCHORS={…};` literal, strip its comments, parse as JSON."""
    m = re.search(r"var LEGACY_ANCHORS\s*=\s*\{(.*?)\}\s*;", text, re.S)
    assert m, "could not locate LEGACY_ANCHORS object"
    body = "{" + m.group(1) + "}"
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    json_body = body.replace("'", '"')
    json_body = re.sub(r",(\s*\})\s*$", r"\1", json_body.strip())
    return json.loads(json_body)


def test_legacy_anchors_literal_parses_to_exactly_21_keys() -> None:
    anchors = _parse_legacy_anchors(_router())
    assert len(anchors) == 21, (
        f"LEGACY_ANCHORS literal must hold exactly 21 keys, found {len(anchors)} "
        "(the S2 keys live outside it by design — see the 21/23 split note)"
    )
    assert all(isinstance(v, list) and len(v) == 2 for v in anchors.values()), (
        "every LEGACY_ANCHORS entry must remain a [view, scroll-target] pair"
    )
