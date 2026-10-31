"""Future original bridge against the real engine caller; no nightly replay."""
import json
from pathlib import Path

import pytest

from tests.test_qledger_push_original import original  # noqa: F401
from tests.test_qledger_runner_bootstrap import bootstrap  # noqa: F401
from tests.test_qledger_conversion_candidate import fixture, conversion_invocation  # noqa: F401

SOURCE=Path(__file__).resolve().parents[1]


def engine_init():
    # Execute only the incumbent's actual retry-init block. No normalizers,
    # producers, staging, commit, rebase, network or old run is executed.
    text=(SOURCE/'scripts/ci/daily_engine_commit_outputs.sh').read_text()
    block=text.split('PUSH_ALARM=420\n',1)[1].split('push_retry_init "engine outputs"',1)[0]
    return 'PUSH_ALARM=420\n'+block+'push_retry_init "engine outputs"\n'


def test_future_engine_original_records_actual_600_20_420_contract(original):
    run,_,owner,_,_=original
    out=run(engine_init()+'''before="$PUSH_DEADLINE:$PUSH_QLEDGER_ORIGINAL_DIGEST"
push_attempt
[ "$before" = "$PUSH_DEADLINE:$PUSH_QLEDGER_ORIGINAL_DIGEST" ]
if push_retry_init replacement; then exit 90; fi
echo "$PUSH_ATTEMPT:$PUSH_MAX_ATTEMPTS:$PUSH_BUDGET_SECS:$PUSH_ALARM"
''')
    assert out.strip()=='1:20:600:420'
    doc=json.loads((owner/'original-push.json').read_bytes())
    assert doc['retry']['retry_budget_seconds']==600
    assert doc['retry']['max_attempts']==20
    assert doc['retry']['git_push_alarm_seconds']==420
    assert doc['resource_assurance']=='PRIVATE_ROOT_CUSTODY_ONLY_POLICY_NOT_PROVIDED'
    assert not (owner/'qledger-installed.json').exists()
    assert not (owner/'bundle/IMPORT_OCCURRED').exists()


@pytest.mark.parametrize('change',['PUSH_BUDGET_SECS=420','PUSH_MAX_ATTEMPTS=10','PUSH_ALARM=0'])
def test_future_engine_original_refuses_recast_engine_budget_or_alarm(original,change):
    run,_,owner,_,_=original
    out=run(engine_init()+'''before="$PUSH_DEADLINE:$PUSH_QLEDGER_ORIGINAL_DIGEST"
'''+change+'''
if push_attempt; then exit 90; fi
[ "$PUSH_ATTEMPT" -eq 0 ]
[ "$before" = "$PUSH_DEADLINE:$PUSH_QLEDGER_ORIGINAL_DIGEST" ]
echo "$PUSH_FAIL_CLASS"
''')
    assert out.strip()=='qledger-original-facts'
    assert (owner/'original-push.json').is_file()
    assert not (owner/'qledger-installed.json').exists()
