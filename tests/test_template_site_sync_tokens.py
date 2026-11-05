"""The theme.js pair check must survive theme.js carrying MORE THAN ONE bake token.

`scripts/check_template_site_sync.py` compares site/theme.js against the exact
`emit_theme_js()` output wherever PyYAML is importable. In the stdlib-only context
— `pages.yml` publish, which is a DEPLOY GATE — it cannot reproduce the bake, so it
falls back to asserting that everything AROUND the baked tokens is byte-identical.

That fallback used `str.partition` on the single Supabase token: one head, one
tail, `startswith` + `endswith`. Adding a second token (the mm_brain.js content
hash) to theme.js would have put a token inside `head` or `tail` — whichever side
it fell on, the site copy carries a hash there and the template carries the
placeholder, so the comparison fails on a perfectly healthy tree and the publish
refuses. A publish gate that fails closed on correct input is an outage.

These tests pin the generalized form: N tokens -> N+1 invariant segments, matched
in order, and still strict about everything the bake does not touch.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.check_template_site_sync import (  # noqa: E402
    _MM_BRAIN_VER_TOKEN,
    _THEME_TOKEN,
    _THEME_TOKENS,
    _matches_around_tokens,
    _token_segments,
)

WORKTREE = Path(__file__).resolve().parent.parent
TEMPLATES = WORKTREE / "templates"
SITE = WORKTREE / "site"


def test_token_list_matches_the_baker() -> None:
    """The guard's token list is the baker's, or the fallback silently mis-splits."""
    from lib import site_assets

    assert _THEME_TOKEN == site_assets.SUPABASE_TOKEN
    assert _MM_BRAIN_VER_TOKEN == site_assets.MM_BRAIN_VER_TOKEN
    assert set(_THEME_TOKENS) == {site_assets.SUPABASE_TOKEN, site_assets.MM_BRAIN_VER_TOKEN}


def test_every_token_in_the_list_is_actually_in_theme_js() -> None:
    """A token the template no longer carries is dead weight that hides a real one."""
    src = (TEMPLATES / "theme.js").read_text()
    for tok in _THEME_TOKENS:
        assert tok in src, f"{tok!r} is listed but absent from templates/theme.js"


def test_segments_are_the_invariant_text() -> None:
    text = "AAA<T1>BBB<T2>CCC"
    assert _token_segments(text, ("<T1>", "<T2>")) == ["AAA", "BBB", "CCC"]
    # order-independent: the splitter follows the text, not the tuple
    assert _token_segments(text, ("<T2>", "<T1>")) == ["AAA", "BBB", "CCC"]
    assert _token_segments("no tokens here", ("<T1>",)) == ["no tokens here"]


def test_missing_emitter_fails_theme_verification_closed(tmp_path, monkeypatch, capsys) -> None:
    from scripts import check_template_site_sync as guard
    (tmp_path / "templates").mkdir(); (tmp_path / "site").mkdir()
    source = "window.SUPABASE_CFG = " + _THEME_TOKEN + ";"
    (tmp_path / "templates" / "theme.js").write_text(source)
    (tmp_path / "site" / "theme.js").write_text(source)
    monkeypatch.setattr(guard, "_bake_theme", lambda _path: None)
    assert guard.check(tmp_path) == ["theme.js"]
    assert guard.check(tmp_path, fix=True) == ["theme.js"]
    assert guard.check.unfixed == ["theme.js"]
    assert "rjsmin==1.2.5" in capsys.readouterr().out
    assert (tmp_path / "site" / "theme.js").read_text() == source


def test_exact_emitter_accepts_minified_pair_and_rejects_changes(tmp_path) -> None:
    from lib import site_assets
    from scripts import check_template_site_sync as guard
    (tmp_path / "templates").mkdir(); (tmp_path / "site").mkdir()
    theme = tmp_path / "templates" / "theme.js"
    theme.write_text("window.SUPABASE_CFG = " + _THEME_TOKEN + ";")
    output = tmp_path / "site" / "theme.js"
    emitted = site_assets.emit_theme_js(theme); output.write_text(emitted)
    assert guard.check(tmp_path) == []
    for broken in (emitted[:len(emitted)//2], emitted + "window.changed=true;", emitted.replace("SUPABASE_CFG","WRONG_CFG")):
        output.write_text(broken)
        assert guard.check(tmp_path) == ["theme.js"]


def test_fallback_still_rejects_a_real_one_sided_edit() -> None:
    """Generalizing the split must not soften what the gate is FOR."""
    tpl = (TEMPLATES / "theme.js").read_text()
    site = (SITE / "theme.js").read_text()
    segs = _token_segments(tpl, _THEME_TOKENS)
    overlay = TEMPLATES / "terminal_overlay.js"
    if overlay.is_file():
        segs[-1] = f"{segs[-1].rstrip()}\n\n{overlay.read_text().lstrip()}"
    reworded = site.replace("function initChatLauncher", "function initChatLauncherX", 1)
    assert reworded != site, "fixture no longer matches theme.js — re-point it"
    assert not _matches_around_tokens(reworded, segs), "a template-only reword must fail"
    assert not _matches_around_tokens(site[: len(site) // 2], segs), "truncation must fail"
    assert not _matches_around_tokens(site + "\n/* appended */", segs), "an append must fail"


def test_fallback_is_exact_when_there_are_no_tokens() -> None:
    """A pair with no bake token at all is a plain byte compare."""
    assert _matches_around_tokens("abc", ["abc"])
    assert not _matches_around_tokens("abcd", ["abc"])
    assert not _matches_around_tokens("ab", ["abc"])
