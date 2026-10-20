"""The fourth supplied country must retain its actual owner's warning detail."""
from copy import deepcopy
from functools import lru_cache
from unittest.mock import patch

import pandas as pd
import pytest

from engine.intl_risk import vulnerability_table
from scripts.build_intl import _enrich_vulnerability
from tests.test_intl_fragility_scope_render import panel


@lru_cache(maxsize=3)
def disclosure_owner(count):
    # Synthetic observations, passed through the existing owner and enrichment.
    # Every country differs, so copying the first row's tags cannot pass.
    countries = ['AUS', 'BRA', 'CAN', 'CHL', 'CHN'][:count]

    def read(group, name):
        iso3 = name.rsplit('_', 1)[-1]
        if group != 'imf_weo' or iso3 not in countries:
            return None
        offset = countries.index(iso3)
        if name.startswith('GGXWDG'):
            return pd.DataFrame(
                {'gross_debt_pct_gdp': [80 + offset, 85 + offset, 90 + offset, 95 + offset]},
                index=pd.date_range('2021-01-01', periods=4, freq='YS'),
            )
        if name.startswith('GGXCNL'):
            return pd.DataFrame({'fiscal_balance_pct_gdp': [-6. - offset]},
                                index=pd.to_datetime(['2022-01-01']))
        if name.startswith('BCA'):
            return pd.DataFrame({'current_account_pct_gdp': [-4. - offset]},
                                index=pd.to_datetime(['2023-01-01']))
        return None

    with patch('engine.intl_risk.store.read', side_effect=read):
        return _enrich_vulnerability(vulnerability_table())


def disclosure_fixture(count=5):
    return {'vulnerability': deepcopy(disclosure_owner(count))}


@pytest.mark.parametrize('count', [3, 4, 5])
def test_disclosure_boundary_preserves_each_country_and_warning(count):
    payload = disclosure_fixture(count)
    before = deepcopy(payload)
    countries = payload['vulnerability']['countries']
    assert len(countries) == count
    assert all(c['fragile'] and len(c['tags']) == 3 for c in countries)
    rendered = panel(payload)
    rows = rendered.select('.ird-frag-row')
    assert len(rows) == count
    assert len(rendered.select('details')) == int(count > 3)
    disclosure = rendered.find('details')
    assert len(disclosure.select('.ird-frag-row') if disclosure else []) == max(count - 3, 0)
    for actual, country in zip(rows, countries):
        assert country['name_en'] in actual.get_text(' ', strip=True)
        assert country['name_zh'] in actual.get_text(' ', strip=True)
        tags = actual.select('.ird-frag-tags .chip')
        assert len(tags) == len(country['tags']), country['iso3']
        for tag, supplied in zip(tags, country['tags']):
            text = tag.get_text(' ', strip=True)
            assert supplied['en'] in text and supplied['zh'] in text
    assert payload == before


def test_chinese_year_note_has_no_duplicated_character():
    text = panel(disclosure_fixture()).get_text(' ', strip=True)
    assert '这不是发布日期。' in text
    assert '发布日期期' not in text
