"""Stateless presentation of the incumbent native D5 Earnings vector.
Native validator, source clocks, identities and correction truth remain owners.
"""
from __future__ import annotations
from copy import deepcopy
from html import escape
import json
from engine.prophet_lab.intelligence_vector import IntelligenceVectorContractError, validate_intelligence_vector

COPY = {
'en': {
'title':'Earnings evidence','subtitle':'Review what was known. Keep entry and hold decisions separate.',
'cut':'Decision-time view','covered':'Reported earnings context is available for review, not a buy signal.',
'partial':'Some earnings evidence is available; missing comparisons remain explicit.',
'identity':'Canonical issuer identity is unresolved; earnings values are not supplied.',
'missing':'No eligible earnings evidence is available at this decision time.',
'corrected':'Later correction recorded. The figures retain the original decision-time evidence.',
'later_unknown':'A later revision was observed but cannot be fully projected; original figures are retained.',
'revenue':'Reported revenue','guidance':'Revenue growth outlook',
'revenue_note':'Source-reported amount; the fiscal period is not exposed as a separate field.',
'guidance_note':'Management guidance; the horizon is not exposed by this projection.',
'empty':'No source-backed numeric evidence','empty_note':'Absence is not zero revenue, a neutral revision, or a failed thesis.',
'comparison':'What remains unknown','prior':'Prior-period comparison','consensus':'Consensus comparison',
'unlicensed':'Not supplied: consensus is unlicensed in this packet.','unavailable':'Not supplied by the earnings owner.',
'no_delta':'No comparable revenue-change packet is supplied.','separate':'Separate decisions',
'expectations':'Forward expectations','expectations_note':'Not connected. This event packet is not the +1y EPS/revenue revision species.',
'entry':'New entry','entry_note':'Not asserted. Earnings evidence cannot grant entry permission.',
'hold':'Hold thesis','hold_note':'Not supplied. An earnings observation does not establish a hold instruction.',
'corrections':'Later correction','no_correction':'No later correction is exposed by this read; this is not a guarantee that none exists.',
'lineage':'Sources, clocks and corrections','scope_title':'Scope of this read',
'freshness':'Freshness is unknown: the owner supplies no staleness clock. This is not a live quote.',
'scope':'Current event discovery and current registrant identity only. This is not a complete historical event set.',
'authority':'All source and view authorities remain false. No ranking, sizing, entry change or order is produced.',
'integrity':'The native D5 contract is checked. Hash consistency does not independently authenticate a supplied file.',
'guidance_absent':'Guidance not supplied','absent_note':'The source marks guidance absent; retained bounds are not an active outlook.','guidance_withdrawn':'Guidance withdrawn','withdrawn_note':'The earlier numeric bounds remain in the receipt; they are not current guidance.',
'guidance_status':'Guidance status','missing_bound':'not supplied','million_usd':'USD million',
'COVERED':'Evidence supplied','PARTIAL':'Partial evidence','NOT_COVERED':'Not covered','UNKNOWN':'Unknown',
'introduced':'introduced','reiterated':'reiterated','raised':'raised','cut_status':'cut','withdrawn':'withdrawn','absent':'absent'},
'zh': {
'title':'财报证据','subtitle':'查看当时已知信息，分别判断开仓与持有。',
'cut':'决策时点视图','covered':'已有财报背景信息可供研究，但这不是买入信号。',
'partial':'部分财报证据可用；缺失的比较数据仍会明确保留。',
'identity':'发行人身份尚未完成规范匹配，因此不提供财报数值。',
'missing':'该决策时点没有可采用的财报证据。',
'corrected':'已记录后续更正；数值仍保留原决策时点可知的信息。',
'later_unknown':'已观察到后续修订，但无法完整展示；原始数值保持不变。',
'revenue':'已报告营收','guidance':'营收增长指引',
'revenue_note':'这是来源报告的金额；当前数据接口未单独提供财务期间。',
'guidance_note':'这是管理层指引；当前数据接口未单独提供预测期限。',
'empty':'没有可追溯的数值证据','empty_note':'缺失不代表营收为零、预期没有变化，也不代表投资逻辑失效。',
'comparison':'仍有哪些未知','prior':'历史同期比较','consensus':'市场一致预期比较',
'unlicensed':'未提供：此数据包中的一致预期没有使用许可。','unavailable':'财报数据方未提供。',
'no_delta':'未提供可比较的营收变动数据包。','separate':'分别判断',
'expectations':'未来盈利预期','expectations_note':'尚未接入。财报事件数据不等于未来一年每股收益与营收预期修订。',
'entry':'新开仓','entry_note':'未作判断。财报证据不能授予开仓许可。',
'hold':'持有逻辑','hold_note':'未提供。财报观察本身不能构成持有指令。',
'corrections':'后续更正','no_correction':'本次读取未展示后续更正，但不保证不存在更正。',
'lineage':'来源、时点与更正','scope_title':'本次读取的范围',
'freshness':'时效性未知：数据方未提供过期判定时钟。这不是实时报价。',
'scope':'仅发现当前事件并匹配当前注册主体，不代表完整的历史事件集合。',
'authority':'来源与视图的所有权限均保持关闭：不排名、不定仓、不改变开仓状态，也不生成订单。',
'integrity':'已执行原有 D5 数据规范检查；哈希一致本身不能证明外部文件的真实性。',
'guidance_absent':'未提供指引','absent_note':'来源将指引标记为缺失；保留的范围不代表有效预期。','guidance_withdrawn':'指引已撤回','withdrawn_note':'历史数值范围保留在来源记录中，不代表当前指引。',
'guidance_status':'指引状态','missing_bound':'未提供','million_usd':'百万美元',
'COVERED':'已提供证据','PARTIAL':'部分证据','NOT_COVERED':'未覆盖','UNKNOWN':'未知',
'introduced':'首次发布','reiterated':'维持','raised':'上调','cut_status':'下调','withdrawn':'撤回','absent':'缺失'}
}

def build_earnings_view(vector, *, language='en'):
    if language not in COPY: raise ValueError('language must be en or zh')
    text=COPY[language]
    source=deepcopy(vector)
    validate_intelligence_vector(source)
    if any(e.get('type')=='WorkspaceChainIntegrityError' for e in source['assembly_receipt']['errors']):
        raise IntelligenceVectorContractError('source integrity failure cannot become empty success')
    family=source['evidence_families'][0]
    if family['evidence_family_id']!='earnings.event': raise IntelligenceVectorContractError('unsupported family')
    metrics=[]
    for obs in family['observations']:
        if obs['value_state']!='PRESENT': continue
        key=obs['native_metric_id']
        if key not in {'fact:revenue','guidance:revenue_yoy_pct'}: raise IntelligenceVectorContractError('unsupported metric')
        name='revenue' if key=='fact:revenue' else 'guidance'
        metrics.append({'observation_id':obs['observation_id'],'native_metric_id':key,'label':text[name],
                        'value':deepcopy(obs['value']),'units':obs['units'],'note':text[name+'_note'],
                        'guidance_status':next((f.split(':',1)[1] for f in obs['quality_flags'] if f.startswith('status:')),None),
                        'source_ref_ids':list(obs['source_ref_ids'])})
    coverage=family['coverage']['state']; correction=family['correction']
    summary=text['identity'] if family['identity_state']!='RESOLVED' else text.get(coverage.lower(),text['missing'])
    if correction['current_state']=='CORRECTED': summary=text['corrected']
    elif correction['later_revision_state']=='OBSERVED_UNPROJECTABLE': summary=text['later_unknown']
    delta=next((d['value'] for d in family['trajectory']['dimensions'] if d['native_metric_id']=='metric_delta:revenue'),None)
    result={'view_version':'earnings-detail/1','language':language,'source_projection_id':source['projection_id'],
            'source_schema':source['schema'],'episode_ref':deepcopy(source['episode_ref']),
            'decision_cut':deepcopy(source['decision_cut']),'summary':summary,'metrics':metrics,'comparison':deepcopy(delta),
            'assembly_receipt':deepcopy(source['assembly_receipt']),'authority':deepcopy(source['authority']),
            'expectation_revision':{'state':'NOT_CONNECTED','strategy_id':'quality_earnings_expectation_revision/v1','source_horizon':'+1y','horizon_sessions':21},
            'availability':deepcopy(source['decision_cut']['tradable_at']),'hold':{'state':'NOT_SUPPLIED','horizon_role':'hold_thesis'}}
    for key in ['coverage','rights','freshness','identity_state','point_in_time','correction','source_refs','owner_lane_dispositions','owner_warnings']:
        result[key]=deepcopy(family[key])
    result['presentation'] = _presentation(result, text)
    return result

# Exact DS V1 section 2.2 fallback scales where shared spacing/radius tokens
# have not landed. Colors and material treatment still use the shared tokens.
STYLE = """
.plab-evidence{color:var(--text);font-family:var(--font-ui);font-size:var(--fs-body);line-height:1.55;min-width:0}
.plab-evidence *{box-sizing:border-box}.plab-evidence header{margin-bottom:var(--sp-6,24px)}
.plab-evidence h2{font-size:var(--fs-h1);line-height:1.15;margin:0 0 var(--sp-2,8px);font-weight:800}
.plab-evidence h3{font-size:var(--fs-h2);margin:0 0 var(--sp-3,12px)}.plab-evidence p{margin:0 0 var(--sp-3,12px)}
.plab-evidence .pe-muted{color:var(--muted)}
.plab-evidence .pe-state{padding:var(--sp-4,16px);border:1px solid var(--line);border-left:3px solid var(--info);border-radius:var(--r-ctl,8px);background:var(--panel2);margin-bottom:var(--sp-5,20px)}
.plab-evidence .pe-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--sp-4,16px);margin:var(--sp-4,16px) 0 var(--sp-6,24px)}
.plab-evidence .pe-card{min-width:0;padding:var(--sp-5,20px);background:var(--panel);border:1px solid var(--line);border-radius:var(--r-card,12px);box-shadow:var(--card-shadow)}
.plab-evidence .pe-value{font-size:var(--fs-num-lg);font-weight:800;line-height:1.3;font-variant-numeric:tabular-nums;overflow-wrap:anywhere;margin:var(--sp-2,8px) 0 var(--sp-3,12px)}
.plab-evidence .pe-label{font-size:var(--fs-sm);font-weight:700}.plab-evidence .pe-section{margin-top:var(--sp-6,24px)}
.plab-evidence .pe-row{display:grid;grid-template-columns:minmax(8rem,1fr) minmax(0,3fr);gap:var(--sp-4,16px);padding:var(--sp-3,12px) 0;border-top:1px solid var(--line)}
.plab-evidence details{margin-top:var(--sp-5,20px);border-top:1px solid var(--line);padding-top:var(--sp-4,16px)}
.plab-evidence summary{cursor:pointer;font-weight:700;min-height:44px;display:list-item;padding:var(--sp-2,8px) 0}
.plab-evidence summary:focus-visible{outline:2px solid var(--info);outline-offset:4px}
.plab-evidence pre{font-family:var(--font-mono);font-size:var(--fs-sm);white-space:pre-wrap;overflow-wrap:anywhere;padding:var(--sp-4,16px);background:var(--panel2);border-radius:var(--r-ctl,8px);max-width:100%}
.plab-evidence .pe-foot{border-top:1px solid var(--line);padding-top:var(--sp-4,16px);margin-top:var(--sp-6,24px);font-size:var(--fs-sm);color:var(--muted)}
html[data-theme="light"] .plab-evidence .pe-state{background:var(--panel);box-shadow:var(--card-shadow)}
html[data-theme="light"] .plab-evidence .pe-card{box-shadow:var(--card-shadow);border-color:var(--line)}
@media(max-width:600px){.plab-evidence .pe-grid{grid-template-columns:1fr}.plab-evidence .pe-row{grid-template-columns:1fr;gap:var(--sp-1,4px)}}
"""

def _h(value): return escape(str(value),quote=True)
def _num(value,text): return text['missing_bound'] if value is None else format(value,',.6f').rstrip('0').rstrip('.')

def _presentation(view, text):
    """One source of wording and number formatting for both native consumers."""
    for metric in view['metrics']:
        value = metric['value']
        if isinstance(value, dict):
            display = f"{_num(value['low'], text)} – {_num(value['high'], text)}%"
        elif metric['units'] == 'USD':
            display = '$' + _num(value, text)
        else:
            display = _num(value, text) + ' ' + text['million_usd']
        metric['display_value'] = display
        status = metric['guidance_status']
        metric['guidance_status_label'] = text['cut_status' if status == 'cut' else status] if status else None
        if status in {'withdrawn', 'absent'}:
            metric['display_value'] = text['guidance_' + status]
            metric['note'] = text[status + '_note']
    correction = view['correction']
    correction_note = (text['corrected'] if correction['current_state'] == 'CORRECTED'
                       else text['later_unknown'] if correction['later_revision_state'] == 'OBSERVED_UNPROJECTABLE'
                       else text['no_correction'])
    comparisons = []
    if view['comparison']:
        for key in ['prior', 'consensus']:
            note = text['unlicensed'] if view['comparison'][key].get('reason') == 'consensus_unlicensed' else text['unavailable']
            comparisons.append({'label': text[key], 'note': note})
    return {
        'title': text['title'], 'subtitle': text['subtitle'], 'cut_label': text['cut'],
        'coverage_label': text.get(view['coverage']['state'], text['UNKNOWN']),
        'guidance_status_label': text['guidance_status'],
        'comparison_title': text['comparison'], 'comparisons': comparisons, 'no_comparison': text['no_delta'],
        'separate_title': text['separate'],
        'separate': [{'label': text[k], 'note': text[k + '_note']} for k in ['expectations', 'entry', 'hold']],
        'correction_title': text['corrections'], 'correction_note': correction_note,
        'lineage_title': text['lineage'], 'scope_title': text['scope_title'],
        'scope_notes': [text[k] for k in ['freshness', 'scope', 'authority', 'integrity']],
        'empty_title': text['empty'], 'empty_note': text['empty_note'],
    }


def render_earnings_fragment(vector, *, language='en'):
    v=build_earnings_view(vector,language=language); t=COPY[language]; cards=[]
    for m in v['metrics']:
        display=m['display_value']
        status=m['guidance_status']; label=m['guidance_status_label'] or ''
        status_html=f"<p class='pe-muted'>{_h(t['guidance_status'])}: {_h(label)}</p>" if status else ''
        cards.append(f"<section class='pe-card'><div class='pe-label'>{_h(m['label'])}</div><p class='pe-value'>{_h(display)}</p>{status_html}<p class='pe-muted'>{_h(m['note'])}</p></section>")
    metrics='<div class="pe-grid">'+''.join(cards)+'</div>' if cards else f"<section class='pe-card'><h3>{_h(t['empty'])}</h3><p>{_h(t['empty_note'])}</p></section>"
    comparisons=[]
    if v['comparison']:
        for key in ['prior','consensus']:
            reason=t['unlicensed'] if v['comparison'][key].get('reason')=='consensus_unlicensed' else t['unavailable']
            comparisons.append(f"<div class='pe-row'><strong>{_h(t[key])}</strong><span>{_h(reason)}</span></div>")
    else: comparisons.append(f"<p class='pe-muted'>{_h(t['no_delta'])}</p>")
    separate=''.join(f"<div class='pe-row'><strong>{_h(t[k])}</strong><span>{_h(t[k+'_note'])}</span></div>" for k in ['expectations','entry','hold'])
    correction=v['correction']
    correction_text=t['corrected'] if correction['current_state']=='CORRECTED' else t['later_unknown'] if correction['later_revision_state']=='OBSERVED_UNPROJECTABLE' else t['no_correction']
    keys=['metrics','source_projection_id','episode_ref','decision_cut','coverage','rights','freshness','point_in_time','correction','source_refs','owner_lane_dispositions','owner_warnings','assembly_receipt','authority']
    receipt=_h(json.dumps({k:v[k] for k in keys},ensure_ascii=False,indent=2,allow_nan=False))
    badge=t.get(v['coverage']['state'],t['UNKNOWN'])
    return (f'<style>{STYLE}</style><article class="plab-evidence" lang="{language}" data-source-projection="{_h(v["source_projection_id"])}">'
            f"<header><h2>{_h(t['title'])}</h2><p>{_h(t['subtitle'])}</p><p class='pe-muted'>{_h(t['cut'])}: {_h(v['decision_cut']['opened_at'])} · {_h(badge)}</p></header>"
            f"<div class='pe-state' role='status'>{_h(v['summary'])}</div>{metrics}"
            f"<section class='pe-section'><h3>{_h(t['comparison'])}</h3>{''.join(comparisons)}</section>"
            f"<section class='pe-section'><h3>{_h(t['separate'])}</h3>{separate}</section>"
            f"<section class='pe-section'><h3>{_h(t['corrections'])}</h3><p>{_h(correction_text)}</p></section>"
            f"<details><summary>{_h(t['lineage'])}</summary><pre>{receipt}</pre></details>"
            f"<section class='pe-foot'><h3>{_h(t['scope_title'])}</h3><p>{_h(t['freshness'])}</p><p>{_h(t['scope'])}</p><p>{_h(t['authority'])}</p><p>{_h(t['integrity'])}</p></section></article>")
