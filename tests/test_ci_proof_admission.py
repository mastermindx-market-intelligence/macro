"""Shared authored/refresh admission: actual workload and oldest eligible demand."""
from dataclasses import replace

import pytest

from scripts import ci_proof_admission as admission


def run(i, status='in_progress', role='pr_head', attempt=1):
    return admission.Run(i, attempt, status, role)


def record(generation='a'*12, run_id=None, **kwargs):
    return admission.Admission(generation, 123, '1'*40, '2'*40, '3'*40, '4'*40,
                               run_id=run_id, **kwargs)


def free(runs=(), records=(), **kwargs):
    return admission.capacity(list(runs), list(records), census_complete=True,
                              records_complete=True, **kwargs)


def demand(number, when, purpose='authored', generation=None):
    return admission.Demand(number, '1'*40, purpose, when,
                            generation or f'{number:012x}')


def test_hard_cap_counts_legacy_and_new_work_without_cancel():
    assert free([run(i) for i in range(1, 8)]) == 1
    assert free([run(i) for i in range(1, 9)]) == 0
    assert free([run(i) for i in range(1, 14)]) == 0
    assert free([run(i) for i in range(1, 8)], [record()]) == 0
    assert free([run(i) for i in range(1, 8)], legacy_reservations=1) == 0


@pytest.mark.parametrize('status', ['queued', 'pending', 'requested', 'waiting', 'in_progress'])
def test_every_active_status_consumes_capacity(status):
    assert free([run(1, status)]) == 7


def test_indexed_binding_deduplicates_but_missing_index_keeps_reservation():
    assert free([run(42)], [record(run_id=42)]) == 7
    assert free([], [record(run_id=42)]) == 7
    assert free([run(42, 'completed')], [record(run_id=42)]) == 7
    assert free([run(42, 'completed')], [record(run_id=42, settled=True)]) == 8


def test_unindexed_unknown_dispatch_does_not_expire_or_free_on_pr_close():
    # No timestamp, PR-state or current-head field can delete admitted workload.
    r = record()
    assert free([], [r]) == 7
    assert free([], [replace(r, head_sha='5'*40)]) == 7


def test_observed_active_work_wins_over_settled_record():
    assert free([run(42)], [record(run_id=42, settled=True)]) == 7


def test_status_page_transition_is_union_not_double_count_or_last_wins():
    assert free([run(42, 'queued'), run(42, 'in_progress')]) == 7
    assert free([run(42, 'in_progress'), run(42, 'completed')]) == 7
    assert free([run(42, 'completed'), run(42, 'in_progress')]) == 7


@pytest.mark.parametrize('runs,records', [
    ([run(1, role='unknown')], []),
    ([run(1, role='unrecognized')], []),
    ([run(1, status='unrecognized')], []),
    ([run(42, attempt=2)], [record(run_id=42)]),
    ([run(42, role='main')], [record(run_id=42)]),
    ([run(1), run(1, role='main')], []),
    ([], [record(), replace(record(), head_sha='5'*40)]),
    ([], [record(run_id=42), record(generation='b'*12, run_id=42)]),
    ([], [record(settled=True)]),
])
def test_ambiguous_identity_never_authorizes(runs, records):
    assert free(runs, records) == 0


def test_affirmatively_main_baseline_is_not_pr_capacity():
    assert free([run(1, role='main')]) == 8


@pytest.mark.parametrize('flag', ['census_complete', 'records_complete'])
def test_incomplete_evidence_closes_admission(flag):
    args = dict(census_complete=True, records_complete=True)
    args[flag] = False
    assert admission.capacity([], [], **args) == 0


@pytest.mark.parametrize('bad', [-1, True, 1.5, '1'])
def test_malformed_legacy_count_fails_closed(bad):
    assert free(legacy_reservations=bad) == 0


def test_later_authored_arrivals_cannot_pass_older_refresh():
    oldest = demand(10640, '2026-11-03T00:00:00Z', 'refresh')
    pending = [oldest]
    for tick in range(1, 100):
        pending.append(demand(11000 + tick, f'2026-11-03T00:{tick//60:02}:{tick%60:02}Z'))
        assert admission.ordered_demands(pending)[0] == oldest
    # Work can begin only when a real slot becomes free, regardless of rank.
    assert free([run(i) for i in range(1, 9)]) == 0
    assert free([run(i) for i in range(1, 8)]) == 1


def test_timestamp_order_uses_absolute_time_and_has_no_purpose_priority():
    earlier = demand(1, '2026-11-03T01:00:00+02:00')
    later = demand(2, '2026-11-03T00:00:00Z', 'refresh')
    assert admission.ordered_demands([later, earlier]) == [earlier, later]


def test_replacing_unserved_head_retains_age_and_demand_identity():
    old = demand(42, '2026-11-03T00:00:00Z', 'refresh')
    new = admission.replace_pending_head(old, 'f'*40)
    assert new == replace(old, head_sha='f'*40)
    assert old.head_sha == '1'*40


@pytest.mark.parametrize('change', [dict(pr_number=True), dict(head_sha='x'*40),
    dict(purpose='priority'), dict(requested_at='2026-11-03T00:00:00'),
    dict(demand_id='bad')])
def test_invalid_demand_rejected(change):
    with pytest.raises(ValueError):
        admission.ordered_demands([replace(demand(1, '2026-11-03T00:00:00Z'), **change)])


def test_conflicting_duplicate_pr_demand_is_not_silently_ranked():
    d = demand(1, '2026-11-03T00:00:00Z')
    with pytest.raises(ValueError):
        admission.ordered_demands([d, replace(d, head_sha='f'*40)])


def test_binding_run_is_one_way_and_attempt_exact():
    pending = record()
    bound = admission.bind_run(pending, 42, 1)
    assert bound.run_id == 42 and bound.run_attempt == 1
    assert admission.bind_run(bound, 42, 1) == bound
    with pytest.raises(ValueError):
        admission.bind_run(bound, 43, 1)
    with pytest.raises(ValueError):
        admission.bind_run(bound, 42, 2)


def test_terminal_settlement_requires_original_bound_run_and_attempt():
    bound = record(run_id=42)
    for r in [run(42), run(43, 'completed'), run(42, 'completed', attempt=2),
              run(42, 'completed', role='main')]:
        with pytest.raises(ValueError):
            admission.settle_run(bound, r)
    assert admission.settle_run(bound, run(42, 'completed')).settled is True
    with pytest.raises(ValueError):
        admission.settle_run(record(), run(42, 'completed'))


def test_exact_tested_merge_and_workflow_required_before_execution():
    a = record()
    admission.validate_execution(a, subject_head='1'*40, base='2'*40,
                                 merge='3'*40, parents=['2'*40, '1'*40], workflow='4'*40)
    for field, value in [('subject_head','5'*40), ('base','5'*40), ('merge','5'*40),
                         ('parents',['1'*40,'2'*40]), ('parents',['2'*40]),
                         ('workflow','5'*40)]:
        args = dict(subject_head='1'*40,base='2'*40,merge='3'*40,
                    parents=['2'*40,'1'*40],workflow='4'*40)
        args[field] = value
        with pytest.raises(ValueError):
            admission.validate_execution(a, **args)


def anchor_fixture():
    import hashlib
    import json
    import io
    import zipfile
    from dataclasses import asdict
    payload = json.dumps({'schema':'mastermind.ci-proof-admission.v1',
                          'repository_id':17, 'controller_run_id':70,
                          'controller_run_attempt':1,
                          'admission':asdict(record())}, sort_keys=True).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('ci-proof-admission.json', payload)
    archive = buffer.getvalue()
    return dict(
        archive=archive, payload_sha256=hashlib.sha256(payload).hexdigest(),
        repository_id=17, artifact_id=80,
        controller_run_id=70, controller_attempt=1, controller_sha='c'*40,
        artifact={'id':80, 'name':'ci-proof-admission-70-1-aaaaaaaaaaaa-prepared', 'expired':False,
                  'digest':'sha256:'+hashlib.sha256(archive).hexdigest(),
                  'workflow_run':{'id':70,'repository_id':17,'head_sha':'c'*40}},
        controller={'id':70,'run_attempt':1,'repository':{'id':17},
                    'path':'.github/workflows/merge-on-green.yml',
                    'head_branch':'main','head_sha':'c'*40, 'event':'schedule'},
    )


def test_admission_receipt_binds_controller_not_comment_bot_identity():
    args = anchor_fixture()
    assert admission.authenticate_receipt(**args) == record()


@pytest.mark.parametrize('target,field,value', [
    ('artifact','id',81), ('artifact','expired',True),
    ('artifact','digest','sha256:'+'d'*64), ('artifact','name','other'),
    ('artifact','workflow_run',{'id':71,'repository_id':17,'head_sha':'c'*40}),
    ('controller','id',71), ('controller','run_attempt',2),
    ('controller','repository',{'id':18}), ('controller','head_sha','d'*40),
    ('controller','head_branch','candidate'), ('controller','event','pull_request'),
    ('controller','path','.github/workflows/ci.yml'),
])
def test_forged_or_wrong_controller_provenance_fails_closed(target, field, value):
    args = anchor_fixture()
    args[target][field] = value
    with pytest.raises(ValueError):
        admission.authenticate_receipt(**args)


def test_comment_payload_hash_does_not_substitute_for_actual_artifact_bytes():
    args = anchor_fixture()
    args['archive'] = args['archive'].replace(b'"pr_number": 123', b'"pr_number": 124')
    with pytest.raises(ValueError):
        admission.authenticate_receipt(**args)


def test_receipt_duplicate_keys_and_extra_fields_are_not_accepted():
    import hashlib
    for raw in [b'{"schema":"x","schema":"y"}', b'{"forged":true}']:
        args = anchor_fixture()
        import io, zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            z.writestr('ci-proof-admission.json', raw)
        args['archive'] = buffer.getvalue()
        args['artifact']['digest'] = 'sha256:'+hashlib.sha256(args['archive']).hexdigest()
        args['payload_sha256'] = hashlib.sha256(raw).hexdigest()
        with pytest.raises(ValueError):
            admission.authenticate_receipt(**args)


@pytest.mark.parametrize('bad', [True, 1.0])
def test_terminal_settlement_rejects_coerced_run_identity(bad):
    a = record(run_id=1)
    for observed in [run(bad, 'completed'), run(1, 'completed', attempt=bad)]:
        with pytest.raises(ValueError):
            admission.settle_run(a, observed)


def test_immutable_receipt_chain_only_advances_same_original_binding():
    pending=record()
    bound=admission.bind_run(pending,42,1)
    settled=admission.settle_run(bound,run(42,'completed'))
    assert admission.merge_records([pending,bound,settled,pending]) == [settled]
    for conflicting in [record(run_id=43),replace(bound,head_sha='f'*40)]:
        with pytest.raises(ValueError):
            admission.merge_records([pending,bound,conflicting])


def test_existing_reservation_can_dispatch_only_with_its_own_real_slot():
    a=record()
    assert admission.reserved_dispatch_allowed([run(i) for i in range(1,8)],[a],a,
                                               census_complete=True,records_complete=True)
    assert not admission.reserved_dispatch_allowed([run(i) for i in range(1,9)],[a],a,
                                                   census_complete=True,records_complete=True)
    assert not admission.reserved_dispatch_allowed([],[],a,census_complete=True,records_complete=True)
    assert not admission.reserved_dispatch_allowed([], [replace(a,run_id=42)],a,
                                                   census_complete=True,records_complete=True)


def test_pending_demand_age_survives_source_updates_but_not_consumed_cycle():
    d=demand(7,'2026-11-03T00:00:00Z','refresh',generation='a'*12)
    assert admission.pending_demand_for_pr([d,replace(d,head_sha='b'*40)],[],7,'c'*40)==replace(d,head_sha='c'*40)
    assert admission.pending_demand_for_pr([d],[replace(record(generation='a'*12,run_id=42),pr_number=7)],7,'c'*40) is None
    with pytest.raises(ValueError):
        admission.pending_demand_for_pr([d,replace(d,requested_at='2026-11-03T00:01:00Z')],[],7,'c'*40)
    with pytest.raises(ValueError):
        admission.pending_demand_for_pr([d,replace(d,demand_id='b'*12)],[],7,'c'*40)


def test_authenticated_compaction_keeps_unknown_and_consumes_only_terminal_original():
    unknown=record()
    bound=record(generation='b'*12,run_id=42)
    served=demand(123,'2026-11-03T00:00:00Z',generation='b'*12)
    pending=demand(123,'2026-11-03T00:01:00Z',generation='c'*12)
    checkpoint=admission.compact_pr_records(123,900,[unknown,bound],[served,pending],
                                           [run(42,'completed')],records_complete=True)
    assert checkpoint.covered_through_comment_id==900
    assert checkpoint.admissions==(unknown,)
    assert checkpoint.settled==(replace(bound,settled=True),)
    assert checkpoint.demands==(pending,)
    assert free([],checkpoint.admissions)==7


@pytest.mark.parametrize('terminal',[[],[run(42)],[run(43,'completed')],[run(42,'completed',attempt=2)]])
def test_compaction_cannot_erase_unknown_or_wrong_terminal_attempt(terminal):
    bound=record(run_id=42)
    checkpoint=admission.compact_pr_records(123,900,[bound],[],terminal,records_complete=True)
    assert checkpoint.admissions==(bound,)
    assert checkpoint.settled==()


def test_incomplete_or_cross_pr_compaction_refuses():
    with pytest.raises(ValueError):
        admission.compact_pr_records(123,900,[record()],[],[],records_complete=False)
    with pytest.raises(ValueError):
        admission.compact_pr_records(124,900,[record()],[],[],records_complete=True)
    with pytest.raises(ValueError):
        admission.compact_pr_records(123,True,[record()],[],[],records_complete=True)


def test_checkpoint_selection_uses_authenticated_coverage_and_cannot_hide_later_refs():
    c1=admission.compact_pr_records(123,900,[record()],[],[],records_complete=True)
    c2=admission.compact_pr_records(123,950,[record()],[],[],records_complete=True)
    # An old checkpoint appearing in a later comment cannot rewind coverage.
    chosen=admission.select_checkpoint([c2,c1],123)
    assert chosen==c2
    assert admission.references_after_checkpoint([(899,'old'),(930,'old2'),(951,'new')],chosen)==[(951,'new')]
    with pytest.raises(ValueError):
        admission.select_checkpoint([c2,replace(c2,admissions=())],123)
    with pytest.raises(ValueError):
        admission.references_after_checkpoint([(951,'new'),(951,'forged')],chosen)


def test_checkpoint_cannot_rewind_a_bound_original_or_discard_observed_active():
    a=record(run_id=42)
    old=admission.compact_pr_records(123,900,[a],[],[],records_complete=True)
    newer=replace(old,covered_through_comment_id=950,admissions=(record(),))
    with pytest.raises(ValueError):
        admission.select_checkpoint([old,newer],123)
    settled=replace(a,settled=True)
    observed=admission.compact_pr_records(123,950,[settled],[],[run(42)],records_complete=True)
    assert observed.admissions==(a,)
    assert observed.settled==()


def test_compaction_folds_chronological_pending_head_updates_without_changing_age():
    d=admission.Demand(7,'1'*40,'authored','2026-11-03T00:00:00Z','a'*12)
    new=replace(d,head_sha='2'*40)
    cp=admission.compact_pr_records(7,20,[],[d,new],[],records_complete=True)
    assert cp.demands==(new,)
    with pytest.raises(ValueError):
        admission.compact_pr_records(7,20,[],[d,replace(new,requested_at='2020-01-01T00:00:00Z')],[],records_complete=True)


@pytest.mark.parametrize('change',['drop','age','purpose','generation'])
def test_checkpoint_keeps_unserved_identity_until_actual_admission(change):
    d=admission.Demand(123,'1'*40,'authored','2026-11-03T00:00:00Z','a'*12)
    old=admission.Checkpoint(123,20,(),(d,),())
    replacement={'drop':None,'age':replace(d,requested_at='2020-01-01T00:00:00Z'),
        'purpose':replace(d,purpose='refresh'),'generation':replace(d,demand_id='b'*12)}[change]
    new=replace(old,covered_through_comment_id=30,demands=() if replacement is None else (replacement,))
    with pytest.raises(ValueError):admission.select_checkpoint([old,new],123)
    admitted=replace(record(generation=d.demand_id,run_id=None),head_sha=d.head_sha)
    served=replace(new,demands=(),admissions=(admitted,))
    assert admission.select_checkpoint([old,served],123)==served
