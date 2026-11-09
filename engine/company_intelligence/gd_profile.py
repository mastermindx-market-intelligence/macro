"""GD Marine Systems current reported literals in the incumbent owner seam.

Funded backlog, unfunded backlog, total backlog and estimated potential
contract value remain separate issuer categories. No procurement obligation,
program workshare, common-shareholder capture, or sum is inferred.
"""
import re
from engine.company_intelligence import defense_profiles as p
from engine.company_intelligence.issuer_profiles import IssuerProfile,_fact_present,_fact_absent
from engine.company_intelligence.identity import IssuerIdentity,ListingAlias,company_id_for_cik
from engine.company_intelligence.events import FiscalPeriod
from engine.earnings_release.receipts import receipt_for_literal,replay_receipt,ReceiptError

GD_METRICS=('marine_segment_sales','marine_segment_operating_profit','marine_segment_margin','marine_funded_backlog','marine_unfunded_backlog','marine_total_backlog','marine_estimated_potential_contract_value','marine_total_estimated_contract_value')


def gd_issuer():
    return IssuerIdentity(company_id=company_id_for_cik('0000040533'),display_name='General Dynamics',fiscal_year_end_month=12,reporting_currency='USD',listings=(ListingAlias(ticker='GD',mic='XNYS',share_class='common',trading_currency='USD',is_primary=True),),external_ids={'cik':'0000040533'})


def _table(bound,*,backlog):
    found=[]
    for i,b in enumerate(bound.document.blocks):
        if not b.table or 'Marine Systems' not in b.text:continue
        qualified=('Funded' in b.text and 'Unfunded' in b.text and 'Total Backlog' in b.text) if backlog else ('Three Months Ended' in b.text and 'Revenue:' in b.text and 'Operating earnings:' in b.text and 'Operating margin:' in b.text)
        if qualified:
            if not any(q.text.strip()=='DOLLARS IN MILLIONS' for q in bound.document.blocks[max(i-3,0):i]):raise ValueError('gd_table_unit_not_source_qualified')
            found.append(b)
    if len(found)!=1:raise ValueError('gd_table_missing_or_ambiguous')
    return found[0]


def gd_fiscal_period(bound):
    labels=[re.fullmatch(r'General Dynamics Reports (First|Second|Third|Fourth)-Quarter (20[0-9]{2}) Financial Results',b.text) for b in bound.document.blocks if not b.table]
    labels=[m for m in labels if m]
    if len(labels)!=1:raise ValueError('gd_release_period_label_missing_or_ambiguous')
    m=labels[0];period=FiscalPeriod(int(m.group(2)),{'First':1,'Second':2,'Third':3,'Fourth':4}[m.group(1)])
    table=_table(bound,backlog=False);positions=p._layout_cells(table)
    headers=[c for row in table.table.rows for c in row if c.text=='Three Months Ended']
    if len(headers)!=1:raise ValueError('gd_quarter_header_unqualified')
    start,end,ordinal=positions[headers[0].cell_id]
    dates=[c for row in table.table.rows for c in row if positions[c.cell_id][2]==ordinal+1 and start<=positions[c.cell_id][0]<positions[c.cell_id][1]<=end and re.fullmatch(r'[A-Za-z]+ [0-9]{1,2}, (20[0-9]{2})',c.text)]
    dates.sort(key=lambda c:positions[c.cell_id][0])
    if len(dates)!=2 or not dates[0].text.endswith(str(period.year)) or not dates[1].text.endswith(str(period.year-1)):raise ValueError('gd_current_comparative_column_order_unqualified')
    return period


def extract_gd_facts(*,bound,document_id,event_id,fiscal_period):
    def absent(metric,reason):return _fact_absent(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,detail=reason,document_id=document_id)
    try:
        current=gd_fiscal_period(bound)
        if current!=fiscal_period:raise ValueError('gd_period_mismatch')
        table=_table(bound,backlog=False);positions=p._layout_cells(table)
        header=next(c for row in table.table.rows for c in row if c.text=='Three Months Ended');start,end,ordinal=positions[header.cell_id]
        current_date=next(c for row in table.table.rows for c in row if positions[c.cell_id][2]==ordinal+1 and start<=positions[c.cell_id][0]<positions[c.cell_id][1]<=end and re.fullmatch(r'[A-Za-z]+ [0-9]{1,2}, '+str(current.year),c.text))
        bounds=positions[current_date.cell_id][:2]
    except ValueError as exc:return [absent(m,str(exc)) for m in GD_METRICS]
    output=[]
    def present(metric,cell,value,basis):
        receipt=receipt_for_literal(source=bound.source,source_sha256=bound.revision.source_sha256,search_start=cell.source_span.char_start,search_end=cell.source_span.char_end,literal=cell.text.strip());replay_receipt(receipt,source=bound.source)
        return _fact_present(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,value=value,unit='percent' if metric.endswith('margin') else 'USD_million',period=f'{current.year}Q{current.quarter}',basis=basis,document_id=document_id,bound=bound,receipt=receipt)
    for metric,label in zip(GD_METRICS[:3],('Revenue:','Operating earnings:','Operating margin:')):
        try:
            starts=[i for i,row in enumerate(table.table.rows) if p._cells(row) and p._cells(row)[0].text==label]
            if len(starts)!=1:raise ValueError('gd_metric_section_ambiguous')
            selected=[]
            for row in table.table.rows[starts[0]+1:]:
                cells=p._cells(row)
                if cells and cells[0].text in ('Revenue:','Operating earnings:','Operating margin:'):break
                if cells and cells[0].text=='Marine Systems':selected.append(row);break
            if len(selected)!=1:raise ValueError('gd_segment_row_unqualified')
            cell,value=p._selected_number(selected[0],bounds,positions)
            output.append(present(metric,cell,value,'issuer_reported_segment:Marine Systems:reported'))
        except (ValueError,ReceiptError) as exc:output.append(absent(metric,type(exc).__name__))
    try:
        backlog=_table(bound,backlog=True);layout=p._layout_cells(backlog)
        label=('First','Second','Third','Fourth')[current.quarter-1]+' Quarter '+str(current.year)+':'
        section=[i for i,row in enumerate(backlog.table.rows) if any(c.text==label for c in row)]
        if len(section)!=1:raise ValueError('gd_backlog_period_section_ambiguous')
        row=None
        for candidate in backlog.table.rows[section[0]+1:]:
            cells=p._cells(candidate)
            if cells and re.fullmatch(r'(First|Second|Third|Fourth) Quarter [0-9]{4}:',cells[0].text):break
            if cells and cells[0].text=='Marine Systems':row=candidate;break
        if row is None:raise ValueError('gd_backlog_segment_missing')
        headers=('Funded','Unfunded','Total Backlog','EstimatedPotentialContract Value*','Total Estimated Contract Value')
        for metric,name in zip(GD_METRICS[3:],headers):
            matches=[c for header_row in backlog.table.rows[:section[0]] for c in header_row if c.text==name]
            if len(matches)!=1:raise ValueError('gd_backlog_category_header_ambiguous')
            cell,value=p._selected_number(row,layout[matches[0].cell_id][:2],layout)
            output.append(present(metric,cell,value,'issuer_reported_backlog_category:Marine Systems:'+name))
    except (ValueError,ReceiptError) as exc:
        output=[f for f in output if f['metric'] not in GD_METRICS[3:]]+[absent(m,type(exc).__name__) for m in GD_METRICS[3:]]
    return output


def gd_profile():return IssuerProfile(ticker='GD',extract_release_facts=extract_gd_facts,extract_transcript_claims=lambda **k:[],extract_guidance=lambda **k:[])
