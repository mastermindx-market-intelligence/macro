from pathlib import Path
import json
import pytest
from engine.company_intelligence import defense_profiles as profiles
from engine.earnings_release.binding import bind_release_document
from engine.company_intelligence.documents import verify_span,SourceSpan

FIXTURES=Path(__file__).parent/'fixtures/company_intelligence/defense'


def facts(body):
    filing=json.loads((FIXTURES/'LHX.filing.json').read_text());bound=bind_release_document(body=body,**filing)
    return profiles.extract_segment_facts(ticker='LHX',bound=bound,document_id=bound.revision.document_id,
        event_id='evt_cik0000202058_2026q2_results',fiscal_period=profiles.source_fiscal_period(bound,'LHX')),bound


def body():
    return (FIXTURES/'LHX.segment_income.html').read_text()+'\n'+(FIXTURES/'LHX.segment.html').read_text()


def profit(rows):return next(v for v in rows if v['metric']=='defense_segment_operating_profit')


def test_current_reported_income_130_is_native_not_calculated():
    raw=body();rows,bound=facts(raw);f=profit(rows)
    assert f['value']==130 and f['unit']=='USD_million' and not f.get('typed_absence')
    assert [r['value'] for r in rows]==[1054,130,12.3]
    span=SourceSpan(**{k:v for k,v in f['source_span'].items() if k in SourceSpan.__dataclass_fields__});verify_span(span,segment_text=raw,body_sha256=bound.revision.source_sha256)
    assert '130' in span.display_excerpt


def test_current_income_negative_sign_is_preserved():
    rows,_=facts(body().replace('>130<','>(130)<',1));assert profit(rows)['value']==-130


@pytest.mark.parametrize('mutation',['swapped_years','missing_section','ambiguous_literal','missing_units'])
def test_unqualified_consolidated_profit_withholds_only_profit(mutation):
    table=(FIXTURES/'LHX.segment_income.html').read_text()
    if mutation=='swapped_years':table=table.replace('>2026<','>YEAR_SWAP<',1).replace('>2025<','>2026<',1).replace('>YEAR_SWAP<','>2025<',1)
    if mutation=='missing_section':table=table.replace('>Operating income<','>Other result<')
    if mutation=='ambiguous_literal':table=table.replace('>130<','>130 131<',1)
    if mutation=='missing_units':table=table.replace('millions','units')
    rows,_=facts(table+'\n'+(FIXTURES/'LHX.segment.html').read_text());assert profit(rows).get('typed_absence')
    assert rows[0]['value']==1054 and rows[2]['value']==12.3
