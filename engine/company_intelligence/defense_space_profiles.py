"""Reported NOC Space Systems quarters through the existing fact owner.

Comparisons are disclosed in the current release, not historical house knowledge.
These segment figures establish no program allocation, cash flow or capacity.
"""
from __future__ import annotations

import re
import math

from engine.company_intelligence.issuer_profiles import _fact_present, _fact_absent
from engine.earnings_release.receipts import receipt_for_literal, replay_receipt, ReceiptError

_ROWS = (
    ('sales', 'Sales', 'reported_segment_sales', 'USD_million'),
    ('operating_profit', 'Operating income', 'reported_segment_operating_profit', 'USD_million'),
    ('margin', 'Operating margin rate', 'reported_segment_margin', 'percent'),
)
_BASIS = 'issuer_reported_segment:Space Systems:reported'
_NUMBER = r'(?:-?\d+(?:,\d{3})*(?:\.\d+)?|\(\d+(?:,\d{3})*(?:\.\d+)?\))'


def space_fact_rules(ticker, year, quarter):
    if ticker != 'NOC' or quarter != 2:
        return {}
    return {
        'issuer_space_segment_' + metric + ('_prior' if prior else ''):
        (fact_class, unit, _BASIS, f'{year - int(prior)}Q2')
        for metric, _, fact_class, unit in _ROWS for prior in (False, True)
    }


def extract_space_facts(*, ticker, bound, document_id, event_id, fiscal_period):
    """Require one qualified table; an invalid cell refuses its whole six-fact set."""
    from engine.company_intelligence.defense_profiles import (
        _cells, _current_column, _row_for, _selected_number,
    )
    from engine.company_intelligence.defense_cash_profiles import _columns

    rules = space_fact_rules(ticker, fiscal_period.year, fiscal_period.quarter)
    if not rules:
        return []
    try:
        tables = [
            block for block in bound.document.blocks if block.table and any(
                _cells(row) and _cells(row)[0].text.strip().lower() == 'space systems'
                and any(c.text.strip().startswith('Three Months Ended') for c in row)
                for row in block.table.rows
            )
        ]
        if len(tables) != 1:
            raise ValueError('space_segment_table_missing_or_ambiguous')
        table = tables[0]
        period, current_bounds, _ = _current_column(table, 'NOC')
        if period != fiscal_period:
            raise ValueError('space_segment_fiscal_period_mismatch')
        header = ' '.join(c.text for row in table.table.rows[:5] for c in row).lower()
        if 'million' not in header or '$' not in header:
            raise ValueError('space_segment_USD_million_header_unqualified')
        headings = [c.text.strip() for row in table.table.rows for c in row
                    if c.text.strip().startswith('Three Months Ended')]
        if len(headings) != 1:
            raise ValueError('space_quarter_heading_ambiguous')
        columns, positions = _columns(table, headings[0], fiscal_period.year)
        if columns[0] != current_bounds:
            raise ValueError('space_current_column_disagrees')
        result = []
        for name, label, _, unit in _ROWS:
            row = _row_for(table, 'NOC', label)
            if row is None:
                raise ValueError('space_reported_row_missing_or_ambiguous')
            for prior, column in zip((False, True), columns):
                cell, value = _selected_number(row, column, positions)
                literal = cell.text.strip()
                if not re.fullmatch(_NUMBER + ('%?' if unit == 'percent' else ''), literal):
                    raise ValueError('space_numeric_literal_unqualified')
                receipt = receipt_for_literal(
                    source=bound.source, source_sha256=bound.revision.source_sha256,
                    search_start=cell.source_span.char_start,
                    search_end=cell.source_span.char_end, literal=literal,
                )
                replay_receipt(receipt, source=bound.source)
                metric = 'issuer_space_segment_' + name + ('_prior' if prior else '')
                _, expected_unit, basis, period_label = rules[metric]
                result.append(_fact_present(
                    fact_id=event_id + ':' + metric, event_id=event_id, metric=metric,
                    value=value, unit=expected_unit, period=period_label, basis=basis,
                    document_id=document_id, bound=bound, receipt=receipt,
                ))
        return result
    except (ValueError, ReceiptError) as exc:
        return [_fact_absent(fact_id=event_id + ':' + metric, event_id=event_id,
                             metric=metric, detail=str(exc), document_id=document_id)
                for metric in rules]


def space_adverse_fact_rules(ticker, year, quarter):
    """One qualified issuer/period prose profile; no extrapolation to other releases."""
    if (ticker, year, quarter) != ('NOC', 2026, 2):
        return {}
    return {'issuer_space_gem63xl_unfavorable_eac': (
        'reported_eac', 'USD_million',
        'issuer_reported_program_cost_estimate:GEM63XL:unfavorable_EAC', '2026Q2')}


def extract_space_adverse_facts(*, ticker, bound, document_id, event_id, fiscal_period):
    """Replay the adverse estimate's magnitude, never treat it as cash or loss.

    The known release's complete operating-income sentence structure is required.
    A changed/ambiguous narrative yields absence independently of the six cells.
    """
    from engine.company_intelligence.defense_profiles import _cells

    rules = space_adverse_fact_rules(ticker, fiscal_period.year, fiscal_period.quarter)
    if not rules:
        return []
    metric, (fact_class, unit, basis, period) = next(iter(rules.items()))
    try:
        cells = extract_space_facts(ticker=ticker, bound=bound, document_id=document_id,
                                    event_id=event_id, fiscal_period=fiscal_period)
        if len(cells) != 6 or any(f.get('typed_absence') for f in cells):
            raise ValueError('space_adverse_quarter_context_unqualified')
        blocks = bound.document.blocks
        index = next(i for i, block in enumerate(blocks) if block.table and any(
            _cells(row) and _cells(row)[0].text.strip().lower() == 'space systems'
            and any(c.text.strip().startswith('Three Months Ended') for c in row)
            for row in block.table.rows))
        end = next((i for i in range(index + 1, len(blocks)) if blocks[i].table), len(blocks))
        number = r'(?:0|[1-9]\d*)(?:,\d{3})*(?:\.\d+)?'
        pattern = (
            r'Second quarter 2026 operating income decreased \$' + number
            + r' million, or ' + number + r' percent, primarily due to a lower operating margin rate, '
            r'partially offset by higher sales\. Operating margin rate decreased to ' + number
            + r' percent from ' + number + r' percent, primarily due to lower net EAC adjustments, '
            r'including a \$(' + number + r') million unfavorable adjustment on GEM 63XL '
            r'largely related to increases in the projected cost to complete the program, '
            r'partially offset by favorable changes in contract mix\.'
        )
        matches = [(block, re.fullmatch(pattern, block.text)) for block in blocks[index + 1:end] if not block.table]
        matches = [(block, match) for block, match in matches if match is not None]
        if len(matches) != 1:
            raise ValueError('space_adverse_narrative_missing_or_ambiguous')
        block, match = matches[0]
        literal = match.group(1)
        value = float(literal.replace(',', ''))
        if not math.isfinite(value) or value <= 0:
            raise ValueError('space_adverse_magnitude_unqualified')
        receipt = receipt_for_literal(source=bound.source, source_sha256=bound.revision.source_sha256,
                                      search_start=block.source_span.char_start,
                                      search_end=block.source_span.char_end, literal=literal)
        replay_receipt(receipt, source=bound.source)
        return [_fact_present(fact_id=event_id + ':' + metric, event_id=event_id,
                              metric=metric, value=value, unit=unit, period=period,
                              basis=basis, document_id=document_id, bound=bound, receipt=receipt)]
    except (ValueError, ReceiptError, StopIteration) as exc:
        return [_fact_absent(fact_id=event_id + ':' + metric, event_id=event_id,
                             metric=metric, detail=str(exc), document_id=document_id)]
