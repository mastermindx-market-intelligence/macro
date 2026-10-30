"""Source correlation availability must survive the template boundary."""
from copy import deepcopy

import pandas as pd
from bs4 import BeautifulSoup

from engine.intl_performance import correlation_matrix
from tests.test_intl_workspace_integration import render_fixture


def correlation_fixture(flat=False):
    index=pd.bdate_range('2024-01-02', periods=260)
    constant=pd.Series(100.,index=index)
    prices={'JP':pd.Series([100+i*.1+(i%7)*.2 for i in range(260)],index=index),
            'KR':pd.Series([200+i*.2+(i%7)*.4 for i in range(260)],index=index),
            'TW':pd.Series([200-i*.1-(i%7)*.2 for i in range(260)],index=index)}
    return correlation_matrix(closes=pd.DataFrame(index=index),bench=constant,
                              usd_map={k:constant for k in prices} if flat else prices)


def panel(cr):
    s=BeautifulSoup(render_fixture(perf={'correlation':cr}),'html.parser')
    return s.select_one('#intl-cross-market-correlation').find_parent('div',class_='panel')


def test_constant_owner_series_never_become_perfect_diagonal():
    cr=correlation_fixture(flat=True)
    assert all(v is None for row in cr['cells'] for v in row)
    el=panel(cr)
    assert not el.select('td.diag')
    assert len(el.select('td[data-correlation-unavailable]'))==16
    assert '0 / 6' in el.get_text()
    assert 'No available pairwise correlations.' in el.get_text()
    assert '暂无可用的成对相关性。' in el.get_text()


def test_partial_owner_pairs_preserve_values_and_actual_coverage():
    cr=correlation_fixture();before=deepcopy(cr);el=panel(cr)
    assert len(el.select('td.diag'))==3
    assert len(el.select('td[data-correlation-unavailable]'))==7
    assert '3 / 6' in el.get_text()
    cells=el.select('tbody tr')[0].select('td')
    assert cells[1].get_text()==f"{cr['cells'][0][1]:.2f}"
    assert cells[2].get_text()==f"{cr['cells'][0][2]:.2f}"
    assert cr==before
    text=el.get_text()
    assert 'weekly USD returns' in text and '美元周收益' in text
    assert 'Configured window' in text and '配置窗口' in text
    assert el.select_one('#intl-cross-market-correlation')['tabindex']=='-1'
    assert el.select_one('[data-correlation-scroll]')['role']=='region'
    assert el.select_one('[data-correlation-scroll]')['tabindex']=='0'


def test_real_zero_correlation_remains_a_number():
    cr=correlation_fixture();cr['cells'][0][1]=cr['cells'][1][0]=0.
    el=panel(cr);cell=el.select('tbody tr')[0].select('td')[1]
    assert cell.get_text()=='0.00' and not cell.has_attr('data-correlation-unavailable')
    assert '3 / 6' in el.get_text()


def test_correlation_summary_does_not_promise_safety():
    html=render_fixture(perf={'correlation':correlation_fixture()})
    assert 'lower = safer' not in html
    assert 'weekly USD returns' in html and '美元周收益' in html


def test_strong_mixed_pairs_do_not_inherit_diversification_promise():
    cr=correlation_fixture();before=deepcopy(cr)
    assert cr['avg_offdiag'] < 0
    assert cr['cells'][0][1] == 1.0 and cr['cells'][0][2] <= -0.99
    assert 'meaningful diversification' in cr['read_en']
    text=panel(cr).get_text()
    assert 'meaningful diversification' not in text and '分散价值显著' not in text
    assert 'opposing pairwise relationships' in text and '相反的成对关系' in text
    assert cr==before
