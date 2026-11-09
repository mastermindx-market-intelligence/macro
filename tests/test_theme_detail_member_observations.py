"""Existing basket-detail consumption of source-bound member observations."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import jinja2
import numpy as np
import pandas as pd
import pytest

from engine.company_intelligence.contracts import canonical_json_bytes
from engine import group_member_observations as GMO
from engine import group_pulse as GP
from scripts import build_theme_detail as BTD
from scripts import check_group_member_observations as CHECK

AS_OF = "2026-09-15"
GENERATED_AT = "2026-09-16T07:32:35+00:00"
GROUP_ID = "test_group"
ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "basket_detail.html.j2"
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")


def _write_generation(site: Path, member_keys=("A", "B", "C")) -> dict:
    idx = pd.bdate_range(end=AS_OF, periods=220)
    closes = pd.DataFrame(
        {key: np.linspace(100.0, 150.0 + pos, len(idx))
         for pos, key in enumerate(member_keys)},
        index=idx,
    )
    if "C" in closes.columns:
        closes.loc[idx[:70], "C"] = np.nan  # legacy partial warm-up; strict 200 refuses
    rets = closes.pct_change(fill_method=None)
    true = pd.DataFrame(True, index=idx, columns=closes.columns)
    false = pd.DataFrame(False, index=idx, columns=closes.columns)
    panel = {
        "index": idx,
        "closes": closes,
        "rets": rets,
        "spy_adj": rets - 0.001,
        "covered": true,
        "active": false,
        "has_ma50": true,
        "has_ma200": true,
        "above_ma50": true,
        "above_ma200": true,
        "activity_z": pd.DataFrame(0.0, index=idx, columns=closes.columns),
    }
    panel["active"].loc[idx[-1], member_keys[0]] = True
    members = [
        {"member_key": key, "source_symbol": key, "identity_ref": f"source:{key}"}
        for key in member_keys
    ]
    legacy = {
        "schema": "group_pulse.v1", "authority": "context_only",
        "generated_at": GENERATED_AT, "basket_id": GROUP_ID, "as_of": AS_OF,
        "n_members": len(member_keys), "n_covered": len(member_keys),
        "participation": {
            "activity_share": round(1 / len(member_keys), 4), "activity_n": 1,
            "trend_share_50d": 1.0, "trend_n_50d": len(member_keys),
            "trend_share_200d": 1.0, "trend_n_200d": len(member_keys),
            "activity_basis": {"ret_only": 1, "ret_and_volume": 0},
        },
    }
    as_of_ts = pd.Timestamp(AS_OF)
    legacy_activity_state = (panel["active"].loc[[as_of_ts]].astype("float64")
                             .where(panel["covered"].loc[[as_of_ts]]))
    legacy_trend_50_state = (panel["above_ma50"].loc[[as_of_ts]].astype("float64")
                             .where((panel["covered"] & panel["has_ma50"]).loc[[as_of_ts]]))
    legacy_trend_200_state = (panel["above_ma200"].loc[[as_of_ts]].astype("float64")
                              .where((panel["covered"] & panel["has_ma200"]).loc[[as_of_ts]]))
    receipts = [
        GMO.normalized_frame_receipt(
            closes, source_ref="group_pulse:member_close_panel",
            basis="total_return_close", effective_at=AS_OF,
        ),
        GMO.normalized_frame_receipt(
            legacy_activity_state, source_ref="group_pulse:legacy_activity_state",
            basis="legacy_activity_state", effective_at=AS_OF,
        ),
        GMO.normalized_frame_receipt(
            legacy_trend_50_state, source_ref="group_pulse:legacy_trend_50_state",
            basis="legacy_trend_50_state", effective_at=AS_OF,
        ),
        GMO.normalized_frame_receipt(
            legacy_trend_200_state, source_ref="group_pulse:legacy_trend_200_state",
            basis="legacy_trend_200_state", effective_at=AS_OF,
        ),
        GMO.normalized_frame_receipt(
            rets, source_ref="group_pulse:member_raw_return_panel",
            basis="raw_daily_change", effective_at=AS_OF,
        ),
        GMO.normalized_frame_receipt(
            panel["spy_adj"], source_ref="group_pulse:member_benchmark_relative_return_panel",
            basis="benchmark_relative_daily_change", effective_at=AS_OF,
        ),
    ]
    group = GMO.project_group_members(
        group_id=GROUP_ID, member_records=members, panel=panel, as_of=AS_OF,
        covered_members=list(member_keys), active_members=[member_keys[0]],
        legacy_pulse=legacy, source_receipts=receipts,
        generated_at=GENERATED_AT,
    )
    pulse_bytes = GP.site_payload_bytes({GROUP_ID: legacy})
    bundle = GMO.assemble_member_bundle(
        groups={GROUP_ID: group}, as_of=AS_OF, generated_at=GENERATED_AT,
        source_receipts=receipts, legacy_pulse_bytes=pulse_bytes,
    )
    basketdata = site / "basketdata"
    basketdata.mkdir(parents=True, exist_ok=True)
    (basketdata / "pulse.json").write_bytes(pulse_bytes)
    (basketdata / "member_observations.json").write_bytes(canonical_json_bytes(bundle))
    return bundle


def test_member_observation_index_requires_exact_pulse_bytes(tmp_path):
    site = tmp_path / "site"
    bundle = _write_generation(site)
    index = BTD.member_observation_index(site, "us")
    assert set(index) == {GROUP_ID}
    assert index[GROUP_ID]["group"]["member_keys"] == ["A", "B", "C"]
    assert index[GROUP_ID]["projection_digest"] == bundle["projection_digest"]
    pulse = site / "basketdata" / "pulse.json"
    pulse.write_bytes(pulse.read_bytes() + b" ")
    assert BTD.member_observation_index(site, "us") == {}
    assert BTD.member_observation_index(site, "china") == {}


class _Template:
    def __init__(self):
        self.calls: list[dict] = []

    def render(self, **kwargs):
        self.calls.append(kwargs)
        return "<html>ok</html>"


class _Env:
    def __init__(self, template: _Template):
        self.template = template

    def get_template(self, name: str):
        assert name == "basket_detail.html.j2"
        return self.template


def test_detail_builder_keeps_legacy_action_members_separate(monkeypatch, tmp_path):
    site = tmp_path / "site"
    _write_generation(site, member_keys=("A", "B", "C"))
    template = _Template()
    action_inputs: list[list[str]] = []
    from engine import basket_history, basket_score

    monkeypatch.setattr(BTD, "_conviction", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(BTD, "standout_index", lambda _region="us": {})
    monkeypatch.setattr(BTD, "member_context_index", lambda _region="us": {})
    monkeypatch.setattr(BTD, "write_page", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(basket_history, "score_series", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(basket_history, "change_timeline", lambda *_args, **_kwargs: [])

    def capture_action(members, _theme):
        action_inputs.append([member["symbol"] for member in members])
        return {"captured": True}

    monkeypatch.setattr(basket_score, "act_now_stocks", capture_action)
    data = {
        "baskets": [{
            "id": GROUP_ID, "name": "Test Group", "name_zh": "测试组",
            "created": AS_OF,
            "members": [
                {"symbol": "A", "name": "Alpha"},
                {"symbol": "B", "name": "Beta"},
            ],
        }],
        "theme_intel": {"as_of": AS_OF, "themes": [{"id": GROUP_ID}]},
    }
    assert BTD.build_detail_pages(data, site, _Env(template), "us") == 1
    detail = json.loads(template.calls[0]["detail_json"])
    assert action_inputs == [["A", "B"]]
    assert [member["symbol"] for member in detail["members"]] == ["A", "B"]
    assert detail["act_now"] == {"captured": True}
    assert detail["member_observations"]["group"]["member_keys"] == ["A", "B", "C"]
    assert detail["member_observations"]["authority"] == "context_only"
    assert detail["member_observations"]["legacy_pulse_sha256"]


def test_detail_builder_degrades_quietly_on_observation_mismatch(monkeypatch, tmp_path):
    site = tmp_path / "site"
    _write_generation(site)
    pulse = site / "basketdata" / "pulse.json"
    pulse.write_bytes(pulse.read_bytes() + b" ")
    template = _Template()
    from engine import basket_history, basket_score

    monkeypatch.setattr(BTD, "_conviction", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(BTD, "standout_index", lambda _region="us": {})
    monkeypatch.setattr(BTD, "member_context_index", lambda _region="us": {})
    monkeypatch.setattr(BTD, "write_page", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(basket_history, "score_series", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(basket_history, "change_timeline", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(basket_score, "act_now_stocks", lambda *_args: {})
    data = {
        "baskets": [{
            "id": GROUP_ID, "name": "Test Group", "created": AS_OF,
            "members": [{"symbol": "A", "name": "Alpha"}],
        }],
        "theme_intel": {"as_of": AS_OF, "themes": [{"id": GROUP_ID}]},
    }
    assert BTD.build_detail_pages(data, site, _Env(template), "us") == 1
    detail = json.loads(template.calls[0]["detail_json"])
    assert detail["member_observations"] is None


def test_template_exposes_complete_member_evidence_without_client_refetch():
    text = Path("templates/basket_detail.html.j2").read_text(encoding="utf-8")
    required = (
        "P1:MEMBER-EVIDENCE:BEGIN",
        "P1:MEMBER-EVIDENCE:END",
        "memberObservationSection(d.member_observations)",
        "group.member_keys",
        'id="mo-metric"',
        'id="mo-search"',
        'id="mo-filter"',
        'id="mo-rows"',
        "observations_available",
        "observations_required",
        "projection_digest",
        "legacy_pulse_sha256",
        "data-member-observations-digest",
        "data-member-observations-pulse-sha256",
        "What supports this read?",
        "哪些成分股支持这项读数？",
        "Context only — does not rank, score, gate, or change action inputs.",
        "仅作背景 — 不排序、不评分、不设门槛，也不改变操作输入。",
    )
    for token in required:
        assert token in text, token
    assert "fetch('../basketdata/member_observations.json'" not in text


def _member_evidence_js() -> str:
    source = TEMPLATE.read_text(encoding="utf-8")
    start = source.index("/* P1:MEMBER-EVIDENCE:BEGIN")
    end = source.index("/* P1:MEMBER-EVIDENCE:END */", start)
    return source[start:end]


def _run_member_js(observation: dict, body: str) -> dict:
    prelude = r'''
function L(en,zh){return '<en>'+en+'</en><zh>'+(zh==null?en:zh)+'</zh>';}
function esc(s){return(s==null?'':String(s)).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));}
function cls(x){return x==null?'muted':(x>=0?'pos':'neg');}
function fmtPct(x){return x==null?'—':(x>=0?'+':'')+(x*100).toFixed(1)+'%';}
function _isZh(){return false;}
function stkGR(sym){return '<ticker>'+sym+'</ticker>';}
'''
    script = (prelude + "\nconst OBS=" + json.dumps(observation, separators=(",", ":"))
              + ";\nconst DETAIL={member_observations:OBS};\n"
              + _member_evidence_js() + "\n" + body)
    result = subprocess.run(
        [shutil.which("node") or "node", "-e", script],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@needs_node
def test_shipped_member_evidence_filters_only_visible_rows(tmp_path):
    site = tmp_path / "site"
    _write_generation(site)
    observation = BTD.member_observation_index(site, "us")[GROUP_ID]
    result = _run_member_js(observation, r'''
const before=JSON.stringify(OBS.group.metrics.strict_trend_200);
_moState.metric='strict_trend_200'; _moState.filter='all'; _moState.query='';
const allRows=moRowsHtml(OBS,_moState.metric);
_moState.filter='unavailable';
const missingRows=moRowsHtml(OBS,_moState.metric);
_moState.filter='all'; _moState.query='A';
const searchedRows=moRowsHtml(OBS,_moState.metric);
_moState.query='';
const html=memberObservationSection(OBS);
console.log(JSON.stringify({
  all:allRows.visible, missing:missingRows.visible, searched:searchedRows.visible,
  roster:OBS.group.member_keys.length,
  metricUnchanged:before===JSON.stringify(OBS.group.metrics.strict_trend_200),
  hasControls:html.includes('id="mo-metric"')&&html.includes('id="mo-search"')&&html.includes('id="mo-filter"'),
  hasContextBoundary:html.includes('does not rank, score, gate, or change action inputs'),
  hasUnavailable:missingRows.html.includes('Unavailable')
}));
''')
    assert result == {
        "all": 3, "missing": 1, "searched": 1, "roster": 3,
        "metricUnchanged": True, "hasControls": True,
        "hasContextBoundary": True, "hasUnavailable": True,
    }


@needs_node
def test_rendered_detail_inline_javascript_parses(tmp_path):
    site = tmp_path / "site"
    _write_generation(site)
    observation = BTD.member_observation_index(site, "us")[GROUP_ID]
    detail = {
        "basket": {"id": GROUP_ID, "name": "Test Group", "members": []},
        "members": [], "theme": {}, "act_now": {}, "history": [], "timeline": [],
        "as_of": AS_OF, "market_concentration": {}, "stock_base": "../stock.html#",
        "back": "../sector_central.html", "region": "us",
        "bench_label": "S&P 500", "bench_label_zh": "标普500",
        "member_observations": observation,
    }
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT / "templates")), autoescape=False,
    )
    html = env.get_template("basket_detail.html.j2").render(
        detail_json=json.dumps(detail, separators=(",", ":")),
        basket_name="Test Group", generated_utc="2026-09-16 07:32 UTC",
        member_observation_digest=observation["projection_digest"],
        member_observation_pulse_sha256=observation["legacy_pulse_sha256"],
        back_href="../sector_central.html", back_label_en="Sector Intelligence",
        back_label_zh="行业智慧",
    )
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S)
    checked = 0
    for script in scripts:
        if not script.strip():
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as handle:
            handle.write(script)
            handle.flush()
            result = subprocess.run(
                [shutil.which("node") or "node", "--check", handle.name],
                capture_output=True, text=True, timeout=30,
            )
        assert result.returncode == 0, result.stderr
        checked += 1
    assert checked >= 2
    page = site / "basket" / f"{GROUP_ID}.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html, encoding="utf-8")
    result = CHECK.evaluate(site)
    assert result["ok"] is True, result["errors"]


def _write_detail_receipt(site: Path, bundle: dict, *, digest: str | None = None,
                          payload: dict | None = None) -> Path:
    group_id = next(iter(bundle["groups"]))
    out = site / "basket" / f"{group_id}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    value = digest or bundle["projection_digest"]
    pulse = bundle["source"]["legacy_pulse_sha256"]
    if payload is None:
        payload = {
            "basket": {"id": group_id},
            "member_observations": BTD.member_observation_index(site, "us")[group_id],
        }
    out.write_text(
        f'<body data-member-observations-digest="{value}" '
        f'data-member-observations-pulse-sha256="{pulse}">'
        f'<script>\nconst DETAIL = {json.dumps(payload)};\n</script></body>',
        encoding="utf-8",
    )
    return out


def test_publication_validator_binds_pulse_companion_and_detail(tmp_path):
    site = tmp_path / "site"
    bundle = _write_generation(site)
    _write_detail_receipt(site, bundle)
    result = CHECK.evaluate(site)
    assert result["ok"] is True
    assert result["group_count"] == 1
    assert result["errors"] == []


def test_publication_validator_rejects_pulse_and_detail_mismatch(tmp_path):
    site = tmp_path / "site"
    bundle = _write_generation(site)
    detail = _write_detail_receipt(site, bundle, digest="0" * 64)
    first = CHECK.evaluate(site)
    assert first["ok"] is False
    assert any("detail" in error.lower() for error in first["errors"])
    detail.write_text(detail.read_text().replace("0" * 64, bundle["projection_digest"]), encoding="utf-8")
    pulse = site / "basketdata" / "pulse.json"
    pulse.write_bytes(pulse.read_bytes() + b" ")
    second = CHECK.evaluate(site)
    assert second["ok"] is False
    assert any("pulse" in error.lower() for error in second["errors"])


def test_current_run_gate_refuses_capture_errors_or_missing_artifact():
    assert CHECK.current_run_errors({
        "member_observation_errors": ["capture failed"],
        "member_observations_artifact": None,
        "member_observations_digest": None,
    })
    assert CHECK.current_run_errors({
        "member_observation_errors": [],
        "member_observations_artifact": None,
        "member_observations_digest": None,
    })
    assert CHECK.current_run_errors({
        "member_observation_errors": [],
        "member_observations_artifact": "/tmp/member_observations.json",
        "member_observations_digest": "a" * 64,
    }) == []


def test_publication_validator_binds_companion_semantics_to_pulse(tmp_path):
    site = tmp_path / "site"
    bundle = _write_generation(site)
    _write_detail_receipt(site, bundle)
    companion_path = site / "basketdata" / "member_observations.json"

    forged = json.loads(canonical_json_bytes(bundle))
    forged["as_of"] = "2026-09-14"
    for receipt in forged["source"]["receipts"]:
        receipt["effective_at"] = "2026-09-14"
    for group in forged["groups"].values():
        for member in group["members"].values():
            for cell in member["metrics"].values():
                cell["effective_at"] = "2026-09-14"
    forged["projection_digest"] = GMO.projection_digest(forged)
    companion_path.write_bytes(canonical_json_bytes(forged))
    result = CHECK.evaluate(site)
    assert result["ok"] is False
    assert any("as_of" in error.lower() for error in result["errors"])

    bundle = _write_generation(site)
    _write_detail_receipt(site, bundle)
    forged = json.loads(canonical_json_bytes(bundle))
    forged["generated_at"] = "2026-09-16T08:00:00+00:00"
    forged["projection_digest"] = GMO.projection_digest(forged)
    companion_path.write_bytes(canonical_json_bytes(forged))
    result = CHECK.evaluate(site)
    assert result["ok"] is False
    assert any("generated_at" in error.lower() for error in result["errors"])


def test_publication_validator_binds_legacy_metric_values_and_byte_count(tmp_path):
    site = tmp_path / "site"
    bundle = _write_generation(site)
    _write_detail_receipt(site, bundle)
    companion_path = site / "basketdata" / "member_observations.json"

    forged = json.loads(canonical_json_bytes(bundle))
    forged["source"]["legacy_pulse_bytes"] += 1
    forged["projection_digest"] = GMO.projection_digest(forged)
    companion_path.write_bytes(canonical_json_bytes(forged))
    result = CHECK.evaluate(site)
    assert result["ok"] is False
    assert any("byte count" in error.lower() for error in result["errors"])

    bundle = _write_generation(site)
    _write_detail_receipt(site, bundle)
    forged = json.loads(canonical_json_bytes(bundle))
    group = forged["groups"][GROUP_ID]
    metric = group["metrics"]["legacy_activity"]
    metric["numerator_member_keys"] = []
    metric["numerator"] = 0
    metric["value"] = 0.0
    group["members"]["A"]["metrics"]["legacy_activity"]["value"] = False
    forged["projection_digest"] = GMO.projection_digest(forged)
    assert GMO.validate_member_bundle(forged) == []
    companion_path.write_bytes(canonical_json_bytes(forged))
    result = CHECK.evaluate(site)
    assert result["ok"] is False
    assert any("legacy_activity" in error for error in result["errors"])


@pytest.mark.parametrize("mutation", [
    "missing_observation", "wrong_basket", "wrong_group", "missing_member",
    "changed_metric", "changed_null", "boolean_as_number", "wrong_schema",
    "wrong_as_of", "wrong_projection", "wrong_pulse", "nonfinite_value",
])
def test_publication_validator_rejects_embedded_payload_drift(tmp_path, mutation):
    site = tmp_path / "site"
    bundle = _write_generation(site)
    observation = BTD.member_observation_index(site, "us")[GROUP_ID]
    payload = {"basket": {"id": GROUP_ID}, "member_observations": observation}
    if mutation == "missing_observation":
        payload["member_observations"] = None
    elif mutation == "wrong_basket":
        payload["basket"]["id"] = "other_group"
    elif mutation == "wrong_group":
        observation["group"]["group_id"] = "other_group"
    elif mutation == "missing_member":
        observation["group"]["members"].pop("C")
    elif mutation == "changed_metric":
        observation["group"]["metrics"]["strict_trend_200"]["value"] = 0.0
    elif mutation == "changed_null":
        observation["group"]["members"]["C"]["metrics"]["strict_trend_200"]["value"] = False
    elif mutation == "boolean_as_number":
        observation["group"]["members"]["A"]["metrics"]["strict_trend_200"]["value"] = 1
    elif mutation == "wrong_schema":
        observation["schema"] = "unrecognised.v1"
    elif mutation == "wrong_as_of":
        observation["as_of"] = "2026-09-14"
    elif mutation == "wrong_projection":
        observation["projection_digest"] = "0" * 64
    elif mutation == "wrong_pulse":
        observation["legacy_pulse_sha256"] = "0" * 64
    else:
        observation["group"]["members"]["A"]["metrics"]["raw_daily_change"]["value"] = float("nan")
    _write_detail_receipt(site, bundle, payload=payload)
    result = CHECK.evaluate(site)
    assert result["ok"] is False, f"accepted drift: {mutation}"
    assert any("detail" in error.lower() for error in result["errors"])


@pytest.mark.parametrize("mutation", [
    "missing_script", "duplicate_detail", "external_script", "duplicate_json_key",
    "metadata_only_in_comment", "duplicate_body_attribute", "commented_payload",
    "non_executable_type", "duplicate_body", "unterminated_literal",
])
def test_publication_validator_requires_unambiguous_real_body_payload(tmp_path, mutation):
    site = tmp_path / "site"
    bundle = _write_generation(site)
    page = _write_detail_receipt(site, bundle)
    text = page.read_text()
    script = re.search(r"<script>.*?</script>", text, re.S).group(0)
    if mutation == "missing_script":
        text = text.replace(script, "")
    elif mutation == "duplicate_detail":
        text = text.replace("</body>", script + "</body>")
    elif mutation == "external_script":
        text = text.replace("<script>", '<script src="ignored.js">')
    elif mutation == "commented_payload":
        text = text.replace("<script>", "<script>/*").replace("</script>", "*/</script>")
    elif mutation == "non_executable_type":
        text = text.replace("<script>", '<script type="application/json">')
    elif mutation == "duplicate_body":
        text += "<body></body>"
    elif mutation == "unterminated_literal":
        text = text.replace(";\n</script>", "\n</script>")
    elif mutation == "duplicate_json_key":
        text = text.replace('const DETAIL = {', 'const DETAIL = {"member_observations":null,', 1)
    elif mutation == "metadata_only_in_comment":
        body_tag = re.search(r"<body[^>]*>", text).group(0)
        text = "<!-- " + body_tag + " -->" + text.replace(body_tag, "<body>", 1)
    else:
        text = text.replace("<body ", '<body data-member-observations-digest="' + "0" * 64 + '" ', 1)
    page.write_text(text)
    result = CHECK.evaluate(site)
    assert result["ok"] is False, f"accepted ambiguous page: {mutation}"
    assert any("detail" in error.lower() for error in result["errors"])


@needs_node
@pytest.mark.parametrize("value, display", [(0.01, "+1.0"), (-0.015, "-1.5"), (0.0, "+0.0")])
def test_member_relative_change_uses_percentage_points_not_return_percent(value, display):
    result = _run_member_js({}, """
const cell={value:%s}; const before=JSON.stringify(cell);
console.log(JSON.stringify({
  relative:moCellValue('benchmark_relative_daily_change',cell),
  raw:moCellValue('raw_daily_change',cell),
  note:moMetricNote('benchmark_relative_daily_change'),
  label:moLabel('benchmark_relative_daily_change'),
  unchanged:before===JSON.stringify(cell)
}));
""" % json.dumps(value))
    assert display in result["relative"]
    assert "pp" in result["relative"] and "个百分点" in result["relative"]
    assert "%" not in result["relative"]
    assert display + "%" in result["raw"]
    assert "percentage points" in result["note"] and "百分点" in result["note"]
    assert "minus" in result["note"] and "减去" in result["note"]
    assert "pp" in result["label"][0] and "百分点" in result["label"][1]
    assert result["unchanged"] is True


@needs_node
def test_member_relative_units_do_not_turn_null_or_boolean_into_numbers():
    result = _run_member_js({}, r'''
console.log(JSON.stringify({
 missing:moCellValue('benchmark_relative_daily_change',{value:null}),
 raw:moCellValue('raw_daily_change',{value:0.03}),
 above:moCellValue('strict_trend_200',{value:true}),
 below:moCellValue('strict_trend_200',{value:false})
}));
''')
    assert "Unavailable" in result["missing"] and "不可用" in result["missing"]
    assert "0.0" not in result["missing"] and "pp" not in result["missing"]
    assert "+3.0%" in result["raw"]
    assert "Above" in result["above"] and "Below" in result["below"]


@needs_node
def test_member_evidence_mobile_rows_keep_reason_and_history_labels(tmp_path):
    site = tmp_path / "site"
    _write_generation(site)
    observation = BTD.member_observation_index(site, "us")[GROUP_ID]
    result = _run_member_js(observation, r'''
_moState.metric='strict_trend_200'; _moState.filter='unavailable';
const before=JSON.stringify(OBS);
const rows=moRowsHtml(OBS,_moState.metric);
console.log(JSON.stringify({
  html:rows.html, section:memberObservationSection(OBS),
  visible:rows.visible, unchanged:before===JSON.stringify(OBS)
}));
''')
    assert result["visible"] == 1 and result["unchanged"] is True
    assert 'headers="mo-col-reason"' in result["html"]
    assert 'headers="mo-col-history"' in result["html"]
    assert 'class="mo-mobile-label"' in result["html"]
    assert 'Not enough history' in result["html"]
    assert 'role="row"' in result["html"] and 'role="cell"' in result["html"]
    assert 'role="table"' in result["section"]
    assert 'Available / minimum' in result["section"]
    assert '可用 / 最低要求' in result["section"]
