"""Adversarial contract tests for the strict offline SEC filing parser."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import builtins
import json
import re
import socket

import pytest

import collectors.sec_filing_parser as parser_module

from collectors.sec_filing_parser import (
    PARSER_LIMITS,
    SEC_FILING_PARSER_PROFILE,
    SEC_FILING_PARSER_SCHEMA,
    SEC_FILING_PARSER_VERSION,
    SUPPORTED_TRANSFORMS,
    SecFilingParseError,
    parse_sec_filing_document,
    validate_sec_filing_parse_result,
)


FIXTURES = Path(__file__).parent / "fixtures" / "sec_filings"
XBRLI = "http://www.xbrl.org/2003/instance"
IX = "http://www.xbrl.org/2013/inlineXBRL"
TRR3 = "http://www.xbrl.org/inlineXBRL/transformation/2015-02-26"
TRR4 = "http://www.xbrl.org/inlineXBRL/transformation/2020-02-12"


def _instance(body: str, *, resources: str | None = None) -> bytes:
    resource_xml = resources or """
      <xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>
      <xbrli:unit id="u"><xbrli:measure>ex:USD</xbrli:measure></xbrli:unit>
    """
    return f'''<xbrli:xbrl xmlns:xbrli="{XBRLI}" xmlns:ex="urn:example">{resource_xml}{body}</xbrli:xbrl>'''.encode()


def _inline(body: str, *, continuations: str = "", resources: str | None = None) -> bytes:
    resource_xml = resources or f"""
      <xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>
      <xbrli:unit id="u"><xbrli:measure>ex:USD</xbrli:measure></xbrli:unit>
    """
    # Keep all positive fixtures on the SEC-realistic Inline XBRL 1.1 path:
    # one header in the XHTML body, with resources as its direct child.
    # Negative tests below deliberately construct illegal placements.
    return f'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="{IX}" xmlns:xbrli="{XBRLI}" xmlns:ex="urn:example" xmlns:i3="{TRR3}" xmlns:i4="{TRR4}"><head></head><body><ix:header><ix:resources>{resource_xml}</ix:resources></ix:header>{body}{continuations}</body></html>'''.encode()


def test_public_contract_and_transform_registry_are_fixed():
    assert SEC_FILING_PARSER_SCHEMA == "fundamental_forensics.sec_filing_parser/v1"
    assert SEC_FILING_PARSER_PROFILE == "strict_offline_ixbrl/v1"
    assert SEC_FILING_PARSER_VERSION == "1"
    assert set(SUPPORTED_TRANSFORMS) == {
        f"{{{TRR3}}}numdotdecimal",
        f"{{{TRR3}}}numcommadecimal",
        f"{{{TRR3}}}zerodash",
        f"{{{TRR3}}}nocontent",
        f"{{{TRR4}}}num-dot-decimal",
        f"{{{TRR4}}}num-comma-decimal",
        f"{{{TRR4}}}fixed-zero",
        f"{{{TRR4}}}fixed-empty",
    }


def test_indexed_direct_text_preserves_owner_and_mixed_content_without_full_scan():
    content = (
        b'<r xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">before'
        b'<a>Caf\xc3\xa9&amp;<![CDATA[raw]]><!--split-->tail'
        b'<b>nested</b>after<ix:exclude>excluded</ix:exclude>end</a>'
        b'<empty/>' + b'<s>unrelated</s>' * 1000 + b'</r>'
    )
    _, nodes, events = parser_module._TreeBuilder(
        content, parser_module._limits_snapshot()
    ).build()
    reference_events = list(events)

    class IndexedOnlyEvents(parser_module._TextEvents):
        def __iter__(self):
            raise AssertionError("direct text scanned the complete event stream")

    indexed = IndexedOnlyEvents(events)
    indexed.starts = events.starts
    for node in nodes:
        expected = "".join(e.value for e in reference_events if e.owner is node)
        assert parser_module._direct_text(node, indexed) == expected
        assert parser_module._direct_text(node, reference_events) == expected
    a = next(node for node in nodes if node.local == "a")
    assert parser_module._direct_text(a, indexed) == "Café&rawtailafterend"


def test_pure_instance_context_units_dimensions_and_exact_multibyte_spans():
    content = (FIXTURES / "minimal_instance.xml").read_bytes()
    result = parse_sec_filing_document(content, document_name="minimal_instance.xml")

    assert set(result) == {
        "schema", "parser", "source", "document", "contexts", "units",
        "continuations", "facts", "diagnostics", "coverage",
    }
    assert result["document"]["kind"] == "xbrl_instance"
    assert [context["period"]["kind"] for context in result["contexts"]] == ["instant", "duration"]
    assert result["contexts"][0]["dimensions"][0]["kind"] == "explicit"
    typed = result["contexts"][1]["dimensions"][0]
    assert typed["kind"] == "typed"
    assert typed["typed_value_xml"] == "<ex:Channel>Direct</ex:Channel>"
    assert result["units"][1]["denominator_measures"] == ["{https://example.test/taxonomy}shares"]
    label = next(fact for fact in result["facts"] if fact["concept_qname"].endswith("}Label"))
    assert label["normalized_value"] == "Café"
    text_span = label["text_spans"][0]
    assert content[text_span["start"] : text_span["end"]] == "Café".encode()
    assert label["source_span"]["start"] == content.index(b"<ex:Label")
    validate_sec_filing_parse_result(result, source_content=content)


def test_inline_hidden_exclude_scale_sign_nil_fraction_continuation_and_unknown_transform():
    content = (FIXTURES / "minimal_inline.xhtml").read_bytes()
    result = parse_sec_filing_document(content, document_name="minimal_inline.xhtml")
    facts = {fact["fact_id"]: fact for fact in result["facts"]}

    assert result["document"]["kind"] == "inline_xbrl"
    assert facts["scaled"]["raw_value"] == "1,234.5"
    assert facts["scaled"]["normalized_value"] == "-1234500"
    assert facts["scaled"]["hidden"] is True
    assert facts["scaled"]["excluded_text_spans"] == []
    assert facts["label"]["normalized_value"] == "Café"
    assert facts["nil"]["status"] == "nil"
    assert facts["ratio"]["fraction"] == {
        "numerator_raw": "1", "denominator_raw": "3",
        "numerator_normalized": "1", "denominator_normalized": "3",
    }
    assert facts["ratio"]["normalized_value"] is None
    assert facts["unknown"]["status"] == "unsupported_transform"
    assert facts["unknown"]["normalized_value"] is None
    assert result["coverage"]["canonical_value_complete"] is False
    assert result["diagnostics"] == [{
        "code": "unsupported_transform",
        "fact_start": facts["unknown"]["source_span"]["start"],
        "format": "{https://example.test/taxonomy}mystery",
    }]


@pytest.mark.parametrize(
    ("format_value", "raw", "normalized"),
    [
        ("i3:numdotdecimal", "1,234.50", "1234.5"),
        ("i3:numcommadecimal", "1.234,50", "1234.5"),
        ("i3:zerodash", "-", "0"),
        ("i4:num-dot-decimal", "2,500.25", "2500.25"),
        ("i4:num-comma-decimal", "2.500,25", "2500.25"),
        ("i4:fixed-zero", "", "0"),
    ],
)
def test_pinned_transform_vectors(format_value, raw, normalized):
    content = _inline(
        f'<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" format="{format_value}">{raw}</ix:nonFraction>'
    )
    fact = parse_sec_filing_document(content, document_name="transform.xhtml")["facts"][0]
    assert fact["normalized_value"] == normalized
    assert fact["status"] == "available"


@pytest.mark.parametrize(
    ("format_value", "raw", "normalized"),
    [
        ("i3:numdotdecimal", "1 234.50", "1234.5"),
        ("i3:numdotdecimal", "1\u00a0234.50", "1234.5"),
        ("i3:numcommadecimal", "1 234,50", "1234.5"),
        ("i3:numcommadecimal", "1\u00a0234,50", "1234.5"),
        ("i4:num-dot-decimal", ". 5", "0.5"),
        ("i4:num-comma-decimal", ", 5", "0.5"),
    ],
)
def test_registry_permitted_space_nbsp_and_missing_integer_vectors(
    format_value, raw, normalized
):
    content = _inline(
        f'<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" '
        f'format="{format_value}">{raw}</ix:nonFraction>'
    )
    fact = parse_sec_filing_document(content, document_name="registry-edge.xhtml")["facts"][0]
    assert fact["status"] == "available"
    assert fact["normalized_value"] == normalized


@pytest.mark.parametrize("format_value", ["i3:nocontent", "i4:fixed-empty"])
def test_pinned_nonnumeric_empty_transform_vectors(format_value):
    fact = parse_sec_filing_document(
        _inline(f'<ix:nonNumeric name="ex:F" contextRef="c" format="{format_value}">ignored</ix:nonNumeric>'),
        document_name="text-transform.xhtml",
    )["facts"][0]
    assert fact["transformed_value"] == ""
    assert fact["normalized_value"] == ""
    assert fact["status"] == "available"


def test_nested_inline_facts_are_each_preserved():
    content = _inline(
        '<ix:nonNumeric id="outer" name="ex:Outer" contextRef="c">before '
        '<ix:nonNumeric id="inner" name="ex:Inner" contextRef="c">inside</ix:nonNumeric> after</ix:nonNumeric>'
    )
    facts = parse_sec_filing_document(content, document_name="nested.xhtml")["facts"]
    assert [fact["fact_id"] for fact in facts] == ["outer", "inner"]
    assert facts[0]["raw_value"] == "before inside after"
    assert facts[1]["raw_value"] == "inside"


def test_numeric_fact_inside_text_block_is_preserved_with_independent_span():
    content = _inline(
        '<ix:nonNumeric id="text" name="ex:TextBlock" contextRef="c">'
        'Revenue was <ix:nonFraction id="amount" name="ex:Amount" '
        'contextRef="c" unitRef="u" decimals="0">100</ix:nonFraction>.'
        '</ix:nonNumeric>'
    )
    facts = parse_sec_filing_document(
        content, document_name="nested-numeric-text-block.xhtml"
    )["facts"]
    by_id = {fact["fact_id"]: fact for fact in facts}
    assert by_id["text"]["raw_value"] == "Revenue was 100."
    assert by_id["amount"]["raw_value"] == "100"
    assert by_id["amount"]["normalized_value"] == "100"
    assert by_id["amount"]["source_span"] != by_id["text"]["source_span"]


def test_escaped_nonnumeric_retains_markup_strips_inline_tags_and_replays() -> None:
    content = _inline(
        '<ix:nonNumeric id="outer" name="ex:Outer" contextRef="c" escape="true">'
        '<div class="note">A <ix:nonNumeric id="inner" name="ex:Inner" '
        'contextRef="c" escape="true"><b>B</b></ix:nonNumeric>'
        '<ix:exclude>drop</ix:exclude> C</div></ix:nonNumeric>'
    )
    parsed = parse_sec_filing_document(content, document_name="escaped-text-block.xhtml")
    facts = {fact["fact_id"]: fact for fact in parsed["facts"]}

    assert facts["outer"]["escape"] is True
    assert facts["outer"]["raw_value"] == '<div class="note">A <b>B</b> C</div>'
    assert facts["inner"]["raw_value"] == "<b>B</b>"
    assert facts["outer"]["transformed_value"] == facts["outer"]["raw_value"]
    validate_sec_filing_parse_result(parsed)
    validate_sec_filing_parse_result(parsed, source_content=content)


def test_escaped_nonnumeric_continuation_and_uri_boundary() -> None:
    fact = (
        '<ix:nonNumeric id="f" name="ex:F" contextRef="c" '
        'continuedAt="a" escape="true"><p>A</p></ix:nonNumeric>'
    )
    continuation = '<ix:continuation id="a"><div>B</div></ix:continuation>'
    content = _inline(fact, continuations=continuation)
    parsed = parse_sec_filing_document(content, document_name="escaped-continuation.xhtml")
    assert parsed["facts"][0]["raw_value"] == "<p>A</p><div>B</div>"
    validate_sec_filing_parse_result(parsed, source_content=content)

    relative_uri = _inline(
        '<ix:nonNumeric name="ex:F" contextRef="c" escape="true">'
        '<a href="relative">link</a></ix:nonNumeric>'
    )
    with pytest.raises(SecFilingParseError, match="relative URI"):
        parse_sec_filing_document(relative_uri, document_name="escaped-relative-uri.xhtml")


def test_escaped_nonnumeric_same_document_fragment_href_is_admitted() -> None:
    # (P1) The fragment target sits inside the same fact.
    fact = (
        '<ix:nonNumeric id="f" name="ex:F" contextRef="c" escape="true">'
        '<p><a style="color:#0000ff" href="#t1">see</a></p><span id="t1"></span></ix:nonNumeric>'
    )
    content = _inline(fact)
    parsed = parse_sec_filing_document(content, document_name="fragment-in-fact.xhtml")
    assert parsed["facts"][0]["raw_value"] == (
        '<p><a style="color:#0000ff" href="#t1">see</a></p><span id="t1"></span>'
    )
    validate_sec_filing_parse_result(parsed, source_content=content)

    # (P2) The fragment target sits in the body outside every ix element.
    fact = (
        '<ix:nonNumeric id="f" name="ex:F" contextRef="c" escape="true">'
        '<a href="#t2">x</a></ix:nonNumeric>'
    )
    content = _inline(fact + '<div id="t2"></div>')
    parsed = parse_sec_filing_document(content, document_name="fragment-in-body.xhtml")
    assert parsed["facts"][0]["raw_value"] == '<a href="#t2">x</a>'
    validate_sec_filing_parse_result(parsed, source_content=content)

    # (P3) The fragment link sits in an escaped continuation whose target id
    # is carried by the fact head.
    fact = (
        '<ix:nonNumeric id="f" name="ex:F" contextRef="c" continuedAt="a" escape="true">'
        '<span id="t3"></span><p>A</p></ix:nonNumeric>'
    )
    continuation = '<ix:continuation id="a"><a href="#t3">go</a></ix:continuation>'
    content = _inline(fact, continuations=continuation)
    parsed = parse_sec_filing_document(content, document_name="fragment-in-continuation.xhtml")
    assert parsed["facts"][0]["raw_value"] == '<span id="t3"></span><p>A</p><a href="#t3">go</a>'
    validate_sec_filing_parse_result(parsed, source_content=content)

    # (P4) Removing the fragment link changes only the retained markup value;
    # no other record moves.
    linked = parse_sec_filing_document(
        _inline(
            '<ix:nonNumeric id="f" name="ex:F" contextRef="c" escape="true">'
            '<p><a style="color:#0000ff" href="#t1">see</a></p><span id="t1"></span></ix:nonNumeric>'
        ),
        document_name="fragment-p4.xhtml",
    )
    unlinked = parse_sec_filing_document(
        _inline(
            '<ix:nonNumeric id="f" name="ex:F" contextRef="c" escape="true">'
            '<p>see</p><span id="t1"></span></ix:nonNumeric>'
        ),
        document_name="fragment-p4.xhtml",
    )
    anchor = '<a style="color:#0000ff" href="#t1">see</a>'
    assert linked["facts"][0]["raw_value"].replace(anchor, "see") == unlinked["facts"][0]["raw_value"]
    assert linked["contexts"] == unlinked["contexts"]
    assert linked["units"] == unlinked["units"]
    assert len(linked["facts"]) == len(unlinked["facts"]) == 1
    span_and_value_fields = {
        "raw_value",
        "transformed_value",
        "normalized_value",
        "text_spans",
        "excluded_text_spans",
        "source_span",
    }
    assert {key: value for key, value in linked["facts"][0].items() if key not in span_and_value_fields} == {
        key: value for key, value in unlinked["facts"][0].items() if key not in span_and_value_fields
    }


_BAD_FRAGMENT_HREFS = [
    "#",
    "# t1",
    "#t1 ",
    " #t1",
    "#t1&#9;",
    "#t1&#x85;",
    "#t1&#x200B;",
    "#t/1",
    "#t\\1",
    "#t:1",
    "#t?1",
    "#t#1",
    "#t%31",
    "#1t",
    "t1",
    "a.htm",
    "./a",
    "../a",
    "//host/a",
    "?q",
    "a.htm#t1",
    "",
]


@pytest.mark.parametrize(
    ("case", "markup", "body_suffix", "match"),
    [
        *[
            (f"href={value!r}", f'<a href="{value}">x</a>', '<span id="t1"></span>', "relative URI")
            for value in _BAD_FRAGMENT_HREFS
        ],
        ("unknown-id", '<a href="#nope">x</a>', '<span id="t1"></span>', "relative URI"),
        # The parser keeps one document-wide id namespace across ALL elements,
        # so a duplicated id is refused by that pre-existing rule first.
        (
            "duplicate-id",
            '<a href="#t1">x</a>',
            '<span id="t1"></span><span id="t1"></span>',
            "duplicate Inline XBRL id",
        ),
        ("non-a-element", '<span href="#t1">x</span>', '<span id="t1"></span>', "relative URI"),
        ("src-not-href", '<img src="#t1"/>', '<span id="t1"></span>', "relative URI"),
        (
            "prefixed-href",
            '<a xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="#t1">x</a>',
            '<span id="t1"></span>',
            "relative URI",
        ),
        ("non-xhtml-a", '<ex:a href="#t1">x</ex:a>', '<span id="t1"></span>', "relative URI"),
    ],
)
def test_escaped_nonnumeric_fragment_href_refusals(case, markup, body_suffix, match) -> None:
    body = (
        '<ix:nonNumeric id="f" name="ex:F" contextRef="c" escape="true">'
        f"{markup}</ix:nonNumeric>{body_suffix}"
    )
    with pytest.raises(SecFilingParseError, match=match):
        parse_sec_filing_document(_inline(body), document_name="fragment-refusal.xhtml")


@pytest.mark.parametrize(
    ("case", "markup", "body_suffix", "inject_base_element"),
    [
        (
            "xml-base-on-anchor",
            '<a xml:base="https://evil.example/other.htm" href="#t1">x</a>',
            '<span id="t1"></span>',
            False,
        ),
        (
            "xml-base-on-ancestor",
            '<div xml:base="https://evil.example/other.htm"><a href="#t1">x</a></div>',
            '<span id="t1"></span>',
            False,
        ),
        (
            "relative-xml-base-on-ancestor",
            '<div xml:base="other.htm"><a href="#t1">x</a></div>',
            '<span id="t1"></span>',
            False,
        ),
        (
            "xhtml-base-element-in-head",
            '<a href="#t1">x</a>',
            '<span id="t1"></span>',
            True,
        ),
        (
            "xml-base-elsewhere-in-document",
            '<a href="#t1">x</a>',
            '<span id="t1"></span><div xml:base="other.htm"></div>',
            False,
        ),
    ],
)
def test_escaped_nonnumeric_fragment_href_refused_under_a_changed_base(
    case, markup, body_suffix, inject_base_element
) -> None:
    # A same-document fragment resolves against the document base URI, so any
    # base-changing construct anywhere in the member - xml:base on the anchor,
    # on an ancestor, or elsewhere, or an XHTML base element in the head -
    # makes the fragment exception inapplicable and the refusal fires.
    body = (
        '<ix:nonNumeric id="f" name="ex:F" contextRef="c" escape="true">'
        f"{markup}</ix:nonNumeric>{body_suffix}"
    )
    content = _inline(body)
    if inject_base_element:
        assert content.count(b"<head></head>") == 1
        content = content.replace(
            b"<head></head>",
            b'<head><base href="https://evil.example/other.htm"/></head>',
        )
    with pytest.raises(SecFilingParseError, match="relative URI markup is unsupported"):
        parse_sec_filing_document(content, document_name="fragment-base-refusal.xhtml")


def test_escaped_nonnumeric_fragment_href_is_admitted_without_a_base_construct() -> None:
    # Same shape as the document-level negative, minus the base construct:
    # the fragment exception applies and the markup is retained unchanged.
    body = (
        '<ix:nonNumeric id="f" name="ex:F" contextRef="c" escape="true">'
        '<a href="#t1">x</a></ix:nonNumeric><span id="t1"></span><div></div>'
    )
    content = _inline(body)
    parsed = parse_sec_filing_document(content, document_name="fragment-no-base.xhtml")
    assert parsed["facts"][0]["raw_value"] == '<a href="#t1">x</a>'
    validate_sec_filing_parse_result(parsed, source_content=content)


@pytest.mark.parametrize(
    ("case", "head_markup", "body_suffix"),
    [
        ("upper_xhtml_head", '<BASE href="https://evil.example/other.htm"/>', ""),
        ("foreign_namespace_body", "", '<x:base xmlns:x="urn:example:other"/>'),
        ("mixed_case_head", '<Base href="https://evil.example/other.htm"/>', ""),
        ("no_namespace_body", "", '<base xmlns=""/>'),
    ],
)
def test_escaped_nonnumeric_fragment_href_refused_under_any_casefold_base_element(
    case, head_markup, body_suffix
) -> None:
    # D1X-5: a same-document fragment resolves against the document base URI,
    # and HTML base-construct matching is case-insensitive, so ANY element
    # whose local name casefolds to "base" - uppercase/mixed-case XHTML in the
    # head, a foreign namespace, or no namespace at all - changes the base and
    # voids the fragment exception exactly like a lowercase XHTML <base>.
    body = (
        '<ix:nonNumeric id="f" name="ex:F" contextRef="c" escape="true">'
        f'<a href="#t1">x</a></ix:nonNumeric><span id="t1"></span><div></div>{body_suffix}'
    )
    content = _inline(body)
    if head_markup:
        assert content.count(b"<head></head>") == 1
        content = content.replace(b"<head></head>", f"<head>{head_markup}</head>".encode())
    with pytest.raises(SecFilingParseError, match="relative URI markup is unsupported"):
        parse_sec_filing_document(content, document_name=f"fragment-casefold-base-{case}.xhtml")


def test_same_document_fragment_predicate_requires_exactly_one_target_and_no_base() -> None:
    anchor = parser_module._Node(
        qname=f"{{{parser_module.XHTML}}}a",
        lexical_name="a",
        attrs={"href": "#t1"},
        namespaces={},
        start=0,
        start_tag_end=0,
        self_closing=False,
        parent=None,
    )
    pred = parser_module._is_same_document_fragment_href
    assert pred(anchor, "href", "#t1", {"t1": 1}, document_base_changed=False) is True
    assert pred(anchor, "href", "#t1", {"t1": 2}, document_base_changed=False) is False
    assert pred(anchor, "href", "#t1", {}, document_base_changed=False) is False
    assert pred(anchor, "href", "#t1", {"t1": 1}, document_base_changed=True) is False


def test_escape_attribute_is_limited_to_inline_nonnumeric_facts() -> None:
    plain = parse_sec_filing_document(
        _inline('<ix:nonNumeric name="ex:F" contextRef="c" escape="false"><b>plain</b></ix:nonNumeric>'),
        document_name="unescaped-text.xhtml",
    )
    assert plain["facts"][0]["escape"] is False
    assert plain["facts"][0]["raw_value"] == "plain"

    invalid = _inline(
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" '
        'decimals="0" escape="true">1</ix:nonFraction>'
    )
    with pytest.raises(SecFilingParseError, match="unsupported attributes"):
        parse_sec_filing_document(invalid, document_name="numeric-escape.xhtml")


def test_forever_context_and_unknown_scenario_are_explicit_partial():
    resources = f'''<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:forever /></xbrli:period><xbrli:scenario><ex:VendorExtension>opaque</ex:VendorExtension></xbrli:scenario></xbrli:context>'''
    result = parse_sec_filing_document(_instance("", resources=resources), document_name="partial.xml")
    assert result["contexts"][0]["period"]["kind"] == "forever"
    assert result["contexts"][0]["scenario_content_status"] == "partial"
    assert result["coverage"]["unknown_scenario_content_count"] == 1


@pytest.mark.parametrize(
    "payload,match",
    [
        (b'<!DOCTYPE r [<!ENTITY x "lol">]><r>&x;</r>', "DTD"),
        (b'<!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>', "DTD"),
        (b'<r xmlns:xi="http://www.w3.org/2001/XInclude"><xi:include href="file:///etc/passwd"/></r>', "XInclude"),
        (b'<r><a></r>', "malformed"),
        (b'<r a="1" a="2"/>', "malformed"),
        (b'<r><p:x/></r>', "malformed"),
        (b'\xff\xfe<r/>', "UTF-8"),
        ('<?xml version="1.0" encoding="ISO-8859-1"?><r>Café</r>'.encode(), "UTF-8"),
        (b'<r>\x00</r>', "NUL"),
    ],
)
def test_unsafe_or_malformed_xml_is_rejected_without_recovery(payload, match):
    with pytest.raises(SecFilingParseError, match=match):
        parse_sec_filing_document(payload, document_name="unsafe.xml")


@pytest.mark.parametrize("encoding", ["ASCII", "us-ascii"])
def test_ascii_xml_declarations_are_admitted_for_ascii_payloads(encoding):
    content = f'<?xml version="1.0" encoding="{encoding}"?>'.encode() + _instance(
        '<ex:F contextRef="c" unitRef="u" decimals="0">1</ex:F>'
    )
    result = parse_sec_filing_document(content, document_name="ascii-declaration.xml")

    assert result["facts"][0]["normalized_value"] == "1"


@pytest.mark.parametrize(
    "payload",
    [
        b'<?xml version="1.0" encoding="ASCII"?><r>Caf\xc3\xa9</r>',
        b'<?xml version="1.0" encoding="us-ascii"?><r>Caf\xe9</r>',
    ],
)
def test_ascii_xml_declarations_reject_contradictory_or_non_utf8_payloads(payload):
    with pytest.raises(SecFilingParseError, match="UTF-8|ASCII"):
        parse_sec_filing_document(payload, document_name="ascii-contradiction.xml")


def test_qname_valued_attributes_must_be_bound():
    content = _inline('<ix:nonNumeric name="missing:Fact" contextRef="c">x</ix:nonNumeric>')
    with pytest.raises(SecFilingParseError, match="unbound QName"):
        parse_sec_filing_document(content, document_name="unbound.xhtml")


@pytest.mark.parametrize(
    ("body", "continuations", "match"),
    [
        ('<ix:nonNumeric name="ex:F" contextRef="c" continuedAt="missing">x</ix:nonNumeric>', "", "missing continuation"),
        ('<ix:nonNumeric name="ex:F" contextRef="c" continuedAt="a">x</ix:nonNumeric>', '<ix:continuation id="a" continuedAt="a">a</ix:continuation>', "cycle"),
        ('<ix:nonNumeric name="ex:F" contextRef="c" continuedAt="a">x</ix:nonNumeric><ix:nonNumeric name="ex:G" contextRef="c" continuedAt="a">y</ix:nonNumeric>', '<ix:continuation id="a">a</ix:continuation>', "shared"),
        ('<ix:nonNumeric name="ex:F" contextRef="c">x</ix:nonNumeric>', '<ix:continuation id="a">a</ix:continuation>', "orphan"),
        ('<ix:nonNumeric name="ex:F" contextRef="c" continuedAt="a">x</ix:nonNumeric>', '<ix:continuation id="a" continuedAt="missing">a</ix:continuation>', "missing continuation"),
        ('<ix:nonNumeric name="ex:F" contextRef="missing">x</ix:nonNumeric>', "", "missing context"),
        ('<ix:nonFraction name="ex:F" contextRef="c" unitRef="missing">1</ix:nonFraction>', "", "missing unit"),
    ],
)
def test_invalid_references_and_continuation_graphs_fail_closed(body, continuations, match):
    with pytest.raises(SecFilingParseError, match=match):
        parse_sec_filing_document(_inline(body, continuations=continuations), document_name="refs.xhtml")


def test_duplicate_context_unit_continuation_and_fact_ids_are_rejected():
    duplicate_context = _instance("", resources='''
      <xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context>
      <xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context>''')
    with pytest.raises(SecFilingParseError, match="duplicate context"):
        parse_sec_filing_document(duplicate_context, document_name="duplicate.xml")

    duplicate_unit = _instance("", resources='''
      <xbrli:unit id="u"><xbrli:measure>ex:USD</xbrli:measure></xbrli:unit>
      <xbrli:unit id="u"><xbrli:measure>ex:shares</xbrli:measure></xbrli:unit>''')
    with pytest.raises(SecFilingParseError, match="duplicate unit"):
        parse_sec_filing_document(duplicate_unit, document_name="duplicate-unit.xml")

    duplicate_continuation = _inline(
        '<ix:nonNumeric name="ex:F" contextRef="c" continuedAt="a">x</ix:nonNumeric>',
        continuations='<ix:continuation id="a">a</ix:continuation><ix:continuation id="a">b</ix:continuation>',
    )
    with pytest.raises(SecFilingParseError, match="duplicate"):
        parse_sec_filing_document(duplicate_continuation, document_name="duplicate.xhtml")

    content = _instance('<ex:F id="same" contextRef="c">x</ex:F><ex:G id="same" contextRef="c">y</ex:G>')
    # Expat does not type ID attributes without a DTD, so the independent result
    # validator is the final local-identity boundary.
    with pytest.raises(SecFilingParseError, match="duplicate fact"):
        parse_sec_filing_document(content, document_name="facts.xml")


@pytest.mark.parametrize(
    ("limit", "value", "content", "match"),
    [
        ("max_bytes", 10, b"<root>12345</root>", "byte limit"),
        ("max_nodes", 1, b"<root><child/></root>", "node limit"),
        ("max_depth", 1, b"<root><child/></root>", "depth limit"),
        ("max_attributes_per_element", 1, b'<root a="1" b="2"/>', "attribute limit"),
        ("max_total_attributes", 1, b'<root a="1"><child b="2"/></root>', "attribute limit"),
        ("max_text_bytes", 2, b"<root>abc</root>", "text limit"),
        ("max_contexts", 1, _instance("", resources='''<xbrli:context id="a"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context><xbrli:context id="b"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context>'''), "context limit"),
        ("max_units", 1, _instance("", resources='<xbrli:unit id="a"><xbrli:measure>ex:USD</xbrli:measure></xbrli:unit><xbrli:unit id="b"><xbrli:measure>ex:shares</xbrli:measure></xbrli:unit>'), "unit limit"),
        ("max_facts", 1, _instance('<ex:F contextRef="c">x</ex:F><ex:G contextRef="c">y</ex:G>'), "fact limit"),
        ("max_continuations", 1, _inline('<ix:nonNumeric name="ex:F" contextRef="c" continuedAt="a">x</ix:nonNumeric><ix:nonNumeric name="ex:G" contextRef="c" continuedAt="b">y</ix:nonNumeric>', continuations='<ix:continuation id="a">a</ix:continuation><ix:continuation id="b">b</ix:continuation>'), "continuation limit"),
        ("max_dimensions_per_context", 1, _instance("", resources='''<xbrli:context xmlns:xbrldi="http://xbrl.org/2006/xbrldi" id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier><xbrli:segment><xbrldi:explicitMember dimension="ex:A">ex:X</xbrldi:explicitMember><xbrldi:explicitMember dimension="ex:B">ex:Y</xbrldi:explicitMember></xbrli:segment></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context>'''), "dimension limit"),
        ("max_abs_scale", 2, _inline('<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" scale="3">1</ix:nonFraction>'), "scale"),
        ("max_output_bytes", 16, b"<root/>", "output byte limit"),
    ],
)
def test_hard_caps_are_fail_closed(monkeypatch, limit, value, content, match):
    lowered = dict(PARSER_LIMITS)
    lowered[limit] = value
    monkeypatch.setattr(parser_module, "PARSER_LIMITS", lowered)
    with pytest.raises(SecFilingParseError, match=match):
        parse_sec_filing_document(content, document_name="cap.xml")


def test_continuation_chain_depth_cap(monkeypatch):
    lowered = dict(PARSER_LIMITS)
    lowered["max_continuation_chain"] = 1
    monkeypatch.setattr(parser_module, "PARSER_LIMITS", lowered)
    content = _inline(
        '<ix:nonNumeric name="ex:F" contextRef="c" continuedAt="a">x</ix:nonNumeric>',
        continuations='<ix:continuation id="a" continuedAt="b">a</ix:continuation><ix:continuation id="b">b</ix:continuation>',
    )
    with pytest.raises(SecFilingParseError, match="chain limit"):
        parse_sec_filing_document(content, document_name="deep.xhtml")


def test_validator_rejects_shape_order_reference_coverage_and_value_forgeries():
    content = _instance('<ex:F contextRef="c" unitRef="u" decimals="0">10</ex:F>')
    result = parse_sec_filing_document(content, document_name="canonical.xml")
    mutations = []
    extra = deepcopy(result); extra["invented"] = True; mutations.append(extra)
    order = deepcopy(result); order["facts"][0]["source_span"]["end"] = order["facts"][0]["source_span"]["start"]; mutations.append(order)
    reference = deepcopy(result); reference["facts"][0]["context_ref"] = "missing"; mutations.append(reference)
    coverage = deepcopy(result); coverage["coverage"]["fact_count"] = 99; mutations.append(coverage)
    value = deepcopy(result); value["facts"][0]["normalized_value"] = "11"; mutations.append(value)
    registry = deepcopy(result); registry["parser"]["transform_registry"].reverse(); mutations.append(registry)
    for forged in mutations:
        with pytest.raises(SecFilingParseError):
            validate_sec_filing_parse_result(forged)


def test_source_replay_rejects_canonical_result_forgery_and_wrong_bytes():
    content = _instance('<ex:F contextRef="c">truth</ex:F>')
    result = parse_sec_filing_document(content, document_name="replay.xml")
    forged = deepcopy(result)
    forged["facts"][0]["raw_value"] = "lie"
    forged["facts"][0]["transformed_value"] = "lie"
    forged["facts"][0]["normalized_value"] = "lie"
    # It is locally self-consistent, but exact-byte replay defeats the forgery.
    validate_sec_filing_parse_result(forged)
    with pytest.raises(SecFilingParseError, match="canonical source replay"):
        validate_sec_filing_parse_result(forged, source_content=content)
    with pytest.raises(SecFilingParseError, match="source witness"):
        validate_sec_filing_parse_result(result, source_content=content + b" ")


def test_parser_performs_no_open_or_socket_calls(monkeypatch):
    content = _instance('<ex:F contextRef="c">offline</ex:F>')

    def forbidden(*_args, **_kwargs):
        raise AssertionError("I/O attempted")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    result = parse_sec_filing_document(content, document_name="offline.xml")
    assert result["facts"][0]["normalized_value"] == "offline"


# ---------------------------------------------------------------------------
# Structural XBRL / Inline XBRL regressions.  These are intentionally not
# convenience-parser tests: a filing which cannot meet the narrow evidence
# contract must fail closed (or advertise incomplete coverage), not be
# accepted by descendant scans and labelled complete.


@pytest.mark.parametrize(
    "resources",
    [
        # entity and period must be direct, ordered children of context.
        '''<xbrli:context id="c"><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity></xbrli:context>''',
        '''<xbrli:context id="c"><ex:wrapper><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity></ex:wrapper><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>''',
        # identifier is direct to entity; a descendant search must not rescue it.
        '''<xbrli:context id="c"><xbrli:entity><ex:wrapper><xbrli:identifier scheme="s">1</xbrli:identifier></ex:wrapper></xbrli:entity><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>''',
        # scenario follows period and cannot be a nested surprise element.
        '''<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:scenario/><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>''',
        '''<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><ex:wrapper><xbrli:instant>2025-12-31</xbrli:instant></ex:wrapper></xbrli:period></xbrli:context>''',
        # Period content is an exact choice, with valid dates and chronology.
        '''<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>not-a-date</xbrli:instant></xbrli:period></xbrli:context>''',
        '''<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:startDate>2025-12-31</xbrli:startDate><xbrli:endDate>2024-12-31</xbrli:endDate></xbrli:period></xbrli:context>''',
    ],
)
def test_context_grammar_is_direct_ordered_and_temporally_valid(resources):
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(_instance("", resources=resources), document_name="bad-context.xml")


def test_same_day_date_only_duration_is_valid_but_zero_length_datetime_is_not() -> None:
    date_only = '''<xbrli:context id="same-day"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:startDate>2016-08-30</xbrli:startDate><xbrli:endDate>2016-08-30</xbrli:endDate></xbrli:period></xbrli:context>'''
    content = _instance("", resources=date_only)
    parsed = parse_sec_filing_document(content, document_name="same-day-duration.xml")
    assert parsed["contexts"][0]["period"] == {
        "kind": "duration",
        "instant_date": None,
        "start_date": "2016-08-30",
        "end_date": "2016-08-30",
        "source_span": parsed["contexts"][0]["period"]["source_span"],
    }
    validate_sec_filing_parse_result(parsed, source_content=content)

    zero_length_datetime = date_only.replace(
        "2016-08-30</xbrli:startDate><xbrli:endDate>2016-08-30",
        "2016-08-30T00:00:00</xbrli:startDate><xbrli:endDate>2016-08-30T00:00:00",
    )
    with pytest.raises(SecFilingParseError, match="valid XBRL interval"):
        parse_sec_filing_document(
            _instance("", resources=zero_length_datetime),
            document_name="zero-length-datetime-duration.xml",
        )


@pytest.mark.parametrize(
    "resources",
    [
        # A segment may only appear under entity, after the direct identifier.
        '''<xbrli:context id="c"><xbrli:entity><xbrli:segment/><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context>''',
        # Typed dimensions carry exactly one element child and no free text.
        '''<xbrli:context xmlns:xbrldi="http://xbrl.org/2006/xbrldi" id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier><xbrli:segment><xbrldi:typedMember dimension="ex:A">stray<ex:One/><ex:Two/></xbrldi:typedMember></xbrli:segment></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context>''',
    ],
)
def test_context_segment_and_dimension_grammar_is_not_descendant_based(resources):
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(_instance("", resources=resources), document_name="bad-dimension.xml")


def test_nested_dimension_is_not_promoted_and_makes_its_container_partial():
    resources = '''<xbrli:context xmlns:xbrldi="http://xbrl.org/2006/xbrldi" id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier><xbrli:segment><ex:wrap><xbrldi:explicitMember dimension="ex:A">ex:M</xbrldi:explicitMember></ex:wrap></xbrli:segment></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context>'''
    result = parse_sec_filing_document(
        _instance("", resources=resources), document_name="nested-dimension.xml"
    )
    context = result["contexts"][0]
    assert context["dimensions"] == []
    assert context["segment_content_status"] == "partial"
    assert result["coverage"]["unknown_segment_content_count"] == 1


def test_opaque_segment_and_scenario_content_is_explicitly_partial_not_complete():
    resources = '''
      <xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier><xbrli:segment><ex:OpaqueSegment>vendor data</ex:OpaqueSegment></xbrli:segment></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period><xbrli:scenario><ex:OpaqueScenario>vendor data</ex:OpaqueScenario></xbrli:scenario></xbrli:context>
    '''
    result = parse_sec_filing_document(_instance("", resources=resources), document_name="opaque-context.xml")
    context = result["contexts"][0]
    assert context["segment_content_status"] == "partial"
    assert context["scenario_content_status"] == "partial"
    assert result["coverage"]["unknown_segment_content_count"] == 1
    assert result["coverage"]["unknown_scenario_content_count"] == 1


@pytest.mark.parametrize(
    "unit_xml",
    [
        '<xbrli:unit id="u"><ex:wrapper><xbrli:measure>ex:USD</xbrli:measure></ex:wrapper></xbrli:unit>',
        '<xbrli:unit id="u"><xbrli:measure>ex:USD</xbrli:measure><xbrli:divide><xbrli:unitNumerator><xbrli:measure>ex:shares</xbrli:measure></xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>ex:days</xbrli:measure></xbrli:unitDenominator></xbrli:divide></xbrli:unit>',
        '<xbrli:unit id="u"><xbrli:divide><xbrli:unitNumerator><ex:wrapper><xbrli:measure>ex:USD</xbrli:measure></ex:wrapper></xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>ex:shares</xbrli:measure></xbrli:unitDenominator></xbrli:divide></xbrli:unit>',
        '<xbrli:unit id="u"><xbrli:divide><xbrli:unitNumerator><xbrli:measure>ex:USD</xbrli:measure></xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>ex:USD</xbrli:measure></xbrli:unitDenominator></xbrli:divide></xbrli:unit>',
    ],
)
def test_unit_and_divide_grammar_is_exact_and_cannot_cancel_measures(unit_xml):
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(_instance("", resources=unit_xml), document_name="bad-unit.xml")


@pytest.mark.parametrize(
    "lexical",
    ["ex:bad:name", "ex:bad!", ":Fact", "ex:"],
)
def test_qname_valued_fields_require_lexically_valid_single_colon_qnames(lexical):
    content = _inline(f'<ix:nonNumeric name="{lexical}" contextRef="c">x</ix:nonNumeric>')
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(content, document_name="bad-qname.xhtml")


@pytest.mark.parametrize("bad_id", ["1starts-with-digit", "contains space", ""])
def test_local_xbrl_ids_are_xml_id_lexical_values_not_just_trimmed_text(bad_id):
    resources = f'''<xbrli:context id="{bad_id}"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context>'''
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(_instance("", resources=resources), document_name="bad-id.xml")


def test_mixed_inline_versions_and_invalid_header_resource_hidden_placement_fail_closed():
    mixed = f'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="{IX}" xmlns:old="http://www.xbrl.org/2008/inlineXBRL" xmlns:xbrli="{XBRLI}" xmlns:ex="urn:example"><head></head><body><ix:header><ix:resources><xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context></ix:resources></ix:header><old:nonNumeric name="ex:F" contextRef="c">x</old:nonNumeric></body></html>'''.encode()
    resources_in_body = f'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="{IX}" xmlns:xbrli="{XBRLI}" xmlns:ex="urn:example"><head></head><body><ix:resources><xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context></ix:resources><ix:nonNumeric name="ex:F" contextRef="c">x</ix:nonNumeric></body></html>'''.encode()
    hidden_in_body = _inline('<ix:hidden><ix:nonNumeric name="ex:F" contextRef="c">x</ix:nonNumeric></ix:hidden>')
    for content in (mixed, resources_in_body, hidden_in_body):
        with pytest.raises(SecFilingParseError):
            parse_sec_filing_document(content, document_name="bad-inline-placement.xhtml")


def test_inline_profile_requires_xhtml_root_and_rejects_unmodeled_ix_semantics():
    non_xhtml_root = _inline(
        '<ix:nonNumeric name="ex:F" contextRef="c">x</ix:nonNumeric>'
    ).replace(
        b'<html xmlns="http://www.w3.org/1999/xhtml"',
        b'<root xmlns="urn:not-xhtml"',
        1,
    ).replace(b"</html>", b"</root>", 1)
    unknown_ix = _inline(
        '<ix:mystery/><ix:nonNumeric name="ex:F" contextRef="c">x</ix:nonNumeric>'
    )
    misplaced_references = _inline(
        '<ix:references/><ix:nonNumeric name="ex:F" contextRef="c">x</ix:nonNumeric>'
    )

    for content in (non_xhtml_root, unknown_ix, misplaced_references):
        with pytest.raises(SecFilingParseError):
            parse_sec_filing_document(content, document_name="unsupported-inline.xhtml")


def test_native_negative_fact_is_canonical_but_inline_value_attributes_are_rejected():
    negative = _instance('<ex:F contextRef="c" unitRef="u" decimals="0">-1</ex:F>')
    result = parse_sec_filing_document(negative, document_name="native-negative.xml")
    assert result["facts"][0]["normalized_value"] == "-1"
    assert result["facts"][0]["status"] == "available"
    assert result["coverage"]["fact_inventory_complete"] is False

    for attrs in ('sign="-"', 'scale="3"', 'format="ex:made-up"'):
        transformed_native = _instance(f'<ex:F contextRef="c" unitRef="u" decimals="0" {attrs}>1</ex:F>')
        with pytest.raises(SecFilingParseError):
            parse_sec_filing_document(transformed_native, document_name="native-inline-attribute.xml")


def test_non_xbrl_xml_and_native_xbrl_do_not_overclaim_inventory_or_reference_coverage():
    other = parse_sec_filing_document(b"<root><child/></root>", document_name="other.xml")
    assert other["document"]["kind"] == "other_xml"
    assert other["coverage"]["fact_inventory_complete"] is False
    assert other["coverage"]["context_references_complete"] is False
    assert other["coverage"]["unit_references_complete"] is False
    assert other["coverage"]["taxonomy_validation_complete"] is False

    native = parse_sec_filing_document(_instance('<ex:Text contextRef="c">reported</ex:Text>'), document_name="native.xml")
    assert native["document"]["kind"] == "xbrl_instance"
    assert native["coverage"]["fact_inventory_complete"] is False
    assert native["coverage"]["taxonomy_validation_complete"] is False


@pytest.mark.parametrize("raw", ["1,2", "1,2,3", "1 2", "1\u00a02"])
def test_unformatted_inline_numeric_does_not_guess_grouping_or_whitespace(raw):
    fact = parse_sec_filing_document(
        _inline(f'<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0">{raw}</ix:nonFraction>'),
        document_name="identity-numeric.xhtml",
    )["facts"][0]
    assert fact["status"] == "invalid_value"
    assert fact["transformed_value"] is None
    assert fact["normalized_value"] is None


@pytest.mark.parametrize("raw", ["١٢٣", "１２３"])
def test_numeric_lexical_profiles_do_not_widen_ascii_digits(raw):
    fact = parse_sec_filing_document(
        _inline(
            f'<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0">'
            f"{raw}</ix:nonFraction>"
        ),
        document_name="unicode-digits.xhtml",
    )["facts"][0]
    assert fact["status"] == "invalid_value"
    assert fact["normalized_value"] is None


@pytest.mark.parametrize(
    ("format_value", "raw"),
    [
        ("i3:numdotdecimal", "12,34.5"),
        ("i3:numdotdecimal", "1,234,56.7"),
        ("i3:numcommadecimal", "12.34,5"),
        ("i4:num-dot-decimal", "1.234,5"),
        ("i4:num-comma-decimal", "1,234.5"),
        ("i4:num-dot-decimal", "1\u202f234.5"),
        ("i4:num-comma-decimal", "1\u202f234,5"),
    ],
)
def test_numeric_transform_grouping_and_decimal_separators_are_not_guessed(format_value, raw):
    fact = parse_sec_filing_document(
        _inline(f'<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" format="{format_value}">{raw}</ix:nonFraction>'),
        document_name="bad-transform.xhtml",
    )["facts"][0]
    assert fact["status"] == "invalid_value"
    assert fact["normalized_value"] is None


@pytest.mark.parametrize("format_value", ["i3:nocontent", "i4:fixed-empty"])
def test_string_empty_transforms_never_release_a_numeric_fact_without_a_value(format_value):
    fact = parse_sec_filing_document(
        _inline(
            f'<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" '
            f'format="{format_value}">ignored</ix:nonFraction>'
        ),
        document_name="numeric-empty-transform.xhtml",
    )["facts"][0]
    assert fact["status"] == "invalid_value"
    assert fact["transformed_value"] is None
    assert fact["normalized_value"] is None


@pytest.mark.parametrize("raw", ["", "\u2212", "not-a-dash"])
def test_trr3_zerodash_is_the_exact_registry_dash_set(raw):
    fact = parse_sec_filing_document(
        _inline(f'<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" format="i3:zerodash">{raw}</ix:nonFraction>'),
        document_name="bad-zerodash.xhtml",
    )["facts"][0]
    assert fact["status"] == "invalid_value"
    assert fact["normalized_value"] is None


def test_trr3_zerodash_accepts_figure_dash_and_fixed_transforms_accept_any_text():
    figure_dash = parse_sec_filing_document(
        _inline('<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" format="i3:zerodash">‒</ix:nonFraction>'),
        document_name="figure-dash.xhtml",
    )["facts"][0]
    assert figure_dash["normalized_value"] == "0"

    zero = parse_sec_filing_document(
        _inline('<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" format="i4:fixed-zero">anything at all</ix:nonFraction>'),
        document_name="fixed-zero.xhtml",
    )["facts"][0]
    empty = parse_sec_filing_document(
        _inline('<ix:nonNumeric name="ex:F" contextRef="c" format="i4:fixed-empty">anything at all</ix:nonNumeric>'),
        document_name="fixed-empty.xhtml",
    )["facts"][0]
    no_content = parse_sec_filing_document(
        _inline('<ix:nonNumeric name="ex:F" contextRef="c" format="i3:nocontent">anything at all</ix:nonNumeric>'),
        document_name="no-content.xhtml",
    )["facts"][0]
    assert zero["normalized_value"] == "0"
    assert empty["normalized_value"] == ""
    assert no_content["normalized_value"] == ""


def test_inline_sign_is_only_negative_not_plus():
    content = _inline('<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" sign="+">1</ix:nonFraction>')
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(content, document_name="plus-sign.xhtml")


@pytest.mark.parametrize(
    "body,continuations",
    [
        ('<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" continuedAt="a">1</ix:nonFraction>', '<ix:continuation id="a">x</ix:continuation>'),
        ('<ix:fraction name="ex:F" contextRef="c" unitRef="u" continuedAt="a"><ix:numerator>1</ix:numerator><ix:denominator>2</ix:denominator></ix:fraction>', '<ix:continuation id="a">x</ix:continuation>'),
        ('<ix:nonNumeric name="ex:F" contextRef="c" continuedAt="a">x</ix:nonNumeric>', '<ix:hidden><ix:continuation id="a">x</ix:continuation></ix:hidden>'),
    ],
)
def test_only_nonnumeric_facts_can_continue_and_continuations_cannot_be_hidden(body, continuations):
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(_inline(body, continuations=continuations), document_name="bad-continuation.xhtml")


def test_exclude_is_owner_relative_so_a_nested_fact_retains_its_own_text():
    content = _inline(
        '<ix:nonNumeric id="outer" name="ex:Outer" contextRef="c">before '
        '<ix:exclude>drop <ix:nonNumeric id="inner" name="ex:Inner" contextRef="c">inner</ix:nonNumeric></ix:exclude>'
        ' after</ix:nonNumeric>'
    )
    facts = {fact["fact_id"]: fact for fact in parse_sec_filing_document(content, document_name="owner-exclude.xhtml")["facts"]}
    assert facts["outer"]["raw_value"] == "before  after"
    assert facts["inner"]["raw_value"] == "inner"


@pytest.mark.parametrize(
    "body",
    [
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" xsi:nil="true">1</ix:nonFraction>',
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" xsi:nil="true"/>',
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u">1</ix:nonFraction>',
        '<ix:nonNumeric name="ex:F" contextRef="c" decimals="0">text</ix:nonNumeric>',
        '<ix:nonNumeric name="ex:F" contextRef="c" unitRef="u">text</ix:nonNumeric>',
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" precision="0">1</ix:nonFraction>',
    ],
)
def test_nil_accuracy_and_nonnumeric_attribute_combinations_fail_closed(body):
    content = _inline(
        body,
        resources=f'''<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context><xbrli:unit id="u"><xbrli:measure>ex:USD</xbrli:measure></xbrli:unit>''',
    )
    # Add xsi only to this intentionally local helper construction.
    content = content.replace(b'xmlns:i4=', b'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:i4=', 1)
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(content, document_name="bad-nil.xhtml")


@pytest.mark.parametrize("parent_attrs", [' format="i3:numdotdecimal"', ' scale="2"', ' sign="-"'])
def test_fraction_level_numeric_attributes_are_not_silently_applied(parent_attrs):
    body = f'<ix:fraction name="ex:F" contextRef="c" unitRef="u"{parent_attrs}><ix:numerator>1</ix:numerator><ix:denominator>2</ix:denominator></ix:fraction>'
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(_inline(body), document_name="bad-fraction.xhtml")


def test_fraction_component_transforms_are_explicitly_rejected_until_they_have_a_canonical_contract():
    content = _inline(
        '<ix:fraction id="f" name="ex:F" contextRef="c" unitRef="u">'
        '<ix:numerator format="i3:numdotdecimal" scale="2" sign="-">1,234</ix:numerator>'
        '<ix:denominator format="i4:num-dot-decimal">2</ix:denominator>'
        '</ix:fraction>'
    )
    # A profile may later add component-level transform support, but it must
    # do so as a separately specified wire contract.  Silently treating these
    # values as identity numerics is worse than rejecting the member.
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(content, document_name="fraction-components.xhtml")


def test_validator_rejects_forged_sign_accuracy_and_numeric_status_combinations():
    content = _inline('<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0">1</ix:nonFraction>')
    canonical = parse_sec_filing_document(content, document_name="validator-value.xhtml")
    forged_sign = deepcopy(canonical)
    forged_sign["facts"][0].update({"sign": "x", "status": "invalid_value", "transformed_value": None, "normalized_value": None})
    forged_accuracy = deepcopy(canonical)
    forged_accuracy["facts"][0]["precision"] = "0"
    forged_value = deepcopy(canonical)
    forged_value["facts"][0].update({"raw_value": "1,2", "transformed_value": "12", "normalized_value": "12"})
    for forged in (forged_sign, forged_accuracy, forged_value):
        with pytest.raises(SecFilingParseError):
            validate_sec_filing_parse_result(forged)


def test_validation_separates_observed_runtime_patch_provenance_from_semantic_fingerprint():
    content = _instance('<ex:F contextRef="c" unitRef="u" decimals="0">1</ex:F>')
    canonical = parse_sec_filing_document(content, document_name="runtime-provenance.xml")
    assert re.fullmatch(r"[a-f0-9]{64}", canonical["parser"]["algorithm_fingerprint"])

    observed_runtime_drift = deepcopy(canonical)
    observed_runtime_drift["parser"]["library_version"] = "python-99.99.99"
    observed_runtime_drift["parser"]["xml_library_version"] = "expat_99.99.99"
    # These fields identify the observed local runtime only.  They are useful
    # provenance, but cannot redefine the deterministic parser contract.
    validate_sec_filing_parse_result(observed_runtime_drift)
    validate_sec_filing_parse_result(observed_runtime_drift, source_content=content)

    semantic_drift = deepcopy(canonical)
    semantic_drift["parser"]["algorithm_fingerprint"] = "0" * 64
    with pytest.raises(SecFilingParseError):
        validate_sec_filing_parse_result(semantic_drift)
    with pytest.raises(SecFilingParseError):
        validate_sec_filing_parse_result(semantic_drift, source_content=content)


def test_namespace_declarations_count_against_attribute_admission_caps(monkeypatch):
    lowered = dict(PARSER_LIMITS)
    lowered["max_attributes_per_element"] = 32
    lowered["max_total_attributes"] = 32
    monkeypatch.setattr(parser_module, "PARSER_LIMITS", lowered)
    namespaces = " ".join(f'xmlns:p{index}="urn:example:{index}"' for index in range(100))
    with pytest.raises(SecFilingParseError, match="attribute|namespace declaration"):
        parse_sec_filing_document(f"<root {namespaces}/>".encode(), document_name="namespace-cap.xml")


def test_declared_text_event_cap_is_fail_closed(monkeypatch):
    if "max_text_events" not in PARSER_LIMITS:
        pytest.skip("text event count is not part of the public parser admission profile")
    lowered = dict(PARSER_LIMITS)
    lowered["max_text_events"] = 2
    monkeypatch.setattr(parser_module, "PARSER_LIMITS", lowered)
    with pytest.raises(SecFilingParseError, match="text event"):
        parse_sec_filing_document(b"<root>a<child/>b<child/>c</root>", document_name="text-event-cap.xml")


def test_header_uses_the_ixbrl11_body_placement_and_ordered_direct_content_model():
    fact = '<ix:nonNumeric name="ex:F" contextRef="c">x</ix:nonNumeric>'
    header_in_head = _inline(fact).replace(
        b"<head></head><body><ix:header>", b"<head><ix:header>", 1
    ).replace(b"</ix:header><ix:nonNumeric", b"</ix:header></head><body><ix:nonNumeric", 1)
    duplicate_hidden = _inline(fact).replace(
        b"<ix:header><ix:resources>",
        b'<ix:header><ix:hidden><ix:nonNumeric name="ex:H" contextRef="c">one</ix:nonNumeric></ix:hidden>'
        b'<ix:hidden><ix:nonNumeric name="ex:I" contextRef="c">two</ix:nonNumeric></ix:hidden><ix:resources>',
        1,
    )
    duplicate_resources = _inline(fact).replace(
        b"<ix:header><ix:resources>", b"<ix:header><ix:resources></ix:resources><ix:resources>", 1
    )
    resources_before_hidden = _inline(fact).replace(
        b"</ix:resources></ix:header>",
        b'</ix:resources><ix:hidden><ix:nonNumeric name="ex:H" contextRef="c">h</ix:nonNumeric></ix:hidden></ix:header>',
        1,
    )
    for index, content in enumerate((header_in_head, duplicate_hidden, duplicate_resources, resources_before_hidden)):
        with pytest.raises(SecFilingParseError):
            parse_sec_filing_document(content, document_name=f"bad-header-{index}.xhtml")


@pytest.mark.parametrize(
    "body",
    [
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0">1<ix:nonFraction name="ex:G" contextRef="c" unitRef="u" decimals="0">2</ix:nonFraction></ix:nonFraction>',
        '<ix:fraction name="ex:F" contextRef="c" unitRef="u"><ix:numerator><ix:nonFraction name="ex:G" contextRef="c" unitRef="u" decimals="0">1</ix:nonFraction></ix:numerator><ix:denominator>2</ix:denominator></ix:fraction>',
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0">1<b xmlns="http://www.w3.org/1999/xhtml">2</b></ix:nonFraction>',
    ],
)
def test_numeric_facts_do_not_concatenate_nested_fact_or_foreign_markup_values(body):
    with pytest.raises(SecFilingParseError, match="nested|child elements"):
        parse_sec_filing_document(_inline(body), document_name="nested-numeric.xhtml")


def test_exact_workiva_nonfraction_wrapper_preserves_both_numeric_facts_and_shared_lexical_text():
    resources = f'''
      <xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>
      <xbrli:context id="c2"><xbrli:entity><xbrli:identifier scheme="s">2</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period></xbrli:context>
      <xbrli:unit id="u"><xbrli:measure>ex:USD</xbrli:measure></xbrli:unit>
    '''
    content = _inline(
        '<ix:nonFraction id="wrapper" name="ex:Wrapper" contextRef="c" unitRef="u" decimals="0" format="i3:numdotdecimal">'
        '\n  <ix:nonFraction id="leaf" name="ex:Leaf" contextRef="c2" unitRef="u" decimals="0" format="i3:numdotdecimal">1,234.5</ix:nonFraction>\n'
        '</ix:nonFraction>',
        resources=resources,
    )

    facts = parse_sec_filing_document(content, document_name="workiva-wrapper.xhtml")["facts"]

    assert [(fact["fact_id"], fact["concept_qname"], fact["context_ref"]) for fact in facts] == [
        ("wrapper", "{urn:example}Wrapper", "c"),
        ("leaf", "{urn:example}Leaf", "c2"),
    ]
    assert [fact["raw_value"] for fact in facts] == ["1,234.5", "1,234.5"]
    assert [fact["normalized_value"] for fact in facts] == ["1234.5", "1234.5"]
    assert facts[0]["text_spans"] == facts[1]["text_spans"]
    validate_sec_filing_parse_result(
        parse_sec_filing_document(content, document_name="workiva-wrapper.xhtml"), source_content=content
    )


@pytest.mark.parametrize(
    "body",
    [
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0">1<ix:nonFraction name="ex:G" contextRef="c" unitRef="u" decimals="0">2</ix:nonFraction></ix:nonFraction>',
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0"><ix:nonFraction name="ex:G" contextRef="c" unitRef="u" decimals="0">1</ix:nonFraction><ix:nonFraction name="ex:H" contextRef="c" unitRef="u" decimals="0">2</ix:nonFraction></ix:nonFraction>',
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0"><b xmlns="http://www.w3.org/1999/xhtml">1</b></ix:nonFraction>',
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0"><ix:fraction name="ex:G" contextRef="c" unitRef="u"><ix:numerator>1</ix:numerator><ix:denominator>2</ix:denominator></ix:fraction></ix:nonFraction>',
    ],
)
def test_nonfraction_numeric_nesting_admits_no_mixed_or_nonwrapper_shapes(body):
    with pytest.raises(SecFilingParseError, match="wrapper|nested"):
        parse_sec_filing_document(_inline(body), document_name="invalid-numeric-wrapper.xhtml")


def test_exclude_is_limited_to_nonnumeric_and_continuation_owners():
    fact = '<ix:nonNumeric id="f" name="ex:F" contextRef="c" continuedAt="a">A</ix:nonNumeric>'
    continuation = '<ix:continuation id="a">B<ix:exclude>drop</ix:exclude>C</ix:continuation>'
    content = _inline(fact, continuations=continuation)
    result = parse_sec_filing_document(content, document_name="continuation-exclude.xhtml")
    parsed = result["facts"][0]
    assert parsed["raw_value"] == "ABC"
    excluded = parsed["excluded_text_spans"]
    assert len(excluded) == 1
    assert b"".join(content[span["start"] : span["end"]] for span in excluded) == b"drop"

    invalid = (
        '<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0">1<ix:exclude>x</ix:exclude></ix:nonFraction>',
        '<ix:fraction name="ex:F" contextRef="c" unitRef="u"><ix:numerator>1<ix:exclude>x</ix:exclude></ix:numerator><ix:denominator>2</ix:denominator></ix:fraction>',
        '<ix:exclude>x</ix:exclude>',
    )
    for index, body in enumerate(invalid):
        with pytest.raises(SecFilingParseError, match="exclude"):
            parse_sec_filing_document(_inline(body), document_name=f"invalid-exclude-{index}.xhtml")


def test_inline_document_id_namespace_covers_context_unit_fact_continuation_and_markup():
    duplicate_context_unit = _inline(
        '<ix:nonNumeric name="ex:F" contextRef="c">x</ix:nonNumeric>',
        resources='''<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:forever/></xbrli:period></xbrli:context><xbrli:unit id="c"><xbrli:measure>ex:USD</xbrli:measure></xbrli:unit>''',
    )
    duplicate_fact_continuation = _inline(
        '<ix:nonNumeric id="dup" name="ex:F" contextRef="c" continuedAt="dup">x</ix:nonNumeric>',
        continuations='<ix:continuation id="dup">y</ix:continuation>',
    )
    duplicate_markup_context = _inline('<div id="c">presentation</div><ix:nonNumeric name="ex:F" contextRef="c">x</ix:nonNumeric>')
    for index, content in enumerate((duplicate_context_unit, duplicate_fact_continuation, duplicate_markup_context)):
        with pytest.raises(SecFilingParseError, match="duplicate"):
            parse_sec_filing_document(content, document_name=f"duplicate-global-id-{index}.xhtml")


def test_continuation_preceding_fact_preserves_logical_value_and_witness_order():
    fact = '<ix:nonNumeric id="f" name="ex:F" contextRef="c" continuedAt="a">A</ix:nonNumeric>'
    continuation = '<ix:continuation id="a">B<ix:exclude>X</ix:exclude>C</ix:continuation>'
    content = _inline(fact, continuations=continuation).replace(
        (fact + continuation).encode(), (continuation + fact).encode(), 1
    )
    result = parse_sec_filing_document(content, document_name="continuation-before-fact.xhtml")
    parsed = result["facts"][0]
    assert parsed["raw_value"] == "ABC"
    assert "".join(content[span["start"] : span["end"]].decode() for span in parsed["text_spans"]) == "ABC"
    assert "".join(content[span["start"] : span["end"]].decode() for span in parsed["excluded_text_spans"]) == "X"
    validate_sec_filing_parse_result(result)


def test_continuation_chain_cannot_nest_an_owner_or_link_inside_another_link():
    content = _inline(
        '<ix:nonNumeric name="ex:F" contextRef="c" continuedAt="a">A<ix:continuation id="a">B</ix:continuation></ix:nonNumeric>'
    )
    with pytest.raises(SecFilingParseError, match="ancestor/descendant"):
        parse_sec_filing_document(content, document_name="nested-continuation.xhtml")


@pytest.mark.parametrize("attribute", ["precision", "scale"])
def test_huge_numeric_control_lexicals_fail_closed_without_runtime_integer_leaks(attribute):
    value = "9" * 5000
    content = _inline(
        f'<ix:nonFraction name="ex:F" contextRef="c" unitRef="u" decimals="0" {attribute}="{value}">1</ix:nonFraction>'
    )
    with pytest.raises(SecFilingParseError):
        parse_sec_filing_document(content, document_name=f"huge-{attribute}.xhtml")


def test_validator_replays_accuracy_nil_and_identity_invariants_without_source_bytes():
    numeric = parse_sec_filing_document(
        _inline('<ix:nonFraction id="f" name="ex:F" contextRef="c" unitRef="u" decimals="0">1</ix:nonFraction>'),
        document_name="validator-controls.xhtml",
    )
    nil = parse_sec_filing_document(
        _inline('<ix:nonFraction id="n" name="ex:F" contextRef="c" unitRef="u" xsi:nil="true"/>').replace(
            b"xmlns:i4=", b'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:i4=', 1
        ),
        document_name="validator-nil.xhtml",
    )
    bad_decimals = deepcopy(numeric); bad_decimals["facts"][0]["decimals"] = "oops"
    bad_precision = deepcopy(numeric); bad_precision["facts"][0]["decimals"] = None; bad_precision["facts"][0]["precision"] = "0"
    bad_nil = deepcopy(nil); bad_nil["facts"][0]["raw_value"] = "smuggled"
    bad_root = deepcopy(numeric); bad_root["document"]["root_qname"] = "{urn:fake}root"
    for forged in (bad_decimals, bad_precision, bad_nil, bad_root):
        with pytest.raises(SecFilingParseError):
            validate_sec_filing_parse_result(forged)


# ---------------------------------------------------------------------------
# Inline XBRL 1.1 ix:relationship / ix:footnote admission (D1-ext).  Neither
# element is a fact: relationships are empty resources-only links, footnotes
# are transparent body content, and previously admitted documents must stay
# byte-identical (pinned against the base parser's semantic bytes below).

_FOOTNOTE_ARCROLE = "http://www.xbrl.org/2003/arcrole/fact-footnote"
_FOOTNOTE_ROLE = "http://www.xbrl.org/2003/role/footnote"
_LINK_ROLE = "http://www.xbrl.org/2003/role/link"
_BASE_RESOURCES = f'''
      <xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="s">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>
      <xbrli:unit id="u"><xbrli:measure>ex:USD</xbrli:measure></xbrli:unit>
    '''


def test_relationship_and_footnote_parse_with_transparent_fact_ownership():
    relationship = (
        f'<ix:relationship arcrole="{_FOOTNOTE_ARCROLE}" fromRefs="f1" '
        f'linkRole="{_LINK_ROLE}" toRefs="fn1" order="1"/>'
    )
    footnote_open = f'<ix:footnote id="fn1" footnoteRole="{_FOOTNOTE_ROLE}">'
    footnote_close = "</ix:footnote>"
    fact = '<ix:nonNumeric id="f1" name="ex:F" contextRef="c">revenue</ix:nonNumeric>'
    inner_fact = (
        '<ix:nonFraction id="f2" name="ex:N" contextRef="c" unitRef="u" '
        'decimals="0">7</ix:nonFraction>'
    )
    content = _inline(
        fact + footnote_open + "note " + inner_fact + footnote_close,
        resources=_BASE_RESOURCES + relationship,
    )
    result = parse_sec_filing_document(content, document_name="footnote.xhtml")
    assert result["coverage"]["ix_relationship_count"] == 1
    assert result["coverage"]["ix_footnote_count"] == 1
    assert result["coverage"]["ix_footnote_continuation_count"] == 0
    facts = {item["fact_id"]: item for item in result["facts"]}
    assert facts["f1"]["raw_value"] == "revenue"
    # A footnote is transparent: facts inside it are ordinary facts.
    assert facts["f2"]["raw_value"] == "7"
    assert facts["f2"]["normalized_value"] == "7"
    assert facts["f2"]["hidden"] is False
    validate_sec_filing_parse_result(result, source_content=content)

    # Neutralize the new material at identical byte offsets; the fact records
    # and the 17-key coverage must be exactly what the base parser produced.
    stripped = (
        content.replace(relationship.encode(), b" " * len(relationship), 1)
        .replace(footnote_open.encode(), b"<span" + b" " * (len(footnote_open) - 6) + b">", 1)
        .replace(footnote_close.encode(), b"</span" + b" " * (len(footnote_close) - 7) + b">", 1)
    )
    baseline = parse_sec_filing_document(stripped, document_name="footnote-stripped.xhtml")
    assert len(baseline["coverage"]) == 17
    baseline_facts = {item["fact_id"]: item for item in baseline["facts"]}
    assert facts["f1"] == baseline_facts["f1"]
    assert facts["f2"] == baseline_facts["f2"]


@pytest.mark.parametrize(
    ("resources_suffix", "body_suffix", "match"),
    [
        # fromRefs must resolve to inline fact elements.
        (
            '<ix:relationship fromRefs="missing" toRefs="fn1"/>',
            '<ix:footnote id="fn1">n</ix:footnote>',
            r"ix:relationship fromRefs does not resolve to an inline fact",
        ),
        # toRefs must resolve to an ix:footnote, never to a fact.
        (
            '<ix:relationship fromRefs="f1" toRefs="nofn"/>',
            '<ix:footnote id="fn1">n</ix:footnote>',
            r"ix:relationship toRefs does not resolve to an ix:footnote",
        ),
        (
            '<ix:relationship fromRefs="f1" toRefs="f1"/>',
            '<ix:footnote id="fn1">n</ix:footnote>',
            r"ix:relationship toRefs does not resolve to an ix:footnote",
        ),
        # Only the standard fact-footnote arcrole is admitted.
        (
            f'<ix:relationship arcrole="http://example.com/other" fromRefs="f1" toRefs="fn1"/>',
            '<ix:footnote id="fn1">n</ix:footnote>',
            r"ix:relationship has unsupported arcrole",
        ),
        # A relationship carries no content at all.
        (
            '<ix:relationship fromRefs="f1" toRefs="fn1"><span>x</span></ix:relationship>',
            '<ix:footnote id="fn1">n</ix:footnote>',
            r"ix:relationship must be empty",
        ),
        # Footnote attributes are exactly id/footnoteRole/continuedAt.
        (
            '<ix:relationship fromRefs="f1" toRefs="fn1"/>',
            '<ix:footnote id="fn1" bogus="x">n</ix:footnote>',
            r"ix:footnote has unsupported attributes",
        ),
    ],
)
def test_relationship_and_footnote_grammar_fails_closed(resources_suffix, body_suffix, match):
    fact = '<ix:nonNumeric id="f1" name="ex:F" contextRef="c">revenue</ix:nonNumeric>'
    content = _inline(fact + body_suffix, resources=_BASE_RESOURCES + resources_suffix)
    with pytest.raises(SecFilingParseError, match=match):
        parse_sec_filing_document(content, document_name="bad-footnote.xhtml")


def test_relationship_outside_ix_resources_and_unreferenced_footnote_fail_closed():
    fact = '<ix:nonNumeric id="f1" name="ex:F" contextRef="c">revenue</ix:nonNumeric>'
    footnote = '<ix:footnote id="fn1">n</ix:footnote>'
    outside = _inline(
        fact + '<ix:relationship fromRefs="f1" toRefs="fn1"/>' + footnote,
        resources=_BASE_RESOURCES,
    )
    with pytest.raises(SecFilingParseError, match=r"ix:relationship must be a direct child of ix:resources"):
        parse_sec_filing_document(outside, document_name="relationship-in-body.xhtml")

    unreferenced = _inline(fact + footnote, resources=_BASE_RESOURCES)
    with pytest.raises(SecFilingParseError, match=r"ix:footnote is not referenced by any ix:relationship"):
        parse_sec_filing_document(unreferenced, document_name="unreferenced-footnote.xhtml")


def test_footnote_must_not_appear_in_ix_header():
    content = _inline(
        '<ix:nonNumeric id="f1" name="ex:F" contextRef="c">revenue</ix:nonNumeric>',
        resources=_BASE_RESOURCES + '<ix:relationship fromRefs="f1" toRefs="fn1"/>',
    ).replace(
        b"</ix:resources></ix:header>",
        b'</ix:resources><ix:footnote id="fn1">n</ix:footnote></ix:header>',
        1,
    )
    with pytest.raises(SecFilingParseError, match=r"ix:footnote must not appear in ix:header"):
        parse_sec_filing_document(content, document_name="footnote-in-header.xhtml")


def test_footnote_continuation_chains_are_excluded_from_fact_continuations():
    relationship = '<ix:relationship fromRefs="f1" toRefs="fn1"/>'
    footnote = '<ix:footnote id="fn1" continuedAt="fn1c">part one </ix:footnote>'
    continuation = '<ix:continuation id="fn1c">part two</ix:continuation>'
    fact = '<ix:nonNumeric id="f1" name="ex:F" contextRef="c">head</ix:nonNumeric>'
    content = _inline(
        fact + footnote,
        continuations=continuation,
        resources=_BASE_RESOURCES + relationship,
    )
    result = parse_sec_filing_document(content, document_name="footnote-chain.xhtml")
    assert result["continuations"] == []
    assert result["coverage"]["continuation_count"] == 0
    assert result["coverage"]["ix_footnote_continuation_count"] == 1
    validate_sec_filing_parse_result(result, source_content=content)

    # A continuation may not be shared between a fact chain and a footnote chain.
    shared_fact = (
        '<ix:nonNumeric id="f1" name="ex:F" contextRef="c" '
        'continuedAt="c1">head</ix:nonNumeric>'
    )
    shared_footnote = '<ix:footnote id="fn1" continuedAt="c1">part one</ix:footnote>'
    shared_continuation = '<ix:continuation id="c1">tail</ix:continuation>'
    shared = _inline(
        shared_fact + shared_footnote,
        continuations=shared_continuation,
        resources=_BASE_RESOURCES + relationship,
    )
    with pytest.raises(SecFilingParseError, match="shared"):
        parse_sec_filing_document(shared, document_name="shared-chain.xhtml")

    # A footnote continuedAt must name an existing ix:continuation.
    dangling = _inline(
        fact + '<ix:footnote id="fn1" continuedAt="gone">part one</ix:footnote>',
        resources=_BASE_RESOURCES + relationship,
    )
    with pytest.raises(SecFilingParseError, match="footnote references a missing continuation"):
        parse_sec_filing_document(dangling, document_name="dangling-footnote-chain.xhtml")


def test_node_budget_is_raised_to_300k_nodes():
    # 1 root + 299,999 children = 300,000 nodes: admitted at the 300,000
    # budget.  The node check is `len(self.nodes) >= max_nodes` before append,
    # so N nodes are admitted and N + 1 refused.  No text between tags, so no
    # text events.
    within = b"<root>" + b"<span/>" * 299_999 + b"</root>"
    result = parse_sec_filing_document(within, document_name="nodes-within.xml")
    assert result["document"]["kind"] == "other_xml"
    assert len(result["coverage"]) == 17

    beyond = b"<root>" + b"<span/>" * 300_000 + b"</root>"
    with pytest.raises(SecFilingParseError, match="node limit"):
        parse_sec_filing_document(beyond, document_name="nodes-beyond.xml")


def test_b2_cap_literals_are_frozen():
    # The B'2 seat values; every other _HARD_LIMITS key is unchanged and the
    # parser identity (version + fingerprint) must not move with caps.
    assert parser_module._HARD_LIMITS["max_nodes"] == 300_000
    assert parser_module._HARD_LIMITS["max_fact_text_bytes"] == 2 * 1024 * 1024
    assert parser_module._HARD_LIMITS["max_facts"] == 12_000
    assert parser_module._HARD_LIMITS["max_continuation_chain"] == 32
    assert parser_module._HARD_LIMITS["max_output_bytes"] == 64 * 1024 * 1024
    assert SEC_FILING_PARSER_VERSION == "1"


def test_fact_budget_boundary_is_12000():
    # The fact check is `len(facts_nodes) > limits["max_facts"]` after
    # collection, so exactly 12,000 facts are admitted and the 12,001st
    # refuses.  Repeated identical element names are legal: facts carry no
    # name-uniqueness rule (only ids are unique, and these have none).
    within = _instance('<ex:F contextRef="c">x</ex:F>' * 12_000)
    result = parse_sec_filing_document(within, document_name="facts-within.xml")
    assert result["coverage"]["fact_count"] == 12_000

    beyond = _instance('<ex:F contextRef="c">x</ex:F>' * 12_001)
    with pytest.raises(SecFilingParseError, match="fact limit"):
        parse_sec_filing_document(beyond, document_name="facts-beyond.xml")


def test_continuation_chain_boundary_is_32():
    # A chain is counted as the number of ix:continuation elements reachable
    # from the owning fact's continuedAt by following continued_at links (the
    # owning fact itself is not counted).  The root walk checks
    # `len(chain) >= limits["max_continuation_chain"]` before appending each
    # member, so exactly 32 linked continuations are admitted and a 33rd
    # refuses with the chain-limit message.
    def chain_document(count: int) -> bytes:
        continuations = "".join(
            f'<ix:continuation id="c{index}"'
            + (f' continuedAt="c{index + 1}"' if index < count - 1 else "")
            + f">t{index}</ix:continuation>"
            for index in range(count)
        )
        return _inline(
            '<ix:nonNumeric id="f" name="ex:F" contextRef="c" continuedAt="c0">x</ix:nonNumeric>',
            continuations=continuations,
        )

    within = parse_sec_filing_document(chain_document(32), document_name="chain-within.xhtml")
    assert len(within["facts"][0]["continuation_chain"]) == 32

    with pytest.raises(SecFilingParseError, match="chain limit"):
        parse_sec_filing_document(chain_document(33), document_name="chain-beyond.xhtml")


def test_fact_text_boundary_is_2mib():
    # The fact-text check measures the UTF-8 encoding of the joined lexical
    # text value (`len(value.encode("utf-8")) > max_fact_text_bytes`), so an
    # ASCII text of exactly 2 MiB is admitted and one byte more refuses.
    cap = 2 * 1024 * 1024
    within = _inline(f'<ix:nonNumeric name="ex:F" contextRef="c">{"a" * cap}</ix:nonNumeric>')
    result = parse_sec_filing_document(within, document_name="fact-text-within.xhtml")
    assert len(result["facts"][0]["raw_value"].encode("utf-8")) == cap

    beyond = _inline(f'<ix:nonNumeric name="ex:F" contextRef="c">{"a" * (cap + 1)}</ix:nonNumeric>')
    with pytest.raises(SecFilingParseError, match="text byte limit"):
        parse_sec_filing_document(beyond, document_name="fact-text-beyond.xhtml")


def test_output_byte_boundary_is_exact(monkeypatch):
    # The output check measures the canonical JSON encoding of the complete
    # result (`json.dumps(..., sort_keys=True, separators=(",", ":"))` bytes)
    # against max_output_bytes on both the parse and validate paths.  The
    # real-value boundary artifact would be a 64 MiB document, so the boundary
    # is proven at the exact measured length with the cap lowered to it.
    assert parser_module._HARD_LIMITS["max_output_bytes"] == 64 * 1024 * 1024
    content = b"<root/>"
    result = parse_sec_filing_document(content, document_name="output-exact.xml")
    measured = len(
        json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )

    at_cap = dict(PARSER_LIMITS)
    at_cap["max_output_bytes"] = measured
    monkeypatch.setattr(parser_module, "PARSER_LIMITS", at_cap)
    parse_sec_filing_document(content, document_name="output-exact.xml")

    below_cap = dict(PARSER_LIMITS)
    below_cap["max_output_bytes"] = measured - 1
    monkeypatch.setattr(parser_module, "PARSER_LIMITS", below_cap)
    with pytest.raises(SecFilingParseError, match="output byte limit"):
        parse_sec_filing_document(content, document_name="output-beyond.xml")


# Semantic byte pins computed by the BASE parser (version 1, fingerprint
# 95f7e4b7...) for every pinned corpus member it accepts.  The D1-ext change
# must keep each accepted member byte-identical.
_BYTE_IDENTITY_PINS = {
    "fundamental_forensics/aapl_10k_2025/members/aapl-20250927.htm": "7a32e79244ab7138af42b8b679ee9e1043b0a297534884a14d66a5df1be89ed1",
    "fundamental_forensics/aapl_10k_2025/members/aapl-20250927.xsd": "0ee751300128648bb3bfcb47568877153e01a253e3cf9aec3c45577680007fb8",
    "fundamental_forensics/aapl_10k_2025/members/aapl-20250927_cal.xml": "90531b850f7a9f097d86ed426b151c1e8f59dbc4e43238f8d76ed18a8fb519fe",
    "fundamental_forensics/aapl_10k_2025/members/aapl-20250927_def.xml": "039be93ededb56777b0e7620c5b265c558b940685fd6ad548892027274d2beef",
    "fundamental_forensics/aapl_10k_2025/members/aapl-20250927_lab.xml": "253ff7e65e3b86501f59fb0e4a8501cf7284c2feba7f28a863641689590cef7c",
    "fundamental_forensics/aapl_10k_2025/members/aapl-20250927_pre.xml": "7c54fac85534a5d2a63dff5d905985693fe9204215a67dd84e01028f42e77c9d",
    "fundamental_forensics/aapl_10q_2026q3/members/aapl-20260627.htm": "d65c849a700c780533188175ef5bc1d29e0d32f61a0b58e72ea2111e6835f0ff",
    "fundamental_forensics/aapl_10q_2026q3/members/aapl-20260627.xsd": "5f894b33ffadaebd9ad828e14ddcb7b1c77f84128eed7da222ba3f301cde63c0",
    "fundamental_forensics/aapl_10q_2026q3/members/aapl-20260627_cal.xml": "cf0141cb72cfc124c4a50292d5599dfcb63d71da22c199e0f8b1cccad9f9fbe6",
    "fundamental_forensics/aapl_10q_2026q3/members/aapl-20260627_def.xml": "b8e8bade6a2563e10682625938227fdc198d863a2c99069e0428f2da6e4ebe39",
    "fundamental_forensics/aapl_10q_2026q3/members/aapl-20260627_lab.xml": "cdb991293ff0b3a4028add1a070fe36c198824a153c579f4e6bbea898010ce68",
    "fundamental_forensics/aapl_10q_2026q3/members/aapl-20260627_pre.xml": "648e30661e98ff74d6cb402c0b7419c8aa89344fd1b189ffa39e5d33546ebed6",
    "sec_filings/minimal_inline.xhtml": "ce0b664e6be463202ff164f30b06aedad8bdef890c1c16fc8f7f9b212949f958",
    "sec_filings/minimal_instance.xml": "607d16eadfffc53c86415c14340830b24277dbd0e46587ec8a45f648e11557b8",
}


@pytest.mark.parametrize(("member", "expected_sha"), sorted(_BYTE_IDENTITY_PINS.items()))
def test_accepted_corpus_members_stay_byte_identical(member, expected_sha):
    content = (Path(__file__).parent / "fixtures" / member).read_bytes()
    result = parse_sec_filing_document(content, document_name=Path(member).name)
    assert sha256(parser_module._semantic_result_bytes(result)).hexdigest() == expected_sha
