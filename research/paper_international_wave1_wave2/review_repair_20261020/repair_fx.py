from pathlib import Path
w=Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018')
p=w/'lib/intl_currency_observation.py';s=p.read_text()
helper=(w/'research/paper_international_wave1_wave2/review_repair_20261020/fx_receipt_helpers.txt').read_text()
assert 'FX_CAPTURE_COLUMN' not in s
s=s.replace('\ndef _captured_day(source):',helper+'\n\ndef _captured_day(source):')
s=s.replace('def _valid_source(source, cc, today):','def _valid_source(source, cc, today, *, selecting=False):')
s=s.replace('''    if (type(source) is not dict or set(source) != keys''','''    if type(source) is dict and source.get("kind") == "captured_store":
        keys.add("endpoint_receipts")
    if (type(source) is not dict or set(source) != keys''',1)
s=s.replace('''    if source["kind"] == "configured_store":
        return all(source[k] is None for k in (
            "dataset_url", "retrieved_at", "response_sha256", "provider_symbol"))''','''    if source["kind"] == "configured_store":
        # A series name and a daily label do not establish acquisition custody.
        return False
    if source["kind"] == "captured_store":
        if any(source[k] is not None for k in ("dataset_url", "response_sha256", "provider_symbol")):
            return False
        receipts = source["endpoint_receipts"]
        if selecting and receipts is None:
            return source["retrieved_at"] is None
        if type(receipts) is not dict or set(receipts) != {"start", "end"}:
            return False
        for receipt in receipts.values():
            if type(receipt) is not dict:
                return False
            try:
                value = _price(float.fromhex(receipt.get("quote_hex", "")))
            except (TypeError, ValueError, OverflowError):
                return False
            if _read_adapter_receipt(receipt, cc, _day(receipt.get("date")), value, today) is None:
                return False
        latest = max((r["adapter_result_returned_at_utc"] for r in receipts.values()), key=_instant)
        return source["retrieved_at"] == latest''')
s=s.replace('''    if not _valid_source(source, cc, today):
        return _missing(cc, "source_unavailable")''','''    if not _valid_source(source, cc, today, selecting=True):
        return _missing(cc, "source_unavailable")''')
s=s.replace('''    by_day = {}
    for item in observations:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            continue
        observed, value = _day(item[0]), _price(item[1])
        if observed is None or observed >= cutoff or value is None:
            continue
        by_day.setdefault(observed, set()).add(value)''','''    by_day, row_receipts = {}, {}
    stored = source["kind"] == "captured_store"
    for item in observations:
        if not isinstance(item, (tuple, list)) or len(item) != (3 if stored else 2):
            continue
        observed, value = _day(item[0]), _price(item[1])
        if observed is None or observed >= cutoff or value is None:
            continue
        if stored:
            receipt = _read_adapter_receipt(item[2], cc, observed, value, today)
            if receipt is None:
                continue
            identity = (observed, value)
            prior = row_receipts.get(identity)
            if (prior is None or _instant(receipt["adapter_result_returned_at_utc"])
                    < _instant(prior["adapter_result_returned_at_utc"])):
                row_receipts[identity] = receipt
        by_day.setdefault(observed, set()).add(value)''')
old='''    payload = {
        "schema": SCHEMA, "status": "available", "cc": cc,'''
new='''    selected_source = dict(source)
    if stored:
        receipts = {"start": row_receipts[(start, start_quote)], "end": row_receipts[(end, end_quote)]}
        selected_source["endpoint_receipts"] = receipts
        selected_source["retrieved_at"] = max(
            (r["adapter_result_returned_at_utc"] for r in receipts.values()), key=_instant)
    payload = {
        "schema": SCHEMA, "status": "available", "cc": cc,'''
assert old in s;s=s.replace(old,new)
s=s.replace('''        "value": value, "source": dict(source),''','''        "value": value, "source": selected_source,''')
old='''    try:
        target = reference_date(end)
    except ValueError:
        return missing'''
new='''    if raw["source"]["kind"] == "captured_store":
        receipts = raw["source"]["endpoint_receipts"]
        if (_read_adapter_receipt(receipts["start"], cc, start, a, today) is None
                or _read_adapter_receipt(receipts["end"], cc, end, b, today) is None):
            return missing
    try:
        target = reference_date(end)
    except ValueError:
        return missing'''
assert old in s;s=s.replace(old,new)
p.write_text(s)

p=w/'collectors/intl_prices.py';s=p.read_text()
s=s.replace('import logging\n','import logging\nfrom datetime import datetime, timezone\n',1)
s=s.replace('from lib import config, store','from lib import config, store\nfrom lib.intl_currency_observation import FX_CAPTURE_COLUMN, adapter_capture_receipt',1)
s=s.replace('''            df = self._download(batch, period)''','''            # Clear before every call: a failure/override cannot inherit another
            # invocation's acquisition clock.
            self._last_download_capture = None
            df = self._download(batch, period)''')
s=s.replace('''                    frames[t] = sub''','''                    if t in {c["fx"] for c in self.countries.values()}:
                        # Daily labels are provider calendar dates, never UTC-
                        # converted local midnights. The ordinary daily download
                        # already uses this normalization explicitly.
                        sub.index = pd.to_datetime(sub.index).tz_localize(None).normalize()
                        capture = self._last_download_capture
                        if capture:
                            sub[FX_CAPTURE_COLUMN] = [
                                adapter_capture_receipt(t, stamp.date(), value,
                                    started_at=capture[0], returned_at=capture[1])
                                for stamp, value in sub["close"].items()]
                    frames[t] = sub''')
s=s.replace('''                df = yf.download(batch, period=period, auto_adjust=True,
                                 progress=False, group_by="ticker", threads=True)''','''                started = datetime.now(timezone.utc).isoformat()
                df = yf.download(batch, period=period, interval="1d", ignore_tz=True,
                                 auto_adjust=True, progress=False, group_by="ticker", threads=True)
                returned = datetime.now(timezone.utc).isoformat()''')
s=s.replace('''                return df
            except Exception as e:''','''                self._last_download_capture = (started, returned)
                return df
            except Exception as e:''')
p.write_text(s)

p=w/'engine/intl_inputs.py';s=p.read_text()
helper='''def country_currency_inputs():
    """Read quote and capture from the same frame, without changing legacy closes."""
    from lib.intl_currency_observation import FX_CAPTURE_COLUMN, stored_source_context
    result = {}
    for cc, cfg in countries().items():
        observations = []
        try:
            frame = store.read("intl", cfg["fx"])
            if frame is not None and {"close", FX_CAPTURE_COLUMN} <= set(frame.columns):
                for stamp, row in frame[["close", FX_CAPTURE_COLUMN]].iterrows():
                    try:
                        label = pd.Timestamp(stamp).date()
                        observations.append((label, row["close"], row[FX_CAPTURE_COLUMN]))
                    except (TypeError, ValueError, OverflowError):
                        continue
        except Exception:  # A broken optional FX frame cannot kill country analysis.
            log.warning("intl: currency capture unavailable for %s", cc)
        result[cc] = {"observations": observations, "source": stored_source_context(cc, cfg)}
    return result


'''
assert 'def country_currency_inputs(' not in s
s=s.replace('def read_intl_macro_col(',helper+'def read_intl_macro_col(',1);p.write_text(s)

p=w/'engine/intl_run.py';s=p.read_text()
s=s.replace('build_currency_observation, incumbent_source_context','build_currency_observation, stored_source_context')
s=s.replace('''                   fx_source: dict | None = None) -> tuple''','''                   fx_source: dict | None = None,
                   fx_observations: list | None = None) -> tuple''')
old='''        observations = []
        for stamp, value in (fx.items() if fx is not None else []):
            try:
                observations.append((pd.Timestamp(stamp).date(), value))
            except (TypeError, ValueError, OverflowError):
                continue'''
new='''        observations = fx_observations
        if observations is None:
            observations = []
            for stamp, value in (fx.items() if fx is not None else []):
                try:
                    observations.append((pd.Timestamp(stamp).date(), value))
                except (TypeError, ValueError, OverflowError):
                    continue'''
assert old in s;s=s.replace(old,new)
s=s.replace('''    equity = intl_equity_risk.equity_risk_all()
    if closes.empty:''','''    equity = intl_equity_risk.equity_risk_all()
    currency_inputs = intl_inputs.country_currency_inputs()
    if closes.empty:''')
s=s.replace('''                                      fx_source=incumbent_source_context(cc, country_config))''','''                                      fx_source=currency_inputs.get(cc, {}).get("source")
                                          or stored_source_context(cc, country_config),
                                      fx_observations=currency_inputs.get(cc, {}).get("observations", []))''')
p.write_text(s)
print("Repaired acquisition, row custody, same-frame reader and production bridge.")
