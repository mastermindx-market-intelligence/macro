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
    replay_restore = result['restored_vintage_inputs']['replay']['data/yahoo/SPY.parquet']
    assert replay_restore['kind'] == 'historical_tail'
    assert replay_restore['source_commit'] == sha
    assert replay_restore['restored_sessions'] == ['2026-07-15']
    receipt = ppr.build_harness_receipt(market='us', session='2026-07-15', entry=entry,
        vintage_info={'slot_utc': '2026-07-15T22:30:00Z', 'sha': sha,
                      'committed_utc': '2026-07-15T21:00:00Z', 'ancestry': 'fixture'},
        result=result, executed_at='2026-07-16T00:00:00Z', executing_commit=sha, dry_run=True)
    assert receipt['restored_vintage_inputs'] == result['restored_vintage_inputs']
    assert receipt['harness_fidelity']['passes_floor'] is True


@pytest.fixture
def wide_archive(archive):
    repo, vintage, _, _ = archive
    relative = 'data/test_panel/closes.parquet'
    path = repo / relative
    path.parent.mkdir(parents=True)
    old = pd.DataFrame({'AAA': [100., 101.], 'RETIRED': [50., 51.]},
                      index=pd.to_datetime(['2026-07-14', '2026-07-15']))
    old.to_parquet(path)
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'historical wide panel')
    return repo, vintage, git(repo, 'rev-parse', 'HEAD'), old, relative


@pytest.mark.parametrize('directory_exists', [False, True])
def test_missing_tracked_wide_panel_keeps_historical_rows_and_columns(wide_archive, directory_exists):
    repo, vintage, sha, old, relative = wide_archive
    if directory_exists:
        (vintage / relative).parent.mkdir(parents=True)
    later = pd.DataFrame({'AAA': [900., 901., 102., 999.], 'NEW': [1., 2., 3., 4.]},
        index=pd.to_datetime(['2026-07-14', '2026-07-15', '2026-07-16', '2026-07-17']))
    later.to_parquet(repo / relative)
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'later wide-panel revisions')
    manifest = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-16',
        live_ref='main', vintage_commit=sha,
        surface=ppr.PriceSurface(wide_panels=(relative,)))
    actual = pd.read_parquet(vintage / relative)
    pd.testing.assert_frame_equal(actual.loc[:'2026-07-15'], old)
    assert list(actual.columns) == ['AAA', 'RETIRED']
    assert actual.loc['2026-07-16', 'AAA'] == 102.
    assert pd.isna(actual.loc['2026-07-16', 'RETIRED'])
    assert manifest['files'][relative]['added'] == ['2026-07-16']
    assert manifest['files'][relative]['substituted'] is False
    assert manifest['restored_vintage_inputs'][relative]['source_commit'] == sha


def test_later_panel_deletion_does_not_erase_historical_panel(wide_archive):
    repo, vintage, sha, old, relative = wide_archive
    git(repo, 'rm', relative); git(repo, 'commit', '-m', 'later panel removal')
    manifest = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
        live_ref='main', vintage_commit=sha,
        surface=ppr.PriceSurface(wide_panels=(relative,)))
    assert (vintage / relative).exists(), 'tracked historical panel silently omitted'
    pd.testing.assert_frame_equal(pd.read_parquet(vintage / relative), old)
    assert manifest['restored_vintage_inputs'][relative]['source_commit'] == sha


def test_corrupt_tracked_wide_history_cannot_fall_back_to_later_values(wide_archive):
    repo, vintage, _, old, relative = wide_archive
    (repo / relative).write_bytes(b'corrupt historical panel')
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'corrupt pinned panel')
    sha = git(repo, 'rev-parse', 'HEAD')
    old.to_parquet(repo / relative)
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'later repaired panel')
    with pytest.raises(ppr.PitReplayRefused, match='cannot restore historical price input'):
        ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
            live_ref='main', vintage_commit=sha,
            surface=ppr.PriceSurface(wide_panels=(relative,)))
    assert not (vintage / relative).exists()


def test_wide_panel_restoration_is_idempotent_across_two_passes(wide_archive):
    repo, vintage, sha, old, relative = wide_archive
    surface = ppr.PriceSurface(wide_panels=(relative,))
    control = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-14',
        live_ref='main', vintage_commit=sha, surface=surface)
    assert control['restored_vintage_inputs'][relative]['rows'] == 1
    replay = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
        live_ref='main', vintage_commit=sha, surface=surface)
    pd.testing.assert_frame_equal(pd.read_parquet(vintage / relative), old)
    assert replay['files'][relative]['added'] == ['2026-07-15']
    path = vintage / relative
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    repeat = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
        live_ref='main', vintage_commit=sha, surface=surface)
    assert repeat['restored_vintage_inputs'] == {}
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert ppr.tree_fingerprint(replay) == ppr.tree_fingerprint(repeat)


@pytest.mark.parametrize('sparse', [False, True])
def test_wide_panel_real_builder_pipeline_matches_full_checkout(wide_archive, tmp_path, sparse):
    import json
    import sys
    repo, vintage, _, old, relative = wide_archive
    board_relative = 'site/factordata/test-board.json'
    reference = {'as_of': '2026-07-14', 'rank_by': 'fixture',
        'board_definition': 'fixture', 'buy': [{'ticker': 'AAA'}, {'ticker': 'RETIRED'}]}
    board = repo / board_relative
    board.parent.mkdir(parents=True)
    board.write_text(json.dumps(reference))
    (repo / 'build_fixture.py').write_text(
        'import json\nfrom pathlib import Path\nimport pandas as pd\n'
        f'frame = pd.read_parquet({relative!r})\n'
        f'out = Path({board_relative!r})\n'
        'out.parent.mkdir(parents=True, exist_ok=True)\n'
        "payload = {'as_of': str(frame.index.max())[:10], 'rank_by': 'fixture',\n"
        "    'board_definition': 'fixture', 'columns': list(frame.columns),\n"
        "    'buy': [{'ticker': str(c)} for c in frame.columns if pd.notna(frame[c].iloc[-1])],\n"
        "    'fixture_aaa_close': float(frame['AAA'].iloc[-1]),\n"
        "    'fixture_aaa_sum': float(frame['AAA'].sum())}\n"
        'out.write_text(json.dumps(payload, sort_keys=True))\n')
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'synthetic producer and reference')
    sha = git(repo, 'rev-parse', 'HEAD')
    later = pd.DataFrame({'AAA': [900., 901., 102.], 'NEW': [7., 8., 9.]},
        index=pd.to_datetime(['2026-07-14', '2026-07-15', '2026-07-16']))
    later.to_parquet(repo / relative)
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'synthetic later panel')
    source_bytes = (repo / relative).read_bytes()
    git(repo, 'clone', '--quiet', '--no-hardlinks', str(repo), str(vintage))
    git(vintage, 'checkout', '--quiet', '--detach', sha)
    if sparse:
        (vintage / relative).unlink()
    work = tmp_path / 'pipeline-work'
    entry = {'board_relpath': board_relative,
        'build_cmd': (sys.executable, 'build_fixture.py'), 'fidelity_floor': 0.85,
        'price_surface': ppr.PriceSurface(wide_panels=(relative,)),
        'plans_supported': False, 'alpha_prestep': False}
    result = ppr.run_pit_replay(repo, market='us', session='2026-07-16', entry=entry,
        vintage=vintage, vintage_sha=sha, plans_baseline=sha, live_price_ref='main',
        work=work, control=True, aux_panel_source=None, allow_low_fidelity=False)
    actual = json.loads(Path(result['board_path']).read_text())
    assert actual == {'as_of': '2026-07-16', 'rank_by': 'fixture',
        'board_definition': 'fixture', 'columns': ['AAA', 'RETIRED'],
        'buy': [{'ticker': 'AAA'}], 'fixture_aaa_close': 102., 'fixture_aaa_sum': 303.}
    assert result['fidelity']['jaccard'] == 1.0
    assert result['fidelity']['waived'] is False
    assert result['minted'] == []
    assert result['overlay']['fence']['violations'] == 0
    assert (repo / relative).read_bytes() == source_bytes
    expected_restored = {relative} if sparse else set()
    assert set(result['restored_vintage_inputs']['control']) == expected_restored
    receipt = ppr.build_harness_receipt(market='us', session='2026-07-16', entry=entry,
        vintage_info={'slot_utc': '2026-07-16T22:30:00Z', 'sha': sha,
                      'committed_utc': '2026-07-16T21:00:00Z', 'ancestry': 'fixture'},
        result=result, executed_at='2026-07-17T00:00:00Z', executing_commit=sha, dry_run=True)
    assert set(receipt['restored_vintage_inputs']['control']) == expected_restored
    assert receipt['harness_fidelity']['passes_floor'] is True
    assert receipt['board_identity']['as_of'] == '2026-07-16'
    assert receipt['dry_run'] is True
    restored_tail = receipt['restored_vintage_inputs']['replay'][relative]
    assert restored_tail['source_commit'] == sha
    assert restored_tail['restored_sessions'] == ['2026-07-15']
    assert receipt['overlay_files'][relative]['historical_tail'] == restored_tail
    assert result['board_builds']['control']['mode'] == 'fresh'
    assert result['board_builds']['replay']['mode'] == 'fresh'
    assert receipt['board_builds'] == result['board_builds']
    assert receipt['board_builds']['control']['proof']['binding']['vintage_sha'] == sha
    assert receipt['board_builds']['replay']['proof']['output_sha256'] == receipt['board_identity']['sha256']
    repeated = ppr.run_pit_replay(repo, market='us', session='2026-07-16', entry=entry,
        vintage=vintage, vintage_sha=sha, plans_baseline=sha, live_price_ref='main',
        work=work, control=True, aux_panel_source=None, allow_low_fidelity=False)
    assert repeated['board_builds']['control']['mode'] == 'cache'
    assert repeated['board_builds']['replay']['mode'] == 'cache'
    assert repeated['board_identity']['sha256'] == result['board_identity']['sha256']
    import hashlib
    evidence = {'kind': 'SYNTHETIC_TWO_PASS_PIPELINE_PROOF', 'sparse_fixture': sparse,
        'scope': 'temporary Git data and real builder subprocess; no real market control',
        'owner_sha256': hashlib.sha256(Path(ppr.__file__).read_bytes()).hexdigest(),
        'first_harness_receipt': receipt,
        'repeat_board_builds': repeated['board_builds'],
        'repeat_output_matches': repeated['board_identity']['sha256'] == result['board_identity']['sha256'],
        'source_panel_untouched': (repo / relative).read_bytes() == source_bytes}
    (work / 'synthetic-acceptance.json').write_text(json.dumps(evidence, indent=2))


def test_unavailable_tracked_wide_blob_refuses_without_later_substitution(wide_archive, monkeypatch):
    repo, vintage, sha, _, relative = wide_archive
    monkeypatch.setattr(ppr, 'batch_blobs', lambda *args: {})
    with pytest.raises(ppr.PitReplayRefused, match='missing historical price blobs'):
        ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
            live_ref='main', vintage_commit=sha,
            surface=ppr.PriceSurface(wide_panels=(relative,)))
    assert not (vintage / relative).exists()


def test_genuinely_untracked_aux_panel_still_discloses_substitution(archive, tmp_path):
    repo, vintage, sha, old = archive
    relative = 'data/test_aux/closes.parquet'
    aux = tmp_path / 'auxiliary'
    aux.mkdir()
    old.to_parquet(aux / 'closes.parquet')
    manifest = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
        live_ref='main', vintage_commit=sha, aux_panel_source=aux,
        surface=ppr.PriceSurface(wide_panels=(relative,),
            aux_panel_dirnames=frozenset({'test_aux'})))
    pd.testing.assert_frame_equal(pd.read_parquet(vintage / relative), old)
    assert manifest['restored_vintage_inputs'] == {}
    assert manifest['files'][relative]['substituted'] is True
    assert manifest['files'][relative]['added'] == ['2026-07-14', '2026-07-15']


@pytest.fixture
def board_builder(tmp_path):
    import json
    import sys
    vintage = tmp_path / 'builder-vintage'
    vintage.mkdir()
    relative = 'site/fixture-board.json'
    target = vintage / relative
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({'as_of': '2026-07-14', 'marker': 'original'}))
    script = (
        'import json\nfrom pathlib import Path\n'
        f'out = Path({relative!r})\n'
        'prior = json.loads(out.read_text()) if out.exists() else {}\n'
        "counter = Path('builder-count.txt')\n"
        'count = int(counter.read_text()) + 1 if counter.exists() else 1\n'
        'counter.write_text(str(count))\n'
        'out.parent.mkdir(parents=True, exist_ok=True)\n'
        "out.write_text(json.dumps({'as_of': '2026-07-14', 'generation': count,\n"
        "    'prior_marker': prior.get('marker')}, sort_keys=True))\n")
    return vintage, relative, target, tmp_path / 'builder-work', (sys.executable, '-c', script)


def test_successful_noop_cannot_reuse_preexisting_board_as_fresh_output(board_builder):
    import sys
    vintage, relative, target, work, _ = board_builder
    original = target.read_bytes()
    with pytest.raises(ppr.PitReplayRefused, match='did not write'):
        ppr.build_board(vintage, through='2026-07-14', work=work,
            build_cmd=(sys.executable, '-c', 'pass'), board_relpath=relative,
            fingerprint='synthetic-noop')
    assert target.read_bytes() == original
    assert not (work / 'board_2026-07-14_synthetic-noop.json').exists()


def test_legacy_bare_cache_cannot_launder_a_noop_builder(board_builder):
    import sys
    vintage, relative, target, work, _ = board_builder
    work.mkdir()
    (work / 'board_2026-07-14_legacy.json').write_bytes(target.read_bytes())
    with pytest.raises(ppr.PitReplayRefused, match='did not write'):
        ppr.build_board(vintage, through='2026-07-14', work=work,
            build_cmd=(sys.executable, '-c', 'pass'), board_relpath=relative,
            fingerprint='legacy', vintage_sha='a' * 40)


def test_builder_may_read_original_board_before_writing_and_receipts_are_bound(board_builder):
    import hashlib
    import json
    vintage, relative, target, work, command = board_builder
    observation = {}
    output = ppr.build_board(vintage, through='2026-07-14', work=work,
        build_cmd=command, board_relpath=relative, fingerprint='fixture-prices',
        vintage_sha='a' * 40, observation=observation)
    assert json.loads(output.read_text())['prior_marker'] == 'original'
    proof = json.loads(output.with_suffix('.buildproof.json').read_text())
    assert proof['schema'] == 'pit_replay.board_build_proof/v1'
    assert proof['output_sha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert proof['binding']['vintage_sha'] == 'a' * 40
    assert proof['binding']['price_fingerprint'] == 'fixture-prices'
    assert proof['before'] != proof['after']
    assert observation == {'mode': 'fresh', 'proof': proof}
    assert target.read_bytes() == output.read_bytes()


def test_identical_content_rewrite_is_a_real_output_write(board_builder):
    import os
    import sys
    vintage, relative, target, work, _ = board_builder
    before = target.read_bytes()
    os.utime(target, ns=(1_000_000_000, 1_000_000_000))
    command = (sys.executable, '-c',
        f'from pathlib import Path; p=Path({relative!r}); p.write_bytes(p.read_bytes())')
    observation = {}
    output = ppr.build_board(vintage, through='2026-07-14', work=work,
        build_cmd=command, board_relpath=relative, fingerprint='same-content',
        observation=observation)
    assert output.read_bytes() == before
    assert observation['mode'] == 'fresh'
    assert observation['proof']['before'] != observation['proof']['after']


@pytest.mark.parametrize('change', ['cache_body', 'proof', 'proof_missing_before',
                                   'proof_partial_after', 'command', 'env', 'source'])
def test_cache_rebuilds_when_output_or_declared_build_identity_changes(board_builder, change):
    import json
    vintage, relative, target, work, command = board_builder
    args = dict(through='2026-07-14', work=work, build_cmd=command,
        board_relpath=relative, fingerprint='fixed-prices', vintage_sha='a' * 40)
    output = ppr.build_board(vintage, **args)
    if change == 'cache_body':
        output.write_text(json.dumps({'as_of': '2026-07-14', 'generation': 999}))
    elif change == 'proof':
        output.with_suffix('.buildproof.json').write_text('{}')
    elif change in ('proof_missing_before', 'proof_partial_after'):
        proof_path = output.with_suffix('.buildproof.json')
        proof = json.loads(proof_path.read_text())
        if change == 'proof_missing_before':
            del proof['before']
        else:
            proof['after'] = {'sha256': proof['output_sha256']}
        proof_path.write_text(json.dumps(proof))
    elif change == 'command':
        args['build_cmd'] = (*command[:-1], command[-1] + '\n# new command identity\n')
    elif change == 'env':
        args['env_pins'] = {'TZ': 'UTC'}
    elif change == 'source':
        args['vintage_sha'] = 'b' * 40
    observation = {}
    rebuilt = ppr.build_board(vintage, **args, observation=observation)
    assert json.loads(rebuilt.read_text())['generation'] == 2
    assert (vintage / 'builder-count.txt').read_text() == '2'
    assert target.read_bytes() == rebuilt.read_bytes()
    assert observation['mode'] == 'fresh'


def test_valid_cache_restores_target_without_executing_builder_again(board_builder):
    vintage, relative, target, work, command = board_builder
    args = dict(through='2026-07-14', work=work, build_cmd=command,
        board_relpath=relative, fingerprint='verified', vintage_sha='a' * 40)
    output = ppr.build_board(vintage, **args)
    expected = output.read_bytes()
    target.unlink()
    target.parent.rmdir()
    observation = {}
    cached = ppr.build_board(vintage, **args, observation=observation)
    assert cached.read_bytes() == expected == target.read_bytes()
    assert (vintage / 'builder-count.txt').read_text() == '1'
    assert observation['mode'] == 'cache'
    assert observation['proof']['output_sha256']


def test_missing_price_fingerprint_never_reuses_a_board_cache(board_builder):
    import json
    vintage, relative, _, work, command = board_builder
    args = dict(through='2026-07-14', work=work, build_cmd=command,
                board_relpath=relative, vintage_sha='a' * 40)
    ppr.build_board(vintage, **args)
    output = ppr.build_board(vintage, **args)
    assert json.loads(output.read_text())['generation'] == 2
    assert (vintage / 'builder-count.txt').read_text() == '2'


def test_missing_source_identity_never_reuses_a_board_cache(board_builder):
    import json
    vintage, relative, _, work, command = board_builder
    args = dict(through='2026-07-14', work=work, build_cmd=command,
                board_relpath=relative, fingerprint='known-price-only')
    ppr.build_board(vintage, **args)
    output = ppr.build_board(vintage, **args)
    assert json.loads(output.read_text())['generation'] == 2


@pytest.mark.parametrize('payload, message', [
    ('not-json', 'invalid JSON'), ('[]', 'non-object'),
    ('{"as_of": "2026-07-15"}', 'as_of')])
def test_newly_written_bad_board_never_earns_cache_proof(board_builder, payload, message):
    import sys
    vintage, relative, _, work, _ = board_builder
    command = (sys.executable, '-c',
        f'from pathlib import Path; Path({relative!r}).write_text({payload!r})')
    observation = {}
    with pytest.raises(ppr.PitReplayRefused, match=message):
        ppr.build_board(vintage, through='2026-07-14', work=work,
            build_cmd=command, board_relpath=relative, fingerprint='invalid-output',
            vintage_sha='a' * 40, observation=observation)
    assert observation == {}
    assert not (work / 'board_2026-07-14_invalid-output.buildproof.json').exists()


@pytest.mark.parametrize('allow_low_fidelity', [False, True])
def test_noop_pipeline_refuses_before_fidelity_is_computed(wide_archive, tmp_path,
                                                         monkeypatch, allow_low_fidelity):
    import json
    import sys
    repo, vintage, _, _, panel = wide_archive
    relative = 'site/factordata/test-board.json'
    target = repo / relative
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({'as_of': '2026-07-14', 'rank_by': 'fixture',
        'board_definition': 'fixture', 'buy': [{'ticker': 'AAA'}]}))
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'preexisting reference fixture')
    sha = git(repo, 'rev-parse', 'HEAD')
    git(repo, 'clone', '--quiet', '--no-hardlinks', str(repo), str(vintage))
    original = (vintage / relative).read_bytes()
    reached = []
    def forbidden_fidelity(*args):
        reached.append(True)
        raise AssertionError('a no-output producer reached the fidelity calculator')
    monkeypatch.setattr(ppr, 'board_fidelity', forbidden_fidelity)
    entry = {'board_relpath': relative, 'build_cmd': (sys.executable, '-c', 'pass'),
        'price_surface': ppr.PriceSurface(wide_panels=(panel,)),
        'fidelity_floor': 0.85, 'plans_supported': False, 'alpha_prestep': False}
    work = tmp_path / 'noop-pipeline'
    with pytest.raises(ppr.PitReplayRefused, match='did not write'):
        ppr.run_pit_replay(repo, market='us', session='2026-07-15', entry=entry,
            vintage=vintage, vintage_sha=sha, plans_baseline=sha, live_price_ref=sha,
            work=work, control=True, aux_panel_source=None,
            allow_low_fidelity=allow_low_fidelity)
    assert reached == []
    assert (vintage / relative).read_bytes() == original
    assert not list(work.glob('*.buildproof.json'))


def test_later_git_panel_is_not_mislabelled_as_auxiliary_cache(archive):
    repo, vintage, sha, old = archive
    relative = 'data/test_panel/later.parquet'
    path = repo / relative
    path.parent.mkdir(parents=True)
    old.rename(columns={'close': 'AAA'}).to_parquet(path)
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'later tracked panel')
    result = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
        live_ref='main', vintage_commit=sha,
        surface=ppr.PriceSurface(wide_panels=(relative,)))
    assert result['files'][relative]['substituted'] is True
    assert 'aux' not in result['files'][relative]['note']
    assert 'later store' in result['files'][relative]['note']
    assert result['restored_vintage_inputs'] == {}


def test_corrupt_existing_wide_panel_keeps_bytes_and_reports_unreadable(wide_archive):
    repo, vintage, sha, old, relative = wide_archive
    target = vintage / relative
    target.parent.mkdir(parents=True)
    corrupt = b'broken local historical panel'
    target.write_bytes(corrupt)
    (old * 900).to_parquet(repo / relative)
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'later revised panel')
    result = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-15',
        live_ref='main', vintage_commit=sha,
        surface=ppr.PriceSurface(wide_panels=(relative,)))
    assert target.read_bytes() == corrupt
    assert 'unreadable' in result['files'][relative]['note']
    assert result['files'][relative]['added_sessions'] == 0
    assert result['files'][relative].get('substituted') is not True


@pytest.mark.parametrize('panel_kind', ['ticker', 'wide'])
@pytest.mark.parametrize('later_deleted', [False, True])
@pytest.mark.parametrize('control_through', ['2026-07-13', '2026-07-14'])
def test_two_pass_restores_truncated_vintage_tail_before_later_history(
        archive, panel_kind, later_deleted, control_through):
    repo, vintage, _, old = archive
    relative = 'data/yahoo/SPY.parquet'
    if panel_kind == 'wide':
        relative = 'data/test_panel/closes.parquet'
        (repo / relative).parent.mkdir(parents=True)
        old = old.rename(columns={'close': 'AAA'})
        old.to_parquet(repo / relative)
        git(repo, 'add', '.'); git(repo, 'commit', '-m', 'historical panel')
    sha = git(repo, 'rev-parse', 'HEAD')
    surface = (ppr.PriceSurface(ticker_stores=(('data/yahoo', '*.parquet'),))
        if panel_kind == 'ticker' else ppr.PriceSurface(wide_panels=(relative,)))
    if later_deleted:
        git(repo, 'rm', relative)
    else:
        later = pd.DataFrame({old.columns[0]: [900., 901., 102.]},
            index=pd.to_datetime(['2026-07-14', '2026-07-15', '2026-07-16']))
        later.to_parquet(repo / relative)
        git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'later removal or historical restatement')
    ppr.prepare_reconstruction_tree(vintage, repo, through=control_through,
        live_ref='main', vintage_commit=sha, surface=surface)
    result = ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-16',
        live_ref='main', vintage_commit=sha, surface=surface)
    actual = pd.read_parquet(vintage / relative)
    pd.testing.assert_frame_equal(actual.loc[:'2026-07-15'], old)
    if not later_deleted:
        assert actual.iloc[-1, 0] == 102.
        assert str(actual.index.max())[:10] == '2026-07-16'
    assert result['fence']['violations'] == 0
    restored = result['restored_vintage_inputs'][relative]
    expected_dates = [str(d)[:10] for d in old.index if str(d)[:10] > control_through]
    assert restored['kind'] == 'historical_tail'
    assert restored['source_commit'] == sha
    assert restored['restored_sessions'] == expected_dates
    assert result['files'][relative]['historical_tail'] == restored
    assert result['files'][relative]['substituted'] is False
    assert result['totals']['written'] == 1
    assert result['totals']['sessions_added'] == len(expected_dates) + (not later_deleted)
    before = ((vintage / relative).read_bytes(), (vintage / relative).stat().st_mtime_ns)
    ppr.prepare_reconstruction_tree(vintage, repo, through='2026-07-16',
        live_ref='main', vintage_commit=sha, surface=surface)
    assert ((vintage / relative).read_bytes(), (vintage / relative).stat().st_mtime_ns) == before
