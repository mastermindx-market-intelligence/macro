"""Tests for scripts/build_stage_analysis_page.py (SGA Wave 3 page).

Verifies:
1. Full-data render from the demo fixture (no crash, no unrendered braces).
2. Warm-up render when the artifact is absent (page still builds, honest empty
   states — a missing input never crashes a build).
3. House-law / doctrine checks on the rendered HTML: nav present, padding-top,
   no 'validated', <title> plain-EN, bilingual l-en/l-zh parity, no title=
   bilingual leak, no svg-span-breakout, no raw earnings-tag slugs on Tier 1.
4. Signature + product elements present (stage arc, micro-arc glyphs, stances).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "stage_page_demo.json"

sys.path.insert(0, str(REPO))

from scripts.build_stage_analysis_page import _copy_stagedata, render  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _render_with_fixture() -> str:
    return render(REPO, fixture=FIXTURE)


def _render_warmup() -> str:
    """Render with no artifact (warm-up state)."""
    return render(REPO, fixture=Path("/nonexistent/path/stage_page_demo.json"))


# ---------------------------------------------------------------------------
# fixture validity
# ---------------------------------------------------------------------------

def test_fixture_is_valid_json_and_rich():
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert raw.get("schema") == "stage_context.v1"
    assert len(raw.get("top_stage2", [])) >= 25, "fixture must be rich (>=25 fresh names)"


# ---------------------------------------------------------------------------
# full-data render (fixture)
# ---------------------------------------------------------------------------

def test_fixture_renders_without_crash():
    html = _render_with_fixture()
    assert len(html) > 50_000


def test_no_unrendered_jinja_braces():
    """No leftover {{ }} or {% %} in the output (render actually completed)."""
    html = _render_with_fixture()
    assert "{{" not in html
    assert "{%" not in html


def test_stage_arc_signature_present():
    """The signature stage arc SVG + its stage numerals render."""
    html = _render_with_fixture()
    assert 'id="arc-wrap"' in html
    assert "drawArc" in html  # the JS signature-arc builder draws the four seasons


def test_stage_board_client_rendered_with_stage_chips():
    """v2 Stage Board renders client-side (rows load from site/stagedata) and uses
    stage chips; the arc is a once-drawn hero signature, not a per-row glyph."""
    html = _render_with_fixture()
    assert 'data-tab="board"' in html
    assert "stagechip" in html


def test_stance_vocabulary_only_from_doctrine():
    """Every stance shown is from the doctrine six; the banned old-style states
    (no-stance) never appear.  We assert the doctrine words are present."""
    html = _render_with_fixture()
    assert "Watch — don" in html  # "Watch — don't chase"
    assert "Protect gains" in html
    assert "Stand aside" in html
    assert "In favour" in html


def test_no_warmup_divs_with_full_fixture():
    html = _render_with_fixture()
    assert html.count('class="warmup"') == 0


def test_earnings_tag_slugs_prettified():
    """Raw taxonomy slugs are mapped to plain words via TAG_META/tagLabel.  A slug
    may appear as a JS map key, but the prettify mechanism must exist so a slug is
    never rendered raw to the user (DESIGN_DOCTRINE Law 2)."""
    html = _render_with_fixture()
    assert "TAG_META" in html
    assert "tagLabel" in html


# ---------------------------------------------------------------------------
# warm-up render (absent artifact)
# ---------------------------------------------------------------------------

def test_warmup_renders_without_crash():
    html = _render_warmup()
    assert len(html) > 5_000


def test_warmup_shows_honest_empty_states():
    """Warm-up must render honest plain-word empty states, not crash."""
    html = _render_warmup()
    assert 'class="empty"' in html
    assert "runs tonight" in html.lower() or "warming up" in html.lower()


def test_warmup_still_has_nav_and_footer():
    html = _render_warmup()
    assert "nav-mega" in html  # nav still included
    assert "never a buy signal" in html.lower()  # footer honesty survives


# ---------------------------------------------------------------------------
# house-law / doctrine checks
# ---------------------------------------------------------------------------

def test_nav_mega_marker_present():
    """Site nav (single-source mega menu) is included."""
    html = _render_with_fixture()
    assert "nav-mega" in html


def test_nav_gap_padding_top_ge_14px():
    html = _render_with_fixture()
    m = re.search(r"padding-top:\s*(\d+)", html)
    assert m, "no padding-top found in rendered HTML"
    assert int(m.group(1)) >= 14, f"padding-top too small: {m.group(0)}"


def test_uses_canonical_san_francisco_inter_stack_only():
    """Stage Analysis must not introduce a page-specific webfont.

    Apple platforms use San Francisco via -apple-system; self-hosted Inter is
    the cross-platform fallback used across the main Mastermind experience.
    """
    html = _render_with_fixture()
    assert "Space Grotesk" not in html
    assert "fonts.googleapis.com" not in html
    assert "--font-display:-apple-system,BlinkMacSystemFont,'SF Pro Display',Inter" in html
    assert "font:14px/1.5 var(--font-display)" in html


def test_title_is_plain_english():
    """<title> RCDATA must be plain EN — no t()/td() markup, no CJK
    (title RCDATA plain-EN sweep, #2705/#2724)."""
    html = _render_with_fixture()
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    assert m, "no <title> found"
    title = m.group(1)
    assert "<span" not in title, "markup leaked into <title>"
    assert not re.search(r"[一-鿿]", title), "CJK in <title>"


def test_no_validated_claim():
    html = _render_with_fixture()
    assert "validated" not in html.lower()


def test_no_title_attr_bilingual_leak():
    """title= attributes must not contain <span> markup (CI-guarded)."""
    html = _render_with_fixture()
    assert not re.search(r'title="[^"]*<span', html)


def test_no_svg_text_span_breakout():
    """No <span> inside <svg><text> (svg-span-breakout LETHAL trap)."""
    html = _render_with_fixture()
    assert not re.search(r"<text[^>]*>[^<]*<span", html)


def test_bilingual_parity():
    """Both languages present, and equal span counts (every EN has a ZH twin)."""
    html = _render_with_fixture()
    en = html.count('class="l-en"')
    zh = html.count('class="l-zh"')
    assert en > 100
    assert en == zh, f"bilingual parity broken: {en} l-en vs {zh} l-zh"


def test_l_zh_spans_present():
    html = _render_with_fixture()
    assert 'class="l-zh"' in html


def test_footer_plain_word_null_disclosure():
    """Footer states the context/null in plain words (doctrine Law 5)."""
    html = _render_with_fixture()
    assert "never a buy signal or a sizing input" in html


def test_earnings_no_call_honest_null():
    """Names with no analyzed call show the honest plain-word null."""
    html = _render_with_fixture()
    assert "No earnings" in html  # honest plain-word empty state for the earnings surface


def test_earnings_reader_links_to_terminal_company_intelligence():
    """The cross-sectional Stage reader hands a selected ticker to the full Terminal dossier."""
    html = _render_with_fixture()
    assert 'id="reader-terminal"' in html
    assert "https://app.mastermind-x.com/analysis?symbol=" in html
    assert "&page=intelligence" in html


def test_no_css_width_over_100pct():
    """FIX 2 — no rendered `width: N%` exceeds 100%. Guards against the sector
    weather double-×100 unit bug (pct_stage2 is already 0-100)."""
    html = _render_with_fixture()
    widths = re.findall(r"width:\s*(\d+(?:\.\d+)?)%", html)
    assert widths, "expected at least one percentage width in the rendered page"
    over = [w for w in widths if float(w) > 100.0]
    assert not over, f"CSS width exceeds 100%: {over}"


# ---------------------------------------------------------------------------
# Wave 8 — market-weather branch reachability
# ---------------------------------------------------------------------------
def _render_weather(tmp_path: Path, weather: str) -> str:
    """Render the hero with a synthetic market.weather value."""
    base = json.loads(FIXTURE.read_text())
    base.setdefault("market", {})["weather"] = weather
    fx = tmp_path / f"weather_{weather}.json"
    fx.write_text(json.dumps(base))
    return render(REPO, fixture=fx)


def test_deteriorating_weather_renders_the_declining_stance(tmp_path):
    """`_weather()` emits 'deteriorating'; the hero must render the STAND-ASIDE
    copy for it.

    Regression pin: the template branched on 'declining', a value the engine
    never emits, so the branch was dead and a deteriorating market fell through
    to the 'mixed' copy — telling the user to "pick spots" while >=40% of names
    sat in Stage 4. The wrong-way assertion is the point: rendering 'mixed' for
    a deteriorating tape is the defect, not a formatting nit.
    """
    html = _render_weather(tmp_path, "deteriorating")
    # "Downtrends dominate" is unique to the hero's declining stance; the bare
    # words "Stand aside" also live in the client-side stage-label map, which
    # renders regardless of weather, so they cannot discriminate the branch.
    assert "Downtrends dominate" in html, (
        "deteriorating weather must render the declining/stand-aside hero")
    assert "No clear season" not in html, (
        "deteriorating weather fell through to the 'mixed' stance copy")


def test_mixed_weather_still_renders_the_mixed_stance(tmp_path):
    html = _render_weather(tmp_path, "mixed")
    assert "No clear season" in html
    assert "Downtrends dominate" not in html


def test_advancing_weather_still_renders_the_advancing_stance(tmp_path):
    html = _render_weather(tmp_path, "advancing")
    assert "Good weather for fresh breakouts" in html
    assert "No clear season" not in html
    assert "Downtrends dominate" not in html


def test_no_target_week_renders_unavailable_not_warming_up(tmp_path):
    """Acceptance gate §2.4: a MATURE-lane failure (no completed Stage week could
    be resolved) must never be described as a first run.

    "Warming up" is honest copy only when there is no artifact at all. Here the
    artifact exists and is well-formed — it just has no current cross-sectional
    authority — so the page must say so. Asserting the ABSENCE of the warm-up
    string is the whole point of the test.
    """
    base = json.loads(FIXTURE.read_text())
    base["target_stage_week"] = None
    base.setdefault("market", {})["weather"] = None
    base["counts"] = {k: None for k in (base.get("counts") or {"total": None})}
    base["population"] = {
        "status": "no_target_week", "target_stage_week": None,
        "target_week_source": "unresolved", "spy_stage_week": None,
        "population_modal_week": None,
        "current": 0, "stale": 0, "unknown": 2741, "total": 2741,
        "current_coverage_pct": None, "data_session": None,
        "week_histogram": [], "issues": ["no_target_week"],
    }
    fx = tmp_path / "no_target_week.json"
    fx.write_text(json.dumps(base))
    html = render(REPO, fixture=fx)

    assert "Stage read unavailable" in html
    # Scoped to the HERO. Load-failure empty states on the screener/board no
    # longer say "Warming up" (W7 r2 m1); the hero still owns first-run copy.
    assert "The first stage read runs tonight" not in html, (
        "the hero must not describe a mature-lane failure as a first run")
    assert "The arc fills in once the weekly classification lands" not in html
    # The retired build-date label must not come back on this path either.
    assert "Priced <b>" not in html


def test_warmup_with_no_artifact_still_says_warming_up():
    """The genuine first-run state keeps its warm-up copy — the §2.4 unavailable
    branch must not swallow it."""
    html = _render_warmup()
    assert "The first stage read runs tonight" in html
    assert "Stage read unavailable" not in html


# ---------------------------------------------------------------------------
# Wave 8 §8 — publication integrity: `_copy_stagedata` revocation behavior.
# ---------------------------------------------------------------------------
def _mk_dirs(tmp_path: Path) -> tuple[Path, Path]:
    data_dir = tmp_path / "data"
    site_dir = tmp_path / "site"
    (data_dir / "stage_analysis").mkdir(parents=True, exist_ok=True)
    return data_dir, site_dir


def test_missing_source_with_existing_public_copy_is_revoked(tmp_path: Path):
    """§8 acceptance gate: a stale destination whose source vanished must not
    survive as though it were current — the destination is removed and the
    revocation disclosed."""
    data_dir, site_dir = _mk_dirs(tmp_path)
    out_dir = site_dir / "stagedata"
    out_dir.mkdir(parents=True)
    # yesterday's public copy, no matching source under data/stage_analysis
    (out_dir / "screener.json").write_text(
        json.dumps({"schema": "stage_screener.v1", "status": "ready"}))
    copied, revoked, stale = _copy_stagedata(data_dir, site_dir)
    assert revoked == 1
    assert copied == 0
    assert not (out_dir / "screener.json").exists()


def test_missing_source_with_no_existing_public_copy_is_a_noop(tmp_path: Path):
    data_dir, site_dir = _mk_dirs(tmp_path)
    copied, revoked, stale = _copy_stagedata(data_dir, site_dir)
    assert copied == 0
    assert revoked == 0
    assert stale == 0


def test_current_valid_source_copies_normally(tmp_path: Path):
    data_dir, site_dir = _mk_dirs(tmp_path)
    src = data_dir / "stage_analysis" / "screener.json"
    src.write_text(json.dumps({"schema": "stage_screener.v1", "status": "ready"}))
    copied, revoked, stale = _copy_stagedata(data_dir, site_dir)
    assert copied == 1
    assert revoked == 0
    assert stale == 0
    out = site_dir / "stagedata" / "screener.json"
    assert out.exists()
    assert json.loads(out.read_text())["status"] == "ready"


def test_explicitly_stale_source_still_copies_and_is_counted_stale(tmp_path: Path):
    """Valid last-known data is retained ONLY when the artifact itself
    discloses that it is stale — it still copies, so the client can render
    the stale state, but the report counts it honestly."""
    data_dir, site_dir = _mk_dirs(tmp_path)
    src = data_dir / "stage_analysis" / "industry_ranks.json"
    src.write_text(json.dumps({"schema": "stage_industry_ranks.v1",
                               "status": "stale"}))
    copied, revoked, stale = _copy_stagedata(data_dir, site_dir)
    assert copied == 1
    assert stale == 1
    assert revoked == 0
    out = site_dir / "stagedata" / "industry_ranks.json"
    assert out.exists()


def test_stage_current_false_counts_as_stale(tmp_path: Path):
    data_dir, site_dir = _mk_dirs(tmp_path)
    src = data_dir / "stage_analysis" / "industry_flows.json"
    src.write_text(json.dumps({"schema": "stage_industry_flows.v1",
                               "stage_current": False}))
    copied, revoked, stale = _copy_stagedata(data_dir, site_dir)
    assert copied == 1
    assert stale == 1


def test_no_target_week_population_counts_as_stale(tmp_path: Path):
    data_dir, site_dir = _mk_dirs(tmp_path)
    src = data_dir / "stage_analysis" / "screener.json"
    src.write_text(json.dumps({
        "schema": "stage_screener.v1",
        "population": {"status": "no_target_week"},
    }))
    copied, revoked, stale = _copy_stagedata(data_dir, site_dir)
    assert copied == 1
    assert stale == 1


def test_invalid_json_source_is_skipped_not_copied(tmp_path: Path):
    data_dir, site_dir = _mk_dirs(tmp_path)
    src = data_dir / "stage_analysis" / "screener.json"
    src.write_text("{not valid json")
    copied, revoked, stale = _copy_stagedata(data_dir, site_dir)
    assert copied == 0
    assert not (site_dir / "stagedata" / "screener.json").exists()


def test_source_without_a_schema_key_still_publishes(tmp_path: Path):
    """A missing `schema` key must NOT block publication.

    This assertion is deliberately inverted from an earlier draft that required
    `"schema" in payload`. Five live surfaces (`ec_industry`,
    `ec_industry_heatmap`, `earnings_table`, `earnings_season`,
    `earnings_compare`) are stamped `surface` by `engine/earnings_qual.py`, so
    that rule silently froze all five. The validator's job is to reject
    unusable bytes, not to enforce a key convention this estate does not have.
    """
    data_dir, site_dir = _mk_dirs(tmp_path)
    src = data_dir / "stage_analysis" / "screener.json"
    src.write_text(json.dumps({"surface": "A", "status": "ready"}))  # no "schema"
    copied, revoked, stale = _copy_stagedata(data_dir, site_dir)
    assert copied == 1
    assert (site_dir / "stagedata" / "screener.json").exists()


def test_stale_destination_replaced_by_a_fresh_source_on_a_later_build(tmp_path: Path):
    """A previously-revoked/stale destination is not sticky: once a genuinely
    current source reappears, the normal current copy wins."""
    data_dir, site_dir = _mk_dirs(tmp_path)
    out_dir = site_dir / "stagedata"
    out_dir.mkdir(parents=True)
    (out_dir / "screener.json").write_text(
        json.dumps({"schema": "stage_screener.v1", "status": "stale"}))
    src = data_dir / "stage_analysis" / "screener.json"
    src.write_text(json.dumps({"schema": "stage_screener.v1", "status": "ready"}))
    copied, revoked, stale = _copy_stagedata(data_dir, site_dir)
    assert copied == 1
    assert stale == 0
    assert revoked == 0
    assert json.loads((out_dir / "screener.json").read_text())["status"] == "ready"


def test_every_real_stagedata_artifact_publishes(tmp_path):
    """REGRESSION PIN (Wave 8 §8): the publication validator must not silently
    freeze healthy surfaces.

    An earlier draft required a `schema` key, which skipped the five earnings /
    ec_industry artifacts whose producer (`engine/earnings_qual.py`) stamps
    `surface` instead — five live surfaces would have stopped refreshing with
    nothing louder than a log line. This walks the REAL artifact names and gives
    each a producer-realistic payload (half `schema`-stamped, half
    `surface`-stamped) and asserts every one of them lands in site/stagedata/.
    """
    from scripts.build_stage_analysis_page import _STAGEDATA_FILES, _copy_stagedata

    data_dir = tmp_path / "data"
    src = data_dir / "stage_analysis"
    src.mkdir(parents=True)
    site_dir = tmp_path / "site"

    for i, name in enumerate(_STAGEDATA_FILES):
        key = "schema" if i % 2 == 0 else "surface"
        (src / name).write_text(json.dumps({key: name.replace(".json", ".v1"),
                                            "rows": []}))

    copied, revoked, stale = _copy_stagedata(data_dir, site_dir)

    assert copied == len(_STAGEDATA_FILES), (
        f"only {copied} of {len(_STAGEDATA_FILES)} artifacts published — the "
        "validator is freezing healthy surfaces")
    assert revoked == 0
    for name in _STAGEDATA_FILES:
        assert (site_dir / "stagedata" / name).exists(), f"{name} did not publish"


def test_corrupt_or_empty_stagedata_is_not_published(tmp_path):
    """The validator still has to do its actual job: truncated/corrupt bytes and
    an empty object must not reach the public path."""
    from scripts.build_stage_analysis_page import _copy_stagedata

    data_dir = tmp_path / "data"
    src = data_dir / "stage_analysis"
    src.mkdir(parents=True)
    site_dir = tmp_path / "site"

    (src / "screener.json").write_text('{"schema": "stage_screener.v1", "rows": [')  # truncated
    (src / "industry_ranks.json").write_text("{}")                                   # empty object
    (src / "stage_board_daily.json").write_text(json.dumps({"schema": "ok", "n": 1}))

    copied, _revoked, _stale = _copy_stagedata(data_dir, site_dir)

    assert not (site_dir / "stagedata" / "screener.json").exists()
    assert not (site_dir / "stagedata" / "industry_ranks.json").exists()
    assert (site_dir / "stagedata" / "stage_board_daily.json").exists()
    assert copied == 1


# ---------------------------------------------------------------------------
# Wave 8 §3 — stale-row treatment + the mobile clock overflow fix
# ---------------------------------------------------------------------------
def test_stale_rows_get_a_visible_stale_chip_in_the_client():
    """A stale row must SAY it is stale, not merely lack a rank.

    Browser-verified: SILA renders `stale 2026-06-26` with a rank of `—`. The
    fields shipped in screener.json from day one, but nothing rendered them —
    this pins the client wiring so the provenance cannot go dark again.
    """
    html = _render_with_fixture()
    assert "staleChip" in html, "the stale-chip renderer is missing"
    assert ".staletag{" in html, "the stale-chip style is missing"
    # Gated on observation currentness, NOT on `source` — those are different
    # facts and conflating them is the defect this wave exists to fix.
    assert "row.stage_current!==false" in html
    assert "Last Stage read" in html
    assert "最近阶段判定" in html
    # It must be wired into BOTH row renderers (screener table + stage board).
    assert html.count("staleChip(r)") >= 2, (
        "staleChip must be wired into the screener AND the board renderer")


def test_hero_clock_can_wrap_on_narrow_viewports():
    """The Wave 8 clock is far longer than the retired "Priced <date>" label.

    Measured at 375px before the fix: `.asof` scrollWidth 374px inside a 347px
    `.pghead`, clipping the second date, "Weekly stage read" and "unknown". The
    nowrap must be lifted on narrow viewports while each clause stays intact.
    """
    html = _render_with_fixture()
    assert "@media (max-width:760px)" in html
    assert ".pghead .asof{white-space:normal" in html
    assert ".asof .clk{display:inline-block}" in html
    # Dates themselves must never break mid-token.
    assert ".asof b{" in html and "white-space:nowrap}" in html


# ---------------------------------------------------------------------------
# W7 round 1 — P0 truth blockers + pipeline strings
# ---------------------------------------------------------------------------

_W7_PIPELINE_BAN = (
    "ingestion-health",
    "摄取健康",
    "source heartbeat",
    "数据源心跳",
    "data contract",
    "数据合约",
    "call generation",
    "批次",
    "history generation",
    "Historical lane",
    "历史数据通道",
    "committed latest-call fallback",
    "ECtone0_100",
    "Try All regions",
    "generated tonight",
    "今晚生成",
)


def test_w7_screener_showing_uses_current_population_not_raw_length():
    """M1: the current population is the page's one canonical count.

    Hero counts exclude stale; the Screener must not use RAW.length as the
    of-N denominator. Stale rows print as a labelled slice. Unknown rows
    (stage_current null) are a third labelled slice, shown only when >0.
    """
    html = _render_with_fixture()
    assert "stale shown for context" in html
    assert "只过时数据仅供参考" in html
    assert "function isCurrentRow" in html
    assert "function isStaleRow" in html
    assert "function isUnknownRow" in html
    assert "row.stage_current===true" in html
    assert "row.stage_current===false" in html
    assert "of <b>'+denom.toLocaleString()+'</b> current" in html
    assert "isCurrentRow(r)&&regionOf(r)===region" in html
    assert "unresolved" in html
    assert "阶段周未能判定" in html


def test_w7_research_and_altdata_own_empty_states():
    """C1: Research items:0 names the Research surface, never Earnings."""
    html = _render_with_fixture()
    assert "function resEmpty()" in html
    assert "function altEmpty()" in html
    assert "Company primers are being written" in html
    assert "公司简介正在撰写中" in html
    assert "The Screener and Stage Board are unaffected" in html
    assert "host.innerHTML=resEmpty()" in html
    assert "host.innerHTML=altEmpty()" in html
    assert "host.innerHTML=ernEmpty()" not in html


def test_w7_research_empty_never_says_earnings_unavailable():
    html = _render_with_fixture()
    res_fn = html.split("function resEmpty()", 1)[1].split("function ", 1)[0]
    assert "Earnings data unavailable" not in res_fn
    assert "Earnings calls aren" not in res_fn
    assert "财报数据不可用" not in res_fn
    assert "Company primers are being written" in res_fn


def test_w7_one_published_ec_scale_on_the_page():
    """M3: one 0–100 / 0–10 vocabulary; client-side conversions deleted."""
    html = _render_with_fixture()
    assert "(row.ec_sent+1)/2*100" not in html
    assert "(r.ec_sent+1)/2*100" not in html
    assert "sent30/30*100" not in html
    assert "ECtone0_100" not in html
    assert "'EC Tone'" in html
    assert "<small>/100</small>" in html
    assert "<small>/30</small>" not in html
    assert "Call tone 0–100 over result 0–10" in html
    assert "Call tone 0–30 over result 0–10" not in html
    assert "ec_sent is a −1..1" not in html


def test_w7_region_control_is_honest():
    """M2: four uncovered region buttons disabled; no phantom All; US eyebrow."""
    html = _render_with_fixture()
    assert "US market weather" in html
    assert "美股市场天气" in html
    assert "var REGION_COVERED={US:1}" in html
    assert "US coverage only for now; other markets land when their price feed is wired" in html
    assert "目前仅覆盖美股；其他市场待行情接入后上线" in html
    assert "Try All regions" not in html
    assert "可切换到「全部」地区" not in html
    assert "if(r==='all')" not in html
    assert "exact==='all'" not in html
    assert "r==='all'" not in html


def test_w7_pipeline_strings_removed_from_page():
    """C2–C4/M6: ernEmpty AND the populated-table health banner."""
    html = _render_with_fixture()
    for banned in _W7_PIPELINE_BAN:
        assert banned not in html, f"banned pipeline string still on page: {banned!r}"
    assert "Earnings calls aren" in html
    assert "财报电话会暂时无法加载" in html
    assert "Our earnings feed is down; the Screener, Stage Board and Industries are unaffected." in html
    assert "showing the last complete set of earnings calls" in html


def test_w7_indempty_is_the_file_arm():
    """C7: region arm unreachable after M2; file arm, no 'generated tonight'."""
    html = _render_with_fixture()
    ind = html.split("function indEmpty()", 1)[1].split("function ", 1)[0]
    assert "Industry rankings aren" in ind
    assert "The file for this view didn" in ind
    assert "generated tonight" not in ind
    assert "Try another region" not in ind
    assert "今晚生成" not in ind


# ---------------------------------------------------------------------------
# W7 round 2 — one tone vocabulary, region-scoped denom, unknown bucket
# ---------------------------------------------------------------------------

_needs_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node not on PATH",
)

_WORD_TO_CHIP = {
    "Upbeat": "c-up",
    "Balanced": "c-info",
    "Guarded": "c-amb",
    "Downbeat": "c-dn",
}


def _extract_js_fn(html: str, name: str) -> str:
    marker = f"function {name}("
    start = html.index(marker)
    nxt = html.find("\n  function ", start + 1)
    if nxt < 0:
        raise AssertionError(f"could not bound function {name}")
    return html[start:nxt].rstrip()


def test_w7_r2_retired_desk_gauge_cutoffs_are_gone():
    """B1: 67/37/13 and the Screener's 66/45 table must not survive."""
    html = _render_with_fixture()
    assert "function toneBand(" in html
    assert "sent>=72" in html
    assert "sent>=47" in html
    assert "sent>=28" in html
    assert "sent>=67" not in html
    assert "sent>=37" not in html
    assert "sent>=13" not in html
    assert "pct>=66" not in html
    assert "pct>=45" not in html
    assert "ernSortKey='ec_sent'" in html
    assert "ernSortKey='ec_combined'" not in html


def test_w7_r2_load_failure_empty_states_name_the_surface():
    """m1: a genuine fetch failure is not a first-run warm-up."""
    html = _render_with_fixture()
    assert "Screener isn" in html
    assert "选股器暂时无法加载" in html
    assert "The board isn" in html
    assert "榜单暂时无法加载" in html
    screener_fn = html.split("function loadScreener()", 1)[1].split(
        "/* =====================================================================", 1)[0]
    assert "Warming up" not in screener_fn
    assert "Stage Board and Industries are unaffected" in screener_fn
    board_fn = html.split("function renderBoard()", 1)[1].split(
        "function renderBoardProv()", 1)[0]
    assert "Warming up" not in board_fn
    assert "Screener and Industries are unaffected" in board_fn


@_needs_node
def test_w7_r2_earnings_read_and_screener_chip_agree():
    """B1: one published number → one word / one chip class, including the
    reviewer's divergent cells (38.9, 46, 66.5)."""
    from engine.earnings_qual import publish_ec_tone

    html = _render_with_fixture()
    stubs = (
        "function TT(en,zh){return en;}\n"
        "function isZH(){return false;}\n"
    )
    fns = "\n".join(_extract_js_fn(html, n) for n in (
        "esc", "chip", "toneBand", "toneClass", "toneWord", "ecSent",
    ))
    published = []
    for desk in range(-10, 31):
        p = publish_ec_tone(desk, native="desk30")
        if p is not None:
            published.append(p)
    published.extend([38.9, 46, 66.5, 72.2, 47.2, 27.8, 0, 50, 100, 71.9, 47.0, 28.0, 27.9])
    published = sorted(set(published))
    harness = stubs + fns + """
var cases = """ + json.dumps(published) + """;
var WORD_TO_CHIP = """ + json.dumps(_WORD_TO_CHIP) + """;
var out = cases.map(function(v){
  var word = toneWord(v)[0];
  var html = ecSent(v);
  var m = html.match(/class="chip ([^"]+)"/);
  var cls = m ? m[1] : null;
  return {v:v, word:word, cls:cls, ok: WORD_TO_CHIP[word]===cls};
});
process.stdout.write(JSON.stringify(out));
"""
    res = subprocess.run(
        ["node", "-e", harness], capture_output=True, text=True, timeout=30,
    )
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}"
    rows = json.loads(res.stdout)
    diverged = [r for r in rows if not r["ok"]]
    assert not diverged, f"Read word vs chip class diverged: {diverged[:8]!r}"
    by_v = {r["v"]: r for r in rows}
    assert by_v[38.9]["word"] == "Guarded" and by_v[38.9]["cls"] == "c-amb"
    assert by_v[46]["word"] == "Guarded" and by_v[46]["cls"] == "c-amb"
    assert by_v[66.5]["word"] == "Balanced" and by_v[66.5]["cls"] == "c-info"
    assert by_v[72.2]["word"] == "Upbeat" and by_v[72.2]["cls"] == "c-up"
    assert by_v[27.8]["word"] == "Downbeat" and by_v[27.8]["cls"] == "c-dn"


@_needs_node
def test_w7_r2_showing_denominator_is_region_scoped_is_true():
    """M1/M2/M3: rendered denom is the fixture's region-scoped is-True count,
    not RAW.length, not unknown, not another region's current rows."""
    html = _render_with_fixture()
    start = html.index("var currentPop=") + len("var currentPop=")
    end = html.index(";});", start) + 3
    expr = html[start:end]
    assert "isCurrentRow(r)&&regionOf(r)===region" in expr, expr
    fns = "\n".join(_extract_js_fn(html, n) for n in (
        "regionOf", "isCurrentRow", "isStaleRow", "isUnknownRow",
    ))
    raw = [
        {"ticker": "AAPL", "region": "USA", "stage_current": True},
        {"ticker": "MSFT", "region": "USA", "stage_current": True},
        {"ticker": "SILA", "region": "USA", "stage_current": False},
        {"ticker": "UNK", "region": "USA", "stage_current": None},
        {"ticker": "BBVA.MC", "region": "EUROPE", "stage_current": None,
         "source": "seed"},
        {"ticker": "SAP.DE", "region": "EUROPE", "stage_current": True},
    ]
    harness = fns + """
var RAW = """ + json.dumps(raw) + """;
var region = 'US';
var currentPop = """ + expr + """;
var VIEW = RAW.filter(function(r){return regionOf(r)===region;});
var out = {
  denom: currentPop.length,
  rawLength: RAW.length,
  nCur: VIEW.filter(isCurrentRow).length,
  nStale: VIEW.filter(isStaleRow).length,
  nUnknown: VIEW.filter(isUnknownRow).length,
  tickers: currentPop.map(function(r){return r.ticker;}).sort()
};
process.stdout.write(JSON.stringify(out));
"""
    res = subprocess.run(
        ["node", "-e", harness], capture_output=True, text=True, timeout=30,
    )
    assert res.returncode == 0, f"node failed:\nSTDERR:\n{res.stderr}\nexpr={expr}"
    out = json.loads(res.stdout)
    assert out["rawLength"] == 6
    assert out["denom"] == 2, (
        f"US current denom must be 2 (AAPL+MSFT), got {out!r} via {expr}")
    assert out["tickers"] == ["AAPL", "MSFT"]
    assert out["nCur"] == 2
    assert out["nStale"] == 1
    assert out["nUnknown"] == 1  # UNK only; EU rows are other-region
    assert out["denom"] != out["rawLength"]
