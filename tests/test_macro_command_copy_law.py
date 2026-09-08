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
    "Source receipt",
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
    openings = len(re.findall(r'<(?:button|a)[^>]*class="mc-analyst"', main))
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
>>>>>>> b5110b24fa45 (Macro Command P5: copy-law sweep, analyst wiring, evidence matrix)


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
