"""Interaction contract for the shared market-alert banner asset."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COPIES = (ROOT / "templates" / "wh_banner.js", ROOT / "site" / "wh_banner.js")


def test_wh_banner_copies_remain_identical() -> None:
    assert COPIES[0].read_bytes() == COPIES[1].read_bytes()


def test_dismiss_control_meets_touch_keyboard_and_i18n_contract() -> None:
    for path in COPIES:
        text = path.read_text(encoding="utf-8")
        assert ".whb-x{flex:0 0 40px;width:40px;height:40px;display:grid;place-items:center;" in text
        assert "border-radius:var(--r-sm,10px);touch-action:manipulation" in text
        assert ".whb-x:focus-visible{outline:2px solid" in text
        assert ".whb-x:active{color:var(--text,#fff);" in text
        assert 'function syncCloseLabel() {' in text
        assert '? "关闭市场提醒"' in text
        assert ': "Dismiss market alert"' in text
        assert 'document.addEventListener("langchange", syncCloseLabel);' in text
        assert 'document.removeEventListener("langchange", syncCloseLabel);' in text
