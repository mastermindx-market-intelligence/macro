"""Public metadata and drift tests; no credentials or provider inference."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import html
import json
from pathlib import Path
import re

import pytest
from engine import provider_subscription_catalog_opencode as go

F = Path(__file__).parent / "fixtures" / "opencode_go"
NOW = "2026-09-14T17:00:00Z"
LATER = "2026-09-14T17:05:00Z"


def payload():
    return json.loads((F / "inventory.json").read_text())


def document():
    return (F / "terms.mdx").read_text()


def metadata(text=None, data=None, at=NOW):
    return go.Metadata(go.parse_models(payload() if data is None else data, observed_at=at), go.parse_terms(document() if text is None else text, observed_at=at))


def offer(value, name):
    return next(m for m in value.terms.models if m.model_id == name)


def actions(a, b):
    return {(x["model_id"], x["action"]) for x in go.metadata_changes(a, b)}


def as_html(text):
    # Deliberately a synthetic HTML fixture, NOT a captured published page.
    parts, table = [], False
    for line in text.splitlines():
        if line.startswith('|'):
            if re.fullmatch(r'[\s|:-]+', line): continue
            if not table: parts.append('<table>')
            tag = 'td' if table else 'th'
            table = True
            cells = line.strip('|').split('|')
            def markup(cell):
                value = html.escape(go._plain(cell))
                return re.sub(r'~~([^~]+)~~', r'<del>\1</del>', value)
            parts.append('<tr>' + ''.join(f'<{tag}>{markup(c)}</{tag}>' for c in cells) + '</tr>')
        else:
            if table: parts.append('</table>'); table = False
            if line.startswith('## '): parts.append('<h2>' + html.escape(line[3:]) + '</h2>')
            elif line.startswith('### '): parts.append('<h3>' + html.escape(line[4:]) + '</h3>')
            elif line: parts.append('<p>' + html.escape(line) + '</p>')
    if table: parts.append('</table>')
    return ('<html><script>bad()</script>' + ''.join(parts) + '</html>').encode()


def test_current_factual_shapes_and_unknowns_are_visible_not_routable():
    value = metadata()
    preview = go.catalog_preview(value, now=NOW)
    assert len(value.inventory.model_ids) == 37
    assert len(value.terms.models) == 28
    assert sum(len(m.rates) for m in value.terms.models) == 36
    assert preview['horizon_fractions'] == {'five_hour':'0.2','weekly':'0.5','monthly':'1'}
    assert sum('OFFER_TERMS_UNKNOWN' in x['metadata_issues'] for x in preview['models']) == 9
    assert not any(x['routing_authorized'] for x in preview['models'])
    row = next(x for x in preview['models'] if x['model_id'] == 'minimax-m2.5')
    assert 'DATA_POLICY_UNKNOWN' in row['metadata_issues']
    assert preview['production_armed'] is False


def test_created_and_array_order_never_become_model_release_or_drift():
    first = metadata()
    data = payload()
    data['data'].reverse()
    for x in data['data']: x['created'] += 9999
    second = metadata(data=data, at=LATER)
    assert first.inventory.source_digest != second.inventory.source_digest
    assert first.inventory.semantic_digest == second.inventory.semantic_digest
    assert go.metadata_changes(first, second) == ()


def test_added_discovered_removed_blocked_no_automatic_promotion():
    data = payload()
    data['data'] = [x for x in data['data'] if x['id'] != 'glm-5.3']
    data['data'].append({'id':'new-future-model','object':'model','created':1,'owned_by':'opencode'})
    delta = actions(metadata(), metadata(data=data, at=LATER))
    assert ('glm-5.3','STOP_NEW_REQUESTS') in delta
    assert ('new-future-model','DISCOVER_ONLY') in delta
    assert all('ENABLE' not in a for _, a in delta)


@pytest.mark.parametrize('mutation', [
    lambda p: p.update(object='error'),
    lambda p: p.update(data=[]),
    lambda p: p['data'].append(p['data'][0]),
    lambda p: p['data'][0].update(id='../secret'),
    lambda p: p['data'][0].update(created=True),
    lambda p: p['data'][0].update(owned_by='someone-else'),
    lambda p: p['data'][0].update(context_window=1000000),
])
def test_schema_or_identity_drift_refuses_not_empty_free(mutation):
    data = payload(); mutation(data)
    with pytest.raises(go.GoCatalogError): go.parse_models(data, observed_at=NOW)


def test_promotion_original_limit_and_variants_are_not_flattened():
    value = metadata(); model = offer(value, 'deepseek-v4.1-flash')
    assert {r.qualifier for r in model.rates} == {'Peak','Off-Peak'}
    assert {Decimal(r.monthly_equivalent_usd) for r in model.rates} == {Decimal(60)}
    assert {Decimal(r.baseline_equivalent_usd) for r in model.rates} == {Decimal(15)}
    assert all('Ends Sep 20' in r.promotion_note for r in model.rates)
    row = next(x for x in go.catalog_preview(value, now=NOW)['models'] if x['model_id']==model.model_id)
    assert 'PROMOTION_REVALIDATION_REQUIRED' in row['metadata_issues']
    assert 'CONDITIONAL_RETENTION_REVALIDATION_REQUIRED' in row['metadata_issues']
    assert offer(value,'qwen3.7-plus').rates[0].qualifier != 'standard'


@pytest.mark.parametrize('old,new', [('$0.15 | $0.50','$0.19 | $0.50'), ('20% of the monthly limit','10% of the monthly limit'), ('01:00-04:00','02:00-05:00'), ('Ends Sep 20','Ends Sep 21')])
def test_economic_change_requires_new_quote_and_native_usage(old,new):
    text=document(); assert old in text
    delta=actions(metadata(),metadata(text=text.replace(old,new),at=LATER))
    assert any(a=='REQUOTE_AND_REOBSERVE_USAGE' for _,a in delta)


def test_expiring_promotion_reduction_is_detected_not_extra_allowance():
    text=document().replace('~~$15~~ **$60**<br /><small>4x \u00b7 Ends Sep 20</small>','$15')
    delta=actions(metadata(),metadata(text=text,at=LATER))
    assert ('deepseek-v4.1-flash','REQUOTE_AND_REOBSERVE_USAGE') in delta


def test_privacy_renewal_or_worsening_is_not_auto_approved():
    text=document().replace('September 30, 2026','October 31, 2026')
    assert (None,'HOLD_POLICY_REVIEW') in actions(metadata(),metadata(text=text,at=LATER))


def test_protocol_change_requires_review_not_translate_tools():
    text=document().replace('| glm-5.3 | `https://opencode.ai/zen/go/v1/chat/completions`','| glm-5.3 | `https://opencode.ai/zen/go/v1/responses`')
    assert ('glm-5.3','REVALIDATE_HARNESS') in actions(metadata(),metadata(text=text,at=LATER))


@pytest.mark.parametrize('mutation', [
    lambda s:s.replace('## Usage limits','## Allowances'),
    lambda s:s.replace('Monthly limit |','Budget |'),
    lambda s:s.replace('$60 |','$0 |'),
    lambda s:s.replace('$0.15 |','$NaN |'),
    lambda s:s.replace('https://opencode.ai/zen/go/v1/responses','https://attacker.invalid/responses'),
    lambda s:s.replace('5-hour \u2014 20%','5-hour \u2014 150%'),
    lambda s:s.replace('## Privacy','## Unknown'),
])
def test_unknown_doc_schema_or_unsafe_endpoint_never_guessed(mutation):
    with pytest.raises(go.GoCatalogError): go.parse_terms(mutation(document()),observed_at=NOW)


def test_html_decoder_matches_factual_markdown_but_not_live_page_proof():
    plain=go.parse_terms(document(),observed_at=NOW)
    extracted=go.parse_published_terms(as_html(document()),observed_at=NOW)
    assert plain.models==extracted.models
    assert plain.horizon_fractions==extracted.horizon_fractions


def test_request_estimates_do_not_define_capacity():
    text=document().replace('This fixture deliberately omits estimated request counts; these are not caps.', 'A million requests are estimated, not a quota.')
    assert metadata(text=text).terms.semantic_digest==metadata().terms.semantic_digest


def test_missing_terms_after_known_model_goes_to_hold():
    first=metadata()
    terms=replace(first.terms,models=tuple(m for m in first.terms.models if m.model_id!='glm-5.3'),observed_at=LATER)
    assert ('glm-5.3','HOLD_MISSING_TERMS') in actions(first,replace(first,terms=terms))


def test_stale_future_and_unknown_metadata_never_look_approved():
    for now in ('2026-09-14T16:59:59Z','2026-09-15T00:00:00Z'):
        rows=go.catalog_preview(metadata(),now=now)['models']
        assert all('INVENTORY_NOT_FRESH' in r['metadata_issues'] for r in rows)
        assert all('TERMS_NOT_FRESH' in r['metadata_issues'] for r in rows)
        assert not any(r['routing_authorized'] for r in rows)


def test_out_of_order_observations_do_not_rollback_metadata():
    with pytest.raises(go.GoCatalogError,match='OUT_OF_ORDER'):
        go.metadata_changes(metadata(at=LATER),metadata())


def test_acquisition_uses_only_public_origins_and_no_credentials():
    calls=[]
    def get(url):
        calls.append(url)
        return json.dumps(payload()).encode() if url==go.MODELS_URL else as_html(document())
    clock=lambda:datetime(2026,9,14,17,tzinfo=timezone.utc)
    result=go.acquire_metadata(getter=get,clock=clock)
    assert calls==[go.MODELS_URL,go.DOCS_URL]
    assert len(result.inventory.model_ids)==37


def test_get_failure_does_not_retry_or_erase_previous_snapshot():
    first=metadata(); before=deepcopy(first); calls=[]
    def get(url):
        calls.append(url);raise OSError('untrusted-content-secret')
    with pytest.raises(go.GoCatalogError) as caught:go.acquire_metadata(getter=get)
    assert str(caught.value)=='PUBLIC_METADATA_ACQUISITION_FAILED'
    assert len(calls)==1 and first==before


def test_public_http_redirect_policy_does_not_follow_new_origin():
    with pytest.raises(go.GoCatalogError):go._NoRedirect().redirect_request(None,None,302,'',{},'https://attacker.invalid/')
    with pytest.raises(go.GoCatalogError):go._get_public('https://attacker.invalid/')


def test_quota_math_keeps_shared_debit_separate_from_cash():
    a=go.estimate_quota_debit(quoted_usage_usd='0.6',monthly_equivalent_usd='60',horizon_fractions=('0.2','0.5','1'))
    b=go.estimate_quota_debit(quoted_usage_usd='0.6',monthly_equivalent_usd='15',horizon_fractions=('0.2','0.5','1'))
    assert a=={'five_hour':'5','weekly':'2','monthly':'1'}
    assert b=={'five_hour':'2E+1','weekly':'8','monthly':'4'}


@pytest.mark.parametrize('spend,cap', [('NaN','60'),('1','0'),('-1','60'),('1','Infinity'),(True,'60'),('1','-2')])
def test_bad_estimates_refuse(spend,cap):
    with pytest.raises(go.GoCatalogError):go.estimate_quota_debit(quoted_usage_usd=spend,monthly_equivalent_usd=cap,horizon_fractions=('0.2','0.5','1'))


def test_cli_factual_preview_is_explicitly_not_live():
    import subprocess
    import sys
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'opencode_go_catalog_preview.py'
    result = subprocess.run([sys.executable, str(script), '--models-file', str(F/'inventory.json'), '--terms-file', str(F/'terms.mdx'), '--observed-at', NOW, '--now', NOW], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    value = json.loads(result.stdout)
    assert value['acquisition_origin'] == 'supplied_fixture_not_live_evidence'
    assert len(value['models']) == 37 and value['production_armed'] is False


def test_live_cli_refuses_a_forged_evidence_clock_before_network():
    import subprocess
    import sys
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'opencode_go_catalog_preview.py'
    result = subprocess.run([sys.executable, str(script), '--live', '--now', NOW], capture_output=True, text=True, timeout=10)
    assert result.returncode == 2 and 'cannot take fixture' in result.stderr


def test_unrecognized_training_value_remains_unknown():
    value = metadata(text=document().replace('| GLM-5.3 | Not used |','| GLM-5.3 | Undocumented |'))
    assert offer(value,'glm-5.3').training is None


def test_lost_price_is_unknown_not_zero():
    text='\n'.join(l for l in document().splitlines() if not l.startswith('| GLM-5.3 | $'))
    value=metadata(text=text)
    row=next(x for x in go.catalog_preview(value,now=NOW)['models'] if x['model_id']=='glm-5.3')
    assert 'OFFER_TERMS_UNKNOWN' in row['metadata_issues']
    assert ('glm-5.3','HOLD_MISSING_TERMS') in actions(metadata(),value)


def test_document_only_model_not_listed_is_not_a_candidate_row():
    data=payload();data['data']=[r for r in data['data'] if r['id']!='glm-5.3']
    preview=go.catalog_preview(metadata(data=data),now=NOW)
    assert preview['documented_not_listed']==['glm-5.3']
    assert 'glm-5.3' not in {r['model_id'] for r in preview['models']}


def test_unknown_rate_unit_refuses_instead_of_mispricing_by_a_thousand():
    with pytest.raises(go.GoCatalogError,match='PRICE_UNIT_UNKNOWN'):
        go.parse_terms(document().replace('per 1M tokens','per 1K tokens'),observed_at=NOW)


def test_limit_views_are_per_model_equivalents_not_universal_twelve_dollars():
    rows={r['model_id']:r for r in go.catalog_preview(metadata(),now=NOW)['models']}
    def five(model):return Decimal(rows[model]['offer']['rates'][0]['window_equivalent_usd']['five_hour'])
    assert five('glm-5.3')==3
    assert five('glm-5.3-flash')==12
    assert five('qwen3.8-flash')==6


def test_offer_drift_never_reprices_old_native_account_usage():
    from engine.provider_subscription_usage_opencode import parse_opencode_go_usage
    observation=parse_opencode_go_usage({'usage':{
        'rolling':{'status':'ok','percent':70,'resetsAt':'2026-09-14T21:00:00Z'},
        'weekly':{'status':'ok','percent':30,'resetsAt':'2026-09-20T00:00:00Z'},
        'monthly':{'status':'ok','percent':20,'resetsAt':'2026-10-14T00:00:00Z'},
    }},observed_at=NOW)
    before=deepcopy(observation)
    text=document().replace('~~$15~~ **$60**<br /><small>4x \u00b7 Ends Sep 20</small>','$15')
    changes=go.metadata_changes(metadata(),metadata(text=text,at=LATER))
    assert observation==before
    assert [r['used_percent'] for r in observation.quota_rows]==[70,30,20]
    assert any(r['action']=='REQUOTE_AND_REOBSERVE_USAGE' for r in changes)
