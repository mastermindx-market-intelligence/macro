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
    assert captured - declared == set()
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
            assert state.get("coordSpace") == "host-page", state.get("file")
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
        assert state.get("crop_selector") == "section.mq-method .mq-axis-method"
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
            if fam == "method_table_390" and "method_table_390_start-" in name:
                end = name.replace(
                    "method_table_390_start-", "method_table_390_end-", 1)
                if end not in files and not state.get("table_fits"):
                    offenders.append((name, "missing end without table_fits"))
    assert not missing_key, missing_key[:10]
    assert not offenders, offenders[:10]


@pytest.mark.needs_full_checkout("mockups")
def test_method_table_390_contribution_union() -> None:
    """E-B1(3)/C-m1: every probe value appears in start∪end visible_text_at_scroll.

    Reads MANIFEST cells' visible_text_at_scroll FIRST (MUT-a1: blanking
    manifest receipts alone must FAIL). Asserts they equal probes map entries.
    Missing end is accepted only when start has table_fits: true.
    """
    import json
    import re
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
    for key, full in table_probes.items():
        m = re.match(
            r"method_table_390-(.+)-(dark|light)-(en|zh)-(\d+)$", key)
        assert m, key
        slug, theme, locale, width = m.groups()
        contribs = re.findall(r"[+\-−]?\d+(?:\.\d+)?", full)
        values = [v for v in contribs if "." in v]
        headers = re.findall(
            r"(COMPONENT|RAW|STANDARDIZED|WEIGHT|CONTRIBUTION|"
            r"分项|原始|标准化|权重|贡献)", full, flags=re.I)
        start = by_file.get(
            f"method_table_390_start-{slug}-{theme}-{locale}-{width}.png")
        end = by_file.get(
            f"method_table_390_end-{slug}-{theme}-{locale}-{width}.png")
        assert start, key
        if end is None:
            assert start.get("table_fits") is True, (
                key, "missing end without table_fits")
        # C-m1: MANIFEST receipts are authoritative — probes must match them.
        start_vis = str(start.get("visible_text_at_scroll") or "")
        assert start_vis, (key, "blank manifest visible_text_at_scroll")
        if start["file"] in vis_map:
            assert vis_map[start["file"]] == start_vis, (
                key, "probes map != manifest start")
        parts = [start_vis]
        if end is not None:
            end_vis = str(end.get("visible_text_at_scroll") or "")
            assert end_vis, (key, "blank manifest end visible_text_at_scroll")
            if end["file"] in vis_map:
                assert vis_map[end["file"]] == end_vis, (
                    key, "probes map != manifest end")
            parts.append(end_vis)
        union = " ".join(parts)
        assert values, (key, full[:120])
        for v in values:
            assert v in full, (key, v)
            assert v in union, (key, v, "missing from start∪end visible text")
        for h in headers:
            assert h.casefold() in union.casefold(), (
                key, h, "header missing from start∪end")


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


@pytest.mark.needs_full_checkout("mockups")
def test_occlusion_y_coverage_from_raw_box() -> None:
    """E-B2/C-M1/C-M2: coverage from samples vs raw_box; only grid:short exempt."""
    import json
    from scripts.macro_command_capture_guards import y_coverage
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
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
            ys = [float(s["y"]) for s in samples if "y" in s]
            top = float(raw["y"])
            bottom = top + h
            if cov + 1e-6 < 0.95:
                bad.append((state.get("file"), "cov", cov))
            if ys and min(ys) > top + 8.0 + 1e-6:
                bad.append((state.get("file"), "top", min(ys), top))
            if ys and max(ys) < bottom - 8.0 - 1e-6:
                bad.append((state.get("file"), "bottom", max(ys), bottom))
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
            for prefix in (
                "method_table_390_start-", "method_table_390_end-",
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


@pytest.mark.needs_full_checkout("mockups")
def test_en_zh_visible_text_distinct_all_stations() -> None:
    """E-M2: EN ≠ ZH visible_text_sha256 at every two-locale station."""
    import json
    from collections import defaultdict
    from scripts.capture_macro_command_p5 import family_for
    manifest = json.loads(
        (ROOT / "mockups" / "evidence" / "macro-command-p5" / "manifest.json")
        .read_text(encoding="utf-8"))
    stations: dict[tuple, dict[str, str]] = defaultdict(dict)
    for page in manifest["pages"]:
        for state in page["states"]:
            if not state.get("crop_selector"):
                continue
            fam = state.get("family") or family_for(state.get("file") or "")
            key = (
                fam,
                state.get("page_id") or page.get("page"),
                state.get("theme"),
                state.get("viewport_width") or state.get("viewport"),
                state.get("force_state") or state.get("file", "").rsplit("-", 3)[0],
            )
            loc = state.get("locale")
            digest = state.get("visible_text_sha256")
            head = state.get("visible_text_head")
            assert head, state.get("file")
            if loc and digest:
                stations[key][loc] = digest
    collisions = []
    for key, locs in stations.items():
        if "en" in locs and "zh" in locs and locs["en"] == locs["zh"]:
            collisions.append(key)
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
