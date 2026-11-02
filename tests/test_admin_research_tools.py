"""Contract tests for the authenticated Research Tools SPA directory."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP_JS = ROOT / "admin" / "static" / "app.js"
STYLES_CSS = ROOT / "admin" / "static" / "styles.css"
CADDY = ROOT / "app" / "deploy" / "Caddyfile"

TOOLS = (
    ("committee.html", "Neural Web Deep View"),
    ("measurement.html", "Calibration Lab"),
    ("crossasset.html", "Cross-Asset Diagnostics"),
    ("signal_lab.html", "Signal Lab"),
    ("tech_lab.html", "Technical Lab"),
    ("macro_signals.html", "Macro Signals"),
    ("factors.html", "Factors &amp; Seasonality"),
)


def _source() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _renderer(source: str) -> str:
    return source.split("RENDER.research_tools = () => {", 1)[1].split(
        "/* ---- EXPERIMENTS", 1
    )[0]


def test_research_tools_is_a_first_class_sidebar_route():
    source = _source()
    assert "research_tools: NAV_ICO(" in source
    assert '["research_tools", "Research Tools"]' in source
    assert 'label: "Intelligence & research"' in source
    assert "RENDER.research_tools = () => {" in source


def test_research_tools_renderer_is_static_and_makes_no_api_call():
    renderer = _renderer(_source())
    assert "api(" not in renderer
    assert "fetch(" not in renderer
    assert "post(" not in renderer


def test_all_internal_surfaces_are_secure_new_tab_links():
    renderer = _renderer(_source())
    links = re.findall(
        r'<a class="rt-card[^"]*" href="([^"]+)" target="_blank" rel="noopener">',
        renderer,
    )
    assert links == [
        f"https://admin.mastermind-x.com/research-tools/{path}"
        for path, _ in TOOLS
    ]
    for _, label in TOOLS:
        assert f"<strong>{label}</strong>" in renderer


def test_internal_surfaces_are_admin_host_only():
    caddy = CADDY.read_text(encoding="utf-8")
    assert "handle_path /research-tools/*" in caddy
    assert "forward_auth 127.0.0.1:8787" in caddy
    assert "uri /api/auth-check" in caddy
    never_site = caddy.split("@never_site {", 1)[1].split("}", 1)[0]
    for path, _ in TOOLS:
        assert f"/{path}" in never_site


def test_research_copy_and_responsive_styles_keep_the_internal_boundary_clear():
    renderer = _renderer(_source())
    styles = STYLES_CSS.read_text(encoding="utf-8")
    assert "Diagnostics, calibration, and internal research methods." in renderer
    assert "Admin-only research workspace." in renderer
    assert renderer.count("<svg") >= 16
    assert "@media (max-width: 700px)" in styles
    assert ".rt-grid" in styles


# ---- public pages and the internal boundary ----

_TEMPLATES = ROOT / "templates"
_INTERNAL = tuple(path for path, _ in TOOLS)
_INTERNAL_LINK = re.compile(
    r"""href\s*=\s*\\?["'](?:\./|/)?(%s)"""
    % "|".join(re.escape(path) for path in _INTERNAL)
)

# A public page that links here sends its reader to "Not found": these pages
# return 404 on the public host (see test_internal_surfaces_are_admin_host_only).
# dashboard.html.j2 still has links because other PRs were writing that file when
# this guard was added. hk.html.j2 and canada.html.j2 still have one each because
# the P0B browser receipts pin those two templates and another PR is rewriting the
# receipts. These counts may fall. They may not rise, and no other public template
# may join them.
_KNOWN_PUBLIC_LINKS = {"canada.html.j2": 1, "dashboard.html.j2": 8, "hk.html.j2": 1}


def _public_links_to_internal_pages():
    found = {}
    for path in sorted(_TEMPLATES.rglob("*")):
        if not path.is_file() or path.suffix not in {".j2", ".html", ".js"}:
            continue
        if path.name.split(".")[0] + ".html" in _INTERNAL:
            continue  # an internal page may link to another internal page
        count = len(_INTERNAL_LINK.findall(path.read_text(encoding="utf-8", errors="replace")))
        if count:
            found[str(path.relative_to(_TEMPLATES))] = count
    return found


def test_public_templates_do_not_link_to_internal_pages():
    found = _public_links_to_internal_pages()
    extra = {
        name: count
        for name, count in found.items()
        if count > _KNOWN_PUBLIC_LINKS.get(name, 0)
    }
    assert not extra, f"public template links to an admin-only page: {extra}"


def test_the_guard_sees_a_link_to_an_internal_page():
    for link in (
        '<a href="measurement.html">',
        "<a href='signal_lab.html#x'>",
        '<a href="./committee.html">',
        '<a href="/factors.html">',
        '\'<a href=\\"tech_lab.html\\">\'',
    ):
        assert _INTERNAL_LINK.search(link), link
    for link in ('<a href="methodology.html">', '<a href="neural_web.html">'):
        assert not _INTERNAL_LINK.search(link), link


def test_alerts_do_not_send_the_reader_to_signal_lab():
    """The engine's verdict still carries link=signal_lab.html for internal use.

    That value reaches no static scan, so it is pinned here at the template.
    """
    src = (_TEMPLATES / "alerts.html.j2").read_text(encoding="utf-8")
    assert "v.link" not in src
    assert "See Signal Lab" not in src
    assert "详见信号实验室" not in src
    assert "Validated as" not in src
    assert "验证为" not in src
    assert "Measured as: " in src and "度量为：" in src


def test_seasonality_keeps_its_one_working_method_link():
    src = (_TEMPLATES / "seasonality.html.j2").read_text(encoding="utf-8")
    assert src.count('href="methodology.html#seasonality"') == 1
    target = (_TEMPLATES / "methodology.html.j2").read_text(encoding="utf-8")
    assert 'id="seasonality"' in target


def test_macro_context_stops_pointing_at_the_committee_view():
    src = (_TEMPLATES / "macro_context.html.j2").read_text(encoding="utf-8")
    assert "Committee View" not in src
    assert "委员会视图" not in src
    assert "Contradictions are context only." in src
