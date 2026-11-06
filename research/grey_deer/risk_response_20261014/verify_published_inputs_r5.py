"""Read-only candidate composition against the now-published October 14 inputs.

No production builder, market-data writer, episode ledger or forecast fitter is
called. The result compares the recorded main artifact with candidate composition
in memory and renders the real foreground macro. This is a source-to-render
integration diagnostic, not an issued historical alert or production deployment.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
SOURCE = 'c95766ce92a2ffe75f45d464110c9c7534bd409d'


def main() -> int:
    from engine.risk_envelope import compose_envelope
    from scripts.build_risk_envelope import build_sources
    from tests.test_macro_risk_dialog import _vm
    from tests.test_dashboard_template_render import _env
    import re
    from tests.test_risk_envelope_radar_integration import _foreground_fragment

    docs = {}
    refs = {}
    for name in ('market_state', 'leadership_crack', 'risk_envelope'):
        path = f'data/{name}/latest.json'
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', SOURCE + ':' + path], timeout=30)
        docs[name] = json.loads(raw)
        refs[path] = hashlib.sha256(raw).hexdigest()
    before = deepcopy(docs)
    measured = docs['market_state']
    leadership = docs['leadership_crack']
    session = measured['asof']
    assert session == leadership['asof'] == '2026-10-14'
    assert leadership['state'] == 'CRACKING'
    observed = datetime.now(timezone.utc).isoformat()
    candidate = compose_envelope(
        sources=build_sources(measured, leadership, session), market='US',
        source_session=session, observed_at=observed, produced_at=observed, as_of=session,
    )
    assert candidate['measured_state']['score'] == measured['score'] == 44
    assert candidate['hazard_summary']['stage'] == 'FRAGILE'
    assert candidate['authority']['envelope_may_gate'] is False
    assert candidate['authority']['envelope_may_size'] is False
    vm = _vm(risk_envelope=candidate)
    vm['market_state'] = measured
    environment = _env()
    # The compact test environment omits this production filter; real populated
    # native flip-copy exercises it. Match scripts/build_site.py:6099 exactly.
    environment.filters['regex_replace'] = lambda value, pattern, repl: re.sub(pattern, repl, value) if isinstance(value, str) else value
    html = environment.get_template('dashboard.html.j2').render(**vm, mode='macro')
    foreground = _foreground_fragment(html)
    assert 'data-state="warning"' in foreground
    assert 'AI-hardware leaders: weakening' in foreground
    assert '2026-10-14' in foreground
    assert docs == before
    result = {
        'kind': 'published_inputs_candidate_composition', 'source_commit': SOURCE,
        'observation_mode': 'read_only_reconstruction_at_current_read_time',
        'observed_at': observed, 'source_sha256': refs,
        'published_leadership': {'asof': leadership['asof'], 'state': leadership['state']},
        'published_envelope': docs['risk_envelope']['hazard_summary'],
        'candidate_envelope': candidate['hazard_summary'],
        'measured_score': measured['score'], 'measured_verdict': measured['verdict'],
        'foreground_contains_native_warning': True, 'source_session': session,
        'input_documents_unchanged': True, 'production': False,
        'historically_issued_alert': False, 'new_forecast_or_sizing_authority': False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
