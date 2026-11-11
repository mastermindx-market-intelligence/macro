"""Exact Signal Lab evidence destination for alert trust."""
from __future__ import annotations

from datetime import date

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
