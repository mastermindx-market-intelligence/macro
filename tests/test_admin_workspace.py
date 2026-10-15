"""Behavioral contracts for the shipped, dependency-free admin workspace model."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "admin/static/workspace.js"


def node_assert(code):
    assert MODULE.exists(), "The task-oriented admin workspace module has not been implemented"
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the shipped workspace model")
    prelude = """
const assert = require('node:assert/strict');
const fs = require('node:fs');
const model = require('./admin/static/workspace.js');
const app = fs.readFileSync('./admin/static/app.js', 'utf8');
const a = app.indexOf('const NAV_GROUPS = [');
const b = app.indexOf('const TAB_LABELS = ', a);
const groups = new Function(app.slice(a,b) + ';return NAV_GROUPS;')();
const catalog = model.createCatalog(groups);
"""
    result = subprocess.run([node, "-e", prelude + code], cwd=ROOT,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def test_catalog_reuses_all_54_routes_without_duplicate_identity():
    node_assert("""
assert.equal(catalog.length, 54);
assert.equal(new Set(catalog.map(x => x.id)).size, 54);
assert.equal(catalog.filter(x => x.primary).length, 13);
assert(catalog.every(x => x.label && x.group && x.description));
assert.equal(catalog.find(x => x.id === 'support_tickets').group, 'Customers');
""")


@pytest.mark.parametrize("query,expected", [
    ("customer help", "support_tickets"), ("password", "users"),
    ("scheduled posts", "marketing_outbox"), ("AI COST", "cost"),
    ("release", "deploy"), ("access country", "site_gate"),
    ("  customer   help  ", "support_tickets"),
])
def test_task_search_finds_real_destinations(query, expected):
    import json
    node_assert(f"assert.equal(model.search(catalog, {json.dumps(query)})[0].id, {json.dumps(expected)});")


def test_search_does_not_execute_or_echo_markup_and_has_an_empty_state():
    node_assert("""
assert.deepEqual(model.search(catalog, '<img src=x onerror=alert(1)>'), []);
assert.deepEqual(model.search(catalog, 'zzzz_no_such_page'), []);
assert.equal(model.search(catalog, '').length, 54);
""")


def test_preferences_are_bounded_validated_and_do_not_retain_private_fields():
    node_assert("""
const ids = catalog.map(x => x.id);
const safe = model.sanitizePreferences({version:1, pins:[...ids, 'bogus', '__proto__'],
  recent:['users', 'users', '#/ticket/private-customer', 'overview', 'cost'],
  token:'secret', customer:'private'}, catalog);
assert.equal(safe.pins.length, 8);
assert.deepEqual(safe.recent, ['users', 'cost']);
assert.deepEqual(Object.keys(safe).sort(), ['pins','recent','version']);
assert.deepEqual(model.sanitizePreferences(null, catalog), {version:1,pins:[],recent:[]});
assert.deepEqual(model.sanitizePreferences({version:999,pins:['users']}, catalog).pins, []);
assert.deepEqual(model.sanitizePreferences({version:1,pins:'users',recent:22}, catalog).recent, []);
""")


def test_pin_toggle_and_recent_navigation_are_immutable_and_bounded():
    node_assert("""
const initial = {version:1,pins:[],recent:[]};
const pinned = model.togglePin(initial, 'users', catalog);
assert.deepEqual(initial.pins, []);
assert.deepEqual(pinned.pins, ['users']);
assert.deepEqual(model.togglePin(pinned, 'users', catalog).pins, []);
assert.deepEqual(model.togglePin(initial, 'missing', catalog), initial);
let state = initial;
for (const item of catalog) state = model.visit(state, item.id, catalog);
assert.equal(state.recent.length, 6);
state = model.visit(state, 'users', catalog);
assert.equal(state.recent[0], 'users');
assert.equal(new Set(state.recent).size, state.recent.length);
assert.equal(model.visit(state, '#/ticket/private', catalog).recent[0], 'users');
""")


def test_status_is_an_observation_not_a_freshness_or_health_claim():
    node_assert("""
const now = Date.parse('2026-10-13T04:00:00Z');
assert.equal(model.readState({lastSuccess:0}, now).kind, 'unknown');
assert.equal(model.readState({lastSuccess:now,pending:true}, now).kind, 'loading');
assert.equal(model.readState({lastSuccess:now}, now).kind, 'current');
assert.equal(model.readState({lastSuccess:now-360000}, now).kind, 'old');
const failed = model.readState({lastSuccess:now-10000,error:true}, now);
assert.equal(failed.kind, 'failed');
assert.match(failed.label, /previous snapshot/i);
assert.equal(model.readState({lastSuccess:Infinity}, now).kind, 'unknown');
assert.equal(model.readState({lastSuccess:now+600000}, now).kind, 'unknown');
assert(!model.readState({lastSuccess:now},now).label.toLowerCase().includes('live'));
""")


def test_new_assets_use_the_existing_versioned_public_asset_boundary():
    index = (ROOT / 'admin/static/index.html').read_text()
    server = (ROOT / 'admin/server.py').read_text()
    assert 'src="workspace.js"' in index
    assert 'href="workspace.css"' in index
    assert index.index('src="workspace.js"') < index.index('src="app.js"')
    assert '"workspace.js"' in server and '"workspace.css"' in server
    assert '"/workspace.js"' in server and '"/workspace.css"' in server
    assert 'id="mainContent"' in index and 'class="admin-skip-link"' in index
    assert 'for="pw"' in index and 'aria-live="polite"' in index
