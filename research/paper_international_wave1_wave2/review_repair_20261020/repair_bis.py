from pathlib import Path
w=Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018')
p=w/'lib/intl_policy_evidence.py';s=p.read_text()
s=s.replace('import math\n','import math\nimport re\n',1)
helper=(w/'research/paper_international_wave1_wave2/review_repair_20261020/bis_qualification_helpers.txt').read_text()
assert '_BIS_POINT_ERAS' not in s
s=s.replace('\ndef _official_url(value, host):',helper+'\n\ndef _official_url(value, host):')
old='''            and _day(selected["effective_date"]) <= month_end
            and context["value"] != selected["value"]):'''
new='''            and ((context.get("comparison_observation_date")
                  and _day(context["comparison_observation_date"]) is not None
                  and _day(context["period"] + "-01") <= _day(context["comparison_observation_date"]) <= month_end
                  and _day(selected["effective_date"]) <= _day(context["comparison_observation_date"]))
                 or (not context.get("comparison_observation_date")
                     and _day(selected["effective_date"]) < _day(context["period"] + "-01")))
            and context["value"] != selected["value"]):'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)

p=w/'collectors/intl_country_sources.py';s=p.read_text()
s=s.replace('from lib.intl_policy_evidence import merge_policy_decisions, merge_policy_reviews',
            'from lib.intl_policy_evidence import merge_policy_decisions, merge_policy_reviews, qualify_bis_monthly_policy')
s=s.replace('''    series = {}
    with ZipFile''','''    series, daily = {}, {}
    with ZipFile''',1)
s=s.replace('''                if area not in AREAS or _code(row["FREQ:Frequency"]) != "M":
                    continue''','''                frequency = _code(row["FREQ:Frequency"])
                if area not in AREAS or frequency not in (("M","D") if kind == "policy" else ("M",)):
                    continue''',1)
old='''                period = _month(row["TIME_PERIOD:Time period or range"])
                # Month-end data for an incomplete future month is not an observation.'''
new='''                label = row["TIME_PERIOD:Time period or range"]
                if frequency == "D":
                    try:
                        observed = date.fromisoformat(label)
                    except (TypeError,ValueError):
                        continue
                    if observed.isoformat() != label or observed >= cutoff:
                        continue
                    period = label[:7]
                else:
                    period = _month(label)
                # Month-end data for an incomplete future month is not an observation.'''
assert s.count(old)==1;s=s.replace(old,new)
old='''                points = series.setdefault(cc, {})
                if period in points and points[period]["value"] != value:'''
new='''                if frequency == "D":
                    points = daily.setdefault(cc,{})
                    point = {"date":label,"value":value,"series_id":"D."+area,
                             "definition":row.get("COMPILATION:Compilation") or row.get("COVERAGE:Coverage") or ""}
                    prior_daily = points.get(period)
                    if prior_daily and prior_daily["date"] == label and prior_daily != point:
                        raise ValueError("conflicting_bis_daily_observation")
                    if prior_daily is None or label > prior_daily["date"]:
                        points[period] = point
                    continue
                points = series.setdefault(cc, {})
                if period in points and points[period]["value"] != value:'''
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('''    url = BIS_CPI if kind == "inflation" else BIS_POLICY
    for cc, points in series.items():''','''    url = BIS_CPI if kind == "inflation" else BIS_POLICY
    digest = sha256(blob).hexdigest()
    for cc, points in series.items():''',1)
s=s.replace('''            "source_sha256": sha256(blob).hexdigest(),
        }
    return {"observations": observations, "series": series}''','''            "source_sha256": digest,
        }
        if kind == "policy":
            if last in daily.get(cc,{}):
                observations[cc]["daily_reference"] = {**daily[cc][last], "source_sha256":digest}
            observations[cc] = qualify_bis_monthly_policy(observations[cc],cc,today=cutoff)
    return {"observations": observations, "series": series}''',1)

old='''    for cc, values in _mapping(incoming.get("official")).items():'''
new='''    observed_at = datetime.now(timezone.utc).isoformat()
    for cc, values in result["official"].items():
        if type(values.get("policy")) is dict:
            values["policy"] = qualify_bis_monthly_policy(values["policy"],cc,today=today)
    for cc, values in _mapping(incoming.get("official")).items():'''
assert s.count(old)==1;s=s.replace(old,new)
old='''            if observation["period"] >= current_clock:
                existing[key] = deepcopy(observation)'''
new='''            if observation["period"] >= current_clock:
                candidate = deepcopy(observation)
                if key == "policy":
                    candidate = qualify_bis_monthly_policy(candidate,cc,today=today)
                    identity_fields = ("metric","period","value","unit","provider","source_url",
                        "dataset_url","series_id","status","frequency","instrument","setting_qualifier",
                        "instrument_effective_from","comparison_observation_date","comparison_qualification")
                    same = (all(candidate.get(k) == current.get(k) for k in identity_fields)
                            and (candidate.get("comparison_qualification") == "qualified"
                                 or candidate.get("definition") == current.get("definition")))
                    if same and current.get("first_observed_at"):
                        continue
                    if not preserve_custody:
                        candidate["first_observed_at"] = observed_at
                    candidate = qualify_bis_monthly_policy(candidate,cc,today=today)
                existing[key] = candidate'''
assert s.count(old)==1;s=s.replace(old,new)
# Use the single actual merge-boundary clock for all acquisition admissions.
assert s.count('    observed_at = datetime.now(timezone.utc).isoformat()')==2
at=s.rfind('    observed_at = datetime.now(timezone.utc).isoformat()\n')
s=s[:at]+s[at:].replace('    observed_at = datetime.now(timezone.utc).isoformat()\n','',1)
p.write_text(s)

p=w/'tests/test_intl_policy_evidence.py';s=p.read_text()
old='''            "observation_convention": "end_of_period", "first_observed_at": "2026-10-01T12:00:00+00:00"}'''
new='''            "observation_convention": "end_of_period", "first_observed_at": "2026-10-01T12:00:00+00:00",
            "comparison_observation_date": "2026-09-30"}'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
print("Qualified BIS source semantics, actual daily corroboration and retained knowledge clocks.")
