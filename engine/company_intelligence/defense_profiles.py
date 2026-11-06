"""Defense segment extraction through the incumbent IssuerProfile seam.

Reads reported literals only. No program role/share, ratio, estimate, price or
financial truth store is constructed. The existing release binder/receipts and
Event Workspace producer continue to own document/event identity and clocks.
"""
from __future__ import annotations
import re
from engine.company_intelligence.issuer_profiles import (
    IssuerProfile, _fact_present, _fact_absent,
)
from engine.earnings_release.figures import parse_numeric
from engine.earnings_release.receipts import receipt_for_literal, replay_receipt, ReceiptError
from engine.company_intelligence.events import FiscalPeriod

SEGMENTS = {'LMT':'Missiles and Fire Control','RTX':'Raytheon',
            'NOC':'Defense Systems','LHX':'Missile Solutions'}
METRICS = ('defense_segment_sales','defense_segment_operating_profit','defense_segment_margin')
LABELS = {
    'LMT': ('Sales','Operating profit','Operating margin'),
    'NOC': ('Sales','Operating income','Operating margin rate'),
    'LHX': ('Revenue','Operating income','Operating margin'),
    'RTX': ('Net Sales','Operating Profit (Loss)','Segment Operating Profit Margin'),
}
_MONTHS = {'march':1,'june':2,'september':3,'december':4}
_QUARTERS = {'first':1,'second':2,'third':3,'fourth':4}


def _cells(row):
    return [c for c in row if c.text.strip()]


def _segment_table(bound, ticker):
    blocks=bound.document.blocks
    segment=SEGMENTS[ticker].lower()
    found=[]
    for i,block in enumerate(blocks):
        if ticker in ('LMT','LHX') and block.text.strip().lower()==segment:
            candidates=[z for z in blocks[i+1:i+4] if z.table]
            if candidates: found.append(candidates[0])
        elif ticker=='NOC' and block.table:
            rows=[_cells(v) for v in block.table.rows]
            if any(v and v[0].text.strip().lower()==segment and 'three months ended' in ' '.join(c.text for c in v).lower() for v in rows):
                found.append(block)
        elif ticker=='RTX' and block.table and all(v in block.text for v in ('Quarter Ended','Reported','Adjusted','Net Sales','Segment Operating Profit Margin','Raytheon')):
            found.append(block)
    if len(found)!=1: return None
    return found[0]


def _layout_cells(table):
    """Bounded local HTML geometry; no generic financial parser changes."""
    positions={};occupied={}
    for row in table.table.rows:
        if not row:continue
        ordinal=row[0].row_ordinal if row[0].row_ordinal>=0 else row[0].row_index
        col=0
        for cell in row:
            if cell.span_overflow or cell.rowspan==0 or not 1<=cell.colspan<=64 or not 1<=cell.rowspan<=64:
                raise ValueError('unsupported_header_geometry')
            while occupied.get(col,-1)>=ordinal:col+=1
            end=col+cell.colspan
            if end>128 or any(occupied.get(c,-1)>=ordinal for c in range(col,end)):
                raise ValueError('ambiguous_header_geometry')
            positions[cell.cell_id]=(col,end,ordinal)
            if cell.rowspan>1:
                for c in range(col,end):occupied[c]=ordinal+cell.rowspan-1
            col=end
    return positions


def _current_column(table,ticker):
    if table is None:raise ValueError('segment_table_missing_or_ambiguous')
    positions=_layout_cells(table)
    def inside(cell,bounds):
        start,end,_=positions[cell.cell_id]
        return bounds[0]<=start<end<=bounds[1]
    cells=[c for row in table.table.rows for c in row]
    quarter_headers=[c for c in cells if re.fullmatch(r'(Quarters? Ended|Three Months Ended(?: [A-Za-z]+ [0-9]+)?|(?:First|Second|Third|Fourth) Quarter)',c.text.strip(),re.I)]
    if len(quarter_headers)!=1:raise ValueError('quarter_header_missing_or_ambiguous')
    heading=quarter_headers[0];qstart,qend,qrow=positions[heading.cell_id]
    period_rows={}
    for cell in cells:
        _,_,row=positions[cell.cell_id]
        if qrow<row<=qrow+4 and inside(cell,(qstart,qend)):
            # Only standalone year or exact month-day-year headers qualify.
            match=re.fullmatch(r'(?:[A-Za-z]+ [0-9]{1,2},? )?(20[0-9]{2})',cell.text.strip())
            if match:period_rows.setdefault(row,[]).append((cell,int(match.group(1))))
    if not period_rows:raise ValueError('quarter_year_header_missing')
    headers=period_rows[min(period_rows)]
    headers.sort(key=lambda pair:positions[pair[0].cell_id][0])
    if len(headers)!=2 or headers[0][1]!=headers[1][1]+1:
        raise ValueError('current_comparative_column_order_not_qualified')
    current,year=headers[0];prior,_=headers[1]
    qtext=heading.text+' '+current.text
    quarter=None
    for word,value in _QUARTERS.items():
        if re.search(r'\b'+word+r' quarter\b',qtext,re.I):quarter=value;break
    if quarter is None:
        month=re.search(r'\b(March|June|September|December)\b',qtext,re.I)
        if month:quarter=_MONTHS[month.group(1).lower()]
    if quarter is None:raise ValueError('quarter_period_not_qualified')
    bounds=positions[current.cell_id][:2]
    if ticker=='RTX':
        basis_headers=[c for c in cells if positions[c.cell_id][2]==positions[current.cell_id][2]+1 and inside(c,bounds) and c.text.strip()]
        basis_headers.sort(key=lambda cell:positions[cell.cell_id][0])
        # Narrow supported source schema: current-quarter Reported precedes
        # Adjusted. Changed/ambiguous layouts are typed absence, not guessed.
        if [c.text.strip() for c in basis_headers]!=['Reported','Adjusted']:
            raise ValueError('reported_adjusted_column_order_not_qualified')
        bounds=positions[basis_headers[0].cell_id][:2]
    return FiscalPeriod(year=year,quarter=quarter),bounds,positions


def source_fiscal_period(bound,ticker):
    return _current_column(_segment_table(bound,ticker),ticker)[0]


def _row_for(table,ticker,label):
    rows=table.table.rows
    if ticker!='RTX':
        found=[row for row in rows if _cells(row) and _cells(row)[0].text.strip()==label]
    else:
        starts=[i for i,row in enumerate(rows) if _cells(row) and _cells(row)[0].text.strip()==label]
        found=[]
        if len(starts)==1:
            for row in rows[starts[0]+1:]:
                cells=_cells(row)
                if cells and cells[0].text.strip() in LABELS['RTX']:break
                if cells and cells[0].text.strip()=='Raytheon':found.append(row);break
    return found[0] if len(found)==1 else None


def _selected_number(row,bounds,positions):
    selected=[cell for cell in row if bounds[0]<=positions[cell.cell_id][0]<positions[cell.cell_id][1]<=bounds[1]]
    values=[]
    for cell in selected:
        parsed=parse_numeric(cell.text)
        if parsed is not None:values.append((cell,parsed[0]))
        elif cell.text.strip() not in ('','$','%'):
            # Separate minus/parenthesis cells cannot silently lose the sign.
            raise ValueError('unqualified_sign_or_numeric_column')
    if len(values)!=1:raise ValueError('numeric_column_missing_or_ambiguous')
    return values[0]


def _lhx_reported_operating_income(bound,fiscal_period):
    # The standalone Missile Solutions table omits operating income; the
    # consolidated Segment Results table reports it. Qualify that table's
    # own current quarter/year/units, never derive income from margin.
    tables=[b for b in bound.document.blocks if b.table and all(t in b.text for t in
        ('Missile Solutions','Segment operating income','Operating income'))]
    if len(tables)!=1:raise ValueError('LHX_reported_income_table_missing_or_ambiguous')
    table=tables[0];period,bounds,positions=_current_column(table,'LHX')
    if period!=fiscal_period:raise ValueError('LHX_reported_income_period_mismatch')
    header=' '.join(c.text for row in table.table.rows[:5] for c in row).lower()
    if 'million' not in header or not any('$' in c.text for row in table.table.rows for c in row):
        raise ValueError('LHX_reported_income_units_unqualified')
    starts=[i for i,row in enumerate(table.table.rows) if len(_cells(row))==1 and _cells(row)[0].text=='Operating income']
    if len(starts)!=1:raise ValueError('LHX_income_section_missing_or_ambiguous')
    selected=[]
    for row in table.table.rows[starts[0]+1:]:
        cells=_cells(row)
        if cells and cells[0].text.startswith('Segment operating income'):break
        if cells and cells[0].text=='Missile Solutions':selected.append(row)
    if len(selected)!=1:raise ValueError('LHX_income_segment_row_missing_or_ambiguous')
    return _selected_number(selected[0],bounds,positions)


def extract_segment_facts(*, ticker, bound, document_id, event_id, fiscal_period):
    table=_segment_table(bound,ticker)
    output=[]
    def absent(metric,reason):
        return _fact_absent(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,
                            detail=reason,document_id=document_id)
    try:
        source_period,bounds,positions=_current_column(table,ticker)
        if source_period!=fiscal_period:raise ValueError('fiscal_period_mismatch')
        header=' '.join(c.text for row in table.table.rows[:5] for c in _cells(row)).lower()
        if 'million' not in header:raise ValueError('units_not_declared_as_millions')
        if not any('$' in c.text for row in table.table.rows for c in row):raise ValueError('dollar_currency_not_declared')
    except ValueError as exc:return [absent(v,str(exc)) for v in METRICS]
    for metric,label in zip(METRICS,LABELS[ticker]):
        row=_row_for(table,ticker,label)
        if row is None and not (ticker=='LHX' and metric=='defense_segment_operating_profit'):
            output.append(absent(metric,'reported_row_missing_or_ambiguous'));continue
        try:
            cell,value=_lhx_reported_operating_income(bound,fiscal_period) if row is None else _selected_number(row,bounds,positions)
            receipt=receipt_for_literal(source=bound.source,source_sha256=bound.revision.source_sha256,
                search_start=cell.source_span.char_start,search_end=cell.source_span.char_end,
                literal=cell.text.strip())
            replay_receipt(receipt,source=bound.source)
            output.append(_fact_present(fact_id=event_id+':'+metric,event_id=event_id,metric=metric,
                value=value,unit='percent' if metric.endswith('margin') else 'USD_million',
                period=f'{fiscal_period.year}Q{fiscal_period.quarter}',
                basis='issuer_reported_segment:'+SEGMENTS[ticker]+':reported',
                document_id=document_id,bound=bound,receipt=receipt))
        except (ValueError,ReceiptError) as exc:output.append(absent(metric,type(exc).__name__))
    return output


def _extract_defense_facts(*, ticker, **kwargs):
    from engine.company_intelligence.defense_cash_profiles import extract_financial_facts
    return extract_segment_facts(ticker=ticker, **kwargs)+extract_financial_facts(ticker=ticker, **kwargs)


def defense_profile(ticker):
    if ticker not in SEGMENTS:raise ValueError('issuer_not_in_defense_cohort')
    return IssuerProfile(ticker=ticker,
        extract_release_facts=lambda **kwargs:_extract_defense_facts(ticker=ticker,**kwargs),
        extract_transcript_claims=lambda **kwargs:[],extract_guidance=lambda **kwargs:[])

# Frozen identity facts verified against each issuer's SEC submissions JSON
# on 2026-10-13. LHX reports fiscalYearEnd=0102; source_fiscal_period reads
# its release's own quarter label, never infers a calendar quarter from it.
_CIKS={'LMT':'0000936468','RTX':'0000101829','NOC':'0001133421','LHX':'0000202058'}
_NAMES={'LMT':'Lockheed Martin','RTX':'RTX','NOC':'Northrop Grumman','LHX':'L3Harris Technologies'}
DEFENSE_TICKERS=tuple(SEGMENTS)

def defense_issuer(ticker):
    from engine.company_intelligence.identity import IssuerIdentity, ListingAlias, company_id_for_cik
    if ticker not in _CIKS:return None
    return IssuerIdentity(company_id=company_id_for_cik(_CIKS[ticker]),display_name=_NAMES[ticker],
        fiscal_year_end_month=1 if ticker=='LHX' else 12,reporting_currency='USD',
        listings=(ListingAlias(ticker=ticker,mic='XNYS',share_class='common',trading_currency='USD',is_primary=True),),
        external_ids={'cik':_CIKS[ticker]})
