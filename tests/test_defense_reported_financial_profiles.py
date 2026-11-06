"""Discriminating release-profile checks; all fixtures are synthetic source bytes."""
import pytest
from engine.earnings_release.binding import bind_release_document
from engine.company_intelligence.events import FiscalPeriod
from engine.company_intelligence.defense_cash_profiles import extract_cash_facts,extract_additional_facts,financial_fact_rules

ROWS={'LMT':('Cash from operations','Free cash flow1'),'RTX':('Operating Cash Flow','Free Cash Flow*'),'NOC':('Net cash provided by (used in) operating activities','Adjusted free cash flow1'),'LHX':('Cash from operations','Free cash flow3')}
HEADINGS={'LMT':('Quarters Ended','Six Months Ended'),'NOC':('Three Months Ended June 30','Six Months Ended June 30'),'LHX':('Second Quarter','Year to Date')}

def source(ticker,*,years=('2026','2025'),units='($ in millions)'):
    one,two=ROWS[ticker]
    dates=[f'June 28, {v}' for v in years] if ticker=='LMT' else list(years)
    if ticker=='RTX':
        table=f'<table><tr><td>{units}</td><td colspan="2">2nd Quarter</td></tr><tr><td></td><td>{years[0]}</td><td>{years[1]}</td></tr><tr><td>{one}</td><td>100</td><td>(20)</td></tr><tr><td>{two}</td><td>80</td><td>(30)</td></tr></table>'
        table+=f'<table><tr><td>{units}</td><td colspan="2">Quarter Ended June 30,</td></tr><tr><td></td><td>{years[0]}</td><td>{years[1]}</td></tr><tr><td>Net cash flows provided by operating activities</td><td>100</td><td>(20)</td></tr><tr><td>Free cash flow</td><td>80</td><td>(30)</td></tr><tr><td></td><td colspan="2">Six Months Ended June 30,</td></tr><tr><td></td><td>{years[0]}</td><td>{years[1]}</td></tr><tr><td>Net cash flows provided by operating activities</td><td>140</td><td>(50)</td></tr><tr><td>Free cash flow</td><td>90</td><td>(70)</td></tr></table>'
    else:
        q,h=HEADINGS[ticker]
        table=f'<table><tr><td>{units}</td><td colspan="2">{q}</td><td colspan="2">{h}</td></tr><tr><td></td><td>{dates[0]}</td><td>{dates[1]}</td><td>{dates[0]}</td><td>{dates[1]}</td></tr><tr><td>{one}</td><td>100</td><td>(20)</td><td>140</td><td>(50)</td></tr><tr><td>{two}</td><td>80</td><td>(30)</td><td>90</td><td>(70)</td></tr></table>'
    return '<html><body>'+table+'</body></html>'

def extract(ticker,body,additional=False):
    bound=bind_release_document(body=body,cik={'LMT':'936468','RTX':'101829','NOC':'1133421','LHX':'202058'}[ticker],accession='0000000000-26-000001',form='8-K',filing_date='2026-07-30',acceptance_datetime='2026-07-30T13:00:00Z',report_date='2026-07-30',exhibit_url='https://www.sec.gov/Archives/synthetic.htm')
    return (extract_additional_facts if additional else extract_cash_facts)(ticker=ticker,bound=bound,document_id=bound.revision.document_id,event_id='synthetic',fiscal_period=FiscalPeriod(year=2026,quarter=2))

@pytest.mark.parametrize('ticker',ROWS)
def test_duration_comparison_sign_and_basis_are_not_conflated(ticker):
    facts=extract(ticker,source(ticker));assert [f['value'] for f in facts]==[100,-20,80,-30,140,-50,90,-70]
    assert [f['period'] for f in facts]==['2026Q2','2025Q2','2026Q2','2025Q2','2026H1','2025H1','2026H1','2025H1']
    assert all(f['unit']=='USD_million' and f['source_span']['receipt_state']=='byte_replayed' for f in facts)
    assert facts[0]['basis']=='issuer_reported_consolidated:GAAP_operating_cash_flow'
    assert facts[2]['basis'].endswith('nonGAAP_adjusted_free_cash_flow' if ticker=='NOC' else 'nonGAAP_free_cash_flow')

@pytest.mark.parametrize('ticker',ROWS)
@pytest.mark.parametrize('defect',['reverse_years','missing_units','duplicate_tables','minus_cell'])
def test_ambiguous_duration_numeric_geometry_fails_closed(ticker,defect):
    body=source(ticker,years=('2025','2026')) if defect=='reverse_years' else source(ticker,units='($ only)' if defect=='missing_units' else '($ in millions)')
    if defect=='duplicate_tables':body+=body
    if defect=='minus_cell':body=body.replace('<td>(20)</td>','<td>-</td><td>20</td>')
    facts=extract(ticker,body);assert all(f.get('typed_absence') for f in facts[:4])


def test_rtx_mixed_backlog_and_repeated_guidance_endpoint_keep_scope():
    body='<p>Company backlog of $289 billion, including $170 billion of commercial and $119 billion of defense</p><p>Free cash flow* of $8.50 - $8.75 billion, up from $8.25 - $8.75 billion</p>'
    facts=[f for f in extract('RTX',body,True) if not f.get('typed_absence')]
    assert [f['value'] for f in facts]==[289,170,119,8.50,8.75]
    assert facts[0]['basis']=='issuer_reported_consolidated:total_backlog_stock'
    assert facts[2]['basis']=='issuer_reported_consolidated:defense_backlog_stock'
    assert all(f['period']=='2026FY' and f['unit']=='USD_billion' and f['basis'].startswith('issuer_guidance_consolidated:') for f in facts[-2:])


def test_no_unsupported_quarter_or_foreign_component_inference():
    assert financial_fact_rules('LMT',2026,3)=={}
    assert financial_fact_rules('FOREIGN_JV',2026,2)=={}
    assert all('cash_change_half_year' not in metric for metric in financial_fact_rules('RTX',2026,2))


def test_lmt_guidance_update_headings_cannot_be_reversed():
    def body(current,prior):
        return f'<table><tr><td>($ in millions)</td><td>{current}</td><td>{prior}</td></tr><tr><td>Cash from operations</td><td>~$9,200 - $9,400</td><td>$9,150 - $9,450</td></tr><tr><td>Free cash flow1</td><td>~$7,000 - $7,200</td><td>$6,500 - $6,800</td></tr></table>'
    normal=[f for f in extract('LMT',body('Current Update','April 2026'),True) if '_guidance_' in f['metric']]
    assert len(normal)==8 and all(not f.get('typed_absence') for f in normal)
    reversed=[f for f in extract('LMT',body('April 2026','Current Update'),True) if '_guidance_' in f['metric']]
    assert len(reversed)==8 and all(f.get('typed_absence') for f in reversed)


@pytest.mark.parametrize('unit_cell',['$3.6','$3.6M','$3.6 million','$3.6 billion'])
def test_lhx_guidance_requires_its_selected_cell_explicit_native_B(unit_cell):
    def body(value):
        return f'<table><tr><td>($ millions)</td><td>2026 Guidance</td></tr><tr><td>Cash from operations</td><td>{value}</td></tr><tr><td>Free cash flow3</td><td>{value}</td></tr></table>'
    valid=[f for f in extract('LHX',body('$3.6B'),True) if '_guidance_' in f['metric']]
    assert len(valid)==2 and all(f['value']==3.6 and f['unit']=='USD_billion' and not f.get('typed_absence') for f in valid)
    invalid=[f for f in extract('LHX',body(unit_cell),True) if '_guidance_' in f['metric']]
    assert len(invalid)==2 and all(f.get('typed_absence') for f in invalid)


@pytest.mark.parametrize('ticker',['LMT','NOC'])
@pytest.mark.parametrize('unit_cell',['$9,200B - $9,400B','$9,200M - $9,400M','$9,200 million - $9,400 million'])
def test_declared_million_guidance_cannot_ignore_selected_cell_suffix(ticker,unit_cell):
    if ticker=='LMT':
        body=f'<table><tr><td>($ in millions)</td><td>Current Update</td><td>April 2026</td></tr><tr><td>Cash from operations</td><td>{unit_cell}</td><td>$9,150 - $9,450</td></tr><tr><td>Free cash flow1</td><td>{unit_cell}</td><td>$6,500 - $6,800</td></tr></table>'
    else:
        body=f'<table><tr><td>($ in millions)</td><td>2026 Guidance</td></tr><tr><td>Adjusted free cash flow1</td><td>{unit_cell}</td></tr></table>'
    invalid=[f for f in extract(ticker,body,True) if '_guidance_' in f['metric']]
    assert invalid and all(f.get('typed_absence') for f in invalid)


@pytest.mark.parametrize('ticker',['LMT','NOC'])
def test_guidance_declared_million_header_is_required(ticker):
    if ticker=='LMT':
        body='<table><tr><td>($ only)</td><td>Current Update</td><td>April 2026</td></tr><tr><td>Cash from operations</td><td>$9,200 - $9,400</td><td>$9,150 - $9,450</td></tr><tr><td>Free cash flow1</td><td>$7,000 - $7,200</td><td>$6,500 - $6,800</td></tr></table>'
    else:
        body='<table><tr><td>($ only)</td><td>2026 Guidance</td></tr><tr><td>Adjusted free cash flow1</td><td>$3,100 — $3,500</td></tr></table>'
    facts=[f for f in extract(ticker,body,True) if '_guidance_' in f['metric']]
    assert facts and all(f.get('typed_absence') for f in facts)
