"""Protected dispatch wiring: candidate code cannot authenticate its own proof."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow():
    return yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())


def test_admitted_pr_inputs_are_bounded_and_do_not_replace_main_baseline():
    doc=workflow();inputs=doc.get('on',doc.get(True))['workflow_dispatch']['inputs']
    assert set(inputs)=={'expected_sha','proof_role','admission_generation','admission_artifact_id',
        'admission_payload_sha256','pr_number','subject_head_sha','tested_base_sha','tested_merge_sha',
        'expected_workflow_definition_sha'}
    assert all(i['type']=='string' and i['required'] is False for i in inputs.values())
    assert 'inputs.admission_generation' in doc['concurrency']['group']
    assert 'github.run_id' in doc['concurrency']['group']


def test_readonly_protected_resolver_precedes_every_candidate_job():
    jobs=workflow()['jobs'];gate=jobs['ci-admission']
    assert gate['runs-on']=='ubuntu-latest' and gate['timeout-minutes']<=5
    assert gate['permissions']=={'contents':'read','actions':'read','pull-requests':'read'}
    checkout=next(s for s in gate['steps'] if 'checkout@' in s.get('uses',''))
    assert checkout['with']['ref']=='${{ github.workflow_sha }}'
    assert checkout['with']['persist-credentials'] is False
    resolver=next(s for s in gate['steps'] if s.get('id')=='resolve')
    assert 'python3 -I scripts/resolve_ci_pr_admission.py' in resolver['run']
    assert resolver['env']['GITHUB_WORKFLOW_SHA']=='${{ github.workflow_sha }}'
    assert resolver['env']['CI_PR_ADMISSION_INPUTS']=='${{ toJSON(inputs) }}'
    assert 'secrets.ADMIN' not in str(gate)
    assert jobs['ci-plan']['needs']==['ci-admission']
    assert "needs.ci-admission.result == 'success'" in jobs['ci-plan']['if']
    assert 'inputs.tested_merge_sha' not in str(jobs['ci-plan']['steps'])


def test_exact_resolved_identity_reaches_execution_and_contract_gate():
    jobs=workflow()['jobs'];plan=jobs['ci-plan']
    checkout=next(s for s in plan['steps'] if s.get('name')=='check out the exact candidate')
    assert 'needs.ci-admission.outputs.tested_commit' in checkout['with']['ref']
    identity=next(s for s in plan['steps'] if s.get('id')=='identity')
    assert identity['env']['ADMISSION_GENERATION']=='${{ needs.ci-admission.outputs.admission_generation }}'
    assert 'ADMITTED_BASE' in identity['run'] and 'ADMITTED_HEAD' in identity['run']
    assert 'admission_generation' in plan['outputs']
    pack=jobs['ci-pack'];contract=jobs['contract-delta']
    pack_checkout=next(s for s in pack['steps'] if s.get('name')=='check out the exact candidate')
    assert pack_checkout['with']['ref']=='${{ needs.ci-plan.outputs.tested_tree_sha }}'
    assert contract['needs']==['ci-plan']
    assert "needs.ci-plan.outputs.semantic_role == 'pr_head'" in contract['if']
    contract_checkout=next(s for s in contract['steps'] if s.get('name')=='check out the exact candidate')
    assert contract_checkout['with']['ref']=='${{ needs.ci-plan.outputs.tested_tree_sha }}'
    contract_gate=next(s for s in jobs['ci-gate']['steps'] if s.get('name')=='enforce contract-delta verdict')
    assert "PR_PROOF" in contract_gate['env']
    assert '!= "success"' in contract_gate['run']


def test_planner_and_pack_use_protected_bundle_for_admitted_mode():
    jobs=workflow()['jobs']
    for key in ('ci-plan','ci-pack'):
        steps=jobs[key]['steps']
        bundle=next(s for s in steps if s.get('name')=='retain protected proof control bundle')
        assert 'ci-proof-control' in bundle['run']
        assert '-I ' in str(steps)
    run=next(s for s in jobs['ci-plan']['steps'] if s.get('name')=='plan the CI packs once')
    assert '--admission-generation' in run['env']['CI_ADMISSION_ARG']
    assert 'CONTROL_ROOT' in run['run']
    pack=next(s for s in jobs['ci-pack']['steps'] if s.get('name')=='validate and run legacy CI pack')
    assert '--expect-admission-generation' in pack['run']
    assert 'CONTROL_ROOT' in pack['run']


def test_incumbent_controller_serializes_receipt_upload_before_each_effect():
    doc=yaml.safe_load((ROOT/'.github/workflows/merge-on-green.yml').read_text())
    assert doc['permissions']['checks']=='write'
    text=(ROOT/'.github/workflows/merge-on-green.yml').read_text()
    assert "github.event.workflow_run.name == 'ci'" in text
    jobs=doc['jobs'];sweep=jobs['sweep'];steps=sweep['steps']
    commands=[(i,s) for i,s in enumerate(steps) if 'ci_admission_stages.py' in s.get('run','')]
    assert len(commands)==5
    previous=-1
    for action in ['complete','prepare','reserve','dispatch','finalize']:
        entries=[(i,s) for i,s in commands if ' '+action in s['run']]
        assert len(entries)==1
        assert entries[0][0]>previous;previous=entries[0][0]
    for i,step in enumerate(steps):
        if 'upload-artifact@' in step.get('uses',''):
            assert step['with'].get('overwrite',False) is False
            assert step['with']['if-no-files-found']=='error'
    checkout=next(s for s in steps if 'checkout@' in s.get('uses',''))
    assert checkout['with']['ref']=='${{ github.workflow_sha }}'
    assert checkout['with']['persist-credentials'] is False
    assert '.github/ci/legacy-jobs.yml' in checkout['with']['sparse-checkout']
