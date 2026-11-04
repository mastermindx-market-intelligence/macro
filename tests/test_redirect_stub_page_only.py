"""--page-only regression: the redirect-stub builders refresh ONLY their stub shell.

scripts/build_gex_board.py and scripts/build_baskets_china.py both emit a fixed,
zero-context Jinja redirect stub through the builder's own Environment +
lib.pages.write_page. The --page-only / main(page_only=True) boundary added to
both builders must perform exactly that one render+write — BEFORE any collector
import, engine compute, session-clock read, or payload/JSON write — so a
source-only stub update never needs a live market refresh.

The builders' module-level write_page seam is redirected into a temp site root
(the REAL lib.pages.write_page still performs every write) so the checkout's
real site tree is untouched and any stray write shows up as a captured call or
a foreign file next to the sentinel. Every collector/engine entry the FULL
build would touch becomes a loud trap for the duration of a test, so a
page-only fall-through into the full path fails here instead of fetching.
"""
from __future__ import annotations

import inspect
import hashlib
import shutil
import sys
from pathlib import Path

import jinja2
import pytest

from lib import config, shared_shell
from lib.pages import write_page as _real_write_page
from scripts import build_baskets_china, build_gex_board

# builder module -> (stub page name, stub template name)
STUBS = {
    build_gex_board: ("gex.html", "gex.html.j2"),
    build_baskets_china: ("baskets_china.html", "baskets_china.html.j2"),
}


class _Trap:
    """Attribute namespace that fails loudly if a page-only run reaches it."""

    def __init__(self, label: str) -> None:
        self._label = label

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        raise AssertionError(f"page-only must not touch {self._label}.{name}")


def _trap_full_build_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every collector/engine entry of the two FULL builds becomes a loud trap.

    A correct page-only run never consults any of them (it returns before the
    first function-local `from ... import` of the full path). A fall-through
    dies on the trap — or, where the full path swallows exceptions, fails the
    stub-written assertions below — before any real compute or network work.
    """
    for modname in (
        "collectors.cboe",           # gex: GexAdapter
        "engine.gex_model",          # gex: build_model
        "engine.gex_state",          # gex: compute_gex_state
        "engine.baskets_china",      # china: compute_china_baskets
        "engine.theme_scoring",      # china: theme rotation desk
        "engine.theme_context",      # china: leadership hero
        "engine.narrative_emergence",
        "engine.risk_radar_intl",
        "engine.sector_pulse",
        "engine.basket_freeze",
        "engine.china_basket_turn",
        "engine.signal_gate",        # china: member entry signals
    ):
        monkeypatch.setitem(sys.modules, modname, _Trap(modname))

    # gex: the as-of clock is market work too — page-only must never read it.
    def _no_session_clock(*_args, **_kwargs):
        raise AssertionError("page-only must not resolve the market session clock")

    monkeypatch.setattr(build_gex_board, "_resolve_session", _no_session_clock)


@pytest.fixture
def temp_site(tmp_path, monkeypatch: pytest.MonkeyPatch):
    # Keep every default path, including canonical page-writer asset ensures,
    # inside this temp root. The template source remains read-only.
    source_root = config.ROOT
    (tmp_path / "templates").symlink_to(source_root / "templates", target_is_directory=True)
    shutil.copyfile(source_root / "config.yml", tmp_path / "config.yml")
    site = tmp_path / "site"
    site.mkdir()
    for name in ("shared_shell_bridge.js", "shared_shell.css", "data_base.js"):
        shutil.copyfile(source_root / "templates" / name, site / name)
    sentinel = site / "sentinel.json"
    sentinel.write_text("keep-me", encoding="utf-8")
    for path in (site / "gex/index.json", site / "chinabasketdata/baskets.json",
                 tmp_path / "data/market-sentinel.json"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"asof":"retained","sentinel":true}', encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    config.load.cache_clear()
    monkeypatch.setattr(shared_shell, "ROOT", tmp_path)
    shared_shell.ensure_shared_shell_asset.cache_clear()
    shared_shell.asset_version.cache_clear()
    shared_shell.stylesheet_version.cache_clear()
    calls: list[tuple[Path, str]] = []

    def snapshot():
        return {str(path.relative_to(tmp_path)): hashlib.sha256(path.read_bytes()).hexdigest()
                for root in (site, tmp_path / "data") for path in root.rglob("*") if path.is_file()}

    before = snapshot()
    def _recording_write(path, html):
        target = Path(path)
        assert target.parent == site
        calls.append((target, html))
        return _real_write_page(target, html)

    for mod in STUBS:
        monkeypatch.setattr(mod, "write_page", _recording_write)
    yield site, sentinel, calls, before, snapshot
    config.load.cache_clear()
    shared_shell.ensure_shared_shell_asset.cache_clear()
    shared_shell.asset_version.cache_clear()
    shared_shell.stylesheet_version.cache_clear()


@pytest.mark.parametrize("builder", list(STUBS), ids=["gex_board", "baskets_china"])
def test_page_only_writes_only_the_fixed_redirect_stub(builder, temp_site, monkeypatch):
    site, sentinel, calls, before, snapshot = temp_site
    page_name, template_name = STUBS[builder]

    _trap_full_build_paths(monkeypatch)

    assert builder.main(page_only=True) == 0

    # Exactly ONE write crossed the builder boundary: the fixed stub page.
    assert [target.name for target, _ in calls] == [page_name]

    html = calls[0][1]
    # Same fixed render the full build emits — an independent zero-context
    # render of the SAME existing template through an identical Environment
    # (both builders render their stub with no context at all).
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(config.ROOT / "templates")), autoescape=True
    )
    assert html == env.get_template(template_name).render()

    # The existing shell navigation + declarative noscript fallback survive.
    if builder is build_gex_board:
        assert 'content="0;url=options.html#ticker"' in html
        assert "options.html?t=" in html  # deep-link symbol carry into the workspace
    else:
        assert 'content="0;url=sector_central_china.html#si-explore"' in html
        assert "sector_central_china.html" in html
    assert "<noscript>" in html
    assert "MMXSharedShell" in html

    # Existing payload/data/assets are byte-identical. The only added file is
    # the fixed stub; canonical write_page is allowed to inject its owned head.
    after = snapshot()
    assert set(after) - set(before) == {"site/" + page_name}
    assert all(after.get(path) == digest for path, digest in before.items())
    assert sentinel.read_text(encoding="utf-8") == "keep-me"
    emitted = (site / page_name).read_text(encoding="utf-8")
    assert emitted.count('name="mmx-shell-document"') == 1
    assert "data-dbase" in emitted
    assert "MMXSharedShell" in emitted
    assert "<noscript>" in emitted


def test_main_signatures_keep_existing_callers_whole():
    # GEX as_of callers are untouched; page_only is additive and defaults off,
    # so the default full build behaves exactly as before.
    gex = inspect.signature(build_gex_board.main)
    assert list(gex.parameters) == ["as_of", "page_only"]
    assert gex.parameters["as_of"].default is None
    assert gex.parameters["page_only"].default is False

    cn = inspect.signature(build_baskets_china.main)
    assert list(cn.parameters) == ["page_only"]
    assert cn.parameters["page_only"].default is False


def test_render_lane_routes_stub_changes_to_page_only_producers():
    import subprocess

    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/render.yml").read_text()
    lines = workflow.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "region_of() {")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "}")
    picker = "\n".join(line.strip() for line in lines[start:end + 1])
    for path in ("templates/gex.html.j2", "templates/baskets_china.html.j2"):
        actual = subprocess.check_output(["bash", "-c", picker + '\nregion_of "$1"', "_", path], text=True)
        assert actual.strip() == "stubs"
    for path, expected in (("scripts/build_gex_board.py", "gex"),
                           ("scripts/build_baskets_china.py", "all")):
        actual = subprocess.check_output(["bash", "-c", picker + '\nregion_of "$1"', "_", path], text=True)
        assert actual.strip() == expected
    assert 'scripts.build_gex_board --page-only' in workflow
    assert 'scripts.build_baskets_china --page-only' in workflow
    # Both all-scope and the narrow template-only scope must execute the helper.
    assert "us_pages; libs; sits; csits; stubs ;;" in workflow
    assert "stubs)\n              stubs ;;" in workflow
