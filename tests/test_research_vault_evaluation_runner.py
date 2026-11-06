"""Synthetic adapter/scorer boundary tests; no heldout inputs or live queries."""
import copy
import hashlib
import json

import pytest

try:
    from engine.research_vault.evaluation_runner import evaluate_full_document
except ModuleNotFoundError:
    evaluate_full_document = None

PIN = 'c' * 64
PARAMS = {'limit': 5, 'max_passages': 3, 'timeout_s': 0.25}
BODY = 'Private synthetic café signal.'
SHA = hashlib.sha256(BODY.encode()).hexdigest()
IDENTITY = ('synthetic-report', 'a' * 64, SHA)
SOURCE = {'report_id': IDENTITY[0], 'source_pdf_sha256': IDENTITY[1],
          'extracted_text_sha256': IDENTITY[2], 'family_id': 'synthetic-family',
          'lineage_id': 'synthetic-lineage', 'grouping_qualified': True}
SPAN = {k: SOURCE[k] for k in ('report_id', 'source_pdf_sha256', 'extracted_text_sha256')}
SPAN.update(start_byte=0, end_byte=len(BODY.encode()),
            passage_text_sha256=hashlib.sha256(BODY.encode()).hexdigest())


def case(case_id='PRIVATE_LABEL', query='Public question', *, negative=None, pending=False):
    return {'id': case_id, 'query': query,
            'stratum': 'no_text' if negative == 'UNAVAILABLE' else 'truly_absent' if negative else 'tail_only',
            'split': 'holdout', 'fill_state': 'PENDING_HOST_FILL' if pending else 'READY',
            'searched_scope': [copy.deepcopy(SOURCE)],
            'abstain_expected': bool(negative),
            'expected_evidence_state': negative,
            'expected_doc_ids': [] if negative or pending else [IDENTITY[0]],
            'gold_spans': [] if negative or pending else [copy.deepcopy(SPAN)]}


def benchmark(cases=None):
    return {'schema': 'research_vault.full_document_benchmark.v1',
            'protocol_sha256': 'b' * 64, 'candidate_frozen_sha256': PIN,
            'cases': cases if cases is not None else [case()]}


def response(state='FOUND', *, wrong_revision=False):
    if state in {'NOT_FOUND', 'UNAVAILABLE'}:
        return {'ranked_report_ids': [], 'abstained': True,
                'evidence': {'evidence_state': state, 'passages': []}}
    passage = dict(SPAN, text=BODY)
    if wrong_revision:
        passage['source_pdf_sha256'] = 'd' * 64
    return {'ranked_report_ids': [IDENTITY[0]], 'abstained': False,
            'evidence': {'evidence_state': state, 'passages': [passage]}}


def run(candidate, *, document=None, clock=None, **kwargs):
    assert evaluate_full_document is not None, 'evaluation runner implementation missing'
    ticks = iter(i / 40 for i in range(100))
    return evaluate_full_document(document or benchmark(), candidate,
                                  candidate_sha256=kwargs.pop('candidate_sha256', PIN),
                                  candidate_scope=kwargs.pop('candidate_scope', [IDENTITY]),
                                  source_texts=kwargs.pop('source_texts', {IDENTITY: BODY.encode()}),
                                  request_parameters=kwargs.pop('request_parameters', PARAMS),
                                  clock=clock or (lambda: next(ticks)), **kwargs)


def test_ready_failures_keep_full_denominator_and_pending_never_queries():
    kinds = ['success', 'timeout', 'error', 'unavailable', 'notfound', 'wrongrevision', 'empty']
    cases = [case('PRIVATE_' + kind, kind) for kind in kinds]
    cases += [case('PRIVATE_negative_unavailable', 'negative_unavailable', negative='UNAVAILABLE'),
              case('PRIVATE_negative_notfound', 'negative_notfound', negative='NOT_FOUND'),
              case('PRIVATE_pending', 'pending', pending=True)]
    calls = []

    def adapter(query, parameters):
        calls.append((query, dict(parameters)))
        if query == 'timeout':
            raise TimeoutError('SECRET_TIMEOUT_PAYLOAD')
        if query == 'error':
            raise RuntimeError('SECRET_EXCEPTION_PAYLOAD')
        if query == 'empty':
            return None
        if query in {'unavailable', 'negative_unavailable'}:
            return response('UNAVAILABLE')
        if query in {'notfound', 'negative_notfound'}:
            return response('NOT_FOUND')
        return response(wrong_revision=query == 'wrongrevision')

    report = run(adapter, document=benchmark(cases))
    assert report['ready_denominator'] == 9
    assert report['positive_denominator'] == 7
    assert report['negative_denominator'] == 2
    assert report['excluded_pending'] == 1
    assert report['case_accuracy'] == pytest.approx(1 / 3)
    assert report['literal_support_rate'] == pytest.approx(1 / 7)
    assert report['abstention_accuracy'] == 1
    assert [q for q, p in calls] == kinds + ['negative_unavailable', 'negative_notfound']
    assert all(p == PARAMS for q, p in calls)
    statuses = {x['id']: x['status'] for x in report['cases']}
    assert statuses['PRIVATE_timeout'] == 'TIMEOUT'
    assert statuses['PRIVATE_error'] == 'ERROR'
    assert statuses['PRIVATE_empty'] == 'NONANSWER'
    assert statuses['PRIVATE_wrongrevision'] == 'OK'
    wrong = next(x for x in report['cases'] if x['id'] == 'PRIVATE_wrongrevision')
    assert wrong['recall_at_k'] == 1
    assert wrong['exact_evidence_identity'] == 0
    assert wrong['literal_support'] == 0
    assert wrong['correct'] == 0
    assert all(x['latency_ms'] == pytest.approx(25) for x in report['cases'])
    assert 'SECRET_' not in json.dumps(report)


def test_candidate_receives_query_and_public_parameters_only():
    received = []

    def adapter(*args, **kwargs):
        received.append((args, kwargs))
        return response()

    report = run(adapter)
    assert report['case_accuracy'] == 1
    assert received == [(('Public question', PARAMS), {})]
    assert all(x not in repr(received) for x in ('PRIVATE_LABEL', 'gold_spans', IDENTITY[0], BODY))


@pytest.mark.parametrize('bad', ['e' * 64, '', 'C' * 64])
def test_wrong_candidate_pin_rejects_before_any_query(bad):
    calls = []
    with pytest.raises(ValueError):
        run(lambda *a: calls.append(a), candidate_sha256=bad)
    assert calls == []


@pytest.mark.parametrize('scope', [[], [('synthetic-report', 'd' * 64, SHA)], [IDENTITY, IDENTITY]])
def test_wrong_admitted_scope_rejects_before_any_query(scope):
    calls = []
    with pytest.raises(ValueError):
        run(lambda *a: calls.append(a), candidate_scope=scope)
    assert calls == []


def test_later_case_scope_mismatch_rejects_batch_before_first_query():
    second = case('PRIVATE_SECOND', 'Second public question')
    second['searched_scope'][0]['source_pdf_sha256'] = 'd' * 64
    second['gold_spans'][0]['source_pdf_sha256'] = 'd' * 64
    calls = []
    with pytest.raises(ValueError):
        run(lambda *a: calls.append(a), document=benchmark([case(), second]))
    assert calls == []


def test_gold_source_hash_failure_rejects_before_any_query():
    calls = []
    with pytest.raises(ValueError):
        run(lambda *a: calls.append(a), source_texts={IDENTITY: b'wrong private bytes'})
    assert calls == []


@pytest.mark.parametrize('parameters', [
    {'timeout_s': .25, 'gold_spans': []}, {'timeout_s': .25, 'report_id': 'SECRET_GOLD_ID'},
    {'timeout_s': True}, {'timeout_s': float('nan')}, {'timeout_s': float('inf')},
    {'timeout_s': 0}, {'timeout_s': -1}, {'limit': 5}, {'timeout_s': .25, 'limit': True},
])
def test_invalid_or_gold_request_parameters_reject_before_any_query(parameters):
    calls = []
    with pytest.raises(ValueError):
        run(lambda *a: calls.append(a), request_parameters=parameters)
    assert calls == []


@pytest.mark.parametrize('exception', [TimeoutError('SECRET'), RuntimeError('SECRET')])
def test_failed_call_cannot_earn_negative_abstention(exception):
    def adapter(q, p):
        raise exception
    report = run(adapter, document=benchmark([case(negative='UNAVAILABLE')]))
    assert report['ready_denominator'] == 1
    assert report['abstention_accuracy'] == 0
    assert report['case_accuracy'] == 0
    assert 'SECRET' not in json.dumps(report)


def test_candidate_latency_and_debug_extras_are_not_exported():
    def adapter(q, p):
        return dict(response(), latency_ms=-1000, debug='SECRET', source_texts={'secret': BODY},
                    model_tokens=7)
    report = run(adapter)
    assert report['cases'][0]['latency_ms'] == pytest.approx(25)
    assert report['cases'][0]['model_tokens'] == 7
    assert 'SECRET' not in json.dumps(report)
    assert BODY not in json.dumps(report)


def test_elapsed_after_return_is_measurement_not_claimed_deadline():
    ticks = iter([100.0, 105.0])
    report = run(lambda q, p: response(), clock=lambda: next(ticks))
    assert report['cases'][0]['status'] == 'OK'
    assert report['cases'][0]['latency_ms'] == 5000
    assert report['case_accuracy'] == 1
    assert report['execution']['timeout_owner'] == 'external_candidate_adapter_transport'


def test_response_parameter_mutation_does_not_change_later_requests_or_gold():
    document = benchmark([case(), case('PRIVATE_SECOND', 'Second question')])
    retained = copy.deepcopy(document)
    received = []
    def adapter(q, p):
        received.append(dict(p))
        p.clear()
        return response()
    report = run(adapter, document=document)
    assert received == [PARAMS, PARAMS]
    assert document == retained
    assert PARAMS == {'limit': 5, 'max_passages': 3, 'timeout_s': .25}
    assert report['case_accuracy'] == 1


@pytest.mark.parametrize('result', [False, 'SECRET', {'status': 'SECRET'},
                                  {'ranked_report_ids': 'bad', 'evidence': {}},
                                  dict(response(), status='TIMEOUT', error='SECRET')])
def test_malformed_or_transport_failure_response_is_sanitized(result):
    report = run(lambda q, p: result)
    assert report['ready_denominator'] == 1
    assert report['case_accuracy'] == 0
    assert report['cases'][0]['status'] in {'NONANSWER', 'TIMEOUT'}
    assert 'SECRET' not in json.dumps(report)


def test_huge_timeout_is_rejected_as_invalid_quantity_before_any_query():
    calls = []
    with pytest.raises(ValueError):
        run(lambda *a: calls.append(a), request_parameters={'timeout_s': 10 ** 1000})
    assert calls == []


def test_invalid_utf8_source_is_rejected_before_any_query():
    calls = []
    with pytest.raises(ValueError):
        run(lambda *a: calls.append(a), source_texts={IDENTITY: b'\xff'})
    assert calls == []


def test_found_empty_result_is_a_nonanswer_in_ready_denominator():
    report = run(lambda q, p: {'ranked_report_ids': [], 'abstained': False,
                             'evidence': {'evidence_state': 'FOUND', 'passages': []}})
    assert report['ready_denominator'] == 1
    assert report['cases'][0]['status'] == 'NONANSWER'
    assert report['case_accuracy'] == 0


@pytest.mark.parametrize('wanted,returned', [('UNAVAILABLE', 'NOT_FOUND'), ('NOT_FOUND', 'UNAVAILABLE')])
def test_swapped_successful_negative_state_does_not_earn_abstention(wanted, returned):
    report = run(lambda q, p: response(returned), document=benchmark([case(negative=wanted)]))
    assert report['ready_denominator'] == 1
    assert report['cases'][0]['status'] == 'OK'
    assert report['case_accuracy'] == 0
    assert report['abstention_accuracy'] == 0


@pytest.mark.parametrize('kind', ['function', 'callable_object'])
def test_known_async_adapter_is_rejected_before_queries_without_warning(kind):
    import gc
    import warnings
    executed = []
    async def function(query, parameters):
        executed.append(query)
        return response()
    class Adapter:
        async def __call__(self, query, parameters):
            executed.append(query)
            return response()
    adapter = function if kind == 'function' else Adapter()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always', RuntimeWarning)
        with pytest.raises(ValueError):
            run(adapter)
        gc.collect()
    assert executed == []
    assert not [x for x in captured if issubclass(x.category, RuntimeWarning)]


def test_sync_adapter_returned_coroutines_are_closed_unexecuted_and_measured():
    import gc
    import warnings
    executed, created, called = [], [], []
    async def body():
        executed.append('EXECUTED')
        return response()
    def adapter(query, parameters):
        called.append(query)
        coroutine = body()
        created.append(coroutine)
        return coroutine
    document = benchmark([case(), case('PRIVATE_SECOND', 'Second question')])
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always', RuntimeWarning)
        report = run(adapter, document=document)
        assert all(c.cr_frame is None for c in created)
        created.clear()
        gc.collect()
    assert called == ['Public question', 'Second question']
    assert executed == []
    assert report['ready_denominator'] == 2
    assert report['case_accuracy'] == 0
    assert all(x['status'] == 'NONANSWER' and x['latency_ms'] == pytest.approx(25)
               for x in report['cases'])
    assert not [x for x in captured if issubclass(x.category, RuntimeWarning)]


def test_other_awaitable_is_never_awaited_and_remains_a_measured_nonanswer():
    executed = []
    class Awaitable:
        def __await__(self):
            executed.append('AWAITED')
            yield
            return response()
    report = run(lambda q, p: Awaitable())
    assert executed == []
    assert report['ready_denominator'] == 1
    assert report['cases'][0]['status'] == 'NONANSWER'
    assert report['cases'][0]['latency_ms'] == pytest.approx(25)
