import json
from datetime import datetime, timezone

import pytest

from engine.exposure_outlook_data import audit_surface_session

ASOF = '2026-09-18T16:00:00Z'


def store(tmp_path, stamps=('1000', '1002'), publish=True):
    folder = tmp_path / 'SPY' / '2026-09-18'
    folder.mkdir(parents=True)
    index = dict(root='SPY', date='2026-09-18', stamps=list(stamps), latest=stamps[-1],
                 asof=ASOF, cadenceSec=120)
    (folder / 'idx.json').write_text(json.dumps(index))
    for stamp in stamps:
        hour, minute = int(stamp[:2]), int(stamp[2:])
        frame = dict(root='SPY', session_date='2026-09-18', spot=762.,
                     asof=f'2026-09-18T{hour + 4:02}:{minute:02}:00Z',
                     time_steps=[f'{hour:02}:{minute:02}'], price_levels=[761., 762.],
                     metrics=['gex'], grids={'gex': [[1.], [2.]]}, coverage={'greeks':1.0})
        if publish:
            frame['published_at'] = frame['asof']
        (folder / f'{stamp}.json').write_text(json.dumps(frame))
    return folder


def audit(tmp_path, **kwargs):
    return audit_surface_session(tmp_path, 'SPY', '2026-09-18', as_of=ASOF, **kwargs)


def change(path, **kwargs):
    x = json.loads(path.read_text()); x.update(kwargs); path.write_text(json.dumps(x))


def test_reads_only_index_not_orphan(tmp_path):
    f = store(tmp_path)
    (f / '2359.json').write_text('old malformed orphan')
    out = audit(tmp_path)
    assert out['indexed_frames'] == 2
    assert out['readable_frames'] == 2
    assert not any('2359' in e['path'] for e in out['evidence'])
    assert all(len(e['sha256']) == 64 for e in out['evidence'])
    assert out['observed_cadence_seconds']['median'] == 120


def test_publication_time_missing_is_not_pit(tmp_path):
    store(tmp_path, publish=False)
    out = audit(tmp_path)
    assert not out['forecast_eligible']
    assert 'PUBLICATION_TIME_MISSING' in out['reason_codes']
    assert out['nominal_cadence_seconds'] == 120


def test_measures_gaps_not_floor(tmp_path):
    store(tmp_path, ('1000', '1030', '1100'))
    out = audit(tmp_path)
    assert out['observed_cadence_seconds']['max'] == 1800
    assert 'SPARSE_OBSERVATIONS' in out['reason_codes']
    assert not out['forecast_eligible']


@pytest.mark.parametrize('root,day', [('SPY/../../x','2026-09-18'), ('SPY','../x'),
                                      ('SPY','2026-02-30')])
def test_rejects_path_or_calendar_input(tmp_path, root, day):
    with pytest.raises(ValueError):
        audit_surface_session(tmp_path, root, day, as_of=ASOF)


@pytest.mark.parametrize('stamps', [['1002','1000'], ['1000','1000'], ['2460'], ['../x']])
def test_refuses_bad_stamp_index(tmp_path, stamps):
    f = store(tmp_path)
    change(f/'idx.json', stamps=stamps, latest=stamps[-1])
    assert 'INVALID_INDEX' in audit(tmp_path)['reason_codes']


def test_future_grid_column_cannot_be_historical_input(tmp_path):
    f = store(tmp_path)
    change(f/'1000.json', time_steps=['13:30'])
    assert 'FRAME_TIME_AFTER_ASOF' in audit(tmp_path)['reason_codes']


def test_missing_frame_and_foreign_root(tmp_path):
    f = store(tmp_path)
    (f/'1000.json').unlink()
    change(f/'1002.json', root='QQQ')
    codes = audit(tmp_path)['reason_codes']
    assert 'MISSING_FRAME' in codes
    assert 'IDENTITY_MISMATCH' in codes


def test_index_latest_mismatch(tmp_path):
    f = store(tmp_path); change(f/'idx.json', latest='1230')
    assert 'INVALID_INDEX' in audit(tmp_path)['reason_codes']


@pytest.mark.parametrize('grids', [{'gex': [[1., 2.], [2.]]}, {'gex': [[float('nan')], [2.]]},
                                   {'gex': [[True], [2.]]}])
def test_invalid_grid_is_not_usable_exposure(tmp_path, grids):
    f = store(tmp_path); change(f/'1000.json', grids=grids)
    assert 'INVALID_FRAME' in audit(tmp_path)['reason_codes']


def test_non_gex_surface_is_not_exposure(tmp_path):
    f = store(tmp_path)
    for stamp in ('1000','1002'):
        change(f/f'{stamp}.json', metrics=['netprem'], grids={'netprem': [[1.],[2.]]})
    assert 'GEX_UNAVAILABLE' in audit(tmp_path)['reason_codes']


def test_missing_source_returns_machine_reason(tmp_path):
    out = audit(tmp_path)
    assert out['readable_frames'] == 0
    assert 'MISSING_INDEX' in out['reason_codes']


def test_source_future_to_requested_cutoff(tmp_path):
    store(tmp_path)
    out = audit_surface_session(tmp_path,'SPY','2026-09-18',as_of='2026-09-18T14:01:00Z')
    assert 'INDEX_AFTER_CUTOFF' in out['reason_codes']
    assert 'FRAME_AFTER_CUTOFF' in out['reason_codes']


def test_publication_before_source_is_impossible(tmp_path):
    f = store(tmp_path); change(f/'1000.json', published_at='2026-09-18T13:00:00Z')
    assert 'PUBLICATION_BEFORE_SOURCE' in audit(tmp_path)['reason_codes']


def test_naive_cutoff_refused(tmp_path):
    with pytest.raises(ValueError):
        audit_surface_session(tmp_path,'SPY','2026-09-18',as_of='2026-09-18T16:00:00')


def test_declared_receipts_do_not_earn_model_qualification(tmp_path):
    store(tmp_path)
    out = audit(tmp_path)
    assert out['authority_tier'] == 'research'
    assert out['forecast_eligible'] is False
    assert 'INTRADAY_TRAINING_CORPUS_NOT_QUALIFIED' in out['reason_codes']


def test_symlink_escape_is_refused(tmp_path):
    f = store(tmp_path)
    other = tmp_path / 'outside.json'
    other.write_text((f/'1000.json').read_text())
    (f/'1000.json').unlink()
    (f/'1000.json').symlink_to(other)
    assert 'UNSAFE_SOURCE_PATH' in audit(tmp_path)['reason_codes']


def test_read_budget_is_enforced(tmp_path):
    store(tmp_path)
    assert 'SOURCE_SIZE_LIMIT' in audit(tmp_path, max_file_bytes=10)['reason_codes']


def test_source_clock_non_advancement_is_reported(tmp_path):
    f = store(tmp_path)
    change(f/'1002.json', asof='2026-09-18T14:00:00Z')
    assert 'NON_ADVANCING_SOURCE_CLOCK' in audit(tmp_path)['reason_codes']


def test_separates_source_integrity_from_unearned_qualification(tmp_path):
    store(tmp_path)
    out = audit(tmp_path)
    assert out['source_integrity'] == 'consistent'
    assert not out['forecast_eligible']


@pytest.mark.parametrize('value', [None, 0, -1, True, float('inf')])
def test_invalid_spot_is_never_a_zero_price(tmp_path, value):
    f = store(tmp_path); change(f/'1000.json', spot=value)
    assert 'INVALID_FRAME' in audit(tmp_path)['reason_codes']


def test_legacy_current_layout_is_explicit_and_session_checked(tmp_path):
    f = store(tmp_path)
    for p in f.iterdir():
        p.rename(f.parent/p.name)
    out = audit(tmp_path, layout='current')
    assert out['readable_frames'] == 2
    assert out['layout'] == 'current'
    assert audit(tmp_path)['reason_codes'] == ['INTRADAY_TRAINING_CORPUS_NOT_QUALIFIED','MISSING_INDEX']
    change(f.parent/'idx.json', date='2026-09-17')
    assert 'INVALID_INDEX' in audit(tmp_path,layout='current')['reason_codes']


def test_unknown_layout_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        audit(tmp_path,layout='auto')


def test_invalid_frame_identifies_unusable_fields(tmp_path):
    f=store(tmp_path); change(f/'1000.json', grids={'gex': [[None], [2.]]})
    out=audit(tmp_path)
    detail=next(row for row in out['frame_findings'] if row['stamp']=='1000')
    assert detail['invalid_fields']==['gex_grid']
    assert 'INVALID_FRAME' in detail['reason_codes']


def test_optional_metric_nulls_do_not_invalidate_valid_gex(tmp_path):
    f=store(tmp_path)
    for stamp in ('1000','1002'):
        change(f/f'{stamp}.json', grids={'gex': [[1.],[2.]], 'charm': [[None],[None]]})
    assert audit(tmp_path)['source_integrity']=='consistent'


def test_total_session_budget_stops_before_extra_frame_reads(tmp_path):
    f=store(tmp_path)
    first=(f/'idx.json').stat().st_size
    out=audit(tmp_path,max_session_bytes=first+10)
    assert out['readable_frames']==0
    assert 'SESSION_SIZE_LIMIT' in out['reason_codes']


def test_zero_greek_coverage_is_absence_not_a_measured_zero_gamma(tmp_path):
    f=store(tmp_path)
    change(f/'1000.json', coverage={'greeks':0.0}, grids={'gex':[[0.],[0.]]})
    out=audit(tmp_path)
    detail=next(x for x in out['frame_findings'] if x['stamp']=='1000')
    assert detail['reported_greek_coverage']==0
    assert 'GEX_NO_CONTRIBUTING_STRIKES' in detail['reason_codes']


@pytest.mark.parametrize('value',[None,True,-0.1,1.1,float('nan')])
def test_invalid_greek_coverage_does_not_imply_observation(tmp_path,value):
    f=store(tmp_path);change(f/'1000.json',coverage={'greeks':value})
    out=audit(tmp_path)
    assert 'GEX_COVERAGE_NOT_VALID' in out['reason_codes']


def test_missing_greek_coverage_is_not_invented_from_grid(tmp_path):
    f=store(tmp_path);change(f/'1000.json',coverage={})
    assert 'GEX_COVERAGE_NOT_VALID' in audit(tmp_path)['reason_codes']


def test_positive_greek_coverage_keeps_its_limited_denominator(tmp_path):
    f=store(tmp_path);change(f/'1000.json',coverage={'greeks':0.5})
    out=audit(tmp_path)
    detail=next(x for x in out['frame_findings'] if x['stamp']=='1000')
    assert detail['reported_greek_coverage']==0.5
    assert detail['coverage_scope']=='quoted_strike_union_not_full_chain'
    assert out['forecast_eligible'] is False
