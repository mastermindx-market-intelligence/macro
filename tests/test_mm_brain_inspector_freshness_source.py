"""Source pin for inspector freshness mapping. Browser fixture is the functional proof."""

from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
COPIES = [ROOT / "templates" / "mm_brain.js", ROOT / "site" / "mm_brain.js"]
LIE = "var freshWord = freshState === 'stale' ? L('stale', '较早') : L('current', '最新');"


def _read(path: pathlib.Path) -> str:
    if not path.exists():
        pytest.skip(f"{path} absent (sparse checkout)")
    return path.read_text(encoding="utf-8")


def test_paired_widget_copies_stay_byte_identical() -> None:
    if not all(path.exists() for path in COPIES):
        pytest.skip("paired asset absent (sparse checkout)")
    assert COPIES[0].read_bytes() == COPIES[1].read_bytes()


@pytest.mark.parametrize("path", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_unknown_freshness_is_not_defaulted_to_current(path: pathlib.Path) -> None:
    text = _read(path)
    assert LIE not in text
    assert "function ctxFreshnessWord(state)" in text
    assert "var freshWord = ctxFreshnessWord(freshState);" in text
    assert "fresh: ['current', '最新']" in text
    assert "stale: ['stale', '较早']" in text
    assert "unknown: ['unknown', '未知']" in text
    assert "not_applicable: ['not applicable', '不适用']" in text
    assert "return pair ? L(pair[0], pair[1]) : L('unknown', '未知');" in text
    assert "typeof state === 'string'" in text
    assert "Object.prototype.hasOwnProperty.call(CTX_FRESHNESS_WORDS, state)" in text
