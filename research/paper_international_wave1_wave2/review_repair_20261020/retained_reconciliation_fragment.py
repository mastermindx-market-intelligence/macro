def _merge_retained_record(known, incoming, diagnostics):
    """Reconcile identical content without detaching clocks from their receipts."""
    records = (deepcopy(known), deepcopy(incoming))
    # One complete acquisition record wins. Do not combine an early retrieval
    # from one copy with the first-observation/admission claim of another.
    winner = min(records, key=lambda r: (
        _time(r["admitted_at"]), _time(r["first_observed_at"]),
        _time(r["retrieved_at"]), _digest(r)))
    result = deepcopy(winner)
    withdrawal_fields = ("withdrawn_at", "withdrawal_source_url", "withdrawal_admitted_at")
    for field in withdrawal_fields:
        result.pop(field, None)
    events = [r for r in records if r.get("withdrawn_at")]
    if events:
        # This is one whole retained withdrawal event, including its source.
        event = min(events, key=lambda r: (_time(r["withdrawal_admitted_at"]), _digest(r)))
        result.update({field: deepcopy(event[field]) for field in withdrawal_fields})
    supersessions = [r for r in records if r.get("superseded_at")]
    if supersessions:
        event = min(supersessions, key=lambda r: (_time(r["superseded_at"]), _digest(r)))
        result["superseded_at"] = event["superseded_at"]
    if (len({r["admission_status"] for r in records}) > 1
            or len({r.get("supersedes_record_id") for r in records}) > 1):
        result["admission_status"] = "conflict"
        diagnostics.append({"kind": "retained_identity_conflict", "record_id": result["record_id"]})
    known.clear()
    known.update(result)


