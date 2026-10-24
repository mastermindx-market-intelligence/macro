"""INTL-GS-W2F foundation contracts (spec R14, DEC:INTL-GS-R14-DESIGN-FREEZE).

RED-first suite: written before any implementation existed (see
LANE_RECORD_INTL-GS-W2F.md for the RED receipt). Covers the scoped §5.3 token
block, the L1–L12 design laws the reviewer attacks, shell registration of the
seven surveillance views, the mount/builder contract and the access wiring.
"""
import ast
import importlib.util
import re
import subprocess
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

CSS_PATH = REPO / "templates/intl_workspace_surveillance.css"
MACROS_PATH = REPO / "templates/intl_workspace/_gs_macros.html.j2"
FIXTURE_PATH = REPO / "templates/intl_workspace/_gs_state_fixture.html.j2"
MOUNT_PATH = REPO / "lib/intl_surveillance_mount.py"
SHELL_PATH = REPO / "templates/intl_workspace/shell.html.j2"
INTL_PAGE_PATH = REPO / "templates/intl.html.j2"
STATE_JS_PATH = REPO / "templates/intl_workspace_state.js"
WORKSPACE_JS_PATH = REPO / "templates/intl_workspace.js"
BUILD_INTL_PATH = REPO / "scripts/build_intl.py"
SITE_ACCESS_PATH = REPO / "config/site_access.yml"
CADDY_PATH = REPO / "app/deploy/Caddyfile"
SPEC_PATH = REPO / "research/INTL_GLOBAL_SURVEILLANCE_DESIGN_SPEC_R14_2026-10-21.md"

TOKEN_MARK_START = "/* === INTL-GS §5.3 TOKENS — amendment A1 (2026-10-22): pure theme derivations, no literals === */"
TOKEN_MARK_END = "/* === END INTL-GS §5.3 TOKENS === */"

GS_VIEWS = ("scanner", "dislocations", "transmission", "dossier", "scenario", "replay", "coverage")
GS_EN = {"scanner": "Scanner", "dislocations": "Dislocations", "transmission": "Transmission",
         "dossier": "Dossiers", "scenario": "Scenario lab", "replay": "Replay", "coverage": "Coverage"}
GS_ZH = {"scanner": "扫描", "dislocations": "背离", "transmission": "传导", "dossier": "档案",
         "scenario": "情景", "replay": "回放", "coverage": "覆盖"}
LEGACY_VIEWS = ("overview", "compare", "macro", "risk", "history", "library")
ALL_VIEWS = LEGACY_VIEWS + GS_VIEWS

# The §5.3 block exactly as frozen in the spec on main (blob 5d9c51dc…).
SPEC_BLOCK = """.intl-gs{
  --r-panel:var(--r-card); --r-btn:var(--r-ctl);
  --r-pill:calc(var(--r-card) * 100);   /* pill = any radius ≥ half-height; theme has no pill token */
  --ser-1:var(--info); --ser-2:var(--q2); --ser-3:var(--ok); --ser-4:var(--orange);
  --ink-tier:var(--ink-link);           /* tier_preview.css's own default outside the prophet gate */
}
/* returns heat — FILL ONLY, never text ink; follows --up/--down so light theme and ZH red-up
   hold BY CONSTRUCTION (theme.css L277 swaps --up/--down under html[data-lang="zh"]) */
.intl-gs__heat--up-soft{fill:var(--up);fill-opacity:.14;}
.intl-gs__heat--up-mid{fill:var(--up);fill-opacity:.26;}
.intl-gs__heat--up-strong{fill:var(--up);fill-opacity:.42;}
.intl-gs__heat--down-soft{fill:var(--down);fill-opacity:.14;}
.intl-gs__heat--down-mid{fill:var(--down);fill-opacity:.26;}
.intl-gs__heat--down-strong{fill:var(--down);fill-opacity:.42;}
.intl-gs__heatbg{position:relative;isolation:isolate;}
.intl-gs__heatbg::before{content:"";position:absolute;inset:0;background:var(--heat-ink);opacity:var(--heat-a);z-index:-1;pointer-events:none;}
.intl-gs__heatbg--up-strong{--heat-ink:var(--up);--heat-a:.42;}
.intl-gs__heatbg--down-strong{--heat-ink:var(--down);--heat-a:.42;}"""

HEATBG_BEFORE_SELECTOR = ".intl-gs__heatbg::before"
HEATBG_BEFORE_BODY = 'content:"";position:absolute;inset:0;background:var(--heat-ink);opacity:var(--heat-a);z-index:-1;pointer-events:none;'
A1_SUPERSEDED = ("--" + "sp-", "--" + "returns-", "--" + "font-zh", "#" + "9b86ff", "#" + "5b3fc4")

STATE_ORDER = ("restricted", "loading", "abstain", "stale", "suspended", "closed", "corrected",
               "qualified", "partial", "recovered", "empty", "complete")
STATE_EN = {"complete": "Complete", "loading": "Loading", "qualified": "Qualified", "abstain": "Abstain",
            "empty": "No data", "partial": "Partial", "stale": "Stale", "closed": "Closed",
            "suspended": "Suspended", "restricted": "Restricted", "corrected": "Corrected",
            "recovered": "Recovered"}
STATE_ZH = {"complete": "完整", "loading": "加载中", "qualified": "有条件", "abstain": "弃权",
            "empty": "无数据", "partial": "部分", "stale": "过期", "closed": "休市",
            "suspended": "停牌", "restricted": "受限", "corrected": "已更正", "recovered": "已恢复"}


def _require(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"required file missing: {path.relative_to(REPO)}")
    return path.read_text(encoding="utf-8")


def _css() -> str:
    return _require(CSS_PATH)


def _strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _rules(text: str):
    """Flat (selector, body) pairs; @media/@keyframes wrappers fall away."""
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
        yield match.group(1), match.group(2)


def _token_region(text: str) -> str:
    start = text.index(TOKEN_MARK_START) + len(TOKEN_MARK_START)
    end = text.index(TOKEN_MARK_END)
    return text[start:end]


def _outside_token_region(text: str) -> str:
    start = text.index(TOKEN_MARK_START)
    end = text.index(TOKEN_MARK_END) + len(TOKEN_MARK_END)
    return text[:start] + text[end:]


def _fixture_site():
    spec = importlib.util.spec_from_file_location(
        "intl_gs_fixture_site", REPO / "tests/intl_gs_fixture_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _render_env(extra=None):
    from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
    loader = FileSystemLoader(str(REPO / "templates"))
    if extra:
        loader = ChoiceLoader([DictLoader(extra), loader])
    env = Environment(loader=loader, autoescape=False)
    from engine import i18n
    env.globals.update(t=i18n.t, tr=i18n.tr, td=i18n.td)
    return env


# ---------------------------------------------------------------- 2.1 tokens


def test_spec_block_present_verbatim_between_markers():
    css = _css()
    assert TOKEN_MARK_START in css and TOKEN_MARK_END in css
    assert css.index(TOKEN_MARK_START) < css.index(TOKEN_MARK_END)
    assert SPEC_BLOCK in _token_region(css), "§5.3 block must be copied verbatim inside the markers"
    assert _token_region(css).count(".intl-gs{") >= 1


def test_every_selector_is_intl_gs_scoped():
    css = _strip_comments(_css())
    offenders = []
    for selector, _body in _rules(css):
        selector = re.sub(r":(?:is|where|not)\([^)]*\)", "", selector)
        for part in selector.split(","):
            part = part.strip()
            if not part or part.startswith("@") or re.fullmatch(r"\d+%|from|to", part):
                continue
            if not (part.startswith(".intl-gs") or re.match(r"^html(\[[^\]]+\])+\s*\.intl-gs", part)):
                offenders.append(part)
    assert not offenders, f"selectors outside .intl-gs scope: {offenders}"


def test_no_igs_token_anywhere_in_owned_templates():
    for path in (CSS_PATH, MACROS_PATH, FIXTURE_PATH):
        text = _require(path)
        assert ".igs" not in text and "igs-" not in text and "-igs" not in text, path


def test_a1_block_in_spec_amendment_verbatim():
    spec = _require(SPEC_PATH)
    head = "### 5.3 amendment A1 (2026-10-22)"
    assert spec.count(head) == 1, "spec must carry the §5.3 amendment A1 subsection once"
    start = spec.index(head)
    section = spec[start:spec.index("\n## 6.", start)]
    assert TOKEN_MARK_START + "\n" + SPEC_BLOCK in section


def test_a1_token_block_is_pure_theme_derivation():
    region = _strip_comments(_token_region(_css()))
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", region), "hex literal in the A1 block"
    assert not re.findall(r"\d+(?:\.\d+)?px\b", region), "px literal in the A1 block"
    assert not re.findall(r"\b(?:rgb|rgba|hsl|hsla|color-mix)\(", region), "colour function in the A1 block"
    for name, value in re.findall(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;}\n]+)", region):
        assert "var(--" in value or re.fullmatch(r"\.\d+", value.strip()), (name, value)


def test_a1_heat_follows_direction_tokens():
    rules = {sel.strip(): body.strip() for sel, body in _rules(_strip_comments(_css()))}
    for side in ("up", "down"):
        for step, alpha in (("soft", ".14"), ("mid", ".26"), ("strong", ".42")):
            assert rules[f".intl-gs__heat--{side}-{step}"] == f"fill:var(--{side});fill-opacity:{alpha};"
        assert rules[f".intl-gs__heatbg--{side}-strong"] == f"--heat-ink:var(--{side});--heat-a:.42;"


def test_a1_superseded_tokens_and_literal_fallbacks_absent():
    owned = [CSS_PATH, REPO / "site/intl_workspace_surveillance.css", MACROS_PATH, FIXTURE_PATH,
             REPO / "tests/intl_gs_foundation_browser.test.cjs", REPO / "tests/intl_gs_fixture_site.py"]
    for path in owned:
        text = _require(path)
        for needle in A1_SUPERSEDED:
            assert needle not in text, (path.name, needle)
    css = _strip_comments(_css())
    # Seat ruling A1.1 (2026-10-22): --r-card/--r-ctl are not yet at :root (DS-PR-0 pending), so radius
    # declarations carry exactly these three estate fallback pairs; every other var() fallback is refused.
    for path, text in ((CSS_PATH, css), (MACROS_PATH, _require(MACROS_PATH)), (FIXTURE_PATH, _require(FIXTURE_PATH))):
        opened = re.findall(r"var\(--[A-Za-z0-9_-]+\s*,", text)
        allowed = re.findall(r"var\(--r-(?:panel,12px|btn,8px|pill,999px)\)", text)
        assert len(opened) == len(allowed), (path.name, "var() fallback outside the A1.1 pairs", opened)
    assert not re.search(r"--[A-Za-z0-9_-]+::?(?:before|after)", css), "pseudo-element directly after a --modifier"


def test_site_css_is_byte_identical_to_template():
    assert (REPO / "site/intl_workspace_surveillance.css").read_bytes() == CSS_PATH.read_bytes()


# ---------------------------------------------------------------- 2.2 L1 stripe


def test_no_accent_stripe_l1():
    css = _strip_comments(_css())
    sanctioned = 0
    for selector, body in _rules(css):
        if selector.strip() == HEATBG_BEFORE_SELECTOR:
            # A1 (2026-10-22): the ONE pseudo-element allowed to paint, the returns-heat
            # background layer. It fills the whole box behind the content (inset:0) and can
            # never become an edge: no size, offset, border, outline or shadow declarations.
            assert body.strip() == HEATBG_BEFORE_BODY, body
            props = {d.split(":", 1)[0].strip().lower() for d in body.split(";") if d.strip()}
            assert "inset" in props, props
            assert not props & {"width", "height", "min-width", "min-height", "max-width",
                                "max-height", "left", "right", "top", "bottom", "inset-inline",
                                "inset-block", "inset-inline-start", "inset-inline-end",
                                "inset-block-start", "inset-block-end", "border", "border-width",
                                "border-color", "border-style", "box-shadow", "outline",
                                "transform", "clip-path"}, props
            sanctioned += 1
            continue
        for decl in body.split(";"):
            decl = decl.strip()
            prop = decl.split(":")[0].strip().lower()
            assert prop not in ("border-left", "border-right", "border-inline-start",
                                "border-inline-end", "border-block-start", "border-block-end"), selector
            if prop in ("border-top", "border-bottom"):
                assert decl.endswith("1px solid var(--line)") or decl.endswith(":none"), (selector, decl)
                assert re.search(r"row|cell|table|head", selector), (selector, decl)
        assert "inset" not in body, selector
        if "::before" in selector or "::after" in selector:
            # The only permitted pseudo-element rule is one that neutralises a
            # page-wide accent bar inside the scope (VF15) — it may draw nothing.
            assert re.fullmatch(r"content:\s*none;?", body.strip()), (selector, body)
        else:
            assert "::before" not in selector and "::after" not in selector, selector
    assert sanctioned == 1, "the heat background layer must be the one sanctioned pseudo-element"


# ---------------------------------------------------------------- 2.3 L2 focus/ring


def test_focus_visible_rule_covers_primitives():
    css = _strip_comments(_css())
    found = None
    for selector, body in _rules(css):
        if ":focus-visible" in selector:
            compact = body.replace(" ", "")
            if "outline:2pxsolidvar(--link)" in compact and "outline-offset:3px" in compact:
                found = selector
    assert found, "focus rule outline:2px solid var(--link); outline-offset:3px missing"
    for token in ("button", "__seg__opt", "__qcard", "__row", "__chip--link"):
        assert token in found, f"focus rule does not cover {token}"


def test_selected_ring_is_info_1_5px():
    css = _strip_comments(_css())
    assert re.search(r"outline:\s*1\.5px solid var\(--info\)", css), "1.5px var(--info) ring missing"


# ---------------------------------------------------------------- 2.4 T3 literal mirror


def test_no_colour_font_or_radius_literals_outside_token_block():
    outside = _strip_comments(_outside_token_region(_css()))
    hexes = re.findall(r"#[0-9a-fA-F]{3,8}\b", outside)
    assert not hexes, f"hex literals outside §5.3 block: {hexes}"
    funcs = re.findall(r"\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch|color-mix|color)\(", outside)
    assert not funcs, f"colour functions outside §5.3 block: {funcs}"
    for value in re.findall(r"font-family\s*:\s*([^;}\n]+)", outside):
        assert re.fullmatch(r"\s*var\(--font-(?:ui|mono|zh)\)(?:\s*,\s*var\(--font-(?:ui|zh)\))?\s*", value), value
    for value in re.findall(r"border-radius\s*:\s*([^;}\n]+)", outside):
        # A1.1: exactly one scoped estate pair per declaration (calc() allowed); never --r-card/--r-ctl here
        pairs = re.findall(r"var\(--r-(?:panel,12px|btn,8px|pill,999px)\)", value)
        assert len(pairs) == 1 and not re.search(r"--r-(?:card|ctl)\b", value), value


# ---------------------------------------------------------------- 2.5 shell registration


def _view_nav_buttons(html):
    return re.findall(r'<button[^>]*data-im-action="set_view"[^>]*data-im-view="([a-z]+)"[^>]*>(.*?)</button>', html)


def _view_select_options(html):
    return re.findall(r'<option value="([a-z]+)"[^>]*data-im-label-en="([^"]*)"[^>]*data-im-label-zh="([^"]*)"[^>]*>', html)


def test_shell_lists_all_thirteen_views_with_labels():
    module = _fixture_site()
    html = module.render_intl_page()
    buttons = _view_nav_buttons(html)
    assert [b[0] for b in buttons] == list(ALL_VIEWS)
    for key, rendered in buttons:
        if key in GS_ZH:
            assert GS_EN[key] in rendered and GS_ZH[key] in rendered, (key, rendered)
    view_select = html.split('<select data-im-action="set_view">', 1)[1].split("</select>", 1)[0]
    options = _view_select_options(view_select)
    assert [o[0] for o in options] == list(ALL_VIEWS)
    for key, en, zh in options:
        if key in GS_ZH:
            assert (en, zh) == (GS_EN[key], GS_ZH[key]), (key, en, zh)


def test_seven_new_tabs_disabled_without_available_payload():
    module = _fixture_site()
    html = module.render_intl_page()
    for key in GS_VIEWS:
        button = re.search(r'<button[^>]*data-im-view="%s"[^>]*>' % key, html).group(0)
        assert "disabled" in button, key
        option = re.search(r'<option value="%s"[^>]*>' % key, html).group(0)
        assert "disabled" in option, key


def test_legacy_entries_byte_identical_with_and_without_payload():
    module = _fixture_site()
    base = module.render_intl_page(include_surveillance=False)
    payload = module.render_intl_page()
    assert base and payload
    nav1 = base.split('<nav class="intl-workspace__view-nav"', 1)[1].split("</nav>", 1)[0]
    nav2 = payload.split('<nav class="intl-workspace__view-nav"', 1)[1].split("</nav>", 1)[0]
    for key in LEGACY_VIEWS:
        line1 = [l for l in nav1.split("<button") if 'data-im-view="%s"' % key in l]
        line2 = [l for l in nav2.split("<button") if 'data-im-view="%s"' % key in l]
        assert line1 and line2 and line1 == line2, key
    sel1 = base.split('<select data-im-action="set_view">', 1)[1].split("</select>", 1)[0]
    sel2 = payload.split('<select data-im-action="set_view">', 1)[1].split("</select>", 1)[0]
    for key in LEGACY_VIEWS:
        line1 = [l for l in sel1.split("<option") if 'value="%s"' % key in l]
        line2 = [l for l in sel2.split("<option") if 'value="%s"' % key in l]
        assert line1 and line2 and line1 == line2, key


def test_shell_renders_no_surveillance_wrapper_without_panels():
    module = _fixture_site()
    html = module.render_intl_page()
    assert 'class="intl-gs"' not in html, "wrapper must not render with no panels"


# ---------------------------------------------------------------- 2.6 stub view


def test_stub_coverage_view_enables_only_coverage():
    module = _fixture_site()
    html = module.render_intl_page(stub_coverage=True)
    button = re.search(r'<button[^>]*data-im-view="coverage"[^>]*>', html).group(0)
    assert "disabled" not in button
    for key in GS_VIEWS:
        if key == "coverage":
            continue
        other = re.search(r'<button[^>]*data-im-view="%s"[^>]*>' % key, html).group(0)
        assert "disabled" in other, key
    section = re.search(r'<section[^>]*data-im-panel[^>]*data-view="coverage"[^>]*>', html).group(0)
    for attr in ("data-view", "data-horizon", "data-basis", "data-source"):
        assert attr in section, attr
    workspace_at = html.index('class="intl-workspace"')
    wrapper_at = html.index('class="intl-gs"')
    assert workspace_at < wrapper_at, "surveillance wrapper must render inside the workspace"


# ---------------------------------------------------------------- 2.7 mount contract


def _base_workspace():
    from engine.intl_workspace_overview import build_workspace_overviews
    return build_workspace_overviews(None)


def _load_mount():
    spec = importlib.util.spec_from_file_location("lib.intl_surveillance_mount", MOUNT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gs_views_and_builders_tables():
    mount = _load_mount()
    assert mount.GS_VIEWS == GS_VIEWS
    assert mount.BUILDERS == {view: f"lib.intl_gs_{view}_view" for view in GS_VIEWS}


def test_attach_surveillance_none_is_none():
    assert _load_mount().attach_surveillance(None) is None


def test_absent_builders_are_not_built_and_leave_workspace_intact():
    mount = _load_mount()
    workspace = _base_workspace()
    result = mount.attach_surveillance(workspace, universe_loader=lambda: {}, rights_loader=lambda: {})
    assert set(result["surveillance"]["views"]) == set(GS_VIEWS)
    assert all(v["status"] == "not_built" for v in result["surveillance"]["views"].values())
    assert result["surveillance_panels"] == []
    for key in workspace:
        if key in ("surveillance", "surveillance_panels"):
            continue
        assert result[key] == workspace[key] or key in ("panels",), key
    assert "surveillance" not in workspace, "caller workspace must not be mutated"


def test_loaders_come_from_engine_module_and_are_callable(monkeypatch):
    mount = _load_mount()
    from engine import intl_global_universe as engine_module
    calls = {"universe": 0, "rights": 0}
    monkeypatch.setattr(engine_module, "load_universe", lambda: (calls.__setitem__("universe", calls["universe"] + 1) or {}))
    monkeypatch.setattr(engine_module, "load_rights_matrix", lambda: (calls.__setitem__("rights", calls["rights"] + 1) or {}))
    monkeypatch.setattr(engine_module, "coverage_summary", lambda universe, capability: {"capability": capability})
    mount.attach_surveillance(_base_workspace())
    assert calls == {"universe": 1, "rights": 1}
    universe_block = mount.attach_surveillance(_base_workspace())["surveillance"]["universe"]
    assert set(universe_block) == set(engine_module.CAPABILITIES)


def test_loader_failure_marks_every_view_error_and_keeps_page(monkeypatch):
    mount = _load_mount()

    def boom():
        raise RuntimeError("no universe")

    workspace = _base_workspace()
    result = mount.attach_surveillance(workspace, universe_loader=boom, rights_loader=lambda: {})
    assert all(v["status"] == "error" for v in result["surveillance"]["views"].values())
    assert result["surveillance_panels"] == []
    assert result["config"] == workspace["config"] and result["panels"] == workspace["panels"]


def _install_builder(monkeypatch, view, func):
    name = f"lib.intl_gs_{view}_view"
    module = types.ModuleType(name)
    module.build_view = func
    monkeypatch.setitem(sys.modules, name, module)
    return name


def test_builder_status_ladder(monkeypatch):
    mount = _load_mount()

    def raises_value_error(**_kwargs):
        raise ValueError("boom")

    def raises_other_module(**_kwargs):
        import importlib
        importlib.import_module("definitely_not_a_real_module_xyz")

    _install_builder(monkeypatch, "scanner", raises_value_error)
    _install_builder(monkeypatch, "dislocations", raises_other_module)
    _install_builder(monkeypatch, "transmission", lambda **_kwargs: [])
    _install_builder(monkeypatch, "dossier", lambda **_kwargs: [
        dict(view="dossier", context_id="im-gs-dossier", context={}, generation=None, payload={"a": 1})])
    result = mount.attach_surveillance(_base_workspace(), universe_loader=lambda: {}, rights_loader=lambda: {})
    views = result["surveillance"]["views"]
    assert views["scanner"] == {"status": "error", "reason": "ValueError"}
    assert views["dislocations"] == {"status": "error", "reason": "ModuleNotFoundError"}
    assert views["transmission"] == {"status": "empty"}
    assert views["dossier"]["status"] == "available"
    assert result["surveillance_panels"] and result["surveillance_panels"][0]["view"] == "dossier"
    assert views["coverage"]["status"] == "not_built"


def test_no_network_or_file_writes(monkeypatch):
    mount = _load_mount()

    class Forbidden(Exception):
        pass

    def no_socket(*_args, **_kwargs):
        raise Forbidden("network")

    real_open = open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wxa+"):
            raise Forbidden("write")
        return real_open(file, mode, *args, **kwargs)

    import socket as socket_module
    monkeypatch.setattr(socket_module, "socket", no_socket)
    monkeypatch.setattr("builtins.open", guarded_open)
    result = mount.attach_surveillance(_base_workspace(), universe_loader=lambda: {}, rights_loader=lambda: {})
    assert result["surveillance"]["views"]["scanner"]["status"] == "not_built"


# ---------------------------------------------------------------- 2.8 build_intl


def _load_build_intl():
    spec = importlib.util.spec_from_file_location("build_intl_under_test", BUILD_INTL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_assets_tuple_appends_surveillance_css_last():
    module = _load_build_intl()
    assert module.ASSETS[-1] == "intl_workspace_surveillance.css"
    assert module.ASSETS.count("intl_workspace_surveillance.css") == 1


def test_attach_surveillance_call_is_isolated_try_except():
    """AST route: _publication_workspace needs the live closes store, config
    grants and publication inputs; calling it without the data store is not
    feasible in a unit test, so the isolation contract is asserted on the AST."""
    tree = ast.parse(BUILD_INTL_PATH.read_text(encoding="utf-8"))
    function = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == "_publication_workspace")
    enclosing = []
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) \
                and getattr(node.value.func, "id", None) == "attach_surveillance":
            for parent in ast.walk(function):
                if isinstance(parent, ast.Try) and node in ast.walk(parent):
                    enclosing.append((parent, node))
    assert enclosing, "workspace = attach_surveillance(workspace) call not found"
    for try_node, call in enclosing:
        reassigned = [n for n in ast.walk(try_node.handlers[0]) if isinstance(n, ast.Assign)]
        assert not reassigned, "handler must not reassign workspace"
        logged = [n for n in ast.walk(try_node.handlers[0]) if isinstance(n, ast.Call)
                  and getattr(n.func, "attr", None) == "error"]
        assert logged, "handler must log"
        message = ast.literal_eval(logged[0].args[0])
        assert message == "International Surveillance panel unavailable (%s)", message


def test_build_intl_imports_attach_surveillance():
    tree = ast.parse(BUILD_INTL_PATH.read_text(encoding="utf-8"))
    names = [node.module for node in ast.walk(tree)
             if isinstance(node, ast.ImportFrom) and node.module]
    assert any(module == "lib.intl_surveillance_mount" for module in names), names


# ---------------------------------------------------------------- 2.9 stylesheet link


def test_intl_page_has_single_surveillance_link_after_history():
    text = _require(INTL_PAGE_PATH)
    assert text.count("intl_workspace_surveillance.css") == 1
    link = '<link rel="stylesheet" href="intl_workspace_surveillance.css">'
    assert link in text
    history = '<link rel="stylesheet" href="intl_workspace_history.css">'
    assert history in text
    assert text.index(history) < text.index(link)
    between = text[text.index(history):text.index(link)]
    assert between.count("<link") == 1, "surveillance link must be immediately after the history link"
    guard_start = text.index("{% if mode != 'stocks' and intl_workspace|default(none) %}")
    assert guard_start < text.index(link)
    guard_end = text.index("{% endif %}", guard_start)
    assert text.index(link) < guard_end, "surveillance link must sit inside the same guard"


# ---------------------------------------------------------------- 2.10 access


def test_site_access_lists_surveillance_css_adjacent():
    text = _require(SITE_ACCESS_PATH)
    assert "/intl_workspace_surveillance.css" in text
    lines = [line.strip().lstrip("- ").strip() for line in text.splitlines()]
    assert lines.index("/intl_workspace_surveillance.css") == lines.index("/intl_workspace_history.css") + 1


def test_caddy_matchers_list_surveillance_css_four_times():
    text = _require(CADDY_PATH)
    assert text.count("/intl_workspace_surveillance.css") == 4
    carrier_lines = [line for line in text.splitlines() if "intl_workspace_entry.js" in line]
    assert len(carrier_lines) == 4, len(carrier_lines)
    for line in carrier_lines:
        assert "/intl_workspace_surveillance.css" in line


# ---------------------------------------------------------------- 2.11 macros


def _macro_render(source, **ctx):
    env = _render_env()
    return env.from_string('{% import "intl_workspace/_gs_macros.html.j2" as gs %}' + source).render(**ctx)


IMPORT_LINE = '{% import "intl_workspace/_gs_macros.html.j2" as gs %}'


def test_gs_value_refuses_numbers_without_all_five_parts():
    full = {"label": "USD move", "unit": "%", "basis": "USD", "clock": "21 Oct 08:00 UTC", "tier": "T1"}
    env = _render_env()
    good = env.from_string(IMPORT_LINE + "{{ gs.gs_value(1.24, parts=parts) }}").render(parts=full)
    assert "1.24" in good and "intl-gs__num" in good
    for missing in full:
        broken = {k: v for k, v in full.items() if k != missing}
        out = env.from_string(IMPORT_LINE + "{{ gs.gs_value(1.24, parts=parts) }}").render(parts=broken)
        assert "1.24" not in out, missing
        assert "missing_%s" % missing in out, missing
        assert "abstain" in out, missing


def test_state_cell_renders_twelve_states_both_languages():
    for state in STATE_ORDER:
        out = _macro_render("{{ gs.gs_state_cell(state=state, market='Brazil', value=1.24, unit='%', basis='USD', clock='21 Oct 08:00 UTC') }}", state=state)
        assert STATE_EN[state] in out, state
        assert STATE_ZH[state] in out, state
        assert 'data-state="%s"' % state in out, state


def test_winning_state_precedence_all_pairs():
    for i, higher in enumerate(STATE_ORDER):
        for lower in STATE_ORDER[i + 1:]:
            winner = _macro_render("{{ gs.gs_winning_state([%r, %r]) }}" % (higher, lower)).strip()
            assert winner == higher, (higher, lower, winner)
            flipped = _macro_render("{{ gs.gs_winning_state([%r, %r]) }}" % (lower, higher)).strip()
            assert flipped == higher, (lower, higher, flipped)
    spec_chain = ("restricted", "loading", "abstain", "stale", "suspended", "closed",
                  "corrected", "qualified", "partial", "complete")
    for i, higher in enumerate(spec_chain):
        for lower in spec_chain[i + 1:]:
            assert _macro_render("{{ gs.gs_winning_state([%r, %r]) }}" % (lower, higher)).strip() == higher


# ---------------------------------------------------------------- 2.12 fixture


def _render_fixture():
    env = _render_env()
    # FX1/FX5: the fixture template consumes the snapshot/horizon context the
    # fixture site composes through the same lib.intl_gs_display path as the
    # mount — never hand-typed literals.
    return env.get_template("intl_workspace/_gs_state_fixture.html.j2").render(
        **_fixture_site()._fixture_snapshot_context())


def test_fixture_renders_thirteen_cells_both_languages():
    html = _render_fixture()
    cells = re.findall(r'data-state="([a-z]+)"', html)
    assert len(cells) == 13, cells
    assert set(cells) == set(STATE_ORDER)
    for state in STATE_ORDER:
        assert STATE_EN[state] in html and STATE_ZH[state] in html, state
    assert 'data-dir="up"' in html and 'data-dir="down"' in html


def test_fixture_restricted_loading_and_specimen_rules():
    html = _render_fixture()
    restricted = html.split('data-state="restricted"', 1)[1].split('data-state="corrected"', 1)[0]
    assert "intl-gs__rights-slot" in restricted
    assert not re.search(r"\d", re.sub(r"<[^>]+>", " ", restricted)), "restricted cell must show no number"
    segment = html.split('data-state="loading"', 1)[1]
    segment = segment.split('data-state="qualified"', 1)[0]
    assert "intl-gs__skel" in segment
    assert "Acquiring" in segment and "获取中" in segment
    assert not re.search(r"\d", re.sub(r"<[^>]+>", " ", segment)), "loading cell must show no digit"


def test_fixture_every_number_lives_in_specimen_scope():
    from html.parser import HTMLParser

    class Scope(HTMLParser):
        """Stack-walking specimen-scope checker (stdlib only, no bs4 gate)."""

        def __init__(self):
            super().__init__()
            self.stack = []
            self.scopes = 0
            self.numbers = 0
            self.bad = 0
            self.chips_in_scope = 0

        def _classes(self, attrs):
            return (dict(attrs).get("class") or "").split()

        def handle_starttag(self, tag, attrs):
            classes = self._classes(attrs)
            is_scope = "intl-gs__specimen-scope" in classes
            self.stack.append(is_scope)
            if is_scope:
                self.scopes += 1
                return
            in_scope = any(self.stack[:-1])
            if "intl-gs__num" in classes:
                if in_scope:
                    self.numbers += 1
                else:
                    self.bad += 1
            if "intl-gs__chip--specimen" in classes and in_scope:
                self.chips_in_scope += 1

        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
            if self.stack:
                self.stack.pop()

        def handle_endtag(self, tag):
            if self.stack:
                self.stack.pop()

    parser = Scope()
    parser.feed(_render_fixture())
    assert parser.scopes >= 1, "fixture must carry a specimen scope"
    assert parser.chips_in_scope >= 1, "specimen chip must live inside the scope"
    assert parser.numbers > 0, "fixture must render specimen numbers"
    assert parser.bad == 0, f"{parser.bad} specimen numbers outside the specimen scope"


def test_fixture_not_referenced_by_production_templates():
    for path in (SHELL_PATH, INTL_PAGE_PATH, REPO / "templates/_navlinks.html.j2"):
        text = path.read_text(encoding="utf-8")
        assert "_gs_state_fixture" not in text, path


# ---------------------------------------------------------------- 2.13 frozen files


def _frozen_base() -> str:
    """merge-base(origin/main, HEAD); FAILS CLOSED when it cannot be resolved.

    CI: the international-workspace-browser job fetches origin/<base> before pytest,
    and its checkout requests fetch-depth: 0 so scripts/run_ci_pack.py deepens the
    tested tree to the merge base. Locally: `git fetch origin main`. This helper
    never touches the network.
    """
    ref = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "origin/main^{commit}"],
                         cwd=REPO, capture_output=True, text=True)
    if ref.returncode != 0:
        pytest.fail("FAIL CLOSED: origin/main does not resolve, so the frozen-file guard has "
                    "no comparison base. CI must run the job's `git fetch origin <base>` step "
                    "before pytest; locally run `git fetch origin main`.")
    base = subprocess.run(["git", "merge-base", "origin/main", "HEAD"],
                          cwd=REPO, capture_output=True, text=True)
    sha = base.stdout.strip()
    if base.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        pytest.fail("FAIL CLOSED: no merge base between origin/main and HEAD (shallow "
                    "checkout?). The job's checkout must request fetch-depth: 0 so the pack "
                    "runner deepens the tested tree; locally deepen or unshallow.")
    return sha


@pytest.mark.parametrize("path", [
    "templates/theme.css",
    "templates/_navlinks.html.j2",
    "engine/intl_global_universe.py",
    "engine/intl_global_observation.py",
    "lib/intl_global_observation_adapter.py",
])
def test_frozen_files_unchanged_vs_origin_main(path):
    base = _frozen_base()
    result = subprocess.run(["git", "diff", "--quiet", base, "--", path],
                            cwd=REPO, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        pytest.fail(f"FAIL CLOSED: git diff {base} -- {path} errored: {result.stderr.strip()}")
    assert result.returncode == 0, f"{path} changed vs merge-base(origin/main, HEAD) {base}"


# ---------------------------------------------------------------- 2.14 JS


def test_state_js_views_appended_in_order():
    text = _require(STATE_JS_PATH)
    match = re.search(r"var VIEWS = \[([^\]]+)\];", text)
    assert match, "VIEWS list not found"
    views = [v.strip().strip("'\"") for v in match.group(1).split(",")]
    assert views == list(ALL_VIEWS), views


def test_workspace_js_panelvalid_allowlist_appended_in_order():
    text = _require(WORKSPACE_JS_PATH)
    lists = re.findall(r"\[('overview'(?:,\s*'[^']+')*)\]\.includes\(", text)
    assert lists, "panelValid allowlist not found"
    for body in lists:
        views = [v.strip().strip("'\"") for v in body.split(",")]
        assert views == list(ALL_VIEWS) or views == list(LEGACY_VIEWS[:-1]), views
    assert any(list(v.strip().strip("'\"") for v in body.split(",")) == list(ALL_VIEWS) for body in lists), \
        "panelValid allowlist must accept the seven surveillance views"


# ================================================================ W2F-X X1..X7

GS_LIB_DIR = REPO / "lib"


def _gs_module(name):
    spec = importlib.util.spec_from_file_location(
        name, GS_LIB_DIR / (name.split(".")[-1] + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _macro_state_keys():
    text = _require(MACROS_PATH)
    block = re.search(r"\{'complete': \('Complete'.*?\}\.get\(state", text, re.DOTALL).group(0)
    return set(re.findall(r"'([a-z_]+)': \(", block))


# ---------------------------------------------------------------- X1 display


def test_x1_names_zh_covers_universe_and_aggregate():
    from engine.intl_global_universe import load_universe
    display = _gs_module("lib.intl_gs_display")
    universe = load_universe()
    expected = set(universe["jurisdictions"]) | set(universe.get("aggregates") or {})
    assert set(display.NAMES_ZH) == expected, sorted(set(display.NAMES_ZH) ^ expected)
    values = list(display.NAMES_ZH.values())
    assert len(set(values)) == len(values), "duplicate ZH name"
    for key, name in display.NAMES_ZH.items():
        assert re.search(r"[一-鿿]", name), key
    assert display.NAMES_ZH["BR"] == "巴西"
    assert display.NAMES_ZH["EZ"] == "欧元区"
    assert display.NAMES_ZH["TW"] == "台湾"
    assert display.NAMES_ZH["IR"] == "伊朗" and display.NAMES_ZH["VE"] == "委内瑞拉"


def test_x1_region_groups_partition_the_63_jurisdictions():
    from engine.intl_global_universe import load_universe
    display = _gs_module("lib.intl_gs_display")
    universe = load_universe()
    seen = {}
    for group_key, regions, _en, _zh in display.REGION_GROUPS:
        assert len(regions) >= 1
        for region in regions:
            assert region not in seen, f"region {region} in two groups"
            seen[region] = group_key
    total = 0
    for jid, jur in universe["jurisdictions"].items():
        assert jur["region"] in seen, f"{jid} region {jur['region']} in no group"
        total += 1
    assert total == 63
    assert [g[0] for g in display.REGION_GROUPS] == ["asia", "emea", "americas"]
    assert display.REGION_GROUPS[0][2:] == ("Asia", "亚太")
    assert display.REGION_GROUPS[1][2:] == ("EMEA", "欧洲、中东及非洲")
    assert display.REGION_GROUPS[2][2:] == ("Americas", "美洲")


def test_x1_capability_labels_keys_exactly_capabilities():
    from engine.intl_global_universe import CAPABILITIES
    display = _gs_module("lib.intl_gs_display")
    assert set(display.CAPABILITY_LABELS) == set(CAPABILITIES)
    for pair in display.CAPABILITY_LABELS.values():
        assert len(pair) == 2 and pair[0] and re.search(r"[一-鿿]", pair[1])
    assert display.CAPABILITY_LABELS["equity_index_fx"] == ("Equity index + FX", "股指与汇率")
    assert display.CAPABILITY_LABELS["history_pit_rights"] == ("History + point-in-time rights", "历史与时点权利")


def test_x1_capability_display_maps_states_to_macro_keys():
    from engine.intl_global_universe import CAPABILITY_STATES
    display = _gs_module("lib.intl_gs_display")
    assert set(display.CAPABILITY_DISPLAY) == set(CAPABILITY_STATES)
    assert set(display.CAPABILITY_DISPLAY.values()) <= _macro_state_keys()
    assert display.CAPABILITY_DISPLAY["qualified"] == "complete"
    assert display.CAPABILITY_DISPLAY["delayed"] == "qualified"
    assert display.CAPABILITY_DISPLAY["retained_stale"] == "stale"
    assert display.CAPABILITY_DISPLAY["market_closed"] == "closed"
    assert display.CAPABILITY_DISPLAY["unavailable"] == "empty"
    assert display.CAPABILITY_DISPLAY["denied"] == "restricted"
    assert display.CAPABILITY_DISPLAY["not_applicable"] == "empty"


def test_x1_reason_copy_covers_abstain_and_capability_tokens():
    from engine.intl_global_observation import ABSTAIN_REASONS
    from engine.intl_global_universe import load_universe
    display = _gs_module("lib.intl_gs_display")
    universe = load_universe()
    tokens = set()
    for doc in (universe["jurisdictions"].values(), (universe.get("aggregates") or {}).values()):
        for entry_container in doc:
            for entry in entry_container["capabilities"].values():
                if entry.get("reason"):
                    tokens.add(entry["reason"])
    assert tokens, "the universe must carry capability reason tokens"
    missing = (set(ABSTAIN_REASONS) | tokens) - set(display.REASON_COPY)
    assert not missing, sorted(missing)
    for key, pair in display.REASON_COPY.items():
        assert len(pair) == 2 and pair[0], key


def test_x1_coverage_fields_binding():
    from engine.intl_global_universe import CAPABILITIES
    display = _gs_module("lib.intl_gs_display")
    fields = display.COVERAGE_FIELDS
    assert [f[0] for f in fields] == ["index_close", "fx_fix", "y10", "cds5y", "usd_funding", "us_proxy"]
    assert [f[1] for f in fields] == ["INDEX CLOSE", "FX FIX", "10Y YIELD", "CDS 5Y", "USD FUNDING", "US PROXY"]
    assert [f[2] for f in fields] == ["指数收盘", "汇率定盘", "10年期收益率", "5年期CDS", "美元融资", "美国代理"]
    for field in fields:
        assert field[3] in CAPABILITIES, field


def test_x1_jurisdiction_rows_shape():
    from engine.intl_global_universe import load_universe
    display = _gs_module("lib.intl_gs_display")
    universe = load_universe()
    rows = display.jurisdiction_rows(universe)
    assert len(rows) == 64
    assert [r["id"] for r in rows[:63]] == list(universe["jurisdictions"])
    assert rows[-1]["id"] == "EZ" and rows[-1]["kind"] == "aggregate"
    assert all(r["kind"] == "jurisdiction" for r in rows[:63])
    japan = rows[[r["id"] for r in rows].index("JP")]
    assert japan["name_en"] == "Japan" and japan["name_zh"] == "日本"
    assert japan["region"] == "asia_pacific" and japan["region_group"] == "asia"
    assert japan["cohort"] == "msci_dm" and japan["currency"] == "JPY"
    assert japan["timezone"] == "Asia/Tokyo"
    verbatim = {key: entry["state"] for key, entry in
                universe["jurisdictions"]["JP"]["capabilities"].items()}
    verbatim_reasons = {key: entry["reason"] for key, entry in
                        universe["jurisdictions"]["JP"]["capabilities"].items()}
    assert {key: entry["state"] for key, entry in japan["capabilities"].items()} == verbatim
    assert {key: entry["reason"] for key, entry in japan["capabilities"].items()} == verbatim_reasons
    for row in rows[:63]:
        entry = row["capabilities"]["equity_index_fx"]
        assert {"state", "display", "reason"} <= set(entry)
    assert rows[-1]["region_group"] is None
    group_sizes = {}
    for row in rows[:63]:
        group_sizes[row["region_group"]] = group_sizes.get(row["region_group"], 0) + 1
    assert group_sizes == {"asia": 18, "emea": 36, "americas": 9}, group_sizes
    assert sum(group_sizes.values()) == 63


# ---------------------------------------------------------------- X1 addendum


def test_x1_rights_class_labels_match_matrix():
    from engine.intl_global_universe import load_rights_matrix
    display = _gs_module("lib.intl_gs_display")
    classes = {row["rights_class"] for row in load_rights_matrix()["rows"]}
    assert set(display.RIGHTS_CLASS_LABELS) == classes, sorted(classes)
    for pair in display.RIGHTS_CLASS_LABELS.values():
        assert pair[0] and re.search(r"[一-鿿]", pair[1])


def test_x1_rights_view_projection():
    from engine.intl_global_universe import (
        ROW_LEGACY_SERIES, load_rights_matrix, load_universe)
    display = _gs_module("lib.intl_gs_display")
    universe, matrix = load_universe(), load_rights_matrix()
    row = display.rights_view(universe, matrix, "JP", "equity_index_fx")
    assert row["rights_ref"] == ROW_LEGACY_SERIES
    assert row["rights_class"] == "direct_display_ok"
    source = next(r for r in matrix["rows"] if r["id"] == ROW_LEGACY_SERIES)
    assert row["delay"] == source.get("delay")
    assert row["decision_ref"] == source.get("decision_ref")
    assert row["review_status"] == (source.get("review") or {}).get("status")
    assert row["label_en"] == "Display permitted" and row["label_zh"] == "允许展示"
    assert display.rights_view(universe, matrix, "BR", "equity_index_fx") is None
    assert display.rights_view(universe, matrix, "EZ", "equity_index_fx") is not None


def test_x1_rights_view_missing_row_never_guesses():
    from engine.intl_global_universe import load_rights_matrix, load_universe
    display = _gs_module("lib.intl_gs_display")
    japan = dict(load_universe()["jurisdictions"]["JP"])
    japan["capabilities"] = {
        **japan["capabilities"],
        "equity_index_fx": {"state": "delayed", "reason": "x", "evidence_ref": "e",
                            "rights_ref": "no.such.row"}}
    broken = {"jurisdictions": {"JP": japan}, "aggregates": {}}
    row = display.rights_view(broken, load_rights_matrix(), "JP", "equity_index_fx")
    assert row["rights_ref"] == "no.such.row"
    assert row["rights_class"] is None
    assert row["label_en"] == "Rights row missing"
    assert row["label_zh"] == "权利记录缺失"
    assert row["delay"] is None and row["decision_ref"] is None and row["review_status"] is None


def test_x1_evidence_tier_source_is_none_and_view_tokens():
    from engine.intl_global_observation import ABSTAIN_REASONS
    from engine.intl_global_universe import load_universe
    display = _gs_module("lib.intl_gs_display")
    assert display.EVIDENCE_TIER_SOURCE is None
    tokens = display.VIEW_ABSTAIN_TOKENS
    assert isinstance(tokens, tuple)
    expected = ("common_factor_unadmitted", "divergence_unadmitted", "series_unadmitted",
                "stance_unadmitted", "attention_unadmitted", "credit_funding_unadmitted",
                "transmission_unadmitted", "us_corroboration_unadmitted", "thesis_unadmitted",
                "session_calendar_unadmitted", "corrections_none")
    assert tokens == expected
    assert set(tokens) <= set(display.REASON_COPY)
    for token in tokens:
        en, zh = display.REASON_COPY[token]
        assert en, token
        assert re.search(r"[一-鿿]", zh), token
    assert not (set(tokens) & set(ABSTAIN_REASONS))
    data_tokens = set()
    universe = load_universe()
    for doc in (universe["jurisdictions"].values(), (universe.get("aggregates") or {}).values()):
        for entry_container in doc:
            for entry in entry_container["capabilities"].values():
                if entry.get("reason"):
                    data_tokens.add(entry["reason"])
    assert not (set(tokens) & data_tokens)
    assert display.REASON_COPY["evidence_tier_undefined"] == (
        "Evidence tier not yet defined", "证据层级尚未定义")


# ---------------------------------------------------------------- X2 observations

W2FX_EVALUATED = "2026-10-09T20:30:00+00:00"
W2FX_GRANT = {
    "status": "confirmed",
    "scope": "intl-index-fx-eod-user-facing-v1",
    "decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
}


def _w2fx_setup(tmp_path):
    import pandas as pd
    from engine import intl_inputs
    dates = pd.bdate_range(end="2026-10-07", periods=280)
    series = []
    for cc, market in intl_inputs.countries().items():
        for symbol in (market["index"], market["fx"]):
            if symbol not in series:
                series.append(symbol)
    cols = {}
    for slot, symbol in enumerate(series):
        value = [float(100 + slot * 4 + 0.125 * i) for i in range(len(dates))]
        cols[symbol] = pd.Series(value, index=dates)
        path = tmp_path / "intl" / (
            symbol.replace("^", "_").replace("=", "_").replace("/", "_") + ".parquet")
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"close": value}, index=dates).to_parquet(path)
    return pd.DataFrame(cols).sort_index(), series


def _w2fx_status(tmp_path):
    import json as _json
    (tmp_path / "run_status.json").write_text(_json.dumps({"sources": {"intl_prices": {
        "source": "intl_prices", "status": "ok", "checked_at": "2026-10-09T15:00:00+00:00",
        "last_date": "2026-10-07"}}}), encoding="utf-8")


def _w2fx_admitted(tmp_path):
    from lib.intl_eod_publication import build_eod_inputs
    frame, _series = _w2fx_setup(tmp_path)
    _w2fx_status(tmp_path)
    return build_eod_inputs(frame, data_root=tmp_path, evaluated_at=W2FX_EVALUATED,
                            rights=W2FX_GRANT)


def test_x2_admitted_chain_matches_the_direct_adapter_output(tmp_path):
    import json
    from engine import intl_inputs
    from engine.intl_performance_records import build_return_records
    from lib.intl_global_observation_adapter import observations_from_qualification
    observations_module = _gs_module("lib.intl_gs_observations")
    selected, inputs = _w2fx_admitted(tmp_path)
    assert selected is not None
    result = observations_module.build_observation_set(
        selected, publication_inputs=inputs, evaluated_at=W2FX_EVALUATED,
        data_root=tmp_path, rights=W2FX_GRANT)
    assert result["status"] == "admitted"
    assert result["contract_version"] == "intl-global-observation-v1"
    assert result["source_reference"].startswith("intl-supplied-close:sha256:")
    pending = intl_inputs.source_snapshot(
        selected, source_reference="intl-supplied-close:pending",
        adjustment_bases=inputs["adjustment_bases"])
    reference = "intl-supplied-close:sha256:" + pending["content_sha256"]
    snapshot = intl_inputs.source_snapshot(
        selected, source_reference=reference, adjustment_bases=inputs["adjustment_bases"])
    records = build_return_records(selected, market_ids=list(intl_inputs.countries()),
                                   source_reference=reference)
    for basis in ("local", "usd_unhedged"):
        qualification = intl_inputs.qualify_return_records(
            records, snapshot=snapshot, source_evidence=inputs["source_evidence"],
            disclosure_decisions=inputs["disclosure_decisions"],
            policy_id=inputs["policy_id"], currency_basis=basis)
        direct = observations_from_qualification(
            records, qualification, closes=selected,
            source_evidence=inputs["source_evidence"],
            run_status_source={"checked_at": "2026-10-09T15:00:00+00:00"},
            evaluated_at=W2FX_EVALUATED, rights=W2FX_GRANT, currency_basis=basis)
        assert json.dumps(result["bases"][basis], sort_keys=True) == json.dumps(direct, sort_keys=True)
        for observation, record in zip(result["bases"][basis], records["records"]):
            if observation["state"] == "qualified":
                leg = "local" if basis == "local" else "usd"
                assert observation["value"]["pct"] == record[leg]["value"]


def test_x2_hedged_abstains_basis_unsupported(tmp_path):
    observations_module = _gs_module("lib.intl_gs_observations")
    selected, inputs = _w2fx_admitted(tmp_path)
    result = observations_module.build_observation_set(
        selected, publication_inputs=inputs, evaluated_at=W2FX_EVALUATED,
        data_root=tmp_path, rights=W2FX_GRANT)
    assert result["bases"]["usd_hedged"]
    for observation in result["bases"]["usd_hedged"]:
        assert observation["state"] == "abstain"
        assert "basis_unsupported" in observation["abstain_reasons"]
        assert observation["value"] is None


def test_x2_publication_inputs_none_withholds_everything(tmp_path):
    observations_module = _gs_module("lib.intl_gs_observations")
    frame, _series = _w2fx_setup(tmp_path)
    _w2fx_status(tmp_path)
    result = observations_module.build_observation_set(
        frame, publication_inputs=None, evaluated_at=W2FX_EVALUATED,
        data_root=tmp_path, rights=W2FX_GRANT)
    assert result["status"] == "withheld"
    assert result["source_reference"] is None
    for basis in ("local", "usd_unhedged", "usd_hedged"):
        assert result["bases"][basis]
        assert all(obs["state"] == "abstain" for obs in result["bases"][basis])
        assert all(obs["abstain_reasons"] for obs in result["bases"][basis])


def test_x2_run_status_absent_abstains_clock_missing(tmp_path):
    observations_module = _gs_module("lib.intl_gs_observations")
    selected, inputs = _w2fx_admitted(tmp_path)
    (tmp_path / "run_status.json").unlink()
    result = observations_module.build_observation_set(
        selected, publication_inputs=inputs, evaluated_at=W2FX_EVALUATED,
        data_root=tmp_path, rights=W2FX_GRANT)
    for basis in ("local", "usd_unhedged"):
        assert result["bases"][basis]
        for observation in result["bases"][basis]:
            assert "clock_missing" in observation["abstain_reasons"]


def test_x2_each_basis_list_is_single_basis(tmp_path):
    from engine.intl_global_observation import assert_single_basis
    observations_module = _gs_module("lib.intl_gs_observations")
    selected, inputs = _w2fx_admitted(tmp_path)
    result = observations_module.build_observation_set(
        selected, publication_inputs=inputs, evaluated_at=W2FX_EVALUATED,
        data_root=tmp_path, rights=W2FX_GRANT)
    for basis in ("local", "usd_unhedged", "usd_hedged"):
        assert_single_basis(result["bases"][basis])


def test_x2_hedged_call_receives_the_usd_unhedged_qualification(tmp_path):
    """The adapter contract: the usd_hedged basis is fed the usd_unhedged
    qualification (never the local one), so no hedged observation can borrow
    an unhedged incumbent receipt."""
    import json as _json
    from lib.intl_global_observation_adapter import observations_from_qualification
    observations_module = _gs_module("lib.intl_gs_observations")
    selected, inputs = _w2fx_admitted(tmp_path)
    seen = {}
    real = observations_from_qualification

    def spy(records, qualification, **kwargs):
        basis = kwargs.get("currency_basis")
        if basis in ("local", "usd_unhedged", "usd_hedged"):
            seen[basis] = _json.dumps(qualification, sort_keys=True, default=str)
        return real(records, qualification, **kwargs)

    observations_module.observations_from_qualification = spy
    try:
        observations_module.build_observation_set(
            selected, publication_inputs=inputs, evaluated_at=W2FX_EVALUATED,
            data_root=tmp_path, rights=W2FX_GRANT)
    finally:
        observations_module.observations_from_qualification = real
    assert set(seen) == {"local", "usd_unhedged", "usd_hedged"}
    assert seen["local"] != seen["usd_unhedged"], \
        "the two supported bases must carry different qualifications"
    assert seen["usd_hedged"] == seen["usd_unhedged"], \
        "the hedged basis must be fed the usd_unhedged qualification"


# ---------------------------------------------------------------- X3 mount seam


def _sample_observations():
    return {
        "contract_version": "intl-global-observation-v1",
        "status": "admitted",
        "source_reference": "intl-supplied-close:sha256:abc",
        "bases": {
            "local": [{"state": "qualified", "abstain_reasons": [], "clocks": {
                "observation": {"at": "2026-10-07", "precision": "session_date"},
                "source_publication": {"at": "2026-10-09T15:00:00+00:00", "precision": "upper_bound"},
                "ingestion": {"at": "2026-10-09T15:00:00+00:00", "precision": "exact"},
                "computation": {"at": "2026-10-09T20:30:00+00:00", "precision": "exact"}}}],
            "usd_unhedged": [],
            "usd_hedged": [],
        },
    }


def test_x3_observations_reach_builders_as_deep_copies(monkeypatch):
    from copy import deepcopy
    mount = _load_mount()
    captured = {}

    def build_view(*, universe, rights, contexts, workspace, observations=None):
        captured["observations"] = deepcopy(observations)
        if observations is not None:
            observations["bases"]["probe"] = ["mutation"]
        return []

    _install_builder(monkeypatch, "scanner", build_view)
    payload = _sample_observations()
    before = _sample_observations()
    result = mount.attach_surveillance(_base_workspace(), universe_loader=lambda: {},
                                       rights_loader=lambda: {}, observations=payload)
    assert captured["observations"] == before, "builder must receive the payload unchanged"
    assert captured["observations"] is not payload, "builder must receive a deep copy"
    assert payload == before, "caller dict must not be mutated"
    block = result["surveillance"]["observations"]
    assert block["status"] == "admitted"
    assert block["source_reference"] == "intl-supplied-close:sha256:abc"
    assert set(block["counts"]) == {"local", "usd_unhedged", "usd_hedged"}


def test_x3_none_observations_reach_builders_as_none(monkeypatch):
    mount = _load_mount()
    captured = {}

    def build_view(*, universe, rights, contexts, workspace, observations=None):
        captured["observations"] = observations
        return []

    _install_builder(monkeypatch, "scanner", build_view)
    result = mount.attach_surveillance(_base_workspace(), universe_loader=lambda: {},
                                       rights_loader=lambda: {})
    assert captured["observations"] is None
    block = result["surveillance"]["observations"]
    assert block["counts"]["local"] == {"total": 0, "qualified": 0, "abstain": 0}


def _count_numbers(node):
    numbers = []
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        numbers.append(node)
    elif isinstance(node, dict):
        for value in node.values():
            numbers.extend(_count_numbers(value))
    elif isinstance(node, (list, tuple)):
        for value in node:
            numbers.extend(_count_numbers(value))
    return numbers


def test_x3_counts_block_holds_no_other_numbers(monkeypatch):
    mount = _load_mount()
    _install_builder(monkeypatch, "scanner", lambda **_kwargs: [])
    result = mount.attach_surveillance(_base_workspace(), universe_loader=lambda: {},
                                       rights_loader=lambda: {}, observations=_sample_observations())
    outside = dict(result["surveillance"]["observations"])
    counts = outside.pop("counts")
    assert not _count_numbers(outside), "numbers outside counts"
    for basis, entry in counts.items():
        assert set(entry) == {"total", "qualified", "abstain"}, (basis, entry)


def test_x3_snapshot_block_latest_qualified_clocks(monkeypatch):
    from engine.intl_global_observation import REQUIRED_CLOCKS
    mount = _load_mount()
    _install_builder(monkeypatch, "scanner", lambda **_kwargs: [])
    payload = _sample_observations()
    payload["bases"]["local"].append({"state": "abstain", "abstain_reasons": ["clock_missing"], "clocks": {
        "observation": {"at": "2026-10-09", "precision": "session_date"},
        "source_publication": {"at": "2026-10-10T15:00:00+00:00", "precision": "upper_bound"},
        "ingestion": {"at": "2026-10-10T15:00:00+00:00", "precision": "exact"},
        "computation": {"at": "2026-10-10T20:30:00+00:00", "precision": "exact"}}})
    result = mount.attach_surveillance(_base_workspace(), universe_loader=lambda: {},
                                       rights_loader=lambda: {}, observations=payload)
    snapshot = result["surveillance"]["snapshot"]
    assert set(snapshot) == {"local", "usd_unhedged", "usd_hedged"}
    for basis in snapshot:
        assert set(snapshot[basis]) == {"clocks", "clock_display", "qualified", "total"}
        assert set(snapshot[basis]["clocks"]) == set(REQUIRED_CLOCKS)
        assert set(snapshot[basis]["clock_display"]) == set(REQUIRED_CLOCKS)
    assert snapshot["local"]["qualified"] == 1 and snapshot["local"]["total"] == 2
    assert snapshot["local"]["clocks"]["computation"] == "2026-10-09T20:30:00+00:00"
    assert snapshot["local"]["clocks"]["source_publication"] == "2026-10-09T15:00:00+00:00"
    assert snapshot["usd_hedged"]["qualified"] == 0
    assert all(value is None for value in snapshot["usd_hedged"]["clocks"].values())


# ---------------------------------------------------------------- X4 build wiring


def test_x4_observation_call_is_own_try_except():
    tree = ast.parse(BUILD_INTL_PATH.read_text(encoding="utf-8"))
    function = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == "_publication_workspace")
    assigns = [node for node in ast.walk(function)
               if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
               and getattr(node.value.func, "id", None) == "build_observation_set"]
    assert assigns, "observation_set = build_observation_set(...) not found"
    for assign in assigns:
        guards = [parent for parent in ast.walk(function)
                  if isinstance(parent, ast.Try) and assign in ast.walk(parent)]
        assert guards, "build_observation_set call is not inside a try"
        handler = guards[0].handlers[0]
        reset = [n for n in ast.walk(handler) if isinstance(n, ast.Assign)
                 and any(getattr(t, "id", None) == "observation_set" for t in n.targets)]
        assert reset, "handler must reset observation_set"
        logged = [n for n in ast.walk(handler) if isinstance(n, ast.Call)
                  and getattr(n.func, "attr", None) == "error"]
        assert logged, "handler must log"
        assert ast.literal_eval(logged[0].args[0]) == \
            "International Surveillance observations unavailable (%s)"


def test_x4_same_rights_object_reaches_both_calls_and_none_propagates(tmp_path):
    module = _load_build_intl()
    seen = {}
    captured = {}

    def fake_build_eod_inputs(closes, *, data_root, evaluated_at, rights):
        seen["eod_rights"] = rights
        return None

    def fake_build_observation_set(closes, *, publication_inputs, evaluated_at, data_root, rights):
        seen["observation_rights"] = rights
        seen["publication_inputs"] = publication_inputs
        raise RuntimeError("boom")

    def fake_attach(workspace, **kwargs):
        captured.update(kwargs)
        return workspace

    import lib.intl_eod_publication as eod_module
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(eod_module, "build_eod_inputs", fake_build_eod_inputs)
    monkeypatch.setattr(module, "build_observation_set", fake_build_observation_set)
    monkeypatch.setattr(module, "attach_surveillance", fake_attach)
    try:
        workspace = module._publication_workspace(
            None, data_root=tmp_path, evaluated_at="2026-10-09T20:30:00+00:00")
    finally:
        monkeypatch.undo()
    assert workspace is not None, "a raising observation build must not kill the page"
    assert captured.get("observations") is None, "attach must receive None on failure"
    assert seen.get("publication_inputs") is None
    assert "eod_rights" in seen and "observation_rights" in seen
    assert seen["eod_rights"] is seen["observation_rights"], "rights must be one shared object"


# ---------------------------------------------------------------- X5 chrome macros


def test_x5_gs_page_header_renders_specimen_and_plain():
    plain = _macro_render("{{ gs.gs_page_header('eyebrow', 'title', 'lede') }}")
    assert "intl-gs__pagehead" in plain and "title" in plain and "lede" in plain
    assert "intl-gs__chip--specimen" not in plain
    specimen = _macro_render("{{ gs.gs_page_header('eyebrow', 'title', 'lede', specimen=true) }}")
    assert "intl-gs__chip--specimen" in specimen
    assert "Specimen values · not live" in specimen and "示例数值 · 非实时" in specimen


def test_x5_gs_questions_strip_six_bilingual_questions():
    out = _macro_render("{{ gs.gs_questions() }}")
    for n in range(1, 7):
        assert 'class="intl-gs__qcard__n intl-gs__num">%d</span>' % n in out, n
    for en, zh in (("What changed globally?", "全球发生了什么变化？"),
                   ("Local, FX, common or divergent?", "本地、汇率、共同还是背离？"),
                   ("Credit, funding, liquidity?", "信用、融资、流动性？"),
                   ("Transmission into the US?", "如何传导至美国？"),
                   ("Eligible US corroboration?", "合格的美国佐证？"),
                   ("What resolves the thesis?", "什么能验证或推翻论点？")):
        assert en in out and zh in out, en
    active = _macro_render("{{ gs.gs_questions(active=3) }}")
    assert active.count("is-active") == 1


def test_x5_gs_snapshot_populated_and_all_none():
    horizon = {"id": "1m", "en": "1M", "zh": "1月"}
    populated = {"local": {"clocks": {
        "observation": "2026-10-07", "source_publication": "2026-10-09T15:00:00+00:00",
        "ingestion": "2026-10-09T15:00:00+00:00", "computation": "2026-10-09T20:30:00+00:00"},
        "qualified": 35, "total": 35,
        "clock_display": {}}}
    empty = {"local": {"clocks": {name: None for name in (
        "observation", "source_publication", "ingestion", "computation")},
        "qualified": 0, "total": 0, "clock_display": {}}}
    module = _display_module()
    populated = module.snapshot_display(populated)
    empty = module.snapshot_display(empty)
    out = _macro_render("{{ gs.gs_snapshot(snapshot, 'local', horizon) }}",
                        snapshot=populated, horizon=horizon)
    assert "2026-10-09T20:30:00+00:00" in out and "2026-10-07" in out
    assert "9 Oct 20:30 UTC" in out and "10月9日 20:30 UTC" in out
    assert "1M" in out and "1月" in out
    assert "No qualified observation" not in out
    blank = _macro_render("{{ gs.gs_snapshot(snapshot, 'local', horizon) }}",
                          snapshot=empty, horizon=horizon)
    assert blank.count("No qualified observation") >= 1 and "无合格观测" in blank
    hedged = _macro_render("{{ gs.gs_snapshot(snapshot, 'usd_hedged', horizon) }}",
                           snapshot=empty, horizon=horizon)
    assert "Hedged basis not supported" in hedged and "不支持对冲口径" in hedged
    assert "Local" in out and "本币" in out
    assert "USD · Hedged" in hedged and "美元 · 已对冲" in hedged


def test_x5_fixture_carries_both_snapshot_variants():
    html = _render_fixture()
    assert html.count('class="intl-gs__snapshot"') >= 2
    assert "No qualified observation" in html and "无合格观测" in html


# ---------------------------------------------------------------- X7 anchors


def test_x7_css_and_yaml_merge_anchors():
    css = _css()
    assert css.rstrip().endswith("/* ==== end W2B region ==== */"), \
        "CSS must end with the W2B end anchor"
    w2a = css.index("/* ==== W2A region")
    w2a_end = css.index("/* ==== end W2A region ==== */")
    spacer1 = css.index("/* spacer 1: keep unchanged; separates the two lane regions */")
    w2b = css.index("/* ==== W2B region")
    w2b_end = css.index("/* ==== end W2B region ==== */")
    assert w2a < w2a_end < spacer1 < w2b < w2b_end
    between = css[w2a_end + len("/* ==== end W2A region ==== */"):w2b].strip().splitlines()
    assert len(between) >= 3 and all("spacer" in line for line in between), \
        "at least two unchanged spacer lines must separate the regions"
    yaml_text = _require(REPO / ".github/ci/legacy-jobs.yml")
    start = yaml_text.index("  international-workspace-browser:")
    nxt = re.search(r"\n  [a-zA-Z][a-zA-Z0-9_-]*:", yaml_text[start + 10:])
    job = yaml_text[start:start + 10 + (nxt.start() if nxt else len(yaml_text))]
    paths_anchor = job.index("# W2A (IM13) paths: insert below this line")
    steps_anchor = job.index("# W2A (IM13) test steps: insert below this line")
    assert job.index("# W2B (IM14) paths: insert below this line") > \
        job.index("# spacer: keep unchanged", paths_anchor) > paths_anchor
    assert job.index("# W2B (IM14) test steps: insert below this line") > \
        job.index("# spacer: keep unchanged", steps_anchor) > steps_anchor


# ---------------------------------------------------------------- visual fixes


def test_vf2_state_cell_anatomy_three_rows():
    from html.parser import HTMLParser
    out = _macro_render(
        "{{ gs.gs_state_cell('complete', 'Brazil', 1.24, '%', 'USD · Unhedged', '21 Oct 08:00 UTC', dir='up') }}")

    class Rows(HTMLParser):
        def __init__(self):
            super().__init__()
            self.depth = 0
            self.rows = 0
            self.started = False

        def handle_starttag(self, tag, attrs):
            classes = (dict(attrs).get("class") or "").split()
            if not self.started and "intl-gs__statecell" in classes and tag == "div":
                self.started = True
                self.depth = 0
            elif self.started and self.depth == 1 and tag == "div":
                self.rows += 1
            self.depth += 1

        def handle_endtag(self, tag):
            self.depth -= 1

    parser = Rows()
    parser.feed(out)
    assert parser.rows == 3, f"state cell must render exactly three rows, saw {parser.rows}"
    assert "intl-gs__statecell__mainrow" in out
    assert "intl-gs__statecell__basis" in out.split("intl-gs__statecell__mainrow")[1].split("</div>")[0], \
        "basis must sit inline on the value row"


def test_vf3_partial_and_stale_chip_copy():
    html = _render_fixture()
    assert "3 of 5" in html and "5个中3个" in html
    assert "3/5" not in html
    assert " · 2d" in html and " · 2天" in html


def test_vf4_no_english_state_word_outside_bilingual_twin():
    from html.parser import HTMLParser

    class Leaks(HTMLParser):
        WORDS = ("Qualified", "Abstain", "Partial", "Stale", "Closed", "Suspended",
                 "Restricted", "Corrected", "Restored", "Proxy", "Loading", "No data",
                 "Complete")

        def __init__(self):
            super().__init__()
            self.stack = []
            self.leaks = []

        def handle_starttag(self, tag, attrs):
            classes = (dict(attrs).get("class") or "").split()
            self.stack.append("l-en" in classes)

        def handle_endtag(self, tag):
            if self.stack:
                self.stack.pop()

        def handle_data(self, data):
            if any(self.stack):
                return
            for word in self.WORDS:
                if word in data:
                    self.leaks.append((word, data.strip()[:40]))

    parser = Leaks()
    parser.feed(_render_fixture())
    assert not parser.leaks, f"unwrapped English state words: {parser.leaks}"


def test_vf5_muted_states_never_carry_direction_ink():
    for state in ("stale", "closed", "suspended"):
        out = _macro_render(
            "{{ gs.gs_state_cell(state, 'Market', 0.55, '%', 'basis', 'clock', dir='up') }}",
            state=state)
        assert "intl-gs__num--up" not in out, state
        assert "intl-gs__num--down" not in out, state
        assert "intl-gs__num--muted" in out, state


def test_vf6_corrected_cell_shows_same_metric_old_and_new():
    html = _render_fixture()
    corrected = html.split('data-state="corrected"', 1)[1].split('data-state="recovered"', 1)[0]
    assert "+2.90%" in corrected and "+2.60%" in corrected, \
        "old and new must be the same metric at the same precision"
    assert "5.712" not in corrected
    assert 'intl-gs__old' in corrected


def test_vf8_legend_and_figure_sizes_use_tokens():
    css = _css()
    edge_rule = css.split(".intl-gs__edgelabel", 1)[1].split("}", 1)[0] if ".intl-gs__edgelabel" in css else ""
    assert "var(--fs-label)" in edge_rule and "var(--muted)" in edge_rule
    assert ".intl-gs__num--fig" in css
    html = _render_fixture()
    assert "intl-gs__edgelabel" in html and "intl-gs__num--fig" in html


def test_vf10_kpi_counts_are_unsigned_integers():
    html = _render_fixture()
    kpi_block = html.split("intl-gs__kpirow", 1)[1]
    assert "+31.00" not in kpi_block and "+3.00" not in kpi_block
    assert ">31<" in kpi_block
    assert "intl-gs__num--up" in kpi_block and "intl-gs__num--down" in kpi_block


def test_vf13_vf14_fixture_reserves_copilot_and_header_space():
    css = _css()
    assert ".intl-gs--fixture" in css
    fixture_rule = css.split(".intl-gs--fixture", 1)[1].split("}", 1)[0]
    assert "padding-bottom" in fixture_rule
    states = _fixture_site().render_states_page()
    assert "intl-gs--fixture" in states
    assert "intl-gs__specimen-head" in states


def test_vf15_h2_bar_neutralised_inside_scope():
    css = _strip_comments(_css())
    assert re.search(r"\.intl-gs h2::before\{content:none\}", css) or \
        re.search(r"\.intl-gs h2::before\s*\{[^}]*content:\s*none", css), \
        "the page-wide h2::before gradient bar must be neutralised inside .intl-gs"


def test_vf16_fixture_site_serves_fonts_and_live_config(tmp_path):
    module = _fixture_site()
    out = tmp_path / "site"
    module.write_site(out)
    for name in ("Inter-400.woff2", "Inter-600.woff2", "Inter-700.woff2"):
        assert (out / "fonts" / name).is_file(), name
    assert (out / "live_config.js").is_file()


def test_vf18_loading_skeleton_unchanged():
    css = _css()
    assert ".intl-gs__skel{display:block;height:10px;" in css
    assert ".intl-gs__skel--sm{height:8px;" in css
    assert "prefers-reduced-motion" in css


def test_vf9_selected_row_ring_declared_inside_the_clip():
    css = _strip_comments(_css())
    rule = re.search(r"\.intl-gs__table tbody tr\.is-selected\{([^}]*)\}", css)
    assert rule, "selected row ring rule missing"
    body = rule.group(1)
    assert "outline:1.5px solid var(--info)" in body
    assert "outline-offset:-1.5px" in body


def test_vf7_glyph_clocks_are_micro_muted():
    css = _css()
    assert ".intl-gs__glyphwrap .intl-gs__num{font-size:var(--fs-micro);color:var(--muted);}" in css
    html = _render_fixture()
    assert "intl-gs__glyphwrap" in html


# ------------------------------------------------------------ FX fix round
# (orchestrator visual review FX1–FX7 + independent-review findings F2/F3/F7;
# written RED before any implementation — see LANE_RECORD_INTL-GS-W2F-FX.md)

from html.parser import HTMLParser  # noqa: E402  (FX scans parse rendered pages)

RAW_ISO_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def _display_module():
    spec = importlib.util.spec_from_file_location(
        "intl_gs_display", REPO / "lib/intl_gs_display.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _PageScan(HTMLParser):
    """Collects visible text nodes and every attribute pair of a page."""

    def __init__(self):
        super().__init__()
        self.text = []
        self.attrs = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value is not None:
                self.attrs.append((name, value))

    def handle_data(self, data):
        self.text.append(data)


def _scan(html):
    parser = _PageScan()
    parser.feed(html)
    return parser


# ---------------------------------------------------------------- FX1 clocks

def test_fx1_format_clock_unit_cases():
    display = _display_module()
    format_clock = display.format_clock
    # Z and +00:00 suffixes: same instant, original string kept in `datetime`.
    assert format_clock("2026-10-09T15:00:00Z") == {
        "datetime": "2026-10-09T15:00:00Z", "en": "9 Oct 15:00 UTC", "zh": "10月9日 15:00 UTC"}
    assert format_clock("2026-10-09T15:00:00+00:00") == {
        "datetime": "2026-10-09T15:00:00+00:00", "en": "9 Oct 15:00 UTC", "zh": "10月9日 15:00 UTC"}
    # +08:00 converts to UTC first (spec §13.3: 23:30 wall -> 15:30 UTC).
    assert format_clock("2026-10-09T23:30:00+08:00") == {
        "datetime": "2026-10-09T23:30:00+08:00", "en": "9 Oct 15:30 UTC", "zh": "10月9日 15:30 UTC"}
    # Naive datetime is already UTC; seconds are dropped (24h HH:MM).
    assert format_clock("2026-10-09T15:00:30")["en"] == "9 Oct 15:00 UTC"
    # Spec §13.3 Dates row verbatim.
    assert format_clock("2026-10-21T08:00:00+00:00") == {
        "datetime": "2026-10-21T08:00:00+00:00", "en": "21 Oct 08:00 UTC", "zh": "10月21日 08:00 UTC"}
    # Date-only (PROPOSAL, record gap): EN "7 Oct 2026", ZH "2026年10月7日".
    assert format_clock("2026-10-07") == {
        "datetime": "2026-10-07", "en": "7 Oct 2026", "zh": "2026年10月7日"}
    # datetime/date objects (naive datetime = UTC; aware converts).
    from datetime import date, datetime, timedelta, timezone
    assert format_clock(datetime(2026, 10, 9, 15, 0))["en"] == "9 Oct 15:00 UTC"
    aware = datetime(2026, 10, 9, 23, 30, tzinfo=timezone(timedelta(hours=8)))
    assert format_clock(aware)["en"] == "9 Oct 15:30 UTC"
    assert format_clock(aware)["zh"] == "10月9日 15:30 UTC"
    assert format_clock(date(2026, 10, 7))["zh"] == "2026年10月7日"
    # None / empty -> None; unparseable -> ValueError (never echoed into markup).
    assert format_clock(None) is None and format_clock("") is None
    with pytest.raises(ValueError):
        format_clock("not a date")
    with pytest.raises(ValueError):
        format_clock("2026-13-99T99:99")


def test_fx1_snapshot_display_one_composition_path():
    display = _display_module()
    raw = {"local": {"clocks": {"observation": "2026-10-07",
                                "computation": "2026-10-09T20:30:00+00:00",
                                "ingestion": None},
                     "qualified": 35, "total": 35}}
    out = display.snapshot_display(raw)
    # The raw clocks pass through unchanged, plus one clock_display per clock.
    assert out["local"]["clocks"] == raw["local"]["clocks"]
    assert out["local"]["qualified"] == 35 and out["local"]["total"] == 35
    display_map = out["local"]["clock_display"]
    assert display_map["observation"] == {"datetime": "2026-10-07", "en": "7 Oct 2026",
                                         "zh": "2026年10月7日"}
    assert display_map["computation"]["en"] == "9 Oct 20:30 UTC"
    assert display_map["ingestion"] is None


def test_fx1_render_shows_formatted_clocks_and_no_raw_iso():
    site = _fixture_site()
    states = site.render_states_page()
    # The populated snapshot variant keeps the machine instant in <time datetime>
    # and prints the §13.3 form as the visible value.
    assert 'datetime="2026-10-09T15:00:00+00:00"' in states
    assert "9 Oct 15:00 UTC" in states and "10月9日 15:00 UTC" in states
    assert 'datetime="2026-10-07"' in states
    assert "7 Oct 2026" in states and "2026年10月7日" in states
    # No visible text node anywhere carries a raw ISO instant (fixture + production).
    for html in (states, site.render_intl_page()):
        scan = _scan(html)
        leaks = [node for node in scan.text if RAW_ISO_TEXT.search(node)]
        assert not leaks, f"raw ISO-8601 leaked into visible text: {leaks[:3]}"
    # The all-None variant keeps the withheld state copy.
    assert "No qualified observation" in states and "无合格观测" in states


def test_fx1_mount_snapshot_carries_clock_display_all_bases(monkeypatch):
    mount = _load_mount()
    _install_builder(monkeypatch, "scanner", lambda **_kwargs: [])
    result = mount.attach_surveillance(_base_workspace(), universe_loader=lambda: {},
                                       rights_loader=lambda: {},
                                       observations=_sample_observations())
    snapshot = result["surveillance"]["snapshot"]
    assert set(snapshot) == {"local", "usd_unhedged", "usd_hedged"}
    for basis in snapshot:
        assert "clock_display" in snapshot[basis], basis
    assert snapshot["local"]["clock_display"]["computation"]["en"] == "9 Oct 20:30 UTC"
    assert snapshot["local"]["clock_display"]["computation"]["zh"] == "10月9日 20:30 UTC"
    assert snapshot["local"]["clock_display"]["observation"]["en"] == "7 Oct 2026"
    assert all(entry is None for entry in snapshot["usd_hedged"]["clock_display"].values()), \
        "usd_hedged never has a qualified observation"


# ---------------------------------------------------------------- FX2 attributes

def test_fx2_no_markup_inside_any_html_attribute():
    site = _fixture_site()
    pages = {
        "states": site.render_states_page(),
        "stub shell": site.render_intl_page(stub_coverage=True),
        "production intl.html": site.render_intl_page(),
    }
    for name, html in pages.items():
        scan = _scan(html)
        bad = []
        for attr, value in scan.attrs:
            # Markup never enters an attribute. The class="l-en"/"l-zh" tokens
            # themselves are legitimate ONLY as class values — anywhere else
            # they are leaked language-span markup.
            if "<" in value or (attr != "class" and ("l-en" in value or "l-zh" in value)):
                bad.append((attr, value))
        assert not bad, f"{name} carries markup inside an attribute: {bad[:3]}"
    # And the source templates never place t() markup in an attribute slot.
    for path in (MACROS_PATH, FIXTURE_PATH, REPO / "tests/intl_gs_fixture_site.py"):
        source = path.read_text(encoding="utf-8")
        hits = re.findall(r'="\{\{\s*t\(', source)
        assert not hits, f'{path.name} places t() inside an attribute: {hits[:3]}'


def test_fx2_stub_market_section_names_its_visible_bandhead():
    site = _fixture_site()
    html = site.render_intl_page(stub_coverage=True)
    assert 'aria-labelledby="intl-gs-market-selection"' in html
    assert '<h2 class="intl-gs__bandhead__title" id="intl-gs-market-selection">' in html


# ---------------------------------------------------------------- FX5 horizon

def test_fx5_horizon_label_vocabulary():
    display = _display_module()
    horizon_label = display.horizon_label
    assert horizon_label("1m") == ("1M", "1月")
    assert horizon_label("3m") == ("3M", "3月")
    assert horizon_label("20d") == ("20D", "20日")
    assert horizon_label("6m") == ("6m", "6m")
    assert horizon_label("ytd") == ("ytd", "ytd")


def test_fx5_snapshot_readout_and_control_share_one_vocabulary():
    site = _fixture_site()
    states = site.render_states_page()
    # The read-out prints the label pair, never the raw id.
    assert ">1m<" not in states and "1M" in states and "1月" in states

    class SegOptions(HTMLParser):
        """Every .intl-gs__seg__opt element: (classes, data-value, inner html)."""

        def __init__(self):
            super().__init__()
            self.options = []
            self._current = None
            self._depth = 0
            self._chunks = []

        def handle_starttag(self, tag, attrs):
            pairs = dict(attrs)
            classes = (pairs.get("class") or "").split()
            if self._current is None:
                if "intl-gs__seg__opt" in classes:
                    self._current = {"classes": classes,
                                     "value": pairs.get("data-value")}
                    self._chunks = []
                    self._depth = 1
                    return
            elif self._current is not None:
                self._depth += 1
                self._chunks.append(self.get_starttag_text())

        def handle_endtag(self, tag):
            if self._current is not None:
                self._depth -= 1
                if self._depth == 0:
                    self.options.append((self._current, "".join(self._chunks)))
                    self._current = None
                    self._chunks = []
                else:
                    self._chunks.append("</%s>" % tag)

        def handle_data(self, data):
            if self._current is not None:
                self._chunks.append(data)

    parser = SegOptions()
    parser.feed(states)
    # The read-out is the is-active option of the READ-ONLY control inside the
    # snapshot bar (its span carries intl-gs__num); the interactive fixture
    # control is the button with data-value.
    readouts = [inner for entry, inner in parser.options
                if "is-active" in entry["classes"] and "intl-gs__num" in entry["classes"]]
    controls = [(entry["value"], inner) for entry, inner in parser.options
                if entry["value"] is not None]
    assert readouts, "the horizon read-out option is missing"
    readout = readouts[0]
    assert "1M" in readout and "1月" in readout, readout
    control = dict(controls).get("1m")
    assert control, "the fixture horizon control is missing a 1m option"
    assert "1M" in control and "1月" in control, control
    assert control == readout, \
        "the segmented control and the read-out must share one vocabulary"


def test_fx5_mount_publishes_horizon_labels_for_every_config_horizon(monkeypatch):
    mount = _load_mount()
    display = _display_module()
    _install_builder(monkeypatch, "scanner", lambda **_kwargs: [])
    result = mount.attach_surveillance(_base_workspace(), universe_loader=lambda: {},
                                       rights_loader=lambda: {}, observations=None)
    labels = result["surveillance"]["horizon_labels"]
    assert set(labels) == set(_base_workspace()["config"]["horizons"])
    for horizon, pair in labels.items():
        assert pair == {"en": display.horizon_label(horizon)[0],
                        "zh": display.horizon_label(horizon)[1]}, horizon


# ---------------------------------------------------------------- FX6 fixture copy

def test_fx6_zh_fixture_copy_is_real_chinese():
    from html.parser import HTMLParser

    class ZhSpans(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack = []
            self.spans = []

        def handle_starttag(self, tag, attrs):
            classes = (dict(attrs).get("class") or "").split()
            self.stack.append("l-zh" in classes)

        def handle_endtag(self, tag):
            if self.stack:
                self.stack.pop()

        def handle_data(self, data):
            if any(self.stack):
                self.spans.append(data)

    parser = ZhSpans()
    parser.feed(_render_fixture())
    for text in parser.spans:
        for word in ("fixture", "Fixture", "stub"):
            assert word not in text, f"English word {word!r} inside a ZH span: {text!r}"
    joined = "".join(parser.spans)
    assert "仅限测试页面" in joined and "示例数值仅用于排版" in joined


# ---------------------------------------------------------------- FX7 precision

def test_fx7_corrected_old_and_new_share_precision():
    html = _render_fixture()
    corrected = html.split('data-state="corrected"', 1)[1].split('data-state="recovered"', 1)[0]
    old = re.search(r'class="intl-gs__old">(.*?)</span>', corrected)
    new = re.search(r'class="intl-gs__statecell__value[^"]*">(.*?)</span>', corrected)
    assert old and new, "the corrected cell must render old and new numerals"
    strip = lambda markup: re.sub(r"<[^>]+>", "", markup)
    old_digits = strip(old.group(1)).strip()
    new_digits = strip(new.group(1)).strip()
    assert old_digits == "+2.90%" and new_digits == "+2.60%", (old_digits, new_digits)

    def decimals(numeral):
        return len(numeral.rstrip("%").split(".")[1]) if "." in numeral else 0

    assert decimals(old_digits) == decimals(new_digits) == 2, (old_digits, new_digits)


def test_fx7_string_old_is_no_longer_accepted():
    with pytest.raises(TypeError):
        _macro_render("{{ gs.gs_state_cell('corrected', 'Brazil', 2.6, '%', 'USD', 'clock', old='+2.9%') }}")


# ---------------------------------------------------------------- F3 single span

def test_f3_gs_value_renders_exactly_one_num_element():
    parts = {"label": "USD move", "unit": "%", "basis": "USD", "clock": "21 Oct 08:00 UTC",
             "tier": "T1", "ink": "up", "dp": 2}
    out = _macro_render("{{ gs.gs_value(1.24, parts=parts) }}", parts=parts)
    elements = re.findall(r'class="[^"]*\bintl-gs__num\b[^"]*"', out)
    assert len(elements) == 1, f"gs_value must emit exactly one .intl-gs__num element: {out}"
    assert out.count("<span") == 1, out


# ---------------------------------------------------------------- F7a chip borders

def test_f7a_loading_and_empty_chips_declare_muted_border():
    css = _css()
    assert ".intl-gs__chip--loading,.intl-gs__chip--empty{border-color:var(--muted);}" in css
    for state in ("loading", "empty"):
        out = _macro_render("{{ gs.gs_state_cell(state, 'Market') }}", state=state)
        assert 'intl-gs__chip--%s' % state in out, state


# ---------------------------------------------------------------- F6 mobile H1

def test_f6_mobile_pagehead_title_uses_the_22px_token():
    css = _css()
    block = re.search(r"@media \(max-width:900px\)\{(.*?)\}\s*\n", css, re.DOTALL)
    assert block, "the ≤900 breakpoint block must exist"
    assert ".intl-gs__pagehead__title{font-size:var(--fs-num-lg);}" in css, \
        "the mobile H1 must reuse the existing 22px token (no px literal, no new token)"
