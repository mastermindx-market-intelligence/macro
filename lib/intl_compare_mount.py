"""Attach detached Compare catalogues to the existing rendered workspace."""
from copy import deepcopy
import re

from lib.intl_compare_view import build_compare_catalogue
from lib.intl_workspace_binding import binding_version, panel_generation


_CONTEXT = ('horizon', 'currency_basis', 'return_basis', 'source_reference')
_BASES = ('local', 'usd_unhedged')
_MARKET = re.compile(r'[A-Za-z][A-Za-z0-9_:-]*')


def _fail():
    raise ValueError('invalid_compare_workspace')


def _text(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value:
        _fail()


def _validate_config(config):
    required = {
        'markets', 'horizons', 'bases', 'default_horizon', 'default_basis',
        'source_reference', 'anchor_ids', 'library_group_ids',
    }
    if type(config) is not dict or not required.issubset(config):
        _fail()
    for key in ('markets', 'horizons', 'bases'):
        values = config[key]
        if type(values) is not list or not values:
            _fail()
        if any(type(value) is not str or not value for value in values):
            _fail()
        if len(values) != len(set(values)):
            _fail()
    if config['default_horizon'] not in config['horizons']:
        _fail()
    if config['default_basis'] not in config['bases']:
        _fail()
    if any(basis not in _BASES for basis in (*config['bases'], config['default_basis'])):
        _fail()
    _text(config['source_reference'], nullable=True)
    for key in ('anchor_ids', 'library_group_ids'):
        values = config[key]
        if type(values) is not list or any(type(value) is not str for value in values):
            _fail()


def _validate_panel(panel, config, contexts, tuples, version, generation):
    if type(panel) is not dict or not {'context_id', 'overview'}.issubset(panel):
        _fail()
    context_id = panel['context_id']
    if (type(context_id) is not str or _MARKET.fullmatch(context_id) is None
            or context_id in contexts):
        _fail()
    contexts.add(context_id)
    overview = panel['overview']
    try:
        catalogue = build_compare_catalogue(overview)
    except ValueError as error:
        raise ValueError('invalid_compare_workspace') from error
    context = overview.get('context') if type(overview) is dict else None
    if type(context) is not dict or set(context) != {*_CONTEXT, 'source_reference_reason'}:
        _fail()
    if context['horizon'] not in config['horizons']:
        _fail()
    if context['currency_basis'] not in config['bases']:
        _fail()
    if context['return_basis'] != 'price':
        _fail()
    if version == 1 and context['source_reference'] != config['source_reference']:
        _fail()
    panel_generation(panel, generation) if version == 2 else None
    binding = tuple(context[key] for key in _CONTEXT)
    if binding in tuples:
        _fail()
    tuples.add(binding)
    rows = overview.get('rows', ())
    if type(rows) is not list:
        _fail()
    by_slot = {row.get('slot'): row for row in rows}
    if set(by_slot) != set(range(len(config['markets']))):
        _fail()
    for slot, market in enumerate(config['markets']):
        row = by_slot[slot]
        if type(row) is not dict or row.get('slot') != slot:
            _fail()
        if row.get('quality') != 'denied' and row.get('market_id') != market:
            _fail()

    return catalogue


def attach_compares(workspace):
    """Publish detached Compare catalogues while preserving the owner workspace."""
    if workspace is None:
        return None
    if type(workspace) is not dict or not {'config', 'panels'}.issubset(workspace):
        _fail()
    _validate_config(workspace['config'])
    version, generation = binding_version(workspace)
    panels = workspace['panels']
    if type(panels) is not list:
        _fail()
    contexts, tuples = set(), set()
    catalogues = [_validate_panel(panel, workspace['config'], contexts, tuples, version, generation)
                  for panel in panels]
    result = deepcopy(workspace)
    result['compares'] = [{
        'context_id': panel['context_id'],
        'compare_catalogue': catalogue,
        **({'generation': panel['generation']} if version == 2 else {}),
    } for panel, catalogue in zip(panels, catalogues, strict=True)]
    return result
