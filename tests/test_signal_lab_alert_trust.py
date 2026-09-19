"""Exact Signal Lab evidence destination for alert trust."""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from engine import i18n, signal_lab
from lib import config


def _gate():
    return {
        "ok": True, "asof": "2026-09-10", "all_pass": False,
        "holdout_start": "2024-01-01", "label": "fwd(3d) +-5%",
        "legs": {
            "d2": {"status": "demoted", "pass": False, "dir": "down",
                   "label": "Vol-of-vol jolt (DVOL range)", "floor": 1.5,
                   "min_holdout_n": 30, "lift_holdout": 1.826,
                   "perm_p": 0.4343, "n_fires_holdout": 61},
            "d3": {"status": "demoted", "pass": False, "dir": "down",
                   "label": "SOPR profit-take spike", "floor": 1.3,
                   "min_holdout_n": 30, "lift_holdout": 1.198,
                   "perm_p": 0.4213, "n_fires_holdout": 31},
            "u1": {"status": "insufficient_n", "pass": False, "dir": "up",
                   "label": "SOPR capitulation (wash-out)", "floor": 1.3,
                   "min_holdout_n": 30, "lift_holdout": 1.7,
                   "perm_p": 0.0025, "n_fires_holdout": 14},
        },
    }


def test_scorecard_exposes_exact_btc_impulse_evidence_rows():
    payload = signal_lab.build_scorecard(gate=_gate(), evaluation_date=date(2026, 9, 10))
    block = payload["alert_trust"]
    assert block["present"] is True
    rows = {row["identity"]: row for row in block["rows"]}
    assert set(rows) == {"d2", "d3", "u1", "d2+d3"}
    assert rows["d2"]["anchor"] == "signal-lab-btc-impulse-d2"
    assert rows["d2"]["status"] == "demoted"
    assert rows["d3"]["stats"][0]["lift_holdout"] == 1.198
    assert rows["u1"]["stats"][0]["n_fires_holdout"] == 14
    assert rows["d2+d3"]["status"] == "demoted"
    assert all(row["target"]["bars"] == 3 for row in rows.values())
    assert all(row["model_version"] is None for row in rows.values())
    assert all(row["permitted_use"] == "observation_only" for row in rows.values())


def test_signal_lab_template_renders_stable_exact_anchors_and_plain_current_status():
    payload = signal_lab.build_scorecard(gate=_gate(), evaluation_date=date(2026, 9, 10))
    env = Environment(loader=FileSystemLoader(config.ROOT / "templates"))
    env.filters["min"] = min
    env.globals.update(t=i18n.t, td=i18n.td, tr=i18n.tr, zip=zip)
    html = env.get_template("signal_lab.html.j2").render(**payload)
    for anchor in (
        "signal-lab-btc-impulse-d2", "signal-lab-btc-impulse-d3",
        "signal-lab-btc-impulse-u1", "signal-lab-btc-impulse-d2-d3",
    ):
        assert f'id="{anchor}"' in html
    assert "Current alert evidence" in html
    assert "当前警报证据" in html
    assert "Observation only" in html
    assert "仅作观察" in html
    assert "Model version not declared" in html
    assert "模型版本未声明" in html
    assert "FALSIFIER" not in html and "证伪" not in html


# DYNAMIC LIMIT COPY REGRESSION

def test_eligible_rows_do_not_render_stale_failure_specific_limits():
    gate = _gate()
    for row in gate["legs"].values():
        row.update({
            "status": "leading", "pass": True,
            "lift_holdout": max(float(row["floor"]) + 0.2, 1.5),
            "perm_p": 0.01, "n_fires_holdout": 40,
        })
    gate["all_pass"] = True
    payload = signal_lab.build_scorecard(gate=gate, evaluation_date=date(2026, 9, 10))
    rows = payload["alert_trust"]["rows"]
    assert all(row["current_permitted"] for row in rows)
    forbidden = (
        "does not permit action use", "do not clear the action gate",
        "below the declared minimum", "不允许用于行动", "未通过行动门槛", "低于既定最小值",
    )
    for row in rows:
        copy = (row["limits"] + " " + row["limits_zh"]).lower()
        assert not any(fragment.lower() in copy for fragment in forbidden), row



def test_signal_lab_loads_the_shared_typed_gate_receipt(monkeypatch):
    from engine import signal_evidence

    receipt = {"read_state": "corrupt", "artifact": None, "path": "/typed-corrupt"}
    calls = {"n": 0}

    def load():
        calls["n"] += 1
        return receipt

    monkeypatch.setattr(signal_evidence, "load_btc_gate", load)
    block = signal_lab._build_alert_trust(evaluation_date=date(2026, 9, 10))
    assert calls["n"] == 1
    assert all(row["gate_read_state"] == "corrupt" for row in block["rows"])


def test_signal_lab_exposes_the_append_only_d2_research_projection():
    research = {
        "schema": "btc_d2_forward.v1",
        "status": "matured",
        "entry_asof": "2026-09-17",
        "entry_close": 100.0,
        "source_asof": "2026-09-16",
        "check_after": "2026-09-20",
        "fired": True,
        "trading_authority": False,
        "source_generation_id": "sha256:source",
        "outcome_generation_id": "sha256:outcome",
        "generation_count": 2,
        "outcome": {"matured": True, "fwd_min_pct": -7.0, "fwd_max_pct": 1.0,
                    "down_hit": True},
        "reason": None,
    }
    payload = signal_lab.build_scorecard(
        gate=_gate(), evaluation_date=date(2026, 9, 17), d2_research=research,
    )
    rows = {row["identity"]: row for row in payload["alert_trust"]["rows"]}
    assert rows["d2"]["research_journey"] == research
    assert all(row.get("research_journey") is None for key, row in rows.items() if key != "d2")

    env = Environment(loader=FileSystemLoader(config.ROOT / "templates"))
    env.filters["min"] = min
    env.globals.update(t=i18n.t, td=i18n.td, tr=i18n.tr, zip=zip)
    html = env.get_template("signal_lab.html.j2").render(**payload)
    assert "Prospective research journey" in html
    assert "前瞻研究轨迹" in html
    assert "Raw D2 observation: fired" in html
    assert "原始 D2 观察：已触发" in html
    assert "Matured · down target hit" in html
    assert "已成熟 · 下行目标命中" in html
    assert "Research only — no trading authority" in html
    assert "仅供研究 — 无交易权限" in html
    assert "Observed: 2026-09-16" in html
    assert "观察：2026-09-16" in html
    assert "Entry date: 2026-09-17" in html
    assert "入场日期：2026-09-17" in html
    assert "Entry BTC close: 100.00" in html
    assert "入场 BTC 收盘：100.00" in html
    assert "Entry close: 2026-09-17" not in html
    assert "Grade after: 2026-09-20" in html
    assert "评估日：2026-09-20" in html
    assert "Immutable generations: 2" in html
    assert "不可变代次：2" in html
    soup = BeautifulSoup(html, "html.parser")
    d2_row = soup.find(id="signal-lab-btc-impulse-d2")
    cells = d2_row.find_all("td", recursive=False)
    assert len(cells) == 5
    assert "Prospective research journey" in cells[0].get_text(" ", strip=True)
    assert "Prospective research journey" not in cells[3].get_text(" ", strip=True)


def _render_d2_scorecard(payload):
    env = Environment(loader=FileSystemLoader(config.ROOT / "templates"))
    env.filters["min"] = min
    env.globals.update(t=i18n.t, td=i18n.td, tr=i18n.tr, zip=zip)
    return env.get_template("signal_lab.html.j2").render(**payload)


def test_scorecard_keeps_completed_d2_outcome_inspectable_after_rollover(monkeypatch):
    from engine import btc_impulse_ledger
    from tests.test_btc_d2_research_journey import _rollover_rows
    rows = _rollover_rows()
    monkeypatch.setattr(btc_impulse_ledger, "load", lambda: rows)
    payload = signal_lab.build_scorecard(gate=_gate(), evaluation_date=date(2026, 9, 17))
    d2_row = next(r for r in payload["alert_trust"]["rows"] if r["identity"] == "d2")
    assert d2_row["research_journey"]["status"] == "pending"
    assert d2_row["research_journey"]["last_matured"]["status"] == "matured"
    assert d2_row["current_permitted"] is False
    html = _render_d2_scorecard(payload)
    assert "Most recent completed observation" in html
    assert "最近完成的观察" in html
    assert "Matured · down target hit" in html
    assert "Pending outcome after three future closes" in html
    assert "2024-03-03" in html and "2024-03-07" in html


def test_matured_no_fire_observation_is_not_presented_as_a_prediction_miss():
    from engine import btc_d2_research
    from tests.test_btc_d2_research_journey import _capture_available
    import pandas as pd
    _, journey, entry, sig, _ = _capture_available(fired=False)
    full = pd.concat([sig, pd.DataFrame(
        {"close": [98.0, 94.0, 93.0]},
        index=[entry + pd.Timedelta(days=i) for i in (1, 2, 3)],
    )])
    assert btc_d2_research.mature_outcome(journey, full)
    payload = signal_lab.build_scorecard(
        gate=_gate(), evaluation_date=date(2026, 9, 17),
        d2_research=btc_d2_research.project(journey),
    )
    html = _render_d2_scorecard(payload)
    assert "Matured · no signal fired" in html
    assert "已成熟 · 未触发信号" in html
    assert "Matured · down target missed" not in html
    assert "Matured · down target hit" not in html
    assert "Research only — no trading authority" in html


def test_correction_history_is_visible_in_the_actual_d2_cell():
    from engine import btc_d2_research
    from tests.test_btc_d2_research_journey import _rollover_rows, _frames
    from bs4 import BeautifulSoup
    journey = _rollover_rows()[0]["research_d2"]
    entry, sig, dvol = _frames(fired=False)
    assert btc_d2_research.capture_source(
        journey, entry_asof=str(entry.date()), sig_df=sig, dvol_df=dvol,
    )
    projected = btc_d2_research.project(journey)
    payload = signal_lab.build_scorecard(
        gate=_gate(), evaluation_date=date(2026, 9, 17), d2_research=projected,
    )
    html = _render_d2_scorecard(payload)
    cell = BeautifulSoup(html, "html.parser").find(id="signal-lab-btc-impulse-d2")
    assert "Correction history" in cell.get_text()
    assert "修订历史" in cell.get_text()
    assert "Source inputs restated" in cell.get_text()
    assert projected["corrections"][0]["supersedes_generation_id"] in str(cell)
