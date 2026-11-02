"""tests/test_ontology_explorer_identity.py — F04-X1 source identity (RED first).

A composed read is only as truthful as its claim about WHICH owner generation it
read. Two failure classes are specifically in scope, and they are different:

  * MID-READ MUTATION — the nightly rewrites an artifact between the composer's
    first and last read, so the response blends two generations. Detected by
    re-verifying the byte digest after composition, not by trusting a stat taken
    before it.
  * STABLE BUT MIXED GENERATION — nothing moves during the read, yet the two
    sources already disagree: the knowledge file is at one revision and the
    compiled state was built from another. Nothing is racing; the pair is simply
    incoherent, and a digest of "what I read" cannot notice that on its own.

Both must fail closed with a typed error, never a plausible blended answer.

The freshness clause is separate and deliberately modest: this process cannot
observe what the DEPLOYED checkout serves, so it must never claim to be fresher
than the canonical `/transmission.html` surface. Where the comparison cannot be
made, it reports that the verification is unavailable.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ontology_explorer_fixtures as fx  # noqa: E402


def _compose(root: Path, **kwargs):
    from engine.ontology_explorer import compose_snapshot
    return compose_snapshot(root, chain=kwargs.pop("chain", fx.SLUG), **kwargs)


# --------------------------------------------------------------------------
# the read receipt
# --------------------------------------------------------------------------
def test_every_source_read_is_receipted_with_its_own_digest(tmp_path):
    root = fx.build_root(tmp_path)
    snap = _compose(root)
    reads = {r["path"]: r for r in snap["source"]["reads"]}
    assert set(reads) == {
        f"knowledge/transmission/{fx.SLUG}.yaml",
        "data/transmission/chain_state.json",
    }
    for relpath, receipt in reads.items():
        raw = (root / relpath).read_bytes()
        assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
        assert receipt["bytes"] == len(raw)


def test_manifest_hash_is_a_function_of_the_read_digests(tmp_path):
    """The manifest hash must be reproducible from the receipts alone —
    otherwise a caller cannot check that two responses saw the same generation."""
    from engine.ontology_explorer import manifest_hash_for
    snap = _compose(fx.build_root(tmp_path))
    assert snap["source"]["source_manifest_hash"] == manifest_hash_for(snap["source"]["reads"])


def test_identical_sources_produce_an_identical_manifest_hash(tmp_path):
    a = _compose(fx.build_root(tmp_path / "a"))
    b = _compose(fx.build_root(tmp_path / "b"))
    assert a["source"]["source_manifest_hash"] == b["source"]["source_manifest_hash"]


def test_a_single_changed_byte_changes_the_manifest_hash(tmp_path):
    root_a = fx.build_root(tmp_path / "a")
    state = fx.chain_state()
    state["chains"][0]["nodes"][0]["receipts"][0]["value"] = 999.0
    root_b = fx.build_root(tmp_path / "b", state_doc=state)
    assert (_compose(root_a)["source"]["source_manifest_hash"]
            != _compose(root_b)["source"]["source_manifest_hash"])


def test_the_receipt_is_a_read_receipt_not_an_owner_generation(tmp_path):
    """Composing does not GENERATE anything the owners did not. The digest
    describes bytes this process read; it is never presented as a new owner
    generation, and the owner's own build stamp is carried through untouched."""
    root = fx.build_root(tmp_path)
    snap = _compose(root)
    assert snap["source"]["receipt_kind"] == "composed_read"
    assert snap["source"]["built"] == "2026-01-03 02:10 UTC"
    assert snap["source"]["asof"] == "2026-01-02"
    assert "owner_generation" not in snap["source"]


# --------------------------------------------------------------------------
# mutant class 1 — mid-read mutation
# --------------------------------------------------------------------------
def test_a_mid_read_mutation_fails_closed(tmp_path, monkeypatch):
    """The nightly rewrites the state file AFTER this process has read it, so the
    composed answer describes a generation that no longer exists. The composer
    must notice by re-reading, not by trusting a stat it took beforehand."""
    from engine import ontology_explorer as oe

    root = fx.build_root(tmp_path)
    target = root / "data" / "transmission" / "chain_state.json"
    original = oe._read_source

    def mutating_read(path: Path):
        result = original(path)
        if path.name == "chain_state.json":
            doc = fx.chain_state(confirmed=(True, True, True, True), state="expressed")
            target.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return result

    monkeypatch.setattr(oe, "_read_source", mutating_read)
    with pytest.raises(oe.SourceIncoherent) as excinfo:
        _compose(root)
    assert "mid_read_mutation" in str(excinfo.value)


def test_a_write_that_lands_before_its_own_read_is_covered_by_the_rev_check(tmp_path):
    """The honest limit of digest re-verification.

    If a source is rewritten BEFORE this process reads it, that read simply
    returns the newer generation and every digest stays stable afterwards — so
    re-reading cannot detect that a sibling artifact was read from the older
    generation. What closes that window is not the digest but the revision
    coherence check, which is why both exist and why neither is redundant.
    """
    from engine.ontology_explorer import SourceIncoherent
    root = fx.build_root(tmp_path, yaml_doc=fx.chain_yaml(rev=4),
                         state_doc=fx.chain_state(rev=5))
    with pytest.raises(SourceIncoherent) as excinfo:
        _compose(root)
    assert "rev_mismatch" in str(excinfo.value)


def test_a_stable_read_does_not_trip_the_mutation_detector(tmp_path):
    """The guard must not be so eager that an ordinary quiet read fails."""
    snap = _compose(fx.build_root(tmp_path))
    assert snap["source"]["source_manifest_hash"]


# --------------------------------------------------------------------------
# mutant class 2 — stable but mixed generation
# --------------------------------------------------------------------------
def test_a_revision_mismatch_between_knowledge_and_state_fails_closed(tmp_path):
    from engine.ontology_explorer import SourceIncoherent
    root = fx.build_root(
        tmp_path,
        yaml_doc=fx.chain_yaml(rev=3),
        state_doc=fx.chain_state(rev=2),
    )
    with pytest.raises(SourceIncoherent) as excinfo:
        _compose(root)
    assert "rev_mismatch" in str(excinfo.value)


def test_an_unknown_state_schema_fails_closed(tmp_path):
    from engine.ontology_explorer import SourceIncoherent
    state = fx.chain_state()
    state["schema"] = "transmission_chains.v99"
    with pytest.raises(SourceIncoherent) as excinfo:
        _compose(fx.build_root(tmp_path, state_doc=state))
    assert "schema_incompatible" in str(excinfo.value)


def test_a_node_in_state_that_the_knowledge_file_does_not_define_fails_closed(tmp_path):
    from engine.ontology_explorer import SourceIncoherent
    state = fx.chain_state()
    state["chains"][0]["nodes"].append(
        {"id": "ghost", "resolved": True, "confirmed": True, "receipts": []})
    with pytest.raises(SourceIncoherent) as excinfo:
        _compose(fx.build_root(tmp_path, state_doc=state))
    assert "unknown_node" in str(excinfo.value)


# --------------------------------------------------------------------------
# absence of the source at all
# --------------------------------------------------------------------------
def test_a_missing_knowledge_file_is_source_unavailable(tmp_path):
    from engine.ontology_explorer import SourceUnavailable
    root = fx.build_root(tmp_path)
    (root / "knowledge" / "transmission" / f"{fx.SLUG}.yaml").unlink()
    with pytest.raises(SourceUnavailable):
        _compose(root)


def test_a_missing_state_file_is_source_unavailable(tmp_path):
    from engine.ontology_explorer import SourceUnavailable
    root = fx.build_root(tmp_path)
    (root / "data" / "transmission" / "chain_state.json").unlink()
    with pytest.raises(SourceUnavailable):
        _compose(root)


def test_an_unparseable_state_file_is_source_unavailable(tmp_path):
    from engine.ontology_explorer import SourceUnavailable
    root = fx.build_root(tmp_path)
    (root / "data" / "transmission" / "chain_state.json").write_text("{ not json",
                                                                    encoding="utf-8")
    with pytest.raises(SourceUnavailable):
        _compose(root)


def test_a_chain_absent_from_the_state_file_is_source_unavailable(tmp_path):
    from engine.ontology_explorer import SourceUnavailable
    state = fx.chain_state()
    state["chains"] = []
    with pytest.raises(SourceUnavailable):
        _compose(fx.build_root(tmp_path, state_doc=state))


# --------------------------------------------------------------------------
# freshness — never claim to be fresher than the canonical surface
# --------------------------------------------------------------------------
def test_freshness_reports_verification_unavailable_not_a_comparison(tmp_path):
    """This process reads the checkout it is running from. It cannot observe
    what the deployed canonical surface is serving, and the deployed checkout may
    lag either way, so "fresher than /transmission.html" is not a claim it is in
    a position to make."""
    snap = _compose(fx.build_root(tmp_path))
    freshness = snap["source"]["freshness"]
    assert freshness["status"] == "verification_unavailable"
    assert freshness["compared_against"] is None
    blob = json.dumps(snap, ensure_ascii=False).lower()
    assert "fresher" not in blob
    assert "most recent" not in blob
    assert "up to date" not in blob


def test_freshness_states_the_source_age_it_can_actually_observe(tmp_path):
    snap = _compose(fx.build_root(tmp_path))
    freshness = snap["source"]["freshness"]
    assert isinstance(freshness["source_age_seconds"], int)
    assert freshness["source_age_basis"] == "chain_state.built"


def test_the_house_build_stamp_format_is_actually_parsed(tmp_path):
    """The compiled artifact stamps `built` as "2026-09-05 02:10 UTC", which
    `datetime.fromisoformat` cannot read. The first version of this composer
    caught that failure and reported an age of ZERO — rendering as "built just
    now", the most reassuring possible reading of a stamp it had not understood.
    """
    snap = _compose(fx.build_root(tmp_path))
    freshness = snap["source"]["freshness"]
    assert freshness["source_age_basis"] == "chain_state.built"
    assert isinstance(freshness["source_age_seconds"], int)
    assert freshness["source_age_seconds"] > 0


def test_an_unparseable_build_stamp_reports_no_age_rather_than_zero(tmp_path):
    state = fx.chain_state()
    state["built"] = "some day, probably"
    snap = _compose(fx.build_root(tmp_path, state_doc=state))
    freshness = snap["source"]["freshness"]
    assert freshness["source_age_seconds"] is None
    assert freshness["source_age_basis"] == "unparseable_build_stamp"


def test_every_gap_carries_a_reader_facing_location(tmp_path):
    """A gap the reader cannot locate is a count, and a gap located by its raw
    field path puts internal names — and, for the watch list, the refutation
    family — onto a customer surface. Every gap gets a labelled location."""
    snapshot = _compose(fx.build_root(tmp_path))
    assert snapshot["gaps"], "fixture must produce at least one gap to test"
    for gap in snapshot["gaps"]:
        assert "where_label" in gap, gap
        assert set(gap["where_label"]) == {"en", "zh"}
        assert gap["where_label"]["en"] and gap["where_label"]["zh"]
        if gap.get("reason"):
            assert "reason_label" in gap, gap


def test_a_gap_location_never_carries_a_field_path_or_the_refutation_family():
    from engine.ontology_explorer import _REFUTATION_TERMS, _gap_where_label
    wheres = ["falsifiers[0].note", "falsifiers[3].note", "title", "state_label",
              "chain_state.built", "chain_state.asof", "nodes.oil_shock.title",
              "hops.a->b.label", "hops.a->b.condition", "hops.a->b.mechanism",
              "exposure_screens.long_duration_valuation.label",
              "exposure_screens.long_duration_valuation.note"]
    for where in wheres:
        label = _gap_where_label(where)
        assert label is not None, where
        blob = f"{label['en']} {label['zh']}".lower()
        assert not any(term in blob for term in _REFUTATION_TERMS), (where, label)
        for fragment in ("falsifier", "oil_shock", "long_duration_valuation",
                         "chain_state", "hops.", "nodes.", "[0]", "->"):
            assert fragment not in blob, (where, fragment)


def test_an_unmapped_field_path_yields_no_label_rather_than_leaking_itself():
    """Failing closed matters more than completeness here: an unrecognised path
    must not fall back to printing itself."""
    from engine.ontology_explorer import _gap_where_label
    assert _gap_where_label("some.future.field") is None
    assert _gap_where_label("") is None
    assert _gap_where_label(None) is None


def test_a_node_gap_is_located_by_step_number_not_by_slug(tmp_path):
    from engine.ontology_explorer import _label_gaps
    legs = [{"node_id": "oil_shock", "index": 2,
             "title": {"en": "Oil supply shock", "zh": "油价供给冲击"}}]
    gaps = [{"kind": "node_unresolved", "node_id": "oil_shock"},
            {"kind": "node_unresolved", "node_id": "ghost"}]
    _label_gaps(gaps, legs)
    assert gaps[0]["where_label"]["en"] == "Step 2 · Oil supply shock"
    assert "oil_shock" not in gaps[0]["where_label"]["en"]
    assert "ghost" not in gaps[1]["where_label"]["en"]
    assert "ghost" not in gaps[1]["where_label"]["zh"]


# Private X4 projection uses native identity, never ticker equality or new stores.
def _portfolio_inputs():
    from lib.dataos.identity import VendorAliasTable
    request = {'schema': 'ontology_portfolio_request.v1', 'chain': 'oil_inflation_duration_derate',
               'source_manifest_hash': 'sha256:' + '1' * 64,
               'symbols': ['NEW', 'REUSED', 'OTHER', 'MISSING']}
    snapshot = {
        'source': {'chain': 'oil_inflation_duration_derate', 'source_manifest_hash': request['source_manifest_hash'], 'reads': []},
        'company_exposure': {'status': 'available', 'reason': None, 'asof': '2026-01-02',
                             'identity_source': {'sha256': '2' * 64}},
        'exposure_screens': [{'id': 'synthetic_screen', 'status': 'available', 'companies': {
            'linked': [{'symbol': 'OLD', 'security_id': 'SEC:US-XNYS-OLD'},
                       {'symbol': 'REUSED', 'security_id': 'SEC:US-XNYS-REUSED'}],
            'unlinked': [], 'identity_unavailable': False}}],
    }
    aliases = VendorAliasTable.from_records([
        {'vendor': 'store', 'vendor_symbol': 'OLD', 'security_id': 'SEC:US-XNYS-OLD',
         'valid_from': None, 'valid_to': '2026-02-01'},
        {'vendor': 'store', 'vendor_symbol': 'NEW', 'security_id': 'SEC:US-XNYS-OLD',
         'valid_from': '2026-02-01', 'valid_to': None},
        {'vendor': 'store', 'vendor_symbol': 'REUSED', 'security_id': 'SEC:US-XNYS-REUSED',
         'valid_from': None, 'valid_to': '2026-02-01'},
        {'vendor': 'store', 'vendor_symbol': 'REUSED', 'security_id': 'SEC:US-XNYS-REUSED.2',
         'valid_from': '2026-02-01', 'valid_to': None},
        {'vendor': 'store', 'vendor_symbol': 'OTHER', 'security_id': 'SEC:CA-XTSE-OTHER',
         'valid_from': None, 'valid_to': None},
    ])
    return request, snapshot, aliases


def _portfolio_project(request=None, snapshot=None, aliases=None):
    from datetime import date
    from engine.ontology_portfolio import project_portfolio_read
    default_request, default_snapshot, default_aliases = _portfolio_inputs()
    return project_portfolio_read(request or default_request,
        snapshot=snapshot or default_snapshot, aliases=aliases or default_aliases,
        identity_date=date(2026, 10, 19))


def test_portfolio_membership_survives_rename_but_never_ticker_reuse():
    out = _portfolio_project()
    assert out['rows'][0]['state'] == 'covered'
    assert out['rows'][0]['security_id'] == 'SEC:US-XNYS-OLD'
    assert out['rows'][0]['channels'] == ['synthetic_screen']
    assert out['rows'][1]['state'] == 'not_in_available_screens'
    assert out['rows'][1]['security_id'] == 'SEC:US-XNYS-REUSED.2'
    assert out['rows'][2]['currency'] == 'CAD'
    assert out['rows'][3]['state'] == 'identity_unresolved'
    assert out['counts'] == {'covered': 1, 'not_in_available_screens': 2,
                             'identity_unresolved': 1, 'membership_unavailable': 0}
    assert out['pnl'] is None
    assert not any(out['authority'].values())


def test_portfolio_does_not_mutate_snapshot_or_carry_private_sizes():
    request, snapshot, aliases = _portfolio_inputs()
    before = json.dumps(snapshot, sort_keys=True)
    out = _portfolio_project(request, snapshot, aliases)
    assert before == json.dumps(snapshot, sort_keys=True)
    assert not any(k in json.dumps(out) for k in ('shares', 'entry_price', 'notes', 'weights'))


def test_portfolio_partial_native_screen_coverage_remains_visible():
    request, snapshot, aliases = _portfolio_inputs()
    snapshot['exposure_screens'].append({'id': 'unavailable', 'status': 'unavailable'})
    snapshot['exposure_screens'][0]['companies']['unlinked'] = [{'symbol': 'UNMAPPED'}]
    out = _portfolio_project(request, snapshot, aliases)
    assert out['unresolved_channels'] == ['synthetic_screen', 'unavailable']
    assert out['rows'][0]['state'] == 'covered'


def test_portfolio_absent_membership_never_claims_no_exposure():
    request, snapshot, aliases = _portfolio_inputs()
    snapshot['exposure_screens'] = []
    snapshot['company_exposure'].update(status='unavailable', reason='chain_inactive')
    out = _portfolio_project(request, snapshot, aliases)
    assert out['counts']['membership_unavailable'] == 3
    assert out['counts']['not_in_available_screens'] == 0
    assert out['membership_reason'] == 'chain_inactive'


def test_portfolio_alias_source_absent_keeps_every_requested_row_unknown():
    from datetime import date
    from engine.ontology_portfolio import project_portfolio_read
    request, snapshot, _ = _portfolio_inputs()
    out = project_portfolio_read(request, snapshot=snapshot, aliases=None, identity_date=date(2026,10,19))
    assert out['counts']['identity_unresolved'] == 4
    assert len(out['rows']) == 4


@pytest.mark.parametrize('mutation', [
    lambda r: r.update(shares=[100]), lambda r: r.update(symbols=['NEW', 'NEW']),
    lambda r: r.update(symbols=['private secret\n']), lambda r: r.update(symbols=['NEW']*501),
    lambda r: r.update(chain='../../outside'), lambda r: r.update(source_manifest_hash='unknown'),
])
def test_portfolio_private_request_is_closed_and_bounded(mutation):
    from engine.ontology_portfolio import parse_request, PortfolioInputError
    request, _, _ = _portfolio_inputs()
    mutation(request)
    with pytest.raises(PortfolioInputError, match='^invalid_request$'):
        parse_request(json.dumps(request).encode())


def test_portfolio_private_request_rejects_duplicate_keys_and_oversize():
    from engine.ontology_portfolio import parse_request, PortfolioInputError
    for raw in [b'{"symbols":[],"symbols":[]}', b' ' * 65537, b'\xff']:
        with pytest.raises(PortfolioInputError, match='^invalid_request$'):
            parse_request(raw)


def test_portfolio_refuses_changed_selection_instead_of_refreshing_silently():
    from engine.ontology_portfolio import PortfolioInputError
    request, snapshot, aliases = _portfolio_inputs()
    snapshot['source']['source_manifest_hash'] = 'sha256:' + '3' * 64
    with pytest.raises(PortfolioInputError, match='^snapshot_changed$'):
        _portfolio_project(request, snapshot, aliases)


def test_portfolio_wrapper_rechecks_selected_sources_after_projection(tmp_path, monkeypatch):
    from datetime import UTC, datetime
    from engine import ontology_portfolio as portfolio
    from engine import ontology_explorer as explorer
    request, snapshot, _ = _portfolio_inputs()
    owner = tmp_path / 'owner.json'; owner.write_bytes(b'original')
    snapshot['source']['reads'] = [{'path':'owner.json', 'sha256':hashlib.sha256(b'original').hexdigest()}]
    snapshot['company_exposure']['identity_source'] = {'status': 'unavailable', 'sha256': None}
    monkeypatch.setattr(explorer, 'compose_snapshot', lambda *a, **k: snapshot)
    original = portfolio.project_portfolio_read
    def changed(*a, **k):
        out = original(*a, **k); owner.write_bytes(b'changed'); return out
    monkeypatch.setattr(portfolio, 'project_portfolio_read', changed)
    with pytest.raises(explorer.SourceIncoherent, match='selected_source_changed'):
        portfolio.compose_portfolio_read(tmp_path, request, now=datetime(2026,10,19,tzinfo=UTC))


def test_portfolio_composes_real_selected_owner_and_alias_bytes_without_recomputation(tmp_path, monkeypatch):
    from datetime import UTC, datetime
    import pandas as pd
    from engine import ontology_explorer as explorer
    from engine.ontology_portfolio import compose_portfolio_read
    import engine.transmission_chains as owner
    from tests.test_ontology_explorer_contract import _exposure_root
    root=_exposure_root(tmp_path)
    # Preserve synthetic values, but bind the one product chain accepted by this reader.
    import yaml
    definition=yaml.safe_load((root/'knowledge/transmission'/f'{fx.SLUG}.yaml').read_text())
    definition['chain']=explorer.DEFAULT_CHAIN
    state=json.loads((root/'data/transmission/chain_state.json').read_text())
    state['chains'][0]['chain']=explorer.DEFAULT_CHAIN
    root=fx.build_root(root,yaml_doc=definition,state_doc=state,slug=explorer.DEFAULT_CHAIN)
    path=root/'data/reference/vendor_aliases.parquet';path.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame([{'vendor':'store','vendor_symbol':'SYNA','security_id':'SEC:US-XNAS-SYNA',
      'valid_from':None,'valid_to':None}]).to_parquet(path,index=False)
    now=datetime(2026,1,4,tzinfo=UTC)
    snapshot=explorer.compose_snapshot(root,chain=explorer.DEFAULT_CHAIN,now=now)
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    def forbidden(*args,**kwargs):raise AssertionError('cannot recompute owner screen')
    monkeypatch.setattr(owner,'resolve_blast',forbidden)
    out=compose_portfolio_read(root,{'schema':'ontology_portfolio_request.v1','chain':explorer.DEFAULT_CHAIN,
      'source_manifest_hash':snapshot['source']['source_manifest_hash'],'symbols':['SYNA','SYNB']},now=now)
    assert out['rows'][0]['security_id']=='SEC:US-XNAS-SYNA'
    assert out['rows'][0]['channels']==['synthetic_screen']
    assert out['rows'][0]['currency']=='USD'
    assert out['rows'][1]['state']=='identity_unresolved'
    assert out['unresolved_channels']==['synthetic_screen']
    assert out['identity_source_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert out['membership_asof']=='2026-01-02' and out['identity_valid_on']=='2026-01-04'
    assert before=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
