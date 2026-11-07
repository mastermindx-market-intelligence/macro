"""Literal incumbent extras downloader.
Source: scripts/fetch_basket_extras.py at 765cd41712a0a838f7ec68c659dd6dd3e8c092a9
Function SHA256: 98a534528ad9254869405f4aea331f9fbbaf423e932841b42320c5f856819a95
"""
from __future__ import annotations
import logging
import time
import pandas as pd
START = "2023-01-01"
RETRIES = 4
BACKOFF_S = 3.0
BATCH = 60
log = logging.getLogger(__name__)

def _download_closes(tickers: list[str]) -> pd.DataFrame:
    """Adjusted closes for `tickers`, [Date x TICKER], deep history from START. Reuses the breadth
    yfinance pattern (crumb/cookie auth that works headless), batched with retry+backoff."""
    import yfinance as yf
    frames: list[pd.DataFrame] = []
    for i in range(0, len(tickers), BATCH):
        batch = tickers[i:i + BATCH]
        for attempt in range(RETRIES):
            try:
                df = yf.download(batch, start=START, auto_adjust=True,
                                 progress=False, group_by="column", threads=True)
                if df is None or df.empty:
                    raise RuntimeError("empty frame")
                closes = df["Close"] if "Close" in df.columns.get_level_values(0) else df
                if isinstance(closes, pd.Series):              # single-ticker shape
                    closes = closes.to_frame(batch[0])
                frames.append(closes.sort_index())
                break
            except Exception as e:  # noqa: BLE001
                wait = BACKOFF_S * (2 ** attempt)
                log.warning("batch %d/%d (%s…) attempt %d failed (%s); retry in %.0fs",
                            i // BATCH + 1, (len(tickers) - 1) // BATCH + 1, batch[0], attempt + 1, e, wait)
                time.sleep(wait)
        else:
            log.error("batch starting %s failed after %d retries — leaving to prior store", batch[0], RETRIES)
    if not frames:
        raise RuntimeError("all download batches failed")
    out = pd.concat(frames, axis=1).sort_index()
    return out.loc[:, ~out.columns.duplicated()]
