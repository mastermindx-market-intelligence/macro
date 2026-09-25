"""A-MOR-2b lane B — AM Edition premarket overlay boundary (extracted).

The lane writes ``/var/lib/macro-live/public/am_edition.{json,html}`` from a
VPS-side oneshot; Caddy is the only place that decides whether anonymous bytes
flow. This file pins the boundary contracts the spec names (B4, B6) so a
future edit cannot silently widen the static-access boundary — particularly
the trap that adding /am_edition.json to @vps_public_live would create (it
would let anonymous callers read the registered asset without paying the wall).

This file is SEPARATE from ``tests/test_caddy_hub_boundary.py`` because that
suite carries a module-level ``pytest.importorskip("fastapi")`` (line ~457 in
the merged head) which skips the ENTIRE module on a venv without fastapi —
including any test defined above the importorskip line. Extracting the AM-
edition assertions here lets the thin venv used by
``scripts/check_caddy_hub_boundary.py --mode enforce-added``'s review unit
pick up these boundary checks too (the precise MINOR-6 fix).

Run: ``python -m pytest tests/test_caddy_hub_boundary_am_edition.py -q``
"""
from __future__ import annotations

import re
from pathlib import Path

from scripts.check_caddy_hub_boundary import (
    REPO_ROOT,
    UNSAFE,
    classify_backend_proxies,
)

CADDYFILE_PATH = REPO_ROOT / "app" / "deploy" / "Caddyfile"


def _matcher_block(caddy: str, name: str) -> str:
    """Find the named matcher's body: from `@name {` to the matching closing
    brace, returning the inner text. Used by the AM-edition assertions below
    to read the path list verbatim."""
    start = caddy.find(f"@{name} {{")
    assert start != -1, f"Caddyfile has no @{name} matcher"
    i = caddy.find("{", start)
    depth = 0
    j = i
    while j < len(caddy):
        ch = caddy[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return caddy[i + 1 : j]
        j += 1
    raise AssertionError(f"@{name} matcher has no closing brace")


def _handle_block(caddy: str, name: str) -> str:
    """Find `handle @name { ... }` body. Distinct from `_matcher_block`
    because the Caddyfile can have BOTH `@name { ... }` (the matcher that
    classifies requests) AND `handle @name { ... }` (the route body that
    acts on them). The AM-edition overlay must live inside the HANDLE, not
    the MATCHER — gate 2's anonymous 200+noindex depends on the overlay
    running through the gate reached via the handle's route body."""
    needle = f"handle @{name} {{"
    start = caddy.find(needle)
    assert start != -1, f"Caddyfile has no `handle @{name}` block"
    i = caddy.find("{", start)
    depth = 0
    j = i
    while j < len(caddy):
        ch = caddy[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return caddy[i + 1 : j]
        j += 1
    raise AssertionError(f"`handle @{name}` has no closing brace")


def test_am_edition_json_is_in_vps_external_and_not_in_vps_public_live() -> None:
    """B6: the json is in @vps_external and NOT in @vps_public_live.

    Why both sides matter:
      * @vps_external serves only from inside handle @reg_asset's authenticated
        route (line 371-374), so anonymous GET /am_edition.json stays 401 — the
        registered asset contract gate 2 names.
      * @vps_public_live serves the reviewed public live artifacts with
        Cache-Control: no-store. If /am_edition.json ever landed there, an
        anonymous visitor would read the registered asset without paying the
        wall — exactly the boundary-widening the spec forbids.
    """
    caddy = CADDYFILE_PATH.read_text(encoding="utf-8")
    external = _matcher_block(caddy, "vps_external")
    public_live = _matcher_block(caddy, "vps_public_live")

    assert "/am_edition.json" in external, (
        "/am_edition.json must live in @vps_external so anonymous reads stay 401"
    )
    assert "/am_edition.json" not in public_live, (
        "/am_edition.json must NOT be in @vps_public_live — adding it would "
        "let anonymous callers read a registered asset and widen the static-access "
        "boundary the spec forbids widening"
    )


def test_am_edition_html_overlay_handle_sits_inside_handle_open_html() -> None:
    """B6: the html overlay handle sits inside handle @open_html.

    The block ordering inside `handle @open_html`'s route body is meaningful:
        reverse_proxy 127.0.0.1:8000 { ... }   <- gate check (line ~430)
        header Cache-Control ...               <- anonymous-read TTL
        header X-Robots-Tag ...                <- noindex, noarchive
        @am_edition_live { path /am_edition.html file { root ... } }
        handle @am_edition_live { root * /var/lib/macro-live/public
                                  header Cache-Control "no-store"
                                  file_server }
        file_server { index index.html }       <- canonical site copy

    The @am_edition_live matcher's `file { root ... }` existence check means a
    missing overlay falls through to the canonical `file_server` block at the
    tail — the visitor never sees a 404. Gate 2 names 200+noindex for the html
    and 401 for the json: both routes pass through that gate via the
    @open_html container.
    """
    caddy = CADDYFILE_PATH.read_text(encoding="utf-8")
    # The Caddyfile has TWO blocks named `open_html`: the @open_html matcher
    # (line 423) and the `handle @open_html { ... }` route body (line 428).
    # The AM-edition overlay lives inside the HANDLE's route body, not the
    # matcher's path list — gate 2's anonymous 200+noindex depends on the
    # overlay running through the gate, which is reached via the handle.
    open_html_handle = _handle_block(caddy, "open_html")
    assert "@am_edition_live" in open_html_handle, (
        "@am_edition_live matcher must live inside handle @open_html's route "
        "block, not at the site block's top level — gate 2's anonymous "
        "200+noindex depends on the overlay running through the gate"
    )
    # And it carries the file-existence fallback to the canonical site copy.
    assert "file {" in open_html_handle and "root /var/lib/macro-live/public" in open_html_handle
    assert re.search(
        r"@am_edition_live\s*\{[^}]*path\s+/am_edition\.html[^}]*\}",
        open_html_handle,
        flags=re.S,
    ), "@am_edition_live must match exactly path /am_edition.html"
    assert "Cache-Control" in open_html_handle and "no-store" in open_html_handle


def test_no_new_top_level_live_file_server() -> None:
    """B6: no new top-level /live/* file_server.

    The site block's top level already serves a tight, reviewed list of live
    artifacts via @vps_public_live (B1). A future edit that adds a top-level
    `handle /live/something.json { file_server }` would bypass the registration
    wall — the same widening the original security commentary on
    @vps_public_live warns against. The AM-edition lane is the exact shape that
    was at risk of regressing: this test pins the topology so the lane stays
    inside the existing auth route and never adds a sibling.
    """
    caddy = CADDYFILE_PATH.read_text(encoding="utf-8")
    # Top-level file_server with no enclosing matcher name is the dangerous shape.
    # We approximate by looking for `handle /live/...` or `handle /am_edition.*`
    # at indentation level 1 (a tab), as the file_server for the canonical
    # site/ copy at the open_html tail is also at indentation level 3 (route body).
    for path in re.finditer(r"^\thandle\s+/live/\S+", caddy, flags=re.M):
        # /live/quotes.json, /live/breadth.json, /live/release_publications.json,
        # /live/staleness.json are the four pre-existing fallbacks B1 documents;
        # any new /live/* here would widen the boundary.
        match = path.group(0).split()[-1]
        assert match in {
            "/live/quotes.json",
            "/live/breadth.json",
            "/live/release_publications.json",
            "/live/staleness.json",
        }, f"top-level `handle {match}` widens the static-access boundary"
    # And the AM-edition overlay must NEVER be served via a top-level handle.
    assert not re.search(r"^\thandle\s+/am_edition\.", caddy, flags=re.M), (
        "/am_edition.html / /am_edition.json must NOT have a top-level handle "
        "— both routes run inside handle @open_html's route block (the html) "
        "or behind @reg_asset (the json), so the gate and the registration "
        "wall still run"
    )
