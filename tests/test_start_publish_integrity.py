"""Regression guards for the signed-in start page publish path.

The 2026-08-01 render race committed an autostash conflict literally into
``site/start.html``. Browsers executed both conflict sides, starting two globe and
sky animation loops on the same canvases. These checks keep the shipped runtime
single-instance and make every lane that writes the page fail closed before push.
"""
from __future__ import annotations

import re
import hashlib
from pathlib import Path

from scripts.workflow_run_source import resolved_workflow_text


ROOT = Path(__file__).resolve().parents[1]
START = ROOT / "site" / "start.html"
WORKFLOWS = ROOT / ".github" / "workflows"


def _lane_text(lane: str) -> str:
    # 512KB-cap diet: some daily.yml bodies live in scripts/ci/ — splice them
    # back IN PLACE so the count/order assertions keep their meaning.
    return resolved_workflow_text(WORKFLOWS / lane, ROOT)


def _script_basenames(html: str) -> list[str]:
    srcs = re.findall(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\']', html)
    return [src.split("?", 1)[0].rsplit("/", 1)[-1] for src in srcs]


def test_committed_start_has_one_copy_of_each_runtime() -> None:
    html = START.read_text(encoding="utf-8")
    assert "<<<<<<< " not in html
    assert ">>>>>>> " not in html

    scripts = _script_basenames(html)
    for asset in (
        "globe-deck.js",
        "sky.js",
        "hub-welcome.js",
        "live_config.js",
        "live.js",
        "wh_banner.js",
    ):
        assert scripts.count(asset) == 1, f"start.html loads {asset} {scripts.count(asset)} times"


def test_animation_runtimes_are_idempotent() -> None:
    guards = {
        "site/globe-deck.js": "window.__gdDeckInit",
        "site/sky.js": "window.__skyDeckInit",
        "site/hub-welcome.js": "window.__hubWelcomeInit",
    }
    for relative, marker in guards.items():
        assert marker in (ROOT / relative).read_text(encoding="utf-8"), relative


def test_start_builder_does_not_reload_nav_live_runtime() -> None:
    source = (ROOT / "scripts" / "build_vector.py").read_text(encoding="utf-8")
    hub = source[source.index("def _hub_html("):source.index("\ndef ", source.index("def _hub_html(") + 1)]
    assert '<script src="live_config.js"></script>' not in hub
    assert '<script src="live.js"></script>' not in hub
    assert hub.count('data-whb data-root="" src="wh_banner.js"') == 1


def test_start_writing_lanes_guard_before_commit_and_after_rebase() -> None:
    guard = "python3 scripts/check_conflict_markers.py --file site/start.html"
    sync = "python -m scripts.check_template_site_sync --fix"
    for lane in ("render.yml", "engine-render.yml", "daily.yml"):
        text = _lane_text(lane)
        assert text.count(guard) >= 2, f"{lane} lacks pre-commit and post-rebase marker gates"
        for match in re.finditer(re.escape(sync), text):
            next_guard = text.find(guard, match.end())
            boundaries = [
                pos for token in ("git add site/", "if ! git diff --quiet", "if push_do")
                if (pos := text.find(token, match.end())) >= 0
            ]
            assert boundaries and match.end() < next_guard < min(boundaries), (
                f"{lane} can stage or push after a sync without rerunning the conflict-marker gate"
            )


def test_pr_marker_gate_ratchets_from_the_base_branch() -> None:
    manifest = (ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    assert 'check_conflict_markers.py --changed-from "origin/${CI_BASE_REF:-main}"' in manifest


def test_start_writing_lanes_gate_runtime_single_instance() -> None:
    """Marker gates can't see the 2026-08-01 second act: a stale-checkout render
    re-emitted the doubled live pair with zero conflict markers (adad513bdfe) and
    pushed it over the #4163 fix. Every start-writing lane must pair each marker
    gate with the runtime single-instance guard — pre-commit healing from HEAD,
    post-rebase healing from the freshly rebased origin/main."""
    marker_gate = "python3 scripts/check_conflict_markers.py --file site/start.html"
    for lane in ("render.yml", "engine-render.yml", "daily.yml"):
        text = _lane_text(lane)
        assert text.count("python3 scripts/check_start_runtime.py --heal-from HEAD") == 1, (
            f"{lane} lacks the pre-commit start-runtime gate (heal from HEAD)"
        )
        assert text.count("python3 scripts/check_start_runtime.py --heal-from origin/main") == 1, (
            f"{lane} lacks the post-rebase start-runtime gate (heal from origin/main)"
        )
        assert text.count("scripts/check_start_runtime.py") == text.count(marker_gate), (
            f"{lane}: every start.html marker gate needs a runtime gate beside it"
        )


def test_lane_guard_checks_the_same_runtimes() -> None:
    """The lane guard and this file must police the same runtime list — a drift
    (an asset added here but not there) reopens the unguarded-lane hole."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_start_runtime", ROOT / "scripts" / "check_start_runtime.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert set(mod.RUNTIMES) == {
        "globe-deck.js",
        "sky.js",
        "hub-welcome.js",
        "live_config.js",
        "live.js",
        "wh_banner.js",
    }
    assert not mod.check_text(
        "".join(f'<script defer src="{a}?v=x"></script>' for a in mod.RUNTIMES)
    )
    assert mod.check_text('<script defer src="sky.js"></script>')



def test_wh_banner_asset_copies_remain_identical() -> None:
    """The shared alert rail is a plain-copy runtime and must ship paired bytes."""
    source = ROOT / "templates" / "wh_banner.js"
    shipped = ROOT / "site" / "wh_banner.js"
    assert source.read_bytes() == shipped.read_bytes()


def test_wh_banner_dismiss_control_meets_interaction_contract() -> None:
    """Sitewide alert dismissal must be touch-, keyboard-, and locale-reachable."""
    for relative in ("templates/wh_banner.js", "site/wh_banner.js"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert ".whb-x{flex:0 0 40px;width:40px;height:40px;display:grid;place-items:center;" in text
        assert "background:transparent;border:0;color:inherit;opacity:.6;" in text
        assert "border-radius:var(--r-sm,10px);touch-action:manipulation" in text
        assert ".whb-x:hover{opacity:1}" in text
        assert ".whb-x:focus-visible{outline:2px solid currentColor;" in text
        assert ".whb-x:active{opacity:.78}" in text
        assert 'function syncCloseLabel() {' in text
        assert '? "关闭市场提醒"' in text
        assert ': "Dismiss market alert"' in text
        assert 'document.addEventListener("langchange", syncCloseLabel);' in text
        assert 'document.removeEventListener("langchange", syncCloseLabel);' in text


def test_mobile_menu_parks_globe_and_resumes_once_when_closed() -> None:
    source = (ROOT / "site" / "globe-deck.js").read_text(encoding="utf-8")
    assert "document.querySelector('.site-nav')" in source
    assert "classList.contains('nav-open')" in source
    assert 'if (_navMenuOpen()) { _park(); return; }' in source
    assert 'if (_navMenuOpen()) return;' in source
    assert 'if (open === _navWasOpen) return;' in source
    assert 'if (open) _park(); else _wake();' in source
    assert "attributeFilter: ['class']" in source
    assert "window.__gdDeckInit" in source


def test_mobile_menu_parks_sky_and_unparks_only_on_transition() -> None:
    source = (ROOT / "site" / "sky.js").read_text(encoding="utf-8")
    assert "document.querySelector('.site-nav')" in source
    assert "classList.contains('nav-open')" in source
    assert 'if (_navMenuOpen()) { running = false; raf = 0; return; }' in source
    assert 'if (_navMenuOpen()) return; lastActT = nowMs();' in source
    assert 'if (open === _navWasOpen) return;' in source
    assert 'if (raf) cancelAnimationFrame(raf);' in source
    assert 'else _activity();' in source
    assert "attributeFilter: ['class']" in source
    assert "window.__skyDeckInit" in source


def test_start_hub_serves_current_content_hashed_animation_scripts() -> None:
    html = START.read_text(encoding="utf-8")
    for filename in ('globe-deck.js', 'sky.js'):
        values = re.findall(rf'<script defer src="{re.escape(filename)}\?v=([0-9a-f]{{8}})"', html)
        expected = hashlib.sha256((ROOT / 'site' / filename).read_bytes()).hexdigest()[:8]
        assert values == [expected], filename
