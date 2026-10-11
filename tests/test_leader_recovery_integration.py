"""Recovery additions must preserve incumbent Leader Radar state and data ownership."""
from pathlib import Path
import json
import os
from unittest.mock import patch
import pytest
from test_build_leader_radar import _build_fixture_root
from scripts.build_leader_radar import build


def test_builder_emits_recovery_without_advancing_data_stores(tmp_path):
    root=_build_fixture_root(tmp_path,['AAPL','MSFT'])
    before={str(p.relative_to(root)):p.read_bytes() for p in (root/'data').rglob('*') if p.is_file()}
    with patch('lib.config.ROOT',root),patch('lib.config.data_dir',lambda:root/'data'),patch('lib.config.load',lambda:{'storage':{'data_dir':'data','site_dir':'site'},'leader_radar':{'enabled':True,'basket_keys':['mag7'],'dow30':[]}}),patch.dict(os.environ,{'COLLECT_LANE':'express'}):
        result=build(data_root=root/'data',site_root=root/'site')
    assert len(result['rows'])==2
    assert result['recovery_roster']['population_rows']==2
    assert sum(result['recovery_roster']['counts'].values())==2
    for row in result['rows']:
        r=row['display_chips']['leader_recovery']
        assert r['schema']=='leader_recovery.v1'
        assert r['as_of']==result['as_of']
        assert not any(r['authority'].values())
        assert r['fundamental_thesis']['state']=='UNKNOWN'
    assert json.loads((root/'site/leaderradar/radar.json').read_text())['recovery_roster']==result['recovery_roster']
    after={str(p.relative_to(root)):p.read_bytes() for p in (root/'data').rglob('*') if p.is_file()}
    assert before==after


def test_optional_recovery_failure_cannot_remove_incumbent_rows(tmp_path):
    root=_build_fixture_root(tmp_path,['AAPL','MSFT'])
    with patch('lib.config.ROOT',root),patch('lib.config.data_dir',lambda:root/'data'),patch('lib.config.load',lambda:{'storage':{'data_dir':'data','site_dir':'site'},'leader_radar':{'enabled':True,'basket_keys':['mag7'],'dow30':[]}}),patch.dict(os.environ,{'COLLECT_LANE':'express'}),patch('engine.leader_recovery.describe_recovery',side_effect=ValueError('bad optional projection')):
        result=build(data_root=root/'data',site_root=root/'site')
    assert len(result['rows'])==2
    assert result['recovery_roster']['counts']['UNAVAILABLE']==2
    assert all(r['display_chips']['leader_recovery']['reason']=='projection_error' for r in result['rows'])
