"""Original SPDR transform pinned at Macro4eddd4ad83f761d4178e1faa73173dccd71ed419.
Source SHA-2568aea671c115cb200127040bdf17159acb46710b4ea717e6dd24b4c716bd0842e.
Test-only parity oracle; no network call or ambient source read.
"""
import io
from datetime import date
import pandas as pd

TOP_N = 20
SSGA_XLSX = ("https://www.ssga.com/us/en/intermediary/etfs/library-content/"
             "products/fund-data/etfs/us/holdings-daily-us-en-{fund}.xlsx")

class OriginalSectorHoldingsAdapter:
    def _fetch_fund(self, fund: str) -> pd.DataFrame:
        r = self.http_get(SSGA_XLSX.format(fund=fund.lower()), retries=3, timeout=60,
                          headers={"User-Agent": "Mozilla/5.0 (research)"})
        # keep_default_na=False: 'NA' is a live listing (Nano Labs; National Bank of
        # Canada on TSX). na_values=[""] keeps blank -> NaN so dropna/to_numeric are unchanged.
        raw = pd.read_excel(io.BytesIO(r.content), header=None,
                            keep_default_na=False, na_values=[""])
        # find the header row ("Name", "Ticker", ...) and the as-of date above it
        hdr_idx = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "Name"]
        if not len(hdr_idx):
            raise ValueError("holdings header row not found")
        asof = str(date.today())
        for i in range(hdr_idx[0]):
            cell = str(raw.iloc[i, 1])
            if "As of" in cell:
                asof = str(pd.to_datetime(cell.replace("As of", "").strip()).date())
        df = raw.iloc[hdr_idx[0] + 1:].copy()
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in raw.iloc[hdr_idx[0]]]
        df = df.rename(columns={"weight": "weight_pct"})
        wcol = next((c for c in df.columns if "weight" in c), None)
        if wcol is None or "ticker" not in df.columns:
            raise ValueError(f"unexpected columns: {list(df.columns)[:6]}")
        df["weight_pct"] = pd.to_numeric(df[wcol], errors="coerce")
        df = (df.dropna(subset=["weight_pct", "ticker"])
                .query("ticker != '-'")
                .nlargest(TOP_N, "weight_pct"))
        out = pd.DataFrame({
            "ticker": df["ticker"].astype(str).str.strip(),
            "name": df["name"].astype(str).str.strip() if "name" in df.columns else "",
            "weight_pct": df["weight_pct"].round(2),
            "rank": range(1, len(df) + 1),
        })
        out.index = pd.to_datetime([asof] * len(out))
        return out

