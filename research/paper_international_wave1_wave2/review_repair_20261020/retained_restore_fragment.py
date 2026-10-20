def _restore_retained_publications(previous, incoming, now):
    """Reconstruct the union before evaluating its accepted correction graph."""
    lookup, diagnostics = {}, []
    for envelope in (previous, incoming):
        for raw in envelope if type(envelope) is list else []:
            if not _retained_custody_valid(raw, now):
                diagnostics.append({"kind": "invalid_retained_custody"})
                continue
            record = normalize_publication(raw, observed_at=now)
            if record is None:
                diagnostics.append({"kind": "invalid_archived_publication"})
                continue
            known = lookup.get(record["record_id"])
            if known is None:
                lookup[record["record_id"]] = record
            else:
                _merge_retained_record(known, record, diagnostics)
    archive = list(lookup.values())
    if len(archive) > MAX_ARCHIVE_RECORDS:
        raise ValueError("forecast_archive_capacity")
    groups = {}
    for record in archive:
        if record["admission_status"] == "accepted":
            groups.setdefault((record["publication_key"], record["correction_sequence"]), []).append(record)
    for records in groups.values():
        if len(records) > 1:
            for record in records:
                record["admission_status"] = "conflict"
                diagnostics.append({"kind": "retained_identity_conflict", "record_id": record["record_id"]})
    latest = {}
    for record in sorted(archive, key=lambda r: (r["correction_sequence"], r["record_id"])):
        if record["admission_status"] != "accepted":
            continue
        prior = latest.get(record["publication_key"])
        predecessor = lookup.get(record.get("supersedes_record_id"))
        initial = record["correction_sequence"] == 0 and prior is None and predecessor is None
        ordered = (predecessor is not None and prior is predecessor
                   and predecessor["admission_status"] == "accepted"
                   and predecessor["publication_key"] == record["publication_key"]
                   and record["correction_sequence"] > predecessor["correction_sequence"]
                   and _source(record.get("correction_source_url"), record["provider"])
                   and _time(predecessor["admitted_at"]) <= _time(record["admitted_at"]))
        if not (initial or ordered):
            record["admission_status"] = "conflict"
            diagnostics.append({"kind": "invalid_retained_lineage", "record_id": record["record_id"]})
            continue
        if ordered:
            event = predecessor.get("superseded_at")
            if not event or _time(record["admitted_at"]) < _time(event):
                predecessor["superseded_at"] = record["admitted_at"]
        latest[record["publication_key"]] = record
    archive.sort(key=lambda r: (r["published"], r["cc"], r["series_id"], r["correction_sequence"], r["record_id"]))
    return archive, diagnostics


