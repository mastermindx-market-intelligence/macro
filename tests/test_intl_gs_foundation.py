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

TOKEN_MARK_START = "/* === INTL-GS §5.3 TOKENS (seat ruling DEC:INTL-GS-R14-DESIGN-FREEZE (1)) === */"
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
  --r-panel:14px; --r-btn:10px; --r-pill:999px;
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:20px; --sp-6:24px; --sp-7:32px; --sp-8:44px;
  /* chart series: Local, FX, Common, 4th series */
  --ser-1:#5b9bf0; --ser-2:#d4a017; --ser-3:#0ea5e9; --ser-4:#e08b45;
  /* returns heat — FILL ONLY, never text ink */
  --returns-up-soft:#1a2325; --returns-up-mid:#1d2b29; --returns-up-strong:#213a31;
  --returns-down-soft:#222025; --returns-down-mid:#302429; --returns-down-strong:#402a2f;
}
html[data-theme="light"] .intl-gs{
  --ser-1:#2f63c4; --ser-2:#8f6a04; --ser-3:#0284c7; --ser-4:#b06a25;
  --returns-up-soft:#edf7f1; --returns-up-mid:#dbefe4; --returns-up-strong:#c0e3cf;
  --returns-down-soft:#fbf0f0; --returns-down-mid:#f7e0e0; --returns-down-strong:#f2caca;
}
/* ZH: positive heat follows the red-up convention, exactly like --up/--down */
html[data-lang="zh"] .intl-gs{
  --returns-up-soft:#222025; --returns-up-mid:#302429; --returns-up-strong:#402a2f;
  --returns-down-soft:#1a2325; --returns-down-mid:#1d2b29; --returns-down-strong:#213a31;
}
html[data-theme="light"][data-lang="zh"] .intl-gs{
  --returns-up-soft:#fbf0f0; --returns-up-mid:#f7e0e0; --returns-up-strong:#f2caca;
  --returns-down-soft:#edf7f1; --returns-down-mid:#dbefe4; --returns-down-strong:#c0e3cf;
}
html[data-lang="zh"] .intl-gs{
  --font-zh:"PingFang SC","Hiragino Sans GB","Noto Sans SC","Microsoft YaHei";
  font-family:var(--font-zh),var(--font-ui);
}"""

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


# ---------------------------------------------------------------- 2.2 L1 stripe


def test_no_accent_stripe_l1():
    css = _strip_comments(_css())
    for selector, body in _rules(css):
        for decl in body.split(";"):
            decl = decl.strip()
            prop = decl.split(":")[0].strip().lower()
            assert prop not in ("border-left", "border-right", "border-inline-start",
                                "border-inline-end", "border-block-start", "border-block-end"), selector
            if prop in ("border-top", "border-bottom"):
                assert decl.endswith("1px solid var(--line)") or decl.endswith(":none"), (selector, decl)
                assert re.search(r"row|cell|table|head", selector), (selector, decl)
        assert "inset" not in body, selector
        assert "::before" not in selector and "::after" not in selector, selector


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
        assert "var(--r-" in value, value


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
    return env.get_template("intl_workspace/_gs_state_fixture.html.j2").render()


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
    pytest.importorskip("bs4")
    from bs4 import BeautifulSoup
    html = _render_fixture()
    soup = BeautifulSoup(html, "html.parser")
    scopes = [el for el in soup.find_all(class_="intl-gs__specimen-scope")]
    assert scopes, "fixture must carry a specimen scope"
    chips = soup.find_all(class_="intl-gs__chip--specimen")
    assert chips and any(chip.find_parent(class_="intl-gs__specimen-scope") for chip in chips)
    for number in soup.find_all(class_="intl-gs__num"):
        assert number.find_parent(class_="intl-gs__specimen-scope"), str(number)


def test_fixture_not_referenced_by_production_templates():
    for path in (SHELL_PATH, INTL_PAGE_PATH, REPO / "templates/_navlinks.html.j2"):
        text = path.read_text(encoding="utf-8")
        assert "_gs_state_fixture" not in text, path


# ---------------------------------------------------------------- 2.13 frozen files


@pytest.mark.parametrize("path", [
    "templates/theme.css",
    "templates/_navlinks.html.j2",
    "engine/intl_global_universe.py",
    "engine/intl_global_observation.py",
    "lib/intl_global_observation_adapter.py",
])
def test_frozen_files_unchanged_vs_origin_main(path):
    result = subprocess.run(["git", "diff", "--quiet", "origin/main", "--", path],
                            cwd=REPO, capture_output=True)
    assert result.returncode == 0, f"{path} changed vs origin/main"


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
