from pathlib import Path
import json
from engine.company_intelligence.gd_profile import gd_fiscal_period,extract_gd_facts
from engine.earnings_release.binding import bind_release_document
from engine.company_intelligence.events import FiscalPeriod
import pytest
FIXTURES=Path(__file__).with_name('fixtures')/'company_intelligence'/'defense'


def facts(change=lambda x:x):
    filing=json.loads((FIXTURES/'GD.filing.json').read_text());body=change((FIXTURES/'GD.marine.html').read_text());bound=bind_release_document(body=body,**filing)
    return extract_gd_facts(bound=bound,document_id=bound.revision.document_id,event_id='evt_cik0000040533_2026q2_results',fiscal_period=FiscalPeriod(2026,2))


def test_reported_segment_and_backlog_categories_keep_exact_basis_and_receipts():
    output=facts();assert [f['value'] for f in output]==[4660,342,7.3,42356,22826,65182,7442,72624]
    assert len({f['basis'] for f in output[3:]})==5
    assert all(f['period']=='2026Q2' and f['source_span']['receipt_state']=='byte_replayed' for f in output)


def test_year_column_swap_refuses_relabeling_comparative_as_current():
    def swap(body):return body.replace('July 5, 2026','__DATE__').replace('June 29, 2025','July 5, 2026').replace('__DATE__','June 29, 2025')
    assert all(f.get('typed_absence') for f in facts(swap))


def test_funded_unfunded_header_swap_tracks_selected_semantics_not_first_number():
    def swap(body):return body.replace('>Funded<','>__FUNDED__<').replace('>Unfunded<','>Funded<').replace('>__FUNDED__<','>Unfunded<')
    output=facts(swap)
    assert output[3]['value']==22826 and output[4]['value']==42356
    assert output[3]['basis'].endswith(':Funded') and output[4]['basis'].endswith(':Unfunded')


def test_numeric_category_receipts_do_not_prove_procurement_obligations():
    output=facts();assert all('issuer_reported_backlog_category' in f['basis'] for f in output[3:])
    assert all('obligation' not in f['metric'] for f in output)
