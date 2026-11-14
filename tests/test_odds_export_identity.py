"""Native Odds Desk export identity under deferred fetch/logo completion.

The fixture evaluates the real client IIFE; only boot and unrelated painting
are replaced. DOM/canvas/network/timers are deterministic fakes, not browser
or live-provider acceptance. Requires Node.js.
"""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('case', [
    'pending switch clears path',
    'pending switch clears histogram',
    'pending switch clears strip',
    'pending switch clears path note',
    'pending ticker clears prior evidence',
    'latest response wins',
    'failed response stays unavailable',
    'share cancelled after ticker change',
    'share cancelled after horizon change',
    'share cancelled after stats change',
    'unchanged share downloads once',
    'unchanged CSV exports original ticker',
])
def test_odds_export_identity(case):
    result = subprocess.run(
        ['node', str(ROOT/'tests/fixtures/odds_export_identity.cjs'),
         str(ROOT/'site/odds.js'), case],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS ' + case in result.stdout
