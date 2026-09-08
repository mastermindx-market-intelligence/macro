"""The FRONT-END CLARITY LAW gate for Macro Command (frozen spec G2/G2b, §9 P1).

`scripts/check_macro_command_copy.py` is the CI-wired guard. This file proves:

  1. it correctly ignores banned copy relocated inside `.mc-details` /
     `.mc-primer`, and correctly fails on the same copy left in the reading
     path (G2);
  2. the G2b bare-timestamp rule fires on an unprefixed `YYYY-MM-DD` /
     `T\\d\\d:\\d\\d` and passes a properly prefixed one;
  3. it is green against the REAL built `site/macro_monetary.html` (the
     frozen spec §9 P1 acceptance: "the copy guard is green");
  4. it is actually wired into CI next to the other Macro Command test files
     (`.github/ci/legacy-jobs.yml`), so a P2+ regression cannot ship
     unguarded.

Every packet after P1 ships new copy through this same guard (§9 standing
note: "green against the page that packet builds"), so this file's fixtures
and assertions are meant to survive unchanged as later packets add real
stance/primer/Read/chip content — only `test_the_real_built_page_is_clean`
runs against a moving target.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts import build_macro_suite_pages as builder
from scripts import check_macro_command_copy as guard

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "site" / "macrodata"
BUILT_AT = "2026-09-06T00:00:00Z"


@pytest.fixture(scope="module")
def built_hub(tmp_path_factory) -> str:
    """The real `macro_monetary.html`, rendered from the CURRENT templates
    against the real repo root — same convention as
    `tests/test_macro_command_shell.py`."""
    out = tmp_path_factory.mktemp("macro_command_copy") / "site"
    pages = builder.render(ROOT, data_root=DATA_ROOT, out_dir=out, page_built_at=BUILT_AT)
    hub = [p for p in pages if p.name == builder.HUB_PAGE.output]
    assert hub, "the builder did not write macro_monetary.html"
    return hub[0].read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# G2 — banned vocabulary outside mc-details / mc-primer
# --------------------------------------------------------------------------

@pytest.mark.parametrize("phrase", [
    "accepted snapshot", "Regime map", "authority ceiling", "content hash",
    "falsifier", "refuted", "证伪",
])
def test_banned_phrase_left_in_the_reading_path_fails(phrase: str) -> None:
    html = f'<main class="mc-shell"><p>{phrase} appears here.</p></main>'
    violations = guard.find_violations(html)
    assert any(phrase in v for v in violations), violations


@pytest.mark.parametrize("phrase", ["accepted snapshot", "falsifier", "证伪"])
def test_the_same_phrase_inside_mc_details_is_exempt(phrase: str) -> None:
    html = (
        '<main class="mc-shell">'
        '<details class="mc-details"><summary>Details, methods and sources</summary>'
        f'<div class="mc-details-body">{phrase}</div></details>'
        '</main>'
    )
    assert guard.find_violations(html) == []


def test_the_same_phrase_inside_mc_primer_is_exempt() -> None:
    html = (
        '<main class="mc-shell">'
        '<details class="mc-primer"><summary>New to this? 30 seconds</summary>'
        '<div class="mc-primer-body">accepted snapshot</div></details>'
        '</main>'
    )
    assert guard.find_violations(html) == []


def test_closed_vocabulary_token_from_labels_module_is_banned() -> None:
    tokens = guard._closed_vocabulary_tokens()
    assert "SOURCE_FAILED" in tokens
    html = '<main class="mc-shell"><p>SOURCE_FAILED</p></main>'
    violations = guard.find_violations(html)
    assert any("SOURCE_FAILED" in v for v in violations)


def test_script_content_is_never_scanned() -> None:
    """`macro_command.js`'s own header comment quotes the very substrings it
    forbids (G9) in prose — a copy-law scan of raw <script> text would flag
    the guard's OWN houseeeping comment. Script content is out of scope: this
    guard is about what a reader sees, not what the source code says about
    itself."""
    html = (
        '<main class="mc-shell"></main>'
        '<script>// this producer artifact snapshot is a code comment, not copy</script>'
    )
    assert guard.find_violations(html) == []


# --------------------------------------------------------------------------
# G2b — bare timestamp
# --------------------------------------------------------------------------

def test_bare_timestamp_with_no_preceding_word_fails() -> None:
    """G2b's own regex (`(?<![A-Za-z一-鿿][  ])\\d{4}-\\d{2}-\\d{2}`) only
    exempts a date preceded by a letter-then-space — "As of:" ends in a
    colon and a space, not a letter and a space, so this is a genuine bare
    timestamp under the spec's own definition."""
    html = '<main class="mc-shell"><p>As of: 2026-09-06.</p></main>'
    violations = guard.find_violations(html)
    assert any("bare timestamp" in v for v in violations), violations


def test_timestamp_prefixed_by_a_plain_word_passes() -> None:
    html = '<main class="mc-shell"><p>Data to 2026-09-06.</p></main>'
    assert guard.find_violations(html) == []


def test_emitted_asof_markup_with_intervening_tags_passes() -> None:
    """The page emits the G2b prefix and the date in sibling tags
    (`templates/macro_monetary.html.j2` header :106 and chip :145). Tag
    stripping must not insert a space that breaks the lookbehind."""
    header = (
        '<span class="mc-asof-word"><span class="l-en">Data to</span>'
        '<span class="l-zh">数据截至</span></span> '
        '<time datetime="2026-09-03">2026-09-03</time>'
    )
    chip = (
        '<span class="mc-chip-asof">'
        '<span class="mc-asof-word"><span class="l-en">Data to</span>'
        '<span class="l-zh">数据截至</span></span> '
        '<time datetime="2026-09-03">2026-09-03</time>'
        '</span>'
    )
    assert guard.find_violations(f'<main class="mc-shell">{header}</main>') == []
    assert guard.find_violations(f'<main class="mc-shell">{chip}</main>') == []


def test_datetime_attribute_value_is_never_scanned() -> None:
    """The machine value legitimately lives in `datetime=`; tag-stripping
    removes the attribute along with the tag, so it never reaches the scan
    even though the surrounding visible text is plain words."""
    html = ('<main class="mc-shell"><p><span>Data to</span> '
            '<time datetime="2026-09-06">3 Sep 2026</time></p></main>')
    assert guard.find_violations(html) == []


def test_raw_iso_time_fragment_always_fails() -> None:
    html = '<main class="mc-shell"><p>Built 2026-09-06T00:00:00Z</p></main>'
    violations = guard.find_violations(html)
    assert any("ISO time" in v for v in violations), violations


# --------------------------------------------------------------------------
# the real built page (§9 P1 acceptance: "the copy guard is green")
# --------------------------------------------------------------------------

def test_the_real_built_page_is_clean(built_hub: str) -> None:
    assert guard.find_violations(built_hub) == []


def test_mc_figure_text_is_never_a_bare_number(built_hub: str) -> None:
    """E-m10: every Overview / section figure reading carries a scale word."""
    from html.parser import HTMLParser

    class _FigureTexts(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self._depth = 0
            self.texts: list[str] = []

        def handle_starttag(self, tag, attrs):
            cls = dict(attrs).get("class", "")
            if self._depth:
                self._depth += 1
            elif "mc-figure" in cls.split() or "mc-move" in cls.split():
                self._depth = 1

        def handle_endtag(self, tag):
            if self._depth:
                self._depth -= 1

        def handle_data(self, data):
            if not self._depth:
                return
            text = " ".join(data.split())
            if text:
                self.texts.append(text)

    parser = _FigureTexts()
    parser.feed(built_hub)
    assert parser.texts
    bare = re.compile(r"^[-−]?\d+(?:\.\d+)?$")
    for text in parser.texts:
        assert not bare.match(text), text


# --------------------------------------------------------------------------
# P5 — all fifteen built pages + relocated §5 strings
# --------------------------------------------------------------------------

# Non-figure §5 strings that P5 moves into <details class="mc-details">.
# Identity is the cited English string (spec §5, R1 — never deleted).
RELOCATED_STRINGS: tuple[str, ...] = (
    "Conservative over the required set — a degraded optional leg cannot turn this green.",
    "Last accepted source cut",
    "Calculation as-of",
    "Page built",
    "Required components and their source clocks",
    "Presence",
    "Freshness",
    "Source as-of",
    "Dates, coverage and source clocks",
    "Deterministic text from the accepted snapshot. No language model writes here.",
    "Confidence basis",
    "Trace",
    "Method version",
    "Hysteresis band",
    "Applied against the prior print",
    "Not applied: no comparable prior print",
    "Basis",
    "Definition",
    "Clocks and owner",
    "Authority ceiling",
    "Correction and method lineage",
    "Predecessor generation",
    "Changed fingerprints",
    "Artifact",
    "Transform",
    "Non-economic clocks",
    "Publication receipt",
    "Content hash",
    "Generation id",
    "Producer",
    "The page validated this artifact against the closed schema and recomputed its content hash before rendering.",
    "Technical detail for whoever repairs this",
    "Owner cadence, daily republish",
    "Latest accepted print",
    "Prior accepted print",
    "What this state implies",
)


def _outside_details(html: str) -> str:
    return guard.reading_path_text(html)


def test_every_relocated_string_is_inside_mc_details_on_a_workspace_page(
        tmp_path_factory) -> None:
    """Each cited §5 string is present inside .mc-details and absent from
    the reading path on a page that carried it (a built workspace page)."""
    out = tmp_path_factory.mktemp("macro_command_reloc") / "site"
    pages = builder.render(ROOT, data_root=DATA_ROOT, out_dir=out, page_built_at=BUILT_AT)
    workspace = [p for p in pages if p.name != builder.HUB_PAGE.output]
    assert workspace, "builder wrote no workspace pages"
    missing: list[str] = []
    leaked: list[str] = []
    # Conditional branches (hysteresis-not-applied; degraded refusal) only
    # appear on some builds — require presence when the page carried them.
    optional = {
        "Not applied: no comparable prior print",
        "Technical detail for whoever repairs this",
    }
    for cited in RELOCATED_STRINGS:
        carriers = [p for p in workspace if cited in p.read_text(encoding="utf-8")]
        if not carriers:
            if cited not in optional:
                missing.append(cited)
            continue
        for path in carriers:
            html = path.read_text(encoding="utf-8")
            if cited in _outside_details(html):
                leaked.append(f"{path.name}: {cited}")
    assert missing == [], f"relocated string missing from every workspace page: {missing}"
    assert leaked == [], f"relocated string still in the reading path: {leaked}"


def test_all_fifteen_built_pages_are_clean_outside_details(tmp_path_factory) -> None:
    """P5 acceptance: hub + 14 deep-link pages, zero banned hits outside
    .mc-details / .mc-primer."""
    out = tmp_path_factory.mktemp("macro_command_15") / "site"
    pages = builder.render(ROOT, data_root=DATA_ROOT, out_dir=out, page_built_at=BUILT_AT)
    names = {p.name for p in pages}
    assert builder.HUB_PAGE.output in names
    deep = [p for p in pages if p.name.startswith("macro_") and p.name.endswith(".html")
            and p.name != builder.HUB_PAGE.output]
    assert len(deep) == 14, f"expected 14 deep-link pages, got {len(deep)}: {sorted(p.name for p in deep)}"
    dirty: list[str] = []
    for path in pages:
        hits = guard.find_violations(path.read_text(encoding="utf-8"))
        if hits:
            dirty.append(f"{path.name}: {hits[:4]}")
    assert dirty == [], dirty


def test_built_hub_has_exactly_one_analyst_control_and_zero_endpoint_literals(
        built_hub: str) -> None:
    import re
    main = built_hub[built_hub.index('<main class="mc-shell"'):]
    openings = len(re.findall(r'<(?:button|a)[^>]*class="[^"]*mc-analyst', main))
    assert openings == 1
    js = (ROOT / "templates" / "macro_command.js").read_text(encoding="utf-8")
    for forbidden in ("?topic=", "&section=", "/api/"):
        assert forbidden not in main
        assert forbidden not in js


def test_row_62_footer_uses_the_exact_plain_strings(built_hub: str) -> None:
    assert "This page shows what each workspace published. It produces no score and no ranking of its own." in built_hub
    assert "本页展示各工作区已发布的内容。它不产生自己的评分，也不做自己的排序。" in built_hub
    assert "never tells you what to do" not in built_hub
    assert "It produces no score and no ordering of its own" not in built_hub


def test_guard_script_exits_zero_on_the_real_built_page(built_hub: str, tmp_path: Path) -> None:
    clean = tmp_path / "clean.html"
    clean.write_text(built_hub, encoding="utf-8")
    assert guard.main([str(clean)]) == 0


def test_guard_script_exits_nonzero_on_a_dirty_file(tmp_path: Path) -> None:
    dirty = tmp_path / "dirty.html"
    dirty.write_text('<main class="mc-shell"><p>accepted snapshot</p></main>', encoding="utf-8")
    assert guard.main([str(dirty)]) == 1


def test_guard_script_reports_a_missing_file_rather_than_crashing(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.html"
    assert guard.main([str(missing)]) == 1


# --------------------------------------------------------------------------
# CI wiring — a P2+ regression must not ship unguarded
# --------------------------------------------------------------------------

def test_guard_is_wired_into_ci() -> None:
    ci = (ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    assert "tests/test_macro_command_copy_law.py" in ci


# --------------------------------------------------------------------------
# P5 r2 — B1 / M2 / M3 / M4 / M5 / M6
# --------------------------------------------------------------------------

_POINTER_STRINGS = (
    "A published note is in Details",
    "A published reading",
    "A published driver",
    "A compared reading",
    "A published series",
    "A recorded data issue",
)

_B1_REWRITES = (
    ("macro_rates_curves.html",
     "This page does not publish a two-sided headline state"),
    ("macro_rates_curves.html",
     "This page reads the Treasury curve and the policy corridor only."),
    ("macro_business_activity.html",
     "No two-sided business-activity state is published today"),
    ("macro_financial_conditions.html",
     "The lending channel has no source wired today"),
    ("macro_housing_real_estate.html",
     "No two-sided housing state is published today"),
    ("macro_national_debt_liabilities.html",
     "No two-sided debt-pressure state is published today"),
    ("macro_trade_flows.html",
     "This page does not publish a two-sided headline state — Trade Flows was added after the original twelve workspaces"),
    ("macro_growth_real_economy.html",
     "Growth score"),
)

_B1_ORIGINALS = (
    ("macro_rates_curves.html",
     "This page publishes no dual-axis state and no headline quadrant"),
    ("macro_rates_curves.html",
     "This workspace reads FRED Treasury-curve and policy-corridor parquets only"),
    ("macro_growth_real_economy.html",
     "Growth axis composite (engine/axes.py)"),
)


def test_customer_macro_and_pointer_fallbacks_are_gone() -> None:
    shell = (ROOT / "templates" / "_macro_suite_shell.html.j2").read_text(encoding="utf-8")
    assert "{%- macro customer(" not in shell
    assert "macro customer(" not in shell
    for pointer in _POINTER_STRINGS:
        assert pointer not in shell


def test_copy_probe_ok_is_the_conjunction_of_every_row() -> None:
    from lib.macro_suite_labels import copy_probe_ok, copy_probe_row_ok
    present = {"in_page": True, "inside": True, "outside": False}
    assert copy_probe_row_ok(present) is True
    assert copy_probe_ok([present, present]) is True
    assert copy_probe_row_ok({"in_page": False, "inside": False, "outside": False}) is False
    assert copy_probe_row_ok({"in_page": False, "inside": True, "outside": False}) is False
    assert copy_probe_ok([present, {"in_page": False, "inside": False, "outside": False}]) is False
    assert copy_probe_ok([]) is False


def test_apply_plain_producer_unreviewed_machine_text_uses_fallback() -> None:
    from lib.macro_suite_labels import PLAIN_FALLBACK, apply_plain_producer
    reading, original = apply_plain_producer(
        {"en": "raw_unreviewed_slug has no pair", "zh": "无"})
    assert reading == PLAIN_FALLBACK
    assert original["en"].startswith("raw_unreviewed_slug")


def test_machine_text_predicate_catches_slugs_tokens_and_iso() -> None:
    from lib.macro_suite_labels import machine_text_hits
    assert machine_text_hits("sticky_led in the mix")
    assert machine_text_hits("typed NOT_COVERED forever")
    assert machine_text_hits("closed to {rate_side, balance_sheet}")
    assert machine_text_hits("as of 2026-09-06T17:33:16")
    assert machine_text_hits("p = 0.04")
    assert machine_text_hits("label_en is a field")
    assert not machine_text_hits("Sticky prices are leading the mix.")


def test_production_key_space_has_no_machine_text_on_rendered_output(
        tmp_path_factory) -> None:
    from lib.macro_suite_labels import machine_text_hits
    out = tmp_path_factory.mktemp("macro_command_predicate") / "site"
    pages = builder.render(ROOT, data_root=DATA_ROOT, out_dir=out,
                           page_built_at=BUILT_AT)
    dirty: list[str] = []
    for path in pages:
        html = path.read_text(encoding="utf-8")
        # Suite shell only — site chrome (nav, brand) is out of this packet.
        start = html.find('class="mq-context"')
        if start < 0:
            start = html.find('class="mc-shell"')
        if start < 0:
            start = 0
        shell = html[start:]
        en = guard.reading_path_text(
            shell.replace('class="l-zh"', 'class="l-zh" hidden'))
        zh = guard.reading_path_text(
            shell.replace('class="l-en"', 'class="l-en" hidden'))
        for locale, text in (("en", en), ("zh", zh)):
            hits = machine_text_hits(text)
            if hits:
                dirty.append(f"{path.name}:{locale}:{hits[:8]}")
    assert dirty == [], dirty


FIVE_COMMAND_PAGES = (
    "macro_monetary.html",
    "macro_rates_curves.html",
    "macro_business_activity.html",
    "macro_financial_conditions.html",
    "macro_housing_real_estate.html",
)


def test_committed_payloads_have_zero_plain_fallbacks() -> None:
    """MA4: count BOTH fallback sentences against committed site/*.html."""
    from lib.macro_suite_labels import PLAIN_FALLBACK

    if not (ROOT / "site" / "macro_monetary.html").is_file():
        pytest.skip("site/ is sparse-omitted; capture records fallback_count_* = 0")
    leftover: list[str] = []
    counts = {"en": 0, "zh": 0}
    for name in FIVE_COMMAND_PAGES:
        path = ROOT / "site" / name
        assert path.is_file(), name
        html = path.read_text(encoding="utf-8")
        start = html.find('class="mq-context"')
        if start < 0:
            start = html.find('class="mc-shell"')
        if start < 0:
            start = 0
        text = guard.reading_path_text(html[start:])
        n_en = text.count(PLAIN_FALLBACK["en"])
        n_zh = text.count(PLAIN_FALLBACK["zh"])
        counts["en"] += n_en
        counts["zh"] += n_zh
        if n_en or n_zh:
            leftover.append(f"{name}:en={n_en}:zh={n_zh}")
    assert counts["en"] == 0 and counts["zh"] == 0, leftover


def test_read_stance_has_one_space_after_each_topic(tmp_path_factory) -> None:
    """M-E12: the H1 stance join is one word space, never two."""
    out = tmp_path_factory.mktemp("macro_command_stance") / "site"
    pages = {p.name: p.read_text(encoding="utf-8")
             for p in builder.render(ROOT, data_root=DATA_ROOT, out_dir=out,
                                     page_built_at=BUILT_AT)}
    hub = pages["macro_monetary.html"]
    start = hub.find('class="mc-read"')
    assert start > 0
    chunk = hub[start:start + 4000]
    en = guard.reading_path_text(
        chunk.replace('class="l-zh"', 'class="l-zh" hidden'))
    zh = guard.reading_path_text(
        chunk.replace('class="l-en"', 'class="l-en" hidden'))
    assert "  " not in en, en
    assert "  " not in zh, zh


def test_synthetic_slug_renders_the_fallback_pair() -> None:
    import json
    from lib.macro_suite_labels import PLAIN_FALLBACK
    from lib.macro_suite_view import build_view
    workspace = DATA_ROOT / "workspaces" / "rates_curves" / "US" / "latest.json"
    if not workspace.is_file():
        pytest.skip("rates_curves snapshot is not in this checkout")
    body = json.loads(workspace.read_text(encoding="utf-8"))
    items = (((body.get("implications") or {}).get("items")) or [])
    if not items:
        pytest.skip("rates_curves snapshot carries no implications")
    items[0]["text"] = {"en": "raw_slug_token has no reviewed pair",
                        "zh": "raw_slug_token 无审定"}
    view = build_view(
        body, page_built_at=BUILT_AT,
        artifact={"path": "x", "manifest_path": "y", "sha256": "z", "bytes": 1},
    )
    lead = view["implications"]["entries"][0]["text"]
    assert lead == PLAIN_FALLBACK
    assert "raw_slug_token" not in lead["en"]
    assert "raw_slug_token" not in lead["zh"]


def test_b1_rewrites_are_in_the_reading_path_and_originals_are_in_details(
        tmp_path_factory) -> None:
    out = tmp_path_factory.mktemp("macro_command_b1") / "site"
    pages = {p.name: p.read_text(encoding="utf-8")
             for p in builder.render(ROOT, data_root=DATA_ROOT, out_dir=out,
                                     page_built_at=BUILT_AT)}
    for pointer in _POINTER_STRINGS:
        for name, html in pages.items():
            assert pointer not in html, f"{name} still has {pointer!r}"
    for name, needle in _B1_REWRITES:
        html = pages[name]
        assert needle in guard.reading_path_text(html), name
    for name, needle in _B1_ORIGINALS:
        html = pages[name]
        assert needle in html
        assert needle not in guard.reading_path_text(html), name


def test_no_details_has_a_p_or_span_ancestor_on_the_fifteen_pages(
        tmp_path_factory) -> None:
    from html.parser import HTMLParser

    class _Walker(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.stack: list[str] = []
            self.bad: list[str] = []

        def handle_starttag(self, tag, attrs):
            if tag == "details" and any(a in self.stack for a in ("p", "span")):
                self.bad.append("/".join(self.stack + [tag]))
            if tag not in {"br", "img", "input", "meta", "link", "hr"}:
                self.stack.append(tag)

        def handle_endtag(self, tag):
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
            elif tag in self.stack:
                while self.stack and self.stack[-1] != tag:
                    self.stack.pop()
                if self.stack:
                    self.stack.pop()

    out = tmp_path_factory.mktemp("macro_command_m3") / "site"
    pages = builder.render(ROOT, data_root=DATA_ROOT, out_dir=out, page_built_at=BUILT_AT)
    dirty: list[str] = []
    for path in pages:
        walker = _Walker()
        walker.feed(path.read_text(encoding="utf-8"))
        if walker.bad:
            dirty.append(f"{path.name}: {walker.bad[:3]}")
    assert dirty == [], dirty


def test_analyst_explain_passes_section_id_then_label() -> None:
    js = (ROOT / "templates" / "macro_command.js").read_text(encoding="utf-8")
    assert "window.MMBrain.explain(sectionId, label)" in js
    assert "window.MMBrain.explain(label, label)" not in js


def test_implication_contra_block_is_gone() -> None:
    shell = (ROOT / "templates" / "_macro_suite_shell.html.j2").read_text(encoding="utf-8")
    assert "mq-implication-contra" not in shell
    assert "item.contradictions" not in shell


def test_evidence_drawer_has_one_sources_heading_and_distinct_title() -> None:
    shell = (ROOT / "templates" / "_macro_suite_shell.html.j2").read_text(encoding="utf-8")
    assert "t('Source receipt', '来源凭据')" in shell
    assert "t('Evidence', '证据')" in shell
    assert shell.count("t('Sources', '数据来源')") == 1


def test_clearance_probe_js_binds_locator_element_then_arg() -> None:
    """Playwright locator.evaluate calls fn(element, arg). A one-arg
    function reads the HTMLElement and scores ok on zero text nodes."""
    from scripts.capture_macro_command_p5 import _CLEARANCE_JS
    assert _CLEARANCE_JS.lstrip().startswith("async (el, arg)")
    assert "texts.length > 0" in _CLEARANCE_JS
    assert "maxScrollAtCheck" in _CLEARANCE_JS
    assert "fonts.ready" in _CLEARANCE_JS
    assert "requestAnimationFrame" in _CLEARANCE_JS
    assert "mergedInto" in _CLEARANCE_JS
    assert "NodeFilter.SHOW_TEXT" in _CLEARANCE_JS
    assert "querySelectorAll('*')" in _CLEARANCE_JS
    assert "no_occluders_found" in _CLEARANCE_JS
    assert "mmbBootDisplay" in _CLEARANCE_JS
    assert "clipView" in _CLEARANCE_JS
    assert "scroll_under_top_chrome" in _CLEARANCE_JS
    assert "closest('.mc-rail, .mq-suitenav')" in _CLEARANCE_JS
    assert ".mc-rail, .mc-rail-list" not in _CLEARANCE_JS
    assert "position > 0" not in _CLEARANCE_JS
    assert "exposedAtScrollY" in _CLEARANCE_JS
    assert "top-chrome-full-cover-unexposable" in _CLEARANCE_JS


def test_capture_relocated_needles_are_locale_visible_and_must_be_inside() -> None:
    """M2 / B3: 15/16 probe strings exist on the rates page and live in details."""
    from scripts.capture_macro_command_p5 import RELOCATED_EN, RELOCATED_ZH
    html = (ROOT / "site" / "macro_rates_curves.html").read_text(encoding="utf-8")
    assert "This page publishes no dual-axis" in html
    for needle in RELOCATED_EN:
        assert needle in html
        assert needle not in guard.reading_path_text(html)
    for needle in RELOCATED_ZH:
        assert needle in html
        assert needle not in guard.reading_path_text(html)


def test_analyst_is_last_rail_child_and_not_fixed_at_768() -> None:
    hub = (ROOT / "templates" / "macro_monetary.html.j2").read_text(encoding="utf-8")
    rail_end = hub.index("</nav>")
    rail = hub[hub.index('<nav class="mc-rail"'):rail_end]
    assert rail.index("mc-rail-list") < rail.index("mc-analyst")
    css = (ROOT / "templates" / "macro_command.css").read_text(encoding="utf-8")
    mobile = css.split("@media (max-width: 768px)")[1].split("@media (max-width: 480px)")[0]
    assert "position: fixed" not in mobile
    assert "position: static" in mobile
    assert "84px + 16px + 16px + 16px" not in css
    assert "84px + 44px + 16px" not in css


def test_clearance_probe_ok_fails_on_empty_or_hits() -> None:
    from scripts.capture_macro_command_p5 import clearance_probe_ok
    assert clearance_probe_ok({}) is False
    assert clearance_probe_ok({"text_count": 0, "intersections": [], "ok": True}) is False
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [{"text": "x"}], "ok": True,
        "occluders": [{"position": "sticky"}],
    }) is False
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [], "at_max": True,
        "maxScrollMatched": False, "ok": True,
        "occluders": [{"position": "sticky"}],
    }) is False
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [], "analyst_hits": [],
        "at_max": True, "maxScrollMatched": True, "ok": True,
        "occluders": [{"position": "sticky"}], "width": 390,
    }) is True
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [], "analyst_hits": [],
        "ok": True, "occluders": [], "width": 390,
    }) is False
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [], "analyst_hits": [],
        "ok": True, "occluders": [], "width": 1440,
    }) is False
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [], "analyst_hits": [],
        "scrollMatched": False, "ok": True,
        "occluders": [{"position": "sticky"}], "width": 390,
    }) is False


def test_p5_manifest_viewport_identity() -> None:
    import json
    from pathlib import Path as _Path
    manifest_path = ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json"
    if not manifest_path.is_file():
        pytest.skip("P5 evidence manifest is not in this checkout")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dirty: list[str] = []
    for page in manifest.get("pages") or []:
        for state in page.get("states") or []:
            if not state.get("captured"):
                continue
            name = state.get("file")
            dpr = float(state.get("dpr") or 0)
            css = state.get("viewport_css_width")
            width = state.get("width")
            declared = state.get("viewport_width")
            if not dpr or css is None or width is None:
                dirty.append(f"{name}: missing dpr/viewport_css_width/width")
                continue
            expected = width / dpr
            if abs(float(css) - expected) > 0.51:
                dirty.append(f"{name}: css {css} != ihdr {width}/{dpr}")
            if abs(float(declared) - expected) > 0.51:
                dirty.append(f"{name}: viewport_width {declared} != {expected}")
            if state.get("crop"):
                if not state.get("selector"):
                    dirty.append(f"{name}: crop without selector")
            png = manifest_path.parent / name
            if png.is_file():
                data = png.read_bytes()
                ihdr_w = int.from_bytes(data[16:20], "big")
                if ihdr_w != width:
                    dirty.append(f"{name}: recorded width {width} != IHDR {ihdr_w}")
    orphan = manifest_path.parent / "16-light-en-1440.png"
    if orphan.is_file():
        dirty.append("orphan 16-light-en-1440.png still committed")
    assert dirty == [], dirty


def test_top_chrome_cover_uses_document_geometry() -> None:
    """R1: inside the stuck zone is a hit; below is excused against the
    re-measured max. A stale past-max that fits maxScrollAtCheck is not
    a hit; one that survives the re-measure is."""
    from scripts.capture_macro_command_p5 import (
        classify_top_chrome_cover, _CLEARANCE_JS,
    )
    inside = classify_top_chrome_cover(
        doc_top=40, ov_bottom=60, max_scroll_at_check=800)
    assert inside["hit"] is True
    assert inside["reason"] == "top-chrome-full-cover-unexposable"
    below = classify_top_chrome_cover(
        doc_top=200, ov_bottom=60, max_scroll_at_check=800)
    assert below["hit"] is False
    assert below["exposedAtScrollY"] == 140
    stale = classify_top_chrome_cover(
        doc_top=900, ov_bottom=60, max_scroll_at_check=1200)
    assert stale["hit"] is False
    assert stale["maxScrollAtCheck"] == 1200
    survives = classify_top_chrome_cover(
        doc_top=900, ov_bottom=60, max_scroll_at_check=800)
    assert survives["hit"] is True
    assert survives["reason"] == "top-chrome-full-cover-unexposable"
    assert "position > 0" not in _CLEARANCE_JS
    assert "target ===" not in _CLEARANCE_JS
    assert "slop" not in _CLEARANCE_JS


def test_five_pages_have_one_analyst_entry_and_nojs_fallback(tmp_path_factory) -> None:
    """MA3: each of the five pages has exactly one analyst entry;
    mountable=False emits <a href="chat.html">."""
    from jinja2 import Environment, FileSystemLoader, StrictUndefined

    pages = builder.render(ROOT, data_root=DATA_ROOT,
                           out_dir=tmp_path_factory.mktemp("analyst") / "site",
                           page_built_at=BUILT_AT)
    wanted = {name: None for name in FIVE_COMMAND_PAGES}
    for path in pages:
        if path.name in wanted:
            wanted[path.name] = path.read_text(encoding="utf-8")
    missing = [name for name, html in wanted.items() if html is None]
    assert not missing, missing
    for name, html in wanted.items():
        openings = len(re.findall(
            r'<(?:a|button)\b[^>]*class="[^"]*\bmc-analyst[\s"]', html))
        assert openings == 1, (name, openings)
        assert 'href="chat.html"' in html
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=True, undefined=StrictUndefined)
    nav = env.get_template("_macro_suite_nav.html.j2")
    # Render the macro with mountable=False via a thin wrapper.
    rendered = env.from_string(
        '{% import "_macro_suite_nav.html.j2" as suitenav %}'
        '{{ suitenav.suite_bar(nav, analyst) }}'
    ).render(
        nav={"hub": {"href": "macro_monetary.html"}, "entries": []},
        analyst={"mountable": False},
    )
    assert "<button" not in rendered
    assert re.search(r'<a[^>]*class="[^"]*\bmc-analyst\b[^>]*href="chat\.html"',
                     rendered) or re.search(
        r'<a[^>]*href="chat\.html"[^>]*class="[^"]*\bmc-analyst\b', rendered)


def test_e6_on_five_pages_matches_p4_v6_slots(tmp_path_factory) -> None:
    """R4: verify P4's five E6 slots at this head; do not rewrite them."""
    from lib import macro_suite_labels as labels
    from tests.test_macro_command_empty_states import _render_empty

    spec = labels.EMPTY_STATES["e6"]
    assert spec["title"]["en"] == "Included in a higher plan"
    assert spec["title"]["zh"] == "包含在更高方案中"
    assert spec["stance"]["en"] == "The reading is available on upgrade."
    assert spec["stance"]["zh"] == "升级后可查看该读数。"
    assert spec["why"]["en"] == "This section is part of {plan}."
    assert spec["why"]["zh"] == "本板块属于{plan}。"
    assert spec["unlock"]["en"] == "See it with an upgrade."
    assert spec["unlock"]["zh"] == "升级即可查看。"
    assert spec["cta_label"]["en"] == "Upgrade to see it"
    assert spec["cta_label"]["zh"] == "查看升级方案"
    rendered = _render_empty(builder._empty_state("e6", plan="Research"))
    assert "Included in a higher plan" in rendered
    assert "包含在更高方案中" in rendered
    assert "See it with an upgrade." in rendered
    assert "升级即可查看。" in rendered
    assert "This section is part of Research." in rendered
    assert "本板块属于Research。" in rendered
    assert "Upgrade to see it" in rendered
    assert "查看升级方案" in rendered
    assert "This section is included in a higher plan." not in rendered
    assert "本板块包含在更高方案中。" not in rendered
    assert rendered.count("Included in a higher plan") == 1
    assert "Read this section closely" not in rendered
    assert "请先仔细读本板块" not in rendered
    from lib.macro_suite_labels import EMPTY_STATES as LIVE
    assert LIVE["e6"]["cta_label"]["zh"] == "查看升级方案"
    pages = builder.render(
        ROOT, data_root=DATA_ROOT,
        out_dir=tmp_path_factory.mktemp("e6five") / "site",
        page_built_at=BUILT_AT)
    names = {path.name for path in pages}
    assert set(FIVE_COMMAND_PAGES) <= names


def test_e5_is_not_a_workspace_declared_state() -> None:
    """R2: workspace pages cannot enter E5; hub can."""
    from scripts.capture_macro_command_p5 import (
        declared_cells, e5_applicability_for_html, WORKSPACE_PAGES,
    )
    declared = declared_cells()
    assert "e5-dark-en-1440.png" in declared
    for page in WORKSPACE_PAGES:
        slug = page.replace(".html", "")
        assert not any(name.startswith(f"e5-{slug}") for name in declared)
        assert f"empty-e5-{slug}" not in "".join(declared)
    for page in WORKSPACE_PAGES:
        path = ROOT / "site" / page
        if not path.is_file():
            pytest.skip("site/ omitted")
        receipt = e5_applicability_for_html(path.read_text(encoding="utf-8"))
        assert receipt == {"fragments": False, "template": False}, (page, receipt)
    hub = ROOT / "site" / "macro_monetary.html"
    if hub.is_file():
        receipt = e5_applicability_for_html(hub.read_text(encoding="utf-8"))
        assert receipt["fragments"] is True
        assert receipt["template"] is True


def test_p5_element_shot_imports_p3_device_span() -> None:
    """R3: P5 uses P3's exact _device_px span; no 4-px slop."""
    from scripts import capture_macro_command_p5 as p5
    from scripts.capture_macro_command_p3 import _device_px, _write_element_shot
    assert p5._device_px is _device_px
    assert p5._write_element_shot is _write_element_shot
    src = (ROOT / "scripts" / "capture_macro_command_p5.py").read_text(
        encoding="utf-8")
    assert "slop=4" not in src
    assert "slop: int" not in src


def test_copy_guard_keeps_details_summary() -> None:
    """m-b: <summary> text is in the reading path; the body is not."""
    html = (
        '<details class="mc-details">'
        "<summary>How this is calculated 1.25 score (0-100)</summary>"
        "<div>hysteresis snapshot producer</div>"
        "</details>"
    )
    text = guard.reading_path_text(html)
    assert "How this is calculated" in text
    assert "1.25 score (0-100)" in text
    assert "hysteresis snapshot" not in text


def test_declared_cells_minus_captured_is_gaps() -> None:
    from scripts.capture_macro_command_p5 import declared_cells
    declared = declared_cells()
    captured = set(declared)
    assert sorted(set(declared) - captured) == []
    assert "01-dark-en-1440-full.png" in declared
    assert "09-dark-en-390.png" in declared
    assert "ws-macro_rates_curves-closed-dark-en-1440.png" in declared


def test_committed_manifest_gaps_equal_declared_minus_captured() -> None:
    """Tests recompute gaps and IHDR equalities from the committed manifest."""
    import json
    from scripts.capture_macro_command_p5 import declared_cells

    manifest_path = ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json"
    probes_path = ROOT / "mockups" / "evidence" / "macro-command-p5" / "probes.json"
    if not manifest_path.is_file():
        pytest.skip("P5 evidence manifest is not in this checkout")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    probes = json.loads(probes_path.read_text(encoding="utf-8"))
    if "declared_cells" not in probes:
        pytest.skip("r4 recapture has not written declared_cells yet")
    captured = {
        st["file"]
        for page in manifest.get("pages") or []
        for st in page.get("states") or []
        if st.get("captured") and st.get("file")
    }
    expected = sorted(set(declared_cells()) - captured)
    recorded = [
        row["file"] for row in (probes.get("gaps") or [])
        if isinstance(row, dict) and row.get("reason") == "declared minus captured"
    ]
    assert recorded == expected
    assert manifest.get("tree_clean_start") is True
    assert manifest.get("tree_clean_end") is True
    for page in manifest.get("pages") or []:
        for state in page.get("states") or []:
            if not state.get("captured"):
                continue
            dpr = float(state.get("dpr") or 0)
            assert dpr > 0, state.get("file")
            png = manifest_path.parent / state["file"]
            if not png.is_file():
                continue
            ihdr_w = int.from_bytes(png.read_bytes()[16:20], "big")
            assert ihdr_w == state["width"], state.get("file")
            fixture = state.get("fixture")
            assert fixture == "builder-payload" or (
                isinstance(fixture, str) and fixture.endswith((".json", ".html"))
            ), (state.get("file"), fixture)
