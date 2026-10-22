"""Host-scope view seam is reversible, inert and correctly account-isolated."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.research.market_navigator_view_browser_check import synthetic_wire

ROOT=Path(__file__).resolve().parents[1]


def test_browserless_host_account_and_instrument_switch():
    run=subprocess.run(['node','tests/market_navigator_mount_harness.js'],
                       cwd=ROOT,input=json.dumps(synthetic_wire()),
                       text=True,capture_output=True,timeout=25)
    assert run.returncode==0,run.stderr
    report=json.loads(run.stdout)
    assert report['passed'] and report['stale_scope_refused']
    assert report['cross_subject_refused'] and report['midflight_switch_withdrawn']
    assert report['auto_reads']==0


def test_mount_contains_no_implicit_network_auth_or_storage():
    source=(ROOT/'templates/market_navigator_mount.js').read_text()
    for forbidden in ('fetch(', 'localStorage','sessionStorage','XMLHttpRequest',
                      'document.cookie','WebSocket(','.innerHTML','setInterval('):
        assert forbidden not in source
    for path in ('templates/market_navigator_mount.js',
                 'tests/market_navigator_mount_harness.js'):
        subprocess.run(['node','--check',path],cwd=ROOT,check=True,
                       timeout=10,capture_output=True)
