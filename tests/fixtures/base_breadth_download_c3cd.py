"""Frozen incumbent downloader; literal source, not a reconstructed expectation.
Source: collectors/breadth.py at c3cd9bb6256ae7ea5943d226691a9b290e475f9e
Method SHA256: ca8435027f01f41696ad391cb82319de3d889a6bf4eb2b6b598803667202d3a9
"""
from __future__ import annotations
import logging
import time
import pandas as pd
import yfinance as yf
log = logging.getLogger(__name__)

class FrozenBreadthDownload:
    def _download_closes(self, tickers: list[str], period: str) -> pd.DataFrame:
        bs = self.ycfg["batch_size"]
        parts: list[pd.DataFrame] = []
        # ADDITIVE OHLCV capture: yfinance already downloads high/low/volume — keep them
        # (instead of discarding all but Close) so the stock library can compute
        # volume-based signals (engine/bottom_radar) for the full universe, not just the
        # ~114 deep names. Stashed on self for fetch() to cache; never affects closes.
        extras: dict[str, list] = {"high": [], "low": [], "volume": []}
        for i in range(0, len(tickers), bs):
            batch = tickers[i:i + bs]
            for attempt in range(self.ycfg["retries"]):
                try:
                    df = yf.download(batch, period=period, auto_adjust=True,
                                     progress=False, group_by="column", threads=True)
                    lvl0 = (df.columns.get_level_values(0)
                            if isinstance(df.columns, pd.MultiIndex) else df.columns)
                    parts.append(df["Close"] if "Close" in lvl0 else df)
                    for k, F in (("high", "High"), ("low", "Low"), ("volume", "Volume")):
                        if F in lvl0:
                            extras[k].append(df[F])
                    break
                except Exception as e:  # noqa: BLE001
                    wait = self.ycfg["backoff_base_s"] * (2 ** attempt)
                    log.warning("breadth batch %d failed (%s); retry in %.0fs", i // bs, e, wait)
                    time.sleep(wait)
            time.sleep(1)
        if not parts:
            raise RuntimeError("no constituent closes downloaded")

        def _wide(plist: list) -> pd.DataFrame:
            w = pd.concat(plist, axis=1)
            return w.loc[:, ~w.columns.duplicated()].sort_index()

        self._last_extras = {k: _wide(v) for k, v in extras.items() if v}
        return _wide(parts)
