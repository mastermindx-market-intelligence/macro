"""Keep the mobile Quick Jump foreground free of decorative canvas work."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _asset(name: str) -> str:
    return (ROOT / 'site' / name).read_text(encoding='utf-8')


def test_mobile_menu_parks_globe_and_resumes_once_when_closed() -> None:
    source = _asset('globe-deck.js')
    assert "document.querySelector('.site-nav')" in source
    assert "classList.contains('nav-open')" in source
    assert 'if (_navMenuOpen()) { _park(); return; }' in source
    assert 'if (_navMenuOpen()) return;' in source
    assert 'if (open === _navWasOpen) return;' in source
    assert 'if (open) _park(); else _wake();' in source
    assert "attributeFilter: ['class']" in source
    assert "window.__gdDeckInit" in source


def test_mobile_menu_parks_sky_and_unparks_only_on_transition() -> None:
    source = _asset('sky.js')
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
    html = _asset('start.html')
    for filename in ('globe-deck.js', 'sky.js'):
        values = re.findall(rf'<script defer src="{re.escape(filename)}\?v=([0-9a-f]{{8}})"', html)
        expected = hashlib.sha256((ROOT / 'site' / filename).read_bytes()).hexdigest()[:8]
        assert values == [expected], filename
