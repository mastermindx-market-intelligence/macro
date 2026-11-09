"""CFTC Commitments of Traders — legacy futures-only report.

Primary: CFTC's public Socrata API (no key, weekly updates Friday ~15:30 ET
for Tuesday data — the 3-day lag is labeled wherever this is displayed).
On API failure, the existing runner retains last-good data and reports failure.
Canonical 21-market Legacy/TFF/Disaggregated snapshots share this adapter/store.
Older alias projections remain compatible; canonical identities never use OI splices.

Stored per market: net non-commercial (spec) position and open interest, plus
net as % of OI for percentile work.
"""
from __future__ import annotations

import io
import logging
import zipfile
from datetime import date, datetime, timezone, timedelta

import pandas as pd

from collectors.base import Adapter
from lib import config, store
from lib.cot_contracts import BY_KEY, DATASETS, MARKETS, source_fields, store_name
from lib.cot_data import normalize_frame, preserve_source

log = logging.getLogger(__name__)

FIELDS = ("report_date_as_yyyy_mm_dd,market_and_exchange_names,"
          "cftc_contract_market_code,noncomm_positions_long_all,"
          "noncomm_positions_short_all,open_interest_all")


class CotAdapter(Adapter):
    name = "cot"
    group = "cot"
    stale_after_days = 12   # weekly release + 3-day publication lag

    def __init__(self) -> None:
        self.cfg = config.load()["cot"]

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        frames: dict[str, pd.DataFrame] = {}
        errors: list[str] = []
        try:
            frames.update(self.fetch_positioning(full_history))
        except Exception as exc:  # preserve legacy collection during a family outage
            errors.append(f"canonical positioning: {type(exc).__name__}")
        for key, prefixes in self.cfg["markets"].items():
            try:
                market = BY_KEY.get(key)
                canonical = frames.get(store_name(market.code)) if market else None
                if canonical is not None and key != "oil":
                    # Preserve the old alias schema and first-column meaning;
                    # full cohorts and source clocks live in canonical frames.
                    frames[f"cot_{key}"] = canonical[["net_spec", "open_interest", "net_spec_pct_oi"]].copy()
                else:
                    # Preserve the old mixed-exchange oil alias for unmigrated
                    # consumers; canonical readers use the exact NYMEX series.
                    frames[f"cot_{key}"] = self._fetch_market(key, prefixes, full_history)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{key}: {e}")
        if not frames:
            raise RuntimeError(f"all COT markets failed: {errors}")
        if errors:
            log.warning("COT partial failure: %s", errors)
        return frames

    def _fetch_market(self, key: str, prefixes: list[str], full_history: bool) -> pd.DataFrame:
        start = "1995-01-01"
        if not full_history:
            last = store.last_date(self.group, f"cot_{key}")
            if last:
                start = str(last)
        # SoQL escapes a single quote by doubling it — WTI's older CFTC name
        # carries a literal apostrophe (CRUDE OIL, LIGHT 'SWEET') that would
        # otherwise break the WHERE clause.
        clause = " OR ".join(
            "starts_with(market_and_exchange_names, '{}')".format(p.replace("'", "''"))
            for p in prefixes)
        where = (f"({clause}) AND "
                 f"report_date_as_yyyy_mm_dd > '{start}T00:00:00.000'")
        r = self.http_get(self.cfg["socrata_url"], retries=self.cfg["retries"],
                          params={"$where": where, "$select": FIELDS,
                                  "$order": "report_date_as_yyyy_mm_dd", "$limit": "50000"},
                          timeout=120)
        df = pd.DataFrame(r.json())
        if df.empty:
            stored = store.read(self.group, f"cot_{key}")
            if not full_history and stored is not None and not stored.empty:
                # no new weekly report yet (released Fridays) — not a failure;
                # re-upserting the stored tail keeps freshness reporting honest
                return stored.tail(1)
            raise ValueError(f"no rows for {prefixes} since {start}")
        for c in ["noncomm_positions_long_all", "noncomm_positions_short_all",
                  "open_interest_all"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        # contracts get renamed/recoded over the years (UST 10Y in 2022, etc.)
        # — per report date keep the dominant contract by open interest
        df = (df.sort_values("open_interest_all", ascending=False)
                .drop_duplicates("report_date_as_yyyy_mm_dd"))
        net = (df["noncomm_positions_long_all"] - df["noncomm_positions_short_all"])
        out = pd.DataFrame({
            "net_spec": net.to_numpy(),
            "open_interest": df["open_interest_all"].to_numpy(),
        }, index=pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).to_numpy())
        out["net_spec_pct_oi"] = 100 * out["net_spec"] / out["open_interest"]
        return out.sort_index()

    def fetch_positioning(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        """Collect exact 21-market series; all families are alternative views.

        Batched bounded SoQL pages avoid one request per row/contract. The
        immutable response remains under data/cot/raw, owned by this collector.
        No separate service, schedule or source-of-truth is introduced.
        """
        frames: dict[str, pd.DataFrame] = {}
        for family, dataset in DATASETS.items():
            markets = [m for m in MARKETS if family == "legacy" or m.detail_family == family]
            previous = {m.code: store.read(self.group, store_name(m.code, family)) for m in markets}
            known = [f.index.max() for f in previous.values() if f is not None and not f.empty]
            if full_history:
                start = "1995-01-01"
            elif len(known) == len(markets):
                start = (min(known) - pd.Timedelta(weeks=8)).date().isoformat()
            else:
                # Canonical readers replace aliases in long-history engines.
                # A 4-year first pull would silently truncate those consumers.
                start = "1995-01-01"
            codes = ",".join(f"'{m.code}'" for m in markets)
            where = f"cftc_contract_market_code in ({codes}) AND report_date_as_yyyy_mm_dd >= '{start}T00:00:00.000'"
            rows: list[dict] = []
            try:
                for offset in range(0, 120000, 5000):
                    response = self.http_get(
                        f"https://publicreporting.cftc.gov/resource/{dataset}.json",
                        params={"$where": where, "$select": ",".join(source_fields(family)),
                                "$order": "cftc_contract_market_code,report_date_as_yyyy_mm_dd",
                                "$limit": 5000, "$offset": offset},
                        retries=self.cfg.get("retries", 3), timeout=30,
                    )
                    page = response.json()
                    if not isinstance(page, list) or any(not isinstance(r, dict) for r in page):
                        raise ValueError("CFTC response is not a row list")
                    rows.extend(page)
                    if len(page) < 5000:
                        break
                else:
                    raise ValueError("CFTC pagination ceiling reached; refusing truncated history")
                if not rows:
                    log.warning("COT family %s returned no reports", family)
                    continue
                observed = datetime.now(timezone.utc).isoformat()
                family_frames = {}
                for market in markets:
                    selected = [row for row in rows if row.get("cftc_contract_market_code") == market.code]
                    if not selected:
                        log.warning("COT %s/%s source unavailable", family, market.code)
                        continue
                    try:
                        family_frames[store_name(market.code, family)] = normalize_frame(
                            selected, family, code=market.code, observed_at=observed,
                            previous=previous[market.code],
                        )
                    except ValueError as exc:
                        log.warning("COT %s/%s rejected: %s", family, market.code, exc)
                evidence = preserve_source(rows, family, observed_at=observed, data_root=config.data_dir())
                for frame in family_frames.values():
                    frame["source_response_sha256"] = evidence
                frames.update(family_frames)
            except Exception as exc:  # family-local failure, existing cache untouched
                log.warning("COT %s failed: %s", family, type(exc).__name__)
        if not frames:
            raise RuntimeError("all canonical COT families failed")
        return frames
