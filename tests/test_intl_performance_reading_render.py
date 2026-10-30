"""Actual price/FX owner over synthetic configured inputs, no data acquisition."""
from copy import deepcopy
import pandas as pd
from bs4 import BeautifulSoup
from engine import intl_inputs
from engine.intl_performance import usd_leaderboard,usd_series
from tests.test_intl_workspace_integration import render_fixture
from tests.test_intl_rotation_reading_render import rotation_fixture


def performance_fixture(short_only=False):
    countries=intl_inputs.countries();dates=pd.bdate_range("2024-01-02",periods=260);frame=pd.DataFrame(index=dates)
    for cc,local,fx in [("JP",5.,-3.),("KR",0.,0.),("TW",1.,0.)]:
        c=countries[cc];frame[c["index"]]=[100.]*259+[100*(1+local/100)]
        frame[c["fx"]]=[1.]*259+[1/(1+fx/100) if c.get("fx_invert") else 1+fx/100]
        if short_only or cc=="TW":frame.loc[dates[:-40],[c["index"],c["fx"]]]=float("nan")
    rows=usd_leaderboard(frame,{cc:usd_series(cc,frame) for cc in ["JP","KR","TW"]})
    return {"leaderboard":rows,"horizons":[{"key":key,"en":en,"zh":zh} for key,en,zh in [("1m","1M","1月"),("12m","12M","12月")]]}


def test_actual_fx_contribution_is_percentage_points_not_currency_return():
    p=performance_fixture();rows={r["cc"]:r for r in p["leaderboard"]};v=rows["JP"]["returns"]["12m"]
    assert v=={"usd":1.8,"local":5.,"fx":-3.2}
    assert rows["KR"]["returns"]["12m"]=={"usd":0.,"local":0.,"fx":0.}
    assert "12m" not in rows["TW"]["returns"] and "1m" in rows["TW"]["returns"]
    html=render_fixture(perf=p)
    assert "FX contribution (percentage points)" in html and "汇率贡献（百分点）" in html
    assert "fast 20d momentum" not in html


def test_performance_anchor_is_named_focusable_and_payload_unchanged():
    p=performance_fixture();before=deepcopy(p);soup=BeautifulSoup(render_fixture(perf=p,rotation_ranks=rotation_fixture()),"html.parser")
    target=soup.select_one("#lb-board")
    assert target["tabindex"]=="-1" and target["aria-labelledby"]=="intl-performance-heading"
    assert soup.select_one("#intl-performance-heading")
    assert p==before


def test_absent_performance_has_no_target_or_fake_returns():
    soup=BeautifulSoup(render_fixture(),"html.parser")
    assert not soup.select("#lb-board")
    assert not soup.select('[data-im-library-tool="performance_currency"] a[href="#lb-board"]')
