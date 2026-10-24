"""Local bare-Git publication through the existing factory/gate; no host admission."""
from hashlib import sha256
from pathlib import Path
import subprocess

import pytest

from tests.test_qledger_runner_bootstrap import bootstrap, put  # noqa: F401
from tests.test_qledger_conversion_candidate import fixture, conversion_invocation  # noqa: F401

SOURCE=Path(__file__).resolve().parents[1]


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE).strip()


@pytest.fixture
def publication(bootstrap):
    run,config,owner,repo=bootstrap
    remote=owner.parent/'published.git'
    subprocess.run(['git','init','--bare','--quiet',str(remote)],check=True,capture_output=True)
    git(repo,'remote','add','origin',str(remote))
    # This is the original identity captured before this fresh fixture push,
    # using the same convention as the incumbent normal-push observation.
    origin=sha256(git(repo,'remote','get-url','--push','origin')).hexdigest()
    name='scripts/ci/qledger_owner_evidence.py'
    config['bundle_files'][name]=put(owner/'bundle'/name,(SOURCE/name).read_bytes())
    entry=owner/'bundle/owner_entry.py'
    prefix=entry.read_bytes()
    driver=owner.parent/'driver.py'
    original_driver=driver.read_text()
    def configure(*, publish=False, mode='readback', tamper='', origin_pin=origin):
        extension=f'''
from scripts.ci.qledger_owner_evidence import build_evidence as production_evidence
class PublicationFixtureEvidence(FixtureEvidence):
    # All other evidence here is exclusively the accepted offline fixture.
    def __init__(self, context):
        super().__init__(context)
        self.real = production_evidence(context, origin_binding_sha256={origin_pin!r})
    def assert_publication_readback(self, **context):
        {tamper or 'pass'}
        return self.real.assert_publication_readback(**context)
'''
        if mode=='resources':
            extension+='''
    def assert_resources(self, **context):
        return self.real.assert_resources(**context)
'''
        extension+='''
def build_evidence(context):
    return PublicationFixtureEvidence(context)
'''
        if mode=='production':
            extension+=f'''
def build_evidence(context):
    return production_evidence(context, origin_binding_sha256={origin_pin!r})
'''
        config['bundle_files']['owner_entry.py']=put(entry,prefix+extension.encode())
        text=original_driver
        if publish:
            # Normal Git push is performed inside the fixture's already-held
            # install barrier, after preflight/checkout and before confirm. No
            # production shell budget is minted or claimed by these tests.
            helper='''
def fixture_checkout_and_publish(oid):
    subprocess.check_call(['git','-C',str(repo),'checkout','--quiet','--detach',oid])
    subprocess.check_call(['git','-C',str(repo),'push','--quiet','origin',oid+':refs/heads/main'])
'''
            text=text.replace('operational=False',helper+'\noperational=False')
            text=text.replace("lambda oid: subprocess.check_call(\n                ['git','-C',str(repo),'checkout','--quiet','--detach',oid])",'fixture_checkout_and_publish')
        # Mark install refusals as operational: every one must retain HOLD.
        text=text.replace('            loaded.gate.initial_checkout(', '            operational=True\n            loaded.gate.initial_checkout(')
        driver.write_text(text)
    return run,config,owner,repo,remote,configure


def test_normal_publication_readback_releases_only_test_owned_installation(publication):
    run,config,owner,repo,remote,configure=publication
    configure(publish=True)
    assert 'OFFLINE_FIXTURE_SUCCESS' in run('reader')
    assert git(remote,'rev-parse','refs/heads/main').decode()==config['gate']['candidate_oid']
    assert (owner/'qledger-installed.json').is_file()
    assert not (owner/'qledger-install.hold').exists()


def test_local_candidate_and_tracking_ref_do_not_prove_remote_publication(publication):
    run,config,owner,repo,_,configure=publication
    configure()
    # Local objects already contain the complete candidate. An invented local
    # tracking ref cannot make the actual remote contain it.
    git(repo,'update-ref','refs/remotes/fake/main',config['gate']['candidate_oid'])
    run('reader','normal publication ref readback is unavailable')
    assert not (owner/'qledger-installed.json').exists()


def test_wrong_remote_generation_stays_held_without_fetch_or_replay(publication):
    run,config,owner,repo,_,configure=publication
    old=config['gate']['accepted_tip_oid']
    git(repo,'push','--quiet','origin',old+':refs/heads/main')
    configure()
    run('reader','exact full candidate is not confirmed')
    assert (owner/'qledger-install.hold').is_file()


def test_changed_original_origin_is_not_recaptured(publication):
    run,_,_,repo,_,configure=publication
    configure()
    git(repo,'remote','set-url','origin',str(repo.parent/'different-origin.git'))
    run('reader','original normal-push origin changed')


@pytest.mark.parametrize('tamper', [
    "context['bootstrap_pid'] += 1",
    "context['conversion_manifest_digest'] = '0'*64",
    "context['budget_id'] = 'different-original-budget'",
    "context['gate'].tree_oid = '0'*40",
])
def test_readback_binds_original_process_result_budget_and_complete_tree(publication,tamper):
    run,_,_,_,_,configure=publication
    configure(publish=True,tamper=tamper)
    expected='complete publication tree differs' if 'tree_oid' in tamper else 'original publication invocation binding differs'
    run('reader',expected)


def test_no_original_origin_pin_is_an_explicit_refusal(publication):
    run,_,_,_,_,configure=publication
    configure(origin_pin=None)
    run('reader','original normal-push origin binding required')


def test_actual_resource_contract_cannot_be_replaced_by_manifest_labels(publication):
    run,_,_,_,_,configure=publication
    configure(mode='resources')
    run('reader','original ordinary push budget/process anchor and actual root retention/capacity policy unavailable')


def test_partial_production_factory_never_issues_runtime_admission(publication):
    run,_,owner,_,_,configure=publication
    configure(publish=True,mode='production')
    run('reader','held complete new-entry/launcher exclusion authority unavailable')
    assert not (owner/'qledger-installed.json').exists()


@pytest.mark.parametrize('tamper', [
    "self.real._pid += 1",
    "self.real.context = __import__('dataclasses').replace(self.real.context, original_deadline_monotonic_ns=1)",
])
def test_readback_does_not_reanchor_expired_or_different_process_inputs(publication,tamper):
    run,_,_,_,_,configure=publication
    configure(publish=True,tamper=tamper)
    run('reader','readback process changed or original endpoint is unavailable/expired')


@pytest.mark.parametrize('redirect', ['origin', 'insteadOf'])
def test_remote_query_cannot_follow_mutable_origin_aba(publication, redirect):
    run,config,owner,repo,remote,configure=publication
    alternate=owner.parent/'alternate.git'
    subprocess.run(['git','init','--bare','--quiet',str(alternate)],check=True,capture_output=True)
    git(repo,'push','--quiet',str(alternate),config['gate']['candidate_oid']+':refs/heads/main')
    # Interleave exactly at the actual Git read: original has no candidate,
    # alternate does. Restore configuration before the final identity check.
    change = (['remote','set-url','origin',str(alternate)] if redirect=='origin' else
              ['config','url.'+str(alternate)+'.insteadOf',str(remote)])
    restore = (['remote','set-url','origin',str(remote)] if redirect=='origin' else
               ['config','--unset-all','url.'+str(alternate)+'.insteadOf'])
    lines=[
        'read_git = self.real._git',
        'def interleave(args, *extra, **kwargs):',
        "    if args[0] != 'ls-remote': return read_git(args, *extra, **kwargs)",
        "    command = ['git', '-C', str(self.real.context.repo)]",
        f"    __import__('subprocess').check_call(command + {change!r})",
        '    try:',
        '        return read_git(args, *extra, **kwargs)',
        '    finally:',
        f"        __import__('subprocess').check_call(command + {restore!r})",
        'self.real._git = interleave',
    ]
    configure(tamper='\n        '.join(lines))
    run('reader','normal publication ref readback is unavailable')
    assert not (owner/'qledger-installed.json').exists()
    assert (owner/'qledger-install.hold').is_file()
    assert git(repo,'remote','get-url','origin')==str(remote).encode()
    assert git(alternate,'rev-parse','refs/heads/main').decode()==config['gate']['candidate_oid']
    assert git(remote,'for-each-ref','--format=%(objectname)','refs/heads/main')==b''
