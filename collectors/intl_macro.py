"""International macro — Plane B of the International comparative dashboard.

The operational base is FRED's keyless CSV repackaging of OECD/Eurostat/central-
bank series.  ``intl.macro.official_series`` can override an individual stored
column with an official ECB or Eurostat API response after parser, unit and
release-period validation.  One failed official endpoint falls back to the
existing FRED frame (if any); it never erases a last-known-good store.

One parquet per stored_col under group ``intl_macro`` plus a deterministic
``provenance.json`` sidecar retaining provider, request, source update timestamp,
unit and fallback state.

Stored cols:
  * "<CC>_<metric>" for each country's config["intl"].countries[CC].fred map
      (e.g. JP_yield_10y, GB_cpi_yoy, EZ_unemployment) — yields, short rates,
      CPI YoY, unemployment, GDP, M2.
  * the shared `macro.extra_series` (ECB policy/assets, DE/IT/ES/FR 10y for the
      BTP-Bund periphery read, US 2y/10y anchor).

Every series fetches + degrades INDEPENDENTLY (one bad FRED id can't kill the
plane); history is archived forever by store.upsert. FRED is reachable from CI;
it is firewalled from some sandboxes — the engine then renormalizes over whatever
resolved (degrade-don't-crash). Mirrors collectors/canada_macro.py's FRED half.
"""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timezone
from math import prod
from pathlib import Path
from typing import Any

import pandas as pd

from collectors.base import Adapter, is_connection_error
from collectors.fred import FREDGRAPH_UA
from lib import config

log = logging.getLogger(__name__)

# After this many CONSECUTIVE connection failures (timeout/refused — not a dead
# series id), treat the keyless FRED frontend as unreachable from this runner and
# skip the rest of the plan. Bounds a full outage to ~a couple of minutes instead
# of 34 series x 3 retries x 30s ~= 56 min (every series produced nothing anyway).
_ABORT_AFTER_CONSECUTIVE_CONN_ERRORS = 3


class IntlMacroAdapter(Adapter):
    name = "intl_macro"
    group = "intl_macro"
    stale_after_days = 45  # monthly/quarterly OECD releases lag weeks
    # Native annual period cadence is separate from the 400-day application
    # display limit. Other monthly/quarterly series retain their existing rule.
    cadence_days_by_series = {"EZ_current_account_gdp_official": 365}

    def __init__(self) -> None:
        icfg = config.load()["intl"]
        self.cfg = icfg["macro"]
        self.countries = icfg["countries"]
        self.source_meta: dict[str, dict[str, Any]] = {}
        self._eurostat_responses = {}
        self._boe_response = None
        self._ecb_policy_response = None

    def _fetch_fred(self, fid: str) -> pd.DataFrame:
        r = self.http_get(
            self.cfg["fred_base_url"],
            params={"id": fid},
            retries=self.cfg["retries"],
            timeout=15,
            headers={"User-Agent": FREDGRAPH_UA},
        )
        raw = pd.read_csv(io.StringIO(r.text))
        date_col = raw.columns[0]  # observation_date (or DATE on older series)
        val_col = raw.columns[1]
        raw[val_col] = pd.to_numeric(raw[val_col], errors="coerce")
        s = raw.dropna(subset=[val_col]).set_index(pd.to_datetime(raw[date_col]))[
            val_col
        ]
        if s.empty:
            raise ValueError(f"fred {fid}: no numeric rows")
        return pd.DataFrame({"_": s}).sort_index()

    def fetch_result_status(self, frames):
        """Use the accepted year-end limit only for an annual-only source run.

        Mixed ordinary runs retain the existing adapter-level status rule;
        each field's publication admission still applies its own period age.
        A collection timestamp never replaces the economic observation date.
        """
        from lib.intl_eurostat_publication import ANNUAL_FIELD, ANNUAL_FIELDS
        spec = ANNUAL_FIELDS[ANNUAL_FIELD]
        if type(frames) is not dict or set(frames) != {spec["column"]}:
            return None
        last = frames[spec["column"]].dropna(how="all").index.max().date()
        age = (datetime.now(timezone.utc).date() - last).days
        return "ok" if 0 <= age <= spec["max_age_days"] else "stale"

    def after_store_commit(self, name, returned, merged, *, committed_at):
        if name == "ez_depo_rate" and self._ecb_policy_response is not None:
            from lib.intl_ecb_policy_publication import capture_ecb_policy_commit
            pending, self._ecb_policy_response = self._ecb_policy_response, None
            capture_ecb_policy_commit(data_root=config.data_dir(), returned=returned,
                                      committed_at=committed_at, **pending)
            return
        if name == "GB_bank_rate_official" and self._boe_response is not None:
            from lib.intl_boe_publication import capture_boe_commit
            pending, self._boe_response = self._boe_response, None
            # The base adapter contains a post-store evidence failure. Consume
            # the response first so it can never trigger another acquisition.
            capture_boe_commit(data_root=config.data_dir(), returned=returned,
                               committed_at=committed_at, **pending)
            return
        pending = getattr(self, "_eurostat_responses", {}).pop(name, None)
        if pending is not None:
            from lib.intl_eurostat_publication import capture_eurostat_commit
            # Consume before capture: post-store evidence failure cannot replay
            # acquisition or certify a write that did not commit.
            capture_eurostat_commit(data_root=config.data_dir(), returned=returned,
                                    committed_at=committed_at, **pending)
            return

    def _fetch_eurostat_yoy(self, field, spec, *, requested_at, retries, timeout):
        from lib.intl_eurostat_publication import FIELDS, ANNUAL_FIELDS, _decode, _sha, _source_url, parse_native_field
        from lib.intl_macro_publication import _read_stable_once

        contract = FIELDS[field] if field in FIELDS else ANNUAL_FIELDS[field]
        if (spec.get("provider") != "eurostat" or spec.get("dataset") != contract["dataset"]
                or spec.get("unit") != contract["selectors"]["unit"]):
            raise ValueError("Eurostat configured field contract mismatch")
        native = spec.get("native_input")
        received = None
        if native is not None:
            if type(native) is not dict or set(native) != {"response", "receipt"}:
                raise ValueError("invalid retained Eurostat input configuration")
            root = config.data_dir().resolve()
            def retained(key):
                value = native[key]
                if type(value) is not str or Path(value).is_absolute() or ".." in Path(value).parts:
                    raise ValueError("retained Eurostat input must be data relative")
                path = (root / value).resolve()
                path.relative_to(root)
                return _read_stable_once(path, 8 * 1024 * 1024)
            raw = retained("response")
            receipt = _decode(retained("receipt"))
            if receipt.get("status") != 200 or receipt.get("sha256") != _sha(raw):
                raise ValueError("retained Eurostat acquisition identity mismatch")
            url = receipt.get("response_url")
            requested_at = receipt.get("requested_at")
            # Original parent receipts omit this clock. Import time is never
            # relabeled as the original HTTP response receipt.
            received = receipt.get("response_received_at")
            if field in ANNUAL_FIELDS:
                # This retained acquisition records actual request/receipt
                # clocks under its original field names. Older two-field
                # receipts still retain their explicitly unknown HTTP clock.
                url = receipt.get("response_url", receipt.get("url"))
                received = receipt.get("response_received_at", receipt.get("received_at"))
        else:
            params = {"lang": "en", **(spec.get("params") or {})}
            if spec.get("since"):
                params["sinceTimePeriod"] = str(spec["since"])
            response = self.http_get(
                "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/" + contract["dataset"].lower(),
                params=params, retries=retries, timeout=timeout,
            )
            if response.status_code != 200:
                raise ValueError("Eurostat response not successful")
            raw, url = response.content, response.url
            received = datetime.now(timezone.utc).isoformat()
        _source_url(field, url)
        parsed, frame = parse_native_field(field, raw)
        verified = datetime.now(timezone.utc).isoformat()
        from lib.intl_eurostat_publication import _source_time, _utc
        if not _source_time(parsed["updated"]) <= _utc(requested_at) <= _utc(verified):
            raise ValueError("Eurostat source chronology mismatch")
        if received is not None and not _utc(requested_at) <= _utc(received) <= _utc(verified):
            raise ValueError("Eurostat response chronology mismatch")
        column = contract["column"]
        self._eurostat_responses[column] = dict(
            field=field, response_bytes=raw, source_url=url, requested_at=requested_at,
            input_verified_at=verified, response_received_at=received,
        )
        self.source_meta[column] = {
            "provider": "eurostat", "source_id": contract["dataset"], "source_url": url,
            "requested_at": requested_at, "source_updated": parsed["updated"],
            "last_observation": str(frame.index[-1].date()), "unit": contract["selectors"]["unit"],
            "release_period_semantics": ("Native annual statistical period; vintage/classification not supplied"
                                         if field in ANNUAL_FIELDS else
                                         "Native YoY rate; economic period end, dataset update separately retained"),
            "status": "official_pending_store_evidence",
        }
        return frame

    def _fetch_boe_bank_rate(self, spec, *, requested_at, timeout):
        """The native official daily policy series, never the SONIA carry leg."""
        from urllib.parse import urlencode, urlsplit, parse_qs
        from lib.intl_boe_source import parse_bank_rate_xml
        from lib.intl_macro_publication import _read_stable_once
        import hashlib

        if (spec.get("provider") != "boe" or spec.get("series_key") != "IUDBEDR"
                or spec.get("unit") != "percent"):
            raise ValueError("BoE configured field contract mismatch")
        endpoint = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
        native = spec.get("native_input")
        if native is not None:
            if type(native) is not dict or set(native) != {"response", "receipt"}:
                raise ValueError("invalid retained BoE input configuration")
            root = config.data_dir().resolve()
            def retained(key):
                value = native[key]
                if type(value) is not str or Path(value).is_absolute() or ".." in Path(value).parts:
                    raise ValueError("retained BoE input must be data relative")
                path = (root / value).resolve()
                path.relative_to(root)
                return _read_stable_once(path, 8 * 1024 * 1024)
            raw = retained("response")
            receipt = json.loads(retained("receipt"))
            if receipt.get("status") != 200 or receipt.get("sha256") != hashlib.sha256(raw).hexdigest():
                raise ValueError("retained BoE acquisition identity mismatch")
            url, requested_at = receipt.get("url_final"), receipt.get("requested_at")
            received_at = receipt.get("settled_at")
        else:
            today = datetime.now(timezone.utc).date()
            # Revised-data XML is bounded to one calendar year by the native
            # provider contract. A new year is not a fabricated historical read.
            months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
            params = {"CodeVer": "new", "xml.x": "yes", "Datefrom": f"01/Jan/{today.year}",
                      "Dateto": f"{today.day:02d}/{months[today.month - 1]}/{today.year}",
                      "SeriesCodes": "IUDBEDR", "VPD": "N", "VFD": "Y", "VUD": "A"}
            response = self.http_get(endpoint, params=params, retries=1, timeout=timeout)
            if response.status_code != 200:
                raise ValueError("BoE source request did not succeed")
            raw, url = response.content, response.url
            received_at = datetime.now(timezone.utc).isoformat()
        # Reject a retained/mutated foreign carrier before accepting any source.
        if type(url) is not str:
            raise ValueError("BoE source URL missing")
        parsed_url = urlsplit(url)
        if (parsed_url.scheme != "https" or parsed_url.netloc != "www.bankofengland.co.uk"
                or parsed_url.path != "/boeapps/database/_iadb-fromshowcolumns.asp"
                or parsed_url.fragment):
            raise ValueError("BoE source URL mismatch")
        query = parse_qs(parsed_url.query, keep_blank_values=True, strict_parsing=True)
        expected = {"CodeVer": "new", "xml.x": "yes", "SeriesCodes": "IUDBEDR", "VPD": "N", "VFD": "Y", "VUD": "A"}
        if (set(query) != set(expected) | {"Datefrom", "Dateto"}
                or any(query[k] != [v] for k, v in expected.items())
                or any(len(query[k]) != 1 for k in ("Datefrom", "Dateto"))):
            raise ValueError("BoE source query mismatch")
        def source_date(value):
            bits = value.split("/")
            months = {v: i + 1 for i, v in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"))}
            if len(bits) != 3 or len(bits[0]) != 2 or len(bits[2]) != 4 or bits[1] not in months:
                raise ValueError("BoE source date mismatch")
            from datetime import date
            return date(int(bits[2]), months[bits[1]], int(bits[0]))
        start, end = (source_date(query[k][0]) for k in ("Datefrom", "Dateto"))
        if start.year != end.year or end < start:
            raise ValueError("BoE revised-data interval exceeds native one-year range")
        parsed = parse_bank_rate_xml(raw)
        rows = parsed["observations"]
        if not rows or any(not start <= datetime.fromisoformat(r["date"]).date() <= end for r in rows):
            raise ValueError("BoE observations outside requested interval")
        verified = datetime.now(timezone.utc).isoformat()
        def utc(value):
            if type(value) is not str:
                raise ValueError("BoE source clock missing")
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
                raise ValueError("BoE source clock must be UTC")
            return parsed
        if not utc(requested_at) <= utc(received_at) <= utc(verified):
            raise ValueError("BoE source chronology mismatch")
        column = "GB_bank_rate_official"
        frame = pd.DataFrame({column: [r["value"] for r in rows]}, index=pd.to_datetime([r["date"] for r in rows]))
        self._boe_response = dict(response_bytes=raw, source_url=url, requested_at=requested_at,
                                 response_received_at=received_at, input_verified_at=verified)
        self.source_meta[column] = {"provider": "boe", "source_id": "IUDBEDR", "source_url": url,
            "requested_at": requested_at, "source_updated": rows[-1]["source_updated_raw"],
            "source_updated_timezone": None, "last_observation": rows[-1]["date"], "unit": "percent",
            "release_period_semantics": "Daily supplied official Bank Rate; source LAST_UPDATED timezone unknown",
            "status": "official_pending_store_evidence"}
        return frame

    def _fetch_ecb_deposit(self, spec, *, requested_at, timeout):
        """Preserve original exact-series flags before committing observed rows."""
        from lib.intl_ecb_policy_publication import SOURCE_URL, SOURCE_ID, _utc
        from lib.intl_ecb_policy_source import parse_ecb_policy_csv
        from lib.intl_macro_publication import _read_stable_once, _reject_duplicate_keys
        import hashlib
        if (spec.get("provider") != "ecb" or spec.get("series_key") not in {SOURCE_ID, "FM/" + SOURCE_ID}
                or (spec.get("series_key") == SOURCE_ID and spec.get("flow") != "FM")
                or spec.get("unit") != "PCPA" or spec.get("start_period", "1999-01-01") != "1999-01-01"
                or spec.get("base_url", "https://data-api.ecb.europa.eu/service/data") != "https://data-api.ecb.europa.eu/service/data"):
            raise ValueError("ECB exact deposit-series configuration mismatch")
        native = spec.get("native_input")
        if native is not None:
            if type(native) is not dict or set(native) != {"response", "receipt"}:
                raise ValueError("invalid retained ECB input configuration")
            root = config.data_dir().resolve()
            def retained(key):
                value = native[key]
                if type(value) is not str or Path(value).is_absolute() or ".." in Path(value).parts:
                    raise ValueError("retained ECB input must be data relative")
                path = (root / value).resolve(); path.relative_to(root)
                return _read_stable_once(path, 8 * 1024 * 1024)
            raw = retained("response")
            receipt = json.loads(retained("receipt"), object_pairs_hook=_reject_duplicate_keys)
            if (receipt.get("status") != 200 or receipt.get("url") != SOURCE_URL
                    or receipt.get("sha256") != hashlib.sha256(raw).hexdigest()):
                raise ValueError("retained ECB response identity mismatch")
            requested_at, received = receipt.get("requested_at"), receipt.get("received_at")
        else:
            response = self.http_get(SOURCE_URL.split("?")[0],
                params={"format": "csvdata", "startPeriod": "1999-01-01"}, retries=1, timeout=timeout)
            if response.status_code != 200 or response.url != SOURCE_URL:
                raise ValueError("unrecognized ECB response")
            raw, received = response.content, datetime.now(timezone.utc).isoformat()
        parsed = parse_ecb_policy_csv(raw)
        verified = datetime.now(timezone.utc).isoformat()
        if not _utc(requested_at) <= _utc(received) <= _utc(verified):
            raise ValueError("ECB response chronology mismatch")
        rows = [row for row in parsed["observations"] if row["status"] == "observed"]
        if not rows:
            raise ValueError("ECB original response has no observed rows")
        frame = pd.DataFrame({"ez_depo_rate": [row["value"] for row in rows]},
                             index=pd.to_datetime([row["date"] for row in rows]))
        self._ecb_policy_response = dict(response_bytes=raw, source_url=SOURCE_URL,
            requested_at=requested_at, response_received_at=received, input_verified_at=verified)
        self.source_meta["ez_depo_rate"] = {"provider": "ecb", "source_id": SOURCE_ID,
            "source_url": SOURCE_URL, "requested_at": requested_at,
            "source_updated": parsed["observations"][-1]["date"],
            "last_observation": rows[-1]["date"], "unit": "PCPA",
            "release_period_semantics": spec.get("release_period_semantics"),
            "status": "official" if parsed["observations"][-1]["status"] == "observed" else "official_withheld"}
        return frame


    @staticmethod
    def _jsonstat_series(payload: dict[str, Any]) -> pd.Series:
        """Extract the time axis from a one-series Eurostat JSON-stat payload."""
        dims = list(payload.get("id") or [])
        sizes = [int(value) for value in (payload.get("size") or [])]
        if "time" not in dims or not sizes or any(size == 0 for size in sizes):
            raise ValueError("eurostat: empty or malformed dimension set")
        time_axis = dims.index("time")
        time_category = (
            payload.get("dimension", {})
            .get("time", {})
            .get("category", {})
            .get("index", {})
        )
        if isinstance(time_category, list):
            labels = {label: idx for idx, label in enumerate(time_category)}
        else:
            labels = {str(label): int(idx) for label, idx in time_category.items()}
        label_by_pos = {idx: label for label, idx in labels.items()}
        stride = prod(sizes[time_axis + 1 :]) if time_axis + 1 < len(sizes) else 1
        values: dict[pd.Timestamp, float] = {}
        for raw_flat, raw_value in (payload.get("value") or {}).items():
            flat = int(raw_flat)
            time_pos = (flat // stride) % sizes[time_axis]
            label = label_by_pos.get(time_pos)
            if label is None:
                continue
            parsed = pd.to_numeric(raw_value, errors="coerce")
            if pd.isna(parsed):
                continue
            values[pd.Timestamp(f"{label}-01" if len(label) == 7 else label)] = float(
                parsed
            )
        if not values:
            raise ValueError("eurostat: no numeric observations")
        return pd.Series(values).sort_index()

    def _fetch_official(self, stored_col: str, spec: dict[str, Any]) -> pd.DataFrame:
        provider = str(spec["provider"])
        retries = int(spec.get("retries", self.cfg.get("retries", 3)))
        timeout = int(spec.get("timeout_s", 20))
        requested_at = datetime.now(timezone.utc).isoformat()
        if stored_col == "ez_depo_rate":
            return self._fetch_ecb_deposit(spec, requested_at=requested_at, timeout=timeout)
        if stored_col == "GB_bank_rate_official":
            return self._fetch_boe_bank_rate(spec, requested_at=requested_at, timeout=timeout)
        native_period_fields = {"EZ_gdp_yoy_official": "EZ.gdp_yoy", "EZ_hicp_yoy_official": "EZ.cpi_yoy",
                                "EZ_current_account_gdp_official": "EZ.annual_current_account"}
        if stored_col in native_period_fields:
            return self._fetch_eurostat_yoy(native_period_fields[stored_col], spec,
                                            requested_at=requested_at, retries=retries, timeout=timeout)
        if provider == "ecb":
            base = str(
                spec.get("base_url") or "https://data-api.ecb.europa.eu/service/data"
            )
            raw_key = str(spec["series_key"])
            if "/" in raw_key:
                flow, key = raw_key.split("/", 1)
            elif spec.get("flow"):
                flow, key = str(spec["flow"]), raw_key
            else:
                flow, key = raw_key.split(".", 1)
            response = self.http_get(
                f"{base.rstrip('/')}/{flow}/{key}",
                params={
                    "format": "csvdata",
                    "startPeriod": str(spec.get("start_period", "1999-01-01")),
                },
                retries=retries,
                timeout=timeout,
            )
            raw = pd.read_csv(io.StringIO(response.text))
            if not {"TIME_PERIOD", "OBS_VALUE"}.issubset(raw.columns):
                raise ValueError("ecb: TIME_PERIOD/OBS_VALUE columns missing")
            numeric = pd.to_numeric(raw["OBS_VALUE"], errors="coerce")
            series = pd.Series(
                numeric.to_numpy(),
                index=pd.to_datetime(raw["TIME_PERIOD"], errors="coerce"),
            ).dropna()
            source_updated = (
                str(raw["TIME_PERIOD"].dropna().iloc[-1])
                if not raw["TIME_PERIOD"].dropna().empty
                else None
            )
            response_unit = (
                str(raw["UNIT"].dropna().iloc[-1])
                if "UNIT" in raw and not raw["UNIT"].dropna().empty
                else None
            )
        elif provider == "eurostat":
            base = str(
                spec.get("base_url")
                or "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
            )
            dataset = str(spec["dataset"])
            params = {"lang": "en", **(spec.get("params") or {})}
            if spec.get("since"):
                params["sinceTimePeriod"] = str(spec["since"])
            response = self.http_get(
                f"{base.rstrip('/')}/{dataset}",
                params=params,
                retries=retries,
                timeout=timeout,
            )
            payload = response.json()
            series = self._jsonstat_series(payload)
            source_updated = payload.get("updated")
            response_unit = str((spec.get("params") or {}).get("unit") or "")
        else:
            raise ValueError(f"unsupported official provider: {provider}")

        if series.empty or series.index.hasnans:
            raise ValueError(f"{provider}: invalid observation dates")
        expected_unit = str(spec.get("unit") or "")
        if expected_unit and response_unit and expected_unit != response_unit:
            raise ValueError(
                f"{provider}: unit mismatch expected={expected_unit} actual={response_unit}"
            )
        series = series[~series.index.duplicated(keep="last")].sort_index()
        self.source_meta[stored_col] = {
            "provider": provider,
            "source_id": spec.get("series_key") or spec.get("dataset"),
            "source_url": response.url,
            "requested_at": requested_at,
            "source_updated": source_updated,
            "last_observation": str(series.index[-1].date()),
            "unit": response_unit or expected_unit,
            "release_period_semantics": spec.get("release_period_semantics"),
            "status": "official",
        }
        return pd.DataFrame({stored_col: series})

    def _write_provenance(self) -> None:
        path = config.data_dir() / self.group / "provenance.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema": "intl_macro_provenance.v1",
                    "built": datetime.now(timezone.utc).isoformat(),
                    "series": self.source_meta,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        self._eurostat_responses = {}
        # No cold-start branch needed: fredgraph.csv returns each series' FULL history
        # every call, so this plane self-seeds on the first run regardless of
        # `full_history` (unlike the price plane, which is 1mo-incremental).
        plan: list[tuple[str, str]] = []
        for cc, c in self.countries.items():
            for metric, fid in (c.get("fred") or {}).items():
                plan.append((f"{cc}_{metric}", fid))
        for col, fid in (self.cfg.get("extra_series") or {}).items():
            plan.append((col, fid))

        frames: dict[str, pd.DataFrame] = {}
        conn_errors = 0  # consecutive connection failures (all series share one host)
        for i, (col, fid) in enumerate(plan):
            try:
                frames[col] = self._fetch_fred(fid).rename(columns={"_": col})
                self.source_meta[col] = {
                    "provider": "fred_fallback",
                    "source_id": fid,
                    "source_url": f"{self.cfg['fred_base_url']}?id={fid}",
                    "requested_at": datetime.now(timezone.utc).isoformat(),
                    "source_updated": None,
                    "last_observation": str(frames[col].dropna().index[-1].date()),
                    "unit": None,
                    "release_period_semantics": "Inherited from the underlying series",
                    "status": "fallback",
                }
                conn_errors = 0
            except Exception as e:  # noqa: BLE001 — one series down can't break the plane
                log.warning("intl_macro %s (%s) failed: %s", col, fid, e)
                conn_errors = conn_errors + 1 if is_connection_error(e) else 0
                if conn_errors >= _ABORT_AFTER_CONSECUTIVE_CONN_ERRORS:
                    log.error(
                        "intl_macro: FRED frontend unreachable (%d consecutive "
                        "connection failures) — skipping the remaining %d series "
                        "to fail fast",
                        conn_errors,
                        len(plan) - i - 1,
                    )
                    break

        official_plan = self.cfg.get("official_series") or {}
        for col, spec in official_plan.items():
            try:
                frames[col] = self._fetch_official(col, spec)
            except Exception as e:  # noqa: BLE001 — preserve fallback / last-good store
                log.warning(
                    "intl_macro official %s (%s) failed; %s: %s",
                    col,
                    spec.get("provider"),
                    "keeping FRED fallback"
                    if col in frames
                    else "leaving series missing",
                    e,
                )
                if col in self.source_meta:
                    self.source_meta[col]["official_error"] = f"{type(e).__name__}: {e}"
                else:
                    self.source_meta[col] = {
                        "provider": spec.get("provider"),
                        "source_id": spec.get("series_key") or spec.get("dataset"),
                        "requested_at": datetime.now(timezone.utc).isoformat(),
                        "status": "missing",
                        "official_error": f"{type(e).__name__}: {e}",
                    }

        if not frames:
            raise RuntimeError(
                "intl_macro: every FRED series failed (FRED unreachable?)"
            )
        self._write_provenance()
        official_ok = sum(
            1 for meta in self.source_meta.values() if meta.get("status") == "official"
        )
        log.info(
            "intl_macro: %d total series (%d/%d FRED plan; %d official overrides)",
            len(frames),
            len([col for col, _ in plan if col in frames]),
            len(plan),
            official_ok,
        )
        return frames
