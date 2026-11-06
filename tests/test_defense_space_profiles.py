"""Synthetic discriminators plus one unchanged, provenance-bound source table."""
import hashlib
import json
from pathlib import Path

import pytest

from engine.company_intelligence.defense_space_profiles import extract_space_facts, space_fact_rules
from engine.company_intelligence.defense_profiles import defense_profile
from engine.company_intelligence.defense_cash_profiles import financial_fact_rules
from engine.company_intelligence.events import FiscalPeriod
from engine.earnings_release.binding import bind_release_document


def synthetic(segment='SPACE SYSTEMS'):
    return f'''<table><tr><td>{segment}</td><td colspan="2">Three Months Ended June 30</td><td colspan="2">Six Months Ended June 30</td></tr>
<tr><td>($ in millions)</td><td>2026</td><td>2025</td><td>2026</td><td>2025</td></tr>
<tr><td>Sales</td><td>2,753</td><td>2,646</td><td>5,233</td><td>5,214</td></tr>
<tr><td>Operating income</td><td>236</td><td>280</td><td>471</td><td>563</td></tr>
<tr><td>Operating margin rate</td><td>8.6</td><td>10.6</td><td>9.0</td><td>10.8</td></tr></table>'''


def bound(body):
    return bind_release_document(body=body, cik='1133421', accession='0001133421-26-000033',
                                 form='8-K', filing_date='2026-07-21',
                                 acceptance_datetime='2026-07-21T10:45:45Z', report_date='2026-07-21',
                                 exhibit_url='https://www.sec.gov/Archives/synthetic-space-test.htm')


def extract(body, ticker='NOC', period=FiscalPeriod(year=2026, quarter=2)):
    b = bound(body)
    return extract_space_facts(ticker=ticker, bound=b, document_id=b.revision.document_id,
                               event_id='space-source-test', fiscal_period=period)


def assert_six(facts, body):
    assert len(facts) == 6
    assert [f.get('value') for f in facts] == [2753, 2646, 236, 280, 8.6, 10.6]
    assert [f['period'] for f in facts] == ['2026Q2', '2025Q2'] * 3
    assert [f['unit'] for f in facts] == ['USD_million'] * 4 + ['percent'] * 2
    assert all(f['basis'] == 'issuer_reported_segment:Space Systems:reported' for f in facts)
    for f in facts:
        span = f['source_span']; receipt = span['receipt']
        literal = body.encode()[receipt['span_start_byte']:receipt['span_end_byte']].decode()
        assert literal == span['display_excerpt']
        assert hashlib.sha256(body.encode()).hexdigest() == receipt['source_sha256']
        assert hashlib.sha256(literal.encode()).hexdigest() == span['text_sha256']


def test_quarter_prior_and_half_year_are_separate_source_cells():
    body = synthetic()
    assert_six(extract(body), body)
    assert set(space_fact_rules('NOC', 2026, 2)) <= set(financial_fact_rules('NOC', 2026, 2))


@pytest.mark.parametrize('defect', [
    'duplicate_table', 'wrong_segment', 'missing_row', 'duplicate_row', 'reversed_years',
    'wrong_year', 'missing_units', 'missing_currency', 'separate_minus', 'currency_suffix',
    'margin_currency', 'half_year_only', 'wrong_quarter',
])
def test_unqualified_table_refuses_all_six_facts(defect):
    body = synthetic()
    if defect == 'duplicate_table': body += body
    elif defect == 'wrong_segment': body = body.replace('SPACE SYSTEMS', 'DEFENSE SYSTEMS')
    elif defect == 'missing_row': body = body.replace('Operating income', 'Other income')
    elif defect == 'duplicate_row': body = body.replace('</table>', '<tr><td>Sales</td><td>1</td><td>2</td></tr></table>')
    elif defect == 'reversed_years': body = body.replace('<td>2026</td><td>2025</td>', '<td>2025</td><td>2026</td>')
    elif defect == 'wrong_year': body = body.replace('2026', '2027').replace('2025', '2026')
    elif defect == 'missing_units': body = body.replace('in millions', 'only')
    elif defect == 'missing_currency': body = body.replace('$', '')
    elif defect == 'separate_minus': body = body.replace('<td>280</td>', '<td>-</td><td>280</td>')
    elif defect == 'currency_suffix': body = body.replace('2,753', '2,753B')
    elif defect == 'margin_currency': body = body.replace('<td>8.6</td>', '<td>$8.6</td>')
    elif defect == 'half_year_only': body = body.replace('Three Months Ended', 'Six Months Ended')
    elif defect == 'wrong_quarter': body = body.replace('June 30', 'September 30')
    facts = extract(body)
    assert len(facts) == 6 and all(f.get('typed_absence') for f in facts)


@pytest.mark.parametrize('ticker,quarter', [('LMT', 2), ('RTX', 2), ('LHX', 2), ('NOC', 3)])
def test_no_other_issuer_or_unsupported_quarter_admission(ticker, quarter):
    assert space_fact_rules(ticker, 2026, quarter) == {}
    assert extract(synthetic(), ticker, FiscalPeriod(year=2026, quarter=quarter)) == []


def test_existing_defense_systems_profile_and_financial_facts_remain_distinct():
    body = synthetic() + synthetic('DEFENSE SYSTEMS').replace('2,753', '1,123')
    b = bound(body)
    facts = defense_profile('NOC').extract_release_facts(bound=b, document_id=b.revision.document_id,
                                                       event_id='space-source-test', fiscal_period=FiscalPeriod(year=2026, quarter=2))
    by_metric = {f['metric']: f for f in facts}
    assert len(by_metric) == len(facts)
    assert by_metric['defense_segment_sales']['value'] == 1123
    assert by_metric['defense_segment_sales']['basis'] == 'issuer_reported_segment:Defense Systems:reported'
    assert_six([f for f in facts if f['metric'].startswith('issuer_space_segment_')], body)


def test_retained_real_space_table_replays_its_own_bytes():
    base = Path(__file__).parent / 'fixtures/company_intelligence/defense'
    body = (base / 'NOC.space_systems.real_fragment.html').read_text()
    provenance = json.loads((base / 'NOC.space_systems.real_fragment.provenance.json').read_text())
    assert hashlib.sha256(body.encode()).hexdigest() == provenance['fragment_sha256']
    assert len(body.encode()) == provenance['original_byte_end'] - provenance['original_byte_start']
    assert_six(extract(body), body)


def adverse_paragraph():
    base = Path(__file__).parent / 'fixtures/company_intelligence/defense'
    body = (base / 'NOC.GEM63XL.real_fragment.html').read_text()
    provenance = json.loads((base / 'NOC.GEM63XL.real_fragment.provenance.json').read_text())
    assert hashlib.sha256(body.encode()).hexdigest() == provenance['fragment_sha256']
    return body


def extract_adverse(body, ticker='NOC', year=2026, quarter=2):
    from engine.company_intelligence.defense_space_profiles import extract_space_adverse_facts
    b = bound(body)
    return extract_space_adverse_facts(ticker=ticker, bound=b, document_id=b.revision.document_id,
                                      event_id='space-source-test', fiscal_period=FiscalPeriod(year=year, quarter=quarter))


def test_real_adverse_paragraph_with_synthetic_table_replays_one_estimate():
    # Deliberately mixed fixture, not a claim of full-release source qualification.
    body = synthetic() + adverse_paragraph()
    facts = extract_adverse(body)
    assert len(facts) == 1
    fact = facts[0]
    assert fact['metric'] == 'issuer_space_gem63xl_unfavorable_eac'
    assert (fact['value'], fact['unit'], fact['period'], fact['basis']) == (
        91, 'USD_million', '2026Q2', 'issuer_reported_program_cost_estimate:GEM63XL:unfavorable_EAC')
    receipt = fact['source_span']['receipt']
    assert body.encode()[receipt['span_start_byte']:receipt['span_end_byte']] == b'91'
    assert receipt['source_sha256'] == hashlib.sha256(body.encode()).hexdigest()
    assert financial_fact_rules('NOC', 2026, 2)[fact['metric']][0] == 'reported_eac'
    assert_six(extract(body), body)


@pytest.mark.parametrize('defect', [
    'missing', 'duplicate', 'favorable', 'foreign_program', 'billion', 'wrong_currency',
    'negative', 'zero', 'wrong_year', 'wrong_quarter', 'qualified_negation',
    'before_space_section', 'after_next_table', 'ambiguous_numeric_receipt',
])
def test_adverse_prose_refuses_without_damaging_segment_figures(defect):
    prose = adverse_paragraph()
    if defect == 'missing': prose = ''
    elif defect == 'duplicate': prose += prose
    elif defect == 'favorable': prose = prose.replace('unfavorable adjustment', 'favorable adjustment')
    elif defect == 'foreign_program': prose = prose.replace('GEM 63XL', 'SiAW')
    elif defect == 'billion': prose = prose.replace('$91 million', '$91 billion')
    elif defect == 'wrong_currency': prose = prose.replace('$91 million', 'EUR91 million')
    elif defect == 'negative': prose = prose.replace('$91 million', '$-91 million')
    elif defect == 'zero': prose = prose.replace('$91 million', '$0 million')
    elif defect == 'wrong_year': prose = prose.replace('quarter 2026', 'quarter 2025')
    elif defect == 'wrong_quarter': prose = prose.replace('Second quarter', 'Third quarter')
    elif defect == 'qualified_negation': prose = prose.replace('including a $91', 'not including a $91')
    elif defect == 'ambiguous_numeric_receipt': prose = prose.replace('$44 million', '$91 million')
    body = synthetic() + prose
    if defect == 'before_space_section': body = prose + synthetic()
    if defect == 'after_next_table': body = synthetic() + '<table><tr><td>Guidance</td></tr></table>' + prose
    facts = extract_adverse(body)
    assert len(facts) == 1 and facts[0].get('typed_absence')
    assert_six(extract(body), body)


@pytest.mark.parametrize('ticker,year,quarter', [('LMT',2026,2), ('RTX',2026,2), ('LHX',2026,2), ('NOC',2025,2), ('NOC',2026,1), ('NOC',2026,3), ('NOC',2026,4)])
def test_adverse_profile_is_exact_subject_period(ticker, year, quarter):
    from engine.company_intelligence.defense_space_profiles import space_adverse_fact_rules
    assert space_adverse_fact_rules(ticker, year, quarter) == {}
    assert extract_adverse(synthetic() + adverse_paragraph(), ticker, year, quarter) == []


@pytest.mark.parametrize('defect', ['foreign_segment', 'ambiguous_table', 'wrong_fiscal_table'])
def test_adverse_requires_qualified_space_quarter_context(defect):
    table = synthetic()
    if defect == 'foreign_segment': table = synthetic('DEFENSE SYSTEMS')
    elif defect == 'ambiguous_table': table += table
    else: table = table.replace('June 30', 'September 30')
    facts = extract_adverse(table + adverse_paragraph())
    assert len(facts) == 1 and facts[0].get('typed_absence')
