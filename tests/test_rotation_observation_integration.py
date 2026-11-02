"""Independent integration regressions for the recovered observation consumer.

All clocks and measurements are fixtures. No users, databases or transports.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from app import mailer
from engine import rotation_events
from lib import rotation_observation_notification as contract
from lib import us_cash_calendar


def notice(n=2.0, d=-1.0, **changes):
    payload = {
        "source":"macro.rotation_observation.v1", "category":"sector_rotation_relative",
        "authority":"notification_only", "kind":"observed_change",
        "observation_id":"rotobs_fixture_new", "previous_observation_id":"rotobs_fixture_previous",
        "pair_id":"xlp_vs_smh", "num":"XLP", "den":"SMH", "event_as_of":"2026-10-22",
        "source_as_of":"2026-10-22", "observed_at":"2026-10-22T22:00:00+00:00",
        "not_after":"2026-10-23T22:00:00+00:00",
        "values":{"sessions":2,"numerator_return_pct":n,"denominator_return_pct":d,
                  "ratio_return_pct":((1+n/100)/(1+d/100)-1)*100},
    }
    return {**payload, **changes}


NOW = datetime(2026,10,22,22,10,tzinfo=timezone.utc)


def ledes(payload):
    composed = mailer.compose_alert(payload,lang="en")
    return composed["blocks"][0]["en"], composed["blocks"][0]["zh"]


@pytest.mark.parametrize("n,d",[(-3,-1),(-9,-2),(-99,-50)])
def test_defensive_leg_falling_more_is_not_relative_shelter(n,d):
    en,zh=ledes(notice(n,d))
    assert "fell more" in en and "absolute and relative returns were negative" in en
    assert "relative shelter" not in en and "relatively stronger" not in en
    assert "跌幅更大" in zh and "相对抗跌" not in zh


@pytest.mark.parametrize("n,d",[(-1,-3),(-2,-9),(-50,-99)])
def test_less_negative_is_only_relative_shelter_not_an_absolute_gain(n,d):
    en,zh=ledes(notice(n,d))
    assert "relative shelter only, not an absolute gain" in en
    assert "仅相对抗跌" in zh and "不代表绝对收益为正" in zh


@pytest.mark.parametrize("n,d",[(-1,-1),(-2,-2),(-50,-50)])
def test_equal_losses_are_not_labelled_more_less_or_shelter(n,d):
    en,zh=ledes(notice(n,d))
    assert "Both fell equally" in en
    assert "fell more" not in en and "fell less" not in en and "relative shelter" not in en
    assert "两者跌幅相同" in zh


def test_both_flat_are_not_weaker_or_falling():
    en,zh=ledes(notice(0,0))
    assert "Both were flat" in en and "weaker" not in en and "Both fell" not in en
    assert "两者均持平" in zh


@pytest.mark.parametrize("n,d,symbol",[(0,-1,"XLP"),(0,1,"XLP"),(1,0,"SMH"),(-1,0,"SMH")])
def test_flat_leg_is_explicit_without_invented_direction(n,d,symbol):
    en,_=ledes(notice(n,d));assert f"{symbol} was flat" in en


def test_equal_gains_are_not_called_relative_weakness():
    en,zh=ledes(notice(2,2))
    assert "neither leg outperformed" in en and "weaker" not in en
    assert "两者表现相同" in zh


def test_tolerance_does_not_turn_equal_absolute_legs_into_relative_advantage():
    payload=notice(-1,-1);payload["values"]["ratio_return_pct"]=1e-7
    contract.validate(payload)
    en,_=ledes(payload)
    assert "Both fell equally" in en and "relative shelter" not in en


@pytest.mark.parametrize("field",["numerator_return_pct","denominator_return_pct","ratio_return_pct"])
def test_unrepresentable_integer_returns_fail_closed_without_escaping_drain(field):
    payload=notice();payload["values"][field]=10**1000
    with pytest.raises(ValueError):contract.validate(payload)
    verdict=contract.evaluate(payload,now_utc=NOW)
    assert verdict.action=="unevaluable" and verdict.reason==contract.REASON_INVALID
    with pytest.raises(ValueError):mailer.compose_alert(payload)


@pytest.mark.parametrize("symbol",["XLP\n","XLP\r\n","XLP\t","XLP "])
def test_symbol_match_covers_the_entire_input(symbol):
    with pytest.raises(ValueError):contract.validate(notice(num=symbol))


@pytest.mark.parametrize("field",["observed_at","not_after"])
def test_timezone_normalization_overflow_is_a_validation_error(field):
    payload=notice(**{field:"0001-01-01T00:00:00+14:00"})
    with pytest.raises(ValueError):contract.validate(payload)
    assert contract.evaluate(payload,now_utc=NOW).action=="unevaluable"


def test_unrepresentable_injected_utc_clock_is_unevaluable():
    now=datetime(1,1,1,tzinfo=timezone(timedelta(hours=14)))
    assert contract.evaluate(notice(),now_utc=now).status==contract.UNEVALUABLE


@pytest.mark.parametrize("missing",["values","source_as_of"])
def test_withdrawal_requires_explicit_nullable_fields(missing):
    payload=notice(kind="data_withdrawal",values=None,source_as_of=None)
    del payload[missing]
    with pytest.raises(ValueError):contract.validate(payload)


def test_previous_reference_cannot_point_to_itself():
    payload=notice();payload["previous_observation_id"]=payload["observation_id"]
    with pytest.raises(ValueError):contract.validate(payload)


@pytest.mark.parametrize("bad",["2026-10-22",datetime(2026,10,22),1,True])
def test_calendar_wrong_return_type_is_unknown_not_current(monkeypatch,bad):
    monkeypatch.setattr(us_cash_calendar,"expected_last_session",lambda _:bad)
    assert contract.evaluate(notice(),now_utc=NOW).status==contract.UNEVALUABLE


def test_email_target_is_existing_static_mount_not_async_insertion():
    assert mailer.ROTATION_EVIDENCE_URL=="https://www.mastermind-x.com/sector_central.html#rc-events-mount"
    payload=notice(evidence_url="https://attacker.invalid/",url="javascript:alert(1)")
    composed=mailer.compose_alert(payload)
    buttons=[b for b in composed["blocks"] if b.get("kind")=="button"]
    assert [b["url"] for b in buttons]==[mailer.ROTATION_EVIDENCE_URL]


def context(session, n, d):
    end=datetime.fromisoformat(session).date()
    start=us_cash_calendar.last_session_on_or_before(
        us_cash_calendar.last_session_on_or_before(end-timedelta(days=1))-timedelta(days=1))
    values=notice(n,d)["values"]
    return {"schema":"rotation_early_context/v1","definition_id":"rotation_early_context/1",
            "display_only":True,"as_of":session,"pairs":[{
                "schema":"ratio_lens.short_horizon.v1","context_group":"defensive_sector",
                "pair_id":"xlp_vs_smh","num":"XLP","den":"SMH","eligible_2s":True,
                "requested_as_of":session,"value_as_of":session,
                "horizons":{"2s":{**values,"eligible":True,"start":start.isoformat(),"end":session}}}]}


def test_actual_source_receipt_passes_consumer_and_real_mail_composition():
    baseline=rotation_events.advance_early_observation_history(
        None,context("2026-10-21",-1,1),observed_at=datetime(2026,10,21,22,tzinfo=timezone.utc))
    current=rotation_events.advance_early_observation_history(
        baseline["state"],context("2026-10-22",2,-1),observed_at=NOW)
    payload=current["records"][0]["notification"]
    assert contract.evaluate(payload,now_utc=NOW).status==contract.OK
    en,zh=ledes(payload)
    assert "XLP returned +2.00%" in en and "SMH returned -1.00%" in en
    assert "+3.03%" in en and "+3.03%" in zh
    later=rotation_events.advance_early_observation_history(
        current["state"],{},observed_at=NOW+timedelta(minutes=1))
    withdrawal=later["records"][0]["notification"]
    assert contract.evaluate(withdrawal,now_utc=NOW+timedelta(minutes=1)).status==contract.OK
    assert withdrawal["values"] is None
    assert "+2.00%" not in ledes(withdrawal)[0]


@pytest.mark.parametrize("acked,checked,expected",[
    (["fif_saved_issuer"],False,["fif_saved_issuer","sector_rotation_relative"]),
    (["fif_saved_issuer","sector_rotation_relative"],True,["fif_saved_issuer"]),
    ([],False,["sector_rotation_relative"]),
])
def test_real_category_click_preserves_topics_owned_by_other_surfaces(acked,checked,expected):
    import json
    import shutil
    import subprocess
    from pathlib import Path

    node=shutil.which("node")
    assert node is not None, "Node is required for the executable preference event contract"
    root=Path(__file__).resolve().parents[1]
    code=(root/"templates/account.js").read_text()
    start=code.index("function onAlertCat(")
    end=code.index("function onAlertTz(",start)
    function=code[start:end]
    driver="""
const vm = require('node:vm');
const request = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const row = { attrs: {'data-cat': 'sector_rotation_relative', 'aria-checked': String(request.checked)},
  getAttribute(k) { return this.attrs[k]; }, setAttribute(k,v) { this.attrs[k] = v; } };
const saved = [];
const context = vm.createContext({
  document: { querySelectorAll: () => [row] },
  _ackedAlerts: () => ({alert_categories: request.acked, alert_email_optin: false}),
  persistAlertPref: (key, value, success) => { saved.push({key, value}); success(); },
  setMsg: () => {}, T: (en) => en, _syncAlertControl: () => {},
});
vm.runInContext(request.code + '\\nglobalThis.invoke = onAlertCat;', context);
context.invoke(row);
process.stdout.write(JSON.stringify(saved));
"""
    completed=subprocess.run([node,"-e",driver],input=json.dumps({"code":function,"acked":acked,"checked":checked}),
                             capture_output=True,text=True,timeout=20,check=False)
    assert completed.returncode==0,completed.stderr
    saved=json.loads(completed.stdout)
    assert len(saved)==1 and saved[0]["key"]=="alert_categories"
    assert sorted(saved[0]["value"])==sorted(expected)
    # Selecting a topic cannot implicitly enable email delivery.
    assert all(entry["key"]!="alert_email_optin" for entry in saved)
    assert (root/"templates/account.js").read_bytes()==(root/"site/account.js").read_bytes()
