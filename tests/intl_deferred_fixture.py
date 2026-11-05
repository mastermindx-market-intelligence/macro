#!/usr/bin/env python3
"""TEST-ONLY reader for the INTL-GS deferred-context carriers (B6).

The International workspace shell publishes a deferred view (B6: Coverage) as
an INERT carrier: the canonical panel root, hidden, carrying the ALREADY
RENDERED canonical markup of that view as JSON text inside one
``script[type=application/json][data-im-deferred-payload]`` child. The page
controller materialises the selected context in the browser; the carrier text
itself is never visible.

``materialize_deferred_view(html, view)`` is a pure SOURCE-FIXTURE INSPECTION
helper for the native test suite: it returns the SAME html with ONLY the
canonical selected-view deferred root sections replaced by their already
rendered ``payload.markup``, so a static test can read the logical page.

It is NOT a renderer, NOT a second copy of the production renderer, NOT a
security proof and NOT a proof of what a connected browser shows. It performs
no I/O, opens no file, runs no script and executes no markup: the payload
markup is copied byte for byte.

The carrier contract this reader enforces (a malformed carrier raises, it is
never worked around):

* the carrier root carries ``data-im-deferred="v1"`` and exactly one
  ``script[type=application/json][data-im-deferred-payload]`` child;
* the payload schema is ``intl-gs-deferred.v1``;
* the payload view, context_id, horizon, basis and generation AGREE with the
  carrier's own attributes (the carrier id is ``<context_id>-<view>-carrier``,
  the canonical root id is ``<context_id>-<view>``);
* one carrier id identifies one element, and the materialised markup
  introduces no id the page already carries.

Carriers of other views are left untouched and are not inspected.

The carrier span is taken from the HTML tokenizer, never from a regular
expression: HTMLParser reads ``<script>`` content as raw text, so a literal
``</section>`` inside the payload JSON never ends the carrier early.
"""
import json
from html.parser import HTMLParser

SCHEMA = "intl-gs-deferred.v1"
DEFERRED_ATTRIBUTE = "data-im-deferred"
DEFERRED_VERSION = "v1"
PAYLOAD_ATTRIBUTE = "data-im-deferred-payload"
PAYLOAD_TYPE = "application/json"
VOID_ELEMENTS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split())


class DeferredFixtureError(ValueError):
    """A deferred carrier does not satisfy the published carrier contract."""


class _Element:
    """One parsed element with its source span in the html."""

    __slots__ = ("tag", "attrs", "start", "open_end", "close_start", "close_end",
                 "children")

    def __init__(self, tag, attrs, start, open_end):
        self.tag = tag
        self.attrs = attrs
        self.start = start
        self.open_end = open_end
        self.close_start = None
        self.close_end = None
        self.children = []

    @property
    def end(self):
        """Offset just after the element (after its end tag when it has one)."""
        return self.open_end if self.close_end is None else self.close_end

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()


class _SpanParser(HTMLParser):
    """Offset-tracking HTMLParser.

    HTMLParser reads <script>/<style> content as raw text, so a literal
    ``</section>`` inside a deferred payload never ends the carrier: the
    carrier span comes from the tokenizer, never from a regular expression.
    """

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self._html = html
        self._line_starts = [0]
        for index, char in enumerate(html):
            if char == "\n":
                self._line_starts.append(index + 1)
        self.root = _Element("#document", {}, 0, 0)
        self._stack = [self.root]
        self.feed(html)
        self.close()

    def _offset(self):
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self._offset()
        text = self.get_starttag_text() or ""
        element = _Element(tag, dict(attrs), start, start + len(text))
        self._stack[-1].children.append(element)
        if tag not in VOID_ELEMENTS:
            self._stack.append(element)

    def handle_startendtag(self, tag, attrs):
        start = self._offset()
        text = self.get_starttag_text() or ""
        element = _Element(tag, dict(attrs), start, start + len(text))
        element.close_start = element.close_end = element.open_end
        self._stack[-1].children.append(element)

    def handle_endtag(self, tag):
        start = self._offset()
        gt = self._html.find(">", start)
        end = len(self._html) if gt < 0 else gt + 1
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                element = self._stack[index]
                element.close_start = start
                element.close_end = end
                del self._stack[index:]
                return


def _payload(element, source):
    """The deferred payload object of one carrier (its JSON, parsed)."""
    scripts = [child for child in element.descendants()
               if child.tag == "script"
               and (child.attrs.get("type") or "").strip().lower() == PAYLOAD_TYPE
               and PAYLOAD_ATTRIBUTE in child.attrs]
    if len(scripts) != 1:
        raise DeferredFixtureError(
            "deferred carrier must carry exactly one payload script")
    script = scripts[0]
    if script.close_start is None:
        raise DeferredFixtureError("deferred payload script is not closed")
    try:
        payload = json.loads(source[script.open_end:script.close_start])
    except ValueError as exc:
        raise DeferredFixtureError("deferred payload is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise DeferredFixtureError("deferred payload is not an object")
    return payload


def _materialized_markup(element, identifiers, source):
    """The canonical markup of one carrier, once the carrier contract holds."""
    view = element.attrs.get("data-view")
    identifier = element.attrs.get("id")
    suffix = "-" + view + "-carrier"
    if not identifier or not identifier.endswith(suffix):
        raise DeferredFixtureError(
            "deferred carrier id is not <context_id>-<view>-carrier")
    context_id = identifier[:-len(suffix)]
    if not context_id:
        raise DeferredFixtureError("deferred carrier carries no context id")
    if identifiers.get(identifier, 0) != 1:
        raise DeferredFixtureError("duplicate deferred carrier id: " + identifier)
    payload = _payload(element, source)
    if payload.get("schema") != SCHEMA:
        raise DeferredFixtureError("unexpected deferred payload schema")
    if payload.get("view") != view:
        raise DeferredFixtureError("deferred payload view does not match its carrier")
    if payload.get("context_id") != context_id:
        raise DeferredFixtureError(
            "deferred payload context does not match its carrier")
    if payload.get("horizon") != element.attrs.get("data-horizon"):
        raise DeferredFixtureError(
            "deferred payload horizon does not match its carrier")
    if payload.get("basis") != element.attrs.get("data-basis"):
        raise DeferredFixtureError(
            "deferred payload basis does not match its carrier")
    generation = element.attrs.get("data-im-generation")
    if generation is None:
        if payload.get("generation") not in (None, ""):
            raise DeferredFixtureError(
                "deferred payload generation does not match its carrier")
    elif str(payload.get("generation")) != generation:
        raise DeferredFixtureError(
            "deferred payload generation does not match its carrier")
    markup = payload.get("markup")
    if not isinstance(markup, str) or not markup:
        raise DeferredFixtureError("deferred payload carries no markup")
    root = _SpanParser(markup).root
    head = root.children[0] if root.children else None
    if head is None or head.attrs.get("id") != context_id + "-" + view:
        raise DeferredFixtureError(
            "deferred markup root is not the canonical panel root")
    markup_ids = [child.attrs["id"] for child in root.descendants()
                  if child.attrs.get("id")]
    if len(set(markup_ids)) != len(markup_ids):
        raise DeferredFixtureError("deferred markup repeats an id")
    for markup_id in markup_ids:
        if identifiers.get(markup_id, 0):
            raise DeferredFixtureError(
                "deferred markup would duplicate the id " + markup_id)
    return markup


def materialize_deferred_view(html, view):
    """Return ``html`` with the selected view's deferred carriers replaced by
    their already rendered canonical markup.

    Every other node of the document — the other views, the ordinary nodes and
    every script — is returned byte for byte. A malformed, mismatched or
    duplicated carrier raises :class:`DeferredFixtureError`; it is never
    worked around and never partially materialised.
    """
    if not isinstance(view, str) or not view:
        raise DeferredFixtureError("view must be a non-empty string")
    source = str(html)
    if DEFERRED_ATTRIBUTE not in source:
        return source
    root = _SpanParser(source).root
    elements = list(root.descendants())
    identifiers = {}
    for element in elements:
        identifier = element.attrs.get("id")
        if identifier:
            identifiers[identifier] = identifiers.get(identifier, 0) + 1
    selected = []
    for element in elements:
        if element.attrs.get(DEFERRED_ATTRIBUTE) != DEFERRED_VERSION:
            continue
        if element.attrs.get("data-view") != view:
            continue  # another view's carrier: left exactly as published
        if element.tag != "section":
            raise DeferredFixtureError(
                "deferred carrier root is not a section")
        selected.append(element)
    resolved = [(element, _materialized_markup(element, identifiers, source))
                for element in selected]
    pieces = []
    cursor = 0
    for element, markup in resolved:
        pieces.append(source[cursor:element.start])
        pieces.append(markup)
        cursor = element.end
    pieces.append(source[cursor:])
    return "".join(pieces)
