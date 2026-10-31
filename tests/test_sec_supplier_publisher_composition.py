"""Hermetic append entry point and protected supplier decision checks."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.company_intelligence import issuer_disclosure_owner as owner
from engine.company_intelligence import issuer_disclosures as native
from engine.company_intelligence import sec_supplier_adoption as supplier
from engine.research_vault import r2_store
from scripts import publish_company_disclosure as cli


def test_protected_supplier_decision_qualifies_without_source_body():
    spec_raw = Path(supplier.SPEC_PATH).read_bytes()
    spec = owner._json(spec_raw)
    snapshot = owner.qualify_records('a' * 40, spec_raw, Path(supplier.POLICY_PATH).read_bytes(),
        Path(owner.REGISTRY_PATH).read_bytes(), spec['identities'],
        theme_sources_raw=Path('config/theme_sources.yml').read_bytes())
    assert snapshot.spec['fact']['subject_id'] == 'ISS:US-XNAS-NVDA'
    assert snapshot.spec['fact']['object_id'] == 'ISS:US-XNYS-TSM'
    assert snapshot.spec['fact']['kind'] == 'disclosed_supplier'
    assert snapshot.spec['fact']['amount'] is snapshot.spec['fact']['economic_share'] is None
    assert native._instant(snapshot.spec['fact']['known_at']) > native._instant(
        snapshot.spec['edition']['known_at'])
    assert spec['temporal_decision']['historical_admitted'] is False


def test_append_binds_exact_protected_paths_and_separate_legacy_source(monkeypatch):
    constructed = []
    def source(repo, **kwargs):
        result = (repo, kwargs)
        constructed.append(result)
        return result
    monkeypatch.setattr(cli.owner, 'CommittedDisclosureSource', source)
    supplier_source, preserved = cli._append_sources(Path('/fixture'))
    assert supplier_source[1] == {'sec_supplier_paths': supplier.SOURCE_PATHS}
    assert preserved == {native.FACT_SCHEMA: (Path('/fixture'), {})}
    assert len(constructed) == 2


def test_local_source_override_refuses_before_any_store_construction(monkeypatch):
    monkeypatch.setenv('RESEARCH_LOCAL_STORE', '/must-not-be-created')
    monkeypatch.setattr(r2_store, 'build_store', lambda: pytest.fail('store constructed before refusal'))
    with pytest.raises(native.DisclosureError, match='SEC_LOCAL_SOURCE_OVERRIDE_REFUSED'):
        cli._pinned_supplier_source(None)


@pytest.mark.parametrize('store', [None, object()])
def test_unavailable_or_alternate_source_store_refuses_before_pinned_read(monkeypatch, store):
    monkeypatch.delenv('RESEARCH_LOCAL_STORE', raising=False)
    monkeypatch.setattr(r2_store, 'build_store', lambda: store)
    with pytest.raises(native.DisclosureError, match='SEC_NATIVE_SOURCE_STORE_UNAVAILABLE'):
        cli._pinned_supplier_source(None)


def test_factory_uses_the_existing_native_snapshot_and_never_source_discovery(monkeypatch):
    from engine.fundamental_forensics import filing_attestation
    monkeypatch.delenv('RESEARCH_LOCAL_STORE', raising=False)
    class NativeStore:
        available = True
    store = NativeStore()
    monkeypatch.setattr(r2_store, 'R2Store', NativeStore)
    monkeypatch.setattr(r2_store, 'build_store', lambda: store)
    admitted = SimpleNamespace(spec={'edition': {'schema': native.SEC_EDITION_SCHEMA,
        'sec_source': {'snapshot_id': 'ffsecsrc_' + 'b' * 64}}})
    calls = []
    def authority(**kwargs):
        calls.append(kwargs)
        return 'native-authority'
    monkeypatch.setattr(filing_attestation, 'PinnedSourceAuthority', authority)
    monkeypatch.setattr(supplier, 'PinnedSupplierSource', lambda snapshot, auth: (snapshot, auth))
    assert cli._pinned_supplier_source(admitted) == (admitted, 'native-authority')
    assert calls == [{'store': store, 'snapshot_id': 'ffsecsrc_' + 'b' * 64}]
