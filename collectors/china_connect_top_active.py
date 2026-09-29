"""Additive cache owned by ChinaConnectAdapter; bounded collection, not rendering."""
from datetime import datetime, timezone
import hashlib
import json
import logging

import pandas as pd

from engine.china_connect_leaderboard import VENUES

log = logging.getLogger(__name__)
ENDPOINT = "https://datacenter-web.eastmoney.com/api/data/v1/get"


def fetch_top_active(http_get) -> dict[str, pd.DataFrame]:
    frames = {}
    observed = datetime.now(timezone.utc)
    for leg, (_, venue, currency) in VENUES.items():
        try:
            params = {"reportName": "RPT_MUTUAL_TOP10DEAL", "columns": "ALL", "pageSize": 10,
                      "sortColumns": "TRADE_DATE", "sortTypes": -1, "pageNumber": 1,
                      "filter": f'(MUTUAL_TYPE="{leg}")'}
            r = http_get(ENDPOINT, params=params, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}, timeout=15, retries=2)
            r.raise_for_status()
            rows = (r.json().get("result") or {}).get("data") or []
            if not rows or any(not isinstance(x, dict) for x in rows):
                raise ValueError("no_usable_top_active_rows")
            dates = pd.to_datetime([x.get("TRADE_DATE") for x in rows], errors="coerce")
            if dates.isna().any():
                raise ValueError("invalid_top_active_reference_date")
            if dates.tz is not None:
                dates = dates.tz_convert("Asia/Shanghai").tz_localize(None)
            latest = dates.max().normalize()
            cutoff = pd.Timestamp(observed).tz_convert("Asia/Shanghai").normalize().tz_localize(None)
            if latest > cutoff:
                raise ValueError("future_top_active_reference_date")
            selected = [x for x, d in zip(rows, dates) if d.normalize() == latest]
            encoded = json.dumps(selected, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            frames["top_active_"+leg] = pd.DataFrame([{"rows_json": encoded, "source_url": ENDPOINT,
                "source_report": "RPT_MUTUAL_TOP10DEAL", "venue": venue, "currency": currency,
                "observed_at": observed.isoformat(), "publication_time": None,
                "source_sha256": hashlib.sha256(encoded.encode()).hexdigest()}], index=pd.DatetimeIndex([latest], name="date"))
        except Exception as exc:  # each disclosure route may fail independently
            log.warning("china_connect top-active %s unavailable: %s", leg, type(exc).__name__)
    return frames
