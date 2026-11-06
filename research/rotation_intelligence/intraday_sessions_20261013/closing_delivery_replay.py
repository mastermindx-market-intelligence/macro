"""Synthetic closing-delivery replay through actual producer and grounding code."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import build_basket_pulse as bp
from engine.neuralweb import market_packet as mp


def main() -> None:
    close = datetime(2026, 10, 13, 20, 0, tzinfo=timezone.utc)
    first_at = close - timedelta(minutes=15)
    delivered_at = close + timedelta(minutes=16)
    points = []
    with TemporaryDirectory(prefix="rotation-closing-proof-") as temporary:
        root = Path(temporary)
        quote_path = root / "quotes.json"
        membership_path = root / "membership.json"
        membership_path.write_text(json.dumps({"baskets": {
            "ai_semiconductors": {"members": [{"ticker": "A", "removed": None}]},
            "us_sector_health": {"members": [{"ticker": "B", "removed": None}]},
        }}))
        def observe(prices: dict, source_at: datetime, observed_at: datetime) -> dict:
            rows = {symbol: {"price": price, "prevClose": 100, "changePct": price-100,
                             "ts": int(source_at.timestamp()*1000), "basis": "regular",
                             "currency": "USD", "source": "synthetic"}
                    for symbol, price in prices.items()}
            quote_path.write_text(json.dumps({"quotes": rows}))
            with patch.dict(os.environ, {"LIVE_QUOTES_PATH": str(quote_path)}), \
                 patch.object(bp, "_cum_2d", return_value=None), \
                 patch.object(bp, "_load_market_drivers", return_value=None), \
                 patch.object(bp, "_attach_day_flow"):
                return bp.build(quotes_path=quote_path, membership_path=membership_path,
                                now=observed_at, out_dir=root)
        observe({"A": 102, "B": 99, "SPY": 100}, first_at-timedelta(minutes=1), first_at)
        result = observe({"A": 100, "B": 100, "SPY": 100}, close+timedelta(seconds=1), delivered_at)
        for row in result["baskets"]:
            points.append({"id": row["id"], "day_change_pct": row["live_ew_chg_pct"],
                           "comparison": row["intraday_comparison"]})
        publication = root / "site" / "live"
        publication.mkdir(parents=True)
        (publication / "basket_pulse.json").write_text(json.dumps(result, allow_nan=False))
        with patch.dict(os.environ, {mp._LIVE_DIR_ENV: str(publication)}):
            packet = mp.build_packet(root, now=delivered_at)
            digest = mp.render_digest(packet)
        assert all(row["day_change_pct"] == 0 for row in points)
        assert all(row["comparison"]["status"] == "observed" for row in points)
        assert "regular-session close" in digest and "not fund flows" in digest
        repeat = observe({"A": 100, "B": 100, "SPY": 100}, close+timedelta(seconds=1),
                         delivered_at+timedelta(minutes=5))
        statuses = [row["intraday_comparison"]["status"] for row in repeat["baskets"]]
        assert all(state == "observed" for state in statuses)
        repeat_new = [row["intraday_comparison"]["is_new_observation"] for row in repeat["baskets"]]
        assert not any(repeat_new)
    source_paths = ["scripts/build_basket_pulse.py", "engine/neuralweb/market_packet.py"]
    evidence = {"proof_kind": "synthetic_actual_closing_delivery_path_not_production",
                "source_hashes": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths},
                "delivered_at": delivered_at.isoformat(), "mode": result["mode"],
                "settled_close": result["settled_close"], "rows": points,
                "grounding_digest": digest, "repeat_statuses": statuses, "repeat_is_new_observation": repeat_new,
                "production_verified": False, "financial_edge_tested": False}
    print(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
