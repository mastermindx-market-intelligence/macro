"""No-network tests for the futures entitlement probe."""
from __future__ import annotations

from scripts import probe_massive_futures as pmf


class FakeProber:
    def __init__(self, payloads):
        self.payloads = payloads
        self.results = {}

    def probe(self, name, path, params=None, evidence=None):
        payload = self.payloads.get(name)
        verdict = "entitled" if payload is not None else "not_entitled"
        rec = {"http_status": 200 if payload is not None else 403,
               "verdict": verdict, "evidence": {}}
        if evidence and payload is not None:
            rec["evidence"].update(evidence(payload))
        self.results[name] = rec
        return payload


def test_probe_walks_reference_then_trade_quote() -> None:
    p = FakeProber({
        "futures_products_es": {"results": [{"product_code": "ES"}]},
        "futures_contracts_es": {"results": [{"ticker": "ESZ6"}]},
        "futures_trades": {"results": [{"ticker": "ESZ6", "price": 6700.0}]},
        "futures_quotes": {"results": [{"ticker": "ESZ6", "bid_price": 6699.75}]},
    })
    out = pmf.run_probe(p)
    assert out["contract_ticker"] == "ESZ6"
    assert out["derived"] == {
        "reference_entitled": True,
        "trades_entitled": True,
        "quotes_entitled": True,
    }


def test_reference_without_contract_does_not_fabricate_trade_entitlement() -> None:
    p = FakeProber({
        "futures_products_es": {"results": [{"product_code": "ES"}]},
        "futures_contracts_es": {"results": []},
    })
    out = pmf.run_probe(p)
    assert out["contract_ticker"] is None
    assert out["derived"]["reference_entitled"] is True
    assert out["derived"]["trades_entitled"] is None
    assert out["derived"]["quotes_entitled"] is None


def test_first_ticker_ignores_unrelated_contracts() -> None:
    assert pmf._first_ticker({"results": [{"ticker": "GCZ6"}, {"ticker": "ESH7"}]}) == "ESH7"
