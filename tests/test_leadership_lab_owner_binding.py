"""Use the actual B1 writer/reader in an isolated synthetic fixture only."""
from __future__ import annotations

from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path

import pytest


@pytest.fixture
def native_store(tmp_path, monkeypatch):
    # Existing owner fixture supplies source records and calls the existing writer;
    # no new episode allocator, store schema, or validation implementation.
    from importlib import util
    spec = util.spec_from_file_location('_lab_native_fixture', Path(__file__).with_name('test_us_candidate_episode_reconciler.py'))
    owner = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(owner)
    root = tmp_path / 'fixture-repository'
    owner._seed_sources(root)
    owner._run_nightly(root, monkeypatch)
    store = owner._episode_root(root)
    head_bytes = (store / 'HEAD.json').read_bytes()
    generation = json.loads(head_bytes)['generation_id']
    book = store / 'generations' / generation / 'all_candidates.json'
    return store, generation, sha256(head_bytes).hexdigest(), sha256(book.read_bytes()).hexdigest()


def bind(native_store, **updates):
    module = import_module('engine.leadership_lab.owner_binding')
    store, generation, head_hash, book_hash = native_store
    arguments = dict(episode_store=store, generation_id=generation,
                     head_sha256=head_hash, book_sha256=book_hash)
    arguments.update(updates)
    return module.validate_native_episode_binding(**arguments)


def test_actual_native_generation_validates_without_any_store_mutation(native_store):
    store = native_store[0]
    before = {str(p.relative_to(store)): sha256(p.read_bytes()).hexdigest()
              for p in store.rglob('*') if p.is_file()}
    result = bind(native_store)
    assert result['status'] == 'VALIDATED_CANONICAL_OWNER'
    assert result['generation_id'] == native_store[1]
    assert result['historical_identity_qualified'] is False
    assert before == {str(p.relative_to(store)): sha256(p.read_bytes()).hexdigest()
                      for p in store.rglob('*') if p.is_file()}


@pytest.mark.parametrize('field,value', [('generation_id', 'peg:' + '0'*64),
                                        ('head_sha256', '0'*64), ('book_sha256', '0'*64)])
def test_read_chain_must_match_exact_git_snapshot(native_store, field, value):
    assert bind(native_store, **{field: value})['status'] == 'UNAVAILABLE'


def test_tampered_projected_book_is_rejected_by_native_validator(native_store):
    store, generation, _, _ = native_store
    path = store / 'generations' / generation / 'all_candidates.json'
    path.write_bytes(path.read_bytes() + b' ')
    result = bind(native_store)
    assert result['status'] == 'UNAVAILABLE'
    assert result['reason'] == 'NATIVE_GENERATION_INVALID'


def test_missing_store_is_unavailable_and_not_created(tmp_path):
    missing = tmp_path / 'does-not-exist'
    args = (missing, 'peg:' + '0'*64, '0'*64, '0'*64)
    assert bind(args)['status'] == 'UNAVAILABLE'
    assert not missing.exists()


@pytest.fixture
def bound_git_store(native_store):
    import subprocess
    store, generation, _, _ = native_store
    root = store.parents[2]
    episodes = json.loads((store / 'generations' / generation / 'all_candidates.json').read_bytes())['episodes']
    tickers = sorted({row['ticker_at_observation'] for row in episodes})
    payloads = {
        'site/factordata/alpha.json': {'as_of': '2026-11-27', 'per_ticker': {t: {'alpha': 1.0, 'rs': 70} for t in tickers}},
        'site/factordata/factors.json': {'as_of': '2026-11-27', 'table': []},
        'site/basketdata/baskets.json': {'as_of': '2026-11-27', 'baskets': []},
    }
    for path, data in payloads.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data))
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', 'data', 'site'], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture', '-c',
                    'user.email=fixture@example.invalid', '-c', 'core.hooksPath=/dev/null',
                    'commit', '-qm', 'Native fixture'], check=True)
    ref = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    return root, store, ref


def test_builder_binds_exact_source_generation_through_native_reader(bound_git_store):
    from scripts.build_leadership_lab import build_view
    root, store, ref = bound_git_store
    result = build_view(ref, '2026-11-27', repo_root=root, context_ref=ref, episode_store=store)
    receipt = result['current_context']['episode_book']['source_validation']
    assert receipt['status'] == 'VALIDATED_CANONICAL_OWNER'
    assert receipt['book_sha256'] == result['current_context']['sources']['episode_book']['sha256']


def test_raw_git_projection_without_native_reader_does_not_claim_validation(bound_git_store):
    from scripts.build_leadership_lab import build_view
    root, store, ref = bound_git_store
    result = build_view(ref, '2026-11-27', repo_root=root, context_ref=ref)
    assert result['current_context']['episode_book']['source_validation']['status'] == 'NOT_VALIDATED'


def test_missing_native_binding_degrades_only_episode_trust(bound_git_store, tmp_path):
    from scripts.build_leadership_lab import build_view
    root, store, ref = bound_git_store
    result = build_view(ref, '2026-11-27', repo_root=root, context_ref=ref, episode_store=tmp_path/'absent')
    assert result['recovered_count'] > 0
    assert result['current_context']['episode_book']['source_validation']['status'] == 'UNAVAILABLE'


def test_builder_reads_only_exact_ref_current_issuer_master_and_never_claims_history(bound_git_store):
    # The upstream native B1 fixture is an existing owner writer output; this
    # later CIK observation is CURRENT identity only, not historical lineage.
    import subprocess
    import pandas as pd
    from hashlib import sha256
    from scripts.build_leadership_lab import build_view, _read_current_issuer_master
    root, store, original_ref = bound_git_store
    source = root / "data/reference/security_master.parquet"
    old_master, old_receipt = _read_current_issuer_master(root, original_ref)
    assert old_receipt["read_status"] == "READ"
    assert old_master.cik_of_issuer("ISS:US-XNAS-ALFA") is None

    rows = pd.read_parquet(source)
    rows["issuer_cik"] = "0000123456"
    rows["issuer_state"] = "RESOLVED"
    rows.to_parquet(source, index=False)
    subprocess.run(["git", "-C", str(root), "add", str(source.relative_to(root))], check=True)
    subprocess.run([
        "git", "-C", str(root), "-c", "user.name=Fixture", "-c",
        "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
        "commit", "-qm", "Current source CIK synthetic fixture"], check=True)
    context_ref = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    master, receipt = _read_current_issuer_master(root, context_ref)
    assert receipt["read_status"] == "READ"
    assert receipt["sha256"] == sha256(source.read_bytes()).hexdigest()
    assert receipt["identity_scope"] == "CURRENT_ONLY_NOT_HISTORICAL"
    assert master.issuer_of_security("SEC:US-XNAS-ALFA") == "ISS:US-XNAS-ALFA"
    assert master.cik_of_issuer("ISS:US-XNAS-ALFA") == "0000123456"

    view = build_view(
        original_ref, "2026-11-27", repo_root=root, context_ref=context_ref,
        episode_store=store, earnings_details={})
    assert view["current_context"]["sources"]["issuer_master"] == receipt
    assert view["current_context"]["episode_book"]["source_validation"]["status"] == "VALIDATED_CANONICAL_OWNER"
    assert view["current_context"]["earnings"]["historical_identity_qualified"] is False
    assert view["authority"]["trade"] is False
    assert _read_current_issuer_master(root, original_ref)[0].cik_of_issuer(
        "ISS:US-XNAS-ALFA") is None
