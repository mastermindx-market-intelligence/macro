from pathlib import Path
import json
from engine.company_intelligence import defense_profiles as p
from engine.earnings_release.binding import bind_release_document
from engine.company_intelligence.noc_adverse_profile import extract_noc_adverse_facts

FIXTURES=Path(__file__).with_name('fixtures')/'company_intelligence'/'defense'

def facts(mutate=lambda x:x):
    filing=json.loads((FIXTURES/'NOC.filing.json').read_text());body=mutate((FIXTURES/'NOC.adverse.html').read_text());bound=bind_release_document(body=body,**filing)
    # fixed intended event period; source mutation must not redefine it
    from engine.company_intelligence.events import FiscalPeriod
    return extract_noc_adverse_facts(bound=bound,document_id=bound.revision.document_id,event_id='evt_cik0001133421_2026q2_results',fiscal_period=FiscalPeriod(2026,2))


def test_current_unfavorable_and_prior_favorable_are_distinct_periods_and_basis():
    output=facts();assert [(f['metric'],f['value'],f['period']) for f in output]==[('defense_segment_prior_margin',12.7,'2025Q2'),('siaw_unfavorable_eac',68,'2026Q2'),('sentinel_prior_favorable_eac',76,'2025Q2')]
    assert output[1]['basis'].endswith(':unfavorable_EAC') and output[2]['basis'].endswith(':prior_favorable_EAC')
    assert all(f['source_span']['receipt_state']=='byte_replayed' for f in output)


def test_changed_direction_never_reuses_unfavorable_class():
    output=facts(lambda x:x.replace('unfavorable EAC adjustment on SiAW','favorable EAC adjustment on SiAW'))
    assert next(f for f in output if f['metric']=='siaw_unfavorable_eac').get('typed_absence')


def test_current_clause_must_name_exact_program_and_period():
    output=facts(lambda x:x.replace('Second quarter 2026 operating income','Second quarter 2025 operating income'))
    assert all(f.get('typed_absence') for f in output[1:])
    output=facts(lambda x:x.replace('adjustment on SiAW','adjustment on Sentinel'))
    assert next(f for f in output if f['metric']=='siaw_unfavorable_eac').get('typed_absence')


def test_prior_comparison_cannot_become_current_adjustment():
    output=facts(lambda x:x.replace('prior year $76 million favorable','current year $76 million favorable'))
    assert next(f for f in output if f['metric']=='sentinel_prior_favorable_eac').get('typed_absence')


def test_duplicate_source_paragraph_refuses_ambiguous_adverse_claim():
    text=(FIXTURES/'NOC.adverse.html').read_text();paragraph=text[text.index('Second quarter 2026 operating income'):]
    output=facts(lambda x:x+'<p>'+paragraph+'</p>')
    assert all(f.get('typed_absence') for f in output[1:])
