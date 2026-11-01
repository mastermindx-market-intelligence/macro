"""Tests for the GEX -> signal_archive snapshot (scripts/build_gex_board)."""
from __future__ import annotations

import json
import copy
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
import yaml

from engine import signal_archive as sa
from scripts import build_gex_board as bg


SESSION = date(2026, 7, 31)


def _manifest() -> list[dict]:
    """One index, one ETF, one single name — the single name must be dropped (dealer
    sign is only robust for broad indices)."""
    return [
        {"key": "SPX", "spot": 7500.0, "regime": "long", "tier": "full",
         "net_gex_bn": 26.2, "gamma_flip": 7443.0, "dist_to_flip_pct": 0.77,
         "iv30": 13.7, "put_call_oi_ratio": 1.07, "call_wall": 7700.0,
         "put_wall": 7300.0, "max_pain": 7075.0, "daily_move_pct": 0.86},
        {"key": "SPY", "spot": 745.0, "regime": "long", "tier": "full",
         "net_gex_bn": 5.1, "gamma_flip": 743.0, "dist_to_flip_pct": 0.3,
         "iv30": 13.0, "put_call_oi_ratio": 1.2, "call_wall": 770.0,
         "put_wall": 730.0, "max_pain": 707.0, "daily_move_pct": 0.8},
        {"key": "TSLA", "spot": 250.0, "regime": "short", "tier": "full",
         "net_gex_bn": -0.4, "gamma_flip": 255.0, "dist_to_flip_pct": -2.0,
         "iv30": 55.0, "put_call_oi_ratio": 0.9, "call_wall": 300.0,
         "put_wall": 200.0, "max_pain": 240.0, "daily_move_pct": 3.5},
    ]


def test_snapshot_keeps_index_etf_excludes_single_names(tmp_path):
    bg._write_archive_snapshot(_manifest(), tmp_path, SESSION)
    snap = json.loads((tmp_path / "gex" / "latest.json").read_text())
    assert set(snap["indices"]) == {"SPX", "SPY"}          # TSLA (single name) excluded
    assert snap["indices"]["SPX"]["net_gex_bn"] == 26.2
    assert snap["indices"]["SPX"]["regime"] == "long"
    assert snap["source"] == "cboe_delayed" and snap["asof"]
    assert isinstance(snap["market"], dict)                # no cboe parquets -> {} (no crash)


def test_market_context_reads_cboe(tmp_path):
    cboe = tmp_path / "cboe"
    cboe.mkdir()
    pd.DataFrame({"skew": [120.0, 146.72]},
                 index=pd.to_datetime(["2026-06-17", "2026-06-18"])).to_parquet(cboe / "skew.parquet")
    # 2026-06-19 is JUNETEENTH — the exchange is closed. _market_context session-filters
    # these cboe stores now (the #3721 weekend-row class: putcall.parquet held 13
    # non-session rows of 39, and both the published level AND the *_asof stamp come off
    # the last row), so a holiday-dated fixture row is correctly discarded. Use the next
    # real session, 2026-06-22, so "the latest row" is unambiguous.
    pd.DataFrame({"index_pc_ratio": [1.1, 1.333], "equity_pc_ratio": [1.0, 1.339]},
                 index=pd.to_datetime(["2026-06-18", "2026-06-22"])).to_parquet(cboe / "putcall.parquet")
    ctx = bg._market_context(tmp_path)
    assert ctx["skew"] == 146.72 and ctx["skew_asof"] == "2026-06-18"
    assert ctx["index_pc_ratio"] == 1.333 and ctx["put_call_asof"] == "2026-06-22"


def test_snapshot_flattens_and_dedups_in_archive(tmp_path):
    bg._write_archive_snapshot(_manifest(), tmp_path, SESSION)
    snap = json.loads((tmp_path / "gex" / "latest.json").read_text())
    asof = sa.find_asof(snap, prefer="asof")
    arch = tmp_path / "arch"
    assert sa.archive_snapshot("options_gex", snap, asof, archive_dir=arch) is True
    assert sa.archive_snapshot("options_gex", snap, asof, archive_dir=arch) is False   # keep-first
    df = sa.load_archive("options_gex", archive_dir=arch)
    assert df.iloc[0]["indices_SPX_net_gex_bn"] == 26.2           # queryable flat column
    assert df.iloc[0]["snapshot"]["indices"]["SPY"]["regime"] == "long"  # lossless backstop


def test_empty_or_nonindex_manifest_writes_nothing(tmp_path):
    bg._write_archive_snapshot(
        [{"key": "TSLA", "net_gex_bn": -0.4}], tmp_path, SESSION
    )
    assert not (tmp_path / "gex" / "latest.json").exists()        # no index/ETF -> no snapshot


def _git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


@pytest.fixture
def publication(tmp_path):
    _git(tmp_path, 'init', '-q')
    _git(tmp_path, 'config', 'user.email', 'fixture@example.invalid')
    _git(tmp_path, 'config', 'user.name', 'fixture')
    manifest = [dict(r, asof=SESSION.isoformat()) for r in _manifest()]
    bg._write_archive_snapshot(manifest, tmp_path / 'data', SESSION)
    site = tmp_path / 'site/gex'
    site.mkdir(parents=True)
    (site / 'index.json').write_text(json.dumps(manifest))
    _git(tmp_path, 'add', '.')
    _git(tmp_path, 'commit', '-qm', 'base')
    return tmp_path, _git(tmp_path, 'rev-parse', 'HEAD')


def _check(root, base, accepted=None):
    from scripts.check_gex_archive_publication import check
    return check(root, session=SESSION.isoformat(), base_ref=base, accepted_ref=accepted)


def test_publication_accepts_original_partial_projection_without_writes(publication):
    root, base = publication
    files = [root / 'data/gex/latest.json', root / 'site/gex/index.json']
    before = [p.read_bytes() for p in files]
    assert _check(root, base)['indices'] == ['SPX', 'SPY']
    assert [p.read_bytes() for p in files] == before


@pytest.mark.parametrize('change', ['date', 'source', 'value', 'missing_core',
                                  'single_name', 'duplicate_core', 'nan', 'symlink',
                                  'raw_context', 'future_context'])
def test_publication_refuses_mismatched_or_unbound_archive(publication, change):
    root, base = publication
    path = root / 'data/gex/latest.json'
    snap = json.loads(path.read_text())
    if change == 'date': snap['asof'] = '2026-07-30'
    elif change == 'source': snap['source'] = 'unbound-provider'
    elif change == 'value': snap['indices']['SPX']['net_gex_bn'] *= 1000
    elif change == 'missing_core': snap['indices'].pop('SPY')
    elif change == 'single_name': snap['indices']['TSLA'] = snap['indices']['SPY']
    elif change == 'nan': snap['indices']['SPY']['net_gex_bn'] = float('nan')
    elif change == 'raw_context': snap['market'] = {'raw_chains': [1, 2, 3]}
    elif change == 'future_context': snap['market'] = {'skew_asof': '2026-08-03'}
    elif change == 'duplicate_core':
        manifest = root / 'site/gex/index.json'
        rows = json.loads(manifest.read_text()); rows.append(copy.deepcopy(rows[0]))
        manifest.write_text(json.dumps(rows))
    elif change == 'symlink':
        other = root / 'saved.json'; other.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(other)
    if change not in {'duplicate_core', 'symlink'}: path.write_text(json.dumps(snap))
    with pytest.raises(ValueError): _check(root, base)


def test_publication_allows_nullable_producer_fields(publication):
    root, _ = publication
    p = root / 'data/gex/latest.json'; snap = json.loads(p.read_text())
    q = root / 'site/gex/index.json'; manifest = json.loads(q.read_text())
    snap['indices']['SPX']['gamma_flip'] = None
    manifest[0]['gamma_flip'] = None
    p.write_text(json.dumps(snap)); q.write_text(json.dumps(manifest))
    _git(root, 'add', '.'); _git(root, 'commit', '-qm', 'nullable')
    assert _check(root, 'HEAD')['indices'] == ['SPX', 'SPY']


def test_publication_refuses_concurrent_same_session_archive(publication):
    root, base = publication
    p = root / 'data/gex/latest.json'; original = p.read_bytes()
    snap = json.loads(original); snap['market'] = {'skew': 123, 'skew_asof': '2026-07-31'}
    p.write_text(json.dumps(snap)); _git(root, 'add', '.'); _git(root, 'commit', '-qm', 'concurrent')
    accepted = _git(root, 'rev-parse', 'HEAD')
    p.write_bytes(original)
    with pytest.raises(ValueError, match='concurrent'):
        _check(root, base, accepted)


def test_publication_accepts_already_identical_candidate(publication):
    root, base = publication
    p = root / 'data/gex/latest.json'; snap = json.loads(p.read_text())
    snap['market'] = {'skew': 123, 'skew_asof': '2026-07-31'}
    p.write_text(json.dumps(snap)); _git(root, 'add', '.'); _git(root, 'commit', '-qm', 'candidate')
    assert _check(root, base, 'HEAD')['archive_sha256']


def test_publication_refuses_uncommitted_pair_as_commit_proof(publication):
    from scripts.check_gex_archive_publication import check
    root, base = publication
    p = root / 'data/gex/latest.json'; snap = json.loads(p.read_text())
    snap['market'] = {'skew': 123, 'skew_asof': '2026-07-31'}
    p.write_text(json.dumps(snap))
    with pytest.raises(ValueError, match='candidate commit'):
        check(root, session=SESSION.isoformat(), base_ref=base, candidate_ref='HEAD')


def _publication_step():
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / '.github/workflows/closing-bell.yml').read_text())
    return next(s['run'] for s in workflow['jobs']['closingbell']['steps']
                if s.get('name') == 'commit rendered site + provisional snapshot pointers (ledgers discarded)')


@pytest.mark.parametrize('valid', [False, True])
def test_actual_closingbell_staging_obeys_archive_guard(publication, valid):
    root, _ = publication
    real = Path(__file__).resolve().parents[1]
    run = _publication_step()
    block = run.split('# GEX archive admission', 1)[1].split('\n', 1)[1].split('# THEN discard', 1)[0]
    (root / 'scripts').symlink_to(real / 'scripts', target_is_directory=True)
    path = root / 'data/gex/latest.json'; snap = json.loads(path.read_text())
    snap['market'] = {'skew': 123, 'skew_asof': '2026-07-31'}
    if not valid: snap['source'] = 'unbound-provider'
    path.write_text(json.dumps(snap))
    ledger = root / 'data/risk_radar/forward_log.jsonl'
    ledger.parent.mkdir(); ledger.write_text('unrelated fixture ledger')
    cmd = f'SESSION_DATE={SESSION.isoformat()}\n' + block
    proc = subprocess.run(['bash', '-e', '-c', cmd], cwd=root, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
    staged = _git(root, 'diff', '--cached', '--name-only').splitlines()
    assert ('data/gex/latest.json' in staged) is valid
    assert 'data/risk_radar/forward_log.jsonl' not in staged
    assert ledger.read_text() == 'unrelated fixture ledger'
    assert path.read_text() == json.dumps(snap)


def test_closingbell_checks_pair_again_after_rebase_before_push():
    run = _publication_step()
    guard = run.index('--accepted-ref origin/main')
    assert run.index('git pull --rebase') < guard < run.index('if push_do;')
    assert 'GEX_ARCHIVE_ADMITTED' in run[guard - 300:guard]
