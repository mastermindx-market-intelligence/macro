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
