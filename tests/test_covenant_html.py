"""Native-byte transcription boundaries, not a new financial model."""
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from engine.capital_structure.covenant_html import visible_html
from engine.capital_structure import covenant_terms as ct

F = Path(__file__).parent / 'fixtures/capital_structure'


def fixture():
    metadata = json.loads((F / 'covenant_eprt_section_7_1.source.json').read_text())
    excerpt = (F / 'covenant_eprt_section_7_1.html').read_bytes()
    assert hashlib.sha256(excerpt).hexdigest() == metadata['excerpt']['sha256']
    # Explicit controlled wrapper; native qualification separately reads the
    # full retained SEC object and uses its original manifest/hash/offsets.
    raw = b'<html><body>' + excerpt + b'</body></html>'
    manifest = metadata['manifest']
    manifest['document']['content_sha256'] = hashlib.sha256(raw).hexdigest()
    manifest['document']['byte_length'] = len(raw)
    return manifest, raw


def compile_raw(raw):
    manifest, _ = fixture()
    manifest['document']['content_sha256'] = hashlib.sha256(raw).hexdigest()
    manifest['document']['byte_length'] = len(raw)
    return ct.compile_observations(manifest, raw.decode(), generated_at='2026-10-19T20:00:00Z')


def test_actual_excerpt_yields_only_the_supported_minimum_fixed_charge_term():
    manifest, raw = fixture()
    rows = compile_raw(raw)
    assert len(rows) == 1
    row = rows[0]
    assert row['term']['name'] == 'minimum_fixed_charge_coverage_ratio'
    assert row['reported'] == {'raw': '1.50 to 1.00', 'unit': 'ratio', 'value': None}
    assert row['clause']['section_label_normalized'] == 'section_7_1_financial_condition_covenants'
    a, b = ct._locator_bounds(row['evidence']['spans'][0]['locator'])
    assert raw[a:b] == b'1.50 to 1.00'
    schema = json.loads((Path(__file__).parents[1] / 'contracts/capital_structure_covenant_term_observation.schema.json').read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(row)


def test_source_hash_mismatch_refuses_even_if_visible_clause_is_plausible():
    manifest, raw = fixture()
    with pytest.raises(ct.CovenantSpanUnbound, match='identity'):
        ct.extract_candidates(manifest, raw.replace(b'1.50', b'1.25').decode())


@pytest.mark.parametrize('attribute', [b'hidden', b'style="display: none"',
    b'style="VISIBILITY : HIDDEN"', b'style="text-decoration: underline line-through !important"'])
def test_hidden_competing_value_is_never_read(attribute):
    raw = b'<div ' + attribute + b'><b>9.99</b></div><div>1.50</div>'
    view = visible_html(raw)
    assert '9.99' not in view.text
    start = view.text.index('1.50')
    a, b = view.exact_byte_span(start, start + 4)
    assert raw[a:b] == b'1.50'


@pytest.mark.parametrize('tag', [b'del', b's', b'strike', b'script', b'style'])
def test_deleted_or_executable_text_does_not_become_a_fact(tag):
    view = visible_html(b'<' + tag + b'>9.99</' + tag + b'><p>1.50</p>')
    assert '9.99' not in view.text
    assert '1.50' in view.text


def test_offsets_survive_multibyte_crlf_and_repeated_values():
    raw = '<p>中文 1.50</p>\r\n<p>第二 1.50</p>'.encode()
    view = visible_html(raw)
    start = view.text.rindex('1.50')
    assert view.exact_byte_span(start, start + 4) == (raw.rindex(b'1.50'), raw.rindex(b'1.50') + 4)


@pytest.mark.parametrize('raw', [b'<p>1.<b>50</b></p>', b'<p>1.&#53;0</p>'])
def test_discontiguous_or_decoded_value_cannot_claim_literal_bytes(raw):
    view = visible_html(raw)
    start = view.text.index('1.50')
    with pytest.raises(ValueError):
        view.exact_byte_span(start, start + 4)


def test_sec_envelope_offsets_remain_relative_to_the_full_retained_object():
    raw = b'\n<TYPE>EX-10.1\n<SEQUENCE>2\n<FILENAME>x.htm\n<DESCRIPTION>credit\n<TEXT>\n<html><body>1.50</body></html>\n</TEXT>\n'
    view = visible_html(raw)
    a = view.text.index('1.50')
    assert view.exact_byte_span(a, a + 4) == (raw.index(b'1.50'), raw.index(b'1.50') + 4)


@pytest.mark.parametrize('raw', [b'<div hidden><span>wrong</div></span>', b'<div>unclosed',
    b'<div>' * 129 + b'</div>' * 129, b'<br>' * 100_001, b'x' * (2 * 1024 * 1024 + 1)])
def test_malformed_or_over_limit_input_refuses(raw):
    with pytest.raises(ValueError):
        visible_html(raw)


def test_table_of_contents_does_not_supply_an_operative_clause():
    with pytest.raises(ct.CovenantSpanUnbound, match='unambiguous'):
        compile_raw(b'<html><body><p>7.1 Financial Condition Covenants. 107</p><p>7.2 Other Covenants</p></body></html>')


def test_multiple_operative_clauses_are_ambiguous_not_first_match_wins():
    _, raw = fixture()
    raw = raw.replace(b'</body>', (F / 'covenant_eprt_section_7_1.html').read_bytes() + b'</body>')
    with pytest.raises(ct.CovenantSpanUnbound, match='unambiguous'):
        compile_raw(raw)


def test_other_coverage_ratios_cannot_be_relabelled_fixed_charge():
    _, raw = fixture()
    raw = raw.replace(b'Consolidated Fixed Charge Coverage Ratio', b'Unencumbered Interest Coverage Ratio')
    with pytest.raises(ct.CovenantSpanUnbound):
        compile_raw(raw)
