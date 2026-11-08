"""Actual full Intl Jinja with the accepted controlled History input.

No acquisition, engine execution, current materialization or rights attestation.
The original test input is explicit fixture data; the real mount and full-page
renderer provide controls, state, and normal source-owned page composition.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from engine.intl_workspace_overview import build_workspace_overviews
from lib.intl_history_mount import attach_history
from lib.intl_library_mount import render_international_pages
from tests.intl_gs_fixture_site import _env, _vm
from tests.test_intl_history_mount import GENERATION, fixture

ROOT = Path(__file__).resolve().parents[1]


def build_fixture():
    vm = _vm()
    workspace = build_workspace_overviews(None, workspace_generation=GENERATION)
    cfg = workspace['config']
    _, args = fixture()
    source = deepcopy(args['sources']['JP'])
    # The original source input includes unrelated synthetic event/track examples.
    # This journey exercises only the finite History output contract.
    source['turn_events'] = []
    source['track_record'] = None
    source['destinations'] = {}
    for key in ('events', 'track_record'):
        source['capabilities'][key] = dict(metadata='unknown', value='unknown')
    registry = dict(markets=[dict(market_id=m, name_en=m, name_zh=m) for m in cfg['markets']],
                    horizons=cfg['horizons'], bases=cfg['bases'])
    workspace = attach_history(workspace, registry=registry, sources={'JP': source})
    vm['intl_workspace'] = workspace
    catalogue = json.loads((ROOT / 'config/intl_library_catalogue.json').read_text())
    html, _ = render_international_pages(_env().get_template('intl.html.j2'), vm,
                                         catalogue=catalogue)
    section = workspace['histories'][0]['sections'][0]
    assert section['snapshot_compare']['selection']['eligible']
    assert len(section['points']) >= 2
    fixture_path = ROOT / 'tests/fixtures/intl_workspace/history_cases.json'
    return dict(
        schema='shared_shell.history.next_fixture.v1',
        scope='controlled full-Jinja consumer input; not current native receipt or execution',
        html=html, html_sha256=sha256(html.encode()).hexdigest(),
        generation=GENERATION, config=cfg,
        expected=dict(market='JP', points=section['points'],
                      initial_dates=['', ''], scenario_initial=['', '']),
        source_fixture=dict(path=str(fixture_path.relative_to(ROOT)),
                            sha256=sha256(fixture_path.read_bytes()).hexdigest()))


if __name__ == '__main__':
    print(json.dumps(build_fixture()))
