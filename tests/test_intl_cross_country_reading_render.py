"""Pure equity-owner scores inside explicit synthetic country metadata."""
from copy import deepcopy
import pandas as pd
from bs4 import BeautifulSoup
from engine import intl_inputs
from engine.intl_equity_risk import equity_risk_all
from tests.test_intl_workspace_integration import render_fixture


def country_fixture():
    dates=pd.bdate_range("2024-01-02",periods=600)
    a=[100+.2*n for n in range(600)];b=a[:-21]+[140. if n%2 else 220. for n in range(20)]+[300.]
    eq=equity_risk_all(pd.DataFrame({"JP":a,"KR":b,"TW":[float("nan")]*520+a[-80:]},index=dates))
    records=[]
    for cc in ["JP","KR","TW"]:
        c=intl_inputs.countries()[cc]
        records.append(dict(cc=cc,name=c["name"],name_zh=c["name_zh"],flag=c["flag"],quad="unknown",quad_name="Unknown",confidence=None,data_limited=True,
                            recession_score=None,recession_band="n/a",equity=eq[cc],macro={k:None for k in ["policy_rate","yield_10y","curve","real_yield","cpi_yoy","gdp_yoy","unemployment","fx_strength_3m"]},macro_asof={"cpi_yoy":None}))
    return records


def test_owner_composite_not_realized_loss():
    rows=country_fixture();before=deepcopy(rows)
    assert rows[0]["equity"]["off_52w_high"]==rows[1]["equity"]["off_52w_high"]==0
    assert [r["equity"]["drawdown_risk"] for r in rows[:2]]==[0.,20.]
    html=render_fixture(records=rows);soup=BeautifulSoup(html,"html.parser")
    panel=soup.select_one("#intl-cross-country").parent
    assert "Realized damage from the 252-day high" not in str(panel)
    assert "Market stress" in panel.get_text() and "市场压力" in panel.get_text()
    assert "volatility" in panel.get_text() and "波动率" in panel.get_text()
    assert rows==before


def test_unavailable_extension_never_becomes_normal():
    rows=country_fixture();assert rows[2]["equity"]["ext_grade"]=="na"
    soup=BeautifulSoup(render_fixture(records=rows),"html.parser")
    panel=soup.select_one("#intl-cross-country").parent
    cells=panel.select("tbody tr")[-1].select("td")
    assert "Unavailable" in cells[-1].get_text() and "不可用" in cells[-1].get_text()
    assert "normal" not in cells[-1].get_text()
    assert "normal" in panel.select("tbody tr")[0].select("td")[-1].get_text()


def test_cross_country_keyboard_semantics():
    soup=BeautifulSoup(render_fixture(records=country_fixture()),"html.parser")
    h=soup.select_one("#intl-cross-country");assert h["tabindex"]=="-1"
    region=h.parent.select_one("[data-cross-country-scroll]")
    assert region["tabindex"]=="0" and region["aria-labelledby"]=="intl-cross-country"
