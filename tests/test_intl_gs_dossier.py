"""INTL-GS-W2B (IM14 market dossier) tests — spec R14 §10.5/§11, the Wave 1
observation contract, the IM16 credit/funding binding and the display laws.

Every number slot reads the production-variant observation set (the W2FX
recipe); the abstain-all variant (observations=None) must pass the same
mount/semantics tests with every number slot in its Abstain state.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.intl_global_acceptance_matrix import acceptance_matrix  # noqa: E402
from engine.intl_global_dollar_credit import (  # noqa: E402
    ABSTAIN_REASONS as DOLLAR_ABSTAIN_REASONS, jurisdiction_assessments)
from engine.intl_global_observation import (  # noqa: E402
    REQUIRED_CLOCKS, RETURN_IDENTITY_TOLERANCE)
from engine.intl_global_universe import (  # noqa: E402
    CAPABILITIES, load_rights_matrix, load_universe)
from lib.intl_gs_display import (  # noqa: E402
    CAPABILITY_DISPLAY, CAPABILITY_LABELS, NAMES_ZH, REASON_COPY, REGION_GROUPS,
    horizon_label, reason_copy, rights_view)
from tests.intl_gs_fixture_site import render_states_page  # noqa: E402
from tests.intl_gs_dossier_fixture import (  # noqa: E402
    render_intl_page, render_specimen_page)
from tests.test_intl_gs_foundation import (  # noqa: E402
    W2FX_EVALUATED, W2FX_GRANT, _w2fx_admitted, _w2fx_setup, _w2fx_status)

UNIVERSE = load_universe()
RIGHTS = load_rights_matrix()
AM = acceptance_matrix(UNIVERSE, RIGHTS)
JA = jurisdiction_assessments(UNIVERSE)
_DOSSIER_PANEL_RE = re.compile(
    r'<section class="intl-gs__panel intl-gs__view intl-gs__view--dossier"'
    r'[^>]*data-horizon="([^"]+)" data-basis="([^"]+)"[^>]*>')
_ARTICLE_RE = re.compile(r'<article class="intl-gs__mkt"[^>]*>')
ISO_TEXT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def _signed(value, dp=2, unit=""):
    sign = "+" if value > 0 else ("−" if value < 0 else "")
    return f"{sign}{abs(value):.{dp}f}{unit}"


def _production_observation_set(tmp_path):
    from lib.intl_gs_observations import build_observation_set
    selected, inputs = _w2fx_admitted(tmp_path)
    return build_observation_set(selected, publication_inputs=inputs,
                                 evaluated_at=W2FX_EVALUATED,
                                 data_root=tmp_path, rights=W2FX_GRANT)


def _withheld_observation_set(tmp_path):
    from lib.intl_gs_observations import build_observation_set
    frame, _series = _w2fx_setup(tmp_path)
    _w2fx_status(tmp_path)
    return build_observation_set(frame, publication_inputs=None,
                                 evaluated_at=W2FX_EVALUATED,
                                 data_root=tmp_path, rights=W2FX_GRANT)


def _obs_index(observation_set):
    index = {}
    for basis, entries in (observation_set or {}).get("bases", {}).items():
        for entry in entries:
            identity = entry.get("identity") or {}
            index[(identity.get("market_id"), identity.get("horizon"), basis)] = entry
    return index


def _panels(html):
    """[(horizon, basis, chunk)] one chunk per dossier panel section."""
    starts = [(m.start(), m.group(1), m.group(2))
              for m in _DOSSIER_PANEL_RE.finditer(html)]
    panels = []
    for position, (start, horizon, basis) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(html)
        panels.append((horizon, basis, html[start:end]))
    return panels


def _articles(panel_html):
    """{market_id: article html} for one panel."""
    starts = [m.start() for m in _ARTICLE_RE.finditer(panel_html)]
    articles = {}
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(panel_html)
        chunk = panel_html[start:end]
        market = re.search(r'data-gs-market="([^"]+)"', chunk).group(1)
        articles[market] = chunk
    return articles


def _article(panel_html, market_id):
    article = _articles(panel_html).get(market_id)
    assert article is not None, f"no dossier article for {market_id}"
    return article


def _visible_text(html):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


class _AttributeScanner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bad = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value and ("<" in value or "l-en" in value or "l-zh" in value):
                self.bad.append((tag, name, value[:60]))


@pytest.fixture(scope="module")
def obs_set(tmp_path_factory):
    return _production_observation_set(tmp_path_factory.mktemp("w2b-obs"))


@pytest.fixture(scope="module")
def page(obs_set):
    return render_intl_page(obs_set)


@pytest.fixture(scope="module")
def abstain_page():
    return render_intl_page(None)


@pytest.fixture(scope="module")
def withheld_page(tmp_path_factory):
    return render_intl_page(
        _withheld_observation_set(tmp_path_factory.mktemp("w2b-withheld")))


@pytest.fixture(scope="module")
def specimen_page():
    return render_specimen_page()


def _panel(page_html, horizon="1m", basis="usd_unhedged"):
    matches = [chunk for h, b, chunk in _panels(page_html)
               if h == horizon and b == basis]
    assert matches, f"no dossier panel for {horizon}/{basis}"
    return matches[0]


# ---------------------------------------------------------------- B1 mount
def test_b1_mount_one_panel_per_context_default_and_hidden(obs_set, page):
    from lib.intl_surveillance_mount import attach_surveillance
    from tests.intl_gs_fixture_site import _vm
    workspace = attach_surveillance(_vm()["intl_workspace"], observations=obs_set)
    assert workspace["surveillance"]["views"]["dossier"]["status"] == "available"
    panels = [p for p in workspace["surveillance_panels"] if p["view"] == "dossier"]
    assert len(panels) == 10
    assert all(p["context"]["currency_basis"] != "usd_hedged" for p in panels)
    index = _obs_index(obs_set)
    for panel in panels:
        horizon = panel["context"]["horizon"]
        chunk = _panel(page, horizon, panel["context"]["currency_basis"])
        scopes = re.findall(r"<div[^>]*data-gs-market-scope", chunk)
        assert len(scopes) == 1, "exactly ONE market scope per panel"
        articles = _articles(chunk)
        assert len(articles) == 64, "63 jurisdictions + EZ aggregate"
        expected_default = next(
            (row_id for row_id in articles
             if (index.get((row_id, horizon, "usd_unhedged")) or {}).get("state")
             == "qualified"),
            next(iter(articles)))
        defaults = [m for m, chunk_a in articles.items()
                    if "data-gs-market-default" in chunk_a.split(">", 1)[0]]
        assert defaults == [expected_default]
        for market, chunk_a in articles.items():
            opening = chunk_a.split(">", 1)[0]
            hidden = "hidden" in opening
            assert hidden == (market != expected_default), market


def test_b1_abstain_all_variant_mounts_with_first_jurisdiction_default(abstain_page):
    chunk = _panel(abstain_page, "1m", "usd_unhedged")
    articles = _articles(chunk)
    assert len(articles) == 64
    defaults = [m for m, a in articles.items() if "data-gs-market-default" in a.split(">", 1)[0]]
    assert defaults == ["AE"], "no qualified observation: first jurisdiction is the default"
    for market, article in articles.items():
        assert ("hidden" in article.split(">", 1)[0]) == (market != "AE")


# ---------------------------------------------------------------- B2 hero
def test_b2_hero_qualified_number_basis_clock(obs_set, page):
    index = _obs_index(obs_set)
    jp = index[("JP", "1m", "usd_unhedged")]
    assert jp["state"] == "qualified"
    article = _article(_panel(page), "JP")
    hero = re.search(r'<div class="intl-gs__hero"[^>]*data-hero-state="([^"]+)"', article)
    assert hero and hero.group(1) == "qualified"
    expected = _signed(jp["value"]["pct"], 2, "%")
    numeral = re.search(r'<span class="intl-gs__hero__num[^"]*"[^>]*>([^<]+)</span>', article)
    assert numeral and numeral.group(1) == expected
    ink = "up" if jp["value"]["pct"] > 0 else "down"
    assert f"intl-gs__num--{ink}" in numeral.group(0)
    assert "USD" in _visible_text(re.search(r'<div class="intl-gs__hero".*?</div>\s*</div>',
                                            article, re.S).group(0))
    clock = jp["clocks"]["observation"]["at"]
    assert f'<time class="intl-gs__hero__clock" datetime="{clock}"' in article


def test_b2_hero_abstaining_observation_renders_state_not_number(withheld_page):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        observation_set = _withheld_observation_set(Path(tmp))
    index = _obs_index(observation_set)
    jp = index[("JP", "1m", "usd_unhedged")]
    assert jp["state"] == "abstain" and jp["abstain_reasons"]
    article = _article(_panel(withheld_page), "JP")
    hero = re.search(r'<div class="intl-gs__hero"[^>]*data-hero-state="([^"]+)"', article)
    assert hero and hero.group(1) == "abstain"
    assert 'intl-gs__hero__num' not in article
    visible = _visible_text(article)
    for reason in jp["abstain_reasons"]:
        en, _zh = reason_copy(reason)
        assert en in visible, reason


def test_b2_hero_no_observation_renders_capability_reason(abstain_page):
    article = _article(_panel(abstain_page), "BR")
    hero = re.search(r'<div class="intl-gs__hero"[^>]*data-hero-state="([^"]+)"', article)
    assert hero and hero.group(1) in ("abstain", "no_observation")
    assert "intl-gs__hero__num" not in article
    en, _zh = reason_copy(UNIVERSE["jurisdictions"]["BR"]["capabilities"]
                          ["equity_index_fx"]["reason"])
    assert en in _visible_text(article)


# ---------------------------------------------------------------- B3 decomposition
def test_b3_decomposition_verbatim_and_identity(obs_set, page):
    index = _obs_index(obs_set)
    jp = index[("JP", "1m", "usd_unhedged")]
    dec = jp["decomposition"]
    article = _article(_panel(page), "JP")
    card = re.search(r'<div class="intl-gs__card intl-gs__decomp".*?(?=<div class="intl-gs__card intl-gs__path)',
                     article, re.S)
    assert card, "decomposition card present"
    text = _visible_text(card.group(0))
    for field, unit in (("local_pct", "%"), ("fx_pct", "%"), ("usd_pct", "%"),
                        ("additive_fx_contribution_pp", "pp"),
                        ("interaction_pp", "pp")):
        expected = _signed(dec[field], 2, unit)
        assert expected in text, (field, expected)
    residual = dec["identity_residual"]
    residual_text = (f"{residual:.1e}".replace("-", "−")
                     if 0 < abs(residual) < 1e-6 else _signed(residual, 2, "pp"))
    assert residual_text in text
    # identity: local + additive FX + interaction = USD within tolerance+|residual|
    difference = abs(dec["local_pct"] + dec["additive_fx_contribution_pp"]
                     + dec["interaction_pp"] - dec["usd_pct"])
    assert difference <= RETURN_IDENTITY_TOLERANCE + abs(dec["identity_residual"])
    identity = re.search(r'<p class="intl-gs__identity">(.*?)</p>', card.group(0), re.S)
    assert identity
    for number in (_signed(dec["local_pct"], 2, "%"),
                   _signed(dec["additive_fx_contribution_pp"], 2, "pp"),
                   _signed(dec["interaction_pp"], 2, "pp"),
                   _signed(dec["usd_pct"], 2, "%")):
        assert number in identity.group(1), number
    assert "恒等式" in identity.group(1)  # ZH leg present
    # Common/Residual segments abstain; no 60-session series anywhere
    assert 'data-abstain-token="common_factor_unadmitted"' in card.group(0)
    path_card = re.search(r'<div class="intl-gs__card intl-gs__path".*?(?=<div class="intl-gs__card intl-gs__sigma)',
                          article, re.S).group(0)
    assert 'data-abstain-token="series_unadmitted"' in path_card
    assert "<svg" not in path_card and "<polyline" not in article


def test_b3_decomposition_abstains_without_qualified_usd_observation(abstain_page):
    article = _article(_panel(abstain_page), "JP")
    card = re.search(r'<div class="intl-gs__card intl-gs__decomp".*?(?=<div class="intl-gs__card intl-gs__path)',
                     article, re.S).group(0)
    assert 'data-decomp="abstain"' in card
    assert "intl-gs__minibar" not in card


# ---------------------------------------------------------------- B4 clocks and rights
def test_b4_clocks_rights_incumbent_evidence_tier(page):
    jp_article = _article(_panel(page), "JP")
    clockcard = re.search(r'<div class="intl-gs__card intl-gs__clockcard".*?(?=<div class="intl-gs__card intl-gs__corrcard)',
                          jp_article, re.S).group(0)
    index_rows = re.findall(r'<div class="intl-gs__clockrow"[^>]*data-clock="([^"]+)"(.*?)</div>\s*(?=<div class="intl-gs__clockrow"|<div)',
                            clockcard, re.S)
    assert [row[0] for row in index_rows] == list(REQUIRED_CLOCKS)
    # JP rights: direct_display_ok + delay token verbatim + decision_ref
    rights = rights_view(UNIVERSE, RIGHTS, "JP", "equity_index_fx")
    assert rights["rights_class"] == "direct_display_ok"
    visible = _visible_text(clockcard)
    assert rights["label_en"] in visible
    assert rights["delay"] in visible
    assert rights["decision_ref"] in visible
    assert 'data-rights="present"' in clockcard
    # evidence tier slot: Abstain, and no T1/T2/T3 token anywhere on the page
    assert 'data-abstain-token="evidence_tier_undefined"' in clockcard
    dossier_html = "\n".join(chunk for _h, _b, chunk in _panels(page))
    assert not re.search(r"\bT[123]\b", _visible_text(dossier_html))
    # incumbent block verbatim
    incumbent = re.search(r'<dl class="intl-gs__incumbent".*?</dl>', jp_article, re.S)
    assert incumbent
    assert "derived-evaluation:sha256:" in incumbent.group(0)


def test_b4_restricted_rights_grammar_and_missing_clocks(abstain_page):
    br_article = _article(_panel(abstain_page), "BR")
    clockcard = re.search(r'<div class="intl-gs__card intl-gs__clockcard".*?(?=<div class="intl-gs__card intl-gs__corrcard)',
                          br_article, re.S).group(0)
    assert 'data-rights="restricted"' in clockcard
    assert "intl-gs__rights-slot" in clockcard
    assert "intl-gs__chip--warn-dashed" in clockcard
    # BR (no observation at all): all four clocks show — + Clock missing
    missing = clockcard.count("Clock missing")
    assert missing >= 4


# ---------------------------------------------------------------- B5 abstain sections
def test_b5_abstain_sections_neutral_ink(page):
    article = _article(_panel(page), "JP")
    assert 'data-abstain-token="divergence_unadmitted"' in article
    assert 'data-abstain-token="transmission_unadmitted"' in article
    assert 'data-abstain-token="us_corroboration_unadmitted"' in article
    assert 'data-abstain-token="thesis_unadmitted"' in article
    assert 'data-abstain-token="corrections_none"' in article
    thesis = re.search(r'<div class="intl-gs__dossier-rail">.*?(<div class="intl-gs__panel intl-gs__featured">.*?</div>\s*</div>)',
                       article, re.S)
    assert thesis, "Q6 thesis card carries the featured ring"
    cf_table = re.search(r'<table class="intl-gs__table intl-gs__cftable">.*?</table>',
                         article, re.S).group(0)
    assert "intl-gs__num--up" not in cf_table and "intl-gs__num--down" not in cf_table


# ---------------------------------------------------------------- B6 coverage vector
def test_b6_coverage_vector_seven_rows_no_stray_percent(page):
    article = _article(_panel(page), "JP")
    vector = re.search(r'<ul class="intl-gs__covvec">.*?</ul>', article, re.S).group(0)
    capabilities = re.findall(r'<li class="intl-gs__covvec__row"[^>]*data-capability="([^"]+)"', vector)
    assert capabilities == list(CAPABILITIES)
    visible = _visible_text(vector)
    for capability in CAPABILITIES:
        assert CAPABILITY_LABELS[capability][0] in visible
    # no % anywhere in the dossier outside signed return numerals
    for token in _visible_text(article).split():
        if "%" in token:
            assert re.search(r"[+−]?\d+(\.\d+)?%$", token), token


# ---------------------------------------------------------------- B7 peers
def test_b7_peers_same_region_group_select_links(obs_set, page):
    article = _article(_panel(page), "AU")
    peers_html = re.search(r'<div class="intl-gs__peers">.*?</div>\s*(?=</article>|<footer|$)',
                           article, re.S).group(0)
    links = re.findall(r'<a class="intl-gs__peer"[^>]*data-gs-select-market="([^"]+)"[^>]*href="([^"]+)"',
                       peers_html)
    assert [m for m, _href in links][:5] == ["CN", "HK", "ID", "IN", "JP"]
    for market, href in links:
        assert href == f"?view=dossier&market={market}"
    index = _obs_index(obs_set)
    cards = re.split(r'<a class="intl-gs__peer"', peers_html)[1:]
    for market, card in zip([m for m, _ in links], cards):
        obs = index.get((market, "1m", "usd_unhedged"))
        if obs and obs["state"] == "qualified":
            assert _signed(obs["value"]["pct"], 2, "%") in _visible_text(card)
        else:
            assert "intl-gs__num--up" not in card and "intl-gs__num--down" not in card
            assert not re.search(r"[+−]\d+\.\d\d%", card), market


# ---------------------------------------------------------------- B8 specimen isolation
def test_b8_build_view_never_sets_specimen(obs_set):
    import lib.intl_gs_dossier_view as dossier
    from engine.intl_workspace_overview import build_workspace_overviews
    from lib.intl_macro_mount import _contexts
    from lib.intl_workspace_binding import binding_version
    workspace = build_workspace_overviews(None)
    version, generation = binding_version(workspace)
    contexts = _contexts(workspace["panels"], workspace["config"], version, generation)
    panels = dossier.build_view(universe=UNIVERSE, rights=RIGHTS, contexts=contexts,
                                workspace=workspace, observations=obs_set)
    assert panels
    for panel in panels:
        assert not panel["payload"].get("specimen")
        for market in panel["payload"]["markets"]:
            assert not market.get("sigma_rows")
            assert not market.get("typed_edges")
            assert market.get("peers") is not None


def test_b8_no_specimen_true_in_production_sources():
    for directory in (ROOT / "lib", ROOT / "templates"):
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix in (".py", ".j2"):
                assert "specimen=True" not in path.read_text(encoding="utf-8"), path


def test_b8_specimen_page_board11(specimen_page):
    assert "Specimen values" in specimen_page and "示例数值" in specimen_page
    assert re.search(r'<span class="intl-gs__hero__num[^"]*"[^>]*>\+3\.40%</span>',
                     specimen_page)
    assert "Chile" in specimen_page and "Peru" in specimen_page
    chile = re.search(r'<a class="intl-gs__peer"[^>]*data-gs-select-market="CL".*?(?=<a class="intl-gs__peer")',
                      specimen_page, re.S).group(0)
    peru = re.search(r'<a class="intl-gs__peer"[^>]*data-gs-select-market="PE".*?(?=<a class="intl-gs__peer")',
                     specimen_page, re.S).group(0)
    assert "intl-gs__chip--warn-dashed" in chile, "Chile Qualified dashed warn"
    assert "intl-gs__chip--muted-dashed" in peru, "Peru Abstain dashed muted"


# ---------------------------------------------------------------- B9 design laws
def _w2b_css_region():
    stylesheet = (ROOT / "templates/intl_workspace_surveillance.css").read_text(
        encoding="utf-8")
    match = re.search(r"/\* ==== W2B region \(IM14 dossier\)[^\n]*\*/(.*?)"
                      r"/\* ==== end W2B region ==== \*/", stylesheet, re.S)
    assert match, "W2B region present"
    return match.group(1)


def test_b9_css_region_design_laws():
    region = _w2b_css_region()
    assert region.strip(), "W2B region carries rules"
    assert ".igs" not in region
    for line in region.splitlines():
        code = line.split("/*")[0].strip()
        if not code:
            continue
        assert not re.search(r"border-(left|right|top|bottom|inline-start|inline-end|block-start|block-end)\s*:", code), code
        assert "box-shadow:inset" not in code.replace(" ", "")
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|color-mix\(", code), code
        assert "font-family" not in code or "var(--font-" in code, code
        if "border-radius" in code:
            assert re.search(r"border-radius:var\(--r-(panel,12px|btn,8px|pill,999px)\);?$", code), code
        if "var(--" in code:
            for name in re.findall(r"var\((--[a-z0-9-]+)", code):
                assert not name.startswith(("--sp-", "--returns-", "--font-zh")), code
                assert ",12px)" not in code or name == "--r-panel", code
        if ":" in code and "{" not in code and "hover" not in code:
            pass  # declaration lines checked above
    selectors = [line.strip().split("{")[0].strip() for line in region.splitlines()
                 if "{" in line and "}" not in line.split("{")[0]]
    for selector in selectors:
        for part in selector.split(","):
            part = part.strip()
            assert part.startswith(".intl-gs") or part.startswith("html["), selector
    # hover may only change neutral surface tokens
    for block in re.findall(r"([^{}]+):hover\s*\{([^}]*)\}", region):
        for declaration in block[1].split(";"):
            if ":" in declaration:
                prop, value = declaration.split(":", 1)
                if prop.strip() in ("background", "background-color"):
                    assert value.strip() in ("var(--panel2)", "var(--panel)"), block


def test_b9_templates_no_style_no_igs():
    for name in ("templates/intl_workspace/dossier.html.j2",
                 "templates/intl_workspace/_gs_dossier_macros.html.j2"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "<style" not in text and "style=" not in text, name
        assert ".igs" not in text


# ---------------------------------------------------------------- B10 ZH
def test_b10_zh_vocabulary(page):
    chunk = _panel(page)
    for market, zh in (("JP", NAMES_ZH["JP"]), ("AU", NAMES_ZH["AU"]), ("EZ", NAMES_ZH["EZ"])):
        assert re.search(rf'data-gs-select-market="{market}"[^>]*>[^<]*<span class="l-zh">{zh}</span>',
                         chunk), market
    assert "全球发生了什么变化？" in chunk  # question labels ZH
    identity = re.search(r"<p class=\"intl-gs__identity\">.*?</p>", chunk, re.S)
    assert identity and "恒等式" in identity.group(0)
    # signed numerals use the semantic ink classes only
    article = _article(chunk, "JP")
    for span in re.findall(r'<span class="intl-gs__hero__num[^"]*"', article):
        assert "intl-gs__num--up" in span or "intl-gs__num--down" in span


# ---------------------------------------------------------------- B12 IM16 binding
CF_ROWS = ("yield_10y", "cds_5y", "usd_funding", "em_credit_sovereign", "dollar_funding")


def _cf_table(page_html, market):
    article = _article(_panel(page_html), market)
    table = re.search(r'<table class="intl-gs__table intl-gs__cftable">.*?</table>',
                      article, re.S)
    assert table, f"credit/funding table for {market}"
    return table.group(0)


@pytest.mark.parametrize("market", ["JP", "BR", "CL"])
def test_b12_credit_funding_rows_match_engine(page, market):
    table = _cf_table(page, market)
    rows = re.findall(r'<tr[^>]*data-cf-row="([^"]+)"[^>]*data-state="([^"]+)"[^>]*>(.*?)</tr>',
                      table, re.S)
    assert [row[0] for row in rows] == list(CF_ROWS)
    cells = AM["coverage_board"]["cells"][market]
    claims = JA["claims"]
    expected_states = [cells["yield_10y"]["state"], cells["cds_5y"]["state"],
                       cells["usd_funding"]["state"],
                       claims["em_credit_sovereign"]["jurisdictions"][market]["state"],
                       claims["dollar_funding"]["jurisdictions"][market]["state"]]
    assert [row[1] for row in rows] == expected_states
    expected_reasons = [cells["yield_10y"]["reason"], cells["cds_5y"]["reason"],
                        cells["usd_funding"]["reason"],
                        claims["em_credit_sovereign"]["jurisdictions"][market]["abstain_reasons"][0],
                        claims["dollar_funding"]["jurisdictions"][market]["abstain_reasons"][0]]
    visible = _visible_text(table)
    for reason in expected_reasons:
        from lib.intl_gs_dossier_view import IM16_REASON_COPY
        en, _zh = REASON_COPY.get(reason) or IM16_REASON_COPY.get(reason, (reason, reason))
        assert en in visible, reason
    # all reasons in title/aria
    for row in rows:
        assert "title=" in row[2] or "title=" in table, row[0]
    # no numerals, no up/down ink
    assert "intl-gs__num--up" not in table and "intl-gs__num--down" not in table
    labelless = re.sub(r'<th class="intl-gs__cftable__label">.*?</th>', "", table, flags=re.S)
    assert not re.search(r"[+−]?\d+\.\d", _visible_text(labelless)), "no data numeral"
    # glyph is the CAPABILITY_DISPLAY presentation of the engine state
    for row, state in zip(rows, expected_states):
        if state == "abstain":
            continue
        display = CAPABILITY_DISPLAY.get(state, state)
        assert f"intl-gs__glyph--{display}" in row[2], (market, row[0], display)


def test_b12_im16_reason_copy_full_coverage():
    from lib.intl_gs_dossier_view import IM16_REASON_COPY
    assert set(IM16_REASON_COPY) <= set(DOLLAR_ABSTAIN_REASONS)
    merged = set(REASON_COPY) | set(IM16_REASON_COPY)
    missing = set(DOLLAR_ABSTAIN_REASONS) - merged
    assert not missing, missing
    for token, (en, zh) in IM16_REASON_COPY.items():
        assert en and zh and en != zh
        assert re.search(r"[一-鿿]", zh), token


def test_b12_every_im16_value_is_none():
    for claim, block in JA["claims"].items():
        for market, assessment in block["jurisdictions"].items():
            assert assessment["state"] == "abstain"
            assert assessment["value"] is None, (claim, market)


# ---------------------------------------------------------------- B13 correction note unit
def test_b13_correction_note_wraps_separator_and_clock():
    states = render_states_page()
    assert states.count('<span class="intl-gs__corr-when">') == states.count(
        'class="intl-gs__corr"')
    assert '<span class="intl-gs__corr-when"> · <span class="intl-gs__num">' in states


def test_b13_css_region_carries_nowrap_rule():
    assert ".intl-gs .intl-gs__corr-when{white-space:nowrap}" in _w2b_css_region().replace(" ", "")


# ---------------------------------------------------------------- B14 no raw ISO / clean attributes
@pytest.mark.parametrize("source", ["production", "abstain"])
def test_b14_no_raw_iso_and_clean_attributes(page, abstain_page, source):
    html = page if source == "production" else abstain_page
    for market in ("AU", "JP"):
        article = _article(_panel(html), market)
        assert not ISO_TEXT_RE.search(_visible_text(article))
        for clock in re.findall(r"<time[^>]*datetime=\"([^\"]+)\"", article):
            assert ISO_TEXT_RE.match(clock) or re.match(r"\d{4}-\d{2}-\d{2}", clock)
    scanner = _AttributeScanner()
    scanner.feed(html)
    assert not scanner.bad, scanner.bad[:3]


def test_b14_templates_never_call_t_in_attributes():
    for name in ("templates/intl_workspace/dossier.html.j2",
                 "templates/intl_workspace/_gs_dossier_macros.html.j2"):
        assert '="{{ t(' not in (ROOT / name).read_text(encoding="utf-8"), name


# ---------------------------------------------------------------- B15 horizon labels
def test_b15_horizon_labels_never_raw(page):
    panels = _panels(page)
    assert len(panels) == 10, "one dossier panel per context"
    for horizon, basis, chunk in panels:
        en, zh = horizon_label(horizon)
        assert f'<span class="l-en">{en}</span>' in chunk, horizon
        assert f'<span class="l-zh">{zh}</span>' in chunk, horizon
        visible = _visible_text(chunk)
        if horizon_label(horizon) != (horizon, horizon):
            # the foundation maps this horizon: no raw id may leak into text
            assert not re.search(rf"\b{re.escape(horizon)}\b", visible), horizon
