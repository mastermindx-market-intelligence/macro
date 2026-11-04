def reconcile_bis_monthly_policy(previous, incoming, cc, *, today):
    """Keep whole evidence records; acquisition order is not correction order."""
    candidates = []
    for raw in (previous, incoming):
        if type(raw) is not dict:
            continue
        items = raw.get("retained_contexts") if raw.get("schema") == "intl_bis_monthly_context_conflict.v1" else [raw]
        if type(items) is not list or len(items) > 12:
            raise ValueError("bis_retained_context_capacity")
        for item in items:
            record = qualify_bis_monthly_policy(item, cc, today=today)
            if type(record) is dict and record.get("comparison_qualification") != "unqualified_source":
                candidates.append(record)
    if not candidates:
        return qualify_bis_monthly_policy(previous or incoming, cc, today=today)
    period = max(r["period"] for r in candidates)
    candidates = [r for r in candidates if r["period"] == period]
    economic_fields = ("metric","period","value","unit","provider","source_url","dataset_url",
                       "series_id","status","frequency","definition")
    meaning_fields = ("instrument","setting_qualifier","instrument_effective_from","observation_convention")
    def identity(record, fields):
        return json.dumps({k:record.get(k) for k in fields},sort_keys=True,separators=(",",":"),ensure_ascii=False)
    def custody(record):
        return (_time(record["first_observed_at"]), _time(record["retrieved_at"]),
                json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=False))
    # Deduplicate identical proof while retaining one complete acquisition.
    proofs = {}
    for record in candidates:
        daily = record.get("daily_reference")
        daily_semantics = {k:v for k,v in daily.items() if k != "source_sha256"} if type(daily) is dict else daily
        key = (identity(record,economic_fields),identity(record,meaning_fields),
               record.get("comparison_qualification"),record.get("comparison_observation_date"),
               json.dumps(daily_semantics,sort_keys=True,separators=(",",":"),ensure_ascii=False))
        if key not in proofs or custody(record) < custody(proofs[key]):
            proofs[key] = record
    candidates = list(proofs.values())
    if len(candidates) == 1:
        return deepcopy(candidates[0])
    if len({identity(r,economic_fields) for r in candidates}) == 1:
        qualified = [r for r in candidates if r.get("comparison_qualification") == "qualified"]
        missing_timing = [r for r in candidates if r.get("daily_reference") is None
                          and r.get("comparison_qualification") in ("qualified","unresolved_instrument_transition")]
        comparable = (qualified and len({identity(r,meaning_fields) for r in qualified}) == 1
                      and all(r in qualified or r in missing_timing for r in candidates))
        if comparable:
            latest_day = max(r.get("comparison_observation_date") or "" for r in qualified)
            strongest = [r for r in qualified if (r.get("comparison_observation_date") or "") == latest_day]
            return deepcopy(min(strongest,key=custody))
    if len(candidates) > 12:
        raise ValueError("bis_retained_context_capacity")
    candidates.sort(key=lambda r: (identity(r,economic_fields),custody(r)))
    # These clocks describe when all conflicting evidence was known. They are
    # not attached to a selected numeric value or an invented source receipt.
    return {"schema":"intl_bis_monthly_context_conflict.v1","metric":"policy",
            "period":period,"value":None,"unit":"%","status":"conflict",
            "provider":"Bank for International Settlements",
            "source_url":"https://data.bis.org/topics/CBPOL","dataset_url":_BIS_POLICY_DATASET,
            "series_id":_BIS_POLICY_SERIES[cc],"frequency":"monthly",
            "comparison_qualification":"retained_conflict",
            "first_observed_at":max(candidates,key=lambda r:_time(r["first_observed_at"]))["first_observed_at"],
            "retrieved_at":max(candidates,key=lambda r:_time(r["retrieved_at"]))["retrieved_at"],
            "retained_contexts":deepcopy(candidates)}


