"""NOC adverse/comparative context through the existing issuer fact seam.

Does not originate a program ID, sum EAC adjustments, infer cash loss, or
create an equity/risk signal. The prior figures are available in the current
release, not historical-house point-in-time evidence.
"""
import re
from engine.company_intelligence import defense_profiles as p
from engine.company_intelligence.issuer_profiles import IssuerProfile,_fact_present,_fact_absent
from engine.earnings_release.receipts import receipt_for_literal,replay_receipt,ReceiptError
from engine.earnings_release.figures import parse_numeric

EXTRA_METRICS=('defense_segment_prior_margin','siaw_unfavorable_eac','sentinel_prior_favorable_eac')
_WORDS={1:'First',2:'Second',3:'Third',4:'Fourth'}


def extract_noc_adverse_facts(*,bound,document_id,event_id,fiscal_period):
    result=[]
    def absent(metric,detail):return _fact_absent(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,detail=detail,document_id=document_id)
    def literal(metric,cell,period,basis,unit):
        number=parse_numeric(cell.text)
        if number is None:raise ValueError('numeric_literal_missing')
        receipt=receipt_for_literal(source=bound.source,source_sha256=bound.revision.source_sha256,search_start=cell.source_span.char_start,search_end=cell.source_span.char_end,literal=cell.text.strip())
        replay_receipt(receipt,source=bound.source)
        return _fact_present(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,value=number[0],unit=unit,period=period,basis=basis,document_id=document_id,bound=bound,receipt=receipt)
    try:
        table=p._segment_table(bound,'NOC');current,_,positions=p._current_column(table,'NOC')
        if current!=fiscal_period:raise ValueError('fiscal_period_mismatch')
        quarter_headers=[c for row in table.table.rows for c in row if c.text.startswith('Three Months Ended')]
        if len(quarter_headers)!=1:raise ValueError('comparative_quarter_header_ambiguous')
        qstart,qend,qrow=positions[quarter_headers[0].cell_id]
        prior_headers=[c for row in table.table.rows for c in row if c.text==str(current.year-1) and positions[c.cell_id][2]==qrow+1 and qstart<=positions[c.cell_id][0]<positions[c.cell_id][1]<=qend]
        if len(prior_headers)!=1:raise ValueError('comparative_period_header_ambiguous')
        prior=prior_headers[0];prior_period=f'{int(prior.text)}Q{current.quarter}'
        row=p._row_for(table,'NOC','Operating margin rate');cell,_=p._selected_number(row,positions[prior.cell_id][:2],positions)
        result.append(literal(EXTRA_METRICS[0],cell,prior_period,'issuer_reported_segment:Defense Systems:reported','percent'))
    except (ValueError,ReceiptError,TypeError) as exc:
        return [absent(m,type(exc).__name__) for m in EXTRA_METRICS]
    blocks=[b for b in bound.document.blocks if not b.table and 'SiAW' in b.text and 'unfavorable EAC adjustment' in b.text]
    if len(blocks)!=1 or f'{_WORDS[current.quarter]} quarter {current.year}' not in blocks[0].text:
        return [*result,*(absent(m,'adverse_current_period_paragraph_missing_or_ambiguous') for m in EXTRA_METRICS[1:])]
    block=blocks[0]
    rules=[(EXTRA_METRICS[1],r'\$([\d,]+(?:\.\d+)?) million unfavorable EAC adjustment on SiAW',f'{current.year}Q{current.quarter}','issuer_reported_program_cost_estimate:SiAW:unfavorable_EAC'),
           (EXTRA_METRICS[2],r'prior year \$([\d,]+(?:\.\d+)?) million favorable adjustment on Sentinel',prior_period,'issuer_reported_program_cost_estimate:Sentinel:prior_favorable_EAC')]
    for metric,pattern,period,basis in rules:
        matches=list(re.finditer(pattern,block.text))
        if len(matches)!=1:result.append(absent(metric,'adverse_clause_missing_or_ambiguous'));continue
        literal_text=matches[0].group(1)
        try:
            receipt=receipt_for_literal(source=bound.source,source_sha256=bound.revision.source_sha256,search_start=block.source_span.char_start,search_end=block.source_span.char_end,literal=literal_text)
            replay_receipt(receipt,source=bound.source)
            result.append(_fact_present(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,value=parse_numeric(literal_text)[0],unit='USD_million',period=period,basis=basis,document_id=document_id,bound=bound,receipt=receipt))
        except (ValueError,ReceiptError) as exc:result.append(absent(metric,type(exc).__name__))
    return result


def noc_adverse_profile():
    core=p.defense_profile('NOC')
    return IssuerProfile(ticker='NOC',extract_release_facts=lambda **kwargs:[*core.extract_release_facts(**kwargs),*extract_noc_adverse_facts(**kwargs)],extract_transcript_claims=core.extract_transcript_claims,extract_guidance=core.extract_guidance)
