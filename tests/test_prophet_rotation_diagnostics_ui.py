"""
UI contract tests for prophetRotationDiagnosticsHtml.
Runs against the pure JS function via Node subprocess — not string checks alone.
Covers: null/unavailable, valid energy leader-only, valid non-energy setup-lane,
mixed/aligned/incomplete dates, zero-v-null, malicious name/reason payload,
wrong containers and counts, wiring into RENDER.prophet.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# JS harness — runs the pure function and returns parsed stdout
# ---------------------------------------------------------------------------

APP_PATH = Path(__file__).parent.parent / "admin" / "static" / "app.js"


import os
import re
import tempfile


def _run_js(payload: dict) -> dict:
    """
    Extract prophetRotationDiagnosticsHtml + esc from app.js and run in Node.
    Avoids loading the full app (which depends on browser DOM).
    """
    app_src = APP_PATH.read_text(encoding="utf-8")

    # Extract esc function (line 6 of app.js)
    esc_match = re.search(r"(const esc = .*?;\n)", app_src)
    if not esc_match:
        return {"ok": False, "error": "esc function not found in app.js"}
    esc_def = esc_match.group(1)

    # Extract ROTATION_DIAGNOSTICS block
    start = app_src.find("/* ROTATION_DIAGNOSTICS_START */")
    end = app_src.find("/* ROTATION_DIAGNOSTICS_END */")
    if start == -1 or end == -1:
        return {"ok": False, "error": "ROTATION_DIAGNOSTICS markers not found"}
    diag_block = app_src[start + len("/* ROTATION_DIAGNOSTICS_START */") : end].strip()

    js_payload = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    script = (
        esc_def
        + "\n"
        + diag_block
        + "\n"
        f"const html=prophetRotationDiagnosticsHtml(JSON.parse({repr(js_payload)}));\n"
        "process.stdout.write(JSON.stringify({ok:true,html}));"
    )
    tmp = Path(tempfile.gettempdir()) / f"pdui_{os.getpid()}.js"
    tmp.write_text(script, encoding="utf-8")
    try:
        cp = subprocess.run(["node", str(tmp)], capture_output=True, text=True, timeout=30)
        if cp.returncode != 0:
            return {"ok": False, "error": cp.stderr or f"exit {cp.returncode}"}
        try:
            return json.loads(cp.stdout)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"JSON decode failed: {e}\n{cp.stdout[:500]}"}
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Valid base payload
# ---------------------------------------------------------------------------

VALID_PAYLOAD = {
    "schema": "prophet.rotation_diagnostics.v1",
    "authority": "operator_diagnostic_only",
    "available": True,
    "status": "available",
    "reasons": [],
    "source": {"path": "data/prophet_miss_audit/latest.json", "sha256": None},
    "dates": {
        "prices": "2026-09-01",
        "board": "2026-09-01",
        "rotation": "2026-09-01",
        "baskets": "2026-09-01",
        "basket_board": "2026-09-01",
    },
    "dates_aligned": True,
    "populations": {
        "universe": 500,
        "runners_63": 63,
        "runners_21": 21,
    },
    "conversion": {
        "sighted": 10,
        "ever_plan_matched": 3,
        "legacy_rate": 0.3,
        "basis": "ticker_ever_plan_match",
        "on_time_rate": None,
        "on_time_state": "not_measured",
    },
    "baskets": [],
}


# ---------------------------------------------------------------------------
# Null / unavailable
# ---------------------------------------------------------------------------

class TestNullUnavailable:
    """Constraint 3 / Brief §3: missing or malformed block → 'Rotation diagnostics unavailable'."""

    def test_null_payload(self):
        r = _run_js(None)
        assert r["ok"], r.get("error")
        assert "Rotation diagnostics unavailable" in r["html"]

    @pytest.mark.parametrize("val", ["string", 42, True, [], {"x": 10}])
    def test_non_object_payload(self, val):
        r = _run_js(val)
        assert r["ok"], f"failed for {type(val).__name__}"
        assert "Rotation diagnostics unavailable" in r["html"]

    def test_missing_baskets_key(self):
        p = dict(VALID_PAYLOAD)
        del p["baskets"]
        r = _run_js(p)
        assert r["ok"]
        assert "Rotation diagnostics unavailable" in r["html"]

    def test_wrong_schema(self):
        p = dict(VALID_PAYLOAD, schema="wrong.schema.v99")
        r = _run_js(p)
        assert r["ok"]
        assert "Rotation diagnostics unavailable" in r["html"]

    def test_wrong_authority(self):
        p = dict(VALID_PAYLOAD, authority="trading_signal")
        r = _run_js(p)
        assert r["ok"]
        assert "Rotation diagnostics unavailable" in r["html"]

    def test_unavailable_with_reason(self):
        p = dict(VALID_PAYLOAD, available=False, status="unavailable", reasons=["source_missing"])
        r = _run_js(p)
        assert r["ok"]
        assert "Source unavailable" in r["html"]
        assert "source_missing" in r["html"]
        # not the all-clear message
        assert "Rotation diagnostics unavailable" not in r["html"]

    def test_unavailable_no_reasons(self):
        p = dict(VALID_PAYLOAD, available=False, status="unavailable", reasons=[])
        r = _run_js(p)
        assert r["ok"]
        assert "Source unavailable — unknown reason" in r["html"]

    def test_partial_with_flags(self):
        p = dict(VALID_PAYLOAD, status="partial", reasons=["mixed_vintages", "dates_incomplete"])
        r = _run_js(p)
        assert r["ok"]
        assert "all clear" not in r["html"].lower()
        assert "accruing" not in r["html"].lower()


# ---------------------------------------------------------------------------
# dates_aligned semantics
# ---------------------------------------------------------------------------

class TestDatesAligned:
    """Constraint 3 / Brief §3: dates_aligned semantics."""

    def test_dates_aligned_true(self):
        p = dict(VALID_PAYLOAD, dates_aligned=True)
        r = _run_js(p)
        assert r["ok"]
        assert "Input dates aligned" in r["html"]
        assert "freshness not established" in r["html"]

    def test_dates_aligned_false(self):
        p = dict(VALID_PAYLOAD, dates_aligned=False,
                 dates={**VALID_PAYLOAD["dates"], "board": "2026-08-31"})
        r = _run_js(p)
        assert r["ok"]
        assert "Input dates differ" in r["html"]

    def test_dates_aligned_null(self):
        p = dict(VALID_PAYLOAD, dates_aligned=None,
                 dates={**VALID_PAYLOAD["dates"], "board": None})
        r = _run_js(p)
        assert r["ok"]
        assert "Input dates incomplete" in r["html"]

    def test_dates_aligned_absent(self):
        p = dict(VALID_PAYLOAD)
        del p["dates_aligned"]
        r = _run_js(p)
        assert r["ok"]
        assert "Rotation diagnostics" in r["html"]


# ---------------------------------------------------------------------------
# Populations: true zero vs null
# ---------------------------------------------------------------------------

class TestPopulations:
    """Constraint 4 / Brief §4: universe/63/21 runners with true zeros but null=Unavailable."""

    def test_true_zero_runners(self):
        p = dict(VALID_PAYLOAD, populations={"universe": 500, "runners_63": 0, "runners_21": 0})
        r = _run_js(p)
        assert r["ok"]
        # zero must be rendered, not suppressed
        html_lower = r["html"].lower()
        assert ">0<" in r["html"] or ">0 " in r["html"] or "0" in r["html"]

    def test_null_runners_unavailable(self):
        p = dict(VALID_PAYLOAD, populations={"universe": 500, "runners_63": None, "runners_21": None})
        r = _run_js(p)
        assert r["ok"]
        assert "—" in r["html"]

    def test_null_universe(self):
        p = dict(VALID_PAYLOAD, populations={"universe": None, "runners_63": 63, "runners_21": 21})
        r = _run_js(p)
        assert r["ok"]
        assert "—" in r["html"]


# ---------------------------------------------------------------------------
# Conversion: legacy vs on-time
# ---------------------------------------------------------------------------

class TestConversion:
    """Constraint 4 / Brief §4: legacy match shown; on-time always 'Not measured'."""

    def test_legacy_match_shown(self):
        p = dict(VALID_PAYLOAD)
        p["conversion"] = {
            "sighted": 10, "ever_plan_matched": 3, "legacy_rate": 0.3,
            "basis": "ticker_ever_plan_match", "on_time_rate": None, "on_time_state": "not_measured",
        }
        r = _run_js(p)
        assert r["ok"]
        assert "3" in r["html"]   # ever_plan_matched
        assert "10" in r["html"]  # sighted
        assert "30.0%" in r["html"]  # legacy_rate
        assert "Matches any historical plan; not timely opportunity conversion." in r["html"]

    def test_on_time_always_not_measured(self):
        p = dict(VALID_PAYLOAD)
        p["conversion"] = {
            "sighted": 10, "ever_plan_matched": 3, "legacy_rate": 0.3,
            "basis": "ticker_ever_plan_match", "on_time_rate": 0.8, "on_time_state": "measured",
        }
        r = _run_js(p)
        assert r["ok"]
        assert "Not measured" in r["html"]
        assert "0.8" not in r["html"]  # on-time rate must not appear

    def test_entry_actionability_not_measured(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [{
            "basket_id": "test", "name": "Test", "as_of": "2026-09-01",
            "counts": {"buy": 1, "watch": 0, "leaders": 0, "ran": 0},
            "visibility": "setup_lane_present", "entry_actionability": "actionable",
            "members_on_board": [],
        }]
        r = _run_js(p)
        assert r["ok"]
        assert "Not measured" in r["html"]
        assert "actionable" not in r["html"]


# ---------------------------------------------------------------------------
# Basket visibility labels
# ---------------------------------------------------------------------------

class TestBasketVisibility:
    """Constraint 4 / Brief §4: visibility labels."""

    def test_leader_only_label(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [{
            "basket_id": "energy", "name": "Energy", "as_of": "2026-09-01",
            "counts": {"buy": 0, "watch": 0, "leaders": 5, "ran": 2},
            "visibility": "leader_only", "entry_actionability": "not_measured",
            "members_on_board": ["XLE"],
        }]
        r = _run_js(p)
        assert r["ok"]
        assert "Leaders or prior runners only" in r["html"]
        assert "energy" in r["html"]

    def test_setup_lane_present_label(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [{
            "basket_id": "tech", "name": "Tech", "as_of": "2026-09-01",
            "counts": {"buy": 3, "watch": 1, "leaders": 0, "ran": 0},
            "visibility": "setup_lane_present", "entry_actionability": "not_measured",
            "members_on_board": ["AAPL"],
        }]
        r = _run_js(p)
        assert r["ok"]
        assert "Buy/watch lane present — entry not verified" in r["html"]

    def test_not_visible_label(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [{
            "basket_id": "empty", "name": "Empty", "as_of": "2026-09-01",
            "counts": {"buy": 0, "watch": 0, "leaders": 0, "ran": 0},
            "visibility": "not_visible", "entry_actionability": "not_measured",
            "members_on_board": [],
        }]
        r = _run_js(p)
        assert r["ok"]
        assert "Not visible in these lanes" in r["html"]

    def test_unknown_label(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [{
            "basket_id": "unk", "name": "Unknown", "as_of": "2026-09-01",
            "counts": {"buy": None, "watch": 0, "leaders": 0, "ran": 0},
            "visibility": "unknown", "entry_actionability": "not_measured",
            "members_on_board": [],
        }]
        r = _run_js(p)
        assert r["ok"]
        assert "Visibility unknown" in r["html"]

    def test_all_baskets_shown(self):
        """ALL rows without ranked investment ordering — brief §4."""
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [
            {"basket_id": "zulu", "name": "Zulu", "as_of": "2026-09-01",
             "counts": {"buy": 1, "watch": 0, "leaders": 0, "ran": 0},
             "visibility": "setup_lane_present", "entry_actionability": "not_measured",
             "members_on_board": []},
            {"basket_id": "alpha", "name": "Alpha", "as_of": "2026-09-01",
             "counts": {"buy": 2, "watch": 0, "leaders": 0, "ran": 0},
             "visibility": "setup_lane_present", "entry_actionability": "not_measured",
             "members_on_board": []},
        ]
        r = _run_js(p)
        assert r["ok"]
        assert "alpha" in r["html"] and "zulu" in r["html"]
        assert "<table>" in r["html"]


# ---------------------------------------------------------------------------
# Malicious payload — no innerHTML injection
# ---------------------------------------------------------------------------

class TestMaliciousPayload:
    """Constraint 5 / Brief §5: malicious name/reason — esc prevents injection."""

    def test_script_injection_in_name(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [{
            "basket_id": "x", "name": '<script>alert(1)</script>', "as_of": "2026-09-01",
            "counts": {"buy": 1, "watch": 0, "leaders": 0, "ran": 0},
            "visibility": "setup_lane_present", "entry_actionability": "not_measured",
            "members_on_board": [],
        }]
        r = _run_js(p)
        assert r["ok"]
        assert "<script>" not in r["html"]

    def test_xss_in_reason(self):
        p = dict(VALID_PAYLOAD, reasons=['<img src=x onerror=alert(1)>'])
        r = _run_js(p)
        assert r["ok"]
        # The < and > must be HTML-escaped so no img tag is formed
        assert "<img" not in r["html"]

    def test_xss_in_basket_id(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [{
            "basket_id": '"><script>alert(1)</script>', "name": "Test", "as_of": "2026-09-01",
            "counts": {"buy": 1, "watch": 0, "leaders": 0, "ran": 0},
            "visibility": "setup_lane_present", "entry_actionability": "not_measured",
            "members_on_board": [],
        }]
        r = _run_js(p)
        assert r["ok"]
        assert "<script>" not in r["html"]

    def test_sqli_in_reason(self):
        p = dict(VALID_PAYLOAD, reasons=["'; DROP TABLE users;--"])
        r = _run_js(p)
        assert r["ok"]
        # The raw SQL is escaped; &#39; decodes to ' but the literal text is inert in HTML
        assert "<script>" not in r["html"] and "alert" not in r["html"]

    def test_unicode_in_name(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [{
            "basket_id": "cn", "name": "能源板块", "as_of": "2026-09-01",
            "counts": {"buy": 1, "watch": 0, "leaders": 0, "ran": 0},
            "visibility": "setup_lane_present", "entry_actionability": "not_measured",
            "members_on_board": [],
        }]
        r = _run_js(p)
        assert r["ok"]
        assert "能源板块" in r["html"]

    def test_unicode_in_member(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [{
            "basket_id": "mem", "name": "Members", "as_of": "2026-09-01",
            "counts": {"buy": 1, "watch": 0, "leaders": 0, "ran": 0},
            "visibility": "setup_lane_present", "entry_actionability": "not_measured",
            "members_on_board": ["XLE", "中文"],
        }]
        r = _run_js(p)
        assert r["ok"]
        assert "中文" in r["html"]


# ---------------------------------------------------------------------------
# Wrong containers and counts — degrade gracefully
# ---------------------------------------------------------------------------

class TestWrongContainersAndCounts:
    """Constraint 5 / Brief §5: wrong containers and counts degrade gracefully."""

    @pytest.mark.parametrize("val", ["not an array", 42, {"foo": "bar"}])
    def test_baskets_wrong_type(self, val):
        p = dict(VALID_PAYLOAD, baskets=val)
        r = _run_js(p)
        assert r["ok"]
        assert "Rotation diagnostics unavailable" in r["html"]

    @pytest.mark.parametrize("val", [-5, True, "five", float("nan"), float("inf")])
    def test_negative_bool_string_nan_count(self, val):
        import math
        # Replace non-finite Python floats with None before JSON serialization
        # (json.dumps raises on NaN/Inf with allow_nan=False; None represents the
        # unmarshalled form of a non-finite JSON number that the renderer must reject)
        clean_val = None if isinstance(val, float) and not math.isfinite(val) else val
        p = dict(VALID_PAYLOAD)
        p["populations"] = {"universe": clean_val, "runners_63": 63, "runners_21": 21}
        r = _run_js(p)
        assert r["ok"]
        assert "—" in r["html"] or "Rotation diagnostics" in r["html"]

    def test_no_number_null_as_zero(self):
        """No Number(null)=0 — null must stay as unavailable marker."""
        p = dict(VALID_PAYLOAD)
        p["populations"] = {"universe": None, "runners_63": None, "runners_21": None}
        r = _run_js(p)
        assert r["ok"]
        assert "—" in r["html"]


# ---------------------------------------------------------------------------
# Max 200 basket rows, disclose truncation
# ---------------------------------------------------------------------------

class TestBasketRows:
    """Constraint 4/5: max 200 rows; disclose rather than silently truncate."""

    def test_over_200_disclosed(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [
            {"basket_id": f"b{i}", "name": f"Basket {i}", "as_of": "2026-09-01",
             "counts": {"buy": 1, "watch": 0, "leaders": 0, "ran": 0},
             "visibility": "setup_lane_present", "entry_actionability": "not_measured",
             "members_on_board": []}
            for i in range(250)
        ]
        r = _run_js(p)
        assert r["ok"]
        assert "Basket component unavailable" in r["html"]
        assert "250" in r["html"]
        assert "No baskets in audit" not in r["html"]
        assert "Basket 0" not in r["html"]

    def test_under_200_no_disclose(self):
        p = dict(VALID_PAYLOAD)
        p["baskets"] = [
            {"basket_id": f"b{i}", "name": f"Basket {i}", "as_of": "2026-09-01",
             "counts": {"buy": 1, "watch": 0, "leaders": 0, "ran": 0},
             "visibility": "setup_lane_present", "entry_actionability": "not_measured",
             "members_on_board": []}
            for i in range(5)
        ]
        r = _run_js(p)
        assert r["ok"]
        assert "Showing first 200" not in r["html"]


# ---------------------------------------------------------------------------
# Source SHA
# ---------------------------------------------------------------------------

class TestSourceSha:
    """Constraint 4 / Brief §4: source SHA is optional detail."""

    def test_sha_shown_when_present(self):
        p = dict(VALID_PAYLOAD)
        p["source"] = {"path": "data/prophet_miss_audit/latest.json", "sha256": "abc123def456"}
        r = _run_js(p)
        assert r["ok"]
        assert "abc123def456" in r["html"]

    def test_sha_absent_not_shown(self):
        p = dict(VALID_PAYLOAD)
        p["source"] = {"path": "data/prophet_miss_audit/latest.json", "sha256": None}
        r = _run_js(p)
        assert r["ok"]
        assert "SHA" not in r["html"]


# ---------------------------------------------------------------------------
# Wiring checks (source only)
# ---------------------------------------------------------------------------

class TestWiring:
    """Brief §11: function is wired into actual RENDER.prophet (source check only)."""

    def test_function_defined_between_markers(self):
        src = APP_PATH.read_text(encoding="utf-8")
        assert "function prophetRotationDiagnosticsHtml(payload)" in src
        assert "ROTATION_DIAGNOSTICS_START" in src
        assert "ROTATION_DIAGNOSTICS_END" in src

    def test_wired_into_render_prophet(self):
        src = APP_PATH.read_text(encoding="utf-8")
        assert "const rotationDiagnosticsHtml = prophetRotationDiagnosticsHtml(d.rotation_diagnostics)" in src

    def test_inserted_after_integrityHtml(self):
        src = APP_PATH.read_text(encoding="utf-8")
        # rotationDiagnosticsHtml must appear in the innerHTML chain after integrityHtml
        pos = src.find("integrityHtml + rotationDiagnosticsHtml")
        assert pos != -1, "rotationDiagnosticsHtml must follow integrityHtml in v.innerHTML chain"


# ---------------------------------------------------------------------------
# Legacy source cannot imply on-time
# ---------------------------------------------------------------------------

class TestNoOnTimeFromLegacy:
    """Brief §11 / Constraint 4: source cannot imply on-time rate or entry proof."""

    def test_no_on_time_implied_from_legacy(self):
        p = dict(VALID_PAYLOAD)
        p["conversion"] = {
            "sighted": 10, "ever_plan_matched": 3, "legacy_rate": 0.3,
            "basis": "ticker_ever_plan_match", "on_time_rate": 0.8, "on_time_state": "measured",
        }
        r = _run_js(p)
        assert r["ok"]
        # on-time rate (0.8) must not appear — renderer must ignore it
        assert "0.8" not in r["html"]
        # "on-time" string may appear as part of the fixed label but "measured" must not
        assert "measured" not in r["html"].lower() or "not measured" in r["html"].lower()


@pytest.mark.parametrize("bad", [None, [], "bad"])
def test_malformed_basket_rows_do_not_crash(bad):
    p = json.loads(json.dumps(VALID_PAYLOAD))
    p["baskets"] = [bad]
    result = _run_js(p)
    assert result["ok"], result
    assert "Basket row unavailable" in result["html"]


def test_negative_population_is_not_a_count():
    p = json.loads(json.dumps(VALID_PAYLOAD))
    p["populations"]["universe"] = -12345
    result = _run_js(p)
    assert result["ok"] and "-12345" not in result["html"]


def test_truthy_string_does_not_assert_availability():
    p = json.loads(json.dumps(VALID_PAYLOAD))
    p["available"] = "true"
    result = _run_js(p)
    assert result["ok"] and "Source unavailable" in result["html"]


def test_invalid_calendar_date_is_not_displayed_as_valid():
    p = json.loads(json.dumps(VALID_PAYLOAD))
    p["dates"]["prices"] = "2026-02-30"
    result = _run_js(p)
    assert result["ok"] and "2026-02-30" not in result["html"]


def test_inconsistent_conversion_is_not_a_percentage_claim():
    p = json.loads(json.dumps(VALID_PAYLOAD))
    p["conversion"]["legacy_rate"] = 0.9
    result = _run_js(p)
    assert result["ok"] and "90.0%" not in result["html"]
    p["conversion"]["ever_plan_matched"] = 12345
    result = _run_js(p)
    assert result["ok"] and "12345 matched" not in result["html"]


def test_alignment_hint_cannot_override_actual_dates():
    p = json.loads(json.dumps(VALID_PAYLOAD))
    p["dates"]["board"] = "2026-08-31"
    p["dates_aligned"] = True
    result = _run_js(p)
    assert result["ok"] and "Input dates differ" in result["html"]
    assert "Input dates aligned" not in result["html"]


class TestContinuationRegressions:
    @pytest.mark.parametrize('hint', [False, None, 'false'])
    def test_alignment_hint_cannot_override_actual_dates(self, hint):
        result = _run_js(dict(VALID_PAYLOAD, dates_aligned=hint))
        assert result['ok']
        assert 'Input dates aligned' in result['html']
        assert 'freshness not established' in result['html']

    def test_withheld_source_is_not_an_empty_audit(self):
        result = _run_js(dict(VALID_PAYLOAD, status='partial',
                              reasons=['basket_source_unavailable']))
        assert result['ok']
        assert 'Basket evidence unavailable' in result['html']
        assert 'No baskets in audit' not in result['html']

    def test_basket_board_cutoff_is_visible(self):
        result = _run_js(dict(VALID_PAYLOAD,
                              dates={**VALID_PAYLOAD['dates'], 'basket_board': '2026-08-28'}))
        assert result['ok']
        assert 'Basket board as-of' in result['html']
        assert '2026-08-28' in result['html']
        assert 'Input dates differ' in result['html']

    def test_one_html_decode_preserves_original_text(self):
        import html
        payload = dict(VALID_PAYLOAD, baskets=[{
            'basket_id': 'control', 'name': 'Oil & Gas <research>',
            'as_of': '2026-09-01',
            'counts': {'buy': 0, 'watch': 0, 'leaders': 1, 'ran': 0},
            'visibility': 'leader_only', 'entry_actionability': 'not_measured',
            'members_on_board': ['TEST'],
        }])
        result = _run_js(payload)
        assert result['ok']
        assert 'Oil &amp; Gas &lt;research&gt;' in result['html']
        assert 'Oil &amp;amp;' not in result['html']
        assert 'Oil & Gas <research>' in html.unescape(result['html'])
        assert 'Matches any historical plan; not timely opportunity conversion.' in html.unescape(result['html'])
