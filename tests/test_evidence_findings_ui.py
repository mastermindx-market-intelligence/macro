"""Execute the actual A1 recorded-context renderer in both supported languages."""
from __future__ import annotations

import json
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

_contract = runpy.run_path(str(Path(__file__).with_name("test_admin_intelligence_os_ui.py")))["_contract"]


def render(tmp_path, findings, language="en"):
    node = shutil.which("node")
    assert node, "Node is required for the actual client contract"
    script = tmp_path / "recorded-context.mjs"
    script.write_text('''
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const document = {documentElement:{dataset:{lang:process.argv[2]}},addEventListener(){}};
const $ = () => null;
const fmtNum = n => n == null ? "—" : String(n);
''' + _contract() + '''
if (typeof iosTypedFindings !== "function") throw new Error("Missing actual recorded findings renderer");
console.log(iosTypedFindings(JSON.parse(process.argv[3])));
''', encoding="utf-8")
    result = subprocess.run([node, str(script), language, json.dumps(findings)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize("language,title,numeric,empty", [
    ("en", "Recorded disagreements", "Numeric source verification", "No findings in this recorded report."),
    ("zh", "记录的观点分歧", "数值来源核验", "此记录中没有分歧条目。"),
])
def test_valid_empty_record_is_visible_with_numeric_unavailability(tmp_path, language, title, numeric, empty):
    html = render(tmp_path, {"status": "recorded", "records": [], "gaps": [],
                            "source": {"as_of": "2026-10-12"}, "unbound_records": 0}, language)
    assert title in html and numeric in html and empty in html
    assert "2026-10-12" in html


def test_unreadable_is_unknown_instead_of_an_empty_report(tmp_path):
    html = render(tmp_path, {"status": "unavailable", "records": None, "gaps": None,
                            "source": {"as_of": None}, "unbound_records": None})
    assert "Recorded findings are unavailable." in html
    assert "No findings in this recorded report." not in html


def test_owner_text_is_escaped_and_binding_and_partial_limits_are_visible(tmp_path):
    finding = {"pair_id": "a<b", "kind": "label-lag", "severity": "note", "as_of": "unknown",
               "note": "<img src=x onerror=bad()>",
               "a": {"artifact": "data/a.json", "reading": "63-day", "binding": "ambiguous"},
               "b": {"artifact": "data/b.json", "reading": "5-day", "binding": "unbound"},
               "engine_ids": []}
    html = render(tmp_path, {"status": "partial", "records": [finding], "gaps": ["source <unknown>"],
                            "source": {"as_of": "unknown", "sha256": "a"*64},
                            "unbound_records": 1, "rejected_records": 2})
    assert "<img" not in html and "&lt;img" in html
    assert "63-day" in html and "5-day" in html
    assert "Ambiguous association" in html and "No engine association" in html
    assert "Rejected owner records" in html and ">2<" in html
    assert "Context annotations only" in html


def test_engine_empty_scope_discloses_unbound_global_findings(tmp_path):
    html = render(tmp_path, {"status": "recorded", "records": [], "gaps": [],
                            "source": {"as_of": "unknown"}, "global_unbound_records": 3})
    assert "No recorded findings match this engine." in html
    assert "Findings without an engine association" in html and ">3<" in html


@pytest.mark.parametrize("language,message", [
    ("en", "No supported findings could be displayed from this partial report."),
    ("zh", "此不完整记录中暂无可显示的有效条目。"),
])
def test_all_rejected_rows_never_assert_absence(tmp_path, language, message):
    for detail in (False, True):
        findings = {"status": "partial", "records": [], "gaps": [],
                    "rejected_records": 2, "unbound_records": 0, "source": {"as_of": "unknown"}}
        if detail:
            findings["global_unbound_records"] = 0
        html = render(tmp_path, findings, language)
        assert message in html
        assert "No findings in this recorded report." not in html
        assert "No recorded findings match this engine." not in html
        assert "此记录中没有分歧条目。" not in html
        assert "没有与此引擎对应的已记录分歧。" not in html
