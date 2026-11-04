"""T07 Semiconductor Theme Intelligence B: industrial-view selection tests.

The pure composition module must project caller-supplied native assertions
into the five industrial views WITHOUT ever merging configurations, inheriting
stages, converting units, overwriting a native utilization with a quotient,
double-counting an integrated purchase, or ordering anything by magnitude.
These tests pin the frozen API from carrier PR #7870 (T07).
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace

from engine.theme_graph.curation_assertion import encode_assertion

from tests.semiconductor_research_helpers import load_case, load_bundle_case

VIEW_KEYS = {'composition', 'manufacturing', 'commercial', 'capacity', 'economics'}


def _restamp(payload: dict, **changes) -> dict:
    """Mint a NEW valid stamped assertion from a payload plus top-level edits."""
    body = copy.deepcopy(dict(payload))
    body.update(changes)
    body['curation_revision'] = None
    return json.loads(encode_assertion(body))


def _restamp_deep(payload: dict, **sections) -> dict:
    """Like _restamp but merges sub-sections key-by-key (e.g. source=...)."""
    body = copy.deepcopy(dict(payload))
    for key, section in sections.items():
        merged = dict(body.get(key) or {})
        merged.update(section)
        body[key] = merged
    body['curation_revision'] = None
    return json.loads(encode_assertion(body))


# ─────────────────────────────────────────────────────────────────────────────
# The plan's verbatim test (frozen — do not reword)
# ─────────────────────────────────────────────────────────────────────────────


def test_sample_does_not_inherit_volume_stage_or_global_identity():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    query, bundle = load_bundle_case('hbm_12h_16h')
    result = select_industrial_sections(query, bundle)
    rows = result['industrial_views']['capacity']['rows']
    assert {(x['configuration'], x['stage']) for x in rows} == {('12H', 'reported_shipment'), ('16H', 'sample')}
    assert all('global_product_id' not in x for x in rows)


# ─────────────────────────────────────────────────────────────────────────────
# Per-fixture view regressions
# ─────────────────────────────────────────────────────────────────────────────


def test_hbm_rows_carry_labels_verbatim_and_never_merge_configurations():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    query, bundle = load_bundle_case('hbm_12h_16h')
    result = select_industrial_sections(query, bundle)
    assert set(result['industrial_views'].keys()) == VIEW_KEYS
    rows = result['industrial_views']['capacity']['rows']
    by_config = {row['configuration']: row for row in rows}
    # stage_source_language is copied verbatim from the assertion, never normalized
    assert by_config['12H']['stage'] == 'reported_shipment'
    assert by_config['16H']['stage'] == 'sample'
    assert by_config['12H']['stage_source_language']  # verbatim source wording present
    assert by_config['16H']['stage_source_language']
    # no row for 16H carries the 12H stage or its shipment figure
    assert by_config['16H']['stage_source_language'] != by_config['12H']['stage_source_language']
    assert '12H' not in json.dumps(by_config['16H']['stage_source_language'])


def test_cowos_variants_have_no_summed_capacity_total():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    query, bundle = load_bundle_case('cowos_variants')
    result = select_industrial_sections(query, bundle)
    capacity = result['industrial_views']['capacity']
    rows = capacity['rows']
    assert sorted(row['configuration'] for row in rows) == ['CoWoS-L', 'CoWoS-R', 'CoWoS-S']
    assert 'total' in capacity, 'capacity view must carry an explicit total field'
    assert capacity['total']['value'] is None, 'a summed capacity total must never be minted'
    assert capacity['total']['reason'] == 'mixed_construction_scope'
    # no row converts or combines the scoped constructions
    assert len({row['observation']['unit'] for row in rows}) == 1  # units stay native
    assert all(row['measure_scope']['value_basis'] != 'sum' for row in rows)


def test_abf_material_and_fabricated_substrate_roles_differ():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    query, bundle = load_bundle_case('abf_substrate')
    result = select_industrial_sections(query, bundle)
    rows = result['industrial_views']['composition']['rows']
    kinds = {row['source_business_label']: row['kind'] for row in rows}
    material_rows = [label for label, kind in kinds.items() if kind == 'material']
    product_rows = [label for label, kind in kinds.items() if kind == 'product']
    assert material_rows and product_rows, 'material and fabricated substrate roles must both appear'
    assert set(material_rows).isdisjoint(product_rows), 'a material role may never be conflated with a substrate product role'
    subjects = {row['source_business_label'] for row in rows}
    assert len(subjects) >= 2


def test_mixed_wafer_units_never_converted():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    query, bundle = load_bundle_case('mixed_wafer_units')
    result = select_industrial_sections(query, bundle)
    rows = result['industrial_views']['capacity']['rows']
    units = {row['observation']['unit'] for row in rows}
    diameters = {row['measure_scope']['wafer_diameter_mm'] for row in rows}
    assert units == {'wafer_per_quarter', 'area_kmm2_per_month'}, 'both native units must survive verbatim'
    assert diameters == {200, 300}, 'both native wafer diameters must survive verbatim'
    blob = json.dumps(result)
    assert 'converted' not in blob and 'normalized_unit' not in blob and 'equivalent' not in blob
    # values stay exactly what the sources said
    values = sorted(row['observation']['value'] for row in rows)
    assert values == [96, 148]


def test_umc_native_utilization_never_overwritten_by_quotient():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    query, bundle = load_bundle_case('umc_output_utilization')
    result = select_industrial_sections(query, bundle)
    rows = result['industrial_views']['capacity']['rows']
    util_rows = [row for row in rows if row['utilization']['native_value'] is not None]
    assert util_rows, 'the native output-based utilization figure must be emitted'
    native = util_rows[0]
    assert native['utilization']['native_value'] == 78
    assert native['utilization']['native_unit'] == '%'
    assert native['utilization']['quotient_value'] is None
    assert native['utilization']['quotient_reason'] == 'not_computed'
    # the shipment and capacity figures stay visible as their own native rows…
    non_util = [row for row in rows if row['utilization']['native_value'] is None]
    assert {row['measure_scope']['value_basis'] for row in non_util} >= {'quarterly shipment', 'nameplate capacity'}
    # …and no quotient of them was computed anywhere in the response
    blob = json.dumps(result)
    assert '77.7' not in blob and '77.8' not in blob and '0.777' not in blob


def test_st_target_then_operations_keeps_both_milestone_vintages():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    query, bundle = load_bundle_case('st_target_then_operations')
    result = select_industrial_sections(query, bundle)
    rows = result['industrial_views']['manufacturing']['rows']
    stages = {row['stage'] for row in rows}
    assert stages == {'target', 'reported_operation'}, (
        'the later reported operation advances the milestone while the older target vintage stays visible'
    )
    # the two vintages stay DIFFERENT assertions with different revisions
    assert len({row['curation_revision'] for row in rows}) == 2
    # deterministic order, and no magnitude anywhere in the ordering
    keys = [(row['selector'], row['stage'], row['curation_revision']) for row in rows]
    assert keys == sorted(keys)


def test_jv_physical_count_once_economics_separate():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    query, bundle = load_bundle_case('jv_physical_vs_economics')
    result = select_industrial_sections(query, bundle)
    capacity = result['industrial_views']['capacity']
    facility_rows = [row for row in capacity['rows'] if row['selector'] == 'fac:jv-line']
    assert len(facility_rows) == 1, 'one facility is counted once physically even with two owning parents'
    assert 'facility_counted_once_multi_owner' in capacity['limitations']
    econ_rows = result['industrial_views']['economics']['rows']
    # parent/NCI and captive/external economics stay separate rows
    bases = {row['measure_scope']['value_basis'] for row in econ_rows}
    assert {'jv ownership share', 'jv captive-external revenue split'} <= bases
    assert len(econ_rows) >= 4
    assert len({row['curation_revision'] for row in econ_rows}) == len(econ_rows)


# ─────────────────────────────────────────────────────────────────────────────
# Reciprocal commercial relations
# ─────────────────────────────────────────────────────────────────────────────


def test_reciprocal_commercial_relations_both_shown():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections, ResearchQuery
    query, bundle = load_bundle_case('abf_substrate')
    forward = bundle.assertions[0]
    reciprocal = _restamp_deep(
        forward,
        source={'locator': 'para-4-reciprocal'},
        industrial_context={
            'relation': {
                'src_selector': forward['industrial_context']['relation']['dst_selector'],
                'dst_selector': forward['industrial_context']['relation']['src_selector'],
                'kind': forward['industrial_context']['relation']['kind'],
            }
        },
    )
    assert reciprocal['curation_revision'] != forward['curation_revision']
    b2 = replace(bundle, assertions=(forward, reciprocal))
    result = select_industrial_sections(query, b2)
    edges = result['industrial_views']['commercial']['graph']['edges']
    directions = {(e['src'], e['dst']) for e in edges}
    fwd = forward['industrial_context']['relation']
    assert (fwd['src_selector'], fwd['dst_selector']) in directions
    assert (fwd['dst_selector'], fwd['src_selector']) in directions, (
        'a reciprocal commercial relation must be shown in BOTH directions'
    )
    rows = result['industrial_views']['commercial']['rows']
    assert len(rows) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Purchase boundary
# ─────────────────────────────────────────────────────────────────────────────


def _purchase_boundary_bundle():
    from engine.market_ontology.semiconductor_theme_research import OwnerBundle, ResearchQuery
    case = load_case('integrated_purchase_boundary')
    valid = case['assertions']['valid_assembly']
    double = case['assertions']['double_count']
    query = ResearchQuery(
        anchor_theme_id='theme:semiconductors', slice_key='hbm_packaging', view='economics',
        time_mode='latest', source_cutoff=None, recorded_cutoff=None,
    )
    return query, valid, double


def test_integrated_assembly_purchase_total_refused_with_contained_part():
    from engine.market_ontology.semiconductor_theme_research import OwnerBundle, select_industrial_sections
    query, valid, _ = _purchase_boundary_bundle()
    bundle = OwnerBundle(
        revision_tuple=(('assertion', valid['curation_revision']),),
        rights_revision='synthetic-rights-0',
        assertions=(valid,), identity_results=(), event_workspaces=(),
        financial_packets=(), interpretation_blocks=(), native_refs=(), omissions=(),
    )
    result = select_industrial_sections(query, bundle)
    rows = result['industrial_views']['economics']['rows']
    assert len(rows) == 1
    row = rows[0]
    assert row['measure_scope']['purchase_boundary'] == 'integrated_assembly'
    assert row['purchase_total'] is None, (
        'integrated assembly plus contained parts must refuse the purchase total'
    )
    assert row['purchase_total_reason'] == 'purchase_boundary'


def test_double_count_assertion_is_dropped_as_invalid():
    from engine.market_ontology.semiconductor_theme_research import OwnerBundle, select_industrial_sections
    query, valid, double = _purchase_boundary_bundle()
    bundle = OwnerBundle(
        revision_tuple=(
            ('assertion', valid['curation_revision']),
            ('assertion', double['curation_revision']),
        ),
        rights_revision='synthetic-rights-0',
        assertions=(valid, double), identity_results=(), event_workspaces=(),
        financial_packets=(), interpretation_blocks=(), native_refs=(), omissions=(),
    )
    result = select_industrial_sections(query, bundle)
    assert result['industrial_views']['economics']['rows'], 'the valid assembly row survives'
    assert 'assertion_invalid:1' in result['limitations'], (
        'the double-count assertion is dropped into limitations by bundle index, never raised'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Graph caps
# ─────────────────────────────────────────────────────────────────────────────


def test_graph_nodes_capped_at_forty_with_limitation():
    from engine.market_ontology.semiconductor_theme_research import OwnerBundle, select_industrial_sections
    query, bundle = load_bundle_case('hbm_12h_16h')
    base = bundle.assertions[0]

    def objects_with(prefix: str):
        template = base['industrial_context']['local_objects'][0]
        return [
            {
                'selector': f'{prefix}:{i:03d}',
                'kind': 'process',
                'source_label': f'{prefix} process {i:03d}',
                'manufacturer': template.get('manufacturer'),
                'model': None,
                'configuration': None,
            }
            for i in range(1, 26)
        ]

    ctx_a = dict(base['industrial_context'])
    ctx_a['local_objects'] = objects_with('capa')
    ctx_a['relation'] = None  # the base relation's endpoints are gone from the new object set
    ctx_b = dict(base['industrial_context'])
    ctx_b['local_objects'] = objects_with('capb')
    ctx_b['relation'] = None
    a = _restamp_deep(base, source={'locator': 'para-97'}, industrial_context=ctx_a)
    b = _restamp_deep(base, source={'locator': 'para-98'}, industrial_context=ctx_b)
    b2 = replace(bundle, assertions=(b, a))
    result = select_industrial_sections(query, b2)
    for view in ('manufacturing', 'capacity'):
        graph = result['industrial_views'][view]['graph']
        assert len(graph['nodes']) <= 40
        assert len(graph['nodes']) == 40, '50 eligible nodes must cap at exactly 40'
        assert 'graph_truncated' in result['industrial_views'][view]['limitations']
    assert 'graph_truncated' in result['limitations']
    assert all(edge['width'] is None for view in VIEW_KEYS
               for edge in result['industrial_views'][view]['graph']['edges'])


# ─────────────────────────────────────────────────────────────────────────────
# No-magnitude ordering — bundle input order must not matter
# ─────────────────────────────────────────────────────────────────────────────


def test_shuffled_bundle_input_order_produces_identical_output():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    for name in ('cowos_variants', 'jv_physical_vs_economics', 'hbm_12h_16h'):
        query, bundle = load_bundle_case(name)
        straight = select_industrial_sections(query, bundle)
        shuffled = select_industrial_sections(
            query,
            replace(
                bundle,
                assertions=tuple(reversed(bundle.assertions)),
                identity_results=tuple(reversed(bundle.identity_results)),
                event_workspaces=tuple(reversed(bundle.event_workspaces)),
                financial_packets=tuple(reversed(bundle.financial_packets)),
                interpretation_blocks=tuple(reversed(bundle.interpretation_blocks)),
                native_refs=tuple(reversed(bundle.native_refs)),
            ),
        )
        assert json.dumps(shuffled, sort_keys=True) == json.dumps(straight, sort_keys=True), (
            f'{name}: reversing the bundle input order changed the output — ordering must be '
            f'deterministic over (selector)/(label)/(curation_revision), never input order or magnitude'
        )


def test_capacity_rows_ordered_by_selector_not_by_value():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    query, bundle = load_bundle_case('cowos_variants')
    result = select_industrial_sections(query, bundle)
    rows = result['industrial_views']['capacity']['rows']
    keys = [(row['selector'] or '', row['configuration'] or '', row['curation_revision']) for row in rows]
    assert keys == sorted(keys)
    # the emitted order IS the key order — and it is proven not to be the
    # magnitude order whenever the two differ for this corpus
    by_key = [row['curation_revision'] for row in sorted(
        rows, key=lambda r: (r['selector'] or '', r['configuration'] or '', r['curation_revision']))]
    by_value = [row['curation_revision'] for row in sorted(
        rows, key=lambda r: (r['observation']['value'] is None, r['observation']['value'] or 0))]
    emitted = [row['curation_revision'] for row in rows]
    assert emitted == by_key
    if by_value != by_key:
        assert emitted != by_value and emitted != list(reversed(by_value))


def _capacity_member(bundle):
    """The first assertion that renders into the capacity view, plus its row."""
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    query, _ = load_bundle_case('mixed_wafer_units')
    view = select_industrial_sections(query, bundle)['industrial_views']['capacity']
    row = view['rows'][0]
    member = next(a for a in bundle.assertions if a['curation_revision'] == row['curation_revision'])
    return query, member, row


def test_a_second_distinct_measurement_on_one_facility_is_kept_not_deleted():
    """Two measures are two rows: a different observation on the same
    facility+stage is never merged, never chosen by hash, and the view is
    marked `multiple_measures_same_facility` (not the multi-owner label)."""
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    _, bundle = load_bundle_case('mixed_wafer_units')
    query, member, row = _capacity_member(bundle)
    observation = dict(member['observation'])
    observation.update({'value': 148, 'unit': 'area_kmm2_per_month'})
    other_measure = _restamp(member, observation=observation)
    assert other_measure['curation_revision'] != member['curation_revision']
    bundle2 = replace(bundle, assertions=list(bundle.assertions) + [other_measure])
    view = select_industrial_sections(query, bundle2)['industrial_views']['capacity']
    same_facility = [r for r in view['rows'] if r['selector'] == row['selector'] and r['stage'] == row['stage']]
    assert len(same_facility) == len([r for r in select_industrial_sections(query, bundle)['industrial_views']['capacity']['rows']
                                      if r['selector'] == row['selector'] and r['stage'] == row['stage']]) + 1
    assert {r['observation']['unit'] for r in same_facility} >= {observation['unit'], member['observation']['unit']}
    assert 'multiple_measures_same_facility' in view['limitations']
    assert 'facility_counted_once_multi_owner' not in view['limitations']
    assert view['status'] == 'degraded'
    # coverage and evidence still count every selected assertion; nothing vanished
    composed_refs = view['input_refs']
    assert other_measure['curation_revision'] in composed_refs


def test_an_exact_duplicate_measurement_on_one_facility_is_counted_once():
    """The JV / multi-owner shape: the SAME observation and measure_scope
    restated by a second assertion (different locator, hence a different
    revision) is one physical line — counted once, labelled honestly."""
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    _, bundle = load_bundle_case('mixed_wafer_units')
    query, member, row = _capacity_member(bundle)
    restated = _restamp_deep(member, source={'locator': (member['source'].get('locator') or 'p') + ' (restated)'})
    assert restated['curation_revision'] != member['curation_revision']
    bundle2 = replace(bundle, assertions=list(bundle.assertions) + [restated])
    before = select_industrial_sections(query, bundle)['industrial_views']['capacity']
    view = select_industrial_sections(query, bundle2)['industrial_views']['capacity']
    assert len(view['rows']) == len(before['rows'])
    assert 'facility_counted_once_multi_owner' in view['limitations']
    assert 'multiple_measures_same_facility' not in view['limitations']


def _with_primary_object(member: dict, **fields) -> dict:
    """Re-mint `member` with fields set on its primary local object (WHAT is measured)."""
    body = copy.deepcopy(member)
    body['industrial_context']['local_objects'][0].update(fields)
    body['curation_revision'] = None
    return json.loads(encode_assertion(body))


def _same_facility(view: dict, row: dict) -> list[dict]:
    return [r for r in view['rows'] if r['selector'] == row['selector'] and r['stage'] == row['stage']]


def test_two_configurations_with_one_observation_are_two_rows_never_a_multi_owner_collapse():
    """12H and 16H on the same facility+stage carrying the SAME observation and
    measure_scope are two constructions: both rows stay, neither is chosen by
    revision hash, and the multi-owner label is never claimed."""
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    _, bundle = load_bundle_case('mixed_wafer_units')
    query, member, row = _capacity_member(bundle)
    twelve = _with_primary_object(member, configuration='12H')
    sixteen = _with_primary_object(member, configuration='16H')
    assert twelve['observation'] == sixteen['observation']
    others = [a for a in bundle.assertions if a['curation_revision'] != member['curation_revision']]
    for order in ([twelve, sixteen], [sixteen, twelve]):
        view = select_industrial_sections(query, replace(bundle, assertions=others + order))['industrial_views']['capacity']
        assert {r['configuration'] for r in _same_facility(view, row)} >= {'12H', '16H'}
        assert 'multiple_measures_same_facility' in view['limitations']
        assert 'facility_counted_once_multi_owner' not in view['limitations']
        assert view['total'] == {'value': None, 'reason': 'mixed_construction_scope'}


def test_a_model_only_difference_on_one_facility_keeps_both_rows():
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    _, bundle = load_bundle_case('mixed_wafer_units')
    query, member, row = _capacity_member(bundle)
    line_b = _with_primary_object(member, model='LINE-B')
    view = select_industrial_sections(query, replace(bundle, assertions=list(bundle.assertions) + [line_b]))['industrial_views']['capacity']
    assert {r['model'] for r in _same_facility(view, row)} >= {row['model'], 'LINE-B'}
    assert 'multiple_measures_same_facility' in view['limitations']
    assert 'facility_counted_once_multi_owner' not in view['limitations']


def test_a_lone_scoped_row_among_unscoped_rows_still_raises_mixed_construction_scope():
    """A deleted distinct row must never silence the mixed-scope hazard: one
    configured construction next to unscoped rows keeps the total refused."""
    from engine.market_ontology.semiconductor_theme_research import select_industrial_sections
    _, bundle = load_bundle_case('mixed_wafer_units')
    query, member, row = _capacity_member(bundle)
    scoped = _with_primary_object(member, configuration='CFG-Z')
    view = select_industrial_sections(query, replace(bundle, assertions=list(bundle.assertions) + [scoped]))['industrial_views']['capacity']
    assert any(r['configuration'] == 'CFG-Z' for r in _same_facility(view, row))
    assert view['total'] == {'value': None, 'reason': 'mixed_construction_scope'}
    assert 'mixed_construction_scope' in view['limitations']
    assert view['status'] == 'degraded'
