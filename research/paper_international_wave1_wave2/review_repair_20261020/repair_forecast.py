from pathlib import Path
import subprocess
w=Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018')
p=w/'lib/intl_forecast_vintages.py'
s=p.read_text()
old='def merge_publications(previous, incoming, *, observed_at=None):'
new='''def _retained_custody_valid(raw, now):
    """A retained archive must carry real clocks; reconstruction creates none."""
    if type(raw) is not dict:
        return False
    fields = ("retrieved_at", "first_observed_at", "admitted_at")
    if any(type(raw.get(k)) is not str or "T" not in raw[k] for k in fields):
        return False
    retrieved, first, admitted = (_time(raw[k]) for k in fields)
    if any(clock is None for clock in (retrieved, first, admitted)):
        return False
    if not retrieved <= first <= admitted <= _time(now):
        return False
    if raw.get("withdrawn_at"):
        event, known = _time(raw["withdrawn_at"]), _time(raw.get("withdrawal_admitted_at"))
        published = _time(raw.get("published"))
        if (event is None or known is None or published is None
                or not published <= event <= known <= _time(now) or known < admitted):
            return False
    elif raw.get("withdrawal_admitted_at"):
        return False
    if raw.get("superseded_at"):
        event = _time(raw["superseded_at"])
        if event is None or not admitted <= event <= _time(now):
            return False
    return True


def merge_publications(previous, incoming, *, observed_at=None, preserve_custody=False):'''
assert s.count(old)==1
s=s.replace(old,new)
s=s.replace('''    """Stable content plus explicitly ordered admission and withdrawal events."""''','''    """Admit live content, or reconstruct already admitted retained archives.

    Only the trusted cache reader uses preserve_custody. Live arrivals always
    receive the actual admission clock, irrespective of supplied lifecycle data.
    """''')
s=s.replace('''    for raw in previous if type(previous) is list else []:
        record = normalize_publication(raw, observed_at=now)''','''    for raw in previous if type(previous) is list else []:
        if preserve_custody and not _retained_custody_valid(raw, now):
            diagnostics.append({"kind": "invalid_retained_custody"})
            continue
        record = normalize_publication(raw, observed_at=now)''')
s=s.replace('''    for raw in incoming if type(incoming) is list else []:
        record = normalize_publication(raw, observed_at=now)''','''    for raw in incoming if type(incoming) is list else []:
        if preserve_custody and not _retained_custody_valid(raw, now):
            diagnostics.append({"kind": "invalid_retained_custody"})
            continue
        record = normalize_publication(raw, observed_at=now)''')
s=s.replace('''        if known is None and record["correction_sequence"] == 0 and not record.get("supersedes_record_id"):''','''        if (not preserve_custody and known is None and record["correction_sequence"] == 0
                and not record.get("supersedes_record_id")):''')
s=s.replace('''                    known["withdrawal_admitted_at"] = now''','''                    known["withdrawal_admitted_at"] = record["withdrawal_admitted_at"] if preserve_custody else now''')
s=s.replace('''            continue
        record["first_observed_at"] = now
        record["admitted_at"] = now
        # Future/lifecycle fields from untrusted incoming records cannot erase
        # other records. Valid supersession is established below.
        record.pop("superseded_at", None)''','''            if preserve_custody and record.get("superseded_at") and not known.get("superseded_at"):
                known["superseded_at"] = record["superseded_at"]
            continue
        if not preserve_custody:
            record["first_observed_at"] = now
            record["admitted_at"] = now
            # A new acquisition cannot supply a supersession event for itself.
            record.pop("superseded_at", None)''')
s=s.replace('''            record["withdrawal_admitted_at"] = now''','''            if not preserve_custody:
                record["withdrawal_admitted_at"] = now''')
s=s.replace('''        ambiguous = len(records) > 1''','''        ambiguous = len([r for r in records if not preserve_custody
                         or r["admission_status"] == "accepted"]) > 1''')
s=s.replace('''                       and (prior is None or predecessor["record_id"] == prior["record_id"]))''','''                       and (prior is None or predecessor["record_id"] == prior["record_id"])
                       and (not preserve_custody
                            or _time(predecessor["admitted_at"]) <= _time(record["admitted_at"])))''')
s=s.replace('''            accepted_new = not ambiguous and (ordered or (prior is None and sequence == 0))''','''            accepted_new = (not ambiguous and (ordered or (prior is None and sequence == 0))
                            and (not preserve_custody or record["admission_status"] == "accepted"))''')
s=s.replace('''                predecessor["superseded_at"] = now''','''                predecessor["superseded_at"] = record["admitted_at"] if preserve_custody else now''')
p.write_text(s)
p=w/'collectors/intl_country_sources.py';s=p.read_text()
old='archive, diagnostics = merge_publications(publications(result), publications(incoming), observed_at=observed_at)'
new='''archive, diagnostics = merge_publications(publications(result), publications(incoming),
                                             observed_at=observed_at, preserve_custody=preserve_custody)'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
log=w/'research/paper_international_wave1_wave2/review_repair_20261020/forecast_metric_after.log'
with log.open('w') as f:
    r=subprocess.run(['/tmp/intl-country-cockpit-testenv-20261018/bin/python','-m','pytest','-q',
                      'tests/test_intl_forecast_vintages.py','tests/test_intl_country_cockpit.py'],
                     cwd=w,stdout=f,stderr=subprocess.STDOUT)
print('exit='+str(r.returncode));print('\n'.join(log.read_text().splitlines()[-22:]))
