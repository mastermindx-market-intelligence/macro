"""Absent Growth/Inflation coordinates are not zero-valued observations."""
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from engine.intl_compare import regime_heatmap
from tests.test_intl_workspace_integration import render_fixture


def project_pairs(pairs):
    return regime_heatmap([{'cc': cc, 'name': cc, 'flag': '', 'growth_score': g,
                            'inflation_score': i, 'data_limited': g is None or i is None}
                           for cc, g, i in pairs])


def map_fixture():
    return project_pairs([('JP', 0., 0.), ('CA', -1., 1.), ('AU', 1., -1.),
                          ('GB', None, .3), ('KR', -.2, None), ('TW', None, None),
                          ('IN', None, -.5)])


def panel(rows):
    soup = BeautifulSoup(render_fixture(heatmap=rows), 'html.parser')
    return soup.select_one('#intl-growth-inflation').find_parent('div', class_='panel')


@pytest.mark.parametrize('growth,inflation', [(None, .3), (-.2, None), (None, None), (float('nan'), 0.), (True, 0.)])
def test_unavailable_axes_never_become_chart_coordinates(growth, inflation):
    rows = project_pairs([('JP', growth, inflation)])
    el = panel(rows)
    assert not el.select('.scatter .pt')
    assert el.select_one('[data-regime-unplotted="JP"]') is not None
    assert 'Unavailable' in el.get_text() and '不可用' in el.get_text()
    assert '0 / 1' in el.get_text()


@pytest.mark.parametrize('growth,inflation,position', [(0., 0., 'left:50.0%;top:50.0%'),(-1., 1., 'left:13.0%;top:13.0%'),(1., -1., 'left:87.0%;top:87.0%')])
def test_real_zero_and_boundaries_keep_supplied_coordinates(growth, inflation, position):
    el=panel(project_pairs([('JP', growth, inflation)]))
    points=el.select('.scatter .pt');assert len(points)==1
    assert points[0]['style']==position
    assert not el.select('[data-regime-unplotted]')
    assert '1 / 1' in el.get_text()


def test_partial_pairs_keep_present_axis_and_country_without_zero_substitution():
    rows=map_fixture();before=deepcopy(rows);el=panel(rows)
    assert len(el.select('.scatter .pt'))==3
    assert '3 / 7' in el.get_text()
    assert [n['data-regime-unplotted'] for n in el.select('[data-regime-unplotted]')]==['GB','KR','TW','IN']
    assert '0.3' in el.select_one('[data-regime-unplotted="GB"]').get_text()
    assert '-0.2' in el.select_one('[data-regime-unplotted="KR"]').get_text()
    assert '-0.5' in el.select_one('[data-regime-unplotted="IN"]').get_text()
    assert 'Missing coordinates are not zero.' in el.get_text()
    assert '缺失坐标不等于零。' in el.get_text()
    assert rows==before


def test_empty_map_explains_absence_and_keeps_destination():
    el=panel([])
    assert not el.select('.pt')
    assert 'No supplied growth/inflation pairs.' in el.get_text()
    assert '暂无所供增长与通胀坐标对。' in el.get_text()
    assert el.select_one('#intl-growth-inflation').get('tabindex')=='-1'


def test_unplotted_owner_text_is_escaped():
    rows=project_pairs([('JP', None, .3)])
    rows[0]['name']='<img src=x onerror=alert(1)>'
    rows[0]['flag']='<script>alert(1)</script>'
    rows[0]['cc']='JP" data-untrusted="1'
    el=panel(rows)
    row=el.select_one('[data-regime-unplotted]')
    assert row['data-regime-unplotted']==rows[0]['cc']
    assert not row.select('script,img') and not row.has_attr('data-untrusted')
    assert rows[0]['name'] in row.get_text() and rows[0]['flag'] in row.get_text()
