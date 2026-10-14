"""Actual rotation owner on synthetic inputs; no acquisition or qualification."""
from copy import deepcopy
import pandas as pd
from bs4 import BeautifulSoup
import pytest
from engine.intl_rotation import rank
from tests.test_intl_workspace_integration import render_fixture


def rotation_fixture(basis="relative", short=False):
    dates=pd.bdate_range("2025-01-02",periods=6 if short else 31)
    rising=pd.Series([100*1.01**i for i in range(len(dates))],index=dates)
    flat=pd.Series(100.,index=dates)
    rows=rank({"JP":rising,"KR":rising,"IN":flat,"TW":flat},
              None if basis=="absolute" else flat,
              {"KR":{"state":"downtrend"},"TW":{"state":"parabolic","ext_pctile":99.,"macd_state":"bear","macd_cross_date":str(dates[-1].date())}})
    names={"JP":("Japan","日本"),"KR":("South Korea","韩国"),"IN":("India","印度"),"TW":("Taiwan","台湾")}
    return [dict(row,name=names[row["cc"]][0],name_zh=names[row["cc"]][1],flag="") for row in rows]


def section(rows):
    soup=BeautifulSoup(render_fixture(rotation_ranks=rows),"html.parser")
    return soup.select_one("#intl-leadership-rotation").parent


def test_actual_owner_same_twenty_session_reading_has_different_rank_score():
    rows=rotation_fixture();by={r["cc"]:r for r in rows}
    assert by["JP"]["rs20_pct"]==by["KR"]["rs20_pct"] and by["JP"]["score"]>by["KR"]["score"]>3
    assert by["IN"]["score"]==0 and by["TW"]["score"]==-6.6
    el=section(rows)
    assert "20d momentum — rotation rank" not in el.get_text()
    assert "Composite score" in el.get_text() and "综合分数" in el.get_text()


@pytest.mark.parametrize("basis,short",[("relative",False),("absolute",False),("relative",True)])
def test_signed_scores_and_owner_order_survive_render(basis,short):
    rows=rotation_fixture(basis,short);before=deepcopy(rows);el=section(rows)
    assert [n["data-rotation-market"] for n in el.select("[data-rotation-market]")]==[r["cc"] for r in rows]
    for row in rows:
        node=el.select_one('[data-rotation-market="'+row["cc"]+'"]')
        assert node.select_one("[data-rotation-score]").get_text()==f'{row["score"]:.3f}'
        assert "%" not in node.select_one("[data-rotation-score]").get_text()
        if row["note_en"]: assert row["note_en"] in node.get_text()
    assert rows==before
    text=el.get_text()
    assert "Missing windows enter the model as zero" in text and "缺失窗口在模型中按零计入" in text
    assert "not a return" in text and "并非收益率" in text
    assert el.select_one("#intl-leadership-rotation")["tabindex"]=="-1"
    assert el.select_one("[data-rotation-scroll]")["tabindex"]=="0"


def test_missing_rotation_has_no_destination_or_invented_rows():
    for rows in (None,[]):
        soup=BeautifulSoup(render_fixture(rotation_ranks=rows),"html.parser")
        assert not soup.select("#intl-leadership-rotation")
        assert not soup.select('[data-im-library-tool="leadership_rotation"] a[href="#intl-leadership-rotation"]')


def test_rotation_text_is_escaped():
    rows=rotation_fixture();rows[0]["name"]='<img src=x onerror=alert(1)>'
    rows[0]["note_en"]='<script>bad()</script>'
    el=section(rows)
    assert not el.select("img,script")
    assert '<img src=x onerror=alert(1)>' in el.get_text()
    assert '<script>bad()</script>' in el.get_text()
