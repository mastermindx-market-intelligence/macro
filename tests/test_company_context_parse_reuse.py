"""Synthetic immutable parsing tests; no production bundle or HTTP request."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timezone
from io import BytesIO
from threading import Lock
import json
import subprocess

import pandas as pd
import pytest
import yaml

from engine.company_intelligence import current_company_context as c


def bundle(*, commit='a' * 40, cik='0000000001', suffix='A', until=None):
    securities = [dict(security_id='SEC:US-XNAS-AA'+suffix,
        issuer_id='ISS:US-XNAS-AA'+suffix, issuer_state='RESOLVED',
        listing_key='US-XNAS-AA'+suffix, issuer_cik=cik,
        issuer_evidence_snapshot='2026-01-01')]
    aliases = [dict(vendor='store', vendor_symbol='AA'+suffix,
        security_id='SEC:US-XNAS-AA'+suffix, valid_from='2026-01-01', valid_to=until)]
    issuers = [dict(issuer_id='ISS:US-XNAS-AA'+suffix, cik=cik,
        status='active', evidence_source='sec_company_tickers', evidence_snapshot='2026-01-01')]
    def parquet(rows):
        stream = BytesIO()
        pd.DataFrame(rows).to_parquet(stream, index=False)
        return stream.getvalue()
    return c.IdentityBundle(commit, parquet(securities), parquet(aliases), parquet(issuers))


def resolve(value, symbol='AAA', today=date(2026, 1, 1)):
    return c.resolve_current_company(value, symbol, today=today)


def count_decodes(monkeypatch):
    counts = []
    real = c._rows
    lock = Lock()
    def counted(raw):
        with lock:
            counts.append(len(raw))
        return real(raw)
    monkeypatch.setattr(c, '_rows', counted)
    return counts


def test_repeated_resolution_reuses_only_parsing(monkeypatch):
    # Regression: repeated fresh resolution reparses the identical three blobs.
    value = bundle(commit='1' * 40)
    counts = count_decodes(monkeypatch)
    outputs = [resolve(value) for _ in range(24)]
    assert all(x['issuer_binding']['evidenced_cik'] == '0000000001' for x in outputs)
    assert len(counts) == 3


def test_changed_bytes_and_generation_never_reuse_old_identity(monkeypatch):
    first = bundle(commit='2' * 40)
    second = bundle(commit='2' * 40, cik='0000000002')
    third = replace(second, source_commit='3' * 40)
    counts = count_decodes(monkeypatch)
    outputs = [resolve(value) for value in (first, second, third)]
    assert [x['issuer_binding']['evidenced_cik'] for x in outputs] == [
        '0000000001', '0000000002', '0000000002']
    assert outputs[2]['identity_receipt']['source_commit'] == '3' * 40
    assert outputs[1]['issuer_binding']['identity_snapshot_reference'] != outputs[2]['issuer_binding']['identity_snapshot_reference']
    assert len(counts) == 9


def test_date_and_symbol_are_resolved_again_after_parse_hit():
    value = bundle(commit='4' * 40, until='2026-01-02')
    assert resolve(value)['security_id'] == 'SEC:US-XNAS-AAA'
    for symbol, today in [('AAA', date(2026, 1, 2)), ('AAB', date(2026, 1, 1)),
                          ('AAA', date(2025, 12, 31))]:
        with pytest.raises(c.native.DisclosureError):
            resolve(value, symbol, today)


def test_mutating_response_cannot_poison_later_identity():
    value = bundle(commit='5' * 40)
    first = resolve(value)
    first['issuer_binding']['evidenced_cik'] = '9999999999'
    first['identity_receipt']['sources']['security_master']['sha256'] = '0' * 64
    first['query']['symbol'] = 'WRONG'
    second = resolve(value)
    assert second['issuer_binding']['evidenced_cik'] == '0000000001'
    assert second['identity_receipt']['sources']['security_master']['sha256'] != '0' * 64
    assert second['query']['symbol'] == 'AAA'


def test_one_generation_bound_releases_previous_parse(monkeypatch):
    first, second = bundle(commit='6' * 40), bundle(commit='7' * 40)
    counts = count_decodes(monkeypatch)
    for value in (first, second, first):
        assert resolve(value)['security_id'] == 'SEC:US-XNAS-AAA'
    assert len(counts) == 9


def test_concurrent_cold_reads_parse_once_and_return_separate_results(monkeypatch):
    value = bundle(commit='8' * 40)
    counts = count_decodes(monkeypatch)
    with ThreadPoolExecutor(max_workers=8) as pool:
        outputs = list(pool.map(lambda _: resolve(value), range(24)))
    assert len(counts) == 3
    assert len({id(x) for x in outputs}) == 24
    outputs[0]['issuer_binding']['evidenced_cik'] = '9999999999'
    assert all(x['issuer_binding']['evidenced_cik'] == '0000000001' for x in outputs[1:])


def test_current_owner_is_reconsulted_and_can_revoke_warm_parsing():
    value = bundle(commit='9' * 40)
    resolve(value)
    class Owner:
        calls = 0
        def current_identity_bundle(self, purpose, audience):
            assert (purpose, audience) == ('private_company_intelligence_context', 'company_intelligence_entitled')
            self.calls += 1
            return value if self.calls == 1 else None
    owner = Owner()
    with pytest.raises(c.native.DisclosureError):
        c.read_company_context(owner, 'AAA', purpose='private_company_intelligence_context',
                               audience='company_intelligence_entitled')
    assert owner.calls == 2


@pytest.mark.parametrize('field', ['security_master', 'vendor_aliases', 'issuer_master'])
def test_changed_malformed_blob_fails_after_warm_parse(field):
    value = bundle(commit='b' * 40)
    resolve(value)
    with pytest.raises(c.native.DisclosureError):
        resolve(replace(value, **{field: b'invalid parquet'}))


def test_midnight_transition_refuses_with_warm_parse(monkeypatch):
    value = bundle(commit='c' * 40)
    resolve(value)
    ticks = iter([datetime(2026, 1, 1, 23, 59, 59, tzinfo=timezone.utc),
                  datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)])
    class Clock:
        @staticmethod
        def now(tz):
            assert tz == timezone.utc
            return next(ticks)
    class Owner:
        def current_identity_bundle(self, purpose, audience):
            return value
    monkeypatch.setattr(c, 'datetime', Clock)
    with pytest.raises(c.native.DisclosureError):
        c.read_company_context(Owner(), 'AAA', purpose='private_company_intelligence_context',
                               audience='company_intelligence_entitled')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode().strip()


def commit(repo):
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'synthetic immutable reference')
    git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
    return git(repo, 'rev-parse', 'HEAD')


@pytest.fixture
def installed(tmp_path):
    from engine.company_intelligence import current_context_runtime as runtime
    repo = tmp_path / 'repo'
    repo.mkdir()
    git(repo, 'init', '-q', '-b', 'main')
    git(repo, 'config', 'user.name', 'Synthetic fixture')
    git(repo, 'config', 'user.email', 'synthetic@example.invalid')
    value = bundle(commit='d' * 40)
    for name, path in runtime._ARTIFACTS.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        data = getattr(value, name)
        if name == 'issuer_master':
            frame = pd.read_parquet(BytesIO(data))
            frame['n_securities'] = 1
            stream = BytesIO()
            frame.to_parquet(stream, index=False)
            data = stream.getvalue()
        target.write_bytes(data)
    receipt = dict(producer='scripts/build_security_master.py', notes=[],
        generated_at='2026-01-01T00:00:00',
        dataset_ids=['reference.' + name for name in runtime._ARTIFACTS],
        authority=dict(identity_authority='canonical_exact_identity', signal_authority='none',
            ranking_authority='none', trade_authority='none', consumers=['gmi.identity_resolution/v1']),
        row_counts=dict(security_master=1, vendor_aliases=1, issuer_master=1, vendor_alias_rows_readable=1))
    (repo / runtime._RECEIPT).write_text(json.dumps(receipt))
    contracts = []
    for name, path in runtime._ARTIFACTS.items():
        key = 'security_id' if name == 'security_master' else 'issuer_id' if name == 'issuer_master' else 'vendor_symbol'
        contracts.append(dict(dataset_id='reference.'+name, layer='L2', status='PRODUCED',
            owner='macro-dashboard', producer='scripts/build_security_master.py', storage=path,
            format='parquet', grain=[key], temporal_profile='SNAPSHOT_SERIES', timezone='UTC',
            frequency='on_demand', conflict_policy='DOMAIN_AUTHORITY', version='0.1.0'))
    (repo / 'config').mkdir()
    (repo / runtime._REGISTRY).write_text(yaml.safe_dump({'datasets': contracts}))
    head = commit(repo)
    return repo, runtime.CommittedCompanyContextOwner(repo), head, runtime


def current(owner):
    return c.read_company_context(owner, 'AAA', purpose='private_company_intelligence_context',
                                   audience='company_intelligence_entitled')


def test_real_adapter_receipt_only_revision_changes_returned_generation(installed):
    repo, owner, first, runtime = installed
    assert current(owner)['identity_receipt']['source_commit'] == first
    path = repo / runtime._RECEIPT
    data = json.loads(path.read_text())
    data['code_version'] = 'corrected producer metadata'
    path.write_text(json.dumps(data))
    second = commit(repo)
    assert second != first
    assert current(owner)['identity_receipt']['source_commit'] == second


def test_real_adapter_registry_revocation_wins_over_warm_parse(installed):
    repo, owner, _, runtime = installed
    assert current(owner)['issuer_binding']['evidenced_cik'] == '0000000001'
    path = repo / runtime._REGISTRY
    data = yaml.safe_load(path.read_text())
    data['datasets'][0]['status'] = 'PROPOSED'
    path.write_text(yaml.safe_dump(data))
    commit(repo)
    with pytest.raises(c.native.DisclosureError):
        current(owner)


def test_real_adapter_head_change_still_refuses_warm_parse(installed, monkeypatch):
    _, owner, _, _ = installed
    current(owner)
    head = owner._head
    calls = []
    def changing():
        calls.append(1)
        return head() if len(calls) == 1 else 'f' * 40
    monkeypatch.setattr(owner, '_head', changing)
    with pytest.raises(c.native.DisclosureError):
        current(owner)
    assert len(calls) == 2
