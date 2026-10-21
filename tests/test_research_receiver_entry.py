"""Static pins for the SIC-I05R Research receiver entry island (masterplan §8.2).

Pure-python text checks against templates/research_vault.html.j2 — no browser,
no network, no site/ or data/ fixtures, no builder imports (keeps the suite on
the tier-gate job's minimal venv line, same discipline as
tests/test_sector_receiver_contracts.py). The island is an inline script +
server-rendered markup block delimited by id="si-research-entry"; these tests
pin the packet's frozen spec: six link params read, verbatim textContent
readback, origin allowlist, explicit-click-only writes through the existing
FifSavedBriefcase writer, and label-only language-switch repaint.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = ROOT / "templates" / "research_vault.html.j2"

#: the six link fields the receiver contract names, verbatim.
LINK_PARAMS = ("si_subject", "si_q", "si_snap", "si_obs", "si_ev", "si_origin")

#: the six readback value sinks in the island markup.
READBACK_IDS = (
    "si-rb-subject",
    "si-rb-q",
    "si-rb-snap",
    "si-rb-obs",
    "si-rb-ev",
    "si-rb-origin",
)

#: the si_origin allowlist producers (frozen spec; sectors/ is a pattern).
ORIGIN_ALLOWLIST = ("sector_central.html", "sector_cycles.html", "sectors")

#: the briefcase's own policy-selection enum — the observed si_ev vocabulary
#: (templates/fif_saved_briefcase.js:44 SELECTIONS; the evidence-ref list at
#: :296 carries entries, not modes).
EVIDENCE_MODES = ("as_reported", "latest_known_as_of", "latest_restated")


def _html() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _island_script(html: str) -> str:
    """The island's inline script, located by its SIC-I05R header comment."""
    match = re.search(r"<script>\s*(/\* SIC-I05R.*?)</script>", html, re.S)
    assert match, "the SIC-I05R island script is missing from the vault template"
    return match.group(1)


def _island_markup(html: str) -> str:
    start = html.index('id="si-research-entry"')
    section_start = html.rindex("<section", 0, start)
    return html[section_start:html.index("</section>", start)]


def _langchange_region(script: str) -> str:
    match = re.search(
        r"document\.addEventListener\('langchange', function \(\) \{(.*?)\n  \}\);",
        script, re.S)
    assert match, "island script has no langchange listener"
    return match.group(1)


# ── island present, hidden without a subject ────────────────────────────────

def test_island_markup_present_and_hidden_by_default():
    markup = _island_markup(_html())
    assert 'id="si-research-entry"' in markup
    assert "hidden" in markup, "the island must ship hidden; only valid si_subject reveals it"
    for sink in READBACK_IDS:
        assert f'id="{sink}"' in markup, f"readback sink {sink} missing"
    assert 'id="si-research-q"' in markup          # the composer
    assert 'id="si-research-save"' in markup       # explicit save
    assert 'id="si-research-return"' in markup     # allowlisted return link
    assert markup.index('id="si-research-save"') < markup.index('id="si-research-return"')


def test_island_labels_ride_the_t_macro_bilingually():
    markup = _island_markup(_html())
    labels = re.findall(r"\{\{ t\('([^']+)', '([^']+)'\) \}\}", markup)
    assert len(labels) >= 9, "every island label must be a t() EN/ZH pair"
    for en, zh in labels:
        assert en and zh


# ── six link params read; vocabulary + allowlist frozen ─────────────────────

def test_six_link_params_are_read_by_name():
    script = _island_script(_html())
    for name in LINK_PARAMS:
        assert f"raw('{name}')" in script, f"the island no longer reads {name}"


def test_evidence_mode_vocabulary_is_the_briefcase_selection_enum():
    script = _island_script(_html())
    for mode in EVIDENCE_MODES:
        assert f"'{mode}'" in script, f"si_ev vocabulary lost {mode}"
    assert "EVIDENCE_MODES.indexOf" in script, "unknown si_ev values must be dropped, not passed through"


def test_origin_allowlist_present_and_same_origin_relative_only():
    script = _island_script(_html())
    for producer in ORIGIN_ALLOWLIST:
        assert producer in script, f"origin allowlist lost {producer}"
    assert "decodeURIComponent" in script, "allowlist comparison happens after decodeURIComponent"
    assert "indexOf('//')" in script and "indexOf(':')" in script, (
        "origin must refuse any // or : (same-origin relative only)"
    )


# ── verbatim readback: textContent only, never trusted as HTML ──────────────

def test_readback_paints_textcontent_and_never_innerhtml():
    script = _island_script(_html())
    assert "innerHTML" not in script, "link values are never trusted as HTML"
    assert ".textContent = " in script
    for sink in READBACK_IDS:
        assert f"paint('{sink}'" in script, f"readback sink {sink} is not painted"


# ── explicit-click-only writes through the existing briefcase writer ────────

def test_no_storage_touch_outside_the_click_handler():
    script = _island_script(_html())
    # the island itself never touches storage; the only write path is the
    # briefcase writer, and it is called from exactly one place — inside the
    # Save click handler.
    assert "localStorage" not in script
    assert "setItem" not in script
    saves = [m.start() for m in re.finditer(r"\.save\(", script)]
    assert len(saves) == 1, f"exactly one writer call expected, found {len(saves)}"
    click = script.index("addEventListener('click'")
    assert saves[0] > click, "the writer call must live inside the click handler"
    resolves = [m.start() for m in re.finditer(r"window\.FifSavedBriefcase", script)]
    assert resolves and min(resolves) > click, (
        "the writer must be resolved inside the click handler, never at load"
    )


def test_save_policy_rides_si_snap_verbatim_and_records_now():
    script = _island_script(_html())
    assert "source_snapshot_at: fields.snap" in script
    assert "recorded_at: now" in script
    assert "new Date().toISOString()" in script
    # the writer is the existing store — no store is added here
    assert "FifSavedBriefcase" in script and "typeof api.create" in script


# ── si_obs: shape + real calendar + not from the future (RI05 MINOR) ────────

def test_observation_date_is_calendar_checked_and_capped_at_today_plus_one():
    script = _island_script(_html())
    assert "validObservationDate(raw('si_obs'))" in script, (
        "si_obs must pass the calendar validator, not just DATE_RE"
    )
    # a real Date round-trip: 2026-02-30 rolls over to March and is refused
    assert "new Date(year, month - 1, day)" in script
    assert "calendar.getFullYear() !== year" in script
    assert "calendar.getMonth() !== month - 1" in script
    assert "calendar.getDate() !== day" in script
    # no later than today+1: local midnight of today+2 is the exclusive ceiling
    assert "setDate(dayAfterTomorrow.getDate() + 2)" in script
    assert "calendar.getTime() < dayAfterTomorrow.getTime()" in script
    # DATE_RE stays the shape gate, inside the validator
    assert "DATE_RE.test(value)" in script
    assert "DATE_RE.test(raw('si_obs'))" not in script


# ── clipping is visible, never silent (RI05 MINOR) ──────────────────────────

def test_clipped_carried_fields_are_marked_shortened_in_the_readback():
    script = _island_script(_html())
    # both clip sites report (RI05 pins the island's own 280/128 caps)
    assert "clip(raw('si_q'), 280)" in script
    assert "clip(raw('si_snap').trim(), 128)" in script
    assert "shortened: text !== value" in script
    # the readback carries the visible EN/ZH mark on a clipped field
    assert "' (shortened)'" in script and "'（已缩短）'" in script
    assert "fields.q + (qCarried.shortened ? shortenedMark : '')" in script
    assert "fields.snap + (snapCarried.shortened ? shortenedMark : '')" in script
    # the frozen snapshot stays pure — the mark never enters SI_RESEARCH_ENTRY
    snapshot = script[script.index("window.SI_RESEARCH_ENTRY"):script.index("window.SI_RESEARCH_ENTRY") + 400]
    assert "shortenedMark" not in snapshot


def test_saved_name_shortened_by_the_store_is_said_so():
    script = _island_script(_html())
    # the store cuts names at MAX_NAME_LENGTH=120 (fif_saved_briefcase.js:34);
    # the island compares the stored name and says so through the EN/ZH
    # status mechanism instead of failing silently
    assert "savedShortened" in script
    assert "result.view.name !== name" in script


# ── the store ships on the vault page (RI05 MAJOR-1) ────────────────────────

def test_vault_page_loads_the_briefcase_store():
    """RI05 MAJOR-1: the island's Save resolves window.FifSavedBriefcase, so the
    vault page must load the store — the exact Forensics tag and stamp
    (templates/fundamental_forensics.html.j2:592), ahead of the island's script."""
    html = _html()
    tag = '<script src="fif_saved_briefcase.js?v=20261012-x2s1" defer></script>'
    assert tag in html, (
        "the vault page must load fif_saved_briefcase.js with the Forensics stamp"
    )
    assert html.index(tag) < html.index("/* SIC-I05R"), (
        "the store tag must precede the island's script in the document"
    )
    # and when the store is still absent, Save says so in the island's own
    # EN/ZH status line — never a silent return
    script = _island_script(html)
    assert "noStore" in script


# ── unsaved text survives the in-page language switch ───────────────────────

def test_langchange_repaints_labels_only():
    script = _island_script(_html())
    region = _langchange_region(script)
    assert "applyPlaceholder()" in region
    assert not re.search(r"\.value\s*=", region), (
        "the langchange handler must never assign the composer's value"
    )
    # the composer value is assigned exactly once — the initial si_q prefill
    assigns = re.findall(r"\.value\s*=", script)
    assert len(assigns) == 1, "the composer value must only be set by the si_q prefill"
    prefill = script.index(".value =")
    assert prefill < script.index("addEventListener('langchange'")
    # readback sinks are painted before the listener too — a switch never
    # rewrites the six verbatim values
    for sink in READBACK_IDS:
        assert script.index(f"paint('{sink}'") < script.index("addEventListener('langchange'")


# ── frozen spec: exactly one new global ─────────────────────────────────────

def test_single_new_global_snapshot():
    script = _island_script(_html())
    globals_touched = set(re.findall(r"window\.([A-Za-z_$][\w$]*)", script))
    assert globals_touched <= {"SI_RESEARCH_ENTRY", "FifSavedBriefcase"}, (
        f"no new globals beyond window.SI_RESEARCH_ENTRY (+ the existing store): {globals_touched}"
    )
    assert "window.SI_RESEARCH_ENTRY = Object.freeze(" in script


def test_langchange_refreshes_the_clipped_mark_language():
    """RI05b MINOR: a clipped field's '(shortened)' mark follows the page
    language after a switch; the six verbatim values are never rewritten."""
    script = _island_script(_html())
    assert "function currentShortenedMark()" in script
    region = _langchange_region(script)
    assert "shortenedMark = currentShortenedMark();" in region
    assert "paint('si-rb-q', fields.q + (qCarried.shortened ? shortenedMark : ''))" in region
    assert "paint('si-rb-snap', fields.snap + (snapCarried.shortened ? shortenedMark : ''))" in region
    assert "si-rb-subject" not in region and "si-rb-obs" not in region and "si-rb-ev" not in region
