"""Display contract for the China A-Share Mechanics page (templates/china_mechanics.html.j2).

The page renders a vm assembled by scripts/build_china_mechanics.py. These tests render the
real template from a synthetic vm shaped like the committed records
(site/chinastatedata/participation.json, cycle_phase.json, data/china_cycle_phase/*.parquet):
  - the Participation header dates the row its numbers come from (participation.json `date`),
    not the participation tape tail, and prints the producer's own snapshot_note;
  - the Phase-Call Track Record prints all four ledger outcomes, including unresolved calls;
  - the Current Phase block anchors "Days in phase" to its start date and the previous phase.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402

import scripts.build_china_mechanics as bcm  # noqa: E402
from engine import i18n  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_NOTE = "core legs null on 2026-10-16; publishing last fully-populated row (2026-09-29)"
_LEDGER = {"total_graded": 22902, "held": 8142, "fired": 1975, "indeterminate": 12785}
_PART_H2 = '<span class="l-zh">参与度 — 谁在交易、热度几何</span></h2>'


def _vm(latest: dict | None = None, tape_as_of: str = "2026-10-16",
        phase: dict | None = None) -> dict:
    lpl = {"date": "2026-09-29", "qvix": 17.2, "regime": "dormant", "who_controls": "mixed",
           "risk": "low", "contradictions": [], "evidence": []}
    lpl.update(latest or {})
    ph = {"current": {"phase": "GRINDING_BEAR", "confidence": 0.667, "asof": "2026-10-16",
                      "evidence": ["turnover_z20_null"]},
          "phase_strip": [], "era_table": [], "ledger_summary": dict(_LEDGER),
          "catalog": bcm.PHASE_CATALOG, "days_in_phase": 16, "phase_started": "2026-09-25",
          "prev_phase": "REPAIR", "prev_phase_name": bcm._phase_meta("REPAIR"),
          "current_meta": bcm._phase_meta("GRINDING_BEAR"), "next_phase": "REPAIR",
          "next_meta": bcm._phase_meta("REPAIR")}
    ph.update(phase or {})
    return {
        "built": "TEST", "as_of": "2026-10-16", "authority": "context_only",
        "state_reading": {"en": "", "zh": ""}, "phase_catalog": bcm.PHASE_CATALOG,
        "participation": {"turnover_z20": [], "margin_balance": [], "margin_chg_5d": [],
                          "southbound_z": [], "qvix": [], "latest": lpl, "as_of": tape_as_of},
        "limits": {"lup_series": [], "ldn_series": [], "fsr_series": [], "lianban_series": [],
                   "latest_events": [], "latest_date": None, "latest_agg": {}, "as_of": None},
        "phase": ph,
        "policy": {"policy_impulse": None, "transmission_channel": [], "recent_events": [],
                   "staleness": {}, "asof": None},
        "cross_market": {"yield_curve": {}, "cgb_curve": {}, "usdcnh": {}, "dxy": None,
                         "as_of": None, "data_gaps": []},
        "data_gaps": [],
    }


def _render(vm: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env.get_template("china_mechanics.html.j2").render(**vm)


def _between(html: str, start: str, end: str) -> str:
    i = html.index(start)
    return html[i + len(start):html.index(end, i)]


def _part_chips(html: str) -> list[str]:
    hdr = _between(html, _PART_H2, "</div>")
    return hdr.split('<span class="stale-chip"')[1:]


def _part_intro(html: str) -> str:
    return _between(html, _PART_H2, '<div class="heat-gauge-row">')


def _ledger(html: str) -> str:
    return _between(html, '<span class="l-en">Phase-Call Track Record</span>', "<!-- Era Table")


def _phase_block(html: str) -> str:
    return _between(html, '<span class="l-en">Current Phase</span>',
                    '<div style="flex:1;min-width:200px">')


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).strip()


# --------------------------------------------------------------------------- #
#  Participation header: snapshot date, tape-tail chip, snapshot_note        #
# --------------------------------------------------------------------------- #

def test_participation_header_uses_the_snapshot_date_not_the_tape_tail():
    chips = _part_chips(_render(_vm()))
    assert len(chips) == 2, chips
    assert "2026-09-29" in chips[0] and "2026-10-16" not in chips[0]
    assert "2026-10-16" in chips[1] and "2026-09-29" not in chips[1]
    assert '<span class="l-en">charts through</span>' in chips[1]
    assert '<span class="l-zh">图表截至</span>' in chips[1]


def test_snapshot_note_is_rendered_when_the_producer_wrote_one():
    intro = _part_intro(_render(_vm(latest={"snapshot_note": _NOTE})))
    assert intro.count(_NOTE) == 1
    assert '<span class="l-en">Data note</span><span class="l-zh">数据说明</span>' in intro


def test_no_snapshot_note_no_extra_chip():
    html = _render(_vm(latest={"date": "2026-10-16"}))
    chips = _part_chips(html)
    assert len(chips) == 1 and "2026-10-16" in chips[0]
    intro = _part_intro(html)
    assert "Data note" not in intro and "数据说明" not in intro


def test_zh_and_en_both_carry_the_snapshot_date():
    chip = _part_chips(_render(_vm()))[0]
    en_view = re.sub(r'<span class="l-zh">.*?</span>', "", chip)
    zh_view = re.sub(r'<span class="l-en">.*?</span>', "", chip)
    assert "2026-09-29" in en_view and "2026-09-29" in zh_view


# --------------------------------------------------------------------------- #
#  Phase-Call Track Record: four outcomes                                     #
# --------------------------------------------------------------------------- #

def test_ledger_panel_renders_the_unresolved_count():
    block = _ledger(_render(_vm()))
    assert ">12785</div>" in block
    assert '<span class="l-en">Unresolved</span><span class="l-zh">未决</span>' in block
    assert "input metric was missing" in block


def test_ledger_counts_sum_to_total_graded():
    block = _ledger(_render(_vm()))
    vals = [int(v) for v in re.findall(r'<div class="lv [a-z-]+">(\d+)</div>', block)]
    assert vals == [22902, 8142, 1975, 12785]
    assert vals[0] == sum(vals[1:])


def test_builder_fallback_includes_indeterminate(tmp_path, monkeypatch):
    state = tmp_path / "site" / "chinastatedata"
    state.mkdir(parents=True)
    (state / "cycle_phase.json").write_text(json.dumps({"phase": "GRINDING_BEAR",
                                                        "asof": "2026-10-16"}))
    ledger_dir = tmp_path / "data" / "china_cycle_phase"
    ledger_dir.mkdir(parents=True)
    outcomes = ["held", "held", "fired", "indeterminate", "indeterminate", "indeterminate"]
    pd.DataFrame({"outcome": outcomes}).to_parquet(ledger_dir / "falsifier_ledger.parquet")
    monkeypatch.setattr(bcm, "_ROOT", tmp_path)
    monkeypatch.setattr(bcm, "_CHINASTATE", state)
    ls = bcm._phase_panel()["ledger_summary"]
    assert ls == {"held": 2, "fired": 1, "indeterminate": 3, "total_graded": 6}


def test_unresolved_label_avoids_banned_vocabulary():
    block = _ledger(_render(_vm())).lower()
    for word in ("falsifier", "证伪", "refuted", "probability", "概率"):
        assert word not in block, word


# --------------------------------------------------------------------------- #
#  Current Phase: start date and previous phase                               #
# --------------------------------------------------------------------------- #

def test_phase_panel_prints_the_start_date():
    since = '<span class="l-en">Since</span><span class="l-zh">始于</span> 2026-09-25'
    assert since in _phase_block(_render(_vm()))
    no_prev = _render(_vm(phase={"prev_phase": None, "prev_phase_name": {}}))
    assert since in _phase_block(no_prev)


def test_phase_panel_names_the_previous_phase_from_the_catalog():
    block = _phase_block(_render(_vm()))
    assert '<span class="l-en">Previous phase</span><span class="l-zh">前一阶段</span>' in block
    assert '<span class="l-en">Repair</span><span class="l-zh">修复期</span>' in block
    assert not re.search(r"\bREPAIR\b", _text(block))
    no_start = _phase_block(_render(_vm(phase={"phase_started": None})))
    assert '<span class="l-en">Repair</span><span class="l-zh">修复期</span>' in no_start


def test_missing_start_or_prev_renders_no_empty_label():
    no_start = _phase_block(_render(_vm(phase={"phase_started": None})))
    no_prev = _phase_block(_render(_vm(phase={"prev_phase": None, "prev_phase_name": {}})))
    assert "Since" not in no_start and "始于" not in no_start
    assert "Previous phase" not in no_prev and "前一阶段" not in no_prev
    for block in (no_start, no_prev):
        assert "None" not in block
        assert not re.search(r":\s*</div>", block)
        assert not re.search(r"<div[^>]*>\s*</div>", block)


def test_days_in_phase_still_rendered_unchanged():
    block = _phase_block(_render(_vm()))
    assert ('<span class="l-en">Days in phase</span><span class="l-zh">已持续天数</span>: 16'
            in block)


# --------------------------------------------------------------------------- #
#  Participation labels: producer vocabularies, zh hero, heat-label row       #
# --------------------------------------------------------------------------- #

_EVIDENCE = ["turnover_z20=-2.25", "fin_pct_float=2.67%",
             "broker_rs=0.0700 (positive, sector leading)",
             "qvix_z=-1.03 (inverted-semantics: high=stress)"]
_CJK = re.compile(r"[一-鿿]")


def _lvm(latest: dict | None = None) -> dict:
    vm = _vm(latest=latest)
    vm["participation_labels"] = bcm._participation_labels(vm["participation"]["latest"])
    return vm


def _label_row(html: str) -> str:
    return _between(html, '<div class="heat-label-row">', "</div>")


def _hero(who: str) -> dict:
    lpl = {"date": "2026-09-29", "qvix": 17.2, "regime": "dormant", "who_controls": who,
           "risk": "low", "turnover_z20": -2.245}
    return bcm._compose_state_reading({"latest": lpl}, {}, {})


def test_zh_hero_never_emits_a_raw_risk_enum():
    zh = _hero("mixed")["zh"]
    assert "整体风险环境为low" not in zh
    assert re.search(r"整体风险环境为[一-鿿]+。", zh), zh


def test_every_producer_enum_value_has_a_label_pair():
    from engine import china_participation as cp
    for field, values in (("regime", cp.REGIME_VALUES), ("who_controls", cp.WHO_CONTROLS_VALUES),
                          ("risk", cp.RISK_VALUES)):
        for slug in values:
            key = {"who_controls": "who"}.get(field, field)
            pair = bcm._participation_labels({field: slug})[key]
            assert pair["en"] and "_" not in pair["en"], (field, slug, pair)
            assert _CJK.search(pair["zh"]), (field, slug, pair)
            assert pair["zh"] not in (slug, slug.replace("_", " ").title()), (field, slug)


def test_who_controls_zh_is_composition_not_sentiment():
    zh = bcm._participation_labels({"who_controls": "mixed"})["who"]["zh"]
    assert "喜忧参半" not in zh and _CJK.search(zh)


def test_regime_and_who_render_from_the_committed_snapshot():
    row = _label_row(_render(_lvm()))
    zh = " ".join(re.findall(r'<span class="l-zh">(.*?)</span>', row, re.S))
    assert "参与制度：沉寂" in zh and "控盘方：多方混合" in zh and "风险：低" in zh
    assert "Dormant" not in zh and "喜忧参半" not in zh


def test_state_proxy_is_not_rendered_as_no_single_group():
    proxy = _hero("state_proxy")
    for other in ("mixed", "unclear"):
        assert proxy["en"] != _hero(other)["en"] and proxy["zh"] != _hero(other)["zh"]
    assert _hero("mixed")["en"] != _hero("unclear")["en"]


def test_participation_evidence_chips_render():
    row = _label_row(_render(_lvm(latest={"evidence": _EVIDENCE})))
    for s in _EVIDENCE:
        assert s in row, s
    assert "The legs this participation reading rests on" in row


def test_empty_evidence_renders_no_chip_row():
    row = _label_row(_render(_lvm()))
    assert 'data-part="evidence"' not in row and "null-chip" not in row
    assert "The legs this participation reading rests on" not in row


def test_evidence_strings_are_not_rewritten():
    row = _label_row(_render(_lvm(latest={"evidence": _EVIDENCE})))
    chips = re.findall(r'<span class="null-chip">(.*?)</span>', row)
    assert chips == _EVIDENCE


def test_contradictions_block_still_renders_when_present():
    row = _label_row(_render(_lvm(latest={
        "evidence": _EVIDENCE,
        "contradictions": [{"a": "turnover", "b": "margin", "detail": "legs disagree"}]})))
    assert '<span class="null-chip">turnover vs margin — legs disagree</span>' in row
    assert row.index('data-part="evidence"') < row.index("turnover vs margin")


def test_build_payload_carries_the_participation_labels(monkeypatch):
    lpl = _vm()["participation"]["latest"]
    monkeypatch.setattr(bcm, "_read_json", lambda p: {})
    monkeypatch.setattr(bcm, "_participation_panel", lambda: {"latest": lpl})
    for name in ("_limit_panel", "_phase_panel", "_policy_panel", "_cross_market_panel"):
        monkeypatch.setattr(bcm, name, lambda: {})
    labels = bcm.build_payload()["participation_labels"]
    assert labels["regime"] == {"en": "Dormant", "zh": "沉寂"}
    assert labels["risk"] == {"en": "low", "zh": "低"}
