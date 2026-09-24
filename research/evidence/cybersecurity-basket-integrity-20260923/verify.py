"""Reproduce the 2026-09-23 cybersecurity basket-composition decision."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
AS_OF = pd.Timestamp("2026-09-23")
CURRENT_10 = ["CRWD", "PANW", "FTNT", "OKTA", "QLYS", "ZS", "S", "NET", "RBRK", "TENB"]
ADDITIONS = ["CHKP", "SAIL", "VRNS", "NTSK"]
EXPANDED_14 = CURRENT_10 + ADDITIONS
RPD_VARIANT = EXPANDED_14 + ["RPD"]
PROXIES = ["CIBR", "BUG", "WCBR"]


def _close(ticker: str) -> pd.Series:
    candidates = [
        ROOT / "data" / "baskets" / "ohlcv" / f"{ticker}.parquet",
        ROOT / "data" / "yahoo" / f"{ticker}.parquet",
        ROOT / "data" / "stocks" / f"{ticker}.parquet",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        raise FileNotFoundError(f"no price store for {ticker}")
    frame = pd.read_parquet(path)
    col = next((c for c in ("close", "Close", "adj_close", "Adj Close") if c in frame), None)
    if col is None:
        raise KeyError(f"{path} has no close column")
    out = pd.to_numeric(frame[col], errors="coerce").dropna()
    out.index = pd.to_datetime(out.index, errors="coerce")
    out = out[~out.index.isna()]
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out.loc[:AS_OF]


def _returns(tickers: list[str]) -> tuple[pd.Series, pd.DataFrame]:
    panel = pd.DataFrame({t: _close(t).pct_change(fill_method=None) for t in tickers})
    return panel.mean(axis=1, skipna=True), panel


def _fit(basket_returns: pd.Series, proxy: str, window: int | None) -> dict:
    pair = pd.concat(
        [basket_returns.rename("basket"), _close(proxy).pct_change(fill_method=None).rename("proxy")],
        axis=1, sort=False,
    ).dropna()
    if window is not None:
        pair = pair.iloc[-window:]
    return {
        "n": int(len(pair)),
        "correlation": round(float(pair["basket"].corr(pair["proxy"])), 3),
        "tracking_error_annualized": round(
            float((pair["basket"] - pair["proxy"]).std() * np.sqrt(252)), 3
        ),
    }


def _set_receipt(tickers: list[str]) -> dict:
    returns, panel = _returns(tickers)
    latest = panel.loc[:AS_OF].dropna(how="all").iloc[-1]
    return {
        "members": tickers,
        "n_members": len(tickers),
        "latest_session": str(latest.name.date()),
        "latest_equal_weight_return_pct": round(float(latest.mean() * 100), 2),
        "latest_advance_decline": {
            "advance": int((latest > 0).sum()),
            "decline": int((latest < 0).sum()),
            "flat": int((latest == 0).sum()),
        },
        "latest_top3_absolute_contribution_share": round(
            float(latest.abs().nlargest(3).sum() / latest.abs().sum()), 3
        ),
        "proxy_fit": {
            proxy: {
                "1y": _fit(returns, proxy, 252),
                "2y": _fit(returns, proxy, 504),
                "full": _fit(returns, proxy, None),
            }
            for proxy in PROXIES
        },
    }


def _candidate_receipt(ticker: str) -> dict:
    candidate = _close(ticker).pct_change(fill_method=None).rename("candidate")
    core, _ = _returns(CURRENT_10)
    pair = pd.concat([candidate, core.rename("core")], axis=1, sort=False).dropna()
    down = pair[pair["core"] < 0]
    close = _close(ticker)
    return {
        "first_session": str(close.index.min().date()),
        "last_session": str(close.index.max().date()),
        "price_rows": int(len(close)),
        "corr_to_current_core": round(float(pair["candidate"].corr(pair["core"])), 3),
        "downside_corr_to_current_core": (
            round(float(down["candidate"].corr(down["core"])), 3) if len(down) >= 20 else None
        ),
    }


def main() -> int:
    result = {
        "schema": "cybersecurity_basket_integrity.v1",
        "as_of": str(AS_OF.date()),
        "construction": "equal-weight daily returns; available members; no future rows beyond as_of",
        "sets": {
            "current_10": _set_receipt(CURRENT_10),
            "expanded_14": _set_receipt(EXPANDED_14),
            "expanded_15_with_rpd": _set_receipt(RPD_VARIANT),
        },
        "candidates": {ticker: _candidate_receipt(ticker) for ticker in ADDITIONS + ["RPD"]},
        "decision": {
            "core_additions": ADDITIONS,
            "watch_not_core": ["RPD"],
            "reason": (
                "The four-name expansion fills missing network, identity-governance, data-security "
                "and SSE/SASE sleeves and improves BUG/WCBR tracking error. RPD adds little "
                "incremental proxy fit and would receive an outsized equal weight for its liquidity."
            ),
        },
    }

    current = result["sets"]["current_10"]["proxy_fit"]
    expanded = result["sets"]["expanded_14"]["proxy_fit"]
    for proxy in ("BUG", "WCBR"):
        assert expanded[proxy]["1y"]["tracking_error_annualized"] < current[proxy]["1y"]["tracking_error_annualized"]
    assert result["sets"]["expanded_14"]["latest_advance_decline"]["decline"] == 0
    assert (
        result["sets"]["expanded_14"]["latest_advance_decline"]["advance"]
        + result["sets"]["expanded_14"]["latest_advance_decline"]["flat"]
        == 14
    )
    assert all(result["candidates"][t]["last_session"] == str(AS_OF.date()) for t in ADDITIONS)

    out = Path(__file__).with_name("results.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
