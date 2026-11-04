"""IMF World Economic Outlook DataMapper collector (IRD-W1 — §2 SLOW tier).

Keyless JSON API: one HTTP GET per indicator returns ALL countries for all years.
Annual data; WEO vintages published April + October (IMF updates these mid-year).

Indicators:
  GGXWDG_NGDP  — Gross government debt (% of GDP)
  GGXCNL_NGDP — Overall net lending/borrowing (% of GDP; DataMapper does not expose the GGXONLB primary-balance series)
  BCA_NGDPD    — Current account balance (% of GDP)

Store layout: one parquet per (indicator, iso3) under data/imf_weo/. File name
convention: data/imf_weo/<INDICATOR>_<ISO3>.parquet (e.g. GGXWDG_NGDP_USA.parquet).
Each parquet has a date index (Dec-31 of the year) and a single value column named
after the indicator alias from config.yml.

Fail-open: a missing or errored country produces a gaps[] log entry but never
kills the run. A missing or errored indicator is also fail-open at the indicator
level. All config driven (imf_weo.indicators, imf_weo.countries).

Runs in the US shard (non-asia name) so it rides the nightly collect lane.

Endpoint verified 2026-07-12:
  curl "https://www.imf.org/external/datamapper/api/v1/GGXWDG_NGDP" → JSON OK
"""
from __future__ import annotations

import logging
import time
from datetime import date

import pandas as pd
import requests

from collectors.base import Adapter
from lib import config, store

log = logging.getLogger(__name__)

# Default 25-country universe (masterplan §2 SLOW tier vulnerability map).
# Overridden by imf_weo.countries in config.yml.
DEFAULT_COUNTRIES = [
    "USA", "CAN", "GBR", "DEU", "FRA", "ITA", "ESP", "JPN", "KOR", "CHN",
    "IND", "IDN", "AUS", "BRA", "MEX", "TUR", "ZAF", "POL", "HUN", "THA",
    "MYS", "PHL", "CHL", "COL", "EGY",
]


def fetch_indicator(
    base_url: str,
    indicator: str,
    countries: list[str],
    retries: int = 3,
    timeout: int = 60,
) -> dict[str, pd.Series]:
    """Fetch one IMF DataMapper indicator → {iso3: annual pd.Series}.

    Index is pd.Timestamp (Dec-31 of each year). Returns empty dict on failure.
    Countries absent from the API response are silently skipped (not every
    country has every indicator).
    """
    url = f"{base_url}/{indicator}"
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            # NOTE: imf.org's edge (Akamai) 403s descriptive/browser-spoof
            # User-Agent strings but accepts the plain requests/curl defaults —
            # verified 2026-07-12. Do not add a custom UA header here.
            r = requests.get(url, timeout=timeout)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            data = r.json()
            break
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if attempt < retries - 1:
                wait = 3.0 * (2 ** attempt)
                log.warning("imf_weo fetch %s attempt %d/%d failed (%s); retry in %.0fs",
                            indicator, attempt + 1, retries, e, wait)
                time.sleep(wait)
    else:
        log.error("imf_weo: all retries exhausted for %s: %s", indicator, last_exc)
        return {}

    # API shape: {"values": {indicator: {iso3: {year: value, ...}, ...}}}
    try:
        ind_data: dict = data["values"].get(indicator, {})
    except (KeyError, AttributeError, TypeError) as e:
        log.error("imf_weo: unexpected API shape for %s: %s", indicator, e)
        return {}

    result: dict[str, pd.Series] = {}
    for iso3 in countries:
        country_data = ind_data.get(iso3)
        if not country_data:
            log.debug("imf_weo: %s has no data for %s", indicator, iso3)
            continue
        try:
            years = {int(k): v for k, v in country_data.items()
                     if v is not None and str(v).strip() not in ("", "null")}
            if not years:
                continue
            idx = [pd.Timestamp(f"{y}-12-31") for y in sorted(years)]
            vals = [float(years[t.year]) for t in idx]
            s = pd.Series(vals, index=idx, name=indicator)
            result[iso3] = s
        except Exception as e:  # noqa: BLE001
            log.warning("imf_weo: parse error for %s/%s: %s", indicator, iso3, e)
    return result


class ImfWeoAdapter(Adapter):
    """IMF WEO DataMapper — annual fiscal/CA fundamentals (IRD-W1 vulnerability map).

    group = 'imf_weo' → data/imf_weo/<INDICATOR>_<ISO3>.parquet

    Staleness blind spot (deliberate, documented): fetch() upserts the per-country
    series itself and returns only the run-summary frame, so run_adapter's
    detect_stale_series sees a frame stamped today and can never flag a frozen WEO
    feed. Accepted for annual display-tier data (synapse SLA 4800h covers the store
    directory); revisit only if this store ever feeds anything time-sensitive.
    """

    name = "imf_weo"
    group = "imf_weo"
    stale_after_days = 200   # annual data; WEO updates ~April + October

    def __init__(self) -> None:
        cfg = config.load()
        self.cfg = cfg.get("imf_weo", {}) or {}

    def materialize_native_current_account(self, workbook_bytes, source_receipt):
        """Commit an already acquired official edition through this store owner.

        Acquisition/rights are separate controls. No network request, vintage
        inference or permission grant occurs here; existing DataMapper remains
        unchanged for its legacy consumers.
        """
        from datetime import datetime, timezone
        from lib.intl_annual_publication import (
            COLUMN, _sha, _utc, capture_current_account_commit, parse_native_current_account,
        )

        source = parse_native_current_account(workbook_bytes)
        if (type(source_receipt) is not dict or source_receipt.get("sha256") != _sha(workbook_bytes)
                or source_receipt.get("status") != 200
                or not str(source_receipt.get("url", "")).startswith("https://data.imf.org/")):
            raise ValueError("unbound original native edition")
        _utc(source_receipt["received_at"])
        frame = pd.DataFrame(
            {COLUMN: [v["value"] for _, v in sorted(source["values"].items())]},
            index=pd.DatetimeIndex([f"{year}-12-31" for year in sorted(source["values"])]),
        )
        current = store.read(self.group, "BCA_NGDPD_JPN")
        if current is not None and current.columns.tolist() != [COLUMN]:
            raise ValueError("incompatible existing current-account alias")
        # The native source owns supplied overlaps; legacy old-only dates remain
        # in the canonical cache but are never certified by this edition's
        # response evidence. This is not adjusted-price span replacement.
        store.upsert(self.group, "BCA_NGDPD_JPN", frame)
        try:
            return capture_current_account_commit(
                data_root=config.data_dir(), workbook_bytes=workbook_bytes,
                source_receipt=source_receipt, returned=frame,
                committed_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            # The canonical write has already succeeded. A receipt failure may
            # leave retained source objects; do not turn it into an acquisition
            # failure, breaker retry or rollback. A new value remains unqualified.
            log.warning("IMF native current-account store committed; evidence unavailable; publication unqualified")
            return {"status": "evidence_unavailable"}

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        if not self.cfg.get("enabled", True):
            raise RuntimeError("imf_weo disabled in config")

        base_url = self.cfg.get("base_url", "https://www.imf.org/external/datamapper/api/v1")
        retries = int(self.cfg.get("retries", 3))
        timeout = int(self.cfg.get("timeout", 60))
        countries: list[str] = list(self.cfg.get("countries", DEFAULT_COUNTRIES))
        indicators: dict[str, str] = dict(self.cfg.get("indicators", {}))  # {fred_id: alias}

        if not indicators:
            raise RuntimeError("imf_weo: no indicators configured")

        frames: dict[str, pd.DataFrame] = {}
        total_ok = 0
        native_japan = self.cfg.get("native_current_account")
        if native_japan is not None:
            import json
            from pathlib import Path
            from lib.intl_macro_publication import _read_stable_once, _reject_duplicate_keys
            from lib.intl_annual_publication import LIMIT

            if (type(native_japan) is not dict or set(native_japan) != {"workbook", "receipt"}
                    or indicators.get("BCA_NGDPD") != "current_account_pct_gdp" or "JPN" not in countries):
                raise ValueError("invalid native current-account input configuration")
            root = config.data_dir().resolve()
            paths = []
            for name in ("workbook", "receipt"):
                relative = native_japan[name]
                if type(relative) is not str or not relative or Path(relative).is_absolute():
                    raise ValueError("native edition input must be data-relative")
                path = root / relative
                if not path.resolve().is_relative_to(root):
                    raise ValueError("native edition input escapes data root")
                paths.append(path)
            raw = _read_stable_once(paths[0], LIMIT)
            receipt = json.loads(_read_stable_once(paths[1], LIMIT), object_pairs_hook=_reject_duplicate_keys)
            self.materialize_native_current_account(raw, receipt)
            total_ok += 1

        for indicator, alias in indicators.items():
            requested_countries = [c for c in countries if not (native_japan is not None and indicator == "BCA_NGDPD" and c == "JPN")]
            if not requested_countries:
                continue
            series_map = fetch_indicator(
                base_url, indicator, requested_countries,
                retries=retries, timeout=timeout,
            )
            if not series_map:
                log.warning("imf_weo: indicator %s returned no data", indicator)
                continue

            for iso3, s in series_map.items():
                if native_japan is not None and indicator == "BCA_NGDPD" and iso3 == "JPN":
                    continue  # native edition owns this one exact series
                key = f"{indicator}_{iso3}"
                df = s.to_frame(alias)
                store.upsert(self.group, key, df)
                frames[key] = df
                total_ok += 1

        if total_ok == 0:
            raise RuntimeError("imf_weo: all indicators/countries failed")

        log.info("imf_weo: %d (indicator, country) series stored", total_ok)
        # Return a summary frame so the adapter contract is satisfied
        summary = pd.DataFrame(
            {"series_ok": [total_ok]},
            index=[pd.Timestamp(date.today())],
        )
        return {"imf_weo_runs": summary}
