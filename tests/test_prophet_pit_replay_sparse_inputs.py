"""Missing sparse-worktree inputs must come from the declared vintage, never today."""
from pathlib import Path
import subprocess
import pandas as pd
import pytest
from scripts import prophet_pit_replay as ppr


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def archive(tmp_path):
    repo = tmp_path / 'source'
    repo.mkdir()
    git(repo, 'init', '-b', 'main')
    git(repo, 'config', 'user.name', 'Synthetic Test')
    git(repo, 'config', 'user.email', 'synthetic@example.invalid')
    path = repo / 'data/yahoo/SPY.parquet'
    path.parent.mkdir(parents=True)
    old = pd.DataFrame({'close': [100., 101.]}, index=pd.to_datetime(['2026-07-14', '2026-07-15']))
    old.to_parquet(path)
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'historical source')
    sha = git(repo, 'rev-parse', 'HEAD')
    vintage = tmp_path / 'vintage'; vintage.mkdir()
    return repo, vintage, sha, old


@pytest.mark.parametrize('directory_exists', [False, True])
def test_missing_ticker_restores_historical_values_not_later_revision(archive, directory_exists):
    repo, vintage, sha, old = archive
    if directory_exists:
        (vintage / 'data/yahoo').mkdir(parents=True)
    later = pd.DataFrame({'close': [900., 901., 902.]},
                         index=pd.to_datetime(['2026-07-14', '2026-07-15', '2026-07-16']))
    later.to_parquet(repo / 'data/yahoo/SPY.parquet')
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'later restatement and future bar')
    manifest = ppr.prepare_reconstruction_tree(
        vintage, repo, through='2026-07-15', live_ref='main', vintage_commit=sha,
        surface=ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),)),
    )
    target = vintage / 'data/yahoo/SPY.parquet'
    assert target.exists(), 'tracked vintage SPY was silently omitted'
    pd.testing.assert_frame_equal(pd.read_parquet(target), old)
    assert manifest['restored_vintage_inputs']['data/yahoo/SPY.parquet']
    assert manifest['fence']['max_date_found'] == '2026-07-15'


def test_price_value_change_with_same_endpoint_changes_cache_identity(archive):
    _, vintage, _, old = archive
    target = vintage / 'data/yahoo/SPY.parquet'
    target.parent.mkdir(parents=True)
    old.to_parquet(target)
    surface = ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),))
    before = ppr.fence_no_bar_after(vintage, '2026-07-15', surface)
    changed = old * 2
    changed.to_parquet(target)
    after = ppr.fence_no_bar_after(vintage, '2026-07-15', surface)
    assert before['max_date_found'] == after['max_date_found']
    assert ppr.tree_fingerprint({'fence': before}) != ppr.tree_fingerprint({'fence': after})


def test_sparse_restore_does_not_add_later_only_ticker(archive):
    repo, vintage, sha, old = archive
    old.to_parquet(repo / 'data/yahoo/NEW.parquet')
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'later universe addition')
    ppr.prepare_reconstruction_tree(
        vintage, repo, through='2026-07-15', live_ref='main', vintage_commit=sha,
        surface=ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),)),
    )
    assert not (vintage / 'data/yahoo/NEW.parquet').exists()
    assert (vintage / 'data/yahoo/SPY.parquet').exists()


def test_restoration_is_idempotent_and_does_not_rewrite_present_bytes(archive):
    repo, vintage, sha, _ = archive
    surface = ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),))
    first = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
        live_ref='main', vintage_commit=sha, surface=surface)
    path = vintage / 'data/yahoo/SPY.parquet'
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    second = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
        live_ref='main', vintage_commit=sha, surface=surface)
    assert first['restored_vintage_inputs']
    assert second['restored_vintage_inputs'] == {}
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert ppr.tree_fingerprint(first) == ppr.tree_fingerprint(second)


def test_unavailable_historical_blob_refuses_without_later_substitution(archive, monkeypatch):
    repo, vintage, sha, _ = archive
    monkeypatch.setattr(ppr, 'batch_blobs', lambda *args: {})
    with pytest.raises(ppr.PitReplayRefused, match='missing historical price blobs'):
        ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
            live_ref='main', vintage_commit=sha,
            surface=ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),)))
    assert not (vintage / 'data/yahoo/SPY.parquet').exists()


def test_corrupt_historical_parquet_refuses_without_publication(archive):
    repo, vintage, _, _ = archive
    (repo / 'data/yahoo/SPY.parquet').write_bytes(b'not parquet')
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'unreadable historical input')
    sha = git(repo, 'rev-parse', 'HEAD')
    with pytest.raises(ppr.PitReplayRefused, match='cannot restore historical price input'):
        ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
            live_ref='main', vintage_commit=sha,
            surface=ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),)))
    assert not (vintage / 'data/yahoo/SPY.parquet').exists()


def test_restore_appends_only_missing_tail_and_keeps_historical_rows(archive):
    repo, vintage, sha, old = archive
    later = pd.DataFrame({'close': [900., 901., 102., 999.]},
        index=pd.to_datetime(['2026-07-14', '2026-07-15', '2026-07-16', '2026-07-17']))
    later.to_parquet(repo / 'data/yahoo/SPY.parquet')
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'later revised history')
    manifest = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-16',
        live_ref='main', vintage_commit=sha,
        surface=ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),)))
    actual = pd.read_parquet(vintage / 'data/yahoo/SPY.parquet')
    pd.testing.assert_frame_equal(actual.loc[:'2026-07-15'], old)
    assert actual['close'].tolist() == [100., 101., 102.]
    assert manifest['files']['data/yahoo/SPY.parquet']['added'] == ['2026-07-16']


def test_restored_vintage_rows_are_truncated_at_pass_ceiling(archive):
    repo, vintage, sha, _ = archive
    manifest = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-14',
        live_ref='main', vintage_commit=sha,
        surface=ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),)))
    actual = pd.read_parquet(vintage / 'data/yahoo/SPY.parquet')
    assert actual['close'].tolist() == [100.]
    assert actual.index.max() == pd.Timestamp('2026-07-14')
    assert manifest['fence']['violations'] == 0


def test_later_deletion_does_not_erase_vintage_population(archive):
    repo, vintage, sha, old = archive
    git(repo, 'rm', 'data/yahoo/SPY.parquet')
    git(repo, 'commit', '-m', 'later delisting')
    ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
        live_ref='main', vintage_commit=sha,
        surface=ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),)))
    pd.testing.assert_frame_equal(pd.read_parquet(vintage / 'data/yahoo/SPY.parquet'), old)


def test_control_then_replay_restores_tail_even_when_git_blob_is_unchanged(archive):
    repo, vintage, sha, old = archive
    surface = ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),))
    ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-14',
        live_ref='main', vintage_commit=sha, surface=surface)
    assert pd.read_parquet(vintage / 'data/yahoo/SPY.parquet')['close'].tolist() == [100.]
    replay = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
        live_ref='main', vintage_commit=sha, surface=surface)
    pd.testing.assert_frame_equal(pd.read_parquet(vintage / 'data/yahoo/SPY.parquet'), old)
    assert replay['files']['data/yahoo/SPY.parquet']['added'] == ['2026-07-15']


def test_pipeline_receipt_retains_control_input_restoration(archive, tmp_path, monkeypatch):
    import json
    repo, vintage, _, _ = archive
    relative = 'site/factordata/test-board.json'
    reference = {'as_of': '2026-07-14', 'rank_by': 'fixture',
        'board_definition': 'fixture', 'buy': [{'ticker': 'SPY'}]}
    board = repo / relative
    board.parent.mkdir(parents=True)
    board.write_text(json.dumps(reference))
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'synthetic reference board')
    sha = git(repo, 'rev-parse', 'HEAD')
    work = tmp_path / 'work'; work.mkdir()
    def build(vintage, *, through, work, **kwargs):
        path = work / ('board-' + through + '.json')
        path.write_text(json.dumps({**reference, 'as_of': through}))
        return path
    monkeypatch.setattr(ppr, 'build_board', build)
    monkeypatch.setattr(ppr, 'reset_builder_state', lambda *args: {})
    entry = {'board_relpath': relative, 'build_cmd': (), 'fidelity_floor': 0.85,
        'price_surface': ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),)),
        'plans_supported': False, 'alpha_prestep': False}
    result = ppr.run_pit_replay(repo, market='us', session='2026-07-15', entry=entry,
        vintage=vintage, vintage_sha=sha, plans_baseline=sha, live_price_ref=sha,
        work=work, control=True, aux_panel_source=None, allow_low_fidelity=False)
    assert result['restored_vintage_inputs']['control']['data/yahoo/SPY.parquet']['source_commit'] == sha
    assert result['restored_vintage_inputs']['replay'] == {}
    receipt = ppr.build_harness_receipt(market='us', session='2026-07-15', entry=entry,
        vintage_info={'slot_utc': '2026-07-15T22:30:00Z', 'sha': sha,
                      'committed_utc': '2026-07-15T21:00:00Z', 'ancestry': 'fixture'},
        result=result, executed_at='2026-07-16T00:00:00Z', executing_commit=sha, dry_run=True)
    assert receipt['restored_vintage_inputs'] == result['restored_vintage_inputs']
    assert receipt['harness_fidelity']['passes_floor'] is True
