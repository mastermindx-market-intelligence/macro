"""Make the review-only reader amendment against one exact complete input.

No file is edited in place. Source/current-catalog/access checks wrap the existing
final-debit step; the gateway and runtime schema are deliberately not registered.
"""
from __future__ import annotations
import ast,hashlib
EXPECTED='376d1045e6187926bea2fd4c83385d140174b817'
HELPER='''def _source_guard_error(guard, *, phase, report_id, query, catalog_item, document=None):
    """Internal request-local source check, not a model argument or new permission owner."""
    if guard is None:
        return None
    try:
        decision = guard(phase=phase, report_id=report_id, query=query,
                         catalog_item=catalog_item, document=document)
    except Exception:
        decision = "source_unavailable"
    if decision is True:
        return None
    allowed_errors = {"selection_invalid", "selection_stale", "source_access_denied",
                      "source_mismatch", "source_unavailable"}
    code = decision if isinstance(decision, str) and decision in allowed_errors else "source_unavailable"
    return _report_error(code, "The selected source could not be verified for this request. No source text is returned.", report_id=report_id)


'''

def amended(raw:bytes)->bytes:
    actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if actual!=EXPECTED:raise ValueError('Unexpected pending Brain source; review required')
    text=raw.decode();lines=text.splitlines(keepends=True);tree=ast.parse(text)
    targets={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    def section(name):
        n=targets[name];return ''.join(lines[n.lineno-1:n.end_lineno])
    def one(text,old,new):
        if text.count(old)!=1:raise ValueError('Ambiguous/missing patch anchor: '+old[:80])
        return text.replace(old,new,1)
    report=section('_research_report');before=report
    report=one(report,'now: datetime) -> dict:','now: datetime, _source_guard=None) -> dict:')
    report=one(report,'    preflight = _peek_report_view(uid, now)',
'''    if _source_guard is not None and not evidence_requested:
        return _report_error("source_request_invalid", "A selected source requires a specific evidence question.", report_id=rid)
    preflight = _peek_report_view(uid, now)''')
    report=one(report,'    document = (',
'''    gate_error = _source_guard_error(_source_guard, phase="admission", report_id=rid,
                                    query=evidence_query, catalog_item=item)
    if gate_error is not None:
        return gate_error
    document = (''')
    report=one(report,'    # Independent re-check (defense in depth alongside the corpus owner\'s own',
'''    gate_error = _source_guard_error(_source_guard, phase="source", report_id=rid,
                                    query=evidence_query, catalog_item=item, document=document)
    if gate_error is not None:
        return gate_error
    # Independent re-check (defense in depth alongside the corpus owner's own''')
    report=one(report,'        if pending_evidence_charge:\n            allowed, info = _charge_report_view(uid, now)',
'''        if pending_evidence_charge:
            gate_error = _source_guard_error(_source_guard, phase="before_debit", report_id=rid,
                                            query=evidence_query, catalog_item=item, document=document)
            if gate_error is not None:
                return gate_error
            allowed, info = _charge_report_view(uid, now)''')
    report=one(report,'            projected["access"] = {"decision": "allowed", "metered": True}',
'''            projected["access"] = {"decision": "allowed", "metered": True}
            gate_error = _source_guard_error(_source_guard, phase="after_debit", report_id=rid,
                                            query=evidence_query, catalog_item=item, document=document)
            if gate_error is not None:
                return _report_error("access_changed_after_accounting",
                                     "The source decision changed after the allowance call. No text is served; no refund or persisted debit is inferred.",
                                     report_id=rid, quota=response["quota"])''')
    text=one(text,before,HELPER+report)
    search=section('search_research');before=search
    search=one(search,'    now: datetime | None = None,','    now: datetime | None = None,\n    _source_guard=None,')
    search=one(search,'    # --- report mode (W4 + R1B evidence) ----------------------------------- #',
'''    if _source_guard is not None and not _is_report_mode(mode):
        return _report_error("source_request_invalid", "Selected-source checks belong to report mode only.")
    # --- report mode (W4 + R1B evidence) ----------------------------------- #''')
    search=one(search,'                                    now=reference)','                                    now=reference, _source_guard=_source_guard)')
    text=one(text,before,search)
    compile(text,'brain_guarded_review.py','exec')
    return text.encode()
