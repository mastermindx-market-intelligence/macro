"""Fresh ordinary Bash originals and targeted own-PID observations, offline only."""
from hashlib import sha256
import json
from pathlib import Path
import shlex
import subprocess

import pytest

from tests.test_qledger_runner_bootstrap import bootstrap, canonical, put  # noqa: F401
from tests.test_qledger_conversion_candidate import fixture, conversion_invocation  # noqa: F401

SOURCE=Path(__file__).resolve().parents[1]
LIB=SOURCE/'scripts/ci/push_retry.sh'


@pytest.fixture
def original(bootstrap):
    _,config,owner,repo=bootstrap
    name='scripts/ci/qledger_push_original.py'
    config['bundle_files'][name]=put(owner/'bundle'/name,(SOURCE/name).read_bytes())
    # Facts require no invented whole-operation endpoint. Native entries still
    # require their original endpoint through the unchanged operational path.
    config.pop('original_deadline_monotonic_ns')
    subprocess.run(['git','-C',str(repo),'remote','add','origin',str(owner.parent/'original.git')],check=True)
    cfg=owner/'bootstrap.json';digest=put(cfg,canonical(config))
    binding=[config['result_path'],config['manifest_digest'],config['gate']['accepted_tip_oid'],
             config['gate']['candidate_oid'],config['gate']['tree_oid']]
    setup=f'. {shlex.quote(str(LIB))}\n'
    setup+='push_bind_qledger_original_bootstrap '+ ' '.join(map(shlex.quote,[str(owner),str(cfg),digest]))+'\n'
    setup+='push_bind_qledger_conversion '+' '.join(map(shlex.quote,binding))+'\n'
    def run(body,*,setup_override=None):
        r=subprocess.run(['bash','-eo','pipefail','-c',(setup if setup_override is None else setup_override)+body],
            cwd=repo,capture_output=True,text=True,timeout=60)
        assert r.returncode==0,r.stderr+r.stdout
        return r.stdout
    return run,config,owner,repo,setup


def test_fresh_init_captures_real_origin_process_and_clock_without_admission(original):
    run,config,owner,repo,_=original
    out=run('push_retry_init "fresh"; echo "$PUSH_ATTEMPT $PUSH_MAX_ATTEMPTS $PUSH_BUDGET_SECS $PUSH_QLEDGER_ORIGINAL_DIGEST"\n')
    attempt,maximum,budget,digest=out.strip().split()
    assert (attempt,maximum,budget)==('0','10','420')
    raw=(owner/'original-push.json').read_bytes();doc=json.loads(raw)
    assert sha256(raw).hexdigest()==digest
    assert doc['process']['pid']>0 and doc['boot']
    assert doc['origin_binding_sha256']==sha256(str(owner.parent/'original.git').encode()).hexdigest()
    assert doc['original']['manifest_digest']==config['manifest_digest']
    assert doc['correlation']['retry_deadline_monotonic_lower_ns']<=doc['correlation']['retry_deadline_monotonic_upper_ns']
    assert doc['resource_assurance']=='PRIVATE_ROOT_CUSTODY_ONLY_POLICY_NOT_PROVIDED'
    assert doc['timing_assurance']=='RETRY_ADMISSION_CORRELATION_NOT_A_WHOLE_OPERATION_ENDPOINT'
    assert not (owner/'qledger-installed.json').exists()
    assert not (owner/'bundle/IMPORT_OCCURRED').exists(), 'facts must not construct a provider'
    assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip()==config['gate']['accepted_tip_oid']


def test_same_original_shell_can_restart_inspection_child_without_recapture(original):
    run,_,owner,_,_=original
    out=run('''push_retry_init fresh
before="$PUSH_QLEDGER_ORIGINAL_DIGEST"
_push_qledger_original inspect
push_attempt
_push_qledger_original inspect
[ "$before" = "$PUSH_QLEDGER_ORIGINAL_DIGEST" ]
echo "$PUSH_ATTEMPT $PUSH_QLEDGER_ORIGINAL_STATE"
''')
    assert out.strip()=='1 retry'
    assert json.loads((owner/'original-push.json').read_bytes())['initial_attempt']==0


def test_original_attempt_exhaustion_is_not_reset(original):
    run,_,_,_,_=original
    assert run('''PUSH_MAX_ATTEMPTS=2
push_retry_init fresh
n=0
while push_attempt; do n=$((n+1)); done
before="$PUSH_DEADLINE:$PUSH_ATTEMPT"
if push_retry_init replacement; then exit 90; fi
[ "$before" = "$PUSH_DEADLINE:$PUSH_ATTEMPT" ]
echo "$n:$PUSH_STOP"
''').strip().startswith('2:attempt budget exhausted')


def test_expired_retry_window_preserves_unconditional_first_attempt(original):
    run,_,_,_,_=original
    out=run('''PUSH_BUDGET_SECS=0
push_retry_init fresh
sleep 1
push_attempt
if push_attempt; then exit 90; fi
echo "$PUSH_ATTEMPT:$PUSH_STOP"
''')
    assert out.strip().startswith('1:time budget exhausted')


def test_original_origin_change_is_sticky_not_recaptured(original):
    run,_,owner,_,_=original
    out=run('''push_retry_init fresh
before="$PUSH_QLEDGER_ORIGINAL_DIGEST"
git remote set-url origin different.git
if push_attempt; then exit 90; fi
[ "$before" = "$PUSH_QLEDGER_ORIGINAL_DIGEST" ]
echo "$PUSH_FAIL_CLASS:$PUSH_STOP"
''')
    assert out.strip().startswith('qledger-original-facts:original facts unavailable or uncertain')
    assert (owner/'original-push.json').is_file()


def test_lost_capture_ack_cannot_reinitialize_or_resource_away_unknown(original):
    run,_,owner,_,_=original
    out=run(f'''python3() {{
  command python3 "$@"
  case "$*" in *capture-push-original*) return 75 ;; esac
}}
if push_retry_init fresh; then exit 90; fi
before="$PUSH_DEADLINE:$PUSH_ATTEMPT:$PUSH_TERMINAL_RC"
unset -f python3
. {shlex.quote(str(LIB))}
if push_retry_init replacement; then exit 91; fi
if push_attempt; then exit 92; fi
[ "$before" = "$PUSH_DEADLINE:$PUSH_ATTEMPT:$PUSH_TERMINAL_RC" ]
echo held
''')
    assert out.strip()=='held'
    assert (owner/'original-push.json').is_file()


def test_dead_original_shell_cannot_be_replaced_by_new_shell_inputs(original):
    run,_,owner,_,setup=original
    digest=run('push_retry_init fresh; echo "$PUSH_QLEDGER_ORIGINAL_DIGEST"').strip()
    doc=json.loads((owner/'original-push.json').read_bytes());retry=doc['retry']
    out=run(f'''PUSH_DEADLINE={retry['retry_deadline_epoch_seconds']}
PUSH_BUDGET_SECS={retry['retry_budget_seconds']}
PUSH_MAX_ATTEMPTS={retry['max_attempts']}
PUSH_ALARM={retry['git_push_alarm_seconds']}
PUSH_ATTEMPT=0
PUSH_QLEDGER_ORIGINAL_DIGEST={digest}
if _push_qledger_original inspect; then exit 90; fi
echo refused
''')
    assert out.strip()=='refused'
    assert sha256((owner/'original-push.json').read_bytes()).hexdigest()==digest


def test_cannot_bind_original_facts_after_legacy_init(original):
    run,_,owner,_,setup=original
    source_line,bind_line,*_=setup.splitlines()
    out=run(source_line+'\npush_retry_init old\nif '+bind_line+'; then exit 90; fi\necho refused\n',setup_override='')
    assert out.strip()=='refused'
    assert not (owner/'original-push.json').exists()


def test_missing_original_record_is_not_recreated_on_inspection(original):
    run,_,owner,_,_=original
    out=run('''push_retry_init fresh
rm -- "'''+str(owner)+'''/original-push.json"
if push_attempt; then exit 90; fi
if push_retry_init replacement; then exit 91; fi
echo held
''')
    assert out.strip()=='held'
    assert not (owner/'original-push.json').exists()
