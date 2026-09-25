"""Self-tests for the production Caddy topology guard over ``/api/hub/prophet``
(``scripts/check_caddy_hub_boundary.py``, B1 Day-6 AMENDMENT clause F,
DEC:B1-PROPHET-PUBLIC-SPLIT).

``_hub_prophet_authorized`` (app/prophet_lab.py) denies the internal-only hub
route unless the caller is loopback AND carries no ``X-MM-Peer`` header. That
guard is only as good as the topology fact it relies on: every edge-facing
``reverse_proxy ... 127.0.0.1:8000`` block either stamps ``X-MM-Peer`` (so a
public request always carries it) or rewrites the caller's path to something
fixed and non-hub (so the caller's own path can never select the hub route).
These tests prove the shipped Caddyfile satisfies that today, prove the
checker actually REJECTS the shape clause F is worried about (a bare, unstamped
``reverse_proxy ... 127.0.0.1:8000`` — the "future generic block" that could
otherwise silently bypass the hub guard), and tie the classification directly
to the real ``_hub_prophet_authorized`` property it depends on.

Run: python -m pytest tests/test_caddy_hub_boundary.py -q
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.check_caddy_hub_boundary import (
    REPO_ROOT,
    SAFE_FIXED_REWRITE,
    SAFE_PEER_STAMPED,
    UNSAFE,
    classify_backend_proxies,
)

CADDYFILE_PATH = REPO_ROOT / "app" / "deploy" / "Caddyfile"


# ---------------------------------------------------------------------------
# The shipped production Caddyfile — must classify all-safe, and the exact
# proxy COUNT is pinned so a silently-dropped block is caught rather than
# passing vacuously.
# ---------------------------------------------------------------------------
def test_shipped_caddyfile_has_exactly_seven_backend_proxies_all_safe() -> None:
    text = CADDYFILE_PATH.read_text(encoding="utf-8")
    proxies = classify_backend_proxies(text)

    assert len(proxies) == 7, (
        f"expected exactly 7 :8000 backend reverse_proxy blocks, found {len(proxies)}: {proxies}\n"
        "If this is a deliberate topology change, update the pinned count here — do not just "
        "delete the assertion, that is exactly the vacuous pass clause F exists to prevent."
    )
    unsafe = [p for p in proxies if p.classification == UNSAFE]
    assert unsafe == [], f"shipped Caddyfile has UNSAFE backend proxy block(s): {unsafe}"

    peer_stamped = [p for p in proxies if p.classification == SAFE_PEER_STAMPED]
    fixed_rewrite = [p for p in proxies if p.classification == SAFE_FIXED_REWRITE]
    assert len(peer_stamped) == 2, peer_stamped
    assert len(fixed_rewrite) == 5, fixed_rewrite
    assert len(peer_stamped) + len(fixed_rewrite) == 7


def test_shipped_caddyfile_line_numbers_match_known_blocks() -> None:
    """Pins WHICH lines classify which way, so a future edit that moves a
    block without preserving its safety property shows up as a line-number
    diff a reviewer will actually look at.

    A-MOR-2b lane B inserted the @am_edition_live overlay handle inside
    handle @open_html's route block — that pushed the last reverse_proxy at
    line 772 down to line 793. The proxy COUNT (7) and the OTHER six lines
    (121, 146, 350, 359, 392, 430) are unchanged; the topology guard itself
    is unchanged. If you find yourself changing a count or classification
    here, you almost certainly widened the static-access boundary — read
    the @open_html route block commentary before doing that."""
    text = CADDYFILE_PATH.read_text(encoding="utf-8")
    proxies = {p.line: p.classification for p in classify_backend_proxies(text)}
    assert proxies == {
        121: SAFE_PEER_STAMPED,
        146: SAFE_PEER_STAMPED,
        350: SAFE_FIXED_REWRITE,
        359: SAFE_FIXED_REWRITE,
        392: SAFE_FIXED_REWRITE,
        430: SAFE_FIXED_REWRITE,
        793: SAFE_FIXED_REWRITE,
    }


# ---------------------------------------------------------------------------
# NON-VACUITY / mutation tests — the checker must actually be able to fail.
# ---------------------------------------------------------------------------
def test_generic_unstamped_block_is_rejected_unsafe() -> None:
    """This is exactly clause F's worry: 'a future generic reverse_proxy
    :8000 block cannot silently bypass the hub guard'."""
    caddy = (
        "example.com {\n"
        "\treverse_proxy /* 127.0.0.1:8000 {\n"
        "\t}\n"
        "}\n"
    )
    proxies = classify_backend_proxies(caddy)
    assert len(proxies) == 1
    assert proxies[0].classification == UNSAFE
    assert proxies[0].reasons


def test_placeholder_rewrite_does_not_count_as_a_fixed_rewrite() -> None:
    """A `rewrite` whose target is a placeholder re-emits the CALLER's path, so
    the caller still selects the upstream route. Accepting it as
    SAFE_FIXED_REWRITE would be a silent bypass of the hub guard — the exact
    thing clause F asks this check to make impossible."""
    for target in ("{http.request.uri}", "{path}", "{uri}"):
        caddy = (
            "example.com {\n"
            "\treverse_proxy /* 127.0.0.1:8000 {\n"
            f"\t\trewrite {target}\n"
            "\t}\n"
            "}\n"
        )
        proxies = classify_backend_proxies(caddy)
        assert len(proxies) == 1, target
        assert proxies[0].classification == UNSAFE, target
        assert proxies[0].reasons, target


def test_a_peer_stamp_still_saves_a_block_that_also_has_a_placeholder_rewrite() -> None:
    """The peer stamp alone is sufficient: the request arrives at :8000 carrying
    X-MM-Peer, so `_hub_prophet_authorized` denies it whatever the path is."""
    caddy = (
        "example.com {\n"
        "\treverse_proxy /* 127.0.0.1:8000 {\n"
        "\t\trewrite {http.request.uri}\n"
        "\t\theader_up X-MM-Peer {remote_host}\n"
        "\t}\n"
        "}\n"
    )
    proxies = classify_backend_proxies(caddy)
    assert len(proxies) == 1
    assert proxies[0].classification == SAFE_PEER_STAMPED


def test_bare_directive_with_no_block_at_all_is_rejected_unsafe() -> None:
    caddy = (
        "example.com {\n"
        "\treverse_proxy 127.0.0.1:8000\n"
        "}\n"
    )
    proxies = classify_backend_proxies(caddy)
    assert len(proxies) == 1
    assert proxies[0].classification == UNSAFE
    assert proxies[0].has_header_up_peer is False
    assert proxies[0].rewrite_targets == ()


def test_rewrite_into_the_hub_path_is_rejected_even_though_it_has_a_rewrite() -> None:
    caddy = (
        "example.com {\n"
        "\treverse_proxy /leak/* 127.0.0.1:8000 {\n"
        "\t\tmethod GET\n"
        "\t\trewrite /api/hub/prophet\n"
        "\t}\n"
        "}\n"
    )
    proxies = classify_backend_proxies(caddy)
    assert len(proxies) == 1
    p = proxies[0]
    assert p.classification == UNSAFE
    assert p.rewrite_targets == ("/api/hub/prophet",)
    assert any("/api/hub/" in r for r in p.reasons)


def test_rewrite_into_the_hub_path_is_unsafe_even_with_a_peer_stamp_present() -> None:
    """The 'additionally FAIL' clause is unconditional — belt-and-suspenders
    even for a block that also stamps the peer header."""
    caddy = (
        "example.com {\n"
        "\treverse_proxy /weird/* 127.0.0.1:8000 {\n"
        "\t\trewrite /api/hub/prophet\n"
        "\t\theader_up X-MM-Peer {remote_host}\n"
        "\t}\n"
        "}\n"
    )
    proxies = classify_backend_proxies(caddy)
    assert proxies[0].classification == UNSAFE


# ---------------------------------------------------------------------------
# Sanctioned shapes pass.
# ---------------------------------------------------------------------------
def test_peer_stamped_block_passes() -> None:
    caddy = (
        "example.com {\n"
        "\treverse_proxy /api/* 127.0.0.1:8000 {\n"
        "\t\theader_up X-MM-Peer {remote_host}\n"
        "\t}\n"
        "}\n"
    )
    proxies = classify_backend_proxies(caddy)
    assert proxies[0].classification == SAFE_PEER_STAMPED


def test_fixed_rewrite_block_passes() -> None:
    caddy = (
        "example.com {\n"
        "\treverse_proxy /gate/* 127.0.0.1:8000 {\n"
        "\t\tmethod GET\n"
        "\t\trewrite /api/gate/check\n"
        "\t}\n"
        "}\n"
    )
    proxies = classify_backend_proxies(caddy)
    assert proxies[0].classification == SAFE_FIXED_REWRITE


def test_localhost_and_ipv6_loopback_hosts_are_also_recognized() -> None:
    caddy = (
        "example.com {\n"
        "\treverse_proxy /a/* localhost:8000 {\n"
        "\t\theader_up X-MM-Peer {remote_host}\n"
        "\t}\n"
        "\treverse_proxy /b/* [::1]:8000 {\n"
        "\t\theader_up X-MM-Peer {remote_host}\n"
        "\t}\n"
        "}\n"
    )
    proxies = classify_backend_proxies(caddy)
    assert len(proxies) == 2
    assert all(p.classification == SAFE_PEER_STAMPED for p in proxies)


def test_a_non_backend_reverse_proxy_is_not_counted() -> None:
    """A reverse_proxy to some other port/host must not pollute the count —
    only :8000 loopback targets are this route's backend."""
    caddy = (
        "example.com {\n"
        "\treverse_proxy /admin/* 127.0.0.1:8787 {\n"
        "\t\theader_up X-Admin-Client-IP {remote_host}\n"
        "\t}\n"
        "}\n"
    )
    proxies = classify_backend_proxies(caddy)
    assert proxies == []


def test_nested_braces_inside_a_block_do_not_break_block_boundary_detection() -> None:
    """handle_response {}-nesting inside a real reverse_proxy block (as seen
    in the shipped Caddyfile's regwall/paywall/gate blocks) must not fool the
    brace-depth scan into closing the block early or late."""
    caddy = (
        "example.com {\n"
        "\treverse_proxy 127.0.0.1:8000 {\n"
        "\t\tmethod GET\n"
        "\t\trewrite /api/regwall/check\n"
        "\t\t@rallow status 2xx\n"
        "\t\thandle_response @rallow {\n"
        "\t\t}\n"
        "\t}\n"
        "\treverse_proxy /elsewhere/* 127.0.0.1:9999\n"
        "}\n"
    )
    proxies = classify_backend_proxies(caddy)
    assert len(proxies) == 1
    assert proxies[0].classification == SAFE_FIXED_REWRITE
    assert proxies[0].rewrite_targets == ("/api/regwall/check",)


# ---------------------------------------------------------------------------
# main() exit-code contract.
# ---------------------------------------------------------------------------
def test_main_exits_zero_on_the_shipped_caddyfile() -> None:
    from scripts.check_caddy_hub_boundary import main

    assert main(["--root", str(REPO_ROOT)]) == 0


def test_main_exits_nonzero_on_a_synthetic_unsafe_caddyfile(tmp_path: Path) -> None:
    from scripts.check_caddy_hub_boundary import main

    caddy_path = tmp_path / "Caddyfile"
    caddy_path.write_text(
        "example.com {\n\treverse_proxy /* 127.0.0.1:8000 {\n\t}\n}\n",
        encoding="utf-8",
    )
    assert main(["--caddyfile", str(caddy_path)]) == 1


def test_main_exits_nonzero_when_no_backend_proxies_are_found(tmp_path: Path) -> None:
    """A silently-emptied Caddyfile must not pass vacuously."""
    from scripts.check_caddy_hub_boundary import main

    caddy_path = tmp_path / "Caddyfile"
    caddy_path.write_text("example.com {\n\trespond \"hi\"\n}\n", encoding="utf-8")
    assert main(["--caddyfile", str(caddy_path)]) == 1


# ---------------------------------------------------------------------------
# Tie the topology guard to the REAL app-level property it depends on:
# loopback peer + absent X-MM-Peer is denied by _hub_prophet_authorized.
# Same request-stub style as tests/test_prophet_lab_api.py.
# ---------------------------------------------------------------------------
fastapi = pytest.importorskip("fastapi", reason="prophet_lab guard tests need fastapi")
pytest.importorskip("starlette", reason="prophet_lab guard tests need starlette")

from starlette.requests import Request  # noqa: E402

import app.prophet_lab as prophet_lab_api  # noqa: E402


def _hub_request(*, client_host: str | None, headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/hub/prophet",
        "raw_path": b"/api/hub/prophet",
        "query_string": b"",
        "headers": [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in (headers or {}).items()
        ],
        "client": (client_host, 51000) if client_host is not None else None,
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
    }
    return Request(scope)


def test_loopback_peer_carrying_the_edge_stamped_header_is_denied() -> None:
    """This is the property the whole Caddy topology guard exists to protect:
    a request that looks loopback but carries X-MM-Peer (i.e. it came through
    the /api/* proxy, which ALWAYS stamps that header) must be denied, even
    though the bare TCP peer alone cannot tell it apart from a direct call."""
    request = _hub_request(client_host="127.0.0.1", headers={"x-mm-peer": "203.0.113.7"})
    assert prophet_lab_api._hub_prophet_authorized(request) is False  # noqa: SLF001


def test_loopback_peer_with_no_peer_header_is_authorized() -> None:
    request = _hub_request(client_host="127.0.0.1")
    assert prophet_lab_api._hub_prophet_authorized(request) is True  # noqa: SLF001


def test_ontology_trace_assets_are_static_only_and_cannot_select_a_backend() -> None:
    """F04-X1 asset admission must not touch the proxy topology this file guards.

    ``/ontology.css`` and ``/ontology.js`` were added to four path matchers so a
    logged-out visitor can render the shell. That is a STATIC concern; if either
    literal ever appeared inside a ``reverse_proxy``/``rewrite`` block it would
    become a caller-controlled path into the backend, which is exactly the shape
    ``_hub_prophet_authorized`` depends on never existing.
    """
    caddy = CADDYFILE_PATH.read_text(encoding="utf-8")
    assert "/ontology.css" in caddy and "/ontology.js" in caddy

    for block in re.findall(r"(reverse_proxy[^\n]*\{.*?^\s*\}|rewrite[^\n]*)", caddy, flags=re.S | re.M):
        assert "/ontology." not in block, f"ontology asset leaked into a proxy/rewrite block: {block[:120]}"

    # And the topology itself is unchanged by the admission.
    proxies = classify_backend_proxies(caddy)
    assert len(proxies) == 7
    assert not [p for p in proxies if p.classification == UNSAFE]


# ---------------------------------------------------------------------------
# A-MOR-2b lane B — AM Edition premarket overlay. The lane writes
# `/var/lib/macro-live/public/am_edition.{json,html}` from a VPS-side oneshot;
# Caddy is the only place that decides whether anonymous bytes flow. This
# block pins the boundary contracts the spec names (B4, B6) so a future edit
# cannot silently widen the static-access boundary — particularly the trap
# that adding /am_edition.json to @vps_public_live would create (it would let
# anonymous callers read the registered asset without paying the wall).
# ---------------------------------------------------------------------------

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
