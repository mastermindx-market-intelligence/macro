"""Real qualifier with explicit synthetic syscall data; no OS/service proof."""
import copy
import pickle

import pytest

from engine.research_factory import market_memory_e0_native_peer as peer
from tests.market_memory_native_peer_fixtures import native_peer_primitives, native_peer_capability


def test_real_factory_and_current_binding(native_peer_capability,native_peer_primitives):
    peer.require_current_broker_service(native_peer_capability)
    value=peer.broker_service_binding(native_peer_capability)
    assert value['ssh_key_fingerprint']==native_peer_primitives['fingerprint']
    assert value['restriction_profile']==peer.PROFILE
    assert value['native_executable']['version']=='OpenSSH_9.6p1 Ubuntu-SYNTHETIC'
    assert set(value)=={'ssh_key_fingerprint','restriction_profile','forced_command','native_observation_sha256','native_executable','journal_profile'}
    assert peer.PROFILE == 'memory.e0.protected_m2_service_ssh.v2'
    assert all(argv[0] == '/usr/bin/journalctl' for argv in native_peer_primitives['calls'])
    value['native_executable'].clear()
    assert peer.broker_service_binding(native_peer_capability)['native_executable']['path']=='/usr/sbin/sshd'


@pytest.mark.parametrize('operation',[copy.copy,copy.deepcopy,pickle.dumps])
def test_nominal_capability_not_copyable(native_peer_capability,operation):
    with pytest.raises(peer.NativePeerError):operation(native_peer_capability)


def test_clone_and_body_mutation_refuse(native_peer_capability):
    clone=object.__new__(peer.NativeBrokerServiceCapability)
    clone._body=native_peer_capability._body;clone._seal=native_peer_capability._seal
    with pytest.raises(peer.NativePeerError):peer.require_current_broker_service(clone)
    native_peer_capability._body=b'{}'
    with pytest.raises(peer.NativePeerError):peer.require_current_broker_service(native_peer_capability)


@pytest.mark.parametrize('mutation',['missing_location','other_location','unsigned_other_location','wrong_boot','wrong_pid','wrong_connection','config_forced','missing_anchor','ancestor_replaced','unsafe_key','unsafe_ancestor','current_image'])
def test_native_join_mutations_refuse(native_peer_primitives,mutation):
    f=native_peer_primitives
    if mutation=='missing_location':f['rows'].pop(1)
    elif mutation=='other_location':f['rows'][1]['MESSAGE']=f['rows'][1]['MESSAGE'].replace(peer.KEY_FILE,'/other/authorized_keys')
    elif mutation=='unsigned_other_location':
        extra=dict(f['rows'][1]);extra['MESSAGE']=extra['MESSAGE'].replace(peer.KEY_FILE,'/other/authorized_keys');f['rows'].insert(2,extra)
    elif mutation=='wrong_boot':f['rows'][2]['_BOOT_ID']='2'*32
    elif mutation=='wrong_pid':f['rows'][2]['_PID']='101'
    elif mutation=='wrong_connection':f['rows'][2]['MESSAGE']=f['rows'][2]['MESSAGE'].replace('127.0.0.2','127.0.0.3')
    elif mutation=='config_forced':f['rows'][3]['MESSAGE']=f['rows'][3]['MESSAGE'].replace('(key-option)','(config)')
    elif mutation=='missing_anchor':f['rows'].pop(0)
    elif mutation=='ancestor_replaced':f['nodes']['/etc/macro']['meta'].st_ctime_ns=3000000000
    elif mutation=='unsafe_key':f['nodes'][peer.KEY_FILE]['meta'].st_mode=0o100644
    elif mutation=='unsafe_ancestor':f['nodes']['/etc/macro']['meta'].st_mode=0o40777
    elif mutation=='current_image':f['nodes']['/usr/sbin/sshd']['meta'].st_uid=501
    with pytest.raises(peer.NativePeerError):peer.observe_current_broker_service()


def test_current_change_revokes_issued_capability(native_peer_capability,native_peer_primitives):
    native_peer_primitives['nodes'][peer.KEY_FILE]['meta'].st_mode=0o100644
    with pytest.raises(peer.NativePeerError):peer.require_current_broker_service(native_peer_capability)


def test_new_service_profile_does_not_misrepresent_current_parse_as_history(native_peer_primitives):
    # A live/permissive daemon followed by tightened disk configuration was the
    # counterexample to the OLD standalone profile. This component now makes no
    # environment assertion; the real qualified M2 client/sole key custody must
    # provide that part of the joined installed contract. Neither value below
    # is consulted as native authority. No successful runtime facade is supplied.
    native_peer_primitives['config']['permituserenvironment']='yes'
    native_peer_primitives['config']['acceptenv']='*'
    cap=peer.observe_current_broker_service()
    binding=peer.broker_service_binding(cap)
    assert binding['restriction_profile']=='memory.e0.protected_m2_service_ssh.v2'
    assert all(argv[0]!='/usr/sbin/sshd' for argv in native_peer_primitives['calls'])
