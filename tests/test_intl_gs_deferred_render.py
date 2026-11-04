#!/usr/bin/env python3
"""INTL-GS deferred contexts — the producer side of the inert-payload contract.

The Dossier and Coverage contexts are published by the canonical Jinja
partials as escaped JSON carriers instead of as live DOM. This proof renders
the real page through the fixture-site seam and shows that:

  * every Dossier and Coverage context is published as one inert carrier;
  * the carrier carries the panel markup as escaped JSON text, so no closing
    markup can leave the carrier and no panel markup is parsed into the
    document;
  * every canonical jurisdiction of the Dossier is still published (none is
    dropped because the workspace core markets are fewer);
  * the default jurisdiction of each context keeps its published identity;
  * the carrier publishes the context identity the controller binds to.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.intl_gs_fixture_site import render_intl_page  # noqa: E402

CARRIER = re.compile(
    r'<script type="application/json" data-im-deferred-payload>(.*?)</script>', re.S)
MARKET_CARRIER = re.compile(r'data-im-gs-market-id="([A-Z]{2})"')
DEFAULT_MARKET_CARRIER = re.compile(r'data-im-gs-market-id="([A-Z]{2})" data-im-gs-market-default')


def _carriers(page):
    return [json.loads(match) for match in CARRIER.findall(page)]


def test_dossier_and_coverage_contexts_are_published_as_inert_carriers():
    page = render_intl_page()
    payloads = _carriers(page)
    views = [payload["view"] for payload in payloads]
    assert views.count("dossier") == 10, "ten Dossier contexts are published"
    assert views.count("coverage") == 10, "ten Coverage contexts are published"

    # The carrier carries the panel markup as escaped JSON text: outside the
    # carriers the rendered document never parses a Dossier article, a
    # Coverage board or a jurisdiction carrier.
    outside = CARRIER.sub("<script type=\"application/json\" data-im-deferred-payload></script>", page)
    assert '<article class="intl-gs__mkt"' not in outside, "no Dossier article is parsed into the document"
    assert "data-im-gs-market-id" not in outside, "no jurisdiction carrier is parsed into the document"
    assert "intl-gs__covgrid" not in outside, "no Coverage board is parsed into the document"
    for match in CARRIER.findall(page):
        assert not re.search(
            r"<!--|</?script", match, re.ASCII | re.IGNORECASE
        ), "no script-tokenizer state delimiter leaves the carrier"

    # The carrier publishes the identity the controller binds to.
    dossier = next(payload for payload in payloads if payload["view"] == "dossier")
    assert dossier["schema"] == "intl-gs-deferred.v1"
    assert dossier["horizon"] and dossier["basis"] and dossier["context_id"]
    assert dossier["markup"].lstrip().startswith("<section"), "the carrier carries the canonical panel root"
    assert 'data-im-panel' in dossier["markup"]
    assert 'data-view="dossier"' in dossier["markup"]


def test_every_canonical_jurisdiction_is_published_and_none_is_dropped():
    page = render_intl_page()
    payloads = [payload for payload in _carriers(page) if payload["view"] == "dossier"]
    assert payloads, "the Dossier contexts are published"
    for payload in payloads:
        markets = payload["markets"]
        assert len(markets) == 64, "all canonical jurisdictions stay published"
        assert len(set(markets)) == 64, "the published jurisdictions are distinct"
        published = set(MARKET_CARRIER.findall(payload["markup"]))
        assert published == set(markets), "every published jurisdiction carries its own carrier"
        defaults = DEFAULT_MARKET_CARRIER.findall(payload["markup"])
        assert len(defaults) == 1, "one default jurisdiction per context"
        assert defaults[0] in markets

    # The jurisdictions of the shipped page are the canonical 64, not the seven
    # core markets of the workspace configuration.
    page_markets = set()
    for payload in payloads:
        page_markets |= set(payload["markets"])
    assert len(page_markets) == 64, "the page publishes 64 canonical jurisdictions"
    assert len(page_markets & {"JP", "GB", "US"}) == 3, "the core markets are a subset, not the whole set"


def test_the_carrier_keeps_the_published_jurisdiction_identity():
    page = render_intl_page()
    payload = next(payload for payload in _carriers(page) if payload["view"] == "dossier")
    market = json.loads(re.search(
        r'<script type="application/json" data-im-gs-market-id="([A-Z]{2})"[^>]*>(.*?)</script>',
        payload["markup"], re.S).group(2))
    assert market["schema"] == "intl-gs-market.v1"
    assert market["market_id"] in payload["markets"]
    assert market["markup"].lstrip().startswith("<article"), "the jurisdiction carrier carries the canonical article"
    assert 'data-gs-market="' in market["markup"], "the published jurisdiction identity is kept"


def test_inert_json_roundtrips_without_script_raw_text_breakout():
    from lib.intl_library_mount import intl_inert_json
    payload = {"markup": "</script><!--<img onerror=bad()>中文😀\u2028\u2029&\"'", "literal": r"\u003c"}
    encoded = str(intl_inert_json(payload))
    assert not re.search(r"<!--|</?script", encoded, re.ASCII | re.IGNORECASE)
    assert "<img" in encoded, "ordinary tags remain JSON string data"
    assert "中文" in encoded
    assert json.loads(encoded) == payload
