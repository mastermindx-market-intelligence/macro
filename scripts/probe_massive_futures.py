#!/usr/bin/env python3
"""Read-only Massive Futures entitlement probe.

This helper deliberately REUSES scripts.massive_entitlement_probe.RestProber and
its key/scrubbing logic. It does not write a second capability manifest and it
does not mutate the existing stock/options manifest. Its output is a bounded
source-qualification receipt for WS:FUTURES-MARKET-TAPE-PLANE F0.

Run:
  python -m scripts.probe_massive_futures
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from scripts.massive_entitlement_probe import (
    RestProber,
    _base_url,
    _ev_results,
    resolve_key,
)

PRODUCT = "ES"


def _first_ticker(payload: Any) -> str | None:
    rows = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict):
            ticker = row.get("ticker")
            if isinstance(ticker, str) and ticker.upper().startswith(PRODUCT):
                return ticker
    return None


def run_probe(prober: RestProber) -> dict:
    p = prober.probe
    products = p(
        "futures_products_es",
        "/futures/v1/products",
        params={"product_code": PRODUCT, "limit": 5},
        evidence=_ev_results,
    )
    contracts = p(
        "futures_contracts_es",
        "/futures/v1/contracts",
        params={"product_code": PRODUCT, "active": "true", "limit": 10},
        evidence=_ev_results,
    )
    ticker = _first_ticker(contracts)
    if ticker:
        p(
            "futures_trades",
            f"/futures/v1/trades/{ticker}",
            params={"limit": 1, "sort": "timestamp.desc"},
            evidence=_ev_results,
        )
        p(
            "futures_quotes",
            f"/futures/v1/quotes/{ticker}",
            params={"limit": 1, "sort": "timestamp.desc"},
            evidence=_ev_results,
        )
    return {
        "product": PRODUCT,
        "contract_ticker": ticker,
        "rest": dict(prober.results),
        "derived": {
            "reference_entitled": prober.results.get("futures_contracts_es", {}).get("verdict")
            == "entitled",
            "trades_entitled": (
                prober.results.get("futures_trades", {}).get("verdict") == "entitled"
                if ticker else None
            ),
            "quotes_entitled": (
                prober.results.get("futures_quotes", {}).get("verdict") == "entitled"
                if ticker else None
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--key-env", default=None)
    ap.add_argument("--timeout", type=float, default=15.0)
    args = ap.parse_args(argv)

    key, label = resolve_key(args.key_env)
    if not key:
        raise SystemExit(
            "No Massive/Polygon credential is available. This is an external source gate, "
            "not permission to create or rotate a key."
        )
    prober = RestProber(key, _base_url(), timeout=args.timeout)
    result = run_probe(prober)
    result["key_source"] = label
    result["base_url"] = prober.base_url
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
