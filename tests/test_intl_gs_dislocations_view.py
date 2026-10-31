"""INTL-GS-W3U dislocation explorer contracts (RED-first, spec R14 §10.3/§9.7).

The view under test is the `dislocations` surveillance sub-tab: the production
builder ``lib/intl_gs_dislocations_view.py`` over the IM15 engine, the template
``templates/intl_workspace/dislocations.html.j2`` and the W3U CSS region in
``templates/intl_workspace_surveillance.css``. Every test renders through the
W2 fixture helpers and this lane's observation fixture — no network, no data/
reads. Mutants 1–5 and 7 of the seat commission are named tests below.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engine.intl_global_dislocation import (  # noqa: E402
    ATTENTION_MODIFIED_Z,
    DISLOCATION_ABSTAIN_REASONS,
    EXCLUSION_REASONS,
    dislocation_peer_divergence,
    region_of,
)
from engine.intl_global_observation import RETURN_IDENTITY_TOLERANCE  # noqa: E402
from lib.intl_gs_display import NAMES_ZH, REASON_COPY, reason_copy  # noqa: E402

BUILDER_PATH = REPO / "lib/intl_gs_dislocations_view.py"
TEMPLATE_PATH = REPO / "templates/intl_workspace/dislocations.html.j2"
CSS_PATH = REPO / "templates/intl_workspace_surveillance.css"
SITE_CSS_PATH = REPO / "site/intl_workspace_surveillance.css"
FIXTURE_PATH = REPO / "tests/intl_gs_dislocations_fixture.py"
MOUNT_PATH = REPO / "lib/intl_surveillance_mount.py"
BUILD_INTL_PATH = REPO / "scripts/build_intl.py"

W3U_START = "/* ==== W3U region (IM15 dislocation explorer) ==== */"
W3U_END = "/* ==== end W3U region ==== */"
SPACER2 = "/* spacer 2: keep unchanged */"
SPACER3 = "/* spacer 3: keep unchanged */"

ROW_KEYS = {
    "market_id", "name_en", "name_zh", "region", "dislocation_id", "state",
    "abstain_reasons", "z", "direction", "attention", "rank",
    "local_pct", "fx_pct", "usd_pct", "interaction_pp",
    "observation_state", "observation_reasons", "clocks", "clock_display",
    "references", "fragility", "extras", "view_state", "view_reasons",
    "peers", "index",
}
PAYLOAD_KEYS = {
    "horizon", "horizon_label", "basis", "observation_status", "computed_at",
    "computed_at_display", "specimen", "copy", "rows", "selected", "counts",
    "scatter", "thresholds", "footnotes", "census",
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder():
    module = _load(BUILDER_PATH, "lib.intl_gs_dislocations_view")
    # Register under the canonical name so the seam's importlib.import_module
    # resolves THIS instance (monkeypatches on it reach render_page).
    sys.modules["lib.intl_gs_dislocations_view"] = module
    return module

@pytest.fixture(scope="module")
def fixture():
    return _load(FIXTURE_PATH, "intl_gs_dislocations_fixture")


def _x_usd(observation_set, horizon="1m"):
    return [obs for obs in observation_set["bases"]["usd_unhedged"]
            if obs["identity"]["horizon"] == horizon]


def _computed_at(observation_set, horizon="1m"):
    stamps = [obs["clocks"]["computation"]["at"]
              for obs in observation_set["bases"]["usd_unhedged"]
              + observation_set["bases"]["local"]
              if obs["identity"]["horizon"] == horizon]
    return max(stamps)


# ---------------------------------------------------------------- V1 empty

def test_v1_build_view_returns_empty_for_unusable_inputs(builder, fixture):
    observation_set = fixture.build_set()
    universe = fixture.universe()
    workspace = fixture.workspace()
    kwargs = dict(universe=universe, rights={}, contexts={}, workspace=workspace)
    assert builder.build_view(observations=None, **kwargs) == []
    assert builder.build_view(observations={}, **kwargs) == []
    assert builder.build_view(
        observations={"status": "admitted", "bases": {}}, **kwargs) == []
    assert builder.build_view(
        observations={"status": "admitted",
                      "bases": {"usd_unhedged": [], "local": []}}, **kwargs) == []
    undeclared = fixture.build_set(horizon="7m")
    assert builder.build_view(observations=undeclared, **kwargs) == []
    assert builder.build_view(observations=observation_set,
                              **{**kwargs, "universe": {}}) == []


# ---------------------------------------------------------------- V2 panel

def test_v2_panel_contract_through_the_seam(fixture):
    mount = _load(MOUNT_PATH, "lib.intl_surveillance_mount")
    result = mount.attach_surveillance(
        fixture.workspace(), universe_loader=fixture.universe,
        rights_loader=lambda: {"rows": []},
        observations=fixture.build_set())
    views = result["surveillance"]["views"]
    assert views["dislocations"]["status"] == "available"
    # DEC:INTL-GS-FOUNDATION-TESTS-ENCODE-WORLD-STATE-NOT-INVARIANT (F-POST-3):
    # the six sibling views encode today's fixture world, not a law. A view is
    # "available" exactly when its builder produced a panel; the day the
    # scanner/coverage/dossier builders ship a panel in this fixture world the
    # equality keeps holding. B1 stands: no builder may abstain to keep a
    # test green.
    panel_views = {panel["view"] for panel in result["surveillance_panels"]}
    for view in ("scanner", "transmission", "dossier", "scenario", "replay",
                 "coverage"):
        has_panel = view in panel_views
        assert (views[view]["status"] == "available") == has_panel, view
        if not has_panel:
            assert views[view]["status"] != "available", view
    panels = [panel for panel in result["surveillance_panels"]
              if panel["view"] == "dislocations"]
    assert len(panels) == 1
    panel = panels[0]
    assert panel["context_id"] == "im-gs-dislocations"
    assert panel["context"]["horizon"] in fixture.workspace()["config"]["horizons"]
    assert panel["context"]["currency_basis"] == "usd_unhedged"


# ---------------------------------------------------------------- V3 engine fields

def test_v3_payload_carries_engine_fields_only(builder, fixture):
    observation_set = fixture.build_set()
    payload = builder.build_payload(universe=fixture.universe(),
                                    workspace=fixture.workspace(),
                                    observations=observation_set)
    assert payload is not None
    assert set(payload) == PAYLOAD_KEYS
    cross = _x_usd(observation_set)
    computed_at = _computed_at(observation_set)
    universe = fixture.universe()
    by_market = {row["market_id"]: row for row in payload["rows"]}
    assert set(by_market) == {obs["identity"]["universe_id"] for obs in cross}
    for subject in cross:
        market = subject["identity"]["universe_id"]
        receipt = dislocation_peer_divergence(
            subject, cross, kind="peer_divergence_return",
            computed_at=computed_at, peer_rule="same_universe_region",
            universe=universe)
        row = by_market[market]
        assert set(row) == ROW_KEYS, market
        assert row["dislocation_id"] == receipt["dislocation_id"]
        assert row["state"] == receipt["state"]
        assert row["abstain_reasons"] == receipt["abstain_reasons"]
        assert row["z"] == (receipt["evidence"]["modified_z"]
                            if receipt["evidence"] else None)
        assert row["direction"] == (receipt["evidence"]["direction"]
                                    if receipt["evidence"] else None)
        assert row["attention"] == (receipt["evidence"]["attention"]
                                    if receipt["evidence"] else None)
        assert row["rank"] == (receipt["evidence"]["rank"]
                               if receipt["evidence"] else None)
        assert row["clocks"] == receipt["clocks"]
        decomposition = (subject["decomposition"] or {})
        for field in ("local_pct", "fx_pct", "usd_pct", "interaction_pp"):
            assert row[field] == decomposition.get(field), (market, field)
        assert row["observation_reasons"] == subject["abstain_reasons"]
        assert row["region"] == region_of(market, universe)
        assert row["name_en"] == fixture.market_name(market)
        assert row["name_zh"] == NAMES_ZH.get(market, fixture.market_name(market))
        refs = receipt["references"]
        assert row["references"]["used"] == refs["used"]
        assert row["references"]["offered"] == refs["offered"]
        assert (row["references"]["used_observation_ids"]
                == refs["used_observation_ids"])
        assert (row["references"]["excluded_by_reason"]
                == refs["excluded_by_reason"])
    assert payload["thresholds"]["attention_modified_z"] == ATTENTION_MODIFIED_Z
    assert payload["thresholds"]["fragility"] == 60
    assert payload["computed_at"] == computed_at


# ---------------------------------------------------------------- V4 rank_rows

def _full_clocks():
    return {name: {"at": "2026-10-09T20:30:00+00:00", "precision": "exact"}
            for name in ("observation", "source_publication", "ingestion",
                         "computation")}


def _synthetic(z, market_id):
    return {"market_id": market_id, "z": z, "state": "qualified",
            "dislocation_id": f"id-{market_id}", "clocks": _full_clocks(),
            "fragility": None}


def test_v4_rank_rows_orders_ties_and_caps_at_twelve(builder):
    rows = [_synthetic(z, f"M{i:02d}") for i, z in enumerate(
        [1.0, -5.0, 5.0, 0.0, 3.0, -3.0, 2.0, -2.0, 4.0, -4.0, 2.5, -2.5,
         1.5, 6.0])]
    rows.append(_synthetic(5.0, "M99"))  # |z| tie with M02, market_id breaks it
    ranked, unranked = builder.rank_rows(rows)
    assert len(ranked) == 12 and len(unranked) == 3  # 15 rankable -> cap 12
    assert [abs(row["z"]) for row in ranked] == sorted(
        (abs(row["z"]) for row in ranked), reverse=True)
    assert ranked.index(next(r for r in ranked if r["market_id"] == "M02")) < \
        ranked.index(next(r for r in ranked if r["market_id"] == "M99"))
    assert [row["index"] for row in ranked] == list(range(12))
    assert [row["market_id"] for row in unranked] == sorted(
        row["market_id"] for row in unranked)
    assert all(row["index"] is None for row in unranked)


# ---------------------------------------------------------------- V5 mutant 5

def test_row_without_evidence_id_or_clocks_is_not_ranked(builder, fixture,
                                                         monkeypatch):
    observation_set = fixture.build_set()
    real = builder.dislocation_peer_divergence

    def strip_id(subject, cross, **kwargs):
        receipt = real(subject, cross, **kwargs)
        receipt["dislocation_id"] = None
        return receipt

    monkeypatch.setattr(builder, "dislocation_peer_divergence", strip_id)
    payload = builder.build_payload(universe=fixture.universe(),
                                    workspace=fixture.workspace(),
                                    observations=observation_set)
    assert payload["counts"]["ranked"] == 0
    assert payload["selected"] is None
    assert all(row["index"] is None for row in payload["rows"])
    assert fixture.render_page(observations=observation_set).count(
        'class="intl-dislocations__pick"') == 0

    def strip_clock(subject, cross, **kwargs):
        receipt = real(subject, cross, **kwargs)
        receipt["clocks"]["computation"] = {"precision": "exact"}
        return receipt

    monkeypatch.setattr(builder, "dislocation_peer_divergence", strip_clock)
    payload = builder.build_payload(universe=fixture.universe(),
                                    workspace=fixture.workspace(),
                                    observations=observation_set)
    assert payload["counts"]["ranked"] == 0
    assert payload["counts"]["unranked"] == payload["counts"]["carried"]


# ---------------------------------------------------------------- V6 states

def test_v6_every_state_renders_its_chip_and_precedence(builder, fixture):
    html = fixture.render_page(variant="production", scenario="restricted")
    section = _dislocations_section(html)
    assert re.search(r'<span class="l-en">Restricted</span>', section)
    assert "intl-gs__rights-slot" in section
    assert re.search(r'<span class="l-en">Abstain</span>', section)
    assert re.search(r'<span class="l-en">Qualified</span>', section)
    qualified_copy = builder.DISLOCATION_REASON_COPY["not_qualified"]
    assert qualified_copy[0] in section or qualified_copy[1] in section
    payload = builder.build_payload(
        universe=fixture.universe(), workspace=fixture.workspace(),
        observations=fixture.build_set(scenario="restricted"))
    states = {row["market_id"]: row["view_state"] for row in payload["rows"]}
    assert states == {"AU": "qualified", "EZ": "abstain", "GB": "abstain",
                      "IN": "qualified", "JP": "qualified", "KR": "qualified",
                      "TW": "restricted"}
    qualified_row = next(row for row in payload["rows"]
                         if row["market_id"] == "JP")
    assert any(entry["token"] == "not_qualified" and entry["count"] == 1
               for entry in qualified_row["view_reasons"])
    payload_complete = builder.build_payload(
        universe=fixture.universe(), workspace=fixture.workspace(),
        observations=fixture.build_set(scenario="complete"))
    states_complete = {row["market_id"]: row["view_state"]
                       for row in payload_complete["rows"]}
    assert states_complete["TW"] == "complete"
    assert all(states_complete[market] == "complete"
               for market in ("JP", "KR", "IN", "AU"))


# ---------------------------------------------------------------- V7 copy closure

def test_v7_reason_copy_key_set_is_closed_and_never_raw(builder, fixture):
    expected = (set(DISLOCATION_ABSTAIN_REASONS) | set(EXCLUSION_REASONS)
                | {"fragility_unadmitted"})
    assert set(builder.DISLOCATION_REASON_COPY) == expected
    for token in ("clock_missing", "clock_order_violation"):
        assert builder.DISLOCATION_REASON_COPY[token] == REASON_COPY[token]
    for token, (en, zh) in builder.DISLOCATION_REASON_COPY.items():
        assert en and zh and en != token, token
    for region, (en, zh) in builder.REGION_COPY.items():
        assert en and zh, region
    assert set(builder.REGION_COPY) >= {"asia_pacific", "europe",
                                        "middle_east_africa", "americas"}
    html = fixture.render_page(variant="production", scenario="restricted")
    text = _strip_tags(html)
    for token in sorted(expected | set(REASON_COPY)):
        assert token not in text, f"raw token rendered: {token}"


# ---------------------------------------------------------------- V8 mutant 3

def test_abstain_renders_dash_never_numeral(fixture):
    html = fixture.render_page(variant="production", scenario="restricted")
    unranked = re.findall(r'<tr data-unranked="[^"]*">.*?</tr>', html, re.DOTALL)
    assert len(unranked) == 3  # TW, GB, EZ
    for row_html in unranked:
        for cell in re.findall(r"<td.*?</td>", row_html, re.DOTALL):
            label = re.search(r'data-label="([^"]*)"', cell)
            if label and label.group(1) in ("Z", "RESIDUAL"):
                cell_text = _strip_tags(cell)
                assert "—" in cell_text, cell
                assert not re.search(r"\d", cell_text), cell
        assert "intl-dislocations__resbar" not in row_html
    tw_row = next(row for row in unranked
                  if ">TW<" in row or "Taiwan" in row or "台湾" in row)
    for leg in ("USD", "LOCAL", "FX"):
        cell = next(c for c in re.findall(r"<td.*?</td>", tw_row, re.DOTALL)
                    if f'data-label="{leg}"' in c)
        assert "—" in cell and not re.search(r"\d", _strip_tags(cell)), leg


# ---------------------------------------------------------------- V9 mutant 2

def test_qualified_bar_is_dashed_outline_without_fill(fixture):
    html = fixture.render_page(variant="production", scenario="restricted")
    section = _dislocations_section(html)
    qualified_bar = re.search(
        r'<svg class="intl-dislocations__resbar[^>]*>.*?data-q="1".*?</svg>',
        section, re.DOTALL)
    assert qualified_bar, "no Qualified residual bar carrying data-q=1"
    css = _w3u_region(CSS_PATH.read_text(encoding="utf-8"))
    rule = re.search(r'\[data-q="1"\]\{([^}]*)\}', css)
    assert rule, "no [data-q=1] rule in the W3U region"
    body = rule.group(1).replace(" ", "")
    assert "fill:none" in body
    assert "stroke:var(--warn)" in body
    assert "stroke-dasharray" in body
    assert "stroke-width:1.5" in body
    assert "intl-gs__divbar__fill" not in qualified_bar.group(0)


# ---------------------------------------------------------------- V10 mutant 1

def test_fragility_at_or_above_threshold_carries_label(builder, fixture):
    html = fixture.render_page(variant="specimen", scenario="restricted")
    section = _dislocations_section(html)
    cells = re.findall(r'<td[^>]*data-label="FRAGILITY"[^>]*>.*?</td>',
                       section, re.DOTALL)
    assert len(cells) >= 4
    above = [cell for cell in cells if 'data-above="1"' in cell]
    labelled = [cell for cell in cells if "above threshold" in cell]
    assert len(above) == 2, "specimen fragility 72 and 60 must both be above"
    assert len(labelled) == len(above)
    assert "高于阈值" in section
    below = [cell for cell in cells
             if re.search(r"\d", _strip_tags(cell)) and 'data-above="1"' not in cell]
    assert below and all("above threshold" not in cell for cell in below)
    production = _dislocations_section(fixture.render_page(variant="production"))
    production_cells = re.findall(r'<td[^>]*data-label="FRAGILITY"[^>]*>.*?</td>',
                                  production, re.DOTALL)
    assert production_cells
    fragility_copy = builder.DISLOCATION_REASON_COPY["fragility_unadmitted"]
    for cell in production_cells:
        assert "—" in cell, cell
        assert not re.search(r"\d", _strip_tags(cell)), cell
        assert fragility_copy[0] in cell or fragility_copy[1] in cell, cell
        assert "data-above" not in cell


# ---------------------------------------------------------------- V11 mutant 4

def test_zh_up_move_never_green(fixture):
    html = fixture.render_page(variant="specimen", scenario="restricted")
    section = _dislocations_section(html)
    up_cell = re.search(r'<span class="intl-gs__num intl-gs__num--up">[^<]*</span>',
                        section)
    assert up_cell, "no UP numeral using the foundation up class"
    assert "style" not in up_cell.group(0)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert not re.search(r"style\s*=", template)
    css = _w3u_region(CSS_PATH.read_text(encoding="utf-8"))
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if "data-lang" in selector:
            assert "--up" not in body and "--down" not in body, selector
    assert "var(--up)" in css and "var(--down)" in css  # unconditional fills


# ---------------------------------------------------------------- V12 mutant 7

def test_template_classes_are_view_or_shared_scoped(fixture):
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    # strip Jinja expression/statement chunks so class="..." captures only the
    # literal class tokens the template emits
    source = re.sub(r"\{\{.*?\}\}", " ", template, flags=re.DOTALL)
    tokens = set()
    for attribute in re.findall(r'class="([^"]*)"', source):
        tokens.update(attribute.split())
    # the estate i18n classes (engine.i18n.t / svgt twins) are lawful in the
    # template exactly as in the render; everything else must be view- or
    # shared-scoped (mutant 7)
    estate_i18n = {"l-en", "l-zh"}
    allowed = re.compile(r"^(intl-dislocations__|intl-gs__)")
    offenders = sorted(token for token in tokens - estate_i18n
                       if not allowed.match(token))
    assert not offenders, f"template class outside the two scopes: {offenders}"
    html = fixture.render_page(variant="specimen", scenario="restricted")
    section = _dislocations_section(html)
    rendered = set()
    for attribute in re.findall(r'class="([^"]*)"', section):
        rendered.update(attribute.split())
    estate_i18n = {"l-en", "l-zh"}  # engine.i18n.t language spans
    offenders = sorted(token for token in rendered - estate_i18n
                       if not allowed.match(token))
    assert not offenders, f"rendered class outside the two scopes: {offenders}"
    assert ".igs" not in template and "igs-" not in template


# ---------------------------------------------------------------- V13 CSS law

def _merge_base() -> str:
    result = subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                             "origin/main^{commit}"],
                            cwd=REPO, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail("FAIL CLOSED: origin/main does not resolve (git fetch origin main)")
    base = subprocess.run(["git", "merge-base", "origin/main", "HEAD"],
                          cwd=REPO, capture_output=True, text=True)
    sha = base.stdout.strip()
    if base.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        pytest.fail("FAIL CLOSED: no merge base (shallow checkout?)")
    return sha


W2A_REGION = ("/* ==== W2A region (IM13 scanner + coverage): the W2A lane inserts "
              "its rules between this line and the next ==== */")


def _v13_region_law(css: str, base: str) -> None:
    """The W3U insert-only law against the merge base, in both merge phases.

    PRE (base carries no W3U region — this PR against current main): the W3U
    block is a pure insertion before the W2A region anchor, so the bytes
    before it and the bytes from the W2A anchor to EOF equal the base's.
    POST (base carries exactly one W3U region — this PR merged, or any later
    PR on that main): only the prefix before the region and the region bytes
    themselves are pinned; the bytes from the W2A region line to EOF belong
    to the W2A/W2B lanes and are pinned by their own suites (F-POST-1).
    """
    if W3U_START not in base:
        assert css[:css.index(W3U_START)] == base[:base.index(W2A_REGION)]
        assert css[css.index(W3U_END) + len(W3U_END) + 1:] == \
            base[base.index(W2A_REGION):]
        return
    assert base.count(W3U_START) == 1 and base.count(W3U_END) == 1
    assert css[:css.index(W3U_START)] == base[:base.index(W3U_START)]
    region = slice(css.index(W3U_START), css.index(W3U_END) + len(W3U_END))
    base_region = slice(base.index(W3U_START),
                        base.index(W3U_END) + len(W3U_END))
    assert css[region] == base[base_region]


def test_v13_css_region_law():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert css.count(W3U_START) == 1 and css.count(W3U_END) == 1
    # DEVIATION css_region_position: the frozen W2 x7 merge-anchor test pins the
    # W2A-end -> W2B-start window to spacer-only lines and the file tail to the
    # W2B end anchor, so the commission's spacer-2/3 slot is unshippable; the
    # region sits immediately before the W2A region start instead.
    assert css.index(W3U_START) < css.index(W3U_END) < css.index(W2A_REGION)
    assert css.index(W3U_END) < css.index(SPACER2) < css.index(SPACER3)
    base = subprocess.run(
        ["git", "show", f"{_merge_base()}:templates/intl_workspace_surveillance.css"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    _v13_region_law(css, base)
    assert SITE_CSS_PATH.read_bytes() == CSS_PATH.read_bytes()
    region = _w3u_region(css)
    stripped = re.sub(r"/\*.*?\*/", "", region, flags=re.DOTALL)
    for selector, _body in re.findall(r"([^{}]+)\{([^{}]*)\}", stripped):
        cleaned = re.sub(r":(?:is|where|not)\([^)]*\)", "", selector)
        for part in cleaned.split(","):
            part = part.strip()
            if not part or part.startswith("@"):
                continue
            assert part.startswith(".intl-gs") or re.match(
                r"^html(\[[^\]]+\])+\s*\.intl-gs", part), part
    assert not re.search(r"(--[A-Za-z0-9_-]+)\s*:", region), "custom property"
    for banned in ("--sp-", "--returns-", "--font-zh", "color-mix(", "inset"):
        assert banned not in region, banned
    for value in re.findall(r"border-radius\s*:\s*([^;}\n]+)", region):
        pairs = re.findall(r"var\(--r-(?:panel,12px|btn,8px|pill,999px)\)", value)
        assert len(pairs) == 1 and not re.search(r"--r-(?:card|ctl)\b", value), value
    for value in set(re.findall(r"var\(--[A-Za-z0-9_-]+\s*,[^)]*\)", region)):
        assert re.fullmatch(
            r"var\(--r-(?:panel,12px|btn,8px|pill,999px)\)", value.strip()), value
    for decl in re.findall(r"([^;{}]+)", region):
        prop = decl.split(":")[0].strip().lower()
        assert prop not in ("border-left", "border-right", "border-inline-start",
                            "border-inline-end", "border-block-start",
                            "border-block-end"), decl


def _flip_one_byte(text: str, index: int) -> str:
    char = text[index]
    return text[:index] + ("b" if char == "a" else "a") + text[index + 1:]


def test_v13b_region_law_modes():
    """F-POST-1: the region law is phase-aware, pure and in memory."""
    css = CSS_PATH.read_text(encoding="utf-8")
    start = css.index(W3U_START)
    after = css.index(W3U_END) + len(W3U_END) + 1  # drop the newline as well
    pre_base = css[:start] + css[after:]           # == the real merge-base css
    # (i) PRE: this PR's css against the base without the W3U region passes.
    _v13_region_law(css, pre_base)
    # (ii) POST: base == css passes.
    _v13_region_law(css, css)
    # (iii) POST: a scratch edit inside the W2B region of css still passes —
    # those bytes are the W2B lane's, pinned by its own suite.
    w2b_line = css.index("\n", css.index("/* ==== W2B region")) + 1
    scratch = css[:w2b_line] + "/* scratch w2b edit */\n" + css[w2b_line:]
    _v13_region_law(scratch, css)
    # (iv) POST: one byte changed inside the W3U region fails.
    with pytest.raises(AssertionError):
        _v13_region_law(_flip_one_byte(css, start + (after - start) // 2), css)
    # (v) POST: one byte changed in the prefix fails.
    with pytest.raises(AssertionError):
        _v13_region_law(_flip_one_byte(css, start // 2), css)
    # (vi) PRE: one byte changed in the prefix fails.
    with pytest.raises(AssertionError):
        _v13_region_law(_flip_one_byte(css, start // 2), pre_base)


# ---------------------------------------------------------------- V14 hygiene

def test_v14_template_hygiene():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    for banned in ("<style", "style=", "<script", "onclick=", "onchange=",
                   "onload="):
        assert banned not in template, banned
    assert "gs_stance_chip" not in template
    # with context: _gs_macros resolves t() from the caller — the real build
    # supplies t as an env global, ad-hoc test envs as a macro of the
    # including template (test_intl_eod_publisher_integration RED of run
    # 41180689984), which a context-less import hides.
    assert ("{% import 'intl_workspace/_gs_macros.html.j2' as gs with context %}" in template
            or '{% import "intl_workspace/_gs_macros.html.j2" as gs with context %}' in template)


# ---------------------------------------------------------------- V15 production honesty

def test_v15_production_honesty_and_withheld(builder, fixture):
    production = _dislocations_section(fixture.render_page(variant="production"))
    assert "intl-gs__chip--specimen" not in production
    assert "above threshold" not in production and "高于阈值" not in production
    assert "intl-dislocations__dot" not in production  # no fragility -> no points
    empty_note = builder.COPY["scatter_empty_note"]
    assert empty_note[0] in production or empty_note[1] in production
    fragility_copy = builder.DISLOCATION_REASON_COPY["fragility_unadmitted"]
    assert fragility_copy[0] in production or fragility_copy[1] in production
    stance_copy = reason_copy("stance_unadmitted")
    assert stance_copy[0] in production or stance_copy[1] in production

    withheld = fixture.build_set(withheld=True)
    section = _dislocations_section(fixture.render_page(observations=withheld))
    assert 'class="intl-dislocations__pick' not in section
    census = builder.COPY["empty_census"]
    assert census[0] in section or census[1] in section
    payload = builder.build_payload(universe=fixture.universe(),
                                    workspace=fixture.workspace(),
                                    observations=withheld)
    assert payload["counts"]["ranked"] == 0
    assert payload["selected"] is None
    assert any("withheld" in note["en"].lower() for note in payload["footnotes"])


# ---------------------------------------------------------------- V16 decomposition

def test_v16_decomposition_identity_and_series_ink(fixture):
    html = fixture.render_page(variant="specimen", scenario="restricted")
    section = _dislocations_section(html)
    assert "intl-dislocations__leg--local" in section
    assert "intl-dislocations__leg--fx" in section
    assert re.search(r'intl-dislocations__leg--cross', section)
    css = _w3u_region(CSS_PATH.read_text(encoding="utf-8"))
    assert "fill:var(--ser-1)" in css.replace(" ", "")
    assert "fill:var(--ser-2)" in css.replace(" ", "")
    cross_rule = re.search(r'\.intl-gs \.intl-dislocations__leg--cross\{([^}]*)\}', css)
    assert cross_rule and "var(--info)" in cross_rule.group(1) \
        and "fill:none" in cross_rule.group(1).replace(" ", "")
    observation_set = fixture.build_set()
    for observation in _x_usd(observation_set):
        if observation["decomposition"] is None:
            continue
        d = observation["decomposition"]
        residual_pp = abs(d["local_pct"] + d["fx_pct"] + d["interaction_pp"]
                          - d["usd_pct"])
        assert residual_pp <= RETURN_IDENTITY_TOLERANCE * 100 + 1e-9


# ---------------------------------------------------------------- V17 not plotted

def test_v17_not_plotted_completeness(builder, fixture):
    payload = builder.build_payload(
        universe=fixture.universe(), workspace=fixture.workspace(),
        observations=fixture.build_set(), fragility=fixture.SPECIMEN_FRAGILITY,
        specimen=True)
    carried = {row["market_id"] for row in payload["rows"]}
    plotted = {point["market_id"] for point in payload["scatter"]["points"]}
    chipped = {chip["market_id"] for chip in payload["scatter"]["not_plotted"]}
    assert plotted | chipped == carried
    assert not plotted & chipped
    html = fixture.render_page(variant="specimen", scenario="restricted")
    for chip in payload["scatter"]["not_plotted"]:
        if chip["reason"] == "fragility_unadmitted":
            expected = builder.DISLOCATION_REASON_COPY["fragility_unadmitted"]
        elif chip["reason"] in builder.DISLOCATION_REASON_COPY:
            expected = builder.DISLOCATION_REASON_COPY[chip["reason"]]
        else:
            expected = reason_copy(chip["reason"])
        assert expected[0] in html and expected[1] in html, chip
    production_payload = builder.build_payload(
        universe=fixture.universe(), workspace=fixture.workspace(),
        observations=fixture.build_set())
    assert production_payload["scatter"]["points"] == []
    production_carried = {row["market_id"] for row in production_payload["rows"]}
    production_chipped = {chip["market_id"]
                          for chip in production_payload["scatter"]["not_plotted"]}
    assert production_chipped == production_carried


# ---------------------------------------------------------------- V18 scatter

def test_v18_scatter_geometry(builder, fixture):
    payload = builder.build_payload(
        universe=fixture.universe(), workspace=fixture.workspace(),
        observations=fixture.build_set(), fragility=fixture.SPECIMEN_FRAGILITY,
        specimen=True)
    html = fixture.render_page(variant="specimen", scenario="restricted")
    scatter = re.search(r'<svg class="intl-dislocations__scatter[^"]*"[^>]*>.*?</svg>',
                        html, re.DOTALL)
    assert scatter, "no scatter svg"
    svg = scatter.group(0)
    assert 'viewBox="0 0 640 420"' in svg
    assert 'role="img"' in svg and "aria-label" in svg
    assert re.search(r'<line[^>]*x1="395\.2"', svg), "threshold line not at 60"
    # SVG-safe bilingual labels: every <text> twin carries the estate i18n
    # class pair, and NO t() span may appear inside the svg — a <span> inside
    # foreign content is an HTML-parser breakout tag that silently truncates
    # the chart after the first label (attack finding (a), r2).
    assert not re.search(r"<span", svg), "t() markup inside the scatter svg"
    threshold_text = re.search(
        r'<text class="intl-dislocations__thresholdlabel l-en"[^>]*>(.*?)</text>',
        svg, re.DOTALL)
    assert threshold_text, "threshold label EN text twin missing"
    assert re.search(
        r'<text class="intl-dislocations__thresholdlabel l-zh"[^>]*>(.*?)</text>',
        svg, re.DOTALL), "threshold label ZH text twin missing"
    threshold_copy = builder.COPY["threshold_label"]
    assert threshold_copy[0] in threshold_text.group(1)
    y_title = builder.COPY["y_axis_title"]
    assert y_title[0] in svg or y_title[1] in svg
    assert "σ" not in svg and "sigma" not in svg.lower()
    x_title = builder.COPY["x_axis_title"]
    assert x_title[0] in svg or x_title[1] in svg
    assert svg.count("intl-dislocations__gridline") >= 6
    attention = builder.COPY["attention_ticks"]
    assert attention[0] in svg or attention[1] in svg
    clamped = [point for point in payload["scatter"]["points"] if point["clamped"]]
    assert clamped and clamped[0]["market_id"] == "JP"
    assert "intl-dislocations__clamp" in svg
    assert 'class="intl-dislocations__vh"' in html


# ---------------------------------------------------------------- V19 radios

def test_v19_radio_selection_contract(builder, fixture):
    payload = builder.build_payload(
        universe=fixture.universe(), workspace=fixture.workspace(),
        observations=fixture.build_set())
    html = fixture.render_page(variant="production", scenario="restricted")
    radios = re.findall(
        r'<input type="radio" class="intl-dislocations__pick"[^>]*>', html)
    assert 0 < len(radios) <= 12
    assert len(radios) == payload["counts"]["ranked"]
    assert "checked" in radios[0]
    for index, radio in enumerate(radios):
        assert f'data-i="{index}"' in radio
    labels = re.findall(r'<label[^>]*for="(im-gs-dislocations-pick-\d+)"[^>]*'
                        r'data-i="(\d+)"', html)
    assert {fid for fid, _ in labels} == {
        f"im-gs-dislocations-pick-{i}" for i in range(len(radios))}
    split = html.index("intl-dislocations__explorer")
    ranking = html.index("intl-dislocations__ranking")
    first_radio = html.index('class="intl-dislocations__pick"')
    assert first_radio < split < ranking
    css = _w3u_region(CSS_PATH.read_text(encoding="utf-8"))
    flat = re.sub(r"\s+", " ", css)
    for index in range(12):
        for fragment in (
            f'.intl-gs .intl-dislocations__pick[data-i="{index}"]:checked ~ .intl-gs__split .intl-dislocations__insp[data-i="{index}"]{{display:grid;}}',
            f'.intl-gs .intl-dislocations__pick[data-i="{index}"]:checked ~ .intl-gs__split .intl-dislocations__peers[data-i="{index}"]{{display:grid;}}',
            f'.intl-gs .intl-dislocations__pick[data-i="{index}"]:checked ~ .intl-gs__split .intl-dislocations__ring[data-i="{index}"]{{display:inline;}}',
            f'.intl-gs .intl-dislocations__pick[data-i="{index}"]:checked ~ .intl-dislocations__ranking tr[data-i="{index}"]{{outline:1.5px solid var(--info);outline-offset:-1.5px;}}',
            f'.intl-gs .intl-dislocations__pick[data-i="{index}"]:focus-visible ~ .intl-dislocations__ranking label[data-i="{index}"]{{outline:2px solid var(--link);outline-offset:3px;}}',
        ):
            assert fragment in flat, fragment
    pick_rule = re.search(r"\.intl-gs \.intl-dislocations__pick\{([^}]*)\}", css)
    assert pick_rule, "no visually hidden rule for the radios"
    assert "display:none" not in pick_rule.group(1).replace(" ", "")
    assert "clip-path" in pick_rule.group(1)


# ---------------------------------------------------------------- V20 determinism

def test_v20_determinism_and_dict_order_independence(builder, fixture):
    workspace, universe = fixture.workspace(), fixture.universe()
    first = builder.build_payload(universe=universe, workspace=workspace,
                                  observations=fixture.build_set())
    second = builder.build_payload(universe=universe, workspace=workspace,
                                   observations=fixture.build_set())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    shuffled = fixture.build_set()
    shuffled["bases"] = {
        basis: list(reversed(entries))
        for basis, entries in reversed(list(shuffled["bases"].items()))}
    third = builder.build_payload(universe=universe, workspace=workspace,
                                  observations=shuffled)
    assert json.dumps(first, sort_keys=True) == json.dumps(third, sort_keys=True)
    assert fixture.render_page() == fixture.render_page()


# ---------------------------------------------------------------- V21 no I/O

def test_v21_no_network_and_no_writes(builder, fixture, monkeypatch):
    import socket

    def refuse_socket(*args, **kwargs):
        raise AssertionError("network access during build_view/render")

    monkeypatch.setattr(socket, "socket", refuse_socket)
    real_open = open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"write during build_view/render: {file} {mode}")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", guarded_open)
    payload = builder.build_payload(universe=fixture.universe(),
                                    workspace=fixture.workspace(),
                                    observations=fixture.build_set())
    assert payload["counts"]["ranked"] > 0
    assert "intl-dislocations__root" in fixture.render_page()


# ---------------------------------------------------------------- V22 seam frozen

def test_v22_seam_files_unchanged_and_builder_registered():
    sha = _merge_base()
    for path in (MOUNT_PATH, BUILD_INTL_PATH):
        result = subprocess.run(["git", "diff", "--quiet", sha, "--", str(path)],
                                cwd=REPO, capture_output=True, text=True)
        assert result.returncode == 0, f"{path} changed vs merge base"
    mount = _load(MOUNT_PATH, "lib.intl_surveillance_mount_check")
    assert mount.BUILDERS["dislocations"] == "lib.intl_gs_dislocations_view"
    module = _load(BUILDER_PATH, "lib.intl_gs_dislocations_view_check")
    assert callable(module.build_view)


# ---------------------------------------------------------------- V23 horizon

def test_v23_horizon_selection(builder, fixture):
    universe, workspace = fixture.universe(), fixture.workspace()
    payload = builder.build_payload(universe=universe, workspace=workspace,
                                    observations=fixture.build_set())
    assert payload["horizon"] == "1m"
    three_month = builder.build_payload(
        universe=universe, workspace=workspace,
        observations=fixture.build_set(horizon="3m"))
    assert three_month["horizon"] == "3m"
    assert builder.build_payload(universe=universe, workspace=workspace,
                                 observations=fixture.build_set(horizon="ytd")) is None


# ------------------------------------------- V24 direction→ink (review R-01)

def _signed_text(value: float, dp: int = 2) -> str:
    """The exact numeral text gs_signed emits (typed sign, U+2212 minus)."""
    sign = "+" if value > 0 else ("−" if value < 0 else "")
    return f"{sign}{abs(value):.{dp}f}"


def test_v24_direction_to_ink_binding_for_z_numerals(builder, fixture):
    """R14 §6 signed ink, pinned after review R-01 (surviving mutant RM-2).

    Every direction-bound numeral — the ranking Z cell, the printed residual
    value beside the bar, and the inspector Z — must carry the foundation ink
    class for its receipt direction (above→up, below→down), never a swapped
    one; and the ink must travel exclusively through the foundation classes so
    the ZH red-up inversion comes from theme.css's --up/--down swap alone.
    """
    payload = builder.build_payload(universe=fixture.universe(),
                                    workspace=fixture.workspace(),
                                    observations=fixture.build_set(
                                        scenario="restricted"))
    ranked = [row for row in payload["rows"] if row["index"] is not None]
    assert ranked, "fixture must carry ranked rows"
    assert {"above", "below"} <= {row["direction"] for row in ranked}, \
        "pin needs at least one above and one below ranked row"
    html = fixture.render_page(variant="production", scenario="restricted")
    section = _dislocations_section(html)
    ink_for = {"above": "up", "below": "down"}
    for row in ranked:
        ink = ink_for.get(row["direction"], "muted")
        numeral = (f'<span class="intl-gs__num intl-gs__num--{ink}">'
                   f'{_signed_text(row["z"])}</span>')
        row_html = re.search(rf'<tr data-i="{row["index"]}">.*?</tr>',
                             section, re.DOTALL)
        assert row_html, f"ranked row {row['market_id']} missing"
        for label in ("Z", "RESIDUAL"):
            cell = re.search(rf'<td[^>]*data-label="{label}"[^>]*>.*?</td>',
                             row_html.group(0), re.DOTALL)
            assert cell, f"{label} cell missing for {row['market_id']}"
            assert numeral in cell.group(0), \
                f"{label} numeral for {row['market_id']} (direction " \
                f"{row['direction']}) does not carry {ink} ink"
        # inspector Z (rail pane for this index; slice to the next pane/aside)
        start = section.index(f'intl-dislocations__insp" data-i="{row["index"]}"')
        nxt = section.find('intl-dislocations__insp" data-i=', start + 1)
        inspector = section[start:nxt if nxt != -1 else section.index("</aside>")]
        assert numeral in inspector, \
            f"inspector Z for {row['market_id']} does not carry {ink} ink"
    # the ZH inversion pathway, pinned by construction:
    css = CSS_PATH.read_text(encoding="utf-8")
    assert ".intl-gs__num--up{color:var(--ink-up);}" in css.replace(" ", "")
    assert ".intl-gs__num--down{color:var(--ink-down);}" in css.replace(" ", "")
    for selector, _body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if "data-lang" in selector:
            assert "num--up" not in selector and "num--down" not in selector, \
                f"per-language ink override: {selector}"
    theme = (REPO / "templates/theme.css").read_text(encoding="utf-8")
    assert re.search(r"--ink-up:[^;}]*var\(--up\)", theme), \
        "--ink-up no longer derives from --up"
    assert re.search(r"--ink-down:[^;}]*var\(--down\)", theme), \
        "--ink-down no longer derives from --down"
    zh_block = re.search(r'html\[data-lang="zh"\]\s*\{([^}]*)\}', theme)
    assert zh_block, "theme.css zh block missing"
    assert "--up:" in zh_block.group(1) and "--down:" in zh_block.group(1), \
        "theme.css zh block no longer swaps --up/--down (ZH red-up)"


# ------------------------------------------- V25 bandhead (review R-02)

def test_v25_first_band_head_title_and_horizon_label(builder, fixture):
    """FROZEN SPEC 2 ROOT clause, pinned after review R-02.

    The first band head (the gs_panel_root aria-labelledby target) is titled
    "Dislocation explorer"/"错位探索" and carries the horizon label alongside
    qnum Q2, the computed_at clock and — specimen variant only — the specimen
    chip; the head never repeats the qnum inside its title.
    """
    for variant, expect_chip in (("specimen", True), ("production", False)):
        html = fixture.render_page(variant=variant, scenario="restricted")
        section = _dislocations_section(html)
        assert 'aria-labelledby="im-gs-dislocations-dislocations-title"' \
            in section
        heads = re.findall(r'<div class="intl-gs__bandhead">(.*?)</div>',
                           section, re.DOTALL)
        head = next((h for h in heads
                     if 'id="im-gs-dislocations-dislocations-title"' in h), None)
        assert head, "first band head (title id) missing"
        title = re.search(
            r'<h2 class="intl-gs__bandhead__title"[^>]*>(.*?)</h2>',
            head, re.DOTALL)
        assert title, "band head h2 missing"
        assert "<span class=\"l-en\">Dislocation explorer</span>" in title.group(1)
        assert "<span class=\"l-zh\">错位探索</span>" in title.group(1)
        assert "dislocation map" not in title.group(1) \
            and "错位图" not in title.group(1), \
            "the head must not repeat the qnum inside its title (R-02)"
        assert re.search(r'<span class="intl-gs__eyebrow">.*>\s*Q2\s*<',
                         head, re.DOTALL), "qnum eyebrow missing"
        assert '<span class="intl-gs__bandhead__sub">' in head, \
            "horizon label (band head sub) missing"
        horizon_label = builder.build_payload(
            universe=fixture.universe(), workspace=fixture.workspace(),
            observations=fixture.build_set(scenario="restricted"))["horizon_label"]
        assert f">{horizon_label['en']}<" in head
        assert f">{horizon_label['zh']}<" in head
        assert re.search(r'<span class="intl-gs__bandhead__clock', head), \
            "computed_at clock missing from the band head"
        assert ("intl-gs__chip--specimen" in section) is expect_chip, variant


# ---------------------------------------------------------------- helpers

def _dislocations_section(html: str) -> str:
    """The full dislocations panel root INCLUDING its nested sub-sections
    (scatter, peers, ranking): scans <section>/</section> depth from the panel
    start — a lazy regex stops at the first nested close."""
    start = html.find('<section class="intl-gs__panel intl-gs__view '
                      'intl-gs__view--dislocations"')
    assert start != -1, "dislocations panel missing from the rendered page"
    depth, cursor = 0, start
    for match in re.finditer(r"<section\b|</section>", html[start:]):
        depth += 1 if match.group(0) == "<section" else -1
        if depth == 0:
            cursor = start + match.end()
            break
    assert cursor > start, "dislocations panel never closes"
    return html[start:cursor]


def _w3u_region(css: str) -> str:
    start = css.index(W3U_START) + len(W3U_START)
    return css[start:css.index(W3U_END)]


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)
