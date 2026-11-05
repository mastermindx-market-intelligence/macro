"""Reported consolidated liquidity through the incumbent release-profile seam.

Quarter/H1 values and prior comparisons are source literals; no subtraction,
conversion, award arithmetic or common-shareholder cash attribution occurs.
"""
from __future__ import annotations
import re
from engine.company_intelligence.issuer_profiles import _fact_present, _fact_absent
from engine.earnings_release.receipts import receipt_for_literal, replay_receipt

_CASH_ROWS={
 'LMT':('Cash from operations','Free cash flow1'),
 'RTX':('Operating Cash Flow','Free Cash Flow*'),
 'NOC':('Net cash provided by (used in) operating activities','Adjusted free cash flow1'),
 'LHX':('Cash from operations','Free cash flow3'),
}
_FCF_BASIS={'LMT':'nonGAAP_free_cash_flow','RTX':'nonGAAP_free_cash_flow',
            'NOC':'nonGAAP_adjusted_free_cash_flow','LHX':'nonGAAP_free_cash_flow'}
_HEADINGS={'LMT':('Quarters Ended','Six Months Ended'),
 'RTX':('2nd Quarter',None),'NOC':('Three Months Ended June 30','Six Months Ended June 30'),
 'LHX':('Second Quarter','Year to Date')}

def cash_fact_rules(ticker, year, quarter):
    """Closed projection contract; duration and accounting basis stay explicit."""
    if ticker not in _CASH_ROWS or quarter!=2:return {}
    result={}
    for kind,basis in [('operating_cash','GAAP_operating_cash_flow'),('free_cash',_FCF_BASIS[ticker])]:
        for duration in ['quarter','half_year']:
            for prior in [False,True]:
                metric=f'issuer_{kind}_{duration}'+('_prior' if prior else '')
                period=f'{year-int(prior)}Q2' if duration=='quarter' else f'{year-int(prior)}H1'
                result[metric]=('reported_cashflow','USD_million',f'issuer_reported_consolidated:{basis}',period)
    return result

def _columns(table, heading, year):
    from engine.company_intelligence.defense_profiles import _layout_cells
    positions=_layout_cells(table)
    cells=[c for row in table.table.rows for c in row]
    matches=[c for c in cells if c.text.strip()==heading]
    if len(matches)!=1:raise ValueError('cash_duration_heading_ambiguous')
    start,end,row=positions[matches[0].cell_id]
    years=[c for c in cells if row<positions[c.cell_id][2]<=row+2 and start<=positions[c.cell_id][0]<positions[c.cell_id][1]<=end and re.fullmatch(r'(?:June [0-9]{1,2},? )?20[0-9]{2}',c.text.strip())]
    years.sort(key=lambda c:positions[c.cell_id][0])
    if len(years)!=2 or [int(re.search(r'20[0-9]{2}',c.text).group()) for c in years]!=[year,year-1]:raise ValueError('cash_current_prior_columns_unqualified')
    return [positions[c.cell_id][:2] for c in years],positions

def _row(table,label):
    rows=[r for r in table.table.rows if next((c.text.strip() for c in r if c.text.strip()),'')==label]
    if len(rows)!=1:raise ValueError('cash_row_missing_or_ambiguous')
    return rows[0]

def extract_cash_facts(*,ticker,bound,document_id,event_id,fiscal_period):
    from engine.company_intelligence.defense_profiles import _selected_number
    rules=cash_fact_rules(ticker,fiscal_period.year,fiscal_period.quarter)
    if not rules:return []
    output=[]
    def absent(metric,reason):return _fact_absent(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,detail=reason,document_id=document_id)
    for duration in ('quarter','half_year'):
        heading=_HEADINGS[ticker][duration=='half_year']
        labels=_CASH_ROWS[ticker]
        tables=[b for b in bound.document.blocks if b.table and heading and heading in b.text and all(label in b.text for label in labels)]
        if ticker=='RTX' and duration=='half_year':
            # RTX's reconciliation combines quarter and H1 as separate vertical
            # sections, unlike other issuers' horizontal columns.
            heading='Six Months Ended June 30,'
            labels=('Net cash flows provided by operating activities','Free cash flow')
            tables=[b for b in bound.document.blocks if b.table and heading in b.text and 'Quarter Ended June 30,' in b.text and all(label in b.text for label in labels)]
        metrics=[m for m in rules if f'_{duration}' in m]
        try:
            if len(tables)!=1:raise ValueError('cash_table_missing_or_ambiguous')
            table=tables[0]
            if 'million' not in table.text.lower() or '$' not in table.text:raise ValueError('cash_USD_million_units_unqualified')
            columns,positions=_columns(table,heading,fiscal_period.year)
            selected_rows=table.table.rows
            if ticker=='RTX' and duration=='half_year':
                header=[c for r in table.table.rows for c in r if c.text.strip()==heading][0]
                header_row=positions[header.cell_id][2]
                selected_rows=[r for r in table.table.rows if r and positions[r[0].cell_id][2]>header_row]
                from types import SimpleNamespace
                selected_table=SimpleNamespace(table=SimpleNamespace(rows=selected_rows))
            else:selected_table=table
            for kind,label in zip(('operating_cash','free_cash'),labels):
                row=_row(selected_table,label)
                for prior,column in zip((False,True),columns):
                    metric=f'issuer_{kind}_{duration}'+('_prior' if prior else '')
                    cell,value=_selected_number(row,column,positions)
                    receipt=receipt_for_literal(source=bound.source,source_sha256=bound.revision.source_sha256,search_start=cell.source_span.char_start,search_end=cell.source_span.char_end,literal=cell.text.strip())
                    replay_receipt(receipt,source=bound.source)
                    _,unit,basis,period=rules[metric]
                    output.append(_fact_present(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,value=value,unit=unit,period=period,basis=basis,document_id=document_id,bound=bound,receipt=receipt))
        except ValueError as exc:
            # No partial same-duration admission after an ambiguous header/row.
            output=[f for f in output if f['metric'] not in metrics]
            output.extend(absent(metric,str(exc)) for metric in metrics)
    return output


def additional_fact_rules(ticker,year,quarter):
    if quarter!=2 or ticker not in _CASH_ROWS:return {}
    rules={}
    if ticker in ('LMT','NOC'):
        for prior in (False,True):
            period=f'{year-1}-12-31' if prior else f'{year}-06-'+('28' if ticker=='LMT' else '30')
            rules['issuer_backlog'+('_prior' if prior else '')]=('reported_backlog','USD_million','issuer_reported_consolidated:total_backlog_stock',period)
        if ticker=='NOC':
            for scope in ('funded','unfunded'):
                rules['issuer_backlog_'+scope]=('reported_backlog','USD_million','issuer_reported_consolidated:'+scope+'_backlog_stock',f'{year}-06-30')
    else:
        rules['issuer_backlog']=('reported_backlog','USD_billion','issuer_reported_consolidated:total_backlog_stock',f'{year}Q2')
        if ticker=='RTX':
            for scope in ('commercial','defense'):
                rules['issuer_backlog_'+scope]=('reported_backlog','USD_billion','issuer_reported_consolidated:'+scope+'_backlog_stock',f'{year}Q2')
    for kind in ('operating_cash','free_cash'):
        if ticker=='NOC' and kind=='operating_cash':continue
        for relation in (('current','prior') if ticker=='LMT' else ('current',)):
            for edge in (('point',) if ticker=='LHX' else ('low','high')):
                metric=f'issuer_{kind}_guidance_{edge}'+('_prior' if relation=='prior' else '')
                unit='USD_billion' if ticker in ('RTX','LHX') else 'USD_million'
                basis='GAAP_operating_cash_flow' if kind=='operating_cash' else _FCF_BASIS[ticker]
                rules[metric]=('reported_guidance',unit,'issuer_guidance_consolidated:'+basis,f'{year}FY')
    # RTX discloses FCF guidance, not CFO guidance in this qualified release.
    if ticker=='RTX':rules={k:v for k,v in rules.items() if not k.startswith('issuer_operating_cash_guidance')}
    return rules


def extract_additional_facts(*,ticker,bound,document_id,event_id,fiscal_period):
    from engine.company_intelligence.defense_profiles import _layout_cells,_selected_number
    rules=additional_fact_rules(ticker,fiscal_period.year,fiscal_period.quarter);output=[]
    def emit(metric,cell,literal,value,search_end=None):
        receipt=receipt_for_literal(source=bound.source,source_sha256=bound.revision.source_sha256,search_start=cell.source_span.char_start,search_end=search_end or cell.source_span.char_end,literal=literal)
        replay_receipt(receipt,source=bound.source)
        _,unit,basis,period=rules[metric]
        output.append(_fact_present(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,value=value,unit=unit,period=period,basis=basis,document_id=document_id,bound=bound,receipt=receipt))
    # Backlog stocks are independently selected source columns, not forecasts.
    try:
        if ticker in ('LMT','NOC'):
            tables=[b for b in bound.document.blocks if b.table and any(next((c.text.strip() for c in r if c.text.strip()),'')=='Total backlog' for r in b.table.rows)]
            if len(tables)!=1:raise ValueError('backlog_table_ambiguous')
            table=tables[0];pos=_layout_cells(table);row=_row(table,'Total backlog')
            context=' '.join(b.text for b in bound.document.blocks[max(0,bound.document.blocks.index(table)-1):bound.document.blocks.index(table)+1])
            if 'million' not in context.lower() or '$' not in table.text:raise ValueError('backlog_units_unqualified')
            cells=[c for r in table.table.rows for c in r]
            if ticker=='LMT':
                labels=[f'June 28, {fiscal_period.year}',f'Dec. 31, {fiscal_period.year-1}']
                columns=[]
                for label in labels:
                    headers=[c for c in cells if c.text.strip()==label]
                    if len(headers)!=1:raise ValueError('backlog_date_heading_unqualified')
                    columns.append(pos[headers[0].cell_id][:2])
            else:
                dates=[c for c in cells if c.text.strip()==f'June 30, {fiscal_period.year}'];prior=[c for c in cells if c.text.strip()==f'December 31, {fiscal_period.year-1}']
                if len(dates)!=1 or len(prior)!=1:raise ValueError('backlog_date_heading_unqualified')
                current_bounds=pos[dates[0].cell_id][:2];prior_bounds=pos[prior[0].cell_id][:2]
                def col(label,bounds):
                    found=[c for c in cells if c.text.strip()==label and bounds[0]<=pos[c.cell_id][0]<pos[c.cell_id][1]<=bounds[1]]
                    if len(found)!=1:raise ValueError('backlog_funding_column_unqualified')
                    return pos[found[0].cell_id][:2]
                columns=[col('Total Backlog2',current_bounds),col('Total Backlog2',prior_bounds)]
                for scope,label in [('funded','Funded1'),('unfunded','Unfunded')]:
                    cell,value=_selected_number(row,col(label,current_bounds),pos);emit('issuer_backlog_'+scope,cell,cell.text.strip(),value)
            for metric,column in zip(('issuer_backlog','issuer_backlog_prior'),columns):
                cell,value=_selected_number(row,column,pos);emit(metric,cell,cell.text.strip(),value)
        else:
            pattern=r'Company backlog of \$(\d+) billion, including \$(\d+) billion of commercial and \$(\d+) billion of defense' if ticker=='RTX' else r'increases backlog to record \$(\d+) billion'
            matches=[(b,m) for b in bound.document.blocks if not b.table for m in [re.search(pattern,b.text)] if m]
            if len(matches)!=1:raise ValueError('backlog_prose_missing_or_ambiguous')
            block,match=matches[0]
            metrics=('issuer_backlog','issuer_backlog_commercial','issuer_backlog_defense') if ticker=='RTX' else ('issuer_backlog',)
            for group,metric in enumerate(metrics,1):emit(metric,block,match.group(group),float(match.group(group)))
    except ValueError as exc:
        output=[f for f in output if not f['metric'].startswith('issuer_backlog')]
        output.extend(_fact_absent(fact_id=event_id+':'+m,event_id=event_id,metric=m,detail=str(exc),document_id=document_id) for m in rules if m.startswith('issuer_backlog'))
    # Guidance uses range endpoints/point literals, with explicit forecast basis.
    for kind,label in zip(('operating_cash','free_cash'),_CASH_ROWS[ticker]):
        metrics=[m for m in rules if m.startswith('issuer_'+kind+'_guidance')]
        if not metrics:continue
        try:
            if ticker=='RTX':
                matches=[(b,re.search(r'Free cash flow\* of \$(\d+\.\d+) - \$(\d+\.\d+) billion, up from',b.text)) for b in bound.document.blocks if not b.table]
                matches=[v for v in matches if v[1]]
                if len(matches)!=1:raise ValueError('guidance_prose_ambiguous')
                block,match=matches[0]
                window=bound.source[block.source_span.char_start:block.source_span.char_end]
                separator=window.find('up from')
                if separator<0:raise ValueError('guidance_current_prior_literal_boundary_unqualified')
                for group,edge in enumerate(('low','high'),1):emit(f'issuer_{kind}_guidance_{edge}',block,match.group(group),float(match.group(group)),block.source_span.char_start+separator)
                continue
            tables=[b for b in bound.document.blocks if b.table and ('Current Update' if ticker=='LMT' else f'{fiscal_period.year} Guidance') in b.text and any(next((c.text.strip() for c in r if c.text.strip()),'')==label for r in b.table.rows)]
            if len(tables)!=1:raise ValueError('guidance_table_ambiguous')
            table=tables[0];pos=_layout_cells(table);row=_row(table,label)
            if 'million' not in table.text.lower() or '$' not in table.text:raise ValueError('guidance_units_unqualified')
            if ticker=='LHX':
                heading=[c for r in table.table.rows for c in r if c.text.strip()==f'{fiscal_period.year} Guidance']
                if len(heading)!=1:raise ValueError('guidance_column_ambiguous')
                bounds=pos[heading[0].cell_id][:2]
                selected=[c for c in row if bounds[0]<=pos[c.cell_id][0]<pos[c.cell_id][1]<=bounds[1] and c.text.strip()]
            elif ticker=='LMT':
                allcells=[c for r in table.table.rows for c in r]
                current=[c for c in allcells if c.text.strip()=='Current Update']
                prior=[c for c in allcells if c.text.strip()==f'April {fiscal_period.year}']
                if len(current)!=1 or len(prior)!=1 or pos[current[0].cell_id][0]>=pos[prior[0].cell_id][0]:raise ValueError('guidance_update_heading_order_unqualified')
                selected=[]
                for header in (current[0],prior[0]):
                    bounds=pos[header.cell_id][:2]
                    candidates=[c for c in row if bounds[0]<=pos[c.cell_id][0]<pos[c.cell_id][1]<=bounds[1] and c.text.strip()]
                    if len(candidates)!=1:raise ValueError('guidance_update_literal_column_unqualified')
                    selected+=candidates
            else:selected=[c for c in row if '$' in c.text and c.text.strip()!=label]
            if len(selected)!=(2 if ticker=='LMT' else 1):raise ValueError('guidance_current_prior_columns_unqualified')
            for i,cell in enumerate(selected):
                relation='_prior' if i else ''
                # Cell-level units can override a table's millions heading.
                # LHX explicitly prints B; the other qualified cells print
                # dollar ranges without a suffix in declared-million tables.
                if ticker=='LHX':
                    if not re.fullmatch(r'\$\d+(?:\.\d+)?B',cell.text.strip()):raise ValueError('guidance_selected_cell_billion_unit_unqualified')
                elif not re.fullmatch(r'~?\$\d[\d,]*(?:\.\d+)?\s*[-—]\s*\$\d[\d,]*(?:\.\d+)?',cell.text.strip()):
                    raise ValueError('guidance_selected_cell_million_unit_unqualified')
                values=re.findall(r'\d[\d,]*(?:\.\d+)?',cell.text)
                if len(values)!=(1 if ticker=='LHX' else 2):raise ValueError('guidance_range_unqualified')
                for edge,literal in zip(('point',) if ticker=='LHX' else ('low','high'),values):emit(f'issuer_{kind}_guidance_{edge}'+relation,cell,literal,float(literal.replace(',','')))
        except ValueError as exc:
            output=[f for f in output if f['metric'] not in metrics]
            output.extend(_fact_absent(fact_id=event_id+':'+m,event_id=event_id,metric=m,detail=str(exc),document_id=document_id) for m in metrics)
    return output


def _financial_base_rules(ticker,year,quarter):
    return {**cash_fact_rules(ticker,year,quarter),**additional_fact_rules(ticker,year,quarter)}


def _extract_base_financial_facts(**kwargs):
    return extract_cash_facts(**kwargs)+extract_additional_facts(**kwargs)

_COMPONENT_LABELS={'receivables':'Receivables, net','contract_assets':'Contract assets','inventories':'Inventories','accounts_payable':'Accounts payable','contract_liabilities':'Contract liabilities'}

def working_capital_fact_rules(ticker,year,quarter):
    if ticker not in ('LMT','LHX') or quarter!=2:return {}
    return {f'issuer_{component}_cash_change_half_year'+('_prior' if prior else ''):
            ('reported_cashflow','USD_million',f'issuer_reported_consolidated:GAAP_cashflow_change_in_{component}',f'{year-int(prior)}H1')
            for component in _COMPONENT_LABELS for prior in (False,True)}

def extract_working_capital_components(*,ticker,bound,document_id,event_id,fiscal_period):
    """Signed disclosed H1 cash-flow movements, never working-capital stock."""
    from engine.company_intelligence.defense_profiles import _selected_number
    rules=working_capital_fact_rules(ticker,fiscal_period.year,fiscal_period.quarter)
    if not rules:return []
    output=[]
    try:
        tables=[b for b in bound.document.blocks if b.table and 'Contract assets' in b.text and 'Contract liabilities' in b.text and 'Operating' in b.text and 'activities' in b.text.lower() and 'Capital expenditures' in b.text]
        if len(tables)!=1:raise ValueError('working_capital_cash_statement_ambiguous')
        table=tables[0];i=bound.document.blocks.index(table);context=' '.join(b.text for b in bound.document.blocks[max(0,i-1):i+1])
        if 'million' not in context.lower() or '$' not in table.text:raise ValueError('working_capital_cash_units_unqualified')
        columns,positions=_columns(table,'Six Months Ended' if ticker=='LMT' else 'Year to Date',fiscal_period.year)
        for component,label in _COMPONENT_LABELS.items():
            if ticker=='LHX' and component=='inventories':label='Inventories, net'
            row=_row(table,label)
            for prior,column in zip((False,True),columns):
                metric=f'issuer_{component}_cash_change_half_year'+('_prior' if prior else '')
                cell,value=_selected_number(row,column,positions)
                receipt=receipt_for_literal(source=bound.source,source_sha256=bound.revision.source_sha256,search_start=cell.source_span.char_start,search_end=cell.source_span.char_end,literal=cell.text.strip())
                replay_receipt(receipt,source=bound.source)
                _,unit,basis,period=rules[metric]
                output.append(_fact_present(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,value=value,unit=unit,period=period,basis=basis,document_id=document_id,bound=bound,receipt=receipt))
    except ValueError as exc:
        return [_fact_absent(fact_id=event_id+':'+m,event_id=event_id,metric=m,detail=str(exc),document_id=document_id) for m in rules]
    return output

# Extend the same profile catalogue with explicitly signed source components.

def financial_fact_rules(ticker,year,quarter):
    from engine.company_intelligence.defense_space_profiles import space_fact_rules, space_adverse_fact_rules
    return {**_financial_base_rules(ticker,year,quarter),**working_capital_fact_rules(ticker,year,quarter),**space_fact_rules(ticker,year,quarter),**space_adverse_fact_rules(ticker,year,quarter)}

def extract_financial_facts(**kwargs):
    from engine.company_intelligence.defense_space_profiles import extract_space_facts, extract_space_adverse_facts
    return _extract_base_financial_facts(**kwargs)+extract_working_capital_components(**kwargs)+extract_space_facts(**kwargs)+extract_space_adverse_facts(**kwargs)
