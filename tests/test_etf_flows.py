"""tests/test_etf_flows.py — unit tests for engine/etf_flows.py."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from engine.etf_flows import (
    _derive_flow,
    flows_wide,
    load_proxy,
    proxy_json,
    rebuild,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_so_file(tmp_dir: Path, ticker: str, rows: list[dict]) -> None:
    df = pd.DataFrame(rows)
    df.index = pd.to_datetime(df.pop("date"))
    df.index.name = "date"
    df.to_parquet(tmp_dir / f"{ticker}.parquet")


def _minimal_rows(n: int = 5) -> list[dict]:
    """n rows of synthetic SO data starting 2026-06-02."""
    base = pd.Timestamp("2026-06-02")
    rows = []
    for i in range(n):
        nav = 100.0 + i
        aum_mn = 1000.0 + i * 10
        rows.append({
            "date": base + pd.Timedelta(days=i),
            "nav": nav,
            "aum_mn": aum_mn,
            "so_mn": aum_mn / nav,
        })
    return rows


# ── _derive_flow ──────────────────────────────────────────────────────────────

def test_derive_flow_first_row_nan():
    df = pd.DataFrame(
        {"nav": [100.0, 101.0], "so_mn": [10.0, 11.0]},
        index=pd.to_datetime(["2026-06-02", "2026-06-03"]),
    )
    result = _derive_flow(df)
    assert pd.isna(result.iloc[0]), "first row must be NaN (no prior day)"
    # day-2: delta_so = 1.0, nav = 101.0 → flow = 101.0
    assert abs(result.iloc[1] - 101.0) < 1e-6


def test_derive_flow_negative_redemption():
    df = pd.DataFrame(
        {"nav": [100.0, 100.0], "so_mn": [10.0, 9.5]},
        index=pd.to_datetime(["2026-06-02", "2026-06-03"]),
    )
    result = _derive_flow(df)
    assert result.iloc[1] < 0, "outflow should be negative"


# ── flows_wide ────────────────────────────────────────────────────────────────

def test_flows_wide_returns_none_when_no_files(tmp_path):
    # Empty tickers → no files → None regardless of path
    result = flows_wide(tickers=(), _flows_dir=tmp_path)
    assert result is None


def test_flows_wide_correct_columns(tmp_path):
    for t in ("XLK", "XLF"):
        _make_so_file(tmp_path, t, _minimal_rows(3))

    # _flows_dir injection bypasses the sponsors path and reads synthetic files
    result = flows_wide(tickers=("XLK", "XLF"), _flows_dir=tmp_path)

    assert result is not None
    assert "XLK_flow_mn" in result.columns
    assert "XLF_flow_mn" in result.columns
    assert result.index.name == "date"
    # First row of each should be NaN (diff); remaining 2 are values
    assert result["XLK_flow_mn"].isna().sum() == 1


# ── rebuild ───────────────────────────────────────────────────────────────────

def test_rebuild_creates_parquet(tmp_path):
    for t in ("XLK", "XLF"):
        _make_so_file(tmp_path, t, _minimal_rows(4))
    proxy_path = tmp_path / "etf_flow_proxy.parquet"

    # flows_dir=tmp_path triggers test-injection path in flows_wide()
    out = rebuild(tickers=("XLK", "XLF"), flows_dir=tmp_path, proxy_path=proxy_path)

    assert out is not None
    assert proxy_path.exists()
    df = pd.read_parquet(proxy_path)
    assert "XLK_flow_mn" in df.columns
    assert len(df) == 4


def test_rebuild_idempotent(tmp_path):
    for t in ("XLK",):
        _make_so_file(tmp_path, t, _minimal_rows(3))
    proxy_path = tmp_path / "etf_flow_proxy.parquet"

    rebuild(tickers=("XLK",), flows_dir=tmp_path, proxy_path=proxy_path)
    # second run
    rebuild(tickers=("XLK",), flows_dir=tmp_path, proxy_path=proxy_path)

    df = pd.read_parquet(proxy_path)
    assert len(df) == 3, "idempotent rebuild must not duplicate rows"


def test_rebuild_returns_none_when_no_data(tmp_path):
    proxy_path = tmp_path / "etf_flow_proxy.parquet"
    out = rebuild(tickers=(), flows_dir=tmp_path, proxy_path=proxy_path)
    assert out is None


# ── proxy_json ────────────────────────────────────────────────────────────────

def _write_proxy(tmp_path: Path, n: int = 5) -> Path:
    proxy_path = tmp_path / "etf_flow_proxy.parquet"
    rows = _minimal_rows(n)
    for t in ("XLK", "XLF"):
        _make_so_file(tmp_path, t, rows)
    rebuild(tickers=("XLK", "XLF"), flows_dir=tmp_path, proxy_path=proxy_path)
    return proxy_path


def test_proxy_json_structure(tmp_path):
    proxy_path = _write_proxy(tmp_path, n=5)
    result = proxy_json(proxy_path=proxy_path)
    assert result is not None
    assert result["label"] == "creation/redemption proxy"
    assert "asof" in result
    assert "depth" in result
    assert "funds" in result
    assert "net_flow_1d" in result
    tickers = {f["ticker"] for f in result["funds"]}
    assert "XLK" in tickers
    assert "XLF" in tickers


def test_proxy_json_none_when_no_file(tmp_path):
    result = proxy_json(proxy_path=tmp_path / "missing.parquet")
    assert result is None


def test_proxy_json_flow_signs(tmp_path):
    """Net inflow when so_mn grows each day."""
    rows = []
    base = pd.Timestamp("2026-06-02")
    for i in range(3):
        nav = 100.0
        so = 10.0 + i  # growing SO → net creation
        rows.append({"date": base + pd.Timedelta(days=i),
                     "nav": nav, "aum_mn": so * nav, "so_mn": so})
    proxy_path = tmp_path / "etf_flow_proxy.parquet"

    _make_so_file(tmp_path, "XLK", rows)
    rebuild(tickers=("XLK",), flows_dir=tmp_path, proxy_path=proxy_path)

    result = proxy_json(proxy_path=proxy_path)
    assert result is not None
    xlk = next(f for f in result["funds"] if f["ticker"] == "XLK")
    assert xlk["flow_1d"] > 0, "growing SO → positive flow (creation)"
"""Source-bound acceptance for the proxy sibling explicitly excluded by #10970."""
from pathlib import Path
import ast, json, logging, subprocess
import numpy as np
import pandas as pd
import pytest
from engine import etf_flows as native

ROOT = Path(__file__).resolve().parents[1]
DATES = pd.bdate_range('2026-09-14', periods=30)

def save(tmp_path, df):
    p=tmp_path/'flows.parquet'; df.to_parquet(p); return p

def invoke(tmp_path, values):
    df=pd.DataFrame(values, index=DATES[-len(next(iter(values.values()))):])
    return native.proxy_json(proxy_path=save(tmp_path,df))

def fund(out,ticker='XLK'):
    return next(f for f in out['funds'] if f['ticker']==ticker)

@pytest.mark.parametrize('missing_at',[-1,-2,-4])
def test_missing_dates_do_not_pull_older_rows(tmp_path, missing_at):
    a=[100.]+[1.]*5; a[missing_at]=np.nan
    out=invoke(tmp_path,{'XLK_flow_mn':a,'XLF_flow_mn':[-2.]*6})
    assert fund(out)['flow_5d'] is None
    assert fund(out)['flow_21d'] is None
    assert fund(out)['flow_1d']==(None if missing_at==-1 else 1.)

@pytest.mark.parametrize('missing', [np.nan,np.inf,-np.inf,'bad'])
def test_stale_or_nonfinite_latest_is_not_current(tmp_path, missing):
    values=['100','100',missing] if isinstance(missing,str) else [100.,100.,missing]
    out=invoke(tmp_path,{'XLK_flow_mn':values, 'XLF_flow_mn':[-10.]*3})
    assert fund(out)['flow_1d'] is None
    assert out['net_flow_1d'] is None
    assert out['asof']==str(DATES[-1].date())
    json.dumps(out,allow_nan=False)

@pytest.mark.parametrize('gap',[-1,-2])
def test_all_fund_gap_retains_date_and_window(tmp_path,gap):
    a=[1.,2.,3.,4.,5.,6.];a[gap]=np.nan
    out=invoke(tmp_path,{'XLK_flow_mn':a,'XLF_flow_mn':a})
    assert out['asof']==str(DATES[-1].date())
    assert out['depth']==6
    assert fund(out)['flow_5d'] is None

@pytest.mark.parametrize('n',[2,3,5,21,30])
def test_complete_history_matches_native_short_history_policy(tmp_path,n):
    a=np.arange(1.,n+1);b=-a
    out=invoke(tmp_path,{'XLK_flow_mn':a,'XLF_flow_mn':b})
    for key,w in [('flow_1d',1),('flow_5d',5),('flow_21d',21)]:
        assert fund(out)[key]==sum(a[-w:])
    assert out['net_flow_1d']==0.

def test_zero_is_an_observation(tmp_path):
    out=invoke(tmp_path,{'XLK_flow_mn':[0.]*6,'XLF_flow_mn':[0.]*6})
    assert fund(out)['flow_5d']==0.
    assert out['net_flow_1d']==0.

def test_all_missing_fund_is_retained_unavailable(tmp_path):
    out=invoke(tmp_path,{'XLK_flow_mn':[np.nan]*6,'XLF_flow_mn':[-1.]*6})
    assert fund(out)['flow_1d'] is None
    assert out['net_flow_1d'] is None

def test_leading_diff_only_rows_remain_excluded(tmp_path):
    out=invoke(tmp_path,{'XLK_flow_mn':[np.nan,np.nan,2.,3.],'XLF_flow_mn':[np.nan,np.nan,4.,5.]})
    assert out['depth']==2
    assert fund(out)['flow_5d']==5.

@pytest.mark.parametrize('v',[1e308,-1e308])
def test_overflow_is_unavailable(tmp_path,v):
    out=invoke(tmp_path,{'XLK_flow_mn':[v]*3,'XLF_flow_mn':[v]*3})
    assert fund(out)['flow_5d'] is None
    assert out['net_flow_1d'] is None
    json.dumps(out,allow_nan=False)

def test_row_order_does_not_change_result_or_input(tmp_path):
    df=pd.DataFrame({'XLK_flow_mn':[1.,2.,3.,4.,5.,6.]},index=DATES[-6:])
    p=save(tmp_path,df.iloc[::-1]);before=p.read_bytes()
    out=native.proxy_json(proxy_path=p)
    assert out['asof']==str(DATES[-1].date()) and fund(out)['flow_5d']==20.
    assert before==p.read_bytes()

def test_real_temp_parquet_builder_and_options_html(tmp_path,monkeypatch):
    # Complete native Parquet reader -> unchanged native builder function ->
    # unchanged actual Options renderer. No live acquisition or full app claim.
    p=save(tmp_path,pd.DataFrame({'XLK_flow_mn':[100.,100.,np.nan],
        'XLF_flow_mn':[-10.,-10.,-10.]},index=DATES[-3:]))
    monkeypatch.setattr(native,'_PROXY_PATH',p)
    src=(ROOT/'scripts/build_flow_desk.py').read_text()
    node=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='build_etf_tile')
    ns={'Path':Path,'log':logging.getLogger('acceptance'),'ETF_LABEL':'proxy (creation/redemption)'}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'unchanged_builder','exec'),ns)
    tile=ns['build_etf_tile'](tmp_path)
    template=(ROOT/'templates/options.html.j2').read_text()
    # Each function ends at the next column-zero function declaration. Trailing
    # comment text is harmless; the fixture omits DOM initialization by design.
    names=['esc','bi','num','money','smoney','flSoft','flEtfPanel']
    import re
    chunks=[]
    for name in names:
        start=template.index('function '+name+'(')
        end=template.find('\nfunction ',start+1)
        segment=template[start:end]
        # Each selected function's final closing brace is before any next block
        # comment. Keep through last line-ending/one-line closing brace.
        if name=='flEtfPanel': segment=segment[:segment.index('\n/*')]
        if name=='flSoft': segment=segment[:segment.index('\n/*')]
        chunks.append(segment)
    js='\n'.join(chunks)+'\nconsole.log(flEtfPanel('+json.dumps({'etf_tile':tile})+'));'
    html=subprocess.run(['node','-e',js],text=True,capture_output=True,check=True).stdout
    (tmp_path/'rendered.html').write_text(html)
    assert '~+$100M' not in html
    assert '5D — · 21D —' in html
    assert '~−$10M' in html
    assert str(DATES[-1].date()) in html
    assert tile['net_flow_1d'] is None


def test_native_rebuild_with_asymmetric_source_histories(tmp_path):
    dates=DATES[-4:]
    pd.DataFrame({'so_mn':[10.,11.,12.], 'nav':[100.]*3},index=dates[:3]).to_parquet(tmp_path/'XLK.parquet')
    pd.DataFrame({'so_mn':[10.,9.9,9.8,9.7], 'nav':[100.]*4},index=dates).to_parquet(tmp_path/'XLF.parquet')
    output=tmp_path/'proxy.parquet'
    native.rebuild(tickers=('XLK','XLF'),flows_dir=tmp_path,proxy_path=output)
    out=native.proxy_json(proxy_path=output)
    assert fund(out)['flow_1d'] is None
    assert fund(out,'XLF')['flow_1d']==pytest.approx(-10.)
    assert out['net_flow_1d'] is None
    assert out['asof']==str(dates[-1].date())

