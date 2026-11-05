"""The unified day dossier is a view, not a new archive or signal authority."""
import importlib
import importlib.util
import json
from pathlib import Path
import pytest
from tests.test_market_memory_history_archive import make_archive
from tests.test_market_memory_history_macro import packet

NAME='engine.neuralweb.market_memory_history_dossier'

def module():
    assert importlib.util.find_spec(NAME) is not None,'daily dossier composition is not implemented'
    return importlib.import_module(NAME)

def macro(tmp_path):
    from engine.neuralweb.market_memory_history_macro import build_macro_chronology,write_macro_chronology
    path=tmp_path/'macro.json'
    result=write_macro_chronology(build_macro_chronology(packet(),start='2020-01-01',end='2020-03-31'),path)
    return path,result['sha256']

def test_daily_dossier_exists():
    assert callable(module().build_daily_dossier)

def test_default_dossier_uses_exact_market_day_and_does_not_reveal_outcomes(monkeypatch,tmp_path):
    _,root,r=make_archive(monkeypatch,tmp_path)
    result=module().build_daily_dossier(root,'2020-01-05',expected_manifest_sha256=r['manifest_sha256'])
    assert result['market_date']=='2020-01-05'
    assert len(result['market']['rows'])==1
    assert 'outcomes' not in result['market']
    assert result['macro']['status']=='SOURCE_NOT_SELECTED'
    assert result['retrospective_only'] is True
    assert result['summary']['positive_proxy_count']==1
    assert result['summary']['denominator']=='selected_proxy_observations_with_valid_1bar_return'
    assert result['coverage']['contemporary_consensus']=='NOT_INCLUDED'
    assert result['coverage']['full_macro_revision_history']=='NOT_INCLUDED'
    assert result['coverage']['strict_point_in_time_eligibility']=='NOT_PROVEN'

def test_macro_and_no_market_observation_can_coexist_without_interpolation(monkeypatch,tmp_path):
    _,root,r=make_archive(monkeypatch,tmp_path);mp,mh=macro(tmp_path)
    result=module().build_daily_dossier(root,'2020-02-13',expected_manifest_sha256=r['manifest_sha256'],macro_path=mp,expected_macro_sha256=mh)
    assert result['market']['status']=='NO_OBSERVATION'
    assert result['summary']['observed_proxy_count']==0
    assert result['macro']['total_events']==1
    assert result['macro']['events'][0]['value']==258.687
    assert result['coverage']['macro_first_prints']=='SELECTED_DATE_ONLY_SOURCE'

def test_mismatched_macro_reference_pair_refuses_before_market_read(monkeypatch,tmp_path):
    m=module()
    monkeypatch.setattr(m,'read_day',lambda *a,**k:pytest.fail('validate source pair before reads'))
    with pytest.raises(ValueError):m.build_daily_dossier(tmp_path,'2020-01-01',expected_manifest_sha256='a'*64,macro_path=tmp_path/'macro')

def test_reveal_is_explicit_and_not_reused_in_descriptive_summary(monkeypatch,tmp_path):
    _,root,r=make_archive(monkeypatch,tmp_path)
    m=module();a=m.build_daily_dossier(root,'2020-01-05',expected_manifest_sha256=r['manifest_sha256'])
    b=m.build_daily_dossier(root,'2020-01-05',expected_manifest_sha256=r['manifest_sha256'],reveal_outcomes=True)
    assert b['summary']==a['summary']
    assert b['market']['outcomes']
    assert b['outcomes_revealed'] is True

def test_missing_return_is_not_a_flat_or_negative_proxy(monkeypatch,tmp_path):
    _,root,r=make_archive(monkeypatch,tmp_path)
    result=module().build_daily_dossier(root,'2020-01-01',expected_manifest_sha256=r['manifest_sha256'])
    assert result['summary']['observed_proxy_count']==1
    assert result['summary']['valid_return_count']==0
    assert result['summary']['flat_proxy_count']==0
    assert result['summary']['missing_return_count']==1


@pytest.mark.parametrize('key', ['intraday_publication_time_known', 'full_revision_history', 'units_retained'])
def test_direct_composition_refuses_macro_qualification_upgrade(monkeypatch, tmp_path, key):
    from tests.test_market_memory_history_archive import make_archive
    from engine.neuralweb.market_memory_history_macro import build_macro_chronology, select_macro_date
    from tests.test_market_memory_history_macro import packet
    from engine.neuralweb.market_memory_history_dossier import compose_daily_dossier
    from engine.neuralweb.market_memory_history import HistoricalExperienceError
    ar, root, receipt = make_archive(monkeypatch, tmp_path)
    market = ar.read_day(root, '2020-02-13', expected_manifest_sha256=receipt['manifest_sha256'])
    macro = select_macro_date(build_macro_chronology(packet(), start='2020-01-01', end='2020-03-31'), '2020-02-13')
    macro[key] = True
    with pytest.raises(HistoricalExperienceError):
        compose_daily_dossier(market, macro)



def test_cli_dossier_composes_identical_filing_metadata(monkeypatch,tmp_path):
    import hashlib
    from tests.test_market_memory_history_archive import make_archive
    from tests.test_market_memory_history_filings import row, payload, read
    from engine.neuralweb.market_memory_history_dossier import build_daily_dossier
    ar, root, receipt = make_archive(monkeypatch,tmp_path)
    raw = payload([row(filing_date='2020-01-05',report_date='2020-01-03',acceptance_datetime='2020-01-05T12:00:00Z')])
    source = tmp_path/'earnings_8k_dates.parquet';source.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    actual = build_daily_dossier(root,'2020-01-05',expected_manifest_sha256=receipt['manifest_sha256'],
        filings_path=source,expected_filings_sha256=digest)
    assert actual['filings'] == read(raw,day='2020-01-05')
    assert actual['market']['rows'][0]['close_tradj']==52.0
    assert actual['coverage']['issuer_filings_and_earnings_context']=='SELECTED_ITEM_202_FILING_METADATA_ONLY'
    assert actual['outcomes_revealed'] is False


def test_dossier_refuses_wrong_filing_date_or_qualification(monkeypatch,tmp_path):
    from tests.test_market_memory_history_archive import make_archive
    from tests.test_market_memory_history_filings import read
    from engine.neuralweb.market_memory_history_dossier import compose_daily_dossier
    from engine.neuralweb.market_memory_history import HistoricalExperienceError
    ar,root,receipt=make_archive(monkeypatch,tmp_path)
    market=ar.read_day(root,'2020-03-16',expected_manifest_sha256=receipt['manifest_sha256'])
    for changes in ({'calendar_date':'2020-03-15'},{'point_in_time_eligible':True},
                    {'historical_ticker_identity_proven':True},{'intraday_publication_time_verified':True}):
        with pytest.raises(HistoricalExperienceError):
            compose_daily_dossier(market,filings={**read(),**changes})



def test_shared_dossier_rejects_wrong_transcript_date_or_authority(monkeypatch,tmp_path):
    from tests.test_market_memory_history_archive import make_archive
    from tests.test_market_memory_history_transcripts import day
    from engine.neuralweb.market_memory_history_dossier import compose_daily_dossier
    from engine.neuralweb.market_memory_history import HistoricalExperienceError
    ar,root,receipt=make_archive(monkeypatch,tmp_path)
    market=ar.read_day(root,'2020-03-16',expected_manifest_sha256=receipt['manifest_sha256'])
    calls=day()
    assert compose_daily_dossier(market,transcripts=calls)['transcripts']['total_events']==1
    for field,value in [('calendar_date','2020-03-17'),('point_in_time_eligible',True),
        ('publication_time_verified',True),('historical_security_identity_proven',True)]:
        with pytest.raises(HistoricalExperienceError):compose_daily_dossier(market,transcripts={**calls,field:value})
