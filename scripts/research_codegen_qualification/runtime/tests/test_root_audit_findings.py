"""Root reproductions of retained audit findings; invented files/benign cat only."""
from pathlib import Path
import pytest
import test_runsc_install as f
m=f.mod

def test_postcommit_settlement_failure_is_uncertain_not_blocked():
    x=f.Fixture()
    try:
        f.script_happy(x.runner,polls_before_rf=0);e=x.engine()
        def fail(role):
            assert e.committed
            e.freeze();raise m.InstallError('DAEMON_IDENTITY_CHANGED')
        e._poll_state=fail
        code,r=e.execute(x.binding_path,x.binding_sha)
        assert code==m.EXIT_UNCERTAIN
        assert r['config']['committed'] and r['unknowns']
        assert not r['settlement']['confirmed']
        assert r['settlement']['outcome']=='OBSERVATION_FAILED'
        assert r['rollback']=={}
    finally:x.close()

def test_owned_unpublished_stage_is_reported_without_cleanup():
    x=f.Fixture()
    try:
        e=x.engine();e.binding=m.Binding(x.binding_dict,f.TEST_CONTRACT)
        stage=e._stage_bundle()
        e.freeze()
        info=e._final_receipt()['bundle_staging']
        assert info['owned_created'] is True and info['published_by_rename'] is False
        assert info['path']==stage and info['cleanup_obligation'] is True
        assert Path(stage).is_dir()
    finally:x.close()

def test_staging_checks_file_gid_before_publication(monkeypatch):
    x=f.Fixture()
    try:
        e=x.engine();e.binding=m.Binding(x.binding_dict,f.TEST_CONTRACT)
        actual=m.lstat_meta
        def wrong_gid(path):
            meta=actual(path)
            if '/.stage-' in path and path.endswith('/runsc') and meta:
                return dict(meta,gid=e.root_gid+1)
            return meta
        monkeypatch.setattr(m,'lstat_meta',wrong_gid)
        with pytest.raises(m.InstallError,match='BUNDLE_STAGE_VERIFY_FAILED'):e._stage_bundle()
        assert not Path(x.version_dir()).exists()
    finally:x.close()

def test_initial_settlement_failure_survives_successful_rollback():
    x=f.Fixture()
    try:
        f.script_preflight(x.runner)
        x.runner.script(rc=0,out=b'',err=b'');x.runner.script(rc=0,out=b'',err=b'')
        f.script_poll(x.runner,rf=False,show=f.SHOW_FAILED)
        x.runner.script(rc=0,out=b'',err=b'');f.script_poll(x.runner,rf=False)
        x.runner.script(out=b'0\n');x.runner.script(out=b'0\n')
        code,r=x.engine().execute(x.binding_path,x.binding_sha)
        assert r['status']=='OK_ROLLED_BACK'
        assert r['settlement']['outcome']=='SERVICE_NOT_ACTIVE'
        assert r['rollback']['settlement']['outcome']=='VERIFIED'
    finally:x.close()

def test_production_poll_cadence_fits_existing_output_budget():
    x=f.Fixture()
    try:
        e=x.engine(settlement_window_seconds=m.SETTLEMENT_WINDOW_SECONDS,
                   settlement_interval_seconds=m.SETTLEMENT_INTERVAL_SECONDS,
                   sleeper=lambda s:x.clock.bump(s))
        e.runner=m.BoundedRunner(e.budget,binaries=frozenset({'/bin/cat'}),monotonic=x.clock)
        e.default_runtime_before='runc';e.runtime_mapping_before={'runc':{'path':'runc'}}
        data=Path(x.scratch)/'invented-poll-output';data.write_bytes(b'x'*650)
        e.budget.spend_output(1024)
        started=x.clock()
        def poll(role):
            e._run(['/bin/cat',str(data)],role)
            inventory=dict(e.runtime_mapping_before)
            if x.clock()-started>=45:inventory[m.RUNTIME_NAME]=e._expected_entry()
            return {'service':{'ActiveState':'active'},'runtimes':inventory,'default':'runc'}
        e._poll_state=poll
        state=e._settle('main',True)
        assert state['verified'] and state['polls']<=6
        assert e.budget.spent_output_bytes<=8192
    finally:x.close()

@pytest.mark.parametrize('component',['','/gvisor-bin'])
def test_bundle_gid_is_part_of_metadata_contract(monkeypatch,component):
    x=f.Fixture()
    try:
        x.write_exact_bundle();e=x.engine();e.binding=m.Binding(x.binding_dict,f.TEST_CONTRACT)
        actual=m.lstat_meta
        def wrong_gid(path):
            meta=actual(path)
            if path==x.version_dir()+component:meta=dict(meta,gid=e.root_gid+1)
            return meta
        monkeypatch.setattr(m,'lstat_meta',wrong_gid)
        assert not e._verify_bundle_dir(x.version_dir())
    finally:x.close()
