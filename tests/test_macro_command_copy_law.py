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
     "Reads the policy-corridor series only."),
    ("macro_financial_conditions.html",
     "Shared drivers this week: the policy rate and the central-bank balance sheet."),
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


def test_machine_copy_hits_catch_braces_snake_parquet_and_rule_ids() -> None:
    """E-m1: painted locale spans may not leak slugs, parquets, or study ids."""
    assert "braces" in guard.machine_copy_hits(
        "closed to exactly {rate_side, balance_sheet} (R1A's")
    assert "snake:rate_side" in guard.machine_copy_hits(
        "closed to exactly {rate_side, balance_sheet} (R1A's")
    assert "rule:R1A" in guard.machine_copy_hits(
        "closed to exactly {rate_side, balance_sheet} (R1A's")
    assert "parquet" in guard.machine_copy_hits(
        "Reads the policy-corridor parquets only")
    assert guard.machine_copy_hits(
        "Shared drivers this week: the policy rate and the central-bank "
        "balance sheet.") == []
    assert guard.machine_copy_hits(
        "Reads the policy-corridor series only.") == []


def test_copy_guard_defaults_to_every_suite_page_and_hub() -> None:
    """n1: no-arg invocation scans the Macro Command hub (macro_monetary.html) + the 14 suite pages."""
    from scripts.build_macro_suite_pages import HUB_PAGE, SUITE_PAGES
    from scripts.check_macro_command_copy import default_targets
    names = {path.name for path in default_targets()}
    expected = {HUB_PAGE.output} | {page.output for page in SUITE_PAGES}
    assert names == expected
    assert len(names) >= 15


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
        # v11: internal producer receipts are not rendered in Details.
        assert needle not in html, name


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
    """n2: run the shipped _CLEARANCE_JS against synthetic DOM."""
    from scripts.capture_macro_command_p5 import (
        _CLEARANCE_JS, decide_analyst_merge, assert_merged_geometry,
    )
    assert _CLEARANCE_JS.lstrip().startswith("async (el, arg)")
    rail = {"top": 0, "bottom": 80, "left": 0, "right": 300}
    inside = {"top": 10, "bottom": 40, "left": 20, "right": 80}
    row = decide_analyst_merge(
        inside, rail, dom_descendant=True, analyst_in_viewport=True)
    assert row["analystMergedInto"] == "rail"
    assert row["mergeBasis"] == "geometry"
    assert_merged_geometry(row)
    outside = {"top": 400, "bottom": 430, "left": 20, "right": 80}
    with pytest.raises(RuntimeError, match="analyst-merge-dom-not-geometry"):
        decide_analyst_merge(
            outside, rail, dom_descendant=True, analyst_in_viewport=True,
            overlaps_rail=False)
    off = decide_analyst_merge(
        outside, rail, dom_descendant=True, analyst_in_viewport=False)
    assert off["analystMergedInto"] is None
    assert off["analystOffViewport"] is True
    overlap = {"top": 60, "bottom": 110, "left": 20, "right": 80}
    overlap_row = decide_analyst_merge(
        overlap, rail, dom_descendant=True, analyst_in_viewport=True,
        overlaps_rail=True, viewport_width=390)
    assert overlap_row["analystMergedInto"] is None
    assert overlap_row["analystOffViewport"] is False
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed")
    try:
        playwright_cm = sync_playwright().start()
    except Exception as exc:
        pytest.skip(f"Playwright runtime unavailable: {exc}")
    try:
        try:
            browser = playwright_cm.chromium.launch(headless=True, channel="chrome")
        except Exception:
            try:
                browser = playwright_cm.chromium.launch(headless=True)
            except Exception as exc:
                pytest.skip(f"Chromium unavailable: {exc}")
        page = browser.new_page(viewport={"width": 390, "height": 844})
        try:
            page.set_content(
                """<!doctype html><html><body style="margin:0">
                <nav class="mq-suitenav" id="suitenav"
                     style="position:sticky;top:0;height:80px;width:300px;
                            background:#333;color:#fff">
                  <a class="mc-analyst" href="chat.html"
                     style="position:relative;top:400px;display:block;
                            width:80px;height:30px;background:#f00">Ask</a>
                </nav>
                <p class="mc-stance" style="margin-top:400px">Body stance</p>
                <p>Body text that the chip will overlay</p>
                </body></html>"""
            )
            with pytest.raises(Exception, match="analyst-merge-dom-not-geometry"):
                page.locator("html").evaluate(_CLEARANCE_JS, {"position": 0.0})
            page.set_content(
                """<!doctype html><html><body style="margin:0">
                <nav class="mq-suitenav" id="suitenav"
                     style="position:sticky;top:0;height:80px;width:360px;
                            background:#333;color:#fff">
                  <a class="mc-analyst" href="chat.html"
                     style="display:block;width:80px;height:30px;
                            margin:10px">Ask</a>
                </nav>
                <p class="mc-stance">Body stance</p>
                <p>Body text below the rail</p>
                </body></html>"""
            )
            inside_row = page.locator("html").evaluate(
                _CLEARANCE_JS, {"position": 0.0})
            assert inside_row["analystMergedInto"] == "rail"
            assert inside_row["mergeBasis"] == "geometry"
            assert_merged_geometry(inside_row)
            page.set_content(
                """<!doctype html><html><body style="margin:0">
                <nav class="mq-suitenav" id="suitenav"
                     style="position:sticky;top:0;height:80px;width:360px;
                            background:#333;color:#fff">
                  <a class="mc-analyst" href="chat.html"
                     style="position:absolute;top:50px;left:20px;
                            width:80px;height:40px;background:#f00">Ask</a>
                </nav>
                <p style="position:absolute;top:70px;left:20px;width:80px">
                  HITTEXT</p>
                </body></html>"""
            )
            overlap_js = page.locator("html").evaluate(
                _CLEARANCE_JS, {"position": 0.0})
            assert overlap_js["analystMergedInto"] in (None, "")
            assert overlap_js["analystOffViewport"] is False
            assert overlap_js["analyst_hits"], overlap_js
        finally:
            browser.close()
    finally:
        playwright_cm.stop()


def test_capture_relocated_needles_are_locale_visible_and_must_be_inside() -> None:
    """M2 / B3: probe strings exist on the rates page and live in details."""
    from scripts.capture_macro_command_p5 import RELOCATED_EN, RELOCATED_ZH
    html = (ROOT / "site" / "macro_rates_curves.html").read_text(encoding="utf-8")
    assert "mc-producer-receipt" not in html
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
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [], "analyst_hits": [],
        "ok": True, "occluders": [{"position": "sticky"}], "width": 1440,
        "mmbBootInDom": True, "mmbBootVisible": True,
        "mmbBootBox": {"left": 1216, "right": 1418},
        "fabGutterTextPx": 40, "fabGutterPx": 40, "fabRightMarginPx": 22,
    }) is True
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [], "analyst_hits": [],
        "ok": True, "occluders": [{"position": "sticky"}], "width": 1440,
        "mmbBootInDom": True, "mmbBootVisible": True,
        "mmbBootBox": {"left": 1216, "right": 1418},
        "fabGutterTextPx": None,
        "gutterBasis": {"kind": "no-text-in-fab-band"},
        "fabRightMarginPx": 22,
    }) is True
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [], "analyst_hits": [],
        "ok": True, "occluders": [{"position": "sticky"}], "width": 1440,
        "mmbBootInDom": True, "mmbBootVisible": True,
        "mmbBootBox": {"left": 1216, "right": 1418},
        "fabGutterTextPx": -12, "fabRightMarginPx": 22,
    }) is False
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [], "analyst_hits": [],
        "ok": True, "occluders": [{"position": "sticky"}], "width": 1440,
    }) is False
    assert clearance_probe_ok({
        "text_count": 3, "intersections": [], "analyst_hits": [],
        "ok": True, "occluders": [{"position": "sticky"}], "width": 1440,
        "fabAbsentReason": "not-in-dom",
    }) is True


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
            if declared not in (390, 768, 1440):
                dirty.append(f"{name}: viewport_width {declared} not a declared render width")
            if state.get("crop"):
                if not state.get("selector"):
                    dirty.append(f"{name}: crop without selector")
                if state.get("crop_width") is None:
                    dirty.append(f"{name}: crop missing crop_width")
            elif abs(float(declared) - expected) > 0.51:
                dirty.append(f"{name}: viewport_width {declared} != {expected}")
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
    """M2: E5 cells are derived from e5_applicability; missing file raises."""
    from pathlib import Path as _Path
    from scripts.capture_macro_command_p5 import (
        declared_cells, e5_applicability_for_html, e5_applicability_for_site,
        WORKSPACE_PAGES, FIVE_PAGES, HUB_PAGE,
    )
    with pytest.raises(RuntimeError, match="missing html"):
        e5_applicability_for_html("")
    with pytest.raises(RuntimeError, match="missing site file"):
        e5_applicability_for_site(_Path("/no/such/macro_page.html"))
    appl = {
        HUB_PAGE: {"fragments": True, "template": True},
    }
    for page in WORKSPACE_PAGES:
        appl[page] = {"fragments": False, "template": False}
    declared = declared_cells(appl)
    assert "e5-dark-en-1440.png" in declared
    for page in WORKSPACE_PAGES:
        slug = page.replace(".html", "")
        assert not any(name.startswith(f"e5-{slug}") for name in declared)
    mutated = dict(appl)
    mutated[WORKSPACE_PAGES[0]] = {"fragments": True, "template": True}
    mutated_declared = declared_cells(mutated)
    slug = WORKSPACE_PAGES[0].replace(".html", "")
    assert f"e5-{slug}-dark-en-1440.png" in mutated_declared
    assert "e5-dark-en-1440.png" in mutated_declared
    flipped = dict(appl)
    flipped[HUB_PAGE] = {"fragments": False, "template": False}
    flipped_declared = declared_cells(flipped)
    assert "e5-dark-en-1440.png" not in flipped_declared
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
    _ = FIVE_PAGES


def test_p5_element_shot_imports_p3_device_span() -> None:
    """E1: P5 calls P3 v16 producer unchanged; no local copy."""
    from scripts import capture_macro_command_p5 as p5
    from scripts.capture_macro_command_p3 import (
        _assert_shot_geometry, _device_px, _device_px_span_from_crop_box_doc,
        _write_element_shot,
    )
    assert p5._device_px is _device_px
    assert p5._write_element_shot is _write_element_shot
    assert p5._device_px_span_from_crop_box_doc is _device_px_span_from_crop_box_doc
    assert p5._assert_shot_geometry is _assert_shot_geometry
    src = (ROOT / "scripts" / "capture_macro_command_p5.py").read_text(
        encoding="utf-8")
    assert "slop=4" not in src
    assert "slop: int" not in src
    assert "def _write_element_shot" not in src


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
    assert any(name.startswith("chipmat-") for name in captured)
    expected = sorted(set(declared_cells(probes.get("e5_applicability"))) - captured)
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


def test_covered_rows_are_bounded_including_partial() -> None:
    """M3: every *_covered row is bound; an out-of-bound partial raises."""
    from scripts.capture_macro_command_p5 import _assert_excused_covers
    ok = {
        "maxScrollAtCheck": 800,
        "scroll_under_top_chrome": [{
            "reason": "rail_partially_covered",
            "docTop": 200, "ovBottom": 60,
            "exposedAtScrollY": 140, "maxScrollAtCheck": 800,
        }],
    }
    _assert_excused_covers(ok)
    bad = {
        "maxScrollAtCheck": 800,
        "scroll_under_top_chrome": [{
            "reason": "rail_partially_covered",
            "docTop": 10, "ovBottom": 80,
            "exposedAtScrollY": -70, "maxScrollAtCheck": 800,
        }],
    }
    with pytest.raises(RuntimeError, match="out of bound"):
        _assert_excused_covers(bad)


def test_chip_material_keys_include_both_locales() -> None:
    """M1 / m5: 48 workspace cells; hub is typed not-applicable."""
    from scripts.capture_macro_command_p5 import (
        CHIP_MATERIAL_WIDTHS, WORKSPACE_PAGES, declared_cell_rows,
        family_for, HUB_PAGE,
    )
    appl = {HUB_PAGE: {"fragments": True, "template": True}}
    for page in WORKSPACE_PAGES:
        appl[page] = {"fragments": False, "template": False}
    rows = declared_cell_rows(appl)
    chipmat = [row["file"] for row in rows if row["family"] == "chip_material"]
    assert len(chipmat) == 48
    assert len(set(chipmat)) == 48
    for page in WORKSPACE_PAGES:
        slug = page.replace(".html", "")
        for theme in ("dark", "light"):
            for locale in ("en", "zh"):
                for width in CHIP_MATERIAL_WIDTHS:
                    name = f"chipmat-{slug}-{theme}-{locale}-{width}.png"
                    assert name in chipmat
    assert not any("macro_monetary" in name for name in chipmat)
    assert family_for("chipmat-macro_rates_curves-dark-en-1440.png") == (
        "chip_material")


def test_synthetic_clearance_can_fail() -> None:
    """e2: classifier reports HIT on unexposable cover and a bounded partial."""
    from scripts.capture_macro_command_p5 import (
        classify_partial_cover, classify_top_chrome_cover,
    )
    full = classify_top_chrome_cover(
        doc_top=10.0, ov_bottom=80.0, max_scroll_at_check=800.0)
    assert full["hit"] is True
    assert full["exposedAtScrollY"] < 0
    partial = classify_partial_cover(
        doc_top=200.0, ov_bottom=60.0, max_scroll_at_check=800.0)
    assert partial["hit"] is False
    assert 0 <= partial["exposedAtScrollY"] <= partial["maxScrollAtCheck"]
    assert "hit" in classify_partial_cover(
        doc_top=10.0, ov_bottom=80.0, max_scroll_at_check=800.0)


def test_synthetic_clearance_receipts_never_emits_literal_classifier() -> None:
    """m1: no code path may emit source != classifier-on-synthetic-dom."""
    from scripts.capture_macro_command_p5 import synthetic_clearance_receipts
    src = (ROOT / "scripts" / "capture_macro_command_p5.py").read_text(
        encoding="utf-8")
    assert '"source": "classifier"' not in src
    assert "doc_top=200.0, ov_bottom=60.0, max_scroll_at_check=800.0" not in src
    try:
        synthetic_clearance_receipts()
    except RuntimeError as exc:
        assert "Playwright page" in str(exc)
    else:
        raise AssertionError("no-page path must raise")


def test_p5_committed_crops_span_recomputed_from_crop_box_doc() -> None:
    """E1: every committed crop span recomputes from crop_box_doc − scroll_y."""
    import json
    from scripts import capture_macro_command_p5 as capture

    manifest_path = ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json"
    if not manifest_path.is_file():
        pytest.skip("P5 evidence manifest is not in this checkout")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    crop_states = [
        st for page in manifest.get("pages") or []
        for st in page.get("states") or []
        if st.get("captured") and st.get("crop")
    ]
    assert crop_states, "committed manifest has no crop states"
    assert "crop_box_doc" in crop_states[0], crop_states[0]
    for page in manifest.get("pages") or []:
        for state in page.get("states") or []:
            if not state.get("captured"):
                continue
            assert state.get("family"), state.get("file")
            if state.get("crop"):
                assert state.get("crop_box_doc"), state.get("file")
                assert "scroll_y_at_shot" in state, state.get("file")
                assert state.get("element_text_head") is not None, state.get("file")
                assert "ihdr_delta_px" in state, state.get("file")
                recomputed = capture._device_px_span_from_crop_box_doc(
                    state["crop_box_doc"], float(state["scroll_y_at_shot"]),
                    float(state["dpr"]))
                assert state["device_px_span"] == recomputed, (
                    state.get("file"), state["device_px_span"], recomputed)
                delta = state.get("ihdr_delta_px") or {}
                assert delta.get("w", 99) <= 1, (state.get("file"), delta)
                assert delta.get("h", 99) <= 1, (state.get("file"), delta)
            else:
                assert "scroll_y_at_shot" in state, state.get("file")
                assert "innerWidth" in state and "innerHeight" in state, (
                    state.get("file"))


def test_p5_completeness_against_tree_not_manifest_self() -> None:
    """E6: captured − declared is empty over the tree listing."""
    import json
    import subprocess
    from scripts.capture_macro_command_p5 import declared_cells

    evidence = ROOT / "mockups" / "evidence" / "macro-command-p5"
    manifest_path = evidence / "manifest.json"
    probes_path = evidence / "probes.json"
    if not manifest_path.is_file() or not probes_path.is_file():
        pytest.skip("P5 evidence is not in this checkout")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    probes = json.loads(probes_path.read_text(encoding="utf-8"))
    appl = probes.get("e5_applicability")
    captured = {
        st["file"]
        for page in manifest.get("pages") or []
        for st in page.get("states") or []
        if st.get("captured") and st.get("file")
    }
    assert any(name.startswith("chipmat-") for name in captured)
    declared = set(declared_cells(appl))
    tree = {path.name for path in evidence.glob("*.png")}
    listed = subprocess.check_output(
        ["git", "ls-files", "mockups/evidence/macro-command-p5/*.png"],
        cwd=ROOT, text=True)
    git_pngs = {Path(line).name for line in listed.splitlines() if line.strip()}
    method_table = {n for n in captured if n.startswith("method_table_390_")}
    assert captured - declared - method_table == set()
    assert tree - captured == set()
    if git_pngs:
        assert git_pngs - captured == set()
    assert "14-light-zh-768.png" not in tree
    assert "i2-dark-en-390.png" not in tree
    from scripts.capture_macro_command_p5 import (
        CHIP_MATERIAL_WIDTHS, WORKSPACE_PAGES, _chipmat_collision_ratified,
        parse_chipmat_name,
    )
    expected_ws = {
        f"chip_material_{page.replace('.html', '')}_{theme}_{locale}_{width}"
        for page in WORKSPACE_PAGES
        for theme in ("dark", "light")
        for locale in ("en", "zh")
        for width in CHIP_MATERIAL_WIDTHS
    }
    chip_keys = [key for key in probes if key.startswith("chip_material_")]
    workspace_keys = [key for key in chip_keys if "macro_monetary" not in key]
    assert set(workspace_keys) == expected_ws
    locales = {key.split("_")[-2] for key in workspace_keys}
    assert locales == {"en", "zh"}
    for page in WORKSPACE_PAGES:
        slug = page.replace(".html", "")
        for theme in ("dark", "light"):
            for width in CHIP_MATERIAL_WIDTHS:
                en = probes[f"chip_material_{slug}_{theme}_en_{width}"]
                zh = probes[f"chip_material_{slug}_{theme}_zh_{width}"]
                en_label = en.get("chipLabel") or ""
                zh_label = zh.get("chipLabel") or ""
                en_width = ((en.get("analystBox") or {}).get("width")
                            or en.get("locale"))
                zh_width = ((zh.get("analystBox") or {}).get("width")
                            or zh.get("locale"))
                if en_label == zh_label and en_width == zh_width:
                    assert en.get("identicalToLocale")
                    assert en.get("identicalToLocaleReason")
                    continue
                assert en_label != zh_label or en_width != zh_width
                assert en.get("railInnerHtmlSha256")
                assert zh.get("railInnerHtmlSha256")
                assert en.get("cropDomSha256")
                assert zh.get("cropDomSha256")
                assert en.get("probeBeforeShot") is True
                assert zh.get("probeBeforeShot") is True
                assert en.get("chipSelector")
                assert en.get("siblingPillSelector")
                assert en.get("chipSelector") != en.get("siblingPillSelector")
                assert en.get("scrollResult", {}).get("ok") is True
                assert zh.get("scrollResult", {}).get("ok") is True
    chat_keys = [key for key in probes if key.startswith("chip_opens_chat_")]
    chat_rows = [probes[key] for key in chat_keys]
    assert len(chat_keys) == 40
    assert len(set(chat_keys)) == 40
    # Dark/light at the same page/locale/width are one identity. Timing and
    # painted boxes may fork the raw dict; v6's defect was one constant for
    # all 40. The honest pin is 20 (page, locale, width) identities.
    identities = {
        (row.get("page"), row.get("locale"), row.get("width"),
         row.get("ok"), row.get("openedBy"),
         (row.get("openState") or {}).get("selector"),
         (row.get("openState") or {}).get("visible"))
        for row in chat_rows
    }
    assert len(identities) == 20
    assert len({(row.get("page"), row.get("locale"), row.get("width"))
                for row in chat_rows}) == 20
    for row in chat_rows:
        assert "mmbRootBefore" in row and "mmbRootAfter" in row
        assert "urlBefore" in row and "urlAfter" in row
        assert row.get("openedBy") == "click"
        assert "openState" in row
        assert row["openState"].get("selector") == "#mmb-panel"
        assert row.get("ok") is True
        assert row["openState"].get("visible") is True
        assert "visibleAfterMs" in row
        # E-n1: top-level openClass is "open" iff #mmb-panel.open matched.
        if row["openState"].get("open"):
            assert row.get("openClass") == "open"
            assert row["openState"].get("openClass") == "open"
        else:
            assert row.get("openClass") is None
            assert row["openState"].get("openClass") is None
    for key, row in probes.items():
        if not key.startswith("e5_timeout_"):
            continue
        assert "requestSeenAtMs" in row and "cloneSeenAtMs" in row
        assert abs(float(row["elapsedMs"])
                   - (float(row["cloneSeenAtMs"]) - float(row["requestSeenAtMs"]))) < 1
    assert "clearance_1440_" not in json.dumps(probes)
    syn = probes.get("synthetic_clearance")
    assert syn
    assert syn["full_cover_unexposable"]["hit"] is True
    assert syn["partial_bounded"]["hit"] is False
    chipmat_files = [name for name in captured if name.startswith("chipmat-")]
    assert len(chipmat_files) == 48
    from scripts.capture_macro_command_p5 import (
        assert_chipmat_containment, chipmat_containment_holds,
    )
    contained = 0
    for key in workspace_keys:
        cell = probes[key]
        assert chipmat_containment_holds(cell), key
        assert_chipmat_containment(cell, key=key)
        head = str(cell.get("elementTextHead") or "")
        assert cell.get("chipLabel") in head, (key, head)
        contained += 1
    assert contained == 48
    by_sha: dict[str, list[str]] = {}
    for page in manifest.get("pages") or []:
        for state in page.get("states") or []:
            if not str(state.get("file") or "").startswith("chipmat-"):
                continue
            by_sha.setdefault(state.get("sha256"), []).append(state["file"])
    for files in by_sha.values():
        if len(files) < 2:
            continue
        assert _chipmat_collision_ratified(files, probes), files
        parsed = [parse_chipmat_name(name) for name in files]
        assert all(parsed)
        assert len({(row["theme"], row["locale"], row["width"]) for row in parsed}) == 1


def test_chip_opens_chat_ok_requires_visible_surface() -> None:
    """M1: a hidden mount is not an opened chat; a painted panel is."""
    from scripts.capture_macro_command_p5 import chat_visible_from_state
    hidden = {
        "present": True, "visible": False,
        "box": {"width": 0, "height": 0},
        "openState": {"selector": "#mmb-panel", "openClass": "open",
                      "open": False, "visible": False},
    }
    assert chat_visible_from_state(hidden) is False
    painted = {
        "present": True, "visible": False,
        "box": {"width": 0, "height": 0},
        "openState": {
            "selector": "#mmb-panel", "openClass": "open",
            "open": True, "visible": True,
            "box": {"width": 400, "height": 600},
        },
    }
    assert chat_visible_from_state(painted) is True


def test_chip_opens_chat_synthetic_hidden_mount_is_not_ok() -> None:
    """M1: click that mounts a hidden #mmb-root → ok:false; visible panel → ok."""
    from scripts.capture_macro_command_p5 import _run_chip_opens_chat
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed")
    try:
        playwright_cm = sync_playwright().start()
    except Exception as exc:
        pytest.skip(f"Playwright runtime unavailable: {exc}")
    try:
        try:
            browser = playwright_cm.chromium.launch(headless=True, channel="chrome")
        except Exception:
            try:
                browser = playwright_cm.chromium.launch(headless=True)
            except Exception as exc:
                pytest.skip(f"Chromium unavailable: {exc}")
        page = browser.new_page(viewport={"width": 390, "height": 844})
        try:
            page.set_content(
                """<!doctype html><html><body>
                <a class="mc-analyst" data-mc-analyst href="#">Ask</a>
                <script>
                document.querySelector('.mc-analyst').addEventListener('click', function (e) {
                  e.preventDefault();
                  var root = document.createElement('div');
                  root.id = 'mmb-root';
                  root.style.cssText = 'position:fixed;width:0;height:0;visibility:hidden';
                  document.body.appendChild(root);
                });
                </script></body></html>"""
            )
            hidden = _run_chip_opens_chat(
                page, page_name="synthetic.html", locale="en", width=390)
            assert hidden["ok"] is False
            assert hidden["mmbRootAfter"]["present"] is True
            assert hidden["mmbRootAfter"]["visible"] is False
            page.set_content(
                """<!doctype html><html><body>
                <a class="mc-analyst" data-mc-analyst href="#">Ask</a>
                <script>
                document.querySelector('.mc-analyst').addEventListener('click', function (e) {
                  e.preventDefault();
                  var root = document.createElement('div');
                  root.id = 'mmb-root';
                  var panel = document.createElement('div');
                  panel.id = 'mmb-panel';
                  panel.className = 'open';
                  panel.style.cssText = 'position:fixed;right:10px;bottom:10px;'
                    + 'width:200px;height:200px;background:#111;color:#fff';
                  panel.textContent = 'chat';
                  root.appendChild(panel);
                  document.body.appendChild(root);
                });
                </script></body></html>"""
            )
            shown = _run_chip_opens_chat(
                page, page_name="synthetic.html", locale="en", width=390)
            assert shown["ok"] is True
            assert shown["openState"]["visible"] is True
            assert shown["visibleAfterMs"] is not None
        finally:
            browser.close()
    finally:
        playwright_cm.stop()


def test_chipmat_capture_does_not_inject_or_expand() -> None:
    """M2: no title-pill injection and no rail expansion helper remains."""
    src = (ROOT / "scripts" / "capture_macro_command_p5.py").read_text(
        encoding="utf-8")
    assert "data-mc-chipmat-title" not in src
    assert "_EXPAND_RAIL_JS" not in src
    assert "is-current" not in src or "mq-suitenav-pill is-current" not in src


def test_chipmat_collision_same_bytes_different_dom_raises() -> None:
    """E-m2: identical PNG bytes with different cropDomSha256 are not ratified."""
    from scripts.capture_macro_command_p5 import _chipmat_collision_ratified
    box = {"left": 10, "right": 80, "top": 4, "bottom": 40}
    probes = {
        "chip_material_macro_rates_curves_dark_en_390": {
            "cropDomSha256": "aaa",
            "analystBox": box, "siblingPillBox": box, "cropBox": box,
            "chipmatPairFits": True,
        },
        "chip_material_macro_financial_conditions_dark_en_390": {
            "cropDomSha256": "bbb",
            "analystBox": box, "siblingPillBox": box, "cropBox": box,
            "chipmatPairFits": True,
        },
    }
    files = [
        "chipmat-macro_rates_curves-dark-en-390.png",
        "chipmat-macro_financial_conditions-dark-en-390.png",
    ]
    assert _chipmat_collision_ratified(files, probes) is False


def test_chipmat_collision_same_bytes_same_dom_allowed() -> None:
    """E-m3: identical PNG bytes with matching cropDomSha256 + allowlist pass."""
    from scripts.capture_macro_command_p5 import _chipmat_collision_ratified
    box = {"left": 10, "right": 80, "top": 4, "bottom": 40}
    cell = {
        "cropDomSha256": "same-hash",
        "analystBox": box, "siblingPillBox": box, "cropBox": box,
        "chipmatPairFits": True,
    }
    # Cross-page pair listed in chipmat_identical_allowlist.yml.
    probes_ok = {
        "chip_material_macro_business_activity_dark_zh_390": dict(cell),
        "chip_material_macro_financial_conditions_dark_zh_390": dict(cell),
    }
    files_ok = [
        "chipmat-macro_business_activity-dark-zh-390.png",
        "chipmat-macro_financial_conditions-dark-zh-390.png",
    ]
    assert _chipmat_collision_ratified(files_ok, probes_ok) is True
    # Cross-page pair NOT on the allowlist must fail.
    probes_bad = {
        "chip_material_macro_rates_curves_dark_en_390": dict(cell),
        "chip_material_macro_financial_conditions_dark_en_390": dict(cell),
    }
    files_bad = [
        "chipmat-macro_rates_curves-dark-en-390.png",
        "chipmat-macro_financial_conditions-dark-en-390.png",
    ]
    assert _chipmat_collision_ratified(files_bad, probes_bad) is False


def test_synthetic_partial_binds_from_dom() -> None:
    """m1: classifier-on-synthetic-dom numbers come from a covering paragraph."""
    from scripts.capture_macro_command_p5 import (
        classify_partial_cover, synthetic_clearance_receipts,
    )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed")
    try:
        playwright_cm = sync_playwright().start()
    except Exception as exc:
        pytest.skip(f"Playwright runtime unavailable: {exc}")
    try:
        try:
            browser = playwright_cm.chromium.launch(headless=True, channel="chrome")
        except Exception:
            try:
                browser = playwright_cm.chromium.launch(headless=True)
            except Exception as exc:
                pytest.skip(f"Chromium unavailable: {exc}")
        page = browser.new_page(viewport={"width": 800, "height": 900})
        try:
            row = synthetic_clearance_receipts(page)
            assert row["source"] == "classifier-on-synthetic-dom"
            partial = row["partial_bounded"]
            assert partial["hit"] is False
            assert 0 <= partial["exposedAtScrollY"] <= partial["maxScrollAtCheck"]
            literal = classify_partial_cover(
                doc_top=200.0, ov_bottom=60.0, max_scroll_at_check=800.0)
            assert partial != literal
            assert abs(float(partial["maxScrollAtCheck"])
                       - float(row["maxScrollAtCheck"])) < 1
            assert float(row["maxScrollAtCheck"]) > 800
        finally:
            browser.close()
    finally:
        playwright_cm.stop()


@pytest.mark.needs_full_checkout("site")
def test_user_facing_numbers_have_no_machine_floats() -> None:
    """E-m3: rendered suite HTML never ships ≥4 fractional digits or e±."""
    from scripts.build_macro_suite_pages import HUB_PAGE, SECTIONS, SUITE_PAGES
    from lib.macro_suite_labels import (
        format_user_facing_number, format_user_facing_text,
    )
    assert format_user_facing_number(0.7084035025522297) == "0.71"
    assert format_user_facing_number(-0.21603351448561625) == "\u22120.22"
    assert format_user_facing_number(66.66666666666667, kind="percent") == "66.7%"
    rewritten = format_user_facing_text(
        "6-month momentum 0.7084035025522297, breadth 66.66666666666667")
    assert "0.7084035025522297" not in rewritten
    assert "0.71" in rewritten
    assert "66.7%" in rewritten
    pages = [HUB_PAGE.output] + [page.output for page in SUITE_PAGES]
    present = [name for name in pages if (ROOT / "site" / name).is_file()]
    assert len(present) >= 14, present
    hub = (ROOT / "site" / HUB_PAGE.output).read_text(encoding="utf-8")
    found_sections = [sec.id for sec in SECTIONS if sec.id in hub]
    assert len(found_sections) >= 12, found_sections
    for name in present:
        html = (ROOT / "site" / name).read_text(encoding="utf-8")
        assert guard.find_violations(html) == [], name


@pytest.mark.needs_full_checkout("site")
def test_zh_l_zh_spans_are_translated() -> None:
    """M1: every .l-zh on the Macro Command hub (macro_monetary.html) + the 14 suite pages is not ASCII-letters-only."""
    from scripts.build_macro_suite_pages import HUB_PAGE, SECTIONS, SUITE_PAGES
    ratified = {
        "US", "EU", "JP", "CN", "GB", "USD", "FRED", "SOFR", "TIPS", "OECD",
        "NBER", "FOMC", "VIX", "CPI", "HICP", "BLS", "GDP", "NFCI", "OFR",
        "ECB", "BOJ", "TGA", "WEI", "PMI", "HPI", "EFFR", "OBFR", "IORB",
        "SAAR", "NSA", "JOLTS", "NFP", "ADP", "PCE", "SEP",
        "bp", "pts", "%", "—", "Vix",
    }
    _CJK = re.compile(r"[\u3000-\u303f\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]")
    _LETTERS = re.compile(r"[A-Za-z]")
    pages = [HUB_PAGE.output] + [page.output for page in SUITE_PAGES]
    present = [name for name in pages if (ROOT / "site" / name).is_file()]
    assert len(present) >= 14, present
    hub = (ROOT / "site" / HUB_PAGE.output).read_text(encoding="utf-8")
    found_sections = [sec.id for sec in SECTIONS if sec.id in hub]
    assert len(found_sections) >= 12, found_sections
    scanned = 0
    raw_total = 0
    ascii_hits = []
    per_page: dict[str, int] = {}
    for name in present:
        html = (ROOT / "site" / name).read_text(encoding="utf-8")
        zh_spans = guard.locale_class_texts(html, "l-zh")
        raw = guard.raw_class_token_count(html, "l-zh")
        per_page[name] = len(zh_spans)
        scanned += len(zh_spans)
        raw_total += raw
        assert len(zh_spans) >= raw, (name, len(zh_spans), raw)
        for zh in zh_spans:
            text = re.sub(r"<[^>]+>", "", zh).strip()
            if not text or not _LETTERS.search(text):
                continue
            if text in ratified:
                continue
            if not _CJK.search(text):
                ascii_hits.append((name, text))
    assert scanned > 0
    assert scanned >= raw_total
    assert ascii_hits == [], ascii_hits


@pytest.mark.needs_full_checkout("site")
def test_locale_spans_have_no_machine_text() -> None:
    """E-m1: every visible text node on the Macro Command hub + 14 suite pages is plain."""
    from scripts.build_macro_suite_pages import HUB_PAGE, SECTIONS, SUITE_PAGES
    pages = [HUB_PAGE.output] + [page.output for page in SUITE_PAGES]
    present = [name for name in pages if (ROOT / "site" / name).is_file()]
    assert len(present) >= 14, present
    hub = (ROOT / "site" / HUB_PAGE.output).read_text(encoding="utf-8")
    found_sections = [sec.id for sec in SECTIONS if sec.id in hub]
    assert len(found_sections) >= 12, found_sections
    dirty = []
    for name in present:
        html = (ROOT / "site" / name).read_text(encoding="utf-8")
        for node in guard.visible_text_nodes(html):
            hits = guard.machine_copy_hits(
                node["text"], glance=node.get("glance") == "1")
            if hits:
                dirty.append(
                    f"{name}:{node.get('tag')}:{hits[:6]}:{node['text'][:80]}")
    assert dirty == [], dirty


def test_chipmat_containment_from_manifest_alone() -> None:
    """m2: 48/48 containment from manifest values, no probes, no offset."""
    import json
    from scripts.capture_macro_command_p5 import chipmat_containment_holds
    manifest_path = ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json"
    if not manifest_path.is_file():
        pytest.skip("P5 evidence manifest is not in this checkout")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contained = 0
    for page in manifest.get("pages") or []:
        for state in page.get("states") or []:
            if not str(state.get("file") or "").startswith("chipmat-"):
                continue
            assert state.get("coordSpace") in {"host-page", "iframe", "host"}, (
                state.get("file"), state.get("coordSpace"))
            assert isinstance(state.get("hostFrameOffset"), dict), state.get("file")
            assert "x" in state["hostFrameOffset"] and "y" in state["hostFrameOffset"]
            assert "host_scroll_y_at_shot" in state, state.get("file")
            assert state.get("viewport_width") in (390, 768, 1440), state.get("file")
            assert state.get("frameInnerWidth") in (390, 768, 1440), state.get("file")
            assert state.get("crop_width") is not None, state.get("file")
            assert state.get("analystBox"), state.get("file")
            assert state.get("siblingPillBox"), state.get("file")
            assert state.get("crop_box_doc"), state.get("file")
            assert chipmat_containment_holds(state), state.get("file")
            contained += 1
    assert contained == 48


def test_vector_move_pair_zero_and_nonzero_are_plain_words() -> None:
    from lib.macro_suite_labels import vector_move_pair
    x_axis = {"axis_id": "financial_conditions_level"}
    y_axis = {"axis_id": "financial_conditions_impulse"}
    zero = vector_move_pair(0, 0, x_axis, y_axis)
    assert zero["en"] == "No change on either axis this month."
    assert zero["zh"] == "本月两轴均无变化。"
    moved = vector_move_pair(0.4, -0.2, x_axis, y_axis)
    assert moved["en"] == "Tighter funding conditions, weaker tightening impulse."
    assert moved["zh"] == "融资条件收紧，收紧脉冲减弱。"
    assert "Moved on" not in moved["en"]
    assert "Δ" not in moved["en"] and "·" not in moved["en"]


def test_computation_refused_uses_e2_vocabulary() -> None:
    from lib.macro_suite_labels import EMPTY_STATES, NULL_REASON
    assert NULL_REASON["COMPUTATION_REFUSED"] == EMPTY_STATES["e2"]["title"]
    assert "Computation refused" not in NULL_REASON["COMPUTATION_REFUSED"]["en"]
    assert "拒绝计算" not in NULL_REASON["COMPUTATION_REFUSED"]["zh"]


@pytest.mark.needs_full_checkout("site")
def test_rendered_pages_use_ratified_null_vocabulary() -> None:
    """E-m2: no refused/refusal phrase on the Macro Command hub + 14 suite pages."""
    from scripts.build_macro_suite_pages import HUB_PAGE, SUITE_PAGES
    pages = [HUB_PAGE.output] + [page.output for page in SUITE_PAGES]
    banned = re.compile(r"refus(ed|al)|拒绝计算", re.I)
    hits = []
    for name in pages:
        path = ROOT / "site" / name
        if not path.is_file():
            continue
        html = path.read_text(encoding="utf-8")
        for node in guard.visible_text_nodes(html):
            if banned.search(node["text"]):
                hits.append(f"{name}:{node['text'][:80]}")
    assert hits == [], hits


@pytest.mark.needs_full_checkout("site")
def test_details_use_locale_pairing_not_lang_attributes() -> None:
    """M2: Details text uses .l-en/.l-zh; suite templates have no lang= locale switch."""
    from scripts.build_macro_suite_pages import HUB_PAGE, SUITE_PAGES
    suite_templates = list((ROOT / "templates").glob("macro_*.html.j2"))
    suite_templates.append(ROOT / "templates" / "_macro_suite_shell.html.j2")
    lang_hits = []
    for path in suite_templates:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(
                r"<(?!html\b)([a-zA-Z0-9:-]+)([^>]*\blang=(['\"])(en|zh)\3)",
                text):
            lang_hits.append(f"{path.name}:{match.group(0)[:80]}")
    assert lang_hits == [], lang_hits
    pages = [HUB_PAGE.output] + [page.output for page in SUITE_PAGES]
    present = [name for name in pages if (ROOT / "site" / name).is_file()]
    assert len(present) >= 14, present
    unpaired = []
    for name in present:
        path = ROOT / "site" / name
        if not path.is_file():
            continue
        html = path.read_text(encoding="utf-8")
        blocks = re.findall(
            r'<details class="mc-details"[^>]*>(.*?)</details>', html, re.S)
        for body in blocks:
            if "mq-drawer" in body:
                continue
            en = len(re.findall(r'\bl-en\b', body))
            zh = len(re.findall(r'\bl-zh\b', body))
            if en == 0 and zh == 0:
                continue
            if en != zh:
                unpaired.append(f"{name}:en={en}:zh={zh}")
    assert unpaired == [], unpaired


def test_machine_copy_hits_flag_glance_delta_notation() -> None:
    assert "delta_axis" in guard.machine_copy_hits("Δx 0 · Δy 0", glance=True)
    assert "dot_symbol_pair" in guard.machine_copy_hits("Δx 0 · Δy 0", glance=True)
    assert guard.machine_copy_hits("Δx 0 · Δy 0", glance=False) == []
    assert guard.machine_copy_hits(
        "No change on either axis this month.", glance=True) == []


_RATIFIED_ZH_ASCII = re.compile(
    r"\b(VIX|FRED|OFR|NFCI|CPI|GDP|SOFR|FOMC|HICP|TIPS|OECD|NBER|BLS|TGA|USD|US|EU|JP|CN|GB|ECB|BOJ|GLT|HY|IG|NAR|BEA|EIA)\b"
)
_REPEAT_TOKEN = re.compile(r"(\S{2,})\1")
COMPOSITION_DISCLOSURE_ROWS = (
    ("Weights law", "权重法则"),
    ("Transformation", "变换"),
    ("Frequency alignment", "频率对齐"),
    ("Revision behaviour", "修订行为"),
    ("Coverage floor", "覆盖下限"),
    ("Definition version", "定义版本"),
    ("Authority ceiling", "权限上限"),
)


def test_axis_move_clauses_cover_every_axis_and_direction() -> None:
    from lib.macro_suite_disclosure import (
        AXIS_MOVE_CLAUSES, axis_move_clause, payload_axis_ids, required_axis_ids,
    )
    from lib.macro_suite_labels import vector_move_pair
    emitted = payload_axis_ids(DATA_ROOT)
    table = set(required_axis_ids())
    missing = sorted(emitted - table)
    extra = sorted(table - emitted)
    assert missing == [], f"clause table missing emitted axis ids: {missing}"
    assert extra == [], (
        f"clause table has movement-only extras not emitted by builders: {extra}"
    )
    axes = required_axis_ids()
    assert axes, "clause table is empty"
    for axis_id in axes:
        for direction in ("up", "down", "flat"):
            clause = axis_move_clause(axis_id, direction)
            zh = clause["zh"]
            leftover = _RATIFIED_ZH_ASCII.sub("", zh)
            assert not re.search(r"[A-Za-z]", leftover), (axis_id, direction, zh)
            assert not _REPEAT_TOKEN.search(zh), (axis_id, direction, zh)
            assert "Moved on" not in clause["en"]
            assert clause["en"][0].isupper(), (axis_id, direction, clause["en"])
            assert (axis_id, direction) in AXIS_MOVE_CLAUSES
    zero = vector_move_pair(0, 0, {"axis_id": axes[0]}, {"axis_id": axes[1]})
    assert zero["en"] == "No change on either axis this month."
    assert zero["zh"] == "本月两轴均无变化。"
    moved = vector_move_pair(0.4, -0.2, {"axis_id": "funding_pressure"},
                             {"axis_id": "balance_sheet_support"})
    assert moved["en"][0].isupper()
    assert ", " in moved["en"]
    right = moved["en"].split(", ", 1)[1]
    assert right[0].islower() or right.split()[0] in {
        "GLT", "US", "CPI", "FRED", "OFR", "NFCI"}
    assert "Moved on" not in moved["en"]
    growth = vector_move_pair(0.4, -0.2, {"axis_id": "growth_momentum"},
                              {"axis_id": "growth_level_breadth"})
    assert growth["en"] == "Stronger growth momentum, narrower breadth."
    inflation = vector_move_pair(0.4, -0.2, {"axis_id": "inflation_impulse"},
                                 {"axis_id": "persistence_breadth"})
    assert inflation["en"] == "Faster price rises, across fewer categories."


def test_vector_axes_resolve_by_id_not_list_order() -> None:
    """M2: ids come from committed builder payloads; list order does not bind."""
    from lib.macro_suite_disclosure import resolve_vector_axes
    from lib.macro_suite_labels import vector_move_pair
    from lib.macro_suite_view import _headline
    import json
    for page in builder.SUITE_PAGES:
        path = DATA_ROOT / "workspaces" / page.workspace_id / page.region / "latest.json"
        snap = json.loads(path.read_text(encoding="utf-8"))
        items = list((snap.get("axes") or {}).get("items") or [])
        vector = (snap.get("headline") or {}).get("one_month_vector") or {}
        assert "x_axis_id" in vector and "y_axis_id" in vector, page.output
        if len(items) < 2:
            continue
        assert vector["x_axis_id"] and vector["y_axis_id"], page.output
        got_x, got_y = resolve_vector_axes(items, vector)
        assert got_x["axis_id"] == vector["x_axis_id"]
        assert got_y["axis_id"] == vector["y_axis_id"]
        swapped = list(reversed(items))
        again_x, again_y = resolve_vector_axes(swapped, vector)
        assert again_x["axis_id"] == got_x["axis_id"]
        assert again_y["axis_id"] == got_y["axis_id"]
        if vector.get("status") == "PRESENT":
            first = vector_move_pair(vector.get("dx"), vector.get("dy"), got_x, got_y)
            second = vector_move_pair(vector.get("dx"), vector.get("dy"), again_x, again_y)
            assert first == second
            view = _headline(snap, swapped)
            assert view["vector"]["x_axis_id"] == vector["x_axis_id"]
            assert view["vector"]["y_axis_id"] == vector["y_axis_id"]
            if view["vector"]["move"]:
                assert view["vector"]["move"] == first
    with pytest.raises(KeyError, match="missing required x_axis_id"):
        resolve_vector_axes(
            [{"axis_id": "a"}, {"axis_id": "b"}],
            {},
        )


def test_visible_text_parser_treats_void_elements_as_self_closing() -> None:
    html = (
        '<main class="mc-shell">'
        '<meta name="robots" hidden>'
        '<meta charset="utf-8">'
        "<p>engine.owner_field leak</p>"
        "</main>"
    )
    nodes = guard.visible_text_nodes(html)
    assert any("engine.owner_field leak" in (node.get("text") or "") for node in nodes)
    hits = guard.find_violations(html)
    assert any("snake" in hit or "machine-text" in hit for hit in hits), hits


def test_copy_guard_reports_allowlist_without_deleting_input() -> None:
    src = (ROOT / "scripts" / "check_macro_command_copy.py").read_text(
        encoding="utf-8")
    assert "text.replace(allowed, \"\")" not in src
    html = (
        '<main class="mc-shell">'
        "<p>No change on either axis this month.</p>"
        "</main>"
    )
    assert guard.find_violations(html) == []
    exceptions = guard.find_exceptions(html)
    assert any("No change on either axis this month." in item for item in exceptions)


COMPOSITE_COUNT_BY_PAGE = {
    "macro_monetary.html": 0,
    "macro_liquidity_regime.html": 2,
    "macro_growth_real_economy.html": 2,
    "macro_business_activity.html": 0,
    "macro_labor_markets.html": 2,
    "macro_inflation_system.html": 2,
    "macro_monetary_policy.html": 0,
    "macro_financial_conditions.html": 2,
    "macro_liquidity_central_banks.html": 0,
    "macro_capital_structure.html": 0,
    "macro_housing_real_estate.html": 0,
    "macro_consumer_payments.html": 2,
    "macro_national_debt_liabilities.html": 0,
    "macro_rates_curves.html": 0,
    "macro_trade_flows.html": 0,
}


@pytest.mark.needs_full_checkout("site")
def test_composites_disclose_composition_law_in_plain_words() -> None:
    """M1: every composite on the 15 pages paints the N disclosure rows, EN+ZH."""
    from scripts.build_macro_suite_pages import HUB_PAGE, SUITE_PAGES
    pages = [HUB_PAGE.output] + [page.output for page in SUITE_PAGES]
    present = [name for name in pages if (ROOT / "site" / name).is_file()]
    assert len(present) >= 14, present
    assert set(COMPOSITE_COUNT_BY_PAGE) == set(pages)
    missing: list[str] = []
    machine: list[str] = []
    for name in present:
        html = (ROOT / "site" / name).read_text(encoding="utf-8")
        blocks = re.findall(
            r'<div class="mc-details-body mq-axis-method">(.*?)</div>\s*</details>',
            html, re.S)
        assert len(blocks) == COMPOSITE_COUNT_BY_PAGE[name], (
            name, len(blocks), COMPOSITE_COUNT_BY_PAGE[name])
        for body in blocks:
            for en, zh in COMPOSITION_DISCLOSURE_ROWS:
                if en not in body:
                    missing.append(f"{name}: missing EN {en!r}")
                if zh not in body:
                    missing.append(f"{name}: missing ZH {zh!r}")
            wrapped = f"<div>{body}</div>"
            for node in guard.visible_text_nodes(wrapped):
                hits = guard.machine_copy_hits(node.get("text") or "")
                if hits:
                    machine.append(f"{name}:{hits}:{node.get('text','')[:80]}")
    assert missing == [], missing
    assert machine == [], machine


def test_lineage_note_kinds_render_distinct_facts() -> None:
    from lib.macro_suite_disclosure import (
        LINEAGE_NOTE_KIND_FACTS, classify_lineage_kind, lineage_note_pair,
    )
    samples = {
        "no_change_republication": (
            "Same reference period as the predecessor print; no source value changed "
            "(no-change republication)."
        ),
        "value_correction": (
            "Same reference period as the predecessor print, but one or more "
            "owner-native source values changed: this print supersedes the prior "
            "one as a revision."
        ),
        "reference_period_change": (
            "Reference period differs from the predecessor print (a new observation, "
            "not a revision of the same period); no correction asserted."
        ),
        "first_known": (
            "First-known snapshot for this owner input; predecessor recorded when "
            "a prior accepted print exists."
        ),
    }
    assert "source_swap" not in LINEAGE_NOTE_KIND_FACTS
    rendered: dict[str, str] = {}
    for kind, sample in samples.items():
        assert classify_lineage_kind(sample) == kind
        pair = lineage_note_pair(
            sample, effective_date="2026-09-04", prior_effective_date="2026-09-03")
        assert pair is not None
        rendered[kind] = pair["en"]
        assert LINEAGE_NOTE_KIND_FACTS[kind] in pair["en"], (kind, pair["en"])
        assert "4 Sep 2026" in pair["en"]
        assert pair["zh"]
    assert len(set(rendered.values())) == len(rendered)
    # Equal dates → single "both as of" clause (n1).
    same_dates = lineage_note_pair(
        samples["no_change_republication"],
        effective_date="2026-09-04", prior_effective_date="2026-09-04")
    assert same_dates is not None
    assert "Both as of 4 Sep 2026" in same_dates["en"]
    assert "This print is as of" not in same_dates["en"]
    with pytest.raises(KeyError, match="unknown lineage note kind"):
        classify_lineage_kind("engine.internal_revision_token v3")
    fallback = lineage_note_pair(
        "engine.internal_revision_token v3", effective_date="2026-09-04")
    assert fallback is not None
    assert "4 Sep 2026" in fallback["en"]
    assert "cannot summarise the correction note yet" in fallback["en"]
    assert "A correction note is on file" not in fallback["en"]


def test_producer_lineage_notes_map_to_real_kinds() -> None:
    """Every note string the 15 workspace producers can emit maps to a real kind."""
    import ast
    from pathlib import Path
    from lib.macro_suite_disclosure import (
        LINEAGE_NOTE_KIND_FACTS, classify_lineage_kind,
    )
    root = Path(__file__).resolve().parents[1] / "engine" / "market_os" / "macro_workspaces"
    notes: list[tuple[str, str]] = []
    for path in sorted(root.glob("*.py")):
        if path.name in {"__init__.py", "build.py", "contract.py", "registry.py", "consumer.py"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name != "_corrections":
                continue
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Dict):
                    continue
                for key, value in zip(sub.keys, sub.values):
                    if not (isinstance(key, ast.Constant) and key.value == "note"):
                        continue
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        notes.append((path.name, value.value))
    assert len(notes) >= 40, notes  # 14 producers × ≥3 branches
    producers = {name for name, _ in notes}
    assert len(producers) >= 14, producers
    unknown: list[str] = []
    kinds_seen: set[str] = set()
    for name, note in notes:
        try:
            kind = classify_lineage_kind(note)
        except KeyError as exc:
            unknown.append(f"{name}: {note!r} ({exc})")
            continue
        kinds_seen.add(kind)
        assert kind in LINEAGE_NOTE_KIND_FACTS, (name, kind, note)
    assert unknown == [], unknown
    assert "source_swap" not in kinds_seen
    assert kinds_seen == set(LINEAGE_NOTE_KIND_FACTS), (kinds_seen, set(LINEAGE_NOTE_KIND_FACTS))


def test_unknown_lineage_fallback_is_typed_and_warns(capsys) -> None:
    from lib.macro_suite_disclosure import lineage_note_pair
    pair = lineage_note_pair(
        "engine.internal_revision_token v3",
        effective_date="2026-09-04", prior_effective_date="2026-09-04")
    assert pair is not None
    assert "cannot summarise" in pair["en"]
    assert "both as of 4 Sep 2026" in pair["en"]
    assert "A correction note is on file" not in pair["en"]
    err = capsys.readouterr().out
    assert err.startswith("::warning title=macro-suite-unknown-lineage-kind::")


@pytest.mark.needs_full_checkout("site")
def test_financial_conditions_page_shows_no_change_republication() -> None:
    html = (ROOT / "site" / "macro_financial_conditions.html").read_text(
        encoding="utf-8")
    assert "no-change republication" in html
    assert "A correction note is on file for this reading." not in html


def test_hysteresis_note_distinguishes_configured_from_unused() -> None:
    from lib.macro_suite_disclosure import hysteresis_note_pair
    unused = hysteresis_note_pair({"band": 5, "applied": False, "held_prior": False})
    assert "configured but was not needed" in unused["en"]
    assert "5" in unused["en"]
    assert "未用到" in unused["zh"]
    not_engaged = hysteresis_note_pair({
        "band": 5, "applied": True, "held_prior": False,
        "note": "raw classification already matches the prior print; "
                "no boundary crossing, hysteresis not engaged",
    })
    assert "configured but was not needed" in not_engaged["en"]
    absent = hysteresis_note_pair({"band": 0, "applied": False, "held_prior": False})
    assert absent["en"] == "No hold-back band is configured on this reading."
    assert "未配置" in absent["zh"]
    held = hysteresis_note_pair({"band": 5, "applied": True, "held_prior": True})
    assert "kept this reading on the prior side" in held["en"]
    flipped = hysteresis_note_pair({
        "band": 5, "applied": True, "held_prior": False,
        "note": "prior quadrant not held: labor_demand crossed the 50 boundary "
                "and moved beyond the 5.0-pt hysteresis band, so the transition "
                "to the raw quadrant is accepted",
    })
    assert "did not stay on the prior side" in flipped["en"]


def test_owner_display_pair_falls_back_without_raising(capsys) -> None:
    from lib.macro_suite_disclosure import owner_display_pair
    pair = owner_display_pair("engine.brand_new_desk")
    assert pair == {
        "en": "Source owner not yet named",
        "zh": "数据来源负责人待定",
    }
    captured = capsys.readouterr()
    warning = next(
        (line for line in captured.out.splitlines() if line.startswith("::warning")),
        "",
    )
    assert warning.startswith("::warning title=macro-suite-unmapped-owner::")
    assert "engine.brand_new_desk" in warning


@pytest.mark.needs_full_checkout("site")
def test_trace_row_present_iff_trace_ref() -> None:
    import json
    path = DATA_ROOT / "workspaces" / "financial_conditions" / "US" / "latest.json"
    snap = json.loads(path.read_text(encoding="utf-8"))
    items = ((snap.get("implications") or {}).get("items") or [])[:3]
    assert items, "financial_conditions must have implication items"
    html = (ROOT / "site" / "macro_financial_conditions.html").read_text(
        encoding="utf-8")
    traces = re.findall(r'<p class="mq-trace">', html)
    expected = sum(1 for item in items if item.get("trace_ref"))
    assert len(traces) == expected
    src = (ROOT / "templates" / "_macro_suite_shell.html.j2").read_text(
        encoding="utf-8")
    assert "{%- if item.trace_ref %}" in src
    assert "mq-trace" in src


@pytest.mark.needs_full_checkout("site")
def test_restored_row_families_on_non_composite_page() -> None:
    html = (ROOT / "site" / "macro_monetary_policy.html").read_text(
        encoding="utf-8")
    assert "mq-axis-method" not in html
    for en, zh in (
        ("Method version", "方法版本"),
        ("Changed fingerprints", "已变更指纹"),
        ("Hysteresis", "滞回"),
        ("replaces the prior one", "本期取代上一期"),
    ):
        assert en in html, en
        assert zh in html, zh
    assert "Definition version" in html
    assert "A correction note is on file for this reading." not in html


@pytest.mark.needs_full_checkout("mockups")
def test_method_open_family_photographs_disclosure_rows() -> None:
    import json
    from scripts.capture_macro_command_p5 import declared_families, family_for
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "probes.json")
        .read_text(encoding="utf-8"))
    cells = [
        state
        for page in manifest.get("pages") or []
        for state in page.get("states") or []
        if state.get("family") == "method_open" or family_for(state.get("file") or "") == "method_open"
    ]
    assert len(cells) >= 10, [c.get("file") for c in cells]
    # Labor crops must live under the labor page entry, never FC.
    labor_files = [c["file"] for c in cells if "labor_markets" in c["file"]]
    for page in manifest.get("pages") or []:
        for state in page.get("states") or []:
            if "labor_markets" in str(state.get("file")):
                assert page["page_id"] == "macro_labor_markets.html", (
                    page["page_id"], state.get("file"))
                assert state.get("shot_route") in (
                    "/macro_labor_markets.html", "macro_labor_markets.html")
    assert labor_files, "expected labor method_open cells"
    text_hashes: set[str] = set()
    for state in cells:
        from scripts.capture_macro_command_p5 import METHOD_OPEN_SELECTOR
        assert state.get("crop_selector") == METHOD_OPEN_SELECTOR
        assert state.get("openedBy") == "click"
        locale = state.get("locale") or "en"
        head = (
            state.get("visible_text_head")
            or state.get("element_text_head")
            or ""
        )
        text = (probes.get("method_open_text") or {}).get(state["file"]) or ""
        if not text:
            text = state.get("element_text") or ""
        assert text, state.get("file")
        if locale == "zh":
            assert "权重法则" in text, (state.get("file"), text[:80])
            assert "Weights law" not in text and "WEIGHTS LAW" not in text, (
                state.get("file"), text[:80])
            assert "权重法则" in head or "坐标轴" in head or "方向" in head, (
                state.get("file"), head)
            assert "Weights law" not in head and "WEIGHTS LAW" not in head, (
                state.get("file"), head)
        else:
            assert "weights law" in text.casefold(), (state.get("file"), text[:80])
            assert "权重法则" not in text, (state.get("file"), text[:80])
            assert "weights law" in head.casefold() or "axis method" in head.casefold(), (
                state.get("file"), head)
            assert "权重法则" not in head, (state.get("file"), head)
        assert state.get("visible_text_sha256") or state.get("element_text_sha256")
        if state.get("visible_text_sha256"):
            assert state.get("visible_text_scope") in {"page", "element"}, (
                state.get("file"), state.get("visible_text_scope"))
        text_hashes.add(
            state.get("visible_text_sha256")
            or state.get("element_text_sha256")
        )
        # Geometry guard receipts
        box = state.get("crop_box") or {}
        assert float(box.get("x", -1)) >= 0, (state.get("file"), box)
        assert (
            float(box["x"]) + float(box["width"])
            <= float(state.get("viewport_width") or 0) + 0.5
        ), (state.get("file"), box)
        assert state.get("occlusionSamples"), state.get("file")
        for en, zh in COMPOSITION_DISCLOSURE_ROWS:
            label = zh if locale == "zh" else en
            # dt labels may be CSS-uppercased in visible text
            assert label in text or label.upper() in text or label.casefold() in text.casefold(), (
                state.get("file"), label)
    # EN and ZH must not share a text hash once locale-visible text is used.
    assert len(text_hashes) >= 4, text_hashes
    families = probes.get("declared_families") or declared_families()
    assert "method_open" in families
    details = [
        state
        for page in manifest.get("pages") or []
        for state in page.get("states") or []
        if state.get("family") == "details_open"
        and str(state.get("file", "")).startswith(("15", "16"))
        and "1440" in str(state.get("file"))
    ]
    pairs = {(s.get("theme"), s.get("locale")) for s in details}
    assert pairs >= {("dark", "en"), ("dark", "zh"), ("light", "en"), ("light", "zh")}


@pytest.mark.needs_full_checkout("mockups")
def test_lineage_open_family_photographs_restored_rows() -> None:
    import json
    from scripts.capture_macro_command_p5 import family_for
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "probes.json")
        .read_text(encoding="utf-8"))
    cells = [
        state
        for page in manifest.get("pages") or []
        for state in page.get("states") or []
        if state.get("family") == "lineage_open"
        or family_for(state.get("file") or "") == "lineage_open"
    ]
    assert len(cells) >= 8, [c.get("file") for c in cells]
    pages = {c.get("file", "").split("-")[1] for c in cells}
    assert "macro_financial_conditions" in pages
    assert "macro_monetary_policy" in pages
    for state in cells:
        assert state.get("crop_selector") == "section.mq-lineage"
        assert state.get("openedBy") == "click"
        assert state.get("occlusionSamples")
        assert state.get("raw_box"), state.get("file")
        locale = state.get("locale") or "en"
        text = (probes.get("lineage_open_text") or {}).get(state["file"]) or ""
        assert text, state.get("file")
        low = text.lower()
        # n-A: typed unknown-kind fallback is NOT a lineage sentence.
        assert "cannot summarise" not in low
        assert "无法概括" not in text
        if locale == "zh":
            assert "已变更指纹" in text, (state.get("file"), text[:120])
            assert "滞回" in text, (state.get("file"), text[:120])
            assert (
                "同一参考期" in text
                or "取代上一期" in text
                or "首次发布" in text
                or "更晚的参考期" in text
            ), (state.get("file"), text[:160])
            assert (
                "滞回带" in text
                or "未配置滞回" in text
            ), (state.get("file"), text[:160])
        else:
            assert "changed fingerprints" in low or "changed fingerprint" in low
            assert "hysteresis" in low
            assert (
                "same reference period" in low
                or "replaces the prior one" in low
                or "first published" in low
                or "later reference period" in low
            )
            assert (
                "hold-back band" in low
                or "no hold-back band is configured" in low
            )


@pytest.mark.needs_full_checkout("mockups")
def test_manifest_page_routes_match_shot_routes() -> None:
    import json
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    page_ids = {p["page_id"] for p in manifest["pages"]}
    assert "macro_labor_markets.html" in page_ids
    assert "macro_monetary_policy.html" in page_ids
    for page in manifest["pages"]:
        route = page["route"]
        for state in page["states"]:
            if state.get("page_id"):
                assert state["page_id"] == page["page_id"], (
                    state.get("file"), state.get("page_id"), page["page_id"])
            shot = state.get("shot_route")
            assert shot, (state.get("file"), "missing shot_route")
            normalized = shot if str(shot).startswith("/") else f"/{shot}"
            assert normalized == route, (state.get("file"), shot, route)


@pytest.mark.needs_full_checkout("mockups")
def test_labor_page_rest_matrix_eight_cells_healthy() -> None:
    """m-B: labor carries the 8 required rest keys with empty health receipts."""
    import json
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    labor = next(
        p for p in manifest["pages"]
        if p["page_id"] == "macro_labor_markets.html")
    assert labor["route"] == "/macro_labor_markets.html"
    assert labor["console_errors"] == []
    assert labor["failed_responses"] == []
    rest = [
        s for s in labor["states"]
        if str(s.get("file", "")).startswith("ws-macro_labor_markets")
    ]
    # Premise correction: checker requires 8 (2 viewports × 2 locales × 2 themes),
    # not the r13 "12-cell" wording.
    assert len(rest) == 8, [s.get("file") for s in rest]
    keys = {
        (s.get("viewport"), s.get("locale"), s.get("theme"))
        for s in rest
    }
    assert len(keys) == 8


@pytest.mark.needs_full_checkout("mockups")
def test_crop_selector_cells_carry_guard_receipts() -> None:
    """M-C: every crop_selector cell has raw_box + occlusion + locale text."""
    import json
    from scripts.capture_macro_command_p5 import family_for
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    skip_families = {"workspace", "hub_fold", "hub_full", "hub_390", "hub_768",
                     "tablet_768", "e5"}
    missing = []
    for page in manifest["pages"]:
        for state in page["states"]:
            fam = state.get("family") or family_for(state.get("file") or "")
            if fam in skip_families and not state.get("crop_selector"):
                assert state.get("raw_box") is not None, state.get("file")
                assert state.get("shot_route"), state.get("file")
                continue
            if not state.get("crop_selector"):
                continue
            for key in ("raw_box", "occlusionSamples", "visible_text_sha256",
                        "cropDomSha256", "shot_route"):
                if not state.get(key):
                    missing.append((state.get("file"), key))
    assert not missing, missing[:20]


@pytest.mark.needs_full_checkout("mockups")
def test_allowlist_reasons_min_length_and_observed_bytes() -> None:
    """C-m1 / E-m2: every allowlist reason ≥12 chars; listed pairs byte-identical."""
    import hashlib
    from pathlib import Path
    import yaml
    root = ROOT / "mockups" / "evidence" / "macro-command-p5"
    path = root / "chipmat_identical_allowlist.yml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    pairs = doc.get("pairs") or []
    assert pairs, "allowlist must list observed groups"
    for entry in pairs:
        reason = str(entry.get("reason") or "")
        assert len(reason) >= 12, entry
        kind = str(entry.get("kind") or "chipmat")
        assert kind in {"chipmat", "trace"}, entry
        slugs = entry.get("slugs") or []
        theme = entry["theme"]
        locale = entry["locale"]
        width = str(entry["width"])
        digests = set()
        for slug in slugs:
            if kind == "trace":
                candidate = root / (
                    f"disclosure_rows_open-{slug}-{theme}-{locale}-{width}"
                    f"_rows_trace.png"
                )
            else:
                candidate = root / (
                    f"chipmat-{slug}-{theme}-{locale}-{width}.png"
                )
            assert candidate.is_file(), (entry, candidate.name)
            digests.add(hashlib.sha256(candidate.read_bytes()).hexdigest())
        if len(digests) > 1:
            raise AssertionError(
                f"allowlisted pair not byte-identical: {entry} digests={digests}")


@pytest.mark.needs_full_checkout("mockups")
def test_inner_scrollports_have_method_table_pair() -> None:
    """C-B1/E-B1: every crop content_overflows entry resolves to sanctioned_scrollers.yml.

    MUT-c3 (inject unregistered scrollport on a workspace cell) must FAIL.
    MUT-c4 (inject free text overflow outside any registered scroller on chipmat)
    must FAIL.
    """
    import json
    from pathlib import Path
    from scripts.capture_macro_command_p5 import (
        _load_sanctioned_scrollers, _registry_match_selector, family_for,
    )
    registry = _load_sanctioned_scrollers()
    assert registry, "sanctioned_scrollers.yml empty"
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    files = {
        st.get("file")
        for page in manifest["pages"]
        for st in page["states"]
    }
    missing_key = []
    offenders = []
    for page in manifest["pages"]:
        for state in page["states"]:
            if not state.get("crop"):
                continue
            if "content_overflows" not in state:
                missing_key.append(state.get("file"))
                continue
            overflows = state.get("content_overflows") or []
            fam = state.get("family") or family_for(state.get("file") or "")
            name = str(state.get("file") or "")
            for entry in overflows:
                sel = str(entry.get("selector") or "")
                kind = str(entry.get("kind") or "")
                nearest = entry.get("nearest_registered_scroller")
                for req in ("x", "y", "right", "crop_right"):
                    if req not in entry:
                        offenders.append((name, f"missing {req}", entry))
                        break
                if sel in {"text", "TEXT"} or not sel:
                    offenders.append((name, "unresolvable selector", entry))
                    continue
                if kind == "scrollport":
                    key = _registry_match_selector(sel) or (
                        _registry_match_selector(str(nearest)) if nearest else None)
                    if not key or key not in registry:
                        offenders.append((name, "unregistered scrollport", entry))
                elif kind in {"box", "text"}:
                    key = _registry_match_selector(str(nearest)) if nearest else None
                    if not key or key not in registry:
                        offenders.append((name, "free box/text", entry))
            # method_table_390: missing end only OK under table_fits.
            # midN cells are family members of an overflowing start+end.
            if fam == "method_table_390" and "method_table_390_start-" in name:
                end = name.replace(
                    "method_table_390_start-", "method_table_390_end-", 1)
                if end not in files and not state.get("table_fits"):
                    offenders.append((name, "missing end without table_fits"))
                if not state.get("element_key"):
                    offenders.append((name, "missing element_key"))
            if fam == "method_table_390" and "_mid" in name:
                if not state.get("element_key"):
                    offenders.append((name, "missing element_key"))
                if state.get("table_fits") is True:
                    offenders.append((name, "mid cell with table_fits"))
            for entry in overflows:
                if str(entry.get("selector") or "") == "table.mq-table":
                    if not entry.get("element_key"):
                        offenders.append((name, "overflow missing element_key",
                                          entry))
    assert not missing_key, missing_key[:10]
    assert not offenders, offenders[:10]


# V24-T1: per-element method_table_390 photographs multiple table species.
# Classify by the photographed table's own header tokens. Decimal-union is
# composition-only; every species still owes header-token union coverage.
_COMPOSITION_HEADERS = {
    "en": ("Component", "Raw", "Standardized", "Weight", "Contribution"),
    "zh": ("分项", "原始", "标准化", "权重", "贡献"),
}
_CHANGED_HEADERS = {
    "en": ("Metric", "Prior", "Current", "Change"),
    "zh": ("指标", "上期", "当前", "变化"),
}
_COVERAGE_HEADERS = {
    "en": ("Component", "Presence", "Freshness", "Source", "as-of"),
    "zh": ("分项", "具备情况", "新鲜度", "数据源截止"),
}


def _headers_in_text(text: str, headers: tuple[str, ...], locale: str) -> bool:
    blob = text.casefold() if locale == "en" else text
    if locale == "en":
        return all(h.casefold() in blob for h in headers)
    return all(h in blob for h in headers)


def _canonical_member_count(
        text: str, headers: tuple[str, ...], locale: str) -> int:
    blob = text.casefold() if locale == "en" else text
    n = 0
    for h in headers:
        needle = h.casefold() if locale == "en" else h
        if needle in blob:
            n += 1
    return n


def _canonical_tuple_in_order(
        receipt: list[str], headers: tuple[str, ...], locale: str) -> bool:
    blob = " ".join(receipt)
    if locale == "en":
        blob = blob.casefold()
        needles = [h.casefold() for h in headers]
    else:
        needles = list(headers)
    pos = 0
    for needle in needles:
        i = blob.find(needle, pos)
        if i < 0:
            return False
        pos = i + len(needle)
    return True


def _leading_non_numeric_tokens(full: str, locale: str) -> list[str]:
    out: list[str] = []
    for tok in full.split():
        if re.fullmatch(r"[+\-−]?\d+(?:\.\d+)?%?", tok) or re.search(r"\d", tok):
            break
        if locale == "en":
            if not re.search(r"[A-Za-z]", tok):
                break
        elif not re.search(r"[\u4e00-\u9fff]", tok):
            break
        out.append(tok)
        if len(out) >= 8:
            break
    return out


def _classify_method_table(
        full: str, locale: str) -> tuple[str, tuple[str, ...], bool]:
    """Return (species, headers, demand_decimals) from the table's own headers."""
    composition = _COMPOSITION_HEADERS[locale]
    changed = _CHANGED_HEADERS[locale]
    coverage = _COVERAGE_HEADERS[locale]
    # Component is shared with the coverage table; require the distinctive rest.
    if _headers_in_text(full, composition[1:], locale):
        return "composition", composition, True
    if _headers_in_text(full, changed, locale):
        return "changed", changed, False
    if _headers_in_text(full, coverage[1:], locale):
        return "coverage", coverage, False
    headers = tuple(_leading_non_numeric_tokens(full, locale))
    assert headers, ("unclassified table has no header tokens", full[:160])
    return "other", headers, False


def _header_in_visible(token: str, text: str, locale: str) -> bool:
    if locale == "en":
        return token.casefold() in text.casefold()
    return token in text


@pytest.mark.needs_full_checkout("mockups")
def test_method_table_390_contribution_union() -> None:
    """E-B1(3)/C-m1/E-M1/V24-T1: header-token union for every photographed species.

    Classify each table by its own header tokens. Composition keeps the
    decimal-union assertion; What-changed keeps Metric/Prior/Current/Change;
    any other species (coverage, driver, …) still asserts full header-token
    union, EN/ZH distinctness, and last-column-present-in-end — no decimal
    demand. No species is exempt from union coverage.
    Reads MANIFEST cells' visible_text_at_scroll FIRST (MUT-a1 / MUT-hdr:
    blanking manifest receipts alone must FAIL). Missing end is accepted
    only when start has table_fits: true.
    """
    import json
    from collections import defaultdict
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "probes.json")
        .read_text(encoding="utf-8"))
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    by_file = {
        st["file"]: st
        for page in manifest["pages"]
        for st in page["states"]
        if st.get("file")
    }
    table_probes = probes.get("method_table_390_text") or {}
    assert table_probes, "method_table_390_text probe missing"
    vis_map = probes.get("method_table_390_visible") or {}
    probe_headers = probes.get("method_table_390_headers") or {}
    from scripts.capture_macro_command_p5 import method_table_filename
    unions: dict[tuple, dict[str, str]] = defaultdict(dict)
    species_census: dict[tuple[str, str], int] = defaultdict(int)
    for key, full in table_probes.items():
        m = re.match(
            r"method_table_390-(.+?)(?:__([A-Za-z0-9_.-]+))?-"
            r"(dark|light)-(en|zh)-(\d+)$", key)
        assert m, key
        slug, ekey, theme, locale, width = m.groups()
        assert ekey, (key, "probe key missing element_key")
        species, classified_headers, demand_decimals = _classify_method_table(
            full, locale)
        species_census[(locale, species)] += 1
        start = by_file.get(method_table_filename(
            "start", slug, theme, locale, width, element_key=ekey))
        end = by_file.get(method_table_filename(
            "end", slug, theme, locale, width, element_key=ekey))
        assert start, key
        if end is None:
            assert start.get("table_fits") is True, (
                key, "missing end without table_fits")
            assert float(start.get("scrollWidth") or 0) <= float(
                start.get("clientWidth") or 0) + 1, (key, "table_fits true")
        else:
            assert start.get("table_fits") is not True, (
                key, "end exists but table_fits true")
            # C-m3: end must be at max scroll.
            sw = float(end.get("scrollWidth") or 0)
            cw = float(end.get("clientWidth") or 0)
            sl = float(end.get("scrollLeft") or 0)
            assert abs(sl - (sw - cw)) <= 1.0 or sl >= sw - cw - 1, (
                key, "end scrollLeft", sl, sw, cw)
        start_vis = str(start.get("visible_text_at_scroll") or "")
        assert start_vis, (key, "blank manifest visible_text_at_scroll")
        if start["file"] in vis_map:
            assert vis_map[start["file"]] == start_vis, (
                key, "probes map != manifest start")
        parts = [start_vis]
        crop_states = [start]
        n = 1
        while True:
            mid = by_file.get(method_table_filename(
                f"mid{n}", slug, theme, locale, width, element_key=ekey))
            if mid is None:
                break
            mid_vis = str(mid.get("visible_text_at_scroll") or "")
            assert mid_vis, (key, f"blank manifest mid{n} visible_text_at_scroll")
            if mid["file"] in vis_map:
                assert vis_map[mid["file"]] == mid_vis, (
                    key, f"probes map != manifest mid{n}")
            parts.append(mid_vis)
            crop_states.append(mid)
            n += 1
        end_vis = ""
        if end is not None:
            end_vis = str(end.get("visible_text_at_scroll") or "")
            assert end_vis, (key, "blank manifest end visible_text_at_scroll")
            if end["file"] in vis_map:
                assert vis_map[end["file"]] == end_vis, (
                    key, "probes map != manifest end")
            parts.append(end_vis)
            crop_states.append(end)
        union = " ".join(parts)
        unions[(slug, ekey, theme, width)][locale] = union
        start_receipt = start.get("header_tokens")
        assert isinstance(start_receipt, (list, tuple)) and len(start_receipt) > 0, (
            key, "missing/empty header_tokens receipt")
        start_receipt = [str(h) for h in start_receipt]
        for st in crop_states:
            rec = st.get("header_tokens")
            assert isinstance(rec, (list, tuple)), (
                key, st.get("file"), "header_tokens missing")
            rec = [str(h) for h in rec]
            assert rec == start_receipt, (
                key, st.get("file"), rec, start_receipt,
                "header_tokens != start")
            assert st.get("header_cell_count") == len(rec), (
                key, st.get("file"), st.get("header_cell_count"), len(rec),
                "header_cell_count != len(header_tokens)")
        stored = probe_headers.get(key)
        assert stored == start_receipt, (
            key, stored, start_receipt, "manifest start != probes headers")
        joined = " ".join(start_receipt)
        assert full.casefold().startswith(joined.casefold()), (
            key, joined, "header_tokens not prefix of full probe text")
        if species in ("composition", "changed", "coverage"):
            assert _canonical_tuple_in_order(
                start_receipt, classified_headers, locale), (
                key, species, start_receipt, classified_headers,
                "receipt missing canonical header tuple in order")
        if species == "other":
            for sname, tup in (
                    ("composition", _COMPOSITION_HEADERS[locale]),
                    ("changed", _CHANGED_HEADERS[locale]),
                    ("coverage", _COVERAGE_HEADERS[locale])):
                n_hit = _canonical_member_count(full, tup, locale)
                assert n_hit < len(tup) - 1, (
                    key, "other near-miss of", sname, tup, n_hit)
            receipt = start.get("header_tokens")
            assert isinstance(receipt, (list, tuple)) and len(receipt) > 0, (
                key, "other-species missing/empty header_tokens receipt")
            headers = tuple(str(h) for h in receipt)
        else:
            headers = classified_headers
        for h in headers:
            assert _header_in_visible(h, union, locale), (
                key, species, h, "header missing from start∪end — MUT-hdr must fail")
        last = headers[-1]
        if end is not None:
            assert _header_in_visible(last, end_vis, locale), (
                key, species, last, "last column missing from end")
        else:
            assert _header_in_visible(last, start_vis, locale), (
                key, species, last, "last column missing from fitting start")
        if demand_decimals:
            contribs = re.findall(r"[+\-−]?\d+(?:\.\d+)?", full)
            values = [v for v in contribs if "." in v]
            assert values, (key, species, full[:120])
            for v in values:
                assert v in full, (key, v)
                assert v in union, (key, v, "missing from start∪end visible text")
            # Component labels: EN by token, ZH by exact substring of row label.
            if locale == "en":
                labels = re.findall(
                    r"([A-Za-z][\w/]*(?:\s+channel)?)", full)
                channel_labels = re.findall(
                    r"([A-Za-z][\w/]*\s+channel)", full, flags=re.I)
                skip = {h.upper() for h in headers}
                check = channel_labels or [
                    t for t in labels
                    if t.upper() not in skip and not re.fullmatch(r"[\d.+−\-]+", t)
                ]
                for lab in check[:8]:
                    tok = lab.split()[0]
                    assert tok.casefold() in union.casefold(), (
                        key, lab, "component label missing from start∪end")
            else:
                body = full
                for h in headers:
                    body = body.replace(h, " ")
                body = re.sub(r"[+\-−]?\d+(?:\.\d+)?", " ", body)
                for lab in [p for p in body.split() if len(p) >= 2][:8]:
                    assert lab in union, (
                        key, lab, "ZH component label missing from start∪end")
    collisions = [
        ident for ident, locs in unions.items()
        if "en" in locs and "zh" in locs
        and locs["en"].casefold() == locs["zh"].casefold()
    ]
    assert not collisions, ("EN/ZH visible union not distinct", collisions[:8])
    for loc in ("en", "zh"):
        assert species_census[(loc, "composition")] >= 8, (
            loc, "composition census floor",
            species_census[(loc, "composition")])
        assert species_census[(loc, "changed")] >= 10, (
            loc, "changed census floor", species_census[(loc, "changed")])
        assert species_census[(loc, "coverage")] >= 10, (
            loc, "coverage census floor", species_census[(loc, "coverage")])


@pytest.mark.needs_full_checkout("mockups")
def test_method_table_header_blank_mut_hdr_fails() -> None:
    """MUT-hdr: blanking header tokens in manifest visible_text must fail union."""
    import json
    import re
    import copy
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "probes.json")
        .read_text(encoding="utf-8"))
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    by_file = {
        st["file"]: st
        for page in manifest["pages"]
        for st in page["states"]
        if st.get("file")
    }
    from scripts.capture_macro_command_p5 import (
        METHOD_OPEN_PAGES, method_table_filename,
    )
    contrib_slugs = {p.replace(".html", "") for p in METHOD_OPEN_PAGES}
    key = next(
        k for k in (probes.get("method_table_390_text") or {})
        if any(s in k for s in contrib_slugs)
        and "__" in k
    )
    m = re.match(
        r"method_table_390-(.+?)(?:__([A-Za-z0-9_.-]+))?-"
        r"(dark|light)-(en|zh)-(\d+)$", key)
    assert m, key
    slug, ekey, theme, locale, width = m.groups()
    start_name = method_table_filename(
        "start", slug, theme, locale, width, element_key=ekey)
    start = copy.deepcopy(by_file[start_name])
    end = by_file.get(method_table_filename(
        "end", slug, theme, locale, width, element_key=ekey))
    # Blank header tokens in the start receipt.
    vis = str(start.get("visible_text_at_scroll") or "")
    for h in ("COMPONENT", "RAW", "STANDARDIZED", "WEIGHT", "CONTRIBUTION",
              "Component", "Raw", "Standardized", "Weight", "Contribution",
              "分项", "原始", "标准化", "权重", "贡献"):
        vis = re.sub(re.escape(h), "", vis, flags=re.I)
    start["visible_text_at_scroll"] = vis
    union = vis
    if end is not None:
        end_vis = str(end.get("visible_text_at_scroll") or "")
        for h in ("COMPONENT", "RAW", "STANDARDIZED", "WEIGHT", "CONTRIBUTION",
                  "Component", "Raw", "Standardized", "Weight", "Contribution",
                  "分项", "原始", "标准化", "权重", "贡献"):
            end_vis = re.sub(re.escape(h), "", end_vis, flags=re.I)
        union = f"{vis} {end_vis}"
    headers = (
        ("COMPONENT", "RAW", "STANDARDIZED", "WEIGHT", "CONTRIBUTION")
        if locale == "en" else ("分项", "原始", "标准化", "权重", "贡献")
    )
    missing = [h for h in headers if h.casefold() not in union.casefold()]
    assert missing, "MUT-hdr plant did not remove headers"


@pytest.mark.needs_full_checkout("mockups")
def test_png_dimensions_equal_raw_box() -> None:
    """C-m4: PNG css dims == shoot_box exactly; |shoot_box − raw_box| ≤ 1."""
    import json
    import struct
    root = ROOT / "mockups" / "evidence" / "macro-command-p5"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    bad = []
    for page in manifest["pages"]:
        for state in page["states"]:
            if not state.get("crop"):
                continue
            raw = state.get("raw_box") or {}
            shoot = state.get("shoot_box") or raw
            path = root / str(state.get("file") or "")
            if not path.is_file() or not raw:
                bad.append((state.get("file"), "missing"))
                continue
            data = path.read_bytes()
            assert data[12:16] == b"IHDR", path.name
            pw, ph = struct.unpack(">II", data[16:24])
            dpr = float(state.get("dpr") or 1) or 1.0
            css_w, css_h = pw / dpr, ph / dpr
            if (
                abs(css_w - float(shoot["width"])) > 0.01
                or abs(css_h - float(shoot["height"])) > 0.01
            ):
                bad.append((
                    state.get("file"), "png!=shoot", css_w, css_h,
                    shoot.get("width"), shoot.get("height"), dpr))
            if (
                abs(float(shoot["width"]) - float(raw["width"])) > 1.0
                or abs(float(shoot["height"]) - float(raw["height"])) > 1.0
            ):
                bad.append((
                    state.get("file"), "shoot-raw", shoot, raw))
    assert not bad, bad[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_no_stitched_keys_and_no_repeated_band() -> None:
    """E-B1/C-M4: no stitched keys; tall PNGs have no duplicated 200px band."""
    import json
    import numpy as np
    from pathlib import Path
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow required")
    root = ROOT / "mockups" / "evidence" / "macro-command-p5"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    stitch_keys = []
    repeated = []
    for page in manifest["pages"]:
        for state in page["states"]:
            if "stitched" in state or "stitch_strips" in state:
                stitch_keys.append(state.get("file"))
            if not state.get("crop"):
                continue
            path = root / str(state.get("file") or "")
            if not path.is_file():
                continue
            im = Image.open(path).convert("RGB")
            if im.height <= 900:
                continue
            arr = np.asarray(im)
            band = 200
            coinc = 0
            compared = 0
            for y0 in range(0, arr.shape[0] - 2 * band, band):
                a = arr[y0:y0 + band]
                for y1 in range(y0 + band, arr.shape[0] - band + 1, band):
                    b = arr[y1:y1 + band]
                    compared += 1
                    if a.shape == b.shape and np.array_equal(a, b):
                        coinc += band
                        repeated.append((path.name, y0, y1))
                        break
                if repeated and repeated[-1][0] == path.name:
                    break
            if compared and coinc > 0.01 * arr.shape[0]:
                pass  # already recorded in repeated
    assert not stitch_keys, stitch_keys[:10]
    assert not repeated, repeated[:5]


def _y_coverage_offenders(manifest) -> list:
    """Shared y_coverage comparison (test_occlusion_y_coverage_from_raw_box + MUT-cov)."""
    from scripts.macro_command_capture_guards import y_coverage
    bad = []
    for page in manifest["pages"]:
        for state in page["states"]:
            if not state.get("crop"):
                continue
            samples = state.get("occlusionSamples") or []
            raw = state.get("raw_box") or {}
            if not samples or not raw:
                bad.append((state.get("file"), "missing samples/raw_box"))
                continue
            h = float(raw.get("height") or 0)
            grid = state.get("grid")
            if grid == "medium":
                bad.append((state.get("file"), "unsanctioned grid:medium"))
                continue
            if grid not in {"full", "short"}:
                bad.append((state.get("file"), f"missing/invalid grid={grid!r}"))
                continue
            if h < 40.0:
                if grid != "short":
                    bad.append((state.get("file"), "h<40 must be grid:short"))
                if state.get("y_coverage") == 0.0:
                    bad.append((state.get("file"),
                                "y_coverage 0.0 on short crop misleads"))
                continue  # short exempt from coverage floor
            if grid == "short":
                continue
            sample_box = state.get("occlusion_sample_box") or {}
            if sample_box:
                for dim in ("x", "y", "width", "height"):
                    if abs(float(sample_box.get(dim) or 0)
                           - float(raw.get(dim) or 0)) > 1.0:
                        bad.append((state.get("file"), "sample_box!=raw_box", dim))
                        break
            if state.get("samples_span") not in {None, "crop"}:
                bad.append((state.get("file"), "samples_span",
                            state.get("samples_span")))
                continue
            cov = y_coverage(samples, raw)
            stored = state.get("y_coverage")
            if stored is None:
                bad.append((state.get("file"), "missing stored y_coverage"))
                continue
            if abs(float(stored) - cov) > 1e-9:
                bad.append((state.get("file"), "stored!=recomputed",
                            float(stored), cov))
            ys = [float(s["y"]) for s in samples if "y" in s]
            top = float(raw["y"])
            bottom = top + h
            # R4: floor with 1e-3 epsilon. Exact floor is (h-8)/h.
            floor = (h - 8.0) / h
            if cov < (floor - 1e-3):
                bad.append((state.get("file"), "cov", cov, floor))
            if ys and min(ys) > top + 4.0:
                bad.append((state.get("file"), "top", min(ys), top))
            if ys and max(ys) < bottom - 4.0:
                bad.append((state.get("file"), "bottom", max(ys), bottom))
    return bad


@pytest.mark.needs_full_checkout("mockups")
def test_occlusion_y_coverage_from_raw_box() -> None:
    """E-B2/C-M1/C-M2: coverage from samples vs raw_box; only grid:short exempt."""
    import json
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    bad = _y_coverage_offenders(manifest)
    assert not bad, bad[:15]


@pytest.mark.needs_full_checkout("mockups")
def test_tall_crops_carry_shot_viewport() -> None:
    """C-M3: every tall crop (raw_box.h + chrome + 16 > 900) has tall receipts."""
    import json
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    bad = []
    for page in manifest["pages"]:
        for state in page["states"]:
            if not state.get("crop"):
                continue
            raw = state.get("raw_box") or {}
            if not raw:
                continue
            chrome = 60.0
            hidden = state.get("hidden_fixed") or []
            # Prefer chrome from shot if available; else conservative 60.
            need = float(raw.get("height") or 0) + chrome + 16.0
            if need <= 900.0:
                continue
            if not state.get("shot_viewport"):
                bad.append((state.get("file"), "missing shot_viewport"))
                continue
            rbiv = state.get("raw_box_in_shot_viewport") or {}
            if not rbiv:
                bad.append((state.get("file"), "missing raw_box_in_shot_viewport"))
                continue
            for dim in ("width", "height"):
                if abs(float(rbiv.get(dim) or 0) - float(raw.get(dim) or 0)) > 0.5:
                    bad.append((state.get("file"), "drift", dim, rbiv, raw))
    assert not bad, bad[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_390_matrix_full_theme_locale() -> None:
    """C-n1: per page (FC AND labor) full 2×2; hub_390 included."""
    import json
    from collections import defaultdict
    from scripts.capture_macro_command_p5 import family_for
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    need = {("dark", "en"), ("dark", "zh"), ("light", "en"), ("light", "zh")}
    # family -> page_slug -> set of (theme, locale)
    cells: dict[str, dict[str, set[tuple[str, str]]]] = defaultdict(
        lambda: defaultdict(set))
    hub_cells: set[tuple[str, str]] = set()
    for page in manifest["pages"]:
        for state in page["states"]:
            w = state.get("viewport_width") or state.get("viewport")
            if str(w) not in {"390", "mobile"} and w != 390:
                continue
            fam = state.get("family") or family_for(state.get("file") or "")
            name = str(state.get("file") or "")
            theme, locale = state.get("theme"), state.get("locale")
            if fam == "hub_390" or name.startswith(
                    ("09-", "10-", "11-", "12-")):
                hub_cells.add((theme, locale))
                continue
            if fam not in {
                "method_open", "method_table_390", "disclosure_rows_open",
            }:
                continue
            # Derive page slug from filename.
            rest = name
            from scripts.capture_macro_command_p5 import parse_method_table_name
            parsed = parse_method_table_name(name)
            if parsed:
                slug = parsed["slug"]
            else:
                for prefix in (
                    "method_table_390_start-", "method_table_390_end-",
                    "method_table_390_mid1-", "method_table_390_mid2-",
                    "method_table_390_mid3-",
                    "method_open-", "disclosure_rows_open-",
                ):
                    if rest.startswith(prefix):
                        rest = rest[len(prefix):]
                        break
                parts = rest.replace(".png", "").split("-")
                # …-{theme}-{locale}-390
                if len(parts) >= 3 and parts[-1] == "390":
                    slug = "-".join(parts[:-3])
                else:
                    slug = "unknown"
            cells[fam][slug].add((theme, locale))
    missing = {}
    for fam in ("method_open", "method_table_390", "disclosure_rows_open"):
        pages = cells.get(fam) or {}
        # FC and labor (or monetary_policy for disclosure) each need full 2×2.
        for slug, have in pages.items():
            if not need.issubset(have):
                missing[f"{fam}:{slug}"] = sorted(need - have)
        if fam == "method_open":
            for required in ("macro_financial_conditions", "macro_labor_markets"):
                if required not in pages or not need.issubset(pages[required]):
                    missing[f"method_open:{required}"] = sorted(
                        need - (pages.get(required) or set()))
        if fam == "method_table_390":
            for required in (
                "macro_financial_conditions", "macro_labor_markets",
                "macro_business_activity", "macro_housing_real_estate",
                "macro_rates_curves",
            ):
                if required not in pages or not need.issubset(pages[required]):
                    missing[f"method_table_390:{required}"] = sorted(
                        need - (pages.get(required) or set()))
    if not need.issubset(hub_cells):
        missing["hub_390"] = sorted(need - hub_cells)
    assert not missing, missing


@pytest.mark.needs_full_checkout("mockups")
def test_receipt_document_on_every_crop() -> None:
    import json
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    missing = [
        st.get("file")
        for page in manifest["pages"]
        for st in page["states"]
        if st.get("crop") and st.get("receipt_document") not in {"host", "iframe"}
    ]
    assert not missing, missing[:10]


def _semantic_station_id(state: dict, fam: str) -> str:
    """Station id from manifest fields — never a filename numeric prefix.

    V24-T2(b): hub_390 files 09/10/11/12 are different names for the same
    station; locale is the varying axis. Per-element tables include
    element_key so instances do not collide.
    """
    force = state.get("force_state")
    ekey = str(state.get("element_key") or "").strip()
    crop = str(state.get("crop_selector") or "").strip()
    if ekey:
        return f"{force or fam}::{ekey}"
    if force:
        return str(force)
    if crop:
        return str(crop)
    return fam or "station"


def _station_axis(state: dict, page: dict, fam: str) -> tuple:
    return (
        fam,
        state.get("page_id") or page.get("page"),
        state.get("theme"),
        state.get("viewport_width") or state.get("viewport"),
        _semantic_station_id(state, fam),
    )


def _peer_start_semantic(semantic: str) -> str | None:
    s = str(semantic or "")
    m = re.search(r"_mid\d+::", s)
    if m:
        return s[:m.start()] + "_start::" + s[m.end():]
    m = re.search(r"_mid\d+$", s)
    if m:
        return s[:m.start()] + "_start"
    if "_end::" in s:
        return s.replace("_end::", "_start::", 1)
    if s.endswith("_end"):
        return s[:-4] + "_start"
    if s.endswith("-end"):
        return s[:-4] + "-start"
    return None


def _peer_end_semantic(semantic: str) -> str | None:
    s = str(semantic or "")
    if "_start::" in s:
        return s.replace("_start::", "_end::", 1)
    if s.endswith("_start"):
        return s[:-6] + "_end"
    if s.endswith("-start"):
        return s[:-6] + "-end"
    return None


@pytest.mark.needs_full_checkout("mockups")
def test_en_zh_visible_text_distinct_all_stations() -> None:
    """E-M2/V24-T2: EN ≠ ZH visible_text_sha256 at every two-locale station.

    Station keys come from manifest fields (family, page, theme, width,
    semantic station id) — not filename prefixes. A locale that has no end
    cell is still paired when the same family/element carries table_fits or
    hub fits:true; the fits receipt is that locale's account. Missing both
    the cell and any fits receipt still fails.
    """
    import json
    from collections import defaultdict
    from scripts.capture_macro_command_p5 import family_for
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    stations: dict[tuple, dict[str, tuple]] = defaultdict(dict)
    fits_at: dict[tuple, dict[str, bool]] = defaultdict(dict)
    for page in manifest["pages"]:
        for state in page["states"]:
            fam = state.get("family") or family_for(state.get("file") or "")
            loc = state.get("locale")
            if not loc:
                continue
            key = _station_axis(state, page, fam)
            if state.get("fits") is True or state.get("table_fits") is True:
                fits_at[key][loc] = True
                end_sem = _peer_end_semantic(str(key[-1] or ""))
                if end_sem:
                    fits_at[key[:-1] + (end_sem,)][loc] = True
            if not state.get("crop_selector"):
                continue
            digest = state.get("visible_text_sha256")
            head = state.get("visible_text_head")
            assert head, state.get("file")
            if not digest:
                continue
            scope = state.get("visible_text_scope")
            assert scope in {"page", "element"}, (
                state.get("file"), "visible_text_scope", scope)
            if fam == "method_table_390":
                assert scope == "element", state.get("file")
            if fam == "hub_rail":
                assert scope == "page", state.get("file")
                assert "visible_text_at_scroll" in state, state.get("file")
                assert "visible_text_at_zero" in state, state.get("file")
            stations[key][loc] = (scope, digest)
    collisions = []
    missing_locale = []
    for key, locs in stations.items():
        accounted = set(locs) | set(fits_at.get(key, {}))
        peer = _peer_start_semantic(str(key[-1] or ""))
        is_mid_station = bool(re.search(r"_mid\d+", str(key[-1] or "")))
        if peer:
            accounted |= set(fits_at.get(key[:-1] + (peer,), {}))
            if is_mid_station:
                accounted |= set(stations.get(key[:-1] + (peer,), {}))
        missing = {"en", "zh"} - accounted
        if missing:
            missing_locale.append((key, "missing locale(s)", sorted(missing)))
            continue
        if "en" in locs and "zh" in locs:
            assert locs["en"][0] == locs["zh"][0], (key, "scope mismatch")
            if locs["en"][1] == locs["zh"][1]:
                collisions.append(key)
            continue
        # One locale has a cell; the other is accounted by a fits receipt
        # or (for midN) by the same element's start cell — sweeps are
        # per-locale, so a shorter locale may have no mid.
        other = ({"en", "zh"} - set(locs)).pop()
        has_fits = bool(fits_at.get(key, {}).get(other))
        if not has_fits and peer:
            has_fits = bool(fits_at.get(key[:-1] + (peer,), {}).get(other))
        if not has_fits and is_mid_station and peer:
            has_fits = other in stations.get(key[:-1] + (peer,), {})
        assert has_fits, (key, "paired locale missing fits receipt", other)
    assert not missing_locale, missing_locale[:20]
    assert not collisions, collisions[:20]


@pytest.mark.needs_full_checkout("mockups")
def test_geometry_tolerance_declared_in_manifest() -> None:
    import json
    from scripts.macro_command_capture_guards import GEOMETRY_TOLERANCE_PX
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    assert float(manifest.get("geometry_tolerance_px")) == float(
        GEOMETRY_TOLERANCE_PX)


def test_element_text_diverges_with_hidden_node() -> None:
    import hashlib
    """C-M2: clone-strip vs live-walker diverge when a hidden node is planted."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed")
    from scripts.capture_macro_command_p5 import (
        _element_text_independent, _locale_visible_text,
    )
    try:
        pw = sync_playwright().start()
    except Exception as exc:
        pytest.skip(f"Playwright runtime unavailable: {exc}")
    try:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium unavailable: {exc}")
        page = browser.new_page()
        page.set_content(
            """<div id="root">
                 <span class="l-en">Visible EN</span>
                 <span class="l-zh" style="display:none">隐藏 ZH</span>
                 <span style="visibility:hidden">HIDDEN_NODE_XYZ</span>
               </div>"""
        )
        loc = page.locator("#root")
        visible = _locale_visible_text(loc, "en")
        independent = _element_text_independent(loc, "en")
        assert "Visible EN" in visible
        assert "HIDDEN_NODE_XYZ" not in visible
        # Clone-strip keeps the hidden span's text (visibility not stripped).
        assert "HIDDEN_NODE_XYZ" in independent or independent != visible
        assert hashlib.sha256(visible.encode()).hexdigest() != hashlib.sha256(
            independent.encode()).hexdigest() or "HIDDEN_NODE_XYZ" in independent
        browser.close()
    finally:
        pw.stop()


def _registry_coverage_offenders(registry, manifest) -> list:
    """Covering proof (E-M1 / C-M1 / R1). No page-allowlist.

    table.mq-table is per (page × theme × locale × element_key). Other
    registry rows stay per-page. A row must be observed in ≥1 receipt, or
    carry observed:false and be excluded. MUT-page, MUT-elem, MUT-reg3 and
    MUT-reg4 fail through this helper.
    """
    from collections import defaultdict
    from scripts.capture_macro_command_p5 import _registry_match_selector

    def _norm(s: str) -> str:
        s = s.strip()
        for prefix in ("table.", "ul.", "div.", "ol."):
            if s.startswith(prefix):
                s = s[len(prefix) - 1:]  # keep leading '.'
                break
        return s

    def _scroller_matches(st: dict, sel: str) -> bool:
        sc = str(st.get("scroll_container_selector") or "")
        if sc == sel:
            return True
        sc_key = _registry_match_selector(sc)
        return (
            sc_key == sel
            or _norm(sc) == _norm(sel)
            or sc_key == _registry_match_selector(sel)
        )

    pages_by_sel: dict[str, set[str]] = defaultdict(set)
    table_instances: dict[tuple, dict] = {}
    cells: list[dict] = []
    for page in manifest["pages"]:
        for st in page["states"]:
            if st.get("file"):
                cells.append(st)
            page_id = str(
                st.get("page_id") or page.get("page") or page.get("id") or "")
            theme = st.get("theme")
            locale = st.get("locale")
            for entry in st.get("content_overflows") or []:
                if entry.get("kind") != "scrollport":
                    continue
                key = _registry_match_selector(
                    str(entry.get("nearest_registered_scroller")
                        or entry.get("selector") or ""))
                if key:
                    pages_by_sel[key].add(page_id)
                sel_key = _registry_match_selector(
                    str(entry.get("selector") or ""))
                if sel_key == "table.mq-table":
                    ekey = str(entry.get("element_key") or "")
                    inst = (page_id, theme, locale, ekey)
                    table_instances.setdefault(inst, {
                        "page_id": page_id, "theme": theme,
                        "locale": locale, "element_key": ekey,
                    })
    offenders = []
    for sel, row in registry.items():
        fam = str(row.get("covering_family") or "")
        observed = row.get("observed", True)
        pages = set(pages_by_sel.get(sel) or ())
        if observed is False:
            if pages:
                offenders.append((sel, "observed:false but reported",
                                  sorted(pages)[:4]))
            continue
        if not pages:
            offenders.append((sel, fam, "UNOBSERVED"))
            continue
        if sel == "table.mq-table":
            for inst, meta in table_instances.items():
                page_id, theme, locale, ekey = inst
                if not ekey:
                    offenders.append((sel, fam, page_id, theme, locale,
                                      "missing element_key"))
                    continue
                covering = []
                fits_receipt = False
                for st in cells:
                    if (st.get("family") or "") != fam:
                        continue
                    if str(st.get("page_id") or "") != page_id:
                        continue
                    if st.get("theme") != theme or st.get("locale") != locale:
                        continue
                    if str(st.get("element_key") or "") != ekey:
                        continue
                    if not _scroller_matches(st, sel):
                        continue
                    if st.get("table_fits") is True:
                        sw = float(st.get("scrollWidth") or 0)
                        cw = float(st.get("clientWidth") or 0)
                        if sw <= cw + 1:
                            fits_receipt = True
                            covering.append(st.get("file"))
                        continue
                    if float(st.get("scrollLeft") or 0) <= 0:
                        continue
                    vis = str(st.get("visible_text_at_scroll") or "")
                    zero = str(st.get("visible_text_at_zero") or "")
                    if not vis:
                        continue
                    if zero and vis == zero:
                        continue
                    covering.append(st.get("file"))
                if not covering and not fits_receipt:
                    offenders.append((sel, fam, page_id, theme, locale, ekey))
            continue
        for page_id in pages:
            covering = []
            for st in cells:
                if (st.get("family") or "") != fam:
                    continue
                if str(st.get("page_id") or "") != page_id:
                    continue
                if not _scroller_matches(st, sel):
                    continue
                if float(st.get("scrollLeft") or 0) <= 0:
                    continue
                vis = str(st.get("visible_text_at_scroll") or "")
                zero = str(st.get("visible_text_at_zero") or "")
                if not vis:
                    continue
                if zero and vis == zero:
                    continue
                covering.append(st.get("file"))
            if not covering:
                offenders.append((sel, fam, page_id))
    return offenders


@pytest.mark.needs_full_checkout("mockups")
def test_registry_covering_family_proven_by_manifest() -> None:
    """E-B1: every registry covering_family is proven per page-that-reports."""
    import json
    from scripts.capture_macro_command_p5 import _load_sanctioned_scrollers

    registry = _load_sanctioned_scrollers()
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    offenders = _registry_coverage_offenders(registry, manifest)
    assert not offenders, offenders[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_page_fits_table_complete_and_true() -> None:
    """C-M1: top-level page_fits has 15×4×2×2 rows, all fits:true; MUT-fits fails."""
    import json
    import copy
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    rows = manifest.get("page_fits") or []
    assert len(rows) == 15 * 4 * 2 * 2, len(rows)
    assert all(r.get("fits") is True for r in rows), [
        r for r in rows if not r.get("fits")][:5]
    assert all(r.get("theme") for r in rows), [
        r for r in rows if not r.get("theme")][:5]
    widths = {int(r["width"]) for r in rows}
    locales = {r["locale"] for r in rows}
    themes = {r.get("theme") for r in rows}
    assert widths == {320, 390, 768, 1440}
    assert locales == {"en", "zh"}
    assert themes == {"dark", "light"}
    # MUT-fits: flipping one row to false must be detected.
    planted = copy.deepcopy(rows)
    planted[0]["fits"] = False
    assert any(r.get("fits") is False for r in planted)
    assert not any(r.get("fits") is False for r in rows)


@pytest.mark.needs_full_checkout("mockups")
def test_iframe_coord_space_receipts() -> None:
    """E-m1: iframe cells carry coordSpace/frameInner*/hostFrameOffset."""
    import json
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    bad = []
    for page in manifest["pages"]:
        for st in page["states"]:
            if not st.get("crop"):
                continue
            vw = int(st.get("viewport_width") or 0)
            if st.get("receipt_document") == "iframe" or st.get("coordSpace") == "iframe":
                if st.get("coordSpace") != "iframe":
                    bad.append((st.get("file"), "coordSpace"))
                if st.get("frameInnerWidth") != vw:
                    bad.append((st.get("file"), "frameInnerWidth",
                                st.get("frameInnerWidth"), vw))
                if "frameInnerHeight" not in st:
                    bad.append((st.get("file"), "frameInnerHeight"))
                off = st.get("hostFrameOffset") or {}
                if not isinstance(off, dict) or "x" not in off or "y" not in off:
                    bad.append((st.get("file"), "hostFrameOffset"))
            elif st.get("coordSpace") == "host" or st.get("receipt_document") == "host":
                if int(st.get("innerWidth") or 0) != vw and vw:
                    # Host crops may use tall viewport; width must still match.
                    if int(st.get("innerWidth") or 0) != vw:
                        bad.append((st.get("file"), "host innerWidth",
                                    st.get("innerWidth"), vw))
    assert not bad, bad[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_table_fits_pair_semantics() -> None:
    """C-m3: table_fits False ⇒ end at max scroll; True ⇒ no end + fits."""
    import json
    from scripts.capture_macro_command_p5 import (
        family_for, method_table_filename, parse_method_table_name,
    )
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    by_file = {
        st["file"]: st
        for page in manifest["pages"]
        for st in page["states"]
        if st.get("file")
    }
    starts = [
        st for st in by_file.values()
        if (st.get("family") or family_for(st.get("file") or "")) == "method_table_390"
        and "method_table_390_start-" in str(st.get("file") or "")
    ]
    assert starts
    for start in starts:
        end_name = str(start["file"]).replace(
            "method_table_390_start-", "method_table_390_end-", 1)
        end = by_file.get(end_name)
        if start.get("table_fits") is True:
            assert end is None, start["file"]
            assert float(start.get("scrollWidth") or 0) <= float(
                start.get("clientWidth") or 0) + 1
        else:
            assert end is not None, start["file"]
            sw = float(end.get("scrollWidth") or 0)
            cw = float(end.get("clientWidth") or 0)
            sl = float(end.get("scrollLeft") or 0)
            assert abs(sl - (sw - cw)) <= 1.5 or sl >= max(0.0, sw - cw - 1.5), (
                start["file"], sl, sw, cw)
            # mids (if any) sit strictly between start and end.
            parsed = parse_method_table_name(str(start["file"]))
            if parsed:
                prev_sl = float(start.get("scrollLeft") or 0)
                n = 1
                while True:
                    mid = by_file.get(method_table_filename(
                        f"mid{n}", parsed["slug"], parsed["theme"],
                        parsed["locale"], parsed["width"],
                        element_key=parsed["element_key"]))
                    if mid is None:
                        break
                    mid_sl = float(mid.get("scrollLeft") or 0)
                    assert prev_sl < mid_sl < sl + 1e-9, (
                        start["file"], n, prev_sl, mid_sl, sl)
                    prev_sl = mid_sl
                    n += 1


def test_method_table_filename_roundtrip_includes_element_key() -> None:
    from scripts.capture_macro_command_p5 import (
        method_table_filename, parse_method_table_name,
    )
    name = method_table_filename(
        "end", "macro_rates_curves", "dark", "zh", 390,
        element_key="nth-1")
    parsed = parse_method_table_name(name)
    assert parsed == {
        "pos": "end", "slug": "macro_rates_curves", "element_key": "nth-1",
        "theme": "dark", "locale": "zh", "width": "390",
    }
    mid = method_table_filename(
        "mid1", "macro_financial_conditions", "dark", "en", 390,
        element_key="nth-2")
    parsed_mid = parse_method_table_name(mid)
    assert parsed_mid == {
        "pos": "mid1", "slug": "macro_financial_conditions",
        "element_key": "nth-2", "theme": "dark", "locale": "en",
        "width": "390",
    }


def test_method_table_390_sweep_positions_collapses_or_fills() -> None:
    """V25-1: arithmetic (cw−40) sweep; collapse; halfway mid when needed."""
    from scripts.capture_macro_command_p5 import method_table_390_sweep_positions
    assert method_table_390_sweep_positions(300, 350) == [("start", 0.0)]
    # first step (310) lands past max_sl=250 and half=125 is ≥40 from both
    # ends → mid1 at halfway, not a bare start+end (two crops would miss
    # a middle header under full-containment).
    overshoot = method_table_390_sweep_positions(600, 350)
    assert [p for p, _ in overshoot] == ["start", "mid1", "end"]
    assert overshoot[0][1] == 0.0
    assert overshoot[-1][1] == 250.0
    assert overshoot[1][1] == 125.0
    # tiny overflow: half < 40 → collapse to start+end.
    tiny = method_table_390_sweep_positions(370, 350)
    assert [p for p, _ in tiny] == ["start", "end"]
    assert tiny[-1][1] == 20.0
    # three arithmetic positions: cw=350, step=310, sw=1000, max_sl=650
    # 310 < 650 → mid1@310; 620 < 650 → mid2@620; end@650.
    wide = method_table_390_sweep_positions(1000, 350)
    assert [p for p, _ in wide] == ["start", "mid1", "mid2", "end"]
    assert wide[1][1] == 310.0
    assert wide[2][1] == 620.0
    assert wide[-1][1] == 650.0
    # motivating nth-2 shape: sw=592, cw=328, max_sl=264, step=288 overshoots.
    nth2 = method_table_390_sweep_positions(592, 328)
    assert [p for p, _ in nth2] == ["start", "mid1", "end"]
    assert nth2[-1][1] == 264.0
    assert nth2[1][1] == 132.0
    with pytest.raises(RuntimeError, match=r"scrollport too narrow for sweep"):
        method_table_390_sweep_positions(400, 60, tname="narrow.png")


def test_parse_method_table_name_rejects_keyless() -> None:
    from scripts.capture_macro_command_p5 import parse_method_table_name
    with pytest.raises(RuntimeError, match="element_key"):
        parse_method_table_name(
            "method_table_390_start-macro_rates_curves-dark-zh-390.png")


def test_method_table_pair_ratified_rejects_empty_key() -> None:
    from scripts.capture_macro_command_p5 import (
        _method_table_390_pair_ratified,
    )
    files = [
        "method_table_390_start-macro_rates_curves-dark-en-390.png",
        "method_table_390_end-macro_rates_curves-dark-en-390.png",
    ]
    with pytest.raises(RuntimeError, match="element_key"):
        _method_table_390_pair_ratified(files, [])


def test_method_table_declared_start_floor_is_five_slugs_times_2x2() -> None:
    from scripts.capture_macro_command_p5 import (
        METHOD_TABLE_390_START_FLOOR, METHOD_TABLE_PAGES,
    )
    assert METHOD_TABLE_390_START_FLOOR == len(METHOD_TABLE_PAGES) * 2 * 2
    assert METHOD_TABLE_390_START_FLOOR == 20


def test_assert_method_dl_contained_waits_before_count() -> None:
    import inspect
    from scripts.capture_macro_command_p5 import _assert_method_dl_contained
    src = inspect.getsource(_assert_method_dl_contained)
    wait_at = src.find("wait_for")
    count_at = src.find(".count(")
    assert 0 <= wait_at < count_at, src[:400]


def test_table_fits_branches_on_synthetic_cells() -> None:
    """C-m3 unit: both table_fits branches on synthetic cells."""
    def check(start, end):
        if start.get("table_fits") is True:
            assert end is None
            assert start["scrollWidth"] <= start["clientWidth"] + 1
        else:
            assert end is not None
            assert abs(
                end["scrollLeft"] - (end["scrollWidth"] - end["clientWidth"])
            ) <= 1.0

    check({"table_fits": True, "scrollWidth": 100, "clientWidth": 100}, None)
    check(
        {"table_fits": False, "scrollWidth": 300, "clientWidth": 100},
        {"scrollWidth": 300, "clientWidth": 100, "scrollLeft": 200},
    )


@pytest.mark.needs_full_checkout("mockups")
def test_painted_fraction_present_on_every_cell() -> None:
    """E-m1: painted_fraction on every captured cell.

    Cause lines (from this comment) for the lowest-paint frames:
    - chipmat-*-390/768: suite-nav chip rail is mostly background (pills on a
      dark or light track). The lowest value is often tied across ≥6 cells,
      not a unique five-lowest list.
    - 18/19 viewport frames: empty grid track / min-height under content.
    """
    import json
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    cells = [
        st
        for page in manifest["pages"]
        for st in page["states"]
        if st.get("file") and st.get("captured")
    ]
    missing = [st.get("file") for st in cells if "painted_fraction" not in st]
    assert not missing, missing[:12]
    for st in cells:
        assert 0.0 <= float(st["painted_fraction"]) <= 1.0, st.get("file")
    sorted_cells = sorted(cells, key=lambda st: float(st["painted_fraction"]))
    lowest_val = float(sorted_cells[0]["painted_fraction"])
    tied = [
        st for st in sorted_cells
        if abs(float(st["painted_fraction"]) - lowest_val) < 1e-9
    ]
    print(
        f"painted_fraction lowest {lowest_val:.4f} tied by {len(tied)} cells",
        flush=True)
    causes = {
        "18-dark-en-1440.png": (
            "empty grid track / min-height under content; first-screen canvas "
            "is taller than the content"),
        "18b-dark-zh-1440.png": "same empty grid track on the ZH twin",
        "19-light-en-1440.png": "same empty grid track in light",
        "19b-light-zh-1440.png": "same empty grid track in light ZH",
    }
    printed = []
    for st in tied:
        name = str(st.get("file") or "")
        cause = causes.get(name)
        if cause is None and name.startswith("chipmat-"):
            cause = (
                "chip rail crop is mostly background (pills on a dark/light "
                "track)")
        if cause is None and not st.get("crop"):
            cause = (
                "viewport/full-page canvas includes empty grid track below "
                "content")
        if cause is None:
            h = (st.get("raw_box") or {}).get("height")
            cause = f"family={st.get('family')} crop h={h}"
        line = (
            f"painted_fraction {float(st['painted_fraction']):.4f} {name}: "
            f"{cause}"
        )
        print(line, flush=True)
        printed.append(line)
    undocumented = [
        str(st.get("file") or "")
        for st in tied
        if str(st.get("file") or "") not in causes
        and not str(st.get("file") or "").startswith("chipmat-")
        and st.get("crop")
    ]
    assert not undocumented, (
        "painted_fraction lowest-tie cells missing a documented cause",
        undocumented[:8])
    assert len(printed) == len(tied), (len(printed), len(tied), printed)


def test_page_overflow_error_type() -> None:
    from scripts.capture_macro_command_p5 import PageOverflowError
    err = PageOverflowError("macro_monetary.html", 390, 420.0)
    assert err.route == "macro_monetary.html"
    assert err.width == 390
    assert err.scroll_width == 420.0


def test_shot_raises_on_multi_match_selector() -> None:
    """C-n1: plant two matching nodes; _shot raises by behaviour."""
    from pathlib import Path
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed")
    from scripts.capture_macro_command_p5 import _shot
    try:
        pw = sync_playwright().start()
    except Exception as exc:
        pytest.skip(f"Playwright runtime unavailable: {exc}")
    dest = ROOT / "mockups" / "evidence" / "macro-command-p5" / "_mut_multi.png"
    try:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium unavailable: {exc}")
        page = browser.new_page(viewport={"width": 400, "height": 300})
        page.set_content(
            """<html><body>
                 <div class="dup-crop">one</div>
                 <div class="dup-crop">two</div>
               </body></html>"""
        )
        with pytest.raises(RuntimeError, match=r"matched 2") as ei:
            _shot(dest, page, page.locator(".dup-crop"),
                  selector=".dup-crop", locale="en")
        assert "never .first" in str(ei.value) or "exactly one" in str(ei.value)
        browser.close()
    finally:
        pw.stop()
        dest.unlink(missing_ok=True)


def test_mq_table_path_nth_of_type_uses_same_tag_index() -> None:
    """V23-FIX0: mixed-tag siblings; built path resolves back to the same node."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright not installed")
    from scripts.capture_macro_command_p5 import _mq_table_path_eval_js
    try:
        pw = sync_playwright().start()
    except Exception as exc:
        pytest.skip(f"Playwright runtime unavailable: {exc}")
    try:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium unavailable: {exc}")
        page = browser.new_page()
        # Mixed-tag siblings: all-children index of tbl-scroll is 4
        # (h2, div, span, div.tbl-scroll) but same-tag nth-of-type is 2.
        page.set_content(
            """<html><body>
                 <div id="host">
                   <p class="note">note</p>
                   <span class="gap">gap</span>
                   <section class="mq-changed">
                     <h2>x</h2>
                     <div class="pad">pad</div>
                     <span class="y">y</span>
                     <div class="tbl-scroll">
                       <table class="mq-table" data-k="t1"><tr><td>a</td></tr></table>
                     </div>
                   </section>
                 </div>
               </body></html>"""
        )
        path_js = _mq_table_path_eval_js()
        loc = page.locator("table.mq-table")
        built = loc.evaluate(path_js)
        assert built, built
        n = page.locator(built).count()
        assert n == 1, (built, n)
        resolved = page.locator(built).evaluate(
            "el => el.getAttribute('data-k')")
        assert resolved == "t1", (built, resolved)
        assert ":nth-of-type(" in built, built
        assert "div.tbl-scroll:nth-of-type(2)" in built.replace(" ", ""), (
            "same-tag index must be 2, not all-children 4", built)
        wrong = built.replace(
            "div.tbl-scroll:nth-of-type(2)",
            "div.tbl-scroll:nth-of-type(4)")
        assert page.locator(wrong).count() == 0, (wrong, built)
        browser.close()
    finally:
        pw.stop()


def test_page_fits_overflow_writes_false_and_raises() -> None:
    """C-n2: synthetic overflow writes fits:false AND raises; true path keeps True."""
    from scripts.capture_macro_command_p5 import (
        PageOverflowError, _commit_page_fits_row, _page_fits_receipt,
    )
    overflow = _page_fits_receipt(
        {"page_scroll_width": 500, "innerWidth": 390, "page_fits": False},
        route="macro_monetary.html", width=390, locale="en", theme="light",
    )
    assert overflow["fits"] is False
    assert overflow["theme"] == "light"
    recorded = [overflow]
    with pytest.raises(PageOverflowError) as ei:
        _commit_page_fits_row(overflow)
    assert recorded[0]["fits"] is False
    assert ei.value.scroll_width == 500.0
    ok = _page_fits_receipt(
        {"page_scroll_width": 390, "innerWidth": 390, "page_fits": True},
        route="macro_monetary.html", width=390, locale="zh", theme="dark",
    )
    assert ok["fits"] is True
    assert ok["theme"] == "dark"
    assert _commit_page_fits_row(ok)["fits"] is True


def test_painted_fraction_raises_without_libs(monkeypatch) -> None:
    """C-n3: missing Pillow/numpy raises; receipt is never defaulted to 1.0."""
    from pathlib import Path
    from scripts import capture_macro_command_p5 as cap

    def no_libs():
        raise ImportError("plant")

    monkeypatch.setattr(cap, "_paint_libs", no_libs)
    with pytest.raises(RuntimeError, match="never defaulted"):
        cap._painted_fraction(Path("/tmp/x.png"))


@pytest.mark.needs_full_checkout("mockups")
def test_mut_page_deleting_one_reporting_pages_table_cells_fails() -> None:
    """MUT-page: delete all method_table_390 cells of one reporting page → fail."""
    import copy
    import json
    from scripts.capture_macro_command_p5 import _load_sanctioned_scrollers

    registry = _load_sanctioned_scrollers()
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    planted = copy.deepcopy(manifest)
    victim = "macro_rates_curves.html"
    for page in planted["pages"]:
        page["states"] = [
            st for st in page["states"]
            if not (
                st.get("family") == "method_table_390"
                and st.get("page_id") == victim
            )
        ]
    offenders = _registry_coverage_offenders(registry, planted)
    assert any(
        o[0] == "table.mq-table" and (o[2] if len(o) > 2 else "") == victim
        for o in offenders
    ), offenders[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_mut_elem_deleting_one_instance_on_a_two_instance_page_fails() -> None:
    """MUT-elem: delete ONE instance's cells, keep the other → fail."""
    import copy
    import json
    from collections import defaultdict
    from scripts.capture_macro_command_p5 import _load_sanctioned_scrollers

    registry = _load_sanctioned_scrollers()
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    keys_by_page: dict[str, set[str]] = defaultdict(set)
    for page in manifest["pages"]:
        for st in page["states"]:
            if st.get("family") != "method_table_390":
                continue
            ekey = str(st.get("element_key") or "")
            if ekey:
                keys_by_page[str(st.get("page_id") or "")].add(ekey)
    victim_page, keys = next(
        ((p, ks) for p, ks in keys_by_page.items() if len(ks) >= 2),
        ("", set()),
    )
    assert victim_page and len(keys) >= 2, dict(keys_by_page)
    drop_key = sorted(keys)[0]
    keep_key = sorted(keys)[1]
    planted = copy.deepcopy(manifest)
    for page in planted["pages"]:
        page["states"] = [
            st for st in page["states"]
            if not (
                st.get("family") == "method_table_390"
                and st.get("page_id") == victim_page
                and st.get("element_key") == drop_key
            )
        ]
    remaining = {
        st.get("element_key")
        for page in planted["pages"]
        for st in page["states"]
        if st.get("family") == "method_table_390"
        and st.get("page_id") == victim_page
    }
    assert keep_key in remaining
    assert drop_key not in remaining
    offenders = _registry_coverage_offenders(registry, planted)
    assert any(
        o[0] == "table.mq-table"
        and (o[2] if len(o) > 2 else "") == victim_page
        and (o[5] if len(o) > 5 else "") == drop_key
        for o in offenders
    ), offenders[:16]


def _overflow_census_key_offenders(manifest, probes) -> list:
    """Per page × theme × locale: overflow-entry keys == census keys == cell keys."""
    from collections import defaultdict
    from scripts.capture_macro_command_p5 import _registry_match_selector

    census = probes.get("mq_table_census") or {}
    overflow: dict[tuple, set[str]] = defaultdict(set)
    cells: dict[tuple, set[str]] = defaultdict(set)
    for page in manifest["pages"]:
        for st in page["states"]:
            w = st.get("viewport_width") or st.get("viewport")
            if str(w) not in {"390", "mobile"} and w != 390:
                continue
            page_id = str(st.get("page_id") or page.get("page") or "")
            theme = st.get("theme")
            locale = st.get("locale")
            combo = (page_id, theme, locale)
            if (
                st.get("family") == "method_table_390"
                and st.get("element_key")
                and st.get("table_fits") is not True
            ):
                cells[combo].add(str(st["element_key"]))
            for entry in st.get("content_overflows") or []:
                sel = _registry_match_selector(
                    str(entry.get("selector") or ""))
                if sel != "table.mq-table":
                    continue
                ekey = str(entry.get("element_key") or "")
                if ekey:
                    overflow[combo].add(ekey)
    offenders = []
    combos = set(overflow) | set(cells)
    for combo in sorted(combos, key=lambda c: (str(c[0]), str(c[1]), str(c[2]))):
        page_id, theme, locale = combo
        slug = str(page_id).replace(".html", "")
        census_rows = census.get(f"{slug}-{theme}-{locale}") or []
        census_overflow = {
            str(r.get("element_key") or "")
            for r in census_rows
            if r.get("overflowing") and r.get("element_key")
        }
        ov = overflow.get(combo) or set()
        cell_keys = cells.get(combo) or set()
        if ov != census_overflow:
            offenders.append((combo, "overflow!=census",
                              sorted(ov), sorted(census_overflow)))
        if cell_keys != census_overflow:
            offenders.append((combo, "cells!=census",
                              sorted(cell_keys), sorted(census_overflow)))
    return offenders


@pytest.mark.needs_full_checkout("mockups")
def test_overflow_entry_keys_match_census_keys() -> None:
    """V23-m2: overflow-entry key set == census overflowing keys per combo."""
    import json
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "probes.json")
        .read_text(encoding="utf-8"))
    offenders = _overflow_census_key_offenders(manifest, probes)
    assert not offenders, offenders[:12]


def _method_table_390_family_offenders(manifest) -> list:
    """Pair semantics: start + zero-or-more mids + end; end at sw−cw."""
    from collections import defaultdict
    from scripts.capture_macro_command_p5 import (
        method_table_390_sweep_positions, parse_method_table_name,
    )
    families: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for page in manifest["pages"]:
        for st in page["states"]:
            parsed = parse_method_table_name(str(st.get("file") or ""))
            if not parsed:
                continue
            key = (
                parsed["slug"], parsed["element_key"], parsed["theme"],
                parsed["locale"], parsed["width"],
            )
            families[key][parsed["pos"]] = st
    offenders = []
    for key, by_pos in families.items():
        start = by_pos.get("start")
        if start is None:
            offenders.append((key, "missing start", sorted(by_pos)))
            continue
        sw = float(start.get("scrollWidth") or 0)
        cw = float(start.get("clientWidth") or 0)
        if start.get("table_fits") is True:
            extra = sorted(p for p in by_pos if p != "start")
            if extra:
                offenders.append((key, "fits family has extra pos", extra))
            continue
        expected = [
            p for p, _ in method_table_390_sweep_positions(sw, cw)]
        got = ["start"] if "start" in by_pos else []
        n = 1
        while f"mid{n}" in by_pos:
            got.append(f"mid{n}")
            n += 1
        stray = sorted(
            p for p in by_pos if p.startswith("mid") and p not in got)
        if stray:
            offenders.append((key, "gapped mids", stray, list(got)))
        if "end" in by_pos:
            got.append("end")
        if got != expected:
            offenders.append((key, "pos set != sweep", list(got), expected))
        end = by_pos.get("end")
        if end is None:
            offenders.append((key, "missing end without table_fits"))
            continue
        end_sl = float(end.get("scrollLeft") or 0)
        max_sl = max(
            0.0,
            float(end.get("scrollWidth") or sw)
            - float(end.get("clientWidth") or cw),
        )
        if abs(end_sl - max_sl) > 1.5 and end_sl < max_sl - 1.5:
            offenders.append((key, "end not at sw-cw", end_sl, max_sl))
        prev = float(start.get("scrollLeft") or 0)
        for pos in got[1:]:
            sl = float(by_pos[pos].get("scrollLeft") or 0)
            if not (sl > prev):
                offenders.append(
                    (key, "scrollLeft not strictly increasing", pos, prev, sl))
            prev = sl
    return offenders


@pytest.mark.needs_full_checkout("mockups")
def test_method_table_390_family_shape() -> None:
    """V25-2: overflowing family = start + 0-N mids + end; mids increasing."""
    import json
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    offenders = _method_table_390_family_offenders(manifest)
    assert not offenders, offenders[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_mut_mid_deleting_one_mid_from_three_position_table_fails() -> None:
    """MUT-mid: delete one mid cell from a ≥3-position table → family-shape fails."""
    import copy
    import json
    from collections import defaultdict
    from scripts.capture_macro_command_p5 import parse_method_table_name

    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    families: dict[tuple, list] = defaultdict(list)
    for page in manifest["pages"]:
        for st in page["states"]:
            parsed = parse_method_table_name(str(st.get("file") or ""))
            if not parsed:
                continue
            key = (
                parsed["slug"], parsed["element_key"], parsed["theme"],
                parsed["locale"], parsed["width"],
            )
            families[key].append((parsed["pos"], st.get("file")))
    victim = None
    drop_file = None
    for key, members in families.items():
        poss = {p for p, _ in members}
        mids = sorted(p for p in poss if p.startswith("mid"))
        if "start" in poss and "end" in poss and mids:
            victim = key
            drop_pos = mids[0]
            drop_file = next(fn for p, fn in members if p == drop_pos)
            break
    assert victim and drop_file, (
        "MUT-mid needs a ≥3-position table; none in manifest",
        {k: [p for p, _ in v] for k, v in list(families.items())[:8]},
    )
    planted = copy.deepcopy(manifest)
    for page in planted["pages"]:
        page["states"] = [
            st for st in page["states"] if st.get("file") != drop_file
        ]
    offenders = _method_table_390_family_offenders(planted)
    assert offenders, (victim, drop_file)


@pytest.mark.needs_full_checkout("mockups")
def test_mut_key_fabricated_element_key_fails() -> None:
    """MUT-key: rename one cell's element_key; census==overflow test catches it."""
    import copy
    import json

    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    probes = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "probes.json")
        .read_text(encoding="utf-8"))
    planted = copy.deepcopy(manifest)
    victim = None
    for page in planted["pages"]:
        for st in page["states"]:
            if st.get("family") != "method_table_390":
                continue
            if not st.get("element_key"):
                continue
            if st.get("table_fits") is True:
                continue
            st["element_key"] = "fabricated-key"
            victim = st
            break
        if victim is not None:
            break
    assert victim is not None
    offenders = _overflow_census_key_offenders(planted, probes)
    assert any(
        "cells!=census" in str(row) or "fabricated-key" in str(row)
        for row in offenders
    ), offenders[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_method_table_cells_record_census_path_and_shot_visibility() -> None:
    import json
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    missing = []
    for page in manifest["pages"]:
        for st in page["states"]:
            if st.get("family") != "method_table_390":
                continue
            if not st.get("census_path"):
                missing.append((st.get("file"), "census_path"))
            if st.get("visible_at_shot") is not True:
                missing.append((st.get("file"), "visible_at_shot"))
            if st.get("revealed"):
                if st.get("openedBy") != "reveal":
                    missing.append((st.get("file"), "openedBy"))
                if "reveal" not in str(st.get("verified_how") or "").lower():
                    missing.append((st.get("file"), "verified_how"))
                if not st.get("reveal_ancestors"):
                    missing.append((st.get("file"), "reveal_ancestors"))
    assert not missing, missing[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_mut_cov_stored_y_coverage_mismatch_fails() -> None:
    """MUT-cov: stored y_coverage ≠ recomputed (±1e-9) must fail."""
    import copy
    import json

    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    planted = copy.deepcopy(manifest)
    victim = None
    for page in planted["pages"]:
        for st in page["states"]:
            if not st.get("crop") or st.get("grid") == "short":
                continue
            raw = st.get("raw_box") or {}
            if float(raw.get("height") or 0) < 40:
                continue
            if "y_coverage" not in st or not (st.get("occlusionSamples") or []):
                continue
            st["y_coverage"] = float(st["y_coverage"]) - 0.5
            victim = st
            break
        if victim is not None:
            break
    assert victim is not None
    bad = _y_coverage_offenders(planted)
    assert any(
        row[0] == victim.get("file") and row[1] == "stored!=recomputed"
        for row in bad
    ), bad[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_mut_reg4_split_compact_alias_fails() -> None:
    """MUT-reg4: re-split table.mq-table.mq-table-compact as observed → fail."""
    import copy
    import json
    from scripts.capture_macro_command_p5 import _load_sanctioned_scrollers

    registry = copy.deepcopy(_load_sanctioned_scrollers())
    registry["table.mq-table.mq-table-compact"] = {
        "kind": "table",
        "covering_family": "method_table_390",
        "reason": "MUT-reg4 split alias must fail coverage",
        "observed": True,
    }
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    offenders = _registry_coverage_offenders(registry, manifest)
    assert any(
        o[0] == "table.mq-table.mq-table-compact" for o in offenders
    ), offenders[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_mut_reg3_fabricated_unobserved_row_fails() -> None:
    """MUT-reg3: schema-valid fabricated row with no receipts must fail."""
    import copy
    import json
    from scripts.capture_macro_command_p5 import _load_sanctioned_scrollers

    registry = copy.deepcopy(_load_sanctioned_scrollers())
    registry["div.fake-rail"] = {
        "kind": "designed-rail",
        "covering_family": "chip_material",
        "reason": "schema-valid fabricated row for MUT-reg3 coverage",
        "observed": True,
    }
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    offenders = _registry_coverage_offenders(registry, manifest)
    assert any(o[0] == "div.fake-rail" for o in offenders), offenders[:12]


@pytest.mark.needs_full_checkout("mockups")
def test_pair_families_drop_end_when_fits() -> None:
    """E-n1: when the scroller fits, the end crop is not taken; flag consulted."""
    import json
    from scripts.capture_macro_command_p5 import family_for

    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    by_file = {
        st["file"]: st
        for page in manifest["pages"]
        for st in page["states"]
        if st.get("file")
    }
    hub_starts = [
        st for st in by_file.values()
        if (st.get("family") or family_for(st.get("file") or "")) == "hub_rail"
        and str(st.get("file") or "").endswith("-start.png")
    ]
    assert hub_starts
    for start in hub_starts:
        end_name = str(start["file"]).replace("-start.png", "-end.png", 1)
        end = by_file.get(end_name)
        if start.get("fits") is True:
            assert end is None, start["file"]
            assert float(start.get("scrollWidth") or 0) <= float(
                start.get("clientWidth") or 0) + 1
        else:
            assert end is not None, start["file"]


@pytest.mark.needs_full_checkout("mockups")
def test_no_unlisted_identical_png_pairs() -> None:
    """E-n1: no identical pair may exist unlisted (allowlist / fits flag)."""
    import json
    from collections import defaultdict
    from scripts.capture_macro_command_p5 import _crop_collision_ratified

    root = ROOT / "mockups" / "evidence" / "macro-command-p5"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    probes = json.loads((root / "probes.json").read_text(encoding="utf-8"))
    by_sha: dict[str, list[str]] = defaultdict(list)
    for page in manifest["pages"]:
        for st in page["states"]:
            if st.get("captured") and st.get("sha256") and st.get("file"):
                by_sha[st["sha256"]].append(st["file"])
    illegal = {}
    for sha, files in by_sha.items():
        uniq = sorted(set(files))
        if len(uniq) < 2:
            continue
        if not _crop_collision_ratified(uniq, probes, manifest["pages"]):
            illegal[sha] = uniq
    assert not illegal, illegal
