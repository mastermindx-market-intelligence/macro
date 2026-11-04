#!/usr/bin/env python3
"""Focused tests for the TEST-ONLY deferred-carrier fixture reader.

Every case builds its own small carrier document: no network, no file write,
no script execution and no dependency on the published page.
"""
import builtins
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tests.intl_deferred_fixture import (  # noqa: E402
    DeferredFixtureError,
    materialize_deferred_view,
)

VIEW = "coverage"
OTHER_VIEW = "dossier"
CONTEXT_ID = "im-gs-coverage-1m-usd_unhedged"
CANONICAL_ID = CONTEXT_ID + "-" + VIEW
CARRIER_ID = CANONICAL_ID + "-carrier"


def _markup(context_id=CONTEXT_ID, view=VIEW, body=""):
    """The canonical panel markup a carrier ships as payload text."""
    return (
        '<section class="intl-gs__panel intl-gs__view intl-gs__view--{view}"'
        ' data-im-panel data-gs-panel data-view="{view}" data-horizon="1m"'
        ' data-basis="usd_unhedged" data-return-basis="price" data-source=""'
        ' data-im-deferrable="v1" id="{canonical}"'
        ' aria-labelledby="{canonical}-title">'
        '<h1 id="{canonical}-title">Coverage and data states</h1>'
        '<span class="intl-gs__covcell" data-col="index_close"'
        ' data-tip-en="Qualified" data-tip-zh="有条件" tabindex="0"></span>'
        "{body}</section>").format(view=view, canonical=context_id + "-" + view,
                                   body=body)


def _payload(markup, **overrides):
    payload = {
        "schema": "intl-gs-deferred.v1",
        "view": VIEW,
        "context_id": CONTEXT_ID,
        "horizon": "1m",
        "basis": "usd_unhedged",
        "generation": None,
        "markets": ["JP"],
        "markup": markup,
    }
    payload.update(overrides)
    return payload


def _carrier(markup=None, payload=None, raw=None, view=VIEW,
             context_id=CONTEXT_ID, carrier_id=CARRIER_ID, horizon="1m",
             basis="usd_unhedged", generation=None, payload_script=True):
    """One published carrier: hidden root, one JSON payload script."""
    body = _markup(context_id, view) if markup is None else markup
    if raw is not None:
        blob = raw
    elif payload is not None:
        blob = json.dumps(payload)
    else:
        blob = json.dumps(_payload(body, view=view, context_id=context_id,
                                    horizon=horizon, basis=basis,
                                    generation=generation))
    script = ('<script type="application/json" data-im-deferred-payload>%s</script>'
              % blob) if payload_script else ""
    generation_attr = ("" if generation is None
                       else ' data-im-generation="%s"' % generation)
    return (
        '<section class="intl-gs__panel intl-gs__view intl-gs__view--{view}"'
        ' data-im-panel data-gs-panel data-view="{view}" data-horizon="{horizon}"'
        ' data-basis="{basis}" data-return-basis="price" data-source=""{generation}'
        ' hidden data-im-deferred="v1" data-im-deferred-markets="JP" id="{carrier}"'
        ' aria-labelledby="{canonical}-title">{script}</section>').format(
            view=view, horizon=horizon, basis=basis, generation=generation_attr,
            carrier=carrier_id, canonical=context_id + "-" + view, script=script)


# ------------------------------------------------------------------ happy path


def test_a_valid_carrier_is_replaced_by_its_canonical_markup():
    markup = _markup()
    page = "<html><body>" + _carrier(markup=markup) + "<p>after</p></body></html>"
    out = materialize_deferred_view(page, VIEW)
    assert out == "<html><body>" + markup + "<p>after</p></body></html>"
    assert "data-im-deferred" not in out
    assert "application/json" not in out


def test_a_page_without_a_carrier_is_returned_unchanged():
    page = "<html><body><section class='intl-gs__panel'>x</section></body></html>"
    assert materialize_deferred_view(page, VIEW) == page


def test_the_carrier_of_another_view_is_left_untouched():
    other = _carrier(markup=_markup(context_id="im-gs-dossier-1m", view=OTHER_VIEW),
                     view=OTHER_VIEW, context_id="im-gs-dossier-1m",
                     carrier_id="im-gs-dossier-1m-dossier-carrier")
    page = "<html><body>" + other + "</body></html>"
    assert materialize_deferred_view(page, VIEW) == page


def test_ordinary_sections_around_the_carrier_are_unchanged():
    before = ('<section class="intl-workspace" id="intl-workspace">'
              '<section class="intl-gs__panel intl-gs__view intl-gs__view--scanner"'
              ' id="im-gs-scanner-1m-usd_unhedged-scanner">live</section></section>')
    after = ('<section class="intl-gs__panel intl-gs__view intl-gs__view--dossier"'
             ' id="im-gs-dossier-1m-dossier">dossier</section>')
    page = "<html><body>" + before + _carrier() + after + "</body></html>"
    out = materialize_deferred_view(page, VIEW)
    assert out.startswith("<html><body>" + before)
    assert out.endswith(after + "</body></html>")
    assert _markup() in out


def test_a_literal_closing_section_inside_the_payload_markup():
    # the payload text holds the canonical markup, whose own </section> must
    # not end the carrier early
    markup = _markup(body='<section class="intl-gs__nested">nested</section>')
    assert markup.count("</section>") == 2
    tail = ('<section class="intl-gs__panel intl-gs__view intl-gs__view--scanner">'
            'tail</section>')
    page = "<html><body>" + _carrier(markup=markup) + tail + "</body></html>"
    out = materialize_deferred_view(page, VIEW)
    assert out == "<html><body>" + markup + tail + "</body></html>"
    assert out.count("data-im-deferred") == 0


# ------------------------------------------------------------------- refusals


def test_a_malformed_payload_raises():
    page = "<html><body>" + _carrier(raw="{not json") + "</body></html>"
    with pytest.raises(DeferredFixtureError):
        materialize_deferred_view(page, VIEW)


def test_a_carrier_without_a_payload_script_raises():
    page = "<html><body>" + _carrier(payload_script=False) + "</body></html>"
    with pytest.raises(DeferredFixtureError):
        materialize_deferred_view(page, VIEW)


def test_an_unexpected_schema_raises():
    payload = _payload(_markup(), schema="intl-gs-deferred.v2")
    page = "<html><body>" + _carrier(payload=payload) + "</body></html>"
    with pytest.raises(DeferredFixtureError):
        materialize_deferred_view(page, VIEW)


@pytest.mark.parametrize("overrides", [
    {"context_id": "im-gs-coverage-3m-usd_unhedged"},
    {"horizon": "3m"},
    {"basis": "local"},
    {"generation": "v2"},
    {"view": OTHER_VIEW},
])
def test_a_mismatched_payload_raises(overrides):
    payload = _payload(_markup(), **overrides)
    page = "<html><body>" + _carrier(payload=payload) + "</body></html>"
    with pytest.raises(DeferredFixtureError):
        materialize_deferred_view(page, VIEW)


def test_a_duplicate_carrier_raises():
    carrier = _carrier()
    page = "<html><body>" + carrier + carrier + "</body></html>"
    with pytest.raises(DeferredFixtureError):
        materialize_deferred_view(page, VIEW)


def test_a_carrier_that_is_not_a_section_raises():
    carrier = _carrier().replace("<section ", "<div ").replace("</section>", "</div>")
    page = "<html><body>" + carrier + "</body></html>"
    with pytest.raises(DeferredFixtureError):
        materialize_deferred_view(page, VIEW)


def test_a_matching_generation_attribute_is_accepted():
    payload = _payload(_markup(), generation="v2")
    carrier = _carrier(payload=payload, generation="v2")
    page = "<html><body>" + carrier + "</body></html>"
    assert materialize_deferred_view(page, VIEW) == "<html><body>" + _markup() + "</body></html>"


def test_every_carrier_of_the_view_is_materialized():
    other = _carrier(markup=_markup(context_id="im-gs-coverage-3m-usd_unhedged"),
                     context_id="im-gs-coverage-3m-usd_unhedged",
                     carrier_id="im-gs-coverage-3m-usd_unhedged-coverage-carrier")
    page = "<html><body>" + _carrier() + other + "</body></html>"
    out = materialize_deferred_view(page, VIEW)
    assert out.count("data-im-deferred") == 0
    assert out.count('id="im-gs-coverage-1m-usd_unhedged-coverage"') == 1
    assert out.count('id="im-gs-coverage-3m-usd_unhedged-coverage"') == 1


def test_a_markup_that_would_duplicate_an_id_raises():
    page = ('<html><body><span id="' + CANONICAL_ID + '">taken</span>'
            + _carrier() + "</body></html>")
    with pytest.raises(DeferredFixtureError):
        materialize_deferred_view(page, VIEW)


# --------------------------------------------------------- no writes, no runs


def test_the_helper_writes_nothing_and_executes_nothing(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("the deferred fixture reader must not touch files")
    monkeypatch.setattr(builtins, "open", deny)
    active = '<span onclick="window.ran = true">active</span>'
    markup = _markup(body=active)
    page = "<html><body>" + _carrier(markup=markup) + "</body></html>"
    out = materialize_deferred_view(page, VIEW)
    # the payload markup is copied byte for byte; nothing is evaluated
    assert active in out
    assert isinstance(out, str)


def test_the_reader_module_runs_nothing():
    source = (REPO / "tests/intl_deferred_fixture.py").read_text(encoding="utf-8")
    for forbidden in ("exec(", "eval(", "compile(", "subprocess", "os.system",
                      "os.remove", "import os", "import socket", "urllib"):
        assert forbidden not in source, forbidden
