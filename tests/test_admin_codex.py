"""tests/test_admin_codex.py — Hermetic tests for admin/codex_panel.py.

Coverage:
  panel() shape with monkeypatched github_api + tmp data files
  usage_state variants: reported, degraded, paused
  validate_mode_body() — good/bad mode, interval bounds, lane vocab
  validate_run_body() — good/bad lane, iterations bounds
  server imports OK (compile check only, no port binding)
"""
from __future__ import annotations

import json
import sys
import types
import unittest.mock as mock
from pathlib import Path

import pytest

# Ensure repo root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _cp():
    """Import codex_panel freshly."""
    import admin.codex_panel as cp  # noqa: PLC0415
    return cp


def _mock_gh_vars(cp, *, mode=None, interval=None, lanes=None):
    """Patch get_repo_variable to return canned values per variable name."""
    _map = {
        "CODEX_MODE": mode,
        "CODEX_INTERVAL_HOURS": interval,
        "CODEX_LANES": lanes,
    }

    def fake_get(name):
        return _map.get(name)

    return mock.patch.object(cp.github_api, "get_repo_variable", side_effect=fake_get)


def _mock_runs(cp, runs=None):
    """Patch list_runs to return a canned set of runs."""
    runs = runs or []
    return mock.patch.object(
        cp.github_api, "list_runs",
        return_value={"ok": True, "runs": runs},
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _write_usage(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. panel() shape — basic
# ---------------------------------------------------------------------------

class TestPanelShape:
    """panel() always returns the required keys and never raises."""

    def test_returns_dict(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp), _mock_runs(cp):
            result = cp.panel()
        assert isinstance(result, dict)

    def test_required_keys(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp), _mock_runs(cp):
            result = cp.panel()
        assert "mode" in result
        assert "interval_hours" in result
        assert "lanes" in result
        assert "usage" in result
        assert "attempts" in result
        assert "loop" in result
        assert "runs" in result

    def test_mode_subkeys(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp), _mock_runs(cp):
            result = cp.panel()
        m = result["mode"]
        assert "value" in m
        assert "effective" in m
        assert "allowed" in m

    def test_absent_mode_effective_off(self, tmp_path):
        """CODEX_MODE absent (None) → effective must be 'off' (CRX-R7 fail-closed)."""
        cp = _cp()
        with _mock_gh_vars(cp, mode=None), _mock_runs(cp):
            result = cp.panel()
        assert result["mode"]["effective"] == "off"

    def test_set_mode_propagates(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp, mode="auto"), _mock_runs(cp):
            result = cp.panel()
        assert result["mode"]["value"] == "auto"
        assert result["mode"]["effective"] == "auto"

    def test_invalid_mode_effective_off(self, tmp_path):
        """Unrecognized CODEX_MODE value → effective falls back to 'off'."""
        cp = _cp()
        with _mock_gh_vars(cp, mode="banana"), _mock_runs(cp):
            result = cp.panel()
        assert result["mode"]["effective"] == "off"

    def test_interval_default(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp, interval=None), _mock_runs(cp):
            result = cp.panel()
        assert result["interval_hours"]["effective"] == 6

    def test_interval_set(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp, interval="12"), _mock_runs(cp):
            result = cp.panel()
        assert result["interval_hours"]["effective"] == 12

    def test_lanes_default(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp, lanes=None), _mock_runs(cp):
            result = cp.panel()
        assert result["lanes"]["effective"] == "both"

    def test_lanes_set(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp, lanes="cases"), _mock_runs(cp):
            result = cp.panel()
        assert result["lanes"]["effective"] == "cases"

    def test_usage_none_when_no_file(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp), _mock_runs(cp):
            # Point _CODEX_LANE_DIR to empty tmp_path so no usage_state.json exists
            with mock.patch.object(cp, "_CODEX_LANE_DIR", tmp_path):
                result = cp.panel()
        assert result["usage"] is None

    def test_attempts_empty_when_no_file(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp), _mock_runs(cp):
            with mock.patch.object(cp, "_CODEX_LANE_DIR", tmp_path):
                result = cp.panel()
        assert result["attempts"] == []

    def test_loop_empty_when_no_file(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp), _mock_runs(cp):
            with mock.patch.object(cp, "_CODEX_LANE_DIR", tmp_path):
                result = cp.panel()
        assert result["loop"] == []


# ---------------------------------------------------------------------------
# 2. panel() with usage_state variants
# ---------------------------------------------------------------------------

class TestUsageState:
    """Usage state derived fields: reported, degraded, paused."""

    def _panel_with_usage(self, tmp_path, usage_data):
        cp = _cp()
        _write_usage(tmp_path / "usage_state.json", usage_data)
        with _mock_gh_vars(cp), _mock_runs(cp):
            with mock.patch.object(cp, "_CODEX_LANE_DIR", tmp_path):
                return cp.panel()

    def test_reported_pct_propagates(self, tmp_path):
        result = self._panel_with_usage(tmp_path, {
            "rate_limits": {
                "primary": {"used_percent": 42.5, "resets_at": None},
                "secondary": {"used_percent": 30.0, "resets_at": None},
            }
        })
        u = result["usage"]
        assert u is not None
        assert u["primary_used_pct"] == pytest.approx(42.5)
        assert u["secondary_used_pct"] == pytest.approx(30.0)
        assert u["degraded"] is False

    def test_degraded_when_no_pct(self, tmp_path):
        """No used_percent fields → degraded = True."""
        result = self._panel_with_usage(tmp_path, {"sessions_in_window": 3})
        u = result["usage"]
        assert u is not None
        assert u["degraded"] is True
        assert u["primary_used_pct"] is None
        assert u["secondary_used_pct"] is None

    def test_paused_until_propagates(self, tmp_path):
        paused = "2026-07-14T06:00:00Z"
        result = self._panel_with_usage(tmp_path, {"paused_until": paused})
        u = result["usage"]
        assert u is not None
        assert u["paused_until"] == paused

    def test_paused_until_none_when_absent(self, tmp_path):
        result = self._panel_with_usage(tmp_path, {
            "rate_limits": {"primary": {"used_percent": 10.0}}
        })
        u = result["usage"]
        assert u["paused_until"] is None

    def test_budget_pct_from_defaults(self, tmp_path):
        result = self._panel_with_usage(tmp_path, {})
        u = result["usage"]
        assert u is not None
        assert u["budget_pct"] == 85

    def test_usage_dict_passthrough(self, tmp_path):
        """Arbitrary keys in usage_state.json pass through to the panel."""
        result = self._panel_with_usage(tmp_path, {
            "sessions_in_window": 7,
            "last_run_ts": "2026-07-13T12:00:00Z",
        })
        u = result["usage"]
        assert u["sessions_in_window"] == 7
        assert u["last_run_ts"] == "2026-07-13T12:00:00Z"


# ---------------------------------------------------------------------------
# 3. panel() — data file tails
# ---------------------------------------------------------------------------

class TestDataFileTails:
    def test_attempts_last_10(self, tmp_path):
        cp = _cp()
        rows = [{"episode": f"AAPL_{2000+i}", "status": "pr_opened"} for i in range(15)]
        _write_jsonl(tmp_path / "case_attempts.jsonl", rows)
        with _mock_gh_vars(cp), _mock_runs(cp):
            with mock.patch.object(cp, "_CODEX_LANE_DIR", tmp_path):
                result = cp.panel()
        assert len(result["attempts"]) == 10
        # Last 10 rows = indices 5..14
        assert result["attempts"][0]["episode"] == "AAPL_2005"
        assert result["attempts"][-1]["episode"] == "AAPL_2014"

    def test_loop_last_5(self, tmp_path):
        cp = _cp()
        rows = [{"ts": f"2026-07-13T{10+i:02d}:00:00Z", "action": f"iter_{i}"} for i in range(8)]
        _write_jsonl(tmp_path / "loop_journal.jsonl", rows)
        with _mock_gh_vars(cp), _mock_runs(cp):
            with mock.patch.object(cp, "_CODEX_LANE_DIR", tmp_path):
                result = cp.panel()
        assert len(result["loop"]) == 5
        assert result["loop"][-1]["action"] == "iter_7"

    def test_attempts_fewer_than_10(self, tmp_path):
        cp = _cp()
        rows = [{"episode": "TSLA_2024", "status": "generated"}]
        _write_jsonl(tmp_path / "case_attempts.jsonl", rows)
        with _mock_gh_vars(cp), _mock_runs(cp):
            with mock.patch.object(cp, "_CODEX_LANE_DIR", tmp_path):
                result = cp.panel()
        assert len(result["attempts"]) == 1


# ---------------------------------------------------------------------------
# 4. panel() — workflow runs filter
# ---------------------------------------------------------------------------

class TestRunsFilter:
    def test_codex_run_included(self, tmp_path):
        cp = _cp()
        runs_data = [
            {"id": 1, "name": "Codex Research", "workflow": "codex-research.yml",
             "status": "completed", "conclusion": "success", "created_at": "2026-07-13T10:00:00Z",
             "html_url": "https://github.com/example/actions/runs/1"},
            {"id": 2, "name": "Daily Build", "workflow": "daily.yml",
             "status": "completed", "conclusion": "success", "created_at": "2026-07-13T09:00:00Z",
             "html_url": "https://github.com/example/actions/runs/2"},
        ]
        with _mock_gh_vars(cp), _mock_runs(cp, runs=runs_data):
            with mock.patch.object(cp, "_CODEX_LANE_DIR", tmp_path):
                result = cp.panel()
        # Only the codex-research run should appear
        assert len(result["runs"]) == 1
        assert result["runs"][0]["id"] == 1

    def test_runs_empty_when_list_runs_fails(self, tmp_path):
        cp = _cp()
        with _mock_gh_vars(cp):
            with mock.patch.object(cp.github_api, "list_runs", return_value={"ok": False, "runs": []}):
                with mock.patch.object(cp, "_CODEX_LANE_DIR", tmp_path):
                    result = cp.panel()
        assert result["runs"] == []


# ---------------------------------------------------------------------------
# 5. validate_mode_body() — pure function tests
# ---------------------------------------------------------------------------

class TestValidateModeBody:
    def test_valid_mode_off(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"mode": "off", "confirm": True})
        assert ok is True
        assert errors == {}
        assert to_set == {"CODEX_MODE": "off"}

    def test_valid_mode_auto(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"mode": "auto", "confirm": True})
        assert ok is True
        assert to_set["CODEX_MODE"] == "auto"

    def test_valid_mode_interval(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"mode": "interval", "confirm": True})
        assert ok is True
        assert to_set["CODEX_MODE"] == "interval"

    def test_invalid_mode(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"mode": "banana", "confirm": True})
        assert ok is False
        assert "mode" in errors
        assert to_set == {}

    def test_interval_valid_min(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"interval_hours": 1})
        assert ok is True
        assert to_set["CODEX_INTERVAL_HOURS"] == "1"

    def test_interval_valid_max(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"interval_hours": 48})
        assert ok is True
        assert to_set["CODEX_INTERVAL_HOURS"] == "48"

    def test_interval_too_low(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"interval_hours": 0})
        assert ok is False
        assert "interval_hours" in errors

    def test_interval_too_high(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"interval_hours": 49})
        assert ok is False
        assert "interval_hours" in errors

    def test_interval_non_integer(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"interval_hours": "foo"})
        assert ok is False
        assert "interval_hours" in errors

    def test_valid_lanes_cases(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"lanes": "cases"})
        assert ok is True
        assert to_set["CODEX_LANES"] == "cases"

    def test_valid_lanes_signals(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"lanes": "signals"})
        assert ok is True

    def test_valid_lanes_both(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"lanes": "both"})
        assert ok is True

    def test_invalid_lanes(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"lanes": "everything"})
        assert ok is False
        assert "lanes" in errors

    def test_empty_body(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({})
        assert ok is True
        assert to_set == {}

    def test_multiple_fields_combined(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"mode": "interval", "interval_hours": 12, "lanes": "signals"})
        assert ok is True
        assert to_set["CODEX_MODE"] == "interval"
        assert to_set["CODEX_INTERVAL_HOURS"] == "12"
        assert to_set["CODEX_LANES"] == "signals"

    def test_mixed_valid_invalid(self):
        cp = _cp()
        ok, errors, to_set = cp.validate_mode_body({"mode": "auto", "interval_hours": 100})
        assert ok is False
        assert "interval_hours" in errors
        # mode was valid but we still reject when any field fails
        assert "mode" not in errors


# ---------------------------------------------------------------------------
# 6. validate_run_body() — pure function tests
# ---------------------------------------------------------------------------

class TestValidateRunBody:
    def test_valid_lane_cases(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "cases", "confirm": True})
        assert ok is True
        assert error is None
        assert inputs["lane"] == "cases"

    def test_valid_lane_signals(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "signals"})
        assert ok is True
        assert inputs["lane"] == "signals"

    def test_valid_lane_both(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "both"})
        assert ok is True
        assert inputs["lane"] == "both"

    def test_invalid_lane(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "everything"})
        assert ok is False
        assert error is not None
        assert inputs == {}

    def test_missing_lane(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({})
        assert ok is False
        assert error is not None

    def test_iterations_valid_1(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "both", "iterations": 1})
        assert ok is True
        assert inputs["iterations"] == "1"

    def test_iterations_valid_20(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "both", "iterations": 20})
        assert ok is True
        assert inputs["iterations"] == "20"

    def test_iterations_too_low(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "both", "iterations": 0})
        assert ok is False
        assert error is not None

    def test_iterations_too_high(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "both", "iterations": 21})
        assert ok is False
        assert error is not None

    def test_iterations_non_integer(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "both", "iterations": "many"})
        assert ok is False
        assert error is not None

    def test_no_iterations_key_omitted_from_inputs(self):
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "cases"})
        assert ok is True
        assert "iterations" not in inputs

    def test_iterations_as_string_integer(self):
        """iterations may arrive as string from HTML form submission."""
        cp = _cp()
        ok, error, inputs = cp.validate_run_body({"lane": "both", "iterations": "5"})
        assert ok is True
        assert inputs["iterations"] == "5"


# ---------------------------------------------------------------------------
# 7. Import smoke test — server.py and codex_panel are importable together
# ---------------------------------------------------------------------------

class TestImports:
    def test_codex_panel_importable(self):
        cp = _cp()
        assert hasattr(cp, "panel")
        assert hasattr(cp, "validate_mode_body")
        assert hasattr(cp, "validate_run_body")

    def test_server_imports_codex_panel(self):
        """Verify server.py imports codex_panel without error."""
        import admin.server as srv  # noqa: PLC0415
        import admin.codex_panel as cp  # noqa: PLC0415
        assert srv.codex_panel is cp

    def test_panel_never_raises(self):
        """panel() must not raise even when github_api throws."""
        cp = _cp()
        with mock.patch.object(cp.github_api, "get_repo_variable", side_effect=RuntimeError("boom")):
            with mock.patch.object(cp.github_api, "list_runs", side_effect=RuntimeError("boom")):
                result = cp.panel()
        assert isinstance(result, dict)
        assert result["mode"]["effective"] == "off"


class TestCodexUsageRenderer:
    """Exercise the shipped Codex renderer, not a parallel HTML implementation."""

    def render(self, raw, now=1791014400000):
        import shutil
        import subprocess
        node = shutil.which("node")
        assert node, "Node is required to execute the actual admin renderer"
        js = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const source = fs.readFileSync(process.argv[1], 'utf8');
const begin = source.indexOf('RENDER.codex = async () => {');
const end = source.indexOf('/* ---- boot ', begin);
if (begin < 0 || end < 0) throw Error('Codex renderer boundary not found');
const view = {innerHTML: '', querySelectorAll: () => []};
class FixedDate extends Date { static now() { return input.now; } }
let reads = 0;
const context = {
  RENDER: {}, Date: FixedDate,
  $: (selector) => selector === '#view' ? view : null,
  api: async (path) => { if (path !== '/api/codex') throw Error('unexpected read'); reads++; return {usage: input.usage}; },
  esc: (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
  post: () => { throw Error('unexpected modifying request'); },
};
vm.createContext(context);
vm.runInContext(source.slice(begin, end), context, {timeout: 1000});
context.RENDER.codex().then(() => {
  if (reads !== 1) throw Error('unexpected read count');
  process.stdout.write(JSON.stringify({html: view.innerHTML}));
}).catch(e => { console.error(e); process.exitCode = 1; });
"""
        usage = _cp()._derive_usage(raw, 85)
        result = subprocess.run([node, '-e', js, str(Path(__file__).resolve().parents[1] / 'admin/static/app.js')],
            input=json.dumps({'usage': usage, 'now': now}), text=True,
            capture_output=True, timeout=10, check=True)
        return json.loads(result.stdout)['html']

    def raw(self, primary=7, secondary=None, primary_mins=10080, secondary_mins=None):
        def window(value, mins):
            return None if value is None else {'used_percent': value, 'window_mins': mins,
                'resets_at': '2026-10-10T08:00:00+00:00'}
        return {'rate_limits': {'primary': window(primary, primary_mins),
            'secondary': window(secondary, secondary_mins), 'fetched_at': '2026-10-03T07:55:00+00:00'},
            'paused_until': None, 'sessions': []}

    def test_weekly_primary_is_not_labelled_as_five_hour(self):
        html = self.render(self.raw())
        assert '7-day window (primary)' in html
        assert '5h primary window' not in html
        assert 'Weekly secondary' not in html
        assert '2026-10-10 08:00:00 UTC' in html
        assert 'in 7d 0h' in html

    def test_two_native_windows_use_their_own_durations(self):
        html = self.render(self.raw(12, 26, 300, 10080))
        assert '5-hour window (primary)' in html
        assert '7-day window (secondary)' in html
        assert '12.0%' in html and '26.0%' in html

    def test_unknown_duration_does_not_get_an_invented_weekly_label(self):
        html = self.render(self.raw(7, 8, None, None))
        assert 'Primary window (duration not reported)' in html
        assert 'Secondary window (duration not reported)' in html
        assert '5h primary' not in html and 'Weekly secondary' not in html

    def test_over_budget_number_is_not_clamped_for_display(self):
        html = self.render(self.raw(105))
        assert '105.0%' in html
        assert 'width:100%' in html

    @pytest.mark.parametrize('permission,text', [
        (False, 'Provider has not allowed ordinary usage'),
        (None, 'Provider permission is unknown'),
        (True, 'Provider permission observed'),
    ])
    def test_permission_is_visible_but_not_execution_authority(self, permission, text):
        raw = self.raw(0)
        raw['rate_limits']['ordinary_usage_allowed'] = permission
        html = self.render(raw)
        assert text in html
        assert 'Meter readings do not grant execution' in html

    def test_absent_permission_is_not_invented_as_allowed(self):
        assert 'Provider permission not reported' in self.render(self.raw())

    def test_passed_reset_does_not_claim_automatic_recovery(self):
        raw = self.raw(100)
        raw['rate_limits']['primary']['resets_at'] = '2026-10-03T07:00:00+00:00'
        raw['paused_until'] = '2026-10-03T07:00:00+00:00'
        html = self.render(raw)
        assert 'Reported reset time has passed; awaiting fresh quota data' in html
        assert 'auto-mode resumes after reset' not in html
        assert '100.0%' in html

    def test_unknown_measurement_stays_unknown(self):
        raw = self.raw()
        raw['rate_limits']['primary']['used_percent'] = 'bad'
        html = self.render(raw)
        assert 'Usage not reported' in html
        assert 'NaN' not in html

    def test_observation_time_and_missing_deadline_are_visible(self):
        raw = self.raw()
        raw['rate_limits']['primary']['resets_at'] = None
        html = self.render(raw)
        assert '2026-10-03 07:55:00 UTC' in html
        assert 'Reset time not reported' in html

    def test_invalid_deadline_is_not_echoed_as_html(self):
        raw = self.raw()
        raw['rate_limits']['primary']['resets_at'] = '<img src=x onerror=alert(1)>'
        html = self.render(raw)
        assert '<img src=x' not in html
        assert 'Reset time not reported' in html
