"""Drift guards for the broad static-data access boundary.

PR #3393 originally protected only ``/factordata`` and ``/labdata``. The
default-deny boundary supersedes that narrow matcher: every non-public asset is
now registration- and entitlement-checked, while the two existing Terminal
ingest carve-outs stay explicit and public.
"""
from __future__ import annotations

from fnmatch import fnmatchcase
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CADDYFILE = REPO_ROOT / "app" / "deploy" / "Caddyfile"
POLICY_FILE = REPO_ROOT / "config" / "site_access.yml"

CARVEOUTS = {"/factordata/tech_lab.json", "/factordata/tech_events/*"}


def _read_caddyfile() -> str:
    return CADDYFILE.read_text(encoding="utf-8")


def _extract_block(text: str, header: str) -> str:
    pattern = re.compile(r"(?m)^[ \t]*" + re.escape(header) + r"[ \t]*\{")
    match = pattern.search(text)
    assert match is not None, f"block {header!r} missing"
    start = match.end() - 1
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"unbalanced block {header!r}")


def _path_tokens(block: str) -> set[str]:
    tokens: set[str] = set()
    for match in re.finditer(r"(?m)^[ \t]*(?:not )?path[ \t]+(.+)$", block):
        tokens.update(match.group(1).split())
    return tokens


def _public_policy_tokens() -> set[str]:
    policy = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    result = set(policy["public"]["exact"])
    result.update(prefix.rstrip("/") + "/*" for prefix in policy["public"]["prefixes"])
    return result


def test_shell_opt_in_cache_policy_is_independent_of_parent_framing_admission():
    """An unmatched parent must not prime a cache entry that denies the beta iframe."""
    text = _read_caddyfile()
    cache_selector = _extract_block(text, "@shared_shell_requested")
    assert _path_tokens(cache_selector) == {"/", "*.html"}
    assert "query mmx_shell=1" in cache_selector
    assert "Referer" not in cache_selector
    cache_headers = _extract_block(text, "header @shared_shell_requested")
    assert 'Cache-Control "private, no-store"' in cache_headers
    assert re.search(r"(?m)^\s*defer\s*$", cache_headers)
    frame_selector = _extract_block(text, "@shared_shell_document")
    assert "query mmx_shell=1" in frame_selector
    assert r"header_regexp Referer ^https://(beta|app)\.mastermind-x\.com/" in frame_selector


def test_broad_asset_matcher_protects_paid_json_and_keeps_only_carveouts_public():
    text = _read_caddyfile()
    exclusions = _path_tokens(_extract_block(text, "@reg_asset"))
    assert CARVEOUTS <= exclusions
    assert "/factordata/*" not in exclusions
    assert "/labdata/*" not in exclusions


def test_terminal_carveouts_match_reviewed_policy():
    text = _read_caddyfile()
    policy_public = _public_policy_tokens()
    public_block = _path_tokens(_extract_block(text, "@factordata_public"))
    assert public_block == CARVEOUTS
    assert CARVEOUTS <= policy_public


def test_broad_asset_handle_runs_both_auth_stages_and_is_private():
    block = _extract_block(_read_caddyfile(), "handle @reg_asset")
    assert "rewrite /api/regwall/check" in block
    assert "rewrite /api/paywall/check" in block
    assert "header_up X-Original-Kind asset" in block
    assert 'Cache-Control "private, no-store"' in block
    assert "file_server" in block


def test_broad_asset_error_branch_fails_closed():
    text = _read_caddyfile()
    block = _extract_block(text, "handle @reg_asset_err")
    assert "503" in block
    assert "private, no-store" in block
    assert "file_server" not in block
    assert "handle @reg_asset_err" in _extract_block(text, "handle_errors")


def test_shared_cache_headers_match_only_reviewed_public_paths():
    text = _read_caddyfile()
    policy_public = _public_policy_tokens()
    for matcher in ("@public_static", "@public_versioned", "@factordata_public"):
        assert _path_tokens(_extract_block(text, matcher)) <= policy_public
    assert re.search(r"(?m)^[ \t]*@static[ \t]*\{", text) is None
    assert re.search(r"(?m)^[ \t]*@versioned[ \t]*\{", text) is None
    assert re.search(r"(?m)^[ \t]*@reg_json[ \t]*\{", text) is None


def test_shared_shell_presentation_assets_are_exact_public_paths_in_all_edge_matchers():
    paths = {"/shared_shell_bridge.js", "/shared_shell.css"}
    policy = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    assert paths <= set(policy["public"]["exact"])
    text = _read_caddyfile()
    for matcher in ("@reg_asset", "@reg_asset_err", "@public_static", "@public_versioned"):
        assert paths <= _path_tokens(_extract_block(text, matcher))
    assert "not query v=*" in _extract_block(text, "@public_static")
    assert "query v=*" in _extract_block(text, "@public_versioned")


def test_public_pages_fetch_nothing_under_paid_prefixes():
    files = [
        REPO_ROOT / "templates" / "index.html",
        REPO_ROOT / "templates" / "plans.html.j2",
        REPO_ROOT / "templates" / "theme.js",
        REPO_ROOT / "templates" / "live.js",
        REPO_ROOT / "templates" / "onboard.js",
    ]
    target_re = re.compile(
        r"""(?:fetch\s*\(\s*|getJSON\s*\(\s*|\.src\s*=\s*)"""
        r"""['"`]([^'"`]+)['"`]"""
    )
    offenders = []
    for path in files:
        assert path.is_file(), f"public boundary file missing: {path}"
        for raw in target_re.findall(path.read_text(encoding="utf-8")):
            normalized = raw.split("?", 1)[0].split("#", 1)[0].lstrip("/")
            if normalized.startswith("./"):
                normalized = normalized[2:]
            if normalized.startswith(("factordata/", "labdata/")):
                offenders.append((path.name, raw))
    assert offenders == []


def test_html_documents_are_served_open_not_registration_gated():
    """HTML is open; the JSON/asset wall this module guards is what still gates.

    Was `test_html_registration_matcher_remains_present`, which asserted
    @reg_html carried `path *.html`. Operator 2026-08-04 opened every page shell
    to anonymous visitors, so that matcher is gone and asserting its presence
    would now pin the defect instead of the contract.

    The property that still matters here — and the one this module exists for —
    is the SPLIT: pages open, payloads gated. So assert both halves, because an
    @open_html check alone would still pass if someone widened it to serve the
    paid JSON too.
    """
    text = _read_caddyfile()
    # Pages: served by @open_html, with no account check in the path.
    assert re.search(r"(?m)^[ \t]*@open_html[ \t]*\{", text), "@open_html matcher missing"
    open_block = _extract_block(text, "@open_html")
    assert "path *.html" in open_block, "@open_html no longer claims *.html"
    assert re.search(r"(?m)^[ \t]*@reg_html[ \t]*\{", text) is None, (
        "@reg_html is back — HTML would be registration-gated again"
    )
    # ...and no account check inside the handler that serves them.
    open_handler = _extract_block(text, "handle @open_html")
    for wall in ("regwall/check", "paywall/check"):
        assert wall not in open_handler, f"@open_html routes pages through {wall}"
    # Payloads: the asset wall is untouched and still fail-closed.
    assert "rewrite /api/regwall/check" in _extract_block(text, "handle @reg_asset")


@pytest.mark.parametrize(("asset", "cache_matcher", "other_cache_matcher"), (
    ("/stock-dashboard.css", "@public_versioned", "@watchlist_shell_versioned"),
    ("/hk-stock-v36.js", "@watchlist_shell_versioned", "@public_versioned"),
    ("/canada-stock-v36.js", "@watchlist_shell_versioned", "@public_versioned"),
))
def test_hkca_shell_dependencies_are_public_with_stamp_aware_cache(
    asset, cache_matcher, other_cache_matcher
):
    """The three public shell files keep the cache lane implied by their stamp."""
    policy = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    assert policy["public"]["exact"].count(asset) == 1
    assert asset not in policy["free_registered"]["exact"]
    source = _read_caddyfile()
    for matcher in ("@reg_asset", "@reg_asset_err", "@public_static"):
        assert asset in _path_tokens(_extract_block(source, matcher)), matcher
    assert asset in _path_tokens(_extract_block(source, cache_matcher)), cache_matcher
    assert asset not in _path_tokens(_extract_block(source, other_cache_matcher)), (
        f"{asset} must not be served by both cache lanes"
    )


@pytest.mark.parametrize("payload", (
    "/factordata/hk_standouts.json", "/factordata/canada_standouts.json",
    "/hkstockdata/0700_HK.json", "/canadastockdata/ATRL_TO.json",
))
def test_hkca_shell_restoration_keeps_analytical_payloads_private(payload):
    """Opening presentation files never opens board or per-stock evidence."""
    source = _read_caddyfile()
    assert not any(fnmatchcase(payload, rule) for rule in _public_policy_tokens())
    for matcher in (
        "@reg_asset", "@reg_asset_err", "@public_static",
        "@public_versioned", "@watchlist_shell_versioned",
    ):
        rules = _path_tokens(_extract_block(source, matcher))
        assert not any(fnmatchcase(payload, rule) for rule in rules), matcher


def test_prophet_leader_observation_source_is_early_paid_and_pricing_disclosed():
    """The tier-preview wall is honest only when the raw ticker map cannot bypass it."""
    policy = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    source = "/anticipationdata/us_leader_pullback.json"

    assert source in policy["premium"]["enforced_early"]["exact"]
    assert source not in policy["public"]["exact"]
    assert source not in policy["free_registered"]["exact"]
    assert not any(
        source.startswith(prefix)
        for section in ("public", "free_registered")
        for prefix in policy[section]["prefixes"]
    )

    plans = (REPO_ROOT / "templates" / "plans.html.j2").read_text(
        encoding="utf-8"
    )
    assert "leaders waiting for entry" in plans
    assert "领涨股" in plans
    assert "1 before signup" in plans
    assert "3 / list / day" in plans
    assert "Full book" in plans


def test_international_workspace_assets_are_public_without_promoting_data():
    """The public HTML must load these exact ten presentation/controller files.

    Production answered 401 for them and left the workspace inert. No data or
    future asset family is included in this reviewed presentation-only change.
    """
    assets = {
        "/intl_workspace.css", "/intl_workspace_macro.css",
        "/intl_workspace_risk.css", "/intl_workspace_history.css",
        "/intl_workspace_state.js", "/intl_library_search.js",
        "/intl_workspace_scenario.js", "/intl_workspace.js",
        "/intl_workspace_entry.js", "/intl_workspace_surveillance.css",
    }
    public = _public_policy_tokens()
    assert {path for path in public if path.startswith("/intl")} == assets
    text = _read_caddyfile()
    protected = {"/intldata/latest.json", "/intl_research/private.json",
                 "/premiumdata/intl.json", "/intl_workspace_future.js"}
    for matcher in ("@reg_asset", "@reg_asset_err", "@public_static", "@public_versioned"):
        paths = _path_tokens(_extract_block(text, matcher))
        assert assets <= paths, matcher
        assert not any(fnmatchcase(path, pattern) for path in protected for pattern in paths)


def test_holding_research_code_assets_public_without_private_response_exemption():
    """The anonymous shell loads code; exact-row data stays on the paid API."""
    assets = {"/institutional_holding_research.js", "/institutional_holding_research.css"}
    policy = _public_policy_tokens()
    assert assets <= policy
    text = _read_caddyfile()
    for name in ("@reg_asset", "@reg_asset_err", "@public_static", "@public_versioned"):
        paths = _path_tokens(_extract_block(text, name))
        assert assets <= paths, name
    # Non-API protected paths: they must fail fnmatch against ALL FOUR serving
    # lists, including both registration exclusions as well as cache lanes.
    private_asset_paths = {
        "/institutional_holding_research.json",
        "/institutional_13f/holdings.parquet",
    }
    for path in private_asset_paths:
        assert not any(fnmatchcase(path, public) for public in policy), path
        for name in ("@reg_asset", "@reg_asset_err", "@public_static", "@public_versioned"):
            assert not any(fnmatchcase(path, public) for public in
                           _path_tokens(_extract_block(text, name))), (name, path)

    # The payload API is a different class: in @reg_asset/@reg_asset_err the
    # exact token ``/api/*`` is the intentional NON_POLICY reverse-proxy
    # exclusion (tests/test_site_access_boundary.py), not a public grant, so the
    # endpoint is never asserted against it. What must hold instead is that no
    # OTHER token admits it — no exact endpoint row, no narrower
    # /api/forensics* wildcard, no broad family promotion. The policy and the
    # two cache matchers carry no /api/* token, so there any admitting token is
    # a payload grant outright.
    api_paths = {"/api/forensics/v1/institutional/reported-holding"}
    for path in api_paths:
        assert not any(fnmatchcase(path, public) for public in policy), path
        for name in ("@public_static", "@public_versioned"):
            assert not any(fnmatchcase(path, public) for public in
                           _path_tokens(_extract_block(text, name))), (name, path)
        for name in ("@reg_asset", "@reg_asset_err"):
            admitted = [rule for rule in _path_tokens(_extract_block(text, name))
                        if fnmatchcase(path, rule)]
            assert set(admitted) <= {"/api/*"}, (
                name, [rule for rule in admitted if rule != "/api/*"])


def test_brain_visuals_assets_public_without_payload_or_family_promotion():
    """The chat widget's illustration pair is public; nothing else in its family is.

    /mm_brain_visuals.js and /mm_brain_visuals.css carry illustration code only;
    every response they render arrives through the Bearer-authenticated
    /api/brain/* gateway on the existing reverse proxy. This pins the pair
    exactly and refuses the promotions that would look equivalent: an adjacent
    private JSON/data/source-map/variant file, a family wildcard, and any Brain
    API endpoint or prefix in a public list.

    API negatives follow the /api/* rule: in the two wall matchers the exact
    token ``/api/*`` is the intentional NON_POLICY proxy exclusion, so the test
    asks which OTHER token admits the endpoint — it never asserts that the
    endpoint fails fnmatch against ``/api/*`` itself.
    """
    assets = {"/mm_brain_visuals.js", "/mm_brain_visuals.css"}
    text = _read_caddyfile()
    policy = _public_policy_tokens()
    matchers = ("@reg_asset", "@reg_asset_err", "@public_static", "@public_versioned")
    matcher_tokens = {
        name: _path_tokens(_extract_block(text, name)) for name in matchers
    }

    # Exactly the two reviewed presentation files, in policy and every matcher.
    assert {path for path in policy if "mm_brain_visuals" in path} == assets
    for name, tokens in matcher_tokens.items():
        assert {path for path in tokens if "mm_brain_visuals" in path} == assets, name

    # Adjacent private/derived/future family files are NOT API: they must fail
    # fnmatch against the public policy and ALL FOUR lists.
    private_family = {
        "/mm_brain_visuals.json", "/mm_brain_visuals/private.json",
        "/mm_brain_visuals.js.map", "/mm_brain_visuals_private.js",
        "/mm_brain_visuals_future.js",
    }
    for path in private_family:
        assert not any(fnmatchcase(path, rule) for rule in policy), path
        for name, tokens in matcher_tokens.items():
            assert not any(fnmatchcase(path, rule) for rule in tokens), (name, path)

    # The payload plane: a Brain endpoint may be admitted only by the wall
    # matchers' intentional /api/* proxy token, and by nothing anywhere else.
    endpoint = "/api/brain/threads"
    assert not any(fnmatchcase(endpoint, rule) for rule in policy), endpoint
    prefixes = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))["public"]["prefixes"]
    assert not any(endpoint.startswith(prefix.rstrip("/") + "/") for prefix in prefixes), (
        "a public policy prefix admits the Brain API"
    )
    for name in ("@public_static", "@public_versioned"):
        assert not any(fnmatchcase(endpoint, rule) for rule in matcher_tokens[name]), name
    for name in ("@reg_asset", "@reg_asset_err"):
        admitted = [rule for rule in matcher_tokens[name] if fnmatchcase(endpoint, rule)]
        assert set(admitted) <= {"/api/*"}, (
            name, [rule for rule in admitted if rule != "/api/*"])
