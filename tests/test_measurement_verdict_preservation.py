"""Preserved Research Verdicts section on Calibration Lab (V1, display-tier)."""

from __future__ import annotations

import ast
import json
import re
import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

REGISTRY_PATH = REPO / "config" / "verdict_preservation_registry.json"
EXPECTED_IDS = [
    "c2-regime-indicator",
    "b1-cross-asset",
    "f1-temporal-grain",
    "e-scoped-null",
    "d0-point-in-time",
    "c1-upstream",
    "product-boundary",
    "c2-counterfactual",
]
DNC_EN = [
    "C2 round-1 NOT_SUPPORTED headline",
    "F1 AUC and severe-share figures read as probabilities",
    "D0 E* and week-40 numerics",
    "any Trend Persistence calibrated profile or shadow field",
]

STANCE_EN = "Research context — do not use as a trading signal."
STANCE_ZH = "研究背景 — 请勿作为交易信号使用。"


def _render(**overrides) -> str:
    from jinja2 import Environment, FileSystemLoader, meta

    templates_dir = REPO / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    try:
        from engine import i18n

        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)

    context = {
        "page_title": "Test",
        "engines": [],
        "gate_ledger": [],
        "accruing_experiments": [],
        "cone_recalibration": {},
        "collinearity": {},
        "sync_gauge": {"available": False},
        "provenance": {"epochs": {}, "fingerprint_consistent": True},
        "build_date": date.today().isoformat(),
        "generated_at": "2026-07-06T00:00:00Z",
        "n_stamps_grand_total": 0,
        "truth_ledger": {"available": False},
        "accrual_clocks": [],
        "prediction_layer": {"available": False},
        "coverage_matrix": {"available": False, "rows": []},
        "grading_closure": {"available": False},
        "trial_budgets": {"available": False},
        "rule_experiments": {"available": False},
        "qledger_reliability": {"available": False},
        "research_implications": {
            "schema": "mastermind.research_implication_cards/v1",
            "cards": [],
        },
        "imce_prospective": {"available": False},
        "verdict_preservation": {"available": False},
        "seasonality_record": {
            "available": False,
            "registered": 0,
            "graded": 0,
            "next_close": None,
        },
        "etf_board_windows": {"available": False},
    }
    context.update(overrides)

    source = (templates_dir / "measurement.html.j2").read_text(encoding="utf-8")
    needed = meta.find_undeclared_variables(env.parse(source))
    internal_sets = set(re.findall(r"\{%-?\s*set\s+([A-Za-z_]\w*)", source))
    missing = sorted(needed - set(context) - set(env.globals) - internal_sets)
    assert not missing, f"missing template vars: {missing}"

    template = env.get_template("measurement.html.j2")
    return template.render(**context)


def _vp_section(html: str) -> str:
    start = html.find('id="vp-section"')
    if start == -1:
        return ""
    open_tag = html.rfind("<section", 0, start)
    end = html.find("</section>", start)
    assert end != -1
    return html[open_tag : end + len("</section>")]


def _strip_tags(fragment: str) -> str:
    return re.sub(r"<[^>]+>", " ", fragment)


def test_t1_registry_shape():
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert data["schema"] == "mastermind.verdict_preservation_registry.v1"
    assert data["frozen_at"] == "2026-10-06"
    assert "V0_VERDICT_PRESERVATION_CENSUS" in data["source_census"]
    assert len(data["rows"]) == 8
    assert [r["id"] for r in data["rows"]] == EXPECTED_IDS
    for row in data["rows"]:
        assert row["consume_as"] == "display-tier"
    assert data["do_not_consume_until_repair"] == DNC_EN


def test_t2_pins_on_disk():
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for row in data["rows"]:
        path = REPO / row["source_path"]
        lines = path.read_text(encoding="utf-8").splitlines()
        assert row["status_literal"] in lines[row["source_line"] - 1]


def test_t3_build_available():
    from engine.verdict_preservation import build_verdict_preservation

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    c2_actual = [r for r in data["rows"] if r["verdict_key"] == "C2" and r["actual"]]
    assert len(c2_actual) == 1
    built = build_verdict_preservation(REPO)
    assert built["available"] is True
    assert built["row_count"] == 8
    assert built["pin_ok_count"] == 8


def test_t4_counterfactual_card():
    from engine.verdict_preservation import build_verdict_preservation

    built = build_verdict_preservation(REPO)
    cf = next(r for r in built["rows"] if r["id"] == "c2-counterfactual")
    assert cf["actual"] is False
    assert cf["status_class"] == "counterfactual"
    html = _render(verdict_preservation=built)
    sec = _vp_section(html)
    assert "vp-cf" in sec
    assert "counterfactual — not a verdict" in sec
    assert "反事实 — 非结论" in sec
    c2_card = sec.split('id="vp-c2-regime-indicator"', 1)[1].split("</article>", 1)[0]
    cf_card = sec.split('id="vp-c2-counterfactual"', 1)[1].split("</article>", 1)[0]
    c2_badge = re.search(r'class="([^"]*vp-s-[^"]*)"', c2_card)
    cf_badge = re.search(r'class="([^"]*vp-s-[^"]*)"', cf_card)
    assert c2_badge and cf_badge
    assert c2_badge.group(1) != cf_badge.group(1)


def test_t5_absent_and_invalid_registry(tmp_path: Path):
    from engine.verdict_preservation import build_verdict_preservation

    assert build_verdict_preservation(tmp_path) == {"available": False}
    assert 'id="vp-section"' not in _render(verdict_preservation={"available": False})
    assert 'id="vp-section"' not in _render(verdict_preservation=None)

    bad = tmp_path / "config"
    bad.mkdir()
    (bad / "verdict_preservation_registry.json").write_text(
        json.dumps({"schema": "wrong", "rows": []}), encoding="utf-8"
    )
    assert build_verdict_preservation(tmp_path) == {"available": False}

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    broken = json.loads(json.dumps(data))
    for row in broken["rows"]:
        if row["id"] == "c2-counterfactual":
            row["actual"] = True
    cfg = tmp_path / "config"
    cfg.mkdir(exist_ok=True)
    (cfg / "verdict_preservation_registry.json").write_text(
        json.dumps(broken), encoding="utf-8"
    )
    assert build_verdict_preservation(tmp_path) == {"available": False}


def test_t6_pin_drift(tmp_path: Path):
    from engine.verdict_preservation import build_verdict_preservation

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "verdict_preservation_registry.json").write_text(json.dumps(data), encoding="utf-8")
    drift_id = "b1-cross-asset"
    drift_row = next(r for r in data["rows"] if r["id"] == drift_id)
    src = tmp_path / drift_row["source_path"]
    src.parent.mkdir(parents=True)
    src.write_text("line without literal\n", encoding="utf-8")
    for row in data["rows"]:
        if row["id"] == drift_id:
            continue
        p = tmp_path / row["source_path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        lines = (REPO / row["source_path"]).read_text(encoding="utf-8").splitlines()
        p.write_text("\n".join(lines), encoding="utf-8")

    built = build_verdict_preservation(tmp_path)
    assert built["available"] is True
    drift = next(r for r in built["rows"] if r["id"] == drift_id)
    assert drift["pin_ok"] is False
    others = [r for r in built["rows"] if r["id"] != drift_id]
    assert all(r["pin_ok"] for r in others)

    html = _render(verdict_preservation=built)
    card = html.split(f'id="{drift["anchor"]}"', 1)[1].split("</article>", 1)[0]
    assert 'data-pin-ok="false"' in card
    assert "Source re-check needed" in card
    assert "来源待复核" in card
    assert "vp-s-" not in card
    assert drift_row["status_literal"] not in card


def test_t7_card_order_and_ids():
    from engine.verdict_preservation import build_verdict_preservation

    built = build_verdict_preservation(REPO)
    html = _render(verdict_preservation=built)
    articles = re.findall(r'<article class="vp-card[^"]*" id="(vp-[^"]+)"', html)
    assert articles == ["vp-" + i for i in EXPECTED_IDS]
    vp_ids = re.findall(r'id="(vp-[^"]+)"', _vp_section(html))
    assert len(vp_ids) - 1 == 8


def test_t8_en_zh_parity():
    from engine.verdict_preservation import build_verdict_preservation

    html = _render(verdict_preservation=build_verdict_preservation(REPO))
    sec = _vp_section(html)
    en = len(re.findall(r'class="l-en"', sec))
    zh = len(re.findall(r'class="l-zh"', sec))
    assert en == zh
    for m in re.finditer(r'class="l-zh"[^>]*>([^<]+)</span>', sec):
        assert re.search(r"[\u4e00-\u9fff]", m.group(1))


def test_t9_banned_words():
    from engine.verdict_preservation import build_verdict_preservation

    html = _render(verdict_preservation=build_verdict_preservation(REPO))
    sec = _vp_section(html)
    text = _strip_tags(sec)
    assert not re.search(r"[\U0001f300-\U0001faff\u2600-\u27bf]", text)
    lowered = text.lower()
    assert "validated" not in lowered
    assert "已验证" not in text
    assert not re.search(r"\bfalsif", lowered)
    assert not re.search(r"\brefut", lowered)
    assert "证伪" not in text
    assert "intraday" not in lowered
    assert "日内" not in text

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    boundary = next(r for r in data["rows"] if r["id"] == "product-boundary")
    scrubbed = text.replace(boundary["qualifiers_en"], "").replace(boundary["qualifiers_zh"], "")
    scrub_lower = scrubbed.lower()
    assert not re.search(r"\branked\b", scrub_lower)
    assert not re.search(r"\branking\b", scrub_lower)
    assert not re.search(r"\bstrongest\b", scrub_lower)
    assert "signal strength" not in scrub_lower
    assert not re.search(r"\bconviction\b", scrub_lower)
    assert "position siz" not in scrub_lower
    assert not re.search(r"\bsizing\b", scrub_lower)
    assert "排名" not in scrubbed
    assert "仓位" not in scrubbed


def test_t10_stance():
    from engine.verdict_preservation import build_verdict_preservation

    sec = _vp_section(_render(verdict_preservation=build_verdict_preservation(REPO)))
    assert STANCE_EN in sec
    assert STANCE_ZH in sec


def test_t11_template_order():
    source = (REPO / "templates" / "measurement.html.j2").read_text(encoding="utf-8")
    assert source.index('id="vp-section"') > source.index("{# end #ric-section #}")


def test_t12_engine_imports_stdlib_only():
    tree = ast.parse((REPO / "engine" / "verdict_preservation.py").read_text(encoding="utf-8"))
    banned = {
        "socket",
        "urllib",
        "http",
        "requests",
        "httpx",
        "subprocess",
        "git",
        "pygit2",
        "aiohttp",
        "ftplib",
        "smtplib",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned


def test_t13_copy_budgets():
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for row in data["rows"]:
        tokens = [t for t in row["plain_en"].split() if t != "—"]
        assert len(tokens) <= 14
        assert "watch" in row["plain_en"].lower() or "don't chase" in row["plain_en"].lower()
        assert len(row["plain_zh"]) <= 20


_PREFIX_DIRS = {"WS": "workstreams", "DEC": "decisions", "DSC": "discoveries"}


def _copy_registry_sources_to_tmp(tmp_path: Path, data: dict) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "verdict_preservation_registry.json").write_text(json.dumps(data), encoding="utf-8")
    for row in data["rows"]:
        p = tmp_path / row["source_path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text((REPO / row["source_path"]).read_text(encoding="utf-8"), encoding="utf-8")


def test_t14_owner_ref_colon_form_resolves():
    from engine.verdict_preservation import _OWNER_REF_RE

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for row in data["rows"]:
        owner_ref = row["owner_ref"]
        assert _OWNER_REF_RE.fullmatch(owner_ref)
        prefix, key = owner_ref.split(":", 1)
        if prefix == "DNR":
            dnr = (REPO / "research" / "DO_NOT_REBUILD.md").read_text(encoding="utf-8")
            assert f"| {key} |" in dnr
            continue
        subdir = _PREFIX_DIRS[prefix]
        record_path = REPO / "agentos" / subdir / f"{prefix}-{key}.md"
        assert record_path.is_file()
        text = record_path.read_text(encoding="utf-8")
        assert f"key: {key}" in text.splitlines()
        if prefix == "WS":
            parts = text.split("---", 2)
            assert len(parts) >= 3
            fm = parts[1]
            owns = False
            in_owns = False
            for line in fm.splitlines():
                if line.strip() == "owns_paths:":
                    in_owns = True
                    continue
                if in_owns:
                    if line.startswith("  - "):
                        prefix_path = line[4:].strip()
                        if row["source_path"].startswith(prefix_path):
                            owns = True
                            break
                    elif line and not line.startswith(" "):
                        in_owns = False
            assert owns


def test_t15_owner_ref_invalid_fails_closed(tmp_path: Path):
    from engine.verdict_preservation import build_verdict_preservation

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    _copy_registry_sources_to_tmp(tmp_path, data)
    assert build_verdict_preservation(tmp_path)["available"] is True

    bad_values = [
        "",
        "macro PR #6805 (Prophet V4 handoff)",
        "ws:prophet-regime-timeframe-research",
        "WS:",
        "WS:PROPHET REGIME",
    ]
    for bad in bad_values:
        trial = json.loads(json.dumps(data))
        trial["rows"][0]["owner_ref"] = bad
        _copy_registry_sources_to_tmp(tmp_path, trial)
        assert build_verdict_preservation(tmp_path) == {"available": False}


def test_t16_owner_ref_only_in_receipt():
    from engine.verdict_preservation import build_verdict_preservation

    needle = "WS:PROPHET-REGIME-TIMEFRAME-RESEARCH"
    html = _render(verdict_preservation=build_verdict_preservation(REPO))
    sec = _vp_section(html)
    assert sec.count(needle) == 8
    stripped = re.sub(r'<dl class="vp-receipt">.*?</dl>', "", sec, flags=re.DOTALL)
    assert stripped.count(needle) == 0
