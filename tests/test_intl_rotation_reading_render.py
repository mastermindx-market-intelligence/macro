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


# R10_NEUTRAL_ROTATION_REGRESSION — isolated independent audit tests only.
@pytest.mark.parametrize("returns,expected_class,expected_text", [
    ({"3m": None,"6m": 0.0,"12m": -1.4}, ["muted","muted","neg"], ["—","+0.0%","-1.4%"]),
    ({"3m": 1.4,"6m": -1.4,"12m": 0.0}, ["pos","neg","muted"], ["+1.4%","-1.4%","+0.0%"]),
    ({"3m": -0.01,"6m": 0.01,"12m": None}, ["muted","muted","muted"], ["-0.0%","+0.0%","—"]),
    ({"3m": 0.0,"6m": None}, ["muted","muted","muted"], ["+0.0%","—","—"]),
])
def test_r10_null_zero_rotation_cells_are_neutral(returns, expected_class, expected_text):
    """A missing/zero relative return is not positive outperformance."""
    row=dict(cc="JP",name="Japan",name_zh="日本",flag="🇯🇵",q="lead",
        rs_level=105.,rs_mom=1.5,rel_ret=returns)
    rrg=dict(tilt="mixed",tilt_en="Mixed",tilt_zh="分化",rows=[row])
    soup=BeautifulSoup(render_fixture(mode="macro",perf={"rrg":rrg}),"html.parser")
    table=next((t for t in soup.select("table.sb") if "vs US 3m" in t.get_text()),None)
    assert table is not None
    tr=next(x for x in table.select("tbody tr") if "Japan" in x.get_text())
    cells=tr.find_all("td",recursive=False)[2:5]
    assert [c.get("class",[None])[0] for c in cells]==expected_class
    assert [c.get_text(" ",strip=True) for c in cells]==expected_text



def test_withheld_us_relative_benchmark_discloses_without_invented_comparison():
    """The real bilingual template remains informative when every US source fails."""
    from tests.test_intl_build import _env, _perf_vm
    vm = _perf_vm()
    vm["perf"]["rrg"] = None
    vm["bench_note"] = ("US-relative benchmark withheld: no qualified ^GSPC "
                        "(last 2026-09-01) or SPY (last 2026-09-03) "
                        "versus international observation 2026-10-14")
    soup = BeautifulSoup(_env().get_template("intl.html.j2").render(
        **vm, mode="macro"), "html.parser")
    notice = soup.select_one("[data-us-benchmark-withheld]")
    assert notice is not None
    assert "US-relative comparison unavailable" in notice.get_text()
    assert "对美相对比较暂不可用" in notice.get_text()
    assert "2026-09-01" in notice.get_text() and "2026-09-03" in notice.get_text()
    assert soup.select_one("[data-us-benchmark-source]") is not None
    assert not any("US vs the World — capital rotation" in node.get_text()
                   for node in soup.select("div.panel h2"))


def test_us_relative_withheld_disclosure_escapes_source_text():
    from tests.test_intl_build import _env, _perf_vm
    vm = _perf_vm()
    vm["bench_note"] = "US-relative benchmark withheld: <img src=x onerror=alert(1)>"
    soup = BeautifulSoup(_env().get_template("intl.html.j2").render(
        **vm, mode="macro"), "html.parser")
    notice = soup.select_one("[data-us-benchmark-withheld]")
    assert notice is not None and notice.find("img") is None
    assert "<img src=x onerror=alert(1)>" in notice.get_text()


def test_substituted_spy_note_is_not_a_false_withheld_warning():
    from tests.test_intl_build import _env, _perf_vm
    vm = _perf_vm()
    vm["bench_note"] = "US benchmark: qualified SPY substituted (^GSPC unqualified)"
    soup = BeautifulSoup(_env().get_template("intl.html.j2").render(
        **vm, mode="macro"), "html.parser")
    assert soup.select_one("[data-us-benchmark-withheld]") is None
