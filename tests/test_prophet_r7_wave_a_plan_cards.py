"""tests/test_prophet_r7_wave_a_plan_cards.py — R7 Wave A slice A1 record-card states.

R7_DESIGN_SPEC_2026-10-21 §12/§13: the US plan cards are immutable HISTORY records
(record_only, verb none, stance_basis historical_plan). A reader must be able to
tell a rebuilt plan and an old-model signal apart from a live decision, so both new
states are dated/neutral TEXT marks inside the existing marks row — never a stance,
never a glyph, never a Buy/Near/Wait word.

What each state means and where its condition comes from:
  * Reconstructed — mirrors engine/prophet_integrity.py::is_reconstructed exactly
    (origination_mode is a string starting with "outage_backfill"). The date named
    in the copy is the plan row's ``recorded_at`` — the origination day being
    replayed, i.e. the original plan's date — proven by
    engine/prophet_bridge.py::origination_note, which reads exactly that field.
    The value passes the same strict YYYY-MM-DD gate the template already applies
    to the board screen clock (_screen_ok); anything else ships the no-date
    fallback rather than a wrong day.
  * Older signal only — signal_date_basis == 'legacy_formation_alias' AND the
    ticker is not in cand_map (tonight's method never assessed this row).

Guard 3 (states replace content, never slots): the element structure OUTSIDE the
marks container is byte-stable across plain / reconstructed / older-signal, so a
state change is CLS-0 by construction.

Browser-free by design: the partial renders directly through jinja2 with only the
``tr`` global, exactly the tests/test_prophet_card_shared.py _r18_env pattern.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import jinja2
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PLAN_PARTIAL = "_us_prophet_plan_cards.html.j2"
THEME_CSS = ROOT / "templates" / "theme.css"

BACKFILL_MODE = "outage_backfill_2026_08_09"

# OQ8: the two original raw-warn text rules that must stay byte-identical, each
# followed later in the file by its ink-token override (add-only repair).
OQ8_ORIGINAL_SG_WX = (
    "body.page-macro .mx5-sc-vw .sx-vw-row.sx-vw-row--elevated "
    ".sg-wx{color:var(--warn,#f59e0b);}"
)
OQ8_ORIGINAL_TIER = (
    "body.page-macro .mx5-sc-vw .sx-vw-row.sx-vw-row--elevated "
    ".sx-vw-tier{color:var(--warn,#f59e0b);}"
)
OQ8_OVERRIDE_SG_WX = (
    "body.page-macro .mx5-sc-vw .sx-vw-row.sx-vw-row--elevated "
    ".sg-wx{color:var(--ink-warn, var(--warn));}"
)
OQ8_OVERRIDE_TIER = (
    "body.page-macro .mx5-sc-vw .sx-vw-row.sx-vw-row--elevated "
    ".sx-vw-tier{color:var(--ink-warn, var(--warn));}"
)

# Guard 5: classes _prophet_card.html.j2 uses for an ACTIONABLE stance — the
# pv-<verb> card-root family (pv-buy/pv-near/pv-wait/pv-hold/pv-avoid) and the
# filled/half stage-dot states (.pv-dot.on / .pv-dot.pa). None may appear on a
# record card in any state.
STANCE_ROOT_CLASSES = ("pv-buy", "pv-near", "pv-wait", "pv-hold", "pv-avoid")
STANCE_DOT_MARKERS = ('class="pv-dot on"', 'class="pv-dot pa"', 'class="pv-seg pa"')

FORBIDDEN_VISIBLE = ("Buy", "买入", "Near", "临近")


def _env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT / "templates")), autoescape=True
    )
    env.globals["tr"] = lambda value: value
    return env


def _render(item: dict, *, cand_map: dict | None = None) -> str:
    return str(
        _env().get_template(PLAN_PARTIAL).render(
            items=[item],
            cand_map=cand_map or {},
            trg_map={},
            episode_map={},
        )
    )


def _base(**extra: object) -> dict:
    row: dict = {
        "id": "TEST-BULL-20260901",
        "asset": "TEST",
        "lifecycle_state": "invalidated",
        "management_status": "available",
        "management_error": None,
        "entry": 10.0,
        "invalidation": 9.0,
        "targets": [11.0, 12.0],
        "horizon_days": 20,
    }
    row.update(extra)
    return row


class _Structure(HTMLParser):
    """Tag+class sequence OUTSIDE the pv-mk marks container, plus card roots.

    States replace content inside the marks row; nothing outside it may move
    (Guard 3). Void elements are ignored for div matching; the marks container
    is a div whose class list contains pv-mk.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.seq: list[str] = []
        self.text: list[str] = []
        self.card_roots = 0
        self._div_depth = -1  # -1 = outside the marks container

    def handle_starttag(self, tag, attrs):
        cls = (dict(attrs).get("class") or "").split()
        if tag == "div" and "pv-mk" in cls and self._div_depth == -1:
            self._div_depth = 0  # entering the marks container (its own div)
            return
        if self._div_depth >= 0:
            if tag == "div":
                self._div_depth += 1
            return
        if tag == "article" and "pvcard" in cls:
            self.card_roots += 1
        self.seq.append(tag + "." + ".".join(sorted(cls)))

    def handle_endtag(self, tag):
        if self._div_depth >= 0:
            if tag == "div":
                if self._div_depth == 0:
                    self._div_depth = -1  # the marks container closed
                else:
                    self._div_depth -= 1
            return
        if tag not in ("br", "img", "hr", "input", "meta", "link", "path", "circle"):
            self.seq.append("/" + tag)

    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())


def _structure(html: str) -> _Structure:
    parser = _Structure()
    parser.feed(html)
    parser.close()
    return parser


def _visible_text(html: str) -> str:
    return " ".join(_structure(html).text)


def _variants() -> dict[str, tuple[dict, dict]]:
    """One base row in its three states: plain, reconstructed, older-signal.

    Guard 3's premise: every variant carries the SAME row data — the only
    difference is the state key, and a state may change marks content only.
    """
    shared = _base(recorded_at="2026-10-17", signal_date_basis="tier_event_date")
    return {
        "plain": (shared, {}),
        "reconstructed": (dict(shared, origination_mode=BACKFILL_MODE), {}),
        "older_signal": (dict(shared, signal_date_basis="legacy_formation_alias"), {}),
    }


# --------------------------------------------------------------------------- #
# 1. Reconstructed — dated copy when the original plan's date is certain
# --------------------------------------------------------------------------- #

def test_reconstructed_row_carries_the_dated_bilingual_copy():
    html = _render(_base(origination_mode=BACKFILL_MODE, recorded_at="2026-10-17"))
    assert "Reconstructed from the Oct 17 plan" in html
    assert "依据 10月17日计划重建" in html


@pytest.mark.parametrize("mode", ["nightly", None])
def test_live_rows_never_say_reconstructed(mode):
    row = _base(recorded_at="2026-10-17")
    if mode is not None:
        row["origination_mode"] = mode
    html = _render(row)
    assert "Reconstructed" not in html
    assert "重建" not in html


def test_prefix_not_equality_a_differently_dated_replay_is_still_reconstructed():
    html = _render(_base(origination_mode="outage_backfill_2027_01_02",
                         recorded_at="2027-01-02"))
    assert "Reconstructed from the Jan 2 plan" in html
    assert "依据 1月2日计划重建" in html


def test_day_without_leading_zero_in_both_locales():
    html = _render(_base(origination_mode=BACKFILL_MODE, recorded_at="2026-03-05"))
    assert "Reconstructed from the Mar 5 plan" in html
    assert "Reconstructed from the Mar 05 plan" not in html
    assert "依据 3月5日计划重建" in html


# --------------------------------------------------------------------------- #
# 2. Reconstructed — no certain date: fallback copy, never a wrong day
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("recorded_at", [
    None,                     # key absent
    20261017,                 # not a string
    "",                       # empty
    "2026-10",                # too short
    "2026-10-17T00:00",       # not a plain date
    "20261301",               # malformed shape
    "2026-13-17",             # month out of range
    "2026-10-99",             # day out of range
    "2026-1x-17",             # non-digit month
    "17-10-2026",             # wrong field order
])
def test_reconstructed_without_a_certain_date_ships_the_fallback_copy(recorded_at):
    html = _render(_base(origination_mode=BACKFILL_MODE, recorded_at=recorded_at))
    assert "Reconstructed plan, original date not supplied" in html
    assert "重建的计划，原始日期未提供" in html
    assert "Reconstructed from the" not in html
    assert "计划重建" not in html
    assert "None" not in html  # never the literal None, in either locale


# --------------------------------------------------------------------------- #
# 3. Older signal only
# --------------------------------------------------------------------------- #

def test_older_signal_only_when_basis_is_legacy_and_ticker_not_a_candidate():
    html = _render(_base(signal_date_basis="legacy_formation_alias"), cand_map={})
    assert "Older signal only" in html
    assert "仅有旧信号" in html


def test_older_signal_only_never_when_the_ticker_is_a_candidate():
    html = _render(
        _base(signal_date_basis="legacy_formation_alias"),
        cand_map={"TEST": {"name": "Test Industries", "sector": "Tests"}},
    )
    assert "Older signal only" not in html
    assert "仅有旧信号" not in html


def test_tier_event_date_basis_never_marks_older_signal_only():
    html = _render(_base(signal_date_basis="tier_event_date"), cand_map={})
    assert "Older signal only" not in html
    assert "仅有旧信号" not in html


# --------------------------------------------------------------------------- #
# 4. Guard 3 — states replace content, never slots
# --------------------------------------------------------------------------- #

def test_state_changes_keep_the_structure_outside_the_marks_row():
    parsed = {name: _structure(_render(row, cand_map=cand))
              for name, (row, cand) in _variants().items()}
    seqs = {name: p.seq for name, p in parsed.items()}
    assert seqs["plain"] == seqs["reconstructed"] == seqs["older_signal"]
    for name, p in parsed.items():
        assert p.card_roots == 1, f"{name}: exactly one card root per item"


def test_one_card_root_per_item_in_a_multi_item_render():
    rows = [
        _base(id=f"TEST-BULL-2026090{i}", asset=f"T{i}",
              origination_mode=BACKFILL_MODE, recorded_at="2026-10-17")
        for i in (1, 2)
    ] + [_base(id="TEST-BULL-20260903", asset="T3",
               signal_date_basis="legacy_formation_alias")]
    html = str(_env().get_template(PLAN_PARTIAL).render(
        items=rows, cand_map={}, trg_map={}, episode_map={}))
    parsed = _structure(html)
    assert parsed.card_roots == len(rows) == 3
    assert html.count('data-record-only="1"') == 3


# --------------------------------------------------------------------------- #
# 5. Guards 4/5 — no decision vocabulary, no actionable stance glyph
# --------------------------------------------------------------------------- #

def test_no_stance_word_appears_as_visible_text_in_any_variant():
    for name, (row, cand) in _variants().items():
        text = _visible_text(_render(row, cand_map=cand))
        for word in FORBIDDEN_VISIBLE:
            assert word not in text, f"{name}: {word!r} leaked into reader copy"


def test_no_actionable_stance_glyph_class_in_any_variant():
    # Stance glyph classes checked: the pv-<verb> card-root family and the
    # .pv-dot.on/.pv-dot.pa/.pv-seg.pa stage-dot states from
    # templates/_prophet_card.html.j2 (record cards render none of them).
    for name, (row, cand) in _variants().items():
        html = _render(row, cand_map=cand)
        for root_cls in STANCE_ROOT_CLASSES:
            assert f'"{root_cls}' not in html.replace("pvcard", ""), \
                f"{name}: actionable stance root class {root_cls}"
        for marker in STANCE_DOT_MARKERS:
            assert marker not in html, f"{name}: stance dot state {marker}"


# --------------------------------------------------------------------------- #
# 6. theme.css — quiet line tokens, OQ8 add-only repair, .nowrap utility
# --------------------------------------------------------------------------- #

def _css_blocks(css: str) -> list[tuple[str, str]]:
    """(selector, body) pairs for top-level blocks, by brace matching."""
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.S)  # comments can hold braces
    blocks: list[tuple[str, str]] = []
    for match in re.finditer(r"([^{}]+)\{", stripped):
        head = match.group(1).strip()
        depth, body_start = 1, match.end()
        i = body_start
        while i < len(stripped) and depth:
            if stripped[i] == "{":
                depth += 1
            elif stripped[i] == "}":
                depth -= 1
            i += 1
        blocks.append((head, stripped[body_start:i - 1]))
    return blocks


def test_line_quiet_lives_in_the_dark_root_token_block():
    css = THEME_CSS.read_text(encoding="utf-8")
    dark = [body for head, body in _css_blocks(css)
            if head == ":root" and "--line:" in body]
    assert dark, "dark :root token block with --line not found"
    assert "--line-quiet: #272C35;" in dark[0]


def test_line_quiet_lives_in_the_light_token_block():
    css = THEME_CSS.read_text(encoding="utf-8")
    light = [body for head, body in _css_blocks(css)
             if head.startswith('html[data-theme="light"]') and "--line:" in body]
    assert light, "light token block with --line not found"
    assert "--line-quiet: #E2E6EC;" in light[0]


def test_nowrap_utility_present_and_oq8_repair_is_add_only():
    css = THEME_CSS.read_text(encoding="utf-8")
    assert ".nowrap{white-space:nowrap}" in css
    assert css.count(".nowrap{white-space:nowrap}") == 1
    for original, override in (
        (OQ8_ORIGINAL_SG_WX, OQ8_OVERRIDE_SG_WX),
        (OQ8_ORIGINAL_TIER, OQ8_OVERRIDE_TIER),
    ):
        assert original in css, f"original OQ8 line changed: {original}"
        assert css.index(override) > css.index(original), (
            "override must follow the original later in the file"
        )


# --------------------------------------------------------------------------- #
# 7. Escaping — the date field is untrusted input
# --------------------------------------------------------------------------- #

def test_a_markup_payload_in_the_date_field_never_renders_a_raw_tag():
    html = _render(_base(origination_mode=BACKFILL_MODE,
                         recorded_at="<b>2026-10-17"))
    # The mark itself fails the strict date gate and ships the fallback copy...
    assert "Reconstructed plan, original date not supplied" in html
    assert "重建的计划，原始日期未提供" in html
    # ...and the payload never survives as a raw tag anywhere in the card. The
    # pre-existing date slot does print the value — ESCAPED, which is exactly
    # what "renders escaped" requires (the card's own <b style=...> labels are
    # template markup, not payload, and stay out of this assertion's way).
    assert "<b>2026-10-17" not in html
    assert "&lt;b&gt;2026-10-17" in html


def test_a_well_formed_date_is_digits_only_and_safe_in_output():
    html = _render(_base(origination_mode=BACKFILL_MODE, recorded_at="2026-10-17"))
    # The rendered mark carries both locales and no markup of its own.
    assert "Reconstructed from the Oct 17 plan" in html
    assert "<script" not in html.lower()
