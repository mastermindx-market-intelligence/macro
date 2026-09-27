"""tests/test_ontology_explorer_shell.py — F04-X1 public shell (RED first).

`site/ontology.html` and its paired assets are served publicly by Caddy. They are
the discoverable entry point, so they must be able to describe the product
without containing a single current owner reading — no inlined snapshot, no
bootstrapped JSON, no commented-out sample, no source map.

The failure this guards against is mundane and common: a builder that renders a
"realistic" example into the static shell so the page looks alive before the
fetch resolves. That example is a current premium value published to a public
host.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "ontology.html.j2"
PAGE = ROOT / "site" / "ontology.html"
PAIRS = (("templates/ontology.css", "site/ontology.css"),
         ("templates/ontology.js", "site/ontology.js"))


def _built_page() -> str:
    if not PAGE.exists():
        pytest.fail("site/ontology.html has not been built by "
                    "scripts/build_ontology_explorer.py")
    return PAGE.read_text(encoding="utf-8")


def test_the_public_shell_is_built(tmp_path):
    assert _built_page().lstrip().lower().startswith("<!doctype html")


def test_the_paired_plain_copy_assets_match_byte_for_byte():
    """House law: a non-.j2 templates/<name> that also ships as site/<name> must
    be byte-identical in the same commit."""
    for template_rel, site_rel in PAIRS:
        template, site = ROOT / template_rel, ROOT / site_rel
        assert template.exists(), f"{template_rel} missing"
        assert site.exists(), f"{site_rel} missing"
        assert template.read_bytes() == site.read_bytes(), (
            f"{template_rel} and {site_rel} have drifted; "
            "run python -m scripts.check_template_site_sync --fix")


def test_the_public_shell_contains_no_current_owner_reading():
    """Every number the researcher sees must have arrived over the authenticated
    API. Nothing that looks like a receipt may be baked into the static file."""
    page = _built_page()
    forbidden = (
        "chain_state", "value_receipt", "base_rate", "p_confirm",
        "ontology_explorer_snapshot", "source_manifest_hash",
        "first_blocking_leg", "duration_derate", "breakeven_rise",
        "T10YIE", "CL=F", "QQQ", "SPY",
    )
    for token in forbidden:
        assert token not in page, f"public shell leaks {token!r}"


def test_the_public_shell_inlines_no_json_payload():
    page = _built_page()
    for match in re.finditer(r"<script[^>]*>(.*?)</script>", page, re.S | re.I):
        body = match.group(1).strip()
        if not body:
            continue
        try:
            parsed = json.loads(body)
        except (ValueError, TypeError):
            continue
        assert not isinstance(parsed, dict) or "schema" not in parsed, (
            "a snapshot-shaped JSON payload is inlined into the public shell")


def test_the_public_shell_ships_no_source_map():
    page = _built_page()
    assert "sourceMappingURL" not in page
    for _template_rel, site_rel in PAIRS:
        path = ROOT / site_rel
        if path.exists():
            assert "sourceMappingURL" not in path.read_text(encoding="utf-8")
    assert not list((ROOT / "site").glob("ontology*.map"))


def test_the_client_persists_no_snapshot_in_browser_storage():
    """`private, no-store` on the wire is undone the moment the client writes the
    body into localStorage, IndexedDB or the Cache API."""
    script = ROOT / "site" / "ontology.js"
    if not script.exists():
        pytest.fail("site/ontology.js has not been written")
    body = script.read_text(encoding="utf-8")
    for api in ("localStorage", "sessionStorage", "indexedDB",
                "caches.open", "CacheStorage"):
        assert api not in body, f"the client persists the snapshot via {api}"


def test_the_client_requests_the_frozen_route_with_no_store():
    body = (ROOT / "site" / "ontology.js").read_text(encoding="utf-8")
    assert "/api/ontology/explorer/v1" in body
    assert "no-store" in body


def test_no_current_snapshot_is_committed_under_tracked_premium_paths():
    for candidate in (ROOT / "site" / "premiumdata").glob("ontology*"):
        pytest.fail(f"a current snapshot is committed publicly at {candidate}")


def test_every_internal_link_this_feature_adds_resolves():
    """A dead internal link is not a cosmetic defect here.

    The site publish walks links, and one 404 has previously frozen the whole
    publish rather than degrading the single page that carried it. This feature
    adds links from both the shell and the client, so both are checked.
    """
    sources = [PAGE.read_text(encoding="utf-8") if PAGE.exists() else "",
               (ROOT / "site" / "ontology.js").read_text(encoding="utf-8")]
    hrefs = set()
    for text in sources:
        hrefs.update(re.findall(r'["\'](/[a-zA-Z0-9_./-]+\.html)(?:[?#][^"\']*)?["\']', text))
        hrefs.update(re.findall(r'href="(?!https?:|//|#|mailto:)([a-zA-Z0-9_./-]+\.html)',
                                text))
    missing = sorted(h for h in hrefs
                     if not (ROOT / "site" / h.lstrip("/")).exists())
    assert missing == [], f"dead internal link(s) added by this feature: {missing}"


def test_the_builder_exposes_an_entry_point_the_site_build_can_call(tmp_path):
    """Stage B's hunk in scripts/build_site.py must be one self-contained block.
    If the only entry point were `main()`, the site build would have to stand up
    a second Jinja environment with its own autoescape settings — one page
    rendered by two differently-configured environments is how escaping drifts
    between the nightly build and a manual one."""
    from jinja2 import Environment, FileSystemLoader
    from scripts.build_ontology_explorer import PAGE, PAIRED_ASSETS, build_shell

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    site = tmp_path / "site"
    build_shell(env, site)

    assert (site / PAGE).exists()
    for name in PAIRED_ASSETS:
        assert (site / name).read_bytes() == (
            ROOT / "templates" / name).read_bytes()


def test_the_committed_page_matches_the_current_template_render():
    """site/ontology.html is a hand-committed render: scripts/build_ontology_
    explorer.py is a standalone builder (deliberately not wired into
    scripts/build_site.py's Stage B yet), and check_template_site_sync.py only
    guards the non-.j2 paired assets (ontology.css/js) -- the .j2 -> site/
    render itself can drift silently while the VPS keeps serving the stale
    copy. This is the drift guard until Stage B lands: it fails the moment
    templates/ontology.html.j2 changes without a matching
    `python -m scripts.build_ontology_explorer` re-run and commit."""
    import tempfile
    from jinja2 import Environment, FileSystemLoader
    from scripts.build_ontology_explorer import build_shell

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp)
        build_shell(env, site)
        rendered = (site / "ontology.html").read_bytes()
    assert _without_lane_owned_asset_markup(rendered) == \
        _without_lane_owned_asset_markup(PAGE.read_bytes()), (
        "site/ontology.html is stale -- re-run "
        "`python -m scripts.build_ontology_explorer` and commit the result")


_STAMP = re.compile(rb"\?v=[0-9a-f]{6,16}")
_PRELOAD_LINE = re.compile(rb"^[ \t]*<link rel=\"preload\" as=\"style\" [^\n]*\n", re.M)
_DEFER = re.compile(rb"(<script src=\"[^\"]+\") defer(></script>)")
# Same shape as `_WHB_TAG_RE` in scripts/build_free_content.py: daily.yml's
# scripts/inject_wh_banner.py splices this one tag before </body> of every page.
_WHB_TAG = re.compile(rb"[ \t]*<script[^>]*\bdata-whb\b[^>]*></script>\n?")


def _without_lane_owned_asset_markup(page: bytes) -> bytes:
    """Strip what the render-public re-stamp lane (scripts/optimize_assets,
    idempotent shim/externalize/stamp chain) adds AFTER a page is committed:
    ``?v=<hash>`` stamps, ``<link rel="preload" as="style">`` hints and the
    ``defer`` it puts on the shared scripts. The 2026-09-24 F04-X1 merge
    (ac61896d) committed the builder's plain render; the lane's next tick
    (64b18613, ``render-public: public pages + asset stamps``) rewrote the
    committed bytes, and this guard -- a raw byte comparison -- went red on
    main with no template change behind it. The template drift it exists to
    catch (markup, copy, structure) survives the normalisation; only the
    lane-owned asset markup is ignored.

    The nightly owns one more tag: daily.yml's inject_wh_banner sweep adds the
    alert-banner ``<script defer data-whb ...>`` to every committed page, and
    no builder emits it. Its first pass over this page (a374fd96, 2026-09-25
    ``engine: regime update``) turned this guard red on main the same way."""
    page = _WHB_TAG.sub(b"", page)
    page = _STAMP.sub(b"", page)
    page = _PRELOAD_LINE.sub(b"", page)
    page = _DEFER.sub(rb"\1\2", page)
    return page


def test_a_missing_paired_asset_raises_instead_of_reporting_success(tmp_path,
                                                                    monkeypatch):
    """The site build wraps every page in an additive try/except, so a raise is
    what that pattern expects. Returning quietly would let a page ship without
    its stylesheet and still count as a successful build."""
    import scripts.build_ontology_explorer as builder
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    monkeypatch.setattr(builder, "PAIRED_ASSETS", ("ontology.css", "not-a-real-asset.js"))
    with pytest.raises(FileNotFoundError, match="not-a-real-asset.js"):
        builder.build_shell(env, tmp_path / "site")


def test_the_client_uses_the_house_sign_in_return_convention():
    """A bare `/?signin=1` strands a reader who came for one specific trace: the
    house wall carries `&ret=<root-relative path>`, consumed by onboard.js's
    retTarget(), which accepts same-origin "/..." only. The bounce is this
    page's, so the return is this page's responsibility."""
    client = (ROOT / "templates" / "ontology.js").read_text(encoding="utf-8")
    assert "signin=1&ret=" in client
    assert "encodeURIComponent" in client
    # the guard retTarget() applies, mirrored on our side before we hand it over
    assert 'path.slice(0, 2) !== "//"' in client
    # and never the bare form, which is the regression this pins
    assert '"/?signin=1"' not in client


def test_the_canonical_transmission_continuation_is_offered_in_every_state():
    """It used to be reachable only from the one action branch that fires when
    nothing blocks and nothing is unobserved — a rare case — leaving the ordinary
    reader with the link present solely inside <noscript>, which is exactly where
    a reader who can see the page never looks."""
    client = (ROOT / "templates" / "ontology.js").read_text(encoding="utf-8")
    assert "function transmissionLink(" in client
    # called on the focus_leg branch too, not only the fallback branch
    assert client.count("transmissionLink(") >= 2
    assert (ROOT / "site" / "transmission.html").exists(), (
        "the continuation must point at a page that exists")


def test_every_continuation_link_carries_path_step_source_context():
    """M1 acceptance item 5: security/theme continuation preserves the
    selected path / step / source context. A bare `transmission.html` href
    loses the focused step the reader arrived from; the transmission surface
    would then have to recover that context from somewhere it does not have.
    Pin that every transmission.html href in the rendered DOM carries the
    `from=<chain identifier>` / `focus=<next_action.target, else
    first_blocking_leg.node_id>` / `rev=<source.rev>` query string the
    snapshot supplies."""
    # Pin shape: there must be NO bare `transmission.html` href assignment
    # anywhere in the client (no `a.href = "transmission.html"`, no
    # `link.href = "transmission.html"`).
    client = (ROOT / "templates" / "ontology.js").read_text(encoding="utf-8")
    bare_literal = re.findall(
        r'(?:a|link)\.href\s*=\s*"transmission\.html"', client)
    assert not bare_literal, (
        "every transmission.html link must carry path/step/source context: "
        f"found bare assignments {bare_literal!r}")
    # And the continuation helper must read every context field the snapshot
    # exposes (so a future rebuild of the snapshot keeps the link honest).
    # Bound the body by the helper's own opening/closing braces: the function
    # sits at indent 2, and the matching closing brace is the FIRST `^  }`
    # AFTER its opening `{`.
    helper_open = re.search(
        r"function\s+continuationHref\([^)]*\)\s*\{", client)
    assert helper_open, "continuationHref(snapshot) helper must exist"
    body = client[helper_open.end():]
    body = re.match(r"(.*?)^\s\s\}", body, re.S | re.M).group(1)
    for field in ("source", "chain", "next_action", "target", "rev"):
        assert field in body, (
            f"continuationHref must read snapshot.{field!r} to carry context "
            "(M1 acceptance item 5)")
    # `from` is the chain identifier (`source.chain`), NOT the chain's first
    # node slug (`path.sequence[0]`); the body documents it as `<chain>`.
    assert "sequence" not in body, (
        "continuationHref uses path.sequence[0] (a node slug) as `from`; "
        "use source.chain (the chain identifier) instead")


def test_continuation_focus_follows_next_action_target_not_blocking_leg():
    """A chain can have a first_blocking_leg AND a different next_action.target
    (e.g. an unobserved downstream leg the page just opened, or the confirmed
    leg after a contradiction). `focus=` must follow the step the page LAST
    focused — the next_action target — not the first blocking leg whenever one
    exists, which can be a different step than the control just opened."""
    client = (ROOT / "templates" / "ontology.js").read_text(encoding="utf-8")
    helper_open = re.search(
        r"function\s+continuationHref\([^)]*\)\s*\{", client)
    assert helper_open, "continuationHref(snapshot) helper must exist"
    body = client[helper_open.end():]
    body = re.match(r"(.*?)^\s\s\}", body, re.S | re.M).group(1)
    # The focus assignment must read `next_action.target` FIRST, then fall back
    # to first_blocking_leg.node_id. The order is the source-of-truth here.
    action_pos = body.find("next_action")
    blocking_pos = body.find("first_blocking_leg")
    assert action_pos != -1 and blocking_pos != -1, (
        "continuationHref must consult both next_action and first_blocking_leg")
    assert action_pos < blocking_pos, (
        "next_action.target must be the primary focus source; "
        "first_blocking_leg is the fallback only")


def test_every_blocking_reason_the_composer_emits_has_its_own_sentence():
    """The client's else-branch narrated not_resolved / not_judged / not_readable
    as "condition is not met", converting "we could not judge this" into a market
    verdict on the customer surface — the same collapse the composer refuses
    upstream. Every reason it can emit must be said as what it is."""
    import inspect
    from engine import ontology_explorer

    source = inspect.getsource(ontology_explorer._first_blocking_leg)
    emitted = set(re.findall(r'"(condition_false|not_\w+)"', source))
    assert emitted, "the reason vocabulary must be discoverable from the composer"

    client = (ROOT / "templates" / "ontology.js").read_text(encoding="utf-8")
    handled = set(re.findall(r"^\s{4}(\w+): function \(\)", client, re.M))
    missing = emitted - handled
    assert not missing, f"blocking reasons with no sentence of their own: {sorted(missing)}"
    # and none of them may be phrased as a false condition unless it IS one
    assert "condition_false" in handled


def test_blocking_reason_sentences_are_factories_not_shared_fragments():
    """A DocumentFragment empties when appended, so a shared one renders once and
    then inserts nothing on every later render."""
    client = (ROOT / "templates" / "ontology.js").read_text(encoding="utf-8")
    block = client.split("var BLOCKING_REASON = {", 1)[1].split("};", 1)[0]
    assert "function ()" in block
    assert re.search(r"^\s{4}\w+: say\(", block, re.M) is None


def test_every_engine_gap_kind_has_a_reader_facing_sentence():
    """M1 acceptance item 4 + plain-language law. The composer is the source
    of truth for gap kinds (engine/ontology_explorer.py); this client ships a
    GAP_TEXT map that names each one. A kind the composer emits without a
    GAP_TEXT entry falls through to a raw-slug rendering (e.g. 'clock absent'),
    which is the failure this test pins shut.

    Discovered by `grep -n 'gaps.append({"kind":' engine/ontology_explorer.py`
    — every value that appears as a kind literal there must have an entry in
    GAP_TEXT; nothing in GAP_TEXT may be a kind the composer never emits
    (those are dead keys, kept out of the artifact)."""
    import inspect
    from engine import ontology_explorer

    engine_src = inspect.getsource(ontology_explorer)
    # Some kinds are passed via a local `kind` variable in a loop:
    #   for count, kind in ((foreign, "transitions_from_another_revision"), ...):
    #       if count: gaps.append({"kind": kind, "count": count})
    # Capture those literal strings too, so the parity test pins EVERY kind
    # the composer can emit (literal or via a loop variable).
    emitted_literal = set(re.findall(r'\{"kind":\s*"([^"]+)"', engine_src))
    emitted_loop = set(re.findall(
        r'\(\s*\w+\s*,\s*"(transitions_\w+)"\s*\)', engine_src))
    emitted = sorted(emitted_literal | emitted_loop)
    assert emitted, "the composer's gap kind vocabulary must be discoverable"

    client = (ROOT / "templates" / "ontology.js").read_text(encoding="utf-8")
    block = client.split("var GAP_TEXT = {", 1)[1].split("};", 1)[0]
    listed = sorted(set(re.findall(r"^\s{4}(\w+):\s*\{", block, re.M)))

    missing = sorted(set(emitted) - set(listed))
    dead = sorted(set(listed) - set(emitted))
    assert not missing, (
        "engine emits these gap kinds without a GAP_TEXT sentence: "
        f"{missing}; the page would render them as raw slugs")
    assert not dead, (
        f"GAP_TEXT entries the engine never emits (dead keys): {dead}; "
        "remove them or the test that pins parity will silently miss a kind")


def test_receipts_and_watched_render_as_bilingual_sentences_without_undefined():
    """M1 acceptance item 4 (plain-language law): the client must not concatenate
    raw owner receipt fields into a single textContent string, where a missing
    field printed as `undefined`, a study slug like `ret_bp` reached the reader,
    and EN/ZH fell back to the same concatenated raw string. Pin shape: there
    must be NO `receipt.series + ` style concatenation inside `renderLegDetail`,
    and there must be bilingual helper functions `receiptLabel`, `receiptValue`
    and `watchedSentence` that the loop calls instead."""
    client = (ROOT / "templates" / "ontology.js").read_text(encoding="utf-8")
    # Pin: the old concatenation shape must not be present
    assert "receipt.series +" not in client, (
        "the client still concatenates raw receipt fields; receiptLabel/"
        "receiptValue must render the reading as a bilingual sentence")
    assert "receipt.metric +" not in client
    assert "receipt.value +" not in client
    assert "w.series +" not in client, (
        "the invalidator watched branch still concatenates raw fields; "
        "watchedSentence must render the condition as a bilingual sentence")
    assert "w.metric +" not in client
    # Pin: the bilingual helpers exist and are wired in
    for helper in ("function receiptLabel(", "function receiptValue(",
                   "function watchedSentence("):
        assert helper in client, f"missing helper {helper!r}"
    # Pin: the renderLegDetail loop calls receiptLabel/receiptValue, not el with
    # concatenated textContent
    assert "receiptLabel(receipt)" in client
    assert "receiptValue(receipt)" in client
    assert "watchedSentence(item.watched)" in client
    # Pin: the helper functions handle the empty-receipt branch by disclosing
    # the absence, not by emitting raw concatenated fields
    assert "reading published without a value" in client
    assert "Watching this step's condition" in client
    # Pin: the receiptValue helper guards every owner field through _present()
    # so a missing field never renders as the JavaScript `undefined` string
    assert "function _present(field)" in client
    assert "_present(receipt.value)" in client
    assert "_present(receipt.threshold)" in client


def test_the_continuation_context_is_consumed_on_both_ends():
    """M1 acceptance item 5, the reader-visible half. Writing `from/focus/rev`
    into the transmission.html href preserves nothing unless the landing page
    reads it back. Pin (a) the transmission template consumes the query string
    and offers a return link that carries the step as a `#ox-leg-` hash and the
    revision as `?rev=`, without ever printing the step identifier; (b) the
    explorer client focuses that step from the hash and says, in plain words,
    when the served revision differs from the one the reader left at."""
    landing = (ROOT / "templates" / "transmission.html.j2").read_text(encoding="utf-8")
    consumer = landing[landing.index('id="tx-from"'):]
    consumer = consumer[:consumer.index("</script>")]
    for needle in ('q.get("focus")', 'q.get("from")', 'q.get("rev")',
                   '"#ox-leg-" + encodeURIComponent(focus)',
                   '"?rev=" + encodeURIComponent(rev)', "box.hidden = false"):
        assert needle in consumer, needle
    # The identifier travels in the href only: no textContent/innerText write
    # in the consumer, and the visible copy is a fixed bilingual sentence.
    assert "textContent" not in consumer and "innerText" not in consumer
    assert "go back to that step" in consumer and "返回该步骤" in consumer

    client = (ROOT / "templates" / "ontology.js").read_text(encoding="utf-8")
    assert 'h.indexOf("#ox-leg-") !== 0' in client
    assert "render(snapshot); focusFromHash();" in client
    notice = client[client.index("function continuationNotice"):]
    notice = notice[:notice.index("function continuationHref")]
    assert 'get("rev")' in notice and "String(now) === String(left)" in notice
    assert "revised since you left" in notice and "已修订" in notice
